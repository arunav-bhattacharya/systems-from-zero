package sfz.store.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import sfz.internals.support.CountingFileChannel
import sfz.internals.support.Crash
import java.nio.ByteBuffer
import java.nio.file.Files
import java.nio.file.Path

class LogStoreTest {
    @TempDir
    lateinit var dir: Path

    /** Hands the store counting channels, and remembers the last one it opened. */
    private class Channels : ChannelFactory {
        lateinit var last: CountingFileChannel
        override fun open(path: Path) = CountingFileChannel.open(path).also { last = it }
    }

    private val file get() = dir.resolve(LogStore.FILE_NAME)
    private fun v(s: String) = s.encodeToByteArray()
    private fun LogStore.str(key: String) = get(key)?.decodeToString()
    private fun recordLength(key: String, value: String?) = Record.length(key.length, value?.length ?: Record.TOMBSTONE)

    @Test
    fun `get returns the newest value after overwrites`() {
        LogStore.open(dir).use { db ->
            db.put("auth:9001", v("PENDING"))
            db.put("auth:9002", v("PENDING"))
            db.put("auth:9001", v("AUTHORIZED"))
            db.put("auth:9001", v("CAPTURED"))
            assertThat(db.str("auth:9001")).isEqualTo("CAPTURED")
            assertThat(db.str("auth:9002")).isEqualTo("PENDING")
            assertThat(db.get("auth:0000")).isNull()
        }
    }

    @Test
    fun `every put and delete appends one record to the end of the file`() {
        LogStore.open(dir).use { db ->
            db.put("auth:9001", v("PENDING"))
            db.put("auth:9001", v("CAPTURED"))
            db.delete("auth:9001")
        }
        val expected = recordLength("auth:9001", "PENDING") + recordLength("auth:9001", "CAPTURED") + recordLength("auth:9001", null)
        assertThat(Files.size(file)).isEqualTo(expected)
    }

    @Test
    fun `values survive close and reopen because open rebuilds the keydir from the file`() {
        LogStore.open(dir).use { db ->
            for (i in 1..200) db.put("auth:$i", v("AUTHORIZED-$i"))
            db.put("auth:7", v("CAPTURED"))
        }
        LogStore.open(dir).use { db ->
            assertThat(db.str("auth:7")).isEqualTo("CAPTURED")
            assertThat(db.str("auth:200")).isEqualTo("AUTHORIZED-200")
            assertThat(db.str("auth:1")).isEqualTo("AUTHORIZED-1")
            assertThat(db.get("auth:201")).isNull()
        }
    }

    @Test
    fun `a delete is a tombstone that survives reopen`() {
        LogStore.open(dir).use { db ->
            db.put("auth:1", v("AUTHORIZED"))
            db.put("auth:2", v("AUTHORIZED"))
            db.delete("auth:1")
            assertThat(db.get("auth:1")).isNull()
        }
        LogStore.open(dir).use { db ->
            assertThat(db.get("auth:1")).isNull()
            assertThat(db.str("auth:2")).isEqualTo("AUTHORIZED")
        }
    }

    @Test
    fun `put and delete force the file before they return`() {
        val channels = Channels()
        LogStore.open(dir, channels).use { db ->
            val ch = channels.last
            for (i in 1..20) {
                ch.resetCounts()
                db.put("auth:$i", v("AUTHORIZED"))
                assertThat(ch.writes).`as`("writes during put #$i").isGreaterThanOrEqualTo(1)
                assertThat(ch.events.last()).`as`("the last thing put #$i does to the file").isEqualTo("force")
            }
            ch.resetCounts()
            db.delete("auth:3")
            assertThat(ch.events.last()).`as`("the last thing delete does to the file").isEqualTo("force")
        }
    }

    @Test
    fun `get does exactly one read, and a missing key does none`() {
        LogStore.open(dir).use { db -> for (i in 1..50) db.put("auth:$i", v("AUTHORIZED-$i".repeat(i))) }
        val channels = Channels()
        LogStore.open(dir, channels).use { db ->
            val ch = channels.last
            ch.resetCounts()
            for (i in 1..50) assertThat(db.str("auth:$i")).isEqualTo("AUTHORIZED-$i".repeat(i))
            assertThat(ch.reads).`as`("reads for 50 gets").isEqualTo(50)
            ch.resetCounts()
            assertThat(db.get("auth:999")).isNull()
            assertThat(ch.reads).`as`("reads for a missing key").isZero()
        }
    }

    @Test
    fun `recovery drops a torn last record wherever the crash cut it`() {
        val last = recordLength("auth:3", "CAPTURED")
        for (cut in 1..last) {
            val d = Files.createDirectory(dir.resolve("cut-$cut"))
            LogStore.open(d).use { db ->
                db.put("auth:1", v("AUTHORIZED"))
                db.put("auth:2", v("AUTHORIZED"))
                db.put("auth:3", v("CAPTURED"))
            }
            Crash.chopTail(d.resolve(LogStore.FILE_NAME), cut)
            LogStore.open(d).use { db ->
                assertThat(db.str("auth:1")).`as`("auth:1 after cutting $cut bytes").isEqualTo("AUTHORIZED")
                assertThat(db.str("auth:2")).`as`("auth:2 after cutting $cut bytes").isEqualTo("AUTHORIZED")
                assertThat(db.get("auth:3")).`as`("the torn record after cutting $cut bytes").isNull()
            }
        }
    }

    @Test
    fun `recovery truncates the torn tail so the next put survives the next restart`() {
        LogStore.open(dir).use { db ->
            db.put("auth:1", v("AUTHORIZED"))
            db.put("auth:2", v("CAPTURED"))
        }
        Crash.chopTail(file, 5)
        LogStore.open(dir).use { db -> db.put("auth:3", v("AUTHORIZED")) }
        assertThat(Files.size(file)).`as`("file size: the torn bytes must be gone")
            .isEqualTo(recordLength("auth:1", "AUTHORIZED") + recordLength("auth:3", "AUTHORIZED"))
        LogStore.open(dir).use { db ->
            assertThat(db.str("auth:1")).isEqualTo("AUTHORIZED")
            assertThat(db.get("auth:2")).isNull()
            assertThat(db.str("auth:3")).`as`("the put made after recovery").isEqualTo("AUTHORIZED")
        }
    }

    @Test
    fun `recovery drops a last record whose bytes were damaged, because its CRC no longer matches`() {
        LogStore.open(dir).use { db ->
            db.put("auth:1", v("AUTHORIZED"))
            db.put("auth:2", v("CAPTURED"))
        }
        // damage one byte inside the value of the last record; the sizes still look fine
        Crash.flipByte(file, Files.size(file) - 3)
        LogStore.open(dir).use { db ->
            assertThat(db.str("auth:1")).isEqualTo("AUTHORIZED")
            assertThat(db.get("auth:2")).isNull()
        }
    }

    @Test
    fun `recovery does not trust sizes in a torn header`() {
        LogStore.open(dir).use { db -> db.put("auth:1", v("AUTHORIZED")) }
        // half a write: a header that claims a 2 GB key, then nothing
        val junk = ByteBuffer.allocate(Record.HEADER_SIZE)
            .putInt(0x1234).putLong(0L).putInt(Int.MAX_VALUE).putInt(16).array()
        Crash.appendJunk(file, junk)
        LogStore.open(dir).use { db ->
            assertThat(db.str("auth:1")).isEqualTo("AUTHORIZED")
            db.put("auth:2", v("AUTHORIZED"))
        }
        LogStore.open(dir).use { db -> assertThat(db.str("auth:2")).isEqualTo("AUTHORIZED") }
    }

    @Test
    fun `merge keeps exactly one record per live key and the newest values`() {
        LogStore.open(dir).use { db ->
            for (round in 1..100) for (k in 0 until 10) db.put("card:$k", v("balance-$round"))
            val before = Files.size(file)
            db.merge()
            val live = (0 until 10).sumOf { recordLength("card:$it", "balance-100") }
            assertThat(Files.size(file)).`as`("file size after merge").isEqualTo(live).isLessThan(before)
            for (k in 0 until 10) assertThat(db.str("card:$k")).isEqualTo("balance-100")
            db.put("card:0", v("after-merge"))
        }
        LogStore.open(dir).use { db ->
            assertThat(db.str("card:0")).isEqualTo("after-merge")
            for (k in 1 until 10) assertThat(db.str("card:$k")).isEqualTo("balance-100")
        }
    }

    @Test
    fun `merge drops deleted keys and their tombstones for good`() {
        LogStore.open(dir).use { db ->
            db.put("auth:1", v("AUTHORIZED"))
            db.put("auth:2", v("AUTHORIZED"))
            db.delete("auth:1")
            db.merge()
            assertThat(db.get("auth:1")).isNull()
            assertThat(Files.size(file)).isEqualTo(recordLength("auth:2", "AUTHORIZED"))
        }
        LogStore.open(dir).use { db ->
            assertThat(db.get("auth:1")).isNull()
            assertThat(db.str("auth:2")).isEqualTo("AUTHORIZED")
        }
        assertThat(Files.list(dir).use { s -> s.map { it.fileName.toString() }.toList() })
            .`as`("files left in the directory").containsExactly(LogStore.FILE_NAME)
    }
}
