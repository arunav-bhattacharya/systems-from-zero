-- Lesson nosql-12: 100,000 made-up "embeddings" of 32 numbers, in 200 clusters (like texts about
-- 200 topics), and 20 query vectors. Load: psql -U sfz -f /sfz/nosql-12-vectors.sql (safe to run again)
CREATE EXTENSION IF NOT EXISTS vector;
DROP TABLE IF EXISTS items, queries, centres;
SELECT setseed(0.42);

CREATE TABLE centres AS
SELECT c AS id, (SELECT array_agg(random() * 10 ORDER BY d) FROM generate_series(1, 32) AS d WHERE c > 0) AS v
FROM generate_series(1, 200) AS c;

-- each item: its cluster's centre plus noise
CREATE TABLE items (id int PRIMARY KEY, embedding vector(32));
INSERT INTO items
SELECT i, (SELECT array_agg(x + (random() - 0.5) * 8) FROM unnest(c.v) AS x)::vector
FROM generate_series(1, 100000) AS i JOIN centres c ON c.id = 1 + i % 200;

CREATE TABLE queries (id int PRIMARY KEY, embedding vector(32));
INSERT INTO queries
SELECT q, (SELECT array_agg(x + (random() - 0.5) * 8) FROM unnest(c.v) AS x)::vector
FROM generate_series(1, 20) AS q JOIN centres c ON c.id = 1 + (q * 37) % 200;

ANALYZE items;
SELECT count(*) AS items, (SELECT count(*) FROM queries) AS queries FROM items;
