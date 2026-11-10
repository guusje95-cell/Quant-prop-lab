"""Audit 2026-11-10 (A-1 / A-2): the dry-run bots must trade the CURRENT candidates (bf2.8 on MT5, v9.9e with ERC weights for Hyro /
Propr). Exactness against the hub shadows was checked on the paper ledgers (book multipliers x sleeve returns == shadow return, 6 hours)."""
import inspect

from qpl.bot import venue_mt5 as V
from qpl.live import bf28_book as B28, cfd_extra as X, v99_book as V99


def test_mt5_bridge_defaults_to_bf28():
    assert V.BOOKS["bf28"][0] == "bf28_book" and "bf28cand" in str(V.BOOK)


def test_bf28_book_definition_matches_shadow():
    assert set(B28.DROP) == {"premium carry", "premium carry BF", "trend 4h", "alt kimchi"}
    assert set(B28.EXTRA) == {"rc6 CFD", "basket CFD", "trend 4h ens CFD", "alt kimchi ens CFD"}
    assert "with_positions" in inspect.signature(X.ensembles).parameters


def test_v99_book_uses_erc():
    assert V99.WEIGHTS == "erc" and V99.CANDIDATE.endswith("_erc") and V99.SHRINK == 0.5


def test_news_blackout_times_follow_new_york_dst(tmp_path):
    from qpl.live import news_blackouts as NB
    html = "2027 FOMC Meetings <div class='fomc-meeting__month'>March</div><div class='fomc-meeting__date'>16-17</div>"
    t = NB.fomc_times(html)
    import pandas as pd
    assert t == [pd.Timestamp("2027-03-17 18:00"), pd.Timestamp("2027-03-17 18:30")]       # EDT after 2027-03-14
    f = tmp_path / "nb.json"; f.write_text('["2026-12-09 19:00:00"]')
    assert V.in_blackout(pd.Timestamp("2026-12-09 19:05"), path=f) and not V.in_blackout(pd.Timestamp("2026-12-09 19:10"), path=f)
