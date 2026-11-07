package sfz.net.l11

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.net.l11.Frame.Data
import sfz.net.l11.Frame.Headers
import sfz.net.l11.Frame.Settings
import sfz.net.l11.Frame.WindowUpdate
import sfz.net.support.Hex
import sfz.net.support.Tcp

/** One real HTTP/2 connection: curl 8.5 asking H2Server.java for three URLs at once (see the capture files). */
class Http2CodecTest {
    private val client by lazy { Tcp.stream(Hex.resourceFrames("sfz/net/l11/h2-client.txt")) }
    private val server by lazy { Tcp.stream(Hex.resourceFrames("sfz/net/l11/h2-server.txt")) }

    @Test
    fun `the client starts with the preface, its SETTINGS and a bigger connection window`() {
        val frames = Http2Codec.decode(client)
        assertThat(frames.take(2)).containsExactly(
            Settings(ack = false, values = listOf(3 to 100L, 4 to 10_485_760L, 2 to 0L)),
            WindowUpdate(0, 1_048_510_465L),
        )
    }

    @Test
    fun `three requests are three HEADERS frames on streams 1, 3 and 5`() {
        val headers = Http2Codec.decode(client).filterIsInstance<Headers>()
        assertThat(headers.map { it.streamId }).containsExactly(1, 3, 5)
        assertThat(headers).allMatch { it.endStream && it.endHeaders }
        assertThat(headers.map { it.block.size }).`as`("HPACK: repeated headers shrink to one-byte indexes").containsExactly(36, 12, 12)
        assertThat(headers.map { it.block.take(2) }).`as`("0x82 :method GET, 0x86 :scheme http").allMatch { it == listOf(0x82, 0x86) }
    }

    @Test
    fun `the last client frame acknowledges the server's SETTINGS`() {
        assertThat(Http2Codec.decode(client).last()).isEqualTo(Settings(ack = true, values = emptyList()))
    }

    @Test
    fun `the answers interleave on one connection, in the order they finished`() {
        val frames = Http2Codec.decode(server)
        assertThat(frames.take(2)).containsExactly(Settings(false, listOf(3 to 100L)), Settings(true, emptyList()))
        val answers = frames.drop(2)
        assertThat(answers.map { it::class.simpleName + "[" + it.streamId + "]" })
            .containsExactly("Headers[1]", "Data[1]", "Headers[5]", "Data[5]", "Headers[3]", "Data[3]")
        assertThat(answers.filterIsInstance<Data>()).allMatch { it.endStream && it.text == "hello from stream ${it.streamId}\n" }
        val status = answers.filterIsInstance<Headers>().first()
        assertThat(status.block.first()).`as`("0x88: static table entry 8, :status 200").isEqualTo(0x88)
        assertThat(status.endStream).`as`("the DATA frame ends the stream").isFalse()
    }

    @Test
    fun `a frame cut off by the end of a segment is an error, not a short frame`() {
        val first = Tcp.payload(Hex.resourceFrames("sfz/net/l11/h2-client.txt")[0])
        assertThat(Http2Codec.decode(first)).hasSize(2)
        assertThatThrownBy { Http2Codec.decode(first.copyOf(first.size - 1)) }.isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `padding and the reserved bit are stripped`() {
        // DATA on stream 7 with the reserved bit set, PADDED and END_STREAM: pad length 3, "ok", 3 zero bytes
        val bytes = byteArrayOf(0, 0, 6, 0, 0x09, 0x80.toByte(), 0, 0, 7, 3, 'o'.code.toByte(), 'k'.code.toByte(), 0, 0, 0)
        assertThat(Http2Codec.decode(bytes)).containsExactly(Data(7, true, "ok"))
    }

    @Test
    fun `header writes what decode reads`() {
        val h = Http2Codec.header(length = 20, type = 0, flags = 1, streamId = 5)
        assertThat(Hex.format(h)).isEqualTo("000014000100000005")
        val frame = h + "hello from stream 5\n".toByteArray()
        assertThat(Http2Codec.decode(frame)).containsExactly(Data(5, true, "hello from stream 5\n"))
    }
}
