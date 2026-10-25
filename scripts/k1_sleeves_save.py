"""Save the K1 / v9.0 sleeve P&L (Gen373 construction, point-in-time C*) to results/k1_sleeves.parquet for light follow-up scripts.
    cd scripts && python k1_sleeves_save.py <v86 dump>"""
import sys
from pathlib import Path
DUMP = sys.argv[1]; ROOT = Path(__file__).resolve().parents[1]
g = {"__file__": str(ROOT / "scripts/gen373_honest_cstar.py")}
s = open(ROOT / "scripts/gen373_honest_cstar.py").read().split("\nout = {")[0].replace("DUMP = sys.argv[1]; sys.argv = sys.argv[:1]", f"DUMP = {DUMP!r}")
exec(compile(s, "g373", "exec"), g)
K1C = ["C*", "cascade limit strict", "trend 4h", "Weiss expiry", "delev bounce", "ridge ML", "alt kimchi"]
g["H0"][K1C].assign(**{"C*": g["cp"]}).to_parquet(ROOT / "results/k1_sleeves.parquet"); print("saved")
