package sfz.derive.l05.demo

// A hash-chained log of 1,000 postings. Three attacks, and what verification sees.
fun main() {
    fun fresh() = HashChain().also { c -> for (p in Ledger.log(seed = 5, n = 1_000)) c.append("${p.offset},${p.account},${p.cents}") }
    val published = fresh().head
    println("published head: ${published.hex().take(16)}...")

    val edited = fresh().also { it.tamper(412, "412,acct-001,999999") }
    println("edit entry 412 in place:          verify() = ${edited.verify()}, verify(published) = ${edited.verify(published)}")

    val rewritten = fresh().also { it.rewriteFrom(412, "412,acct-001,999999") }
    println("edit 412 and recompute the rest:  verify() = ${rewritten.verify()}, verify(published) = ${rewritten.verify(published)}")

    val cut = fresh().also { it.truncate(900) }
    println("drop the last 100 entries:        verify() = ${cut.verify()}, verify(published) = ${cut.verify(published)}")
}
