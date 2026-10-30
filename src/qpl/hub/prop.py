"""Prop-firm intelligence: firms, versioned rule sets (simulator parameters) and per-field FACTS with source URL, date checked, quote,
status (verified / uncertain / assumption / not_found / ambiguous) and confidence; compatibility of a strategy profile with a rule
set; challenge + funded simulation through the project's rule engine (qpl.lab.propfirms) with every result stored next to the
exact rule-set version it used. Nothing here buys, connects or trades. A simulated payout is a model estimate, never cash."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from qpl.hub.db import ROOT, audit, jhash, now, tx
from qpl.lab import propfirms as PF

STALE_DAYS = 30
FIRM_INFO = {  # key -> (name, markets, platforms, website)
    "hyrotrader": ("HyroTrader", ["crypto_perps"], ["Bybit (API)", "CLEO"], "https://www.hyrotrader.com"),
    "cft": ("Crypto Fund Trader", ["crypto_perps", "crypto_cfd"], ["Bybit", "MT5"], "https://cryptofundtrader.com"),
    "ftmo": ("FTMO", ["cfd", "crypto_cfd"], ["MT4", "MT5", "cTrader", "DXtrade"], "https://ftmo.com"),
    "brightfunded": ("BrightFunded", ["cfd", "crypto_cfd"], ["MT5", "cTrader", "DXtrade"], "https://brightfunded.com"),
    "breakout": ("Breakout", ["crypto_perps"], ["Breakout terminal"], "https://www.breakoutprop.com"),
    "sizeprop": ("SizeProp", ["crypto_perps"], ["SizeProp terminal"], "https://sizeprop.com"),
    "fundednext": ("FundedNext", ["cfd", "crypto_cfd"], ["MT4", "MT5", "cTrader"], "https://fundednext.com"),
    "topstep": ("Topstep", ["cme_futures"], ["TopstepX", "NinjaTrader", "Tradovate"], "https://www.topstep.com"),
    "apex": ("Apex Trader Funding", ["cme_futures"], ["Rithmic", "Tradovate"], "https://apextraderfunding.com"),
}
PRESET_FIRM = {"Crypto Fund Trader": "cft", "FTMO": "ftmo", "HyroTrader": "hyrotrader", "Breakout": "breakout", "SizeProp": "sizeprop",
               "FundedNext": "fundednext", "BrightFunded": "brightfunded", "Topstep": "topstep", "Apex": "apex"}
SIM_FIELDS = ("account", "fee", "targets", "daily_loss", "daily_basis", "daily_intraday", "max_loss", "max_type", "trailing_intraday", "min_days",
              "max_days", "split", "payout_every", "payout_fee", "refund_fee", "funded_fee", "fee_monthly", "reset_hour_utc", "payout_min", "first_payout_days")
# facts the compatibility engine needs that are not simulator parameters
POLICY_FIELDS = ("bots_allowed", "api_trading", "overnight_holding", "weekend_holding", "news_trading", "country_netherlands", "copy_trading",
                 "max_accounts", "max_allocation_usd", "low_cap_position_cap", "funded_notional_cap_x", "consistency_rule", "instruments")


def _firm_id(c, key):
    name, markets, plat, web = FIRM_INFO[key]
    r = c.execute("SELECT id FROM prop_firms WHERE key=?", (key,)).fetchone()
    if r:
        return r["id"]
    return c.execute("INSERT INTO prop_firms (key, name, markets, platforms, website) VALUES (?,?,?,?,?)",
                     (key, name, json.dumps(markets), json.dumps(plat), web)).lastrowid


def add_rule_set(c: sqlite3.Connection, firm_key: str, account_type: str, params: dict, facts: list[dict], effective_from: str,
                 actor: str = "system") -> int:
    """New rule-set version (old versions stay; the previous one is marked superseded). Identical params -> existing id."""
    h = jhash(params)
    with tx(c):
        fid = _firm_id(c, firm_key)
        last = c.execute("SELECT id, version, params_hash FROM prop_rule_sets WHERE firm_id=? AND account_type=? ORDER BY version DESC LIMIT 1",
                         (fid, account_type)).fetchone()
        if last and last["params_hash"] == h:
            rid = last["id"]
        else:
            v = (last["version"] + 1) if last else 1
            rid = c.execute("INSERT INTO prop_rule_sets (firm_id, account_type, version, effective_from, params, params_hash, created_at) VALUES (?,?,?,?,?,?,?)",
                            (fid, account_type, v, effective_from, json.dumps(params, default=str), h, now())).lastrowid
            if last:
                c.execute("UPDATE prop_rule_sets SET superseded_at=? WHERE id=?", (now(), last["id"]))
            audit(c, actor, "add_rule_set", "prop_rule_sets", rid, {"firm": firm_key, "account_type": account_type, "version": v})
        have = {(r["field"], r["source_url"], r["checked_at"]) for r in c.execute("SELECT field, source_url, checked_at FROM prop_rule_facts WHERE rule_set_id=?", (rid,))}
        for f in facts:
            if (f["field"], f.get("source_url"), f.get("checked_at")) in have:
                continue
            c.execute("INSERT INTO prop_rule_facts (rule_set_id, field, value, status, source_url, quote, checked_at, confidence, note) VALUES (?,?,?,?,?,?,?,?,?)",
                      (rid, f["field"], json.dumps(f.get("value"), default=str), f["status"], f.get("source_url"), f.get("quote"), f.get("checked_at"),
                       f.get("confidence"), f.get("note")))
    return rid


def seed_from_project(c: sqlite3.Connection) -> dict:
    """Rule sets from the simulator presets (project snapshot, every field 'uncertain' with the preset note as provenance) and the
    sourced field values of config/prop_firms.json (status as recorded there on 2026-10-09)."""
    n = 0
    for name, f in PF.PRESETS.items():
        if name == "Custom":
            continue
        fk = next((v for k, v in PRESET_FIRM.items() if name.startswith(k)), None)
        if fk is None:
            continue
        p = {k: v for k, v in asdict(f).items() if k in SIM_FIELDS}
        facts = [{"field": k, "value": v, "status": "uncertain", "source_url": "src/qpl/lab/propfirms.py PRESETS", "checked_at": None, "confidence": "low",
                  "note": f.note or "project preset; verify on the firm's official rule pages before any decision"} for k, v in p.items()]
        add_rule_set(c, fk, name, p, facts, effective_from="2026-10-26"); n += 1
    cfg = json.loads((ROOT / "config/prop_firms.json").read_text())
    for key, e in cfg["firms"].items():
        fk = next((v for k, v in PRESET_FIRM.items() if str(e.get("firm", "")).startswith(k)), None)
        if fk is None:
            continue
        facts = []
        for field, val in e.items():
            if isinstance(val, dict) and "status" in val:
                st = {"VERIFIED": "verified", "UNCERTAIN": "uncertain", "NOT_FOUND": "not_found"}.get(str(val["status"]).split()[0].upper(), "uncertain")
                facts.append({"field": field, "value": val.get("value"), "status": st, "source_url": val.get("source"), "checked_at": "2026-10-09",
                              "confidence": "medium" if st == "verified" else "low", "note": val.get("conflict")})
        add_rule_set(c, fk, f"{e.get('product', key)} (config/prop_firms.json)", {"source": "config/prop_firms.json", "key": key}, facts, effective_from="2026-10-09"); n += 1
    return {"rule_sets": n}


def facts(c: sqlite3.Connection, rule_set_id: int) -> dict:
    """Latest fact per field (newest checked_at, then newest id)."""
    out = {}
    for r in c.execute("SELECT * FROM prop_rule_facts WHERE rule_set_id=? ORDER BY COALESCE(checked_at,''), id", (rule_set_id,)):
        out[r["field"]] = dict(r)
    return out


def stale_facts(c: sqlite3.Connection, days: int = STALE_DAYS) -> list[dict]:
    cut = (pd.Timestamp(now()) - pd.Timedelta(days=days)).isoformat()
    return [dict(r) for r in c.execute(
        "SELECT f.field, f.status, f.checked_at, s.account_type, p.key firm FROM prop_rule_facts f JOIN prop_rule_sets s ON s.id=f.rule_set_id "
        "JOIN prop_firms p ON p.id=s.firm_id WHERE s.superseded_at IS NULL AND (f.checked_at IS NULL OR f.checked_at < ?)", (cut,))]


# ---------------------------------------------------------------------------------------------------------- compatibility
V98_PROFILE = {"name": "crypto book v9.8", "markets": ["crypto_perps"], "venue": "Bybit USDT perps", "needs_api_bot": True, "holds_overnight": True,
               "holds_weekend": True, "trades_news": True, "orders_per_day": 20, "uses_low_cap_coins": True, "max_low_cap_frac": 0.05,
               "funded_notional_x": 1.9, "worst_day_at_risk_1_5": None, "country": "Netherlands"}


def compatibility(c: sqlite3.Connection, rule_set_id: int, profile: dict = V98_PROFILE, version_id: int | None = None,
                  portfolio_version_id: int | None = None, store: bool = True) -> dict:
    rs = c.execute("SELECT s.*, p.key firm, p.markets FROM prop_rule_sets s JOIN prop_firms p ON p.id=s.firm_id WHERE s.id=?", (rule_set_id,)).fetchone()
    F = facts(c, rule_set_id); reasons, unknown, hard_no = [], [], []
    mk = set(json.loads(rs["markets"] or "[]"))
    if not set(profile["markets"]) & mk:
        hard_no.append(f"firm markets {sorted(mk)} do not include {profile['markets']}")

    def chk(field, need, label):
        f = F.get(field)
        if f is None:
            unknown.append(f"{label}: no recorded fact ({field})"); return
        v = json.loads(f["value"]) if f["value"] else None
        ok = need(v)
        tag = f"{label}: {v!r} [{f['status']}, {f['source_url'] or 'no source'}, checked {f['checked_at'] or 'never'}]"
        if ok is False and f["status"] == "verified":
            hard_no.append(tag)
        elif ok is False:
            reasons.append("probably not: " + tag)
        elif f["status"] != "verified":
            unknown.append("unverified: " + tag)
        else:
            reasons.append("ok: " + tag)
    if profile.get("needs_api_bot"):
        chk("bots_allowed", lambda v: bool(v) if v is not None else None, "automated trading / bots")
    if profile.get("holds_overnight"):
        chk("overnight_holding", lambda v: bool(v) if v is not None else None, "overnight holding")
    if profile.get("holds_weekend"):
        chk("weekend_holding", lambda v: bool(v) if v is not None else None, "weekend holding")
    chk("country_netherlands", lambda v: bool(v) if v is not None else None, "accepts residents of the Netherlands")
    if profile.get("uses_low_cap_coins"):
        chk("low_cap_position_cap", lambda v: (v is None) or float(v) >= profile["max_low_cap_frac"], "low-cap coin position cap")
    status = ("incompatible" if hard_no else "verified_compatible" if not unknown and not any(r.startswith("probably not") for r in reasons)
              else "potentially_compatible" if not any(r.startswith("probably not") for r in reasons) else "insufficient_evidence")
    if status == "verified_compatible" and not reasons:
        status = "insufficient_evidence"
    out = {"rule_set_id": rule_set_id, "firm": rs["firm"], "account_type": rs["account_type"], "version": rs["version"], "status": status,
           "blocking": hard_no, "evidence": reasons, "missing_or_unverified": unknown, "profile": profile["name"]}
    if store:
        with tx(c):
            c.execute("INSERT INTO compat_assessments (version_id, portfolio_version_id, rule_set_id, status, reasons, ts) VALUES (?,?,?,?,?,?)",
                      (version_id, portfolio_version_id, rule_set_id, status, json.dumps(out), now()))
    return out


# ---------------------------------------------------------------------------------------------------------- simulation
def daily_with_stop(h: pd.Series, stop: float) -> pd.DataFrame:
    """Hourly returns -> daily net / worst / best with the trader's own daily equity stop (flat at -stop, 0.1% exit slippage)."""
    out = []
    for d, g in h.groupby(h.index.floor("D")):
        p = np.cumprod(1 + g.to_numpy())
        if stop > 0 and (p <= 1 - stop).any():
            k = int(np.argmax(p <= 1 - stop)); close = p[k] - 0.001
            out.append((d, close - 1, min(p[:k + 1].min(), close) - 1, max(p[:k + 1].max(), 1.0) - 1))
        else:
            out.append((d, p[-1] - 1, min(p.min(), 1.0) - 1, max(p.max(), 1.0) - 1))
    return pd.DataFrame(out, columns=["day", "net", "worst", "best"]).set_index("day")


def shift_to_sharpe(h: pd.Series, target: float, start: str = "2022") -> pd.Series:
    """Lower an hourly return series' mean so its daily Sharpe equals `target` (volatility and path shape unchanged): the planning
    scenarios ('what if the live Sharpe is only X')."""
    d = h.loc[start:].groupby(h.loc[start:].index.floor("D")).sum()
    return h - (d.mean() - target * d.std() / np.sqrt(365)) / 24


def simulate(c: sqlite3.Connection, rule_set_id: int, hourly_unit: pd.Series, subject: str, returns_source: str, sharpe_level: float | None,
             risk_challenge: float = 1.5, risk_funded: float = 1.5, stop_frac: float = 0.5, window=("2025-01-01", "2026-09-30 23:00"),
             budget: int = 3, horizon_days: int = 730, n_boot: int = 400, seed: int = 11, store: bool = True) -> dict:
    """Challenge + funded simulation (block bootstrap of the window, 20-day blocks) for one rule set. `hourly_unit` = book returns at
    unit risk (15% vol). Results are conditional model estimates."""
    rs = c.execute("SELECT * FROM prop_rule_sets WHERE id=?", (rule_set_id,)).fetchone(); p = json.loads(rs["params"])
    if "account" not in p:
        return {"status": "rule set has no simulator parameters", "rule_set_id": rule_set_id}
    f = PF.firm_from_dict({**asdict(PF.Firm()), **p})
    h = shift_to_sharpe(hourly_unit, sharpe_level) if sharpe_level is not None else hourly_unit
    h = h.loc[window[0]:window[1]]
    ch = daily_with_stop(h * risk_challenge, stop_frac * f.daily_loss); fd = daily_with_stop(h * risk_funded, stop_frac * f.daily_loss)
    a = PF.attempts(ch, f, 1.0, method="bootstrap", n_boot=n_boot, seed=seed)
    pb = PF.pipeline(ch, f, budget, 1, 1.0, 1.0, daily_fd=fd, horizon_days=horizon_days, method="bootstrap", n_boot=n_boot, block=20, seed=seed)
    res = {"P_pass_single_attempt": a.get("P_pass"), "median_days_to_pass": a.get("median_days_to_pass"), "attempt_outcomes": {k: a.get(k) for k in a if k.startswith("P_")},
           "P_funded_within_budget": pb.get("P_funded"), "P_any_payout": pb.get("P_payout"), "challenges_bought_mean": pb.get("bought"),
           "fees_mean": pb.get("fees"), "payouts_gross_after_split_mean": pb.get("paid"), "net_mean": pb.get("net_mean"), "net_p10": pb.get("net_p10"),
           "net_p50": pb.get("net_p50"), "net_p90": pb.get("net_p90"), "P_net_profit": pb.get("P_profit"), "P_lose_whole_budget": pb.get("P_lose_all_budget"),
           "funded_breaches_mean": pb.get("funded_breaches"), "days_to_first_payout_median": pb.get("days_to_first_payout_median"),
           "net_per_month_mean": pb.get("net_per_month"),
           "caveat": "conditional on the return model (backtest shifted to the stated Sharpe level, block bootstrap of the window); not a forecast; payouts here are modelled eligible payouts after the split, not received cash"}
    cfg = {"risk_challenge": risk_challenge, "risk_funded": risk_funded, "stop_frac": stop_frac, "window": list(window), "budget": budget,
           "horizon_days": horizon_days, "n_boot": n_boot, "seed": seed, "rule_set_version": rs["version"], "params": p}
    if store:
        with tx(c):
            c.execute("INSERT INTO challenge_sims (rule_set_id, subject, returns_source, sharpe_level, config, results, ts) VALUES (?,?,?,?,?,?,?)",
                      (rule_set_id, subject, returns_source, None if sharpe_level is None else str(sharpe_level), json.dumps(cfg, default=str), json.dumps(res, default=str), now()))
    return {"config": cfg, "results": res}
