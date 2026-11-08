package sfz.stream.l07

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Two card streams of 50 records each go through your counter and sink, on virtual time. A run "crashes" by losing
 * everything in memory and restarting from the last completed checkpoint.
 */
class CheckpointingTest {
    private val inputs = listOf(
        List(50) { "card-${it % 3 + 1}" },         // source 0: card-1, card-2, card-3, card-1, ...
        List(50) { "card-${it % 2 + 2}" },         // source 1: card-2, card-3, card-2, ...
    )
    private val records = inputs.sumOf { it.size }
    private val append = { out: MutableList<Update> -> AppendSink(out) }
    private val transactional = { out: MutableList<Update> -> TransactionalSink(out) }

    private fun job(aligned: Boolean, sink: (MutableList<Update>) -> Sink, seed: Long) = Job(inputs, aligned, sink, seed = seed)

    @Test
    fun `the counter blocks an input that delivered the barrier until the other one does`() {
        val snapshots = mutableListOf<Pair<Int, Map<String, Int>>>()
        val task = CountingTask(aligned = true, inputs = 2, restored = mapOf("card-1" to 4)) { id, c -> snapshots += id to c.toMap() }
        assertThat(task.onItem(0, Record(0, 7, "card-1"))).containsExactly(Update("card-1", 5, 0, 7))
        assertThat(task.onItem(0, Barrier(1))).isEmpty()
        assertThat(task.canTake(0)).describedAs("input 0 waits for input 1's barrier").isFalse()
        assertThat(task.canTake(1)).isTrue()
        assertThat(task.onItem(1, Record(1, 3, "card-2"))).containsExactly(Update("card-2", 1, 1, 3))
        assertThat(task.onItem(1, Barrier(1))).containsExactly(Barrier(1))
        assertThat(snapshots).containsExactly(1 to mapOf("card-1" to 5, "card-2" to 1))
        assertThat(task.canTake(0)).describedAs("aligned: both inputs flow again").isTrue()
    }

    @Test
    fun `without alignment the counter keeps taking records after a barrier`() {
        val task = CountingTask(aligned = false, inputs = 2, restored = emptyMap()) { _, _ -> }
        task.onItem(0, Barrier(1))
        assertThat(task.canTake(0)).isTrue()
        assertThat(task.onItem(0, Record(0, 0, "card-1"))).containsExactly(Update("card-1", 1, 0, 0))
    }

    @Test
    fun `the transactional sink shows a checkpoint's updates only when the checkpoint completes`() {
        val external = mutableListOf<Update>()
        val sink = TransactionalSink(external)
        val a = Update("card-1", 1, 0, 0)
        val b = Update("card-2", 1, 1, 0)
        val c = Update("card-1", 2, 0, 1)
        assertThat(sink.onItem(a)).isNull()
        assertThat(sink.onItem(b)).isNull()
        assertThat(sink.onItem(Barrier(1))).isEqualTo(1)
        assertThat(external).describedAs("pre-committed, not committed").isEmpty()
        sink.onItem(c)
        sink.onCheckpointComplete(1)
        assertThat(external).containsExactly(a, b)
        sink.onItem(Barrier(2))
        sink.onCheckpointComplete(2)
        assertThat(external).containsExactly(a, b, c)
    }

    @Test
    fun `with no crash every setup writes one update per record`() {
        for (aligned in listOf(true, false)) for (sink in listOf(append, transactional)) {
            val j = job(aligned, sink, seed = 1).run()
            assertThat(j.external).hasSize(records)
            assertThat(j.finalCounts()).isEqualTo(j.truth())
        }
    }

    @Test
    fun `an aligned snapshot counts exactly the records before its offsets`() {
        for (seed in 1L..30) {
            val j = job(aligned = true, append, seed).run()
            assertThat(j.completed.size).isGreaterThanOrEqualTo(3)
            for (s in j.completed) {
                assertThat(s.counts.values.sum()).describedAs("seed $seed, checkpoint ${s.id}").isEqualTo(s.offsets.sum())
            }
        }
    }

    @Test
    fun `a snapshot taken without alignment can count records past its offsets`() {
        val inconsistent = (1L..30).flatMap { seed ->
            job(aligned = false, append, seed).run().completed.filter { it.counts.values.sum() > it.offsets.sum() }
        }
        assertThat(inconsistent).describedAs("snapshots that counted records the sources will replay").isNotEmpty()
    }

    @Test
    fun `aligned checkpoints and a transactional sink survive a crash exactly once`() {
        for (seed in 1L..30) for (crashAt in listOf(60L, 110L, 160L)) {
            val j = job(aligned = true, transactional, seed).run(crashAt)
            assertThat(j.restoredFrom).describedAs("seed $seed crashed at $crashAt").isNotNull()
            assertThat(j.duplicates()).describedAs("seed $seed crashed at $crashAt").isZero()
            assertThat(j.external).hasSize(records)
            assertThat(j.finalCounts()).isEqualTo(j.truth())
        }
    }

    @Test
    fun `aligned checkpoints and an append sink keep the counts right but write updates twice`() {
        val j = job(aligned = true, append, seed = 1).run(crashAt = 160)
        assertThat(j.finalCounts()).describedAs("the state is exactly-once").isEqualTo(j.truth())
        assertThat(j.duplicates()).describedAs("the output is at-least-once").isPositive()
    }

    @Test
    fun `without alignment a crash can overcount even with a transactional sink`() {
        val overcounts = (1L..30).count { seed ->
            val j = job(aligned = false, transactional, seed).run(crashAt = 160)
            j.finalCounts().any { (key, n) -> n > j.truth().getValue(key) }
        }
        assertThat(overcounts).isPositive()
    }
}
