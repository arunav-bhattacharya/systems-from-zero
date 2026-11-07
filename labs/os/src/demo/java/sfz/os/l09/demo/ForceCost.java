package sfz.os.l09.demo;

import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

/**
 * Appends 4 KB authorization records to a log three ways: never forced, forced after every
 * record (FileChannel.force, which is fdatasync), and forced once per batch of 100.
 * Argument: the directory for the log (default /tmp).
 */
public class ForceCost {
    static final int RECORD = 4096;

    public static void main(String[] args) throws Exception {
        Path dir = Path.of(args.length > 0 ? args[0] : "/tmp");
        System.out.println("mode                 records   total ms   us per record");
        run(dir, "write only", 20_000, 0);
        run(dir, "force every record", 1_000, 1);
        run(dir, "force every 100", 20_000, 100);
    }

    static void run(Path dir, String mode, int records, int every) throws Exception {
        Path log = dir.resolve("auth.log");
        ByteBuffer rec = ByteBuffer.allocateDirect(RECORD);
        try (FileChannel ch = FileChannel.open(log, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING,
                StandardOpenOption.WRITE)) {
            long t0 = System.nanoTime();
            for (int i = 1; i <= records; i++) {
                rec.clear();
                rec.putLong(0, i);                       // the record's sequence number
                ch.write(rec);                           // into the page cache: returns in microseconds
                if (every > 0 && i % every == 0) ch.force(false);   // fdatasync: wait for the device
            }
            double ms = (System.nanoTime() - t0) / 1e6;
            System.out.printf("%-20s %7d %10.0f %15.1f%n", mode, records, ms, ms * 1000 / records);
        } finally {
            Files.deleteIfExists(log);
        }
    }
}
