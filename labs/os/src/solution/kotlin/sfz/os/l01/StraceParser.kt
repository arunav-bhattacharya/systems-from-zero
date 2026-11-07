package sfz.os.l01

data class Syscall(val pid: Int, val name: String, val args: String, val result: Long?, val errno: String?) {
    val failed: Boolean get() = errno != null
}

object StraceParser {
    val PREFIX = Regex("""^(?:\[pid\s+(\d+)\]\s+|(\d+)\s+)?(.*)$""")
    val COMPLETE = Regex("""^(\w+)\((.*)\)\s+=\s+(.+)$""")
    val UNFINISHED = Regex("""^(\w+)\((.*?)\s*<unfinished \.\.\.>$""")
    val RESUMED = Regex("""^<\.\.\. (\w+) resumed>(.*)\)\s+=\s+(.+)$""")

    private val ERRNO = Regex("""E[A-Z0-9]+""")

    fun parse(lines: List<String>): List<Syscall> {
        val calls = mutableListOf<Syscall>()
        // pid -> (name, args so far): the first half of a call another thread interrupted
        val pending = mutableMapOf<Int, Pair<String, String>>()
        for (line in lines) {
            val p = PREFIX.matchEntire(line.trimEnd()) ?: continue
            val pid = (p.groupValues[1].ifEmpty { p.groupValues[2] }).toIntOrNull() ?: 0
            val rest = p.groupValues[3]

            // try the two halves of a split call first, then a whole call
            val resumed = RESUMED.matchEntire(rest)
            if (resumed != null) {
                val (name, firstHalf) = pending.remove(pid) ?: continue    // a resume we never saw start
                val (result, errno) = parseResult(resumed.groupValues[3])
                calls += Syscall(pid, name, firstHalf + resumed.groupValues[2], result, errno)
                continue
            }
            val unfinished = UNFINISHED.matchEntire(rest)
            if (unfinished != null) {
                pending[pid] = unfinished.groupValues[1] to unfinished.groupValues[2]
                continue
            }
            val complete = COMPLETE.matchEntire(rest) ?: continue       // +++ exited +++, --- SIGCHLD ---
            val (result, errno) = parseResult(complete.groupValues[3])
            calls += Syscall(pid, complete.groupValues[1], complete.groupValues[2], result, errno)
        }
        return calls                                                     // anything still pending never finished
    }

    fun parseResult(text: String): Pair<Long?, String?> {
        val words = text.trim().split(Regex("""\s+"""))
        val first = words[0]
        val result = when {
            first == "?" -> null
            first.startsWith("0x") -> first.removePrefix("0x").toULongOrNull(16)?.toLong()  // addresses can use all 64 bits
            else -> first.toLongOrNull()
        }
        // "-1 ENOENT (No such file or directory)": the errno is the second word
        val errno = words.getOrNull(1)?.takeIf { ERRNO.matches(it) }
        return result to errno
    }
}
