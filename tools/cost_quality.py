#!/usr/bin/env python3
"""Issue #10 (cost vs price), issue #13 (the price x quality matrix), and
issue #12 (R&D spend vs quality).

Three deliberate choices govern this file.

COST. Nobody publishes per-product manufacturing cost, so the only cost figure
with a citation behind it is company gross margin. That gives implied cost of
goods per bottle -- packaging, fill, labour, freight and overhead included --
by arithmetic on filed numbers. The ingredient cost inside that is NOT
separately knowable, so it is reported as a bound rather than a point estimate:
even a deliberately generous blended price for the whole formula mass lands far
below the retail price, and that conclusion holds across the whole band. A
precise-looking single number here would be false precision.

QUALITY. Per the project decision of 2026-08-19, quality is derived from the
filings themselves rather than from review scores. Every component below is
read off the FDA-filed label. This measures the formulation, not whether anyone
enjoys wearing it, and the site says so. Issue #12 asks whether R&D spend
correlates with quality; it reuses this exact quality proxy rather than the
review/derm-rating axis the issue names, because that axis was deliberately
rejected for this project. See data/rd-manual.json and tools/fetch_rd.py for
why R&D disclosure turned out to be even less consistent across these
companies than gross margin.
"""
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The 26 fragrance materials the EU requires to be named on a label because
# they are established contact sensitisers (EC 1223/2009 Annex III). Their
# presence is a regulator-defined fact, not an opinion about the product.
EU_DECLARED_ALLERGENS = {
    "amyl cinnamal", "benzyl alcohol", "cinnamyl alcohol", "citral", "eugenol",
    "hydroxycitronellal", "isoeugenol", "amylcinnamyl alcohol", "benzyl salicylate",
    "cinnamal", "coumarin", "geraniol", "hydroxyisohexyl 3-cyclohexene carboxaldehyde",
    "anise alcohol", "benzyl cinnamate", "farnesol", "butylphenyl methylpropional",
    "linalool", "benzyl benzoate", "citronellol", "hexyl cinnamal", "limonene",
    "methyl 2-octynoate", "alpha-isomethyl ionone", "evernia prunastri extract",
    "evernia furfuracea extract",
}

# Blended cost of the whole formula mass, USD per kg. The low end is roughly
# commodity titanium dioxide and bulk silicone fluid; the high end is several
# times that, to absorb the specialty polymers, the pigment surface treatments
# and any botanical actives. The point of the band is that the conclusion does
# not depend on where inside it the truth sits.
BLENDED_FORMULA_USD_PER_KG = (3.0, 15.0)
ASSUMED_DENSITY_G_PER_ML = 1.05

COST_ASSUMPTIONS = [
    "Formula density assumed 1.05 g/mL. Silicone-and-water foundation emulsions sit near this; it is an assumption, not a filed figure.",
    "Blended formula cost assumed $%.2f-%.2f/kg across the whole mass." % BLENDED_FORMULA_USD_PER_KG,
    "Anchors for that band: titanium dioxide traded at roughly $2.06-3.36/kg by region in April 2026 (IMARC, ChemAnalyst commodity price reporting), and bulk cosmetic-grade dimethicone is quoted in the low single dollars per kg on trade listings. Trade-listing prices are materially weaker evidence than the FDA filings this project is otherwise built on, which is exactly why the output is a band.",
    "Implied cost of goods uses the PARENT COMPANY's group gross margin, not a product-level margin. Margin varies enormously by product line, so the per-bottle figure is illustrative of the company's economics, not a measurement of this bottle.",
    "Gross margin covers packaging, filling, labour, freight, duty and factory overhead as well as ingredients. Ingredient cost is a fraction of it.",
]


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def spf_of(product_name, label_actives):
    m = re.search(r"SPF\s*(\d+)", product_name, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"SPF\s*(\d+)", label_actives or "", re.I)
    return int(m.group(1)) if m else None


def main():
    corpus = json.loads((ROOT / "data" / "corpus.json").read_text(encoding="utf-8"))
    analysis = json.loads((ROOT / "data" / "analysis.json").read_text(encoding="utf-8"))
    margins = json.loads((ROOT / "data" / "margins.json").read_text(encoding="utf-8"))
    rd = json.loads((ROOT / "data" / "rd.json").read_text(encoding="utf-8"))
    prices = json.loads((ROOT / "data" / "prices.json").read_text(encoding="utf-8"))["prices"]
    cr = {r["id"]: r for r in analysis["issue_14_complexity_rarity"]["per_product"]}

    rows = []
    for p in corpus["products"]:
        pid = p["id"]
        base = [i["inci"] for i in p["base_formula"]]
        price = prices.get(pid, {})
        margin = margins.get(p["parent_company"], {}).get("gross_margin_pct")

        # ---- quality components, all read off the filed label ----
        spf = spf_of(p["product"], p["active_ingredients_as_filed"])
        uv_actives = len(re.findall(r"\d+(?:\.\d+)?\s*%", p["active_ingredients_as_filed"] or ""))
        allergens = sorted({i for i in base if i in EU_DECLARED_ALLERGENS})
        # An active is "above the line" if it sits in the top third of the
        # declared order -- the region where the ordering rule still bites.
        heroes = cr[pid]["heroes"]
        above_line = [h for h in heroes if h["position"] / h["of"] <= 1 / 3]

        # ---- cost ----
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
                "spf_filed": spf,
                "uv_actives_declared": uv_actives,
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
            if v is not None:
                if r["price_tier"] == tier:
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
        "mean_spf": company_mean(c, ["quality", "spf_filed"]),
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
                "off the FDA-filed OTC drug label. It describes what is in the bottle "
                "and how it is arranged, not whether wearers like it. It is not a "
                "satisfaction score, a dermatological rating, or a safety verdict."),
            "components": {
                "spf_filed": "The FDA-tested SPF on the filing. A measured number, not a claim.",
                "uv_actives_declared": "How many distinct UV filters are declared as actives.",
                "named_actives_above_1pct_line": "Marketing-facing actives sitting in the top third of the declared order, where the descending-concentration rule still binds. An active below that line is present at under about 1%.",
                "eu_declared_allergens": "Count of the 26 fragrance sensitisers the EU requires to be named. Lower is better.",
                "ingredient_count": "Length of the base formula.",
            },
            "per_product": [{"id": r["id"], "brand": r["brand"],
                             "price_tier": r["price_tier"], "list_usd": r["list_usd"],
                             "price_per_ml": r["price_per_ml"], **r["quality"]} for r in rows],
            "by_tier": {t: {
                "n": sum(1 for r in rows if r["price_tier"] == t),
                "mean_price_per_ml": tier_mean(t, ["price_per_ml"]),
                "mean_spf": tier_mean(t, ["quality", "spf_filed"]),
                "mean_actives_above_line": tier_mean(t, ["quality", "named_actives_above_1pct_line"]),
                "mean_allergens": tier_mean(t, ["quality", "eu_declared_allergens"]),
                "mean_ingredient_count": tier_mean(t, ["quality", "ingredient_count"]),
            } for t in tiers},
        },
        "issue_12_rd_vs_quality": {
            "quality_definition": (
                "The same formulation-derived quality proxy as issue #13, above, "
                "averaged across each parent company's products in this corpus -- "
                "not review scores or dermatologist ratings, which this project "
                "deliberately does not use."),
            "rd_definition": (
                "Group-wide R&D expense (or, for L'Oréal, its own reported "
                "'Research & Innovation' line) as a percentage of group-wide "
                "revenue, in the most recent fiscal year each company discloses "
                "it. Company-wide, not product-line-wide: it covers R&D across "
                "every category a company sells, not just foundation."),
            "per_company": rd_rows,
        },
    }
    (ROOT / "data" / "cost-quality.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("%-32s %6s %7s %8s %9s  %s" % ("id", "list$", "$/mL", "margin%", "COGS$", "formula cost $ (band)"))
    for r in out["issue_10_cost_vs_price"]["per_product"]:
        print("%-32s %6s %7s %8s %9s  %s  (%s%% of list)" % (
            r["id"], r["list_usd"], r["price_per_ml"], r["parent_gross_margin_pct"],
            r["implied_cogs_usd"], r["estimated_formula_cost_usd"],
            "-".join(str(x) for x in (r["formula_cost_share_of_list_pct"] or []))))
    print()
    print("%-10s %3s %13s %6s %14s %10s %8s" % (
        "tier", "n", "mean $/mL", "SPF", "actives>1% line", "allergens", "length"))
    for t, v in out["issue_13_price_quality_matrix"]["by_tier"].items():
        print("%-10s %3s %13s %6s %14s %10s %8s" % (
            t, v["n"], v["mean_price_per_ml"], v["mean_spf"],
            v["mean_actives_above_line"], v["mean_allergens"], v["mean_ingredient_count"]))


if __name__ == "__main__":
    main()
