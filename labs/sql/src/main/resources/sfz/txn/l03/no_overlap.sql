-- Lesson txn-03, exercise 3 of 3: let the database refuse a double booking
--
-- Replace the placeholder below with DDL that adds a constraint to room_bookings: no two
-- bookings of the SAME room may overlap in time (the && operator on tstzrange). Bookings of
-- different rooms may overlap, and back-to-back bookings ([12:00,13:00) and [13:00,14:00)) are
-- fine. The extension btree_gist is already installed, so "=" on bigint can sit in a GiST index.
--
-- The tests run this file once (committed), then insert bookings with plain INSERTs, without
-- any check, from one and from two sessions at once. An overlapping insert must fail with
-- SQLSTATE 23P01 (exclusion_violation), even while the booking it overlaps is uncommitted.
-- Check it: ./gradlew :sql:test --tests 'sfz.txn.l03.*'   (from the labs folder)

SELECT 'TODO: add a constraint to room_bookings' AS todo;
