-- Lesson sql-09, exercise 1 of 3: payments for the fraud queue (a trap)
-- Reference answer.

SELECT payment_id,
       metadata ->> 'channel' AS channel,                       -- ->> returns text
       (metadata -> 'risk' ->> 'score')::int AS score           -- text, then cast: a number again
FROM payments
WHERE (metadata -> 'risk' ->> 'score')::int >= 50              -- compare numbers, not strings ('8' > '50')
   OR metadata @> '{"risk": {"rules": ["velocity"]}}'          -- containment: an array element equal to "velocity"
ORDER BY score DESC NULLS LAST, payment_id;

-- Two other spellings that work:
--   (metadata -> 'risk' -> 'score') >= '50'::jsonb     jsonb compares two numbers as numbers
--   metadata -> 'risk' -> 'rules' ? 'velocity'          ? asks whether an array holds that string
-- @> is the one a GIN index on metadata can answer (jsonb_ops or jsonb_path_ops).
