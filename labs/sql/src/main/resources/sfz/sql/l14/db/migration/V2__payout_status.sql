-- Lesson sql-14, exercise 5 of 5: a migration that passes on an empty database (a trap).
--
-- Every payout gets a status: 'pending' when it is created, then 'sent' or 'failed'. The
-- sender looks for pending payouts, oldest first, so a partial index serves it.
--
-- On a fresh, empty database (the developer's laptop, a CI run) this migration works. In
-- production payouts already has rows, and none of them has a status, so ADD COLUMN ... NOT NULL
-- fails with 23502 and the deployment stops. Make it work on a table with rows, and make a new
-- payout that names no status start as 'pending'.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l14.*'   (from the labs folder)

ALTER TABLE payouts
    ADD COLUMN status text NOT NULL
        CHECK (status IN ('pending', 'sent', 'failed'));

CREATE INDEX payouts_pending_idx ON payouts (created_at) WHERE status = 'pending';
