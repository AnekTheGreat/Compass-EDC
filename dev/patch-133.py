#!/usr/bin/env python3
"""MeasureT 1.3.3 - the same five apps, at addresses that answer.

This list already carried all five siblings, which is more than most of the family managed, but four
of its five rows opened Play listings that do not exist yet. 1.3.3 gives every row an address that
answers today, with the same one-line descriptions the other apps use.

The page and app.js had also drifted apart: index.html still said v1.3.1 while app.js was v1.3.2.
Both say 1.3.3 now.

--check says whether the tree ALREADY carries the change, which is what the apply workflow asks it
before deciding there is nothing to do.

    python3 dev/patch-133.py            # apply
    python3 dev/patch-133.py --check    # verify only, writes nothing
"""

import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAGE = "index.html"
APP = "app.js"
PACKAGE = "package.json"
FEED = "updates.json"

V = "1.3.3"
OLD = "1.3.2"
OLD_PAGE = "1.3.1"

ROW = ('      <div class="set-row"><div><div class="label">%s</div><div class="sub">%s</div></div>'
       '<a class="unitbtn" style="text-decoration:none" href="%s" target="_blank" '
       'rel="noopener noreferrer">%s</a></div>\n')

ROWS_NEW = (
    ROW % ("My Hub", "One screen that launches the rest, and keeps each one up to date",
           "https://github.com/AnekTheGreat/My-Hub/releases/latest", "Get")
    + ROW % ("FamTM", "The family tree in your pocket",
             "https://github.com/AnekTheGreat/FamTM/releases/latest", "Get")
    + ROW % ("SideCut", "A music player with its own equaliser",
             "https://play.google.com/store/apps/details?id=com.SideCut.myapp", "Get")
    + ROW % ("UJournal", "A journal for the days you write down",
             "https://github.com/AnekTheGreat/Journal/releases/latest", "Get")
    + ROW % ("UNote", "Notes that link themselves, with a vault behind a PIN",
             "https://anekthegreat.github.io/UNote/", "Open")
)

COMMENT_OLD = "    <!-- The other apps, in the same shape as the journal's and My Hub's lists: a name, what it does, and a tap that opens its Play listing. The addresses are"
COMMENT_NEW = "    <!-- The other apps, in the same shape as the journal's and My Hub's lists: a name, what it does, and a tap that opens where it installs from. Only SideCut is on Play, so its row opens the listing; the rest open their release or their page. The addresses are"

ENTRY = ("    { version: '%s', date: 'November 8, 2026', title: 'All five rows answer', items: [\n"
         "      'More apps lists the same five apps the rest of the family lists, in the same order and with the same one-line descriptions.',\n"
         "      'Four of the five rows pointed at Play listings that are not up yet, so a tap answered with Play\\'s own not-found page. My Hub, FamTM and UJournal now open the release they install from, and UNote opens its page. SideCut keeps its live listing.',\n"
         "      'The version line in the page caught up with the app: it said v1.3.1 while the code was already at 1.3.2.',\n"
         "    ] },\n" % V)

FEED_NOTES = [
    "More apps lists the same five apps the rest of the family lists, in the same order and with the "
    "same one-line descriptions: My Hub, FamTM, SideCut, UJournal and UNote.",
    "Four of the five rows pointed at Play listings that are not up yet, so a tap answered with "
    "Play's own not-found page. My Hub, FamTM and UJournal now open the release they install from, "
    "and UNote opens its page. SideCut keeps its live listing.",
]


def read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def write(rel, text):
    with io.open(os.path.join(ROOT, rel), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def main():
    check = "--check" in sys.argv
    page = read(PAGE)
    app = read(APP)
    package = read(PACKAGE)
    feed = read(FEED)
    touched = []

    if ROWS_NEW not in page:
        if 'id="other-apps"' not in page:
            sys.exit("the page has no other-apps section")
        i = page.index('id="other-apps"')
        start = page.index('<div class="set-row">', i)
        end = page.index("    </div>\n", i)
        page = page[:start] + ROWS_NEW + page[end:]
        touched.append("the More apps rows")

    if COMMENT_NEW not in page and COMMENT_OLD in page:
        page = page.replace(COMMENT_OLD, COMMENT_NEW, 1)
        touched.append("the comment over the rows")

    if ("v" + V) not in page:
        if ("v" + OLD_PAGE) not in page or ("app.js?v=" + OLD_PAGE) not in page:
            sys.exit("the page does not name %s" % OLD_PAGE)
        page = page.replace("v" + OLD_PAGE, "v" + V, 1)
        page = page.replace("app.js?v=" + OLD_PAGE, "app.js?v=" + V, 1)
        touched.append("the version in the page")

    if ("var APP_VERSION = '%s';" % V) not in app:
        if ("var APP_VERSION = '%s';" % OLD) not in app:
            sys.exit("app.js does not name %s" % OLD)
        app = app.replace("var APP_VERSION = '%s';" % OLD, "var APP_VERSION = '%s';" % V, 1)
        head = "var CHANGELOG = [\n"
        if head not in app:
            sys.exit("app.js has no CHANGELOG")
        app = app.replace(head, head + ENTRY, 1)
        touched.append("APP_VERSION and the changelog")

    if ('"version": "%s"' % V) not in package:
        if ('"version": "%s"' % OLD) not in package:
            sys.exit("package.json does not name %s" % OLD)
        package = package.replace('"version": "%s"' % OLD, '"version": "%s"' % V, 1)
        touched.append("package.json")

    if ('"version": "%s"' % V) not in feed:
        if ('"version":"%s"' % OLD) not in feed:
            sys.exit("updates.json does not name %s" % OLD)
        d = json.loads(feed)
        d["version"] = V
        d["date"] = "November 8, 2026"
        d["notes"] = FEED_NOTES
        feed = json.dumps(d, ensure_ascii=False, indent=2) + "\n"
        touched.append("updates.json")

    probes = [
        (ROWS_NEW in page, "the five rows are not in the page"),
        (page.count("https://play.google.com/store/apps/details?id=") == 1,
         "a row still points at a Play listing that is not there"),
        ("github.com/AnekTheGreat/My-Hub/releases/latest" in page, "My Hub has no address"),
        ("github.com/AnekTheGreat/FamTM/releases/latest" in page, "FamTM has no address"),
        ("github.com/AnekTheGreat/Journal/releases/latest" in page, "UJournal has no address"),
        ("anekthegreat.github.io/UNote/" in page, "UNote has no address"),
        ("v" + V in page, "the page does not say %s" % V),
        ("app.js?v=" + V in page, "the page still asks for the old script"),
        ("var APP_VERSION = '%s';" % V in app, "app.js does not say %s" % V),
        ("version: '%s'" % V in app, "the changelog has no %s entry" % V),
        ('"version": "%s"' % V in package, "package.json does not say %s" % V),
        ('"version": "%s"' % V in feed, "updates.json does not say %s" % V),
        ("MeasureT" in page, "the page lost its name"),
    ]
    bad = [why for ok, why in probes if not ok]
    if bad:
        sys.exit("; ".join(bad))

    if check:
        if touched:
            sys.exit("the tree does not carry %s yet (%s)" % (V, ", ".join(touched)))
        print("all %d checks pass - the tree carries MeasureT %s" % (len(probes), V))
        return

    write(PAGE, page)
    write(APP, app)
    write(PACKAGE, package)
    write(FEED, feed)
    print("MeasureT %s written to index.html, app.js, package.json and updates.json" % V)
    print("next: android-build.yml builds it, and the page deploys on its own")


if __name__ == "__main__":
    main()
