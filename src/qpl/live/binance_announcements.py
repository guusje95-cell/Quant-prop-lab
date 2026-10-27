"""Binance announcement titles + release times (public CMS list endpoint of www.binance.com, the same source as
research_data/binance_announcements). Gen468 event short: catalog 161 (Delisting) gives the spot-delisting events.

  update(live)  merges the newest pages into <live>/announcements/catalog_161.json ({"catalog", "name", "articles": [id, title,
                releaseDate ms]}); the research archive plus this file is the full event history."""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
HEADERS = {"User-Agent": "Mozilla/5.0 (qpl research; public announcement titles)"}


def fetch(catalog: int = 161, pages: int = 2, size: int = 50, pause: float = 1.0) -> list[dict]:
    out = []
    for page in range(1, pages + 1):
        r = requests.get(URL, params={"type": 1, "pageNo": page, "pageSize": size, "catalogId": catalog}, headers=HEADERS, timeout=20)
        r.raise_for_status()
        cats = (r.json().get("data") or {}).get("catalogs") or []
        arts = cats[0].get("articles", []) if cats else []
        out += [{"id": a["id"], "title": a["title"], "releaseDate": a["releaseDate"]} for a in arts]
        if len(arts) < size:
            break
        time.sleep(pause)
    return out


def update(live: Path, catalog: int = 161, pages: int = 2, log=print) -> int:
    d = Path(live) / "announcements"; d.mkdir(parents=True, exist_ok=True); f = d / f"catalog_{catalog}.json"
    old = json.loads(f.read_text()) if f.exists() else {"catalog": catalog, "name": "Delisting", "articles": []}
    have = {a["id"] for a in old["articles"]}
    new = [a for a in fetch(catalog, pages) if a["id"] not in have]
    old["articles"] = sorted(old["articles"] + new, key=lambda a: a["releaseDate"], reverse=True)
    f.write_text(json.dumps(old, ensure_ascii=False, indent=0))
    log(f"  announcements catalog {catalog}: {len(new)} new")
    return len(new)
