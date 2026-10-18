// MeasureT release tool.
//
//   node dev/ota.mjs           publish: regenerate updates.json from app.js' head
//                               CHANGELOG entry, stamp sw.js' cache and package.json
//                               from APP_VERSION.
//   node dev/ota.mjs --check   verify all four agree (app.js, updates.json, sw.js,
//                               package.json) and that the manifest's notes are the head
//                               entry's, verbatim. Exits non-zero on any drift.
//
// The app reads updates.json from the published repo, never its own copy, so the field
// this writes is exactly the one a user is comparing against.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (f) => fs.readFileSync(path.join(ROOT, f), 'utf8');
const write = (f, s) => fs.writeFileSync(path.join(ROOT, f), s);

const appSrc = read('app.js');
const ver = (appSrc.match(/^var APP_VERSION = '([^']+)';$/m) || [])[1];
if (!ver) { console.error('app.js has no APP_VERSION line'); process.exit(2); }

const block = appSrc.match(/var CHANGELOG = \[([\s\S]*?)\n\];/);
let head = null;
if (block) {
  try { head = eval('[' + block[1] + ']')[0]; } catch (e) { console.error('CHANGELOG parse failed:', e.message); process.exit(2); }
}
if (!head || String(head.version) !== ver) {
  console.error(`head CHANGELOG entry (${head && head.version}) is not APP_VERSION (${ver}) - write it first`);
  process.exit(2);
}
const notes = (head.items || []).slice(0, 6).map((s) => s.replace(/&amp;/g, '&'));
if (!notes.length) { console.error('head changelog entry has no items'); process.exit(2); }

const manifest = { version: ver, url: 'index.html', notes, date: head.date ? String(head.date) : '' };
const target = path.join(ROOT, 'updates.json');

if (process.argv.includes('--check')) {
  let fail = 0;
  const ok = (name, cond, extra) => {
    if (cond) console.log('  ✓ ' + name);
    else { fail++; console.log('  ✗ ' + name + (extra ? '  [' + extra + ']' : '')); }
  };
  let remote = null;
  try { remote = JSON.parse(read('updates.json')); } catch {}
  ok('updates.json parses', !!remote);
  ok(`updates.json version == APP_VERSION (${ver})`, remote && remote.version === ver, remote && remote.version);
  ok('updates.json notes == head changelog items', remote && JSON.stringify(remote.notes) === JSON.stringify(manifest.notes));
  ok(`updates.json date == head changelog date (${manifest.date})`, remote && remote.date === manifest.date, remote && remote.date);
  ok(`sw.js CACHE == measuret-v${ver}`, read('sw.js').includes(`'measuret-v${ver}'`));
  ok(`package.json version == ${ver}`, JSON.parse(read('package.json')).version === ver);
  console.log(fail ? `\n${fail} failed` : '\nall checks pass');
  process.exit(fail ? 1 : 0);
}

write('updates.json', JSON.stringify(manifest));
const sw = read('sw.js');
write('sw.js', sw.replace(/var CACHE = '[^']+';/, `var CACHE = 'measuret-v${ver}';`));
const pkg = JSON.parse(read('package.json'));
pkg.version = ver;
write('package.json', JSON.stringify(pkg, null, 2) + '\n');
console.log(`MeasureT ${ver} published: updates.json (${notes.length} notes), sw cache stamped, package.json stamped`);