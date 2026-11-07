package sfz.os.l10.demo;

import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

/**
 * Plays a service with its log file open: opens the log in append mode (as logging frameworks do),
 * writes about MB megabytes of authorization lines, then keeps the file open and adds one line a
 * second until it has run for SECONDS seconds.
 * Arguments: the log path (default /dev/shm/auth.log), MB (default 40), SECONDS (default 60).
 */
public class LogHolder {
    public static void main(String[] args) throws Exception {
        String path = args.length > 0 ? args[0] : "/dev/shm/auth.log";
        int mb = args.length > 1 ? Integer.parseInt(args[1]) : 40;
        int seconds = args.length > 2 ? Integer.parseInt(args[2]) : 60;
        byte[] line = "2026-11-07T10:15:02Z auth-7731 card=4111******1111 amount=120.00 approved\n"
                .getBytes(StandardCharsets.US_ASCII);
        try (FileOutputStream log = new FileOutputStream(path, true)) {     // true: open with O_APPEND
            long target = mb * 1024L * 1024L, written = 0;
            while (written < target) {
                log.write(line);
                written += line.length;
            }
            System.out.printf("pid %d wrote %d MB to %s and keeps it open%n", ProcessHandle.current().pid(), mb, path);
            for (int s = 0; s < seconds; s++) {
                Thread.sleep(1000);
                log.write(line);                                             // one more line a second
            }
        }
    }
}
