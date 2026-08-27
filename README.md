# Foundation

[![Discussions](https://img.shields.io/github/discussions/gmhoward9289-ops/counting-makeup-foundation)](https://github.com/gmhoward9289-ops/counting-makeup-foundation/discussions)

A swamplink research property: the counting-chicken-wings sourced-research model,
applied to the cosmetics industry. Site: **https://foundation.swamplink.com/**
(sibling of wings.swamplink.com — same discipline, different shelf).

Questions or shelf finds: [Discussions](https://github.com/gmhoward9289-ops/counting-makeup-foundation/discussions).

Named *Foundation* the same way wings was named: one word, the product itself. It also
carries the second meaning for free — foundational research, what a claim stands on.

## The questions

The site is organized around the four questions from the original brief
(recorded 2026-08-17):

1. **What's in my makeup?** — INCI ingredient comparison across brands selling
   similar products.
2. **Is it really better?** — does a $60 formula actually differ from a $12 one?
3. **What am I paying for?** — cost-to-make vs. retail price, built from public
   filings and bottom-up ingredient cost estimates, always labeled as estimates.
4. **Was it sourced ethically?** — sourcing claims, and to which ethical standards.

Three further studies grew out of the founding four and now stand on their own:
**what's banned where** (the US and EU prohibition lists, tested against the corpus),
**who's watching** (what MoCRA required, and what has actually issued), and
**how long it takes** — development iteration counts are not disclosed anywhere, so this
one sources the checkable half instead: the stability testing a formula must pass before
it can ship (deliberately thin; see `ISSUES.md`'s own framing of it as color, not a
pillar).

Every figure carries a citation to a primary source, chicken-wings style. See
`ISSUES.md` for the feature/epic backlog.

## Design

The site uses the **plumwater** scheme — a mauve & plum recolor of the estate's
Blackwater tokens (parent: `portal/swamp-tokens.css`). Token reference and contrast
rationale: [`site/tokens.css`](site/tokens.css). Status colors (`ok/warn/bad/crit`)
keep their Blackwater values and semantics — they are never decorative.

## Layout & deploy

Chandler-style: `site/` is deployed verbatim (no build step); each page is a
self-contained `site/<slug>/index.html` with tokens inlined. Deploy is a git push to
`lynx:/srv/git/counting-makeup-foundation.git`; a post-receive hook publishes
`site/` to `/var/www/foundation` on lynx.

Public repo (see `.repo-visibility`), like wings: GitHub for collaboration,
swamplink for deploy.

## The corpus

`data/corpus.json` is the ingredient corpus: twelve US liquid foundations spanning
$8 to $60 and five parent companies. Every ingredient list is the manufacturer's own
declaration **filed with the FDA**, not a retailer listing or a transcription site —
an SPF claim makes a cosmetic an OTC drug in the US, so the full declaration is public
on DailyMed. That constraint is also the corpus's main bias: SPF-free foundations are
excluded rather than sourced more weakly.

Rebuild everything from scratch:

```
python tools/fetch_dailymed.py <setid>...   # pull the FDA labels (writes data/raw/)
python tools/build_corpus.py                # parse + normalize  -> data/corpus.json
python tools/fetch_margins.py               # SEC + annual reports -> data/margins.json
python tools/fetch_rd.py                    # SEC + annual reports -> data/rd.json
python tools/analyze.py                     # issues #9 #14 #15  -> data/analysis.json
python tools/cost_quality.py                # issues #10 #12 #13 -> data/cost-quality.json
python tools/analyze_regulatory.py          # issues #16 #17 #18 -> data/regulatory-analysis.json
python tools/build_site.py                  # render site/*/index.html
```

Pages are generated from the data so no published figure can drift from its source.

## Hand-read primary sources

Five data files are not fetched by a script, because their sources cannot be fetched
reliably from here, or because the source itself is prose rather than a structured
filing: `data/margins-manual.json`, `data/rd-manual.json`, `data/regulatory.json`,
`data/sourcing.json` and `data/development.json`. EUR-Lex answers scripted requests with
an empty HTTP 202, and fda.gov fails TLS verification behind a local interception
certificate. L'Oréal and LVMH file outside SEC EDGAR entirely, and even Estée Lauder's
R&D expense — unlike its gross margin — has not been a discrete XBRL fact since fiscal
2014, so it has to be read out of the footnote prose in every 10-K it appears in. So the
consolidated regulations, the statute, and these company figures were read once, by hand,
and every figure in those files carries its own `source` block with the URL, the
publisher and a note on how a count was arrived at. `data/development.json` also carries
its own caveat on the one trade-press figure it uses (a reader poll, not a survey) and
says plainly what it did not find: a sourced iteration count.

## Second corpus: SPF lotions

`data/corpus-lotion.json` is the same discipline applied to a second product
category: eight US daily moisturizing lotions (face and body) carrying an SPF
claim, spanning budget to luxury and six parent companies. It reuses the
foundation corpus's ingestion and normalization tooling
(`tools/build_corpus.py <category>` reads `data/manifest-<category>.json` and
writes `data/corpus-<category>.json`; a bare invocation still targets the
original foundation category). Inclusion criteria and known limits are
recorded in `data/manifest-lotion.json`, same as the foundation manifest.

*Status:* corpus ingestion only (FR-1/FR-2 equivalent for this category) —
the analysis, cost, and regulatory stages (FR-3 through FR-10) have not yet
been run against it, and it is not yet published to `site/`.

The rule that keeps this honest is that nothing *derived* is hand-entered. Which
products a rule actually touches, how many months a deadline is overdue, how the corpus
crosses a prohibition list — all of that is computed by `tools/analyze_regulatory.py`
from the corpus on every run. `data/regulatory.json` also records what could **not** be
verified (the PFAS report, three of six parent companies' scheme memberships) as
explicit nulls with reasons, rather than leaving a gap that later reads as a finding.
Ingredient-name corrections (manufacturers do file typos) and synonym collapsing are
declared in `tools/build_corpus.py` and recorded per-product in the corpus — there are
no silent edits.
