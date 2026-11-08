package sfz.sql.l10.demo

import java.sql.Connection
import java.sql.Timestamp
import java.time.Instant

/**
 * Lesson sql-10, Try it 4: the same 2,000 rows inserted four ways, then the N+1 dashboard and
 * its one-query version. For each, the round trips (a counting socket), the statements the
 * server ran (pg_stat_statements) and the time, which depends on your machine.
 *
 *   ./gradlew :sql:demo -Pmain=sfz.sql.l10.demo.BatchingKt      (from the labs folder)
 */
private const val ROWS = 2_000

fun main() {
    println("server: ${Db.url}")
    println("%-34s %12s %11s %10s".format("2,000 rows into payment_import", "round trips", "statements", "time"))
    insertWay("loop, autocommit") { c -> c.autoCommit = true; loop(c) }
    insertWay("loop, one transaction") { c -> loop(c); c.commit() }
    insertWay("addBatch, one executeBatch") { c -> batch(c); c.commit() }
    insertWay("addBatch + reWriteBatchedInserts", mapOf("reWriteBatchedInserts" to "true")) { c -> batch(c); c.commit() }

    println()
    println("%-34s %12s %11s %10s".format("latest payment of each merchant", "round trips", "statements", "time"))
    Db.counted().use { c ->
        repeat(3) { nPlusOne(c); oneQuery(c) }                        // warm up both
        report("N+1: merchants, then one per merchant", "SELECT") { nPlusOne(c) }
        report("one query with LEFT JOIN LATERAL", "SELECT") { oneQuery(c) }
    }
}

private fun insertWay(label: String, props: Map<String, String> = emptyMap(), work: (Connection) -> Unit) {
    Db.counted(props).use { c ->
        c.createStatement().use {
            it.execute("CREATE TEMP TABLE payment_import (card_id bigint, merchant_id bigint, amount_minor bigint, status text, created_at timestamptz)")
        }
        c.autoCommit = false
        report(label, "INSERT INTO payment_import") { work(c) }
    }
}

private fun report(label: String, statementPrefix: String, work: () -> Unit) {
    Db.connect().use { s -> s.createStatement().use { it.execute("SELECT pg_stat_statements_reset()") } }
    val t = System.nanoTime()
    val (_, trips) = RoundTrips.count(work)
    val elapsed = ms(System.nanoTime() - t)
    val statements = Db.connect().use { s ->
        s.prepareStatement("SELECT coalesce(sum(calls), 0) FROM pg_stat_statements WHERE query ILIKE ? || '%' AND query NOT ILIKE '%pg_stat_statements%'").use { ps ->
            ps.setString(1, statementPrefix)
            ps.executeQuery().use { it.next(); it.getLong(1) }
        }
    }
    println("%-34s %12d %11d %7.0f ms".format(label, trips, statements, elapsed))
}

private const val INSERT = "INSERT INTO payment_import (card_id, merchant_id, amount_minor, status, created_at) VALUES (?, ?, ?, ?, ?)"
private val t0 = Instant.parse("2026-07-01T00:00:00Z")

private fun loop(c: Connection) = c.prepareStatement(INSERT).use { ps ->
    for (i in 1..ROWS) {
        bind(ps, i)
        ps.executeUpdate()                                            // send one row, wait for "INSERT 0 1"
    }
}

private fun batch(c: Connection) = c.prepareStatement(INSERT).use { ps ->
    for (i in 1..ROWS) {
        bind(ps, i)
        ps.addBatch()                                                 // queue it in the driver
    }
    ps.executeBatch()                                                 // send the queue
}

private fun bind(ps: java.sql.PreparedStatement, i: Int) {
    ps.setLong(1, 1L + i % 14)
    ps.setLong(2, 1L + i % 8)
    ps.setLong(3, 100L + i)
    ps.setString(4, "succeeded")
    ps.setTimestamp(5, Timestamp.from(t0.plusSeconds(i.toLong())))
}

private const val LATEST = "SELECT payment_id, amount_minor FROM payments WHERE merchant_id = ? AND status = 'succeeded' ORDER BY created_at DESC, payment_id DESC LIMIT 1"

private fun nPlusOne(c: Connection): Int {
    val ids = c.prepareStatement("SELECT merchant_id FROM merchants ORDER BY merchant_id").use { ps ->
        ps.executeQuery().use { rs -> buildList { while (rs.next()) add(rs.getLong(1)) } }
    }
    return c.prepareStatement(LATEST).use { ps ->
        ids.count { id ->
            ps.setLong(1, id)
            ps.executeQuery().use { it.next() }                       // one round trip per merchant
        }
    }
}

private fun oneQuery(c: Connection): Int = c.prepareStatement(
    """
    SELECT m.merchant_id, p.payment_id, p.amount_minor
    FROM merchants m
    LEFT JOIN LATERAL (
        SELECT payment_id, amount_minor FROM payments
        WHERE merchant_id = m.merchant_id AND status = 'succeeded'
        ORDER BY created_at DESC, payment_id DESC LIMIT 1
    ) p ON true
    ORDER BY m.merchant_id
    """,
).use { ps -> ps.executeQuery().use { rs -> var n = 0; while (rs.next()) n++; n } }
