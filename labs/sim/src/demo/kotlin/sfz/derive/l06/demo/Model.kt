package sfz.derive.l06.demo

// The demos carry their own copy of the lab's model, with the exercises finished.
// Do the lab first if you want to write the encryption, erasure and rebuild yourself.

import java.nio.ByteBuffer
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec
import kotlin.random.Random

/**
 * AES-256 in GCM mode, from the JDK (`javax.crypto`). GCM encrypts and also authenticates: it
 * appends a 16-byte tag, and decryption checks the tag before it returns a single byte. A wrong
 * key, a flipped bit in the ciphertext, or different associated data (aad) all fail the check
 * with `javax.crypto.AEADBadTagException`.
 *
 * The [iv] (12 bytes) must never repeat under the same key.
 */
object Gcm {
    const val TAG_BITS = 128
    const val IV_BYTES = 12

    /** Exercise 1. Encrypt [plaintext] under [key] with "AES/GCM/NoPadding", a [TAG_BITS]-bit tag and [aad]. */
    fun seal(key: SecretKey, iv: ByteArray, plaintext: ByteArray, aad: ByteArray): ByteArray {
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.ENCRYPT_MODE, key, GCMParameterSpec(TAG_BITS, iv))
        c.updateAAD(aad)                            // bound to the ciphertext, but not secret: the subject id
        return c.doFinal(plaintext)                 // ciphertext followed by the 16-byte tag
    }

    /** Exercise 2. The reverse of [seal]. Throws `AEADBadTagException` if anything doesn't match. */
    fun open(key: SecretKey, iv: ByteArray, sealed: ByteArray, aad: ByteArray): ByteArray {
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(TAG_BITS, iv))
        c.updateAAD(aad)
        return c.doFinal(sealed)                    // checks the tag first
    }
}

/** The list of subjects whose data was erased, kept apart from the keys and from their backups. */
class ErasureLedger {
    private val erased = LinkedHashSet<String>()
    val subjects: Set<String> get() = erased
    fun record(subject: String) { erased += subject }
}

/** A copy of the key store, as a nightly backup would take it. */
class KeyBackup(val keys: Map<String, ByteArray>)

/**
 * One AES-256 data key per subject (a customer). Every event about that customer encrypts its
 * personal fields with this key, so deleting the key makes all of them unreadable at once,
 * wherever the copies are: the topic, the lakehouse, last month's backup of the event store.
 *
 * Keys come from a seeded [Random] so the tests are repeatable. A real key store uses
 * `SecureRandom` or a KMS, and never lets keys leave it unwrapped.
 */
class KeyStore(seed: Long) {
    private val rnd = Random(seed)
    private val keys = LinkedHashMap<String, ByteArray>()

    /** The subject's key, made on first use (finished). */
    fun keyFor(subject: String): SecretKey = SecretKeySpec(keys.getOrPut(subject) { rnd.nextBytes(32) }, "AES")

    /** The subject's key, or null if there is none (never made, or forgotten). */
    fun lookup(subject: String): SecretKey? = keys[subject]?.let { SecretKeySpec(it, "AES") }

    fun has(subject: String): Boolean = subject in keys

    /** Exercise 3. Forget [subject]'s key. Overwrite the bytes before you drop them. */
    fun forget(subject: String) {
        keys.remove(subject)?.fill(0)               // the only copy of the key in this store is now gone
    }

    /** A full copy of every key, as a backup job takes it (finished). */
    fun backup(): KeyBackup = KeyBackup(keys.mapValues { it.value.copyOf() })

    /**
     * Exercise 4. Restore from [backup]: replace every key with the backup's keys, then forget the
     * key of every subject in [erased]. Without that second step a restore brings erased people back.
     */
    fun restore(backup: KeyBackup, erased: ErasureLedger) {
        keys.clear()
        for ((s, k) in backup.keys) keys[s] = k.copyOf()
        for (s in erased.subjects) forget(s)        // re-apply every erasure made since the backup
    }
}

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
