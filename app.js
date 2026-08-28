(function(){
'use strict';

// ---------- STATE ----------
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
  if (state.heading == null) return;
  var displayHeading = state.heading;
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
  state.heading = (heading + 360) % 360;
  state.tilt = e.beta != null ? Math.abs(e.beta) : 0;
  updateCompassUI();

  // level tab uses beta/gamma
  if (e.beta != null && e.gamma != null) {
    state.pitch = e.beta > 90 ? 180 - e.beta : (e.beta < -90 ? -180 - e.beta : e.beta);
    state.roll = e.gamma;
    updateLevelUI();
  }
}

// ---------- LEVEL ----------
function updateLevelUI(){
  var pitch = state.pitch, roll = state.roll;
  $('level-pitch').textContent = pitch.toFixed(1);
  $('level-roll').textContent = roll.toFixed(1);
  var maxOffset = 90;
  var dx = Math.max(-90, Math.min(90, roll)) / maxOffset * 90;
  var dy = Math.max(-90, Math.min(90, pitch)) / maxOffset * 90;
  var bubble = $('level-bubble');
  var cx = 140 + dx, cy = 140 + dy;
  bubble.setAttribute('cx', cx);
  bubble.setAttribute('cy', cy);
  var isFlat = Math.abs(pitch) < 1 && Math.abs(roll) < 1;
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
  overlay.innerHTML = '<div style="font-size:15px;color:#0e3350;margin-bottom:18px;line-height:1.5;">Compass EDC needs access to<br>motion and orientation sensors</div><button id="grant-btn" style="background:linear-gradient(180deg,#5bb8f2,#2f8fd6);color:#fff;border:1px solid #2f8fd6;padding:14px 28px;border-radius:24px;font-size:14px;box-shadow:0 6px 16px rgba(47,143,214,0.35);">Enable sensors</button>';
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
