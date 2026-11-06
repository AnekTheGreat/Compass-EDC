# Patch notes

What changed in each release, newest first.

**The in-app notes are the source of truth**: the changelog inside `app.js` (`CHANGELOG`) is what an
installed copy shows in Settings → Updates, and `dev/ota.mjs --check` fails a release whose
`APP_VERSION`, changelog head, `updates.json` and `package.json` disagree. This file mirrors those
entries for anyone reading the repository.

Every run of the Android workflow produces four files: `MeasureT-<version>-release.aab` (the Play
upload), `MeasureT-<version>-release.apk` (the same build, installable), and the debug pair
`MeasureT-<version>-debug.apk` / `MeasureT-<version>-debug.aab`. The release pair is signed with
the upload keystore, and the run fails rather than hand over an unsigned bundle.

## 1.3.1 — November 6, 2026

**Updates that never took: the version loop is gone**

- The app's page and its script are each cached for **ten minutes** by the host, and only the page was being fetched fresh. The app therefore reported the version from the **old script** while the release feed kept offering the new one: **Update now** landed back on the same version, every time.
- The script is now requested by a **versioned address** (`app.js?v=1.3.1`), which no phone's cache has ever seen, and the service worker no longer trusts the browser cache for **any** of the app's files.
- **Check for updates** can no longer sit on "Checking…" forever: ten seconds and it reports that there was no answer.
- Settings → Updates ends with **Reload this page**, which loads the app from a fresh address — the way out if a cache ever disagrees with the server again.
- Nothing else changed — the time-zone chip, elevation, location, the level, the converter, currency, GPS measuring, the AR range finder and permissions are as they were.

## 1.3.0 — November 6, 2026

**A Time chip in Convert: what time it is anywhere, and how far that is from you**

- A **Time** chip sits at the end of the Convert row. Pick a place from the searchable list — about fifty, from London and Lagos to Tokyo and Auckland — and the card shows the time there, the day there, and the gap from your own clock in words: **3 hours ahead of you**, **the same time as you**, **5 hours 45 minutes behind you**.
- Your own time sits under it, both clocks on one screen, and the last place you picked is remembered.
- The times come from the phone's own time-zone database, so daylight saving is whatever each place is actually doing on that date.
- Nothing else changed — elevation, location, the level, the unit converter and its six categories, currency, GPS measuring, the AR range finder, permissions and updates are as they were.

## 1.2.3 — November 5, 2026

**The other apps are on the Settings tab, and the build proves which key signed it**

- Settings ends with **More apps**: UJournal, FamTM, My Hub and SideCut, each with what it does and a **Get** button that opens its Play listing.
- The Android build now checks the release APK's certificate against MeasureT's upload certificate and **fails** when they differ, instead of printing it and passing.

## 1.2.2 — November 5, 2026

**The Compass tab is gone, and the currency answer is easy to read**

- The **Compass** tab has been **removed**. It was the most complicated thing in the app, and the
  heading dial, its calibration banner, the marked bearing and the true-north switch went with it.
  MeasureT now has **six tabs** and opens on **Convert**.
- The **currency answer** could be cut off at the bottom of its card on a phone with larger text,
  which is why the number was hard to see. The card now grows to fit what is in it instead of being
  squeezed, the answer is **larger and darker**, and the labels above it are legible.
- Nothing else changed — elevation, location, the level, the converter, GPS measuring, the AR range
  finder, permissions and updates are exactly as they were.

## 1.2.1 — 2026-11-05 — type the currency

### Changed
- Both currency buttons open a **searchable list**: type a three-letter code (`eur`) or a name
  (`euro`, `rupee`) and it narrows as you type; common currencies sit at the top and the pair in
  use is ticked. Enter takes the first match; Escape or a tap outside closes it.
- The amount is a real field — tap the big number and type, or use the 10 / 50 / 100 / 500 chips —
  with the currency being typed in shown beside it, and the answer following as you type.
- One glowing card holds the amount, the pair and the answer: the answer is set in a blue-to-green
  gradient, ⇅ spins when the pair swaps, and the number pulses when it changes. All of that motion
  is off under `prefers-reduced-motion`.
- The seven tab labels scale with the screen width instead of running into each other.

### Fixed
- The update button could stay on **Updating…** after the automatic check on opening the tab. It
  now goes back to *Update rates*, or offers *Try again* when the fetch failed.

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
