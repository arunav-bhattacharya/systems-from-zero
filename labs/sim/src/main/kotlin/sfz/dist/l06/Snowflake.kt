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

    /**
     * The next id: it must be larger than every id this generator has made, whatever the clock does.
     *
     * This version is the bug from the lesson. When the wall clock steps back it reuses old milliseconds, so ids go
     * down and can repeat; and the 4,097th id in one millisecond wraps the sequence to 0 and repeats the first.
     * Fix it: never use a millisecond older than [lastMs], and when the sequence runs out, borrow the next millisecond.
     */
    fun next(): Long {
        val ms = clock()
        if (ms == lastMs) {
            sequence = (sequence + 1) and MAX_SEQUENCE    // TODO dist-06 lab: wraps to 0 after 4,096 ids
        } else {
            sequence = 0                                  // TODO dist-06 lab: an older ms also lands here
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
