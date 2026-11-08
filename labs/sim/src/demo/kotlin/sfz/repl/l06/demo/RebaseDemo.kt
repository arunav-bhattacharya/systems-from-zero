package sfz.repl.l06.demo

/**
 * Server reconciliation, the scheme behind Linear's sync engine, Replicache and Zero.
 *
 * Two agents have dispute DSP-311 open. Each click runs a mutator on the local copy at once and
 * queues it. The server runs the same mutators, one at a time, in the order they arrive, with its
 * own rules, and numbers every change it accepts. When a client hears from the server, it throws
 * away its guesses, takes the server's state, and re-runs whatever the server hasn't answered yet.
 */
private data class Dispute(val status: String = "OPEN", val reason: String = "-", val notes: List<String> = emptyList()) {
    override fun toString() = "status=$status reason=$reason notes=$notes"
}

private data class Mutation(val id: String, val name: String, val arg: String)

/** The client's version of each mutator: no rules, just the change, so the screen updates now. */
private fun clientRun(d: Dispute, m: Mutation) = when (m.name) {
    "addNote" -> d.copy(notes = d.notes + m.arg)
    "setReason" -> d.copy(reason = m.arg)
    "close" -> d.copy(status = "CLOSED")
    else -> error(m.name)
}

/** The server's version: the same change, plus the business rule. Null means rejected. */
private fun serverRun(d: Dispute, m: Mutation): Dispute? =
    if (m.name == "addNote" && d.status == "CLOSED") null else clientRun(d, m)

private class Client(val name: String, var confirmed: Dispute, var syncId: Int) {
    val pending = mutableListOf<Mutation>()
    val view get() = pending.fold(confirmed, ::clientRun) // what the agent sees

    fun click(t: Int, m: Mutation) {
        pending += m
        println("t=%-4d %s clicks %-26s sees %s   (pending %d)".format(t, name, "${m.name}(${m.arg})", view, pending.size))
    }

    /** The server's answer: its newest state and sync id, and which of our mutations it has decided. */
    fun rebase(t: Int, state: Dispute, id: Int, decided: Map<String, Boolean>) {
        for ((mid, ok) in decided) if (pending.any { it.id == mid } && !ok) println("t=%-4d %s %s was rejected: rolled back, the agent is told".format(t, name, mid))
        pending.removeAll { it.id in decided }
        confirmed = state
        syncId = id
        println("t=%-4d %s rebases on sync id %d, re-runs %d pending, sees %s".format(t, name, id, pending.size, view))
    }
}

fun main() {
    var server = Dispute()
    var syncId = 41
    val log = mutableListOf<String>()
    val a = Client("agent A", server, syncId)
    val b = Client("agent B", server, syncId)

    val m1 = Mutation("a1", "addNote", "customer called")
    val n1 = Mutation("b1", "close", "")
    val m2 = Mutation("a2", "setReason", "not received")
    a.click(10, m1)
    b.click(12, n1)
    a.click(20, m2)

    // the server runs mutations one at a time, in arrival order: it is the single leader
    val decided = mutableMapOf<String, Boolean>()
    fun serve(t: Int, m: Mutation) {
        val next = serverRun(server, m)
        if (next == null) {
            println("t=%-4d server rejects %s %s: the dispute is %s".format(t, m.id, m.name, server.status))
            decided[m.id] = false
        } else {
            server = next
            syncId++
            log += "$syncId:${m.id}"
            println("t=%-4d server applies %s %s as sync id %d".format(t, m.id, m.name, syncId))
            decided[m.id] = true
        }
    }
    // b's mutation reaches the server first, then a's two, in a's order
    serve(60, n1)
    serve(75, m1)
    serve(76, m2)
    // a clicks again before the server's answer reaches it
    val m3 = Mutation("a3", "setReason", "damaged")
    a.click(95, m3)
    println("       server log: $log   state: $server")
    a.rebase(110, server, syncId, decided.toMap())
    b.rebase(115, server, syncId, decided.toMap())
    decided.clear()
    serve(130, m3)
    a.rebase(170, server, syncId, decided.toMap())
}
