#!/usr/bin/env python3
"""MeasureT 1.1.2 - the app can be thanked, the way SideCut can.

SideCut has a Donate tab: five Stripe Payment Links, one fixed amount each, paid on a card page
Stripe hosts and opened in the browser. MeasureT had no way to say thank you at all, so this is
that same tip jar as five rows in Settings, above the version line.

WHAT IS AND IS NOT HERE:

  * a Payment Link is a public URL, so there is no key, no secret and no backend in this repo;
  * the five amounts are SideCut's, so there is one place in the world that knows them;
  * nothing unlocks. MeasureT is the same app whether a tip is paid or not - which is why no
    receipt is ever checked, and why an offline phone simply cannot open the page.

Each row is an ordinary <a> with target="_blank", so it works in a browser (a new tab) and in
the APK's WebView (the page loads there, and Back comes straight back to the app). No JavaScript
is added: there is nothing to wire.

index.html and app.js are the app and must land byte for byte, and the service worker only
re-ships a new index.html when APP_VERSION moves, so this release is also a version bump with
its own changelog head. node dev/ota.mjs republishes updates.json and stamps sw.js and
package.json from APP_VERSION.

Idempotent: the marker is the Support group's id in index.html.

  python3 dev/patch-support.py            # apply, from the repo root
  python3 dev/patch-support.py --check    # report only, exit 1 if behind
"""
import datetime
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CHECK = '--check' in sys.argv
VERSION = '1.1.2'
OLD_VERSION = '1.1.1'
MARK = 'support-tips'

# dollars -> Stripe Payment Link, the same five tiers in the same order as SideCut's Donate tab.
TIERS = [
    (2, 'https://buy.stripe.com/eVqcN48Yn37BeBOagIdMI00'),
    (5, 'https://buy.stripe.com/28E4gyb6vfUn1P2dsUdMI01'),
    (10, 'https://buy.stripe.com/4gM4gy5Mb8rVbpC1KcdMI02'),
    (25, 'https://buy.stripe.com/6oUdR8fmLaA351e1KcdMI03'),
    (50, 'https://buy.stripe.com/4gM8wOb6v23x8dqcoQdMI04'),
]

# ---------------------------------------------------------------------------
# 1. index.html - a Support group in Settings, just above the version line.
# ---------------------------------------------------------------------------
ANCHOR = '    <div class="about-line">MeasureT <span id="app-version-line">'

rows = ''.join(
    '      <div class="set-row"><div><div class="label">Tip $%d</div>'
    '<div class="sub">Paid on Stripe&rsquo;s own card page</div></div>'
    '<a class="unitbtn" style="text-decoration:none" href="%s" target="_blank" '
    'rel="noopener noreferrer">Pay</a></div>\n' % (dollars, url)
    for dollars, url in TIERS
)

BLOCK = (
    '    <!-- Support: the five Stripe Payment Links SideCut already opens - fixed amounts, a page\n'
    '         Stripe hosts. No key, no backend, and nothing unlocks. -->\n'
    '    <div class="set-group glass" id="%s">\n'
    '      <div class="set-group-title">Support</div>\n'
    '%s'
    '      <div class="set-row"><div><div class="sub">Stripe takes the payment on its own page. '
    'Nothing unlocks &mdash; MeasureT is the same app either way, so this is a thank you.</div>'
    '</div></div>\n'
    '    </div>\n\n'
) % (MARK, rows)

# ---------------------------------------------------------------------------
# 2. app.js - this release is this version, with its own entry at the head.
# ---------------------------------------------------------------------------
APP_VERSION_OLD = "var APP_VERSION = '%s';" % OLD_VERSION
APP_VERSION_NEW = "var APP_VERSION = '%s';" % VERSION
CHANGELOG_OLD = "var CHANGELOG = [\n  { version: '%s'," % OLD_VERSION
CHANGELOG_NEW = """var CHANGELOG = [
  { version: '%s', date: '%s', title: 'MeasureT can be thanked, in Settings', items: [
    'A <b>Support</b> group now sits in Settings, above the version line: five amounts, each one an ordinary Stripe payment page opened in the browser. Nothing unlocks and nothing is sent from the app — a tip is a thank you, and the app is the same either way.',
    'Nothing else changed — the converter, GPS measuring, the AR range finder, the compass, permissions and updates are exactly as they were.'
  ]},
  { version: '%s',""" % (
    VERSION,
    datetime.datetime.now(datetime.timezone.utc).strftime('%B %-d, %Y'),
    OLD_VERSION,
)


def read(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return f.read()


def write(path, text):
    with open(os.path.join(ROOT, path), 'w', encoding='utf-8') as f:
        f.write(text)


def swap(text, old, new, why, path):
    if old not in text:
        print('  !! %s: %s is not where it was - refusing to guess' % (path, why))
        sys.exit(1)
    return text.replace(old, new, 1)


def main():
    print('MeasureT %s - the tip jar' % VERSION)

    # ---- index.html ----
    html = read('index.html')
    if MARK in html:
        print('  index.html: already carries the Support group')
    elif CHECK:
        print('  index.html: MISSING the Support group')
    else:
        html = swap(html, ANCHOR, BLOCK + ANCHOR, 'the version line', 'index.html')
        write('index.html', html)
        print('  index.html: five tip rows in Settings, above the version line')

    # ---- app.js ----
    js = read('app.js')
    if APP_VERSION_NEW in js:
        print('  app.js: already %s' % VERSION)
    elif CHECK:
        print('  app.js: MISSING the %s bump and its changelog head' % VERSION)
    else:
        js = swap(js, APP_VERSION_OLD, APP_VERSION_NEW, 'the version', 'app.js')
        js = swap(js, CHANGELOG_OLD, CHANGELOG_NEW, 'the changelog head', 'app.js')
        write('app.js', js)
        print('  app.js: the version is %s and the changelog head is %s' % (VERSION, VERSION))

    # ---- the check, and the report ----
    html = read('index.html')
    js = read('app.js')
    missing = [tier for tier, url in TIERS if url not in html]
    behind = (
        MARK not in html
        or any(missing)
        or APP_VERSION_NEW not in js
        or ("{ version: '%s'," % VERSION) not in js
    )
    for tier, url in TIERS:
        print('  tip $%-2d %s' % (tier, 'linked' if url in html else 'MISSING'))
    if CHECK and behind:
        print('  -> behind: run without --check')
        sys.exit(1)
    if behind:
        print('  !! still behind after applying - something is not right')
        sys.exit(1)
    print('  -> %s is in place' % VERSION)


main()
