-- Lesson sql-14, exercise 5 of 5: a migration that passes on an empty database (a trap).
-- Reference answer.

-- The DEFAULT gives every existing row 'pending' and every new row that names no status.
-- Since PostgreSQL 11 a constant default is stored in the catalog, so this ALTER does not
-- rewrite the table, however many rows it has. Flyway runs the file in one transaction: if any
-- statement fails, PostgreSQL rolls all of it back and the history records no version 2.
ALTER TABLE payouts
    ADD COLUMN status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'sent', 'failed'));

CREATE INDEX payouts_pending_idx ON payouts (created_at) WHERE status = 'pending';

-- On a large, busy table, build the index in a migration of its own with CREATE INDEX
-- CONCURRENTLY, which cannot run inside a transaction. With Flyway's default lock on PostgreSQL
-- (held in a transaction of its own) that statement waits for Flyway forever: set
-- postgresql.transactional.lock=false for such migrations.
