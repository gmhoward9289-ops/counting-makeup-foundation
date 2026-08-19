#!/usr/bin/env python3
"""Pull reported research and development expense from primary company filings.

Issue #12 asks whether R&D spend correlates with quality. This project's
quality proxy is formulation-derived from FDA filings (see cost_quality.py),
never review or dermatologist scores -- that decision is not reopened here,
only paired with a new axis: how much each parent company spends on R&D,
relative to its revenue.

R&D turns out to be disclosed even less consistently than gross margin.
Coty still tags ResearchAndDevelopmentExpense in XBRL. Estée Lauder discloses
the dollar figure every year but only in prose, in a note to the financial
statements, folded into SG&A on the face of the income statement -- so it has
to be hand-read like the non-EDGAR filers. e.l.f. Beauty discloses no R&D
figure at all, in prose or in XBRL. L'Oréal is the outlier: it reports
"Research & Innovation" as its own headline P&L line. LVMH discloses none.
Revlon no longer files. All of that goes into data/rd-manual.json with a
citation; this script only automates the one company where XBRL still works.

Writes data/rd.json.
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


def latest_rd(cik):
    rd = annual(cik, "ResearchAndDevelopmentExpense")
    revenue = {}
    for tag in REVENUE_TAGS:
        revenue.update(annual(cik, tag))
    shared = sorted(set(rd) & set(revenue))
    if not shared:
        return None
    end = shared[-1]
    return {
        "fiscal_year_end": end,
        "revenue_usd": revenue[end],
        "rd_usd": rd[end],
        "rd_pct_of_revenue": round(100 * rd[end] / revenue[end], 2),
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
        r = latest_rd(cik)
        if r:
            out[name] = r
    manual = ROOT / "data" / "rd-manual.json"
    if manual.exists():
        out.update(json.loads(manual.read_text(encoding="utf-8")))
    (ROOT / "data" / "rd.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for k, v in sorted(out.items(), key=lambda kv: -(kv[1].get("rd_pct_of_revenue") or -1)):
        pct = v.get("rd_pct_of_revenue")
        if pct is None:
            print("%-28s no current primary figure (%s)" % (k, v["source"]["type"]))
            continue
        rd = v.get("rd_usd") or v.get("rd_eur")
        cur = "USD" if v.get("rd_usd") else "EUR"
        print("%-28s FY%s  R&D=%6.1fM %s  = %.2f%% of revenue" % (
            k, v["fiscal_year_end"], rd / 1e6, cur, pct))


if __name__ == "__main__":
    main()
