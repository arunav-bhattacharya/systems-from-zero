package sfz.derive.l05

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test

/** Exercises 5 and 6: a hash-chained log, and the attacks it does and doesn't catch on its own. */
class HashChainTest {
    private lateinit var chain: HashChain

    @BeforeEach
    fun fill() {
        chain = HashChain()
        for (p in Ledger.log(seed = 5, n = 1_000)) chain.append("${p.offset},${p.account},${p.cents}")
    }

    @Test
    fun `each entry links to the one before it`() {
        val c = HashChain()
        val e0 = c.append("a")
        val e1 = c.append("b")
        assertThat(e0.prev).isEqualTo(HashChain.GENESIS)
        assertThat(e0.hash).isEqualTo(sha256(HashChain.GENESIS, "a".toByteArray()))
        assertThat(e1.prev).isEqualTo(e0.hash)
        assertThat(c.head).isEqualTo(e1.hash)
    }

    @Test
    fun `an untouched chain verifies, against itself and against its published head`() {
        assertThat(chain.verify()).isNull()
        assertThat(chain.verify(chain.head.copyOf())).isNull()
    }

    @Test
    fun `editing one old entry is caught at exactly that entry`() {
        chain.tamper(412, "412,acct-001,999999")
        assertThat(chain.verify()).isEqualTo(412)
    }

    @Test
    fun `an insider who recomputes every later hash passes the self-check, but not the published head`() {
        val published = chain.head.copyOf()
        chain.rewriteFrom(412, "412,acct-001,999999")
        assertThat(chain.verify()).isNull()                       // consistent with itself
        assertThat(chain.verify(published)).isEqualTo(chain.size) // not with what the world saw
    }

    @Test
    fun `cutting off the newest entries is caught only by the published head`() {
        val published = chain.head.copyOf()
        chain.truncate(900)
        assertThat(chain.verify()).isNull()
        assertThat(chain.verify(published)).isEqualTo(900)
    }
}
