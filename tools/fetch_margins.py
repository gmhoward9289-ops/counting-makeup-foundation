#!/usr/bin/env python3
"""Pull reported gross margin from primary company filings.

Gross margin is the only cost figure a cosmetics company actually publishes.
Nobody discloses per-product cost, so the published margin is the ceiling of
what can be said with a citation -- everything more granular is modelling.

US filers (Estée Lauder, e.l.f. Beauty, Coty) are read from SEC XBRL company
facts, which is the structured form of the 10-K itself. L'Oréal and LVMH file
in France and are not in EDGAR; their figures are recorded in
data/margins-manual.json with a page citation to the annual report.

Writes data/margins.json.
"""
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "foundation.swamplink.com research (dev@swamplink.com)"}
FACTS = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json"
FILING = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K"

# Which public parent companies in each corpus can be pulled live from EDGAR.
# Private companies (Mary Kay Inc., Blistex Inc., Alchemee LLC, LVMH's French
# filing, etc.) and companies not in EDGAR live in <category>-margins-manual.json
# instead -- see fetch_rd.py's docstring for why disclosure is this uneven.
FILERS_BY_CATEGORY = {
    "foundation": {
        "Estée Lauder Companies": "0001001250",
        "e.l.f. Beauty": "0001600033",
        "Coty": "0001024305",
    },
    "toner": {
        "Kenvue": "0001944048",
        "Target Corporation": "0000027419",
        "The Clorox Company": "0000021076",
    },
}
REVENUE_TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"]
# Some filers (Target, since it stopped tagging a discrete GrossProfit fact in
# XBRL after FY2018) only report cost of goods sold; gross profit is derived
# as revenue minus this when GrossProfit itself is absent.
COGS_TAGS = ["CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold"]


def annual(cik, tag):
    """Return {fiscal-year-end: value} for full-year figures reported on a 10-K."""
    try:
        req = urllib.request.Request(FACTS.format(cik=cik, tag=tag), headers=UA)
        data = json.load(urllib.request.urlopen(req, timeout=90))
    except Exception:
        return {}
    out = {}
    for u in data.get("units", {}).get("USD", []):
        if u.get("form") != "10-K" or u.get("fp") != "FY" or "start" not in u:
            continue
        start = dt.date.fromisoformat(u["start"])
        end = dt.date.fromisoformat(u["end"])
        if not (350 <= (end - start).days <= 380):
            continue  # a full year, not a quarter or a two-year comparative
        out[u["end"]] = u["val"]
    return out


def latest_margin(cik):
    gross = annual(cik, "GrossProfit")
    revenue = {}
    for tag in REVENUE_TAGS:
        revenue.update(annual(cik, tag))
    shared = sorted(set(gross) & set(revenue))
    if shared:
        end = shared[-1]
        return {
            "fiscal_year_end": end,
            "revenue_usd": revenue[end],
            "gross_profit_usd": gross[end],
            "gross_margin_pct": round(100 * gross[end] / revenue[end], 1),
            "source": {
                "type": "SEC Form 10-K (XBRL company facts)",
                "publisher": "U.S. Securities and Exchange Commission",
                "cik": cik,
                "url": FILING.format(cik=cik),
            },
        }
    # No discrete GrossProfit fact (Target stopped tagging one after FY2018) --
    # fall back to revenue minus cost of goods sold.
    cogs = {}
    for tag in COGS_TAGS:
        cogs.update(annual(cik, tag))
    shared = sorted(set(cogs) & set(revenue))
    if not shared:
        return None
    end = shared[-1]
    gp = revenue[end] - cogs[end]
    return {
        "fiscal_year_end": end,
        "revenue_usd": revenue[end],
        "cost_of_goods_sold_usd": cogs[end],
        "gross_profit_usd": gp,
        "gross_margin_pct": round(100 * gp / revenue[end], 1),
        "source": {
            "type": "SEC Form 10-K (XBRL company facts)",
            "publisher": "U.S. Securities and Exchange Commission",
            "cik": cik,
            "url": FILING.format(cik=cik),
            "note": "No discrete GrossProfit fact in XBRL; computed as revenue minus the tagged cost-of-goods-sold figure.",
        },
    }


def main():
    category = sys.argv[1] if len(sys.argv) > 1 else "foundation"
    suffix = "" if category == "foundation" else "-%s" % category
    out = {}
    for name, cik in FILERS_BY_CATEGORY.get(category, {}).items():
        m = latest_margin(cik)
        if m:
            out[name] = m
    manual = ROOT / "data" / ("margins-manual%s.json" % suffix)
    if manual.exists():
        out.update(json.loads(manual.read_text(encoding="utf-8")))
    (ROOT / "data" / ("margins%s.json" % suffix)).write_text(json.dumps(out, indent=2), encoding="utf-8")
    for k, v in sorted(out.items(),
                       key=lambda kv: -(kv[1].get("gross_margin_pct") or -1)):
        gm = v.get("gross_margin_pct")
        if gm is None:
            print("%-28s no current primary figure (%s)" % (k, v["source"]["type"]))
            continue
        rev = v.get("revenue_usd") or v.get("revenue_eur")
        cur = "USD" if v.get("revenue_usd") else "EUR"
        print("%-28s FY%s  rev=%7.2fB %s  gross margin=%.1f%%" % (
            k, v["fiscal_year_end"], rev / 1e9, cur, gm))


if __name__ == "__main__":
    main()
