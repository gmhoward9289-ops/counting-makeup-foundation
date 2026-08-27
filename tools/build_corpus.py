#!/usr/bin/env python3
"""Parse FDA-filed ingredient declarations into the normalized INCI corpus.

Input : data/manifest.json + data/raw/dailymed-<setid>.xml (see fetch_dailymed.py)
Output: data/corpus.json

Two rules govern this file:
  1. The verbatim filing text is preserved on every product. Nothing here
     replaces the source; the normalized list sits alongside it.
  2. Every correction is declared in SPELLING_FIXES or SYNONYMS below and is
     reported in the corpus output. There are no silent edits.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

import sys
sys.path.insert(0, str(ROOT / "tools"))
from fetch_dailymed import section_text, strip_tags, ACTIVE_SECTION, INACTIVE_SECTION, VIEW

# Manufacturer typos in the filed labels. Left side is what the FDA filing
# literally says; right side is the INCI name it denotes. Rimmel's filing in
# particular is riddled with these.
SPELLING_FIXES = {
    "butylene glucol": "butylene glycol",
    "triethoxycaprylysilance": "triethoxycaprylylsilane",
    "hydroxyethyleclulose": "hydroxyethylcellulose",
    "penaerythrityl tetra-di-t-butyl hydroxyhydrocinnamate": "pentaerythrityl tetra-di-t-butyl hydroxyhydrocinnamate",
    "alpha-isomethyl lonone": "alpha-isomethyl ionone",
    "sodium hyaluraonate": "sodium hyaluronate",
    "caprylica/capric triglyceride": "caprylic/capric triglyceride",
    "parfum.fragrance": "parfum/fragrance",
    "thermus thermophillus ferment": "thermus thermophilus ferment",
    "ethylhexylglycerinma": "ethylhexylglycerin",
    # Up & Up (Target) toner filing.
    "benozphenone-4": "benzophenone-4",
    # Thayers toner filing.
    "melalecua alternifolia (tea tree) leaf oil": "melaleuca alternifolia (tea tree) leaf oil",
}

# A handful of filings run a comma into the middle of one INCI botanical name
# rather than between two ingredients -- the comma-splitter above has no way
# to tell that apart from a real separator, so the merge is declared here
# instead. Applied to the raw declaration text before splitting.
RAW_TEXT_FIXES = {
    # Thayers toner filing: "Hamamelis Virginiana (Witch Hazel), Bark/Leaf/Twig
    # Extract" is one INCI name; every other filing in this project's corpora
    # writes the common name and plant part with no internal comma.
    "hamamelis virginiana (witch hazel), bark/leaf/twig extract":
        "hamamelis virginiana (witch hazel) bark/leaf/twig extract",
}

# Names for one and the same substance. Collapsing these is what makes
# cross-brand comparison possible at all -- "Aqua/Water/Eau" and "water" are
# the same declaration in different house styles.
SYNONYMS = {
    "aqua/water/eau": "water", r"aqua\water\eau": "water", r"water\aqua\eau": "water",
    "water (aqua)": "water", "aqua (water)": "water", "aqua": "water", "eau": "water",
    "aqua (water, eau)": "water", "purified water": "water",
    "fragrance": "parfum/fragrance", "parfum (fragrance)": "parfum/fragrance",
    "parfum": "parfum/fragrance", "fragrance (parfum)": "parfum/fragrance",
    "alcohol denat.": "alcohol denat", "alcohol": "alcohol denat",
    r"yeast extract\faex\extrait de levure": "yeast extract",
    "hyaluronic acid": "sodium hyaluronate",
    "silicon dioxide": "silica",
    "vitamin e": "tocopherol",
}

MAY_CONTAIN = re.compile(
    r"(?:\[?\s*(?:\+/-|\+\s*/\s*-)\s*|may\s+contain\s*(?:/\s*peut\s+contenir)?\s*(?:\(\+/-\))?\s*:?)",
    re.I)


def clean_token(tok):
    tok = tok.strip().strip(".;[]() \t\u2022")
    tok = re.sub(r"<ILN\d+>|\[ILN\d+\]|\biln\d+\b", "", tok, flags=re.I)
    tok = re.sub(r"\s+", " ", tok).strip().strip(".,;[]() ")
    # Filings are inconsistent about whitespace around the separators inside an
    # INCI name -- L'Oreal files "HDI /trimethylol ..." and "BIS -PEG/PPG-14/14"
    # where every other filing writes them closed up. Left alone, the same
    # ingredient fails to match itself across products.
    tok = re.sub(r"\s*/\s*", "/", tok)
    tok = re.sub(r"\s*-\s*", "-", tok)
    # Stripping trailing punctuation above can eat the closing paren of a name
    # that legitimately ends in one ("Water (Aqua)"). Put it back.
    if tok.count("(") > tok.count(")"):
        tok += ")" * (tok.count("(") - tok.count(")"))
    return tok


def split_list(text):
    """Split a filed declaration into ordered ingredient tokens.

    Labels separate ingredients with commas or with bullets, and the bullet
    survives the XML round-trip as a replacement char often enough that both
    have to be handled.
    """
    text = re.sub(r"^\s*(?:inactive\s+)?ingredients?\s*:?\s*", "", text, flags=re.I)
    text = text.replace("\u2022", ",").replace("\ufffd", ",").replace("\u00b7", ",")
    # A locant comma inside a chemical name ("1,2-Hexanediol", "Diethylhexyl 2,
    # 6-Naphthalate") is not a separator. Protect any comma directly between
    # two digits (allowing the filer's optional space) before splitting, and
    # restore it once tokens are cut.
    text = re.sub(r"(\d),(\s*\d)", "\\1\x00\\2", text)
    # A comma inside parentheses belongs to the ingredient -- "Iron Oxides (CI
    # 77491, CI 77492)" is one declaration, not two. Split only at depth 0.
    tokens, buf, depth = [], [], 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            tokens.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    tokens.append("".join(buf))
    # Some filings run the +/- colorants together with no separator at all
    # (Revlon files "Iron Oxides (CI 77491) Iron Oxides (CI 77492) ...").
    out = []
    for tok in tokens:
        runs = re.findall(r"[^()]+?\((?:CI|Ci)\s*\d{5}[^)]*\)?", tok)
        out.extend(runs if len(runs) > 1 else [tok])
    return [t.replace("\x00", ",") for t in (clean_token(x) for x in out) if t]


# Colour Index numbers. The +/- colorant block is where house styles diverge
# most: the same pigment is filed as "Iron Oxides (CI 77491)", "CI 77491 (Iron
# Oxides)" and bare "Iron Oxides" by three different manufacturers. Collapsing
# the CI number off the name is what makes those three countable as one
# ingredient. The collapse is recorded per-product in synonyms_collapsed, so it
# is visible rather than silent, exactly like the SYNONYMS table.
CI_SUFFIX = re.compile(r"^(.+?)\s*\((?:ci\s*\d{5})(?:\s*,\s*ci\s*\d{5})*\)$", re.I)
CI_PREFIX = re.compile(r"^(?:ci\s*\d{5})(?:\s*,\s*ci\s*\d{5})*\s*\((.+)\)$", re.I)

# Two filings leak characters that are not part of any ingredient name: Rimmel
# keeps the "+/-" marker glued to its first colorant, and Dior's label runs a
# French cosmetic registration number ("N. 22157/Z") on past the closing
# bracket of the last one.
STRAY_PREFIX = re.compile(r"^[\[\]\s]*(?:/\s*\+\s*-|\+\s*/\s*-)\s*:?\s*", re.I)
STRAY_SUFFIX = re.compile(r"\]\s*\..*$")


def canonical_colorant(key):
    """Strip CI numbers and filing artefacts off a colorant name."""
    out = STRAY_SUFFIX.sub("", STRAY_PREFIX.sub("", key)).strip()
    m = CI_PREFIX.match(out) or CI_SUFFIX.match(out)
    if m:
        out = m.group(1).strip()
    return out


def normalize(name):
    key = name.lower().strip()
    fixed = SPELLING_FIXES.get(key, key)
    colorant = canonical_colorant(fixed)
    canon = SYNONYMS.get(colorant, colorant)
    return canon, (fixed != key), (canon != fixed)


def parse_product(entry):
    setid = entry["setid"]
    xml = (RAW / ("dailymed-%s.xml" % setid)).read_text(encoding="utf-8")
    eff = re.search(r'<effectiveTime value="(\d{8})"', xml).group(1)
    raw = section_text(xml, INACTIVE_SECTION)
    active = section_text(xml, ACTIVE_SECTION)
    for before, after in RAW_TEXT_FIXES.items():
        raw = re.sub(re.escape(before), after, raw, flags=re.I)

    parts = MAY_CONTAIN.split(raw, maxsplit=1)
    base_raw, mc_raw = parts[0], (parts[1] if len(parts) > 1 else "")

    corrections, synonym_hits = [], []
    def build(text):
        out = []
        for pos, tok in enumerate(split_list(text), 1):
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
        # Foundation's manifest carries parent-company/price-tier for the
        # ownership and price studies; other manifests (e.g. lip gloss) may
        # not have that axis to source and simply omit "parent"/"tier".
        "parent_company": entry.get("parent"),
        "price_tier": entry.get("tier"),
        "source": {
            "type": "FDA-filed OTC drug label (SPL)",
            "publisher": "DailyMed, U.S. National Library of Medicine",
            "setid": setid,
            "url": VIEW.format(setid),
            "label_effective_date": "%s-%s-%s" % (eff[:4], eff[4:6], eff[6:]),
        },
        "active_ingredients_as_filed": active,
        "inactive_ingredients_as_filed": raw,
        "base_formula": build(base_raw),
        "may_contain": build(mc_raw),
        "label_corrections": corrections,
        "synonyms_collapsed": synonym_hits,
    }


def main():
    # A bare `manifest.json`/`corpus.json` is the foundation corpus (the
    # project's original category); any other category reads/writes its own
    # `manifest-<category>.json` / `corpus-<category>.json` pair so multiple
    # product categories can share this same normalization logic.
    category = sys.argv[1] if len(sys.argv) > 1 else "foundation"
    suffix = "" if category == "foundation" else "-%s" % category
    retrieved = {"foundation": "2026-08-19"}.get(category, "2026-08-26")

    # encoding is explicit everywhere in this toolchain: Windows defaults
    # read_text() to cp1252, which silently turns "Estee Lauder" into mojibake.
    manifest = json.loads((ROOT / "data" / ("manifest%s.json" % suffix)).read_text(encoding="utf-8"))
    products = [parse_product(p) for p in manifest["products"]]
    out = {
        "corpus": manifest["corpus"],
        "description": manifest["description"],
        "inclusion_criteria": manifest["inclusion_criteria"],
        "known_limits": manifest["known_limits"],
        "retrieved": manifest.get("retrieved", retrieved),
        "products": products,
    }
    (ROOT / "data" / ("corpus%s.json" % suffix)).write_text(json.dumps(out, indent=2), encoding="utf-8")
    for p in products:
        print("%-34s base=%2d  +/-=%2d  fixes=%d" % (
            p["id"], len(p["base_formula"]), len(p["may_contain"]), len(p["label_corrections"])))


if __name__ == "__main__":
    main()
