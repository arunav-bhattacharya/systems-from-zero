-- Lesson sql-10, Try it 5: the second migration. NULL until the bank confirms the payout.
ALTER TABLE settlement_batches ADD COLUMN paid_at timestamptz;
