package sfz.os.l10.demo;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * A config reader with a leak: it opens the file for every "request" and never closes it. Each open
 * takes a file descriptor, and the list keeps the streams reachable so the garbage collector can't
 * close them either. It stops by itself after MAX opens, so it can't use up the whole machine's
 * descriptors when no limit is set.
 * Arguments: the file to open (default /etc/hostname), MAX (default 5000).
 */
public class FdLeak {
    public static void main(String[] args) throws Exception {
        String file = args.length > 0 ? args[0] : "/etc/hostname";
        int max = args.length > 1 ? Integer.parseInt(args[1]) : 5000;
        System.out.println("open file descriptors at start: " + openFds());
        List<FileInputStream> leaked = new ArrayList<>();
        try {
            while (leaked.size() < max) {
                leaked.add(new FileInputStream(file));     // the bug: no close(), no try-with-resources
            }
            System.out.println("opened " + max + " files without an error; open file descriptors: " + openFds());
        } catch (IOException e) {
            System.out.println("open number " + (leaked.size() + 1) + " failed: " + e);
            leaked.remove(leaked.size() - 1).close();      // free one descriptor so the count below can run
            System.out.println("open file descriptors when it failed: " + (openFds() + 1));
        }
    }

    static int openFds() {
        String[] fds = new File("/proc/self/fd").list();   // one entry per open descriptor
        return fds == null ? -1 : fds.length - 1;           // minus the one this listing holds open
    }
}
