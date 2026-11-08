package sfz.batch.l04

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession

/**
 * A Hive-style payments table: Parquet files in one directory per day (`dt=2026-11-01/`),
 * registered in a catalog so engines can find it by name.
 *
 * Spark's built-in catalog plays the Hive metastore here. It keeps tables and their partitions
 * in memory instead of in MySQL behind a Thrift service, but it follows the same rules: a table
 * points at a directory, and the catalog keeps its own list of partitions.
 */
object PaymentsLake {

    /**
     * Writes [payments] under [root] as Parquet, one directory per value of the `dt` column:
     * `root/dt=2026-11-01/part-....parquet`. Replaces whatever was under [root] before.
     *
     * The `dt` value lives in the directory name, not inside the files.
     */
    fun writeByDay(payments: Dataset<Row>, root: String) {
        TODO("payments.write() with overwrite mode, partitionBy(\"dt\"), as parquet")
    }

    /**
     * Registers the files under [root] as an external table called [table], partitioned by `dt`,
     * and makes the catalog learn every day directory that is already on disk.
     *
     * The catalog holds the schema, so the DDL lists the columns: `payment_id BIGINT,
     * merchant_id INT, card_country STRING, currency STRING, amount_cents BIGINT, status STRING,
     * created_at TIMESTAMP, dt STRING`. The table does not exist yet when this runs. Paths may
     * contain spaces, so keep the path inside quotes.
     */
    fun registerTable(spark: SparkSession, table: String, root: String) {
        TODO("CREATE TABLE ... USING parquet PARTITIONED BY (dt) LOCATION '...', then find the partitions")
    }

    /**
     * Another job wrote new `dt=` directories straight into the table's location. Make the catalog
     * add them, the way Hive's MSCK REPAIR TABLE does.
     */
    fun refreshPartitions(spark: SparkSession, table: String) {
        TODO("one SQL statement")
    }

    /**
     * The total of `amount_cents` for the day [dt] (`yyyy-MM-dd`), read through the catalog
     * table [table]: one row, one column.
     *
     * It must read only that day's files. Filter on the partition column, not on `created_at`.
     */
    fun dailyTotal(spark: SparkSession, table: String, dt: String): Dataset<Row> {
        TODO("spark.table(table), filter on dt, sum amount_cents")
    }

    /**
     * DuckDB SQL that returns the same total (one row, one column) straight from the Parquet files
     * under [root], with no catalog at all, and opens only that day's files.
     */
    fun dailyTotalSql(root: String, dt: String): String {
        TODO("read_parquet('<root>/**/*.parquet', hive_partitioning = true) with a WHERE on dt")
    }
}
