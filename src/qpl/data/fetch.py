"""Fetch the pinned raw data sources with partial git clones.

Only public GitHub repositories are used because the research environment's
network policy blocks the usual market-data vendors (Yahoo, Dukascopy, Stooq,
HistData, Kaggle). Commits are pinned in config/data_sources.json.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CFG = json.loads((ROOT / "config" / "data_sources.json").read_text())
RAW = ROOT / "data" / "raw"


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    out = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True,
                         env={"GIT_TERMINAL_PROMPT": "0", **__import__("os").environ})
    return out.stdout


def _partial_clone(repo: str, commit: str, dest: Path, paths: list[str]) -> None:
    if not (dest / ".git").exists():
        dest.mkdir(parents=True, exist_ok=True)
        _run(["git", "init", "-q"], dest)
        _run(["git", "config", "gc.auto", "0"], dest)
        _run(["git", "remote", "add", "origin", repo], dest)
    _run(["git", "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", commit], dest)
    missing = [p for p in paths if not (dest / p).exists()]
    if missing:
        _run(["git", "checkout", "-q", "FETCH_HEAD", "--", *missing], dest)


def dukascopy_paths() -> list[str]:
    c = CFG["dukascopy_github"]
    return [tpl.format(tf=tf) for tpl in c["files"].values() for tf in c["timeframes"]]


def topstepx_paths(listing: list[str]) -> list[str]:
    c = CFG["topstepx_github"]
    keep = []
    for p in listing:
        parts = p.split("/")
        if len(parts) != 2 or parts[0] not in c["symbols"]:
            continue
        if any(f"_{tf}_" in parts[1] for tf in c["timeframes"]):
            keep.append(p)
    return keep


def fetch_all() -> None:
    d = CFG["dukascopy_github"]
    dest = RAW / "dukascopy"
    _partial_clone(d["repo"], d["commit"], dest, dukascopy_paths())

    t = CFG["topstepx_github"]
    dest = RAW / "topstepx"
    _partial_clone(t["repo"], t["commit"], dest, [])
    listing = _run(["git", "ls-tree", "-r", "--name-only", "FETCH_HEAD"], dest).split()
    paths = topstepx_paths(listing)
    _run(["git", "checkout", "-q", "FETCH_HEAD", "--", *paths], dest)


if __name__ == "__main__":
    fetch_all()
    print("raw data fetched into", RAW)
