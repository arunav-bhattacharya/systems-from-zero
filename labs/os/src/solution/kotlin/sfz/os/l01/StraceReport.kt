package sfz.os.l01

class StraceReport(private val calls: List<Syscall>) {

    fun countsByName(): Map<String, Int> =
        calls.groupingBy { it.name }.eachCount()
            .entries.sortedByDescending { it.value }
            .associate { it.key to it.value }          // associate keeps insertion order (LinkedHashMap)

    fun errorsByErrno(): Map<String, Int> =
        calls.filter { it.failed }.groupingBy { it.errno!! }.eachCount()

    fun threadsCreated(): List<Int> =
        calls.filter { it.name == "clone" || it.name == "clone3" }
            .filter { "CLONE_THREAD" in it.args }       // without it, clone makes a process (fork)
            .filter { !it.failed && it.result != null } // Docker's seccomp answers clone3 with ENOSYS
            .map { it.result!!.toInt() }                // the parent gets the new thread's TID back

    fun filesOpened(): List<String> =
        calls.filter { it.name == "openat" && !it.failed }
            .mapNotNull { QUOTED.find(it.args)?.groupValues?.get(1) }

    private companion object {
        val QUOTED = Regex(""""([^"]*)"""")
    }
}
