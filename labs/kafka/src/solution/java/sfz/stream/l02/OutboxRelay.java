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
        if (!event.table().equals("outbox")) return null;                 // other tables: not events
        if (!event.op().equals("c") && !event.op().equals("r")) return null; // updates and deletes route nothing
        Map<String, String> row = event.after();
        var record = new ProducerRecord<>(TOPIC_PREFIX + row.get("aggregatetype"), row.get("aggregateid"), row.get("payload"));
        record.headers().add("id", row.get("id").getBytes(StandardCharsets.UTF_8));          // the dedupe key
        record.headers().add("eventType", row.get("type").getBytes(StandardCharsets.UTF_8));
        return record;
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
        Map<Long, List<ChangeEvent>> open = new LinkedHashMap<>();       // txId -> its changes so far
        List<ProducerRecord<String, String>> out = new ArrayList<>();
        for (WalEntry e : wal) {
            switch (e.kind()) {
                case "change" -> open.computeIfAbsent(e.txId(), id -> new ArrayList<>()).add(e.change());
                case "abort" -> open.remove(e.txId());                     // rolled back: never seen downstream
                case "commit" -> {
                    List<ChangeEvent> changes = open.remove(e.txId());
                    if (changes == null || e.lsn() <= fromLsn) continue;   // already written before the restart
                    for (ChangeEvent c : changes) {
                        ProducerRecord<String, String> r = route(c);
                        if (r != null) out.add(r);
                    }
                }
                default -> throw new IllegalArgumentException("unknown WAL entry kind " + e.kind());
            }
        }
        return out;
    }
}
