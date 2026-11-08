package sfz.found.l03.demo

import java.io.IOException

/**
 * A nightly job sends one payout instruction per merchant to the bank. The bank's upload fails
 * for one merchant: once (a dropped connection), or every time (the bank is down for it).
 * Three versions of the same error handler, and what each one reports.
 */
private class Bank(private val failFor: String, private var failuresLeft: Int) {
    val received = mutableListOf<String>()
    fun upload(merchant: String, cents: Long) {
        if (merchant == failFor && failuresLeft > 0) {                            // the injected fault
            failuresLeft--
            throw IOException("connection reset by peer")
        }
        received += "$merchant:$cents"
    }
}

private val payouts = linkedMapOf("m-cafe" to 49_00L, "m-books" to 12_50L, "m-bikes" to 310_00L, "m-shoes" to 88_00L, "m-hotel" to 1_204_00L)

/** Version 1: the handler someone meant to come back to. */
private fun swallow(bank: Bank): String {
    for ((m, c) in payouts) {
        try {
            bank.upload(m, c)
        } catch (e: IOException) {
            // TODO: retry
        }
    }
    return "job finished: OK"
}

/** Version 2: log it and carry on. */
private fun logAndContinue(bank: Bank): String {
    var failed = 0
    for ((m, c) in payouts) {
        try {
            bank.upload(m, c)
        } catch (e: IOException) {
            failed++
            System.err.println("    warn: upload for $m failed: ${e.message}")   // a log line nobody pages on
        }
    }
    return "job finished: OK ($failed warnings)"
}

/** Version 3: a failed payout is a failed job. Retry it, and if it still fails, say so loudly. */
private fun retryThenFail(bank: Bank, attempts: Int = 3): String {
    val missing = mutableListOf<String>()
    for ((m, c) in payouts) {
        var sent = false
        for (attempt in 1..attempts) {
            try { bank.upload(m, c); sent = true; break } catch (e: IOException) { /* try again */ }
        }
        if (!sent) missing += m
    }
    return if (missing.isEmpty()) "job finished: OK" else "job FAILED: no payout for $missing, settlement blocked"
}

fun main() {
    for ((name, run, failures) in listOf<Triple<String, (Bank) -> String, Int>>(
        Triple("swallow the exception, one dropped connection", ::swallow, 1),
        Triple("log and continue, one dropped connection", ::logAndContinue, 1),
        Triple("retry, then fail the job, one dropped connection", { b -> retryThenFail(b) }, 1),
        Triple("retry, then fail the job, bank keeps failing", { b -> retryThenFail(b) }, Int.MAX_VALUE),
    )) {
        val bank = Bank(failFor = "m-bikes", failuresLeft = failures)
        println("-- $name")
        val status = run(bank)
        println("    reports: $status")
        println("    the bank received ${bank.received.size} of ${payouts.size} payouts")
    }
}
