package sfz.derive.l05.demo

// A live consumer keeps a balance per account from a 5,000-posting ledger log. Each run injects
// one silent bug. The audit recomputes the view from offset 0 and diffs it; a reconciliation
// check compares only the grand totals; the Merkle tree compares 1,024 key ranges.
fun main() {
    val log = Ledger.log(seed = 5)
    val truth = recompute(log)
    // two accounts where flipping bit 4 moves one up by 16 and the other down by 16
    val up = truth.keys.first { truth.getValue(it) and 16L == 0L }
    val down = truth.keys.first { truth.getValue(it) and 16L != 0L }
    val runs = listOf(
        "no fault" to arrayOf<Fault>(),
        "drop every 1,000th record" to arrayOf<Fault>(Fault.DropEvery(1_000)),
        "redeliver offsets 10..12 after a crash" to arrayOf<Fault>(Fault.Redeliver(setOf(10, 11, 12))),
        "flip bit 20 of acct-123" to arrayOf<Fault>(Fault.FlipBit(account(123), 20)),
        "two flips that cancel in the total" to arrayOf<Fault>(Fault.FlipBit(up, 4), Fault.FlipBit(down, 4)),
        "truncate cents from offset 2,500" to arrayOf<Fault>(Fault.TruncateCents(2_500)),
    )
    println("fault                                   accounts off   total drift   totals match   merkle comparisons")
    for ((name, faults) in runs) {
        val live = liveBalances(log, *faults)
        val drift = diff(live, truth)
        val totalsMatch = live.values.sum() == truth.values.sum()
        val m = compare(MerkleTree(truth), MerkleTree(live))
        println("%-40s %12d %13d %14s %20d".format(name, drift.size, drift.sumOf { it.delta }, if (totalsMatch) "yes" else "NO", m.comparisons))
    }
}
