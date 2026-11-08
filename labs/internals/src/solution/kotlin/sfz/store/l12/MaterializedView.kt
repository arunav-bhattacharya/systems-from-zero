package sfz.store.l12

import java.util.TreeMap

// Lesson 12 lab: keep the view
//     SELECT merchant, count(*), sum(amount_cents), min(amount_cents) FROM payments GROUP BY merchant
// up to date two ways, and count the rows each way touches.
// Your job: fullRecompute(), IncrementalView.onInsert(), IncrementalView.onDelete() and MinTracker.
// Payment, Change, Totals, Work and PaymentTable are done.

/** One row of the base table. */
data class Payment(val id: Long, val merchant: String, val amountCents: Long)

/** One change to the base table, as an AFTER trigger or a change-data-capture feed sees it. */
sealed interface Change {
    val payment: Payment
}

data class Inserted(override val payment: Payment) : Change
data class Deleted(override val payment: Payment) : Change

/**
 * One row of the view. The average is computed from [sumCents] and [count] when someone asks: an average
 * can't be maintained on its own, because you can't take one payment back out of it.
 */
data class Totals(val merchant: String, val count: Long, val sumCents: Long, val minCents: Long) {
    val avgCents: Double get() = sumCents.toDouble() / count
}

/** The cost of keeping the view right: rows read from the base table, and view rows written. */
class Work {
    var baseRowsRead = 0L
    var viewRowsWritten = 0L
    val rowsTouched: Long get() = baseRowsRead + viewRowsWritten
}

/** The base table, with an index on merchant so that one merchant's rows can be read on their own. */
class PaymentTable {
    private val rows = LinkedHashMap<Long, Payment>()
    private val byMerchant = HashMap<String, LinkedHashSet<Long>>()

    val size: Int get() = rows.size

    /** Applies one change. Inserting an id twice, or deleting a row that isn't there, is a bug in the caller. */
    fun apply(change: Change) {
        val p = change.payment
        when (change) {
            is Inserted -> {
                require(rows.putIfAbsent(p.id, p) == null) { "payment ${p.id} is already in the table" }
                byMerchant.getOrPut(p.merchant) { LinkedHashSet() } += p.id
            }
            is Deleted -> {
                require(rows.remove(p.id) == p) { "payment ${p.id} is not in the table as $p" }
                val ids = byMerchant.getValue(p.merchant)
                ids -= p.id
                if (ids.isEmpty()) byMerchant -= p.merchant
            }
        }
    }

    /** Every row, in insertion order: a full scan. Each row it hands out counts as one base row read. */
    fun scan(work: Work): Sequence<Payment> = rows.values.asSequence().onEach { work.baseRowsRead++ }

    /** One merchant's rows, through the index. Each row counts as one base row read. */
    fun rowsOf(merchant: String, work: Work): List<Payment> {
        val ids = byMerchant[merchant] ?: return emptyList()
        work.baseRowsRead += ids.size
        return ids.map { rows.getValue(it) }
    }
}

/**
 * Version 1, what REFRESH MATERIALIZED VIEW does: read every row of [table] (through [PaymentTable.scan]) and
 * build every merchant's [Totals] from nothing. Count one view row written per merchant in the result.
 */
fun fullRecompute(table: PaymentTable, work: Work): Map<String, Totals> {
    val out = HashMap<String, Totals>()
    for (p in table.scan(work)) {                        // every row, whatever changed
        val t = out[p.merchant]
        out[p.merchant] = if (t == null) Totals(p.merchant, 1, p.amountCents, p.amountCents)
        else Totals(p.merchant, t.count + 1, t.sumCents + p.amountCents, minOf(t.minCents, p.amountCents))
    }
    work.viewRowsWritten += out.size                     // and every view row is written again
    return out
}

/**
 * Version 2, incremental view maintenance. The view starts from a full recompute (not counted in [work]);
 * after that, call [apply] once per change, after the table has applied it, the way an AFTER trigger runs.
 */
class IncrementalView(private val table: PaymentTable) {
    val work = Work()

    /** How many deletes removed a merchant's minimum and forced a rescan of that merchant's rows. */
    var minRescans = 0
        private set

    private val rows = HashMap<String, Totals>(fullRecompute(table, Work()))

    operator fun get(merchant: String): Totals? = rows[merchant]

    fun snapshot(): Map<String, Totals> = rows.toMap()

    fun apply(change: Change) = when (change) {
        is Inserted -> onInsert(change.payment)
        is Deleted -> onDelete(change.payment)
    }

    /**
     * The delta rule for an insert: count + 1, sum + amount, min = the smaller of the old min and the amount.
     * A merchant with no row yet gets one. Either way: one view row written, no base rows read.
     */
    fun onInsert(p: Payment) {
        val t = rows[p.merchant]
        rows[p.merchant] = if (t == null) Totals(p.merchant, 1, p.amountCents, p.amountCents)
        else Totals(p.merchant, t.count + 1, t.sumCents + p.amountCents, minOf(t.minCents, p.amountCents))
        work.viewRowsWritten++
    }

    /**
     * The delta rule for a delete: count - 1, sum - amount. If that was the merchant's last payment, remove its
     * row. COUNT and SUM never need the table. MIN does: if the deleted amount was the minimum, the view can't
     * know the next smallest amount, so read that merchant's remaining rows with [PaymentTable.rowsOf] (counting
     * them in [work]) and count a [minRescans]. One view row is written (updated or removed) in every case.
     */
    fun onDelete(p: Payment) {
        val t = rows.getValue(p.merchant)
        work.viewRowsWritten++
        if (t.count == 1L) {                              // the group is empty: its row goes
            rows -= p.merchant
            return
        }
        var min = t.minCents
        if (p.amountCents == t.minCents) {                // the minimum left: only the base table knows the next one
            minRescans++
            min = table.rowsOf(p.merchant, work).minOf { it.amountCents }
        }
        rows[p.merchant] = Totals(p.merchant, t.count - 1, t.sumCents - p.amountCents, min)
    }
}

/**
 * Version 3 of MIN: keep enough state that a delete never needs the table. For one group, remember every
 * amount and how many rows have it, sorted: then the minimum is the first key, even after it is deleted.
 * Streaming databases keep state like this per group, and pay for it in memory.
 */
class MinTracker {
    private val counts = TreeMap<Long, Int>()

    /** How many values are tracked, duplicates included. */
    var size = 0
        private set

    /** The smallest value tracked, or null when there is none. */
    val min: Long? get() = if (counts.isEmpty()) null else counts.firstKey()

    fun add(v: Long) {
        counts.merge(v, 1, Int::plus)
        size++
    }

    /** Removes one occurrence of [v]; throws IllegalArgumentException if [v] isn't tracked. */
    fun remove(v: Long) {
        val n = counts[v] ?: throw IllegalArgumentException("$v is not tracked")
        if (n == 1) counts.remove(v) else counts[v] = n - 1   // a duplicate of the minimum keeps it in place
        size--
    }
}
