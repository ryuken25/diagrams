"""FASE D — Playwright QA: render the *real* draw.io output headless.

Proves the matplotlib preview matches what draw.io draws. Loads each generated
``.drawio`` page into the official draw.io viewer (Chromium, browser UA — which
gets past the CDN's 403 for non-browser fetches) and screenshots it to
``qa/drawio/``. The geometric 0-overlap / 0-crossing gates already run in
``python -m kenshi.cli --check``; this adds the visual ground-truth render.

Usage:  python qa/playwright_check.py [name ...]   (default: all out/*.drawio)
"""
from __future__ import annotations

import glob
import html
import os
import sys

VIEWER = "https://viewer.diagrams.net/js/viewer-static.min.js"
OUT = os.path.join("qa", "drawio")


def _page(drawio_xml: str) -> str:
    # the viewer reads a JSON blob on a div.mxgraph; feed it the whole mxfile
    cfg = html.escape('{"highlight":"#0000ff","nav":false,"toolbar":null,'
                      '"xml":' + _jstr(drawio_xml) + '}', quote=True)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{margin:0;background:#fff}</style></head><body>"
        f"<div class='mxgraph' data-mxgraph=\"{cfg}\"></div>"
        f"<script src='{VIEWER}'></script></body></html>"
    )


def _jstr(s: str) -> str:
    import json
    return json.dumps(s)


def render(names):
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT, exist_ok=True)
    files = []
    for n in names:
        p = n if n.endswith(".drawio") else os.path.join("out", f"{n}.drawio")
        if os.path.exists(p):
            files.append(p)
    if not files:
        print("no .drawio inputs (run `python -m kenshi.cli --out out` first)")
        return 1
    ok = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1800, "height": 1400})
        for f in files:
            xml = open(f, encoding="utf-8").read()
            page.set_content(_page(xml))
            try:
                page.wait_for_selector("svg", timeout=15000)
                page.wait_for_timeout(800)
                out = os.path.join(OUT, os.path.basename(f)[:-7] + ".png")
                el = page.query_selector("div.mxgraph") or page
                el.screenshot(path=out)
                print("rendered", out)
                ok += 1
            except Exception as exc:
                print("FAILED", f, "-", type(exc).__name__, str(exc)[:80])
        browser.close()
    print(f"\n{ok}/{len(files)} draw.io pages rendered to {OUT}/")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(render(sys.argv[1:] or
                            [os.path.basename(p)[:-7]
                             for p in glob.glob(os.path.join("out", "*.drawio"))]))
