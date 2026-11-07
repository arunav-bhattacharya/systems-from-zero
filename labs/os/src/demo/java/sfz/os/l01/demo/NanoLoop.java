package sfz.os.l01.demo;

/**
 * Calls System.nanoTime() one million times. On Linux each call reads the clock
 * through the vDSO, so strace sees no clock_gettime system calls from this loop.
 */
public class NanoLoop {
    public static void main(String[] args) {
        int calls = args.length > 0 ? Integer.parseInt(args[0]) : 1_000_000;
        long sum = 0;
        long t0 = System.nanoTime();
        for (int i = 0; i < calls; i++) {
            sum += System.nanoTime();      // vDSO: no trap into the kernel
        }
        long ns = System.nanoTime() - t0;
        // print sum so the JIT cannot drop the loop
        System.out.printf("%,d nanoTime() calls in %,d ms (%d ns each), checksum %d%n",
                calls, ns / 1_000_000, ns / calls, sum % 10);
    }
}
