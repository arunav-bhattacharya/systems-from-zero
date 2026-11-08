-- Lesson txn-02, exercise 1 of 2: claim the next job from the queue (a trap)
-- Reference answer.

UPDATE jobs
SET status    = 'running',
    locked_by = current_setting('application_name'),
    locked_at = now(),
    attempts  = attempts + 1
WHERE job_id = (
    SELECT job_id
    FROM jobs
    WHERE status = 'queued'
      AND run_after <= now()
    ORDER BY run_after, job_id
    LIMIT 1
    FOR UPDATE SKIP LOCKED      -- lock the row as we pick it, and step over rows another worker
                                -- holds: the second worker takes job 3 at once instead of waiting
                                -- for job 2. A row someone committed as 'running' since our
                                -- snapshot fails the recheck of the WHERE and is skipped too.
)
RETURNING job_id, kind, payload;

-- FOR UPDATE alone stops the double claim but makes the workers queue: the second one waits
-- for the first one's COMMIT, then rechecks job 2, finds it running, and takes job 3.
-- NOWAIT instead of SKIP LOCKED fails with 55P03 whenever the first candidate is taken.
-- The partial index jobs_ready_idx (run_after) WHERE status = 'queued' keeps the subquery to a
-- few index entries however many done jobs pile up in the table.
