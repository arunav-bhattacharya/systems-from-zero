package sfz.bigdata.l06

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col

/** Three ways to change how a DataFrame is cut into partitions. */
object Layout {

    /**
     * [n] partitions (fewer than [df] has now) WITHOUT a shuffle: merge neighbouring partitions in
     * place. Use it to write fewer, bigger files.
     */
    fun fewer(df: Dataset<Row>, n: Int): Dataset<Row> {
        // narrow: each new partition is a few old ones read one after another, no Exchange
        return df.coalesce(n)
    }

    /**
     * [n] partitions of nearly equal size, however lopsided [df]'s partitions are now. Every row
     * may move.
     */
    fun even(df: Dataset<Row>, n: Int): Dataset<Row> {
        // Exchange RoundRobinPartitioning(n): row 1 to partition k, row 2 to k + 1, ...
        return df.repartition(n)
    }

    /**
     * [n] partitions where all rows with the same value of [key] land in the same partition, so
     * that a later `groupBy(key)` finds its rows already together.
     */
    fun byKey(df: Dataset<Row>, key: String, n: Int): Dataset<Row> {
        // Exchange hashpartitioning(key, n): the same rule a groupBy(key) would use
        return df.repartition(n, col(key))
    }
}
