package sfz.derive.l06

import java.nio.ByteBuffer
import kotlin.random.Random

/** The personal fields of a payment. They are stored only encrypted. */
data class Pii(val name: String, val email: String) {
    fun encode(): ByteArray = "$name\n$email".toByteArray()

    companion object {
        fun decode(bytes: ByteArray): Pii = String(bytes).split("\n").let { Pii(it[0], it[1]) }
    }
}

/**
 * One event in the append-only log. [subject] is a random customer token, [merchant] and
 * [amountCents] are kept in the clear for aggregates, and the name and email are in [sealedPii],
 * encrypted with the subject's key. The event itself is never changed or deleted.
 */
class PaymentEvent(
    val offset: Int,
    val subject: String,
    val merchant: String,
    val amountCents: Long,
    val iv: ByteArray,
    val sealedPii: ByteArray,
)

/** An append-only event log whose personal fields are encrypted per subject (finished). */
class EventStore(private val keys: KeyStore) {
    private val events = ArrayList<PaymentEvent>()
    private var ivCounter = 0L

    val all: List<PaymentEvent> get() = events

    fun append(subject: String, merchant: String, amountCents: Long, pii: Pii): PaymentEvent {
        val iv = ByteBuffer.allocate(Gcm.IV_BYTES).putInt(0).putLong(ivCounter++).array()   // never repeats
        val sealed = Gcm.seal(keys.keyFor(subject), iv, pii.encode(), subject.toByteArray())
        return PaymentEvent(events.size, subject, merchant, amountCents, iv, sealed).also { events += it }
    }

    /** Every stored byte of every event, as a disk scan or `kafka-dump-log.sh` would see it. */
    fun rawBytes(): ByteArray {
        val out = java.io.ByteArrayOutputStream()
        for (e in events) {
            out.write("${e.offset}|${e.subject}|${e.merchant}|${e.amountCents}|".toByteArray())
            out.write(e.iv); out.write(e.sealedPii); out.write('\n'.code)
        }
        return out.toByteArray()
    }

    /** Flips one bit of one event's ciphertext: a bad disk, not an erasure. */
    fun corrupt(offset: Int) {
        val e = events[offset]
        val bytes = e.sealedPii.copyOf().also { it[0] = (it[0].toInt() xor 1).toByte() }
        events[offset] = PaymentEvent(e.offset, e.subject, e.merchant, e.amountCents, e.iv, bytes)
    }
}

/** Seeds a store with [payments] payments by [customers] customers at 8 merchants (finished). */
object Customers {
    val merchants = listOf("m-cafe", "m-books", "m-bikes", "m-pharmacy", "m-grocer", "m-travel", "m-cinema", "m-garage")

    fun subject(i: Int) = "cust-%03d".format(i)

    /** Every customer's email starts with "zz-plain-", so a scan for plaintext is a byte search. */
    fun pii(i: Int) = Pii("Customer $i", "zz-plain-$i@example.com")

    fun seed(store: EventStore, seed: Long, customers: Int = 50, payments: Int = 1_000) {
        val rnd = Random(seed)
        repeat(payments) {
            val c = rnd.nextInt(customers)
            store.append(subject(c), merchants[rnd.nextInt(merchants.size)], 100L + rnd.nextInt(20_000), pii(c))
        }
    }
}
