package sfz.net.l10.demo;

import java.io.ByteArrayInputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyFactory;
import java.security.KeyStore;
import java.security.cert.Certificate;
import java.security.cert.CertificateFactory;
import java.security.spec.PKCS8EncodedKeySpec;
import java.time.Duration;
import java.util.Base64;
import java.util.List;
import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;

/**
 * One HTTPS request with the JDK's HttpClient, and what the TLS handshake decided: the TLS version and
 * cipher suite, or the exact exception your service would log when the handshake fails.
 *
 *   java Handshake.java https://api.pay.test:8443/ --ca /tmp/pki/root.pem
 *   java Handshake.java https://api.pay.test:8443/ --ca /tmp/pki/root.pem --cert /tmp/pki/checkout-chain.pem --key /tmp/pki/checkout.key
 *   java Handshake.java https://example.com/                     (no --ca: the JDK's own list of trusted roots)
 *
 * --ca replaces the JDK's trust store with one root, the way a service that talks only to a private
 * PKI is set up. --cert and --key give the client a certificate to send when the server asks (mTLS).
 * In the lab box the file lives at /labs/net/src/demo/java/sfz/net/l10/demo/Handshake.java.
 * On your Mac: ./gradlew :net:demo -Pmain=sfz.net.l10.demo.Handshake -Pargs='https://example.com/'
 */
public class Handshake {

    public static void main(String[] args) throws Exception {
        List<String> opts = List.of(args);
        URI uri = URI.create(args.length > 0 ? args[0] : "https://example.com/");
        String ca = opt(opts, "--ca"), cert = opt(opts, "--cert"), key = opt(opts, "--key");

        TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        if (ca == null) {
            tmf.init((KeyStore) null);                         // the JDK's cacerts: about 150 public roots
        } else {
            KeyStore trust = KeyStore.getInstance("PKCS12");
            trust.load(null, null);
            int i = 0;
            for (Certificate c : certs(ca)) trust.setCertificateEntry("ca" + i++, c);
            tmf.init(trust);                                   // trust exactly these roots and nothing else
        }
        KeyManagerFactory kmf = null;
        if (cert != null) {                                    // our own certificate, for servers that ask
            KeyStore id = KeyStore.getInstance("PKCS12");
            id.load(null, null);
            String b64 = Files.readString(Path.of(key)).replaceAll("-----[A-Z ]+-----", "").replaceAll("\\s", "");
            id.setKeyEntry("me", KeyFactory.getInstance("EC").generatePrivate(new PKCS8EncodedKeySpec(Base64.getDecoder().decode(b64))),
                    new char[0], certs(cert).toArray(new Certificate[0]));
            kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
            kmf.init(id, new char[0]);
        }
        SSLContext tls = SSLContext.getInstance("TLS");
        tls.init(kmf == null ? null : kmf.getKeyManagers(), tmf.getTrustManagers(), null);

        HttpClient client = HttpClient.newBuilder().sslContext(tls).connectTimeout(Duration.ofSeconds(5)).build();
        long start = System.nanoTime();
        try {
            HttpResponse<String> r = client.send(HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(10)).build(),
                    HttpResponse.BodyHandlers.ofString());
            long ms = (System.nanoTime() - start) / 1_000_000;
            var session = r.sslSession().orElseThrow();
            System.out.printf("%d %s  %s %s  %d ms%n", r.statusCode(), r.version(), session.getProtocol(), session.getCipherSuite(), ms);
            String body = r.body().strip();
            System.out.println(body.length() > 120 ? body.substring(0, 120) + "..." : body);
        } catch (Exception e) {
            Throwable root = e;                                // the deepest cause names the real problem
            while (root.getCause() != null) root = root.getCause();
            System.out.println("failed: " + e.getClass().getName() + ": " + e.getMessage());
            if (root != e) System.out.println("  root cause: " + root.getClass().getName() + ": " + root.getMessage());
        }
    }

    static List<? extends Certificate> certs(String pem) throws Exception {
        return List.copyOf(CertificateFactory.getInstance("X.509").generateCertificates(new ByteArrayInputStream(Files.readAllBytes(Path.of(pem)))));
    }

    static String opt(List<String> opts, String name) {
        int i = opts.indexOf(name);
        return i >= 0 ? opts.get(i + 1) : null;
    }
}
