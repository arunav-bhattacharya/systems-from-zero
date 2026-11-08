package sfz.cache.l02.demo

import java.io.InputStream
import java.io.OutputStream
import java.net.Socket

/** Speaks RESP to Redis over a plain socket, with no client library, and prints every byte. */
fun main() {
    Socket("localhost", 6379).use { socket ->
        val out = socket.getOutputStream()
        val inp = socket.getInputStream()
        send(out, inp, "PING")
        send(out, inp, "SET", "payment:42", "approved")
        send(out, inp, "GET", "payment:42")
        send(out, inp, "GET", "payment:404")
        send(out, inp, "INCR", "auths:today")
        send(out, inp, "INCR", "payment:42")
        send(out, inp, "HSET", "payment:45", "status", "approved", "amount", "1250")
        send(out, inp, "HGETALL", "payment:45")
        send(out, inp, "HELLO", "3")                    // switch this connection to RESP3
        send(out, inp, "HGETALL", "payment:45")
        send(out, inp, "GET", "payment:404")
    }
}

// a command is an array of bulk strings: *<count>, then $<length> and the bytes of each word
private fun send(out: OutputStream, inp: InputStream, vararg words: String) {
    val cmd = buildString {
        append("*${words.size}\r\n")
        for (w in words) append("$${w.toByteArray().size}\r\n$w\r\n")
    }
    out.write(cmd.toByteArray())
    out.flush()
    // good enough for a demo: on loopback a short reply arrives in one read
    val buf = ByteArray(8192)
    val n = inp.read(buf)
    println("> " + show(cmd, 200))
    println("< " + show(String(buf, 0, n), 90))
}

private fun show(s: String, max: Int): String {
    val visible = s.replace("\r\n", "\\r\\n")
    return if (visible.length <= max) visible else visible.take(max) + "... (${s.length} bytes)"
}
