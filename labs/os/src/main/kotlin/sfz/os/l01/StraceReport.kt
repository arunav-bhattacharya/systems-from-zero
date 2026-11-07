package sfz.os.l01

/**
 * Answers questions about a parsed trace: what did this program ask the kernel for?
 */
class StraceReport(private val calls: List<Syscall>) {

    /** How many times each system call ran, most frequent first (ties in any order). */
    fun countsByName(): Map<String, Int> {
        TODO("group by name, count, sort by count descending into a LinkedHashMap")
    }

    /** How many calls failed with each errno, such as ENOENT or EAGAIN. */
    fun errorsByErrno(): Map<String, Int> {
        TODO("only failed calls, grouped by errno")
    }

    /**
     * The TIDs of the threads this program created. A thread is a successful `clone` or `clone3`
     * whose flags include `CLONE_THREAD`; the result is the new thread's TID.
     * A `clone` without `CLONE_THREAD` makes a new process (that is how `fork()` works), so leave it out.
     * A `clone3` that failed made nothing.
     */
    fun threadsCreated(): List<Int> {
        TODO("filter clone/clone3 by CLONE_THREAD in args and success")
    }

    /**
     * The paths opened successfully with `openat`, in trace order. The path is the second argument,
     * the first quoted string: `openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC)`.
     */
    fun filesOpened(): List<String> {
        TODO("successful openat calls; pull the first \"...\" out of args")
    }
}
