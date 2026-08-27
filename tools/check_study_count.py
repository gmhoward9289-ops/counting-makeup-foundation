#!/usr/bin/env python3
"""Fail if the homepage badge drifts from the live study list.

The homepage (site/index.html) is hand-written; the research pages are
generated. The badge used to be a hardcoded "Eight" that was not bumped
when /rd/ shipped. This check is the lock: live cards, the PAGES nav in
build_site.py, and the on-disk study pages must agree, and the badge
must spell that count.
"""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
HOME = SITE / "index.html"

# Small closed set — the badge is a spelled cardinal, not a digit.
CARDINALS = {
    1: "One",
    2: "Two",
    3: "Three",
    4: "Four",
    5: "Five",
    6: "Six",
    7: "Seven",
    8: "Eight",
    9: "Nine",
    10: "Ten",
    11: "Eleven",
    12: "Twelve",
    13: "Thirteen",
}

LIVE_CARD = re.compile(
    r'<div class="card live">\s*<h2><a href="(/[^"/]+/)">',
    re.DOTALL,
)
BADGE = re.compile(
    r'<span class="status">([A-Za-z]+) (study|studies) live',
)


def live_study_hrefs(html: str) -> list[str]:
    hrefs = LIVE_CARD.findall(html)
    if not hrefs:
        raise AssertionError("no live study cards found on the homepage")
    return hrefs


def badge_phrase(n: int) -> str:
    try:
        word = CARDINALS[n]
    except KeyError as e:
        raise AssertionError(
            "no spelled cardinal for %d live studies; extend CARDINALS" % n
        ) from e
    noun = "study" if n == 1 else "studies"
    return "%s %s live" % (word, noun)


def current_badge_phrase(html: str) -> str:
    m = BADGE.search(html)
    if not m:
        raise AssertionError("homepage status badge not found")
    return "%s %s live" % (m.group(1), m.group(2))


def pages_hrefs() -> list[str]:
    """Read build_site.PAGES without importing the renderer."""
    tree = ast.parse(
        (ROOT / "tools" / "build_site.py").read_text(encoding="utf-8")
    )
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "PAGES":
                hrefs = []
                for elt in node.value.elts:
                    href = elt.elts[0]
                    hrefs.append(href.value if isinstance(href, ast.Constant) else href.s)
                return hrefs
    raise AssertionError("PAGES not found in tools/build_site.py")


def sync_home_badge() -> bool:
    """Rewrite the homepage badge from the live-card count. Returns True if changed."""
    html = HOME.read_text(encoding="utf-8")
    phrase = badge_phrase(len(live_study_hrefs(html)))
    new, n = re.subn(
        r'(<span class="status">)[A-Za-z]+ (?:study|studies) live',
        r"\1" + phrase,
        html,
        count=1,
    )
    if n != 1:
        raise AssertionError("could not update the homepage status badge")
    if new == html:
        return False
    HOME.write_text(new, encoding="utf-8")
    return True


def check() -> None:
    html = HOME.read_text(encoding="utf-8")
    hrefs = live_study_hrefs(html)
    nav = pages_hrefs()
    missing_pages = [h for h in hrefs if h not in nav]
    extra_pages = [h for h in nav if h not in hrefs]
    if missing_pages or extra_pages:
        raise AssertionError(
            "homepage live cards and build_site.PAGES disagree: "
            "on homepage but not in PAGES %s; in PAGES but not on homepage %s"
            % (missing_pages, extra_pages)
        )
    missing_files = []
    for href in hrefs:
        path = SITE / href.strip("/") / "index.html"
        if not path.is_file():
            missing_files.append(str(path.relative_to(ROOT)))
    if missing_files:
        raise AssertionError("live study pages missing on disk: %s" % missing_files)
    expected = badge_phrase(len(hrefs))
    actual = current_badge_phrase(html)
    if actual != expected:
        raise AssertionError(
            "homepage badge says %r but %d live studies are listed (expected %r)"
            % (actual, len(hrefs), expected)
        )


class TestStudyCount(unittest.TestCase):
    def test_badge_matches_live_studies(self):
        check()

    def test_rd_is_among_the_live_studies(self):
        hrefs = live_study_hrefs(HOME.read_text(encoding="utf-8"))
        self.assertIn("/rd/", hrefs)


if __name__ == "__main__":
    check()
    print("ok: homepage badge matches %d live studies" % len(
        live_study_hrefs(HOME.read_text(encoding="utf-8"))))
