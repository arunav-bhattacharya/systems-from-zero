package sfz.net.l10

/**
 * Names for the numbers in a TLS hello, from the IANA TLS registries. Finished: use it in your own
 * output and in assertion messages, for example `TlsNames.group(0x11EC)` is "X25519MLKEM768".
 */
object TlsNames {
    /** Key exchange groups (the supported_groups and key_share extensions). */
    val groups = mapOf(
        0x0017 to "secp256r1", 0x0018 to "secp384r1", 0x0019 to "secp521r1",
        0x001D to "x25519", 0x001E to "x448",
        0x0100 to "ffdhe2048", 0x0101 to "ffdhe3072", 0x0102 to "ffdhe4096", 0x0103 to "ffdhe6144", 0x0104 to "ffdhe8192",
        0x11EB to "SecP256r1MLKEM768",
        0x11EC to "X25519MLKEM768",   // hybrid post-quantum key exchange, RFC 10024
    )

    /** The five TLS 1.3 cipher suites, and two TLS 1.2 ones you will see offered next to them. */
    val cipherSuites = mapOf(
        0x1301 to "TLS_AES_128_GCM_SHA256", 0x1302 to "TLS_AES_256_GCM_SHA384", 0x1303 to "TLS_CHACHA20_POLY1305_SHA256",
        0x1304 to "TLS_AES_128_CCM_SHA256", 0x1305 to "TLS_AES_128_CCM_8_SHA256",
        0xC02B to "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256", 0xC02F to "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    )

    /** Protocol versions as they appear on the wire: TLS 1.3 is 0x0304. */
    val versions = mapOf(0x0301 to "TLS 1.0", 0x0302 to "TLS 1.1", 0x0303 to "TLS 1.2", 0x0304 to "TLS 1.3")

    /** Extension types this lab reads, and a few more that show up in real hellos. */
    object Ext {
        const val SERVER_NAME = 0
        const val SUPPORTED_GROUPS = 10
        const val SIGNATURE_ALGORITHMS = 13
        const val ALPN = 16
        const val PRE_SHARED_KEY = 41
        const val EARLY_DATA = 42
        const val SUPPORTED_VERSIONS = 43
        const val PSK_KEY_EXCHANGE_MODES = 45
        const val KEY_SHARE = 51
        const val ENCRYPTED_CLIENT_HELLO = 0xFE0D
    }

    fun group(code: Int): String = groups[code] ?: "0x%04x".format(code)
    fun cipherSuite(code: Int): String = cipherSuites[code] ?: "0x%04x".format(code)
    fun version(code: Int): String = versions[code] ?: "0x%04x".format(code)
}
