package sfz.batch.l14

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.io.TempDir
import java.nio.file.Files
import java.nio.file.Path
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread

class ServingStoreTest {
    /** Risk scores for 1,000 merchants, every one of them equal to [run]: a store whose versions are easy to tell apart. */
    private fun scores(run: Int) = (0 until 1_000).map { "merchant-%04d".format(it) to "$run" }.shuffled(kotlin.random.Random(run))

    @Test
    fun `a build writes a sorted file in a new version folder`(@TempDir root: Path) {
        val store = ServingStore(root)
        assertThat(store.build(scores(1))).isEqualTo("v1")
        assertThat(store.build(scores(2))).isEqualTo("v2")
        val lines = Files.readAllLines(root.resolve("v2/data"))
        assertThat(lines).hasSize(1_000)
        assertThat(lines.first()).isEqualTo("merchant-0000\t2")
        assertThat(lines).isSorted()
        assertThat(store.current()).describedAs("building publishes nothing").isNull()
    }

    @Test
    fun `a duplicate key is refused before anything is written`(@TempDir root: Path) {
        val store = ServingStore(root)
        assertThatThrownBy { store.build(listOf("b" to "1", "a" to "2", "b" to "3")) }.isInstanceOf(IllegalArgumentException::class.java)
        assertThat(Files.list(root).use { it.toList() }).describedAs("folders left behind").isEmpty()
    }

    @Test
    fun `readers see the published version until the next publish, and rolling back is publishing again`(@TempDir root: Path) {
        val store = ServingStore(root)
        val v1 = store.build(scores(1))
        store.publish(v1)
        assertThat(store.open().get("merchant-0042")).isEqualTo("1")
        val v2 = store.build(scores(2))
        assertThat(store.open().get("merchant-0042")).describedAs("v2 is built but not live").isEqualTo("1")
        store.publish(v2)
        assertThat(store.current()).isEqualTo("v2")
        assertThat(store.open().get("merchant-0042")).isEqualTo("2")
        assertThat(store.open().get("merchant-9999")).isNull()
        store.publish(v1)                                                  // the new scores were bad: roll back
        assertThat(store.open().get("merchant-0042")).isEqualTo("1")
        assertThat(Files.readString(root.resolve("v2/data"))).describedAs("v2 is still there to roll forward to").contains("merchant-0042\t2")
    }

    @Test
    @Timeout(20)
    fun `while versions are swapped under them, readers never see a mix and never find the pointer missing`(@TempDir root: Path) {
        val store = ServingStore(root)
        store.publish(store.build(scores(1)))
        val stop = AtomicBoolean(false)
        val problems = ConcurrentLinkedQueue<String>()
        val seen = ConcurrentLinkedQueue<String>()
        val readers = (1..3).map {
            thread {
                while (!stop.get()) {
                    try {
                        val s = store.open()
                        val values = (0 until 1_000 step 37).map { s.get("merchant-%04d".format(it)) }.toSet()
                        if (values.size != 1 || null in values) problems += "mixed read: $values"
                        seen += values.first()!!
                    } catch (e: Exception) {
                        problems += "${e::class.simpleName}: ${e.message}"
                    }
                }
            }
        }
        for (run in 2..30) store.publish(store.build(scores(run)))
        Thread.sleep(50)
        stop.set(true)
        readers.forEach { it.join() }
        assertThat(problems).isEmpty()
        assertThat(seen.toSet().size).describedAs("versions the readers saw").isGreaterThan(1)
        assertThat(store.open().get("merchant-0000")).isEqualTo("30")
    }
}
