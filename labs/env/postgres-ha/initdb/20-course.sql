-- Database "course" with the SQL track's schema and small seed, as in env/postgres.yml.
CREATE DATABASE course;
\connect course
\i /seed/course/schema.sql
\i /seed/course/seed.sql
