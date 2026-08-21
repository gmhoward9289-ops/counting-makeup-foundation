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
  table.brands td:nth-child(2), table.brands td:nth-child(4) { white-space: normal; }
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
    ("/rd/", "Does R&D pay off"),
    ("/ownership/", "Who makes it"),
    ("/banned/", "What's banned"),
    ("/sourcing/", "Where it came from"),
    ("/mocra/", "Who's watching"),
    ("/development/", "How long it takes"),
]


def nav(current):
    """Sibling links, so a reader can move between the studies without going home."""
    items = "".join(
        ('<span aria-current="page">%s</span>' % escape(label)) if href == current
        else ('<a href="%s">%s</a>' % (href, escape(label)))
        for href, label in PAGES)
    return '  <nav class="pagenav" aria-label="Research pages">%s</nav>\n' % items


ORIGIN = "https://foundation.swamplink.com"


def page(title, desc, h1, lede, body, extra_css="", script="", current=""):
    canonical = ORIGIN + (current if current else "/")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(desc)}">
<link rel="canonical" href="{escape(canonical)}">
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


def load_regulatory():
    j = lambda n: json.loads((ROOT / "data" / n).read_text(encoding="utf-8"))
    return j("regulatory.json"), j("sourcing.json"), j("regulatory-analysis.json")


def load_development():
    return json.loads((ROOT / "data" / "development.json").read_text(encoding="utf-8"))


def longdate(iso):
    """2022-12-29 -> 29 December 2022. For prose; tables keep the ISO form."""
    from datetime import date
    d = date.fromisoformat(iso)
    return "%d %s %d" % (d.day, d.strftime("%B"), d.year)


def cite(src, label=None):
    """Render a source block as a footnote line.

    Every regulatory figure on these pages carries one of these, because the
    whole claim of the page is that the number came out of the instrument and
    not out of a summary of it.
    """
    if not src or not src.get("url"):
        return '<span class="note">%s</span>' % escape(
            (src or {}).get("note") or "no source")
    text = label or src.get("type", "source")
    out = '<a href="%s">%s</a>' % (escape(src["url"]), escape(text))
    if src.get("publisher"):
        out += ' <span class="note">— %s</span>' % escape(src["publisher"])
    return out


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

    <div class="panel">
      <table class="brands">
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



# ------------------------------------------------------------------------ rd
def build_rd(cq):
    c12 = cq["issue_12_rd_vs_quality"]
    rows = c12["per_company"]
    disclosed = [r for r in rows if r["rd_pct_of_revenue"] is not None]
    undisclosed = [r for r in rows if r["rd_pct_of_revenue"] is None]

    def row(r):
        pct = "%.2f%%" % r["rd_pct_of_revenue"] if r["rd_pct_of_revenue"] is not None else "—"
        fy = r["rd_fiscal_year_end"] or "—"
        return (
            "<tr><td>{p}</td><td class='num'>{n}</td><td class='num'>{pct}</td>"
            "<td class='note'>{fy}</td><td class='num'>{spf}</td><td class='num'>{ab}</td>"
            "<td class='num'>{al}</td><td class='num'>{ic}</td></tr>"
        ).format(
            p=escape(r["parent_company"]), n=r["n_products"], pct=pct, fy=fy,
            spf=r["mean_spf"] if r["mean_spf"] is not None else "—",
            ab=r["mean_actives_above_line"], al=r["mean_allergens"],
            ic=r["mean_ingredient_count"] if r["mean_ingredient_count"] is not None else "—")

    table = "".join(row(r) for r in sorted(
        rows, key=lambda r: (r["rd_pct_of_revenue"] is None, -(r["rd_pct_of_revenue"] or 0))))

    sources = "".join(
        "<li><strong>%s</strong> — %s</li>" % (escape(r["parent_company"]), cite(r["rd_source"]))
        for r in rows)

    body = f"""
  <section>
    <h2>Who discloses R&amp;D at all</h2>
    <p>{escape(c12['rd_definition'])}</p>
    <div class="finding"><p><strong>Half the companies behind this corpus disclose no R&amp;D
    figure whatsoever — not e.l.f. Beauty, not LVMH, not Revlon.</strong> Only Coty, Estée Lauder
    and L'Oréal publish a number a reader can actually cite, and even Estée Lauder's only survives
    in prose in a footnote, not as a structured financial-statement fact.</p></div>

    <div class="panel scroll">
      <table>
        <thead><tr><th>Parent company</th><th class="num">Products in corpus</th>
          <th class="num">R&amp;D / revenue</th><th>Fiscal year</th>
          <th class="num">Mean SPF</th><th class="num">Mean actives above 1% line</th>
          <th class="num">Mean allergens</th><th class="num">Mean ingredient count</th></tr></thead>
        <tbody>{table}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">Quality columns are the exact same formulation-derived
    proxy used throughout this site, averaged per company across its products in this corpus — see
    <a href="/price/">price against quality</a> for the full definition.</p>
  </section>

  <section>
    <h2>Does more R&amp;D buy a better formula?</h2>
    <div class="finding"><p><strong>No visible relationship, at n=3.</strong> Ranked by R&amp;D as
    a share of revenue: Coty (2.09%), Estée Lauder (2.21%), L'Oréal (3.10%). Ranked by the
    formulation-quality proxy, the order scrambles completely — Coty's single product carries the
    most declared fragrance allergens and zero actives above the 1% line, while Estée Lauder's
    products average the fewest allergens and the most actives above that line, sitting in the
    middle of the R&amp;D ranking. Spending more on research is not visibly buying a cleaner or
    more concentrated formula in this corpus.</p></div>

    <h3>Sources for each R&amp;D figure</h3>
    <div class="sunken"><ul class="tight">{sources}</ul></div>
  </section>

  <section>
    <div class="caveat"><p><strong>Read this page skeptically.</strong> Three companies with a
    disclosed figure is not a sample size that can establish or rule out a correlation — it is
    barely enough to plot. R&amp;D-as-percent-of-revenue is company-wide, covering every category
    each company sells (skincare, fragrance, haircare, and in L'Oréal and LVMH's case, far beyond
    beauty), not R&amp;D spent on foundation specifically, which no company breaks out. And the
    quality proxy on this page is exactly what it is everywhere else on this site: formulation
    read off an FDA filing, never a review score, a dermatologist rating, or a reformulation-
    frequency count — the axis the original request for this page asked for, and which this
    project does not use.</p></div>
  </section>
"""
    write("rd", page(
        "Does R&D spend buy quality? — Foundation",
        "Public-company R&D expense, paired against this project's formulation-derived quality "
        "proxy. Most companies in this corpus disclose no R&D figure at all.",
        "Does R&D spend buy quality?",
        "Half the companies behind these twelve foundations disclose no R&D figure. Among the "
        "three that do, spending more does not visibly buy a cleaner or more concentrated formula.",
        body, current="/rd/"))


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
        body, current="/disclaimer/"))


# --------------------------------------------------------------------- banned
def build_banned(reg, ra):
    """Issue #16 -- FDA-allowed vs internationally banned."""
    s = ra["issue_16_banned_ingredients"]
    silo = reg["siloxanes"]
    uv = reg["uv_filters"]

    us_rows = "".join(
        "<tr><td><code>{c}</code></td><td>{s}</td></tr>".format(
            c=escape(x["cite"]), s=escape(x["substance"]))
        for x in reg["us_prohibited_substances"]["sections"])

    fp_rows = "".join(
        "<tr><td>{i}</td><td class='num'>{r}</td><td>{w}</td></tr>".format(
            i=escape(x["ingredient"]), r=x["annex_ii_ref"], w=escape(x["why"]))
        for x in reg["corpus_ingredients_on_eu_prohibited_list"]["false_positives"])

    silo_rows = "".join(
        "<tr><td>{b}</td><td class='note'>{p}</td><td><span class='tier'>{t}</span></td>"
        "<td>{s}</td></tr>".format(
            b=escape(r["brand"]), p=escape(r["product"]), t=r["tier"],
            s=", ".join("%s (%s)" % (escape(x["inci"]), x["designation"])
                        for x in r["siloxanes"]))
        for r in s["siloxane_products"])

    alg_rows = "".join(
        "<tr><td>{b}</td><td><span class='tier'>{t}</span></td><td class='num'>{n}</td>"
        "<td class='note'>{a}</td></tr>".format(
            b=escape(r["brand"]), t=r["tier"], n=r["count"],
            a=escape(", ".join(r["allergens"])))
        for r in s["allergen_products"])

    octi = [a for a in s["actives"] if a["octinoxate_pct"] is not None]
    octi.sort(key=lambda a: -a["octinoxate_pct"])
    octi_rows = "".join(
        "<tr><td>{b}</td><td><span class='tier'>{t}</span></td><td class='num'>{p:.1f}%</td>"
        "<td class='num'>{l:g}%</td><td>{ok}</td></tr>".format(
            b=escape(a["brand"]), t=a["tier"], p=a["octinoxate_pct"],
            l=s["octinoxate_eu_limit_pct"],
            ok="<span style='color:var(--ok)'>within limit</span>"
               if not a["octinoxate_over_eu_limit"]
               else "<span style='color:var(--bad)'>over limit</span>")
        for a in octi)

    eu_only = "".join("<li>%s</li>" % escape(x) for x in uv["eu_only_examples"])

    body = f"""
  <section>
    <h2>The premise, tested</h2>
    <div class="finding"><p><strong>Not one of the
    {s['corpus_ingredients_tested']} ingredients in this corpus is prohibited in the
    European Union.</strong> The EU's prohibited-substances list runs to
    {s['eu_prohibited_entries']:,} entries and the American one to
    {s['us_prohibited_entries']}, and that {round(s['eu_prohibited_entries'] / s['us_prohibited_entries'])}-fold
    gap does not separate these twelve products at all. Where the two regimes actually
    diverge is somewhere else entirely — in concentration ceilings, in which UV filters a
    regulator will approve, in a restriction that has not started yet, and in what has to
    be printed on the box.</p></div>

    <p>The claim that American cosmetics are full of ingredients Europe has banned is
    common enough to be worth testing rather than repeating. It is testable here because
    the corpus is built from filings: every ingredient in every product is on the record,
    so the list can be run against the prohibition list directly.</p>

    <h3>How the match was done</h3>
    <p class="note">{escape(reg['corpus_ingredients_on_eu_prohibited_list']['method'])}</p>
    <p>The raw comparison threw {len(reg['corpus_ingredients_on_eu_prohibited_list']['false_positives'])} string
    collisions. Every one turned out to be a longer chemical name that happens to contain a
    corpus ingredient's name inside it — which is exactly the kind of hit that a careless
    version of this study would publish as a finding.</p>
    <div class="panel scroll">
      <table>
        <thead><tr><th>Corpus ingredient</th><th class="num">Annex II ref</th>
          <th>What the entry actually prohibits</th></tr></thead>
        <tbody>{fp_rows}</tbody>
      </table>
    </div>
    <div class="caveat" style="margin-top:1rem"><p><strong>The limit of this result.</strong>
    Annex II is keyed by systematic chemical name and CAS number, not by INCI name, because a
    banned substance needs no INCI glossary entry. A name-based match is conservative: read
    this as <em>no match found</em>, not as a chemical clearance of any product.</p></div>
  </section>

  <section>
    <h2>What the American list actually contains</h2>
    <p>The entire US prohibited-and-restricted list for cosmetic ingredients is nine
    substances or classes, and it has not grown since MoCRA. It fits on one screen.</p>
    <div class="panel scroll">
      <table>
        <thead><tr><th>Citation</th><th>Substance</th></tr></thead>
        <tbody>{us_rows}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">Source: {cite(reg['us_prohibited_substances']['source'], '21 CFR 700, subpart B')}.
    Two further sections of the subpart are excluded from the count because they restrict
    packaging and labelling rather than an ingredient.</p>
  </section>

  <section>
    <h2>Sunscreen: the divergence runs the other way</h2>
    <div class="finding"><p><strong>The EU permits {s['eu_uv_filters']} UV filters. The
    United States permits {s['us_uv_filters']} — and reached that number ten weeks ago.</strong>
    On the one ingredient class where these two regimes differ most, the American regulator
    is the restrictive one.</p></div>

    <p>Every product in this corpus carries an SPF claim, which is why its ingredients are
    filed with the FDA at all. The filters they use are the old ones. Bemotrizinol, permitted
    in Europe for years, was added to the US monograph by final order on
    {longdate(uv['bemotrizinol']['final_order_published'])} at up to
    {uv['bemotrizinol']['max_concentration_pct']}% — the first new American UV filter in
    decades.</p>

    <h3>Permitted in the EU, not in the US</h3>
    <ul class="tight">{eu_only}</ul>

    <div class="caveat"><p><strong>And the older American filters are not settled either.</strong>
    {escape(uv['grase_status_note']['text'])}</p></div>
    <p class="note">Sources: {cite(uv['bemotrizinol']['source'], 'final order OTC000039')};
    {cite(uv['us_source'], '21 CFR 352.10')}; {cite(uv['eu_source'], 'Annex VI, consolidated')}.</p>
  </section>

  <section>
    <h2>Octinoxate, and a myth worth retiring</h2>
    <p>{s['products_declaring_octinoxate']} of the {ra['products']} products declare
    octinoxate. It is routinely described as banned in Europe. It is not: the EU permits it
    up to {s['octinoxate_eu_limit_pct']:g}%, and the highest concentration anyone in this
    corpus files is {s['octinoxate_max_declared_pct']:.1f}%.</p>
    <div class="panel scroll">
      <table>
        <thead><tr><th>Brand</th><th>Tier</th><th class="num">Declared</th>
          <th class="num">EU ceiling</th><th>Status</th></tr></thead>
        <tbody>{octi_rows}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">{escape(reg['octinoxate_limit']['source']['note'])}
    Source: {cite(reg['octinoxate_limit']['source'], 'Annex VI entry 12')}. Local reef-protection
    laws in Hawaii, Key West and Palau restrict octinoxate in sunscreens, and those are real —
    but they are municipal and state measures, not an EU ban, and conflating the two is where
    the myth comes from.</p>
  </section>

  <section>
    <h2>The divergence that has not happened yet</h2>
    <div class="finding"><p><strong>{s['products_affected_by_siloxane_restriction']} of the
    {ra['products']} products contain a cyclic siloxane that the EU will bar from leave-on
    cosmetics after {longdate(s['siloxane_restriction_applies_from'])} — {s['days_until_siloxane_restriction']}
    days from now.</strong> In the United States there is no restriction at all, and none in
    prospect.</p></div>

    <p>A foundation is a leave-on product, so it falls under the later of the two dates in the
    restriction — a distinction press coverage regularly loses. The restriction is
    environmental rather than a consumer-safety finding: D4, D5 and D6 are classified as very
    persistent and very bioaccumulative.</p>
    <div class="panel scroll">
      <table>
        <thead><tr><th>Brand</th><th>Product</th><th>Tier</th><th>Siloxane declared</th></tr></thead>
        <tbody>{silo_rows}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">Threshold is {silo['concentration_threshold_pct']}% by
    weight. Source: {cite(silo['source'], 'Regulation (EU) 2024/1328, REACH Annex XVII entry 70')}.
    US position: {escape(silo['us_position'])}</p>
  </section>

  <section>
    <h2>What the label has to say</h2>
    <p>{s['products_declaring_eu_allergens']} of the {ra['products']} products name
    EU-declarable fragrance allergens in their FDA filing. No American rule requires that.
    They appear because a manufacturer running one global formula prints one global ingredient
    list — the US label is carrying a European obligation for free.</p>
    <div class="panel scroll">
      <table>
        <thead><tr><th>Brand</th><th>Tier</th><th class="num">Allergens</th><th>Declared</th></tr></thead>
        <tbody>{alg_rows}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">The EU expanded this list by
    {reg['fragrance_allergens']['eu']['new_annex_iii_entries']} new Annex III entries under
    Regulation (EU) 2023/1545; non-compliant products could be placed on the Union market only
    until {longdate(reg['fragrance_allergens']['eu']['placing_on_market_deadline'])}, a deadline
    that has now passed. The American equivalent, FD&amp;C section 609(b), exists in statute and
    has never been given a list —
    <a href="/mocra/">that story is on the MoCRA page</a>.
    Sources: {cite(reg['fragrance_allergens']['eu']['source'], 'Regulation (EU) 2023/1545')};
    {cite(reg['fragrance_allergens']['us']['source'], 'Public Law 117-328')}.</p>
  </section>
"""
    write("banned", page(
        "What's banned where — Foundation",
        "The EU prohibits 1,760 substances and the US prohibits nine. Neither list touches "
        "the twelve foundations in this corpus.",
        "What's banned where",
        "The EU prohibits 1,760 substances in cosmetics. The United States prohibits nine. "
        "Testing that gap against twelve real American foundations gives an answer almost "
        "nobody expects.",
        body, current="/banned/"))


# ------------------------------------------------------------------- sourcing
def build_sourcing(src, ra):
    """Issue #17 -- the fourth founding question, and why the label cannot answer it."""
    s = ra["issue_17_sourcing"]
    acop = src["loreal_acop_2023"]
    a = s["loreal_acop"]

    reasoning = "".join("<li>%s</li>" % escape(x)
                        for x in src["why_the_label_cannot_answer"]["reasoning"])

    palm_rows = "".join(
        "<tr><td>{b}</td><td><span class='tier'>{t}</span></td><td>{p}</td>"
        "<td class='num'>{c}</td><td class='num'>{n}</td><td class='num'>{s:.0%}</td></tr>".format(
            b=escape(r["brand"]), t=r["tier"], p=escape(r["parent"]),
            c=r["count"], n=r["formula_length"], s=r["share_of_formula"])
        for r in s["per_product"])

    model_rows = "".join(
        "<tr><td>{k}</td><td class='num'>{v:,.0f}</td><td class='num'>{p:.1f}%</td></tr>".format(
            k=escape(k.replace("_", " ").title()), v=v,
            p=100 * v / a["certified_total_tonnes"])
        for k, v in acop["certified_by_model_tonnes"].items())

    parent_rows = "".join(
        "<tr><td>{p}</td><td>{r}</td><td>{m}</td><td class='note'>{n}</td></tr>".format(
            p=escape(c["parent"]),
            r=("<span style='color:var(--ok)'>confirmed</span>" if c["rspo_member"] is True
               else "<span class='note'>not confirmed</span>"),
            m=("<span style='color:var(--ok)'>confirmed</span>" if c["rmi_member"] is True
               else "<span class='note'>not confirmed</span>"),
            n=escape((c["source"].get("note") or "")[:150]))
        for c in src["parent_company_positions"])

    body = f"""
  <section>
    <h2>The question the label cannot answer</h2>
    <div class="finding"><p><strong>An ingredient declaration names what a substance is and
    never where it came from.</strong> That is a property of the labelling system, not a gap in
    this corpus — and it means no amount of care with FDA filings can tell you whether the
    glycerin in a particular bottle was responsibly sourced.</p></div>
    <ul class="tight">{reasoning}</ul>
    <p>So this study does the only honest thing available: it maps where the sourcing question
    <em>arises</em> in these twelve formulas, and then goes to the company-level filings, which
    are the only primary documents that speak to provenance at all.</p>
  </section>

  <section>
    <h2>Where the question arises: palm</h2>
    <p>Palm and palm-kernel oil are the feedstock behind a long list of cosmetic ingredients
    that carry no hint of it in the name. Across this corpus a product declares on average
    {s['mean_palm_derivable_per_product']} ingredients that are commonly palm-derived, and one
    declares {s['max_palm_derivable_in_one_product']}.</p>
    <div class="panel scroll">
      <table>
        <thead><tr><th>Brand</th><th>Tier</th><th>Parent</th><th class="num">Palm-derivable</th>
          <th class="num">Formula length</th><th class="num">Share</th></tr></thead>
        <tbody>{palm_rows}</tbody>
      </table>
    </div>
    <div class="caveat" style="margin-top:1rem"><p><strong>Derivable, not derived.</strong>
    {escape(src['palm_derivable_ingredients']['source']['note'])}</p></div>
  </section>

  <section>
    <h2>What a certification actually certifies</h2>
    <div class="finding"><p><strong>L'Oréal reports {a['total_palm_volume_tonnes']:,.0f} tonnes
    of palm and palm derivatives for 2023, of which
    {a['mass_balance_share_of_certified']:.1%} of the certified volume is Mass Balance and
    {a['physically_separated_share_of_certified']:.2%} is physically separated from uncertified
    material.</strong> Certified, at this scale, is an accounting statement about volumes bought —
    not a claim that the molecule in your bottle is traceable to a certified plantation.</p></div>

    <p>This is the corpus's largest parent by product count, and the figures come from its own
    filing to RSPO rather than from a sustainability brochure. Two things in it are worth
    reading closely. The first is that
    {a['derivatives_share_of_volume']:.1%} of the volume is <em>derivatives and fractions</em>,
    not palm oil — in cosmetics, palm arrives as glycerin and stearates, which is exactly why it
    is invisible on a label. The second is the split by supply-chain model:</p>

    <div class="panel scroll">
      <table>
        <thead><tr><th>RSPO model</th><th class="num">Tonnes</th><th class="num">Share of certified</th></tr></thead>
        <tbody>{model_rows}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">{escape(src['certification_schemes']['rspo']['why_the_model_matters'])}</p>
    <p class="note">Source: {cite(acop['source'], "L'Oréal RSPO Annual Communication of Progress 2023")}.
    The company's own summary: “{escape(acop['company_statement'])}”</p>
    <p class="note"><strong>On the two percentages.</strong> The table above reports Mass Balance as
    {a['mass_balance_share_of_certified']:.1%} of <em>all certified volume</em>, across all four
    models. The company's statement reports {acop['certified_by_model_tonnes']['mass_balance'] / acop['derivatives_and_fractions_tonnes']:.1%}
    of <em>derivative volume only</em>, which excludes the crude palm oil that carries the Segregated
    certification. Both are correct and they are not the same denominator — the difference is the
    209 tonnes of crude oil, out of {acop['total_palm_volume_tonnes']:,.0f}.</p>
  </section>

  <section>
    <h2>Mica, and the one sourcing choice that is visible</h2>
    <p>Natural mica carries a child-labour concern in Indian and Madagascan mining.
    {len(s['natural_mica_products'])} of the {ra['products']} products list it among their
    colourants. {len(s['synthetic_mica_products'])} declare synthetic fluorphlogopite — mica grown
    in a reactor instead of dug out of the ground.</p>
    <div class="finding"><p><strong>That substitution is one of the very few sourcing decisions a
    reader can actually see on an ingredient list.</strong> It is not necessarily made for ethical
    reasons — synthetic mica is also brighter and more uniform — which is precisely why the label
    cannot be read as a claim.</p></div>
    <p>Talc appears in {len(s['talc_products'])} product. Its sourcing question is asbestos
    contamination, because the two minerals occur together geologically. That is the one
    ingredient issue MoCRA addressed head-on, and
    <a href="/mocra/">the resulting rule was withdrawn</a>.</p>
  </section>

  <section>
    <h2>What could and could not be confirmed</h2>
    <p>Membership of a certification scheme is a checkable fact about a company. It is also the
    ceiling of what is checkable: a product made by an RSPO member is not an RSPO-certified
    product, and no scheme in this table certifies a finished foundation.</p>
    <div class="panel scroll">
      <table>
        <thead><tr><th>Parent</th><th>RSPO</th><th>Responsible Mica Initiative</th><th>Note</th></tr></thead>
        <tbody>{parent_rows}</tbody>
      </table>
    </div>
    <div class="caveat" style="margin-top:1rem"><p><strong>Read the blanks as blanks.</strong>
    {s['parents_with_confirmed_rspo_membership']} of {s['parents_total']} parents were confirmed as
    RSPO members from the scheme's own member pages. The remaining
    {s['parents_unconfirmed']} are recorded as <em>not confirmed</em>, which is not the same as not
    a member: RSPO publishes no member search API and its directory pages are rendered client-side,
    so failing to locate a page is a limit of the retrieval, not evidence about the company.</p></div>
  </section>
"""
    write("sourcing", page(
        "Where it came from — Foundation",
        "Ethical-sourcing claims tested against twelve foundations, and why an ingredient "
        "list structurally cannot answer the question.",
        "Where it came from",
        "The fourth founding question — was it sourced ethically, and to which standard. The "
        "short answer is that an ingredient list cannot tell you, and the interesting part is why.",
        body, current="/sourcing/"))


# ---------------------------------------------------------------------- mocra
def build_mocra(reg, ra):
    """Issue #18 -- what MoCRA requires, and by when."""
    s = ra["issue_18_mocra"]
    m = reg["mocra"]
    fr = m["federal_register_record"]

    def status_cell(st):
        colour = {"in force": "var(--ok)", "not issued": "var(--bad)",
                  "withdrawn": "var(--bad)", "not confirmed": "var(--warn)"}.get(st, "var(--muted)")
        return "<span style='color:%s'>%s</span>" % (colour, escape(st))

    rows = "".join(
        "<tr class='{hi}'><td>{r}</td><td class='note'><code>{c}</code></td>"
        "<td class='num'>{d}</td><td>{s}</td><td class='note'>{n}</td></tr>".format(
            hi="hi" if x["status"] in ("not issued", "withdrawn") else "",
            r=escape(x["requirement"]), c=escape(x["cite"]),
            d=escape(x["statutory_deadline"]), s=status_cell(x["status"]),
            n=escape(x.get("status_detail") or ""))
        for x in m["requirements"])

    overdue_rows = "".join(
        "<tr><td>{r}</td><td class='num'>{d}</td><td>{s}</td>"
        "<td class='num'>{mo:.1f}</td></tr>".format(
            r=escape(x["requirement"]), d=escape(x["statutory_deadline"]),
            s=status_cell(x["status"]), mo=x["months_past_deadline"])
        for x in s["overdue"])

    talc = next(x for x in m["requirements"] if x["id"] == "talc")
    talc_docs = " · ".join(
        '<a href="%s">%s, %s</a>' % (escape(d["url"]), escape(d["kind"]), escape(d["date"]))
        for d in talc["documents"])

    sections = "".join(
        "<tr><td class='num'>%s</td><td>%s</td></tr>" % (escape(x["cite"]), escape(x["title"]))
        for x in m["new_fdc_sections"])

    body = f"""
  <section>
    <h2>The first cosmetics law in eighty years</h2>
    <div class="finding"><p><strong>MoCRA was enacted on {longdate(m['enacted'])} —
    {s['years_since_enactment']:.1f} years ago — and has produced
    {s['rules_issued_final']} final rules.</strong> Of the
    {s['requirements_total']} obligations tracked here, {s['in_force']} are in force because the
    statute made them self-executing. Every one that depends on FDA writing a rule is
    outstanding.</p></div>

    <p>Before MoCRA, the FDA's authority over cosmetics rested on a 1938 statute that gave it no
    power to require registration, no access to safety records, and no mandatory recall. MoCRA
    added eleven new sections to the Food, Drug, and Cosmetic Act, listed below. The question this
    page answers is a narrow and checkable one: what did it require, by when, and what has actually
    happened.</p>

    <div class="panel scroll">
      <table>
        <thead><tr><th class="num">FD&amp;C §</th><th>Title</th></tr></thead>
        <tbody>{sections}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">Every deadline on this page is computed from the
    enactment date and the statute's own “not later than” clauses, read in the enrolled text:
    {cite(m['source'], 'Public Law 117-328, Division FF, Title III, Subtitle E')}. FDA's own summary
    pages are not used as a source for any of them.</p>
  </section>

  <section>
    <h2>Requirement by requirement</h2>
    <div class="panel scroll">
      <table>
        <thead><tr><th>Requirement</th><th>Cite</th><th class="num">Statutory deadline</th>
          <th>Status</th><th>Detail</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <p class="note" style="margin-top:.7rem">Status is as at {longdate(ra['as_of'])}. “Not confirmed”
    appears once, for the PFAS report, which is published on FDA's own website rather than in the
    Federal Register — and fda.gov could not be reached from the machine this was built on. It is
    recorded as unverified rather than as missing, because those are different claims.</p>
  </section>

  <section>
    <h2>What is overdue</h2>
    <div class="panel scroll">
      <table>
        <thead><tr><th>Requirement</th><th class="num">Due</th><th>Status</th>
          <th class="num">Months late</th></tr></thead>
        <tbody>{overdue_rows}</tbody>
      </table>
    </div>

    <h3>The talc rule, proposed and withdrawn</h3>
    <p>{escape(talc['status_detail'])} Talc's asbestos question is the single most concrete
    ingredient-safety issue MoCRA named, and one product in this corpus declares talc.</p>
    <p class="note">{talc_docs}</p>

    <h3>The allergen rule that would have given section 609(b) its content</h3>
    <p>The statute requires a label to identify each fragrance allergen, but leaves the identity of
    those allergens to be set by regulation. No proposed rule has issued, so the duty has no list
    and binds no one. The European Union, over the same period, added
    {reg['fragrance_allergens']['eu']['new_annex_iii_entries']} substances to its declarable list
    and let the transition deadline for placing non-compliant products on the market pass on
    {longdate(reg['fragrance_allergens']['eu']['placing_on_market_deadline'])}.
    <a href="/banned/">Five of the twelve products already declare EU allergens anyway</a>,
    because global formulas travel with global labels.</p>
  </section>

  <section>
    <h2>The whole Federal Register record</h2>
    <div class="finding"><p><strong>{fr['documents_referencing_mocra']} documents mentioning MoCRA
    by name have appeared in the Federal Register since enactment: {fr['final_rules']} final rules,
    {fr['proposed_rules']} proposed rule, and {fr['proposed_rules_withdrawn']} withdrawal — of that
    same proposed rule.</strong> The rest is guidance and administrative notices.</p></div>
    <p class="note">{escape(fr['source']['note'])} Source:
    {cite(fr['source'], 'Federal Register full-text search')}.</p>
    <div class="caveat"><p><strong>What this does and does not show.</strong> A missed rulemaking
    deadline is a fact about the rulemaking record, not a judgement about the agency, and guidance
    documents do real work even though they are not rules — the November 2023 compliance policy is
    why registration and listing became workable at all. What the record does establish is that the
    parts of MoCRA that need a rule to mean anything still do not have one.</p></div>
  </section>
"""
    write("mocra", page(
        "Who's watching — Foundation",
        "MoCRA's requirements and deadlines, read out of the statute, against what has "
        "actually appeared in the Federal Register.",
        "Who's watching",
        "MoCRA was the first substantial change to US cosmetics law since 1938. Three and a half "
        "years on, this is what it required, what took effect, and what never issued.",
        body, current="/mocra/"))


# --------------------------------------------------------------- development
def build_development(dev):
    """Issue #11 -- development/testing effort. Color, not a pillar: see
    data/development.json's own description of why this page is thin on
    purpose."""
    us = dev["us_otc_stability"]
    eu = dev["eu_stability_guidance"]
    poll = dev["concept_to_launch_poll"]

    us_reqs = "".join("<li>%s</li>" % escape(x) for x in us["requirements"])
    eu_reqs = "".join("<li>%s</li>" % escape(x) for x in eu["requirements"])

    body = f"""
  <section>
    <h2>The number that isn't public</h2>
    <div class="caveat"><p><strong>How many prototypes, how many failed batches, how many
    months a specific formula took — no manufacturer in this corpus discloses that, and
    it could not be found sourced anywhere else either.</strong> That number lives inside
    a company's R&amp;D function and never reaches a filing, an annual report or a
    standard. Anything claiming a precise iteration count for the industry is not
    reporting a fact; it is guessing. This page does not guess.</p></div>

    <p>What it does instead is answer a narrower, checkable question: what is a
    manufacturer legally required to prove about a formula's stability before that
    formula may ship, and how is that requirement structured. That's not the same
    question as "how many tries did it take" — but it is the part of development time
    that a regulator, not a marketing brief, actually controls, and it is the same
    reasoning MoCRA's own <a href="/mocra/">safety-substantiation duty</a> rests on:
    a company must be able to show its work, even though the work itself stays
    private.</p>
  </section>

  <section>
    <h2>What has to be proven before a US OTC drug can ship</h2>
    <div class="finding"><p><strong>{escape(us['cite'])} is the rule that actually binds
    these twelve products.</strong> {escape(us['applies_because'])}</p></div>
    <ul class="tight">{us_reqs}</ul>
    <p class="note">Source: {cite(us['source'], us['cite'] + ' — ' + us['title'])}.
    {escape(us['source']['note'])}</p>
    <p>The load-bearing clause is the one about accelerated data: a company can launch on
    a projected shelf life while real-time testing is still running, but only as a
    <em>tentative</em> date that must later be verified. That's the mechanism that lets a
    product with a two-year claimed shelf life ship well under two years after formulation
    is finalized, without skipping the real-time study — the real-time data just keeps
    running in the background after launch.</p>
  </section>

  <section>
    <h2>What the EU requires of every cosmetic, drug claim or not</h2>
    <div class="finding"><p>{eu['title']} requires a documented stability assessment for
    every cosmetic product placed on the EU market, drug claim or not. {escape(eu['quote'])}</p></div>
    <ul class="tight">{eu_reqs}</ul>
    <p class="note">Source: {cite(eu['source'], eu['cite'])}. {escape(eu['source']['note'])}</p>
    <p>The EU rule is broader than the US one in scope — it covers all twelve products in
    this corpus, not just the OTC-drug half of what those products' SPF claims trigger —
    and it is explicit about testing in the real market packaging rather than a neutral
    reference container, because packaging interactions are themselves a stability
    variable.</p>
  </section>

  <section>
    <h2>The one public timeline figure, and why it's labeled color</h2>
    <div class="panel">
      <p>{poll['less_than_12_months_pct']}% less than 12 months ·
      <strong>{poll['twelve_to_eighteen_months_pct']}% said 12–18 months</strong> ·
      {poll['more_than_18_months_pct']}% more than 18 months</p>
      <p class="note">{cite(poll['source'], 'Cosmetics & Toiletries reader poll, ' + poll['published'])}</p>
    </div>
    <div class="caveat"><p><strong>{escape(poll['caveat'])}</strong></p></div>
    <p>It's included anyway because it's the only concept-to-launch timeline figure found
    with an attributable publisher and date — and because, read against the two stability
    rules above, the 12–18 month plurality is not surprising. A product claiming a
    multi-year shelf life needs months of accelerated data before it can even launch on a
    tentative date, and that requirement alone accounts for most of the low end of the
    range.</p>
  </section>
"""
    write("development", page(
        "How long it takes — Foundation",
        "What a manufacturer has to prove about a formula's stability before it can "
        "ship, sourced from US and EU regulation — the part of development time a "
        "filing can actually confirm.",
        "How long it takes",
        "Iteration counts are not disclosed by anyone in this corpus. What is public is "
        "what has to be proven before a formula can ship — this page sources that "
        "instead of guessing the rest.",
        body, current="/development/"))


def margins_sort(m):
    return sorted(m.items(), key=lambda kv: -(kv[1].get("gross_margin_pct") or -1))


def main():
    corpus, analysis, cq, prices = load()
    reg, src, ra = load_regulatory()
    dev = load_development()
    build_ingredients(corpus, analysis, prices)
    build_ownership(corpus, analysis, prices)
    build_complexity(analysis)
    build_price(cq)
    build_rd(cq)
    build_banned(reg, ra)
    build_sourcing(src, ra)
    build_mocra(reg, ra)
    build_development(dev)
    build_disclaimer()


if __name__ == "__main__":
    main()
