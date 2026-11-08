package sfz.stream.l03

/**
 * Lesson stream-03: everything in this file is given. Your exercises are in Account.kt and
 * Projections.kt.
 *
 * An event store is an append-only log with two kinds of position:
 * - each stream (one per account, `account-acct-17`) numbers its own events 1, 2, 3: the version;
 * - the whole store numbers every event once, in the order it was appended: the position.
 * Aggregates read one stream; projections read everything, by position.
 */

/** One event as the store keeps it. [data] holds the payload fields as strings, as JSON would. */
data class StoredEvent(
    val stream: String,
    val version: Long,
    val position: Long,
    val type: String,
    val schemaVersion: Int,
    val data: Map<String, String>,
)

/** An event on its way into the store: it gets its version and position when it is appended. */
data class NewEvent(val type: String, val schemaVersion: Int, val data: Map<String, String>)

/** Thrown when a writer's expected version is not the stream's current version: someone appended first. */
class WrongExpectedVersion(val stream: String, val expected: Long, val actual: Long) :
    RuntimeException("stream $stream is at version $actual, the writer expected $expected")

class EventStore {
    private val log = mutableListOf<StoredEvent>()

    /** The stream's current version: how many events it has. 0 for a stream that doesn't exist yet. */
    @Synchronized
    fun version(stream: String): Long = log.count { it.stream == stream }.toLong()

    /**
     * Appends [events] to [stream] only if the stream is still at [expectedVersion]: optimistic
     * concurrency. All of them are appended, or none. Returns the stream's new version.
     */
    @Synchronized
    fun append(stream: String, expectedVersion: Long, events: List<NewEvent>): Long {
        val actual = version(stream)
        if (actual != expectedVersion) throw WrongExpectedVersion(stream, expectedVersion, actual)
        events.forEachIndexed { i, e ->
            log += StoredEvent(stream, actual + i + 1, log.size + 1L, e.type, e.schemaVersion, e.data)
        }
        return actual + events.size
    }

    /** One stream's events, oldest first. */
    @Synchronized
    fun read(stream: String): List<StoredEvent> = log.filter { it.stream == stream }

    /** Every event after [afterPosition], in the order they were appended. */
    @Synchronized
    fun readAll(afterPosition: Long = 0): List<StoredEvent> = log.filter { it.position > afterPosition }

    /** Puts an event in exactly as given, as an old version of the service once wrote it (the tests use this). */
    @Synchronized
    fun appendRaw(stream: String, type: String, schemaVersion: Int, data: Map<String, String>) {
        log += StoredEvent(stream, version(stream) + 1, log.size + 1L, type, schemaVersion, data)
    }
}

/**
 * What Kafka's log cleaner leaves of a compacted topic (`cleanup.policy=compact`), given: the last
 * record for each key, in the order those last records were written. A null value is a tombstone,
 * and here it is removed at once (Kafka keeps it for `delete.retention.ms` first).
 */
fun <K, V> compactByKey(records: List<Pair<K, V?>>): List<Pair<K, V>> {
    val lastIndex = HashMap<K, Int>()
    records.forEachIndexed { i, (k, _) -> lastIndex[k] = i }
    return records.filterIndexed { i, (k, v) -> lastIndex[k] == i && v != null }.map { (k, v) -> k to v!! }
}
