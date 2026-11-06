#!/usr/bin/env python3
"""MeasureT 1.3.1 - updates actually land. The "v1.3.0 is available" loop, ended.

THE REPORT, VERBATIM:

    "the ota update isnt working it keeps getting stuck"

WHAT WAS HAPPENING. Three facts, and the loop is just them meeting:

  1. GitHub Pages serves every file here with `cache-control: max-age=600` - the page, the
     script, the manifest, all of them. Check it with `curl -I`; it is in the headers.
  2. The service worker fetched the *document* with `cache: 'no-store'` and everything else
     with the request as it was, which means app.js could be answered from the WebView's
     HTTP cache for ten minutes.
  3. The version on screen comes from app.js (`APP_VERSION`), while the release feed is read
     with `no-store` and is always current.

So the page arrived new, the script behind it did not: the app kept saying v1.2.3, the feed
kept saying 1.3.0, and every "Update now" reloaded into the same stale script. Nothing was
broken in the release - the phone was reading two files from two different moments.

THE FIX, IN THREE PARTS, because one alone leaves a hole:

  * THE SCRIPT IS ASKED FOR BY A VERSIONED ADDRESS - `app.js?v=1.3.1`. A cache can only
    answer an address it has seen, and no phone has ever seen this one. This is the part
    that fixes a phone whose cache is already poisoned.
  * THE SERVICE WORKER TURNS THE CACHE OFF FOR EVERY FILE, not only the page, so the next
    request for anything goes to the network first. Offline still works: the saved copy is
    still what you get when the network is gone.
  * THE RELOAD IS A FRESH ADDRESS RATHER THAN `location.reload()` - `index.html?v=<version>`
    with a timestamp - so the update cannot land back on the page that offered it. There is
    also a plain **Reload this page** button in Settings -> Updates, for the day a cache
    disagrees with the server again.

Plus the check itself can no longer hang: ten seconds and the row reports no answer instead
of sitting on "Checking...".

WHAT THIS DOES NOT TOUCH: the time-zone chip, elevation, location, the level, the converter
and its six categories, currency, GPS measuring, the AR range finder, permissions. The app's
own content is byte for byte what 1.3.0 shipped.

Idempotent: the markers are `app.js?v=1.3.1` in index.html and `hardReload` in app.js.

  python3 dev/patch-131.py            # apply, from the repo root
  python3 dev/patch-131.py --check    # report only, exit 1 if behind
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CHECK = '--check' in sys.argv
VERSION = '1.3.1'
OLD_VERSION = '1.3.0'
MARK_HTML = 'app.js?v=' + VERSION
MARK_JS = 'hardReload'

problems = []


def read(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return f.read()


def write(name, text):
    with open(os.path.join(ROOT, name), 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def sub(text, old, new, name):
    n = text.count(old)
    if n != 1:
        problems.append('%s: anchor appears %d times, expected 1' % (name, n))
        return text
    return text.replace(old, new)


# ---------------------------------------------------------------------------
# 1. index.html - the versioned script, the version line, and a way out.
# ---------------------------------------------------------------------------
SCRIPT_OLD = '<script src="app.js"></script>'
SCRIPT_NEW = ('<!-- 1.3.1 - THE SCRIPT IS ASKED FOR BY A VERSIONED ADDRESS. GitHub Pages sends\n'
              '     max-age=600 on every file, and a cache can only answer an address it has seen;\n'
              '     this one is new with every release, so a stale copy cannot be handed back. -->\n'
              '<script src="app.js?v=%s"></script>' % VERSION)

ABOUT_OLD = '<span id="app-version-line">v%s</span>' % OLD_VERSION
ABOUT_NEW = '<span id="app-version-line">v%s</span>' % VERSION

SETTINGS_OLD = """      <div class="set-row">
        <div><div class="label">Check for updates</div><div class="sub" id="ota-status">Checking&hellip;</div></div>
        <button class="unitbtn" id="btn-check-updates">Check</button>
      </div>
    </div>"""

SETTINGS_NEW = """      <div class="set-row">
        <div><div class="label">Check for updates</div><div class="sub" id="ota-status">Checking&hellip;</div></div>
        <button class="unitbtn" id="btn-check-updates">Check</button>
      </div>
      <!-- 1.3.1 - the way out of a stuck update: a fresh address cannot be answered by a
           cached copy, so this loads the real page from the server. -->
      <div class="set-row">
        <div><div class="label">Reload this page</div><div class="sub">Use this if an update seems stuck</div></div>
        <button class="unitbtn" id="btn-reload-page">Reload</button>
      </div>
    </div>"""

# ---------------------------------------------------------------------------
# 2. app.js - the release, the fresh-address reload, and the ten-second check.
# ---------------------------------------------------------------------------
APP_OLD = "var APP_VERSION = '%s';" % OLD_VERSION
APP_NEW = "var APP_VERSION = '%s';" % VERSION

CHANGELOG_OLD = """var CHANGELOG = [
  { version: '1.3.0',"""

CHANGELOG_NEW = """var CHANGELOG = [
  { version: '1.3.1', date: 'November 6, 2026', title: 'Updates that never took: the version loop is gone', items: [
    'Fixed the update that kept getting stuck: the page and its script are each cached for <b>ten minutes</b> by the site that hosts them, and while the page was being fetched fresh the script was not. The app therefore kept reporting the version from the <b>old script</b> while the release feed kept offering the new one &mdash; <b>Update now</b> landed back on the same version, every time.',
    'The script now comes from a <b>versioned address</b>, so every release is a file the phone has never seen and cannot answer from its cache; the service worker also stopped trusting the browser cache for <b>all</b> of the app&rsquo;s files, not only the page.',
    'The <b>Check for updates</b> row can no longer sit on &ldquo;Checking&hellip;&rdquo; forever: ten seconds and it reports that there was no answer.',
    'Settings &rarr; Updates now ends with <b>Reload this page</b>, which loads the app from a fresh address &mdash; there if a phone&rsquo;s cache ever disagrees with the server again.',
    'Nothing else changed &mdash; the time-zone chip, elevation, location, the level, the converter and its six categories, currency, GPS measuring, the AR range finder and permissions are exactly as they were.'
  ]},
  { version: '1.3.0',"""

APPLY_OLD = """function applyUpdate(m){
  if (m && m.version) storeSet('cedc_ota_seen_' + m.version, '1');
  var dlg = $('ota-dialog'); if (dlg) dlg.remove();
  if (setOtaStatus) setOtaStatus('Updating\u2026');
  if (!('serviceWorker' in navigator)) { location.reload(); return; }
  var done = false;
  function finish(){ if (done) return; done = true; location.reload(); }"""

APPLY_NEW = """// 1.3.1 - A FRESH ADDRESS, NOT A RELOAD. A plain reload asks for the same URL again, and
// the WebView is allowed to answer that from its cache: GitHub Pages sends max-age=600 on
// every file, so a reload can land back on the very page that offered the update. A URL with
// the version and a timestamp on it is one no cache has ever seen.
function hardReload(version){
  var url = 'index.html?v=' + encodeURIComponent(version || APP_VERSION) + '&t=' + Date.now();
  if (location.replace) location.replace(url); else location.href = url;
}
function applyUpdate(m){
  if (m && m.version) storeSet('cedc_ota_seen_' + m.version, '1');
  var dlg = $('ota-dialog'); if (dlg) dlg.remove();
  if (setOtaStatus) setOtaStatus('Updating\u2026');
  if (!('serviceWorker' in navigator)) { hardReload(m && m.version); return; }
  var done = false;
  function finish(){ if (done) return; done = true; hardReload(m && m.version); }"""

FETCH_OLD = """  return fetch(OTA_ENDPOINT, { cache: 'no-store' })
    .then(function(r){ if (!r.ok) throw new Error('http ' + r.status); return r.json(); })"""

FETCH_NEW = """  // 1.3.1 - ten seconds and it is an answer, not a spinner. A fetch that never settles used
  // to leave the Settings row on "Checking\u2026" for the rest of the session, with nothing
  // to tap. AbortController ends the request; the timer ends the wait.
  function otaFetch(){
    var ctrl = (typeof AbortController === 'function') ? new AbortController() : null;
    var opts = { cache: 'no-store' };
    if (ctrl) opts.signal = ctrl.signal;
    return new Promise(function(resolve, reject){
      var timer = setTimeout(function(){
        if (ctrl) { try { ctrl.abort(); } catch (e) {} }
        reject(new Error('timeout'));
      }, 10000);
      fetch(OTA_ENDPOINT, opts).then(function(r){ clearTimeout(timer); resolve(r); },
                                     function(e){ clearTimeout(timer); reject(e); });
    });
  }
  return otaFetch()
    .then(function(r){ if (!r.ok) throw new Error('http ' + r.status); return r.json(); })"""

WIRE_OLD = """if ($('btn-check-updates')) $('btn-check-updates').addEventListener('click', function(){ checkForUpdates(true); });"""

WIRE_NEW = """if ($('btn-check-updates')) $('btn-check-updates').addEventListener('click', function(){ checkForUpdates(true); });
// 1.3.1 - the escape hatch in the UI, for a cache that disagrees with the server.
if ($('btn-reload-page')) $('btn-reload-page').addEventListener('click', function(){ hardReload(APP_VERSION); });"""

# ---------------------------------------------------------------------------
# 3. sw.js - the cache is off for every file, and the versioned script is precached.
# ---------------------------------------------------------------------------
SW_ASSETS_OLD = """var CACHE = 'measuret-v%s';
var ASSETS = [
  './index.html',
  './app.js',""" % OLD_VERSION

SW_ASSETS_NEW = """var CACHE = 'measuret-v%s';
// 1.3.1 - VER is the version the page stamps onto its script address, so the precache asks
// for the same file the page will ask for (and keeps the plain address for older pages).
var VER = CACHE.replace('measuret-v', '');
var ASSETS = [
  './index.html',
  './app.js?v=' + VER,
  './app.js',""" % OLD_VERSION

SW_FETCH_OLD = """  var isDocument = e.request.mode === 'navigate' || e.request.destination === 'document';
  var netRequest = isDocument
    ? new Request(e.request.url, { cache: 'no-store', credentials: 'same-origin', mode: 'same-origin' })
    : e.request;"""

SW_FETCH_NEW = """  var isDocument = e.request.mode === 'navigate' || e.request.destination === 'document';
  // 1.3.1 - EVERY FILE GOES TO THE NETWORK WITH THE CACHE OFF, not just the page. GitHub
  // Pages serves each of them with max-age=600, so app.js could come out of the WebView's
  // HTTP cache while the page was already new: the app showed the version from the old
  // script, the feed kept offering the new one, and every "Update now" reloaded into the
  // same stale script. That loop is what this replaces.
  // A navigation request cannot be copied into a Request (the spec forbids it), so the
  // document is rebuilt from its URL; everything else keeps its own headers and only loses
  // its cache mode. The offline fallback below is untouched.
  var netRequest;
  if (isDocument){
    netRequest = new Request(e.request.url, { cache: 'no-store', credentials: 'same-origin', mode: 'same-origin' });
  } else {
    try { netRequest = new Request(e.request, { cache: 'no-store' }); }
    catch (err) { netRequest = new Request(e.request.url, { cache: 'no-store' }); }
  }"""

# ---------------------------------------------------------------------------
# 4. PATCH_NOTES.md
# ---------------------------------------------------------------------------
NOTES_OLD = '## 1.3.0 \u2014 November 6, 2026'

NOTES_NEW = """## 1.3.1 \u2014 November 6, 2026

**Updates that never took: the version loop is gone**

- The app's page and its script are each cached for **ten minutes** by the host, and only the page was being fetched fresh. The app therefore reported the version from the **old script** while the release feed kept offering the new one: **Update now** landed back on the same version, every time.
- The script is now requested by a **versioned address** (`app.js?v=1.3.1`), which no phone's cache has ever seen, and the service worker no longer trusts the browser cache for **any** of the app's files.
- **Check for updates** can no longer sit on "Checking…" forever: ten seconds and it reports that there was no answer.
- Settings → Updates ends with **Reload this page**, which loads the app from a fresh address — the way out if a cache ever disagrees with the server again.
- Nothing else changed — the time-zone chip, elevation, location, the level, the converter, currency, GPS measuring, the AR range finder and permissions are as they were.

## 1.3.0 \u2014 November 6, 2026"""


def main():
    html = read('index.html')
    js = read('app.js')
    sw = read('sw.js')
    notes = read('PATCH_NOTES.md')

    already = (MARK_HTML in html) and (MARK_JS in js)

    if CHECK:
        checks = [
            ('index.html is %s' % VERSION, ABOUT_NEW in html),
            ('index.html asks for the versioned script', MARK_HTML in html),
            ('index.html has the reload row', 'id="btn-reload-page"' in html),
            ('app.js is %s' % VERSION, APP_NEW in js),
            ('app.js reloads to a fresh address', 'function hardReload(version)' in js and "'index.html?v='" in js),
            ('app.js no longer plain-reloads the page', 'location.reload()' not in js),
            ('app.js times the update check out', 'function otaFetch()' in js and '10000' in js),
            ('app.js wires the reload button', "btn-reload-page" in js),
            ('app.js head changelog entry is %s' % VERSION, "var CHANGELOG = [\n  { version: '%s'," % VERSION in js),
            ('sw.js knows the stamped version', "var VER = CACHE.replace('measuret-v', '')" in sw),
            ('sw.js precaches the versioned script', "'./app.js?v=' + VER" in sw),
            ('sw.js bypasses the cache for every file', "new Request(e.request, { cache: 'no-store' })" in sw),
            ('PATCH_NOTES.md has %s' % VERSION, '## %s' % VERSION in notes),
        ]
        bad = [n for n, ok in checks if not ok]
        for n, ok in checks:
            print(('  ok    ' if ok else '  MISS  ') + n)
        if bad:
            print('\n%d missing - the tree is behind %s' % (len(bad), VERSION))
            return 1
        print('\nall %d checks pass - the tree carries %s' % (len(checks), VERSION))
        return 0

    if already:
        print('%s is already applied - nothing to do' % VERSION)
        return 0

    html = sub(html, SCRIPT_OLD, SCRIPT_NEW, 'index.html: versioned script')
    html = sub(html, ABOUT_OLD, ABOUT_NEW, 'index.html: version line')
    html = sub(html, SETTINGS_OLD, SETTINGS_NEW, 'index.html: reload row')

    js = sub(js, APP_OLD, APP_NEW, 'app.js: APP_VERSION')
    js = sub(js, CHANGELOG_OLD, CHANGELOG_NEW, 'app.js: changelog head')
    js = sub(js, APPLY_OLD, APPLY_NEW, 'app.js: applyUpdate + hardReload')
    js = sub(js, FETCH_OLD, FETCH_NEW, 'app.js: update check timeout')
    js = sub(js, WIRE_OLD, WIRE_NEW, 'app.js: reload button wiring')

    sw = sub(sw, SW_ASSETS_OLD, SW_ASSETS_NEW, 'sw.js: precache assets')
    sw = sub(sw, SW_FETCH_OLD, SW_FETCH_NEW, 'sw.js: fetch handler')

    notes = sub(notes, NOTES_OLD, NOTES_NEW, 'PATCH_NOTES.md: new section')

    if problems:
        print('\n'.join(problems))
        print('\n%d anchor(s) did not match - nothing written' % len(problems))
        return 1

    write('index.html', html)
    write('app.js', js)
    write('sw.js', sw)
    write('PATCH_NOTES.md', notes)
    print('MeasureT %s applied to index.html, app.js, sw.js and PATCH_NOTES.md' % VERSION)
    print('next: node dev/ota.mjs   (republishes updates.json, stamps sw.js and package.json)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
