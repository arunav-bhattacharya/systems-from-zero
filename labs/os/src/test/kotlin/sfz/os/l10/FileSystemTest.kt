package sfz.os.l10

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.os.support.Captured

class FileSystemTest {
    private val links = Captured.lines("/sfz/os/l10/links.txt")
    private val share = Captured.lines("/sfz/os/l10/share.txt")
    private val deleted = Captured.lines("/sfz/os/l10/deleted-log.txt")
    private val leak = Captured.lines("/sfz/os/l10/fdleak.txt")

    private val record = "auth-7731,4111,120.00,approved\n"

    /** "name: inode N, L links" from the captured stat lines. */
    private fun stat(name: String, nth: Int = 0): Pair<Long, Int> {
        val m = links.filter { it.startsWith("$name:") }[nth].let { Regex("""inode (\d+), (\d+) links""").find(it)!! }
        return m.groupValues[1].toLong() to m.groupValues[2].toInt()
    }

    private fun withLedger(): FileSystem {
        val fs = FileSystem()
        fs.mkdir("/tmp")
        val p = fs.spawn()
        val fd = fs.open(p, "/tmp/ledger.csv", setOf(Flag.WRITE, Flag.CREATE, Flag.TRUNC))
        fs.write(p, fd, record)
        fs.exit(p)
        return fs
    }

    @Test
    fun `a hard link is a second name for the same inode`() {
        val fs = withLedger()
        fs.link("/tmp/ledger.csv", "/tmp/ledger-2026.csv")

        val a = fs.resolve("/tmp/ledger.csv")
        val b = fs.resolve("/tmp/ledger-2026.csv")
        assertThat(b).isSameAs(a)                                         // one inode, two directory entries
        assertThat(a.links).isEqualTo(2)
        assertThat(stat("ledger.csv").first).isEqualTo(stat("ledger-2026.csv").first)   // the lab box agrees
        assertThat(stat("ledger.csv").second).isEqualTo(a.links)
        assertThat(a.size).isEqualTo(31)
    }

    @Test
    fun `rm removes one name, and the inode lives on while another name is left`() {
        val fs = withLedger()
        fs.link("/tmp/ledger.csv", "/tmp/ledger-2026.csv")
        val inode = fs.resolve("/tmp/ledger.csv")
        fs.unlink("/tmp/ledger.csv")

        assertThat(fs.exists("/tmp/ledger.csv")).isFalse()
        assertThat(fs.resolve("/tmp/ledger-2026.csv").data.toString()).isEqualTo(record)
        assertThat(inode.links).isEqualTo(stat("ledger-2026.csv", 1).second)   // 1, as stat said after rm
        assertThat(fs.liveInodes).contains(inode)

        fs.unlink("/tmp/ledger-2026.csv")                                   // the last name: now it's gone
        assertThat(fs.liveInodes).doesNotContain(inode)
    }

    @Test
    fun `a symlink holds a path, and dangles once that name is gone`() {
        val fs = withLedger()
        fs.link("/tmp/ledger.csv", "/tmp/ledger-2026.csv")
        val s = fs.symlink("ledger.csv", "/tmp/latest.csv")              // ln -s ledger.csv latest.csv

        assertThat(s.number).isNotEqualTo(fs.resolve("/tmp/ledger.csv").number)   // its own inode
        assertThat(fs.resolve("/tmp/latest.csv")).isSameAs(fs.resolve("/tmp/ledger.csv"))
        assertThat(s.size).isEqualTo(Regex("""latest.csv: inode \d+, 1 links, (\d+) bytes""").find(links.joinToString("\n"))!!.groupValues[1].toInt())

        fs.unlink("/tmp/ledger.csv")
        assertThatThrownBy { fs.resolve("/tmp/latest.csv") }.hasMessageContaining("ENOENT")   // cat: No such file
        assertThat(fs.resolve("/tmp/ledger-2026.csv").data.toString()).isEqualTo(record)        // the hard link still works
    }

    @Test
    fun `a directory can't get a hard link, and a name can't be taken twice`() {
        val fs = withLedger()
        fs.mkdir("/tmp/d")
        assertThatThrownBy { fs.link("/tmp/d", "/tmp/e") }.hasMessageContaining("EPERM")
        assertThatThrownBy { fs.link("/tmp/ledger.csv", "/tmp/d") }.hasMessageContaining("EEXIST")
        assertThatThrownBy { fs.unlink("/tmp/nope") }.hasMessageContaining("ENOENT")
    }

    @Test
    fun `open returns the lowest free descriptor`() {
        val fs = withLedger()
        val p = fs.spawn()                                                  // 0, 1 and 2 are taken
        val a = fs.open(p, "/tmp/ledger.csv", setOf(Flag.READ))
        val b = fs.open(p, "/tmp/ledger.csv", setOf(Flag.READ))
        assertThat(a to b).isEqualTo(3 to 4)
        assertThat(p.fds[a]).isNotSameAs(p.fds[b])                          // two opens, two descriptions
        fs.close(p, a)
        assertThat(fs.open(p, "/tmp/ledger.csv", setOf(Flag.READ))).isEqualTo(3)
        fs.close(p, 1)
        assertThat(fs.open(p, "/tmp/ledger.csv", setOf(Flag.WRITE))).isEqualTo(1)   // how a shell redirects stdout
    }

    /** The records and offsets share.c printed for one of its three runs. */
    private fun captured(run: Int): Pair<List<String>, List<Int>> {
        val start = share.indexOfFirst { it.startsWith("$run. ") }
        val block = share.drop(start + 1).takeWhile { !Regex("""^\d\. """).containsMatchIn(it) }
        val offsets = block.mapNotNull { Regex("""offset (?:is now|before it writes:) ?(\d+)""").find(it)?.groupValues?.get(1)?.toInt() }
        val recs = block.filter { it.trim().matches(Regex("""(child|parent) +auth \d""")) }.map { it.trim() }
        return recs to offsets
    }

    /** share.c with the model: the child writes three records and exits, then the parent writes three. */
    private fun replay(run: Int): Pair<List<String>, List<Int>> {
        val fs = FileSystem()
        fs.mkdir("/tmp")
        val parent = fs.spawn()
        val offsets = mutableListOf<Int>()
        val create = setOf(Flag.WRITE, Flag.CREATE, Flag.TRUNC)
        val each = if (run == 3) setOf(Flag.WRITE, Flag.APPEND) else setOf(Flag.WRITE)
        var fd = -1
        if (run == 1) fd = fs.open(parent, "/tmp/auth.log", create) else fs.close(parent, fs.open(parent, "/tmp/auth.log", create))
        val child = fs.fork(parent)
        val childFd = if (run == 1) fd else fs.open(child, "/tmp/auth.log", each)
        if (run != 1) fd = fs.open(parent, "/tmp/auth.log", each)
        for (i in 1..3) fs.write(child, childFd, "%-6s auth %d\n".format("child", i))
        offsets += child.fds.getValue(childFd).offset
        fs.exit(child)
        offsets += parent.fds.getValue(fd).offset
        for (i in 1..3) fs.write(parent, fd, "%-6s auth %d\n".format("parent", i))
        offsets += parent.fds.getValue(fd).offset
        val text = fs.resolve("/tmp/auth.log").data.toString()
        return text.lines().filter { it.isNotBlank() }.map { it.trim() } to offsets
    }

    @Test
    fun `open then fork gives both processes one description and one offset`() {
        val (records, offsets) = replay(1)
        assertThat(offsets).isEqualTo(listOf(42, 42, 84))                   // the parent's offset moved without it writing
        assertThat(records to offsets).isEqualTo(captured(1))
    }

    @Test
    fun `two opens give two offsets, and the second writer overwrites the first`() {
        val (records, offsets) = replay(2)
        assertThat(records).containsExactly("parent auth 1", "parent auth 2", "parent auth 3")
        assertThat(records to offsets).isEqualTo(captured(2))
    }

    @Test
    fun `with O_APPEND every write lands at the end, whatever the offset was`() {
        val (records, offsets) = replay(3)
        assertThat(records).hasSize(6)
        assertThat(records to offsets).isEqualTo(captured(3))
    }

    @Test
    fun `a deleted file stays until its last descriptor closes, and df counts it while du doesn't`() {
        val fs = FileSystem()
        fs.mkdir("/dev")
        fs.mkdir("/dev/shm")
        val jvm = fs.spawn(extra = 1)                                       // 0, 1, 2 and the JDK's modules file
        val fd = fs.open(jvm, "/dev/shm/auth.log", setOf(Flag.WRITE, Flag.CREATE, Flag.APPEND))
        val mb = "x".repeat(1 shl 20)
        repeat(40) { fs.write(jvm, fd, mb) }                                // LogHolder's 40 MB
        val blocks = fs.dfBlocks()

        fs.unlink("/dev/shm/auth.log")
        assertThat(fs.dfBlocks()).isEqualTo(blocks).isEqualTo(40 * 256)     // still using 40 MB
        assertThat(fs.duBlocks("/dev/shm")).isZero()                       // but no name reaches it
        val lsFd = deleted.first { it.contains("(deleted)") && it.contains("->") }
        assertThat(lsFd).contains(" $fd -> ")                               // the same fd number as the real JVM got
        assertThat(lsFd).endsWith(fs.procFd(jvm, fd, "/dev/shm/auth.log"))
        assertThat(deleted.first { it.startsWith("0") && it.contains("/dev/shm") }).startsWith("0")   // du said 0

        fs.write(jvm, fd, "one more line\n")                                // the service keeps logging into it
        fs.close(jvm, fd)
        assertThat(fs.dfBlocks()).isZero()
    }

    @Test
    fun `after fork the deleted file lives until both processes close it`() {
        val fs = withLedger()
        val parent = fs.spawn()
        val fd = fs.open(parent, "/tmp/ledger.csv", setOf(Flag.READ))
        val child = fs.fork(parent)
        val inode = fs.resolve("/tmp/ledger.csv")
        fs.unlink("/tmp/ledger.csv")
        fs.close(parent, fd)

        assertThat(fs.liveInodes).contains(inode)                           // the child still holds the description
        assertThat(fs.read(child, fd, 9)).isEqualTo("auth-7731")
        fs.close(child, fd)
        assertThat(fs.liveInodes).doesNotContain(inode)
    }

    @Test
    fun `open fails with EMFILE once the table is full`() {
        val fs = withLedger()
        val jvm = fs.spawn(limit = 256, extra = 1)
        val atStart = Regex("""at start: (\d+)""").find(leak.joinToString("\n"))!!.groupValues[1].toInt()
        val failedAt = Regex("""open number (\d+) failed""").find(leak.joinToString("\n"))!!.groupValues[1].toInt()
        assertThat(jvm.fds.size).isEqualTo(atStart)                         // 4, like the JVM in the lab box

        var opened = 0
        val error = runCatching { while (true) { fs.open(jvm, "/tmp/ledger.csv", setOf(Flag.READ)); opened++ } }.exceptionOrNull()
        assertThat(error).isInstanceOf(FsError::class.java).hasMessageContaining("EMFILE")
        assertThat(opened + 1).isEqualTo(failedAt)                          // open number 253 failed
        assertThat(jvm.fds.size).isEqualTo(256)
    }
}
