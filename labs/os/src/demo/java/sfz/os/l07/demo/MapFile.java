package sfz.os.l07.demo;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileChannel.MapMode;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

/**
 * Maps a 256 MB file into memory and reads it through the mapping, then writes through a
 * shared and a private mapping to show which writes reach the file.
 * Argument: the file to create (default /tmp/ledger.dat). The file is deleted at the end.
 */
public class MapFile {
    static final int MB = 1 << 20;

    public static void main(String[] args) throws Exception {
        Path file = Path.of(args.length > 0 ? args[0] : "/tmp/ledger.dat");
        try (FileChannel ch = FileChannel.open(file, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING,
                StandardOpenOption.READ, StandardOpenOption.WRITE)) {
            ByteBuffer chunk = ByteBuffer.allocate(MB);
            for (int i = 0; i < 256; i++) { chunk.clear(); ch.write(chunk); }      // 256 MB of real file data
            memory("before map");

            MappedByteBuffer map = ch.map(MapMode.READ_ONLY, 0, 256L * MB);       // mmap: a region, no RAM yet
            memory("after map");
            long sum = 0;
            for (int off = 0; off < map.capacity(); off += 4096) sum += map.get(off);   // touch every page
            memory("after reading");
            for (String line : Files.readAllLines(Path.of("/proc/self/maps")))
                if (line.endsWith(file.toString())) System.out.println("maps: " + line);

            MappedByteBuffer shared = ch.map(MapMode.READ_WRITE, 0, 4096);        // MAP_SHARED
            MappedByteBuffer priv = ch.map(MapMode.PRIVATE, 0, 4096);             // MAP_PRIVATE: copy-on-write
            shared.put(0, (byte) 'S');
            priv.put(1, (byte) 'P');
            ByteBuffer onDisk = ByteBuffer.allocate(2);
            ch.read(onDisk, 0);
            System.out.printf("file bytes 0-1: '%c' %d   private mapping sees '%c' '%c'%n",
                    (char) onDisk.get(0), onDisk.get(1), (char) priv.get(0), (char) priv.get(1));
            if (sum != 0) System.out.println(sum);
        } finally {
            Files.deleteIfExists(file);
        }
    }

    static void memory(String when) throws IOException {
        long anon = 0, fileKb = 0;
        for (String line : Files.readAllLines(Path.of("/proc/self/status"))) {
            if (line.startsWith("RssAnon:")) anon = kb(line);
            if (line.startsWith("RssFile:")) fileKb = kb(line);
        }
        System.out.printf("%-14s RssAnon %4d MB   RssFile %4d MB%n", when, anon / 1024, fileKb / 1024);
    }

    static long kb(String line) {
        return Long.parseLong(line.replaceAll("[^0-9]", ""));
    }
}
