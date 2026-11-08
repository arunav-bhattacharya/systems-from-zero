package sfz.batch.l03.demo

import org.apache.spark.sql.SparkSession

/** A quiet local SparkSession for the demos: no web UI, loopback only, 4 shuffle partitions. */
fun demoSpark(threads: Int = 2): SparkSession =
    SparkSession.builder()
        .appName("sfz-demo")
        .master("local[$threads]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
        .also { it.sparkContext().setLogLevel("ERROR") }
