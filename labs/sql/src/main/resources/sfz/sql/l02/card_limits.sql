-- Lesson sql-02, exercise 2 of 3: a table that refuses bad rows
--
-- The risk team wants a daily spending limit per card that can change over time.
-- Write the CREATE TABLE for card_limits with exactly these columns:
--
--   card_id            bigint     the card the limit applies to
--   valid_during       tstzrange  when the limit is in force, half-open: [from, to)
--   daily_limit_minor  bigint     the limit in cents
--
-- Make PostgreSQL itself reject every bad row. The tests insert rows and expect:
--   * a card_id that is not in cards is rejected
--   * a missing (NULL) value in any column is rejected
--   * a limit of 0 or less, or above 10000000 (100,000.00), is rejected
--   * two limits for the same card that are in force at the same moment are rejected,
--     but back-to-back periods ([Jan, Jul) then [Jul, ...)) are fine, and so is the
--     same period on two different cards
--
-- The statement below runs, but the table accepts anything. Replace it.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l02.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

CREATE TABLE card_limits (
    card_id            bigint,
    valid_during       tstzrange,
    daily_limit_minor  bigint
);
