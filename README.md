# Foundation

A swamplink research property: the counting-chicken-wings sourced-research model,
applied to the cosmetics industry. Site: **https://foundation.swamplink.com/**
(sibling of wings.swamplink.com — same discipline, different shelf).

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
python tools/analyze.py                     # issues #9 #14 #15  -> data/analysis.json
python tools/cost_quality.py                # issues #10 #13     -> data/cost-quality.json
python tools/build_site.py                  # render site/*/index.html
```

Pages are generated from the data so no published figure can drift from its source.
Ingredient-name corrections (manufacturers do file typos) and synonym collapsing are
declared in `tools/build_corpus.py` and recorded per-product in the corpus — there are
no silent edits.
