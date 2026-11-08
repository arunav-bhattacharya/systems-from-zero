package sfz.enc.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import java.math.BigDecimal
import kotlin.random.Random

/** 64-bit ids in JSON: which ones a double-based parser corrupts, and how a string keeps them exact. */
class JsonIdsTest {
    private val twoTo53 = 1L shl 53

    /** What JavaScript's JSON.parse would hand you for paymentId: a double for a number, the text for a string. */
    private fun idLikeJavaScript(json: String): String {
        val node = Formats.json.readTree(json).get("paymentId")
        return if (node.isTextual) node.asText() else BigDecimal(node.asDouble()).toBigInteger().toString()
    }

    @Test
    fun `2^53 - 1 is the largest safe id, in both directions`() {
        assertThat(JsonIds.isSafe(JsonIds.MAX_SAFE)).isTrue()
        assertThat(JsonIds.isSafe(JsonIds.MAX_SAFE + 1)).isFalse()
        assertThat(JsonIds.isSafe(-JsonIds.MAX_SAFE)).isTrue()
        assertThat(JsonIds.isSafe(-JsonIds.MAX_SAFE - 1)).isFalse()
        assertThat(JsonIds.isSafe(Authorization.SAMPLE.paymentId)).isFalse()
    }

    @Test
    fun `2^53 + 1 comes back from a double as 2^53`() {
        assertThat(JsonIds.changedByDouble(twoTo53 + 1)).isTrue()
        // 2^53 itself survives, but it is not safe: 2^53 + 1 lands on the same double
        assertThat(JsonIds.changedByDouble(twoTo53)).isFalse()
        assertThat(JsonIds.changedByDouble(4000)).isFalse()
        assertThat(JsonIds.changedByDouble(Authorization.SAMPLE.paymentId)).isTrue()
    }

    @Test
    fun `between 2^53 and 2^54 every odd id changes, near 2^60 all but every 256th`() {
        val rnd = Random(7)
        // doubles between 2^53 and 2^54 are 2 apart, so only even ids survive
        val small = List(10_000) { rnd.nextLong(twoTo53, twoTo53 * 2) }
        assertThat(JsonIds.countChanged(small)).isEqualTo(small.count { it % 2 == 1L })
        // between 2^60 and 2^61 they are 256 apart
        val big = List(10_000) { rnd.nextLong(1L shl 60, 1L shl 61) }
        assertThat(JsonIds.countChanged(big)).isEqualTo(big.count { it % 256 != 0L })
        assertThat(JsonIds.countChanged(big)).isGreaterThan(9_900)
    }

    @Test
    fun `a JavaScript-style reader corrupts the numeric id and keeps the string one`() {
        val plain = Formats.json.writeValueAsString(Authorization.SAMPLE)
        assertThat(idLikeJavaScript(plain)).isEqualTo("1849204436731904000")
        assertThat(idLikeJavaScript(JsonIds.toJson(Authorization.SAMPLE))).isEqualTo("1849204436731904017")
    }

    @Test
    fun `toJson turns only paymentId into a string`() {
        val tree = Formats.json.readTree(JsonIds.toJson(Authorization.SAMPLE))
        assertThat(tree.get("paymentId").isTextual).isTrue()
        assertThat(tree.get("amountMinor").isNumber).isTrue()
        assertThat(tree.get("amountMinor").longValue()).isEqualTo(4000)
        assertThat(tree.get("tags").map { it.asText() }).containsExactly("card", "3ds")
    }

    @Test
    fun `fromJson reads the new string form and the old number form exactly`() {
        val fromString = JsonIds.fromJson(JsonIds.toJson(Authorization.SAMPLE))
        val fromNumber = JsonIds.fromJson(Formats.json.writeValueAsString(Authorization.SAMPLE))
        assertThat(fromString).isEqualTo(Authorization.SAMPLE)
        assertThat(fromNumber).isEqualTo(Authorization.SAMPLE)
    }
}
