package sfz.sql.support

import org.opentest4j.AssertionFailedError
import org.postgresql.util.PGobject
import java.math.BigDecimal
import java.sql.Connection
import java.sql.ResultSet
import java.sql.SQLException
import java.sql.Statement
import java.time.Instant
import java.time.OffsetDateTime

/**
 * Helpers for the SQL track's lab tests.
 *
 * A typical test:
 * ```
 * @Test
 * fun `finds the five largest March payments`() = rollback {
 *     val rows = exercise(1, "march_top_payments")
 *     rows.assertColumns("payment_id", "amount_minor")
 *     rows.assertRowsInOrder(row(13, 64000), row(22, 52000))
 * }
 * ```
 */

/**
 * Runs [block] in one transaction on a fresh connection and always rolls it back.
 * It returns Unit on purpose: JUnit skips a test method whose return type is not void, and an
 * expression-bodied test (`fun x() = rollback { ... }`) takes its return type from here.
 */
fun rollback(block: Tx.() -> Unit): Unit =
    CourseDb.connect().use { conn ->
        conn.autoCommit = false
        try {
            conn.createStatement().use {
                // a runaway query (a forgotten join condition) fails the test instead of hanging it
                it.execute("SET LOCAL statement_timeout = '10s'")
                it.execute("SET LOCAL lock_timeout = '5s'")
            }
            Tx(conn).block()
        } finally {
            conn.rollback()
        }
    }

/** The SQL text of an exercise file, `sfz/sql/lNN/<name>.sql`, from the classpath. */
fun exerciseSql(lesson: Int, name: String): String =
    CourseDb.resource("sfz/sql/l%02d/%s.sql".format(lesson, name))

/** One open, uncommitted transaction. Everything it does is rolled back by [rollback]. */
class Tx(val conn: Connection) {

    /** Runs the exercise file (all its statements) and returns the rows of the last query in it. */
    fun exercise(lesson: Int, name: String): Rows {
        val label = "sfz/sql/l%02d/%s.sql".format(lesson, name)
        return script(exerciseSql(lesson, name), label)
            ?: throw AssertionFailedError("$label ran, but it has no query that returns rows")
    }

    /** Runs the exercise file for its side effects (DDL, for example). */
    fun runExercise(lesson: Int, name: String) {
        script(exerciseSql(lesson, name), "sfz/sql/l%02d/%s.sql".format(lesson, name))
    }

    /**
     * Runs one or more statements separated by semicolons and returns the rows of the last
     * statement that produced a result set, or null if none did.
     */
    fun script(sql: String, label: String = "script"): Rows? = conn.createStatement().use { st ->
        var last: Rows? = null
        try {
            var isResult = st.execute(sql)
            while (true) {
                if (isResult) {
                    st.resultSet.use { last = Rows.from(it) }
                } else if (st.updateCount == -1) {
                    break
                }
                isResult = st.getMoreResults(Statement.CLOSE_CURRENT_RESULT)
            }
        } catch (e: SQLException) {
            throw AssertionFailedError("$label failed with SQLSTATE ${e.sqlState}: ${e.message}", e)
        }
        last
    }

    /** Runs one query with `?` parameters. */
    fun query(sql: String, vararg params: Any?): Rows = conn.prepareStatement(sql).use { ps ->
        params.forEachIndexed { i, p -> ps.setObject(i + 1, p) }
        ps.executeQuery().use { Rows.from(it) }
    }

    /** Runs one statement that changes data and returns the update count. */
    fun update(sql: String, vararg params: Any?): Int = conn.prepareStatement(sql).use { ps ->
        params.forEachIndexed { i, p -> ps.setObject(i + 1, p) }
        ps.executeUpdate()
    }

    /**
     * Runs [sql] inside a savepoint. Returns null if it succeeded, or the SQLSTATE it failed
     * with (23505 unique, 23503 foreign key, 23514 check, 23502 not null, 23P01 exclusion).
     * A failure is rolled back to the savepoint, so the transaction stays usable.
     */
    fun sqlStateOf(sql: String, vararg params: Any?): String? {
        val sp = conn.setSavepoint()
        return try {
            conn.prepareStatement(sql).use { ps ->
                params.forEachIndexed { i, p -> ps.setObject(i + 1, p) }
                ps.execute()
            }
            conn.releaseSavepoint(sp)
            null
        } catch (e: SQLException) {
            conn.rollback(sp)
            e.sqlState ?: "unknown"
        }
    }
}

/** A result set read fully into memory, with values normalized by [norm]. */
class Rows(val columns: List<String>, val rows: List<List<Any?>>) {
    val size: Int get() = rows.size

    fun column(name: String): List<Any?> {
        val i = columns.indexOf(name)
        if (i < 0) throw AssertionFailedError("no column \"$name\"; the query returned columns $columns")
        return rows.map { it[i] }
    }

    /** The column names, in order. Names are compared as PostgreSQL returns them (lower case unless quoted). */
    fun assertColumns(vararg expected: String) {
        if (columns != expected.toList()) {
            throw AssertionFailedError(
                "expected columns ${expected.toList()} but the query returned $columns",
                expected.toList().toString(), columns.toString(),
            )
        }
    }

    /** Exactly these rows, in exactly this order. */
    fun assertRowsInOrder(vararg expected: List<Any?>) {
        val want = expected.map { r -> r.map(::norm) }
        if (rows != want) fail("these rows, in this order", want)
    }

    /** Exactly these rows, in any order (duplicates count). */
    fun assertRowsAnyOrder(vararg expected: List<Any?>) {
        val want = expected.map { r -> r.map(::norm) }
        if (sortForCompare(rows) != sortForCompare(want)) fail("these rows, in any order", want)
    }

    private fun fail(what: String, want: List<List<Any?>>): Nothing {
        val expectedText = render(columns, want)
        val actualText = render(columns, rows)
        throw AssertionFailedError(
            "expected $what:\n$expectedText\nbut the query returned:\n$actualText",
            expectedText, actualText,
        )
    }

    override fun toString(): String = render(columns, rows)

    companion object {
        fun from(rs: ResultSet): Rows {
            val md = rs.metaData
            val cols = (1..md.columnCount).map { md.getColumnLabel(it) }
            val out = mutableListOf<List<Any?>>()
            while (rs.next()) out += (1..md.columnCount).map { norm(rs.getObject(it)) }
            return Rows(cols, out)
        }

        private fun sortForCompare(rows: List<List<Any?>>) = rows.sortedBy { r -> r.joinToString("\u0000") { it.toString() } }

        /** psql-style text table, used in failure messages. NULL prints as NULL. */
        fun render(columns: List<String>, rows: List<List<Any?>>): String {
            val cells = rows.map { r -> r.map { it?.toString() ?: "NULL" } }
            val widths = columns.indices.map { i -> maxOf(columns[i].length, cells.maxOfOrNull { it.getOrNull(i)?.length ?: 0 } ?: 0) }
            fun line(values: List<String>) = values.mapIndexed { i, v -> " " + v.padEnd(widths.getOrElse(i) { v.length }) + " " }.joinToString("|")
            val sb = StringBuilder()
            sb.appendLine(line(columns))
            sb.appendLine(widths.joinToString("+") { "-".repeat(it + 2) })
            cells.forEach { sb.appendLine(line(it)) }
            sb.append("(${rows.size} row${if (rows.size == 1) "" else "s"})")
            return sb.toString()
        }
    }
}

/** One expected row: `row(13, 64000, "large", null)`. */
fun row(vararg values: Any?): List<Any?> = values.toList()

/**
 * Makes database values and expected values comparable: every integer type becomes Long,
 * numeric loses trailing zeros (and becomes Long when it is a whole number), timestamps become
 * Instant, date becomes LocalDate, json becomes its text, arrays (and expected lists) become
 * lists of normalized values.
 */
fun norm(v: Any?): Any? = when (v) {
    null -> null
    is Byte -> v.toLong()
    is Short -> v.toLong()
    is Int -> v.toLong()
    is BigDecimal -> {
        // sum(bigint) returns numeric; a whole number compares equal to the Long you expect
        val s = if (v.signum() == 0) BigDecimal.ZERO else v.stripTrailingZeros()
        if (s.scale() <= 0 && s.precision() - s.scale() <= 18) s.longValueExact() else s
    }
    is java.sql.Timestamp -> v.toInstant()
    is OffsetDateTime -> v.toInstant()
    is java.sql.Date -> v.toLocalDate()
    is java.sql.Array -> (v.array as Array<*>).map(::norm)
    is Array<*> -> v.map(::norm)
    is List<*> -> v.map(::norm)              // an expected array value: row(13, listOf(2, 4, 8, 13))
    is PGobject -> v.value
    is Instant -> v
    else -> v
}
