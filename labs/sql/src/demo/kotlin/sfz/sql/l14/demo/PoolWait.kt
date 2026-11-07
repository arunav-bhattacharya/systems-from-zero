package sfz.sql.l14.demo

import com.zaxxer.hikari.HikariConfig
import com.zaxxer.hikari.HikariDataSource
import java.sql.Connection
import java.sql.SQLTransientConnectionException
import java.util.concurrent.Executors

/**
 * Lesson sql-14, Try it 2: ten requests share a pool of four connections, then a leak drains it.
 *
 *   ./gradlew :sql:demo -Pmain=sfz.sql.l14.demo.PoolWaitKt      (from the labs folder)
 */
fun main() {
    println("server: ${Db.url}")
    val config = HikariConfig().apply {
        jdbcUrl = Db.url
        username = Db.USER
        password = Db.PASSWORD
        poolName = "payments"
        maximumPoolSize = 4
        minimumIdle = 4
        connectionTimeout = 1_000               // a borrower waits at most 1 s
        leakDetectionThreshold = 2_000          // log a connection held for more than 2 s
    }
    HikariDataSource(config).use { pool ->
        while (pool.hikariPoolMXBean.idleConnections < 4) Thread.sleep(20)   // the pool opens its 4

        // 1. ten requests at once, each holding a connection for a 300 ms query
        val start = System.nanoTime()
        Executors.newVirtualThreadPerTaskExecutor().use { threads ->
            val results = (1..10).map { n ->
                threads.submit<Pair<Int, Double>> {
                    val asked = System.nanoTime()
                    pool.connection.use { c ->
                        val waited = ms(System.nanoTime() - asked)
                        c.createStatement().use { it.execute("SELECT pg_sleep(0.3)") }
                        n to waited
                    }
                }
            }
            results.map { it.get() }.sortedBy { it.second }
                .forEach { (n, waited) -> println("request %2d waited %4.0f ms for a connection".format(n, waited)) }
        }
        println("all ten done after %.0f ms".format(ms(System.nanoTime() - start)))

        // 2. a leak: code that borrows and never calls close(), four times
        val leaked = mutableListOf<Connection>()
        repeat(4) { leaked += pool.connection }
        println("leaked 4 connections; the pool says ${pool.hikariPoolMXBean.activeConnections} active, ${pool.hikariPoolMXBean.idleConnections} idle")
        val asked = System.nanoTime()
        try {
            pool.connection.use { }
        } catch (e: SQLTransientConnectionException) {
            println("the next borrower, after %.0f ms: %s".format(ms(System.nanoTime() - asked), e.message))
        }
        Thread.sleep(2_500)                     // past leakDetectionThreshold: Hikari logs each leak
        leaked.forEach { it.close() }
    }
}
