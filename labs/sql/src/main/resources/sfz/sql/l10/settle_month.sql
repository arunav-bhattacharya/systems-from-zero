-- Lesson sql-10, exercise 3 of 3: bring the monthly totals up to date with MERGE (a trap)
--
-- merchant_month_totals holds, per merchant and month, the gross of its succeeded payments and
-- how many there were. The tests create it and fill it with last night's numbers:
--   merchant_month_totals (merchant_id bigint, month date, gross_minor bigint, payment_count int,
--                          PRIMARY KEY (merchant_id, month))
-- Since last night, payments have changed. Write ONE MERGE that makes the rows for March 2026
-- (month = date '2026-03-01') match the succeeded payments of March, and nothing else:
--   * a merchant with March payments but no March row gets one        (INSERT)
--   * a March row whose gross or count is wrong is corrected          (UPDATE)
--   * a March row whose merchant has no succeeded March payment goes  (DELETE)
--   * a March row that is already right is not touched, and rows for other months are never
--     touched at all.
-- Return one row per change:
--
-- Columns: action (merge_action()), merchant_id, old_gross, new_gross
--          (old_gross is NULL for an insert, new_gross is NULL for a delete)
-- Order:   any
--
-- The MERGE below rewrites every matched row, even the ones that are right, and its
-- WHEN NOT MATCHED BY SOURCE deletes every row of every month that March's source lacks.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l10.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

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
WHEN MATCHED THEN
    UPDATE SET gross_minor = s.gross_minor, payment_count = s.payment_count
WHEN NOT MATCHED THEN
    INSERT (merchant_id, month, gross_minor, payment_count)
    VALUES (s.merchant_id, s.month, s.gross_minor, s.payment_count)
WHEN NOT MATCHED BY SOURCE THEN
    DELETE
RETURNING merge_action() AS action, t.merchant_id,
          old.gross_minor AS old_gross, new.gross_minor AS new_gross;
