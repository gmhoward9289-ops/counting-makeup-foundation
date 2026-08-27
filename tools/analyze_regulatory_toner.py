#!/usr/bin/env python3
"""Cross the toner corpus against data/regulatory-toner.json (FR-6 for a
second category). Narrower scope than tools/analyze_regulatory.py's
foundation treatment -- see data/regulatory-toner.json's description for
what is deliberately not repeated here (a full EU Annex II general-
prohibition sweep) and why.

What this script computes from the corpus every run: each product's declared
salicylic acid concentration against the EU/US limits, and which products
declare an EU-declarable fragrance allergen by name. Run after
tools/build_corpus.py toner. Writes data/regulatory-analysis-toner.json.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "regulatory-analysis-toner.json"


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def base_inci(product):
    return [i["inci"] for i in product["base_formula"]]


def salicylic_acid_pct(active_text):
    m = re.search(r"salicylic acid[^%]*?([\d.]+)\s*%", active_text or "", re.I)
    return float(m.group(1)) if m else None


def main():
    corpus = load("corpus-toner.json")
    reg = load("regulatory-toner.json")
    products = corpus["products"]
    n = len(products)

    sa_limit = reg["salicylic_acid_limit"]
    eu_max = sa_limit["eu_max_concentration_pct_leave_on"]
    us_max = sa_limit["us_monograph_max_concentration_pct"]

    actives = []
    for p in products:
        pct = salicylic_acid_pct(p["active_ingredients_as_filed"])
        actives.append({
            "id": p["id"], "brand": p["brand"], "tier": p["price_tier"],
            "salicylic_acid_pct": pct,
            "at_us_monograph_ceiling": pct == us_max if pct is not None else None,
            "over_eu_leave_on_limit": (pct is not None and pct > eu_max),
        })
    with_sa = [a for a in actives if a["salicylic_acid_pct"] is not None]

    declarable = set(reg["fragrance_allergens"]["eu_declarable_in_corpus"])
    allergen_hits = []
    for p in products:
        found = sorted(set(base_inci(p)) & declarable)
        if found:
            allergen_hits.append({
                "id": p["id"], "brand": p["brand"], "tier": p["price_tier"],
                "allergens": found, "count": len(found),
            })
    allergen_hits.sort(key=lambda r: -r["count"])

    out = {
        "generated_from": ["corpus-toner.json", "regulatory-toner.json"],
        "products": n,
        "scope_note": reg["description"],

        "issue_16_salicylic_acid_limit": {
            "eu_max_concentration_pct_leave_on": eu_max,
            "us_monograph_max_concentration_pct": us_max,
            "eu_child_under_3_restriction": True,
            "products_declaring_salicylic_acid": len(with_sa),
            "products_at_us_monograph_ceiling": sum(1 for a in with_sa if a["at_us_monograph_ceiling"]),
            "products_over_eu_leave_on_limit": sum(1 for a in with_sa if a["over_eu_leave_on_limit"]),
            "actives": actives,
        },

        "issue_16_fragrance_allergens": {
            "eu_declarable_substances_checked": len(declarable),
            "products_declaring_eu_allergens_by_name": len(allergen_hits),
            "allergen_products": allergen_hits,
        },
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    a = main()
    s16 = a["issue_16_salicylic_acid_limit"]
    print("%d of %d products declare salicylic acid; %d sit at the US monograph's %.1f%% ceiling" % (
        s16["products_declaring_salicylic_acid"], a["products"],
        s16["products_at_us_monograph_ceiling"], s16["us_monograph_max_concentration_pct"]))
    print("EU leave-on limit: %.1f%% -- %d products over it" % (
        s16["eu_max_concentration_pct_leave_on"], s16["products_over_eu_leave_on_limit"]))
    print()
    s16b = a["issue_16_fragrance_allergens"]
    print("%d of %d products name an EU-declarable fragrance allergen (checked %d substances)" % (
        s16b["products_declaring_eu_allergens_by_name"], a["products"], s16b["eu_declarable_substances_checked"]))
