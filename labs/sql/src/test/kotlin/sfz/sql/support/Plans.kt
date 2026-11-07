package sfz.sql.support

import org.opentest4j.AssertionFailedError

/**
 * Runs EXPLAIN on [sql] inside this transaction and returns the plan.
 *
 * With [analyze] (the default) it is `EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF)`, so the
 * query really runs and the plan carries actual rows and buffer counts but no machine-dependent
 * times. [sql] may start with -- comments and end with a semicolon, like an exercise file.
 */
fun Tx.explain(sql: String, analyze: Boolean = true): Plan {
    val options = if (analyze) "ANALYZE, BUFFERS, COSTS OFF, TIMING OFF" else "COSTS OFF"
    val statements = splitStatements(sql)
    if (statements.size != 1) {
        throw AssertionFailedError("expected exactly one statement to EXPLAIN, found ${statements.size}:\n$sql")
    }
    val body = statements.single()
    val lines = conn.createStatement().use { st ->
        st.executeQuery("EXPLAIN ($options)\n$body").use { rs ->
            buildList { while (rs.next()) add(rs.getString(1)) }
        }
    }
    return Plan(lines)
}

/** One EXPLAIN output, split into nodes. Each node has its title line and the detail lines under it. */
class Plan(val lines: List<String>) {

    class Node(val title: String, val details: List<String>) {
        /** "Index Scan Backward using payments_x on payments p (actual rows=20.00 loops=1)" without the parentheses */
        val name: String get() = title.substringBefore(" (").trim()

        fun detail(label: String): String? =
            details.firstOrNull { it.startsWith("$label:") }?.substringAfter(":")?.trim()

        /** shared hit + read for this node and everything under it, from its Buffers line (0 if none) */
        val buffers: Int
            get() {
                val b = detail("Buffers") ?: return 0
                fun n(key: String) = Regex("""$key=(\d+)""").find(b)?.groupValues?.get(1)?.toInt() ?: 0
                return n("hit") + n("read")
            }
    }

    val nodes: List<Node> = run {
        val out = mutableListOf<Node>()
        var title: String? = null
        val details = mutableListOf<String>()
        for ((i, raw) in lines.withIndex()) {
            val line = raw.trim()
            val isNode = i == 0 || line.startsWith("->")
            if (isNode) {
                title?.let { out += Node(it, details.toList()) }
                title = line.removePrefix("->").trim()
                details.clear()
            } else if (line.isNotEmpty()) {
                details += line
            }
        }
        title?.let { out += Node(it, details.toList()) }
        out
    }

    val text: String get() = lines.joinToString("\n")

    /** The node that reads [table] (a scan node whose name ends with "on <table>" or "on <table> <alias>"). */
    fun scanOf(table: String): Node? =
        nodes.firstOrNull { Regex("""\bon $table(\s+\w+)?$""").containsMatchIn(it.name) }

    fun has(nodeName: String): Boolean = nodes.any { it.name.startsWith(nodeName) }

    /** Buffers of the top node: everything the query read. */
    val buffers: Int get() = nodes.firstOrNull()?.buffers ?: 0

    fun fail(message: String): Nothing = throw AssertionFailedError("$message\nThe plan was:\n$text")

    override fun toString(): String = text
}
