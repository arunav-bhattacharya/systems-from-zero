package sfz.net.l10

import java.nio.ByteBuffer

/** One entry of the key_share extension: a group and the length of the public key sent for it. */
data class KeyShare(val group: Int, val length: Int)

/**
 * What a client offers in its first message, read from the bytes that cross the network in the clear.
 * Every number is the raw wire value; [TlsNames] turns them into names.
 */
data class ClientHello(
    val legacyVersion: Int,
    val cipherSuites: List<Int>,
    val serverName: String?,
    val alpn: List<String>,
    val supportedVersions: List<Int>,
    val supportedGroups: List<Int>,
    val keyShares: List<KeyShare>,
)

/** What the server chose. */
data class ServerHello(val cipherSuite: Int, val selectedVersion: Int, val keyShare: KeyShare?)

object TlsHello {
    private const val HANDSHAKE = 22
    private const val CLIENT_HELLO = 1
    private const val SERVER_HELLO = 2

    fun parseClientHello(record: ByteArray): ClientHello {
        val b = handshakeBody(record, CLIENT_HELLO)
        val legacyVersion = u16(b)
        b.position(b.position() + 32)                             // random
        skip8(b)                                                  // legacy session id
        val suites = List(u16(b) / 2) { u16(b) }
        skip8(b)                                                  // compression methods: always [0]
        val ext = extensions(b)

        val sni = ext[TlsNames.Ext.SERVER_NAME]?.let { d ->
            u16(d)                                                // list length
            require(u8(d) == 0) { "only host names exist in server_name" }
            String(bytes(d, u16(d)), Charsets.US_ASCII)
        }
        val alpn = ext[TlsNames.Ext.ALPN]?.let { d ->
            val end = 2 + u16(d)
            buildList { while (d.position() < end) add(String(bytes(d, u8(d)), Charsets.US_ASCII)) }
        } ?: emptyList()
        val versions = ext[TlsNames.Ext.SUPPORTED_VERSIONS]?.let { d -> List(u8(d) / 2) { u16(d) } } ?: emptyList()
        val groups = ext[TlsNames.Ext.SUPPORTED_GROUPS]?.let { d -> List(u16(d) / 2) { u16(d) } } ?: emptyList()
        val shares = ext[TlsNames.Ext.KEY_SHARE]?.let { d ->
            val end = 2 + u16(d)
            buildList { while (d.position() < end) add(keyShare(d)) }
        } ?: emptyList()
        return ClientHello(legacyVersion, suites, sni, alpn, versions, groups, shares)
    }

    fun parseServerHello(record: ByteArray): ServerHello {
        val b = handshakeBody(record, SERVER_HELLO)
        u16(b)                                                    // legacy_version, 0x0303
        b.position(b.position() + 32)                             // random
        skip8(b)                                                  // the client's session id, echoed
        val suite = u16(b)
        u8(b)                                                     // compression method
        val ext = extensions(b)
        val version = ext[TlsNames.Ext.SUPPORTED_VERSIONS]?.let { u16(it) } ?: 0x0303
        val share = ext[TlsNames.Ext.KEY_SHARE]?.let { keyShare(it) }
        return ServerHello(suite, version, share)
    }

    /** Checks the record and handshake headers and returns a buffer over the message body only. */
    private fun handshakeBody(record: ByteArray, type: Int): ByteBuffer {
        require(record.size >= 5) { "not even a record header: ${record.size} bytes" }
        val r = ByteBuffer.wrap(record)
        require(u8(r) == HANDSHAKE) { "not a handshake record" }
        u16(r)                                                    // legacy record version: 0x0301 or 0x0303
        val length = u16(r)
        // the record header promises `length` bytes; a ClientHello cut across segments has fewer
        require(record.size >= 5 + length) { "record is incomplete: header says $length bytes, have ${record.size - 5}" }
        require(u8(r) == type) { "expected handshake message $type" }
        val bodyLength = (u8(r) shl 16) or u16(r)                 // a 3-byte length
        return ByteBuffer.wrap(record, 9, bodyLength).slice()
    }

    /** type -> data of every extension; each data buffer starts at position 0. */
    private fun extensions(b: ByteBuffer): Map<Int, ByteBuffer> {
        if (!b.hasRemaining()) return emptyMap()
        val end = b.position() + 2 + u16(b)
        val out = LinkedHashMap<Int, ByteBuffer>()
        while (b.position() < end) {
            val type = u16(b)
            val len = u16(b)
            out[type] = ByteBuffer.wrap(bytes(b, len))            // unknown types are kept and ignored
        }
        return out
    }

    private fun keyShare(d: ByteBuffer): KeyShare {
        val group = u16(d)
        val len = u16(d)
        d.position(d.position() + len)                            // the public key itself
        return KeyShare(group, len)
    }

    private fun u8(b: ByteBuffer) = b.get().toInt() and 0xFF
    private fun u16(b: ByteBuffer) = b.getShort().toInt() and 0xFFFF
    private fun skip8(b: ByteBuffer) {
        val n = u8(b)                                             // read the length before taking the position
        b.position(b.position() + n)
    }
    private fun bytes(b: ByteBuffer, n: Int) = ByteArray(n).also { b.get(it) }
}
