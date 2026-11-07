-- Lesson sql-02, exercise 1 of 3: test a functional dependency
-- Reference answer.

SELECT mcc,
       count(DISTINCT mcc_description) AS descriptions
FROM payments_export
GROUP BY mcc                                  -- one group per value of the left-hand side
HAVING count(DISTINCT mcc_description) > 1    -- the dependency fails where a group has two answers
ORDER BY mcc;
