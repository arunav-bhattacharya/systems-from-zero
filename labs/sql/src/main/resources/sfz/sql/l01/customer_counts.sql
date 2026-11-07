-- Lesson sql-01, exercise 2 of 3: four counts in one row (count(*) or count(column)?)
--
-- Return one row with four numbers about the customers table:
--   customers  how many customers there are
--   referred   how many customers were referred by someone (referred_by is not NULL)
--   referrers  how many different customers have referred at least one person
--   organic    how many customers nobody referred (referred_by is NULL)
--
-- Columns: customers, referred, referrers, organic
-- Use one SELECT over customers. You need no WHERE clause: pick the right kind of count.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l01.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT count(*) AS customers,
       count(*) AS referred,
       count(*) AS referrers,
       count(*) AS organic
FROM customers;
