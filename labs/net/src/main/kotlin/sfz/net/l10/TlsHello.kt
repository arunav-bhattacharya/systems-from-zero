package sfz.net.l10

/** One entry of the key_share extension: a group and the length of the public key sent for it. */
data class KeyShare(val group: Int, val length: Int)

/**
 * What a client offers in its first message, read from the bytes that cross the network in the clear.
 * Every number is the raw wire value; [TlsNames] turns them into names.
 */
data class ClientHello(
    /** The old version field: 0x0303 (TLS 1.2) in every TLS 1.3 ClientHello. */
    val legacyVersion: Int,
    /** Cipher suites in the client's order of preference. */
    val cipherSuites: List<Int>,
    /** The host name from the server_name extension (SNI), or null if the client sent none. */
    val serverName: String?,
    /** Application protocols offered with ALPN, for example `["h2", "http/1.1"]`. */
    val alpn: List<String>,
    /** The versions from supported_versions: this is where TLS 1.3 (0x0304) is offered. */
    val supportedVersions: List<Int>,
    /** Every key exchange group the client accepts, in its order of preference. */
    val supportedGroups: List<Int>,
    /** The groups the client already sent a public key for, and how long each key is. */
    val keyShares: List<KeyShare>,
)

/** What the server chose. */
data class ServerHello(val cipherSuite: Int, val selectedVersion: Int, val keyShare: KeyShare?)

/**
 * Reads the first two messages of a TLS 1.3 handshake. Both arrive in one TLS record of type 22
 * (handshake), which may have been cut across several TCP segments on the way: put the segments
 * back together before you call these.
 *
 * The record and the message inside it:
 * ```
 * record header   content type (1) = 22, legacy record version (2), length (2)
 * handshake       msg type (1): 1 ClientHello, 2 ServerHello; length (3)
 * ClientHello     legacy_version (2), random (32), session id (1-byte length + bytes),
 *                 cipher suites (2-byte length + 2 bytes each), compression methods (1-byte length + bytes),
 *                 extensions (2-byte length, then each: type (2), length (2), data)
 * ServerHello     legacy_version (2), random (32), session id (1-byte length + bytes),
 *                 cipher suite (2), compression method (1), extensions (as above)
 * ```
 * The extensions this lab reads, and their data:
 * ```
 * server_name (0)          list length (2), then entries: name type (1) = 0, length (2), the host name
 * supported_groups (10)    list length (2), then 2 bytes per group
 * ALPN (16)                list length (2), then entries: length (1), the protocol name
 * supported_versions (43)  ClientHello: list length (1), then 2 bytes per version.  ServerHello: 2 bytes.
 * key_share (51)           ClientHello: list length (2), then entries: group (2), key length (2), key.
 *                          ServerHello: one entry, group (2), key length (2), key.
 * ```
 * Extensions you don't know, skip by their length. All numbers are big-endian.
 */
object TlsHello {

    /**
     * Parses the ClientHello at the start of [record]. Throws IllegalArgumentException if [record] is
     * shorter than its record header says (a ClientHello still missing its second segment), or if
     * it isn't a handshake record holding a ClientHello.
     */
    fun parseClientHello(record: ByteArray): ClientHello {
        TODO("record header, handshake header, fixed fields, then walk the extensions")
    }

    /**
     * Parses the ServerHello at the start of [record]. Bytes after the first record (the server's
     * next records) are ignored. [ServerHello.keyShare] is null if the server sent none.
     */
    fun parseServerHello(record: ByteArray): ServerHello {
        TODO("the same walk: the chosen suite, supported_versions and key_share")
    }
}
