#!/usr/bin/env python3
"""Build data/setting-powder-corpus.json from FDA-filed OTC drug labels.

Same discipline as tools/build_corpus.py (FR-1/FR-2): every product must
carry an SPF claim to have a primary FDA filing at all. Reuses
tools/fetch_dailymed.py's fetch() so the raw XML lands in data/raw/ exactly
like the foundation corpus.

This corpus is deliberately thinner than corpus.json's: no INCI-canonical
normalization layer, because none of the ten filings below needed a
correction (no typos, no synonym collapsing) -- unlike the foundation
corpus, there is nothing to declare here. Ingredients are kept as a plain
ordered list split from the filed inactive-ingredients string.

Run: python tools/build_setting_powder_corpus.py
"""
import json
import re
from pathlib import Path

from fetch_dailymed import fetch

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "setting-powder-corpus.json"

# Every candidate found with an SPF claim (and therefore an FDA-filed OTC
# drug label) among US setting/finishing powders, as of 2026-08-26. Search
# method: DailyMed's own SPL search (services/v2/spls.json) for
# "setting powder" and "finishing powder", cross-checked against press
# roundups of SPF setting powders. Products found in press coverage but with
# no SPF claim (Chanel, Laura Mercier, CoverGirl, Airspun, Givenchy, Fenty --
# see data/talc.json) have no FDA filing and are excluded from this corpus,
# same reasoning as corpus.json excluding SPF-free foundations.
PRODUCTS = [
    {"id": "baremineral-veil-original",  "brand": "bareMinerals", "product": "Original Mineral Veil Protecting Loose Setting Powder SPF 25", "parent": "e.l.f. Beauty", "tier": "prestige", "setid": "64b163dd-8a86-483f-8dab-80fa8740b12f"},
    {"id": "baremineral-ready-touchup",  "brand": "bareMinerals", "product": "READY Touch Up Veil Broad Spectrum SPF 15",                       "parent": "e.l.f. Beauty", "tier": "prestige", "setid": "60e4c728-d4ce-4d67-911a-f8793a4dbff5"},
    {"id": "supergoop-resetting-light",  "brand": "Supergoop!",   "product": "(Re)setting 100% Mineral Powder Light Broad Spectrum SPF 35",    "parent": "Supergoop, LLC", "tier": "prestige", "setid": "aed5a7ef-5cf2-6738-e053-2a95a90aa7f7"},
    {"id": "supergoop-resetting-medium", "brand": "Supergoop!",   "product": "(Re)setting 100% Mineral Powder Medium Broad Spectrum SPF 35",   "parent": "Supergoop, LLC", "tier": "prestige", "setid": "af4b0f17-43ec-a176-e053-2a95a90a7ac6"},
    {"id": "supergoop-resetting-deep",   "brand": "Supergoop!",   "product": "(Re)setting 100% Mineral Powder Deep Broad Spectrum SPF 35",     "parent": "Supergoop, LLC", "tier": "prestige", "setid": "af4cb85b-1275-2105-e053-2995a90a7e74"},
    {"id": "supergoop-invincible-2017",  "brand": "Supergoop!",   "product": "Invincible Setting Powder SPF 45 (predecessor to Re/setting)",   "parent": "Supergoop, LLC", "tier": "prestige", "setid": "717ea2fc-b739-4378-8724-21f6bd835333"},
    {"id": "supergoop-invincible-2018",  "brand": "Supergoop!",   "product": "Invincible Setting Powder SPF 45 Medium",                        "parent": "Supergoop, LLC", "tier": "prestige", "setid": "ba603759-d164-41ff-9191-2675fe0182e6"},
    {"id": "topix-mineral-finishing",    "brand": "TOPIX",        "product": "Mineral Finishing Sunscreen SPF 30",                             "parent": "Topix Pharmaceuticals", "tier": "professional", "setid": "db7375dc-cbe5-4111-b5b3-085cae80d7bf"},
    {"id": "sugargirl-set-screen",       "brand": "Sugargirl",    "product": "Set Screen SPF 30 Setting Powder Sunscreen (Light)",            "parent": "I World LLC", "tier": "mass", "setid": "1fabd546-55e5-4ab2-8a1b-7b161bfbb866"},
    {"id": "younique-touch-behold",      "brand": "Younique",     "product": "SPF 25 Finishing Powder (Touch Behold)",                         "parent": "Younique LLC", "tier": "mass", "setid": "77e777c1-748b-a48d-e053-2991aa0ac280"},
]


def split_list(raw, prefix_pattern):
    """Strip a known label prefix and split the filed ingredient string into
    an ordered list. No INCI canonicalization -- see module docstring."""
    text = re.sub(prefix_pattern, "", raw or "", count=1, flags=re.I).strip()
    text = re.sub(r"^:", "", text).strip()
    parts = re.split(r",\s*", text.rstrip("."))
    return [p.strip() for p in parts if p.strip()]


def build():
    products = []
    for p in PRODUCTS:
        filing = fetch(p["setid"])
        inactive_list = split_list(
            filing["inactive_ingredients_raw"],
            r"^(inactive ingredients?)\s*",
        )
        products.append({
            "id": p["id"],
            "brand": p["brand"],
            "product": p["product"],
            "parent_company": p["parent"],
            "price_tier": p["tier"],
            "source": {
                "type": "FDA-filed OTC drug label (SPL)",
                "publisher": "DailyMed, U.S. National Library of Medicine",
                "setid": p["setid"],
                "url": filing["source_url"],
                "label_effective_date": filing["label_effective_date"],
            },
            "active_ingredients_as_filed": filing["active_ingredients_raw"],
            "inactive_ingredients_as_filed": filing["inactive_ingredients_raw"],
            "inactive_ingredients": inactive_list,
            "contains_talc": any("talc" in i.lower() for i in inactive_list),
        })

    out = {
        "corpus": "setting-powder-spf-us",
        "description": (
            "US setting/finishing powders that carry an SPF claim. SPF cosmetics are "
            "regulated as OTC drugs in the United States, so the manufacturer files the "
            "complete ingredient declaration with the FDA. Every product here is sourced "
            "from that filing (DailyMed SPL), not a retailer listing or a transcription "
            "site -- same rule as corpus.json."
        ),
        "inclusion_criteria": [
            "Marketed as a setting, finishing, or touch-up powder (not a powder foundation or a standalone loose sunscreen powder that doesn't claim to set makeup).",
            "Carries an SPF claim, and therefore has an FDA-filed OTC drug label.",
            "Sold in the US market.",
            "All identifiable SPF setting/finishing-powder filings found via DailyMed's own SPL search were included, not a curated subset -- this corpus is exhaustive against that search, not sampled.",
        ],
        "known_limits": [
            "SPF-only inclusion is a much sharper selection bias here than for foundation: it excludes essentially every setting powder involved in the publicized talc-reformulation story (Chanel, Laura Mercier, CoverGirl, Airspun, Givenchy, Fenty -- see data/talc.json), because none of them carry an SPF claim and none has a primary FDA filing. The primary-source corpus and the talc-reformulation story are, structurally, almost disjoint sets.",
            "Every SPF setting powder found is a mineral sunscreen (zinc oxide and/or titanium dioxide as the active), which is a different formulation tradition from talc-based translucent powders to begin with -- these products were never talc vehicles, so their filings cannot show a talc-to-no-talc transition.",
            "Two Supergoop! products (Invincible, 2017-2018) and three (Re)setting products (2026) are filed separately by shade/version rather than superseding one filing; each shade/version is listed once, but they are the same product family across time.",
        ],
        "retrieved": "2026-08-26",
        "products": products,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote %s (%d products)" % (OUT.relative_to(ROOT), len(products)))


if __name__ == "__main__":
    build()
