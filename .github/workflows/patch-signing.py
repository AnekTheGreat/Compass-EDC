#!/usr/bin/env python3
"""Point the release build at the real upload keystore.

Runs only when ANDROID_KEYSTORE_BASE64 is set (the workflow guards the step). The
keystore is decoded from the repository secret, written next to the project, and a
release signingConfig is injected into android/app/build.gradle. Keystore material
never lives in the repository, and no password is ever printed.

The generated android/ project is thrown away and rebuilt on every run, so both the
injection and android/keystore.properties have to be made here, idempotently.
"""
import base64
import hashlib
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BUILD_GRADLE = os.path.join(ROOT, 'android', 'app', 'build.gradle')
KEYSTORE = os.path.join(ROOT, 'measuret-upload.jks')
CERT_PIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upload-cert-sha256.txt')
PROPERTIES = os.path.join(ROOT, 'android', 'keystore.properties')

MARKER = '// ---- MeasureT release signing (injected by CI) ----'


def detect_storetype(path):
    """PKCS#12 is a DER SEQUENCE (30 82...); JKS starts with FEEDFEED."""
    with open(path, 'rb') as f:
        head = f.read(8)
    if len(head) >= 4 and head[:4] == b'\xfe\xed\xfe\xed':
        return 'jks'
    return 'pkcs12'


def verify_certificate(path, store_type, alias, store_pass):
    """Refuse to build unless the keystore holds MeasureT's upload certificate.

    Until 1.2.3 this script only wrote the keystore out, so a keystore that was not the upload key
    still produced a green run and files that looked ready to upload — Play was the first thing to
    say no. The digest is not a secret: it is printed on every APK and on the Play listing.
    """
    try:
        expected = ''.join(open(CERT_PIN).read().split()).replace(':', '').lower()
    except FileNotFoundError:
        sys.exit('FATAL: %s is missing — it holds the upload certificate digest' % CERT_PIN)
    if not expected:
        sys.exit('FATAL: %s is empty' % CERT_PIN)
    try:
        der = subprocess.run(
            ['keytool', '-exportcert', '-keystore', path, '-alias', alias,
             '-storetype', 'PKCS12' if store_type == 'pkcs12' else 'JKS',
             '-storepass', store_pass],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        ).stdout
    except FileNotFoundError:
        sys.exit('FATAL: keytool not found — the Android image should carry a JDK')
    except subprocess.CalledProcessError as exc:
        sys.exit('FATAL: keytool could not read the certificate out of the keystore (wrong '
                 'password or alias?): %s' % exc.stderr.decode('utf-8', 'replace').strip()[:300])
    actual = hashlib.sha256(der).hexdigest()
    print('upload certificate sha256: %s' % actual)
    if actual != expected:
        sys.exit('FATAL: this keystore is not MeasureT\'s upload key (it holds %s, the upload '
                 'certificate is %s), so Play would reject the AAB. Point the four ANDROID_* '
                 'secrets at MeasureT\'s own keystore.' % (actual, expected))
    print('signing: keystore matches the pinned upload certificate')


def require(name):
    value = os.environ.get(name, '').strip()
    if not value:
        sys.exit('FATAL: %s is empty — set the repository secret or drop it from the job.' % name)
    return value


def main() -> int:
    encoded = require('ANDROID_KEYSTORE_BASE64')
    store_pass = require('ANDROID_KEYSTORE_PASSWORD')
    key_pass = os.environ.get('ANDROID_KEY_PASSWORD', '').strip() or store_pass
    alias = require('ANDROID_KEY_ALIAS')

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
    verify_certificate(KEYSTORE, store_type, alias, store_pass)

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
