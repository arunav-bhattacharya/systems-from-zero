package sfz.bigdata.support

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.RowFactory
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.concat
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.types.DataTypes
import org.apache.spark.sql.types.StructType
import java.sql.Timestamp
import java.time.LocalDate
import java.time.ZoneOffset
import kotlin.random.Random

/** One card authorization, the row type most lessons in this track use. Amounts are in cents. */
data class Payment(
    val paymentId: Long,
    val merchantId: Int,
    val cardCountry: String,
    val currency: String,
    val amountCents: Long,
    val status: String,
    val createdAt: Timestamp,
    /** The day of [createdAt] in UTC, as `yyyy-MM-dd`: the Hive-style partition column. */
    val dt: String,
)

/**
 * Deterministic test data. The same arguments give the same rows on every machine and every run,
 * so tests can assert exact numbers.
 */
object TestData {
    val COUNTRIES = listOf("NL", "DE", "FR", "GB", "US", "IN", "BR", "JP")
    val CURRENCIES = listOf("EUR", "USD", "GBP", "INR")
    val STATUSES = listOf("AUTHORIZED", "CAPTURED", "DECLINED", "REFUNDED")

    /** [n] payments spread evenly over [days] days starting at [firstDay] (UTC). */
    fun payments(n: Int, days: Int = 7, firstDay: LocalDate = LocalDate.of(2026, 11, 1), seed: Long = 42): List<Payment> {
        val rnd = Random(seed)
        return (0 until n).map { i ->
            val day = firstDay.plusDays((i % days).toLong())
            val second = rnd.nextLong(86_400)
            val instant = day.atStartOfDay().toInstant(ZoneOffset.UTC).plusSeconds(second)
            Payment(
                paymentId = i.toLong(),
                merchantId = rnd.nextInt(500),
                cardCountry = COUNTRIES[rnd.nextInt(COUNTRIES.size)],
                currency = CURRENCIES[rnd.nextInt(CURRENCIES.size)],
                amountCents = 100L + rnd.nextLong(250_000),
                status = STATUSES[rnd.nextInt(STATUSES.size)],
                createdAt = Timestamp.from(instant),
                dt = day.toString(),
            )
        }
    }

    /**
     * [n] payments like [payments], except that every payment whose id ends in 00 to [hotPercent] - 1
     * (so [hotPercent] percent of them) belongs to [hotMerchant]: one marketplace merchant with far
     * more payments than the other 499. Lesson 8 uses it for skew.
     */
    fun skewedPayments(n: Int, hotMerchant: Int = 7, hotPercent: Int = 30, seed: Long = 42): List<Payment> =
        payments(n, seed = seed).map { if (it.paymentId % 100 < hotPercent) it.copy(merchantId = hotMerchant) else it }

    /**
     * [n] merchants, one row each: `merchant_id` 0 until [n], `merchant_name` ("Merchant 42") and
     * `mcc`, a made-up merchant category code from 5000 to 5019. Built by Spark from a range, so it
     * needs no files.
     */
    fun merchantsFrame(spark: SparkSession, n: Int = 500): Dataset<Row> =
        spark.range(0, n.toLong(), 1, 2).select(
            col("id").cast("int").alias("merchant_id"),
            concat(lit("Merchant "), col("id")).alias("merchant_name"),
            col("id").mod(20).plus(5_000).cast("int").alias("mcc"),
        )

    /** The Spark schema for [Payment]: snake_case columns, `dt` last. */
    val PAYMENT_SCHEMA: StructType = StructType()
        .add("payment_id", DataTypes.LongType, false)
        .add("merchant_id", DataTypes.IntegerType, false)
        .add("card_country", DataTypes.StringType, false)
        .add("currency", DataTypes.StringType, false)
        .add("amount_cents", DataTypes.LongType, false)
        .add("status", DataTypes.StringType, false)
        .add("created_at", DataTypes.TimestampType, false)
        .add("dt", DataTypes.StringType, false)

    /** [rows] as a Spark DataFrame with [PAYMENT_SCHEMA]. */
    fun paymentsFrame(spark: SparkSession, rows: List<Payment>): Dataset<Row> =
        spark.createDataFrame(
            rows.map {
                RowFactory.create(it.paymentId, it.merchantId, it.cardCountry, it.currency, it.amountCents, it.status, it.createdAt, it.dt)
            },
            PAYMENT_SCHEMA,
        )

    /**
     * Writes [rows] as [files] Parquet files under [dir] (replacing it) and returns a DataFrame that
     * reads them back. Use it instead of [paymentsFrame] when a test looks at plans or stages: Spark
     * evaluates filters on an in-memory frame while it plans, so a `Filter` never shows up there.
     */
    fun paymentsParquet(spark: SparkSession, rows: List<Payment>, dir: java.io.File, files: Int = 4): Dataset<Row> {
        paymentsFrame(spark, rows).repartition(files).write().mode("overwrite").parquet(dir.absolutePath)
        return spark.read().parquet(dir.absolutePath)
    }

    /**
     * [count] lines of text with [wordsPerLine] words each, drawn from a vocabulary of [vocabulary]
     * made-up lowercase words with a Zipf-like skew: the most common word appears about twice as
     * often as the second, three times as often as the third, and so on, like words in real text.
     * Words are joined by single spaces, with an occasional comma or capital letter.
     */
    fun corpus(count: Int, wordsPerLine: Int = 12, vocabulary: Int = 2_000, seed: Long = 7): List<String> {
        val words = vocabulary(vocabulary)
        // cumulative weights for P(rank r) proportional to 1/r
        val cumulative = DoubleArray(words.size)
        var total = 0.0
        for (r in words.indices) { total += 1.0 / (r + 1); cumulative[r] = total }
        val rnd = Random(seed)
        return List(count) {
            (0 until wordsPerLine).joinToString(" ") {
                val x = rnd.nextDouble() * total
                var i = cumulative.binarySearch(x)
                if (i < 0) i = -i - 1
                val w = words[minOf(i, words.size - 1)]
                when (rnd.nextInt(20)) {
                    0 -> w.replaceFirstChar { c -> c.uppercaseChar() }
                    1 -> "$w,"
                    else -> w
                }
            }
        }
    }

    /** [n] distinct pronounceable lowercase words, the same list every time. */
    fun vocabulary(n: Int): List<String> {
        val syllables = listOf("ka", "ro", "mi", "tu", "le", "sa", "no", "vi", "da", "pe", "zu", "ho", "ri", "go", "bel", "tan")
        val out = LinkedHashSet<String>()
        var i = 0
        while (out.size < n) {
            var x = i++
            val sb = StringBuilder()
            do { sb.append(syllables[x % syllables.size]); x /= syllables.size } while (x > 0)
            out += sb.toString()
        }
        return out.toList()
    }
}
