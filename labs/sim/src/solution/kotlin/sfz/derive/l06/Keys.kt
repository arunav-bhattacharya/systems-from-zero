package sfz.derive.l06

import javax.crypto.SecretKey
import javax.crypto.spec.SecretKeySpec
import kotlin.random.Random

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
