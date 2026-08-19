#!/usr/bin/env python3
"""Cross the corpus against the regulatory and sourcing datasets.

Issues #16 (FDA-allowed vs internationally banned), #17 (sourcing claims) and
#18 (MoCRA timeline).

data/regulatory.json and data/sourcing.json hold facts read out of primary legal
texts by hand, each carrying its own source block -- the same arrangement as
data/margins-manual.json, and for the same reason: a consolidated regulation is
not machine-fetchable from here, so the reading is recorded once, with its
provenance, rather than re-derived unreliably on every run.

What this script does is the part that must not be hand-entered: which products
in the corpus are actually touched by each rule, and how many. Those counts are
computed from the FDA filings every time.

Run after tools/build_corpus.py. Writes data/regulatory-analysis.json.
"""
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "regulatory-analysis.json"

# As-of date for "is this rule in force yet". Passed through to the output so a
# page rendered from it can say what it was measured against.
TODAY = date(2026, 8, 19)

# The three cyclic siloxanes restricted by REACH entry 70. Matching is on the
# INCI name as filed; D4 (cyclotetrasiloxane) does not appear in this corpus.
SILOXANE_INCI = {
    "cyclopentasiloxane": "D5",
    "cyclohexasiloxane": "D6",
    "cyclotetrasiloxane": "D4",
}

# Active-ingredient declarations are free text on the SPL, so the percentages
# are parsed rather than looked up.
ACTIVE_RE = re.compile(
    r"(octinoxate|octisalate|ensulizole|titanium dioxide|zinc oxide|avobenzone|"
    r"homosalate|oxybenzone|octocrylene)(?:\s*\(nano\))?\s*:?\s*([\d.]+)\s*%",
    re.I)


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def base_inci(product):
    return [i["inci"] for i in product["base_formula"]]


def may_contain_inci(product):
    return [i["inci"] for i in (product.get("may_contain") or [])]


def parse_actives(product):
    """Pull (filter, percent) pairs out of the filed active-ingredient string."""
    txt = product.get("active_ingredients_as_filed") or ""
    out = []
    for m in ACTIVE_RE.finditer(txt):
        out.append({"filter": m.group(1).lower(), "pct": float(m.group(2))})
    return out


def main():
    corpus = load("corpus.json")
    reg = load("regulatory.json")
    src = load("sourcing.json")
    products = corpus["products"]
    n = len(products)

    # ---------------------------------------------------------------- #16
    # Which products carry a siloxane the EU restricts in leave-on products
    # from 2027-06-06. A foundation is a leave-on product.
    silo_date = date.fromisoformat(
        next(d["applies_after"] for d in reg["siloxanes"]["dates"]
             if "other than wash-off" in d["scope"]))
    siloxane_hits = []
    for p in products:
        found = [(i, SILOXANE_INCI[i]) for i in base_inci(p) if i in SILOXANE_INCI]
        if found:
            siloxane_hits.append({
                "id": p["id"], "brand": p["brand"], "product": p["product"],
                "tier": p["price_tier"],
                "siloxanes": [{"inci": i, "designation": d} for i, d in found],
                "position": [p["base_formula"][base_inci(p).index(i)]["position"]
                             for i, _ in found],
            })

    # EU-declarable fragrance allergens present in the corpus. These appear on a
    # US filing only because the manufacturer runs one global formula and one
    # global ingredient list -- no US rule requires them.
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

    # UV filters as filed, against the EU concentration ceiling for octinoxate.
    eu_octi_max = reg["octinoxate_limit"]["eu_max_concentration_pct"]
    actives = []
    for p in products:
        parsed = parse_actives(p)
        octi = next((a["pct"] for a in parsed if a["filter"] == "octinoxate"), None)
        actives.append({
            "id": p["id"], "brand": p["brand"], "tier": p["price_tier"],
            "filters": parsed,
            "octinoxate_pct": octi,
            "octinoxate_over_eu_limit": (octi is not None and octi > eu_octi_max),
        })
    with_octi = [a for a in actives if a["octinoxate_pct"] is not None]

    # ---------------------------------------------------------------- #17
    palm = set(src["palm_derivable_ingredients"]["inci"])
    palm_rows = []
    for p in products:
        found = sorted(set(base_inci(p)) & palm)
        palm_rows.append({
            "id": p["id"], "brand": p["brand"], "tier": p["price_tier"],
            "parent": p["parent_company"],
            "palm_derivable": found, "count": len(found),
            "formula_length": len(p["base_formula"]),
            "share_of_formula": round(len(found) / len(p["base_formula"]), 4),
        })
    palm_rows.sort(key=lambda r: -r["count"])

    natural_mica = [p["id"] for p in products
                    if any("mica" in i and "fluorphlogopite" not in i
                           for i in may_contain_inci(p) + base_inci(p))]
    synthetic_mica = [p["id"] for p in products
                      if "synthetic fluorphlogopite" in base_inci(p)]
    talc = [p["id"] for p in products if "talc" in base_inci(p)]

    acop = src["loreal_acop_2023"]
    cert = acop["certified_by_model_tonnes"]
    cert_total = sum(cert.values())
    physically_separated = cert["identity_preserved"] + cert["segregated"]

    # ---------------------------------------------------------------- #18
    reqs = reg["mocra"]["requirements"]
    overdue = []
    for r in reqs:
        if r["status"] in ("not issued", "withdrawn"):
            d = date.fromisoformat(r["statutory_deadline"])
            overdue.append({
                "id": r["id"], "requirement": r["requirement"],
                "statutory_deadline": r["statutory_deadline"],
                "status": r["status"],
                "days_past_deadline": (TODAY - d).days,
                "months_past_deadline": round((TODAY - d).days / 30.44, 1),
            })
    overdue.sort(key=lambda r: -r["days_past_deadline"])

    out = {
        "generated_from": ["corpus.json", "regulatory.json", "sourcing.json"],
        "as_of": TODAY.isoformat(),
        "products": n,

        "issue_16_banned_ingredients": {
            "corpus_ingredients_tested": reg["corpus_ingredients_on_eu_prohibited_list"]["tested"],
            "eu_prohibited_entries": reg["eu_prohibited_substances"]["count"],
            "us_prohibited_entries": reg["us_prohibited_substances"]["count"],
            "corpus_ingredients_prohibited_in_eu": reg["corpus_ingredients_on_eu_prohibited_list"]["genuine_matches"],
            "eu_uv_filters": reg["uv_filters"]["eu_permitted_count"],
            "us_uv_filters": reg["uv_filters"]["us_permitted_count"],
            "siloxane_restriction_applies_from": silo_date.isoformat(),
            "siloxane_restriction_in_force": TODAY >= silo_date,
            "days_until_siloxane_restriction": (silo_date - TODAY).days,
            "products_affected_by_siloxane_restriction": len(siloxane_hits),
            "siloxane_products": siloxane_hits,
            "products_declaring_eu_allergens": len(allergen_hits),
            "allergen_products": allergen_hits,
            "products_declaring_octinoxate": len(with_octi),
            "octinoxate_max_declared_pct": max((a["octinoxate_pct"] for a in with_octi), default=None),
            "octinoxate_eu_limit_pct": eu_octi_max,
            "products_over_eu_octinoxate_limit": sum(1 for a in actives if a["octinoxate_over_eu_limit"]),
            "actives": actives,
        },

        "issue_17_sourcing": {
            "palm_derivable_ingredients_defined": len(palm),
            "mean_palm_derivable_per_product": round(
                sum(r["count"] for r in palm_rows) / n, 2),
            "max_palm_derivable_in_one_product": max(r["count"] for r in palm_rows),
            "products_with_no_palm_derivable": sum(1 for r in palm_rows if r["count"] == 0),
            "per_product": palm_rows,
            "natural_mica_products": natural_mica,
            "synthetic_mica_products": synthetic_mica,
            "talc_products": talc,
            "loreal_acop": {
                "total_palm_volume_tonnes": acop["total_palm_volume_tonnes"],
                "derivatives_share_of_volume": round(
                    acop["derivatives_and_fractions_tonnes"] / acop["total_palm_volume_tonnes"], 4),
                "certified_total_tonnes": cert_total,
                "mass_balance_share_of_certified": round(cert["mass_balance"] / cert_total, 4),
                "physically_separated_tonnes": physically_separated,
                "physically_separated_share_of_certified": round(physically_separated / cert_total, 5),
            },
            "parents_with_confirmed_rspo_membership": sum(
                1 for c in src["parent_company_positions"] if c["rspo_member"] is True),
            "parents_unconfirmed": sum(
                1 for c in src["parent_company_positions"] if c["rspo_member"] is None),
            "parents_total": len(src["parent_company_positions"]),
        },

        "issue_18_mocra": {
            "enacted": reg["mocra"]["enacted"],
            "years_since_enactment": round(
                (TODAY - date.fromisoformat(reg["mocra"]["enacted"])).days / 365.25, 2),
            "requirements_total": len(reqs),
            "in_force": sum(1 for r in reqs if r["status"] == "in force"),
            "requiring_a_rule": sum(1 for r in reqs if r["rule_required"]),
            "rules_issued_final": reg["mocra"]["federal_register_record"]["final_rules"],
            "overdue": overdue,
            "overdue_count": len(overdue),
        },
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    a = main()
    s16 = a["issue_16_banned_ingredients"]
    print("#16  %d of %d corpus ingredients prohibited in the EU" % (
        s16["corpus_ingredients_prohibited_in_eu"], s16["corpus_ingredients_tested"]))
    print("     EU prohibits %d substances; the US prohibits %d" % (
        s16["eu_prohibited_entries"], s16["us_prohibited_entries"]))
    print("     UV filters permitted: EU %d, US %d" % (
        s16["eu_uv_filters"], s16["us_uv_filters"]))
    print("     siloxane leave-on restriction from %s (%d days away), hits %d products" % (
        s16["siloxane_restriction_applies_from"],
        s16["days_until_siloxane_restriction"],
        s16["products_affected_by_siloxane_restriction"]))
    print("     %d products declare EU fragrance allergens; %d declare octinoxate (max %.1f%%, EU limit %g%%)" % (
        s16["products_declaring_eu_allergens"], s16["products_declaring_octinoxate"],
        s16["octinoxate_max_declared_pct"], s16["octinoxate_eu_limit_pct"]))
    print()
    s17 = a["issue_17_sourcing"]
    print("#17  mean %.2f palm-derivable ingredients per product (max %d)" % (
        s17["mean_palm_derivable_per_product"], s17["max_palm_derivable_in_one_product"]))
    print("     natural mica in %d, synthetic mica in %d, talc in %d" % (
        len(s17["natural_mica_products"]), len(s17["synthetic_mica_products"]),
        len(s17["talc_products"])))
    print("     L'Oreal certified palm: %.1f%% mass balance, %.3f%% physically separated" % (
        s17["loreal_acop"]["mass_balance_share_of_certified"] * 100,
        s17["loreal_acop"]["physically_separated_share_of_certified"] * 100))
    print("     RSPO membership confirmed for %d of %d parents" % (
        s17["parents_with_confirmed_rspo_membership"], s17["parents_total"]))
    print()
    s18 = a["issue_18_mocra"]
    print("#18  %.2f years since enactment; %d final rules issued" % (
        s18["years_since_enactment"], s18["rules_issued_final"]))
    for r in s18["overdue"]:
        print("     %-20s %-11s %5.1f months past %s" % (
            r["id"], r["status"], r["months_past_deadline"], r["statutory_deadline"]))
