package sfz.bigdata.l12

import kotlin.math.ceil
import kotlin.math.roundToLong

const val GB: Long = 1_000_000_000L
const val TB: Long = 1_000L * GB

enum class Engine { SINGLE_NODE, INTERACTIVE_CLUSTER, BATCH_CLUSTER, STREAMING }

data class Machine(
    val cores: Int,
    val memoryBytes: Long,
    val decodeBytesPerSecondPerCore: Long,
    val ioBytesPerSecond: Long,
)

data class Workload(
    val name: String,
    val tableBytes: Long,
    val partitionsRead: Double,
    val columnsRead: Double,
    val workingSetBytes: Long,
    val timeBudgetSeconds: Double,
    val concurrent: Int = 1,
    val continuous: Boolean = false,
)

data class Route(val engine: Engine, val bytesRead: Long, val singleNodeSeconds: Double, val machines: Int)

object EngineChoice {

    // size the query, not the lake: pruning partitions and columns comes before any hardware
    fun bytesRead(w: Workload): Long = (w.tableBytes * w.partitionsRead * w.columnsRead).roundToLong()

    // the slowest stage sets the speed: cores decoding, or the disk or network feeding them
    fun scanBytesPerSecond(m: Machine): Long = minOf(m.cores * m.decodeBytesPerSecondPerCore, m.ioBytesPerSecond)

    // ten analysts at once each get a tenth of the machine
    fun singleNodeSeconds(w: Workload, m: Machine): Double =
        bytesRead(w).toDouble() / scanBytesPerSecond(m) * w.concurrent

    fun choose(w: Workload, m: Machine): Route {
        val bytes = bytesRead(w)
        val seconds = singleNodeSeconds(w, m)
        // a stream is a different shape of work: it never finishes, so time budgets don't apply
        if (w.continuous) return Route(Engine.STREAMING, bytes, seconds, 1)
        // one machine wins whenever it is fast enough: no network, no scheduling, no cluster to run
        if (seconds <= w.timeBudgetSeconds && w.workingSetBytes <= m.memoryBytes) {
            return Route(Engine.SINGLE_NODE, bytes, seconds, 1)
        }
        // otherwise split the scan and the working set over enough machines
        val forTime = ceil(seconds / w.timeBudgetSeconds).toInt()
        val forMemory = ceil(w.workingSetBytes.toDouble() / m.memoryBytes).toInt()
        val machines = maxOf(2, forTime, forMemory)
        // seconds-scale answers want an engine that pipelines in memory; hour-scale jobs want task retries
        val engine = if (w.timeBudgetSeconds <= 60.0) Engine.INTERACTIVE_CLUSTER else Engine.BATCH_CLUSTER
        return Route(engine, bytes, seconds, machines)
    }
}
