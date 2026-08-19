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
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "foundation.swamplink.com research (dev@swamplink.com)"}
FACTS = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json"
FILING = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K"

FILERS = {
    "Estée Lauder Companies": "0001001250",
    "e.l.f. Beauty": "0001600033",
    "Coty": "0001024305",
}
REVENUE_TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"]


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
    if not shared:
        return None
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


def main():
    out = {}
    for name, cik in FILERS.items():
        m = latest_margin(cik)
        if m:
            out[name] = m
    manual = ROOT / "data" / "margins-manual.json"
    if manual.exists():
        out.update(json.loads(manual.read_text(encoding="utf-8")))
    (ROOT / "data" / "margins.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
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
