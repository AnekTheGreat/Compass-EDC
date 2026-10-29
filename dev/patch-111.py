#!/usr/bin/env python3
"""MeasureT 1.1.1 - there is always a way out of the Measure half of Convert.

THE OWNER'S REPORT, VERBATIM:

    "I SHOULD BE ABLE TO GO BACK TO THE OTHER MODE IN MEASURET NOT STUCK IN THIS MODE"

and the screenshot that came with it is the evidence this release is built on: the Convert
tab, the 0 m readout, Start / Drop pin / Reset - and **no switch at all**. Straight from the
CONVERT title to the distance. Two earlier releases (1.0.x) tried to keep that switch on
screen by making it sticky and refusing to let it shrink. It is still not on screen, so the
lesson is the one worth writing down:

    a control that is the ONLY way out must not depend on the layout that hid it.

So the way out moves inside the Measure half itself, in normal flow, as its first child: a
plain full-width "Convert" button above the readout. It cannot be sticky-clipped, cannot be
shrunk by flex (it is not the only child of a scroll container any more), cannot scroll under
a top bar - it is the top of the content it belongs to, and it is the first thing on the
screen the moment the Measure half opens.

THE SWITCH IS ALSO REPAIRED, because it should work too. Its rule never reserved height for
it: `.seg` is `display:flex` with `overflow:hidden` and no min-height, so as a flex item of
the column scroller its automatic minimum is 0 - the spec's overflow trap, and the exact
thing that clipped both buttons out of the picture. It now carries `flex-shrink:0` in CSS
(where a layout rule belongs, instead of an inline style set from JavaScript after the first
paint) and a 44 px floor, which is a thumb target even if a font ever renders short.

What this does NOT do: it does not touch the converter, the GPS measurement, the AR range
finder, the compass, the permissions or the OTA machinery. Nothing here is new behaviour -
only a second, earlier, simpler door to the behaviour that already exists.

Idempotent: the marker is the back button's id in index.html.

  python3 dev/patch-111.py            # apply, from the repo root
  python3 dev/patch-111.py --check    # report only, exit 1 if behind
"""
import datetime
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CHECK = '--check' in sys.argv
VERSION = '1.1.1'
OLD_VERSION = '1.1.0'
MARK = 'btn-measure-back'

# ---------------------------------------------------------------------------
# 1. index.html - the switch reserves its own height, in CSS.
# ---------------------------------------------------------------------------
SEG_OLD = ".seg{display:flex;background:rgba(255,255,255,0.45);border:1px solid var(--glass-line);border-radius:12px;overflow:hidden;margin-bottom:12px;}"

SEG_NEW = """/* 1.1.1 - THE SWITCH RESERVES ITS HEIGHT. This panel is overflow:hidden, so as a flex item
   its automatic minimum height is 0 by spec: the taller Measure half could shrink it to a
   sliver and clip both buttons out, which is the switch that "disappeared". A floor of 44px
   and no shrinking are stated here, where layout belongs, instead of being patched in from
   JavaScript after the first paint. */
.seg{display:flex;flex-shrink:0;min-height:44px;background:rgba(255,255,255,0.45);border:1px solid var(--glass-line);border-radius:12px;overflow:hidden;margin-bottom:12px;}"""

# ---------------------------------------------------------------------------
# 2. index.html - and the way out becomes the first thing in the Measure half.
# ---------------------------------------------------------------------------
VIEW_OLD = """    <div id="cov-measure-view" style="display:none;">
      <div class="big-elev">"""

VIEW_NEW = """    <div id="cov-measure-view" style="display:none;">
      <!-- 1.1.1 - THE WAY OUT, IN THE CONTENT ITSELF. The Convert / Measure switch above is
           the only other way back, and it is a sticky flex item that two releases in a row
           failed to keep on screen. This button is plain flow, the first child of the view
           it leaves, so nothing about the layout can hide it: opening Measure puts a
           Convert button at the top of the screen, before the readout. -->
      <button class="cov-action" id="btn-measure-back" style="margin-bottom:12px;">&#8592; Convert</button>
      <div class="big-elev">"""

# ---------------------------------------------------------------------------
# 3. app.js - it does exactly what the switch does.
# ---------------------------------------------------------------------------
LISTENER_OLD = "$('cov-mode-measure').addEventListener('click', function(){ setCovMode('measure'); });"

LISTENER_NEW = """$('cov-mode-measure').addEventListener('click', function(){ setCovMode('measure'); });
// 1.1.1 - the way out of the Measure half, from inside the Measure half. Guarded: a page
// from an older cache could be paired with this script for one load, and a missing button
// must not stop the rest of the file from wiring itself up.
if ($('btn-measure-back')){
  $('btn-measure-back').addEventListener('click', function(){ setCovMode('convert'); });
}"""

# ---------------------------------------------------------------------------
# 4. app.js - the release is this version, with its own entry at the head.
# ---------------------------------------------------------------------------
CHANGELOG_OLD = "var CHANGELOG = [\n  { version: '1.1.0',"

CHANGELOG_NEW = """var CHANGELOG = [
  { version: '1.1.1', date: '%s', title: 'There is always a way back to Convert', items: [
    'A <b>Convert</b> button now sits at the top of the Measure half itself &mdash; the first thing on the screen, above the distance readout. The switch at the top of the tab is no longer the only way back, so opening Measure can never leave you with nowhere to go.',
    'The <b>Convert / Measure switch</b> reserves its own height now (44 px, and it refuses to shrink). It is the one panel on that screen whose rounded corners clip it, and the Measure half was squeezing it to a sliver: that is the switch that kept disappearing.',
    'Nothing else changed &mdash; the converter, GPS measuring, the AR range finder, the compass, permissions and updates are exactly as they were.'
  ]},
  { version: '1.1.0',""" % (datetime.datetime.now(datetime.timezone.utc).strftime('%B %-d, %Y'))

APP_VERSION_OLD = "var APP_VERSION = '%s';" % OLD_VERSION
APP_VERSION_NEW = "var APP_VERSION = '%s';" % VERSION


def swap(src, old, new, what, path):
    count = src.count(old)
    if count != 1:
        raise SystemExit('patch-111: %s appears %d times in %s, expected 1'
                         % (what, count, path))
    return src.replace(old, new)


def main():
    html_path = os.path.join(ROOT, 'index.html')
    app_path = os.path.join(ROOT, 'app.js')
    html = open(html_path, encoding='utf-8').read()
    app = open(app_path, encoding='utf-8').read()

    if MARK in html and ("var APP_VERSION = '%s';" % VERSION) in app:
        print('  present: MeasureT %s - the Measure half carries its own way back' % VERSION)
        print('patch-111%s: 0 file(s)' % (' (check only)' if CHECK else ''))
        return 0
    if CHECK:
        print('  PROBLEM MeasureT %s is not in the tree' % VERSION)
        return 1

    if ("var APP_VERSION = '%s';" % OLD_VERSION) not in app:
        sys.exit('patch-111: app.js is not %s, so it is not the shape this release expects'
                 % OLD_VERSION)

    html = swap(html, SEG_OLD, SEG_NEW, 'the switch rule', 'index.html')
    html = swap(html, VIEW_OLD, VIEW_NEW, 'the head of the Measure view', 'index.html')
    app = swap(app, LISTENER_OLD, LISTENER_NEW, 'the switch listener', 'app.js')
    app = swap(app, CHANGELOG_OLD, CHANGELOG_NEW, 'the changelog head', 'app.js')
    app = swap(app, APP_VERSION_OLD, APP_VERSION_NEW, 'the version', 'app.js')

    for needle, why in ((MARK, 'the back button'), ("var APP_VERSION = '%s';" % VERSION, 'the version'),
                        ("{ version: '%s'," % VERSION, 'the changelog entry')):
        if needle not in html and needle not in app:
            sys.exit('patch-111: the tree did not end up carrying %s' % why)
    if 'min-height:44px' not in html:
        sys.exit('patch-111: the switch rule did not end up reserving its height')

    open(html_path, 'w', encoding='utf-8').write(html)
    open(app_path, 'w', encoding='utf-8').write(app)
    print('  index.html: the switch reserves its height, the Measure half carries a Convert button')
    print('  app.js: the button is wired, the changelog head is %s, the version is %s'
          % (VERSION, VERSION))
    print('patch-111: 2 file(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
