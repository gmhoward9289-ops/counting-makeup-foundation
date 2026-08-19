#!/usr/bin/env python3
"""Pull FDA-filed OTC drug labels (SPL) from DailyMed for SPF foundations.

SPF cosmetics are OTC drugs in the US, so the manufacturer files the full
ingredient declaration with the FDA. That filing -- not a transcription site --
is the primary source for this corpus.

Usage: python tools/fetch_dailymed.py <setid> [<setid> ...]
Writes data/raw/dailymed-<setid>.xml and prints the parsed fields as JSON.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
API = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{}.xml"
VIEW = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={}"

# LOINC section codes used on OTC drug labels.
ACTIVE_SECTION = "55106-9"
INACTIVE_SECTION = "51727-6"


def strip_tags(fragment):
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = (text.replace("&amp;", "&").replace("&lt;", "<")
                .replace("&gt;", ">").replace("&#160;", " ").replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", text).strip()


def section_text(xml, loinc):
    """Return the visible text of the <section> carrying the given LOINC code."""
    marker = xml.find('code code="%s"' % loinc)
    if marker == -1:
        return None
    start = xml.rfind("<section", 0, marker)
    depth, pos = 0, start
    while pos < len(xml):
        nxt_open = xml.find("<section", pos + 1)
        nxt_close = xml.find("</section>", pos + 1)
        if nxt_close == -1:
            break
        if nxt_open != -1 and nxt_open < nxt_close:
            depth += 1
            pos = nxt_open
        else:
            if depth == 0:
                return strip_tags(xml[start:nxt_close])
            depth -= 1
            pos = nxt_close
    return None


def fetch(setid):
    xml = urllib.request.urlopen(API.format(setid), timeout=90).read().decode("utf-8", "replace")
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / ("dailymed-%s.xml" % setid)).write_text(xml, encoding="utf-8")

    title = strip_tags(re.search(r"<title>(.*?)</title>", xml, re.S).group(1)) if re.search(r"<title>", xml, re.S) else ""
    eff = re.search(r'<effectiveTime value="(\d{8})"', xml)
    return {
        "setid": setid,
        "label_title": title,
        "label_effective_date": (lambda d: "%s-%s-%s" % (d[:4], d[4:6], d[6:]))(eff.group(1)) if eff else None,
        "source_url": VIEW.format(setid),
        "active_ingredients_raw": section_text(xml, ACTIVE_SECTION),
        "inactive_ingredients_raw": section_text(xml, INACTIVE_SECTION),
    }


if __name__ == "__main__":
    print(json.dumps([fetch(s) for s in sys.argv[1:]], indent=2))
