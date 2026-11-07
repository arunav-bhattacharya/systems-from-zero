-- Lesson sql-11, exercise 3 of 3: answer the monthly statement from the index alone (a trap)
-- Reference answer.

CREATE INDEX payments_merchant_gross_idx
    ON payments (merchant_id, created_at)    -- the search: one merchant, one range of time
    INCLUDE (status, amount_minor);          -- carried in the leaf entries only: the filter on status
                                             -- and the sum read them from the index, not the table

-- INCLUDE columns cannot narrow the search, but they make the index cover the query. The scan
-- still visits the table for any row on a page the visibility map does not mark all-visible:
-- new or recently updated rows, until VACUUM runs. That is the "Heap Fetches" count.
-- (merchant_id, status, created_at) INCLUDE (amount_minor) works too, and lets status narrow
-- the search as well.
