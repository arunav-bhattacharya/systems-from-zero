package sfz.net.support

/**
 * Turns hex text into bytes, for tests that feed real captured frames to your parser.
 *
 * Two formats work:
 * - plain hex, any spacing: `"ffff ffff ffff 0800"`
 * - a `tcpdump -XX` dump, as the lab box prints it: lines like
 *   `0x0010:  007e 43d4 4000 4006 cae1 ac14 0002 6814  .~C.@.@.......h.`
 *   (the offset and the ASCII column on the right are ignored).
 *
 * Captured frames live under `src/test/resources/sfz/net/lNN/`. In those files, lines that start
 * with `#` are comments and the tcpdump summary line is skipped, so you can paste a capture as is.
 */
object Hex {
    private val dumpLine = Regex("""^\s*0x[0-9a-fA-F]+:\s+(.*)$""")

    /** Plain hex: every pair of hex digits is one byte; whitespace is ignored. */
    fun parse(text: String): ByteArray {
        val digits = text.filterNot(Char::isWhitespace)
        require(digits.length % 2 == 0) { "odd number of hex digits" }
        return ByteArray(digits.length / 2) { i -> digits.substring(2 * i, 2 * i + 2).toInt(16).toByte() }
    }

    /** The bytes of a `tcpdump -XX` dump (one frame). */
    fun fromTcpdump(text: String): ByteArray {
        val hex = StringBuilder()
        for (line in text.lineSequence()) {
            val m = dumpLine.find(line) ?: continue
            // the hex groups end where the ASCII column starts: two or more spaces
            hex.append(m.groupValues[1].split(Regex("""\s{2,}""")).first())
        }
        return parse(hex.toString())
    }

    /**
     * Every frame of a `tcpdump -XX` dump that holds several, in order. A new frame starts at each
     * line whose offset is `0x0000`. Use it for a whole conversation in one file (lesson 7 replays a
     * TCP connection this way).
     */
    fun framesFromTcpdump(text: String): List<ByteArray> {
        val frames = mutableListOf<StringBuilder>()
        for (line in text.lineSequence()) {
            val m = dumpLine.find(line) ?: continue
            if (line.trimStart().startsWith("0x0000:") || frames.isEmpty()) frames += StringBuilder()
            frames.last().append(m.groupValues[1].split(Regex("""\s{2,}""")).first())
        }
        return frames.map { parse(it.toString()) }
    }

    /** The frames of a multi-frame capture in the test resources, for example `"sfz/net/l07/echo.txt"`. */
    fun resourceFrames(path: String): List<ByteArray> {
        val text = Hex::class.java.classLoader.getResource(path)?.readText()
            ?: error("test resource not found: $path")
        return framesFromTcpdump(text)
    }

    /** Loads a capture from the test resources, for example `"sfz/net/l01/http-get.txt"`. */
    fun resource(path: String): ByteArray {
        val text = Hex::class.java.classLoader.getResource(path)?.readText()
            ?: error("test resource not found: $path")
        return if (text.lineSequence().any { dumpLine.matches(it) }) {
            fromTcpdump(text)
        } else {
            parse(text.lineSequence().filterNot { it.trimStart().startsWith("#") }.joinToString(""))
        }
    }

    /** Lower-case hex with no spaces, handy in assertion messages. */
    fun format(bytes: ByteArray): String = bytes.joinToString("") { "%02x".format(it) }
}
