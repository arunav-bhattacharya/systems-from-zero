-- Lesson sql-07, exercise 2 of 3: likely double charges (a trap)
--
-- A SUCCEEDED payment is a likely duplicate when the SAME card paid the SAME merchant the SAME
-- amount, also successfully, at most 5 minutes before it. Report each duplicate with the
-- payment it repeats: the closest earlier one with that card, merchant and amount.
--   duplicate_of    payment_id of that earlier payment
--   seconds_after   seconds between the two (130 for payments 17 and 18)
--
-- Columns: payment_id, duplicate_of, seconds_after
-- Order:   payment_id
--
-- The query below compares each payment with the previous one in its window, but its window
-- has the wrong rows in it, and it never checks the 5 minutes. On the seed it reports four
-- "duplicates"; there is one. Decide what "the same charge" means and put exactly that in
-- PARTITION BY. Failed attempts are not charges, so they must not count as the earlier payment.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l07.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT payment_id, duplicate_of, seconds_after
FROM (
    SELECT payment_id,
           lag(payment_id) OVER w AS duplicate_of,
           extract(epoch FROM created_at - lag(created_at) OVER w) AS seconds_after
    FROM payments
    WHERE status = 'succeeded'
    WINDOW w AS (PARTITION BY merchant_id, amount_minor ORDER BY created_at)
) AS s
WHERE duplicate_of IS NOT NULL
ORDER BY payment_id;
