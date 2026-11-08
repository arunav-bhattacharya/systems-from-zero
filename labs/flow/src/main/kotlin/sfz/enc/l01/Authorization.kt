package sfz.enc.l01

import java.io.Serializable

/**
 * One card authorization: the record every encoding in this lesson turns into bytes.
 * This file is the same in src/main and src/solution; you don't change it.
 */
data class Authorization(
    val paymentId: Long,     // a 64-bit id from an id generator, far above 2^53
    val merchant: String,
    val amountMinor: Long,   // 4000 means 40.00 in the currency below
    val currency: String,
    val tags: List<String>,
) : Serializable {
    companion object {
        private const val serialVersionUID = 1L

        /** The record the lesson measures. */
        val SAMPLE = Authorization(1849204436731904017, "Fern Bakery", 4000, "EUR", listOf("card", "3ds"))
    }
}
