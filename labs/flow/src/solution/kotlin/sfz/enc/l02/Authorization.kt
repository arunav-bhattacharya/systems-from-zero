package sfz.enc.l02

/**
 * The card authorization from lesson 1, now with a schema. This file is the same in src/main and src/solution.
 *
 * ```proto
 * syntax = "proto3";
 * message Authorization {
 *   int64  payment_id   = 1;
 *   string merchant     = 2;
 *   int64  amount_minor = 3;   // 4000 means 40.00
 *   string currency     = 4;
 *   repeated string tags = 5;
 * }
 * ```
 */
data class Authorization(
    val paymentId: Long,
    val merchant: String,
    val amountMinor: Long,
    val currency: String,
    val tags: List<String>,
) {
    companion object {
        val SAMPLE = Authorization(1849204436731904017, "Fern Bakery", 4000, "EUR", listOf("card", "3ds"))
    }
}
