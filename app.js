(function(){
'use strict';

// ---------- STATE ----------
var SMOOTH = 0.09;   // EMA alpha — lower = smoother (0.09 ≈ 110 ms time-constant)
var DEAD_ZONE = 1.5; // hold the dial still unless the reading moves more than this (degrees)
var rawHeading = null;
var smoothHeading = null;
var smoothPitch = 0, smoothRoll = 0;
var rafPending = false;

function angleDiff(a, b) {
  var d = a - b;
  return ((d + 540) % 360) - 180; // shortest arc, range (−180, 180]
}
function lerpAngle(prev, next, t) {
  if (prev == null) return next;
  var diff = angleDiff(next, prev);
  return (prev + diff * t + 360) % 360;
}

var state = {
  unitSystem: localStorage.getItem('cedc_units') || 'metric', // 'metric' | 'imperial'
  useTrueNorth: localStorage.getItem('cedc_truenorth') === '1',
  wakeLock: localStorage.getItem('cedc_wakelock') === '1',
  heading: null,
  headingAccuracy: null,
  declination: 0,
  tilt: 0,
  markedBearing: null,
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

// ---------- NAV ----------
document.querySelectorAll('nav button').forEach(function(btn){
  btn.addEventListener('click', function(){
    document.querySelectorAll('nav button').forEach(function(b){ b.classList.remove('active'); });
    document.querySelectorAll('.screen').forEach(function(s){ s.classList.remove('active'); });
    btn.classList.add('active');
    $(btn.dataset.screen).classList.add('active');
  });
});

// ---------- COMPASS DIAL BUILD ----------
(function buildDial(){
  var ticks = $('ticks');
  var labels = $('dial-labels');
  var cx = 150, cy = 150, rOuter = 140, rInnerMajor = 118, rInnerMinor = 128;
  var dirs = [[0,'N'],[90,'E'],[180,'S'],[270,'W']];
  for (var deg = 0; deg < 360; deg += 5) {
    var major = deg % 30 === 0;
    var rad = (deg - 90) * Math.PI / 180;
    var rIn = major ? rInnerMajor : rInnerMinor;
    var x1 = cx + rIn * Math.cos(rad), y1 = cy + rIn * Math.sin(rad);
    var x2 = cx + rOuter * Math.cos(rad), y2 = cy + rOuter * Math.sin(rad);
    var line = document.createElementNS('http://www.w3.org/2000/svg','line');
    line.setAttribute('x1', x1); line.setAttribute('y1', y1);
    line.setAttribute('x2', x2); line.setAttribute('y2', y2);
    line.setAttribute('stroke', deg === 0 ? '#ff6f61' : (major ? 'rgba(14,51,80,0.55)' : 'rgba(14,51,80,0.25)'));
    line.setAttribute('stroke-width', major ? 2 : 1);
    ticks.appendChild(line);
  }
  dirs.forEach(function(d){
    var rad = (d[0] - 90) * Math.PI / 180;
    var r = 100;
    var x = cx + r * Math.cos(rad), y = cy + r * Math.sin(rad) + 6;
    var t = document.createElementNS('http://www.w3.org/2000/svg','text');
    t.setAttribute('x', x); t.setAttribute('y', y);
    t.setAttribute('fill', d[1] === 'N' ? '#ff6f61' : '#0e3350');
    t.setAttribute('font-weight', '600');
    t.textContent = d[1];
    labels.appendChild(t);
  });
})();

function cardinal(deg){
  var dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
  return dirs[Math.round(deg / 22.5) % 16];
}

// ---------- COMPASS ----------
function updateCompassUI(){
  if (smoothHeading == null) return;
  var displayHeading = smoothHeading;
  if (state.useTrueNorth) {
    displayHeading = (displayHeading + state.declination + 360) % 360;
  }
  var rounded = Math.round(displayHeading);
  $('heading-num').textContent = rounded;
  $('heading-cardinal').textContent = cardinal(displayHeading);
  $('dial-rotate').setAttribute('transform', 'rotate(' + (-displayHeading) + ' 150 150)');
  $('stat-tilt').textContent = Math.round(state.tilt) + '°';
  $('stat-declination').textContent = Math.round(state.declination) + '°';
  $('stat-bearing').textContent = state.markedBearing != null ? Math.round(state.markedBearing) + '°' : '--';

  if (state.headingAccuracy != null) {
    if (state.headingAccuracy > 25) {
      $('accuracy-tag').textContent = 'Low accuracy';
      $('accuracy-tag').style.color = '#d9a441';
      $('calib-banner').classList.add('show');
    } else {
      $('accuracy-tag').textContent = '';
      $('calib-banner').classList.remove('show');
    }
  }
}

$('mode-magnetic').addEventListener('click', function(){
  state.useTrueNorth = false;
  localStorage.setItem('cedc_truenorth', '0');
  $('mode-magnetic').classList.add('on');
  $('mode-true').classList.remove('on');
  $('toggle-truenorth').classList.remove('on');
  updateCompassUI();
});
$('mode-true').addEventListener('click', function(){
  state.useTrueNorth = true;
  localStorage.setItem('cedc_truenorth', '1');
  $('mode-true').classList.add('on');
  $('mode-magnetic').classList.remove('on');
  $('toggle-truenorth').classList.add('on');
  updateCompassUI();
});

$('compass-screen').addEventListener('dblclick', function(){
  state.markedBearing = state.useTrueNorth ? (state.heading + state.declination + 360) % 360 : state.heading;
  updateCompassUI();
});

function scheduleUpdate(){
  if (rafPending) return;
  rafPending = true;
  requestAnimationFrame(function(){
    rafPending = false;
    updateCompassUI();
    updateLevelUI();
  });
}

function handleOrientation(e){
  var heading;
  if (e.webkitCompassHeading != null) {
    heading = e.webkitCompassHeading;
    state.headingAccuracy = e.webkitCompassAccuracy;
  } else if (e.alpha != null) {
    heading = 360 - e.alpha;
    state.headingAccuracy = null;
  } else {
    return;
  }
  rawHeading = (heading + 360) % 360;
  state.heading = rawHeading;

  // TRUE dead zone: if the raw reading is essentially where the dial
  // already points, do NOTHING — hold it perfectly still. Only follow the
  // sensor once it moves beyond the dead zone, then ease toward it.
  if (smoothHeading == null || Math.abs(angleDiff(rawHeading, smoothHeading)) >= DEAD_ZONE) {
    smoothHeading = lerpAngle(smoothHeading, rawHeading, SMOOTH);
  }

  state.tilt = e.beta != null ? Math.abs(e.beta) : 0;

  // level tab — EMA smooth pitch/roll
  if (e.beta != null && e.gamma != null) {
    var rawPitch = e.beta > 90 ? 180 - e.beta : (e.beta < -90 ? -180 - e.beta : e.beta);
    var rawRoll = e.gamma;
    state.pitch = rawPitch;
    state.roll = rawRoll;
    // smooth (dead zone doesn't apply to level — continuous response is expected)
    smoothPitch += (rawPitch - smoothPitch) * SMOOTH;
    smoothRoll  += (rawRoll  - smoothRoll)  * SMOOTH;
  }

  scheduleUpdate();
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
    return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  }
  return { rise: fmt(rise), set: fmt(set) };
}

// magnetic declination approximation (rough, WMM-free): use a simple stored value or fetch-free est
function estimateDeclination(lat, lon){
  // extremely rough linear approximation for demo purposes; real apps use WMM tables
  return 0;
}

// ---------- GEOLOCATION ----------
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
}

// ---------- DEVICE ORIENTATION PERMISSION (iOS) ----------
function initOrientation(){
  window.addEventListener('deviceorientationabsolute', handleOrientation, true);
  window.addEventListener('deviceorientation', handleOrientation, true);
}

var needsPermission = typeof DeviceOrientationEvent !== 'undefined' &&
  typeof DeviceOrientationEvent.requestPermission === 'function';

if (needsPermission) {
  var overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;background:linear-gradient(180deg,#cdeaff,#8fc7ee);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:999;padding:24px;text-align:center;';
  overlay.innerHTML = '<div style="font-size:15px;color:#0e3350;margin-bottom:18px;line-height:1.5;">MeasureT needs access to<br>motion and orientation sensors</div><button id="grant-btn" style="background:linear-gradient(180deg,#5bb8f2,#2f8fd6);color:#fff;border:1px solid #2f8fd6;padding:14px 28px;border-radius:24px;font-size:14px;box-shadow:0 6px 16px rgba(47,143,214,0.35);">Enable sensors</button>';
  document.body.appendChild(overlay);
  $('grant-btn').addEventListener('click', function(){
    DeviceOrientationEvent.requestPermission().then(function(res){
      if (res === 'granted') {
        initOrientation();
        overlay.remove();
      }
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

$('toggle-truenorth').addEventListener('click', function(){
  state.useTrueNorth = !state.useTrueNorth;
  localStorage.setItem('cedc_truenorth', state.useTrueNorth ? '1' : '0');
  $('toggle-truenorth').classList.toggle('on', state.useTrueNorth);
  $('mode-true').classList.toggle('on', state.useTrueNorth);
  $('mode-magnetic').classList.toggle('on', !state.useTrueNorth);
  updateCompassUI();
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
$('toggle-truenorth').classList.toggle('on', state.useTrueNorth);
$('toggle-wakelock').classList.toggle('on', state.wakeLock);
if (state.useTrueNorth) {
  $('mode-true').classList.add('on'); $('mode-magnetic').classList.remove('on');
}
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

function setCovMode(m){
  var isC = m === 'convert';
  $('cov-mode-convert').classList.toggle('on', isC);
  $('cov-mode-measure').classList.toggle('on', !isC);
  $('cov-convert-view').style.display = isC ? '' : 'none';
  $('cov-measure-view').style.display = isC ? 'none' : '';
}

$('cov-mode-convert').addEventListener('click', function(){ setCovMode('convert'); });
$('cov-mode-measure').addEventListener('click', function(){ setCovMode('measure'); });
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

// register service worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function(){
    navigator.serviceWorker.register('sw.js').catch(function(){});
  });
}

})();
