-- Shadow / replayed hours: 1 = computed retroactively (before the account was defined), not forward paper evidence.
ALTER TABLE paper_equity ADD COLUMN retro INTEGER NOT NULL DEFAULT 0;
