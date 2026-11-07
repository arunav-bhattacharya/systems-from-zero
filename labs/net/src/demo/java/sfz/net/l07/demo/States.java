package sfz.net.l07.demo;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;

/**
 * One TCP connection on 127.0.0.1, opened and closed one step at a time. After each step it asks the
 * kernel for the state of every socket on the server's port, so you see the states the lesson names:
 * LISTEN, ESTAB, FIN-WAIT-2, CLOSE-WAIT and TIME-WAIT.
 *
 * The client closes first, and the server waits before it closes, the way a server with a forgotten
 * close() would. It prints the states with Linux's `ss`, so run it in the lab box:
 *
 *   java /labs/net/src/demo/java/sfz/net/l07/demo/States.java
 *
 * On a Mac (./gradlew :net:demo -Pmain=sfz.net.l07.demo.States) it runs the same steps without the
 * state listing; `netstat -an -p tcp` in another terminal shows the states there.
 */
public class States {
    static int port;

    public static void main(String[] args) throws Exception {
        InetAddress lo = InetAddress.getByName("127.0.0.1");
        try (ServerSocket listener = new ServerSocket()) {
            listener.bind(new InetSocketAddress(lo, 0), 50);    // socket(), bind(), listen(backlog 50)
            port = listener.getLocalPort();
            show("1. server called listen()");

            Socket client = new Socket();
            client.connect(new InetSocketAddress(lo, port));    // the kernel does the handshake
            show("2. client connect() returned; the server has not called accept() yet");

            Socket accepted = listener.accept();                 // takes the finished connection off the queue
            show("3. server accept() returned a second socket for this one connection");

            client.close();                                      // client sends FIN
            Thread.sleep(50);
            show("4. client close(): its FIN was ACKed, but the server program has not closed");

            int eof = accepted.getInputStream().read();          // the only way the server program learns
            System.out.println("   server read() returned " + eof + ": end of stream, the peer has closed");
            System.out.println();

            accepted.close();                                    // server sends its FIN
            Thread.sleep(50);
            show("5. server close(): the client side, which closed first, waits in TIME-WAIT");
        }
    }

    static void show(String step) throws Exception {
        System.out.println(step);
        Process p;
        try {
            p = new ProcessBuilder("ss", "-tan", "( sport = :" + port + " or dport = :" + port + " )")
                    .redirectErrorStream(true).start();
        } catch (java.io.IOException noSs) {
            // macOS has no ss; netstat -an -p tcp shows the same states (FIN_WAIT_2, CLOSE_WAIT, TIME_WAIT)
            System.out.println("   (no ss here: run this demo in the lab box to see the states)");
            System.out.println();
            Thread.sleep(200);
            return;
        }
        try (BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
            r.lines().forEach(line -> System.out.println("   " + line));
        }
        p.waitFor();
        System.out.println();
    }
}
