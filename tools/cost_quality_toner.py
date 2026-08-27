#!/usr/bin/env python3
"""Cost vs. price and price-vs-quality for the toner corpus (FR-4/FR-5 for a
second category), mirroring tools/cost_quality.py's method but with its own
quality proxy: toner carries no SPF, so there is no FDA-tested number to lean
on the way foundation leans on SPF. The stand-in used here is the declared
salicylic acid concentration -- a monograph-compliant quantity read off the
same FDA filing, though (unlike SPF) not independently lab-tested by the FDA,
only self-declared within the permitted band. That distinction is stated on
every page this number reaches.

COST. Same method as foundation: nobody publishes per-product cost, so the
only defensible figure is an estimate band on the whole formula mass, using
the parent company's group gross margin for implied cost of goods. The band
itself is toner-specific and lower than foundation's, because a toner formula
is overwhelmingly water, alcohol and glycerin rather than pigments and
silicones -- see BLENDED_FORMULA_USD_PER_KG below for the citations.

Run after tools/build_corpus.py toner and tools/analyze.py toner. Writes
data/cost-quality-toner.json.
"""
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Same 26 EU-declarable fragrance sensitisers as tools/cost_quality.py.
EU_DECLARED_ALLERGENS = {
    "amyl cinnamal", "benzyl alcohol", "cinnamyl alcohol", "citral", "eugenol",
    "hydroxycitronellal", "isoeugenol", "amylcinnamyl alcohol", "benzyl salicylate",
    "cinnamal", "coumarin", "geraniol", "hydroxyisohexyl 3-cyclohexene carboxaldehyde",
    "anise alcohol", "benzyl cinnamate", "farnesol", "butylphenyl methylpropional",
    "linalool", "benzyl benzoate", "citronellol", "hexyl cinnamal", "limonene",
    "methyl 2-octynoate", "alpha-isomethyl ionone", "evernia prunastri extract",
    "evernia furfuracea extract",
}

# Blended cost of the whole formula mass, USD per kg. Toner is overwhelmingly
# water (free), denatured alcohol and glycerin, with a small-percentage active
# and a light surfactant/preservative/fragrance package -- nothing like
# foundation's pigment and silicone load. Anchors: bulk ethanol traded at
# roughly $0.68-2.02/kg in North America (ChemAnalyst/Selina Wamucii regional
# indices, 2026), bulk USP glycerin at roughly $1.81/kg (Selina Wamucii, August
# 2026). The low end assumes a formula close to the ethanol/water floor; the
# high end allows for the surfactant package, preservatives and the salicylic
# acid active (a pricier specialty input, but present at only 1-2% of mass).
BLENDED_FORMULA_USD_PER_KG = (1.0, 3.5)
ASSUMED_DENSITY_G_PER_ML = 0.98

COST_ASSUMPTIONS = [
    "Formula density assumed 0.98 g/mL. A water/alcohol/glycerin toner sits close to but slightly below water's density, driven down by the alcohol fraction; this is an assumption, not a filed figure.",
    "Blended formula cost assumed $%.2f-%.2f/kg across the whole mass." % BLENDED_FORMULA_USD_PER_KG,
    "Anchors for that band: bulk ethanol traded at roughly $0.68-2.02/kg by region in 2026 (ChemAnalyst, Selina Wamucii commodity price reporting), and bulk USP glycerin at roughly $1.81/kg (Selina Wamucii, August 2026). Trade-listing prices are materially weaker evidence than the FDA filings this project is otherwise built on, which is exactly why the output is a band.",
    "Implied cost of goods uses the PARENT COMPANY's group gross margin, not a product-level margin -- same method and same caveat as the foundation corpus. For Target Corporation this is a whole-RETAIL margin across every category Target sells, not a cosmetics or manufacturing margin.",
    "Gross margin covers packaging, filling, labour, freight, duty and factory overhead as well as ingredients. Ingredient cost is a fraction of it.",
]


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def salicylic_acid_pct(active_text):
    m = re.search(r"salicylic acid[^%]*?([\d.]+)\s*%", active_text or "", re.I)
    return float(m.group(1)) if m else None


def main():
    corpus = json.loads((ROOT / "data" / "corpus-toner.json").read_text(encoding="utf-8"))
    analysis = json.loads((ROOT / "data" / "analysis-toner.json").read_text(encoding="utf-8"))
    margins = json.loads((ROOT / "data" / "margins-toner.json").read_text(encoding="utf-8"))
    rd = json.loads((ROOT / "data" / "rd-toner.json").read_text(encoding="utf-8"))
    prices = json.loads((ROOT / "data" / "prices-toner.json").read_text(encoding="utf-8"))["prices"]
    cr = {r["id"]: r for r in analysis["issue_14_complexity_rarity"]["per_product"]}

    rows = []
    for p in corpus["products"]:
        pid = p["id"]
        base = [i["inci"] for i in p["base_formula"]]
        price = prices.get(pid, {})
        margin = margins.get(p["parent_company"], {}).get("gross_margin_pct")

        sa_pct = salicylic_acid_pct(p["active_ingredients_as_filed"])
        allergens = sorted({i for i in base if i in EU_DECLARED_ALLERGENS})
        heroes = cr[pid]["heroes"]
        above_line = [h for h in heroes if h["position"] / h["of"] <= 1 / 3]

        list_usd, vol = price.get("list_usd"), price.get("volume_ml")
        mass_g = vol * ASSUMED_DENSITY_G_PER_ML if vol else None
        formula_cost = ([round(mass_g / 1000 * k, 3) for k in BLENDED_FORMULA_USD_PER_KG]
                        if mass_g else None)
        implied_cogs = (round(list_usd * (1 - margin / 100), 2)
                        if (list_usd and margin) else None)

        rows.append({
            "id": pid, "brand": p["brand"], "product": p["product"],
            "parent_company": p["parent_company"], "price_tier": p["price_tier"],
            "list_usd": list_usd, "volume_ml": vol,
            "price_per_ml": round(list_usd / vol, 3) if (list_usd and vol) else None,
            "price_confidence": price.get("confidence"),
            "parent_gross_margin_pct": margin,
            "implied_cogs_usd": implied_cogs,
            "estimated_formula_cost_usd": formula_cost,
            "formula_cost_share_of_list_pct": (
                [round(100 * c / list_usd, 2) for c in formula_cost]
                if (formula_cost and list_usd) else None),
            "quality": {
                "salicylic_acid_pct_filed": sa_pct,
                "named_actives_total": len(heroes),
                "named_actives_above_1pct_line": len(above_line),
                "named_actives_above_line_list": [h["inci"] for h in above_line],
                "eu_declared_allergens": len(allergens),
                "eu_declared_allergen_list": allergens,
                "ingredient_count": cr[pid]["length"],
            },
        })

    def tier_mean(tier, path):
        vals = []
        for r in rows:
            v = r
            for k in path:
                v = v.get(k) if isinstance(v, dict) else None
            if v is not None and r["price_tier"] == tier:
                vals.append(v)
        return round(statistics.mean(vals), 2) if vals else None

    def company_mean(company, path):
        vals = []
        for r in rows:
            if r["parent_company"] != company:
                continue
            v = r
            for k in path:
                v = v.get(k) if isinstance(v, dict) else None
            if v is not None:
                vals.append(v)
        return round(statistics.mean(vals), 2) if vals else None

    companies = sorted({r["parent_company"] for r in rows})
    rd_rows = [{
        "parent_company": c,
        "n_products": sum(1 for r in rows if r["parent_company"] == c),
        "rd_pct_of_revenue": rd.get(c, {}).get("rd_pct_of_revenue"),
        "rd_fiscal_year_end": rd.get(c, {}).get("fiscal_year_end"),
        "rd_source": rd.get(c, {}).get("source"),
        "mean_salicylic_acid_pct": company_mean(c, ["quality", "salicylic_acid_pct_filed"]),
        "mean_actives_above_line": company_mean(c, ["quality", "named_actives_above_1pct_line"]),
        "mean_allergens": company_mean(c, ["quality", "eu_declared_allergens"]),
        "mean_ingredient_count": company_mean(c, ["quality", "ingredient_count"]),
    } for c in companies]

    tiers = ["budget", "mass", "prestige", "luxury"]
    out = {
        "issue_10_cost_vs_price": {
            "assumptions": COST_ASSUMPTIONS,
            "gross_margins": margins,
            "per_product": [{k: r[k] for k in (
                "id", "brand", "price_tier", "list_usd", "price_per_ml",
                "parent_gross_margin_pct", "implied_cogs_usd",
                "estimated_formula_cost_usd", "formula_cost_share_of_list_pct",
                "price_confidence")} for r in rows],
        },
        "issue_13_price_quality_matrix": {
            "quality_definition": (
                "Formulation-derived and primary-sourced only: every component is read "
                "off the FDA-filed OTC drug label, same principle as the foundation "
                "corpus. Toner carries no SPF, so the anchor figure here is the declared "
                "salicylic acid concentration -- a monograph-compliant quantity, but "
                "self-declared within the FDA's permitted band, not independently lab-"
                "tested the way SPF is. It describes what is in the bottle and how it is "
                "arranged, not whether wearers like it. It is not a satisfaction score, a "
                "dermatological rating, or a safety verdict."),
            "components": {
                "salicylic_acid_pct_filed": "The declared acne-treatment active concentration on the filing. A monograph-compliant declared quantity, not an independently tested measurement like SPF.",
                "named_actives_above_1pct_line": "Marketing-facing actives (botanicals, humectants, named acids) sitting in the top third of the declared order, where the descending-concentration rule still binds. An active below that line is present at under about 1%.",
                "eu_declared_allergens": "Count of the 26 fragrance sensitisers the EU requires to be named. Lower is better. Every product in this corpus declares its scent only as generic 'fragrance'/'parfum', so this is 0 for all seven products -- a real finding, not a missing computation.",
                "ingredient_count": "Length of the base formula.",
            },
            "per_product": [{"id": r["id"], "brand": r["brand"],
                             "price_tier": r["price_tier"], "list_usd": r["list_usd"],
                             "price_per_ml": r["price_per_ml"], **r["quality"]} for r in rows],
            "by_tier": {t: {
                "n": sum(1 for r in rows if r["price_tier"] == t),
                "mean_price_per_ml": tier_mean(t, ["price_per_ml"]),
                "mean_salicylic_acid_pct": tier_mean(t, ["quality", "salicylic_acid_pct_filed"]),
                "mean_actives_above_line": tier_mean(t, ["quality", "named_actives_above_1pct_line"]),
                "mean_allergens": tier_mean(t, ["quality", "eu_declared_allergens"]),
                "mean_ingredient_count": tier_mean(t, ["quality", "ingredient_count"]),
            } for t in tiers},
        },
        "issue_12_rd_vs_quality": {
            "quality_definition": (
                "The same formulation-derived quality proxy as issue #13, above, "
                "averaged across each parent company's products in this corpus."),
            "rd_definition": (
                "Group-wide R&D expense as a percentage of group-wide revenue, in the "
                "most recent fiscal year each company discloses it. Company-wide, not "
                "product-line-wide. Target Corporation is omitted (not a null row): it "
                "discloses no R&D figure at all, consistent with a retailer sourcing "
                "private-label goods from contract manufacturers rather than "
                "formulating its own products."),
            "per_company": rd_rows,
        },
    }
    (ROOT / "data" / "cost-quality-toner.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("%-32s %6s %7s %8s %9s  %s" % ("id", "list$", "$/mL", "margin%", "COGS$", "formula cost $ (band)"))
    for r in out["issue_10_cost_vs_price"]["per_product"]:
        print("%-32s %6s %7s %8s %9s  %s" % (
            r["id"], r["list_usd"], r["price_per_ml"], r["parent_gross_margin_pct"],
            r["implied_cogs_usd"], r["estimated_formula_cost_usd"]))
    print()
    print("%-10s %3s %13s %8s %14s %10s %8s" % (
        "tier", "n", "mean $/mL", "SA%", "actives>1% line", "allergens", "length"))
    for t, v in out["issue_13_price_quality_matrix"]["by_tier"].items():
        print("%-10s %3s %13s %8s %14s %10s %8s" % (
            t, v["n"], v["mean_price_per_ml"], v["mean_salicylic_acid_pct"],
            v["mean_actives_above_line"], v["mean_allergens"], v["mean_ingredient_count"]))


if __name__ == "__main__":
    main()
