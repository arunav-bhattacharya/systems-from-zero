package sfz.derive.l05.demo

// How many node comparisons does a Merkle diff need, against comparing every range?
// The live view has k accounts with one flipped bit each; the tree has `leaves` key ranges.
fun main() {
    val log = Ledger.log(seed = 5)
    val truth = recompute(log)
    println("bad accounts   leaves   ranges found   comparisons   a range-by-range scan")
    for (leaves in listOf(256, 1_024, 4_096)) {
        for (k in listOf(1, 3, 10, 100)) {
            val bad = (0 until k).map { account(it * (500 / k)) }
            val live = liveBalances(log, *bad.map { Fault.FlipBit(it, 2) }.toTypedArray())
            val d = compare(MerkleTree(truth, leaves), MerkleTree(live, leaves))
            println("%12d %8d %14d %13d %21d".format(k, leaves, d.leaves.size, d.comparisons, leaves))
        }
    }
}
