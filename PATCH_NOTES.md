# Patch notes

What changed in each release, newest first.

**The in-app notes are the source of truth**: the changelog inside `app.js` (`CHANGELOG`) is what an
installed copy shows in Settings → Updates, and `dev/ota.mjs --check` fails a release whose
`APP_VERSION`, changelog head, `updates.json` and `package.json` disagree. This file mirrors those
entries for anyone reading the repository.

Every run of the Android workflow produces four files: `MeasureT-<version>-debug.apk`,
`MeasureT-<version>-debug.aab`, `MeasureT-<version>.aab` (the Play upload) and — when the keystore
secrets are set — `MeasureT-<version>.apk`.

## 1.2.0 — 2026-11-04 — a Currency tab

### Added
- A **Currency** tab, the seventh, between Convert and Settings: an amount, two currencies and the
  day's rate, the reverse rate underneath, and ⇅ to swap the pair.
- Rates from a public feed that needs no key and no account — `open.er-api.com` — with the European
  Central Bank's own feed as the fallback when that one is down.
- The answer is written to `localStorage`, so the tab keeps converting with no connection and says
  which day's rates are on screen; the picker offers only the currencies the saved rates can convert.

### Changed
- Nothing else — the converter, GPS measuring, the AR range finder, the compass, permissions and
  updates are exactly as they were.

## 1.1.2 — 2026-11-03 — MeasureT can be thanked, in Settings

### Added
- A **Support** group in Settings, above the version line: five amounts ($2, $5, $10, $25, $50),
  each an ordinary Stripe payment page opened in the browser — the same five links SideCut's Donate
  tab uses. Nothing unlocks and nothing is sent from the app; a tip is a thank you.
- A **debug AAB** beside the debug APK, so one run of the workflow gives you something to install
  and something to upload.

### Changed
- Nothing else — the converter, GPS measuring, the AR range finder, the compass, permissions and
  updates are exactly as they were.

## 1.1.1 — 2026-10-29 — there is always a way back to Convert

### Fixed
- A **Convert** button at the top of the Measure half itself, in normal flow, so a way back can no
  longer be clipped away by the layout that hid the switch.
- The Convert / Measure switch reserves 44 px and refuses to shrink: it is `overflow:hidden`, so as a
  flex item its automatic minimum height was 0 — the spec's overflow trap, and the switch that kept
  disappearing.

## 1.1.0 — 2026-10-17 — the switch can no longer disappear, and MeasureT updates itself

### Fixed
- Denying motion & orientation access used to leave a full-screen panel over the app forever.

### Added
- MeasureT checks for a new release on start, in Settings → Updates, and shows what changed before
  it applies. Updates arrive while the app runs, newest-first.

## 1.0.0 — 2026-07-17 — first release

Compass, elevation, location, level, a unit converter, GPS measurement and AR distance.
