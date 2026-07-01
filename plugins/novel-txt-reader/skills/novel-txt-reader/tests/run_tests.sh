#!/usr/bin/env bash
# Build synthetic books in several encodings/formats and verify the generated
# reader headlessly (chapters load, no 乱码, bookmarks + auto-resume work).
# Requires: python3, node, and `npm install jsdom`.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
echo "workdir: $WORK"

python3 "$ROOT/tests/make_samples.py" "$WORK/samples"
cp "$ROOT/examples/sample.txt" "$WORK/samples/sample.txt"

fail=0
for f in "$WORK"/samples/*.txt; do
  name="$(basename "$f" .txt)"
  python3 "$ROOT/scripts/build_reader.py" "$f" "$WORK/out/$name" >/dev/null
  node "$ROOT/tests/test_reader.js" "$WORK/out/$name" "$name" || fail=1
done

echo ""
echo "=== extra: 'tricky' must have NO false 番外 (外传 only mid-sentence) ==="
python3 - "$WORK/out/tricky/data/catalog.js" << 'PY'
import sys, json
t=open(sys.argv[1],encoding='utf-8').read()
c=json.loads(t[t.index('=')+1:].rstrip(';'))
fw=[e['t'] for e in c['entries'] if e['v']=='番外']
assert not fw, f"unexpected 番外 entries: {fw}"
assert len(c['entries'])==2, f"expected 2 chapters, got {len(c['entries'])}"
print("  OK: no false 番外, 2 chapters")
PY

echo ""
[ "$fail" -eq 0 ] && echo "ALL TESTS PASSED" || { echo "SOME TESTS FAILED"; exit 1; }
