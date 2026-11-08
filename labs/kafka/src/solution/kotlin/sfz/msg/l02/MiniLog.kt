package sfz.msg.l02

data class LogRecord(val offset: Long, val key: String?, val value: String)

class MiniLog {
    private val records = ArrayList<LogRecord>()

    // the next offset is simply how many records exist: offsets are dense and start at 0
    val endOffset: Long
        get() = records.size.toLong()

    fun append(key: String?, value: String): Long {
        val offset = endOffset
        records += LogRecord(offset, key, value) // only ever add at the end
        return offset
    }

    fun read(from: Long, max: Int): List<LogRecord> {
        require(from in 0..endOffset) { "offset $from is outside the log (0..$endOffset)" }
        val to = minOf(from + max, endOffset)
        // a copy, so a reader can never change the log through the list it got
        return records.subList(from.toInt(), to.toInt()).toList()
    }
}

class LogReader(private val log: MiniLog, startAt: Long = 0) {
    var position: Long = startAt
        private set

    fun poll(max: Int): List<LogRecord> {
        val batch = log.read(position, max)
        position += batch.size // the reader's whole state: one number
        return batch
    }

    fun seek(offset: Long) {
        require(offset in 0..log.endOffset) { "offset $offset is outside the log (0..${log.endOffset})" }
        position = offset
    }
}
