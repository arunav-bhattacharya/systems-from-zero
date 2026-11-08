package sfz.derive.l06

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import javax.crypto.AEADBadTagException
import javax.crypto.spec.SecretKeySpec

/** Exercises 1 to 6: per-subject keys, erasure by forgetting a key, replay, and the backup pitfall. */
class CryptoShredTest {
    private lateinit var keys: KeyStore
    private lateinit var store: EventStore
    private val ana = Customers.subject(17)

    @BeforeEach
    fun seed() {
        keys = KeyStore(seed = 3)
        store = EventStore(keys)
        Customers.seed(store, seed = 9)                                   // 1,000 payments by 50 customers
    }

    private fun anasEvents() = store.all.count { it.subject == ana }

    @Test
    fun `seal and open round-trip, and the ciphertext is 16 bytes longer than the plaintext`() {
        val key = SecretKeySpec(ByteArray(32) { it.toByte() }, "AES")
        val iv = ByteArray(Gcm.IV_BYTES)
        val sealed = Gcm.seal(key, iv, "Ana".toByteArray(), "cust-017".toByteArray())
        assertThat(sealed).hasSize(3 + 16)
        assertThat(String(Gcm.open(key, iv, sealed, "cust-017".toByteArray()))).isEqualTo("Ana")
    }

    @Test
    fun `opening with the wrong key or the wrong subject fails the tag check`() {
        val key = SecretKeySpec(ByteArray(32) { it.toByte() }, "AES")
        val other = SecretKeySpec(ByteArray(32) { (it + 1).toByte() }, "AES")
        val iv = ByteArray(Gcm.IV_BYTES)
        val sealed = Gcm.seal(key, iv, "Ana".toByteArray(), "cust-017".toByteArray())
        assertThatThrownBy { Gcm.open(other, iv, sealed, "cust-017".toByteArray()) }.isInstanceOf(AEADBadTagException::class.java)
        assertThatThrownBy { Gcm.open(key, iv, sealed, "cust-018".toByteArray()) }.isInstanceOf(AEADBadTagException::class.java)
    }

    @Test
    fun `no plaintext personal data is ever written to the log`() {
        val raw = String(store.rawBytes(), Charsets.ISO_8859_1)
        assertThat(raw).doesNotContain("zz-plain-").doesNotContain("Customer 17")
        assertThat(rebuild(store, keys).customers.getValue(ana).email).isEqualTo("zz-plain-17@example.com")
    }

    @Test
    fun `forgetting the key takes the subject from N decryptable events to 0`() {
        val n = anasEvents()
        assertThat(n).isGreaterThan(10)
        assertThat(decryptable(store, keys, ana)).isEqualTo(n)
        erase(ana, keys, ErasureLedger())
        assertThat(keys.has(ana)).isFalse()
        assertThat(decryptable(store, keys, ana)).isZero()
        assertThat(store.all).hasSize(1_000)                              // not one event was deleted
    }

    @Test
    fun `other customers are not touched`() {
        val bob = Customers.subject(18)
        val before = decryptable(store, keys, bob)
        erase(ana, keys, ErasureLedger())
        assertThat(decryptable(store, keys, bob)).isEqualTo(before).isGreaterThan(0)
    }

    @Test
    fun `a replay after erasure shows the subject as erased, and every aggregate is unchanged`() {
        val before = rebuild(store, keys)
        erase(ana, keys, ErasureLedger())
        val after = rebuild(store, keys)
        assertThat(after.merchantTotals).isEqualTo(before.merchantTotals)
        val row = after.customers.getValue(ana)
        assertThat(row.name).isEqualTo(ERASED)
        assertThat(row.email).isEqualTo(ERASED)
        assertThat(row.payments).isEqualTo(before.customers.getValue(ana).payments)
        assertThat(row.totalCents).isEqualTo(before.customers.getValue(ana).totalCents)
        assertThat(after.customers.filterKeys { it != ana }).isEqualTo(before.customers.filterKeys { it != ana })
    }

    @Test
    fun `restoring last night's key backup brings the erased customer back`() {
        val backup = keys.backup()                                        // taken before the request came in
        erase(ana, keys, ErasureLedger())
        keys.restore(backup, ErasureLedger())                             // a restore that knows nothing of erasures
        assertThat(decryptable(store, keys, ana)).isEqualTo(anasEvents()) // the pitfall: every event readable again
    }

    @Test
    fun `restoring with the erasure ledger re-applies every erasure`() {
        val backup = keys.backup()
        val ledger = ErasureLedger()
        erase(ana, keys, ledger)
        keys.restore(backup, ledger)
        assertThat(decryptable(store, keys, ana)).isZero()
        assertThat(decryptable(store, keys, Customers.subject(18))).isGreaterThan(0)   // everyone else came back
    }

    @Test
    fun `a corrupted record with its key present fails loudly instead of passing as erased`() {
        val offset = store.all.first { it.subject == ana }.offset
        store.corrupt(offset)
        assertThatThrownBy { rebuild(store, keys) }.isInstanceOf(AEADBadTagException::class.java)
        assertThat(decryptable(store, keys, ana)).isEqualTo(anasEvents() - 1)
    }
}
