"""Research data request (direction R2, event edges): Bybit public announcement history (v5 /announcements/index, no key) for
new listings and delistings. Run on the user's PC (Bybit blocks this cloud region; do not route around it): get_bybit_announcements.bat
Writes research_data/bybit_announcements/announcements.json."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research_data" / "bybit_announcements"
URL = "https://api.bybit.com/v5/announcements/index"
UA = {"User-Agent": "Mozilla/5.0 (research; quant-prop-lab)"}


def fetch(kind: str, limit: int = 100, max_pages: int = 200) -> list[dict]:
    rows = []
    for page in range(1, max_pages + 1):
        url = URL + "?" + urllib.parse.urlencode({"locale": "en-US", "type": kind, "page": page, "limit": limit})
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            j = json.loads(r.read().decode())
        lst = (j.get("result") or {}).get("list") or []
        rows += [{"title": x.get("title"), "type": (x.get("type") or {}).get("key"), "tags": x.get("tags"), "dateTimestamp": x.get("dateTimestamp"),
                  "publishTime": x.get("publishTime"), "startDateTimestamp": x.get("startDateTimestamp"), "url": x.get("url")} for x in lst]
        print(f"  {kind} page {page}: {len(lst)}", flush=True)
        if len(lst) < limit:
            break
        time.sleep(0.5)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    out = {k: fetch(k) for k in ("new_crypto", "delistings")}
    (OUT / "announcements.json").write_text(json.dumps(out, indent=0))
    print("done -> research_data/bybit_announcements (push it: git add research_data/bybit_announcements && git commit -m 'Bybit announcements' && git push)")


if __name__ == "__main__":
    main()
