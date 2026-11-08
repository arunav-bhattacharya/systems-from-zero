-- Lesson sql-08, exercise 3 of 3: the next page, with a keyset cursor (a trap)
--
-- The admin console lists ALL payments (any status), newest first, 5 per page, in the order
-- created_at DESC, payment_id DESC. The client sends back the last row it showed, and the
-- CTE page_cursor below holds it: payment 18, created at 2026-03-12 16:42:10. Return the
-- 5 payments that come right after that row in this order: the next page.
--
-- Columns: payment_id, created_at, amount_minor
-- Order:   created_at DESC, payment_id DESC
--
-- Keep page_cursor as it is; in an application its two values would be bind parameters.
-- The query below ignores the cursor and returns the first page. Do not count rows with
-- OFFSET: payments arrive while people page, and the page must not shift when they do. And
-- remember that two payments can share a created_at: a row that ties with the cursor's time
-- but has a smaller payment_id belongs on this page.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l08.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

WITH page_cursor AS (
    SELECT timestamptz '2026-03-12 16:42:10+00' AS created_at,
           18::bigint                           AS payment_id
)
SELECT p.payment_id, p.created_at, p.amount_minor
FROM payments p
ORDER BY p.created_at DESC, p.payment_id DESC
LIMIT 5;
