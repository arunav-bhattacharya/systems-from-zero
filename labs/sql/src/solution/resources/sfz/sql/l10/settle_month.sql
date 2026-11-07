-- Lesson sql-10, exercise 3 of 3: bring the monthly totals up to date with MERGE (a trap)
-- Reference answer.

MERGE INTO merchant_month_totals AS t
USING (SELECT merchant_id,
              date '2026-03-01' AS month,
              sum(amount_minor) AS gross_minor,
              count(*) AS payment_count
       FROM payments
       WHERE status = 'succeeded'
         AND created_at >= '2026-03-01' AND created_at < '2026-04-01'
       GROUP BY merchant_id) AS s
ON t.merchant_id = s.merchant_id AND t.month = s.month
WHEN MATCHED AND (t.gross_minor, t.payment_count)
                 IS DISTINCT FROM (s.gross_minor, s.payment_count) THEN   -- only rows that are wrong:
    UPDATE SET gross_minor = s.gross_minor,                               -- a right row gets no new version
               payment_count = s.payment_count
WHEN NOT MATCHED THEN                                                     -- in the source, not in the target
    INSERT (merchant_id, month, gross_minor, payment_count)
    VALUES (s.merchant_id, s.month, s.gross_minor, s.payment_count)
WHEN NOT MATCHED BY SOURCE AND t.month = date '2026-03-01' THEN           -- PostgreSQL 17+: in the target only.
    DELETE                                                                -- Without the month test this would
                                                                          -- delete every other month's rows.
RETURNING merge_action() AS action,                                       -- 'INSERT', 'UPDATE' or 'DELETE'
          t.merchant_id,
          old.gross_minor AS old_gross,                                   -- PostgreSQL 18: NULL for an insert
          new.gross_minor AS new_gross;                                   -- and NULL for a delete

-- MERGE has no arbiter index the way ON CONFLICT does: if another session inserts the same
-- (merchant_id, month) while this runs, the INSERT branch fails with 23505. A nightly job that
-- runs once at a time is fine; for concurrent writers, use INSERT ... ON CONFLICT.
