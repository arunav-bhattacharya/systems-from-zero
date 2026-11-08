package sfz.batch.l09.client;

import static org.apache.spark.sql.functions.col;
import static org.apache.spark.sql.functions.sum;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.apache.spark.api.java.function.MapFunction;
import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Encoders;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.connect.SparkSession;
import org.apache.spark.sql.connect.client.REPLClassDirMonitor;

/**
 * A Spark Connect client: no driver, no executors, no SparkContext in this JVM. It builds a
 * DataFrame, which is only a plan, and sends the plan to the server over gRPC.
 *
 * Arguments: the server URL (sc://host:port), the payments folder on the server's disk, and this
 * program's own classes folder (for the lambda at the end).
 */
public class SettlementClient {
    public static void main(String[] args) throws Exception {
        String url = args[0];
        String payments = args[1];
        String classesDir = args[2];

        long t0 = System.nanoTime();
        SparkSession spark = SparkSession.builder().remote(url).getOrCreate();
        System.out.printf("client: %s, connected in %d ms, server runs Spark %s%n",
                spark.getClass().getSimpleName(), (System.nanoTime() - t0) / 1_000_000, spark.version());
        System.out.printf("client: %d jars and folders on this JVM's classpath%n",
                System.getProperty("java.class.path").split(java.io.File.pathSeparator).length);

        // building the DataFrame runs nothing and contacts nobody: it is a tree of plan nodes
        Dataset<Row> report = spark.read().parquet(payments)
                .where(col("status").equalTo("CAPTURED"))
                .groupBy("merchant_id").agg(sum("amount_cents").alias("total_cents"))
                .orderBy(col("total_cents").desc())
                .limit(3);

        // the message that will cross the wire: an unresolved plan as protobuf. plan() is
        // package-private in Scala, so the client reaches it by reflection
        Object plan = report.getClass().getMethod("plan").invoke(report);
        byte[] bytes = (byte[]) plan.getClass().getMethod("toByteArray").invoke(plan);
        System.out.printf("client: the plan is a %s of %,d bytes. Without call-site details it reads:%n",
                plan.getClass().getSimpleName(), bytes.length);
        for (String line : withoutCommonBlocks(plan.toString())) System.out.println("  " + line);

        // the action: the server resolves, optimizes and runs the plan, and streams Arrow batches back
        System.out.println("client: top merchants " + report.collectAsList());
        System.out.println("client: explain(), computed by the server:");
        report.explain();

        // the client checks nothing while you build: a misspelled column only fails when the server sees the plan
        Dataset<Row> typo = spark.read().parquet(payments).where(col("stauts").equalTo("CAPTURED"));
        System.out.println("client: built a DataFrame with a misspelled column, no error yet");
        try {
            typo.count();
        } catch (Exception e) {
            System.out.println("client: count() -> " + firstLine(e));
        }

        // what a thin client cannot do: there is no SparkContext and there are no RDDs on this side
        try {
            spark.sparkContext();
        } catch (Exception e) {
            System.out.println("client: sparkContext() -> " + firstLine(e));
        }
        try {
            report.rdd();
        } catch (Exception e) {
            System.out.println("client: rdd() -> " + firstLine(e));
        }

        // a typed lambda is bytecode the server doesn't have
        MapFunction<Long, Long> times100 = x -> x * 100;
        try {
            spark.range(3).map(times100, Encoders.LONG()).collectAsList();
        } catch (Exception e) {
            System.out.println("client: map(lambda) -> " + firstLine(e));
        }
        // upload this program's class files, and the same lambda runs on the server
        spark.registerClassFinder(new REPLClassDirMonitor(Path.of(classesDir).toAbsolutePath().toString()));
        System.out.println("client: map(lambda) after registerClassFinder -> "
                + spark.range(3).map(times100, Encoders.LONG()).collectAsList());
        System.exit(0);
    }

    /** The protobuf text without its `common { ... }` blocks, which carry plan ids and call sites. */
    static List<String> withoutCommonBlocks(String text) {
        List<String> out = new ArrayList<>();
        int skipping = 0;
        for (String line : text.split("\n")) {
            String t = line.trim();
            if (skipping > 0) {
                if (t.endsWith("{")) skipping++;
                if (t.equals("}")) skipping--;
                continue;
            }
            if (t.equals("common {")) {
                skipping = 1;
                continue;
            }
            out.add(line);
        }
        return out;
    }

    static String firstLine(Throwable e) {
        String m = e.getMessage() == null ? "" : e.getMessage();
        String first = m.split("\n")[0];
        return e.getClass().getSimpleName() + ": " + (first.length() > 160 ? first.substring(0, 160) + "..." : first);
    }
}
