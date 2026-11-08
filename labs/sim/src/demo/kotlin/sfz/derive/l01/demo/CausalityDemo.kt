package sfz.derive.l01.demo

import kotlin.random.Random

/**
 * Try it, derive-01 section 2: two logs, no order between them.
 *
 * A support agent decides a dispute in the disputes service (its own log), sees it saved, and
 * then issues the refund in the payments service (another log), 1 to 6 s later. The merchant
 * notifier reads both logs. For each refund it looks up the dispute: if it hasn't seen the
 * decision yet, it treats the refund as merchant-initiated and charges a 15.00 refund fee.
 *
 * The disputes log reaches the notifier through a CDC connector that polls every few seconds
 * (100 to 2,500 ms behind); the payments log is 50 to 300 ms behind. Each consumer reads its own
 * log in order. Run 1: no link between the two logs. Run 2: the refund event carries the offset
 * of the decision that caused it, and the notifier holds the refund until it has read that far.
 */
fun main(args: Array<String>) {
    val n = args.firstOrNull()?.toInt() ?: 1_000
    val random = Random(13)

    data class Dispute(val decidedAt: Long, val refundAt: Long)
    var t = 0L
    val disputes = (0 until n).map {
        t += 500 + random.nextLong(3_000)                       // a decision every 2 s or so
        Dispute(t, t + 1_000 + random.nextLong(5_000))
    }
    // when each consumer gets to each record: in log order, never earlier than the one before it
    fun seenTimes(appends: List<Long>, minLag: Long, maxLag: Long): List<Long> {
        var last = 0L
        return appends.map { a -> maxOf(last, a + minLag + random.nextLong(maxLag - minLag)).also { last = it } }
    }
    val decisionSeen = seenTimes(disputes.map { it.decidedAt }, 100, 2_500)
    val refundOrder = disputes.indices.sortedBy { disputes[it].refundAt }   // the payments log's order
    val refundSeenSorted = seenTimes(refundOrder.map { disputes[it].refundAt }, 50, 300)
    val refundSeen = LongArray(n).also { arr -> refundOrder.forEachIndexed { k, i -> arr[i] = refundSeenSorted[k] } }

    val wrong = disputes.indices.count { refundSeen[it] < decisionSeen[it] }
    println("no link between the logs:")
    println("  refunds handled before the decision that caused them: $wrong of $n")
    println("  refund fees charged by mistake: %,.2f".format(wrong * 15.0))

    // with the link: a refund waits until the notifier has read the disputes log past its cause
    val handled = disputes.indices.map { maxOf(refundSeen[it], decisionSeen[it]) }   // hold until the cause is read
    val waits = disputes.indices.map { handled[it] - refundSeen[it] }.filter { it > 0 }.sorted()
    println("refund carries the offset of its decision, notifier waits for it:")
    println("  refunds handled before their decision: ${disputes.indices.count { handled[it] < decisionSeen[it] }} of $n")
    println("  refunds held back: ${waits.size}, median hold ${waits[waits.size / 2]} ms, longest ${waits.last()} ms")
}
