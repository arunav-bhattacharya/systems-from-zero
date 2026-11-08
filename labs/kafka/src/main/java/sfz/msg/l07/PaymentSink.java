package sfz.msg.l07;

/** Where the consumer applies payments: a ledger, a database, a downstream API. */
@FunctionalInterface
public interface PaymentSink {
    /** Applies the payment. Returns true if it changed something, false if it was a duplicate and was skipped. */
    boolean apply(Payment payment);
}
