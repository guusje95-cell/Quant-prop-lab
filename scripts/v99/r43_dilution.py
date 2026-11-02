"""v9.9 R43 (research/v99/r43_protocol.json): token-dilution cross-sectional factor. Writes results/v99/r43_dilution.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import r16_coinbase as R16
import r22_upbit_r16rules as R22
import r30b_checks as RB
import r32_binance_tag_sleeves as R32
import r34_binance_add as R34
import r42_hodler as R42
D = ROOT / "research_data/defillama_unlocks"


def mapping():
    U = json.loads((D / "unlocks.json").read_text()); L = json.loads((D / "coingecko_list.json").read_text())
    by_id = {x["id"]: x["symbol"].upper() for x in L}; by_name = {}
    for x in L:
        by_name.setdefault(x["name"].lower(), []).append(x["symbol"].upper())
    out = {}
    for slug, u in U.items():
        cands = [by_id[u["gecko_id"]]] if u.get("gecko_id") in by_id else by_name.get((u.get("name") or "").lower(), [])
        for s in cands:
            for c in (s, "1000" + s):
                cl, _ = EL._closes(c)
                if cl is not None:
                    out[slug] = c; break
            if slug in out:
                break
    return out


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    M = json.loads((D / "monthly_supply.json").read_text()); mp = mapping()
    S = {}
    for slug, coin in mp.items():
        m = M.get(slug) or {}
        if m:
            s = pd.Series({pd.Timestamp(int(k), unit="s"): v for k, v in m.items()}).sort_index(); S[coin] = s.groupby(level=0).last()
    S = pd.DataFrame(S).sort_index()
    C, F = {}, {}
    for c in S.columns:
        cl, fu = EL._closes(c); cl = cl[~cl.index.duplicated()].copy(); cl.index = cl.index + pd.Timedelta(hours=1); C[c] = cl
        F[c] = fu.groupby(level=0).sum() if fu is not None and len(fu) else pd.Series(dtype=float)
    C = pd.DataFrame(C).reindex(idx); R = C.pct_change(fill_method=None).fillna(0.0)
    Fd = pd.DataFrame({c: F[c].reindex(idx).fillna(0.0) for c in C.columns})
    W = pd.DataFrame(0.0, index=idx, columns=C.columns); months = pd.date_range("2021-12-01", "2026-09-01", freq="MS"); n_el = []
    for m in months:
        if m not in S.index:
            continue
        ahead = m + pd.DateOffset(months=12)
        now = S.loc[m]; fut = S.loc[S.index[S.index <= ahead][-1]] if (S.index <= ahead).any() else now
        ok = [c for c in S.columns if now.get(c, 0) > 0 and np.isfinite(C[c].loc[m:m + pd.Timedelta(hours=2)]).any()]
        if len(ok) < 9:
            continue
        dil = (fut[ok] / now[ok] - 1).sort_values(); q = len(dil) // 3; n_el.append(len(ok))
        end = m + pd.offsets.MonthBegin(1)
        rows = (W.index >= m) & (W.index < end)
        W.loc[rows, dil.index[:q]] = 0.5 / q; W.loc[rows, dil.index[-q:]] = -0.5 / q
    W = W.where(C.notna(), 0.0); pos = W.shift(1).fillna(0.0)
    h = (pos * R).sum(axis=1) - (pos * Fd).sum(axis=1) - W.diff().abs().sum(axis=1) * 8e-4
    r = book(V8.assign(**{"dilution factor": h}))
    hu, _ = RB.venue(list(R16.events().items()) + list(R22.upbit_events().items()), idx); hf, _ = R32.sleeve(R32.events()["futures delisting"], 14, idx)
    ha, _ = RB.venue(list(R34.events().items()), idx); hh, _ = RB.venue(list(R42.events().items()), idx)
    HC = V8.assign(**{"venue listing short": hu, "futures-delisting short": hf, "binance add short": ha, "hodler short": hh})
    out = {"reference v9.8": ref if (ref := book(V8)) else None, "coins with supply series and a perp": int(S.shape[1]),
           "eligible coins per month: median": float(np.median(n_el)) if n_el else 0, "months traded": len(n_el),
           "sleeve 2022 / 23-24 / 25-26": per(h), "corr with event short": round(float(dd(h.loc["2022":]).corr(dd(s8.loc["2022":]))), 3),
           "book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3))),
           "ALL + add + HODLer": book(HC), "ALL + add + HODLer + dilution": book(HC.assign(**{"dilution factor": h}))}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r43_dilution.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
