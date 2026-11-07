-- Lesson 11 of the Kafka track: the payment service's tables, in database "payments".
-- The service writes a payment and its outbox event in ONE local transaction; Debezium reads both from the WAL.
CREATE TABLE payment (
    id          text PRIMARY KEY,
    account     text   NOT NULL,
    amount      bigint NOT NULL,          -- cents
    status      text   NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- The outbox, in the shape Debezium's outbox event router expects by default.
CREATE TABLE outbox (
    id             uuid PRIMARY KEY,      -- the event id: consumers dedupe on it
    aggregatetype  text  NOT NULL,        -- routes the event: topic outbox.event.<aggregatetype>
    aggregateid    text  NOT NULL,        -- becomes the Kafka record key
    type           text  NOT NULL,        -- the event type, copied to a header
    payload        jsonb NOT NULL         -- becomes the Kafka record value
);
