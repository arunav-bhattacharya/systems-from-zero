-- Lesson sql-12, exercise 1 of 2: a withdrawal that keeps a customer's total at or above zero (a trap)
--
-- A customer may overdraw one account as long as the sum of balance_minor over ALL of their
-- accounts stays at or above zero. Ivy (customer 9) has accounts 109 and 209 with 5,000 each,
-- so one withdrawal of 8,000 is fine and a second one must be refused.
--
-- The tests run this whole file as ONE transaction in each of two sessions at once, one
-- statement at a time, taking turns (A's first statement, B's first, A's second, ...). Each
-- session has its own temporary table with the withdrawal it should make:
--   withdrawal (account_id bigint, amount_minor bigint)        -- one row
-- A withdrawal the rule does not allow changes nothing (the UPDATE matches no row).
-- If a statement fails with a serialization failure (40001) or a deadlock (40P01), the tests
-- roll that session back and run the whole file again for it, as your application would.
--
-- The transaction below checks the rule inside the UPDATE itself. Run it alone and it is
-- right. Run it in two sessions at once and both see 10,000, both withdraw, and Ivy ends at
-- -6,000: write skew. Fix it with a stronger isolation level, or by locking the rows the rule
-- reads. Keep the rule for all of the customer's accounts, not just 109 and 209.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l12.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

BEGIN ISOLATION LEVEL REPEATABLE READ;

UPDATE accounts a
SET balance_minor = a.balance_minor - w.amount_minor
FROM withdrawal w
WHERE a.account_id = w.account_id
  AND (SELECT sum(o.balance_minor)
       FROM accounts o
       WHERE o.customer_id = a.customer_id) >= w.amount_minor;

COMMIT;
