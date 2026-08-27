#!/usr/bin/env python3
"""Compute talc presence across the setting-powder corpus.

FR-6-style discipline: which products contain talc is never hand-entered --
it is computed from data/setting-powder-corpus.json on every run. The
reformulation and litigation context in data/talc.json is a separate,
hand-read file and is not touched here.

Run: python tools/analyze_talc.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "setting-powder-corpus.json"
OUT = ROOT / "data" / "talc-analysis.json"


def analyze():
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    products = corpus["products"]
    with_talc = [p["id"] for p in products if p["contains_talc"]]
    out = {
        "computed_from": "data/setting-powder-corpus.json",
        "corpus": corpus["corpus"],
        "product_count": len(products),
        "products_containing_talc": with_talc,
        "products_talc_free": [p["id"] for p in products if not p["contains_talc"]],
        "talc_free_count": sum(1 for p in products if not p["contains_talc"]),
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote %s -- %d/%d products contain talc" % (
        OUT.relative_to(ROOT), len(with_talc), len(products)))


if __name__ == "__main__":
    analyze()
