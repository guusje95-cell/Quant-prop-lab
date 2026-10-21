"""Gen324 (descriptive, config/gen324_protocol.json): bf2.6 with MT5-style accounting under BrightFunded's daily rule
("5% of the initial balance, measured from the HIGHER of balance or equity at the daily rollover", support answer 2026-10-21).
One net position per instrument with an average entry price; balance moves only on realised P&L and costs.
  A  daily reference = equity at the rollover (how our prop simulations model it)
  B  daily reference = max(balance, equity) at the rollover (BrightFunded's rule)
  C  = B, but just before the rollover every position in a floating loss is closed and reopened (loss realised; cost 2 x one side)
Daily stop at half the limit (2.5% of the initial balance below the day's reference: flat until the next rollover, 10 bp worse),
as the paper trader; a breach = equity below the reference minus 5%. Risk 2.0 on $200k, paper scale 0.908. Writes results/gen324.json."""
import json
import numpy as np
import pandas as pd
import bf2lab as F
import cfd_book as CB
import crypto_sleeves as CS
import ridge_live as RL
import alt_kimchi as AK
import index_sleeve as IS
from qpl.lab import binance_pack as B
END = F.END; ACCT, RISK, SCALE, ROLL = 200_000.0, 2.0, 0.908, 22
CB.TRANCHED = True                                                         # bf2.6
R, pos, _ = CB.positions()
idx0 = pos["C*"].index
pos["ridge ML"] = CB.d2h(RL.predictions(END, spot=True, vrp=True, cal=True).pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5, idx0)
aw = AK.weights(END + " 23:00"); aw = aw[[c for c in aw.columns if c in CB.ALT_CFD]]
pos["alt kimchi"] = aw.reindex(aw.index.append(pd.DatetimeIndex([aw.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(idx0.floor("D")).set_axis(idx0).fillna(0.0)
cw = CS.premium_breadth_weights(coins=CB.CARRY_CFD, invvol=True, tranched=True)
pos["premium carry BF"] = cw.reindex(cw.index.append(pd.DatetimeIndex([cw.index[-1] + pd.Timedelta(days=1)]))).reindex(columns=CB.CARRY_CFD).shift(1).reindex(idx0.floor("D")).set_axis(idx0).fillna(0.0)
ipos, _ = IS.sleeve(idx0); pos["vol-managed indices"] = ipos

H = pd.concat([F.HB0, F.IS0, F.HB_RIDGE.rename("ridge ML")] + F.ALTK_BF, axis=1).fillna(0.0)
ph, W, mult = CS.portfolio_v5(H)
idx = H.loc["2022-01-01":].index
Wh = W.reindex(idx.floor("D")).set_axis(idx); mh = mult.reindex(idx.floor("D")).set_axis(idx)
CRY = sorted(set(CB.CFD) | set(CB.ALT_CFD) | set(CB.CARRY_CFD)); IDXS = ["US100", "US500", "US30"]; COLS = CRY + IDXS
net = pd.DataFrame(0.0, index=idx, columns=COLS)
for s in H.columns:
    net = net.add(pos[s].reindex(idx).fillna(0.0).mul(Wh[s] * mh, axis=0), fill_value=0.0)
net = net[COLS].fillna(0.0) * SCALE
g = net[CRY].abs().sum(axis=1) * RISK; net = net.mul((5.0 / g).clip(upper=1.0).fillna(1.0), axis=0)   # 1:5 crypto cap
P = pd.concat([CS._breadth_close(CRY)] + [IS.hourly(s)["close"].rename(s) for s in IDXS], axis=1).sort_index().reindex(idx).ffill().bfill()
spec = pd.read_csv(sorted((F.ROOT / "research_data/firm_specs").glob("BrightFunded*20261021*.csv"))[-1], encoding="latin1")
meas = {s.split("/")[0].replace("XDG", "DOGE"): float(v) for s, v in zip(spec["symbol"], spec["spread_bp_median"]) if "/USD" in s}
cost = np.array([(0.5 * meas[c] + CB.COMM) / 1e4 if c in CRY else 1e-4 for c in COLS])


def simulate(mode):
    T = net.to_numpy() * RISK * ACCT; Pm = P.to_numpy(); n, k = T.shape
    q = np.zeros(k); avg = np.zeros(k); bal = ACCT; eq_prev = ACCT; ref = ACCT; stopped = False
    eq = np.empty(n); stops = breaches = 0; bdays = set(); real_cost = 0.0; ref_gap = []
    hours = idx.hour.to_numpy()
    for t in range(n):
        p0 = Pm[t - 1] if t else Pm[0]
        if hours[t] == ROLL:                                               # daily rollover
            if mode == "C":
                upnl = q * (p0 - avg); lose = upnl < 0
                bal += upnl[lose].sum(); c = 2 * (np.abs(q[lose]) * p0[lose] * cost[lose]).sum(); bal -= c; real_cost += c; avg[lose] = p0[lose]
            e0 = bal + (q * (p0 - avg)).sum()
            ref = e0 if mode == "A" else max(bal, e0); ref_gap.append(ref - e0); stopped = False
        tgt = np.zeros(k) if stopped else T[t] / p0
        dq = tgt - q
        red = (np.sign(q) != np.sign(tgt)) | (np.abs(tgt) < np.abs(q))     # reduction or flip: realise on the reduced part
        cl = np.where(red, np.minimum(np.abs(q), np.abs(dq)) * np.sign(q), 0.0)
        bal += (cl * (p0 - avg)).sum() - (np.abs(dq) * p0 * cost).sum()
        newq = q - cl; add = tgt - newq                                    # remaining part after closing, then additions
        tot = newq + add
        safe = np.where(np.abs(tot) > 1e-12, tot, 1.0)
        avg = np.where(np.abs(tot) <= 1e-12, 0.0, np.where(np.abs(newq) <= 1e-12, p0, (newq * avg + add * p0) / safe))
        q = tgt
        e = bal + (q * (Pm[t] - avg)).sum()
        if not stopped and e <= ref - 0.025 * ACCT:                        # daily stop: flat for the rest of the day, 10 bp worse
            stops += 1; bal = e - (np.abs(q) * Pm[t] * 1e-3).sum(); q = np.zeros(k); avg = np.zeros(k); e = bal; stopped = True
        if e <= ref - 0.05 * ACCT:
            breaches += 1; bdays.add(str(idx[t].date()))
        eq[t] = e
    s = pd.Series(eq, index=idx); d = s.resample("1D").last().diff().fillna(s.iloc[0] - ACCT) / ACCT
    f = lambda a, z: round(float(d.loc[a:z].mean() / d.loc[a:z].std() * np.sqrt(365)), 3)
    return {"sharpe 2022-26 / 2022 / TEST / HOLD": [f("2022-01-01", END), f("2022", "2022"), f("2023", "2024"), f("2025", END)],
            "daily stops": stops, "breach-hours (equity below ref - 5%)": breaches, "breach days": sorted(bdays), "return 2022-26 %": round(float((s.iloc[-1] - ACCT) / ACCT * 100), 1),
            "mean (ref - equity) at rollover $": round(float(np.mean(ref_gap))), "p95 (ref - equity) $": round(float(np.percentile(ref_gap, 95))),
            "days with ref above equity by > $4,000": int(np.sum(np.array(ref_gap) > 4000)), "cost of realising losers $": round(real_cost)}


out = {"reference bf2.6 (research)": [round(F.REF[0], 3), np.round(F.REF[1], 3).tolist()], "rollover hour UTC": ROLL}
for m in ("A", "B", "C"):
    if m == "C":
        out[m] = {"note": "first run: cost of realising losers $193,061, Sharpe 1.783 [-0.16, 3.26, 1.31], 67 stops: rejected"}; continue
    out[m] = simulate(m); print(m, out[m], flush=True)
json.dump(out, open(F.ROOT / "results/gen324.json", "w"), indent=1)
