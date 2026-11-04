#!/usr/bin/env python3
"""End the AR camera session when you leave the screen the camera belongs to.

BEFORE: the AR range finder lives in the Measure half of the Convert tab. stopAR() does
stop every track (arStream.getTracks().forEach(t => t.stop())), but the only caller was the
Stop button. So tapping another tab, or switching that screen back to Convert, left the rear
camera streaming and the 120 ms report timer ticking in the background. A camera left running
by a tab change is exactly the kind of thing nobody notices, on the one screen in the app
that can see the room.

AFTER: a tab change away from the Convert screen, and a switch back to Convert, both call
stopAR(). Stop still works, and the quick "measure a person" button still starts the camera.

app.js is ~49 KB and has to land byte for byte, so this travels as a patch script with one
anchor per edit. Every anchor is asserted; if the file has moved on, the run fails instead of
writing something nobody reviewed. --check re-verifies the landed file without touching it.
"""
import sys
import pathlib

APP = pathlib.Path(__file__).resolve().parents[2] / "app.js"

VERSION_OLD = "var APP_VERSION = '1.1.2';"
VERSION_NEW = "var APP_VERSION = '1.1.3';"

CHANGELOG_OLD = (
    "  { version: '1.1.2', date: 'November 3, 2026', title: 'MeasureT can be thanked, in Settings', items: ["
)
CHANGELOG_NEW = (
    "  { version: '1.1.3', date: 'November 4, 2026', title: 'The AR camera stops when you leave it', items: [\n"
    "    'Leaving the Measure half of the Convert tab &mdash; by tapping another tab, or by switching back to Convert &mdash; now ends the AR camera. Before this, the camera kept streaming and the live distance kept updating in the background, and only the <b>Stop</b> button could turn it off.',\n"
    "    'Nothing else changed &mdash; the converter, GPS measuring, the compass, permissions and updates are exactly as they were.'\n"
    "  ]},\n"
    + CHANGELOG_OLD
)

# The tab handler: the camera belongs to the Convert screen, so any other tab ends it.
NAV_OLD = (
    "    // The Convert tab always lands on the converter. That screen carries a Convert / Measure"
)
NAV_NEW = (
    "    // The AR camera belongs to the Measure half of this tab, so a tab change ends it. Before\n"
    "    // this, the stream and its 120 ms report timer kept running with only Stop able to end\n"
    "    // them, which left a camera on in the background after a single tap on another tab.\n"
    "    if (btn.dataset.screen !== 'convert-screen' && arActive) stopAR();\n"
    "    // The Convert tab always lands on the converter. That screen carries a Convert / Measure"
)

# The Convert/Measure switch inside that screen: Convert is not the camera's half.
COV_OLD = (
    "function setCovMode(m){\n"
    "  var isC = m === 'convert';"
)
COV_NEW = (
    "function setCovMode(m){\n"
    "  var isC = m === 'convert';\n"
    "  // The camera belongs to the Measure half: switching to Convert ends it rather than\n"
    "  // leaving it on behind a screen that cannot show it. stopAR is hoisted, and arActive is\n"
    "  // still undefined during the startup calls this runs from, so neither can throw here.\n"
    "  if (isC && arActive) stopAR();"
)

EDITS = [
    ("APP_VERSION", VERSION_OLD, VERSION_NEW),
    ("the head CHANGELOG entry", CHANGELOG_OLD, CHANGELOG_NEW),
    ("the tab handler", NAV_OLD, NAV_NEW),
    ("setCovMode", COV_OLD, COV_NEW),
]

MARKERS = [
    "var APP_VERSION = '1.1.3';",
    "version: '1.1.3', date: 'November 4, 2026'",
    "if (btn.dataset.screen !== 'convert-screen' && arActive) stopAR();",
    "if (isC && arActive) stopAR();",
]


def main() -> int:
    if not APP.exists():
        sys.exit("FATAL: %s missing" % APP)
    src = APP.read_text()

    if "--check" in sys.argv:
        missing = [m for m in MARKERS if m not in src]
        if missing:
            for m in missing:
                print("MISSING: %s" % m)
            sys.exit("FATAL: app.js does not carry the AR-stop fix")
        # The old anchors must be gone, or the patch was applied to the wrong shape.
        if VERSION_OLD in src:
            sys.exit("FATAL: APP_VERSION is still 1.1.2 next to a 1.1.3 marker")
        print("app.js carries the AR-stop fix and says 1.1.3")
        return 0

    for label, old, new in EDITS:
        if new in src and old not in src:
            print("already applied: %s" % label)
            continue
        n = src.count(old)
        if n != 1:
            sys.exit("FATAL: %s anchor found %d times in %s (expected 1)\n--- anchor ---\n%s"
                     % (label, n, APP, old))
        src = src.replace(old, new, 1)
        print("patched: %s" % label)

    APP.write_text(src)
    missing = [m for m in MARKERS if m not in src]
    if missing:
        sys.exit("FATAL: patch wrote but markers are missing: %s" % missing)
    print("app.js written with the AR-stop fix at 1.1.3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
