#!/usr/bin/env python3
"""Declare the permissions MeasureT actually uses in the generated manifest.

The android/ project is regenerated from the Capacitor template on every CI run, so an
edit to AndroidManifest.xml cannot be committed -- it is applied here, after
`npx cap add android` and before Gradle builds.

Only what the app really needs is added, because a WebView refuses a browser API unless the
host app itself holds the matching Android permission:

  * ACCESS_FINE_LOCATION -- `navigator.geolocation`, read by the elevation / altitude
    screens and the one-tap "Measure a person's height" button;
  * CAMERA -- `getUserMedia`, which the AR object-height and AR person-height modes start
    on the rear camera (`video.facingMode = 'environment'`).

The compass, level and unit tools are pure sensors and need no permission at all.
"""
import os
import re
import sys

MANIFEST = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'android', 'app', 'src', 'main',
    'AndroidManifest.xml'))

PERMISSIONS = [
    'android.permission.ACCESS_FINE_LOCATION',
    'android.permission.ACCESS_COARSE_LOCATION',
    'android.permission.CAMERA',
]

# The manifest also gets <uses-feature> entries so Play does not treat the missing
# hardware as a reason to filter the app out of a device's listing.
FEATURES = [
    ('android.hardware.location.gps', 'false'),
    ('android.hardware.sensor.compass', 'false'),
    ('android.hardware.camera', 'false'),
    ('android.hardware.camera.autofocus', 'false'),
]


def main() -> int:
    if not os.path.exists(MANIFEST):
        sys.exit('FATAL: %s missing — run `npx cap add android` first.' % MANIFEST)

    src = open(MANIFEST).read()
    inserted = 0
    for perm in PERMISSIONS:
        if perm in src:
            print('already present: %s' % perm)
            continue
        src, n = re.subn(
            r'(<manifest[^>]*>)',
            r'\g<1>\n    <uses-permission android:name="%s" />' % perm,
            src, count=1)
        if n == 0:
            sys.exit('FATAL: no <manifest> tag in %s\n--- head ---\n%s' % (MANIFEST, src[:500]))
        inserted += 1

    for name, required in FEATURES:
        if name in src:
            print('already present: %s' % name)
            continue
        src, n = re.subn(
            r'(<manifest[^>]*>)',
            r'\g<1>\n    <uses-feature android:name="%s" android:required="%s" />' % (name, required),
            src, count=1)
        if n == 0:
            sys.exit('FATAL: no <manifest> tag in %s' % MANIFEST)
        inserted += 1

    open(MANIFEST, 'w').write(src)
    print('inserted %d declaration(s) into %s' % (inserted, MANIFEST))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
