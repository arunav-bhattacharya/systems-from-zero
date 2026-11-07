package sfz.nosql.l07.demo

import com.datastax.oss.driver.api.core.CqlSession
import com.datastax.oss.driver.api.core.config.DefaultDriverOption
import com.datastax.oss.driver.api.core.config.DriverConfigLoader
import com.datastax.oss.driver.api.core.cql.PreparedStatement
import com.datastax.oss.driver.api.core.cql.SimpleStatement
import com.datastax.oss.driver.api.core.servererrors.ReadFailureException
import java.net.InetSocketAddress
import java.time.Duration

/**
 * A payout queue in one Cassandra partition: enqueue 2,000 payouts for M-0042, let a worker
 * delete the ones it has paid, then read the next 10. Run against env/cassandra.yml.
 * Optional argument: how many payouts the worker has processed (default 1990; try 101000).
 */
fun main(args: Array<String>) {
    val processed = args.getOrNull(0)?.toInt() ?: 1_990
    val total = maxOf(2_000, processed + 10) // always leave 10 payouts waiting
    val config = DriverConfigLoader.programmaticBuilder()
        .withBoolean(DefaultDriverOption.REQUEST_LOG_WARNINGS, false) // we print the server's warnings ourselves
        .withDuration(DefaultDriverOption.REQUEST_TIMEOUT, Duration.ofSeconds(10))
        .build()
    CqlSession.builder()
        .addContactPoint(InetSocketAddress("localhost", 9042))
        .withLocalDatacenter("datacenter1")
        .withConfigLoader(config)
        .build().use { session ->
            session.execute("CREATE KEYSPACE IF NOT EXISTS payments WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}")
            session.execute(
                "CREATE TABLE IF NOT EXISTS payments.payout_queue (merchant_id text, payout_id int, amount_minor bigint, " +
                    "PRIMARY KEY ((merchant_id), payout_id))"
            )
            session.execute("TRUNCATE payments.payout_queue")

            // a queue: the producer appends payouts, the worker deletes each one once it's paid
            val enqueue = session.prepare("INSERT INTO payments.payout_queue (merchant_id, payout_id, amount_minor) VALUES ('M-0042', ?, 500)")
            val done = session.prepare("DELETE FROM payments.payout_queue WHERE merchant_id = 'M-0042' AND payout_id = ?")
            runAll(session, enqueue, 0 until total)
            runAll(session, done, 0 until processed)
            println("enqueued $total payouts, processed and deleted $processed")

            // the worker asks for the next batch: the 10 oldest payouts still waiting
            val next = SimpleStatement.newInstance("SELECT payout_id FROM payments.payout_queue WHERE merchant_id = 'M-0042' LIMIT 10")
                .setTracing(true)
            val rs = try {
                session.execute(next)
            } catch (e: ReadFailureException) {
                println("read failed: ${e.message}")
                return
            }
            val ids = rs.all().map { it.getInt("payout_id") }
            println("next batch: ${ids.size} payouts, ${ids.firstOrNull()} to ${ids.lastOrNull()}")
            val trace = rs.executionInfo.queryTrace
            trace.events.map { it.activity ?: "" }
                .filter { "tombstone" in it }
                .forEach { println("trace:   $it") }
            println("trace:   took ${trace.durationMicros} microseconds on the server")
            rs.executionInfo.warnings.forEach { println("warning: $it") }
        }
}

/** Runs [statement] once per id, at most 256 requests in flight. */
private fun runAll(session: CqlSession, statement: PreparedStatement, ids: IntRange) {
    ids.chunked(256).forEach { chunk ->
        chunk.map { session.executeAsync(statement.bind(it)).toCompletableFuture() }.forEach { it.join() }
    }
}
