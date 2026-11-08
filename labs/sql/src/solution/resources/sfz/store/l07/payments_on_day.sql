-- Lesson store-07, exercise 2 of 3: one day's payments, in a form the index can use (a trap)
-- Reference answer.

SELECT payment_id, created_at
FROM payments
WHERE created_at >= timestamptz '2026-03-12 00:00+00'    -- the column alone on the left: the index
  AND created_at <  timestamptz '2026-03-13 00:00+00'    -- seeks to the start and reads to the end
ORDER BY created_at, payment_id;

-- Half-open, [start, next day): midnight is in, 23:59:59.5 is in, the 13th is out.
-- BETWEEN '2026-03-12' AND '2026-03-12 23:59:59' would lose 23:59:59.5.
-- created_at::date depends on the TimeZone setting, so it is not IMMUTABLE and cannot even be
-- indexed as an expression; (created_at AT TIME ZONE 'UTC')::date can, if you must.
