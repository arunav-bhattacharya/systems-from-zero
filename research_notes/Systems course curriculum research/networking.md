# Computer Networking track: research notes (state as of 2026-11-07)

Audience: senior Java/Kotlin backend engineer, macOS on Apple Silicon, Docker Desktop / OrbStack / Colima. Free, local labs only.

Source conventions used below:
- `[local check]` = I ran the command on this research machine (macOS 27.0.1, build 26A434, arm64, 2026-11-07) and observed the output myself. Docker was **not** installed on this machine, so container labs were not smoke-tested.
- RFC publication dates and "Obsoletes/Updates" headers were pulled straight from the rfc-editor.org text of each RFC on 2026-11-07.

---

## 1. Teaching order and scope (what to teach, in what order, how deep)

### Takeaway
Teach bottom-up through the TCP/IP stack (link, IP, transport, application). Use OSI only as vocabulary ("L4 vs L7 load balancer"). Put the most time into TCP behaviour, DNS, TLS, HTTP versions, and the application-side concerns (timeouts, pooling, retries), because that is where a backend engineer's production incidents come from. Link layer, routing protocols and IPv6 internals get "enough to debug" depth.

### Cited Findings

**Layering**
- Kurose & Ross, *Computer Networking: A Top-Down Approach*, is now in its **9th edition** (companion site title "Computer Networking 9E"). It also has free interactive problems, including subnetting and TCP exercises — [Kurose/Ross companion](https://gaia.cs.umass.edu/kurose_ross/index.php), [interactive problems](https://gaia.cs.umass.edu/kurose_ross/interactive/).
- HTTP is now specified as one shared set of *semantics* (RFC 9110) plus separate wire mappings: HTTP/1.1 (RFC 9112), HTTP/2 (RFC 9113) and HTTP/3 (RFC 9114). That makes "semantics vs wire format" a clean layering lesson — [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html), [RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html), [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html), [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html).
- QUIC (RFC 9000) runs over UDP and builds in what used to sit in separate layers: reliability, stream multiplexing, congestion control (RFC 9002) and TLS 1.3 (RFC 9001). The strict layer diagram does not fit it cleanly — [RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html), [RFC 9001](https://www.rfc-editor.org/rfc/rfc9001.html), [RFC 9002](https://www.rfc-editor.org/rfc/rfc9002.html).

**Link layer / ARP / MAC**
- ARP (RFC 826) maps IPv4 addresses to link-layer (MAC) addresses on the local segment — [RFC 826](https://www.rfc-editor.org/rfc/rfc826.html).
- IPv6 has no ARP. It uses Neighbor Discovery (NDP). On macOS, `ndp -an` shows the neighbour cache, the way `arp -a` does for IPv4. Both binaries exist at /usr/sbin — [local check].

**IP addressing / CIDR / NAT**
- CIDR (RFC 4632, Aug 2006, obsoletes RFC 1519) is the current addressing and aggregation model — [RFC 4632](https://www.rfc-editor.org/rfc/rfc4632.html).
- Private IPv4 ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 — [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html). Carrier-grade NAT shared space: "The Shared Address Space address range is 100.64.0.0/10" — [RFC 6598](https://www.rfc-editor.org/rfc/rfc6598.html).
- Free subnetting drills: [subnetting.net](https://subnetting.net/), plus the Kurose/Ross interactive problems above.

**IPv6 essentials**
- IPv6 spec: RFC 8200 (July 2017, obsoletes RFC 2460). Addressing architecture: RFC 4291 (Feb 2006) — [RFC 8200](https://www.rfc-editor.org/rfc/rfc8200.html), [RFC 4291](https://www.rfc-editor.org/rfc/rfc4291.html).
- Happy Eyeballs v2 (RFC 8305, Dec 2017, obsoletes RFC 6555) defines how dual-stack clients race IPv6 and IPv4 — [RFC 8305](https://www.rfc-editor.org/rfc/rfc8305.html).
- Adoption: "Globally, 29% of IPv6-capable ('dual-stack') requests for content were made over IPv6, up a percentage point from 28% in 2024." India led at 67% (Cloudflare data, Jan 1 to Dec 2, 2025) — [Cloudflare Radar 2025 Year in Review](https://blog.cloudflare.com/radar-2025-year-in-review/).
- OrbStack disables IPv6 for containers by default ("For containers, IPv6 is disabled by default for compatibility"). Turn it on with the "Enable IPv6" setting or `"ipv6": true` — [OrbStack networking docs](https://docs.orbstack.dev/docker/network).

**UDP / TCP / TCP internals**
- UDP: RFC 768 — [RFC 768](https://www.rfc-editor.org/rfc/rfc768.html).
- TCP: **RFC 9293 (Aug 2022)** is the consolidated TCP spec. It obsoletes RFC 793, 879, 2873, 6093, 6429, 6528 (and more on its continuation line) and updates RFC 1011, 1122, 5961 — [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html).
- RFC 9293's ISN generator uses a clock that "cycles approximately every 4.55 hours, which is much longer than the MSL". "For this specification the MSL is taken to be 2 minutes." "When a connection is closed actively, it MUST linger in the TIME-WAIT state for a time 2xMSL (MUST-13)" — [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html).
- RFC 9293 has dedicated sections on the Nagle algorithm (3.7.4, plus Appendix A.3 "Nagle Modification"). The original Nagle RFC is RFC 896 — [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html), [RFC 896](https://www.rfc-editor.org/rfc/rfc896.html).
- Delayed ACK: "the delay MUST be less than 0.5 seconds, and in a stream of full-sized segments there SHOULD be an ACK for at least every second segment" — [RFC 1122 §4.2.3.2](https://www.rfc-editor.org/rfc/rfc1122.html).
- TCP keepalive: the idle interval "MUST be configurable (MUST-27) and MUST default to no less than two hours (MUST-28)" — [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html).
- Retransmission timer: initial RTO should be 1 second ("the sender SHOULD set RTO <- 1 second"), down from the older 3 s — [RFC 6298](https://www.rfc-editor.org/rfc/rfc6298.html). Window scaling and timestamps: RFC 7323 — [RFC 7323](https://www.rfc-editor.org/rfc/rfc7323.html).
- Congestion control baseline (slow start, congestion avoidance, fast retransmit/recovery): RFC 5681 (Sept 2009) — [RFC 5681](https://www.rfc-editor.org/rfc/rfc5681.html).
- **CUBIC: RFC 9438 (Aug 2023)**, obsoletes RFC 8312, updates RFC 5681. "CUBIC has been adopted as the default TCP congestion control algorithm by the Linux, Windows, and Apple stacks" — [RFC 9438](https://www.rfc-editor.org/rfc/rfc9438.html).
- BBR is model-based (bottleneck bandwidth and RTT). The IETF draft specifies BBRv3 — [draft-ietf-ccwg-bbr](https://datatracker.ietf.org/doc/draft-ietf-ccwg-bbr/). Status details are in section 2.
- Head-of-line blocking. RFC 9113 says HTTP/1.x "still suffers from application-layer head-of-line blocking" and that HTTP/2 does not fix TCP's: "Note, however, that TCP head-of-line blocking is not addressed by this protocol" — [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html). QUIC: "One of the benefits of QUIC is avoidance of head-of-line blocking across multiple streams. When a packet loss occurs, only streams with data in that packet are blocked" — [RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html). HTTP/3 header compression (QPACK) gives the encoder "some control over how much head-of-line blocking can be caused by compression" — [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html), [RFC 9204](https://www.rfc-editor.org/rfc/rfc9204.html).
- Good readable references: [HPBN "Building Blocks of TCP"](https://hpbn.co/building-blocks-of-tcp/) (handshake, slow start, flow control, BDP, HOL) and [HPBN HTTP/2](https://hpbn.co/http2/). Julia Evans has a concrete Nagle + delayed-ACK latency story — [jvns.ca "Why you should understand (a little) about TCP"](https://jvns.ca/blog/2015/11/21/why-you-should-understand-a-little-about-tcp/).

**Sockets API**
- [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/) is the canonical free walkthrough of socket/bind/listen/accept/connect/send/recv, in C.
- Java side: [java.net.Socket (JDK 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/Socket.html), [SocketChannel (NIO)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/nio/channels/SocketChannel.html), [StandardSocketOptions](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/StandardSocketOptions.html) (TCP_NODELAY, SO_KEEPALIVE, SO_REUSEADDR, SO_LINGER, SO_RCVBUF/SNDBUF), and [jdk.net.ExtendedSocketOptions](https://docs.oracle.com/en/java/javase/25/docs/api/jdk.net/jdk/net/ExtendedSocketOptions.html) (TCP_KEEPIDLE/KEEPINTERVAL/KEEPCOUNT). Event-loop background: [Julia Evans on select/poll/epoll](https://jvns.ca/blog/2017/06/03/async-io-on-linux--select--poll--and-epoll/). Virtual threads make blocking-socket code scale again: [JEP 444](https://openjdk.org/jeps/444).

**DNS**
- Core: RFC 1034/1035 (Nov 1987). Negative caching: RFC 2308 (Mar 1998). The negative-answer TTL "is taken from the minimum of the SOA.MINIMUM field and SOA's TTL" — [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html), [RFC 1035](https://www.rfc-editor.org/rfc/rfc1035.html), [RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html).
- Terminology: RFC 9499 (Mar 2024, obsoletes RFC 8499) — [RFC 9499](https://www.rfc-editor.org/rfc/rfc9499.html). SVCB/HTTPS records: RFC 9460 (Nov 2023) — [RFC 9460](https://www.rfc-editor.org/rfc/rfc9460.html).
- Encrypted DNS: DoT RFC 7858 (May 2016), DoH RFC 8484 (Oct 2018), DoQ RFC 9250 (May 2022) — [RFC 7858](https://www.rfc-editor.org/rfc/rfc7858.html), [RFC 8484](https://www.rfc-editor.org/rfc/rfc8484.html), [RFC 9250](https://www.rfc-editor.org/rfc/rfc9250.html).
- Teaching resources: [Julia Evans "How to use dig"](https://jvns.ca/blog/2021/12/04/how-to-use-dig/), ["What happens when you update your DNS?"](https://jvns.ca/blog/how-updating-dns-works/), the free [Mess With DNS](https://messwithdns.net/) playground, and the zines [How DNS Works](https://wizardzines.com/zines/dns/) and [Networking! ACK!](https://wizardzines.com/zines/networking/).
- The JVM has its own DNS cache, separate from record TTLs. OpenJDK's `java.security` says: "The default behavior in this implementation is to cache for 30 seconds" (`networkaddress.cache.ttl` is commented out by default). `networkaddress.cache.negative.ttl=10` is the shipped default for failed lookups. `networkaddress.cache.stale.ttl` exists with default 0 — [local check, `$JAVA_HOME/conf/security/java.security`, Homebrew OpenJDK 25.0.5]. Property docs: [Networking Properties (JDK 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/doc-files/net-properties.html).

**HTTP versions / QUIC**
- HTTP/1.1 "defaults to the use of 'persistent connections', allowing multiple requests and responses to be carried over a single connection" — [RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html).
- Idempotency, which decides what is safe to retry: "PUT, DELETE, and safe request methods are idempotent" — [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html).
- HTTP/3 discovery uses Alt-Svc ([MDN Alt-Svc](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Alt-Svc)) or DNS HTTPS records ([RFC 9460](https://www.rfc-editor.org/rfc/rfc9460.html)). JEP 517 notes "it is impossible to determine, in advance, whether a target server supports HTTP/3" — [JEP 517](https://openjdk.org/jeps/517).
- Byte-level references: [The Illustrated TLS 1.3 Connection](https://tls13.xargs.org/) and [The Illustrated QUIC Connection](https://quic.xargs.org/).

**TLS 1.3 / certificates / mTLS**
- TLS 1.3 is now **RFC 9846** (see section 2). PKIX certificates: RFC 5280 (May 2008). SNI: RFC 6066. TLS 1.0/1.1 deprecated by RFC 8996 (Mar 2021) — [RFC 5280](https://www.rfc-editor.org/rfc/rfc5280.html), [RFC 6066](https://www.rfc-editor.org/rfc/rfc6066.html), [RFC 8996](https://www.rfc-editor.org/rfc/rfc8996.html).
- Conceptual PKI primer (chains, roots, intermediates, mTLS): [Smallstep "Everything you should know about certificates and PKI"](https://smallstep.com/blog/everything-pki/).

**LB / proxies / CDN / app-level resilience**
- L4 vs L7, client IP propagation: HAProxy's PROXY protocol spec — [proxy-protocol.txt](https://www.haproxy.org/download/3.0/doc/proxy-protocol.txt). Envoy's terminology (downstream/upstream, listener, cluster) is a useful shared vocabulary — [Envoy terminology](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/intro/terminology). Upstream pooling and keepalive in nginx — [ngx_http_upstream_module](https://nginx.org/en/docs/http/ngx_http_upstream_module.html).
- CDN caching semantics: [RFC 9111 HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html).
- Timeouts, retries, backoff, jitter: [AWS Builders' Library "Timeouts, retries, and backoff with jitter"](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) (now redirects to builder.aws.com) and [AWS "Exponential Backoff And Jitter"](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/). Retry amplification and cascading failure: [Google SRE book ch. 22](https://sre.google/sre-book/addressing-cascading-failures/). DNS and frontend LB: [Google SRE book ch. 19](https://sre.google/sre-book/load-balancing-frontend/).
- Java HttpClient pool and keepalive defaults (JDK 25 module summary): `jdk.httpclient.keepalive.timeout` (default **30** seconds, "applies to both HTTP/1.1 and HTTP/2", with an h2 override `jdk.httpclient.keepalive.timeout.h2`); `jdk.httpclient.connectionPoolSize` (default 0 = unbounded HTTP/1.1 keep-alive cache); `jdk.httpclient.maxstreams` (default 100) — [java.net.http module summary (JDK 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.net.http/module-summary.html).

### Inferences
- **Recommended order** (detailed in section 5): (1) mental model and layering, (2) link layer/ARP, (3) IPv4 addressing/CIDR/NAT, (4) routing/ICMP/MTU, (5) IPv6, (6) UDP plus the sockets API, (7) TCP connection lifecycle, (8) TCP performance (flow and congestion control, Nagle/delayed ACK, HOL), (9) DNS, (10) TLS 1.3 and certificates, (11) HTTP/1.1, /2, /3 and QUIC, (12) LBs, proxies and CDNs plus timeouts/retries/pooling, with a debugging capstone.
- DNS could come earlier, since it is very hands-on and motivating. It is placed after TCP because DoH, DoQ, the HTTPS RR, and the "resolution is part of connect latency" lesson all assume transport knowledge. Moving it to slot 6 also works if the writer wants an early win.
- The QUIC and HTTP/3 lesson works best right after TLS 1.3, because QUIC embeds the TLS 1.3 handshake (RFC 9001).
- For a backend engineer, the highest-value 20% is: socket states and TIME_WAIT, keepalive layers, connection pooling and idle-timeout mismatches, timeouts (connect vs read vs total), retries with idempotency, DNS caching (including the JVM's 30 s cache), TLS failure modes (chain, SNI, mTLS), and reading tcpdump/Wireshark.

### Gaps
- I did not fetch HPBN chapter content beyond confirming the pages load. HPBN predates HTTP/3 and TLS 1.3 finalization (it was written about 2013), so the writer should treat it as foundational TCP/HTTP/2 material, not current-status material.
- Linux's mainline `tcp_bbr` module version (BBRv1 vs v3) was not re-verified this session. The out-of-tree BBRv3 code lives at [github.com/google/bbr](https://github.com/google/bbr) (page loads; contents not read).

---

## 2. Current protocol and standard status (as of Nov 2026)

### Takeaway
Three 2026 changes matter for the course: **TLS 1.3 was re-published as RFC 9846 (July 2026), which obsoletes RFC 8446**; **ECH became RFC 9849 (March 2026)**; and **hybrid PQ key exchange became RFC 10024 (Aug 2026)**, with X25519MLKEM768 "Recommended" in IANA. Post-quantum key agreement is now the majority of human traffic at Cloudflare (>65% as of April 2026). HTTP/3 carries about 21% of Cloudflare requests (2025), and 41.1% of websites support it (W3Techs, Nov 2026). BBRv3 is still an Internet-Draft (-07, 2 Nov 2026), not an RFC.

### Cited Findings

**RFC status table (dates and headers read from rfc-editor.org on 2026-11-07)**

| Topic | RFC | Date | Notes |
|---|---|---|---|
| TCP | [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html) | Aug 2022 | Obsoletes 793, 879, 2873, 6093, 6429, 6528 (and others); updates 1011, 1122, 5961 |
| TCP congestion control | [RFC 5681](https://www.rfc-editor.org/rfc/rfc5681.html) | Sept 2009 | Obsoletes 2581 |
| CUBIC | [RFC 9438](https://www.rfc-editor.org/rfc/rfc9438.html) | Aug 2023 | Obsoletes 8312; updates 5681 |
| RTO | [RFC 6298](https://www.rfc-editor.org/rfc/rfc6298.html) | June 2011 | Initial RTO 1 s |
| Window scale / timestamps | [RFC 7323](https://www.rfc-editor.org/rfc/rfc7323.html) | Sept 2014 | Obsoletes 1323 |
| HTTP Semantics | [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) | June 2022 | Obsoletes 2818, 7230, 7231, 7232, 7233, 7235 (and others) |
| HTTP Caching | [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html) | June 2022 | Obsoletes 7234 |
| HTTP/1.1 | [RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html) | June 2022 | Obsoletes 7230 |
| HTTP/2 | [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html) | June 2022 | Obsoletes 7540, 8740 |
| HTTP/3 | [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html) | June 2022 | |
| QPACK | [RFC 9204](https://www.rfc-editor.org/rfc/rfc9204.html) | June 2022 | |
| HTTP priorities | [RFC 9218](https://www.rfc-editor.org/rfc/rfc9218.html) | June 2022 | |
| QUIC transport / TLS / recovery | [RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html), [9001](https://www.rfc-editor.org/rfc/rfc9001.html), [9002](https://www.rfc-editor.org/rfc/rfc9002.html) | May 2021 | Invariants: [RFC 8999](https://www.rfc-editor.org/rfc/rfc8999.html) |
| TLS 1.3 (original) | [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446.html) | Aug 2018 | **Now obsolete** (by RFC 9846) |
| **TLS 1.3 (current)** | [RFC 9846](https://www.rfc-editor.org/rfc/rfc9846.html) | **July 2026** | Obsoletes 5077, 5246, 6961, 7627, 8422, **8446**; updates 5705, 6066; author E. Rescorla ([datatracker](https://datatracker.ietf.org/doc/rfc9846/)) |
| **ECH** | [RFC 9849](https://www.rfc-editor.org/rfc/rfc9849.html) | **March 2026** | Proposed Standard |
| ECH via DNS SVCB/HTTPS | [RFC 9848](https://www.rfc-editor.org/rfc/rfc9848.html) | March 2026 | |
| **Hybrid PQ key agreement** | [RFC 10024](https://www.rfc-editor.org/rfc/rfc10024.html) | **Aug 2026** | Proposed Standard; from draft-ietf-tls-ecdhe-mlkem-05 ([datatracker](https://datatracker.ietf.org/doc/rfc10024/)) |
| Deprecate TLS 1.0/1.1 | [RFC 8996](https://www.rfc-editor.org/rfc/rfc8996.html) | March 2021 | |
| DNS core | [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html) / [1035](https://www.rfc-editor.org/rfc/rfc1035.html) | Nov 1987 | |
| DNS negative caching | [RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html) | March 1998 | Updates 1034, 1035 |
| DNS terminology | [RFC 9499](https://www.rfc-editor.org/rfc/rfc9499.html) | March 2024 | Obsoletes 8499; updates 2308 |
| SVCB/HTTPS RR | [RFC 9460](https://www.rfc-editor.org/rfc/rfc9460.html) | Nov 2023 | |
| DoT / DoH / DoQ | [7858](https://www.rfc-editor.org/rfc/rfc7858.html) / [8484](https://www.rfc-editor.org/rfc/rfc8484.html) / [9250](https://www.rfc-editor.org/rfc/rfc9250.html) | May 2016 / Oct 2018 / May 2022 | |
| IPv6 / addressing | [RFC 8200](https://www.rfc-editor.org/rfc/rfc8200.html) / [4291](https://www.rfc-editor.org/rfc/rfc4291.html) | July 2017 / Feb 2006 | |
| Happy Eyeballs v2 | [RFC 8305](https://www.rfc-editor.org/rfc/rfc8305.html) | Dec 2017 | Obsoletes 6555 |
| CIDR | [RFC 4632](https://www.rfc-editor.org/rfc/rfc4632.html) | Aug 2006 | |
| CGNAT space | [RFC 6598](https://www.rfc-editor.org/rfc/rfc6598.html) | April 2012 | 100.64.0.0/10 |
| Port registry procedures | [RFC 6335](https://www.rfc-editor.org/rfc/rfc6335.html) | Aug 2011 | Dynamic/ephemeral range 49152–65535 |
| PLPMTUD | [RFC 8899](https://www.rfc-editor.org/rfc/rfc8899.html) | Sept 2020 | |
| PKIX certs | [RFC 5280](https://www.rfc-editor.org/rfc/rfc5280.html) | May 2008 | |

**TLS 1.3 re-publication**
- RFC 9846 is titled "The Transport Layer Security (TLS) Protocol Version 1.3", Proposed Standard. "This document obsoletes RFC 8446, which specified TLS 1.3" — [RFC 9846](https://www.rfc-editor.org/rfc/rfc9846.html), [datatracker RFC 9846 (July 2026)](https://datatracker.ietf.org/doc/rfc9846/).
- RFC 8446 already listed "Obsoletes: 5077, 5246, 6961". RFC 9846 adds 7627 and 8422 to that list — [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446.html), [RFC 9846](https://www.rfc-editor.org/rfc/rfc9846.html).

**Post-quantum key exchange**
- RFC 10024 "defines three hybrid key agreement mechanisms for TLS 1.3": X25519MLKEM768, SecP256r1MLKEM768, SecP384r1MLKEM1024 (ML-KEM combined with ECDHE). Published Aug 2026 — [RFC 10024](https://www.rfc-editor.org/rfc/rfc10024.html), [datatracker](https://datatracker.ietf.org/doc/rfc10024/).
- IANA TLS Supported Groups registry: **X25519MLKEM768 = 4588 (0x11EC), Recommended = Y**, reference RFC 10024. SecP256r1MLKEM768 = 4587, Recommended = N. The pre-standard **X25519Kyber768Draft00 (25497) is marked OBSOLETE** — [IANA TLS parameters](https://www.iana.org/assignments/tls-parameters/tls-parameters.xhtml).
- Cloudflare, 2025: PQ-encrypted share of human traffic rose "from 29% at the start of the year to 52% in early December". The mid-September jump coincided with Apple's OS updates. Apple's release note: "TLS-protected connections will automatically advertise support for hybrid, quantum-secure key exchange in TLS 1.3". iOS PQ-supporting requests went from just under 2% to 11% within four days of iOS 26, and passed 25% by early December — [Cloudflare Radar 2025 YIR](https://blog.cloudflare.com/radar-2025-year-in-review/).
- Cloudflare, 7 April 2026 (modified 15 July 2026): "over 65% of human traffic" to Cloudflare is PQ-encrypted. Target is "full post-quantum security including authentication" by 2029, with these milestones: mid-2026 ML-DSA auth to origins; mid-2027 visitor-facing PQ auth via Merkle Tree Certificates; early 2028 Cloudflare One; 2029 fully PQ — [Cloudflare "targets 2029 for full post-quantum security"](https://blog.cloudflare.com/post-quantum-roadmap/).
- Locally, Homebrew OpenSSL 4.1.0 (23 Oct 2026) connecting to cloudflare.com with `-groups X25519MLKEM768` printed "Negotiated TLS1.3 group: X25519MLKEM768". macOS's bundled `/usr/bin/openssl` is **LibreSSL 3.3.6**. Homebrew also has OpenSSL 3.5.9 — [local check].
- Locally, Homebrew OpenJDK 25.0.5's default `SSLParameters.getNamedGroups()` lists **X25519MLKEM768 first**, then x25519, secp256r1, and the rest. Default protocols are TLSv1.3 and TLSv1.2 — [local check]. (The JEP that added this, and whether it was backported to 25u, was not verified. See Gaps.)

**ECH**
- RFC 9849 "describes a mechanism in Transport Layer Security (TLS) for encrypting a ClientHello message under a server public key". Proposed Standard, March 2026. Authors: Rescorla, Oku, Sullivan, Wood. The IETF announcement went out 4 March 2026 — [RFC 9849](https://www.rfc-editor.org/rfc/rfc9849.html), [IETF announce](https://mailarchive.ietf.org/arch/msg/ietf-announce/5MiqV8pQUAIGS1HvdOCh-yDw0hE/) (from search results; the announce page itself was not fetched).
- ECH design: the inner ClientHello (real SNI, ALPN) is encrypted. The outer ClientHello stays in the clear and carries a public SNI. Keys are distributed via DNS (HTTPS RR) and fetched over DoH. The article warns ciphertext length can still leak information — [Cloudflare "Good-bye ESNI, hello ECH!"](https://blog.cloudflare.com/encrypted-client-hello/) (orig. Dec 2020, modified July 2026).
- Browser defaults: Mozilla says ECH was introduced in Firefox 118 and is "enabled by default in Firefox 119 and above", and needs DoH — [Mozilla support](https://support.mozilla.org/en-US/kb/understand-encrypted-client-hello). Wikipedia says Chromium 117 (Sept 2023) enabled it by default and that Firefox 118 did. **The sources conflict on the Firefox version; Mozilla's page is the more authoritative one** — [Wikipedia (secondary)](https://www.wikipedia.org/wiki/Encrypted_SNI).

**BBRv3**
- Latest revision is **draft-ietf-ccwg-bbr-07, 2 November 2026**, "Intended status: Experimental", IESG state "I-D Exists", expires 6 May 2027. Editors are Neal Cardwell, Ian Swett (Google) and Joseph Beshay (Meta). "This document specifies version 3 of the BBR algorithm, BBRv3." **Not an RFC** — [datatracker draft-ietf-ccwg-bbr](https://datatracker.ietf.org/doc/draft-ietf-ccwg-bbr/), [CCWG](https://datatracker.ietf.org/wg/ccwg/about/).

**HTTP/3 adoption**
- Cloudflare 2025 (Jan 1 to Dec 2): **HTTP/2 50%, HTTP/1.x 29%, HTTP/3 21% of requests**. HTTP/2 and HTTP/3 each gained only fractions of a point over 2024. 15 countries/regions sent more than a third of requests over HTTP/3, with Georgia highest at 38% — [Cloudflare Radar 2025 YIR](https://blog.cloudflare.com/radar-2025-year-in-review/).
- W3Techs, November 2026: "HTTP/3 is used by **41.1%** of all the websites" — [W3Techs HTTP/3](https://w3techs.com/technologies/details/ce-http3). These are different metrics. W3Techs counts sites that support HTTP/3 (top-10M style site sample). Cloudflare counts requests that actually used HTTP/3.
- Cloudflare Radar's live pages (`radar.cloudflare.com/adoption-and-usage`, `/year-in-review/2025`) returned **HTTP 403 to automated fetches**. Learners can open them in a browser, but I could not read current 2026 numbers from them.

**Java client support**
- JEP 517 "HTTP/3 for the HTTP Client API" is **delivered in JDK 26**. You opt in with `HttpClient.Version.HTTP_3` on the client or request builder. The legacy `java.net.URL` API stays HTTP/1.1, and there is no server-side HTTP/3 — [JEP 517](https://openjdk.org/jeps/517), [Inside.java "HTTP Client Updates in Java 26"](https://inside.java/2026/03/04/jdk-26-http-client/). The default version stays HTTP/2 (per Inside.java search summary).
- JDK 27 reached General Availability on 2026/09/15 — [JDK 27 project page](https://openjdk.org/projects/jdk/27/). Locally installed: OpenJDK 25.0.5 (default `java`) and 27.0.1 — [local check]. **JDK 25 (the current LTS) does not have JEP 517**, so the HTTP/3 Java lab needs JDK 26+.

**curl HTTP/3**
- Homebrew curl 8.23.0 (released 2026-10-14) lists `HTTP3` in its features and links ngtcp2 1.26.0, nghttp3 1.19.0 and OpenSSL 4.1.0. `--http3-only https://cloudflare-quic.com` returned HTTP version 3, status 200 — [local check]; [Homebrew curl formula](https://formulae.brew.sh/formula/curl); [curl HTTP/3 docs](https://curl.se/docs/http3.html).

**Certificate lifetimes (affects TLS lesson)**
- Let's Encrypt schedule. Today: 90-day certificates with 30-day authorization reuse. **May 13, 2026**: the opt-in `tlsserver` profile moves to 45-day certs. **Feb 10, 2027**: the default `classic` profile moves to 64 days (10-day authz reuse). **Feb 16, 2028**: `classic` moves to 45 days (7-hour authz reuse). There is also an opt-in 6-day `shortlived` profile. These changes are "required by the CA/Browser Forum Baseline Requirements" — [Let's Encrypt "Decreasing Certificate Lifetimes to 45 Days" (Dec 2, 2025)](https://letsencrypt.org/2025/12/02/from-90-to-45/).

### Inferences
- Lesson writers should cite **RFC 9846** as the TLS 1.3 spec and mention that RFC 8446 is what most blog posts and tools still reference. The protocol version is unchanged (still TLS 1.3).
- "PQ key exchange is the default" is now true for the main browsers and Apple OSes, and also for at least the Homebrew JDK 25.0.5 build. This is a good hands-on moment: learners can see `X25519MLKEM768` negotiated themselves with brew OpenSSL. PQ *authentication* (certificates) is not yet deployed for visitor traffic (Cloudflare's milestone is mid-2027).
- The gap between W3Techs' "41% of sites" and Cloudflare's "21% of requests" is itself teachable. Supporting H3 is not the same as using it: clients need discovery (Alt-Svc or HTTPS RR) and UDP reachability, and they fall back to TCP.

### Gaps
- No 2026 full-year Cloudflare HTTP/3 request share was readable (Radar pages return 403 to bots). The 21% figure is for 2025.
- A search summary mentioned a later Cloudflare post saying "over two-thirds of browser traffic" is PQ-protected. I couldn't identify that post, so it is omitted.
- RFC 9934 (PEM format for ECH key pairs, reportedly March 2026) appeared only in search results. Not verified.
- The CA/Browser Forum ballot schedule for max certificate validity (SC-081: 200/100/47 days) was not verified this session. My regex against the cabforum.org BR page failed, so only Let's Encrypt's own timeline is cited.
- The OpenJDK JEP that made X25519MLKEM768 a default named group, and the release it shipped in (and whether 25.0.x got it as a backport), was not verified. Only the local behaviour of Homebrew OpenJDK 25.0.5 was observed.
- HTTP/2 server push deprecation status in browsers was not verified this session.

---

## 3. Common misconceptions (with corrections)

### Takeaway
Most production confusion comes from seven myths: what an ACK or a successful `write()` actually means, TIME_WAIT, the three kinds of "keepalive", the idea that DNS "propagates", the idea that HTTP/2 ends head-of-line blocking, the 64k ephemeral-port myth, and treating retries and timeouts as free.

### Cited Findings
1. **"TCP guarantees the app received or processed my data."** A TCP ACK means only that the peer's TCP stack received the bytes. A successful `write()`/`send()` means only that they were copied into the local kernel send buffer. The ACK carries no application-level meaning. RFC 9293 defines ACKs over sequence space (bytes), not application messages — [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html). Cloudflare shows sockets hanging with unacknowledged data in send buffers and uses TCP_USER_TIMEOUT to bound that — [Cloudflare "When TCP sockets refuse to die"](https://blog.cloudflare.com/when-tcp-sockets-refuse-to-die/). Fix: application-level acknowledgements and idempotency keys.
2. **"UDP is always faster."** UDP has no handshake, no retransmission and no congestion control ([RFC 768](https://www.rfc-editor.org/rfc/rfc768.html)). Anything reliable built on it has to reimplement those pieces, which is exactly what QUIC does: loss detection and congestion control in RFC 9002, streams and flow control in RFC 9000 — [RFC 9002](https://www.rfc-editor.org/rfc/rfc9002.html), [RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html). Cloudflare's QUIC posts cover the engineering cost of UDP paths — [Cloudflare "The Road to QUIC"](https://blog.cloudflare.com/the-road-to-quic/).
3. **TIME_WAIT misunderstandings.**
   - Only the side that closes first enters TIME-WAIT. It exists so stray old segments can't corrupt a new connection with the same 4-tuple, and so the final ACK can be resent if lost. On Linux it lasts about 60 s, hard-coded as `TCP_TIMEWAIT_LEN`. A TIME-WAIT socket costs about 168 bytes; "40,000 inbound TIME-WAIT sockets use under 10 MiB". `tcp_tw_recycle` broke clients behind NAT and **was removed in Linux 4.12**. `tcp_tw_reuse` is "almost safe" on the client side and useless for incoming connections. Bernat's protocol-design advice is to avoid letting clients close first, so that servers, which handle it better, carry the TIME-WAIT burden. His other advice is to increase the number of possible 4-tuples. The everyday version for app engineers is to keep client connections alive and pooled — [Vincent Bernat, "Coping with the TCP TIME-WAIT state on busy Linux servers"](https://vincent.bernat.ch/en/blog/2014-tcp-time-wait-state-linux) (2014, with a 2026 update note).
   - The spec value is 2×MSL with MSL "taken to be 2 minutes" — [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html). macOS sets `net.inet.tcp.msl: 15000` (ms) — [local check]. That implies a 30 s TIME_WAIT on macOS (inference: 2×MSL).
   - Linux `tcp_tw_reuse` values are 0 = disable, 1 = global enable, 2 = loopback only — [kernel ip-sysctl docs](https://www.kernel.org/doc/html/latest/networking/ip-sysctl.html).
   - `SO_REUSEADDR` is about letting a *listener* rebind its port while old connections sit in TIME_WAIT. It does not make TIME_WAIT go away — [StandardSocketOptions](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/StandardSocketOptions.html), [socket(7)](https://man7.org/linux/man-pages/man7/socket.7.html).
4. **"Ephemeral ports cap you at about 64k connections."** The limit is per 4-tuple (src IP, src port, dst IP, dst port). You exhaust ports when one client opens many short-lived connections to the *same* destination IP:port, for example through a proxy. With about 30,000 client ports and a fixed server IP:port, Bernat calculates about 500 new connections per second on average because of TIME-WAIT — [Bernat](https://vincent.bernat.ch/en/blog/2014-tcp-time-wait-state-linux). Linux's default `ip_local_port_range` is "32768 and 60999" — [kernel ip-sysctl](https://www.kernel.org/doc/html/latest/networking/ip-sysctl.html). macOS uses 49152–65535 — [local check], which matches the IANA dynamic range — [RFC 6335](https://www.rfc-editor.org/rfc/rfc6335.html). Cloudflare covers connect() and bind() port-selection pitfalls — [Cloudflare "How to stop running out of ephemeral ports and start to love long-lived connections"](https://blog.cloudflare.com/how-to-stop-running-out-of-ephemeral-ports-and-start-to-love-long-lived-connections/). The fix is connection reuse (pooling and keepalive), not sysctl tuning.
5. **Keepalive confusion: there are at least three.**
   - (a) *TCP keepalive* (SO_KEEPALIVE). Probes on idle connections. Spec default is ≥ 2 hours ([RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html)). Linux defaults: `tcp_keepalive_time` 7200 s, `tcp_keepalive_intvl` 75 s, `tcp_keepalive_probes` 9, and "Keep-alives are sent only when the SO_KEEPALIVE socket option is enabled" — [tcp(7)](https://man7.org/linux/man-pages/man7/tcp.7.html). macOS: keepidle 7,200,000 ms, keepintvl 75,000 ms, keepcnt 8 — [local check]. Java can tune these per socket via `ExtendedSocketOptions.TCP_KEEPIDLE/TCP_KEEPINTERVAL/TCP_KEEPCOUNT` — [ExtendedSocketOptions](https://docs.oracle.com/en/java/javase/25/docs/api/jdk.net/jdk/net/ExtendedSocketOptions.html).
   - (b) *HTTP persistent connections* ("keep-alive"). This is about reusing a connection for many requests. It is the default in HTTP/1.1 — [RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html). The JDK HttpClient's idle keep-alive timeout is 30 s — [java.net.http module summary](https://docs.oracle.com/en/java/javase/25/docs/api/java.net.http/module-summary.html).
   - (c) *Protocol or app heartbeats*: HTTP/2 PING frames ([RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html)), gRPC keepalive, WebSocket ping.
   - Classic incident: the client pool's idle timeout is longer than the server's or LB's idle timeout. The client then reuses a connection the other side already closed, and gets a reset or 502. Fix: set the client idle timeout below every hop's idle timeout, and retry idempotent requests once on a stale-connection failure. (Inference built from the above; nginx upstream keepalive semantics are in [ngx_http_upstream_module](https://nginx.org/en/docs/http/ngx_http_upstream_module.html).)
6. **"DNS changes take 24–48 h to propagate."** Nothing is pushed. Resolvers cache each answer until its TTL runs out, and negative answers are cached too, for the SOA MINIMUM/TTL — [RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html), [Julia Evans "What happens when you update your DNS?"](https://jvns.ca/blog/how-updating-dns-works/). Practical rule: lower the TTL at least one old-TTL ahead of a migration. Extra layers ignore record TTLs: the JVM caches positive lookups for 30 s and negative ones for 10 s by default — [local check of java.security](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/doc-files/net-properties.html). The OS stub resolver (mDNSResponder on macOS) and connection pools also hold on to old addresses: a pooled connection keeps pointing at the old IP no matter what DNS says.
7. **"HTTP/2 removes head-of-line blocking."** It removes HTTP/1.1's *application-level* HOL by multiplexing. The spec itself says "TCP head-of-line blocking is not addressed by this protocol" — [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html). Under packet loss, every stream on the connection stalls. QUIC removes *cross-stream* transport HOL, though a single stream is still ordered — [RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html). QPACK can still introduce some HOL if the encoder chooses — [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html).
8. **"Nagle/delayed ACK don't matter for me."** Small writes can add tens of milliseconds of latency: a write-write-read pattern lets Nagle wait for the ACK that delayed-ACK is holding back, for up to the RFC 1122 limit of < 0.5 s — [RFC 1122](https://www.rfc-editor.org/rfc/rfc1122.html), [Julia Evans' story](https://jvns.ca/blog/2015/11/21/why-you-should-understand-a-little-about-tcp/). Fix: TCP_NODELAY and/or batch writes. In Java, `StandardSocketOptions.TCP_NODELAY` or `Socket.setTcpNoDelay` — [StandardSocketOptions](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/StandardSocketOptions.html).
9. **"HTTPS hides which site I'm visiting."** Without ECH, the SNI in the ClientHello is plaintext, and so is DNS unless DoH/DoT/DoQ is used. ECH (RFC 9849) encrypts the inner ClientHello, but the outer SNI and some length side channels remain — [RFC 9849](https://www.rfc-editor.org/rfc/rfc9849.html), [Cloudflare ECH post](https://blog.cloudflare.com/encrypted-client-hello/).
10. **"Retries make things more reliable."** Unbounded or synchronized retries multiply load and can cause cascading failure. Use capped exponential backoff with jitter, retry budgets, and retry only idempotent operations — [AWS Builders' Library](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/), [AWS backoff+jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/), [Google SRE cascading failures](https://sre.google/sre-book/addressing-cascading-failures/). Per RFC 9110, PUT, DELETE and the safe methods are idempotent. POST is not — [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html).
11. **"One timeout is enough."** There are separate connect, TLS handshake, read/idle (SO_TIMEOUT), per-request total, and pool-acquire timeouts. In Java: `Socket.connect(addr, timeout)` vs `Socket.setSoTimeout` ([Socket](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/Socket.html)), and `HttpClient.Builder.connectTimeout` vs `HttpRequest.Builder.timeout` ([HttpClient](https://docs.oracle.com/en/java/javase/25/docs/api/java.net.http/java/net/http/HttpClient.html)).
12. **"An L7 load balancer forwards my client's TCP connection."** It terminates the client's TCP (and usually TLS) connection and opens its own to the backend. The backend sees the LB's IP unless X-Forwarded-For/Forwarded or the PROXY protocol carries the original address — [HAProxy PROXY protocol spec](https://www.haproxy.org/download/3.0/doc/proxy-protocol.txt).
13. **"OSI's 7 layers describe how the Internet works."** The deployed stack is TCP/IP. QUIC folds transport, security and multiplexing into one user-space protocol over UDP — [RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html), [RFC 9001](https://www.rfc-editor.org/rfc/rfc9001.html). OSI numbers survive as vocabulary (L4/L7).
14. **"0-RTT is a free speedup."** TLS 1.3 early data has weaker guarantees and can be replayed. Only use it for idempotent requests — [RFC 9846 (TLS 1.3)](https://www.rfc-editor.org/rfc/rfc9846.html), [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446.html). (Section-level quote not extracted this session. See Gaps.)
15. **"Connection refused" vs "timeout" are the same failure.** A refusal is an immediate RST: the host is reachable and nothing is listening. A timeout means packets are dropped (firewall, routing, host down). They point to completely different diagnoses — [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html) (RST on SYN to a closed port). Shown in the Lesson 6 lab.

### Inferences
- Misconceptions 3, 4, 5, 6, 10 and 11 should each get a "you will see this at work" sidebar with a reproducible lab. They are the ones most likely to appear in a real incident review for this audience.
- One analogy to *avoid*: "TCP is like a phone call that guarantees delivery." It reinforces misconception 1.

### Gaps
- I did not extract the exact RFC 8446/9846 wording on 0-RTT replay. My grep of the line-wrapped text didn't match. The writer should quote §2.3 / §8 directly.
- No authoritative source was fetched for cloud LB default idle timeouts (e.g., AWS ALB, GCP). Don't state specific numbers without checking the vendor docs.

---

## 4. macOS (Apple Silicon) tooling and gotchas

### Takeaway
macOS has BSD tools, not Linux ones. There is no `ss`, `ip` or `tc`. Use `netstat -anv`, `lsof -i`, `route`, `ifconfig`, `ndp`, `scutil` and `nettop`. Packet capture needs sudo. The bundled curl, dig and openssl are old and lack HTTP/3, the HTTPS RR and PQ, so install the Homebrew versions. Linux-only tools (`ss`, `ip`, `tc netem`, `sysctl net.ipv4.*`) should run inside containers, for example `nicolaka/netshoot`. On Docker Desktop, containers live inside a Linux VM, so host-side tcpdump does **not** see the container bridge.

### Cited Findings (all from [local check] on macOS 27.0.1 arm64 unless otherwise cited)
- **Present by default:** netstat, lsof, tcpdump, dig, nslookup, nc, traceroute, openssl, nettop, route, arp, ndp, ifconfig, networkQuality, scutil, dns-sd, all in /usr/bin, /usr/sbin or /sbin. **Absent:** `ss`, `ip`, `mtr`, `tshark`/Wireshark, Docker — [local check].
- **Socket state inspection.** `netstat -anv -p tcp` shows state (e.g., TIME_WAIT), rx/tx bytes and a `process:pid` column. **macOS prints ports with a dot, not a colon** (`127.0.0.1.9099`) — [local check]. Use `lsof -nP -iTCP -sTCP:LISTEN` for listeners. `ss -tanp` is Linux-only — [ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html).
- **Local TIME_WAIT demo.** `nc -l 127.0.0.1 9099` plus `echo hi | nc -w1 127.0.0.1 9099` left **both** loopback sockets in TIME_WAIT, because both sides closed at nearly the same time (simultaneous close) — [local check]. This is a nice surprise to discuss. For the textbook single-side TIME_WAIT, the Kotlin lab should close from one side first.
- **tcpdump needs root.** `/dev/bpf0` is `crw------- root wheel`. Running without sudo gives "lo0: You don't have permission to capture on that device ((cannot open BPF device) /dev/bpf0: Permission denied)" — [local check]. The loopback interface is `lo0`, not `lo`. Docs: [tcpdump(1)](https://www.tcpdump.org/manpages/tcpdump.1.html), [pcap-filter(7)](https://www.tcpdump.org/manpages/pcap-filter.7.html).
- **Wireshark:** Homebrew cask `wireshark-app` is at version 4.6.9 — [Homebrew cask](https://formulae.brew.sh/cask/wireshark-app), [Wireshark download](https://www.wireshark.org/download.html), [User's Guide](https://www.wireshark.org/docs/wsug_html_chunked/), [tshark(1)](https://www.wireshark.org/docs/man-pages/tshark.html). For decrypting TLS with a key log file see [Wireshark wiki TLS](https://wiki.wireshark.org/TLS).
- **curl.** System `/usr/bin/curl` is **8.7.1 (2024-03-27), SecureTransport/LibreSSL, and has no HTTP3 feature**. Homebrew curl 8.23.0 has `HTTP3` (ngtcp2/nghttp3, OpenSSL 4.1.0). Homebrew curl is **keg-only and not on PATH** (`which -a curl` → only `/usr/bin/curl`), so call `/opt/homebrew/opt/curl/bin/curl` or prepend it to PATH — [local check], [Homebrew curl](https://formulae.brew.sh/formula/curl), [curl HTTP/3](https://curl.se/docs/http3.html). curl's docs say the ngtcp2 backend is non-experimental, while quiche/msh3 remain experimental (per search summary of curl docs).
- **Timing breakdown example** (brew curl to cloudflare-quic.com, one run, warm DNS for the second and third rows): h1.1 connect 30 ms / TLS 46 ms / TTFB 60 ms; h2 12 / 27 / 44 ms; h3 14 / 19 / 33 ms — [local check]. Single-sample numbers, for illustration only. Use `-w '%{http_version} %{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer}'`. The point the numbers make: with H3, the TLS handshake finishes almost as soon as the connection is up.
- **dig.** The bundled dig is **9.10.6** (old BIND). `dig cloudflare.com HTTPS` does **not** query the HTTPS type (it returned A records), while `dig cloudflare.com TYPE65` returns raw wire-format RDATA — [local check]. Install Homebrew `bind` for a modern dig — [Homebrew bind](https://formulae.brew.sh/formula/bind).
- **openssl.** `/usr/bin/openssl` is LibreSSL 3.3.6. Homebrew `openssl@3` is 3.5.9 and `openssl` is 4.1.0. Brew OpenSSL negotiated X25519MLKEM768 with cloudflare.com — [local check], [Homebrew openssl@3](https://formulae.brew.sh/formula/openssl@3).
- **mtr:** not preinstalled. Homebrew mtr 0.96 says "mtr requires root privileges so you will need to run `sudo mtr`" — [Homebrew mtr](https://formulae.brew.sh/formula/mtr). iperf3 is also available via Homebrew — [Homebrew iperf3](https://formulae.brew.sh/formula/iperf3).
- **macOS TCP defaults** (sysctl): `net.inet.tcp.msl: 15000`; `net.inet.ip.portrange.first/last: 49152/65535`; `net.inet.tcp.keepidle: 7200000`, `keepintvl: 75000`, `keepcnt: 8`; `always_keepalive: 0`; `net.inet.tcp.delayed_ack: 3`; `use_newreno: 0`; `cubic_sockets: 123` (CUBIC in use); `use_ledbat: 0` — [local check]. CUBIC being Apple's default matches [RFC 9438](https://www.rfc-editor.org/rfc/rfc9438.html).
- **Other mac-native helpers:** `route -n get <ip>` (which interface and gateway), `netstat -rn` (routing table), `scutil --dns` (resolver config), `networkQuality` (Apple's built-in throughput/responsiveness test), `nettop` (per-process live sockets) — [local check] for presence.
- **Docker Desktop networking.** "The container's `eth0` interface connects to a virtual bridge (`docker0`) inside the VM". Host access is via published ports. "On macOS, all container network traffic originates from `com.docker.backend`". `-p` binds to 0.0.0.0 by default — [Docker Desktop networking docs](https://docs.docker.com/desktop/features/networking/). User-defined bridge networks (with built-in DNS between containers) — [Docker bridge driver](https://docs.docker.com/engine/network/drivers/bridge/), [Docker networking overview](https://docs.docker.com/engine/network/).
- **OrbStack:** "You can also connect to containers by IP, directly from Mac!". Containers get `container-name.orb.local` names. `host.docker.internal` reaches the Mac. IPv6 is off by default for containers — [OrbStack networking](https://docs.orbstack.dev/docker/network).
- **netshoot** packages tcpdump, tshark, termshark, iproute2, bind-tools (dig), mtr, iperf3 and curl. Attach it to another container's namespace with `docker run -it --net container:<container_name> nicolaka/netshoot` — [nicolaka/netshoot](https://github.com/nicolaka/netshoot).
- **tc netem** needs `--cap-add NET_ADMIN` in the container, and the kernel must provide `sch_netem` for loss and delay — [tcconfig docs](https://pypi.org/project/tcconfig/), [tc-netem(8)](https://man7.org/linux/man-pages/man8/tc-netem.8.html).

### Inferences
- Recommend this one-time setup: `brew install curl bind mtr iperf3 openssl@3` plus `brew install --cask wireshark-app`, and add `/opt/homebrew/opt/curl/bin` to PATH. For Java labs, install Homebrew `openjdk@25` (LTS) plus `openjdk@27` (or 26+) for HTTP/3.
- Pick one container runtime for the course. **OrbStack is the easiest for networking labs**, since you can reach container IPs directly from macOS. Docker Desktop works fine if every capture runs *inside* the Docker network, using netshoot as a sidecar. Colima was not researched.
- macOS TIME_WAIT (30 s implied) differs from Linux (60 s). Running the same lab on the host and in a container shows the difference, and it is a nice "specs vs implementations" moment.

### Gaps
- **Docker labs were not smoke-tested here** because Docker isn't installed. Whether Docker Desktop's and OrbStack's VM kernels ship `sch_netem` and `tcp_bbr` was not confirmed from a source. The writer should include a pre-flight check: `docker run --rm --cap-add NET_ADMIN nicolaka/netshoot tc qdisc add dev eth0 root netem delay 100ms && echo OK` and `sysctl net.ipv4.tcp_available_congestion_control` inside a container.
- I didn't verify whether netshoot ships the `tc` binary. Its README lists iproute2 but doesn't name `tc`. If it is missing, use a Debian/Ubuntu image with `apt-get install iproute2`.
- I didn't verify Wireshark's macOS ChmodBPF helper, which allows capture without sudo, for version 4.6.x.
- The meaning of macOS `net.inet.tcp.delayed_ack=3` is not documented in anything I fetched.

---

## 5. Proposed lesson outline (12 lessons) with hands-on labs

### Takeaway
There are 12 lessons. Each pairs one concept cluster with 1–2 labs that make packets, states or caches visible on a Mac. Host-side labs use macOS tools. Linux-only behaviour (tc, ss, routing between namespaces, sysctls) runs in containers.

### Cited Findings (tools and behaviours the labs rely on)
- Host capture: `sudo tcpdump -i lo0 -nn -S 'tcp port 9099'` (root required) — [local check], [tcpdump(1)](https://www.tcpdump.org/manpages/tcpdump.1.html).
- Socket states: `netstat -anv -p tcp`, `lsof -nP -iTCP` — [local check]. Inside containers use `ss -tanpi` — [ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html).
- Container sidecar capture: `--net container:<name>` with netshoot — [netshoot](https://github.com/nicolaka/netshoot).
- Impairment: `tc qdisc add dev eth0 root netem delay 100ms loss 5%` needs NET_ADMIN — [tc-netem(8)](https://man7.org/linux/man-pages/man8/tc-netem.8.html), [tcconfig](https://pypi.org/project/tcconfig/).
- HTTP version comparison: brew curl `--http1.1/--http2/--http3-only` with `-w` timings — [local check], [everything curl](https://everything.curl.dev/).
- PQ/TLS inspection: brew `openssl s_client -groups X25519MLKEM768` — [local check].
- Public H3 test endpoints: [cloudflare-quic.com](https://cloudflare-quic.com/), [quic.nginx.org](https://quic.nginx.org/), [http3check.net](https://http3check.net/).
- Java: `HttpClient.Version.HTTP_3` on JDK 26+ — [JEP 517](https://openjdk.org/jeps/517).

### Lesson plan

**L1. The mental model: layers, encapsulation, "what happens when I curl a URL"**
- Concepts: the TCP/IP 4-layer model vs OSI (vocabulary only), encapsulation, addresses at each layer (MAC / IP / port / hostname), packets vs streams, latency vs bandwidth, the BDP preview.
- Lab 1a: `sudo tcpdump -i en0 -w l1.pcap host example.com` while running `curl -v https://example.com`. Open the capture in Wireshark and label Ethernet, IP, TCP, TLS and DNS headers on one packet. Also try `route -n get example.com`, `scutil --dns`, `ifconfig en0`.
- Lab 1b: annotate `curl -w` timings (DNS / connect / TLS / TTFB) for a few sites, and run `networkQuality` to discuss throughput vs responsiveness.

**L2. Link layer: Ethernet, MAC, ARP, switches, MTU**
- Concepts: frames, MAC addresses, broadcast domains, switches vs routers, ARP request/reply, ARP cache, MTU (1500), a brief VLAN mention, Wi-Fi as "Ethernet-ish".
- Lab 2a: create a user-defined bridge network with two netshoot containers. In one, run `ip neigh flush all` and `tcpdump -e -nn arp`, then ping the other and watch the ARP who-has/is-at exchange plus the MAC addresses in the `-e` output.
- Lab 2b (host): `arp -a`, then `ndp -an` as a preview of L5. Optional: send a ping with DF set larger than the MTU to see fragmentation-needed behaviour inside a container (`ping -M do -s 1472` / `-s 1473`).

**L3. IPv4 addressing, subnetting/CIDR, private ranges, NAT**
- Concepts: dotted quad, prefix length, network/broadcast, longest-prefix match preview, RFC 1918, 100.64/10 CGNAT, NAT/PAT translation tables, why NAT breaks inbound connections, NAT idle timeouts as a link to keepalives.
- Lab 3a: subnetting drills ([subnetting.net](https://subnetting.net/), [Kurose/Ross interactive](https://gaia.cs.umass.edu/kurose_ross/interactive/)), then `docker network create --subnet 10.10.1.0/24 a` and `--subnet 10.10.2.0/24 b`. Predict and test reachability between them.
- Lab 3b: watch NAT. Compare the container's `ip addr`, the Mac's `ifconfig`, and the public IP that a remote server sees (e.g., `curl https://cloudflare.com/cdn-cgi/trace` prints `ip=`). Sketch the translation chain container → VM → Mac → home router.

**L4. Routing, ICMP, traceroute, MTU/PMTUD**
- Concepts: routing tables, default gateway, longest-prefix match, TTL/hop limit, ICMP types (echo, time exceeded, unreachable, frag-needed), how traceroute works, BGP and anycast at a conceptual level, PMTUD black holes (pointer to [RFC 8899](https://www.rfc-editor.org/rfc/rfc8899.html)).
- Lab 4a: a three-container "router" topology. Container R is attached to networks a and b with `sysctl net.ipv4.ip_forward=1`. Hosts A and B each get `ip route add <other subnet> via <R>`. Run traceroute A→B, then `tcpdump icmp` on R while TTL-limited probes expire.
- Lab 4b (host): `traceroute -n 1.1.1.1` vs `sudo mtr -rwc 20 1.1.1.1`. Discuss why some hops show `* * *` (ICMP rate-limiting or filtering does not mean loss).

**L5. IPv6 essentials**
- Concepts: 128-bit notation and compression, scopes (link-local fe80::/10, ULA, global), SLAAC, NDP replacing ARP, multicast instead of broadcast, no NAT by default, extension headers, no router fragmentation, dual stack and Happy Eyeballs ([RFC 8305](https://www.rfc-editor.org/rfc/rfc8305.html)), adoption (29% of dual-stack requests at Cloudflare in 2025).
- Lab 5a (host): `ifconfig en0 | grep inet6`, `ndp -an`, `ping6 -c2 ff02::1%en0` (all-nodes multicast), `curl -6 -v` vs `curl -4 -v` to a dual-stack site. `dig AAAA`.
- Lab 5b: an IPv6-enabled Docker network (`docker network create --ipv6 --subnet fd00:10::/64 v6`, or OrbStack with IPv6 enabled). `tcpdump icmp6` to watch neighbour solicitation and advertisement.

**L6. UDP and the sockets API (Kotlin)**
- Concepts: ports, 5-tuple, socket/bind/listen/accept/connect, blocking vs NIO vs virtual threads, listen backlog, the kernel send/receive buffers (the reason "write succeeded" proves nothing), UDP message boundaries vs TCP byte stream (framing!), connection refused (RST) vs timeout.
- Lab 6a: a Kotlin TCP echo server and client (`java.net.ServerSocket`/`Socket`, then a virtual-thread-per-connection version). Inspect with `lsof -nP -iTCP:9099` and `netstat -anv -p tcp | grep 9099`. Send two `write()`s and observe one `read()` returning both, to show the stream has no message boundaries, then add length-prefix framing.
- Lab 6b: a Kotlin UDP echo with `DatagramSocket`, used with `nc -u`. Then connect to a closed TCP port (immediate `ConnectException: Connection refused`) and to a blackholed IP such as 10.255.255.1 (connect timeout), and compare both in tcpdump (RST vs repeated SYNs).

**L7. TCP I: connection lifecycle**
- Concepts: 3-way handshake, ISN and sequence/ack numbers, the 11-state machine ([RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html)), FIN vs RST, half-close (`shutdownOutput`), CLOSE_WAIT (= your app forgot to close), TIME_WAIT (2×MSL; Linux 60 s; macOS MSL 15 s), SO_REUSEADDR, ephemeral ports and 4-tuple exhaustion.
- Lab 7a: `sudo tcpdump -i lo0 -nn -S port 9099` while the L6 client connects, sends and closes. Annotate SYN/SYN-ACK/ACK, seq/ack arithmetic and the FIN/ACK sequence. Use Wireshark's "Flow Graph". Have the client close first and confirm TIME_WAIT sits on the client in netstat. Then reverse it. Then make the server "forget" to close and watch CLOSE_WAIT pile up.
- Lab 7b (container): ephemeral port exhaustion. In a Linux container, set `sysctl -w net.ipv4.ip_local_port_range="40000 40100"`, then hammer one destination with new connections (Kotlin loop, or `curl` without keepalive) until `Cannot assign requested address`. Fix it with a pooled HttpClient and compare `ss -tan state time-wait | wc -l`.

**L8. TCP II: performance (flow control, congestion control, Nagle, delayed ACK, HOL)**
- Concepts: receive window and zero-window, window scaling ([RFC 7323](https://www.rfc-editor.org/rfc/rfc7323.html)), BDP, RTO ([RFC 6298](https://www.rfc-editor.org/rfc/rfc6298.html)), slow start/cwnd/fast retransmit ([RFC 5681](https://www.rfc-editor.org/rfc/rfc5681.html)), CUBIC ([RFC 9438](https://www.rfc-editor.org/rfc/rfc9438.html), default on Linux, Windows and Apple), BBR's model-based approach (BBRv3 still a draft), Nagle plus delayed ACK, TCP HOL.
- Lab 8a (container): two netshoot containers running `iperf3`. Add `tc qdisc add dev eth0 root netem delay 50ms loss 1%`, then compare throughput with and without loss, and between `-C cubic` and `-C bbr` if the VM kernel has `tcp_bbr` (check `sysctl net.ipv4.tcp_available_congestion_control`). Plot Wireshark's "TCP Stream Graph → Stevens/tcptrace" to see slow start and loss recovery.
- Lab 8b: a Kotlin Nagle demo. The client does write(header) + write(body) + read(response) in a loop against a server that replies only after the full message. Measure p50/p99 with `TCP_NODELAY` off vs on, and add netem delay to make it obvious. Bonus: a slow reader (sleep between reads) to watch the receiver window shrink to zero in Wireshark (`tcp.analysis.zero_window`).

**L9. DNS**
- Concepts: hierarchy (root → TLD → authoritative), stub vs recursive resolver, iterative vs recursive queries, record types (A, AAAA, CNAME, NS, SOA, MX, TXT, SRV, CAA, HTTPS/SVCB), TTL and caching layers (resolver, OS, JVM 30 s, pool), negative caching ([RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html)), UDP/TCP 53, DoT/DoH/DoQ, DNS-based load balancing ([Google SRE ch. 19](https://sre.google/sre-book/load-balancing-frontend/)).
- Lab 9a: `dig +trace example.com`, then reproduce it by hand: `dig +norecurse @a.root-servers.net com NS`, then the TLD server, then the authoritative server. Run `dig @1.1.1.1 example.com +noall +answer` repeatedly to watch the TTL count down, and `dig nonexistent.example.com` to see the SOA in the authority section (the negative TTL). Use brew dig for `dig cloudflare.com HTTPS`. Optional: [Mess With DNS](https://messwithdns.net/) to create records and watch caching.
- Lab 9b (Java): a Kotlin loop calling `InetAddress.getByName` every second while you change the target, for example via a container running dnsmasq or an `/etc/hosts` edit inside a container. Observe the JVM's 30 s cache, then rerun with `-Dsun.net.inetaddr.ttl=0` or by setting `networkaddress.cache.ttl` (security property). Contrast with a pooled HttpClient connection that keeps hitting the old IP.

**L10. TLS 1.3, certificates, mTLS**
- Concepts: goals (confidentiality, integrity, authentication), 1-RTT handshake (ClientHello with key_share → ServerHello → encrypted EncryptedExtensions/Certificate/CertificateVerify/Finished), HelloRetryRequest, resumption/PSK and 0-RTT (replay risk), SNI and ALPN, ECH ([RFC 9849](https://www.rfc-editor.org/rfc/rfc9849.html)), hybrid PQ key exchange ([RFC 10024](https://www.rfc-editor.org/rfc/rfc10024.html), X25519MLKEM768), X.509 chains and trust stores, validity shrinking ([Let's Encrypt 45-day plan](https://letsencrypt.org/2025/12/02/from-90-to-45/)), mTLS. Byte-level visual: [tls13.xargs.org](https://tls13.xargs.org/). Spec: [RFC 9846](https://www.rfc-editor.org/rfc/rfc9846.html).
- Lab 10a: `$(brew --prefix openssl@3)/bin/openssl s_client -connect cloudflare.com:443 -servername cloudflare.com -alpn h2 -groups X25519MLKEM768 -showcerts -brief`. Read the negotiated group, cipher and chain. Repeat with `-groups x25519` and with `/usr/bin/openssl` (LibreSSL), and compare. Capture with `SSLKEYLOGFILE=keys.log curl ...` (brew curl) and decrypt in Wireshark ([Wireshark TLS wiki](https://wiki.wireshark.org/TLS)).
- Lab 10b: an mTLS mini-PKI. Use openssl to create a root CA, a server cert (with SAN!) and a client cert. Run nginx in a container with `ssl_verify_client on`. Call it from Kotlin `HttpClient` with an `SSLContext` built from a PKCS#12 keystore and truststore. Break it on purpose (wrong SAN, missing intermediate, expired cert, no client cert) and read each error.

**L11. HTTP/1.1 vs HTTP/2 vs HTTP/3 and QUIC**
- Concepts: shared semantics ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)) over different wire formats, persistent connections and the 6-connections-per-host workaround, HTTP/2 binary framing, streams, flow control, HPACK, TCP HOL ([RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html)), QUIC (connection IDs, migration, 1-RTT/0-RTT, per-stream loss isolation, user-space congestion control), QPACK, discovery via Alt-Svc/HTTPS RR, UDP-blocked fallback, adoption (21% of Cloudflare requests in 2025; 41.1% of websites support it in Nov 2026). Visual: [quic.xargs.org](https://quic.xargs.org/).
- Lab 11a: brew curl `--http1.1`, `--http2`, `--http3-only` against cloudflare-quic.com with `-w` timings. Then `curl --parallel --parallel-max 20` fetching 20 URLs over h1.1 vs h2, and count TCP connections in tcpdump (`'tcp[tcpflags] & tcp-syn != 0'`). In Wireshark, filter `quic` and note that you cannot see much without keys.
- Lab 11b: head-of-line blocking under loss. Run a local server with h2 and h3 (e.g., Caddy or nginx with QUIC in a container) and add `tc netem loss 3%` on the server container. Fetch many small objects in parallel over h2 vs h3 and compare tail latency. Java: the same requests through `HttpClient` with `Version.HTTP_2` vs `Version.HTTP_3` (JDK 26+).

**L12. Production networking for app engineers: LBs, proxies, CDNs, timeouts, retries, pooling, plus a debugging capstone**
- Concepts: forward vs reverse proxy, L4 (connection-level, sees TCP/UDP) vs L7 (terminates TLS/HTTP, routes on headers), client IP propagation (XFF/Forwarded, PROXY protocol), health checks, connection draining, sticky sessions, CDN caching (RFC 9111 Cache-Control, Age, Vary), anycast. On the app side: connect / read / total / pool-acquire timeouts, deadline propagation, retries with idempotency, backoff and jitter, retry budgets ([AWS](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/), [Google SRE](https://sre.google/sre-book/addressing-cascading-failures/)), connection pooling, idle-timeout alignment across hops, DNS plus pooling interaction.
- Lab 12a: docker-compose with HAProxy (or nginx) in front of two tiny Kotlin backends. Run it in `mode tcp` (L4) and `mode http` (L7) and compare what the backend sees as the client IP, then enable the PROXY protocol or XFF. Capture on both sides of the proxy to show two separate TCP connections in L7 mode. Kill a backend mid-traffic and watch health checks and retries.
- Lab 12b (capstone incident): set the backend's keep-alive idle timeout to 5 s and the Java HttpClient's to 30 s (`-Djdk.httpclient.keepalive.timeout=30`). Send requests every 6 to 10 s and reproduce intermittent connection-reset errors. Diagnose with tcpdump (FIN from the server, then a request on the dead connection gets an RST) and `ss`/`netstat`. Fix it by aligning timeouts plus a single idempotent retry with jitter. Then add `netem delay 2s` to show why connect, read and total timeouts must be separate.

### Inferences
- Lessons 6 to 8 and 12 are the core for this audience. If the track must shrink to 10, merge L2 into L1 (keep the ARP capture) and fold L5 into L3/L4 as an "IPv6 deltas" section.
- Every lab should start with a prediction ("which side will be in TIME_WAIT?", "how many SYNs will h1.1 open?") before the observation. That is the main intuition-building device.
- Reuse one Kotlin codebase (echo server, client, framing, HttpClient harness) across L6 to L12 so learners build on their own tools.

### Gaps
- Lab 11b's specific server image (Caddy/nginx with HTTP/3) and its configuration were not verified this session. [quic.nginx.org](https://quic.nginx.org/) loads, but I didn't confirm current nginx QUIC config syntax.
- Whether `iperf3 -C bbr` works depends on the Docker/OrbStack VM kernel modules (unverified).
- No lab here covers Wi-Fi specifics or BGP hands-on. Both are deliberately out of scope.

---

## Verified URLs

### Takeaway
Every URL below returned HTTP 200 to a scripted fetch from this machine on 2026-11-07, and its page title matched the expected document. The URLs I read in depth via WebFetch are marked (read).

### Cited Findings
**IETF / RFCs (rfc-editor.org, all 200):**
- https://www.rfc-editor.org/rfc/rfc9293.html (TCP)
- https://www.rfc-editor.org/rfc/rfc9110.html, https://www.rfc-editor.org/rfc/rfc9111.html, https://www.rfc-editor.org/rfc/rfc9112.html, https://www.rfc-editor.org/rfc/rfc9113.html, https://www.rfc-editor.org/rfc/rfc9114.html, https://www.rfc-editor.org/rfc/rfc9204.html, https://www.rfc-editor.org/rfc/rfc9218.html, https://www.rfc-editor.org/rfc/rfc9220.html, https://www.rfc-editor.org/rfc/rfc8441.html
- https://www.rfc-editor.org/rfc/rfc9000.html, https://www.rfc-editor.org/rfc/rfc9001.html, https://www.rfc-editor.org/rfc/rfc9002.html, https://www.rfc-editor.org/rfc/rfc8999.html, https://www.rfc-editor.org/rfc/rfc9312.html
- https://www.rfc-editor.org/rfc/rfc8446.html, https://www.rfc-editor.org/rfc/rfc9846.html (read), https://www.rfc-editor.org/rfc/rfc9849.html (read), https://www.rfc-editor.org/rfc/rfc9848.html, https://www.rfc-editor.org/rfc/rfc10024.html (read), https://www.rfc-editor.org/rfc/rfc8996.html, https://www.rfc-editor.org/rfc/rfc6066.html, https://www.rfc-editor.org/rfc/rfc5280.html
- https://www.rfc-editor.org/rfc/rfc5681.html, https://www.rfc-editor.org/rfc/rfc6298.html, https://www.rfc-editor.org/rfc/rfc7323.html, https://www.rfc-editor.org/rfc/rfc9438.html, https://www.rfc-editor.org/rfc/rfc896.html, https://www.rfc-editor.org/rfc/rfc1122.html, https://www.rfc-editor.org/rfc/rfc8899.html
- https://www.rfc-editor.org/rfc/rfc1034.html, https://www.rfc-editor.org/rfc/rfc1035.html, https://www.rfc-editor.org/rfc/rfc2308.html, https://www.rfc-editor.org/rfc/rfc9499.html, https://www.rfc-editor.org/rfc/rfc9460.html, https://www.rfc-editor.org/rfc/rfc8484.html, https://www.rfc-editor.org/rfc/rfc7858.html, https://www.rfc-editor.org/rfc/rfc9250.html
- https://www.rfc-editor.org/rfc/rfc791.html, https://www.rfc-editor.org/rfc/rfc768.html, https://www.rfc-editor.org/rfc/rfc826.html, https://www.rfc-editor.org/rfc/rfc4632.html, https://www.rfc-editor.org/rfc/rfc1918.html, https://www.rfc-editor.org/rfc/rfc6598.html, https://www.rfc-editor.org/rfc/rfc8200.html, https://www.rfc-editor.org/rfc/rfc4291.html, https://www.rfc-editor.org/rfc/rfc8305.html, https://www.rfc-editor.org/rfc/rfc6335.html, https://www.rfc-editor.org/rfc/rfc8445.html
- https://datatracker.ietf.org/doc/draft-ietf-ccwg-bbr/ (read; shows -07), https://datatracker.ietf.org/doc/rfc10024/ (read), https://datatracker.ietf.org/doc/rfc9846/ (read), https://datatracker.ietf.org/doc/rfc9849/, https://datatracker.ietf.org/wg/ccwg/about/, https://quicwg.org/, https://httpwg.org/specs/
- https://www.iana.org/assignments/tls-parameters/tls-parameters.xhtml (read, supported groups), https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml

**Java:**
- https://openjdk.org/jeps/517, https://inside.java/2026/03/04/jdk-26-http-client/, https://openjdk.org/projects/jdk/27/ (read: GA 2026/09/15), https://openjdk.org/projects/jdk/26/, https://openjdk.org/jeps/444
- https://docs.oracle.com/en/java/javase/25/docs/api/java.net.http/java/net/http/HttpClient.html, https://docs.oracle.com/en/java/javase/25/docs/api/java.net.http/module-summary.html (read: jdk.httpclient.* props), https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/Socket.html, https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/nio/channels/SocketChannel.html, https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/StandardSocketOptions.html, https://docs.oracle.com/en/java/javase/25/docs/api/jdk.net/jdk/net/ExtendedSocketOptions.html, https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/doc-files/net-properties.html
- https://github.com/netty/netty, https://hc.apache.org/httpcomponents-client-5.4.x/ (redirects to 5.6.x)

**Adoption / industry:**
- https://blog.cloudflare.com/radar-2025-year-in-review/ (read), https://blog.cloudflare.com/post-quantum-roadmap/ (read), https://blog.cloudflare.com/encrypted-client-hello/ (read), https://blog.cloudflare.com/pq-2025/, https://blog.cloudflare.com/post-quantum-visibility/
- https://blog.cloudflare.com/how-to-stop-running-out-of-ephemeral-ports-and-start-to-love-long-lived-connections/, https://blog.cloudflare.com/when-tcp-sockets-refuse-to-die/, https://blog.cloudflare.com/this-is-strictly-a-violation-of-the-tcp-specification/, https://blog.cloudflare.com/the-story-of-one-latency-spike/, https://blog.cloudflare.com/the-road-to-quic/, https://blog.cloudflare.com/http3-the-past-present-and-future/
- https://w3techs.com/technologies/details/ce-http3 (read: 41.1%, Nov 2026), https://www.google.com/intl/en/ipv6/statistics.html (loads; numbers are JS-rendered, not read)
- https://letsencrypt.org/2025/12/02/from-90-to-45 (read), https://cabforum.org/working-groups/server/baseline-requirements/requirements/
- https://support.mozilla.org/en-US/kb/understand-encrypted-client-hello

**Learning resources:**
- https://hpbn.co/, https://hpbn.co/building-blocks-of-tcp/, https://hpbn.co/http2/
- https://beej.us/guide/bgnet/, https://beej.us/guide/bgnet/html/
- https://jvns.ca/blog/2015/11/21/why-you-should-understand-a-little-about-tcp/, https://jvns.ca/blog/how-updating-dns-works/, https://jvns.ca/blog/2021/12/04/how-to-use-dig/, https://jvns.ca/blog/2017/06/03/async-io-on-linux--select--poll--and-epoll/, https://wizardzines.com/zines/networking/, https://wizardzines.com/zines/dns/, https://messwithdns.net/
- https://gaia.cs.umass.edu/kurose_ross/index.php, https://gaia.cs.umass.edu/kurose_ross/interactive/, https://subnetting.net/
- https://developer.mozilla.org/en-US/docs/Web/HTTP, https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Evolution_of_HTTP, https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Alt-Svc
- https://tls13.xargs.org/, https://quic.xargs.org/, https://smallstep.com/blog/everything-pki/
- https://vincent.bernat.ch/en/blog/2014-tcp-time-wait-state-linux (read)
- https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/ (redirects to builder.aws.com), https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/, https://sre.google/sre-book/addressing-cascading-failures/, https://sre.google/sre-book/load-balancing-frontend/
- https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/intro/terminology, https://nginx.org/en/docs/http/ngx_http_upstream_module.html, https://www.haproxy.org/download/3.0/doc/proxy-protocol.txt

**Tools:**
- https://www.wireshark.org/docs/wsug_html_chunked/, https://www.wireshark.org/docs/man-pages/tshark.html, https://wiki.wireshark.org/TLS, https://www.wireshark.org/download.html
- https://www.tcpdump.org/manpages/tcpdump.1.html, https://www.tcpdump.org/manpages/pcap-filter.7.html
- https://curl.se/docs/http3.html, https://everything.curl.dev/
- https://formulae.brew.sh/formula/curl, https://formulae.brew.sh/formula/bind, https://formulae.brew.sh/formula/mtr, https://formulae.brew.sh/formula/iperf3, https://formulae.brew.sh/formula/openssl@3, https://formulae.brew.sh/formula/wireshark, https://formulae.brew.sh/cask/wireshark-app, https://brew.sh/
- https://docs.docker.com/desktop/features/networking/ (read), https://docs.docker.com/engine/network/, https://docs.docker.com/engine/network/drivers/bridge/, https://docs.orbstack.dev/docker/network (read), https://github.com/nicolaka/netshoot (read)
- https://man7.org/linux/man-pages/man8/tc-netem.8.html, https://man7.org/linux/man-pages/man7/tcp.7.html (read: keepalive defaults), https://man7.org/linux/man-pages/man8/ss.8.html, https://man7.org/linux/man-pages/man7/socket.7.html, https://www.kernel.org/doc/html/latest/networking/ip-sysctl.html (read: port range, tw_reuse), https://pypi.org/project/tcconfig/
- https://cloudflare-quic.com/ (HTTP/3 200 confirmed with brew curl), https://quic.nginx.org/, https://http3check.net/
- https://github.com/google/bbr

### Inferences
- **Do not use these (failed on 2026-11-07):** `https://radar.cloudflare.com/adoption-and-usage` and `https://radar.cloudflare.com/year-in-review/2025` returned 403 to automated fetch (they probably work in a browser). `https://blog.cloudflare.com/a-brief-primer-on-tcp-congestion-control/`, `https://blog.cloudflare.com/rfc-8446-tls-1-3/`, `https://jvns.ca/blog/2016/07/14/whats-tcp-nagle/`, `https://letsencrypt.org/docs/certificate-lifetimes/` and `https://square.github.io/okhttp/` all returned 404.

### Gaps
- An HTTP 200 plus a matching title confirms the page loads and is the right document. For URLs not marked (read), I did not check every claim the lesson might attribute to them.

---

## Teaching notes

### Takeaway
Lead with prediction-then-observation labs, keep OSI as vocabulary only, cut legacy protocol history, and spend the saved time on the failure modes backend engineers actually hit: socket states, keepalive and idle-timeout mismatches, DNS caching layers, TLS chain and SNI errors, retry storms, and HOL under loss.

### Cited Findings
- Misconceptions to address explicitly, each with a lab: ACK semantics, UDP speed, TIME_WAIT, port exhaustion, keepalive types, DNS "propagation", HTTP/2 HOL, Nagle/delayed ACK, SNI visibility, retries, timeouts, L7 client IP, 0-RTT replay, refused vs timeout. Sources are in section 3 (e.g., [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html), [Bernat](https://vincent.bernat.ch/en/blog/2014-tcp-time-wait-state-linux), [RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html), [AWS Builders' Library](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)).
- Facts that changed recently and that older material gets wrong: TLS 1.3 = RFC 9846 (July 2026); ECH = RFC 9849 (March 2026); X25519MLKEM768 standardized in RFC 10024 (Aug 2026) and IANA-Recommended; Kyber draft code point obsolete; Java HttpClient has HTTP/3 since JDK 26; Let's Encrypt moving to 45-day certs (2026–2028) — see section 2 sources. HPBN (hpbn.co) predates these.

### Inferences
**Analogies that work**
- *IP = postcards; TCP = a numbered, acknowledged conversation built from postcards.* Each postcard (packet) can be lost, duplicated or reordered. TCP numbers the bytes, not the postcards. This keeps "stream, not messages" front and centre.
- *Receive window = how much room is left on the receiver's desk; congestion window = how much traffic the road can take right now.* Flow control protects the receiver and congestion control protects the network. The sender sends min(rwnd, cwnd).
- *BDP = the volume of a pipe.* Bandwidth × RTT is how many bytes must be "in flight" to fill it. This explains window scaling and why long-RTT links need big buffers.
- *TIME_WAIT = holding the door for 2×MSL so stragglers from the last conversation aren't mistaken for the next one.* It is the closer's courtesy, not a leak.
- *DNS = a hierarchy of phone books with expiry dates stamped on every entry you copy.* Nobody pushes updates. Copies expire, and some copy-holders (the JVM, connection pools) use their own expiry rules.
- *HTTP/2 over TCP = many lanes merged into one tunnel, so one crash blocks every lane. HTTP/3/QUIC = separate lanes in the same tunnel.*
- *L4 LB = a mail-room sorter that routes envelopes without opening them. L7 LB = a receptionist who opens the letter, reads it and writes a new one to the right department.* This explains why the backend loses the client IP.
- *TLS certificate chain = a notarized letter of introduction chain ending at someone already in your contacts (trust store).*

**What to cut or minimise**
- OSI layers 5 and 6 as separate topics, token ring, FDDI, classful addressing (one paragraph of history at most), RIP/OSPF internals (mention that they exist; BGP/anycast only conceptually), IPv4 header options, ATM/frame relay, legacy TLS ≤1.1 handshakes (just say they're deprecated per [RFC 8996](https://www.rfc-editor.org/rfc/rfc8996.html)), HTTP/2 server push (status not verified; at most a footnote), SCTP, multicast routing.
- Don't teach the full TCP option zoo. Teach MSS, window scale, SACK and timestamps, because they show up in every SYN in Wireshark.
- Don't spend time on raw ICMP tooling beyond ping, traceroute and mtr.

**Practical pedagogy**
- Every lab: predict → run → capture → explain → break it on purpose.
- Use the same Kotlin echo/HTTP harness throughout. Show `netstat`/`lsof` output on the mac and `ss` inside containers side by side so learners know both toolsets.
- Include an environment pre-flight lesson-zero checklist: brew curl on PATH with `curl --version | grep HTTP3`, brew `bind` dig, brew openssl@3, Wireshark, `sudo tcpdump -D`, a container runtime with `--cap-add NET_ADMIN` netem smoke test, JDK 25 plus JDK 26+.
- Flag platform differences as learning moments: macOS TIME_WAIT 30 s vs Linux 60 s, ephemeral ranges (49152–65535 vs 32768–60999), and `.port` vs `:port` in netstat output.

### Gaps
- None of the labs have been executed end-to-end in a container on this machine (no Docker installed). The writer or QA should run each container lab once on Docker Desktop and on OrbStack before publishing.
