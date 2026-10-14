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
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BUILD_GRADLE = os.path.join(ROOT, 'android', 'app', 'build.gradle')
KEYSTORE = os.path.join(ROOT, 'measuret-upload.jks')
PROPERTIES = os.path.join(ROOT, 'android', 'keystore.properties')

MARKER = '// ---- MeasureT release signing (injected by CI) ----'


def detect_storetype(path):
    """PKCS#12 is a DER SEQUENCE (30 82...); JKS starts with FEEDFEED."""
    with open(path, 'rb') as f:
        head = f.read(8)
    if len(head) >= 4 and head[:4] == b'\xfe\xed\xfe\xed':
        return 'jks'
    return 'pkcs12'


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
