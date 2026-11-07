package sfz.kafka.l06;

/**
 * A payment event as it travels in a record's value: {@code "pay-0007,acct-3,4000"}.
 * The idempotency key is chosen by whoever created the payment, once, and every resend of the same payment carries
 * the same key. The record's offset can't play that role: a resend is a new record with a new offset.
 *
 * @param idempotencyKey unique per payment, for example {@code pay-0007}
 * @param account        the account to credit, also the record's key
 * @param amountCents    the amount in cents, 4000 for 40.00
 */
public record Payment(String idempotencyKey, String account, long amountCents) {

    /** Reads a record value written by {@link #toValue()}. */
    public static Payment parse(String value) {
        String[] f = value.split(",");
        if (f.length != 3) throw new IllegalArgumentException("not a payment: " + value);
        return new Payment(f[0], f[1], Long.parseLong(f[2]));
    }

    /** The record value for this payment. */
    public String toValue() {
        return idempotencyKey + "," + account + "," + amountCents;
    }
}
