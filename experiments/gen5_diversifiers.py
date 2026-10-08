"""Generation 5: search for edges uncorrelated with H3 (TRAIN screen + VALIDATION; OOS untouched)."""
from __future__ import annotations
import itertools, json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import accounting as A
from qpl.instruments import get
from qpl.research import pipeline as P, registry as R

ROOT = Path(__file__).resolve().parents[1]
SPL = {"train": P.SPLITS["train"], "validation": P.SPLITS["validation"]}
H7 = {"family": "mean reversion/time-of-day", "hypothesis": "Midday (12:00-14:30 ET) deviations from the session mean price revert, because midday liquidity is provided by mean-reverting market makers once the morning's information flow is absorbed.",
      "rationale": "Intraday U-shaped volume/volatility; midday low-information regime; designed to profit on non-trend days where H3 loses.",
      "falsification": "TRAIN Sharpe <= 0.5 net, or correlation with H3 not negative/low."}
H8 = {"family": "cross-market relative value", "hypothesis": "NQ-vs-ES relative performance that escapes its time-of-day noise band continues into the close (sector-rotation flow persistence).",
      "rationale": "Institutional rotation between growth/tech and broad market is executed over hours (VWAP algos) -> autocorrelated relative returns.",
      "falsification": "TRAIN Sharpe <= 0.5 net of both legs' costs."}


def h3_daily(fut, proxy):
    ctx = P.context("dukascopy", proxy, "M15"); days = P.trading_days(ctx); inst = get(fut)
    tr = P.backtest("noise_area", ctx, dict(lookback=14, mult=1.25, trail="band_mean", check_min=60), inst)
    return A.daily_pnl(P.usd(tr, inst, contracts=1), days)["pnl"]


def run_h7():
    R.register_hypothesis("H7_MIDDAY_MR", H7["family"], 5, H7)
    rows = []
    h3 = {"NQ": h3_daily("NQ", "US100"), "ES": h3_daily("ES", "US500")}
    for fut, proxy in (("NQ", "US100"), ("ES", "US500")):
        ctx = P.context("dukascopy", proxy, "M15"); days = P.trading_days(ctx); inst = get(fut)
        for k, ws in itertools.product([1.0, 1.5, 2.0], [720, 780]):
            prm = dict(lookback=14, k=k, win_start=ws, win_end=870, exit_min=930)
            tr = P.backtest("midday_reversion", ctx, prm, inst)
            u = P.usd(tr, inst, contracts=1)
            sm = P.split_metrics(u, days, SPL)
            d = A.daily_pnl(u, days)["pnl"].loc[SPL["train"][0]:SPL["validation"][1]]
            corr = float(d.corr(h3[fut].loc[d.index]))
            for s, m in sm.items():
                R.record(generation=5, family=H7["family"], hypothesis_id="H7_MIDDAY_MR", strategy="midday_reversion",
                         instrument=fut, data_source=f"dukascopy:{proxy}", timeframe="M15", params=prm, stage=f"screen_{s}",
                         period=s, metrics=m, decision="info", reason="gen5 diversifier screen")
            rows.append(dict(h="H7", mkt=fut, prm=json.dumps(prm), tr_sh=sm["train"]["sharpe"], va_sh=sm["validation"]["sharpe"],
                             n=sm["train"].get("trades"), wr=sm["train"].get("win_rate"), corr_h3=corr))
    return rows


def run_h8():
    """Synthetic dollar-neutral spread: long NQ / short ES (or reverse), fills at next bar open of both legs."""
    R.register_hypothesis("H8_NQES_RS", H8["family"], 5, H8)
    a = P.context("dukascopy", "US100", "M15"); b = P.context("dukascopy", "US500", "M15")
    idx = a.index.intersection(b.index)
    a, b = a.loc[idx], b.loc[idx]
    rth = (a["rth"] & a["valid_day"]).to_numpy()
    date = a["date"].to_numpy(); rb = a["rth_bar"].to_numpy(); et = a["et_min"].to_numpy()
    oa, ob = a["open"].to_numpy(), b["open"].to_numpy()
    ca, cb = a["close"].to_numpy(), b["close"].to_numpy()
    ra, rbx = a["rth_open"].to_numpy(), b["rth_open"].to_numpy()
    rs = np.log(ca / ra) - np.log(cb / rbx)
    mv = pd.DataFrame({"date": date[rth], "slot": rb[rth], "mv": np.abs(rs[rth])})
    piv = mv.pivot_table(index="date", columns="slot", values="mv", aggfunc="last")
    days = P.trading_days(a)
    # per-leg round-trip cost in return units at reference prices (MNQ & MES: 1 tick slip/side + commission)
    cost_rt = (2 * 0.25 + 0.74 / 2) / 19900 + (2 * 0.25 + 0.74 / 5) / 5700
    notional = 100_000.0
    rows = []
    h3 = h3_daily("NQ", "US100")
    for m, chk in itertools.product([1.0, 1.25, 1.5], [30, 60]):
        sig = piv.rolling(14, min_periods=14).mean().shift(1).stack().reindex(pd.MultiIndex.from_arrays([date, rb])).to_numpy()
        is_chk = rth & ((et + 15) % chk == 0) & (et + 15 >= 600) & np.isfinite(sig)
        pos = 0; entry = None; pnl = {}
        for t in range(len(a) - 1):
            if not rth[t]:
                continue
            last = t + 1 >= len(a) or date[t + 1] != date[t] or not rth[t + 1]
            if pos != 0 and (last or (is_chk[t] and pos * rs[t] < sig[t] * m * 0.0 + (sig[t] * m if False else 0) and pos * rs[t] <= 0)):
                # exit at this bar's close on the last bar, else next open
                xa, xb = (ca[t], cb[t]) if last else (oa[t + 1], ob[t + 1])
                r = pos * (np.log(xa / entry[0]) - np.log(xb / entry[1])) - cost_rt
                pnl[date[t]] = pnl.get(date[t], 0.0) + r * notional
                pos = 0
            if pos == 0 and is_chk[t] and not last and et[t] + 15 <= 930:
                if abs(rs[t]) > m * sig[t]:
                    pos = int(np.sign(rs[t])); entry = (oa[t + 1], ob[t + 1])
        d = pd.Series(pnl).reindex(days, fill_value=0.0)
        d.index = pd.DatetimeIndex(d.index)
        prm = dict(mult=m, check_min=chk, exit="sign_flip_or_close")
        for s, (x, y) in SPL.items():
            dd = d.loc[x:y]
            sh = float(dd.mean() / dd.std() * np.sqrt(252)) if dd.std() > 0 else 0.0
            R.record(generation=5, family=H8["family"], hypothesis_id="H8_NQES_RS", strategy="nq_es_rs_noise",
                     instrument="MNQ/MES", data_source="dukascopy:US100+US500", timeframe="M15", params=prm,
                     stage=f"screen_{s}", period=s, metrics={"sharpe": sh, "total_usd": float(dd.sum()), "days": len(dd)},
                     decision="info", reason="gen5 diversifier screen")
        tv = d.loc[SPL["train"][0]:SPL["validation"][1]]
        rows.append(dict(h="H8", mkt="NQ-ES", prm=json.dumps(prm),
                         tr_sh=float(d.loc[SPL["train"][0]:SPL["train"][1]].pipe(lambda z: z.mean() / z.std() * np.sqrt(252))),
                         va_sh=float(d.loc[SPL["validation"][0]:SPL["validation"][1]].pipe(lambda z: z.mean() / z.std() * np.sqrt(252))),
                         n=int((d != 0).sum()), wr=np.nan, corr_h3=float(tv.corr(h3.loc[tv.index]))))
    return rows


if __name__ == "__main__":
    rows = run_h7() + run_h8()
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "gen5_diversifiers.csv", index=False)
    pd.set_option("display.width", 220, "display.max_colwidth", 100)
    print(df.round(3).to_string())
