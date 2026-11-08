package sfz.dist.l06

/**
 * A Snowflake-style id generator: 41 bits of milliseconds since [EPOCH_MS], 10 bits of machine id (0 to 1,023) and
 * 12 bits of sequence (4,096 ids per millisecond), in one positive Long. [clock] reads the wall clock in ms.
 */
class SnowflakeIds(val machine: Int, val clock: () -> Long) {
    init {
        require(machine in 0..MAX_MACHINE) { "machine id must fit in 10 bits" }
    }

    private var lastMs = -1L
    private var sequence = 0

    /** The next id: always larger than every id this generator has made, whatever the clock does. */
    fun next(): Long {
        var ms = maxOf(clock(), lastMs)               // the clock stepped back? keep using the last millisecond
        if (ms == lastMs) {
            sequence++
            if (sequence > MAX_SEQUENCE) {            // 4,096 ids in this millisecond already:
                ms = lastMs + 1                       // borrow the next one and run slightly ahead of the clock
                sequence = 0
            }
        } else {
            sequence = 0
        }
        lastMs = ms
        return compose(ms, machine, sequence)
    }

    companion object {
        /** 2026-01-01T00:00:00Z. Twitter's original used its own epoch in November 2010. */
        const val EPOCH_MS = 1_767_225_600_000L
        const val MAX_MACHINE = 0x3FF
        const val MAX_SEQUENCE = 0xFFF

        fun compose(ms: Long, machine: Int, sequence: Int): Long =
            ((ms - EPOCH_MS) shl 22) or (machine.toLong() shl 12) or sequence.toLong()

        fun timestampOf(id: Long): Long = (id ushr 22) + EPOCH_MS
        fun machineOf(id: Long): Int = ((id ushr 12) and 0x3FF).toInt()
        fun sequenceOf(id: Long): Int = (id and 0xFFF).toInt()
    }
}
