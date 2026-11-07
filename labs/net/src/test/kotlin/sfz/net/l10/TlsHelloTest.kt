package sfz.net.l10

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.net.support.Hex
import sfz.net.support.Tcp

/**
 * Real hellos from the lab network: curl 8.5 (OpenSSL 3.0) and the JDK 25 HttpClient, each talking
 * to the JDK 25 server in ApiServer.java for api.pay.test. See the comments in the capture files.
 */
class TlsHelloTest {
    private fun record(name: String) = Tcp.stream(Hex.resourceFrames("sfz/net/l10/$name.txt"))

    private val curl by lazy { TlsHello.parseClientHello(record("curl-client-hello")) }
    private val jdk by lazy { TlsHello.parseClientHello(record("jdk-client-hello")) }

    @Test
    fun `TLS 1_3 is offered in supported_versions, while the old version field says TLS 1_2`() {
        for (hello in listOf(curl, jdk)) {
            assertThat(hello.legacyVersion).`as`("legacy_version").isEqualTo(0x0303)
            assertThat(hello.supportedVersions).containsExactly(0x0304, 0x0303)
        }
    }

    @Test
    fun `the host name and the application protocols travel in the clear`() {
        for (hello in listOf(curl, jdk)) {
            assertThat(hello.serverName).isEqualTo("api.pay.test")
            assertThat(hello.alpn).containsExactly("h2", "http/1.1")
        }
    }

    @Test
    fun `curl offers the TLS 1_3 suites first and one classical key share`() {
        assertThat(curl.cipherSuites).hasSize(31)
        assertThat(curl.cipherSuites.take(3)).`as`("TLS 1.3 suites first").containsExactly(0x1302, 0x1303, 0x1301)
        assertThat(curl.supportedGroups.take(3).map(TlsNames::group)).containsExactly("x25519", "secp256r1", "x448")
        assertThat(curl.keyShares).containsExactly(KeyShare(0x001D, 32))
    }

    @Test
    fun `the JDK sends a hybrid post-quantum key share first, and a classical one as a fallback`() {
        assertThat(jdk.supportedGroups.first()).isEqualTo(0x11EC)
        assertThat(jdk.keyShares.map { TlsNames.group(it.group) to it.length })
            .`as`("ML-KEM-768's 1,184-byte key plus X25519's 32 bytes, then X25519 alone")
            .containsExactly("X25519MLKEM768" to 1216, "x25519" to 32)
    }

    @Test
    fun `the JDK's ClientHello needs both of its TCP segments`() {
        val segments = Hex.resourceFrames("sfz/net/l10/jdk-client-hello.txt").map(Tcp::payload)
        assertThat(segments.map { it.size }).containsExactly(1448, 166)
        assertThatThrownBy { TlsHello.parseClientHello(segments[0]) }
            .`as`("the record header promises 1,609 bytes; the first segment holds 1,443 of them")
            .isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `the server picks one suite and one group, and sends its own share`() {
        val toCurl = TlsHello.parseServerHello(record("curl-server-hello"))
        val toJdk = TlsHello.parseServerHello(record("jdk-server-hello"))
        assertThat(toCurl).isEqualTo(ServerHello(0x1302, 0x0304, KeyShare(0x001D, 32)))
        assertThat(toJdk).`as`("an ML-KEM ciphertext of 1,088 bytes plus X25519's 32")
            .isEqualTo(ServerHello(0x1302, 0x0304, KeyShare(0x11EC, 1120)))
        assertThat(jdk.keyShares.map { it.group }).`as`("a share the client sent, so no extra round trip").contains(toJdk.keyShare!!.group)
    }

    @Test
    fun `bytes after the first record are ignored`() {
        val bytes = record("jdk-server-hello")
        assertThat(bytes.size).isEqualTo(1215)
        assertThat(TlsHello.parseServerHello(bytes.copyOf(5 + 1210)).keyShare).isEqualTo(KeyShare(0x11EC, 1120))
    }
}
