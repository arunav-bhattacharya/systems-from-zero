-- Lesson store-14, exercise 3 of 3: a least-privilege role for the payments service (solution)
--
-- See src/main/resources/sfz/store/l14/least_privilege.sql for the full task.

-- a role that can log in; CREATE USER would be the same with LOGIN implied
CREATE ROLE payments_app LOGIN PASSWORD 'app-pass';

-- USAGE lets it look up objects in the schema by name; without it every ledger.x is 42501.
-- No CREATE on the schema: only ledger_owner adds tables (PostgreSQL 15 and later also give
-- PUBLIC no CREATE on schema public, so the role cannot create tables there either).
GRANT USAGE ON SCHEMA ledger TO payments_app;

-- read and write, but no DELETE, TRUNCATE, REFERENCES or TRIGGER (GRANT ALL would give all of
-- them). DROP and ALTER are never grantable: they belong to the owner.
GRANT SELECT, INSERT, UPDATE ON ledger.payments, ledger.refunds TO payments_app;

-- append-only: INSERT without SELECT. A plain INSERT works; INSERT ... RETURNING would need SELECT.
GRANT INSERT ON ledger.audit_log TO payments_app;

-- tables that ledger_owner creates in ledger from now on. FOR ROLE matters: default privileges
-- belong to the role that creates the table, and this file runs as the superuser, not as
-- ledger_owner. Without FOR ROLE ledger_owner this would change the superuser's defaults instead.
ALTER DEFAULT PRIVILEGES FOR ROLE ledger_owner IN SCHEMA ledger
    GRANT SELECT, INSERT, UPDATE ON TABLES TO payments_app;

-- nothing to do for CONNECT: PUBLIC has CONNECT on every database by default
