#!/usr/bin/env python3
"""MeasureT 1.3.0 - the Convert tab gets a clock: what time it is anywhere, and how far
that is from your own time.

THE REQUEST, VERBATIM:

    "add a time converter to measureT like different time zones it should tell you the
     difference and what time it is in that area"

So this is not another unit table (a factor between two units is meaningless for zones -
the difference depends on the DATE, because daylight saving moves twice a year in some
places and never in others). It is a third kind of chip on the same row:

    pick a place  ->  its time now, its day now, and the gap from your clock in words.

WHY Intl AND NOT A TABLE OF OFFSETS. A shipped table of "+5:30" constants is wrong the
first time a country changes its rules, and wrong for half the year everywhere that keeps
daylight saving. `Intl.DateTimeFormat(..., {timeZone})` reads the time-zone database that
ships with the phone, updated with Android, so London and New York move on their own
dates and a zone that stopped observing DST last year is right without us shipping
anything. If a WebView is old enough to lack it, the chip says so instead of lying.

WHAT IT DOES NOT TOUCH: elevation, location, the level, the unit converter and its six
categories, currency, GPS measuring, the AR range finder, permissions, updates. The
converter's two selects keep their values; Time simply hides their cards and shows the
clock panel in their place.

Idempotent: the markers are `cov-tz-view` in index.html and `TZ_PLACES` in app.js.

  python3 dev/patch-130.py            # apply, from the repo root
  python3 dev/patch-130.py --check    # report only, exit 1 if behind
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CHECK = '--check' in sys.argv
VERSION = '1.3.0'
OLD_VERSION = '1.2.3'
MARK_HTML = 'cov-tz-view'
MARK_JS = 'TZ_PLACES'

problems = []


def read(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return f.read()


def write(name, text):
    with open(os.path.join(ROOT, name), 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def sub(text, old, new, name):
    """Replace an anchor that must appear exactly once, and remember it if it does not."""
    n = text.count(old)
    if n != 1:
        problems.append('%s: anchor appears %d times, expected 1' % (name, n))
        return text
    return text.replace(old, new)


# ---------------------------------------------------------------------------
# 1. index.html - the styles for the clock panel.
# ---------------------------------------------------------------------------
CSS_ANCHOR = '.cov-equation{font-size:13px;color:var(--dim);margin-top:8px;font-variant-numeric:tabular-nums;}'

CSS_NEW = CSS_ANCHOR + """
/* 1.3.0 - TIME ZONES. The seventh chip on the Convert row is a clock, not a unit table:
   one place's time in large type, its day, the gap from your own clock, and a searchable
   list of places under it. Times are tabular so the ticking numbers do not jitter. */
.tz-time{font-size:46px;font-weight:200;color:var(--text);font-variant-numeric:tabular-nums;letter-spacing:-1px;line-height:1.05;margin-top:6px;}
.tz-day{font-size:13px;color:var(--dim);margin-top:2px;}
.tz-diff{font-size:15px;color:#2f8fd6;margin-top:12px;font-weight:500;line-height:1.4;}
.tz-diff.same{color:var(--dim);}
.tz-you{font-size:12px;color:var(--dim);margin-top:10px;padding-top:10px;border-top:1px solid var(--glass-line);line-height:1.5;}
.tz-you b{color:var(--text);font-weight:500;font-variant-numeric:tabular-nums;}
#tz-search{width:100%;box-sizing:border-box;margin-top:8px;padding:11px 13px;border-radius:13px;background:rgba(255,255,255,0.55);border:1px solid var(--glass-line);font-size:15px;color:var(--text);outline:none;-webkit-appearance:none;appearance:none;}
#tz-search::placeholder{color:var(--dimmer);}
.tz-list{max-height:300px;overflow-y:auto;-webkit-overflow-scrolling:touch;margin-top:10px;}
.tz-item{display:flex;align-items:center;justify-content:space-between;gap:10px;width:100%;box-sizing:border-box;padding:11px 2px;background:none;border:none;border-bottom:1px solid rgba(14,51,80,0.07);text-align:left;font-family:inherit;color:var(--text);}
.tz-item:last-child{border-bottom:none;}
.tz-item.on{color:#2f8fd6;}
.tz-item-name{display:flex;flex-direction:column;min-width:0;}
.tz-item-name b{font-size:14px;font-weight:500;}
.tz-item-name span{font-size:11px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tz-item.on .tz-item-name span{color:#2f8fd6;}
.tz-item-right{display:flex;flex-direction:column;align-items:flex-end;flex-shrink:0;}
.tz-item-time{font-size:15px;font-weight:500;font-variant-numeric:tabular-nums;}
.tz-item-diff{font-size:11px;color:var(--dim);font-variant-numeric:tabular-nums;}
.tz-hint{font-size:12px;color:var(--dim);margin-top:8px;line-height:1.5;}"""

# ---------------------------------------------------------------------------
# 2. index.html - an id on each converter card (Time hides them) and the clock panel.
# ---------------------------------------------------------------------------
UNIT_CARD_OLD = """      <div class="card glass" style="margin-top:16px;">
        <div class="cov-inputrow">
          <input id="cov-value\""""

UNIT_CARD_NEW = """      <div class="card glass" id="cov-unit-card" style="margin-top:16px;">
        <div class="cov-inputrow">
          <input id="cov-value\""""

METHOD_CARD_OLD = """      <div class="card glass" style="margin-top:12px;">
        <div class="l">How to convert</div>"""

METHOD_CARD_NEW = """      <div class="card glass" id="cov-method-card" style="margin-top:12px;">
        <div class="l">How to convert</div>"""

TZ_OLD = """        <div class="cov-equation" id="cov-equation"></div>
      </div>
    </div>
"""

TZ_NEW = """        <div class="cov-equation" id="cov-equation"></div>
      </div>
    </div>

    <!-- 1.3.0 - THE TIME CHIP. Not a unit table: a clock. Pick a place and this card says
         what time it is there, which day it is there, and how far that is from your own
         clock - "3 hours ahead of you" - with the searchable list of places under it. -->
    <div id="cov-tz-view" style="display:none;">
      <div class="card glass" style="margin-top:16px;">
        <div class="l" id="tz-place-label">Place</div>
        <div class="tz-time" id="tz-time">--:--</div>
        <div class="tz-day" id="tz-day">&nbsp;</div>
        <div class="tz-diff" id="tz-diff">Pick a place below.</div>
        <div class="tz-you">Your time <b id="tz-you-time">--:--</b> &middot; <span id="tz-you-zone">your time zone</span></div>
      </div>

      <div class="card glass" style="margin-top:12px;">
        <div class="l">Pick a place</div>
        <input id="tz-search" type="search" autocomplete="off" autocapitalize="words" spellcheck="false" placeholder="City, country or zone">
        <div class="tz-list" id="tz-list"></div>
        <div class="tz-hint" id="tz-hint"></div>
      </div>
    </div>
"""

ABOUT_OLD = '<div class="about-line">MeasureT <span id="app-version-line">v%s</span>' % OLD_VERSION
ABOUT_NEW = '<div class="about-line">MeasureT <span id="app-version-line">v%s</span>' % VERSION

# ---------------------------------------------------------------------------
# 3. app.js - the release, the notes, and the clock itself.
# ---------------------------------------------------------------------------
APP_OLD = "var APP_VERSION = '%s';" % OLD_VERSION
APP_NEW = "var APP_VERSION = '%s';" % VERSION

CHANGELOG_OLD = """var CHANGELOG = [
  { version: '1.2.3',"""

CHANGELOG_NEW = """var CHANGELOG = [
  { version: '1.3.0', date: 'November 6, 2026', title: 'A Time chip in Convert: what time it is anywhere, and how far that is from you', items: [
    'A <b>Time</b> chip now sits at the end of the Convert row. Pick a place from the searchable list &mdash; about fifty of them, from <b>London</b> and <b>Lagos</b> to <b>Tokyo</b> and <b>Auckland</b> &mdash; and the card shows the time there, the day there, and the gap from your own clock in words: <b>3 hours ahead of you</b>, <b>the same time as you</b>, <b>5 hours 45 minutes behind you</b>.',
    'Your own time sits under it, so both clocks are on one screen, and the place you last picked is remembered &mdash; reopening the chip shows the same clock instead of an empty card.',
    'The times come from the phone&rsquo;s own time-zone database, so daylight saving is whatever each place is actually doing that day: London and New York change on their own dates, and neither of them is your date.',
    'Nothing else changed &mdash; elevation, location, the level, the unit converter and its six categories, currency, GPS measuring, the AR range finder, permissions and updates are exactly as they were.'
  ]},
  { version: '1.2.3',"""

SETCAT_OLD = """function setCovCat(cat){
  covCat = cat;
  document.querySelectorAll('.cov-chip').forEach(function(c){ c.classList.toggle('on', c.getAttribute('data-cat') === cat); });
  fillCovSelects();
  updateCovResult();
}"""

SETCAT_NEW = """function setCovCat(cat){
  covCat = cat;
  document.querySelectorAll('.cov-chip').forEach(function(c){ c.classList.toggle('on', c.getAttribute('data-cat') === cat); });
  // 1.3.0 - Time is a chip like the others, but it is not a unit table: it hides the two
  // converter cards and shows the clock panel in their place, instead of refilling the
  // selects. Their values are left alone, so going back to Length lands where it was.
  var isTime = cat === 'time';
  if ($('cov-unit-card')) $('cov-unit-card').style.display = isTime ? 'none' : '';
  if ($('cov-method-card')) $('cov-method-card').style.display = isTime ? 'none' : '';
  if ($('cov-tz-view')) $('cov-tz-view').style.display = isTime ? '' : 'none';
  if (isTime){ tzOn(); return; }
  tzOff();
  fillCovSelects();
  updateCovResult();
}"""

CHIPS_OLD = """function buildCovChips(){
  var row = $('cov-cats');
  row.innerHTML = '';
  Object.keys(CONVERTERS).forEach(function(k){
    var b = document.createElement('button');
    b.className = 'cov-chip' + (k === covCat ? ' on' : '');
    b.setAttribute('data-cat', k);
    b.textContent = CAT_LABEL[k];
    b.addEventListener('click', function(){ setCovCat(k); });
    row.appendChild(b);
  });
}"""

CHIPS_NEW = """function buildCovChips(){
  var row = $('cov-cats');
  row.innerHTML = '';
  Object.keys(CONVERTERS).forEach(function(k){
    var b = document.createElement('button');
    b.className = 'cov-chip' + (k === covCat ? ' on' : '');
    b.setAttribute('data-cat', k);
    b.textContent = CAT_LABEL[k];
    b.addEventListener('click', function(){ setCovCat(k); });
    row.appendChild(b);
  });
  // 1.3.0 - the clock, last so the six unit tables keep the order people know.
  var t = document.createElement('button');
  t.className = 'cov-chip' + (covCat === 'time' ? ' on' : '');
  t.setAttribute('data-cat', 'time');
  t.textContent = 'Time';
  t.addEventListener('click', function(){ setCovCat('time'); });
  row.appendChild(t);
}"""

RESULT_OLD = """function updateCovResult(){
  var from = $('cov-from').value, to = $('cov-to').value;"""

RESULT_NEW = """function updateCovResult(){
  if (covCat === 'time') return; // the clock panel has no two-unit answer to print
  var from = $('cov-from').value, to = $('cov-to').value;"""

TZ_ANCHOR = """function haversine(lat1, lon1, lat2, lon2){"""

TZ_BLOCK = r'''// ---------- TIME ZONES (1.3.0) ----------
// The seventh chip of the Convert row: what time it is somewhere else, and how far that is
// from here. Nothing here is a fixed offset. Every answer comes from Intl, i.e. the
// time-zone database the phone itself carries, so daylight saving is whatever that place
// is doing on that date - the clocks in London and New York move on their own dates, and a
// zone that stopped observing DST last year is simply right.
var TZ_KEY = 'cedc_tz_place';
var TZ_PLACES = [
  ['London', 'United Kingdom', 'Europe/London'],
  ['Dublin', 'Ireland', 'Europe/Dublin'],
  ['Lisbon', 'Portugal', 'Europe/Lisbon'],
  ['Reykjavik', 'Iceland', 'Atlantic/Reykjavik'],
  ['Paris', 'France', 'Europe/Paris'],
  ['Berlin', 'Germany', 'Europe/Berlin'],
  ['Madrid', 'Spain', 'Europe/Madrid'],
  ['Rome', 'Italy', 'Europe/Rome'],
  ['Amsterdam', 'Netherlands', 'Europe/Amsterdam'],
  ['Zurich', 'Switzerland', 'Europe/Zurich'],
  ['Stockholm', 'Sweden', 'Europe/Stockholm'],
  ['Warsaw', 'Poland', 'Europe/Warsaw'],
  ['Athens', 'Greece', 'Europe/Athens'],
  ['Istanbul', 'Turkey', 'Europe/Istanbul'],
  ['Moscow', 'Russia', 'Europe/Moscow'],
  ['Lagos', 'Nigeria', 'Africa/Lagos'],
  ['Nairobi', 'Kenya', 'Africa/Nairobi'],
  ['Cairo', 'Egypt', 'Africa/Cairo'],
  ['Johannesburg', 'South Africa', 'Africa/Johannesburg'],
  ['Casablanca', 'Morocco', 'Africa/Casablanca'],
  ['Dubai', 'United Arab Emirates', 'Asia/Dubai'],
  ['Riyadh', 'Saudi Arabia', 'Asia/Riyadh'],
  ['Tehran', 'Iran', 'Asia/Tehran'],
  ['Karachi', 'Pakistan', 'Asia/Karachi'],
  ['Delhi', 'India', 'Asia/Kolkata'],
  ['Kathmandu', 'Nepal', 'Asia/Kathmandu'],
  ['Dhaka', 'Bangladesh', 'Asia/Dhaka'],
  ['Yangon', 'Myanmar', 'Asia/Yangon'],
  ['Bangkok', 'Thailand', 'Asia/Bangkok'],
  ['Jakarta', 'Indonesia', 'Asia/Jakarta'],
  ['Singapore', 'Singapore', 'Asia/Singapore'],
  ['Hong Kong', 'China', 'Asia/Hong_Kong'],
  ['Shanghai', 'China', 'Asia/Shanghai'],
  ['Tokyo', 'Japan', 'Asia/Tokyo'],
  ['Seoul', 'South Korea', 'Asia/Seoul'],
  ['Adelaide', 'Australia', 'Australia/Adelaide'],
  ['Sydney', 'Australia', 'Australia/Sydney'],
  ['Melbourne', 'Australia', 'Australia/Melbourne'],
  ['Auckland', 'New Zealand', 'Pacific/Auckland'],
  ['Honolulu', 'United States', 'Pacific/Honolulu'],
  ['Anchorage', 'United States', 'America/Anchorage'],
  ['Vancouver', 'Canada', 'America/Vancouver'],
  ['Los Angeles', 'United States', 'America/Los_Angeles'],
  ['Denver', 'United States', 'America/Denver'],
  ['Phoenix', 'United States', 'America/Phoenix'],
  ['Chicago', 'United States', 'America/Chicago'],
  ['Mexico City', 'Mexico', 'America/Mexico_City'],
  ['New York', 'United States', 'America/New_York'],
  ['Toronto', 'Canada', 'America/Toronto'],
  ['Bogota', 'Colombia', 'America/Bogota'],
  ['Lima', 'Peru', 'America/Lima'],
  ['Sao Paulo', 'Brazil', 'America/Sao_Paulo'],
  ['Buenos Aires', 'Argentina', 'America/Argentina/Buenos_Aires'],
  ['Santiago', 'Chile', 'America/Santiago']
];
var tzPlace = storeGet(TZ_KEY);
var tzTimer = null;
var tzUsable = true;
try {
  new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/London' }).format(new Date());
} catch (e) {
  tzUsable = false; // a WebView without time-zone data; the chip says so rather than lie
}

function tzSpot(){
  for (var i = 0; i < TZ_PLACES.length; i++){ if (TZ_PLACES[i][2] === tzPlace) return TZ_PLACES[i]; }
  tzPlace = 'Europe/London';
  return TZ_PLACES[0];
}
// en-GB for 24-hour (it prints 21:05), the phone's own locale for 12-hour (it prints 9:05 PM),
// and 24:xx folded back to 00:xx because some locales spell midnight that way.
function tzClock(zone, d){
  var opt = { timeZone: zone, hour: '2-digit', minute: '2-digit', hour12: !state.use24h };
  var s = new Intl.DateTimeFormat(state.use24h ? 'en-GB' : undefined, opt).format(d);
  return s.replace(/^24:/, '00:');
}
function tzHereClock(d){
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: !state.use24h });
}
function tzHereZone(){
  try {
    var z = new Intl.DateTimeFormat().resolvedOptions().timeZone;
    return z ? z.replace(/_/g, ' ') : 'your time zone';
  } catch (e) { return 'your time zone'; }
}
function tzDay(zone, d){
  return new Intl.DateTimeFormat(undefined, { timeZone: zone, weekday: 'long', day: 'numeric', month: 'long' }).format(d);
}
// A zone's offset from UTC in minutes, read off its own wall clock: format the instant in
// that zone, reassemble those fields as if they were UTC, and compare with the instant.
function tzOffsetMin(zone, d){
  var parts = new Intl.DateTimeFormat('en-US', {
    timeZone: zone, hour12: false,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  }).formatToParts(d);
  var p = {};
  for (var i = 0; i < parts.length; i++){ if (parts[i].type !== 'literal') p[parts[i].type] = parts[i].value; }
  var h = parseInt(p.hour, 10); if (h === 24) h = 0;
  var asUTC = Date.UTC(parseInt(p.year, 10), parseInt(p.month, 10) - 1, parseInt(p.day, 10),
                       h, parseInt(p.minute, 10), parseInt(p.second, 10));
  return Math.round((asUTC - Math.floor(d.getTime() / 1000) * 1000) / 60000);
}
// Positive means the place is ahead of you. getTimezoneOffset() is minutes to ADD to local
// time to reach UTC, so local offset east is its negative.
function tzDiffMin(zone, d){ return tzOffsetMin(zone, d) + d.getTimezoneOffset(); }
function tzSpanText(mins){
  var a = Math.abs(mins), h = Math.floor(a / 60), m = a % 60, bits = [];
  if (h) bits.push(h + (h === 1 ? ' hour' : ' hours'));
  if (m) bits.push(m + (m === 1 ? ' minute' : ' minutes'));
  return bits.join(' ');
}
function tzDiffLong(mins){
  if (mins === 0) return 'The same time as you';
  return tzSpanText(mins) + (mins > 0 ? ' ahead of you' : ' behind you');
}
function tzDiffShort(mins){
  if (mins === 0) return 'same';
  var a = Math.abs(mins), h = Math.floor(a / 60), m = a % 60;
  return (mins > 0 ? '+' : '-') + h + 'h' + (m ? ' ' + m + 'm' : '');
}
// yyyy-mm-dd in a zone, which is what makes "tomorrow there" answerable: two places can be
// on different dates at the same instant.
function tzStamp(zone, d){
  return new Intl.DateTimeFormat('en-CA', { timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(d);
}
function tzStampIndex(s){
  var p = s.split('-');
  return Math.round(Date.UTC(parseInt(p[0], 10), parseInt(p[1], 10) - 1, parseInt(p[2], 10)) / 86400000);
}
function tzRender(){
  if (!tzUsable || !$('tz-time')) return;
  var now = new Date(), spot = tzSpot();
  var diff = tzDiffMin(spot[2], now);
  var shift = tzStampIndex(tzStamp(spot[2], now)) - tzStampIndex(tzStamp(undefined, now));
  var when = shift > 0 ? 'Tomorrow, ' : (shift < 0 ? 'Yesterday, ' : '');
  $('tz-place-label').textContent = spot[0] + ' \u00b7 ' + spot[1];
  $('tz-time').textContent = tzClock(spot[2], now);
  $('tz-day').textContent = when + tzDay(spot[2], now);
  $('tz-diff').textContent = tzDiffLong(diff);
  $('tz-diff').classList.toggle('same', diff === 0);
  $('tz-you-time').textContent = tzHereClock(now);
  $('tz-you-zone').textContent = tzHereZone();
}
function tzBuildList(){
  var row = $('tz-list');
  if (!row) return;
  var q = ($('tz-search').value || '').trim().toLowerCase().replace(/\s+/g, ' ');
  var now = new Date(), shown = 0;
  row.innerHTML = '';
  for (var i = 0; i < TZ_PLACES.length; i++){
    var p = TZ_PLACES[i];
    if (q && (p[0] + ' ' + p[1] + ' ' + p[2]).toLowerCase().indexOf(q) === -1) continue;
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'tz-item' + (p[2] === tzPlace ? ' on' : '');
    b.setAttribute('data-zone', p[2]);
    var name = document.createElement('span');
    name.className = 'tz-item-name';
    var city = document.createElement('b'); city.textContent = p[0];
    var land = document.createElement('span'); land.textContent = p[1];
    name.appendChild(city); name.appendChild(land);
    var right = document.createElement('span');
    right.className = 'tz-item-right';
    var tm = document.createElement('b'); tm.className = 'tz-item-time'; tm.textContent = tzClock(p[2], now);
    var df = document.createElement('span'); df.className = 'tz-item-diff'; df.textContent = tzDiffShort(tzDiffMin(p[2], now));
    right.appendChild(tm); right.appendChild(df);
    b.appendChild(name); b.appendChild(right);
    b.addEventListener('click', function(zone){ return function(){ tzPick(zone); }; }(p[2]));
    row.appendChild(b);
    shown++;
  }
  if ($('tz-hint')){
    $('tz-hint').textContent = (shown || !tzUsable) ? '' : 'No place by that name. Try a city or a country \u2014 Tokyo, Nigeria, Spain.';
  }
}
function tzPick(zone){
  tzPlace = zone;
  storeSet(TZ_KEY, zone);
  tzRender();
  tzBuildList();
}
// The clock only ticks while it is the thing on screen: a tab change sets covCat away from
// 'time' and stops the timer, so nothing redraws behind a screen nobody is looking at.
function tzTick(){
  if (covCat !== 'time' || !tzUsable) return;
  var scr = $('convert-screen'), view = $('cov-convert-view');
  if (!scr || !scr.classList.contains('active')) return;
  if (!view || view.style.display === 'none') return;
  tzRender();
  var rows = $('tz-list') ? $('tz-list').querySelectorAll('[data-zone]') : [];
  var now = new Date();
  for (var i = 0; i < rows.length; i++){
    var t = rows[i].querySelector('.tz-item-time');
    if (t) t.textContent = tzClock(rows[i].getAttribute('data-zone'), now);
  }
}
function tzOn(){
  if (!tzUsable){
    if ($('tz-hint')) $('tz-hint').textContent = 'This phone\u2019s browser cannot look up other time zones.';
    return;
  }
  tzRender();
  tzBuildList();
  if (!tzTimer) tzTimer = setInterval(tzTick, 10000);
}
function tzOff(){
  if (tzTimer){ clearInterval(tzTimer); tzTimer = null; }
}
// Called when the 24-hour setting changes, so the clock follows it without waiting a tick.
function tzRefresh(){ if (covCat === 'time') tzRender(); }
function tzInit(){
  if ($('tz-search')) $('tz-search').addEventListener('input', tzBuildList);
  if (!tzUsable && $('tz-hint')) $('tz-hint').textContent = 'This phone\u2019s browser cannot look up other time zones.';
}

'''

INIT_OLD = """buildCovChips();
fillCovSelects();
updateCovResult();"""

INIT_NEW = """buildCovChips();
fillCovSelects();
updateCovResult();
tzInit();"""

TOGGLE_OLD = """  $('toggle-24h').classList.toggle('on', state.use24h);
  updateSunTimes();
});"""

TOGGLE_NEW = """  $('toggle-24h').classList.toggle('on', state.use24h);
  updateSunTimes();
  tzRefresh();
});"""

# ---------------------------------------------------------------------------
# 4. PATCH_NOTES.md - the repository mirror of the in-app entry.
# ---------------------------------------------------------------------------
NOTES_OLD = '## 1.2.3 \u2014 November 5, 2026'

NOTES_NEW = """## 1.3.0 \u2014 November 6, 2026

**A Time chip in Convert: what time it is anywhere, and how far that is from you**

- A **Time** chip sits at the end of the Convert row. Pick a place from the searchable list \u2014 about fifty, from London and Lagos to Tokyo and Auckland \u2014 and the card shows the time there, the day there, and the gap from your own clock in words: **3 hours ahead of you**, **the same time as you**, **5 hours 45 minutes behind you**.
- Your own time sits under it, both clocks on one screen, and the last place you picked is remembered.
- The times come from the phone's own time-zone database, so daylight saving is whatever each place is actually doing on that date.
- Nothing else changed \u2014 elevation, location, the level, the unit converter and its six categories, currency, GPS measuring, the AR range finder, permissions and updates are as they were.

## 1.2.3 \u2014 November 5, 2026"""


def main():
    html = read('index.html')
    js = read('app.js')
    notes = read('PATCH_NOTES.md')

    already = (MARK_HTML in html) and (MARK_JS in js)

    if CHECK:
        checks = [
            ('index.html is %s' % VERSION, ABOUT_NEW in html),
            ('index.html carries the clock panel', 'id="%s"' % MARK_HTML in html),
            ('index.html hides the converter cards from Time', 'id="cov-unit-card"' in html and 'id="cov-method-card"' in html),
            ('index.html has the place search', 'id="tz-search"' in html),
            ('app.js is %s' % VERSION, APP_NEW in js),
            ('app.js has the time-zone table', MARK_JS in js),
            ('app.js renders the clock', 'function tzRender()' in js),
            ('app.js has the Time chip', "t.textContent = 'Time'" in js),
            ('app.js switches to the clock panel', "if (isTime){ tzOn(); return; }" in js),
            ('app.js head changelog entry is %s' % VERSION, "var CHANGELOG = [\n  { version: '%s'," % VERSION in js),
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

    html = sub(html, CSS_ANCHOR, CSS_NEW, 'index.html: styles')
    html = sub(html, UNIT_CARD_OLD, UNIT_CARD_NEW, 'index.html: converter card id')
    html = sub(html, METHOD_CARD_OLD, METHOD_CARD_NEW, 'index.html: method card id')
    html = sub(html, TZ_OLD, TZ_NEW, 'index.html: clock panel')
    html = sub(html, ABOUT_OLD, ABOUT_NEW, 'index.html: version line')

    js = sub(js, APP_OLD, APP_NEW, 'app.js: APP_VERSION')
    js = sub(js, CHANGELOG_OLD, CHANGELOG_NEW, 'app.js: changelog head')
    js = sub(js, SETCAT_OLD, SETCAT_NEW, 'app.js: setCovCat')
    js = sub(js, CHIPS_OLD, CHIPS_NEW, 'app.js: buildCovChips')
    js = sub(js, RESULT_OLD, RESULT_NEW, 'app.js: updateCovResult guard')
    js = sub(js, TZ_ANCHOR, TZ_BLOCK + TZ_ANCHOR, 'app.js: time-zone module')
    js = sub(js, INIT_OLD, INIT_NEW, 'app.js: startup wiring')
    js = sub(js, TOGGLE_OLD, TOGGLE_NEW, 'app.js: 24-hour toggle')

    notes = sub(notes, NOTES_OLD, NOTES_NEW, 'PATCH_NOTES.md: new section')

    if problems:
        print('\n'.join(problems))
        print('\n%d anchor(s) did not match - nothing written' % len(problems))
        return 1

    write('index.html', html)
    write('app.js', js)
    write('PATCH_NOTES.md', notes)
    print('MeasureT %s applied: index.html +%d, app.js +%d, PATCH_NOTES.md +%d'
          % (VERSION, TZ_NEW.count('\n'), (TZ_BLOCK.count('\n') + CHANGELOG_NEW.count('\n') + SETCAT_NEW.count('\n')
             + CHIPS_NEW.count('\n') + INIT_NEW.count('\n') + TOGGLE_NEW.count('\n')), NOTES_NEW.count('\n')))
    print('next: node dev/ota.mjs   (republishes updates.json, stamps sw.js and package.json)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
