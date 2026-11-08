-- Lesson sql-10: the first migration of the payouts service. It is already applied in every
-- environment, so never edit it: Flyway stored its checksum in flyway_schema_history, and an
-- edited file fails validation. Change the schema with a new, higher version instead.

CREATE TABLE payouts (
    payout_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    merchant_id   bigint NOT NULL,
    amount_minor  bigint NOT NULL CHECK (amount_minor > 0),
    created_at    timestamptz NOT NULL DEFAULT now()
);
