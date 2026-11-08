package sfz.cache.l06

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CountDownLatch
import java.util.concurrent.ExecutionException
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

// no Docker: plain threads in one JVM
@Timeout(10, unit = TimeUnit.SECONDS)
class SingleFlightTest {

    /** Runs [callers] calls of [call] on their own threads, all released at the same moment. */
    private fun <T> together(callers: Int, call: () -> T): List<CompletableFuture<T>> {
        val pool = Executors.newFixedThreadPool(callers)
        val start = CountDownLatch(1)
        val futures = (0 until callers).map {
            CompletableFuture.supplyAsync({ start.await(); call() }, pool)
        }
        start.countDown()
        pool.shutdown()
        return futures
    }

    @Test
    fun `one caller runs the loader and gets its value`() {
        val flights = SingleFlight<String>()
        val calls = AtomicInteger()

        val value = flights.load("m-17") { calls.incrementAndGet(); "Fietsen Utrecht" }

        assertThat(value).isEqualTo("Fietsen Utrecht")
        assertThat(calls.get()).isEqualTo(1)
        assertThat(flights.inFlight()).isZero()
    }

    @Test
    fun `fifty concurrent callers for one key share a single load`() {
        val flights = SingleFlight<String>()
        val calls = AtomicInteger()

        val results = together(50) {
            flights.load("m-17") { calls.incrementAndGet(); Thread.sleep(300); "Fietsen Utrecht" }
        }.map { it.get(5, TimeUnit.SECONDS) }

        assertThat(calls.get()).isEqualTo(1)
        assertThat(results).hasSize(50).containsOnly("Fietsen Utrecht")
        assertThat(flights.inFlight()).isZero()
    }

    @Test
    fun `a null result is shared like any other value`() {
        val flights = SingleFlight<String?>()
        val calls = AtomicInteger()

        val results = together(20) {
            flights.load("m-404") { calls.incrementAndGet(); Thread.sleep(200); null }
        }.map { it.get(5, TimeUnit.SECONDS) }

        assertThat(calls.get()).isEqualTo(1)
        assertThat(results).hasSize(20).containsOnlyNulls()
    }

    @Test
    fun `loads of different keys don't wait for each other`() {
        val flights = SingleFlight<String>()
        val release = CountDownLatch(1)
        val slow = CompletableFuture.supplyAsync { flights.load("m-1") { release.await(); "slow" } }
        Thread.sleep(100)                                      // m-1 is now loading and blocked

        val fast = flights.load("m-2") { "fast" }              // must not queue behind m-1

        assertThat(fast).isEqualTo("fast")
        assertThat(flights.inFlight()).isEqualTo(1)
        release.countDown()
        assertThat(slow.get(5, TimeUnit.SECONDS)).isEqualTo("slow")
    }

    @Test
    fun `after a load finishes the next call loads again`() {
        val flights = SingleFlight<Int>()
        val calls = AtomicInteger()

        flights.load("m-17") { calls.incrementAndGet() }
        flights.load("m-17") { calls.incrementAndGet() }

        assertThat(calls.get()).isEqualTo(2)                   // single-flight is not a cache
    }

    @Test
    fun `a failed load fails every waiting caller with the same exception, and the next call retries`() {
        val flights = SingleFlight<String>()
        val calls = AtomicInteger()

        val results = together(10) {
            flights.load("m-17") {
                calls.incrementAndGet(); Thread.sleep(200)
                throw IllegalStateException("database timeout")
            }
        }
        for (r in results) {
            assertThatThrownBy { r.get(5, TimeUnit.SECONDS) }
                .isInstanceOf(ExecutionException::class.java)
                .cause().isInstanceOf(IllegalStateException::class.java).hasMessage("database timeout")
        }
        assertThat(calls.get()).isEqualTo(1)
        assertThat(flights.inFlight()).isZero()

        assertThat(flights.load("m-17") { "recovered" }).isEqualTo("recovered")
    }
}
