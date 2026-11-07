package sfz.sql.l14.demo

import com.zaxxer.hikari.HikariConfig
import com.zaxxer.hikari.HikariDataSource

/**
 * Lesson sql-14, Try it 1: what a connection costs, what a query costs, what a pool saves, and
 * how a big result arrives: all at once (pgJDBC's default) or in slices through a cursor.
 *
 *   ./gradlew :sql:demo -Pmain=sfz.sql.l14.demo.ConnectionCostKt      (from the labs folder)
 */
fun main() {
    println("server: ${Db.url}")

    // 1. ten new connections, one after the other: each is a TCP connection, a login and a new server process
    val pids = mutableListOf<Int>()
    var connectTrips = 0
    val connectMs = (1..10).map {
        val t = System.nanoTime()
        val (conn, trips) = RoundTrips.count { Db.counted() }
        connectTrips = trips
        conn.use { c ->
            val elapsed = ms(System.nanoTime() - t)
            c.createStatement().use { st -> st.executeQuery("SELECT pg_backend_pid()").use { rs -> rs.next(); pids += rs.getInt(1) } }
            elapsed
        }
    }
    println("open a connection:            median ${median(connectMs)}   ($connectTrips round trips each)")
    println("  ten connections, ten server processes: ${pids.joinToString(" ")}")

    // 2. 1,000 tiny queries on one open connection: each is one round trip
    Db.counted().use { c ->
        c.prepareStatement("SELECT 1").use { ps ->
            repeat(200) { ps.executeQuery().close() }               // warm up
            val (queryMs, trips) = RoundTrips.count {
                (1..1000).map {
                    val t = System.nanoTime()
                    ps.executeQuery().use { it.next() }
                    ms(System.nanoTime() - t)
                }
            }
            println("SELECT 1 on an open one:      median ${median(queryMs)}   ($trips round trips for 1,000 queries)")
        }
    }

    // 3. the same through a pool of 4: borrow, query, give back
    HikariDataSource(HikariConfig().apply {
        jdbcUrl = Db.url
        username = Db.USER
        password = Db.PASSWORD
        maximumPoolSize = 4
        poolName = "demo"
    }).use { pool ->
        repeat(200) { pool.connection.use { c -> c.createStatement().use { it.execute("SELECT 1") } } }
        val borrowMs = mutableListOf<Double>()
        val pooledMs = (1..1000).map {
            val t = System.nanoTime()
            pool.connection.use { c ->                               // close() hands it back, open
                borrowMs += ms(System.nanoTime() - t)
                c.prepareStatement("SELECT 1").use { ps -> ps.executeQuery().use { it.next() } }
            }
            ms(System.nanoTime() - t)
        }
        println("borrow from a pool of 4:      median ${median(borrowMs)}")
        println("borrow + SELECT 1 + return:   median ${median(pooledMs)}")
    }

    // 4. one million rows, read with fetchSize 0 (everything in the first answer) and 10,000 (a cursor)
    Db.counted().use { c ->
        c.autoCommit = false                                         // a cursor lives inside a transaction
        for (size in listOf(0, 10_000)) {
            c.prepareStatement("SELECT g, md5(g::text) FROM generate_series(1, 1000000) AS g").use { ps ->
                ps.fetchSize = size
                val before = usedHeapMb()
                val (heldMb, trips) = RoundTrips.count {
                    ps.executeQuery().use { rs ->
                        rs.next()                                    // the first row is here: what does the JVM hold?
                        val held = usedHeapMb() - before
                        while (rs.next()) { }
                        held
                    }
                }
                println("1,000,000 rows, fetchSize %-6d heap held at the first row: %4d MB, round trips: %d".format(size, heldMb, trips))
            }
        }
        c.rollback()
    }
}

private fun usedHeapMb(): Long {
    System.gc()
    val rt = Runtime.getRuntime()
    return (rt.totalMemory() - rt.freeMemory()) / (1024 * 1024)
}
