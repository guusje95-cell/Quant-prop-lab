"""Business finance ledger: real fees, subscriptions, costs and payouts with explicit statuses. A payout moves
planned -> requested -> approved -> received (or rejected); only 'received' counts as cash. Every status change is kept in
finance_tx_history. Nothing here moves money; it records what the user reports."""
from __future__ import annotations

import sqlite3

import pandas as pd

from qpl.hub.db import audit, get_setting, now, tx

FLOW = {"planned": {"requested", "paid", "cancelled"}, "requested": {"approved", "rejected", "cancelled"}, "approved": {"received", "rejected"},
        "received": set(), "rejected": set(), "paid": set(), "cancelled": set()}
INCOME_KINDS = {"payout", "capital_in"}


def add(c: sqlite3.Connection, kind: str, amount: float, currency: str, status: str, ts: str = None, firm: str = None, account: str = None,
        strategy: str = None, market: str = None, external_ref: str = None, note: str = None, actor: str = "user") -> int:
    if amount <= 0:
        raise ValueError("amount is a positive number; the kind says whether it is income or a cost")
    if kind == "payout" and status not in ("planned", "requested", "approved", "received", "rejected"):
        raise ValueError("payout status must be planned / requested / approved / received / rejected")
    if kind != "payout" and status not in ("planned", "paid", "cancelled", "received"):
        raise ValueError("a cost is planned / paid / cancelled")
    if external_ref and c.execute("SELECT id FROM finance_tx WHERE external_ref=?", (external_ref,)).fetchone():
        return c.execute("SELECT id FROM finance_tx WHERE external_ref=?", (external_ref,)).fetchone()["id"]     # idempotent re-entry
    with tx(c):
        i = c.execute("INSERT INTO finance_tx (ts, kind, amount, currency, status, firm, account, strategy, market, external_ref, note, created_at, updated_at) "
                      "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (ts or now(), kind, float(amount), currency.upper(), status, firm, account, strategy, market,
                                                          external_ref, note, now(), now())).lastrowid
        c.execute("INSERT INTO finance_tx_history (tx_id, ts, old_status, new_status, note) VALUES (?,?,?,?,?)", (i, now(), None, status, "created"))
        audit(c, actor, "finance_add", "finance_tx", i, {"kind": kind, "amount": amount, "currency": currency, "status": status})
    return i


def set_status(c: sqlite3.Connection, tx_id: int, new: str, note: str = None, actor: str = "user"):
    r = c.execute("SELECT status FROM finance_tx WHERE id=?", (tx_id,)).fetchone()
    if not r:
        raise KeyError(tx_id)
    if new not in FLOW[r["status"]]:
        raise ValueError(f"{r['status']} -> {new} is not allowed")
    with tx(c):
        c.execute("UPDATE finance_tx SET status=?, updated_at=? WHERE id=?", (new, now(), tx_id))
        c.execute("INSERT INTO finance_tx_history (tx_id, ts, old_status, new_status, note) VALUES (?,?,?,?,?)", (tx_id, now(), r["status"], new, note))
        audit(c, actor, "finance_status", "finance_tx", tx_id, {"from": r["status"], "to": new})


def report(c: sqlite3.Connection, fx_to_base: dict | None = None) -> dict:
    """Monthly / annual cash report in the base currency. fx_to_base: {'EUR': 1.08, ...} (1 unit -> base). Missing rates are reported,
    not guessed."""
    base = get_setting(c, "base_currency", "USD"); fx = {base: 1.0, **(fx_to_base or {})}
    T = pd.read_sql_query("SELECT * FROM finance_tx", c)
    if T.empty:
        return {"status": "no transactions recorded", "base_currency": base}
    missing = sorted(set(T["currency"]) - set(fx))
    T["amount_base"] = T.apply(lambda r: r["amount"] * fx[r["currency"]] if r["currency"] in fx else float("nan"), axis=1)
    T["month"] = pd.to_datetime(T["ts"]).dt.to_period("M").astype(str)
    cash_in = T[(T.kind.isin(INCOME_KINDS)) & (T.status == "received")]
    cost = T[(~T.kind.isin(INCOME_KINDS)) & (T.status == "paid")]
    pend = T[(T.kind == "payout") & (T.status.isin(["requested", "approved"]))]
    m = pd.DataFrame({"received": cash_in.groupby("month")["amount_base"].sum(), "costs": cost.groupby("month")["amount_base"].sum()}).fillna(0.0)
    m["net_cash"] = m["received"] - m["costs"]
    by_firm = cash_in.groupby(cash_in["firm"].fillna("unknown"))["amount_base"].sum()
    conc = float(by_firm.max() / by_firm.sum()) if by_firm.sum() > 0 else None
    reserve_min = float(get_setting(c, "min_cash_reserve", "0") or 0)
    return {"base_currency": base, "missing_fx_rates": missing, "monthly": m.round(2).to_dict(orient="index"),
            "totals": {"received": float(cash_in["amount_base"].sum()), "costs_paid": float(cost["amount_base"].sum()),
                       "net_cash": float(cash_in["amount_base"].sum() - cost["amount_base"].sum())},
            "pending_payouts": {"requested": float(pend[pend.status == "requested"]["amount_base"].sum()), "approved_not_received": float(pend[pend.status == "approved"]["amount_base"].sum())},
            "received_by_firm": by_firm.round(2).to_dict(), "largest_firm_share_of_received": conc, "min_cash_reserve_setting": reserve_min,
            "note": "only 'received' payouts count as cash; requested / approved payouts are shown separately"}
