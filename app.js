(function(){
'use strict';

// ---------- RELEASE ----------
// APP_VERSION, the CHANGELOG below and updates.json are kept in step by dev/ota.mjs
// ("node dev/ota.mjs" republishes updates.json and stamps sw.js/package.json;
//  "node dev/ota.mjs --check" fails if any of the four disagree).
// Cutting a release = bump APP_VERSION, write its CHANGELOG entry at the head, run the tool.
var APP_VERSION = '1.2.2';
var OTA_ENDPOINT = 'https://anekthegreat.github.io/Compass-EDC/updates.json';
var CHANGELOG = [
  { version: '1.2.2', date: 'November 5, 2026', title: 'The Compass tab is gone, and the currency answer is easy to read', items: [
    'The <b>Compass</b> tab has been <b>removed</b>. It was the most complicated thing in the app, and the heading dial, its calibration banner, the marked bearing and the true-north switch went with it. MeasureT now has <b>six tabs</b> and opens on <b>Convert</b>.',
    'The <b>currency answer</b> could be cut off at the bottom of its card on a phone with larger text, which is why the number was hard to see. The card now grows to fit what is in it instead of being squeezed, the answer is <b>larger and darker</b>, and the labels above it are legible.',
    'Nothing else changed &mdash; elevation, location, the level, the converter, GPS measuring, the AR range finder, permissions and updates are exactly as they were.'
  ]},
  { version: '1.2.1', date: 'November 5, 2026', title: 'Type the currency, and a Currency tab that is a pleasure to look at', items: [
    'The two currency buttons now open a <b>searchable list</b>: type <b>eur</b>, <b>euro</b> or <b>rupee</b> and it narrows to that currency, with the ones people reach for most at the top and a tick on the pair in use. Before this, picking from more than fifty currencies was a long scroll in a native dropdown.',
    'The amount is an obvious field now: <b>tap the big number and type</b>, or tap <b>10</b>, <b>50</b>, <b>100</b> or <b>500</b>, and the answer follows as you type, with the currency you are typing in shown right beside it.',
    'The tab looks and moves like one instrument: a single glowing card, the answer in a blue-to-green gradient, a spinning &#8645; on swap and a soft pulse each time the number changes. Anyone whose phone asks for less motion gets none of that motion.',
    'Fixed: the update button stayed on <b>Updating&hellip;</b> forever after the automatic check on opening the tab. It now returns to its own label, or offers <b>Try again</b>.',
    'The seven tab labels no longer run into each other on a narrow phone. Nothing else changed &mdash; the converter, GPS measuring, the AR range finder, the compass, permissions and updates are exactly as they were.'
  ]},
  { version: '1.2.0', date: 'November 4, 2026', title: 'A Currency tab, with the day&rsquo;s exchange rate', items: [
    'A <b>Currency</b> tab now sits between Convert and Settings. Type an amount, pick the two currencies, and it converts at the day&rsquo;s rate; the reverse rate is printed underneath, and the &#8645; button swaps the pair.',
    'The rates come from a public feed that needs no sign-in, and every answer is saved on the phone &mdash; so the tab keeps converting on a plane or with no signal, and says which day&rsquo;s rates you are looking at.',
    'Nothing else changed &mdash; the converter, GPS measuring, the AR range finder, the compass, permissions and updates are exactly as they were.'
  ]},
  { version: '1.1.3', date: 'November 4, 2026', title: 'The AR camera stops when you leave it', items: [
    'Leaving the Measure half of the Convert tab &mdash; by tapping another tab, or by switching back to Convert &mdash; now ends the AR camera. Before this, the camera kept streaming and the live distance kept updating in the background, and only the <b>Stop</b> button could turn it off.',
    'Nothing else changed &mdash; the converter, GPS measuring, the compass, permissions and updates are exactly as they were.'
  ]},
  { version: '1.1.2', date: 'November 3, 2026', title: 'MeasureT can be thanked, in Settings', items: [
    'A <b>Support</b> group now sits in Settings, above the version line: five amounts, each one an ordinary Stripe payment page opened in the browser. Nothing unlocks and nothing is sent from the app — a tip is a thank you, and the app is the same either way.',
    'Nothing else changed — the converter, GPS measuring, the AR range finder, the compass, permissions and updates are exactly as they were.'
  ]},
  { version: '1.1.1', date: 'October 29, 2026', title: 'There is always a way back to Convert', items: [
    'A <b>Convert</b> button now sits at the top of the Measure half itself &mdash; the first thing on the screen, above the distance readout. The switch at the top of the tab is no longer the only way back, so opening Measure can never leave you with nowhere to go.',
    'The <b>Convert / Measure switch</b> reserves its own height now (44 px, and it refuses to shrink). It is the one panel on that screen whose rounded corners clip it, and the Measure half was squeezing it to a sliver: that is the switch that kept disappearing.',
    'Nothing else changed &mdash; the converter, GPS measuring, the AR range finder, the compass, permissions and updates are exactly as they were.'
  ]},
  { version: '1.1.0', date: 'October 17, 2026', title: 'The Convert / Measure switch can no longer disappear, and MeasureT now updates itself', items: [
    'Tapping Measure collapsed the Convert / Measure switch at the top of the screen to a 2px sliver, so Convert was gone and you were stuck: the switch is the one panel on that screen whose rounded corners clip it, and a screen the size of the Measure view was squeezing it flat. It now holds its size and stays pinned, so Convert is always one tap away.',
    'The sensor permission panel always comes down. Denying motion &amp; orientation access used to leave a full-screen panel over the app forever - every tab gone, every tap swallowed.',
    'MeasureT now checks for new releases on every start, in Settings → Updates, and shows what the release changed before it applies.',
    'Updates arrive while the app runs: the page now loads newest-first and falls back to the saved copy only when the network is gone, instead of pinning the first copy it ever saw.'
  ]},
  { version: '1.0.0', date: 'July 17, 2026', title: 'First release', items: [
    'Compass, elevation, location, level, a unit converter, GPS measurement and AR distance.'
  ]}
];

// ---------- STATE ----------
var SMOOTH = 0.09;   // EMA alpha — lower = smoother (0.09 ≈ 110 ms time-constant)
var smoothPitch = 0, smoothRoll = 0;
var rafPending = false;

var state = {
  unitSystem: localStorage.getItem('cedc_units') || 'metric', // 'metric' | 'imperial'
  use24h: localStorage.getItem('cedc_24h') === '1', // 24-hour (military) time
  wakeLock: localStorage.getItem('cedc_wakelock') === '1',
  lat: null, lon: null, gpsAccuracy: null, speed: null,
  altitude: null, altAccuracy: null,
  elevHistory: [], // {t, alt}
  elevMin: null, elevMax: null, elevGain: 0, lastAlt: null, lastAltT: null,
  sessionStart: Date.now(),
  pitch: 0, roll: 0,
  wakeLockObj: null
};

var M_TO_FT = 3.28084;
var KM_TO_MI = 0.621371;
var MS_TO_MPH = 2.23694;

function $(id){ return document.getElementById(id); }

// localStorage, but never fatal. A WebView with storage switched off throws a
// SecurityError on the first touch of localStorage, and because these reads sit in the
// middle of this file's startup, that one throw used to stop every listener below it from
// ever being attached - which is what a screen with dead tabs, a dead switch and a dead
// nav looks like. Nothing here is allowed to be the reason the app cannot be driven.
function storeGet(k){ try { return localStorage.getItem(k); } catch (e) { return null; } }
function storeSet(k, v){ try { localStorage.setItem(k, v); } catch (e) {} }
var SENSORS_KEY = 'cedc_sensors_ok';
var GEO_KEY = 'cedc_geo_ok';

// ---------- NAV ----------
document.querySelectorAll('nav button').forEach(function(btn){
  btn.addEventListener('click', function(){
    document.querySelectorAll('nav button').forEach(function(b){ b.classList.remove('active'); });
    document.querySelectorAll('.screen').forEach(function(s){ s.classList.remove('active'); });
    btn.classList.add('active');
    $(btn.dataset.screen).classList.add('active');
    // The AR camera belongs to the Measure half of this tab, so a tab change ends it. Before
    // this, the stream and its 120 ms report timer kept running with only Stop able to end
    // them, which left a camera on in the background after a single tap on another tab.
    if (btn.dataset.screen !== 'convert-screen' && arActive) stopAR();
    // The Convert tab always lands on the converter. That screen carries a Convert / Measure
    // switch of its own, so a tab tap that left the screen on Measure looked like a tap that
    // did nothing at all.
    if (btn.dataset.screen === 'convert-screen') setCovMode('convert');
    // The currency tab asks for a fresh rate the first time it is opened, not on every
    // start: nothing on this screen is needed by the compass or the level.
    if (btn.dataset.screen === 'currency-screen') curOnOpen();
    if ($(btn.dataset.screen)) $(btn.dataset.screen).scrollTop = 0;
  });
});

function scheduleUpdate(){
  if (rafPending) return;
  rafPending = true;
  requestAnimationFrame(function(){
    rafPending = false;
    updateLevelUI();
  });
}

function handleOrientation(e){
  // The Compass tab is gone, so this reads only the two angles the level (and the AR readings)
  // use: pitch and roll, smoothed so the bubble does not jitter. No heading, no dead zone.
  if (e.beta != null && e.gamma != null) {
    var rawPitch = e.beta > 90 ? 180 - e.beta : (e.beta < -90 ? -180 - e.beta : e.beta);
    state.pitch = rawPitch;
    state.roll = e.gamma;
    smoothPitch += (rawPitch - smoothPitch) * SMOOTH;
    smoothRoll  += (state.roll - smoothRoll) * SMOOTH;
    scheduleUpdate();
  }
}

// ---------- LEVEL ----------
function updateLevelUI(){
  var pitch = smoothPitch, roll = smoothRoll;
  $('level-pitch').textContent = pitch.toFixed(1);
  $('level-roll').textContent = roll.toFixed(1);
  var maxOffset = 90;
  var dx = Math.max(-90, Math.min(90, roll)) / maxOffset * 90;
  var dy = Math.max(-90, Math.min(90, pitch)) / maxOffset * 90;
  var bubble = $('level-bubble');
  var cx = 140 + dx, cy = 140 + dy;
  bubble.setAttribute('cx', cx);
  bubble.setAttribute('cy', cy);
  var isFlat = Math.abs(state.pitch) < 1 && Math.abs(state.roll) < 1;
  bubble.setAttribute('fill', isFlat ? '#2fa66b' : '#ff6f61');
  $('level-flat-msg').textContent = isFlat ? 'Level' : '';
}

// ---------- ELEVATION ----------
function metersToDisplay(m){
  if (m == null) return null;
  return state.unitSystem === 'imperial' ? m * M_TO_FT : m;
}
function elevUnitLabel(){ return state.unitSystem === 'imperial' ? 'ft' : 'm'; }

function updateElevationUI(){
  var alt = state.altitude;
  $('elev-num').textContent = alt != null ? Math.round(metersToDisplay(alt)) : '--';
  $('elev-unit').textContent = elevUnitLabel();
  $('elev-max').textContent = state.elevMax != null ? Math.round(metersToDisplay(state.elevMax)) + ' ' + elevUnitLabel() : '--';
  $('elev-min').textContent = state.elevMin != null ? Math.round(metersToDisplay(state.elevMin)) + ' ' + elevUnitLabel() : '--';
  $('elev-gain').textContent = Math.round(metersToDisplay(state.elevGain)) + ' ' + elevUnitLabel();
  $('elev-accuracy').textContent = state.altAccuracy != null ? Math.round(metersToDisplay(state.altAccuracy)) + ' ' + elevUnitLabel() : '-- ' + elevUnitLabel();
  $('unit-toggle-elev').textContent = state.unitSystem === 'imperial' ? 'FT' : 'M';
  drawElevGraph();
}

function drawElevGraph(){
  var canvas = $('elev-graph');
  var ctx = canvas.getContext('2d');
  var dpr = window.devicePixelRatio || 1;
  var w = canvas.clientWidth, h = canvas.clientHeight || 110;
  canvas.width = w * dpr; canvas.height = h * dpr;
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,w,h);
  var hist = state.elevHistory;
  if (hist.length < 2) {
    ctx.fillStyle = '#7ea2bd';
    ctx.font = '11px -apple-system, sans-serif';
    ctx.fillText('Gathering elevation data...', 4, h/2);
    return;
  }
  var vals = hist.map(function(p){ return p.alt; });
  var min = Math.min.apply(null, vals), max = Math.max.apply(null, vals);
  var range = (max - min) || 1;
  var pad = 8;
  ctx.beginPath();
  hist.forEach(function(p, i){
    var x = pad + (w - pad*2) * (i / (hist.length - 1));
    var y = h - pad - (h - pad*2) * ((p.alt - min) / range);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = '#2f8fd6';
  ctx.lineWidth = 2;
  ctx.lineJoin = 'round';
  ctx.stroke();
  var grad = ctx.createLinearGradient(0, pad, 0, h - pad);
  grad.addColorStop(0, 'rgba(91,184,242,0.35)');
  grad.addColorStop(1, 'rgba(91,184,242,0.02)');
  ctx.lineTo(w - pad, h - pad);
  ctx.lineTo(pad, h - pad);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();
}

function ingestAltitude(alt, accuracy){
  var now = Date.now();
  if (alt == null) return;
  if (state.lastAlt != null && state.lastAltT != null) {
    var dt = (now - state.lastAltT) / 1000;
    if (dt > 0.5) {
      var vspeed = (alt - state.lastAlt) / dt;
      var displaySpeed = state.unitSystem === 'imperial' ? vspeed * M_TO_FT : vspeed;
      $('elev-vspeed').textContent = (displaySpeed >= 0 ? '+' : '') + displaySpeed.toFixed(1) + ' ' + elevUnitLabel() + '/s';
      if (alt > state.lastAlt) state.elevGain += (alt - state.lastAlt);
      state.lastAlt = alt; state.lastAltT = now;
    }
  } else {
    state.lastAlt = alt; state.lastAltT = now;
  }
  state.altitude = alt;
  state.altAccuracy = accuracy;
  state.elevMin = state.elevMin == null ? alt : Math.min(state.elevMin, alt);
  state.elevMax = state.elevMax == null ? alt : Math.max(state.elevMax, alt);
  state.elevHistory.push({t: now, alt: alt});
  if (state.elevHistory.length > 200) state.elevHistory.shift();
  updateElevationUI();
}

// ---------- LOCATION ----------
function distUnitLabel(){ return state.unitSystem === 'imperial' ? 'mph' : 'km/h'; }

function updateLocationUI(){
  $('loc-lat').textContent = state.lat != null ? state.lat.toFixed(5) + '°' : '--';
  $('loc-lon').textContent = state.lon != null ? state.lon.toFixed(5) + '°' : '--';
  var accM = state.gpsAccuracy;
  $('loc-accuracy').textContent = accM != null ? Math.round(metersToDisplay(accM)) + ' ' + elevUnitLabel() : '-- m';
  var spd = state.speed;
  var spdDisplay = 0;
  if (spd != null) spdDisplay = state.unitSystem === 'imperial' ? spd * MS_TO_MPH : spd * 3.6;
  $('loc-speed').textContent = spdDisplay.toFixed(1) + ' ' + distUnitLabel();
  $('unit-toggle-loc').textContent = state.unitSystem === 'imperial' ? 'MI' : 'KM';
  updateSunTimes();
}

function updateSunTimes(){
  if (state.lat == null || state.lon == null) return;
  var times = calcSunTimes(new Date(), state.lat, state.lon);
  $('sun-rise').textContent = times.rise;
  $('sun-set').textContent = times.set;
}

// simplified NOAA sunrise/sunset algorithm
function calcSunTimes(date, lat, lon){
  function toRad(d){ return d * Math.PI / 180; }
  function toDeg(r){ return r * 180 / Math.PI; }
  var start = new Date(Date.UTC(date.getFullYear(),0,1));
  var dayOfYear = Math.floor((date - start) / 86400000) + 1;
  var zenith = 90.833;
  function compute(isRise){
    var lngHour = lon / 15;
    var t = isRise ? dayOfYear + ((6 - lngHour) / 24) : dayOfYear + ((18 - lngHour) / 24);
    var M = (0.9856 * t) - 3.289;
    var L = M + (1.916 * Math.sin(toRad(M))) + (0.020 * Math.sin(2*toRad(M))) + 282.634;
    L = (L + 360) % 360;
    var RA = toDeg(Math.atan(0.91764 * Math.tan(toRad(L))));
    RA = (RA + 360) % 360;
    var Lquadrant = Math.floor(L/90) * 90;
    var RAquadrant = Math.floor(RA/90) * 90;
    RA = RA + (Lquadrant - RAquadrant);
    RA = RA / 15;
    var sinDec = 0.39782 * Math.sin(toRad(L));
    var cosDec = Math.cos(Math.asin(sinDec));
    var cosH = (Math.cos(toRad(zenith)) - (sinDec * Math.sin(toRad(lat)))) / (cosDec * Math.cos(toRad(lat)));
    if (cosH > 1 || cosH < -1) return null;
    var H = isRise ? 360 - toDeg(Math.acos(cosH)) : toDeg(Math.acos(cosH));
    H = H / 15;
    var T = H + RA - (0.06571 * t) - 6.622;
    var UT = (T - lngHour + 24) % 24;
    var hours = Math.floor(UT);
    var minutes = Math.floor((UT - hours) * 60);
    var localDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate(), hours, minutes));
    return localDate;
  }
  var rise = compute(true), set = compute(false);
  function fmt(d){
    if (!d) return '--:--';
    return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', hour12: !state.use24h});
  }
  return { rise: fmt(rise), set: fmt(set) };
}

// ---------- GEOLOCATION ----------
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
if ('geolocation' in navigator) { startGeo(); }

// ---------- DEVICE ORIENTATION PERMISSION (iOS) ----------
function initOrientation(){
  window.addEventListener('deviceorientationabsolute', handleOrientation, true);
  window.addEventListener('deviceorientation', handleOrientation, true);
}

// ASKED ONCE, NOT ON EVERY LAUNCH. This panel was built on every start, so a phone whose
// WebView exposes requestPermission got "needs motion and orientation sensors" in front of
// it every time the app opened - even after the sensors had been allowed and were working
// fine. The grant is remembered now, and a permission already granted is simply used:
// requestPermission() answers out of the stored state and cannot prompt again.
var needsPermission = typeof DeviceOrientationEvent !== 'undefined' &&
  typeof DeviceOrientationEvent.requestPermission === 'function';

if (needsPermission && !storeGet(SENSORS_KEY)) {
  var overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;background:linear-gradient(180deg,#cdeaff,#8fc7ee);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:999;padding:24px;text-align:center;';
  overlay.innerHTML = '<div style="font-size:15px;color:#0e3350;margin-bottom:18px;line-height:1.5;">MeasureT needs access to<br>motion and orientation sensors</div><button id="grant-btn" style="background:linear-gradient(180deg,#5bb8f2,#2f8fd6);color:#fff;border:1px solid #2f8fd6;padding:14px 28px;border-radius:24px;font-size:14px;box-shadow:0 6px 16px rgba(47,143,214,0.35);">Enable sensors</button>';
  document.body.appendChild(overlay);
  $('grant-btn').addEventListener('click', function(){
    DeviceOrientationEvent.requestPermission().then(function(res){
      if (res === 'granted') {
        storeSet(SENSORS_KEY, '1');
        initOrientation();
      }
      // The overlay used to come down only on 'granted'. An answer of 'denied' (or anything
      // else that resolves — not rejects) left a z-index:999 full-screen panel over the whole
      // app forever: every tab gone, every tap swallowed. Sensors are optional, the app is not:
      // the panel always comes down, and listeners are wired either way (they stay silent
      // without permission). A denial is retried on the next launch, as before.
      overlay.remove();
    }).catch(function(){ overlay.remove(); });
  });
} else {
  initOrientation();
}

// ---------- SETTINGS ----------
function applyUnitSystem(){
  var isImperial = state.unitSystem === 'imperial';
  $('seg-metric').classList.toggle('on', !isImperial);
  $('seg-imperial').classList.toggle('on', isImperial);
  updateElevationUI();
  updateLocationUI();
}
$('seg-metric').addEventListener('click', function(){
  state.unitSystem = 'metric'; localStorage.setItem('cedc_units','metric'); applyUnitSystem();
});
$('seg-imperial').addEventListener('click', function(){
  state.unitSystem = 'imperial'; localStorage.setItem('cedc_units','imperial'); applyUnitSystem();
});
$('unit-toggle-elev').addEventListener('click', function(){
  state.unitSystem = state.unitSystem === 'imperial' ? 'metric' : 'imperial';
  localStorage.setItem('cedc_units', state.unitSystem);
  applyUnitSystem();
});
$('unit-toggle-loc').addEventListener('click', function(){
  state.unitSystem = state.unitSystem === 'imperial' ? 'metric' : 'imperial';
  localStorage.setItem('cedc_units', state.unitSystem);
  applyUnitSystem();
});

$('toggle-24h').addEventListener('click', function(){
  state.use24h = !state.use24h;
  localStorage.setItem('cedc_24h', state.use24h ? '1' : '0');
  $('toggle-24h').classList.toggle('on', state.use24h);
  updateSunTimes();
});

$('toggle-wakelock').addEventListener('click', function(){
  state.wakeLock = !state.wakeLock;
  localStorage.setItem('cedc_wakelock', state.wakeLock ? '1' : '0');
  $('toggle-wakelock').classList.toggle('on', state.wakeLock);
  applyWakeLock();
});

$('btn-reset-session').addEventListener('click', function(){
  state.elevHistory = [];
  state.elevMin = null; state.elevMax = null; state.elevGain = 0;
  state.lastAlt = null; state.lastAltT = null;
  state.sessionStart = Date.now();
  updateElevationUI();
});

function applyWakeLock(){
  if (!('wakeLock' in navigator)) return;
  if (state.wakeLock) {
    navigator.wakeLock.request('screen').then(function(wl){ state.wakeLockObj = wl; }).catch(function(){});
  } else if (state.wakeLockObj) {
    state.wakeLockObj.release().catch(function(){});
    state.wakeLockObj = null;
  }
}
document.addEventListener('visibilitychange', function(){
  if (document.visibilityState === 'visible' && state.wakeLock) applyWakeLock();
});

// init settings UI from storage
$('toggle-wakelock').classList.toggle('on', state.wakeLock);
$('toggle-24h').classList.toggle('on', state.use24h);
applyUnitSystem();
applyWakeLock();

// ---------- TOOLS: CONVERTER + MEASURER ----------
var UNIT_SHORT = {mm:'mm',cm:'cm',m:'m',km:'km',ft:'ft',yd:'yd',in:'in',mi:'mi',mg:'mg',g:'g',kg:'kg',oz:'oz',lb:'lb',st:'st',C:'°C',F:'°F',K:'K',mps:'m/s',kmh:'km/h',mph:'mph',fps:'ft/s',kt:'kn',ml:'mL',l:'L',cup:'cup',floz:'fl oz',pt:'pt',qt:'qt',gal:'gal',m2:'m²',km2:'km²',ft2:'ft²',ac:'ac',mi2:'mi²',ha:'ha'};

var CONVERTERS = {
  length:{units:[['mm','Millimeters',0.001],['cm','Centimeters',0.01],['m','Meters',1],['km','Kilometers',1000],['in','Inches',0.0254],['ft','Feet',0.3048],['yd','Yards',0.9144],['mi','Miles',1609.344]]},
  mass:{units:[['mg','Milligrams',0.001],['g','Grams',1],['kg','Kilograms',1000],['oz','Ounces',28.349523],['lb','Pounds',453.59237],['st','Stones',6350.293]]},
  temperature:{special:true,units:[['C','Celsius'],['F','Fahrenheit'],['K','Kelvin']]},
  speed:{units:[['mps','m/s',1],['kmh','km/h',0.277778],['mph','mph',0.44704],['fps','ft/s',0.3048],['kt','Knots',0.514444]]},
  volume:{units:[['ml','Milliliters',0.001],['l','Liters',1],['cup','Cups (US)',0.24],['floz','Fl oz (US)',0.0295735],['pt','Pints (US)',0.473176],['qt','Quarts (US)',0.946353],['gal','Gallons (US)',3.78541]]},
  area:{units:[['m2','Sq meters',1],['km2','Sq km',1000000],['ft2','Sq feet',0.092903],['ac','Acres',4046.856],['ha','Hectares',10000],['mi2','Sq miles',2589988.11]]}
};
var CAT_LABEL = {length:'Length',mass:'Mass',temperature:'Temp',speed:'Speed',volume:'Volume',area:'Area'};
var tempMethod = {'CF':'Multiply °C by 9/5, then add 32','FC':'Subtract 32 from °F, then multiply by 5/9','CK':'Add 273.15 to °C','KC':'Subtract 273.15 from °K','FK':'Subtract 32 from °F, multiply by 5/9, then add 273.15','KF':'Subtract 273.15 from °K, multiply by 9/5, then add 32'};
var tempFormulaShort = {'CF':'(°C × 9/5) + 32','FC':'(°F − 32) × 5/9','CK':'°C + 273.15','KC':'°K − 273.15','FK':'(°F − 32) × 5/9 + 273.15','KF':'(°K − 273.15) × 9/5 + 32'};

var covCat = 'length';
var measureActive = false, measureDist = 0, lastSample = null, wptLat = null, wptLon = null;

function unitFind(cat, code){
  var arr = CONVERTERS[cat].units;
  for (var i = 0; i < arr.length; i++){ if (arr[i][0] === code) return arr[i]; }
  return null;
}
function numFmt(n){
  if (!isFinite(n)) return '';
  if (n === 0) return '0';
  var s = n.toFixed(6).replace(/\.?0+$/,'');
  return s === '' || s === '-' ? '0' : s;
}
function resultFmt(n){
  if (!isFinite(n)) return '--';
  var abs = Math.abs(n), s;
  if (abs >= 100000) s = n.toFixed(0);
  else if (abs >= 100) s = n.toFixed(1);
  else if (abs >= 1) s = n.toFixed(2);
  else if (abs >= 0.01) s = n.toFixed(3);
  else if (abs >= 0.0001) s = n.toFixed(5);
  else s = n.toExponential(2);
  return s.replace(/\.?0+$/,'');
}
function toKelvin(v, u){ if (u === 'C') return v + 273.15; if (u === 'F') return (v - 32) * 5/9 + 273.15; return v; }
function fromKelvin(k, u){ if (u === 'C') return k - 273.15; if (u === 'F') return (k - 273.15) * 9/5 + 32; return k; }

function convertValue(cat, v, from, to){
  if (CONVERTERS[cat].special) return fromKelvin(toKelvin(v, from), to);
  return v * unitFind(cat, from)[2] / unitFind(cat, to)[2];
}

function fillCovSelects(){
  function fill(id, cat){
    var sel = $(id), opts = CONVERTERS[cat].units;
    sel.innerHTML = '';
    opts.forEach(function(u){
      var o = document.createElement('option');
      o.value = u[0]; o.textContent = u[1];
      sel.appendChild(o);
    });
  }
  fill('cov-from', covCat);
  fill('cov-to', covCat);
  setCovDefaults(covCat);
}
function setCovDefaults(cat){
  var f = $('cov-from'), t = $('cov-to');
  if (cat === 'length'){ f.value = state.unitSystem === 'imperial' ? 'ft' : 'm'; t.value = state.unitSystem === 'imperial' ? 'm' : 'ft'; }
  else if (cat === 'mass'){ f.value = 'kg'; t.value = 'lb'; }
  else if (cat === 'temperature'){ f.value = 'C'; t.value = 'F'; }
  else if (cat === 'speed'){ f.value = state.unitSystem === 'imperial' ? 'mph' : 'kmh'; t.value = state.unitSystem === 'imperial' ? 'kmh' : 'mph'; }
  else if (cat === 'volume'){ f.value = 'l'; t.value = 'gal'; }
  else if (cat === 'area'){ f.value = 'm2'; t.value = 'ft2'; }
}
function setCovCat(cat){
  covCat = cat;
  document.querySelectorAll('.cov-chip').forEach(function(c){ c.classList.toggle('on', c.getAttribute('data-cat') === cat); });
  fillCovSelects();
  updateCovResult();
}
function buildCovChips(){
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
}
function getCovMethod(cat, from, to){
  if (CONVERTERS[cat].special) return 'To convert: ' + (tempMethod[from + to] || '');
  var factor = unitFind(cat, from)[2] / unitFind(cat, to)[2];
  return 'Multiply ' + UNIT_SHORT[from] + ' by ' + numFmt(factor) + ' to get ' + UNIT_SHORT[to] + '. Reverse: divide by ' + numFmt(factor) + '.';
}
function getCovEquation(cat, from, to){
  if (CONVERTERS[cat].special) return tempFormulaShort[from + to] || '';
  var factor = unitFind(cat, from)[2] / unitFind(cat, to)[2];
  return '1 ' + UNIT_SHORT[from] + ' = ' + numFmt(factor) + ' ' + UNIT_SHORT[to];
}
function updateCovResult(){
  var from = $('cov-from').value, to = $('cov-to').value;
  var v = parseFloat($('cov-value').value);
  $('cov-equation').textContent = getCovEquation(covCat, from, to);
  $('cov-method-text').textContent = getCovMethod(covCat, from, to);
  if (isNaN(v)){ $('cov-result').textContent = '--'; return; }
  $('cov-result').textContent = resultFmt(convertValue(covCat, v, from, to)) + ' ' + UNIT_SHORT[to];
}

function haversine(lat1, lon1, lat2, lon2){
  var R = 6371000;
  var dLat = (lat2 - lat1) * Math.PI / 180, dLon = (lon2 - lon1) * Math.PI / 180;
  var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
          Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon/2) * Math.sin(dLon/2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}
function bearing(lat1, lon1, lat2, lon2){
  var dLon = (lon2 - lon1) * Math.PI / 180;
  var y = Math.sin(dLon) * Math.cos(lat2 * Math.PI / 180);
  var x = Math.cos(lat1 * Math.PI / 180) * Math.sin(lat2 * Math.PI / 180) - Math.sin(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.cos(dLon);
  var brng = Math.atan2(y, x) * 180 / Math.PI;
  return (brng + 360) % 360;
}
function formatDistance(m){
  if (state.unitSystem === 'imperial'){
    var ft = m * 3.28084;
    return ft < 3281 ? ft.toFixed(0) + ' ft' : (ft/5280).toFixed(2) + ' mi';
  }
  return m < 1000 ? m.toFixed(0) + ' m' : (m/1000).toFixed(2) + ' km';
}
function sampleMeasure(){
  if (!measureActive || state.lat == null || state.lon == null) return;
  if (lastSample){
    var d = haversine(lastSample[0], lastSample[1], state.lat, state.lon);
    if (d > 0.5 && d < 100){ measureDist += d; } // filter GPS noise & dropouts
  }
  lastSample = [state.lat, state.lon];
  updateMeasureUI();
}
function updateMeasureUI(){
  $('cov-meas-dist').textContent = formatDistance(measureDist);
  if (wptLat != null && state.lat != null){
    $('cov-meas-wpt-dist').textContent = formatDistance(haversine(state.lat, state.lon, wptLat, wptLon));
    $('cov-meas-wpt-brng').textContent = Math.round(bearing(state.lat, state.lon, wptLat, wptLon)) + '°';
  } else {
    $('cov-meas-wpt-dist').textContent = '--';
    $('cov-meas-wpt-brng').textContent = '--';
  }
}
function toggleMeasure(){
  measureActive = !measureActive;
  if (measureActive){ measureDist = 0; lastSample = null; }
  $('btn-measure-toggle').textContent = measureActive ? 'Stop' : 'Start';
  $('btn-measure-toggle').classList.toggle('primary', measureActive);
  updateMeasureUI();
}
function markWaypoint(){
  if (state.lat == null){ return; }
  wptLat = state.lat; wptLon = state.lon;
  updateMeasureUI();
}
function resetMeasure(){
  measureActive = false; measureDist = 0; lastSample = null; wptLat = null; wptLon = null;
  $('btn-measure-toggle').textContent = 'Start';
  $('btn-measure-toggle').classList.remove('primary');
  updateMeasureUI();
}

// THE WAY BACK STAYS ON SCREEN. This screen's Measure half is long - a distance readout,
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
  // The switch is a flex item of #convert-screen (a column flex scroller) and the only
  // child with overflow:hidden - so its automatic minimum height is 0 by spec. The moment
  // the Measure view made the screen's content taller than the viewport, flex shrink crushed
  // the switch to a 2px line, clipping both buttons out of the picture: the tab disappeared
  // and Convert could not be tapped again. Sticky kept it on screen; this keeps it alive.
  seg.style.flexShrink = '0';
}
function setCovMode(m){
  var isC = m === 'convert';
  // The camera belongs to the Measure half: switching to Convert ends it rather than
  // leaving it on behind a screen that cannot show it. stopAR is hoisted, and arActive is
  // still undefined during the startup calls this runs from, so neither can throw here.
  if (isC && arActive) stopAR();
  $('cov-mode-convert').classList.toggle('on', isC);
  $('cov-mode-measure').classList.toggle('on', !isC);
  $('cov-convert-view').style.display = isC ? '' : 'none';
  $('cov-measure-view').style.display = isC ? 'none' : '';
  var scr = $('convert-screen');
  if (scr) scr.scrollTop = 0;
}
pinCovSwitch();

$('cov-mode-convert').addEventListener('click', function(){ setCovMode('convert'); });
$('cov-mode-measure').addEventListener('click', function(){ setCovMode('measure'); });
// 1.1.1 - the way out of the Measure half, from inside the Measure half. Guarded: a page
// from an older cache could be paired with this script for one load, and a missing button
// must not stop the rest of the file from wiring itself up.
if ($('btn-measure-back')){
  $('btn-measure-back').addEventListener('click', function(){ setCovMode('convert'); });
}
$('cov-value').addEventListener('input', updateCovResult);
$('cov-from').addEventListener('change', updateCovResult);
$('cov-to').addEventListener('change', updateCovResult);
$('cov-swap').addEventListener('click', function(){
  var f = $('cov-from').value;
  $('cov-from').value = $('cov-to').value;
  $('cov-to').value = f;
  updateCovResult();
});
$('btn-measure-toggle').addEventListener('click', toggleMeasure);
$('btn-measure-mark').addEventListener('click', markWaypoint);
$('btn-measure-reset').addEventListener('click', resetMeasure);

// AR distance (tilt-based ranging via camera viewfinder)
var arActive = false, arStream = null, arTimer = null;
window.__arBeta = null;
window.__arBetaRaw = null;
var arHeight = parseFloat(localStorage.getItem('cedc_arheight')) || 1.6;
$('ar-height').value = arHeight;
$('ar-person-height').value = arHeight;
var arObjHeight = parseFloat(localStorage.getItem('cedc_arobjheight')) || 2;
$('ar-obj-height').value = arObjHeight;
var arBaseAngle = null, arTopAngle = null, arFeetAngle = null, arHeadAngle = null;
function setArPhoneHeight(v){
  if (isNaN(v) || v < 0.3 || v > 3) v = 1.6;
  arHeight = v;
  localStorage.setItem('cedc_arheight', String(arHeight));
  // keep the two phone-height inputs in sync
  if ($('ar-height').value !== String(arHeight)) $('ar-height').value = arHeight;
  if ($('ar-person-height').value !== String(arHeight)) $('ar-person-height').value = arHeight;
  arReport();
  arReportPerson();
}
$('ar-height').addEventListener('input', function(){ setArPhoneHeight(parseFloat(this.value)); });
$('ar-person-height').addEventListener('input', function(){ setArPhoneHeight(parseFloat(this.value)); });
window.addEventListener('deviceorientation', function(e){
  if (arActive && e.beta != null){ window.__arBetaRaw = e.beta; window.__arBeta = Math.abs(e.beta); }
});
function arAimDelta(){ // signed degrees below horizontal (+ = aiming down)
  if (window.__arBetaRaw == null) return null;
  return 90 - window.__arBetaRaw;
}
function arReportHeight(){
  if (!arActive){ $('ar-height-dist').textContent = '--'; return; }
  if (arBaseAngle == null || arTopAngle == null){ $('ar-height-dist').textContent = '--'; return; }
  var denom = Math.tan(arBaseAngle * Math.PI / 180) - Math.tan(arTopAngle * Math.PI / 180);
  if (denom < 0.02){
    $('ar-height-dist').textContent = 'Check angles';
    $('ar-height-status').textContent = 'The top must appear higher than the base — re-aim and mark again.';
    return;
  }
  $('ar-height-dist').textContent = formatDistance(arObjHeight / denom);
}
function formatHeight(m){
  if (m == null || !isFinite(m) || m <= 0) return '--';
  if (state.unitSystem === 'imperial'){
    var ft = m * 3.28084;
    var f = Math.floor(ft);
    var inch = Math.round((ft - f) * 12);
    if (inch >= 12){ f += 1; inch -= 12; }
    return f + "'" + (inch ? " " + inch + '"' : '') + ' (' + ft.toFixed(1) + ' ft)';
  }
  return m.toFixed(2) + ' m (' + (m * 100).toFixed(0) + ' cm)';
}
function arReportPerson(){
  if (!arActive){ $('ar-person-dist').textContent = '--'; return; }
  if (arFeetAngle == null || arHeadAngle == null){ $('ar-person-dist').textContent = '--'; return; }
  var down = Math.abs(arFeetAngle); // degrees below horizontal to their feet
  down = Math.max(3, Math.min(87, down));
  var d = arHeight / Math.tan(down * Math.PI / 180); // ground distance to them
  var h = arHeight + d * Math.tan(arHeadAngle * Math.PI / 180); // signed head angle above horizontal
  if (h <= 0.05 || !isFinite(h)){ $('ar-person-dist').textContent = 'Check angles'; return; }
  $('ar-person-dist').textContent = formatHeight(h);
}
function setARStatus(t){ $('ar-status').textContent = t || ''; }
function arReport(){
  if (!arActive) return;
  if (window.__arBeta == null){ $('ar-dist').textContent = 'Hold steady &amp; aim downward'; return; }
  var theta = 90 - window.__arBeta; // degrees below horizontal
  theta = Math.abs(theta);
  theta = Math.max(3, Math.min(87, theta));
  var m = arHeight / Math.tan(theta * Math.PI / 180);
  $('ar-dist').textContent = formatDistance(m);
  arReportPerson();
}
function stopAR(){
  arActive = false;
  if (arTimer){ clearInterval(arTimer); arTimer = null; }
  if (arStream){ arStream.getTracks().forEach(function(t){ t.stop(); }); arStream = null; }
  if ($('ar-video').srcObject){ $('ar-video').srcObject = null; }
  arBaseAngle = null; arTopAngle = null; arFeetAngle = null; arHeadAngle = null;
  $('btn-ar-toggle').textContent = 'Start camera';
  setARStatus('');
  $('ar-dist').textContent = '--';
  $('ar-height-dist').textContent = '--';
  $('ar-person-dist').textContent = '--';
  $('ar-height-status').textContent = 'Align the crosshair with the BASE of the object and tap “Mark base”, then align with the TOP and tap “Mark top”. Enter the object’s real height (a standard door is about 2 m).';
  $('ar-person-status').textContent = 'Aim the crosshair at the person\u2019s FEET on the ground and tap “Mark feet”, then aim at the very TOP of their head and tap “Mark head”.';
}
function startAR(){
  if (state.lat == null) setARStatus('GPS not ready yet — the estimate is more accurate once a fix is found.');
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){ setARStatus('Camera not supported on this device.'); return; }
  navigator.mediaDevices.getUserMedia({video:{facingMode:'environment', width:{ideal:1280}, height:{ideal:960}}}).then(function(stream){
    arStream = stream; arActive = true;
    var v = $('ar-video');
    v.srcObject = stream;
    v.play().catch(function(){});
    $('btn-ar-toggle').textContent = 'Stop';
    setARStatus('');
    window.__arBeta = null;
    arTimer = setInterval(arReport, 120);
  }).catch(function(err){
    setARStatus('Could not access camera: ' + err.message);
  });
}
$('btn-ar-toggle').addEventListener('click', function(){ arActive ? stopAR() : startAR(); });
$('ar-obj-height').addEventListener('input', function(){
  var v = parseFloat(this.value);
  if (isNaN(v) || v < 0.3) v = 2;
  arObjHeight = v;
  localStorage.setItem('cedc_arobjheight', String(arObjHeight));
  arReportHeight();
});
$('ar-mark-base').addEventListener('click', function(){
  var d = arAimDelta();
  if (d == null){ $('ar-height-status').textContent = 'Aim the crosshair at the object base first.'; return; }
  arBaseAngle = d;
  $('ar-height-status').textContent = 'Base captured (' + Math.round(d) + '° below horizontal). Now aim at the TOP and tap “Mark top”.';
  arReportHeight();
});
$('ar-mark-top').addEventListener('click', function(){
  var d = arAimDelta();
  if (d == null || arBaseAngle == null){ $('ar-height-status').textContent = 'Mark the base first, then the top.'; return; }
  arTopAngle = d;
  arReportHeight();
});
$('ar-mark-feet').addEventListener('click', function(){
  var d = arAimDelta();
  if (d == null){ $('ar-person-status').textContent = 'Aim the crosshair at the person\u2019s feet on the ground first.'; return; }
  arFeetAngle = d;
  $('ar-person-status').textContent = 'Feet captured (' + Math.round(Math.abs(d)) + '° below horizontal). Now aim at the very TOP of their head and tap “Mark head”.';
  arReportPerson();
});
$('ar-mark-head').addEventListener('click', function(){
  var d = arAimDelta();
  if (d == null || arFeetAngle == null){ $('ar-person-status').textContent = 'Mark the feet first, then the head.'; return; }
  arHeadAngle = d;
  arReportPerson();
});
function setARMode(m){
  var toBase = m === 'base', toHeight = m === 'height', toPerson = m === 'person';
  $('ar-mode-base').classList.toggle('on', toBase);
  $('ar-mode-height').classList.toggle('on', toHeight);
  $('ar-mode-person').classList.toggle('on', toPerson);
  $('ar-base-view').style.display = toBase ? '' : 'none';
  $('ar-height-view').style.display = toHeight ? '' : 'none';
  $('ar-person-view').style.display = toPerson ? '' : 'none';
}
$('ar-mode-base').addEventListener('click', function(){ setARMode('base'); });
$('ar-mode-height').addEventListener('click', function(){ setARMode('height'); });
$('ar-mode-person').addEventListener('click', function(){ setARMode('person'); });

buildCovChips();
fillCovSelects();
updateCovResult();

// periodic redraw for graph resize
window.addEventListener('resize', drawElevGraph);
setInterval(function(){
  if ($('elevation-screen').classList.contains('active')) drawElevGraph();
}, 3000);

// ---------- CURRENCY ----------
// A tab of its own: an amount, two currencies and the day's rate. The rate comes from public
// feeds that need no key, so there is no account and no secret inside the app, and every
// answer is written to localStorage - which is what makes the tab work with no connection.
// The network is asked again only when what is saved has gone a few hours old.
var CUR_TTL = 6 * 60 * 60 * 1000;
var CUR_KEY = 'cedc_rates';
var CUR_FEEDS = [
  { name: 'exchangerate-api.com', url: 'https://open.er-api.com/v6/latest/USD', read: function(j){
      if (!j || j.result !== 'success' || !j.rates) return null;
      return { date: j.time_last_update_utc, rates: j.rates };
    } },
  // The European Central Bank's own rates, for when the first feed is down. It carries a
  // narrower list of currencies, and omits the base one, which is why USD is put back here.
  { name: 'the European Central Bank', url: 'https://api.frankfurter.dev/v1/latest?from=USD', read: function(j){
      if (!j || !j.rates) return null;
      var r = {};
      for (var k in j.rates) { if (Object.prototype.hasOwnProperty.call(j.rates, k)) r[k] = j.rates[k]; }
      r[j.base || 'USD'] = 1;
      return { date: j.date, rates: r };
    } }
];
var CUR_NAMES = {
  USD:'US Dollar', EUR:'Euro', GBP:'British Pound', JPY:'Japanese Yen', CNY:'Chinese Yuan',
  INR:'Indian Rupee', PKR:'Pakistani Rupee', BDT:'Bangladeshi Taka', LKR:'Sri Lankan Rupee',
  NPR:'Nepalese Rupee', AED:'UAE Dirham', SAR:'Saudi Riyal', QAR:'Qatari Riyal',
  KWD:'Kuwaiti Dinar', BHD:'Bahraini Dinar', OMR:'Omani Rial', JOD:'Jordanian Dinar',
  ILS:'Israeli Shekel', TRY:'Turkish Lira', RUB:'Russian Ruble', UAH:'Ukrainian Hryvnia',
  PLN:'Polish Zloty', CZK:'Czech Koruna', HUF:'Hungarian Forint', RON:'Romanian Leu',
  BGN:'Bulgarian Lev', SEK:'Swedish Krona', NOK:'Norwegian Krone', DKK:'Danish Krone',
  CHF:'Swiss Franc', ISK:'Icelandic Krona', CAD:'Canadian Dollar', AUD:'Australian Dollar',
  NZD:'New Zealand Dollar', MXN:'Mexican Peso', BRL:'Brazilian Real', ARS:'Argentine Peso',
  CLP:'Chilean Peso', COP:'Colombian Peso', PEN:'Peruvian Sol', ZAR:'South African Rand',
  NGN:'Nigerian Naira', KES:'Kenyan Shilling', GHS:'Ghanaian Cedi', EGP:'Egyptian Pound',
  MAD:'Moroccan Dirham', TND:'Tunisian Dinar', HKD:'Hong Kong Dollar', SGD:'Singapore Dollar',
  MYR:'Malaysian Ringgit', IDR:'Indonesian Rupiah', THB:'Thai Baht', PHP:'Philippine Peso',
  VND:'Vietnamese Dong', KRW:'South Korean Won', TWD:'New Taiwan Dollar'
};
var curRates = null, curBusy = false;

function curLoadCache(){
  try {
    var o = JSON.parse(storeGet(CUR_KEY) || 'null');
    if (!o || !o.rates || !o.rates.USD) return null;
    return o;
  } catch (e) { return null; }
}
function curFresh(){ return !!(curRates && curRates.at && (Date.now() - curRates.at) < CUR_TTL); }
function curDate(d){
  if (!d) return '';
  var t = null;
  if (typeof d === 'number') t = new Date(d);
  else if (typeof d === 'string') {
    var m = d.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (m) t = new Date(parseInt(m[1], 10), parseInt(m[2], 10) - 1, parseInt(m[3], 10));
    else { var p = new Date(d); if (!isNaN(p.getTime())) t = p; }
  }
  if (!t || isNaN(t.getTime())) return String(d);
  return t.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}
function curMoney(n){
  if (!isFinite(n)) return '--';
  var a = Math.abs(n);
  if (a !== 0 && a < 0.01) return n.toFixed(4);
  return n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}
// The amount as it was typed, without the trailing zeros a money format adds: "250", not
// "250.00", because it is there to confirm what you entered.
function curPlain(n){
  if (!isFinite(n)) return '--';
  var p = String(Math.round(n * 100) / 100).split('.');
  p[0] = p[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return p.join('.');
}
function curRateFmt(n){
  if (!isFinite(n) || n <= 0) return '--';
  if (n >= 1000) return n.toFixed(0);
  if (n >= 1) return n.toFixed(4).replace(/\.?0+$/, '');
  if (n >= 0.001) return n.toFixed(6).replace(/\.?0+$/, '');
  return n.toPrecision(3);
}
// The country behind each code, so the flag is drawn from the letters instead of being a
// separate image: a regional-indicator pair is just the country code shifted into that block.
var CUR_CONT = {
  USD:'US', EUR:'EU', GBP:'GB', JPY:'JP', CNY:'CN', INR:'IN', PKR:'PK', BDT:'BD', LKR:'LK',
  NPR:'NP', AED:'AE', SAR:'SA', QAR:'QA', KWD:'KW', BHD:'BH', OMR:'OM', JOD:'JO', ILS:'IL',
  TRY:'TR', RUB:'RU', UAH:'UA', PLN:'PL', CZK:'CZ', HUF:'HU', RON:'RO', BGN:'BG', SEK:'SE',
  NOK:'NO', DKK:'DK', CHF:'CH', ISK:'IS', CAD:'CA', AUD:'AU', NZD:'NZ', MXN:'MX', BRL:'BR',
  ARS:'AR', CLP:'CL', COP:'CO', PEN:'PE', ZAR:'ZA', NGN:'NG', KES:'KE', GHS:'GH', EGP:'EG',
  MAD:'MA', TND:'TN', HKD:'HK', SGD:'SG', MYR:'MY', IDR:'ID', THB:'TH', PHP:'PH', VND:'VN',
  KRW:'KR', TWD:'TW'
};
// The pair list opens on these, in this order, before everything else alphabetically.
var CUR_PINNED = ['USD','EUR','GBP','JPY','INR','AED','CAD','AUD','CNY','PKR'];
var curFrom = 'USD', curTo = 'EUR', curPopTimer = null;

function curName(c){ return CUR_NAMES[c] || c; }
function curFlag(c){
  var cc = CUR_CONT[c];
  if (cc && String.fromCodePoint) {
    try { return String.fromCodePoint(cc.charCodeAt(0) + 127397, cc.charCodeAt(1) + 127397); }
    catch (e) {}
  }
  return '\uD83C\uDF10';
}
function curCodes(){
  var seen = {}, out = [];
  function add(c){ if (c && !seen[c]) { seen[c] = 1; out.push(c); } }
  // Once rates are on the phone, the picker offers exactly the currencies that can be
  // converted - a currency the feed does not carry would only ever read "--".
  if (curRates && curRates.rates) { for (var k in curRates.rates) add(k); }
  else { for (var n in CUR_NAMES) add(n); }
  out.sort();
  return out;
}
// The amount is typed, so it arrives as free text: keep the digits and a single decimal point.
function curCleanAmount(s){
  s = String(s == null ? '' : s).replace(/,/g, '').replace(/[^\d.]/g, '');
  var i = s.indexOf('.');
  if (i >= 0) s = s.slice(0, i + 1) + s.slice(i + 1).replace(/\./g, '');
  return s.slice(0, 15);
}
function curAmount(){
  var el = $('cur-value');
  if (!el) return NaN;
  var n = parseFloat(curCleanAmount(el.value));
  return isFinite(n) ? n : NaN;
}
function curRate(){
  if (!curRates || !curRates.rates) return null;
  var rf = curRates.rates[curFrom], rt = curRates.rates[curTo];
  if (!rf || !rt) return null;
  return { from: curFrom, to: curTo, rate: rt / rf };
}
// The two buttons, the code beside the amount and the flag all follow the pair.
function curPaint(){
  function put(id, txt){ var el = $(id); if (el) el.textContent = txt; }
  put('cur-from-flag', curFlag(curFrom)); put('cur-from-code', curFrom); put('cur-from-name', curName(curFrom));
  put('cur-to-flag', curFlag(curTo)); put('cur-to-code', curTo); put('cur-to-name', curName(curTo));
  put('cur-amount-code', curFrom);
}
function curSetSource(txt){ var el = $('cur-source'); if (el) el.textContent = txt; }
// A soft pulse on the answer, so typing and swapping feel like a real instrument rather than
// a form. It is decoration: the class does nothing for a phone that asks for less motion.
function curPop(){
  var el = $('cur-result');
  if (!el || !el.classList) return;
  el.classList.remove('pop');
  void el.offsetWidth;   // restart the animation on the next frame
  el.classList.add('pop');
  clearTimeout(curPopTimer);
  curPopTimer = setTimeout(function(){ el.classList.remove('pop'); }, 190);
}
// The quick-amount chips light up when the amount on screen is theirs.
function curChips(){
  var n = curAmount();
  var chips = document.querySelectorAll('#cur-chips .cur-chip');
  for (var i = 0; i < chips.length; i++) {
    var v = parseFloat(chips[i].getAttribute('data-amount'));
    chips[i].className = 'cur-chip' + (isFinite(n) && v === n ? ' on' : '');
  }
}
function curUpdate(){
  if (!$('cur-result')) return;
  curPaint();
  var r = curRate(), amount = curAmount();
  var sub = $('cur-result-sub');
  if (!r) {
    $('cur-result').textContent = '--';
    if (sub) sub.textContent = '';
    $('cur-rate-line').textContent = '--';
    $('cur-rate-inverse').textContent = '';
  } else {
    $('cur-result').textContent = isNaN(amount) ? '--' : curMoney(amount * r.rate) + ' ' + r.to;
    if (sub) sub.textContent = isNaN(amount)
      ? 'Type an amount'
      : curPlain(amount) + ' ' + r.from + (curFresh() ? ' at today\u2019s rate' : ' at the saved rate');
    $('cur-rate-line').textContent = '1 ' + r.from + ' = ' + curRateFmt(r.rate) + ' ' + r.to;
    $('cur-rate-inverse').textContent = '1 ' + r.to + ' = ' + curRateFmt(1 / r.rate) + ' ' + r.from;
  }
  var stale = !!curRates && !curFresh();
  $('cur-badge').textContent = curRates ? (stale ? 'Saved' : 'Today') : '';
  $('cur-badge').className = 'cur-badge' + (stale ? ' stale' : '');
  $('cur-stamp').textContent = curRates ? curDate(curRates.date || curRates.at) : '';
  if (r) { storeSet('cedc_cur_from', r.from); storeSet('cedc_cur_to', r.to); }
  curSetSource(curRates
    ? 'Rates from ' + (curRates.source || 'a public feed') + ', ' + curDate(curRates.date) + '. Daily reference rates, not what a bank charges.'
    : 'No rates saved on this phone yet \u2014 this tab needs one connection to fill in.');
  curChips();
  curPop();
}
function curFetch(i){
  if (i >= CUR_FEEDS.length) return Promise.reject(new Error('no feed answered'));
  var feed = CUR_FEEDS[i];
  return fetch(feed.url, { cache: 'no-store' }).then(function(res){
    if (!res.ok) throw new Error('http ' + res.status);
    return res.json();
  }).then(function(j){
    var got = feed.read(j);
    if (!got || !got.rates || !got.rates.USD) throw new Error('no usable rates');
    return { rates: got.rates, date: got.date || '', at: Date.now(), source: feed.name };
  }).catch(function(){ return curFetch(i + 1); });
}
function curRefresh(manual){
  var btn = $('cur-update');
  if (curBusy) return;
  if (typeof fetch !== 'function') {
    curUpdate();
    curSetSource('This phone cannot fetch rates. The tab converts using the rates saved on it.');
    return;
  }
  curBusy = true;
  // The label is put back on BOTH paths. The automatic check on opening the tab used to
  // leave the button reading "Updating..." for the rest of the session.
  if (btn) btn.textContent = 'Updating\u2026';
  curSetSource('Updating rates\u2026');
  curFetch(0).then(function(got){
    curRates = got;
    storeSet(CUR_KEY, JSON.stringify(got));
    curUpdate();
    if (btn) {
      btn.textContent = 'Updated \u2713';
      setTimeout(function(){ if (btn.textContent === 'Updated \u2713') btn.textContent = 'Update rates'; }, 1500);
    }
  }).catch(function(){
    curUpdate();
    curSetSource(curRates
      ? 'No connection \u2014 showing the rates saved on ' + curDate(curRates.date) + '.'
      : 'No connection, and no rates saved yet. Connect once and tap Update rates.');
    if (btn) btn.textContent = 'Try again';
  }).then(function(){ curBusy = false; });
}
function curOnOpen(){
  if (!$('cur-result')) return;
  if (!curRates || !curFresh()) curRefresh(false);
}
// ---- the picker sheet: a currency list you can type into ----
var curSide = 'from';
function curMatches(q){
  q = String(q == null ? '' : q).trim().toLowerCase();
  var codes = curCodes();
  if (!q) {
    var head = CUR_PINNED.filter(function(c){ return codes.indexOf(c) >= 0; });
    var rest = codes.filter(function(c){ return head.indexOf(c) < 0; });
    return head.concat(rest);
  }
  // An exact code first, then codes that begin with what was typed, then names that
  // contain it - so "eu" offers EUR at the top, not halfway down a list.
  var exact = [], starts = [], contains = [];
  codes.forEach(function(c){
    var name = curName(c).toLowerCase(), cc = c.toLowerCase();
    if (cc === q) exact.push(c);
    else if (cc.indexOf(q) === 0) starts.push(c);
    else if (name.indexOf(q) >= 0) contains.push(c);
  });
  return exact.concat(starts, contains);
}
function curPaintList(q){
  var list = $('cur-list');
  if (!list) return;
  var codes = curMatches(q), current = curSide === 'from' ? curFrom : curTo;
  list.innerHTML = '';
  if (!codes.length) {
    var box = document.createElement('div');
    box.className = 'cur-empty';
    box.textContent = 'Nothing matches \u201c' + String(q) + '\u201d. Try a three-letter code, or a name like euro or rupee.';
    list.appendChild(box);
    return;
  }
  codes.forEach(function(c){
    var row = document.createElement('button');
    row.type = 'button';
    row.className = 'cur-row';
    row.setAttribute('data-code', c);
    row.innerHTML =
      '<span class="flag">' + curFlag(c) + '</span>' +
      '<span class="code">' + c + '</span>' +
      '<span class="cname">' + curName(c) + '</span>' +
      (c === current ? '<span class="tick">&#10003;</span>' : '');
    row.addEventListener('click', function(){ curChoose(c); });
    list.appendChild(row);
  });
}
function curOpenSheet(side){
  var sheet = $('cur-sheet');
  if (!sheet) return;
  curSide = side === 'to' ? 'to' : 'from';
  var title = $('cur-sheet-title');
  if (title) title.textContent = curSide === 'from' ? 'Convert from' : 'Convert to';
  var search = $('cur-search');
  if (search) search.value = '';
  curPaintList('');
  sheet.hidden = false;
  if (search) { try { search.focus(); } catch (e) {} }
  var raf = window.requestAnimationFrame || function(fn){ return setTimeout(fn, 0); };
  raf(function(){ sheet.classList.add('in'); });
}
function curCloseSheet(){
  var sheet = $('cur-sheet');
  if (!sheet || sheet.hidden) return;
  sheet.classList.remove('in');
  setTimeout(function(){ sheet.hidden = true; }, 200);
}
// Choosing the currency that is already on the other side swaps the pair instead of leaving
// both sides the same, which would only ever read 1 unit to 1 unit.
function curChoose(code){
  if (curCodes().indexOf(code) < 0) return;
  if (curSide === 'from') {
    if (code === curTo) curTo = curFrom;
    curFrom = code;
  } else {
    if (code === curFrom) curFrom = curTo;
    curTo = code;
  }
  storeSet('cedc_cur_from', curFrom);
  storeSet('cedc_cur_to', curTo);
  curCloseSheet();
  curUpdate();
}

(function initCurrency(){
  if (!$('cur-result')) return;
  curRates = curLoadCache();

  var input = $('cur-value');
  if (input) {
    var saved = storeGet('cedc_cur_amount');
    if (saved) input.value = curCleanAmount(saved);
    input.addEventListener('input', function(){
      var clean = curCleanAmount(this.value);
      if (clean !== this.value) this.value = clean;
      storeSet('cedc_cur_amount', this.value);
      curUpdate();
    });
    input.addEventListener('focus', function(){ try { this.select(); } catch (e) {} });
  }

  var codes = curCodes();
  var sFrom = storeGet('cedc_cur_from'), sTo = storeGet('cedc_cur_to');
  if (sFrom && codes.indexOf(sFrom) >= 0) curFrom = sFrom;
  if (sTo && codes.indexOf(sTo) >= 0) curTo = sTo;
  if (codes.indexOf(curFrom) < 0) curFrom = codes.indexOf('USD') >= 0 ? 'USD' : codes[0];
  if (codes.indexOf(curTo) < 0) curTo = codes.indexOf('EUR') >= 0 ? 'EUR' : (codes[1] || codes[0]);
  if (curTo === curFrom) curTo = codes.filter(function(c){ return c !== curFrom; })[0] || curFrom;

  var fromBtn = $('cur-from-btn'), toBtn = $('cur-to-btn');
  if (fromBtn) fromBtn.addEventListener('click', function(){ curOpenSheet('from'); });
  if (toBtn) toBtn.addEventListener('click', function(){ curOpenSheet('to'); });

  var swap = $('cur-swap');
  if (swap) swap.addEventListener('click', function(){
    var f = curFrom; curFrom = curTo; curTo = f;
    swap.classList.toggle('spin');
    curUpdate();
  });

  var chips = document.querySelectorAll('#cur-chips .cur-chip');
  for (var i = 0; i < chips.length; i++) {
    chips[i].addEventListener('click', function(){
      var v = this.getAttribute('data-amount');
      if (input) input.value = v;
      storeSet('cedc_cur_amount', v);
      curUpdate();
    });
  }

  var search = $('cur-search');
  if (search) {
    search.addEventListener('input', function(){ curPaintList(this.value); });
    search.addEventListener('keydown', function(e){
      if (e.key === 'Enter' || e.keyCode === 13) {
        var first = curMatches(this.value)[0];
        if (first) curChoose(first);
      }
    });
  }
  var sheet = $('cur-sheet');
  if (sheet) sheet.addEventListener('click', function(e){ if (e.target === sheet) curCloseSheet(); });
  document.addEventListener('keydown', function(e){
    if ((e.key === 'Escape' || e.keyCode === 27) && sheet && !sheet.hidden) curCloseSheet();
  });

  var update = $('cur-update');
  if (update) update.addEventListener('click', function(){ curRefresh(true); });

  curUpdate();
})();

// ---------- RELEASES / OTA ----------
// The manifest is read straight from the published repo, wherever this page is running
// from - the hosted PWA, an installed browser app, or a WebView with assets on disk -
// so a build that boots cannot judge itself by its own (stale) copy.
function cmpVer(a, b){
  var pa = String(a).split('.'), pb = String(b).split('.'), n = Math.max(pa.length, pb.length);
  for (var i = 0; i < n; i++){
    var na = parseInt(pa[i], 10) || 0, nb = parseInt(pb[i], 10) || 0;
    if (na !== nb) return na < nb ? -1 : 1;
  }
  return 0;
}
function escapeHtml(s){
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
var otaReg = null;
function setOtaStatus(txt){ var el = $('ota-status'); if (el) el.textContent = txt; }
function registerSW(){
  if (!('serviceWorker' in navigator)) return;
  navigator.serviceWorker.register('sw.js').then(function(r){ otaReg = r; }).catch(function(){});
}

function showUpdateDialog(m){
  if ($('ota-dialog') || !m || !m.version) return;
  var notes = (m.notes || []).slice(0, 6).map(function(n){ return '<li>' + n + '</li>'; }).join('');
  var d = document.createElement('div');
  d.id = 'ota-dialog';
  d.style.cssText = 'position:fixed;inset:0;background:rgba(14,51,80,0.38);display:flex;align-items:flex-end;justify-content:center;z-index:900;';
  d.innerHTML =
    '<div style="width:calc(100% - 28px);max-width:430px;margin-bottom:16px;border-radius:22px;padding:18px 20px 20px;background:rgba(240,248,253,0.99);border:1px solid rgba(255,255,255,0.8);box-shadow:0 -10px 34px rgba(60,120,160,0.35);">' +
      '<div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#4d7999;font-weight:600;">New release' + (m.date ? ' &middot; ' + escapeHtml(m.date) : '') + '</div>' +
      '<div style="font-size:21px;font-weight:600;color:#0e3350;margin-top:6px;">MeasureT v' + escapeHtml(m.version) + '</div>' +
      (m.title ? '<div style="font-size:13px;color:#4d7999;margin-top:4px;line-height:1.5;">' + escapeHtml(m.title) + '</div>' : '') +
      (notes ? '<ul style="margin:12px 0 0;padding-left:18px;color:#0e3350;font-size:13px;line-height:1.55;">' + notes + '</ul>' : '') +
      '<div style="display:flex;gap:10px;margin-top:16px;">' +
        '<button id="ota-later" style="flex:1;padding:13px 0;border-radius:15px;border:1px solid rgba(255,255,255,0.7);background:rgba(255,255,255,0.6);color:#4d7999;font-size:14px;">Later</button>' +
        '<button id="ota-apply" style="flex:1;padding:13px 0;border-radius:15px;border:none;background:linear-gradient(180deg,#5bb8f2,#2f8fd6);color:#fff;font-size:14px;font-weight:600;box-shadow:0 4px 12px rgba(47,143,214,0.35);">Update now</button>' +
      '</div>' +
    '</div>';
  document.body.appendChild(d);
  d.querySelector('#ota-later').addEventListener('click', function(){
    storeSet('cedc_ota_seen_' + m.version, '1');
    d.remove();
  });
  d.querySelector('#ota-apply').addEventListener('click', function(){ applyUpdate(m); });
}

function applyUpdate(m){
  if (m && m.version) storeSet('cedc_ota_seen_' + m.version, '1');
  var dlg = $('ota-dialog'); if (dlg) dlg.remove();
  if (setOtaStatus) setOtaStatus('Updating…');
  if (!('serviceWorker' in navigator)) { location.reload(); return; }
  var done = false;
  function finish(){ if (done) return; done = true; location.reload(); }
  // The new worker skipWaiting()s itself on install, so taking over raises controllerchange.
  navigator.serviceWorker.addEventListener('controllerchange', finish);
  (otaReg ? Promise.resolve(otaReg) : (navigator.serviceWorker.getRegistration() || Promise.reject()))
    .then(function(reg){
      if (reg && reg.waiting) reg.waiting.postMessage({ type: 'SKIP_WAITING' });
      if (reg && reg.update) return reg.update().catch(function(){});
    })
    .catch(function(){});
  // If the published bytes were identical (no new worker), the reload still follows.
  setTimeout(finish, 2500);
}

function checkForUpdates(interactive){
  if (typeof fetch !== 'function'){ if (interactive) setOtaStatus('v' + APP_VERSION + ' · check unavailable'); return Promise.resolve(null); }
  setOtaStatus('Checking…');
  return fetch(OTA_ENDPOINT, { cache: 'no-store' })
    .then(function(r){ if (!r.ok) throw new Error('http ' + r.status); return r.json(); })
    .then(function(m){
      if (!m || !m.version) throw new Error('bad manifest');
      if (cmpVer(m.version, APP_VERSION) > 0){
        setOtaStatus('v' + m.version + ' is available');
        if (interactive || storeGet('cedc_ota_seen_' + m.version) !== '1') showUpdateDialog(m);
      } else {
        setOtaStatus('Up to date · v' + APP_VERSION);
        if (interactive){
          var el = $('btn-check-updates');
          if (el){ el.textContent = 'Fresh'; setTimeout(function(){ el.textContent = 'Check'; }, 1500); }
        }
      }
      return m;
    })
    .catch(function(){
      setOtaStatus(interactive ? 'No connection · v' + APP_VERSION : 'Offline · v' + APP_VERSION);
      return null;
    });
}

if ($('app-version-line')) $('app-version-line').textContent = 'v' + APP_VERSION;
if ($('btn-check-updates')) $('btn-check-updates').addEventListener('click', function(){ checkForUpdates(true); });

// On start: wire the worker, then ask the published manifest what is out there. The check
// waits for 'load' so it never competes with the app's own first paint, and a release the
// user dismissed for THIS version stays dismissed.
registerSW();
window.addEventListener('load', function(){
  setTimeout(function(){ checkForUpdates(false); }, 1200);
});


})();
