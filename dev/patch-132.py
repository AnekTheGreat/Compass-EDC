#!/usr/bin/env python3
"""1.3.2: UNote is on the More apps list, and this release carries it.

The page already names UNote; this stamps the version so the phone is offered the
page it now holds. dev/ota.mjs regenerates updates.json from this changelog entry
and stamps the service worker and package.json, so all four agree before the APK
is built.
"""
import io
import subprocess
import sys

V = '1.3.2'
PREV = '1.3.1'


def read(p):
    return io.open(p, encoding='utf-8').read()


def write(p, s):
    io.open(p, 'w', encoding='utf-8').write(s)


def applied():
    try:
        return "var APP_VERSION = '%s';" % V in read('app.js')
    except IOError:
        return False


if applied():
    print('%s is already in the tree - nothing to do' % V)
    sys.exit(0)
if '--check' in sys.argv:
    print('%s is not in the tree yet' % V)
    sys.exit(1)

src = read('app.js')
old = "var APP_VERSION = '%s';" % PREV
if src.count(old) != 1:
    sys.exit('app.js is not on %s' % PREV)
src = src.replace(old, "var APP_VERSION = '%s';" % V, 1)

anchor = 'var CHANGELOG = [\n'
if src.count(anchor) != 1:
    sys.exit('app.js has no CHANGELOG list')
entry = (
    "  { version: '%s', date: 'November 8, 2026', title: 'UNote is on the More apps list', items: [\n"
    "    'UNote is on the More apps list, reading &ldquo;Notes that link themselves, with a vault behind a PIN&rdquo;. It is a page rather than a store listing, so the row opens it in the phone&rsquo;s own browser &mdash; nothing to install and nothing to update.',\n"
    "    'Everything else is as it was: the compass, the elevation, the location and the level.',\n"
    "  ]},\n" % V)
src = src.replace(anchor, anchor + entry, 1)
write('app.js', src)

subprocess.check_call(['node', 'dev/ota.mjs'])
subprocess.check_call(['node', 'dev/ota.mjs', '--check'])
print('%s written: app.js, updates.json, sw.js and package.json' % V)
