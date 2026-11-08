package sfz.batch.l02.demo

import kotlin.math.pow
import kotlin.random.Random

// A copy of the lab's AccessLog.kt (demos can't see src/main).
//
// A made-up access log of a payments API, in NGINX's "combined" format. One line per request:
//
//   10.0.17.4 - - [07/Nov/2026:00:00:00 +0000] "POST /v1/authorizations HTTP/1.1" 201 512 "-" "acquirer-sdk/4.2"
//
// Split on blanks, field 7 (awk's $7) is the path and field 9 is the status code. A few paths get
// most of the requests and most paths are rare, the way real traffic looks: the path of rank r is
// requested with a probability that falls roughly like 1 / (r + 1). The same seed gives the same log.

object AccessLog {
    /** The eight busiest paths, most requested first. Every rank after them is one payment's page. */
    val endpoints = listOf(
        "/v1/authorizations", "/v1/captures", "/healthz", "/v1/refunds",
        "/v1/tokens", "/v1/payouts", "/v1/disputes", "/v1/balance",
    )

    /** The path with popularity rank [rank]; rank 0 is the most requested. */
    fun path(rank: Int): String =
        if (rank < endpoints.size) endpoints[rank] else "/v1/payments/pay_%07d".format(rank)

    /** A rank from 0 until [distinctPaths], picked with probability close to 1 / (rank + 1) (a Zipf law). */
    fun rank(random: Random, distinctPaths: Int): Int =
        (distinctPaths.toDouble().pow(random.nextDouble()).toInt() - 1).coerceIn(0, distinctPaths - 1)

    /** [count] log lines spread over one day, with paths drawn from [distinctPaths] possible ones. */
    fun lines(count: Int, distinctPaths: Int, seed: Long = 7): Sequence<String> = sequence {
        require(count >= 0 && distinctPaths >= 1)
        val random = Random(seed)
        val agents = listOf("acquirer-sdk/4.2", "checkout-web/2026.11", "settlement-batch/1.9", "curl/8.11.1")
        for (i in 0 until count) {
            val second = i * 86_400L / maxOf(count, 1)
            val time = "07/Nov/2026:%02d:%02d:%02d +0000".format(second / 3600, second / 60 % 60, second % 60)
            val rank = rank(random, distinctPaths)
            val method = if (rank == 2 || rank == 7 || (rank >= endpoints.size && random.nextInt(4) == 0)) "GET" else "POST"
            val status = when (random.nextInt(100)) {
                in 0..2 -> 402      // declined by the issuer
                3 -> 404
                4 -> 500
                else -> if (method == "POST") 201 else 200
            }
            val ip = "10.0.${random.nextInt(64)}.${random.nextInt(256)}"
            val bytes = 200 + random.nextInt(1_800)
            yield("$ip - - [$time] \"$method ${path(rank)} HTTP/1.1\" $status $bytes \"-\" \"${agents[random.nextInt(agents.size)]}\"")
        }
    }
}
