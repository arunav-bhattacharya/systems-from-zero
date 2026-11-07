package sfz.bigdata.l04.demo

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.SparkPlan
import org.apache.spark.util.AccumulatorV2
import scala.jdk.javaapi.CollectionConverters
import java.io.File
import java.sql.Connection
import java.sql.DriverManager
import java.util.TimeZone

/**
 * 400,000 made-up payments written by DuckDB as Parquet, in row groups of about 100,000 rows:
 * once sorted by amount, once in payment_id order (where the amounts are random).
 */
object PaymentParquet {
    private val dir = File("build/l04")
    val sorted = File(dir, "sorted.parquet")
    val random = File(dir, "random.parquet")

    private const val GENERATOR = """
        SELECT i AS payment_id, (hash(i) % 500)::INTEGER AS merchant_id,
               ['NL','DE','FR','GB'][(hash(i + 1) % 4)::INTEGER + 1] AS card_country,
               ['AUTHORIZED','CAPTURED','DECLINED','REFUNDED'][(hash(i + 2) % 4)::INTEGER + 1] AS status,
               (hash(i + 3) % 250000 + 100)::BIGINT AS amount_cents
        FROM range(400000) t(i)"""

    /** Writes both files (every run, so they always match this code) and returns a DuckDB connection. */
    fun open(): Connection {
        dir.mkdirs()
        val c = DriverManager.getConnection("jdbc:duckdb:")
        c.createStatement().use { s ->
            s.execute("CREATE TABLE p AS $GENERATOR")
            s.execute("COPY (SELECT * FROM p ORDER BY amount_cents, payment_id) TO '${sorted.absolutePath}' (FORMAT parquet, ROW_GROUP_SIZE 100000)")
            s.execute("COPY (SELECT * FROM p ORDER BY payment_id) TO '${random.absolutePath}' (FORMAT parquet, ROW_GROUP_SIZE 100000)")
        }
        return c
    }
}

/** Runs [sql] and returns every row as a list of strings. */
fun Connection.rows(sql: String): List<List<String?>> = createStatement().use { s ->
    s.executeQuery(sql).use { rs ->
        buildList { while (rs.next()) add((1..rs.metaData.columnCount).map { rs.getString(it) }) }
    }
}

/** A quiet local SparkSession for the demos: no web UI, loopback only, UTC everywhere. */
fun demoSpark(): SparkSession {
    TimeZone.setDefault(TimeZone.getTimeZone("UTC"))          // so plans print timestamps in UTC too
    return SparkSession.builder()
        .appName("sfz-demo")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
        .also { it.sparkContext().setLogLevel("ERROR") }
}

/** After [query] ran: how many rows its Parquet scan handed on to the operators above it. */
fun scanRows(query: Dataset<*>): Long {
    fun nodes(p: SparkPlan): List<SparkPlan> = listOf(p) + CollectionConverters.asJava(p.children()).flatMap { nodes(it) }
    val scan = nodes(query.queryExecution().executedPlan()).first { it.nodeName().startsWith("Scan") }
    return ((CollectionConverters.asJava(scan.metrics())["numOutputRows"] as AccumulatorV2<*, *>).value() as Number).toLong()
}

/** The `PushedFilters: [...]` part of [query]'s plan. */
fun pushedFilters(query: Dataset<*>): String =
    Regex("""PushedFilters: \[(.*?)\]""").find(query.queryExecution().executedPlan().toString())?.groupValues?.get(1) ?: "?"
