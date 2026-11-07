package sfz.os.l11.demo;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.nio.channels.ServerSocketChannel;
import java.nio.channels.SocketChannel;

/**
 * One echo server, written three ways: whatever a connection sends, the server sends back.
 *   threads   a platform thread per connection, blocked in read() while the client is quiet
 *   virtual   the same code, on a virtual thread per connection
 *   nio       one thread and a Selector (epoll on Linux) for every connection
 * Arguments: MODE (threads, virtual or nio), PORT (default 9000), SECONDS to run (default 60).
 */
public class EchoServers {
    public static void main(String[] args) throws Exception {
        String mode = args.length > 0 ? args[0] : "nio";
        int port = args.length > 1 ? Integer.parseInt(args[1]) : 9000;
        int seconds = args.length > 2 ? Integer.parseInt(args[2]) : 60;
        Thread.ofPlatform().daemon().start(() -> {               // stop by itself, so a forgotten server goes away
            try { Thread.sleep(seconds * 1000L); } catch (InterruptedException e) { return; }
            System.exit(0);
        });
        System.out.printf("pid %d: %s echo server on port %d%n", ProcessHandle.current().pid(), mode, port);
        if (mode.equals("nio")) nio(port);
        else blocking(port, mode.equals("virtual"));
    }

    // thread per connection: simple code, and each quiet connection parks one thread in read()
    static void blocking(int port, boolean virtual) throws Exception {
        Thread.Builder builder = virtual ? Thread.ofVirtual() : Thread.ofPlatform();
        try (ServerSocket server = new ServerSocket()) {
            server.bind(new InetSocketAddress(port), 4096);
            while (true) {
                Socket s = server.accept();
                builder.start(() -> echo(s));
            }
        }
    }

    static void echo(Socket s) {
        byte[] buf = new byte[512];
        try (s) {
            InputStream in = s.getInputStream();
            OutputStream out = s.getOutputStream();
            int n;
            while ((n = in.read(buf)) > 0) {                   // blocks until the client sends something
                out.write(buf, 0, n);
            }
        } catch (Exception e) {
            // client went away
        }
    }

    // one thread: ask the kernel which sockets are ready, and only touch those
    static void nio(int port) throws Exception {
        Selector selector = Selector.open();                     // epoll_create1 on Linux
        ServerSocketChannel server = ServerSocketChannel.open();
        server.bind(new InetSocketAddress(port), 4096);
        server.configureBlocking(false);
        server.register(selector, SelectionKey.OP_ACCEPT);       // epoll_ctl(ADD)
        ByteBuffer buf = ByteBuffer.allocateDirect(4096);
        while (true) {
            selector.select();                                   // epoll_pwait: sleep until something is ready
            var it = selector.selectedKeys().iterator();
            while (it.hasNext()) {
                SelectionKey key = it.next();
                it.remove();
                if (key.isAcceptable()) {
                    SocketChannel c = server.accept();
                    c.configureBlocking(false);
                    c.register(selector, SelectionKey.OP_READ);
                } else if (key.isReadable()) {
                    SocketChannel c = (SocketChannel) key.channel();
                    buf.clear();
                    int n = c.read(buf);                         // ready, so this never blocks
                    if (n < 0) { key.cancel(); c.close(); continue; }
                    buf.flip();
                    while (buf.hasRemaining()) c.write(buf);     // small echoes fit the send buffer
                }
            }
        }
    }
}
