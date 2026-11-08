package sfz.enc.l04

import io.grpc.ManagedChannel
import io.grpc.Server
import io.grpc.Status
import io.grpc.StatusRuntimeException
import io.grpc.inprocess.InProcessChannelBuilder
import io.grpc.inprocess.InProcessServerBuilder
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import java.time.Duration
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** The client against a real gRPC server in the same JVM (the in-process transport: no sockets, same gRPC stack). */
@Timeout(10, unit = TimeUnit.SECONDS)
class ChargeClientTest {

    /** A server with the given key store and faults, and a channel to it. */
    private class Rig(keys: IdempotencyStore?, faults: Faults = Faults.NONE) : AutoCloseable {
        val issuer = Issuer()
        val service = ChargeService(issuer, keys, faults)
        private val name = InProcessServerBuilder.generateName()
        private val pool: ExecutorService = Executors.newFixedThreadPool(8)
        private val server: Server = InProcessServerBuilder.forName(name).executor(pool)
            .addService(service.definition()).build().start()
        val channel: ManagedChannel = InProcessChannelBuilder.forName(name).build()

        override fun close() {
            channel.shutdownNow()
            server.shutdownNow()
            pool.shutdownNow()
        }
    }

    @Test
    fun `a charge that goes through the first time takes one attempt and one charge`() {
        Rig(IdempotencyStore()).use { rig ->
            val result = ChargeClient(rig.channel).charge("pay-1", 4_000)
            assertThat(result.attempts).isEqualTo(1)
            assertThat(result.reply.amountCents).isEqualTo(4_000)
            assertThat(rig.issuer.chargesFor("pay-1")).isEqualTo(1)
        }
    }

    @Test
    fun `a lost reply is retried with the same key, and the server replays the first charge`() {
        Rig(IdempotencyStore(), Faults(loseReply = mapOf("pay-2" to setOf(1)))).use { rig ->
            val result = ChargeClient(rig.channel).charge("pay-2", 4_000)
            assertThat(result.attempts).isEqualTo(2)
            assertThat(rig.service.requestsFor("pay-2")).isEqualTo(2)
            assertThat(rig.service.keysFor("pay-2")).hasSize(1) // one key, however many attempts
            assertThat(rig.issuer.chargesFor("pay-2")).isEqualTo(1)
        }
    }

    @Test
    fun `a reply slower than the deadline ends that attempt early, and the retry gets the stored answer`() {
        Rig(IdempotencyStore(), Faults(slowReply = setOf("pay-3"), slowMillis = 1_000)).use { rig ->
            val client = ChargeClient(rig.channel, deadline = Duration.ofMillis(150))
            val started = System.nanoTime()
            val result = client.charge("pay-3", 4_000)
            val tookMillis = (System.nanoTime() - started) / 1_000_000
            assertThat(result.attempts).isEqualTo(2)
            assertThat(tookMillis).isLessThan(900) // it did not sit out the 1-second reply
            assertThat(rig.issuer.chargesFor("pay-3")).isEqualTo(1)
        }
    }

    @Test
    fun `a request the server rejects is not retried`() {
        Rig(IdempotencyStore()).use { rig ->
            assertThatThrownBy { ChargeClient(rig.channel).charge("pay-4", 0) }
                .isInstanceOfSatisfying(StatusRuntimeException::class.java) {
                    assertThat(it.status.code).isEqualTo(Status.Code.INVALID_ARGUMENT)
                }
            assertThat(rig.service.requestsFor("pay-4")).isEqualTo(1)
        }
    }

    @Test
    fun `when every reply is lost the client stops after maxAttempts and reports the last error`() {
        Rig(IdempotencyStore(), Faults(loseReply = mapOf("pay-5" to (1..10).toSet()))).use { rig ->
            assertThatThrownBy { ChargeClient(rig.channel, maxAttempts = 4).charge("pay-5", 4_000) }
                .isInstanceOfSatisfying(StatusRuntimeException::class.java) {
                    assertThat(it.status.code).isEqualTo(Status.Code.UNAVAILABLE)
                }
            assertThat(rig.service.requestsFor("pay-5")).isEqualTo(4)
            assertThat(rig.issuer.chargesFor("pay-5")).isEqualTo(1) // the money moved once; the client just never heard
        }
    }

    @Test
    fun `thirty payments with every third first reply lost - ten duplicates without the key store, none with it`() {
        val payments = (1..30).map { "pay-$it" }
        val faults = Faults(loseReply = payments.filterIndexed { i, _ -> i % 3 == 0 }.associateWith { setOf(1) })

        fun duplicates(keys: IdempotencyStore?): Int = Rig(keys, faults).use { rig ->
            val client = ChargeClient(rig.channel)
            payments.forEach { client.charge(it, 4_000) }
            rig.issuer.totalCharges() - payments.size
        }

        assertThat(duplicates(keys = null)).isEqualTo(10)
        assertThat(duplicates(keys = IdempotencyStore())).isEqualTo(0)
    }
}
