package sfz.enc.l04

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/** The key store on its own, no network. */
@Timeout(10, unit = TimeUnit.SECONDS)
class IdempotencyStoreTest {

    @Test
    fun `the first call with a key runs the work and returns its result`() {
        val store = IdempotencyStore()
        assertThat(store.once("k-1", "pay-1|4000") { "ch_1" }).isEqualTo("ch_1")
        assertThat(store.size).isEqualTo(1)
    }

    @Test
    fun `a repeat with the same key and request gets the stored result and the work does not run again`() {
        val store = IdempotencyStore()
        val runs = AtomicInteger()
        val first = store.once("k-1", "pay-1|4000") { "ch_${runs.incrementAndGet()}" }
        val second = store.once("k-1", "pay-1|4000") { "ch_${runs.incrementAndGet()}" }
        assertThat(second).isEqualTo(first).isEqualTo("ch_1")
        assertThat(runs.get()).isEqualTo(1)
    }

    @Test
    fun `a key reused for a different request is refused, not replayed`() {
        val store = IdempotencyStore()
        store.once("k-1", "pay-1|4000") { "ch_1" }
        val runs = AtomicInteger()
        assertThatThrownBy { store.once("k-1", "pay-1|9900") { runs.incrementAndGet() } }
            .isInstanceOf(KeyReusedException::class.java)
        assertThat(runs.get()).isEqualTo(0)
    }

    @Test
    fun `eight requests with one key at the same instant charge once, and all eight get that charge`() {
        val store = IdempotencyStore()
        val runs = AtomicInteger()
        val go = CountDownLatch(1)
        val pool = Executors.newFixedThreadPool(8)
        try {
            val results = (1..8).map {
                pool.submit<String> {
                    go.await()
                    store.once("k-1", "pay-1|4000") {
                        Thread.sleep(50) // the issuer takes a while: every other thread arrives in this window
                        "ch_${runs.incrementAndGet()}"
                    }
                }
            }
            go.countDown()
            assertThat(results.map { it.get(5, TimeUnit.SECONDS) }).containsOnly("ch_1")
            assertThat(runs.get()).isEqualTo(1)
        } finally {
            pool.shutdownNow()
        }
    }

    @Test
    fun `work that fails stores nothing, so a retry with the same key runs it again`() {
        val store = IdempotencyStore()
        assertThatThrownBy { store.once<String>("k-1", "pay-1|4000") { error("issuer down") } }
            .isInstanceOf(IllegalStateException::class.java)
        assertThat(store.once("k-1", "pay-1|4000") { "ch_1" }).isEqualTo("ch_1")
    }
}
