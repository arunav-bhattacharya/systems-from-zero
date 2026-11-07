-- Lesson nosql-12: one day of card-authorization latencies as a TimescaleDB hypertable.
-- Load: docker compose -f env/timescale.yml exec tsdb psql -U sfz -f /sfz/nosql-12-latency.sql (safe to run again)
CREATE EXTENSION IF NOT EXISTS timescaledb;
DROP MATERIALIZED VIEW IF EXISTS latency_hourly;
DROP TABLE IF EXISTS auth_latency CASCADE;

CREATE TABLE auth_latency (
    time        timestamptz      NOT NULL,
    merchant_id text             NOT NULL,
    latency_ms  double precision NOT NULL
);
-- a hypertable: TimescaleDB splits the table into one chunk per hour of `time`
SELECT create_hypertable('auth_latency', by_range('time', INTERVAL '1 hour'));

-- 2026-11-07, one authorization per second for each of three merchants: 259,200 rows.
-- About 1 in 50 is slow (the card issuer took its time). The fixed seed makes every run the same.
SELECT setseed(0.42);
INSERT INTO auth_latency
SELECT t, m, CASE WHEN random() < 0.02 THEN 600 + random() * 900 ELSE 60 + random() * 80 END
FROM generate_series(TIMESTAMPTZ '2026-11-07 00:00:00+00', TIMESTAMPTZ '2026-11-07 23:59:59+00', INTERVAL '1 second') AS t,
     unnest(ARRAY['M-0042', 'M-0043', 'M-0044']) AS m;
ANALYZE auth_latency;
SELECT count(*) AS rows, count(DISTINCT merchant_id) AS merchants FROM auth_latency;
