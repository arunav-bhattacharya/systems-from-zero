package sfz.bigdata.support

import org.apache.spark.sql.SparkSession
import java.nio.file.Files

/**
 * One local SparkSession for the whole test JVM. Starting Spark costs a second or two, so every
 * test class in the track shares this one instead of building its own.
 *
 * - `local[2]`: two worker threads, so tests see real parallelism but stay light.
 * - 4 shuffle partitions instead of the default 200, which is far too many for test-sized data.
 * - No web UI, a UTC session clock, and a loopback driver address, so tests never touch the network.
 * - The Iceberg SQL extensions are switched on now because they can only be set before the session
 *   starts. Lessons that use Iceberg add their catalog at runtime with `spark.conf().set(...)`.
 *
 * Tests must not call `stop()`: the session lives until the JVM exits. Give every table and temp
 * view a name unique to your lesson (for example `l03_payments`) so test classes don't collide.
 */
object LocalSpark {
    val session: SparkSession by lazy {
        val warehouse = Files.createTempDirectory("sfz-spark-warehouse").toFile().apply { deleteOnExit() }
        SparkSession.builder()
            .appName("sfz-bigdata-tests")
            .master("local[2]")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "4")
            .config("spark.default.parallelism", "4")
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.driver.host", "127.0.0.1")
            .config("spark.driver.bindAddress", "127.0.0.1")
            .config("spark.sql.warehouse.dir", warehouse.absolutePath)
            .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
            .getOrCreate()
            .also { it.sparkContext().setLogLevel("ERROR") }
    }

    /**
     * A new session on the same SparkContext with its own SQL settings and temp views, so a test can
     * change settings such as `spark.sql.adaptive.enabled` or `spark.sql.autoBroadcastJoinThreshold`
     * without touching the shared [session]. It starts from the settings above (4 shuffle
     * partitions, UTC) and then applies [conf].
     */
    fun isolated(vararg conf: Pair<String, String>): SparkSession {
        val s: SparkSession = session.newSession()
        for ((key, value) in conf) s.conf().set(key, value)
        return s
    }
}
