package sfz.net.l06.demo;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.PortUnreachableException;
import java.net.SocketTimeoutException;
import java.nio.ByteBuffer;
import java.nio.channels.DatagramChannel;
import java.nio.charset.StandardCharsets;

/**
 * Three ways a datagram disappears, and what the sender hears about each.
 *   1. Sent to a port nobody listens on, from an unconnected socket: send() succeeds, then silence.
 *   2. The same from a connected DatagramChannel: the kernel passes on the ICMP Port Unreachable.
 *   3. A receiver whose queue is full: the kernel drops the overflow, and nobody is told.
 *
 * In the lab box:  java /labs/net/src/demo/java/sfz/net/l06/demo/Silence.java
 *                  then: nstat -az UdpRcvbufErrors   (Linux counts the drops from part 3)
 * On your Mac:     ./gradlew :net:demo -Pmain=sfz.net.l06.demo.Silence   (from the labs folder)
 */
public class Silence {
    public static void main(String[] args) throws Exception {
        InetAddress lo = InetAddress.getLoopbackAddress();
        byte[] auth = "AUTH 4242".getBytes(StandardCharsets.UTF_8);
        int closedPort = freePort(lo);                          // free, so nothing listens there

        // 1. unconnected: the kernel gets the ICMP error, but has no socket it could tell
        try (DatagramSocket s = new DatagramSocket()) {
            s.send(new DatagramPacket(auth, auth.length, new InetSocketAddress(lo, closedPort)));
            System.out.println("1. send() to closed port " + closedPort + " returned normally");
            s.setSoTimeout(1_000);
            long t = System.nanoTime();
            try {
                s.receive(new DatagramPacket(new byte[100], 100));
            } catch (SocketTimeoutException e) {
                System.out.printf("   receive(): %s after %d ms%n", e.getMessage(), (System.nanoTime() - t) / 1_000_000);
            }
        }

        // 2. connected: the socket now has exactly one peer, so the ICMP error can be reported to it
        try (DatagramChannel ch = DatagramChannel.open()) {
            ch.connect(new InetSocketAddress(lo, closedPort));
            int n = ch.write(ByteBuffer.wrap(auth));
            System.out.println("2. connected write() sent " + n + " bytes");
            try {
                ch.read(ByteBuffer.allocate(100));
            } catch (PortUnreachableException e) {
                System.out.println("   read(): PortUnreachableException, the ICMP error reached us");
            }
        }

        // 3. a receiver with a 16 KB queue that is too busy to read while 2,000 datagrams arrive
        try (DatagramSocket receiver = new DatagramSocket(null);
             DatagramSocket sender = new DatagramSocket()) {
            receiver.setReceiveBufferSize(16 * 1024);
            receiver.bind(new InetSocketAddress(lo, 0));
            byte[] payment = new byte[200];
            int sent = 0;
            for (int i = 0; i < 2_000; i++) {
                sender.send(new DatagramPacket(payment, payment.length, receiver.getLocalSocketAddress()));
                sent++;                                         // every send() "succeeded"
            }
            receiver.setSoTimeout(200);
            int received = 0;
            try {
                while (true) {
                    receiver.receive(new DatagramPacket(new byte[1024], 1024));
                    received++;
                }
            } catch (SocketTimeoutException done) {
                // the queue is empty
            }
            System.out.printf("3. sent %d datagrams, received %d, lost %d without a word%n", sent, received, sent - received);
        }
    }

    static int freePort(InetAddress lo) throws Exception {
        try (DatagramSocket probe = new DatagramSocket(new InetSocketAddress(lo, 0))) {
            return probe.getLocalPort();
        }
    }
}
