#!/usr/bin/env python3
"""Give the Android build a version that rises with every push.

The android/ project is regenerated from the Capacitor template on every CI run, and the
template hardcodes versionCode 1 / versionName "1.0". Play Console rejects an upload whose
versionCode is not higher than the one already published, so every build would collide
with the first release.

versionName is the version in package.json (what the app and the listing show);
versionCode is a plain counter derived from the commit count, which only ever grows.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BUILD_GRADLE = os.path.join(ROOT, 'android', 'app', 'build.gradle')
PACKAGE_JSON = os.path.join(ROOT, 'package.json')

# Floor: high enough to sit above whatever the first published build used, so the very
# first CI run does not collide with a version code Play already has.
VERSION_CODE_BASE = 1000


def main() -> int:
    if not os.path.exists(BUILD_GRADLE):
        sys.exit('FATAL: %s missing — run `npx cap add android` first.' % BUILD_GRADLE)

    with open(PACKAGE_JSON) as f:
        version = json.load(f)['version'].strip()
    if not re.match(r'^\d+(\.\d+){1,3}$', version):
        sys.exit('FATAL: cannot use version %r from package.json' % version)

    commit_count = int(subprocess.check_output(
        ['git', 'rev-list', '--count', 'HEAD'], cwd=ROOT).decode().strip())
    version_code = VERSION_CODE_BASE + commit_count

    src = open(BUILD_GRADLE).read()
    src, n_code = re.subn(r'(\s*versionCode\s+)\d+', r'\g<1>%d' % version_code, src, count=1)
    src, n_name = re.subn(
        r'(\s*versionName\s+)"[^"]*"',
        lambda m: m.group(1) + '"' + version + '"',
        src, count=1)
    if n_code == 0 or n_name == 0:
        sys.exit('FATAL: could not find versionCode/versionName in %s' % BUILD_GRADLE)

    open(BUILD_GRADLE, 'w').write(src)
    print('set versionCode=%d versionName="%s" (commits: %d)'
          % (version_code, version, commit_count))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
