package sfz.os.l06.demo;

/**
 * A JVM that allocates a little and then waits, so you can compare the memory it
 * reserved (VSZ) with the memory it really uses (RSS) from outside.
 * Argument: seconds to stay alive (default 30).
 */
public class Idle {
    public static void main(String[] args) throws Exception {
        byte[][] ledger = new byte[64][];
        for (int i = 0; i < ledger.length; i++) ledger[i] = new byte[1 << 20];   // 64 MB of real objects
        System.out.println("pid " + ProcessHandle.current().pid() + " holds " + ledger.length + " MB of arrays");
        Thread.sleep(Long.parseLong(args.length > 0 ? args[0] : "30") * 1000);
        System.out.println(ledger[0].length);
    }
}
