#!/usr/bin/env python3
"""Derive the eyeliner ingredient-comparison analysis from data/corpus-eyeliner.json.

Mirrors analyze.py's issue-9 computation (what's shared, what differs) for the
eyeliner corpus. This pass covers the ingredients study only -- see the plan
for why ownership/complexity/price etc. are out of scope for eyeliner for now.
Everything here is computed from the corpus; no figure is entered by hand.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus-eyeliner.json"
OUT = ROOT / "data" / "analysis-eyeliner.json"


def load():
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def base(p):
    return [i["inci"] for i in p["base_formula"]]


def prevalence(products):
    n = len(products)
    counts = {}
    for p in products:
        for ing in set(base(p)):
            counts[ing] = counts.get(ing, 0) + 1
    rows = [{"inci": k, "products": v, "share": round(v / n, 3)}
            for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    return rows, counts


def shared_core(products, counts, threshold=0.75):
    n = len(products)
    return [r for r in counts if counts[r] / n >= threshold]


def main():
    c = load()
    products = c["products"]
    prev_rows, counts = prevalence(products)

    analysis = {
        "generated_from": "data/corpus-eyeliner.json",
        "n_products": len(products),
        "issue_9_ingredient_comparison": {
            "distinct_base_ingredients": len(counts),
            "appearing_in_one_product_only": sum(1 for v in counts.values() if v == 1),
            "shared_core_75pct": sorted(shared_core(products, counts, 0.75)),
            "prevalence": prev_rows,
        },
    }
    OUT.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    return analysis


if __name__ == "__main__":
    a = main()
    i9 = a["issue_9_ingredient_comparison"]
    print("distinct base ingredients:", i9["distinct_base_ingredients"])
    print("appearing in one product only:", i9["appearing_in_one_product_only"])
    print("shared core (>=75%):", i9["shared_core_75pct"])
