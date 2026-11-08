-- Lesson txn-03, exercise 2 of 3: book a meeting room only if nothing overlaps (a trap)
-- Reference answer.

BEGIN;                                  -- Read Committed

-- Materialize the conflict: every booking of a room first locks that room's row, which always
-- exists. A second booking of room 4 waits here until the first one commits; its INSERT below,
-- a new statement with a new snapshot, then sees the first booking and inserts nothing.
-- Bookings of room 7 lock a different row and never wait for room 4.
SELECT m.room_id
FROM rooms m, booking_request r
WHERE m.room_id = r.room_id
FOR UPDATE OF m;

INSERT INTO room_bookings (room_id, during, booked_by)
SELECT r.room_id, r.during, r.booked_by
FROM booking_request r
WHERE NOT EXISTS (SELECT 1
                  FROM room_bookings b
                  WHERE b.room_id = r.room_id
                    AND b.during && r.during);

COMMIT;

-- BEGIN ISOLATION LEVEL SERIALIZABLE; with no lock passes too: SSI's predicate locks notice that
-- each transaction searched a range the other then inserted into, and one of them retries.
-- Exercise 3 removes the need for either: a constraint makes the database refuse the overlap.
