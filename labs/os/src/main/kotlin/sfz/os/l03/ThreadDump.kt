package sfz.os.l03

/**
 * One thread from a `jstack <pid>` dump.
 *
 * @property name the Java thread name, without the quotes
 * @property javaId the `#27` number (the Java thread id); null for JVM-internal threads such as "VM Thread"
 * @property osTid the `nid`: the kernel's thread id, the TID you see in `ps -L`, `top -H` and /proc/<pid>/task
 * @property daemon true when the header says `daemon`
 * @property state the first word after `java.lang.Thread.State:`, such as "RUNNABLE" or "TIMED_WAITING"
 *   (drop the "(sleeping)" part); null when the thread has no state line
 * @property topFrame the first `at ...` line of the stack, without the leading `at `; null when there is no stack
 */
data class DumpedThread(
    val name: String,
    val javaId: Long?,
    val osTid: Int,
    val daemon: Boolean,
    val state: String?,
    val topFrame: String?,
)

/**
 * Parses jstack output. A real JDK 25 thread looks like this:
 * ```
 * "fraud-scorer" #27 [64] prio=5 os_prio=0 cpu=6158.85ms elapsed=6.17s tid=0x0000ffffb414db90 nid=64 runnable  [0x0000ffff8225d000]
 *    java.lang.Thread.State: RUNNABLE
 * 	at sfz.os.l03.demo.PaymentWorkers.score(PaymentWorkers.java:45)
 * 	at java.lang.Thread.run(java.base@25.0.5/Thread.java:1474)
 *
 * "VM Thread" os_prio=0 cpu=0.56ms elapsed=6.18s tid=0x0000ffffb411efb0 nid=52 runnable
 * ```
 * A header starts with a quote. The lines after it, up to the next blank line, belong to that thread.
 * JDK 18 and later print `nid` in decimal. JDK 17 and older print it in hex: `nid=0x40`.
 */
object ThreadDump {
    /**
     * Matches a header line. Group 1: name. Group 2: java id (may be empty). Group 3: "daemon " (may be empty).
     * Group 4: the nid text, decimal or 0x hex.
     */
    val HEADER = Regex("""^"(.*)"\s+(?:#(\d+)\s+)?(?:\[\d+\]\s+)?(daemon\s+)?.*?\bnid=(0x[0-9a-fA-F]+|\d+)""")

    /** "64" gives 64 (JDK 18+), "0x40" gives 64 (JDK 17 and older). */
    fun nidToTid(nid: String): Int {
        TODO("hex when it starts with 0x, decimal otherwise")
    }

    /** Every thread in the dump, in the order jstack printed them. */
    fun parse(text: String): List<DumpedThread> {
        TODO("find header lines with HEADER, then read the state and the first 'at' line below each one")
    }
}

/** One kernel task from `ps -L -p <pid> -o tid,pcpu,time,comm`. */
data class OsTask(val tid: Int, val cpuPercent: Double, val comm: String)

/** Parses `ps -L -p <pid> -o tid,pcpu,time,comm` output. Written for you. */
object PsThreads {
    fun parse(text: String): List<OsTask> =
        text.lines()
            .map { it.trim() }
            .filter { it.isNotEmpty() && !it.startsWith("TID") }       // skip the header
            .map { line ->
                // comm may contain spaces ("GC Thread#0"), so split into at most 4 columns
                val (tid, pcpu, _, comm) = line.split(Regex("""\s+"""), limit = 4)
                OsTask(tid.toInt(), pcpu.toDouble(), comm)
            }
}

/**
 * Joins what the kernel sees (tasks) with what the JVM sees (threads). The join key is the TID.
 * Never join on the name: the kernel keeps only the first 15 characters of a thread name, so twelve
 * different "ForkJoinPool-1-worker-N" threads all show up as "ForkJoinPool-1-".
 */
class ThreadMap(private val threads: List<DumpedThread>, private val tasks: List<OsTask>) {

    /** The Java thread running on kernel task [tid], or null if the dump has no thread with that TID. */
    fun javaThreadFor(tid: Int): DumpedThread? {
        TODO("match on osTid")
    }

    /** The task using the most CPU, with its Java thread (null if jstack did not list it). */
    fun hottest(): Pair<OsTask, DumpedThread?> {
        TODO("max by cpuPercent, then javaThreadFor")
    }

    /** Tasks that the dump does not mention, in ps order. */
    fun tasksNotInDump(): List<OsTask> {
        TODO("tasks whose tid is no thread's osTid")
    }
}
