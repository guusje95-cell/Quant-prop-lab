"""Token-unlock schedules from DefiLlama's public dataset bucket (the data behind the free defillama.com/unlocks pages; no key, no paid
API) -> research_data/defillama_unlocks/unlocks.json: per protocol its name, gecko id, and every CLIFF unlock event with the number of
tokens, category and the cumulative unlocked supply just before it (circulating proxy)."""
import json
import time
from pathlib import Path
import numpy as np
import requests
ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / "research_data/defillama_unlocks/unlocks.json"; B = "https://defillama-datasets.llama.fi"


def main():
    names = requests.get(f"{B}/emissionsProtocolsList", timeout=60).json(); out = json.loads(OUT.read_text()) if OUT.exists() else {}
    for i, n in enumerate(names):
        if n in out:
            continue
        try:
            j = requests.get(f"{B}/emissions/{n}", timeout=60).json()
        except Exception:                                                # noqa: BLE001
            continue
        series = {}                                                       # timestamp -> total unlocked (all categories but noncirculating)
        nonc = set((j.get("categories") or {}).get("noncirculating", []))
        for sec in (j.get("documentedData") or {}).get("data", []):
            if sec.get("label") in nonc:
                continue
            for p in sec.get("data", []):
                series[p["timestamp"]] = series.get(p["timestamp"], 0.0) + float(p.get("unlocked") or 0.0)
        ts = np.array(sorted(series)); cum = np.array([series[t] for t in ts])
        ev = []
        for e in (j.get("metadata") or {}).get("events", []) or []:
            if e.get("unlockType") != "cliff" or e.get("category") == "noncirculating":
                continue
            t = int(e["timestamp"]); k = np.searchsorted(ts, t) - 1
            before = float(cum[k]) if k >= 0 else 0.0
            ev.append({"t": t, "tokens": float(sum(e.get("noOfTokens") or [0])), "category": e.get("category"), "unlocked_before": before})
        out[n] = {"name": j.get("name"), "gecko_id": j.get("gecko_id"), "max_supply": (j.get("supplyMetrics") or {}).get("maxSupply"), "events": ev}
        if i % 50 == 0:
            OUT.write_text(json.dumps(out)); print(i, n, len(ev), flush=True)
        time.sleep(0.2)
    OUT.write_text(json.dumps(out)); print("done", len(out))


if __name__ == "__main__":
    main()
