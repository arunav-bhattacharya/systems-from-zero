-- Lesson txn-03, exercise 3 of 3: let the database refuse a double booking
-- Reference answer.

-- An exclusion constraint generalizes UNIQUE: no two rows may have room_id = room_id AND
-- during && during. PostgreSQL checks it through a GiST index, and an insert that conflicts with
-- an uncommitted row waits for that row's transaction, then fails with 23P01 if it committed.
-- btree_gist (installed by the course schema) lets "=" on bigint sit in the GiST index.
ALTER TABLE room_bookings
    ADD CONSTRAINT room_bookings_no_overlap
    EXCLUDE USING gist (room_id WITH =, during WITH &&);

-- PostgreSQL 18 also accepts a temporal key, which behaves like the same exclusion constraint:
--   ALTER TABLE room_bookings ADD CONSTRAINT room_bookings_no_overlap
--       UNIQUE (room_id, during WITHOUT OVERLAPS);
