-- Lesson sql-10, Try it 5: the first migration of a small settlement service.
CREATE TABLE settlement_batches (
    batch_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    merchant_id  bigint NOT NULL,
    day          date NOT NULL,
    total_minor  bigint NOT NULL,
    UNIQUE (merchant_id, day)
);
