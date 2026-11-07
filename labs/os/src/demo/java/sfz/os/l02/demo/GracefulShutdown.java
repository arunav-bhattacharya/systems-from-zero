package sfz.os.l02.demo;

/**
 * A stand-in for a payment service that must flush work before it dies.
 *
 * <p>Start it in the background, then send it SIGTERM or SIGKILL and compare
 * what prints and which exit status the shell reports.
 */
public class GracefulShutdown {
    public static void main(String[] args) throws InterruptedException {
        // the JVM runs shutdown hooks on a normal exit, Ctrl-C (SIGINT), SIGTERM and SIGHUP
        Runtime.getRuntime().addShutdownHook(new Thread(() ->
                System.out.println("shutdown hook: flushed 3 pending ledger entries")));
        System.out.println("pid " + ProcessHandle.current().pid() + ": settlement batch running");
        Thread.sleep(60_000);
        System.out.println("batch done");
    }
}
