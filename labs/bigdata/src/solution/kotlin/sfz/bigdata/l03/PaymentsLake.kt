package sfz.bigdata.l03

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.sum

object PaymentsLake {

    fun writeByDay(payments: Dataset<Row>, root: String) {
        payments.write()
            .mode(SaveMode.Overwrite)
            // one directory per distinct dt; Spark removes dt from the rows it writes into each file
            .partitionBy("dt")
            .parquet(root)
    }

    fun registerTable(spark: SparkSession, table: String, root: String) {
        // the schema lives in the catalog; the files are only checked against it when a query reads them.
        // LOCATION makes it an external table: DROP TABLE forgets it, the files stay.
        spark.sql(
            """
            CREATE TABLE $table (
                payment_id BIGINT, merchant_id INT, card_country STRING, currency STRING,
                amount_cents BIGINT, status STRING, created_at TIMESTAMP, dt STRING)
            USING parquet
            PARTITIONED BY (dt)
            LOCATION '$root'
            """.trimIndent(),
        )
        // a new table over existing data starts with ZERO partitions in the catalog
        refreshPartitions(spark, table)
    }

    fun refreshPartitions(spark: SparkSession, table: String) {
        // walk the table's directory and add every dt=... folder the catalog doesn't know yet
        spark.sql("MSCK REPAIR TABLE $table")
    }

    fun dailyTotal(spark: SparkSession, table: String, dt: String): Dataset<Row> =
        spark.table(table)
            // a filter on the partition column: the catalog returns one partition, Spark lists one directory
            .where(col("dt").equalTo(dt))
            .agg(sum("amount_cents"))

    // hive_partitioning turns dt=... path segments into a column, and DuckDB prunes files on it
    fun dailyTotalSql(root: String, dt: String): String =
        "SELECT sum(amount_cents) FROM read_parquet('$root/**/*.parquet', hive_partitioning = true) WHERE dt = '$dt'"
}
