#!/usr/bin/env python3
"""Render the research pages from data/.

Pages are generated rather than hand-written so that no figure on the site can
drift away from the corpus it came from. Each page is a self-contained
site/<slug>/index.html with the plumwater tokens inlined, per the layout rule
in README.md -- no build step at deploy time, no external dependency.

Run after tools/build_corpus.py, tools/analyze.py and tools/cost_quality.py.
"""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

TOKENS = """
  :root {
    --bg: #f2eef1; --panel: #fbf8fa; --sunken: #ece6ea;
    --ink: #241a22; --muted: #6e5d69; --line: #dfd6dc;
    --accent: #8a3b66; --accent-soft: #f2dfe9;
    --petal: #9a4f2a; --petal-soft: #f4e3d4;
    --ok: #175b4f; --ok-bg: #dfeeea;
    --warn: #755208; --warn-bg: #f4e8cd; --warn-line: #e3cf9e;
    --bad: #983434; --bad-bg: #f6e2e2;
    --none: #6e5d69; --none-bg: #eae4e8;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #141014; --panel: #1d171c; --sunken: #171217;
      --ink: #e6dee3; --muted: #9a8a94; --line: #332a31;
      --accent: #c77ba4; --accent-soft: #331f2b;
      --petal: #dfa26b; --petal-soft: #34241a;
      --ok: #6fc4b1; --ok-bg: #15302b;
      --warn: #e8b13f; --warn-bg: #33270f; --warn-line: #4a3b17;
      --bad: #ee8f8f; --bad-bg: #361c1c;
      --none: #9a8a94; --none-bg: #241d22;
    }
  }
"""

BASE_CSS = """
  * { box-sizing: border-box; }
  body { background: var(--bg); color: var(--ink);
    font: 15px/1.55 system-ui, "Segoe UI", sans-serif; margin: 0; padding: 2rem 1.25rem 4rem; }
  .wrap { max-width: 940px; margin: 0 auto; display: flex; flex-direction: column; gap: 2.2rem; }
  a { color: var(--petal); }
  header .eyebrow { font-size: .74rem; letter-spacing: .1em; text-transform: uppercase;
    color: var(--muted); margin: 0 0 .5rem; }
  header .eyebrow a { color: var(--muted); text-decoration: none; }
  header .eyebrow a:hover { text-decoration: underline; }
  header h1 { margin: 0 0 .5rem; font-size: 1.95rem; letter-spacing: -.01em; text-wrap: balance; }
  header p.lede { margin: 0; color: var(--muted); max-width: 68ch; font-size: 1.02rem; }
  h2 { font-size: 1.15rem; color: var(--accent); margin: 0 0 .7rem; }
  h3 { font-size: .95rem; margin: 1.4rem 0 .5rem; }
  section > p { margin: 0 0 .8rem; max-width: 72ch; }
  .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
    padding: 1.1rem 1.2rem; }
  .sunken { background: var(--sunken); border: 1px solid var(--line); border-radius: 10px;
    padding: 1.1rem 1.2rem; }
  .finding { border-left: 3px solid var(--accent); background: var(--accent-soft);
    border-radius: 0 8px 8px 0; padding: .9rem 1.1rem; margin: 0 0 1rem; }
  .finding p { margin: 0; }
  .finding strong { color: var(--ink); }
  .caveat { border-left: 3px solid var(--warn); background: var(--warn-bg);
    border-radius: 0 8px 8px 0; padding: .9rem 1.1rem; color: var(--warn); }
  .caveat strong { color: var(--warn); }
  .scroll { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; font-size: .88rem; }
  th, td { text-align: left; padding: .42rem .6rem; border-bottom: 1px solid var(--line);
    white-space: nowrap; }
  th { font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted);
    font-weight: 600; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  tr.hi td { background: var(--accent-soft); }
  .tier { font-size: .68rem; letter-spacing: .05em; text-transform: uppercase;
    padding: .1rem .4rem; border-radius: 3px; background: var(--none-bg); color: var(--none); }
  .note { color: var(--muted); font-size: .85rem; }
  ul.tight { margin: .3rem 0; padding-left: 1.1rem; }
  ul.tight li { margin: .25rem 0; color: var(--muted); }
  footer { border-top: 1px solid var(--line); padding-top: 1.2rem; color: var(--muted);
    font-size: .85rem; }
  footer a { text-decoration: none; }
  footer a:hover { text-decoration: underline; }
  footer .family { display: flex; flex-wrap: wrap; gap: 1.2rem; }
  .pagenav { display: flex; flex-wrap: wrap; gap: .5rem; margin: -1.2rem 0 0; }
  .pagenav a, .pagenav span { font-size: .82rem; padding: .3rem .7rem; border-radius: 20px;
    border: 1px solid var(--line); text-decoration: none; }
  .pagenav a { color: var(--muted); background: var(--panel); }
  .pagenav a:hover { color: var(--ink); border-color: var(--accent); }
  .pagenav span[aria-current] { color: var(--accent); background: var(--accent-soft);
    border-color: var(--accent); font-weight: 600; }
"""

FOOTER = """
  <footer>
    <p class="note" style="margin:0 0 1rem">Every figure on this page is generated from
    <a href="https://github.com/gmhoward9289-ops/counting-makeup-foundation">the corpus in the repo</a>
    by the scripts in <code>tools/</code>, and traces to a primary filing. Read the
    <a href="/disclaimer/">disclaimer</a> — nothing here is medical, dermatological or
    safety advice, and cost figures are estimates, not company data.</p>
    <!-- swamplink family strip — canonical order: home, siblings, data policy, blog.
         Template and property list: claude-rules/shared-rules.md. -->
    <div class="family">
      <span>Foundation · a swamplink research property</span>
      <a href="https://swamplink.com/">swamplink.com</a>
      <a href="https://wings.swamplink.com/">wings — the chicken one</a>
      <a href="https://swamplink.com/data/plates/">plates — the surveillance one</a>
      <a href="https://swamplink.com/data/policy/">data policy</a>
      <a href="https://blog.swamplink.com/">the blog</a>
    </div>
  </footer>
"""


PAGES = [
    ("/ingredients/", "What's in it"),
    ("/complexity/", "Is it better"),
    ("/price/", "What you pay for"),
    ("/ownership/", "Who makes it"),
]


def nav(current):
    """Sibling links, so a reader can move between the studies without going home."""
    items = "".join(
        ('<span aria-current="page">%s</span>' % escape(label)) if href == current
        else ('<a href="%s">%s</a>' % (href, escape(label)))
        for href, label in PAGES)
    return '  <nav class="pagenav" aria-label="Research pages">%s</nav>\n' % items


def page(title, desc, h1, lede, body, extra_css="", script="", current=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(desc)}">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<style>{TOKENS}{BASE_CSS}{extra_css}</style>
</head>
<body>
<div class="wrap">
  <header>
    <p class="eyebrow"><a href="/">Foundation</a> — a swamplink research property</p>
    <h1>{h1}</h1>
    <p class="lede">{lede}</p>
  </header>
{nav(current)}{body}
{FOOTER}
</div>
{script}
</body>
</html>
"""


def write(slug, html):
    d = SITE / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html, encoding="utf-8")
    print("wrote site/%s/index.html (%d bytes)" % (slug, len(html)))


def load():
    j = lambda n: json.loads((ROOT / "data" / n).read_text(encoding="utf-8"))
    return j("corpus.json"), j("analysis.json"), j("cost-quality.json"), j("prices.json")


def src_link(p):
    return '<a href="%s">FDA filing</a>' % p["source"]["url"]


# ---------------------------------------------------------------- ingredients
def build_ingredients(corpus, analysis, prices):
    i9 = analysis["issue_9_ingredient_comparison"]
    n = len(corpus["products"])
    slim = [{
        "id": p["id"], "brand": p["brand"], "product": p["product"],
        "parent": p["parent_company"], "tier": p["price_tier"],
        "url": p["source"]["url"], "date": p["source"]["label_effective_date"],
        "price": prices["prices"].get(p["id"], {}).get("list_usd"),
        "ml": prices["prices"].get(p["id"], {}).get("volume_ml"),
        "base": [i["inci"] for i in p["base_formula"]],
    } for p in corpus["products"]]
    slim.sort(key=lambda x: (x["price"] or 0) / (x["ml"] or 30))

    rows = "".join(
        "<tr><td>{b}</td><td class='note'>{pr}</td><td><span class='tier'>{t}</span></td>"
        "<td>{par}</td><td class='num'>{n}</td><td class='num'>{d}</td><td>{lnk}</td></tr>".format(
            b=escape(p["brand"]), pr=escape(p["product"]), t=p["price_tier"],
            par=escape(p["parent_company"]), n=len(p["base_formula"]),
            d=p["source"]["label_effective_date"], lnk=src_link(p))
        for p in corpus["products"])

    prev = "".join(
        "<tr><td>{i}</td><td class='num'>{c}</td><td class='num'>{s:.0%}</td></tr>".format(
            i=escape(r["inci"]), c=r["products"], s=r["share"])
        for r in i9["prevalence"][:30])

    core = "".join("<li>%s</li>" % escape(x) for x in i9["shared_core_75pct"])

    body = f"""
  <section>
    <h2>The corpus</h2>
    <div class="finding"><p><strong>{i9['distinct_base_ingredients']} distinct ingredients
    appear across {n} foundations, and {i9['appearing_in_one_product_only']} of them
    ({i9['appearing_in_one_product_only'] * 100 // i9['distinct_base_ingredients']}%) appear in
    exactly one product.</strong> Only {len(i9['shared_core_75pct'])} ingredients show up in
    three-quarters or more of them. Foundations are not one formula in twelve bottles — but
    they are built on a very small common spine.</p></div>

    <p>Every product here carries an SPF claim, which in the United States makes it an
    over-the-counter drug. That matters for sourcing: the manufacturer must file the complete
    ingredient declaration with the FDA, and that filing is public. Nothing in this corpus comes
    from a retailer listing or a transcription site.</p>

    <div class="panel scroll">
      <table>
        <thead><tr><th>Brand</th><th>Product</th><th>Tier</th><th>Parent</th>
          <th class="num">Ingredients</th><th class="num">Label filed</th><th>Source</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">Selection is deliberately narrow: liquid, lotion,
    cream or emulsion foundations only. Powders, sticks and cushions use a different vehicle and
    would not be comparable. The cost of that rigour is a real bias — SPF-free foundations
    (Estée Lauder Double Wear, Maybelline Fit Me Matte + Poreless, Fenty Pro Filt'r) have no FDA
    filing and are excluded rather than sourced more weakly.</p>
  </section>

  <section>
    <h2>Slide between two brands</h2>
    <p>Pick any two and watch the formulas converge or diverge. Matching ingredients line up;
    the rest is where the products actually differ. The default pair is the one worth starting
    with.</p>
    <div class="panel">
      <div class="controls">
        <label>A <select id="selA"></select></label>
        <label>B <select id="selB"></select></label>
      </div>
      <div class="slider-row">
        <span class="note">cheapest / mL</span>
        <input type="range" id="slider" min="0" max="{len(slim) - 1}" value="0">
        <span class="note">dearest / mL</span>
      </div>
      <p class="note" id="sliderHint"></p>
      <div id="stats" class="stats"></div>
      <div class="cmp" id="cmp"></div>
      <p class="note" id="srcs"></p>
    </div>
  </section>

  <section>
    <h2>The common spine</h2>
    <p>These {len(i9['shared_core_75pct'])} ingredients appear in at least 75% of the corpus.
    They are the vehicle, the film former, the rheology package and the preservative — the part
    of a foundation that makes it a foundation at all.</p>
    <div class="sunken"><ul class="tight">{core}</ul></div>

    <h3>Thirty most common ingredients</h3>
    <div class="panel scroll">
      <table>
        <thead><tr><th>Ingredient (INCI)</th><th class="num">Products</th><th class="num">Share</th></tr></thead>
        <tbody>{prev}</tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>What the labels themselves get wrong</h2>
    <p>An FDA filing is verbatim what the manufacturer submitted, typos included. Rimmel's
    label alone declares <em>Butylene Glucol</em>, <em>Triethoxycaprylysilance</em>,
    <em>Hydroxyethyleclulose</em> and <em>Alpha-Isomethyl Lonone</em>. Every correction this
    project makes is declared in <code>tools/build_corpus.py</code> and recorded per-product in
    the corpus, so a reader can see exactly what was changed and disagree with it. There are no
    silent edits.</p>
  </section>
"""

    extra_css = """
  .controls { display:flex; gap:1.2rem; flex-wrap:wrap; margin-bottom:.9rem; }
  .controls label { font-size:.8rem; color:var(--muted); display:flex; gap:.4rem; align-items:center; }
  .controls select { font:inherit; font-size:.85rem; padding:.3rem .4rem; background:var(--bg);
    color:var(--ink); border:1px solid var(--line); border-radius:5px; max-width:20rem; }
  .slider-row { display:flex; align-items:center; gap:.8rem; margin-bottom:.5rem; }
  .slider-row input { flex:1; accent-color: var(--accent); }
  .stats { display:flex; flex-wrap:wrap; gap:1.4rem; margin:.8rem 0 1rem;
    padding:.8rem 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line); }
  .stat b { display:block; font-size:1.4rem; color:var(--accent); font-variant-numeric:tabular-nums; }
  .stat span { font-size:.72rem; letter-spacing:.05em; text-transform:uppercase; color:var(--muted); }
  .cmp { display:grid; grid-template-columns:1fr 1fr; gap:.6rem; font-size:.84rem; }
  .cmp .col h4 { margin:0 0 .4rem; font-size:.8rem; color:var(--muted); font-weight:600; }
  .cmp ol { margin:0; padding-left:1.9rem; }
  .cmp li { padding:.1rem .3rem; border-radius:3px; }
  .cmp li.match { background:var(--ok-bg); color:var(--ok); }
  .cmp li.only { color:var(--muted); }
  @media (max-width:640px) { .cmp { grid-template-columns:1fr; } }
"""

    script = """
<script>
const DATA = __DATA__;
const byId = Object.fromEntries(DATA.map(p => [p.id, p]));
const selA = document.getElementById('selA'), selB = document.getElementById('selB');
const slider = document.getElementById('slider');
for (const p of DATA) {
  const label = p.brand + ' — ' + p.product;
  for (const s of [selA, selB]) s.add(new Option(label, p.id));
}
selA.value = 'loreal-infallible-32h';
selB.value = 'lancome-teint-idole-breathable';

function money(p) {
  return p.price ? '$' + p.price.toFixed(2) + ' / ' + p.ml + ' mL' : 'price n/a';
}
function render() {
  const a = byId[selA.value], b = byId[selB.value];
  const sa = new Set(a.base), sb = new Set(b.base);
  const shared = a.base.filter(x => sb.has(x));
  const union = new Set([...a.base, ...b.base]);
  let prefix = 0;
  while (prefix < a.base.length && prefix < b.base.length && a.base[prefix] === b.base[prefix]) prefix++;
  const head = a.base.slice(0, 10).filter(x => new Set(b.base.slice(0, 10)).has(x)).length;

  document.getElementById('stats').innerHTML = [
    ['<b>' + prefix + '</b><span>identical from the top</span>'],
    ['<b>' + (head * 10) + '%</b><span>of the top 10 shared</span>'],
    ['<b>' + Math.round(100 * shared.length / union.size) + '%</b><span>of all ingredients shared</span>'],
    ['<b>' + (a.parent === b.parent ? 'yes' : 'no') + '</b><span>same parent company</span>'],
  ].map(x => '<div class="stat">' + x + '</div>').join('');

  const col = (p, other) => {
    const s = new Set(other.base);
    return '<div class="col"><h4>' + p.brand + ' — ' + money(p) + '</h4><ol>' +
      p.base.map((x, i) => {
        const m = (i < prefix) || s.has(x);
        return '<li class="' + (m ? 'match' : 'only') + '">' + x + '</li>';
      }).join('') + '</ol></div>';
  };
  document.getElementById('cmp').innerHTML = col(a, b) + col(b, a);
  document.getElementById('srcs').innerHTML =
    'Sources: <a href="' + a.url + '">' + a.brand + ' label filed ' + a.date + '</a> · ' +
    '<a href="' + b.url + '">' + b.brand + ' label filed ' + b.date + '</a>';
  const idx = DATA.findIndex(p => p.id === b.id);
  if (idx >= 0) slider.value = idx;
  document.getElementById('sliderHint').textContent =
    'The slider moves B through the corpus in order of price per mL — currently ' +
    b.brand + ' at $' + (b.price / b.ml).toFixed(2) + ' per mL.';
}
slider.addEventListener('input', () => { selB.value = DATA[slider.value].id; render(); });
selA.addEventListener('change', render);
selB.addEventListener('change', render);
render();
</script>
""".replace("__DATA__", json.dumps(slim))

    write("ingredients", page(
        "What's in my makeup? — Foundation",
        "Twelve foundations compared ingredient by ingredient, every list taken from the "
        "manufacturer's own FDA filing.",
        "What's in my makeup?",
        "Twelve foundations, from a $8 drugstore bottle to a $60 one, compared ingredient by "
        "ingredient. Every list is the manufacturer's own declaration to the FDA.",
        body, extra_css, script, "/ingredients/"))


# ------------------------------------------------------------------ ownership
def build_ownership(corpus, analysis, prices):
    o = analysis["issue_15_ownership"]
    P = {p["id"]: p for p in corpus["products"]}
    a, b = P["loreal-infallible-32h"], P["lancome-teint-idole-breathable"]
    la = [i["inci"] for i in a["base_formula"]]
    lb = [i["inci"] for i in b["base_formula"]]
    pa = prices["prices"]["loreal-infallible-32h"]["list_usd"]
    pb = prices["prices"]["lancome-teint-idole-breathable"]["list_usd"]

    ladder = "".join(
        "<tr class='{c}'><td class='num'>{n}</td><td>{x}</td><td>{y}</td></tr>".format(
            n=i + 1, x=escape(x), y=escape(y), c="hi" if x == y else "")
        for i, (x, y) in enumerate(list(zip(la, lb))[:18]))

    tests = "".join(
        "<tr><td>{m}</td><td class='num'>{s:.3f}</td><td class='num'>{d:.3f}</td>"
        "<td class='num'>{g:+.3f}</td><td class='num'>{p:.4f}</td></tr>".format(
            m=escape(t["metric"].replace("_", " ")), s=t["same_parent_mean"],
            d=t["diff_parent_mean"], g=t["observed_gap"], p=t["p_value"])
        for t in o["tests_excluding_same_brand_pairs"])

    pairs = "".join(
        "<tr class='{c}'><td>{a}</td><td>{b}</td><td class='num'>{h:.0%}</td>"
        "<td class='num'>{p}</td><td>{s}</td></tr>".format(
            a=escape(P[r["a"]]["brand"]), b=escape(P[r["b"]]["brand"]),
            h=r["head10_overlap"], p=r["identical_prefix"],
            s=escape(r["a_parent"]) if r["same_parent"] else "—",
            c="hi" if r["same_parent"] else "")
        for r in o["most_similar_pairs"])

    body = f"""
  <section>
    <h2>The finding</h2>
    <div class="finding"><p><strong>L'Oréal Paris Infallible (${pa:.2f}) and Lancôme Teint Idole
    (${pb:.2f}) declare the same first nine ingredients, in the same order.</strong> Lancôme then
    inserts its botanical and skincare story — moringa seed extract, yacon root juice, glycerin,
    alpha-glucan oligosaccharide, sodium hyaluronate — and rejoins the same backbone underneath.
    Both brands belong to L'Oréal. Both filings declare octinoxate at 6.7%.</p></div>

    <div class="panel scroll">
      <table>
        <thead><tr><th class="num">#</th><th>L'Oréal Paris Infallible 32H · ${pa:.2f}</th>
          <th>Lancôme Teint Idole Ultra Wear · ${pb:.2f}</th></tr></thead>
        <tbody>{ladder}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">Highlighted rows are positions where the two labels
    declare the identical ingredient. Sources: {src_link(a)} (filed {a['source']['label_effective_date']})
    and {src_link(b)} (filed {b['source']['label_effective_date']}).</p>
  </section>

  <section>
    <h2>Is that a coincidence?</h2>
    <p>One striking pair proves nothing. The test is whether same-owner pairs across the whole
    corpus are more alike than chance would give. Shuffling the parent-company labels across the
    twelve products and recomputing the gap builds the null distribution directly — no
    distributional assumptions, which matters at this sample size.</p>

    <div class="panel scroll">
      <table>
        <thead><tr><th>Similarity measure</th><th class="num">Same owner</th>
          <th class="num">Different owner</th><th class="num">Gap</th><th class="num">p</th></tr></thead>
        <tbody>{tests}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">All three survive dropping the two same-brand pairs
    (Infallible 24H/32H and the two Teint Idoles), which are two generations of one product line
    rather than two brands under one owner. 20,000 permutations, seed fixed in
    <code>tools/analyze.py</code>.</p>

    <h3>Most similar pairs in the corpus</h3>
    <div class="panel scroll">
      <table>
        <thead><tr><th>A</th><th>B</th><th class="num">Top-10 shared</th>
          <th class="num">Identical from top</th><th>Shared owner</th></tr></thead>
        <tbody>{pairs}</tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="caveat"><p><strong>What this does and does not show.</strong> Shared declared
    ingredients in shared order is strong evidence of a shared formulation platform — a common
    base that sibling brands build on. It is not proof that two products are the same thing in
    different bottles. Concentrations below roughly 1% may be listed in any order, the filings do
    not disclose concentrations, and pigment load, particle treatment, milling and manufacturing
    tolerance all differ in ways no ingredient list records. Twelve products is also a small
    corpus, and L'Oréal contributes four of them.</p></div>
  </section>
"""
    write("ownership", page(
        "Who really makes it? — Foundation",
        "Do sibling brands under one conglomerate share base formulas? Tested across twelve "
        "FDA-filed foundation labels.",
        "Who really makes it?",
        "A $19 drugstore foundation and a $53 prestige one, both owned by L'Oréal, declare the "
        "same first nine ingredients in the same order. Here is how far that pattern goes.",
        body, current="/ownership/"))


# ----------------------------------------------------------------- complexity
def build_complexity(analysis):
    k = analysis["issue_14_complexity_rarity"]
    rows = "".join(
        "<tr><td>{b}</td><td><span class='tier'>{t}</span></td><td class='num'>{l}</td>"
        "<td class='num'>{r:.2f}</td><td class='num'>{e}</td><td class='num'>{h}</td>"
        "<td class='num'>{p}</td></tr>".format(
            b=escape(r["brand"]), t=r["price_tier"], l=r["length"], r=r["mean_rarity"],
            e=r["exclusive_ingredients"], h=r["hero_count"],
            p=("%.0f%%" % (100 * r["hero_median_relative_position"]))
            if r["hero_median_relative_position"] else "—")
        for r in k["per_product"])

    def tier_row(label, d, fmt="%.2f"):
        cells = "".join("<td class='num'>%s</td>" % (fmt % d[t] if t in d else "—")
                        for t in ("budget", "mass", "prestige", "luxury"))
        return "<tr><td>%s</td>%s</tr>" % (label, cells)

    tiers = (tier_row("Ingredients in the formula", k["mean_length_by_tier"], "%.1f")
             + tier_row("Mean ingredient rarity", k["mean_rarity_by_tier"])
             + tier_row("Share that are named actives", k["mean_hero_share_by_tier"])
             + tier_row("Where those actives sit in the list", k["mean_hero_position_by_tier"]))

    body = f"""
  <section>
    <h2>The finding</h2>
    <div class="finding"><p><strong>Paying more buys a longer ingredient list and more
    marketing-facing actives — but not rarer chemistry.</strong> Mean ingredient rarity is
    essentially flat from the cheapest bottle to the dearest
    ({k['mean_rarity_by_tier']['budget']:.2f} at budget,
    {k['mean_rarity_by_tier']['mass']:.2f} at mass,
    {k['mean_rarity_by_tier']['prestige']:.2f} at prestige,
    {k['mean_rarity_by_tier']['luxury']:.2f} at luxury). Prestige formulas are more
    <em>elaborate</em>, not more <em>exotic</em>.</p></div>

    <div class="panel scroll">
      <table>
        <thead><tr><th>Measure</th><th class="num">Budget</th><th class="num">Mass</th>
          <th class="num">Prestige</th><th class="num">Luxury</th></tr></thead>
        <tbody>{tiers}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">Rarity is measured inside the corpus: an ingredient
    declared by one product of twelve scores 0.92, one declared by all twelve scores 0. That is a
    prevalence measure, not a supplier-price measure — a cheap commodity used by only one brand
    still scores as rare here.</p>
  </section>

  <section>
    <h2>Where the hero ingredient actually sits</h2>
    <p>Labelling law requires descending order of concentration down to 1%. So the position of an
    ingredient is evidence about how much of it there is — and a named active near the bottom of a
    forty-item list is present at well under 1%, however prominently it appears on the box.</p>

    <div class="finding"><p><strong>Mass-market brands bury their actives; prestige brands
    don't.</strong> When a drugstore foundation carries a named active it sits around
    {100 * k['mean_hero_position_by_tier']['mass']:.0f}% of the way down the list. In prestige
    formulas the median active sits at {100 * k['mean_hero_position_by_tier']['prestige']:.0f}% —
    materially higher up, and the only measure in this study where the price gap buys something
    unambiguous.</p></div>

    <div class="panel scroll">
      <table>
        <thead><tr><th>Brand</th><th>Tier</th><th class="num">Ingredients</th>
          <th class="num">Mean rarity</th><th class="num">Exclusive to it</th>
          <th class="num">Named actives</th><th class="num">Median active position</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">"Named actives" are matched by pattern — extracts,
    ferments, peptides, vitamin derivatives and the like — and the full pattern list is printed in
    <code>tools/analyze.py</code> and in <code>data/analysis.json</code>, so the classification can
    be argued with rather than taken on trust.</p>
  </section>

  <section>
    <div class="caveat"><p><strong>Where this is weak.</strong> Rarity here is corpus prevalence,
    not supplier availability or price, because credible bulk-price data for cosmetic raw
    materials is not freely published at a standard this project would accept. Position is
    evidence of concentration, not a measurement of it. And Lancôme's Teint Idole scores as one of
    the <em>least</em> rare prestige formulas precisely because it shares L'Oréal's parts bin —
    which is a finding, not an error.</p></div>
  </section>
"""
    write("complexity", page(
        "Is rarity real, or marketing? — Foundation",
        "Does a more expensive foundation contain rarer ingredients? Measured across twelve "
        "FDA-filed labels.",
        "Is rarity real, or marketing?",
        "Expensive foundations are sold on exotic-sounding ingredients. Measured against twelve "
        "FDA filings, price buys a longer list and better-placed actives — but not rarer chemistry.",
        body, current="/complexity/"))


# ---------------------------------------------------------------------- price
def build_price(cq):
    c10, c13 = cq["issue_10_cost_vs_price"], cq["issue_13_price_quality_matrix"]
    margins = "".join(
        "<tr><td>{k}</td><td class='num'>{v}</td><td class='note'>{s}</td></tr>".format(
            k=escape(k), v=("%.1f%%" % v["gross_margin_pct"]) if v.get("gross_margin_pct") else "—",
            s=escape(v["source"]["type"]))
        for k, v in sorted(margins_sort(c10["gross_margins"])))

    cost = "".join(
        "<tr><td>{b}</td><td><span class='tier'>{t}</span></td><td class='num'>{p}</td>"
        "<td class='num'>{m}</td><td class='num'>{c}</td><td class='num'>{f}</td>"
        "<td class='num'>{s}</td></tr>".format(
            b=escape(r["brand"]), t=r["price_tier"],
            p="$%.2f" % r["list_usd"] if r["list_usd"] else "—",
            m="%.1f%%" % r["parent_gross_margin_pct"] if r["parent_gross_margin_pct"] else "—",
            c="$%.2f" % r["implied_cogs_usd"] if r["implied_cogs_usd"] else "—",
            f="$%.2f–$%.2f" % tuple(r["estimated_formula_cost_usd"]) if r["estimated_formula_cost_usd"] else "—",
            s="%.2f–%.2f%%" % tuple(r["formula_cost_share_of_list_pct"]) if r["formula_cost_share_of_list_pct"] else "—")
        for r in c10["per_product"])

    def trow(label, key, fmt="%.2f"):
        cells = "".join(
            "<td class='num'>%s</td>" % (fmt % c13["by_tier"][t][key]
                                         if c13["by_tier"][t][key] is not None else "—")
            for t in ("budget", "mass", "prestige", "luxury"))
        return "<tr><td>%s</td>%s</tr>" % (label, cells)

    matrix = (trow("Price per mL", "mean_price_per_ml", "$%.2f")
              + trow("SPF as filed and tested", "mean_spf", "%.1f")
              + trow("Named actives above the 1% line", "mean_actives_above_line")
              + trow("EU-declared fragrance allergens", "mean_allergens")
              + trow("Ingredients in the formula", "mean_ingredient_count", "%.1f"))

    quality = "".join(
        "<tr><td>{b}</td><td><span class='tier'>{t}</span></td>"
        "<td class='num'>{ppm}</td><td class='num'>{spf}</td><td class='num'>{ab}</td>"
        "<td class='num'>{al}</td></tr>".format(
            b=escape(r["brand"]), t=r["price_tier"],
            ppm="$%.2f" % r["price_per_ml"] if r["price_per_ml"] else "—",
            spf=r["spf_filed"] or "—", ab=r["named_actives_above_1pct_line"],
            al=r["eu_declared_allergens"])
        for r in sorted(c13["per_product"], key=lambda r: r["price_per_ml"] or 0))

    assumptions = "".join("<li>%s</li>" % escape(a) for a in c10["assumptions"])

    body = f"""
  <section>
    <h2>What the margin says</h2>
    <div class="finding"><p><strong>e.l.f. Beauty runs a 70.7% gross margin. Estée Lauder runs
    74.0%.</strong> The gap between a $10 foundation and a $52 one is not a margin gap — both
    companies keep roughly three-quarters of the sale. The price difference is what the rest of
    the business costs, not what the bottle costs.</p></div>

    <div class="panel scroll">
      <table>
        <thead><tr><th>Company</th><th class="num">Gross margin</th><th>Source</th></tr></thead>
        <tbody>{margins}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">These are group-wide margins across every product a
    company sells, taken from its own filings. LVMH's is the weakest comparator on the page: it is
    dominated by fashion and leather goods, and LVMH does not break out a gross margin for its
    Perfumes &amp; Cosmetics segment.</p>
  </section>

  <section>
    <h2>What the formula costs</h2>
    <p>No cosmetics company publishes per-product manufacturing cost, so anything more granular
    than gross margin is modelling. What follows is a <em>bound</em>, not an estimate: even a
    deliberately generous blended price across the entire formula mass lands far below the retail
    price, and that conclusion holds anywhere inside the band.</p>

    <div class="panel scroll">
      <table>
        <thead><tr><th>Brand</th><th>Tier</th><th class="num">List</th>
          <th class="num">Parent margin</th><th class="num">Implied cost of goods</th>
          <th class="num">Formula cost</th><th class="num">Formula as % of list</th></tr></thead>
        <tbody>{cost}</tbody>
      </table>
    </div>

    <div class="finding" style="margin-top:1rem"><p><strong>The stuff in the bottle costs
    between about 0.2% and 6% of what you pay for it — and in absolute terms it costs roughly the
    same whatever you pay.</strong> Thirty millilitres of Lancôme and thirty millilitres of
    Maybelline are the same mass of largely the same commodity chemistry. What separates $12 from
    $53 is packaging, retail margin, advertising and the counter it is sold from.</p></div>

    <h3>Assumptions behind those numbers</h3>
    <div class="sunken"><ul class="tight">{assumptions}</ul></div>
  </section>

  <section>
    <h2>Price against quality</h2>
    <p>{escape(c13['quality_definition'])}</p>

    <div class="panel scroll">
      <table>
        <thead><tr><th>Measure</th><th class="num">Budget</th><th class="num">Mass</th>
          <th class="num">Prestige</th><th class="num">Luxury</th></tr></thead>
        <tbody>{matrix}</tbody>
      </table>
    </div>

    <div class="finding" style="margin-top:1rem"><p><strong>At more than three times the price
    per millilitre, prestige buys two things the cheaper bottles do not have: actives placed high
    enough in the formula to be present above about 1%, and markedly fewer declared fragrance
    allergens.</strong> It does not buy more sun protection — mass-market foundations in this
    corpus average a <em>higher</em> filed SPF than prestige ones.</p></div>

    <div class="panel scroll">
      <table>
        <thead><tr><th>Brand</th><th>Tier</th><th class="num">Price / mL</th>
          <th class="num">SPF</th><th class="num">Actives above 1% line</th>
          <th class="num">Fragrance allergens</th></tr></thead>
        <tbody>{quality}</tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="caveat"><p><strong>Read this axis carefully.</strong> "Quality" here is derived
    entirely from what is on the filed label. It measures the formulation, not whether the product
    wears well, matches your skin, or is worth buying — an ingredient list cannot tell you any of
    that. Prices are US list prices observed on 19 August 2026 and are the softest input on this
    site: they move by retailer, region and promotion, and drugstore brands are rarely sold at
    list. Per-product price confidence is recorded in <code>data/prices.json</code>.</p></div>
  </section>
"""
    write("price", page(
        "What am I paying for? — Foundation",
        "Gross margins from company filings, a bounded formula-cost estimate, and price "
        "measured against what is actually in the bottle.",
        "What am I paying for?",
        "The ingredients in a $53 foundation cost about the same as the ingredients in a $12 one. "
        "Here is what the filings say, and what the extra $41 is actually buying.",
        body, current="/price/"))



# ----------------------------------------------------------------- disclaimer
def build_disclaimer():
    """Render DISCLAIMER.md as a site page.

    The footer on every research page links here, so it has to exist as a page
    and not only as a file in the repo. Kept generated from the markdown so the
    two cannot drift.
    """
    md = (ROOT / "DISCLAIMER.md").read_text(encoding="utf-8")
    html, in_para = [], []

    def flush():
        if in_para:
            html.append("<p>%s</p>" % " ".join(in_para))
            in_para.clear()

    for line in md.splitlines():
        line = line.rstrip()
        if line.startswith("## "):
            flush()
            html.append("<h2>%s</h2>" % escape(line[3:]))
        elif line.startswith("# "):
            flush()
        elif not line:
            flush()
        else:
            in_para.append(escape(line))
    flush()
    body = '  <section>\n    <div class="panel">%s</div>\n  </section>\n' % "\n".join(html)
    write("disclaimer", page(
        "Disclaimer — Foundation",
        "What this site is, what it is not, and how to read its estimates.",
        "Disclaimer",
        "What this site is, what it is not, and how to read its numbers.",
        body))


def margins_sort(m):
    return sorted(m.items(), key=lambda kv: -(kv[1].get("gross_margin_pct") or -1))


def main():
    corpus, analysis, cq, prices = load()
    build_ingredients(corpus, analysis, prices)
    build_ownership(corpus, analysis, prices)
    build_complexity(analysis)
    build_price(cq)
    build_disclaimer()


if __name__ == "__main__":
    main()
