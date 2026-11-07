package sfz.net.l01

import java.nio.ByteBuffer

private fun u8(b: Byte): Int = b.toInt() and 0xff
private fun u16(buf: ByteBuffer, at: Int): Int = buf.getShort(at).toInt() and 0xffff
private fun u32(buf: ByteBuffer, at: Int): Long = buf.getInt(at).toLong() and 0xffffffffL

private fun mac(bytes: ByteArray, from: Int): String =
    (from until from + 6).joinToString(":") { "%02x".format(u8(bytes[it])) }

private fun dotted(bytes: ByteArray, from: Int): String =
    (from until from + 4).joinToString(".") { u8(bytes[it]).toString() }

fun parseEthernet(frame: ByteArray): EthernetFrame {
    require(frame.size >= 14) { "an Ethernet header is 14 bytes, got ${frame.size}" }
    val buf = ByteBuffer.wrap(frame)                 // big-endian, like the wire
    return EthernetFrame(
        dst = mac(frame, 0),                         // destination comes first, so a switch can decide early
        src = mac(frame, 6),
        etherType = u16(buf, 12),
        payload = frame.copyOfRange(14, frame.size),
    )
}

fun parseIpv4(packet: ByteArray): Ipv4Packet {
    val buf = ByteBuffer.wrap(packet)
    val version = u8(packet[0]) shr 4
    val headerLength = (u8(packet[0]) and 0x0f) * 4   // IHL counts 32-bit words
    val totalLength = u16(buf, 2)
    require(version == 4) { "not IPv4: version $version" }
    require(headerLength >= 20 && totalLength >= headerLength && totalLength <= packet.size) {
        "bad lengths: header $headerLength, total $totalLength, have ${packet.size}"
    }
    return Ipv4Packet(
        version = version,
        headerLength = headerLength,
        totalLength = totalLength,
        dontFragment = u8(packet[6]) and 0x40 != 0,
        ttl = u8(packet[8]),
        protocol = u8(packet[9]),
        headerChecksum = u16(buf, 10),
        src = dotted(packet, 12),
        dst = dotted(packet, 16),
        // stop at totalLength: anything after it is Ethernet padding, not data
        payload = packet.copyOfRange(headerLength, totalLength),
    )
}

fun parseTcp(segment: ByteArray): TcpSegment {
    val buf = ByteBuffer.wrap(segment)
    val headerLength = (u8(segment[12]) shr 4) * 4    // data offset, also in 32-bit words
    require(headerLength >= 20 && headerLength <= segment.size) { "bad TCP header length $headerLength" }
    return TcpSegment(
        srcPort = u16(buf, 0),                         // 57236 is negative as a signed short
        dstPort = u16(buf, 2),
        seq = u32(buf, 4),                             // above 2^31 half the time: needs a Long
        ack = u32(buf, 8),
        headerLength = headerLength,
        flags = TcpFlag.from(u8(segment[13])),
        window = u16(buf, 14),
        payload = segment.copyOfRange(headerLength, segment.size),   // skip the options too
    )
}

fun ipv4Checksum(header: ByteArray): Int {
    var sum = 0L
    for (i in 0 until header.size - 1 step 2) {
        if (i == 10) continue                          // the checksum field counts as zero
        sum += (u8(header[i]) shl 8) or u8(header[i + 1])
    }
    while (sum shr 16 != 0L) sum = (sum and 0xffff) + (sum shr 16)   // fold carries back in
    return sum.inv().toInt() and 0xffff                // one's complement of the sum
}

fun decapsulate(frame: ByteArray): Layers {
    val eth = parseEthernet(frame)
    require(eth.etherType == 0x0800) { "EtherType 0x%04x is not IPv4".format(eth.etherType) }
    val ip = parseIpv4(eth.payload)
    require(ip.protocol == 6) { "IP protocol ${ip.protocol} is not TCP" }
    return Layers(eth, ip, parseTcp(ip.payload))
}
