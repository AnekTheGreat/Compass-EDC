#!/usr/bin/env python3
"""Add the Currency tab to MeasureT, exactly.

Every replacement states its anchor and is refused unless that anchor occurs the stated
number of times, so a page that has drifted cannot be half-patched: the script either
produces the intended files or exits non-zero with nothing written.

    python3 dev/patch-currency.py

Idempotent: an edit whose result is already present is skipped rather than doubled.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CSS_ANCHOR = "/* ---------- NAV ---------- */"
CSS_BLOCK = """/* ---------- CURRENCY ---------- */
#cur-value{flex:1;min-width:0;font-size:30px;font-weight:200;color:var(--text);background:none;border:none;outline:none;border-bottom:1px solid var(--glass-line);padding:6px 2px;font-variant-numeric:tabular-nums;user-select:text;-webkit-user-select:text;}
.cur-stamp{font-size:11px;color:var(--dim);letter-spacing:0.5px;}
.cur-head{display:flex;align-items:baseline;justify-content:space-between;gap:10px;}
.cur-badge{font-size:10px;letter-spacing:1px;text-transform:uppercase;color:var(--accent2);}
.cur-badge.stale{color:var(--amber);}
.cur-note{font-size:12px;line-height:1.6;color:var(--dim);margin-top:10px;}

""" + CSS_ANCHOR

SETTINGS_ANCHOR = "  <!-- SETTINGS -->"
SCREEN_BLOCK = """  <!-- CURRENCY -->
  <section class="screen" id="currency-screen">
    <div class="topbar">
      <span class="title">Currency</span>
      <span class="cur-stamp" id="cur-stamp">&nbsp;</span>
    </div>

    <div class="card glass">
      <div class="cov-inputrow">
        <input id="cur-value" type="number" inputmode="decimal" min="0" placeholder="Amount" value="100">
        <button class="cov-swap" id="cur-swap" title="Swap currencies">&#8645;</button>
      </div>
      <div class="cov-unitsrow">
        <select id="cur-from"></select>
        <span class="cov-arrow">&#8594;</span>
        <select id="cur-to"></select>
      </div>
      <div class="cov-resultrow">
        <div class="cov-result" id="cur-result">--</div>
      </div>
    </div>

    <div class="card glass" style="margin-top:12px;">
      <div class="cur-head"><div class="l">Rate</div><span class="cur-badge" id="cur-badge"></span></div>
      <div class="cov-equation" id="cur-rate-line">--</div>
      <div class="cov-equation" id="cur-rate-inverse"></div>
      <div class="cur-note" id="cur-source">Loading the day's rates&hellip;</div>
    </div>

    <div class="cov-actions">
      <button class="cov-action primary" id="cur-update">Update rates</button>
    </div>

    <div class="card glass" style="margin-top:12px;">
      <div class="cur-note" style="margin-top:0;">These are daily reference rates, not the rate a bank, a card or a cash machine gives you. The last ones fetched stay on the phone, so this tab keeps converting with no connection.</div>
    </div>
  </section>

""" + SETTINGS_ANCHOR

CONVERT_BUTTON = """    <button data-screen="convert-screen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M7 5L4 8l3 3M4 8h13M17 19l3-3-3-3M20 16H7"/></svg>
      <span class="navlabel">Convert</span>
    </button>"""
CURRENCY_BUTTON = CONVERT_BUTTON + """
    <button data-screen="currency-screen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2.5" y="6.5" width="19" height="11" rx="2.5"/><circle cx="12" cy="12" r="2.5"/><path d="M6.2 9.8v4.4M17.8 9.8v4.4"/></svg>
      <span class="navlabel">Currency</span>
    </button>"""

VERSION_OLD = "var APP_VERSION = '1.1.3';"
VERSION_NEW = "var APP_VERSION = '1.2.0';"

CHANGELOG_ANCHOR = """var CHANGELOG = [
  { version: '1.1.3',"""
CHANGELOG_NEW = """var CHANGELOG = [
  { version: '1.2.0', date: 'November 4, 2026', title: 'A Currency tab, with the day&rsquo;s exchange rate', items: [
    'A <b>Currency</b> tab now sits between Convert and Settings. Type an amount, pick the two currencies, and it converts at the day&rsquo;s rate; the reverse rate is printed underneath, and the &#8645; button swaps the pair.',
    'The rates come from a public feed that needs no sign-in, and every answer is saved on the phone &mdash; so the tab keeps converting on a plane or with no signal, and says which day&rsquo;s rates you are looking at.',
    'Nothing else changed &mdash; the converter, GPS measuring, the AR range finder, the compass, permissions and updates are exactly as they were.'
  ]},
  { version: '1.1.3',"""

NAV_ANCHOR = "    if (btn.dataset.screen === 'convert-screen') setCovMode('convert');"
NAV_NEW = """    if (btn.dataset.screen === 'convert-screen') setCovMode('convert');
    // The currency tab asks for a fresh rate the first time it is opened, not on every
    // start: nothing on this screen is needed by the compass or the level.
    if (btn.dataset.screen === 'currency-screen') curOnOpen();"""

OTA_ANCHOR = "// ---------- RELEASES / OTA ----------"
CURRENCY_JS = r"""// ---------- CURRENCY ----------
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
function curRateFmt(n){
  if (!isFinite(n) || n <= 0) return '--';
  if (n >= 1000) return n.toFixed(0);
  if (n >= 1) return n.toFixed(4).replace(/\.?0+$/, '');
  if (n >= 0.001) return n.toFixed(6).replace(/\.?0+$/, '');
  return n.toPrecision(3);
}
function curLabel(c){ return CUR_NAMES[c] ? c + ' \u2014 ' + CUR_NAMES[c] : c; }
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
function curFillSelects(){
  var fromSel = $('cur-from'), toSel = $('cur-to');
  if (!fromSel || !toSel) return;
  var keptFrom = fromSel.value, keptTo = toSel.value;
  var codes = curCodes();
  [fromSel, toSel].forEach(function(sel){
    sel.innerHTML = '';
    codes.forEach(function(c){
      var o = document.createElement('option');
      o.value = c; o.textContent = curLabel(c);
      sel.appendChild(o);
    });
  });
  var wantFrom = keptFrom || storeGet('cedc_cur_from') || 'USD';
  var wantTo = keptTo || storeGet('cedc_cur_to') || 'EUR';
  if (codes.indexOf(wantFrom) < 0) wantFrom = codes.indexOf('USD') >= 0 ? 'USD' : codes[0];
  if (codes.indexOf(wantTo) < 0 || wantTo === wantFrom) {
    var alt = codes.filter(function(c){ return c !== wantFrom; });
    wantTo = alt.indexOf('EUR') >= 0 ? 'EUR' : (alt[0] || wantFrom);
  }
  fromSel.value = wantFrom;
  toSel.value = wantTo;
}
function curRate(){
  var f = $('cur-from').value, t = $('cur-to').value;
  if (!curRates || !curRates.rates) return null;
  var rf = curRates.rates[f], rt = curRates.rates[t];
  if (!rf || !rt) return null;
  return { from: f, to: t, rate: rt / rf };
}
function curSetSource(txt){ var el = $('cur-source'); if (el) el.textContent = txt; }
function curUpdate(){
  if (!$('cur-result')) return;
  var r = curRate();
  var amount = parseFloat($('cur-value').value);
  if (!r) {
    $('cur-result').textContent = '--';
    $('cur-rate-line').textContent = '--';
    $('cur-rate-inverse').textContent = '';
  } else {
    $('cur-result').textContent = isNaN(amount) ? '--' : curMoney(amount * r.rate) + ' ' + r.to;
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
  if (btn) btn.textContent = 'Updating\u2026';
  curSetSource('Updating rates\u2026');
  curFetch(0).then(function(got){
    curRates = got;
    storeSet(CUR_KEY, JSON.stringify(got));
    curFillSelects();
    curUpdate();
    if (manual && btn) { btn.textContent = 'Updated'; setTimeout(function(){ btn.textContent = 'Update rates'; }, 1500); }
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
(function initCurrency(){
  var fromSel = $('cur-from'), toSel = $('cur-to');
  if (!fromSel || !toSel) return;
  curRates = curLoadCache();
  if ($('cur-value')) {
    var saved = storeGet('cedc_cur_amount');
    if (saved) $('cur-value').value = saved;
    $('cur-value').addEventListener('input', function(){
      storeSet('cedc_cur_amount', this.value);
      curUpdate();
    });
  }
  curFillSelects();
  curUpdate();
  fromSel.addEventListener('change', curUpdate);
  toSel.addEventListener('change', curUpdate);
  $('cur-swap').addEventListener('click', function(){
    var f = fromSel.value;
    fromSel.value = toSel.value;
    toSel.value = f;
    curUpdate();
  });
  $('cur-update').addEventListener('click', function(){ curRefresh(true); });
})();

""" + OTA_ANCHOR

EDITS = [
    ("index.html", CSS_ANCHOR, CSS_BLOCK, 1),
    ("index.html", SETTINGS_ANCHOR, SCREEN_BLOCK, 1),
    ("index.html", CONVERT_BUTTON, CURRENCY_BUTTON, 1),
    ("app.js", VERSION_OLD, VERSION_NEW, 1),
    ("app.js", CHANGELOG_ANCHOR, CHANGELOG_NEW, 1),
    ("app.js", NAV_ANCHOR, NAV_NEW, 1),
    ("app.js", OTA_ANCHOR, CURRENCY_JS, 1),
]


def main():
    texts = {}
    applied = skipped = 0
    for name, old, new, times in EDITS:
        if name not in texts:
            texts[name] = (ROOT / name).read_text(encoding="utf-8")
        text = texts[name]
        if new in text:
            skipped += 1
            continue
        found = text.count(old)
        if found != times:
            sys.exit(f"{name}: anchor {old.splitlines()[0]!r} appears {found} times, expected {times}")
        texts[name] = text.replace(old, new, times)
        applied += 1

    for name, text in texts.items():
        (ROOT / name).write_text(text, encoding="utf-8")

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app.js").read_text(encoding="utf-8")
    checks = [
        ("one currency screen", html.count('id="currency-screen"') == 1),
        ("one currency nav tab", html.count('data-screen="currency-screen"') == 1),
        ("one local rate cache", js.count("var CUR_KEY = 'cedc_rates';") == 1),
        ("both feeds declared", js.count("url: 'https://") == 2),
        ("version is 1.2.0", "var APP_VERSION = '1.2.0';" in js),
    ]
    bad = [label for label, good in checks if not good]
    if bad:
        sys.exit("failed: " + ", ".join(bad))
    print(f"currency tab applied ({applied} edits, {skipped} already in place)")
    for label, good in checks:
        print("  ok " + label)


if __name__ == "__main__":
    main()
