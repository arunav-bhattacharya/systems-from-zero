package sfz.os.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.os.support.Captured

class StraceTest {
    // `strace -f -o ... java -cp /tmp/out sfz.os.l01.demo.Hello`, captured in the lab box (Docker's default seccomp)
    private val jvmTrace = Captured.lines("/sfz/os/l01/hello-jvm.strace.txt")

    @Test
    fun `parseResult reads decimal, hex, errors and the unknown result`() {
        assertThat(StraceParser.parseResult("3")).isEqualTo(3L to null)
        assertThat(StraceParser.parseResult("0xffff8c2b2000")).isEqualTo(0xffff8c2b2000L to null)
        assertThat(StraceParser.parseResult("-1 ENOENT (No such file or directory)")).isEqualTo(-1L to "ENOENT")
        assertThat(StraceParser.parseResult("?")).isEqualTo(null to null)
        assertThat(StraceParser.parseResult("0x2 (flags O_RDWR)")).isEqualTo(2L to null)
    }

    @Test
    fun `parses a whole call with its pid, name, args and result`() {
        val calls = StraceParser.parse(listOf(
            """143   openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3""",
            """143   faccessat(AT_FDCWD, "/etc/ld.so.preload", R_OK) = -1 ENOENT (No such file or directory)""",
        ))
        assertThat(calls).containsExactly(
            Syscall(143, "openat", """AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC""", 3, null),
            Syscall(143, "faccessat", """AT_FDCWD, "/etc/ld.so.preload", R_OK""", -1, "ENOENT"),
        )
        assertThat(calls[1].failed).isTrue()
    }

    @Test
    fun `reads both pid prefixes and lines without one`() {
        val calls = StraceParser.parse(listOf(
            """[pid    50] dup3(3, 1, 0)               = 1""",
            """50    close(3)                          = 0""",
            """write(1, "box\n", 4)                    = 4""",
        ))
        assertThat(calls.map { it.pid to it.name }).containsExactly(50 to "dup3", 50 to "close", 0 to "write")
    }

    @Test
    fun `joins an unfinished call with its resumed half, even with other threads in between`() {
        val calls = StraceParser.parse(listOf(
            """69    clone(child_stack=0xffff6d837a60, flags=CLONE_VM|CLONE_THREAD <unfinished ...>""",
            """70    futex(0xffff8cdaf270, FUTEX_WAKE_PRIVATE, 1) = 0""",
            """69    <... clone resumed>, parent_tid=[71], tls=0xffff6d6388e0) = 71""",
        ))
        assertThat(calls.map { it.name }).containsExactly("futex", "clone")
        val clone = calls[1]
        assertThat(clone.pid).isEqualTo(69)
        assertThat(clone.args).isEqualTo("child_stack=0xffff6d837a60, flags=CLONE_VM|CLONE_THREAD, parent_tid=[71], tls=0xffff6d6388e0")
        assertThat(clone.result).isEqualTo(71L)
    }

    @Test
    fun `skips exit and signal lines`() {
        val calls = StraceParser.parse(listOf(
            """143   exit_group(0)                     = ?""",
            """143   +++ exited with 0 +++""",
            """--- SIGCHLD {si_signo=SIGCHLD, si_code=CLD_EXITED, si_pid=50, si_uid=0, si_status=0} ---""",
        ))
        assertThat(calls).containsExactly(Syscall(143, "exit_group", "0", null, null))
    }

    @Test
    fun `counts the system calls a JVM hello world makes`() {
        val report = StraceReport(StraceParser.parse(jvmTrace))
        val counts = report.countsByName()
        assertThat(counts.values.sum()).isEqualTo(1453)
        assertThat(counts.keys.first()).isEqualTo("mmap")
        assertThat(counts).containsEntry("mmap", 275).containsEntry("futex", 251).containsEntry("execve", 1)
    }

    @Test
    fun `counts failures by errno, including the clone3 that seccomp refused`() {
        val errors = StraceReport(StraceParser.parse(jvmTrace)).errorsByErrno()
        assertThat(errors).containsEntry("ENOSYS", 1).containsEntry("ENOENT", 23).containsEntry("EAGAIN", 29)
    }

    @Test
    fun `finds the 20 threads the JVM started before main returned`() {
        val threads = StraceReport(StraceParser.parse(jvmTrace)).threadsCreated()
        assertThat(threads).hasSize(20).doesNotHaveDuplicates()
        assertThat(threads.first()).isEqualTo(144)   // the thread that runs main(): it printed the line
        assertThat(threads).contains(163)
    }

    @Test
    fun `leaves out fork, which is a clone without CLONE_THREAD`() {
        val calls = StraceParser.parse(listOf(
            """49    clone(child_stack=NULL, flags=CLONE_CHILD_CLEARTID|CLONE_CHILD_SETTID|SIGCHLD, child_tidptr=0xffffb5774fb0) = 50""",
        ))
        assertThat(StraceReport(calls).threadsCreated()).isEmpty()
    }

    @Test
    fun `lists the files the JVM opened, skipping failed lookups`() {
        val opened = StraceReport(StraceParser.parse(jvmTrace)).filesOpened()
        assertThat(opened).hasSize(51)
        assertThat(opened).contains("/opt/java/openjdk/lib/server/libjvm.so", "/opt/java/openjdk/lib/modules")
        assertThat(opened).doesNotContain("/opt/java/openjdk/bin/libjli.so")   // tried first, ENOENT
    }
}
