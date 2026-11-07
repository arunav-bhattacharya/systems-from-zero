package sfz.kafka.l10;

import org.apache.kafka.streams.Topology;

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

    /**
     * Build it with a {@code StreamsBuilder}:
     *
     * <ol>
     *   <li>{@code stream(PAYMENTS, Consumed.with(Serdes.String(), Serdes.Long()))}, keep only debits (amount &lt; 0);</li>
     *   <li>group by the existing key, then {@code windowedBy(TimeWindows.ofSizeAndGrace(window, grace))};</li>
     *   <li>{@code count}, materialized as {@link #STORE};</li>
     *   <li>{@code toStream()}, keep the counts above {@code limit}, turn each {@code Windowed<String>} key into the
     *       plain account id and the value text above ({@code w.window().startTime()}, {@code endTime()}), and write
     *       to {@link #ALERTS} with String serdes.</li>
     * </ol>
     */
    public static Topology build(Duration window, Duration grace, long limit) {
        throw new UnsupportedOperationException("TODO: debits -> groupByKey -> windowedBy -> count -> above limit -> ALERTS");
    }
}
