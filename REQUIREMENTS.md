# Functional requirements

Ten functional requirements for Foundation (foundation.swamplink.com), written
2026-08-23. They record what the system is required to do — most of them are
already implemented and cite the tool that satisfies them; two (FR-8, FR-9) are
the open interactive work the repo folder is named for. Each requirement states
how it is verified, because a requirement nobody can check is a wish.

Status legend: **implemented** (satisfied today, tool named), **planned**
(backlog, not yet built).

---

## FR-1 — Corpus ingestion from FDA filings

The system shall build its ingredient corpus exclusively from manufacturers'
own declarations filed with the FDA (DailyMed SPL labels, fetched by set ID),
storing the raw XML verbatim under `data/raw/` before any parsing.

*Rationale:* an SPF claim makes a US cosmetic an OTC drug, so the full
declaration is public and first-party. Retailer listings and transcription
sites are not acceptable sources. The known cost — SPF-free foundations are
excluded rather than sourced more weakly — is accepted deliberately.

*Status:* implemented — `tools/fetch_dailymed.py`.
*Verified by:* every product in `data/corpus.json` traces to a raw SPL file in
`data/raw/`.

## FR-2 — Declared, non-silent normalization

The system shall normalize ingredient names (typo corrections, synonym
collapsing) only through rules declared in code, and shall record every applied
correction per-product in the corpus. Silent edits are prohibited.

*Status:* implemented — `tools/build_corpus.py`.
*Verified by:* diffing a product's corpus entry against its raw SPL shows no
change that isn't recorded in that entry's corrections.

## FR-3 — Cross-brand ingredient comparison

The system shall compute, for the full corpus, which ingredients are shared
across brands and which differ — including overlap between sibling brands of
one parent company — and shall derive formula-complexity measures from the
INCI data itself.

*Status:* implemented — `tools/analyze.py` → `data/analysis.json` (issues #9,
#14, #15).
*Verified by:* re-running the tool reproduces `data/analysis.json` from
`data/corpus.json` alone.

## FR-4 — Cost-to-make vs. price, labeled as estimate

The system shall present cost-to-make figures only as bottom-up ingredient
estimates paired with gross-margin data from public filings, and shall label
every such figure as an estimate wherever it is published.

*Status:* implemented — `tools/fetch_margins.py`, `tools/cost_quality.py`
→ `data/cost-quality.json` (issues #10, #12, #13).
*Verified by:* no published cost figure appears without its estimate label and
a filing citation.

## FR-5 — Formulation-derived quality axis

The system shall derive its quality proxy from the formulations in the corpus
(the FDA filings), never from review scores, star ratings, or other
opinion-derived signals — and every analysis that touches quality (including
R&D-vs-quality) shall use this same axis.

*Status:* implemented — `tools/cost_quality.py`.
*Verified by:* no review-score data exists anywhere in `data/`.

## FR-6 — Computed regulatory cross-checks

The system shall compute how the corpus crosses regulatory lists (EU Annex II
prohibitions, FDA restrictions, MoCRA requirements) from the corpus on every
run. Which products a rule touches, and how overdue a deadline is, shall never
be hand-entered; only the regulation texts themselves (unfetchable by script)
may be hand-read into `data/regulatory.json`, each figure with its own
`source` block.

*Status:* implemented — `tools/analyze_regulatory.py`
→ `data/regulatory-analysis.json` (issues #16, #17, #18).
*Verified by:* deleting `data/regulatory-analysis.json` and re-running
reproduces it; `data/regulatory.json` contains no derived values.

## FR-7 — Citation integrity through generation

The system shall generate every published page from the data files
(`tools/build_site.py`), so that no published figure can drift from its
source; every figure shall carry a citation to a primary source.

*Status:* implemented — `tools/build_site.py`; `site/` is deployed verbatim
with no build step on the server.
*Verified by:* regenerating `site/` from `data/` produces the deployed pages.

## FR-8 — Interactive brand comparison (the slider)

The system shall provide an interactive treatment of the INCI comparison: the
user selects or slides between two brands and watches their formulas converge
and diverge — shared ingredients holding position, differing ones entering and
leaving. It shall run client-side from the same generated data as the static
pages (no server component, per the verbatim-deploy constraint) and cite the
same sources.

*Rationale:* this is the "slider" idea from the founding brief (ISSUES.md,
2026-08-17), named as the interactive leg of the load-bearing INCI study.

*Status:* implemented — `tools/build_site.py`'s `build_ingredients()`, live at
`/ingredients/`. Two `<select>`s plus a price-ordered range slider drive a
client-side comparison of any two products' base formulas, with matching
ingredients highlighted and both sources cited inline.
*Verified by:* the comparison view renders from data embedded straight out of
`corpus.json`/`prices.json` at generation time, so every displayed ingredient
fact matches the static ingredient study by construction.

## FR-9 — Cost calculator

The system shall provide a calculator view: given a product, it computes the
bottom-up formula-cost estimate live from the same assumption
(`tools/cost_quality.py`'s blended-formula-cost band) and shows it against the
retail price and the parent company's reported gross margin — with the
estimate framing of FR-4 applied to every number shown.

*Rationale:* the project's working name is the *cosmetics calculator*; the
computation already existed batch-side in `tools/cost_quality.py`, but nothing
let a reader run it on the one assumption that actually drives the estimate
(the assumed $/kg for the blended formula) rather than only see the
pre-computed band.

*Status:* implemented — `tools/build_site.py`'s `build_price()`, live at
`/price/` under "Run the calculator yourself". A product picker plus a
$3–$15/kg slider recompute `mass × price-per-kg` client-side against each
product's exact volume and list price (`data/prices.json`,
`data/cost-quality.json`); the implied cost-of-goods and gross-margin figures
shown alongside are the same pre-computed values FR-4 already labels as
estimates.
*Verified by:* driving the slider to its $3/kg and $15/kg ends for every
product reproduces that product's `estimated_formula_cost_usd` and
`formula_cost_share_of_list_pct` band in `data/cost-quality.json` exactly —
checked programmatically for all twelve corpus products, and interactively
in-browser for a sample of two.

## FR-10 — Negative results recorded, counts locked

The system shall record what it could not verify as explicit nulls with
reasons (never as silent gaps), shall state plainly where a sourced figure
does not exist (e.g. development iteration counts), and shall enforce in CI
that the homepage's advertised study count matches the number of live study
pages.

*Status:* implemented — nulls in `data/regulatory.json`, the caveats in
`data/development.json`, and `tools/check_study_count.py` run by
`.github/workflows/check-study-count.yml`.
*Verified by:* the CI check fails on any count drift; grepping `data/` for
nulls finds a reason beside each.

## FR-11 — Setting-powder talc corpus, checked separately from the reformulation story

The system shall build a second, separate corpus of US setting/finishing powders
carrying an SPF claim (same FR-1 rule: FDA-filed OTC drug label required),
compute talc presence in each product's inactive-ingredient declaration, and
present that alongside — but never blended with — the press/FDA-sourced
narrative on brands reformulating away from talc, since none of those
reformulated products carries an SPF claim or has a primary filing to check.

*Rationale:* the obvious question — "have setting powders gotten rid of
talc?" — turns out to split into two populations that barely overlap: the
FDA-filed SPF powders (all mineral sunscreens, none ever used talc) and the
widely-reported talc-to-talc-free reformulations (Chanel, Laura Mercier,
CoverGirl, Airspun, Givenchy — none SPF-filed). Answering honestly means
keeping the two sourced separately rather than implying one corpus answers
both.

*Status:* implemented — `tools/build_setting_powder_corpus.py` (fetches via
`tools/fetch_dailymed.py`) → `data/setting-powder-corpus.json`;
`tools/analyze_talc.py` → `data/talc-analysis.json`; hand-read FDA
asbestos-testing rounds and named-brand reformulation claims in
`data/talc.json`; rendered by `tools/build_site.py`'s `build_talc()`, live at
`/setting-powders/`.
*Verified by:* every product in `data/setting-powder-corpus.json` traces to a
raw SPL file in `data/raw/`; `contains_talc` on each product is computed by
`tools/analyze_talc.py` from the filed ingredient list, never hand-entered;
every fact in `data/talc.json` carries its own `source` block.

## FR-12 — Toner corpus, sourced through the acne monograph instead of SPF

The system shall build a third, separate corpus of US liquid facial toners,
using the FDA's acne-treatment (salicylic acid) OTC monograph as the filing
trigger in place of an SPF claim, and shall carry the full FR-3/FR-4/FR-5/FR-6
treatment (ingredient comparison, cost-vs-price, quality proxy, and the one
regulatory divergence the corpus actually triggers) rather than ingestion
alone.

*Rationale:* toner is almost never sold with an SPF claim, so FR-1's original
trigger does not produce a corpus for this category at all. The FDA's other
route to an OTC drug label — a salicylic acid acne-treatment claim under 21
CFR Part 333 — does, and unlike the lip-gloss corpus, several of the resulting
parent companies (Kenvue, The Clorox Company, Target Corporation, in addition
to L'Oréal) are public filers, so the cost/margin/R&D treatment FR-4/FR-5
already run for foundation carries over. Two populations that shared the
"toner" label turned out not to be comparable and are excluded rather than
blended in: plain witch-hazel astringents (filed under the FDA's separate
astringent monograph) declare no formulated vehicle to compare, and Stridex
Maximum's filing turned out to be pre-saturated pads, not a pourable liquid,
on inspection of its packaging section.

*Status:* implemented — `tools/build_corpus.py toner` (now parameterized
by category, shared with foundation/lotion/setting-powder) →
`data/corpus-toner.json`; `tools/analyze.py toner` → `data/analysis-toner.json`;
`tools/fetch_margins.py toner` / `tools/fetch_rd.py toner` (also parameterized)
plus `data/margins-manual-toner.json` / `data/rd-manual-toner.json` for the
private parent companies → `data/margins-toner.json` / `data/rd-toner.json`;
`tools/cost_quality_toner.py` → `data/cost-quality-toner.json`;
`tools/analyze_regulatory_toner.py` against `data/regulatory-toner.json` →
`data/regulatory-analysis-toner.json`; rendered by `tools/build_site.py`'s
`build_toner()`, live at `/toner/`.
*Verified by:* every product in `data/corpus-toner.json` traces to a raw SPL
file in `data/raw/`; re-running `tools/build_corpus.py foundation` and
`tools/build_corpus.py lotion` after the shared-tool changes reproduces
`data/corpus.json` and `data/corpus-lotion.json` byte-for-byte; every null
margin/R&D figure in the manual files carries a "privately held, no 10-K"
reason rather than a silent gap. Known open gap, stated on the page itself:
unlike foundation's `data/regulatory.json`, a full EU Annex II
general-prohibition sweep across this corpus's ~50 distinct ingredients has
not yet been performed — `data/regulatory-toner.json` covers the salicylic
acid concentration limit and the fragrance-allergen check only.
