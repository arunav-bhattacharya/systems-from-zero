package sfz.derive.l06

/** What a customer's row in the derived view shows. */
data class CustomerView(val name: String, val email: String, val payments: Int, val totalCents: Long)

/** A derived view, rebuilt from the log: one row per customer, plus totals per merchant. */
data class Projection(val customers: Map<String, CustomerView>, val merchantTotals: Map<String, Long>)

const val ERASED = "[erased]"

/**
 * Exercise 5. Rebuild the view from offset 0.
 *
 * For each event, look up the subject's key. With no key, the subject was erased: their row shows
 * [ERASED] for name and email, and their counts and amounts still add up. With a key, decrypt the
 * PII with [Gcm.open] (aad = the subject's bytes). Let `AEADBadTagException` escape: a record that
 * fails its tag while the key exists is corruption or tampering, and must not pass as erased.
 * Merchant totals include every event.
 */
fun rebuild(store: EventStore, keys: KeyStore): Projection {
    val customers = sortedMapOf<String, CustomerView>()
    val merchants = sortedMapOf<String, Long>()
    for (e in store.all) {
        val key = keys.lookup(e.subject)
        val pii = key?.let { Pii.decode(Gcm.open(it, e.iv, e.sealedPii, e.subject.toByteArray())) }  // throws on a bad tag
        val prev = customers[e.subject]
        customers[e.subject] = CustomerView(
            name = pii?.name ?: ERASED,
            email = pii?.email ?: ERASED,
            payments = (prev?.payments ?: 0) + 1,
            totalCents = (prev?.totalCents ?: 0L) + e.amountCents,
        )
        merchants[e.merchant] = (merchants[e.merchant] ?: 0L) + e.amountCents   // aggregates never needed the PII
    }
    return Projection(customers, merchants)
}

/** Exercise 6. How many of [subject]'s events can still be decrypted with the keys in [keys]. */
fun decryptable(store: EventStore, keys: KeyStore, subject: String): Int {
    val key = keys.lookup(subject) ?: return 0
    return store.all.count { e ->
        e.subject == subject && runCatching { Gcm.open(key, e.iv, e.sealedPii, subject.toByteArray()) }.isSuccess
    }
}

/** The right-to-erasure handler (finished): forget the key, and write the subject into the ledger. */
fun erase(subject: String, keys: KeyStore, ledger: ErasureLedger) {
    keys.forget(subject)
    ledger.record(subject)
}
