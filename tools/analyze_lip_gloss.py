#!/usr/bin/env python3
"""Derive the ingredient-comparison analysis for the lip gloss corpus.

Reuses the #9 prevalence/shared-core computation from analyze.py against
data/corpus-lip-gloss.json instead of the foundation corpus. Only that one
analysis applies here -- see data/manifest-lip-gloss.json's known_limits for
why this corpus does not support a cost/margin or R&D comparison.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from analyze import prevalence, shared_core

CORPUS = ROOT / "data" / "corpus-lip-gloss.json"
OUT = ROOT / "data" / "analysis-lip-gloss.json"


def main():
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    products = corpus["products"]
    prev_rows, counts = prevalence(products)
    out = {
        "issue_ingredient_comparison": {
            "distinct_base_ingredients": len(counts),
            "appearing_in_one_product_only": sum(1 for v in counts.values() if v == 1),
            "shared_core_75pct": sorted(shared_core(products, counts, 0.75)),
            "prevalence": prev_rows,
        },
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    i = out["issue_ingredient_comparison"]
    print("distinct base ingredients:", i["distinct_base_ingredients"])
    print("shared core (>=75%):", i["shared_core_75pct"])


if __name__ == "__main__":
    main()
