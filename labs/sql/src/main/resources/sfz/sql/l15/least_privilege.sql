-- Lesson sql-15, exercise 3 of 3: a least-privilege role for the payments service (a trap)
--
-- The tests first build schema "ledger" as the superuser (src/test/resources/sfz/sql/l15/
-- ledger_schema.sql): its owner is the NOLOGIN role ledger_owner, and it holds three tables,
-- ledger.payments, ledger.refunds and ledger.audit_log. Then they run this file, also as the
-- superuser, and log in as payments_app with the password 'app-pass' over TCP (scram-sha-256).
--
-- What payments_app must be able to do, and nothing more:
--   * log in with the password 'app-pass';
--   * SELECT, INSERT and UPDATE on ledger.payments and ledger.refunds (never DELETE or TRUNCATE:
--     a payment is refunded, never removed);
--   * INSERT into ledger.audit_log, and never read, change or delete what is there;
--   * the same SELECT, INSERT and UPDATE on every table ledger_owner creates in ledger later,
--     without anyone running another GRANT;
--   * nothing else: no DROP or ALTER, no CREATE in ledger or in public, no course tables in
--     public, no new roles.
-- Every refused statement must fail with SQLSTATE 42501 (insufficient_privilege).
--
-- Below is what was shipped in a hurry. It works, and it gives the service far too much.
-- Rewrite it. Check it: ./gradlew :sql:test --tests 'sfz.sql.l15.*'   (from the labs folder)

CREATE ROLE payments_app LOGIN PASSWORD 'app-pass';
GRANT USAGE ON SCHEMA ledger TO payments_app;
GRANT ALL ON ALL TABLES IN SCHEMA ledger TO payments_app;
