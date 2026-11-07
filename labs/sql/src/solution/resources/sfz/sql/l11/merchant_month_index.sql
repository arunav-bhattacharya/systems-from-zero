-- Lesson sql-11, exercise 1 of 3: an index for the merchant dashboard (a trap)
-- Reference answer.

CREATE INDEX payments_merchant_month_idx
    ON payments (merchant_id,      -- the equality column first: one jump to merchant 6's entries,
                 created_at);      -- which are then already in time order, so the range is one
                                   -- contiguous run, read backward for DESC, and LIMIT 20 stops early

-- (created_at, merchant_id) has the same columns, but there merchant 6's entries are scattered
-- through March among everyone else's, so the scan reads tens of index pages to find twenty.
-- (merchant_id) alone finds merchant 6 but leaves the rows unsorted: a Sort over all of them.
