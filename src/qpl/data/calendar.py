"""NYSE/CME equity holiday and early-close calendar (ex-ante knowable)."""
from __future__ import annotations

from functools import lru_cache

import pandas as pd
from pandas.tseries.holiday import (AbstractHolidayCalendar, GoodFriday, Holiday, USLaborDay,
                                    USMartinLutherKingJr, USMemorialDay, USPresidentsDay, USThanksgivingDay,
                                    nearest_workday, sunday_to_monday)


class NYSECalendar(AbstractHolidayCalendar):
    rules = [
        Holiday("NewYearsDay", month=1, day=1, observance=sunday_to_monday),
        USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
        Holiday("Juneteenth", month=6, day=19, start_date="2022-01-01", observance=nearest_workday),
        Holiday("IndependenceDay", month=7, day=4, observance=nearest_workday),
        USLaborDay, USThanksgivingDay,
        Holiday("Christmas", month=12, day=25, observance=nearest_workday),
    ]


SPECIAL_CLOSURES = ["2012-10-29", "2012-10-30", "2018-12-05", "2025-01-09"]


@lru_cache(maxsize=4)
def holidays(start: str = "2005-01-01", end: str = "2027-12-31") -> pd.DatetimeIndex:
    h = NYSECalendar().holidays(start, end)
    return h.union(pd.DatetimeIndex(SPECIAL_CLOSURES)).sort_values()


@lru_cache(maxsize=4)
def early_closes(start: str = "2005-01-01", end: str = "2027-12-31") -> pd.DatetimeIndex:
    """13:00 ET early closes: Jul 3 (weekday, when Jul 4 is a weekday holiday Tue-Fri... approximated as
    Jul 3 on a weekday that is not itself a holiday), the day after Thanksgiving, Dec 24 (weekday)."""
    hol = holidays(start, end)
    out = []
    for y in range(int(start[:4]), int(end[:4]) + 1):
        for d in (pd.Timestamp(y, 7, 3), pd.Timestamp(y, 12, 24)):
            if d.dayofweek < 5 and d not in hol:
                out.append(d)
        tg = [d for d in hol if d.year == y and d.month == 11]
        if tg:
            out.append(tg[-1] + pd.Timedelta(days=1))
    return pd.DatetimeIndex(sorted(out))
