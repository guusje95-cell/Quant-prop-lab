# Paper run log (v86 / bf26, started 2026-10-21 15:00 UTC)

| Date (UTC) | Event |
|---|---|
| 2026-10-21 | v86 and bf26 started; bf26 waited for Dukascopy index bars (HTTP 503) for a few hours |
| 2026-10-22 | First shares: reconcile v86 exact (max diff 6e-20), bf26 corr 0.944 / cum diff -0.04% (index bars during the outage); equity -2.3% / -2.0% after 16 h |
| 2026-10-23 | bf26 share: -2.20%, max DD -3.32%, 1 daily stop; user's PC crashed; both runs restarted (missed hours filled in, flagged late) |
| 2026-10-23 | Share: v86 46 h reconcile exact (-3.2%); bf26 45 h: crypto sleeves exact, **index sleeve differs** (paper -1.34% vs recomputed -1.65% at risk 1.0; cause: late / provisional Dukascopy live index bars, bf26 freezes about 70 min after each hour). Waiting for the user's live index files to fix the feed |
