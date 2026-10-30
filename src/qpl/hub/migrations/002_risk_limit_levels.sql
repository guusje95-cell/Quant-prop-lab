-- Allow several levels of the same rule (e.g. drawdown warning at 8% and stop at 12%): unique per threshold.
CREATE TABLE risk_limits_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT NOT NULL, scope_key TEXT NOT NULL, rule TEXT NOT NULL, threshold REAL NOT NULL,
  action TEXT NOT NULL, recover_below REAL, enabled INTEGER NOT NULL DEFAULT 1, UNIQUE (scope, scope_key, rule, threshold));
INSERT INTO risk_limits_new SELECT * FROM risk_limits;
DROP TABLE risk_limits;
ALTER TABLE risk_limits_new RENAME TO risk_limits;
