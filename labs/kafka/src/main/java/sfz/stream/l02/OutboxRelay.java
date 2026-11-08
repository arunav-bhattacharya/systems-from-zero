package sfz.stream.l02;

import org.apache.kafka.clients.producer.ProducerRecord;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Change data capture with the transactional outbox, as a model of what Debezium does for PostgreSQL.
 *
 * <p>The payment service writes its payment row and an event row into the {@code outbox} table in one database
 * transaction. PostgreSQL records both in its write-ahead log (WAL). Debezium reads the WAL through a replication
 * slot, turns each committed row change into a change event, and its outbox event router turns each outbox row into
 * a Kafka record.
 */
public final class OutboxRelay {
    /** Where routed events go: {@code outbox.event.<aggregatetype>}, Debezium's default. */
    public static final String TOPIC_PREFIX = "outbox.event.";

    /**
     * One row change, the way Debezium describes it.
     *
     * @param table the table name, for example {@code "outbox"} or {@code "payment"}
     * @param op    {@code "c"} insert, {@code "u"} update, {@code "d"} delete, {@code "r"} a row read by the initial snapshot
     * @param after the row's columns after the change (for a delete: before it), as text
     */
    public record ChangeEvent(String table, String op, Map<String, String> after) {
    }

    /**
     * One entry of the write-ahead log, in log order. Each has a log sequence number (LSN) that only grows.
     *
     * @param kind   {@code "change"} (a row change of transaction {@code txId}), {@code "commit"} or {@code "abort"}
     * @param change the row change, for {@code "change"} entries only (null otherwise)
     */
    public record WalEntry(long lsn, long txId, String kind, ChangeEvent change) {
    }

    private OutboxRelay() {
    }

    /**
     * The outbox event router: the Kafka record for one change event, or {@code null} if it routes nothing.
     *
     * <ul>
     *   <li>Only rows of the {@code outbox} table, and only inserts ({@code "c"}) and snapshot reads ({@code "r"}),
     *       become records. The router expects an outbox to be insert-only: it ignores updates (Debezium logs a
     *       warning) and deletes.</li>
     *   <li>Topic: {@link #TOPIC_PREFIX} + the {@code aggregatetype} column. Key: {@code aggregateid}, so all events
     *       of one account share a partition and keep their order. Value: {@code payload}.</li>
     *   <li>Headers: {@code id} = the {@code id} column (the event id, which consumers dedupe on) and
     *       {@code eventType} = the {@code type} column, both as UTF-8 bytes, in that order.</li>
     * </ul>
     */
    public static ProducerRecord<String, String> route(ChangeEvent event) {
        throw new UnsupportedOperationException("TODO: outbox inserts and snapshot reads only; topic, key, value and the id and eventType headers");
    }

    /**
     * Debezium's streaming loop over the WAL: the records it writes, in order, when it starts reading at its stored
     * offset {@code fromLsn}.
     *
     * <ul>
     *   <li>PostgreSQL hands over a transaction only once it commits: collect each transaction's changes, and at its
     *       {@code commit} entry route them all, in the order they were written. Transactions therefore come out in
     *       commit order, even when their changes were interleaved in the WAL.</li>
     *   <li>An {@code abort} (a rollback) drops the transaction's changes: nothing of it is written.</li>
     *   <li>Skip every transaction whose {@code commit} LSN is not greater than {@code fromLsn}: Debezium stored
     *       that position as its offset after it had written them.</li>
     *   <li>Changes that {@link #route} turns into nothing are left out.</li>
     * </ul>
     */
    public static List<ProducerRecord<String, String>> relay(List<WalEntry> wal, long fromLsn) {
        throw new UnsupportedOperationException("TODO: buffer changes per transaction, route them at commit, drop aborts, skip commits at or below fromLsn");
    }
}
