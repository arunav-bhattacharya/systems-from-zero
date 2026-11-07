package sfz.os.l01

/**
 * One system call, as strace printed it.
 *
 * @property pid the task (process or thread) that made the call; 0 when the line had no pid prefix
 * @property name the system call, such as `openat` or `clone3`
 * @property args everything between the parentheses, unparsed
 * @property result the return value; null when strace printed `?` (the call never returned, like `exit_group`)
 * @property errno the error name when the call failed, such as `ENOENT`; null on success
 */
data class Syscall(val pid: Int, val name: String, val args: String, val result: Long?, val errno: String?) {
    val failed: Boolean get() = errno != null
}

/**
 * Turns the text of `strace -f -o trace.txt <command>` into [Syscall]s.
 *
 * The lines look like this (real lines from a JVM start-up in the lab box):
 * ```
 * 143   openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3
 * 143   faccessat(AT_FDCWD, "/etc/ld.so.preload", R_OK) = -1 ENOENT (No such file or directory)
 * 143   mmap(NULL, 8192, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0xffff8c2b2000
 * 69    clone(child_stack=0xffff6d837a60, flags=CLONE_VM|CLONE_THREAD <unfinished ...>
 * 70    futex(0xffff8cdaf270, FUTEX_WAKE_PRIVATE, 1) = 0
 * 69    <... clone resumed>, parent_tid=[71], tls=0xffff6d6388e0) = 71
 * 143   exit_group(0)                     = ?
 * 143   +++ exited with 0 +++
 * --- SIGCHLD {si_signo=SIGCHLD, si_code=CLD_EXITED, si_pid=50} ---
 * ```
 * When strace writes to the terminal instead of a file, the prefix is `[pid    50] ` instead of `50    `.
 * A line with no prefix at all comes from a trace without `-f`; its pid is 0.
 *
 * When another thread prints in the middle of a call, strace splits it: an `<unfinished ...>` line,
 * then later a `<... name resumed>` line from the same pid. Join the two halves into one [Syscall]
 * whose args are the first half's args followed by the resumed part.
 */
object StraceParser {
    /** Splits off the pid. Group 1 (`[pid N]` form) or group 2 (`N` form) is the pid; group 3 is the rest. */
    val PREFIX = Regex("""^(?:\[pid\s+(\d+)\]\s+|(\d+)\s+)?(.*)$""")

    /** A whole call: group 1 is the name, group 2 the args, group 3 the result text. */
    val COMPLETE = Regex("""^(\w+)\((.*)\)\s+=\s+(.+)$""")

    /** The first half of a split call: group 1 is the name, group 2 the args so far. */
    val UNFINISHED = Regex("""^(\w+)\((.*?)\s*<unfinished \.\.\.>$""")

    /** The second half: group 1 is the name, group 2 the rest of the args, group 3 the result text. */
    val RESUMED = Regex("""^<\.\.\. (\w+) resumed>(.*)\)\s+=\s+(.+)$""")

    /**
     * Parses a whole trace. Returns the calls in the order they finished.
     * Skips `+++ exited ... +++` and `--- SIGNAL ... ---` lines, and anything else that is not a call.
     * Drops an unfinished call that never resumes.
     */
    fun parse(lines: List<String>): List<Syscall> {
        TODO("match PREFIX, then COMPLETE, UNFINISHED or RESUMED; keep unfinished halves in a map by pid")
    }

    /**
     * Reads the text after `= `:
     * `"3"` gives (3, null), `"0xffff8c2b2000"` gives (0xffff8c2b2000, null),
     * `"-1 ENOENT (No such file or directory)"` gives (-1, "ENOENT"), `"?"` gives (null, null).
     * Ignore anything after the first word unless the second word is an error name (E followed by capitals),
     * so `"0x2 (flags O_RDWR)"` gives (2, null).
     */
    fun parseResult(text: String): Pair<Long?, String?> {
        TODO("split on whitespace: first word is the number (decimal, 0x hex, or ?), second may be the errno")
    }
}
