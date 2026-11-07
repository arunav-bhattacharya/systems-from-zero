-- Lesson sql-02, exercise 2 of 3: a table that refuses bad rows
-- Reference answer.

CREATE TABLE card_limits (
    card_id            bigint NOT NULL REFERENCES cards,    -- the card must exist
    valid_during       tstzrange NOT NULL,
    daily_limit_minor  bigint NOT NULL
        CHECK (daily_limit_minor > 0 AND daily_limit_minor <= 10000000),  -- CHECK alone lets NULL through
    -- PG18 temporal key: one card, no two periods that overlap; adjacent [a,b) and [b,c) do not overlap
    PRIMARY KEY (card_id, valid_during WITHOUT OVERLAPS)
);

-- Before PostgreSQL 18, the same rule is an exclusion constraint (needs btree_gist for "="):
--     EXCLUDE USING gist (card_id WITH =, valid_during WITH &&)
