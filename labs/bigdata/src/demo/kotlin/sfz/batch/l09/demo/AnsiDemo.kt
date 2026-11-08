package sfz.batch.l09.demo

/**
 * The same expressions with ANSI mode off (Spark 3's default) and on (Spark 4's default), then the
 * try_ functions that give null on purpose.
 */
fun main() {
    val spark = demoSpark()
    println("spark.sql.ansi.enabled by default: ${spark.conf().get("spark.sql.ansi.enabled")}")
    val cases = listOf(
        "CAST('12,50' AS INT)" to "a decimal comma in a settlement file",
        "CAST('2026-13-01' AS DATE)" to "month 13",
        "CAST(25000000 AS INT) * 100" to "25 million euros in cents, as INT",
        "CAST(300 AS TINYINT)" to "a value too big for the type",
        "1250 / 0" to "an fx rate of zero",
        "element_at(array(10, 20, 30), 5)" to "the 5th of 3 elements",
    )
    for ((sql, what) in cases) {
        spark.conf().set("spark.sql.ansi.enabled", "false")
        val off = valueOrError(spark, "SELECT $sql")
        spark.conf().set("spark.sql.ansi.enabled", "true")
        val on = valueOrError(spark, "SELECT $sql")
        println("%-34s (%s)\n    ANSI off: %s\n    ANSI on:  %s".format(sql, what, off, on))
    }
    println("the safe versions, ANSI on:")
    for (sql in listOf("try_cast('12,50' AS INT)", "try_multiply(CAST(25000000 AS INT), 100)",
        "try_divide(1250, 0)", "try_element_at(array(10, 20, 30), 5)", "CAST(25000000 AS BIGINT) * 100")) {
        println("    %-42s -> %s".format(sql, valueOrError(spark, "SELECT $sql")))
    }
    spark.stop()
}
