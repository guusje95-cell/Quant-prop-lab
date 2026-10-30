"""Snapshot the official prop-firm rule pages listed in config/prop_sources.json (run on the PC; the cloud cannot reach them):

    python -m qpl.hub.prop_snapshots          (or get_prop_rules.bat)

Saves research_data/prop_pages/<firm>/<YYYY-MM-DD>/<n>.html plus a plain-text copy and an index.json (url, status, sha256). The
pages are evidence for a human to quote from; the hub never turns page text into rules on its own. Polite: one request per 2 s."""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.request
from datetime import date
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
UA = {"User-Agent": "Mozilla/5.0 (personal research; rule snapshot)"}


def text_of(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", html)
    return re.sub(r"\s+", " ", unescape(re.sub(r"(?s)<[^>]+>", " ", html))).strip()


def snapshot(firms: list[str] | None = None) -> dict:
    src = json.loads((ROOT / "config/prop_sources.json").read_text()); out = {}
    for firm, urls in src.items():
        if firm.startswith("_") or (firms and firm not in firms):
            continue
        d = ROOT / "research_data/prop_pages" / firm / str(date.today()); d.mkdir(parents=True, exist_ok=True); idx = []
        for i, u in enumerate(urls):
            try:
                with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
                    b = r.read(); st = r.status
                (d / f"{i}.html").write_bytes(b); (d / f"{i}.txt").write_text(text_of(b.decode("utf-8", "replace")), encoding="utf-8")
                idx.append({"url": u, "status": st, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(), "file": f"{i}.html"})
            except Exception as e:                                        # noqa: BLE001 - record and continue
                idx.append({"url": u, "error": str(e)})
            time.sleep(2)
        (d / "index.json").write_text(json.dumps(idx, indent=1)); out[firm] = sum("error" not in x for x in idx)
        print(firm, out[firm], "of", len(urls), "pages saved", flush=True)
    return out


if __name__ == "__main__":
    print(snapshot())
    print("push them: git add research_data/prop_pages && git commit -m \"prop rule pages\" && git push")
