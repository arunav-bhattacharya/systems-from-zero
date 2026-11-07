package sfz.net.l06.demo;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

/**
 * Three messages sent over UDP and over TCP on 127.0.0.1, then read back. UDP hands the reader three
 * datagrams, one per send. TCP hands it one stream of bytes, with nothing marking where a message ended.
 * Last, a datagram read into a buffer that is too small: the rest of it is gone.
 *
 * In the lab box:  java /labs/net/src/demo/java/sfz/net/l06/demo/Boundaries.java
 * On your Mac:     ./gradlew :net:demo -Pmain=sfz.net.l06.demo.Boundaries   (from the labs folder)
 */
public class Boundaries {
    static final String[] MESSAGES = {"AUTH 1", "AUTH 22", "AUTH 333"};

    public static void main(String[] args) throws Exception {
        InetAddress lo = InetAddress.getLoopbackAddress();

        // UDP: one socket sends three datagrams to another
        try (DatagramSocket receiver = new DatagramSocket(new InetSocketAddress(lo, 0));
             DatagramSocket sender = new DatagramSocket()) {
            for (String m : MESSAGES) {
                byte[] b = m.getBytes(StandardCharsets.UTF_8);
                sender.send(new DatagramPacket(b, b.length, receiver.getLocalSocketAddress()));
            }
            Thread.sleep(100);                                   // all three are waiting in the queue now
            receiver.setSoTimeout(500);
            for (int i = 0; i < MESSAGES.length; i++) {
                DatagramPacket p = new DatagramPacket(new byte[1024], 1024);
                receiver.receive(p);                             // exactly one datagram per receive
                System.out.printf("UDP receive %d: %d bytes \"%s\"%n", i + 1, p.getLength(), new String(p.getData(), 0, p.getLength(), StandardCharsets.UTF_8));
            }
        }

        // TCP: three write() calls on one connection, then the other side reads once
        try (ServerSocket listener = new ServerSocket(0, 1, lo);
             Socket client = new Socket(lo, listener.getLocalPort());
             Socket server = listener.accept()) {
            OutputStream out = client.getOutputStream();
            for (String m : MESSAGES) out.write(m.getBytes(StandardCharsets.UTF_8));
            out.flush();
            Thread.sleep(100);
            InputStream in = server.getInputStream();
            byte[] buf = new byte[1024];
            int n = in.read(buf);                                // whatever has arrived, as one run of bytes
            System.out.printf("TCP read 1:    %d bytes \"%s\"%n", n, new String(buf, 0, n, StandardCharsets.UTF_8));
        }

        // a datagram bigger than the buffer you receive it into
        try (DatagramSocket receiver = new DatagramSocket(new InetSocketAddress(lo, 0));
             DatagramSocket sender = new DatagramSocket()) {
            byte[] b = "AUTH 4242 EUR 100.00".getBytes(StandardCharsets.UTF_8);
            sender.send(new DatagramPacket(b, b.length, receiver.getLocalSocketAddress()));
            DatagramPacket small = new DatagramPacket(new byte[9], 9);
            receiver.setSoTimeout(500);
            receiver.receive(small);
            System.out.printf("UDP into a 9-byte buffer: \"%s\" (sent %d bytes; the other %d are gone)%n",
                new String(small.getData(), 0, small.getLength(), StandardCharsets.UTF_8), b.length, b.length - small.getLength());
        }
    }
}
