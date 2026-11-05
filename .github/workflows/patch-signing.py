#!/usr/bin/env python3
"""Point the release build at the real upload keystore.

Runs only when ANDROID_KEYSTORE_BASE64 is set (the workflow guards the step). The
keystore is decoded from the repository secret, written next to the project, and a
release signingConfig is injected into android/app/build.gradle. Keystore material
never lives in the repository, and no password or key is ever printed — this repository
is public, so a key that reached a build log would be worthless.

The four ANDROID_* secrets are not trusted to be exactly right: the script opens the
keystore with the password it was given, falls back to the credentials PWABuilder prints
when it generates one, reads every alias inside, and uses the entry whose certificate
matches the pinned digest. A stale alias or password therefore cannot slip a bundle
through, and a keystore that is genuinely the wrong key fails loudly instead.
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

MARKER = '// ---- MeasureT release signing (injected by CI) ----'

# The credentials PWABuilder prints for a signing.keystore it generated. They are tried
# only after the secret's own values, so a working secret always wins.
FALLBACK_PASSWORDS = ('h3gYtWfYyz72', 'h3gYtWfYYz72', 'h3gYtWfyYz72', 'h3gYtwfYYz72')


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
        sys.exit('FATAL: the keystore opens, but it holds %s and the pinned upload '
                 'certificate is %s, so Play would reject the AAB. Point the four '
                 'ANDROID_* secrets at the keystore that owns the upload certificate, or '
                 're-pin %s to the certificate the keystore really holds.'
                 % (', '.join(tried), expected, CERT_PIN))
    sys.exit('FATAL: none of the known passwords open the keystore in '
             'ANDROID_KEYSTORE_BASE64 (%d bytes). The secret is not the keystore whose '
             'certificate is pinned — replace it with that keystore, encoded as base64.'
             % os.path.getsize(path))


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

    store_pass, alias, key_pass = choose_entry(KEYSTORE, store_type, expected)

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
