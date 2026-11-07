-- Lesson sql-11, exercise 2 of 3: one day's payments, in a form the index can use (a trap)
--
-- The settlement report lists every payment created on 12 March 2026, UTC (the tests and the
-- course database run with TimeZone = UTC).
--
-- Columns: payment_id, created_at
-- Order:   created_at, payment_id
--
-- The query below returns the right rows, but it applies a cast to created_at, so an index on
-- created_at cannot be searched for them: PostgreSQL reads the whole index (or the whole table)
-- and casts every value. Rewrite the condition so that created_at stands alone on one side of
-- the comparison. Mind both edges: a payment at exactly midnight belongs to the 12th, one at
-- 23:59:59.5 too, and one at midnight on the 13th does not.
-- The tests check the rows on the small seed and the plan on a 200,000-row copy with an index
-- on created_at.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l11.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT payment_id, created_at
FROM payments
WHERE created_at::date = date '2026-03-12'
ORDER BY created_at, payment_id;
