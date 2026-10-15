#!/usr/bin/env python3
"""
The MeasureT fix that cannot be handed over as a file: app.js is 40 KB and has to arrive
byte for byte, so it travels as this: the six edits, applied to the checked-out file.

WHAT IT FIXES (all three of the owner's reports)

1. "if you switch from convert to measure tab you can go back to the convert tab ... right
   now you can't" - the Convert screen's Measure half is long (a distance readout, three
   action buttons, two cards and the camera viewfinder) and the Convert / Measure switch sat
   at the top of a screen that scrolls, so scrolling down carried the only way back off the
   top edge. The switch is pinned under the top bar, switching returns the screen to the top,
   and tapping the Convert tab itself always lands on the converter.

2. "make sure every time you open the app you don't have to click the permissions again" -
   the location watcher was started the instant the app opened, on every launch, so the OS
   location dialog landed on top of the app every time. The first fix is remembered now and
   the watcher starts again quietly; a phone that has never allowed location is still asked,
   because the compass, the elevation and distance-to-pin all need it.

3. "I don't wanna see 'needs permission to orient sensors' popup everytime" - that panel was
   built on every start whenever the WebView exposed requestPermission, even after the
   sensors had been allowed and were working. It is built once now, and the grant is
   remembered.

It also removes a way for the app to open with dead tabs: every localStorage read is wrapped,
because one uncaught SecurityError from storage used to stop the rest of app.js from ever
attaching its listeners - which is exactly what a screen whose switch and nav do nothing
looks like.

Idempotent: the anchors are looked up first and the file is left alone if it already carries
the fix.

  python3 .github/workflows/patch-measuret-ui.py            # apply, from the repo root
  python3 .github/workflows/patch-measuret-ui.py --check    # report only, exit 1 if behind
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CHECK = '--check' in sys.argv
MARK = 'cedc_sensors_ok'

STORAGE_OLD = """function $(id){ return document.getElementById(id); }"""

STORAGE_NEW = """function $(id){ return document.getElementById(id); }

// localStorage, but never fatal. A WebView with storage switched off throws a
// SecurityError on the first touch of localStorage, and because these reads sit in the
// middle of this file's startup, that one throw used to stop every listener below it from
// ever being attached - which is what a screen with dead tabs, a dead switch and a dead
// nav looks like. Nothing here is allowed to be the reason the app cannot be driven.
function storeGet(k){ try { return localStorage.getItem(k); } catch (e) { return null; } }
function storeSet(k, v){ try { localStorage.setItem(k, v); } catch (e) {} }
var SENSORS_KEY = 'cedc_sensors_ok';
var GEO_KEY = 'cedc_geo_ok';"""

NAV_OLD = """    btn.classList.add('active');
    $(btn.dataset.screen).classList.add('active');
  });
});"""

NAV_NEW = """    btn.classList.add('active');
    $(btn.dataset.screen).classList.add('active');
    // The Convert tab always lands on the converter. That screen carries a Convert / Measure
    // switch of its own, so a tab tap that left the screen on Measure looked like a tap that
    // did nothing at all.
    if (btn.dataset.screen === 'convert-screen') setCovMode('convert');
    if ($(btn.dataset.screen)) $(btn.dataset.screen).scrollTop = 0;
  });
});"""

GEO_OLD = """// ---------- GEOLOCATION ----------
if ('geolocation' in navigator) {
  navigator.geolocation.watchPosition(function(pos){
    state.lat = pos.coords.latitude;
    state.lon = pos.coords.longitude;
    state.gpsAccuracy = pos.coords.accuracy;
    state.speed = pos.coords.speed;
    state.declination = estimateDeclination(state.lat, state.lon);
    if (pos.coords.altitude != null) {
      ingestAltitude(pos.coords.altitude, pos.coords.altitudeAccuracy);
    }
    updateLocationUI();
    sampleMeasure();
    updateMeasureUI();
  }, function(err){
    $('loc-lat').textContent = 'No access';
    $('elev-num').textContent = 'No access';
  }, { enableHighAccuracy: true, maximumAge: 1000, timeout: 15000 });
}"""

GEO_NEW = """// ---------- GEOLOCATION ----------
// ASKED FOR ONCE, AND REMEMBERED. This used to call watchPosition the instant the app
// started, on every single launch, so the OS location dialog landed on top of the app again
// and again until it was allowed - and the app sat behind the dialog while it waited. The
// first fix is written down; from then on the watcher is simply started again, with no
// dialog and nothing to tap. A phone that has never allowed location is still asked, because
// the compass, the elevation and the distance-to-pin all need it - it is asked because it is
// needed, not every time because the app opened.
function onGeoPos(pos){
  storeSet(GEO_KEY, '1');
  state.lat = pos.coords.latitude;
  state.lon = pos.coords.longitude;
  state.gpsAccuracy = pos.coords.accuracy;
  state.speed = pos.coords.speed;
  state.declination = estimateDeclination(state.lat, state.lon);
  if (pos.coords.altitude != null) {
    ingestAltitude(pos.coords.altitude, pos.coords.altitudeAccuracy);
  }
  updateLocationUI();
  sampleMeasure();
  updateMeasureUI();
}
function onGeoErr(){
  $('loc-lat').textContent = 'No access';
  $('elev-num').textContent = 'No access';
}
function startGeoWatch(){
  if (state.geoWatch) return;
  state.geoWatch = navigator.geolocation.watchPosition(onGeoPos, onGeoErr, { enableHighAccuracy: true, maximumAge: 1000, timeout: 15000 });
}
function startGeo(){
  if (storeGet(GEO_KEY)) { startGeoWatch(); return; }
  if (navigator.permissions && navigator.permissions.query) {
    navigator.permissions.query({ name: 'geolocation' }).then(function(p){
      if (p && p.state === 'denied') { onGeoErr(); return; }
      startGeoWatch();
    }).catch(startGeoWatch);
    return;
  }
  startGeoWatch();
}
if ('geolocation' in navigator) { startGeo(); }"""

SENSORS_OLD = """var needsPermission = typeof DeviceOrientationEvent !== 'undefined' &&
  typeof DeviceOrientationEvent.requestPermission === 'function';

if (needsPermission) {"""

SENSORS_NEW = """// ASKED ONCE, NOT ON EVERY LAUNCH. This panel was built on every start, so a phone whose
// WebView exposes requestPermission got "needs motion and orientation sensors" in front of
// it every time the app opened - even after the sensors had been allowed and were working
// fine. The grant is remembered now, and a permission already granted is simply used:
// requestPermission() answers out of the stored state and cannot prompt again.
var needsPermission = typeof DeviceOrientationEvent !== 'undefined' &&
  typeof DeviceOrientationEvent.requestPermission === 'function';

if (needsPermission && !storeGet(SENSORS_KEY)) {"""

GRANT_OLD = """      if (res === 'granted') {
        initOrientation();
        overlay.remove();
      }"""

GRANT_NEW = """      if (res === 'granted') {
        storeSet(SENSORS_KEY, '1');
        initOrientation();
        overlay.remove();
      }"""

COV_OLD = """function setCovMode(m){
  var isC = m === 'convert';
  $('cov-mode-convert').classList.toggle('on', isC);
  $('cov-mode-measure').classList.toggle('on', !isC);
  $('cov-convert-view').style.display = isC ? '' : 'none';
  $('cov-measure-view').style.display = isC ? 'none' : '';
}"""

COV_NEW = """// THE WAY BACK STAYS ON SCREEN. This screen's Measure half is long - a distance readout,
// three action buttons, two cards and the camera viewfinder - and the Convert / Measure
// switch sat at the top of a screen that scrolls, so scrolling down carried the switch off
// the top edge and the only way back to Convert with it. The switch is pinned under the top
// bar now, and switching returns the screen to the top, so Convert is always one tap away.
function pinCovSwitch(){
  var seg = $('cov-mode-convert').parentNode;
  if (!seg) return;
  seg.style.position = 'sticky';
  seg.style.top = '8px';
  seg.style.zIndex = '6';
  seg.style.background = 'rgba(233,244,252,0.94)';
  seg.style.boxShadow = '0 2px 10px rgba(60,120,160,0.10)';
}
function setCovMode(m){
  var isC = m === 'convert';
  $('cov-mode-convert').classList.toggle('on', isC);
  $('cov-mode-measure').classList.toggle('on', !isC);
  $('cov-convert-view').style.display = isC ? '' : 'none';
  $('cov-measure-view').style.display = isC ? 'none' : '';
  var scr = $('convert-screen');
  if (scr) scr.scrollTop = 0;
}
pinCovSwitch();"""

EDITS = [
    ('the storage helpers', STORAGE_OLD, STORAGE_NEW),
    ('the Convert tab', NAV_OLD, NAV_NEW),
    ('the location watcher', GEO_OLD, GEO_NEW),
    ('the sensor panel', SENSORS_OLD, SENSORS_NEW),
    ('remembering the sensor grant', GRANT_OLD, GRANT_NEW),
    ('the Convert / Measure switch', COV_OLD, COV_NEW),
]

path = os.path.join(ROOT, 'app.js')
src = open(path, encoding='utf-8').read()

if MARK in src:
    print('  app.js already carries the fix')
    print('')
    print('patch-measuret-ui: 0 file(s)' + (' (check only)' if CHECK else ''))
    sys.exit(0)

if CHECK:
    print('  PROBLEM app.js does not carry the fix')
    sys.exit(1)

problems = []
for label, old, new in EDITS:
    n = src.count(old)
    if n != 1:
        problems.append('%s: found %d copies of its anchor, expected 1' % (label, n))
        continue
    src = src.replace(old, new)
    print('  %s: done' % label)

if problems:
    for p in problems:
        print('  PROBLEM ' + p)
    sys.exit(1)

open(path, 'w', encoding='utf-8').write(src)
print('')
print('patch-measuret-ui: 1 file(s)')
