package sfz.msg.l07;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Account balances that apply each payment at most once, however often it is delivered.
 *
 * <p>In production this is one database transaction: insert the idempotency key into a table with a unique
 * constraint, and update the balance, together. If the insert hits the constraint, the payment was applied before
 * and the transaction does nothing. Here two in-memory maps play the database; they survive a consumer "crash"
 * because the tests keep the same ledger object while they replace the consumer.
 */
public final class IdempotentLedger implements PaymentSink {
    private final Map<String, Payment> appliedByKey = new ConcurrentHashMap<>();
    private final Map<String, Long> balances = new ConcurrentHashMap<>();
    private final AtomicInteger duplicates = new AtomicInteger();

    /**
     * Applies {@code p} if its idempotency key has not been applied before: remember the key and add the amount to
     * the account's balance, then return true. If the key is already known, change nothing, count a duplicate and
     * return false.
     */
    @Override
    public boolean apply(Payment p) {
        throw new UnsupportedOperationException("TODO: remember the key once (putIfAbsent), add to the balance, count duplicates");
    }

    /** The account's balance in cents; 0 for an account with no payments. */
    public long balanceCents(String account) {
        return balances.getOrDefault(account, 0L);
    }

    /** How many different payments have been applied. */
    public int appliedCount() {
        return appliedByKey.size();
    }

    /** How many deliveries were skipped because their key was already applied. */
    public int duplicatesSkipped() {
        return duplicates.get();
    }
}
