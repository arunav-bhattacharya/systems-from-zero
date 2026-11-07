-- The SQL track's database. Its tables live in their own database, "course", so they never
-- collide with tables you create in database sfz (the internals track works there).
-- Connect with: docker compose -f env/postgres.yml exec db psql -U sfz -d course
CREATE DATABASE course;
\connect course
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pageinspect;
CREATE EXTENSION IF NOT EXISTS pg_buffercache;
-- the payments schema and its small seed: exact copies of the lab test fixtures
-- (labs/sql/src/test/resources/sfz/sql/support/), so psql shows the rows the tests use
\i /seed/course/schema.sql
\i /seed/course/seed.sql
