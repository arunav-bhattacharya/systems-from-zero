package sfz.os.l09.demo;

import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;

/**
 * Replaces a file so that after a crash it holds either the old content or the new, never a mix:
 * write a temporary file, force it, rename it over the old one, then force the directory.
 * Argument: the directory to use (default /tmp/cfg).
 */
public class SafeWrite {
    public static void main(String[] args) throws Exception {
        Path dir = Path.of(args.length > 0 ? args[0] : "/tmp/cfg");
        Files.createDirectories(dir);
        Path target = dir.resolve("routing.json");
        replace(target, "{\"issuer\": \"acme-bank\", \"timeoutMs\": 120}\n");
        System.out.print(Files.readString(target));
    }

    static void replace(Path target, String content) throws Exception {
        Path tmp = target.resolveSibling(target.getFileName() + ".tmp");
        try (FileChannel ch = FileChannel.open(tmp, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING,
                StandardOpenOption.WRITE)) {
            ch.write(ByteBuffer.wrap(content.getBytes(StandardCharsets.UTF_8)));   // 1. write the new copy
            ch.force(true);                                                       // 2. fsync it
        }
        Files.move(tmp, target, StandardCopyOption.ATOMIC_MOVE);                  // 3. rename over the old name
        try (FileChannel d = FileChannel.open(target.getParent(), StandardOpenOption.READ)) {
            d.force(true);                                                        // 4. fsync the directory
        }
    }
}
