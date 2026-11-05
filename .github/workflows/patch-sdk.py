#!/usr/bin/env python3
"""Raise the generated Android project to the SDK levels Play now requires.

The android/ project is regenerated from the Capacitor template on every CI run, so its
SDK levels cannot be committed -- they are patched here, after `npx cap add android` and
before Gradle builds, the same way patch-manifest.py and patch-version.py work.

Play enforces two things on every upload:

  * minSdkVersion 24 (Android 7.0) or higher. The template ships 23, and Play's automatic
    protection refuses the bundle outright: "requires a minimum SDK version of 24 or
    higher. The uploaded App Bundle has a minimum SDK version of 23."

  * targetSdkVersion 36 (Android 16) for every new app and every update submitted on or
    after 31 August 2026. See
    https://developer.android.com/google/play/requirements/target-sdk

compileSdk has to rise with the target, and compiling against 36 needs Android Gradle
Plugin 8.9.1 or newer (on Gradle 8.11.1 or newer), so those are raised here too when the
template ships something older. The web app already declares `viewport-fit=cover` and
pads with `env(safe-area-inset-*)`, which is what target 36's mandatory edge-to-edge
needs, so no layout change is involved.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
VARIABLES = os.path.join(ROOT, 'android', 'variables.gradle')
BUILD_GRADLE = os.path.join(ROOT, 'android', 'build.gradle')
WRAPPER = os.path.join(ROOT, 'android', 'gradle', 'wrapper', 'gradle-wrapper.properties')

MIN_SDK = 24
TARGET_SDK = 36
COMPILE_SDK = 36

MIN_AGP = '8.9.1'
MIN_GRADLE = '8.11.1'


def version_tuple(text):
    parts = []
    for piece in text.split('.'):
        digits = re.match(r'\d+', piece)
        if not digits:
            break
        parts.append(int(digits.group(0)))
    return tuple(parts)


def at_least(found, wanted):
    a, b = version_tuple(found), version_tuple(wanted)
    width = max(len(a), len(b))
    a += (0,) * (width - len(a))
    b += (0,) * (width - len(b))
    return a >= b


def set_level(src, name, value, path):
    """Rewrite `name = 23` / `name 23` to the required value. Returns (src, changed)."""
    pattern = re.compile(r'(\b%s\s*=?\s*)(\d+)' % re.escape(name))
    match = pattern.search(src)
    if not match:
        sys.exit('FATAL: no %s in %s\n--- file ---\n%s' % (name, path, src[:600]))
    current = int(match.group(2))
    if current == value:
        print('%-18s already %d' % (name, value))
        return src, False
    if current > value:
        # Never lower anything: a template that already ships a higher level is fine.
        print('%-18s %d (already above %d, left alone)' % (name, current, value))
        return src, False
    print('%-18s %d -> %d' % (name, current, value))
    return src[:match.start(2)] + str(value) + src[match.end(2):], True


def raise_agp(src, path):
    match = re.search(r"com\.android\.tools\.build:gradle:([0-9][0-9.]*)", src)
    if not match:
        sys.exit('FATAL: no Android Gradle Plugin classpath in %s' % path)
    current = match.group(1)
    if at_least(current, MIN_AGP):
        print('%-18s %s (new enough)' % ('Android Gradle', current))
        return src, False
    print('%-18s %s -> %s (needed to compile against %d)' % (
        'Android Gradle', current, MIN_AGP, COMPILE_SDK))
    return src[:match.start(1)] + MIN_AGP + src[match.end(1):], True


def raise_gradle(src, path):
    match = re.search(r'gradle-([0-9][0-9.]*)-(all|bin)\.zip', src)
    if not match:
        sys.exit('FATAL: no Gradle distribution in %s' % path)
    current = match.group(1)
    if at_least(current, MIN_GRADLE):
        print('%-18s %s (new enough)' % ('Gradle', current))
        return src, False
    print('%-18s %s -> %s' % ('Gradle', current, MIN_GRADLE))
    return src[:match.start(1)] + MIN_GRADLE + src[match.end(1):], True


def main() -> int:
    for path in (VARIABLES, BUILD_GRADLE, WRAPPER):
        if not os.path.exists(path):
            sys.exit('FATAL: %s missing -- run `npx cap add android` first.' % path)

    src = open(VARIABLES).read()
    changed = False
    for name, value in (('minSdkVersion', MIN_SDK),
                        ('compileSdkVersion', COMPILE_SDK),
                        ('targetSdkVersion', TARGET_SDK)):
        src, did = set_level(src, name, value, VARIABLES)
        changed = changed or did
    if changed:
        open(VARIABLES, 'w').write(src)

    src = open(BUILD_GRADLE).read()
    src, did = raise_agp(src, BUILD_GRADLE)
    if did:
        open(BUILD_GRADLE, 'w').write(src)

    src = open(WRAPPER).read()
    src, did = raise_gradle(src, WRAPPER)
    if did:
        open(WRAPPER, 'w').write(src)

    print('Play requirements: minSdkVersion >= %d, targetSdkVersion >= %d'
          % (MIN_SDK, TARGET_SDK))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
