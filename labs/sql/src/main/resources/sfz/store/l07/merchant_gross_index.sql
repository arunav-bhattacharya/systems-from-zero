-- Lesson store-07, exercise 3 of 3: answer the monthly statement from the index alone (a trap)
--
-- The monthly statement asks, for one merchant and one month:
--
--   SELECT count(*) AS payments, sum(amount_minor) AS gross_minor
--   FROM payments
--   WHERE merchant_id = 6 AND status = 'succeeded'
--     AND created_at >= '2026-03-01' AND created_at < '2026-04-01';
--
-- Write ONE CREATE INDEX that answers it without reading the table: EXPLAIN must show an
-- Index Only Scan with "Heap Fetches: 0" on the 200,000-row copy (which has been vacuumed, so
-- its visibility map is up to date).
--
-- The index below finds the rows, but status and amount_minor are not in it, so every row it
-- finds costs a visit to the table.
-- Check it: ./gradlew :sql:test --tests 'sfz.store.l07.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

CREATE INDEX payments_merchant_gross_idx ON payments (merchant_id, created_at);
