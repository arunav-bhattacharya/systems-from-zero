package sfz.repl.l02.demo

/**
 * Lesson repl-02, section 1: the same five statements as a statement log and as a row log, and the
 * tables two followers build from them.
 *
 * Follower S replays the statements 350 ms after the leader ran them, with its own clock and random
 * generator. Follower R applies the row events. Then the last statement is sent a second time, as
 * happens when a follower reconnects and asks for entries it may already have.
 * Run: ./gradlew :sim:demo -Pmain=sfz.repl.l02.demo.LogsDemoKt
 * Optional: -Pargs='pin' makes the leader write its now() and random() values into each statement.
 */
fun main(args: Array<String>) {
    var time = 1_000_000L
    val leader = Leader({ time }, seed = 1).apply { pinValues = args.firstOrNull() == "pin" }
    val s = Server("statement copy", { time + 350 }, seed = 2)
    val r = Server("row copy", { time + 350 }, seed = 3)
    val statements = listOf(
        Statement.Insert("m1", 1_250),
        Statement.Insert("m2", 4_000),
        Statement.Insert("m1", 990),
        Statement.AddFee("m1", 30),
        Statement.DeleteSome("m2", 1),
    )
    for (st in statements) {
        time += 10
        val rowsBefore = leader.rowLog.size
        leader.run(st)
        s.execute(leader.statementLog.last())               // its clock reads 350 ms later than the leader's did
        leader.rowLog.drop(rowsBefore).forEach(r::applyRow)
    }

    println("statement log${if (leader.pinValues) " (values pinned by the leader)" else ""}:")
    leader.statementLog.forEachIndexed { i, st -> println("  %d  %s;".format(i + 1, st.sql)) }
    println("row log:")
    leader.rowLog.forEach { println("  ${describe(it)}") }

    s.replayStatements(leader.statementLog.takeLast(2))     // a resend of the last two entries
    r.replayRows(leader.rowLog.takeLast(4))

    println()
    println("after replaying, and after the tail of each log arrived a second time:")
    println("  %-15s %3s %-8s %7s %4s %-9s %s".format("", "id", "merchant", "amount", "fee", "ref", "created_at"))
    for (server in listOf(leader, s, r)) {
        for (row in server.rows.values.sortedBy { it.id }) {
            val same = leader.rows[row.id] == row
            println("  %-15s %3d %-8s %7d %4d %-9s %d%s".format(
                server.name, row.id, row.merchant, row.amountCents, row.feeCents, row.ref, row.createdAt,
                if (server === leader || same) "" else "   <- differs"))
        }
    }
    println("  statement copy equals the leader: ${s.rows == leader.rows}; row copy equals the leader: ${r.rows == leader.rows}")
}

private fun describe(e: RowEvent): String = when (e) {
    is RowEvent.Inserted -> e.row.let { "insert id=${it.id} merchant=${it.merchant} amount=${it.amountCents} fee=${it.feeCents} ref=${it.ref} created_at=${it.createdAt}" }
    is RowEvent.Updated -> e.row.let { "update id=${it.id} -> merchant=${it.merchant} amount=${it.amountCents} fee=${it.feeCents} ref=${it.ref} created_at=${it.createdAt}" }
    is RowEvent.Deleted -> "delete id=${e.id}"
}
