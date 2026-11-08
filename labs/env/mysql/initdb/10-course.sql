-- Database "course" for the Transactions track's MySQL Try-its (MySQL 8.4, InnoDB).
-- The image creates the database and user sfz first; this file runs once, as root.

USE course;

-- txn-02 (lost updates): Ivy's two accounts, as in the PostgreSQL course database.
CREATE TABLE accounts (
    account_id    BIGINT PRIMARY KEY,
    customer_id   BIGINT NOT NULL,
    balance_minor BIGINT NOT NULL
);
INSERT INTO accounts VALUES (109, 9, 5000), (209, 9, 5000);

-- txn-03 (phantoms): bookings of meeting rooms, with an index on (room_id, starts_at).
CREATE TABLE room_bookings (
    booking_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    room_id    INT NOT NULL,
    starts_at  DATETIME NOT NULL,
    ends_at    DATETIME NOT NULL,
    booked_by  VARCHAR(40) NOT NULL,
    KEY room_time (room_id, starts_at)
);
INSERT INTO room_bookings (room_id, starts_at, ends_at, booked_by) VALUES
    (4, '2026-12-01 09:00', '2026-12-01 10:00', 'risk team'),
    (4, '2026-12-01 14:00', '2026-12-01 15:00', 'settlement review'),
    (7, '2026-12-01 10:00', '2026-12-01 11:00', 'card ops');

-- Lesson 4 (MVCC): 10,000 settlement rows to update while an old snapshot stays open.
CREATE TABLE settlements (
    id           INT PRIMARY KEY,
    amount_cents BIGINT NOT NULL
);
SET SESSION cte_max_recursion_depth = 10000;
INSERT INTO settlements (id, amount_cents)
WITH RECURSIVE n (i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 10000)
SELECT i, 1000 FROM n;

-- sfz may read InnoDB's lock tables (performance_schema.data_locks) and SHOW ENGINE INNODB STATUS.
GRANT SELECT ON performance_schema.* TO 'sfz'@'%';
GRANT PROCESS ON *.* TO 'sfz'@'%';
