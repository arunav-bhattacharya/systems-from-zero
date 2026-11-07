-- Lesson sql-02, exercise 1 of 3: test a functional dependency
--
-- payments_export is a flat file from a partner bank. Every row repeats the merchant's
-- category code (mcc) and its description. The data should obey the functional dependency
-- mcc -> mcc_description: one mcc, one description.
--
-- List every mcc that appears with more than one description, and how many different
-- descriptions it has.
--
-- Columns: mcc, descriptions
-- Order:   mcc
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l02.*'   (from the labs folder)
-- Keep this file plain SQL: psql backslash commands such as \pset do not work in it.

SELECT NULL::text   AS mcc,
       NULL::bigint AS descriptions
WHERE false;
