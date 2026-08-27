# Issues

Now public: the live tracker is
https://github.com/gmhoward9289-ops/counting-makeup-foundation/issues — the entries
below are the founding backlog (2026-08-17), kept as the record of the original
brief. File new work on GitHub.

## 2026-08-17 — feat: INCI ingredient comparison across brands

Take several cosmetic companies selling similar products (start: foundation, ~6–10
brands across price tiers) and compare their INCI ingredient lists — what's shared,
what actually differs. Primary sources: product INCI declarations (legally required),
EU CosIng database (official). This is the load-bearing leg of the project; the
"slider" idea from the brief (slide between brands, watch formulas converge/diverge)
belongs here as the interactive treatment.

## 2026-08-17 — feat: cost-to-make vs. price

What does a product cost to make versus what it sells for. No per-product costs are
public; the honest output is a bottom-up ingredient cost estimate plus gross-margin
data from public filings (L'Oréal, Estée Lauder, e.l.f. as the budget contrast).
Everything labeled as an estimate, educational framing.

## 2026-08-17 — feat: development/testing effort

How many tests/iterations to reach a final formula. Internal R&D data is not
disclosed, so this is color rather than a pillar: general development timelines,
stability-testing requirements, sourced industry figures only.

## 2026-08-17 — feat: R&D cost in comparison to quality

Does R&D spend correlate with product quality? R&D expenditure is reportable for
public companies — pair it with whatever quality proxy the project settles on
(reviews, dermatological ratings, reformulation frequency).

## 2026-08-17 — feat: cost-to-quality matrix

The synthesis view: price tier × quality proxy across the compared brands. Depends on
the INCI comparison and cost work landing first.

## 2026-08-17 — feat: development complexity vs. ingredient rarity

Are complex/rare-ingredient formulas actually harder to make, or is rarity marketing?
Ingredient rarity can be approximated from supplier availability and price; complexity
from formula length/structure in the INCI data.

## 2026-08-17 — epic: company ownership vs. brand — shared base formulas

How conglomerate ownership (L'Oréal group, Estée Lauder companies, Coty, LVMH)
affects base formulas: do sibling brands share bases, and how do formulas carry down
from prestige to mass-market lines within one owner. Needs the INCI corpus first.

## 2026-08-17 — epic: FDA-allowed vs. internationally banned ingredients

The FDA allows ingredients other regulators ban. Dig for real, sourced stats: EU
Cosmetics Regulation Annex II prohibited-substance counts vs. the FDA's restricted
list, plus MoCRA (2022) context on what US regulation actually covers. Primary
sources only — CosIng, eCFR, FDA.gov — chicken-wings sourcing discipline applies.

## 2026-08-26 — feat: eyeliner, a second product category (ingredients study)

Eyeliner as a second product category alongside foundation, starting with the same
load-bearing study foundation started with: INCI ingredient comparison. Eight US
liquid/pencil eyeliners spanning the same price tiers and parent companies as the
foundation corpus. Sourcing had to change — eyeliner carries no SPF claim, so it is
not an OTC drug and has no DailyMed filing — so `data/corpus-eyeliner.json` sources
from each brand's own official product page instead (still first-party under FPLA
labeling law, never a retailer listing). Live at `/eyeliner/`.

*Status:* done — `tools/fetch_eyeliner.py`, `tools/build_corpus_eyeliner.py`,
`tools/analyze_eyeliner.py`, `build_eyeliner_ingredients()` in `tools/build_site.py`.

A genuine finding fell out of it: eyeliner has no shared core at all (0 ingredients
reach a 75% share, versus 7 for foundation), because "eyeliner" is really two
different vehicle chemistries — water-based liquid liner and wax-based pencil/kohl —
wearing one product name. Foundation's corpus is deliberately one vehicle; eyeliner's
isn't, and that's the headline of the page.

## 2026-08-26 — backlog: the rest of eyeliner's studies

Everything foundation has beyond ingredients — cost-to-make vs. price, R&D vs.
quality, ownership/shared-base, banned-ingredient cross-check, MoCRA, sourcing
ethics, formula complexity, development/stability — does not exist yet for
eyeliner. Notes for whoever picks this up:

- **Price/cost** is the easiest next one: `data/margins.json` is already
  company-wide (not foundation-specific), so it's directly reusable. Needs its own
  $/kg cost-band assumption (`BLENDED_FORMULA_USD_PER_KG` in `cost_quality.py` is
  tuned to foundation's TiO2/dimethicone-heavy formulas) and `data/prices.json`
  doesn't have eyeliner list prices/volumes yet.
- **Ownership/shared-base** and **complexity** can likely reuse
  `analyze_eyeliner.py`'s pairwise/prevalence machinery almost as-is (see
  `analyze.py`'s `issue_15_ownership`/`issue_14_complexity_rarity` for the pattern)
  — just needs eyeliner-appropriate `HERO_PATTERNS`/`STRUCTURAL_HINTS` regexes
  (waxes, film-formers, iron-oxide/mica colorants, not SPF actives).
  `permutation_test`'s 8-product corpus is small; interpret p-values accordingly.
- **Banned/MoCRA** mostly cross-check the corpus against EU/US regulation text
  already in `data/regulatory.json` — largely reusable, but the SPF-driven
  stability-trigger framing (`build_site.py:1153`) doesn't apply to eyeliner and
  needs its own regulatory angle (colorant/CI-number restrictions are the more
  relevant cross-check for eye-area cosmetics).
- **R&D** (`data/rd.json`) is keyed by parent company only, so it's reusable
  as-is — no new sourcing needed, just a page.
- **Sourcing/development** need their own hand-curated prose (not derivable),
  same as foundation's — no eyeliner-specific palm-oil/stability-testing research
  has been done yet.
