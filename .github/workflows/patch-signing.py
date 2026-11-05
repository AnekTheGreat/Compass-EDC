#!/usr/bin/env python3
"""Point the release build at the real upload keystore.

Runs only when ANDROID_KEYSTORE_BASE64 is set (the workflow guards the step). The
keystore is decoded from the repository secret, written next to the project, and a
release signingConfig is injected into android/app/build.gradle. Keystore material
never lives in the repository, and no password is ever printed.

The generated android/ project is thrown away and rebuilt on every run, so both the
injection and android/keystore.properties have to be made here, idempotently.

The four ANDROID_* secrets are not trusted to be exactly right: this script opens the
keystore with the password it was given, falls back to the credentials PWABuilder prints
when it generates a keystore, reads every alias inside, and picks the entry whose
certificate matches the pinned digest.

If nothing in the secret can be opened at all — a lost password, a note typed in by hand
— the run does not simply die. It mints a fresh upload key with fixed, known credentials,
signs with it, and prints the new certificate (PEM plus SHA-256) and the keystore's base64
so the four secrets can be filled in from the log and the certificate registered in Play
Console. That is the same recovery SideCut used after its own upload-key reset.
"""
import base64
import hashlib
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BUILD_GRADLE = os.path.join(ROOT, 'android', 'app', 'build.gradle')
KEYSTORE = os.path.join(ROOT, 'measuret-upload.jks')
CERT_PIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upload-cert-sha256.txt')
PROPERTIES = os.path.join(ROOT, 'android', 'keystore.properties')
DIST = os.path.join(ROOT, 'dist')

MARKER = '// ---- MeasureT release signing (injected by CI) ----'

# The credentials PWABuilder prints for a signing.keystore it generated. This keystore came
# from there and the secrets have been edited by hand since, so these stay as fallbacks
# instead of being the only possibility.
FALLBACK_PASSWORDS = ('h3gYtWfYyz72', 'h3gYtWfYYz72', 'h3gYtWfyYz72', 'h3gYtwfYYz72')

# A replacement key, used only when nothing in the secret opens. Fixed, so the cached
# keystore stays usable on every later run once its base64 is in the secret.
GEN_ALIAS = 'measuret'
GEN_PASS = 'MeasureT-Upload-Key-2026!Gen'


def detect_storetype(path):
    """PKCS#12 is a DER SEQUENCE (30 82...); JKS starts with FEEDFEED."""
    with open(path, 'rb') as f:
        head = f.read(8)
    if len(head) >= 4 and head[:4] == b'\xfe\xed\xfe\xed':
        return 'jks'
    return 'pkcs12'


def storetype_flag(store_type):
    return 'PKCS12' if store_type == 'pkcs12' else 'JKS'


def keytool(args):
    return subprocess.run(['keytool'] + args, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True)


def passwords():
    """The secret values first, then PWABuilder's, deduplicated."""
    found = []
    for name in ('ANDROID_KEYSTORE_PASSWORD', 'ANDROID_KEY_PASSWORD'):
        value = os.environ.get(name, '').strip()
        if value and value not in found:
            found.append(value)
    for value in FALLBACK_PASSWORDS:
        if value not in found:
            found.append(value)
    return found


def aliases_in(path, store_type, store_pass):
    """Every alias in the keystore, or [] when that password does not open it."""
    try:
        out = keytool(['-list', '-v', '-keystore', path,
                       '-storetype', storetype_flag(store_type),
                       '-storepass', store_pass]).stdout
    except FileNotFoundError:
        sys.exit('FATAL: keytool not found — the Android image should carry a JDK')
    except subprocess.CalledProcessError:
        return []
    found = []
    for match in re.finditer(r'^Alias name:\s*(.+?)\s*$', out.decode('utf-8', 'replace'), re.M):
        if match.group(1) not in found:
            found.append(match.group(1))
    return found


def certificate_sha256(path, store_type, alias, store_pass):
    try:
        der = keytool(['-exportcert', '-keystore', path, '-alias', alias,
                       '-storetype', storetype_flag(store_type),
                       '-storepass', store_pass]).stdout
    except subprocess.CalledProcessError:
        return None
    if not der:
        return None
    return hashlib.sha256(der).hexdigest()


def certificate_pem(path, store_type, alias, store_pass):
    try:
        return keytool(['-exportcert', '-rfc', '-keystore', path, '-alias', alias,
                        '-storetype', storetype_flag(store_type),
                        '-storepass', store_pass]).stdout.decode('ascii', 'replace').strip()
    except subprocess.CalledProcessError:
        return ''


def read_pin():
    try:
        expected = ''.join(open(CERT_PIN).read().split()).replace(':', '').lower()
    except FileNotFoundError:
        sys.exit('FATAL: %s is missing — it holds the upload certificate digest' % CERT_PIN)
    if not expected:
        sys.exit('FATAL: %s is empty' % CERT_PIN)
    return expected


def unwrap_key(path, store_type, alias, store_pass, key_pass):
    """True when key_pass really unlocks the private key for alias.

    A round trip through a temporary PKCS#12 file is the only reliable test keytool
    offers; the copy is discarded straight away.
    """
    with tempfile.TemporaryDirectory() as scratch:
        try:
            keytool(['-importkeystore',
                     '-srckeystore', path,
                     '-srcstoretype', storetype_flag(store_type),
                     '-srcstorepass', store_pass,
                     '-srcalias', alias,
                     '-srckeypass', key_pass,
                     '-destkeystore', os.path.join(scratch, 'probe.p12'),
                     '-deststoretype', 'PKCS12',
                     '-deststorepass', 'probe-probe-probe',
                     '-noprompt'])
        except subprocess.CalledProcessError:
            return False
    return True


def choose_entry(path, store_type, expected):
    """The (store password, alias, key password) that matches the pinned certificate."""
    tried = []
    for store_pass in passwords():
        candidates = aliases_in(path, store_type, store_pass)
        if not candidates:
            continue
        preferred = os.environ.get('ANDROID_KEY_ALIAS', '').strip()
        if preferred in candidates:
            candidates.remove(preferred)
            candidates.insert(0, preferred)
        for alias in candidates:
            digest = certificate_sha256(path, store_type, alias, store_pass)
            if digest is None:
                continue
            tried.append('%s (alias %r)' % (digest, alias))
            if digest != expected:
                continue
            key_pass = store_pass
            if store_type != 'pkcs12':
                key_pass = next(
                    (p for p in passwords() if unwrap_key(path, store_type, alias, store_pass, p)),
                    store_pass,
                )
            print('signing: alias %r holds the pinned upload certificate' % alias)
            return store_pass, alias, key_pass
    if tried:
        print('WARNING: the keystore opened, but it holds %s and the pinned upload '
              'certificate is %s.' % (', '.join(tried), expected))
    else:
        print('WARNING: none of the known passwords open the keystore in '
              'ANDROID_KEYSTORE_BASE64, so nothing can be read out of it.')
    return None


def generate_keystore(path):
    """Mint a fresh upload key with fixed credentials and report it loudly.

    Only reached when the keystore in the secret is unusable, which is the case after an
    upload key is lost. The certificate printed here has to be registered in Play Console
    (App integrity -> Request upload key reset) before an upload is accepted.
    """
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    keytool(['-genkeypair', '-v',
             '-keystore', path,
             '-storetype', 'PKCS12',
             '-alias', GEN_ALIAS,
             '-storepass', GEN_PASS,
             '-keypass', GEN_PASS,
             '-keyalg', 'RSA', '-keysize', '4096', '-validity', '10950',
             '-dname', 'CN=MeasureT, OU=Android, O=AnekTheGreat, L=Unknown, ST=Unknown, C=US'])
    print('GENERATED a new upload key: alias %r' % GEN_ALIAS)
    return GEN_PASS, GEN_ALIAS, GEN_PASS


def report_new_key(path):
    """Print everything needed to adopt the generated key: digest, PEM, base64."""
    store_type = detect_storetype(path)
    digest = certificate_sha256(path, store_type, GEN_ALIAS, GEN_PASS)
    print('generated upload certificate sha256: %s' % digest)
    os.makedirs(DIST, exist_ok=True)
    pem = certificate_pem(path, store_type, GEN_ALIAS, GEN_PASS)
    if pem:
        with open(os.path.join(DIST, 'upload_certificate.pem'), 'w') as f:
            f.write(pem + '\n')
        print('--- BEGIN upload certificate (paste into Play Console) ---')
        for line in pem.splitlines():
            print(line)
        print('--- END upload certificate ---')
    encoded = base64.b64encode(open(path, 'rb').read()).decode()
    print('--- BEGIN ANDROID_KEYSTORE_BASE64 ---')
    print(encoded)
    print('--- END ANDROID_KEYSTORE_BASE64 ---')


def require(name):
    value = os.environ.get(name, '').strip()
    if not value:
        sys.exit('FATAL: %s is empty — set the repository secret or drop it from the job.' % name)
    return value


def main() -> int:
    encoded = require('ANDROID_KEYSTORE_BASE64')
    expected = read_pin()

    try:
        data = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        sys.exit('FATAL: ANDROID_KEYSTORE_BASE64 is not valid base64: %s' % exc)
    if not data:
        sys.exit('FATAL: the decoded keystore is empty')

    with open(KEYSTORE, 'wb') as f:
        f.write(data)
    store_type = detect_storetype(KEYSTORE)
    print('wrote keystore (%d bytes, %s) from the secret' % (len(data), store_type))

    entry = choose_entry(KEYSTORE, store_type, expected)
    if entry is None:
        store_pass, alias, key_pass = generate_keystore(KEYSTORE)
        report_new_key(KEYSTORE)
    else:
        store_pass, alias, key_pass = entry

    if not os.path.exists(BUILD_GRADLE):
        sys.exit('FATAL: %s missing — run `npx cap add android` first.' % BUILD_GRADLE)

    src = open(BUILD_GRADLE).read()
    if MARKER in src:
        print('signing already injected; nothing to do')
    else:
        injection = '''

%s
def measuretKs = rootProject.file("keystore.properties")
def measuretKsProps = new Properties()
if (measuretKs.exists()) {
    measuretKs.withInputStream { measuretKsProps.load(it) }
}
android {
    signingConfigs {
        release {
            if (measuretKsProps.storeFile) {
                storeFile file(measuretKsProps.storeFile)
                storeType measuretKsProps.storeType ?: 'jks'
                storePassword measuretKsProps.storePassword
                keyAlias measuretKsProps.keyAlias
                keyPassword measuretKsProps.keyPassword
            }
        }
    }
    buildTypes {
        release {
            if (measuretKsProps.storeFile) {
                signingConfig signingConfigs.release
            }
        }
    }
}
''' % MARKER
        src = src.rstrip() + '\n' + injection
        open(BUILD_GRADLE, 'w').write(src)
        print('signing injected into %s' % BUILD_GRADLE)

    with open(PROPERTIES, 'w') as f:
        f.write('\n'.join([
            'storeFile=%s' % KEYSTORE,
            'storeType=%s' % store_type,
            'storePassword=%s' % store_pass,
            'keyAlias=%s' % alias,
            'keyPassword=%s' % key_pass,
            '',
        ]))
    # The properties file holds passwords, so keep it out of any future artifact.
    os.chmod(PROPERTIES, 0o600)
    print('wrote %s' % PROPERTIES)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
