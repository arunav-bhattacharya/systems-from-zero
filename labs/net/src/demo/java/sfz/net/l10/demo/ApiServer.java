package sfz.net.l10.demo;

import com.sun.net.httpserver.HttpsConfigurator;
import com.sun.net.httpserver.HttpsExchange;
import com.sun.net.httpserver.HttpsParameters;
import com.sun.net.httpserver.HttpsServer;
import java.io.ByteArrayInputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyFactory;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.cert.Certificate;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.Base64;
import java.util.List;
import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLParameters;
import javax.net.ssl.SSLPeerUnverifiedException;
import javax.net.ssl.SSLSession;
import javax.net.ssl.TrustManagerFactory;

/**
 * The api.pay.test server for lesson 10: HTTPS with the JDK's own TLS stack, and optionally mTLS.
 *
 * It reads the files that env/net/pki.sh writes: it presents the certificate chain in `api-chain.pem`
 * (or another file you name), proves it holds `api.key`, and with --mtls asks every client for a
 * certificate signed under `root.pem`. Each request is answered with one line and logged with the
 * TLS version, the cipher suite and the client certificate, if any.
 *
 * In the lab box:
 *   bash /labs/env/net/pki.sh /tmp/pki
 *   java /labs/net/src/demo/java/sfz/net/l10/demo/ApiServer.java /tmp/pki &
 *   java /labs/net/src/demo/java/sfz/net/l10/demo/ApiServer.java /tmp/pki --mtls &
 *   java /labs/net/src/demo/java/sfz/net/l10/demo/ApiServer.java /tmp/pki --chain api.pem &   (forgets the intermediate)
 * On your Mac: ./gradlew :net:demo -Pmain=sfz.net.l10.demo.ApiServer -Pargs='/tmp/pki'
 */
public class ApiServer {

    public static void main(String[] args) throws Exception {
        Path dir = Path.of(args.length > 0 ? args[0] : "/tmp/pki");
        List<String> opts = List.of(args);
        boolean mtls = opts.contains("--mtls");
        int port = intOpt(opts, "--port", 8443);
        String chainFile = strOpt(opts, "--chain", "api-chain.pem");

        // Our identity: the certificate chain we send, and the private key that matches the first one.
        KeyStore identity = KeyStore.getInstance("PKCS12");
        identity.load(null, null);
        identity.setKeyEntry("api", readKey(dir.resolve("api.key")), new char[0],
                readCerts(dir.resolve(chainFile)).toArray(new Certificate[0]));
        KeyManagerFactory kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
        kmf.init(identity, new char[0]);

        // Who we trust to vouch for clients (only used with --mtls).
        TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        tmf.init(trustStore(dir.resolve("root.pem")));

        SSLContext tls = SSLContext.getInstance("TLS");
        tls.init(kmf.getKeyManagers(), tmf.getTrustManagers(), null);

        HttpsServer server = HttpsServer.create(new InetSocketAddress(port), 50);
        server.setHttpsConfigurator(new HttpsConfigurator(tls) {
            @Override
            public void configure(HttpsParameters params) {
                SSLParameters p = tls.getDefaultSSLParameters();
                p.setNeedClientAuth(mtls);                  // mTLS: no client certificate, no handshake
                params.setSSLParameters(p);
            }
        });
        server.createContext("/", exchange -> {
            SSLSession s = ((HttpsExchange) exchange).getSSLSession();
            String client = "no client certificate";
            try {
                client = "client " + ((X509Certificate) s.getPeerCertificates()[0]).getSubjectX500Principal().getName();
            } catch (SSLPeerUnverifiedException e) {
                // a plain TLS client: nothing to show
            }
            System.out.printf("%s %s  %s %s  %s%n", exchange.getRequestMethod(), exchange.getRequestURI(),
                    s.getProtocol(), s.getCipherSuite(), client);
            byte[] body = ("hello from api.pay.test, " + client + "\n").getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        server.start();
        System.out.printf("api.pay.test listening on :%d with %s%s%n", port, chainFile, mtls ? ", client certificates required" : "");
    }

    static PrivateKey readKey(Path pem) throws Exception {
        String b64 = Files.readString(pem).replaceAll("-----[A-Z ]+-----", "").replaceAll("\\s", "");
        return KeyFactory.getInstance("EC").generatePrivate(new PKCS8EncodedKeySpec(Base64.getDecoder().decode(b64)));
    }

    static List<X509Certificate> readCerts(Path pem) throws Exception {
        CertificateFactory cf = CertificateFactory.getInstance("X.509");
        return cf.generateCertificates(new ByteArrayInputStream(Files.readAllBytes(pem))).stream()
                .map(c -> (X509Certificate) c).toList();
    }

    static KeyStore trustStore(Path pem) throws Exception {
        KeyStore ks = KeyStore.getInstance("PKCS12");
        ks.load(null, null);
        int i = 0;
        for (X509Certificate c : readCerts(pem)) ks.setCertificateEntry("ca" + i++, c);
        return ks;
    }

    static int intOpt(List<String> opts, String name, int dflt) {
        int i = opts.indexOf(name);
        return i >= 0 ? Integer.parseInt(opts.get(i + 1)) : dflt;
    }

    static String strOpt(List<String> opts, String name, String dflt) {
        int i = opts.indexOf(name);
        return i >= 0 ? opts.get(i + 1) : dflt;
    }
}
