"""Gen359 (config/gen359_protocol.json): final rules for the stress book, chosen on 2020-24. Writes results/gen359.json."""
import json
import numpy as np
import pandas as pd
import stressbook as SB
out = {}; s24 = lambda h: SB.sh(SB.daily(h), "2020", "2024")
D1 = {f"side {s} {'limit' if m else 'market'}": SB.premium_spike(side=s, maker=m) for s in (0, 1) for m in (False, True)}
out["D1"] = {k: {"2020-24": round(s24(v), 3), "periods": SB.periods(SB.daily(v))} for k, v in D1.items()}
c1 = max(D1, key=lambda k: s24(D1[k])); out["D1 chosen"] = c1; print("D1", out["D1"], c1, flush=True)
btc = SB.D["BTC"]; up = btc > btc.rolling(200).mean()
D2 = {f"{fn} {'limit' if m else 'market'}": SB.crash_reversal(filt=(up if fn == "BTC>200d" else None), maker=m) for fn in ("none", "BTC>200d") for m in (False, True)}
out["D2"] = {k: {"2020-24": round(s24(v), 3), "periods": SB.periods(SB.daily(v))} for k, v in D2.items()}
c2 = max(D2, key=lambda k: s24(D2[k])); out["D2 chosen"] = c2; print("D2", out["D2"], c2, flush=True)
NF = {f"{'limit' if m else 'market'}": SB.negative_funding(maker=m) for m in (False, True)}
nfk = max(NF, key=lambda k: s24(NF[k]))
base = {"premium spike": D1[c1], "crash reversal": D2[c2]}
b0 = SB.build(base); b1 = SB.build({**base, "negative funding": NF[nfk]})
out["D3"] = {"without": round(SB.sh(b0, "2020", "2024"), 3), "with": round(SB.sh(b1, "2020", "2024"), 3), "execution": nfk}
inc = SB.sh(b1, "2020", "2024") > SB.sh(b0, "2020", "2024"); out["D3 chosen"] = "in" if inc else "out"
final = {**base, **({"negative funding": NF[nfk]} if inc else {})}
bv0, bv1 = SB.build(final), SB.build(final, voltarget=True)
out["D4"] = {"none": round(SB.sh(bv0, "2020", "2024"), 3), "vol target": round(SB.sh(bv1, "2020", "2024"), 3)}
vt = SB.sh(bv1, "2020", "2024") > SB.sh(bv0, "2020", "2024"); out["D4 chosen"] = "vol target" if vt else "none"
bk = bv1 if vt else bv0; out["BOOK"] = SB.evaluate(bk); out["BOOK"]["sleeves"] = list(final)
print(json.dumps({k: out[k] for k in ("D3", "D3 chosen", "D4", "D4 chosen", "BOOK")}, indent=0))
bk.to_frame("stress book").to_parquet(SB.ROOT / "results/gen359_book.parquet")
pd.DataFrame({k: SB.daily(v) for k, v in final.items()}).to_parquet(SB.ROOT / "results/gen359_sleeves.parquet")
json.dump(out, open(SB.ROOT / "results/gen359.json", "w"), indent=1)
