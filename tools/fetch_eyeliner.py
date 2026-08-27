#!/usr/bin/env python3
"""Archive brand-page ingredient declarations for the eyeliner corpus.

Eyeliner carries no SPF claim, so there is no DailyMed-equivalent government
filing to fetch (see fetch_dailymed.py for the foundation corpus, which has
one). The primary source here is each manufacturer's own product page instead.

This script re-fetches the plain HTTP response for each product in
data/manifest-eyeliner.json and saves it to data/raw-eyeliner/<id>.raw.html,
for reproducibility on the brands whose ingredient panel is present in the
static response. Four of the eight brand pages (e.l.f., MAC, Lancome, Dior)
render the Ingredients panel client-side or block a plain fetch (HTTP 403);
for those, this script can only confirm the block, not recover the panel. The
ingredient text actually used by build_corpus_eyeliner.py lives in the
hand-verified data/raw-eyeliner/<id>.txt snapshot for every product (read from
the rendered page in a browser where a static fetch fails), not in the
.raw.html this script writes -- the .txt is the archived source of truth,
declared as such in data/manifest-eyeliner.json's known_limits.
"""
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw-eyeliner"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; counting-makeup-foundation research)"}


def fetch(product):
    req = urllib.request.Request(product["url"], headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        print("%-30s HTTP %s (blocked -- see %s.txt for the browser-verified snapshot)" % (
            product["id"], e.code, product["id"]))
        return
    except urllib.error.URLError as e:
        print("%-30s fetch failed: %s" % (product["id"], e.reason))
        return
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / ("%s.raw.html" % product["id"])
    out.write_bytes(body)
    print("%-30s wrote %s (%d bytes)" % (product["id"], out.name, len(body)))


def main():
    manifest = json.loads((ROOT / "data" / "manifest-eyeliner.json").read_text(encoding="utf-8"))
    for product in manifest["products"]:
        fetch(product)


if __name__ == "__main__":
    main()
