package sfz.os.l03

data class DumpedThread(
    val name: String,
    val javaId: Long?,
    val osTid: Int,
    val daemon: Boolean,
    val state: String?,
    val topFrame: String?,
)

object ThreadDump {
    val HEADER = Regex("""^"(.*)"\s+(?:#(\d+)\s+)?(?:\[\d+\]\s+)?(daemon\s+)?.*?\bnid=(0x[0-9a-fA-F]+|\d+)""")

    private const val STATE = "java.lang.Thread.State:"

    fun nidToTid(nid: String): Int =
        if (nid.startsWith("0x")) nid.removePrefix("0x").toInt(16)   // JDK 17 and older
        else nid.toInt()                                             // JDK 18+ (JDK-8268425)

    fun parse(text: String): List<DumpedThread> {
        val lines = text.lines()
        val out = mutableListOf<DumpedThread>()
        for ((i, line) in lines.withIndex()) {
            val m = HEADER.find(line) ?: continue
            // the thread's own lines run until the first blank line
            val body = lines.drop(i + 1).takeWhile { it.isNotBlank() }.map { it.trim() }
            out += DumpedThread(
                name = m.groupValues[1],
                javaId = m.groupValues[2].toLongOrNull(),            // VM-internal threads have no #id
                osTid = nidToTid(m.groupValues[4]),
                daemon = m.groupValues[3].isNotEmpty(),
                state = body.firstOrNull { it.startsWith(STATE) }
                    ?.removePrefix(STATE)?.trim()?.substringBefore(" "),   // "TIMED_WAITING (sleeping)" -> "TIMED_WAITING"
                topFrame = body.firstOrNull { it.startsWith("at ") }?.removePrefix("at "),
            )
        }
        return out
    }
}

data class OsTask(val tid: Int, val cpuPercent: Double, val comm: String)

object PsThreads {
    fun parse(text: String): List<OsTask> =
        text.lines()
            .map { it.trim() }
            .filter { it.isNotEmpty() && !it.startsWith("TID") }
            .map { line ->
                val (tid, pcpu, _, comm) = line.split(Regex("""\s+"""), limit = 4)
                OsTask(tid.toInt(), pcpu.toDouble(), comm)
            }
}

class ThreadMap(private val threads: List<DumpedThread>, private val tasks: List<OsTask>) {
    private val byTid = threads.associateBy { it.osTid }             // the TID is the only reliable key

    fun javaThreadFor(tid: Int): DumpedThread? = byTid[tid]

    fun hottest(): Pair<OsTask, DumpedThread?> {
        val task = tasks.maxBy { it.cpuPercent }                     // what top -H would put first
        return task to javaThreadFor(task.tid)
    }

    // e.g. the launcher's first thread (TID = PID): it only waits for main to finish, and jstack skips it
    fun tasksNotInDump(): List<OsTask> = tasks.filter { it.tid !in byTid }
}
