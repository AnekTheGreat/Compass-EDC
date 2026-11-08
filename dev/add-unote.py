#!/usr/bin/env python3
"""UNote joins MeasureT's More apps list.

Run from the repository root: python3 dev/add-unote.py
--check reports without writing, and a second run is a no-op.
"""
import io
import sys

PAGE = 'index.html'
URL = 'https://anekthegreat.github.io/UNote/'
APK = 'https://github.com/AnekTheGreat/UNote/releases/latest/download/UNote.apk'
text = io.open(PAGE, encoding='utf-8').read()

if '>UNote<' in text:
    print('UNote is already in the list - nothing to do')
    sys.exit(0)

if '--check' in sys.argv:
    print('UNote is NOT in the list - it needs applying')
    sys.exit(1)

anchor = ('href="https://play.google.com/store/apps/details?id=com.SideCut.myapp" target="_blank" '
          'rel="noopener noreferrer">Get</a></div>\n    </div>')
if text.count(anchor) != 1:
    sys.exit('the SideCut row is not where it was (%d matches)' % text.count(anchor))

row = ('\n      <div class="set-row"><div><div class="label">UNote</div><div class="sub">Notes that link '
       'themselves, with a vault behind a PIN</div></div><a class="unitbtn" style="text-decoration:none" '
       'href="%s" target="_blank" rel="noopener noreferrer">Open</a></div>' % URL)
text = text.replace(anchor, anchor.replace('\n    </div>', row + '\n    </div>'), 1)

io.open(PAGE, 'w', encoding='utf-8').write(text)
print('added the UNote row after SideCut')
