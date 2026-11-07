package sfz.sql.l14.demo

import java.sql.Connection
import java.sql.Statement

/**
 * Lesson sql-14, Try it 3: a value pasted into SQL versus a value sent as a parameter, what
 * comes back as a "generated key", and when pgJDBC starts preparing on the server.
 *
 *   ./gradlew :sql:demo -Pmain=sfz.sql.l14.demo.InjectionKt      (from the labs folder)
 */
fun main() {
    println("server: ${Db.url}")
    val name = "' OR '1'='1"
    Db.connect().use { conn ->
        conn.autoCommit = false                                       // everything below is rolled back

        // 1. the name pasted into the SQL text
        val pasted = "SELECT merchant_id, name FROM merchants WHERE name = '$name'"
        println("pasted SQL: $pasted")
        conn.createStatement().use { st -> st.executeQuery(pasted).use { rs -> println("  rows: ${count(rs)}") } }

        // 2. the same name as a parameter
        conn.prepareStatement("SELECT merchant_id, name FROM merchants WHERE name = ?").use { ps ->
            ps.setString(1, name)
            ps.executeQuery().use { rs -> println("parameter:  SELECT ... WHERE name = ?   with ? = $name\n  rows: ${count(rs)}") }
        }

        // 3. generated keys: the flag, then a named column
        val insert = "INSERT INTO merchants (name, mcc, country_code) VALUES (?, '5812', 'IE')"
        conn.prepareStatement(insert, Statement.RETURN_GENERATED_KEYS).use { ps ->
            ps.setString(1, "Copper Kettle")
            ps.executeUpdate()
            ps.generatedKeys.use { keys -> println("RETURN_GENERATED_KEYS gives back: ${columns(keys)}") }
        }
        conn.prepareStatement(insert, arrayOf("merchant_id")).use { ps ->
            ps.setString(1, "Mama's Kitchen")                         // the apostrophe is just a character
            ps.executeUpdate()
            ps.generatedKeys.use { keys -> keys.next(); println("arrayOf(\"merchant_id\") gives back: merchant_id = ${keys.getLong(1)}") }
        }

        // 4. the same PreparedStatement run six times: from the fifth, it is prepared on the server
        conn.prepareStatement("SELECT name FROM merchants WHERE merchant_id = ?").use { ps ->
            for (run in 1..6) {
                ps.setLong(1, run.toLong())
                ps.executeQuery().close()
                println("run $run: server-side prepared statements on this connection = ${prepared(conn)}")
            }
        }
        conn.rollback()
    }
}

private fun count(rs: java.sql.ResultSet): Int {
    var n = 0
    while (rs.next()) n++
    return n
}

private fun columns(rs: java.sql.ResultSet): String =
    (1..rs.metaData.columnCount).joinToString(", ") { rs.metaData.getColumnName(it) }

private fun prepared(conn: Connection): String = conn.createStatement().use { st ->
    st.executeQuery("SELECT name FROM pg_prepared_statements ORDER BY name").use { rs ->
        buildList { while (rs.next()) add(rs.getString(1)) }.ifEmpty { listOf("none") }.joinToString()
    }
}
