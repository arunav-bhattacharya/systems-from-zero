package sfz.os.l07.demo;

import java.util.ArrayList;
import java.util.List;

/**
 * Keeps allocating 1 MB arrays and never lets go, printing the heap limit and progress.
 * Run it in a container with a memory limit to see who stops it: the JVM or the kernel.
 */
public class Hog {
    public static void main(String[] args) {
        System.out.printf("max heap %d MB%n", Runtime.getRuntime().maxMemory() >> 20);
        List<byte[]> held = new ArrayList<>();
        while (true) {
            byte[] block = new byte[1 << 20];
            for (int i = 0; i < block.length; i += 4096) block[i] = 1;   // touch every page
            held.add(block);
            if (held.size() % 32 == 0) System.out.printf("holding %d MB%n", held.size());
        }
    }
}
