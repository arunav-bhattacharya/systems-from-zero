package sfz.shard.l01

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test

class TenantsTest {
    // 1,000 merchants, 20,000 payments a second in all; the biggest takes about 13% of everything
    private val merchants = Merchants.zipf(1_000, 20_000.0)
    private val cells = 10

    @Test
    fun `every tenant gets exactly one cell`() {
        val placement = TenantPlacement.bySize(merchants, cells, dedicatedAt = 2_000.0)
        assertThat(placement.keys).containsExactlyInAnyOrderElementsOf(merchants.map { it.id })
        assertThat(placement.values).allMatch { it in 0 until cells }
    }

    @Test
    fun `a tenant above the threshold runs alone, biggest first from cell 0`() {
        val placement = TenantPlacement.bySize(merchants, cells, dedicatedAt = 2_000.0)
        assertThat(placement["T-0001"]).isEqualTo(0)
        assertThat(TenantPlacement.neighbours(placement, "T-0001")).isZero()
        // T-0002 has about 1,336 a second, under the threshold, so it shares
        assertThat(placement["T-0002"]).isEqualTo(1)
        assertThat(TenantPlacement.neighbours(placement, "T-0002")).isPositive()
    }

    @Test
    fun `small tenants fill the shared cells evenly, biggest first`() {
        val placement = TenantPlacement.bySize(merchants, cells, dedicatedAt = 2_000.0)
        val shared = TenantPlacement.cellLoads(placement, merchants, cells).drop(1)
        val mean = shared.average()
        assertThat(shared.max()).isCloseTo(mean, within(mean * 0.01))
        assertThat(shared.min()).isCloseTo(mean, within(mean * 0.01))
    }

    @Test
    fun `hashing tenants onto cells puts the biggest next to dozens of others`() {
        val hashed = TenantPlacement.byHash(merchants, cells)
        val sized = TenantPlacement.bySize(merchants, cells, dedicatedAt = 2_000.0)
        assertThat(TenantPlacement.neighbours(hashed, "T-0001")).isGreaterThan(50)
        val hashedMax = TenantPlacement.cellLoads(hashed, merchants, cells).max()
        val sizedMax = TenantPlacement.cellLoads(sized, merchants, cells).max()
        assertThat(sizedMax).isLessThan(hashedMax)
    }

    @Test
    fun `a lower threshold gives more tenants a cell of their own`() {
        // T-0002 (about 1,336 a second) is now over the line too; T-0003 (about 891) is not
        val placement = TenantPlacement.bySize(merchants, cells, dedicatedAt = 1_000.0)
        assertThat(listOf("T-0001", "T-0002", "T-0003").map { placement[it] }).containsExactly(0, 1, 2)
        assertThat(TenantPlacement.neighbours(placement, "T-0002")).isZero()
        assertThat(TenantPlacement.neighbours(placement, "T-0003")).isPositive()
    }

    @Test
    fun `too many big tenants for the cells is an error`() {
        assertThatThrownBy { TenantPlacement.bySize(merchants, cells = 3, dedicatedAt = 500.0) }
            .isInstanceOf(IllegalArgumentException::class.java)
    }
}
