package sfz.internals.l05

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import sfz.internals.l01.ChannelFactory
import sfz.internals.support.CountingFileChannel
import java.nio.file.Files
import java.nio.file.Path
import java.util.TreeMap
import kotlin.random.Random

class BloomFilterTest {
    @Test
    fun `the filter never says no for a key it holds`() {
        val f = BloomFilter.forKeys(10_000, bitsPerKey = 10)
        repeat(10_000) { f.add("auth:$it") }
        val misses = (0 until 10_000).count { !f.mightContain("auth:$it") }
        assertThat(misses).`as`("false negatives").isZero()
    }

    @Test
    fun `at 10 bits per key about 1 in 100 absent keys gets a false yes, at 5 bits about 1 in 10`() {
        fun rate(bitsPerKey: Int): Double {
            val f = BloomFilter.forKeys(10_000, bitsPerKey)
            repeat(10_000) { f.add("auth:$it") }
            return (0 until 100_000).count { f.mightContain("card:$it") } / 100_000.0
        }
        val ten = rate(10)
        val five = rate(5)
        assertThat(ten).`as`("false-positive rate at 10 bits per key (k = 7)").isBetween(0.004, 0.02)
        assertThat(five).`as`("false-positive rate at 5 bits per key (k = 3)").isBetween(0.06, 0.13)
    }

    @Test
    fun `an empty filter says no to everything`() {
        val f = BloomFilter.forKeys(100, bitsPerKey = 10)
        assertThat((0 until 1_000).none { f.mightContain("auth:$it") }).isTrue()
    }
}

class LsmTest {
    @TempDir
    lateinit var dir: Path

    /** Hands out counting channels and remembers every one, so a test can add up the reads. */
    private class Channels : ChannelFactory {
        val opened = mutableListOf<CountingFileChannel>()
        override fun open(path: Path) = CountingFileChannel.open(path).also { opened += it }
        fun reset() = opened.forEach { it.resetCounts() }
        val reads get() = opened.sumOf { it.reads }
    }

    private fun v(s: String) = s.encodeToByteArray()
    private fun LsmStore.str(key: String) = get(key)?.decodeToString()
    private fun sorted(n: Int, prefix: String = "auth:") = TreeMap<String, ByteArray?>().apply {
        for (i in 0 until n) put("$prefix%05d".format(i), v("AUTHORIZED-$i"))
    }

    @Test
    fun `an SSTable holds its records in key order and answers gets`() {
        val entries = sorted(300)
        val t = SSTable.write(dir.resolve("t.sst"), entries.entries)
        assertThat(t.entries().map { it.first }).isEqualTo(entries.keys.toList())
        for ((k, value) in entries) {
            val r = t.get(k)
            assertThat(r).`as`("get($k)").isInstanceOf(Lookup.Value::class.java)
            assertThat((r as Lookup.Value).bytes.decodeToString()).isEqualTo(value!!.decodeToString())
        }
        assertThat(t.get("auth:99999")).isEqualTo(Lookup.Missing)
        assertThat(t.get("aaa")).`as`("a key before the first key").isEqualTo(Lookup.Missing)
        t.close()
    }

    @Test
    fun `the sparse index holds every 16th key, and a get reads one block`() {
        val channels = Channels()
        val entries = sorted(1_000)
        val t = SSTable.write(dir.resolve("t.sst"), entries.entries, channels)
        assertThat(t.indexKeys).`as`("index keys for 1,000 records").hasSize(63)
        assertThat(t.indexKeys).isEqualTo(entries.keys.filterIndexed { i, _ -> i % 16 == 0 })
        for (k in listOf("auth:00000", "auth:00015", "auth:00016", "auth:00500", "auth:00999")) {
            channels.reset()
            assertThat(t.get(k)).isInstanceOf(Lookup.Value::class.java)
            assertThat(channels.reads).`as`("reads for get($k)").isEqualTo(1)
        }
        t.close()
    }

    @Test
    fun `a key the Bloom filter rules out costs no read at all`() {
        val channels = Channels()
        val t = SSTable.write(dir.resolve("t.sst"), sorted(1_000).entries, channels)
        val absent = (0 until 1_000).map { "auth:%05d-x".format(it) }   // they fall inside the table's key range
        val falsePositives = absent.count { t.filter.mightContain(it) }
        channels.reset()
        for (k in absent) assertThat(t.get(k)).isEqualTo(Lookup.Missing)
        assertThat(channels.reads).`as`("reads for 1,000 absent keys: one per false positive, none for the rest")
            .isEqualTo(falsePositives)
        assertThat(falsePositives).isLessThan(30)
        t.close()
    }

    @Test
    fun `the memtable shadows the tables, and a newer table shadows an older one`() {
        LsmStore.open(dir).use { db ->
            db.put("auth:1", v("PENDING"))
            db.put("auth:2", v("PENDING"))
            db.flush()
            db.put("auth:1", v("AUTHORIZED"))
            db.flush()
            assertThat(db.tables()).hasSize(2)
            assertThat(db.str("auth:1")).`as`("newer table wins").isEqualTo("AUTHORIZED")
            assertThat(db.str("auth:2")).`as`("only in the older table").isEqualTo("PENDING")
            db.put("auth:1", v("CAPTURED"))
            assertThat(db.str("auth:1")).`as`("the memtable wins").isEqualTo("CAPTURED")
            assertThat(db.get("auth:3")).isNull()
        }
    }

    @Test
    fun `a read stops at the newest table that knows the key`() {
        val channels = Channels()
        LsmStore.open(dir, channels = channels).use { db ->
            for (round in 1..3) {
                db.put("auth:7", v("v$round"))
                db.put("auth:old-$round", v("x"))
                db.flush()
            }
            channels.reset()
            assertThat(db.str("auth:7")).isEqualTo("v3")
            assertThat(channels.reads).`as`("reads: auth:7 is in the newest table").isEqualTo(1)
        }
    }

    @Test
    fun `a tombstone hides older values, in the memtable, after a flush and after a reopen`() {
        LsmStore.open(dir).use { db ->
            db.put("auth:1", v("AUTHORIZED"))
            db.put("auth:2", v("AUTHORIZED"))
            db.flush()
            db.delete("auth:1")
            assertThat(db.get("auth:1")).`as`("tombstone in the memtable").isNull()
            db.flush()
            assertThat(db.get("auth:1")).`as`("tombstone in the newest table").isNull()
            assertThat(db.str("auth:2")).isEqualTo("AUTHORIZED")
            assertThat(db.tables()[1].get("auth:1")).`as`("the old value is still in the older table")
                .isInstanceOf(Lookup.Value::class.java)
        }
        LsmStore.open(dir).use { db ->
            assertThat(db.get("auth:1")).`as`("after reopen").isNull()
            assertThat(db.str("auth:2")).isEqualTo("AUTHORIZED")
        }
    }

    @Test
    fun `the memtable flushes by itself when it reaches its size limit`() {
        LsmStore.open(dir, memtableLimit = 4_096).use { db ->
            for (i in 0 until 1_000) db.put("auth:%05d".format(i), v("AUTHORIZED-$i"))
            assertThat(db.tables().size).`as`("tables after about 24 KB of puts with a 4 KB memtable").isBetween(5, 7)
            for (i in 0 until 1_000) assertThat(db.str("auth:%05d".format(i))).isEqualTo("AUTHORIZED-$i")
        }
    }

    @Test
    fun `without a write-ahead log a crash loses the memtable but keeps the flushed tables`() {
        val db = LsmStore.open(dir)
        db.put("auth:1", v("AUTHORIZED"))
        db.flush()
        db.put("auth:2", v("AUTHORIZED"))           // only in memory
        db.crash()
        LsmStore.open(dir).use { again ->
            assertThat(again.str("auth:1")).isEqualTo("AUTHORIZED")
            assertThat(again.get("auth:2")).`as`("the put that never left the memtable").isNull()
        }
    }

    @Test
    fun `compaction merges every table into one, newest value per key, with the tombstones gone`() {
        val rnd = Random(5)
        val expected = TreeMap<String, String>()
        LsmStore.open(dir, memtableLimit = 2_048).use { db ->
            repeat(2_000) {
                val k = "card:%03d".format(rnd.nextInt(300))
                if (rnd.nextInt(10) == 0) {
                    db.delete(k)
                    expected.remove(k)
                } else {
                    val value = "balance-$it"
                    db.put(k, v(value))
                    expected[k] = value
                }
            }
            db.flush()
            assertThat(db.tables().size).isGreaterThan(5)
            db.compact()
            assertThat(db.tables()).`as`("tables after compaction").hasSize(1)
            val only = db.tables().single()
            assertThat(only.entries().map { it.first }).`as`("keys in the compacted table: live keys only, sorted")
                .isEqualTo(expected.keys.toList())
            assertThat(only.entries().none { it.second == null }).`as`("no tombstones left").isTrue()
            for (i in 0 until 300) {
                val k = "card:%03d".format(i)
                assertThat(db.str(k)).`as`("get($k)").isEqualTo(expected[k])
            }
        }
        assertThat(Files.list(dir).use { it.count() }).`as`("files on disk: the inputs are deleted").isEqualTo(1)
        LsmStore.open(dir).use { db -> for ((k, value) in expected) assertThat(db.str(k)).isEqualTo(value) }
    }

    @Test
    fun `compaction writes every live byte again, which is write amplification`() {
        LsmStore.open(dir, memtableLimit = 4_096).use { db ->
            for (round in 1..5) for (i in 0 until 200) db.put("card:%03d".format(i), v("balance-$round-$i"))
            db.flush()
            val flushed = db.tables().sumOf { it.size }
            assertThat(db.bytesWritten).`as`("bytes written by flushes = the size of the table files").isEqualTo(flushed)
            db.compact()
            assertThat(db.bytesWritten).`as`("after compaction").isEqualTo(flushed + db.tables().single().size)
            assertThat(db.writeAmplification).isGreaterThan(1.0)
        }
    }
}
