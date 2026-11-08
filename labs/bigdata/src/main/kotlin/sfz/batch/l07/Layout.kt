package sfz.batch.l07

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row

/** Three ways to change how a DataFrame is cut into partitions. */
object Layout {

    /**
     * [n] partitions (fewer than [df] has now) WITHOUT a shuffle: merge neighbouring partitions in
     * place. Use it to write fewer, bigger files.
     */
    fun fewer(df: Dataset<Row>, n: Int): Dataset<Row> {
        TODO("merge partitions without moving rows between machines")
    }

    /**
     * [n] partitions of nearly equal size, however lopsided [df]'s partitions are now. Every row
     * may move.
     */
    fun even(df: Dataset<Row>, n: Int): Dataset<Row> {
        TODO("shuffle the rows round robin into n partitions")
    }

    /**
     * [n] partitions where all rows with the same value of [key] land in the same partition, so
     * that a later `groupBy(key)` finds its rows already together.
     */
    fun byKey(df: Dataset<Row>, key: String, n: Int): Dataset<Row> {
        TODO("shuffle by hash of the key into n partitions")
    }
}
