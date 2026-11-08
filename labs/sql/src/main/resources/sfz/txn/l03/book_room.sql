-- Lesson txn-03, exercise 2 of 3: book a meeting room only if nothing overlaps (a trap)
--
-- Table room_bookings (booking_id, room_id, during, booked_by) holds every booking; during is a
-- tstzrange, half-open: [12:00, 13:00) ends just before 13:00, so a booking from 13:00 does not
-- overlap it. Table rooms (room_id, name) has one row per room.
--
-- The tests run this whole file as ONE transaction in each of two sessions at once, one
-- statement at a time, taking turns. Each session has its own temporary table with its request:
--   booking_request (room_id bigint, during tstzrange, booked_by text)   -- one row
-- A booking that overlaps another booking of the same room inserts nothing. If a statement
-- fails with 40001 or 40P01, the tests roll that session back and run the whole file again.
--
-- Below is exercise 1's fix applied here: lock what the check finds before deciding. It does
-- not work. The check finds no booking in the way, so FOR UPDATE locks nothing, and two
-- sessions that book overlapping slots both insert: a phantom. Make the two transactions meet
-- on a row that already exists before they check (or use a stronger isolation level).
-- Bookings of different rooms must not wait for each other.
-- Check it: ./gradlew :sql:test --tests 'sfz.txn.l03.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

BEGIN;

-- lock every booking in the way, so nobody can change it while we decide
SELECT b.booking_id
FROM room_bookings b, booking_request r
WHERE b.room_id = r.room_id
  AND b.during && r.during
FOR UPDATE OF b;

INSERT INTO room_bookings (room_id, during, booked_by)
SELECT r.room_id, r.during, r.booked_by
FROM booking_request r
WHERE NOT EXISTS (SELECT 1
                  FROM room_bookings b
                  WHERE b.room_id = r.room_id
                    AND b.during && r.during);

COMMIT;
