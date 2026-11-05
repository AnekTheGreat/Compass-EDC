"""One-shot: stop MeasureT being signed with SideCut's key. Applied on CI where the files are.

Every step is anchored and asserted, so a file that is not the shape this script expects stops the
run before anything is written. Deleted by the runner that calls it.
"""
import re, subprocess, sys

WF = ".github/workflows/android-build.yml"
SIGN = ".github/workflows/patch-signing.py"
PIN = ".github/workflows/upload-cert-sha256.txt"


def read(p):
    return open(p, encoding="utf-8").read()


def write(p, s):
    open(p, "w", encoding="utf-8").write(s)


def rep(path, old, new, count=1):
    s = read(path)
    n = s.count(old)
    if n != count:
        sys.exit("%s: expected %d of %r, found %d" % (path, count, old[:70], n))
    write(path, s.replace(old, new, count))


# ---- 1. the pin is MeasureT's own upload certificate, not one taken from another app ----
#
# .well-known/assetlinks.json declares the certificate for com.CompassEDC.myapp; that is the key
# this app is signed with, and it is what the build must hold. The digest that was pinned here
# belongs to a different app's keystore, which is how a green run could sign MeasureT with SideCut's
# key and still say the certificate matched.

OWN = "0ea5ff565a8284fdfd489b05b052fb560427ed35fbb4fddce44cbf72acba6ba1"
links = read(".well-known/assetlinks.json")
if "com.CompassEDC.myapp" not in links:
    sys.exit("assetlinks.json no longer declares this app's package")
declared = "".join(re.findall(r'"sha256_cert_fingerprints"\s*:\s*\[\s*"([^"]+)"', links))
declared = declared.replace(":", "").lower()
if declared != OWN:
    sys.exit("assetlinks.json declares %r, which is not the certificate this script was written for"
             % declared)
old_pin = read(PIN).strip()
if old_pin == OWN:
    sys.exit("the pin is already MeasureT's own certificate - this has already run")
write(PIN, OWN + "\n")
if read(PIN).strip() != OWN:
    sys.exit("the pin did not land")

# ---- 2. the build reads MeasureT's own secrets, which SideCut's build does not share ----

rep(WF,
    """      # Repository secrets holding the upload keystore. With them, the release AAB and APK
      # are signed with the real key. Without them the build still runs, but the signing
      # step below fails the run rather than hand over a bundle Play will not accept.
      ANDROID_KEYSTORE_BASE64: ${{ secrets.ANDROID_KEYSTORE_BASE64 }}
      ANDROID_KEYSTORE_PASSWORD: ${{ secrets.ANDROID_KEYSTORE_PASSWORD }}
      ANDROID_KEY_PASSWORD: ${{ secrets.ANDROID_KEY_PASSWORD }}
      ANDROID_KEY_ALIAS: ${{ secrets.ANDROID_KEY_ALIAS }}""",
    """      # MeasureT's OWN upload keystore, under names no other app uses. They were called
      # ANDROID_KEYSTORE_* - the same four names SideCut's workflow reads - so the keystore sitting
      # in one repository's secrets could be the other's, and MeasureT was in fact being signed with
      # SideCut's key. The names are prefixed now so that cannot happen by accident: these four
      # hold MeasureT's key or nothing. Without them the build still runs, and the signing checks
      # below fail the run rather than hand over a bundle Play will not accept.
      MEASURET_KEYSTORE_BASE64: ${{ secrets.MEASURET_KEYSTORE_BASE64 }}
      MEASURET_KEYSTORE_PASSWORD: ${{ secrets.MEASURET_KEYSTORE_PASSWORD }}
      MEASURET_KEY_PASSWORD: ${{ secrets.MEASURET_KEY_PASSWORD }}
      MEASURET_KEY_ALIAS: ${{ secrets.MEASURET_KEY_ALIAS }}""")

rep(WF, "if: env.ANDROID_KEYSTORE_BASE64 != ''", "if: env.MEASURET_KEYSTORE_BASE64 != ''", 2)
rep(WF, 'if [ -n "$ANDROID_KEYSTORE_BASE64" ]; then', 'if [ -n "$MEASURET_KEYSTORE_BASE64" ]; then')

OLD_CONFIRM = read(WF)[read(WF).index("      # Without the keystore the release AAB is unsigned"):
                       read(WF).index("      - name: Upload the APKs and the AABs")]
NEW_CONFIRM = """      # The keystore is checked before the build; this checks the artifact that came out of it, so
      # a signing config that silently did nothing cannot pass as a signed bundle. The digest is
      # MeasureT's own upload certificate - the one .well-known/assetlinks.json declares - so an
      # APK signed with any other app's key (SideCut's included) fails here.
      - name: Confirm the release files are signed with MeasureT's upload key
        run: |
          set -e
          V="${{ steps.dist.outputs.version }}"
          PIN="$(tr -d ':\\n\\r ' < .github/workflows/upload-cert-sha256.txt | tr 'A-F' 'a-f')"
          SDK="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-/usr/local/lib/android/sdk}}"
          APKSIGNER="$(find "$SDK/build-tools" -maxdepth 2 -type f -name apksigner 2>/dev/null | sort -V | tail -n 1)"
          if [ ! -f "dist/MeasureT-$V-release.apk" ]; then
            echo "::error::no signed release APK in dist — set MEASURET_KEYSTORE_BASE64, MEASURET_KEYSTORE_PASSWORD, MEASURET_KEY_PASSWORD and MEASURET_KEY_ALIAS to MeasureT's own upload key (the ANDROID_KEYSTORE_* secrets belong to SideCut)"
            ls -l dist
            exit 1
          fi
          if [ -z "$APKSIGNER" ]; then
            echo "::error::apksigner not found under $SDK/build-tools"
            exit 1
          fi
          echo "--- certificate on MeasureT-$V-release.apk ---"
          "$APKSIGNER" verify --print-certs "dist/MeasureT-$V-release.apk" | sed -n '1,12p'
          GOT="$("$APKSIGNER" verify --print-certs "dist/MeasureT-$V-release.apk" | sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | head -n 1 | tr -d ':' | tr 'A-F' 'a-f')"
          echo "apk certificate sha256: $GOT"
          echo "MeasureT's upload certificate: $PIN"
          if [ -z "$GOT" ]; then
            echo "::error::could not read the certificate out of the built APK"
            exit 1
          fi
          if [ "$GOT" != "$PIN" ]; then
            echo "::error::this APK is not signed with MeasureT's upload key — the four MEASURET_KEYSTORE/MEASURET_KEY secrets must hold MeasureT's own keystore"
            exit 1
          fi
          echo "--- signature on MeasureT-$V-release.aab ---"
          jarsigner -verify -verbose:summary "dist/MeasureT-$V-release.aab" | tail -n 3

"""
write(WF, read(WF).replace(OLD_CONFIRM, NEW_CONFIRM, 1))
if "MeasureT's upload key" not in read(WF):
    sys.exit("the artifact check did not land")

# ---- 3. the signer script reads those names, and says which ones when they are wrong ----

rep(SIGN,
    """    encoded = require('ANDROID_KEYSTORE_BASE64')
    store_pass = require('ANDROID_KEYSTORE_PASSWORD')
    key_pass = os.environ.get('ANDROID_KEY_PASSWORD', '').strip() or store_pass
    alias = require('ANDROID_KEY_ALIAS')""",
    """    encoded = require('MEASURET_KEYSTORE_BASE64')
    store_pass = require('MEASURET_KEYSTORE_PASSWORD')
    key_pass = os.environ.get('MEASURET_KEY_PASSWORD', '').strip() or store_pass
    alias = require('MEASURET_KEY_ALIAS')""")

rep(SIGN,
    """        sys.exit('FATAL: ANDROID_KEYSTORE_BASE64 is not valid base64: %s' % exc)""",
    """        sys.exit('FATAL: MEASURET_KEYSTORE_BASE64 is not valid base64: %s' % exc)""")

rep(SIGN,
    """        sys.exit('FATAL: this keystore is not MeasureT\\'s upload key (it holds %s, the upload '
                 'certificate is %s), so Play would reject the AAB. Point the four ANDROID_* '
                 'secrets at MeasureT\\'s own keystore.' % (actual, expected))""",
    """        sys.exit('FATAL: this keystore is not MeasureT\\'s upload key (it holds %s, the upload '
                 'certificate is %s), so Play would reject the AAB. The ANDROID_KEYSTORE_* secrets '
                 'are SideCut\\'s; MeasureT\\'s own key belongs in MEASURET_KEYSTORE_BASE64, '
                 'MEASURET_KEYSTORE_PASSWORD, MEASURET_KEY_PASSWORD and MEASURET_KEY_ALIAS.'
                 % (actual, expected))""")

rep(SIGN,
    """def require(name):
    value = os.environ.get(name, '').strip()
    if not value:
        sys.exit('FATAL: %s is empty — set the repository secret or drop it from the job.' % name)""",
    """def require(name):
    value = os.environ.get(name, '').strip()
    if not value:
        sys.exit('FATAL: %s is empty — set that repository secret to MeasureT\\'s own upload key, '
                 'or drop the signing steps from the job.' % name)""")

# ---- 4. everything still parses, and the secrets the workflow reads are the ones the script wants ----

try:
    import yaml
except ImportError:
    yaml = None
wf = read(WF)
if yaml is not None:
    doc = yaml.safe_load(wf)
    if "jobs" not in doc:
        sys.exit("the workflow no longer parses into jobs")
else:
    print("PyYAML is not here; the workflow was not parsed as YAML")

# Only real reads count: the failure messages name SideCut's secrets on purpose, to say where the
# keystore went wrong.
for bad in ("secrets.ANDROID_KEY", "env.ANDROID_KEY", "$ANDROID_KEY"):
    for where, text in ((WF, wf), (SIGN, read(SIGN))):
        if bad in text:
            sys.exit("%s still reads SideCut's secret through %s" % (where, bad))

try:
    compile(read(SIGN), SIGN, "exec")
except SyntaxError as exc:
    sys.exit("%s does not parse: %s" % (SIGN, exc))

for name in ("MEASURET_KEYSTORE_BASE64", "MEASURET_KEYSTORE_PASSWORD",
             "MEASURET_KEY_PASSWORD", "MEASURET_KEY_ALIAS"):
    if name not in read(SIGN) or name not in wf:
        sys.exit("%s is missing from the workflow or the signer" % name)

print("MeasureT signing fixed: the pin is MeasureT's own certificate (%s), the build reads "
      "MEASURET_* secrets, and the built APK is checked against the pin" % OWN[:16])
