# Foundation

Nicole's research project: apply the counting-chicken-wings sourced-research model to
the cosmetics industry. Site: **https://foundation.swamplink.com/** (sibling of
wings.swamplink.com — same discipline, different shelf).

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
`swamplink:/srv/git/nicole-project-cosmetics.git`; a post-receive hook publishes
`site/` to `/var/www/foundation`.

Public repo (see `.repo-visibility`), like wings: GitHub for collaboration,
swamplink for deploy.
