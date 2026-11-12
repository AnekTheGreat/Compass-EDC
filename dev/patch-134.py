#!/usr/bin/env python3
"""MeasureT 1.3.4 - measuring at a distance.

The AR distance reading was capped by its own guard: the aim angle was clamped to
3 degrees, and eye height over tan(3 degrees) is 30.5 m, so every target past about
thirty metres read the same thirty metres.

  * the aim is read across the whole range, signed, so aiming above the horizon
    says "aim at the base" instead of wrapping round into a distance
  * it is smoothed, and the screen says to hold steady while the aim still moves
  * the reading carries its own accuracy, in metres, under the number
  * the camera modes share one tilt pipeline

--check says whether the tree ALREADY carries the change, which is what the apply
workflow asks before deciding there is nothing to do.

    python3 dev/patch-134.py            # apply
    python3 dev/patch-134.py --check    # verify only, writes nothing
"""

import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.js")
PAGE = os.path.join(ROOT, "index.html")

V = "1.3.4"
OLD = "1.3.3"

ENTRY = """    { version: '%s', date: 'November 12, 2026', title: 'Measuring at a distance', items: [
      'The AR distance reading no longer stops at about thirty metres. The aim angle was clamped to 3 degrees, and eye height divided by tan(3 degrees) is 30.5 m, so every target past roughly thirty metres - a house, a tree, the far end of a field - read the same thirty metres. The floor is gone and the aim is read across the whole range.',
      'The tilt is smoothed before it is used. A single sensor sample drifts by a fraction of a degree, and eye height divided by tan(angle) turns every fraction into metres out there, which is why the number used to jump about. It follows the aim through a low-pass filter now, and says <b>hold steady</b> while the aim is still moving.',
      'The reading says how much to trust it: a line under the number gives what half a degree of aim is worth at that distance, e.g. <i>about \\u00b1 3 m at this distance</i>. At a very shallow aim it says the number is a guess instead of printing one.',
      'The sign of the tilt is respected. Holding the phone past vertical used to fold the angle round into nonsense, because the old reading took the absolute value of the tilt; aiming above the horizon now says <b>aim at the base</b>.',
      'The camera modes read one tilt pipeline, smoothed the way the level smooths its own bubble, so the level and the range finder cannot disagree about how far the phone is tilted.'
    ] },
""" % V

ANCHOR = "var CHANGELOG = [\n"

DECL_OLD = """var arActive = false, arStream = null, arTimer = null;
window.__arBeta = null;
window.__arBetaRaw = null;
"""

DECL_NEW = """var arActive = false, arStream = null, arTimer = null;
// 1.3.4 - one tilt pipeline. `beta`: 0 is flat on its back (camera at the floor), 90 is
// upright (camera level), 180 is flat on its face. The aim is 90 - beta, positive aimed
// down. The old reading kept Math.abs(beta) and clamped the aim to 3 degrees, and eye
// height over tan(3 degrees) is 30.5 m - which is why everything past thirty metres read
// thirty metres.
var arTilt = null;        // smoothed aim in degrees, + = aimed down, - = aimed up
var arJitter = 0;         // how far the raw aim moves between samples, in degrees
var arPrevAim = null;
"""

AIM_OLD = """window.addEventListener('deviceorientation', function(e){
  if (arActive && e.beta != null){ window.__arBetaRaw = e.beta; window.__arBeta = Math.abs(e.beta); }
});
function arAimDelta(){ // signed degrees below horizontal (+ = aiming down)
  if (window.__arBetaRaw == null) return null;
  return 90 - window.__arBetaRaw;
}
"""

AIM_NEW = """function arAimFromBeta(beta){
  if (beta == null || !isFinite(beta)) return null;
  // Outside this the phone is upside down, which is not an aim at anything.
  if (beta < -90 || beta > 180) return null;
  return 90 - beta;
}
function arFeedTilt(beta){
  var aim = arAimFromBeta(beta);
  if (aim == null) return;
  if (arTilt == null) arTilt = aim;
  else arTilt += (aim - arTilt) * 0.22;   // the sensor moves by fractions of a degree
  if (arPrevAim != null) arJitter += (Math.abs(aim - arPrevAim) - arJitter) * 0.3;
  arPrevAim = aim;
}
window.addEventListener('deviceorientationabsolute', function(e){ if (arActive) arFeedTilt(e.beta); }, true);
window.addEventListener('deviceorientation', function(e){ if (arActive) arFeedTilt(e.beta); }, true);
function arAimDelta(){ // signed degrees below horizontal (+ = aiming down)
  return arTilt == null ? null : arTilt;
}
"""

REPORT_OLD = """function arReport(){
  if (!arActive) return;
  if (window.__arBeta == null){ $('ar-dist').textContent = 'Hold steady &amp; aim downward'; return; }
  var theta = 90 - window.__arBeta; // degrees below horizontal
  theta = Math.abs(theta);
  theta = Math.max(3, Math.min(87, theta));
  var m = arHeight / Math.tan(theta * Math.PI / 180);
  $('ar-dist').textContent = formatDistance(m);
  arReportPerson();
}
"""

REPORT_NEW = """function arReport(){
  if (!arActive) return;
  if (arTilt == null){
    $('ar-dist').textContent = 'Hold steady & aim down';
    setARStatus('Hold the phone still for a moment so the tilt can settle.');
    return;
  }
  var theta = arTilt;
  if (theta < 0.4){
    $('ar-dist').textContent = 'Aim at the base';
    setARStatus('The camera is level: put the crosshair where the object meets the ground.');
    arReportPerson();
    return;
  }
  var deg = Math.min(88, theta);
  var m = arHeight / Math.tan(deg * Math.PI / 180);
  $('ar-dist').textContent = formatDistance(m);
  // Half a degree of aim is worth this many metres here; below about 2.5 degrees the answer
  // is a guess dressed up as a number, and it says so.
  var near = arHeight / Math.tan(Math.min(88, deg + 0.5) * Math.PI / 180);
  var far = arHeight / Math.tan(Math.max(0.4, deg - 0.5) * Math.PI / 180);
  var spread = Math.max(0.5, (far - near) / 2);
  var shown = spread >= 1 ? String(Math.round(spread)) : spread.toFixed(1);
  if (deg < 2.5) setARStatus('Very shallow aim - about \\u00b1 ' + shown + ' m out here. Step closer for a number worth trusting.');
  else if (arJitter > 1.2) setARStatus('Hold steady: the aim is moving about ' + arJitter.toFixed(1) + '\\u00b0 between readings.');
  else setARStatus('About \\u00b1 ' + shown + ' m at this distance.');
  arReportPerson();
}
"""

START_OLD = """    window.__arBeta = null;
    arTimer = setInterval(arReport, 120);
"""

START_NEW = """    arTilt = null;
    arPrevAim = null;
    arJitter = 0;
    arTimer = setInterval(arReport, 120);
"""

STOP_OLD = """function stopAR(){
  arActive = false;
"""

STOP_NEW = """function stopAR(){
  arActive = false;
  arTilt = null; arPrevAim = null; arJitter = 0;
"""

HINT_OLD = ("Distance is estimated as height &divide; tan(aim angle) \u2014 approximate, "
            "works best outdoors with GPS accuracy reachable.")

HINT_NEW = ("Distance is eye height &divide; tan(aim angle), so the further the target the "
            "shallower the aim and the rougher the answer: the line under the reading says "
            "how rough. Keep the phone still while you read it - a moving hand is worth "
            "several metres out there.")


def once(text, old, what):
    n = text.count(old)
    if n != 1:
        raise SystemExit("patch-134: %s appears %d times, expected exactly 1" % (what, n))
    return text


def patched_app(src):
    if ("var APP_VERSION = '%s';" % V) in src and "function arFeedTilt(" in src:
        return src
    once(src, "var APP_VERSION = '%s';" % OLD, "the version line")
    once(src, ANCHOR, "the changelog")
    once(src, DECL_OLD, "the AR state declarations")
    once(src, AIM_OLD, "the tilt listener")
    once(src, REPORT_OLD, "arReport")
    once(src, START_OLD, "the start reset")
    once(src, STOP_OLD, "stopAR")
    out = src.replace("var APP_VERSION = '%s';" % OLD, "var APP_VERSION = '%s';" % V, 1)
    out = out.replace(ANCHOR, ANCHOR + ENTRY, 1)
    out = out.replace(DECL_OLD, DECL_NEW, 1)
    out = out.replace(AIM_OLD, AIM_NEW, 1)
    out = out.replace(REPORT_OLD, REPORT_NEW, 1)
    out = out.replace(START_OLD, START_NEW, 1)
    out = out.replace(STOP_OLD, STOP_NEW, 1)
    return out


def patched_page(src):
    if HINT_NEW in src and ('app.js?v=%s' % V) in src:
        return src
    out = src
    if ('<span id="app-version-line">v%s</span>' % OLD) in out:
        out = out.replace('<span id="app-version-line">v%s</span>' % OLD,
                          '<span id="app-version-line">v%s</span>' % V, 1)
    if ('app.js?v=%s' % OLD) in out:
        out = out.replace('app.js?v=%s' % OLD, 'app.js?v=%s' % V, 1)
    once(out, HINT_OLD, "the AR hint line")
    return out.replace(HINT_OLD, HINT_NEW, 1)


def main():
    check = "--check" in sys.argv
    app = io.open(APP, encoding="utf-8").read()
    page = io.open(PAGE, encoding="utf-8").read()
    app_new = patched_app(app)
    page_new = patched_page(page)
    if app_new == app and page_new == page:
        print("already on the page")
        return 0
    if check:
        print("not applied yet")
        return 1
    io.open(APP, "w", encoding="utf-8").write(app_new)
    io.open(PAGE, "w", encoding="utf-8").write(page_new)
    # updates.json, sw.js and package.json are stamped from the head CHANGELOG entry.
    try:
        r = subprocess.run(["node", "dev/ota.mjs"], cwd=ROOT, capture_output=True, text=True)
        print((r.stdout or "").strip())
        if r.returncode != 0:
            print((r.stderr or "").strip())
            raise SystemExit("patch-134: dev/ota.mjs failed")
    except FileNotFoundError:
        print("patch-134: node is not here - updates.json must be regenerated before shipping")
    print("app.js at %s, page at v%s" % (V, V))
    return 0


if __name__ == "__main__":
    sys.exit(main())
