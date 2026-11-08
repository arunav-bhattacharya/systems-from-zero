package sfz.derive.l05

import java.security.MessageDigest
import kotlin.random.Random

/** One record of the ledger log: [cents] added to (or, if negative, taken from) [account]. */
data class Posting(val offset: Int, val account: String, val cents: Long)

fun account(i: Int) = "acct-%03d".format(i)

/** A seeded ledger log (finished): [n] postings over [accounts] accounts, amounts between -50.00 and +99.99. */
object Ledger {
    fun log(seed: Long, n: Int = 5_000, accounts: Int = 500): List<Posting> {
        val rnd = Random(seed)
        return (0 until n).map { i ->
            val cents = if (rnd.nextInt(3) == 0) -(1 + rnd.nextInt(5_000)).toLong() else (1 + rnd.nextInt(9_999)).toLong()
            Posting(i, account(rnd.nextInt(accounts)), cents)
        }
    }
}

/** A bug in the live consumer that keeps the `balances` view. Each one leaves a different fingerprint. */
sealed interface Fault {
    /** The consumer's error handler swallows every [n]th record: it never reaches the view. */
    data class DropEvery(val n: Int) : Fault

    /** After a crash the consumer reads these offsets again and adds them again: `balance += cents` is not idempotent. */
    data class Redeliver(val offsets: Set<Int>) : Fault

    /** A mercurial core or a bad migration flips one bit of one stored balance, after the fact. */
    data class FlipBit(val account: String, val bit: Int) : Fault

    /** A schema change stores amounts in whole units from offset [from] on: the cents are cut off. */
    data class TruncateCents(val from: Int) : Fault
}

/**
 * The live consumer (finished). It reads the log once, in order, and keeps a balance per account,
 * with [faults] injected. Nothing in it throws or logs: every fault here is silent.
 */
fun liveBalances(log: List<Posting>, vararg faults: Fault): Map<String, Long> {
    val view = sortedMapOf<String, Long>()
    val drop = faults.filterIsInstance<Fault.DropEvery>().firstOrNull()
    val redeliver = faults.filterIsInstance<Fault.Redeliver>().flatMap { it.offsets }.toSet()
    val truncateFrom = faults.filterIsInstance<Fault.TruncateCents>().firstOrNull()?.from ?: Int.MAX_VALUE
    for (p in log) {
        if (drop != null && (p.offset + 1) % drop.n == 0) continue                  // swallowed by a catch block
        val cents = if (p.offset >= truncateFrom) p.cents / 100 * 100 else p.cents  // 12.34 stored as 12.00
        val times = if (p.offset in redeliver) 2 else 1
        repeat(times) { view[p.account] = (view[p.account] ?: 0L) + cents }
    }
    for (f in faults.filterIsInstance<Fault.FlipBit>()) {
        view[f.account] = (view[f.account] ?: 0L) xor (1L shl f.bit)                // silent corruption at rest
    }
    return view
}

/** SHA-256 over the concatenation of [parts]. */
fun sha256(vararg parts: ByteArray): ByteArray {
    val md = MessageDigest.getInstance("SHA-256")
    for (p in parts) md.update(p)
    return md.digest()
}

fun ByteArray.hex(): String = joinToString("") { "%02x".format(it) }
