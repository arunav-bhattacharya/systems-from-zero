-- Lesson sql-15, exercise 3: the schema the role exercise runs against. The tests run this as
-- the superuser before your least_privilege.sql, and drop all of it afterwards.
--
-- Schema "ledger" belongs to the role ledger_owner. Nobody logs in as ledger_owner (NOLOGIN):
-- migrations run as an admin who switches to it with SET ROLE, so every table it creates is
-- owned by ledger_owner, and only ledger_owner (or a superuser) can ALTER or DROP them.
CREATE ROLE ledger_owner NOLOGIN;
CREATE SCHEMA ledger AUTHORIZATION ledger_owner;

SET ROLE ledger_owner;

CREATE TABLE ledger.payments (
    payment_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    merchant_id   bigint NOT NULL,
    amount_minor  bigint NOT NULL CHECK (amount_minor > 0),
    status        text NOT NULL CHECK (status IN ('pending', 'succeeded', 'failed'))
);

CREATE TABLE ledger.refunds (
    refund_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payment_id    bigint NOT NULL REFERENCES ledger.payments,
    amount_minor  bigint NOT NULL CHECK (amount_minor > 0)
);

-- who did what: the payments service appends a row for every change it makes
CREATE TABLE ledger.audit_log (
    entry_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor     text NOT NULL DEFAULT current_user,
    action    text NOT NULL,
    at        timestamptz NOT NULL DEFAULT now()
);

INSERT INTO ledger.payments (merchant_id, amount_minor, status) VALUES
    (1, 2500, 'succeeded'),
    (2, 1200, 'succeeded'),
    (1,  990, 'failed');
INSERT INTO ledger.refunds (payment_id, amount_minor) VALUES (1, 500);
INSERT INTO ledger.audit_log (action) VALUES ('ledger schema created');

RESET ROLE;
