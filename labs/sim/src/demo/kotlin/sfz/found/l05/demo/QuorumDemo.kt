package sfz.found.l05.demo

// Aurora's storage layout, checked by brute force: 6 copies of each 10 GB segment, 2 in each of
// 3 availability zones. A write needs 4 copies to acknowledge it, a read needs 3.
// Run from the labs folder:
//   ./gradlew :sim:demo -Pmain=sfz.found.l05.demo.QuorumDemoKt --console=plain -q

val COPIES = listOf("a1", "a2", "b1", "b2", "c1", "c2")   // the letter is the availability zone
const val WRITE_QUORUM = 4
const val READ_QUORUM = 3

fun main() {
    println("every way to lose copies, and what still works (write needs $WRITE_QUORUM, read needs $READ_QUORUM)")
    println("lost  cases  writes ok  reads ok")
    for (lost in 0..COPIES.size) {
        val cases = subsets(COPIES, lost)
        val writes = cases.count { COPIES.size - it.size >= WRITE_QUORUM }
        val reads = cases.count { COPIES.size - it.size >= READ_QUORUM }
        println("%4d %6d %10d %9d".format(lost, cases.size, writes, reads))
    }
    println()
    for ((name, down) in listOf(
        "zone a fails" to setOf("a1", "a2"),
        "zone a fails, then c2 dies" to setOf("a1", "a2", "c2"),
        "zones a and b fail" to setOf("a1", "a2", "b1", "b2"),
    )) {
        val alive = COPIES.size - down.size
        println("%-28s alive %d  writes %-4s reads %s".format(
            name, alive, if (alive >= WRITE_QUORUM) "yes" else "no", if (alive >= READ_QUORUM) "yes" else "no"))
    }
    println()
    // why these numbers: any read set must meet the last write set, and two writes can't both win
    val overlapRW = subsets(COPIES, WRITE_QUORUM).all { w -> subsets(COPIES, READ_QUORUM).all { r -> w.any(r::contains) } }
    val overlapWW = subsets(COPIES, WRITE_QUORUM).all { w1 -> subsets(COPIES, WRITE_QUORUM).all { w2 -> w1.any(w2::contains) } }
    val n = COPIES.size
    println("every read quorum overlaps every write quorum: $overlapRW   ($WRITE_QUORUM + $READ_QUORUM > $n is ${WRITE_QUORUM + READ_QUORUM > n})")
    println("every two write quorums overlap:               $overlapWW   ($WRITE_QUORUM + $WRITE_QUORUM > $n is ${2 * WRITE_QUORUM > n})")
    val repairSeconds = 10.0 * 8 / 10        // 10 GB is 80 gigabits; at 10 Gbit/s
    println("re-copying one 10 GB segment at 10 Gbit/s: %.0f s, before network and disk overheads".format(repairSeconds))
}

fun subsets(items: List<String>, k: Int): List<Set<String>> =
    if (k == 0) listOf(emptySet())
    else if (items.size < k) emptyList()
    else subsets(items.drop(1), k - 1).map { it + items[0] } + subsets(items.drop(1), k)
