-- Lesson sql-13, exercise 1 of 2: claim the next job from the queue (a trap)
--
-- A worker runs this one statement inside its own transaction to claim one job: the oldest
-- queued job that is due (status 'queued' and run_after <= now(); oldest run_after first, then
-- the lowest job_id). It marks the job running, records who took it and when, counts the
-- attempt, and returns the job's job_id, kind and payload. When no job is due, it returns no row.
--
-- The worker's name is its application_name: SET application_name = 'worker-1' in psql, the
-- ApplicationName property in JDBC. SQL reads it with current_setting('application_name').
--
-- The tests start several workers at once. Each one runs BEGIN, then this statement, and keeps
-- its transaction open while it "works", as a real worker would. They check that no two workers
-- get the same job and that no worker ever waits for another worker's lock.
--
-- Run alone, the statement below is right. Run by two workers at once, the second one waits for
-- the first one's row lock on job 2, and once the first commits, it claims job 2 a second time.
-- Fix it with a row lock that steps over the jobs other workers hold.
-- Check it: ./gradlew :sql:test --tests 'sfz.sql.l13.*'   (from the labs folder)

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
)
RETURNING job_id, kind, payload;
