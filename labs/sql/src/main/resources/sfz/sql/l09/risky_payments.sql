-- Lesson sql-09, exercise 1 of 3: payments for the fraud queue (a trap)
--
-- payments.metadata is a jsonb document like
--   {"channel": "web", "risk": {"score": 91, "rules": ["velocity"]}}
-- The fraud team reviews every payment whose risk score is 50 or more, and every payment whose
-- risk rules include exactly "velocity", whatever its score.
--
-- Columns: payment_id, channel (text), score (integer, NULL when the document has none)
-- Order:   score DESC NULLS LAST, payment_id
--
-- The query below compares the score as text, so '8' counts as more than '50' and '100' as less,
-- and it searches the whole document as a string, so it also matches a rule named
-- "velocity_hourly". Compare the score as a number and test the rules array for containment.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l09.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT payment_id,
       metadata ->> 'channel' AS channel,
       (metadata -> 'risk' ->> 'score')::int AS score
FROM payments
WHERE metadata -> 'risk' ->> 'score' >= '50'
   OR metadata::text LIKE '%velocity%'
ORDER BY score DESC NULLS LAST, payment_id;
