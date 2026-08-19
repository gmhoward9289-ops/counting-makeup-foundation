#!/usr/bin/env python3
"""Derive the analyses for issues #9, #14 and #15 from data/corpus.json.

Everything here is computed from the FDA-filed ingredient declarations. No
figure in the output is entered by hand.

The one piece of chemistry the analysis leans on is the ordering rule: US and
EU labelling both require ingredients in descending order of concentration
down to 1%, below which any order is permitted. So a high position is evidence
of a large share of the formula, and a low position is evidence of under 1% --
but only evidence, since sub-1% ingredients may be listed in any order.
"""
import itertools
import json
import random
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus.json"
OUT = ROOT / "data" / "analysis.json"

# Ingredients a brand can put on the front of the box. Botanical, marine,
# ferment, peptide and vitamin-derivative actives are the ones marketing names;
# nobody advertises disteardimonium hectorite. Matching is by pattern so the
# rule is inspectable rather than a hand-curated list.
HERO_PATTERNS = [
    r"\bextract\b", r"\bferment\b", r"\bjuice\b", r"\boil\b", r"\bbutter\b",
    r"\bpeptide\b", r"hyaluron", r"niacinamide", r"\bceramide\b", r"collagen",
    r"resveratrol", r"ascorb", r"\bcaffeine\b", r"\bpolyglutamic\b",
    r"\bprotein\b", r"\blactobacillus\b", r"\balgae\b", r"\bsaccharina\b",
    r"salicylic acid", r"mandelic acid", r"\ballantoin\b", r"\bureaa?\b",
    r"alpha-glucan", r"\btrehalose\b", r"\bpolysilicone-11\b",
]
HERO_RE = re.compile("|".join(HERO_PATTERNS), re.I)

# Structural/functional ingredients that are commodity chemistry: the vehicle,
# the film formers, the rheology package, the preservatives.
STRUCTURAL_HINTS = re.compile(
    r"dimethicone|siloxane|silsesquioxane|silylate|methicone|silica|alumina|"
    r"hectorite|nylon|polyethylene|polypropylene|crosspolymer|copolymer|"
    r"phenoxyethanol|paraben|sorbate|benzoate|chlorphenesin|glycol|"
    r"magnesium sulfate|sodium chloride|talc|mica|titanium dioxide|iron oxide|"
    r"xanthan|cellulose|stearate|laureth|edta|citrate|tocopher|bht", re.I)


def load():
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def base(p):
    return [i["inci"] for i in p["base_formula"]]


# --------------------------------------------------------------------------
# #9 -- what is shared, what differs
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# #15 -- do sibling brands share a base?
# --------------------------------------------------------------------------
def jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0


def head_overlap(a, b, k=10):
    """Overlap of the top-k declared ingredients -- the vehicle and base.

    This is the metric that matters for the shared-base question. Ingredients
    at the top of the list are the bulk of the formula; agreement down there is
    agreement about what the product actually is.
    """
    return len(set(a[:k]) & set(b[:k])) / k


def common_prefix(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def pairwise(products):
    rows = []
    for p, q in itertools.combinations(products, 2):
        a, b = base(p), base(q)
        rows.append({
            "a": p["id"], "b": q["id"],
            "a_parent": p["parent_company"], "b_parent": q["parent_company"],
            "same_parent": p["parent_company"] == q["parent_company"],
            "same_brand": p["brand"] == q["brand"],
            "jaccard": round(jaccard(a, b), 3),
            "head10_overlap": round(head_overlap(a, b), 3),
            "identical_prefix": common_prefix(a, b),
        })
    return rows


def permutation_test(products, rows, metric, iters=20000, seed=20260819, ids_filter=None):
    """Is same-owner similarity higher than chance?

    Shuffling the parent-company labels across products and recomputing the
    gap gives the null distribution directly. With 12 products the asymptotic
    tests are not trustworthy; this one makes no distributional assumption.
    """
    ids = [p["id"] for p in products]
    parents = [p["parent_company"] for p in products]
    rows = rows if ids_filter is None else [r for r in rows if ids_filter(r)]
    pair_vals = {(r["a"], r["b"]): r[metric] for r in rows}

    def gap(assign):
        same = [v for (x, y), v in pair_vals.items() if assign[x] == assign[y]]
        diff = [v for (x, y), v in pair_vals.items() if assign[x] != assign[y]]
        if not same or not diff:
            return None
        return statistics.mean(same) - statistics.mean(diff)

    observed = gap(dict(zip(ids, parents)))
    rng = random.Random(seed)
    hits, valid = 0, 0
    for _ in range(iters):
        shuffled = parents[:]
        rng.shuffle(shuffled)
        g = gap(dict(zip(ids, shuffled)))
        if g is None:
            continue
        valid += 1
        if g >= observed:
            hits += 1
    return {
        "metric": metric,
        "observed_gap": round(observed, 4),
        "same_parent_mean": round(statistics.mean(
            [r[metric] for r in rows if r["same_parent"]]), 4),
        "diff_parent_mean": round(statistics.mean(
            [r[metric] for r in rows if not r["same_parent"]]), 4),
        "permutations": valid,
        "p_value": round((hits + 1) / (valid + 1), 4),
    }


# --------------------------------------------------------------------------
# #14 -- complexity vs rarity
# --------------------------------------------------------------------------
def complexity_rarity(products, counts):
    n = len(products)
    rows = []
    for p in products:
        b = base(p)
        heroes = [(pos, ing) for pos, ing in enumerate(b, 1) if HERO_RE.search(ing)]
        structural = [ing for ing in b if STRUCTURAL_HINTS.search(ing)]
        # Rarity of an ingredient = how few products in the corpus declare it.
        rarity = [1 - (counts[ing] / n) for ing in b]
        hero_positions = [pos / len(b) for pos, _ in heroes]
        rows.append({
            "id": p["id"], "brand": p["brand"], "product": p["product"],
            "parent_company": p["parent_company"], "price_tier": p["price_tier"],
            "length": len(b),
            "structural_share": round(len(structural) / len(b), 3),
            "mean_rarity": round(statistics.mean(rarity), 3),
            "exclusive_ingredients": sum(1 for ing in b if counts[ing] == 1),
            "hero_count": len(heroes),
            "hero_share": round(len(heroes) / len(b), 3),
            "hero_median_relative_position": (
                round(statistics.median(hero_positions), 3) if heroes else None),
            "heroes_in_top_third": sum(1 for x in hero_positions if x <= 1 / 3),
            "heroes": [{"position": pos, "of": len(b), "inci": ing} for pos, ing in heroes],
        })
    return rows


def by_tier(rows, field):
    out = {}
    for tier in ["budget", "mass", "prestige", "luxury"]:
        vals = [r[field] for r in rows if r["price_tier"] == tier and r[field] is not None]
        if vals:
            out[tier] = round(statistics.mean(vals), 3)
    return out


def main():
    c = load()
    products = c["products"]
    prev_rows, counts = prevalence(products)
    pairs = pairwise(products)
    cr = complexity_rarity(products, counts)

    analysis = {
        "generated_from": "data/corpus.json",
        "n_products": len(products),
        "issue_9_ingredient_comparison": {
            "distinct_base_ingredients": len(counts),
            "appearing_in_one_product_only": sum(1 for v in counts.values() if v == 1),
            "shared_core_75pct": sorted(shared_core(products, counts, 0.75)),
            "prevalence": prev_rows,
        },
        "issue_15_ownership": {
            "pairs": pairs,
            "tests": [permutation_test(products, pairs, m)
                      for m in ("head10_overlap", "jaccard", "identical_prefix")],
            # Two pairs in the corpus are two generations of one product line
            # (Infallible 24H/32H, the two Teint Idoles). Those are trivially
            # similar and are the same brand, not two brands under one owner --
            # so the ownership claim has to survive dropping them.
            "tests_excluding_same_brand_pairs": [
                dict(permutation_test(products, pairs, m,
                                      ids_filter=lambda r: not r["same_brand"]),
                     scope="cross-brand pairs only")
                for m in ("head10_overlap", "jaccard", "identical_prefix")],
            "most_similar_pairs": sorted(
                pairs, key=lambda r: -r["head10_overlap"])[:8],
        },
        "issue_14_complexity_rarity": {
            "per_product": cr,
            "mean_length_by_tier": by_tier(cr, "length"),
            "mean_rarity_by_tier": by_tier(cr, "mean_rarity"),
            "mean_hero_share_by_tier": by_tier(cr, "hero_share"),
            "mean_structural_share_by_tier": by_tier(cr, "structural_share"),
            "mean_hero_position_by_tier": by_tier(cr, "hero_median_relative_position"),
            "hero_patterns": HERO_PATTERNS,
        },
    }
    OUT.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    return analysis


if __name__ == "__main__":
    a = main()
    print("distinct base ingredients:", a["issue_9_ingredient_comparison"]["distinct_base_ingredients"])
    print("shared core (>=75%):", a["issue_9_ingredient_comparison"]["shared_core_75pct"])
    print()
    for t in a["issue_15_ownership"]["tests"]:
        print("%-18s same=%.3f  diff=%.3f  gap=%+.3f  p=%.4f" % (
            t["metric"], t["same_parent_mean"], t["diff_parent_mean"],
            t["observed_gap"], t["p_value"]))
    print()
    print("top pairs by shared base (top-10 overlap):")
    for r in a["issue_15_ownership"]["most_similar_pairs"]:
        print("  %.2f  prefix=%2d  %-32s %-32s %s" % (
            r["head10_overlap"], r["identical_prefix"], r["a"], r["b"],
            "SAME OWNER" if r["same_parent"] else ""))
    print()
    k = a["issue_14_complexity_rarity"]
    for f in ("mean_length_by_tier", "mean_rarity_by_tier", "mean_hero_share_by_tier",
              "mean_structural_share_by_tier", "mean_hero_position_by_tier"):
        print("%-32s %s" % (f, k[f]))
