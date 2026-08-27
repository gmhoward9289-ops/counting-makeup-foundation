#!/usr/bin/env python3
"""Parse brand-page ingredient declarations into the normalized eyeliner corpus.

Input : data/manifest-eyeliner.json + data/raw-eyeliner/<id>.txt (see
        fetch_eyeliner.py and manifest-eyeliner.json's known_limits for why the
        .txt snapshot, not the .raw.html, is the archived source of truth).
Output: data/corpus-eyeliner.json

Same two rules as build_corpus.py (foundation): the verbatim declaration is
preserved on every product, and every correction is declared in
SPELLING_FIXES/SYNONYMS below and reported per-product. No silent edits.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw-eyeliner"

sys.path.insert(0, str(ROOT / "tools"))
from build_corpus import MAY_CONTAIN, clean_token, split_list, canonical_colorant

# Brand pages are cleaner than FDA filings (no typos found across the eight),
# so this stays empty for now -- kept as a named, inspectable table rather than
# removed, so a future correction has a declared place to go rather than being
# made silently in split_list/clean_token.
SPELLING_FIXES = {}

# House-style differences in how the same substance is written across brands.
SYNONYMS = {
    "aqua/water/eau": "water", "aqua (water)": "water", "water (aqua)": "water",
    "aqua": "water", "eau": "water",
    "beeswax/cera alba": "cera alba", "cera alba/beeswax": "cera alba",
    "cera microcristallina/microcrystalline wax": "microcrystalline wax",
    "copernicia cerifera cera/carnauba wax": "copernicia cerifera (carnauba) wax",
    "copernicia cerifera (carnauba) wax": "copernicia cerifera (carnauba) wax",
    "ci 77266 [nano]/black 2": "black 2 (ci 77266) [nano]",
    "black 2 [nano]": "black 2 (ci 77266) [nano]",
    "black 2 (ci 77266) [nano]": "black 2 (ci 77266) [nano]",
    "ci 77266 [nano] (black 2)": "black 2 (ci 77266) [nano]",
}


def normalize(name):
    key = name.lower().strip()
    fixed = SPELLING_FIXES.get(key, key)
    colorant = canonical_colorant(fixed)
    canon = SYNONYMS.get(colorant, colorant)
    return canon, (fixed != key), (canon != fixed)


def parse_snapshot(text):
    """Split a data/raw-eyeliner/<id>.txt snapshot into metadata + ingredient blocks."""
    meta = {}
    for line in text.splitlines():
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m and m.group(1) in ("id", "brand", "product", "parent", "tier", "url", "accessed"):
            meta[m.group(1)] = m.group(2).strip()
        if line.strip() == "INGREDIENTS:":
            break
    ing_m = re.search(r"^INGREDIENTS:\s*\n(.*?)(?:\n\nMAY CONTAIN:\s*\n(.*?))?\s*$",
                       text, re.S | re.M)
    base_raw = ing_m.group(1).strip() if ing_m else ""
    mc_raw = (ing_m.group(2) or "").strip() if ing_m else ""
    return meta, base_raw, mc_raw


# A bare digit-comma-digit ("1,2-Hexanediol") is part of one INCI name, not a
# list separator -- split_list's paren-depth guard doesn't cover it, since the
# comma isn't inside parentheses. Protect it before splitting, restore after.
NUMERIC_COMMA = re.compile(r"(?<=\d),(?=\d)")


def parse_product(entry):
    snap_path = RAW / ("%s.txt" % entry["id"])
    meta, base_raw, mc_raw = parse_snapshot(snap_path.read_text(encoding="utf-8"))

    corrections, synonym_hits = [], []
    def build(text):
        protected = NUMERIC_COMMA.sub("⁣", text)
        out = []
        for pos, tok in enumerate((t.replace("⁣", ",") for t in split_list(protected)), 1):
            canon, was_typo, was_syn = normalize(tok)
            if was_typo:
                corrections.append({"as_filed": tok, "read_as": canon})
            if was_syn:
                synonym_hits.append({"as_filed": tok, "canonical": canon})
            out.append({"position": pos, "as_filed": tok, "inci": canon})
        return out

    return {
        "id": entry["id"],
        "brand": entry["brand"],
        "product": entry["product"],
        "parent_company": entry["parent"],
        "price_tier": entry["tier"],
        "source": {
            "type": "Manufacturer's own product page (INCI declaration, FPLA labeling)",
            "publisher": entry["brand"],
            "url": entry["url"],
            "accessed_date": meta.get("accessed", "2026-08-26"),
        },
        "ingredients_as_listed": base_raw,
        "may_contain_as_listed": mc_raw,
        "base_formula": build(base_raw),
        "may_contain": build(mc_raw),
        "label_corrections": corrections,
        "synonyms_collapsed": synonym_hits,
    }


def main():
    manifest = json.loads((ROOT / "data" / "manifest-eyeliner.json").read_text(encoding="utf-8"))
    products = [parse_product(p) for p in manifest["products"]]
    out = {
        "corpus": manifest["corpus"],
        "description": manifest["description"],
        "inclusion_criteria": manifest["inclusion_criteria"],
        "known_limits": manifest["known_limits"],
        "retrieved": "2026-08-26",
        "products": products,
    }
    (ROOT / "data" / "corpus-eyeliner.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for p in products:
        print("%-28s base=%2d  +/-=%2d  fixes=%d" % (
            p["id"], len(p["base_formula"]), len(p["may_contain"]), len(p["label_corrections"])))


if __name__ == "__main__":
    main()
