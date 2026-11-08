package sfz.batch.l15

/** Decimal units, like lesson 1: 1 GB is 1,000,000,000 bytes. */
const val GB: Long = 1_000_000_000L
const val TB: Long = 1_000L * GB

/** Where a query should run. */
enum class Engine {
    /** One machine, in process: DuckDB (or Polars, or Postgres on a big VM). */
    SINGLE_NODE,

    /** A cluster for interactive SQL that answers in seconds: Trino. */
    INTERACTIVE_CLUSTER,

    /** A cluster for long batch jobs that must survive failed tasks: Spark. */
    BATCH_CLUSTER,

    /** An engine that processes events as they arrive: Spark Structured Streaming or Flink. */
    STREAMING,
}

/**
 * One machine. A scan is limited by the slower of two stages (lesson 1): the CPU decoding
 * Parquet, [cores] x [decodeBytesPerSecondPerCore], and the storage feeding it, [ioBytesPerSecond].
 */
data class Machine(
    val cores: Int,
    val memoryBytes: Long,
    val decodeBytesPerSecondPerCore: Long,
    val ioBytesPerSecond: Long,
)

/** A query or job, described by what it reads and what it needs. */
data class Workload(
    val name: String,
    /** Compressed bytes of the whole table on disk. */
    val tableBytes: Long,
    /** Share of the table's partitions the query keeps after partition pruning, 0 to 1. */
    val partitionsRead: Double,
    /** Share of each row's bytes in the columns the query needs, 0 to 1. */
    val columnsRead: Double,
    /** Memory the biggest join build side or aggregation needs to hold at once. */
    val workingSetBytes: Long,
    /** How long the answer may take. */
    val timeBudgetSeconds: Double,
    /** How many people or jobs run it at the same time. */
    val concurrent: Int = 1,
    /** True if it must process events continuously as they arrive. */
    val continuous: Boolean = false,
)

/** The answer: where to run it, and the numbers behind the choice. */
data class Route(
    val engine: Engine,
    /** Bytes the query reads after pruning partitions and columns. */
    val bytesRead: Long,
    /** Seconds on one machine, with [Workload.concurrent] copies sharing it. */
    val singleNodeSeconds: Double,
    /** Machines like the given one needed to meet the time budget and hold the working set (1 for a single node). */
    val machines: Int,
)

/** The rubric of lesson 15, as code. */
object EngineChoice {

    /** Bytes the query reads: table bytes x partitions read x columns read, rounded to the nearest byte. */
    fun bytesRead(w: Workload): Long {
        TODO("tableBytes x partitionsRead x columnsRead")
    }

    /** Bytes per second one machine scans: the slower of all cores decoding and the storage feeding them. */
    fun scanBytesPerSecond(m: Machine): Long {
        TODO("min(cores x decode speed per core, io speed)")
    }

    /**
     * Seconds for [m] to scan what [w] reads, when [Workload.concurrent] copies of it share the
     * machine at once (each gets a 1/concurrent share of the scan speed).
     */
    fun singleNodeSeconds(w: Workload, m: Machine): Double {
        TODO("bytesRead / scan speed x concurrent")
    }

    /**
     * Routes [w], given machines like [m]:
     * 1. continuous work goes to [Engine.STREAMING], whatever its size (machines = 1);
     * 2. if one machine meets the time budget and the working set fits in its memory: [Engine.SINGLE_NODE], 1 machine;
     * 3. otherwise a cluster of machines = the larger of ceil(singleNodeSeconds / budget) and
     *    ceil(workingSet / memory), at least 2: [Engine.INTERACTIVE_CLUSTER] if the budget is
     *    60 seconds or less, else [Engine.BATCH_CLUSTER].
     */
    fun choose(w: Workload, m: Machine): Route {
        TODO("streaming first, then one machine if it fits, then size a cluster")
    }
}
