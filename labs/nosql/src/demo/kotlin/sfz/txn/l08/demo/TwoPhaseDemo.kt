package sfz.txn.l08.demo

/** One item with the metadata a DynamoDB storage node keeps next to it: its last write and the transaction preparing it. */
private class Item(val key: String, var balance: Long) {
    var lastWrite = 0L
    var ongoing: String? = null
}

/** One action of a transaction: change [key] by [delta], if [condition] holds on the current balance. */
private class Action(val key: String, val delta: Long, val condition: (Long) -> Boolean = { true })

private class Tx(val id: String, val timestamp: Long, val actions: List<Action>)

/**
 * A model of the two-phase protocol in "Distributed Transactions at Scale in Amazon DynamoDB"
 * (USENIX ATC 2023): a coordinator prepares every item, then commits or cancels. Each item lives
 * on its own storage node, as if in its own partition. DynamoDB Local runs transactions one at a
 * time, so it can't show a conflict; this model can.
 */
fun main() {
    val items = listOf(Item("A-1001", 10_000), Item("A-2002", 5_000), Item("A-3003", 0)).associateBy { it.key }
    val ledger = mutableMapOf<String, String>() // the coordinators' durable record: transaction id -> decision

    fun log(tx: String, what: String) = println("%-3s %s".format(tx, what))

    /** Phase 1 on one item: the checks from the paper's prepare listing. */
    fun prepare(tx: Tx, a: Action): Boolean {
        val item = items.getValue(a.key)
        val verdict = when {
            item.ongoing != null -> "REJECTED: ${item.ongoing} is in flight on this item"
            tx.timestamp <= item.lastWrite -> "REJECTED: older than the item's last write"
            !a.condition(item.balance) -> "REJECTED: condition failed (balance ${item.balance})"
            else -> null
        }
        log(tx.id, "prepare ${a.key}: ${verdict ?: "accepted"}")
        if (verdict == null) item.ongoing = tx.id // the item is now held for this transaction
        return verdict == null
    }

    fun commit(tx: Tx) {
        for (a in tx.actions) {
            val item = items.getValue(a.key)
            val before = item.balance
            item.balance += a.delta
            item.lastWrite = tx.timestamp
            item.ongoing = null
            log(tx.id, "commit  ${a.key}: $before -> ${item.balance}")
        }
        ledger[tx.id] = "COMPLETED"
    }

    /** One coordinator running one transaction. [crashBeforeCommit] stops it after it has decided. */
    fun run(tx: Tx, crashBeforeCommit: Boolean = false): Boolean {
        ledger[tx.id] = "PREPARING"
        val prepared = mutableListOf<Action>()
        for (a in tx.actions) {
            if (!prepare(tx, a)) {
                prepared.forEach { items.getValue(it.key).ongoing = null; log(tx.id, "cancel  ${it.key}") }
                ledger[tx.id] = "CANCELLED"
                log(tx.id, "-> cancelled; nothing was written")
                return false
            }
            prepared += a
        }
        ledger[tx.id] = "COMMITTING" // the decision is durable before any item changes
        if (crashBeforeCommit) {
            log(tx.id, "-> coordinator crashes after deciding COMMIT; both items stay held")
            return false
        }
        commit(tx)
        log(tx.id, "-> committed")
        return true
    }

    fun transfer(id: String, ts: Long, from: String, to: String, amount: Long) =
        Tx(id, ts, listOf(Action(from, -amount) { it >= amount }, Action(to, amount)))

    println("== two transfers out of A-1001 collide")
    val t1 = transfer("T1", 100, "A-1001", "A-2002", 3_000)
    // T2 moves 50.00 from A-1001 to A-3003, and happens to list the credit first
    val t2 = Tx("T2", 101, listOf(Action("A-3003", 5_000), Action("A-1001", -5_000) { it >= 5_000 }))
    // T1 prepares A-1001 first; T2 prepares A-3003, then reaches A-1001 while T1 holds it
    prepare(t1, t1.actions[0])
    run(t2)
    prepare(t1, t1.actions[1])
    ledger["T1"] = "COMMITTING"
    commit(t1)
    log("T1", "-> committed")
    println("T2 gets TransactionConflict. The SDK doesn't retry a cancelled transaction: your code does,")
    println("with a new timestamp and the same idempotency key, after a short backoff.")
    run(Tx("T2", 105, t2.actions))

    println()
    println("== a coordinator dies between its decision and the commits")
    run(transfer("T3", 110, "A-2002", "A-1001", 2_000), crashBeforeCommit = true)
    run(transfer("T4", 111, "A-1001", "A-3003", 1_000))
    println("recovery manager scans the ledger: ${ledger.filterValues { it == "COMMITTING" }.keys} decided but not completed")
    commit(transfer("T3", 110, "A-2002", "A-1001", 2_000))
    log("T3", "-> completed by a new coordinator")
    run(transfer("T4", 112, "A-1001", "A-3003", 1_000))

    println()
    println("balances: " + items.values.joinToString { "${it.key} ${it.balance}" } + "  (total ${items.values.sumOf { it.balance }})")
}
