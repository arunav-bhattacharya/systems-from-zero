package sfz.kafka.l10;

import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.KeyValue;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.Topology;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.Grouped;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.kstream.Produced;
import org.apache.kafka.streams.kstream.TimeWindows;
import org.apache.kafka.streams.state.WindowStore;

import java.time.Duration;

/**
 * A fraud rule: more than {@code limit} debits on one account inside one window of {@code window} is suspicious.
 *
 * <p>Input: {@link #PAYMENTS}, key = account id, value = amount in cents (a debit is negative), timestamp = when
 * the payment happened (event time). Output: {@link #ALERTS}, key = account id, value =
 * {@code "<count> debits in <window start>/<window end>"}, for example
 * {@code "4 debits in 2026-11-07T10:00:00Z/2026-11-07T10:01:00Z"}, once for every debit that takes the window's
 * count above the limit.
 */
public final class FraudRule {
    public static final String PAYMENTS = "payments";
    public static final String ALERTS = "fraud-alerts";
    public static final String STORE = "debits-per-window";

    private FraudRule() {
    }

    public static Topology build(Duration window, Duration grace, long limit) {
        StreamsBuilder builder = new StreamsBuilder();
        builder.stream(PAYMENTS, Consumed.with(Serdes.String(), Serdes.Long()))
                .filter((account, amount) -> amount < 0)                       // debits only
                .groupByKey(Grouped.with(Serdes.String(), Serdes.Long()))       // already keyed by account
                // tumbling windows: [10:00, 10:01), [10:01, 10:02) ... aligned to the clock, not to the first debit.
                // A record for a window is accepted until stream time passes the window's end plus the grace.
                .windowedBy(TimeWindows.ofSizeAndGrace(window, grace))
                .count(Materialized.<String, Long, WindowStore<Bytes, byte[]>>as(STORE))
                .toStream()                                                     // every change of a window's count
                .filter((w, count) -> count != null && count > limit)
                .map((w, count) -> KeyValue.pair(w.key(),
                        count + " debits in " + w.window().startTime() + "/" + w.window().endTime()))
                .to(ALERTS, Produced.with(Serdes.String(), Serdes.String()));
        return builder.build();
    }
}
