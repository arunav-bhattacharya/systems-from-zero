package sfz.enc.l05

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import java.util.concurrent.TimeUnit

/** The order workflow on one worker: the happy path, the fraud check, the two compensations and a retried charge. */
@Timeout(30, unit = TimeUnit.SECONDS)
class OrderWorkflowTest {

    @Test
    fun `an order is checked, charged, reserved and shipped, each step once`() {
        OrderHarness().use { h ->
            val worker = h.startWorker()
            assertThat(h.run("order-1")).isEqualTo("SHIPPED")
            for (step in listOf("checkFraud", "charge", "reserve", "ship")) {
                assertThat(worker.activities.executions(step)).describedAs(step).isEqualTo(1)
            }
            assertThat(h.world.bank.chargesFor("order-1")).isEqualTo(1)
            assertThat(h.world.courier.parcels()).containsExactly("order-1")
        }
    }

    @Test
    fun `an order above the fraud limit is rejected before any money moves`() {
        OrderHarness().use { h ->
            val worker = h.startWorker()
            assertThat(h.run("order-2", amountCents = 250_000)).isEqualTo("REJECTED")
            assertThat(worker.activities.executions("charge")).isEqualTo(0)
            assertThat(h.world.bank.chargesFor("order-2")).isEqualTo(0)
        }
    }

    @Test
    fun `out of stock, the charge is refunded and nothing ships`() {
        OrderHarness(World(warehouse = Warehouse(mapOf("sku-1" to 0)))).use { h ->
            val worker = h.startWorker()
            assertThat(h.run("order-3")).isEqualTo("REFUNDED")
            assertThat(h.world.bank.chargesFor("order-3")).isEqualTo(1)
            assertThat(h.world.bank.netCents("order-3")).isEqualTo(0)
            // the warehouse said no for good, so Temporal did not retry it
            assertThat(worker.activities.executions("reserve")).isEqualTo(1)
            assertThat(worker.activities.executions("ship")).isEqualTo(0)
        }
    }

    @Test
    fun `a refused parcel goes back on the shelf and the money goes back to the card`() {
        OrderHarness(World(courier = Courier(refuse = true))).use { h ->
            h.startWorker()
            assertThat(h.run("order-4")).isEqualTo("CANCELLED")
            assertThat(h.world.warehouse.onShelf("sku-1")).isEqualTo(10)
            assertThat(h.world.bank.netCents("order-4")).isEqualTo(0)
            assertThat(h.world.courier.parcels()).isEmpty()
        }
    }

    @Test
    fun `a worker that dies after charging makes Temporal run the charge again, so a bank without keys charges twice`() {
        OrderHarness(World(bank = Bank(honorKeys = false))).use { h ->
            val worker = h.startWorker(crashAfter = setOf("charge"))
            assertThat(h.run("order-5")).isEqualTo("SHIPPED")
            assertThat(worker.activities.executions("charge")).isEqualTo(2) // at-least-once
            assertThat(h.world.bank.chargesFor("order-5")).isEqualTo(2) // the duplicate the key exists to stop
        }
    }

    @Test
    fun `with a key per step the bank turns the second attempt into a replay, one charge`() {
        OrderHarness(World(bank = Bank(honorKeys = true))).use { h ->
            val worker = h.startWorker(crashAfter = setOf("charge"))
            assertThat(h.run("order-6")).isEqualTo("SHIPPED")
            assertThat(worker.activities.executions("charge")).isEqualTo(2)
            assertThat(h.world.bank.chargesFor("order-6")).isEqualTo(1)
        }
    }
}
