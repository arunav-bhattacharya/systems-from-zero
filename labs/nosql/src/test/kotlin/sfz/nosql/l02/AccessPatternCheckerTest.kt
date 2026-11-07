package sfz.nosql.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.nosql.l02.AccessPatternChecker.check
import sfz.nosql.l02.AccessPatternChecker.classify
import sfz.nosql.l02.ReadKind.KEY_LOOKUP
import sfz.nosql.l02.ReadKind.RANGE_READ
import sfz.nosql.l02.ReadKind.SCAN

class AccessPatternCheckerTest {
    private val byId = KeyIndex("table", listOf("paymentId"))
    private val byAccount = KeyIndex("byAccount", listOf("accountId"), listOf("createdAt"))
    private val byMerchantStatus = KeyIndex("byMerchantStatus", listOf("merchantId"), listOf("status", "createdAt"))
    private val byMerchantDay = KeyIndex("byMerchantDay", listOf("merchantId", "day"), listOf("createdAt"))

    @Test
    fun `fixing the whole key with = is a key lookup`() {
        assertThat(classify(AccessPattern("by id", setOf("paymentId")), byId)).isEqualTo(KEY_LOOKUP)
        assertThat(classify(AccessPattern("exact", setOf("accountId", "createdAt")), byAccount)).isEqualTo(KEY_LOOKUP)
    }

    @Test
    fun `the partition key plus a range or an order on the next sort attribute is a range read`() {
        assertThat(classify(AccessPattern("newest first", setOf("accountId"), orderBy = "createdAt"), byAccount)).isEqualTo(RANGE_READ)
        assertThat(classify(AccessPattern("last hour", setOf("accountId"), range = "createdAt"), byAccount)).isEqualTo(RANGE_READ)
        // no sort condition at all: the whole partition, still one contiguous read
        assertThat(classify(AccessPattern("all of them", setOf("accountId")), byAccount)).isEqualTo(RANGE_READ)
    }

    @Test
    fun `without the partition key the store has to scan`() {
        assertThat(classify(AccessPattern("by merchant", setOf("merchantId")), byAccount)).isEqualTo(SCAN)
        assertThat(classify(AccessPattern("by time only", emptySet(), range = "createdAt"), byAccount)).isEqualTo(SCAN)
    }

    @Test
    fun `a composite partition key needs every part`() {
        // merchantId alone can't be hashed to a partition when the key is (merchantId, day)
        assertThat(classify(AccessPattern("merchant", setOf("merchantId"), orderBy = "createdAt"), byMerchantDay)).isEqualTo(SCAN)
        assertThat(classify(AccessPattern("merchant today", setOf("merchantId", "day"), orderBy = "createdAt"), byMerchantDay)).isEqualTo(RANGE_READ)
    }

    @Test
    fun `sort key attributes are used left to right, with no gaps`() {
        // skips status, so the createdAt range is not one contiguous slice
        assertThat(classify(AccessPattern("merchant by time", setOf("merchantId"), range = "createdAt"), byMerchantStatus)).isEqualTo(SCAN)
        assertThat(classify(AccessPattern("merchant at a time", setOf("merchantId", "createdAt")), byMerchantStatus)).isEqualTo(SCAN)
        // fixes status first, then the range on createdAt is one slice
        assertThat(classify(AccessPattern("failed by time", setOf("merchantId", "status"), range = "createdAt"), byMerchantStatus)).isEqualTo(RANGE_READ)
        assertThat(classify(AccessPattern("by status", setOf("merchantId"), range = "status"), byMerchantStatus)).isEqualTo(RANGE_READ)
    }

    @Test
    fun `an = on a non-key attribute is a filter, so it scans`() {
        assertThat(classify(AccessPattern("big ones", setOf("accountId", "currency"), orderBy = "createdAt"), byAccount)).isEqualTo(SCAN)
        assertThat(classify(AccessPattern("id and status", setOf("paymentId", "status")), byId)).isEqualTo(SCAN)
    }

    @Test
    fun `results can only come back ordered by the next sort attribute`() {
        assertThat(classify(AccessPattern("by amount", setOf("accountId"), orderBy = "amountMinor"), byAccount)).isEqualTo(SCAN)
        assertThat(classify(AccessPattern("range and order disagree", setOf("merchantId"), range = "status", orderBy = "createdAt"), byMerchantStatus)).isEqualTo(SCAN)
    }

    @Test
    fun `check picks the cheapest index, and the first one on a tie`() {
        val indexes = listOf(byId, byAccount, KeyIndex("byAccountAgain", listOf("accountId"), listOf("createdAt")))
        assertThat(check(AccessPattern("AP1", setOf("accountId"), orderBy = "createdAt"), indexes))
            .isEqualTo(Verdict("AP1", RANGE_READ, "byAccount"))
        assertThat(check(AccessPattern("AP2", setOf("paymentId")), indexes))
            .isEqualTo(Verdict("AP2", KEY_LOOKUP, "table"))
        assertThat(check(AccessPattern("nope", setOf("merchantId")), indexes))
            .isEqualTo(Verdict("nope", SCAN, null))
    }

    @Test
    fun `the payments design answers every access pattern without a scan`() {
        val verdicts = AccessPatternChecker.checkAll(PaymentsKeyDesign.patterns, PaymentsKeyDesign.indexes)
            .associateBy { it.pattern.substringBefore(' ') }

        assertThat(verdicts.values).allSatisfy { assertThat(it.kind).isNotEqualTo(SCAN) }
        assertThat(verdicts["AP1"]!!.kind).isEqualTo(RANGE_READ)
        assertThat(verdicts["AP2"]!!.kind).isEqualTo(KEY_LOOKUP)
        assertThat(verdicts["AP3"]!!.kind).isEqualTo(RANGE_READ)
        assertThat(verdicts["AP4"]!!.kind).isEqualTo(KEY_LOOKUP)
        // every index must earn its place: each one is the answer to at least one pattern
        assertThat(verdicts.values.mapNotNull { it.index }.toSet())
            .containsExactlyInAnyOrderElementsOf(PaymentsKeyDesign.indexes.map { it.name })
    }
}
