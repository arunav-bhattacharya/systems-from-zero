#!/usr/bin/env python3
"""A tiny DNS server for lesson 9 of the networking track, in plain Python (the lab box has no BIND).

It runs in one of two roles:

  python3 /labs/env/net/dns.py auth 10.10.1.2 /labs/env/net/pay.test.zone
      The authoritative server for one made-up zone. It copies the zone file to /tmp once and
      rereads that copy on every query, so an edit to /tmp/pay.test.zone takes effect at once.

  python3 /labs/env/net/dns.py resolver 10.10.1.20 10.10.1.2
      A caching resolver. On a cache miss it asks the authoritative server at 10.10.1.2 (without
      recursion), keeps the answer for its TTL, and keeps "no such name" for the SOA's minimum
      (RFC 2308). Every query is logged to /tmp/resolver.log.

Only class IN, records A and SOA, over UDP port 53: enough to watch TTLs and caches, nothing more.
Neither role compresses names in what it sends (RFC 1035 allows that), but both read compressed ones.
"""
import shutil
import socket
import struct
import sys
import time

A, NS, SOA = 1, 2, 6
NOERROR, NXDOMAIN, REFUSED = 0, 3, 5


def encode_name(name):
    out = b""
    for label in name.rstrip(".").split("."):
        if label:
            out += bytes([len(label)]) + label.encode()
    return out + b"\x00"


def read_name(msg, pos):
    """Returns (name, position after the name), following compression pointers."""
    labels, end = [], None
    while True:
        n = msg[pos]
        if n & 0xC0 == 0xC0:                       # a pointer: the rest of the name is elsewhere
            if end is None:
                end = pos + 2
            pos = ((n & 0x3F) << 8) | msg[pos + 1]
        elif n == 0:
            return ".".join(labels).lower() + ".", (end if end is not None else pos + 1)
        else:
            labels.append(msg[pos + 1:pos + 1 + n].decode())
            pos += 1 + n


def parse(msg):
    """Header fields, the question and every record of a DNS message."""
    ident, flags, qd, an, ns, ar = struct.unpack("!6H", msg[:12])
    qname, pos = read_name(msg, 12)
    qtype, _ = struct.unpack("!2H", msg[pos:pos + 4])
    pos += 4
    records = []
    for section, count in (("answer", an), ("authority", ns), ("additional", ar)):
        for _ in range(count):
            name, pos = read_name(msg, pos)
            rtype, _, ttl, rdlen = struct.unpack("!HHIH", msg[pos:pos + 10])
            pos += 10
            rdata_pos = pos
            pos += rdlen
            records.append({"section": section, "name": name, "type": rtype, "ttl": ttl,
                            "rdata": rdata(msg, rtype, rdata_pos, rdlen)})
    return {"id": ident, "flags": flags, "qname": qname, "qtype": qtype, "records": records}


def rdata(msg, rtype, pos, length):
    if rtype == A:
        return socket.inet_ntoa(msg[pos:pos + 4])
    if rtype == SOA:
        mname, p = read_name(msg, pos)
        rname, p = read_name(msg, p)
        return [mname, rname] + list(struct.unpack("!5I", msg[p:p + 20]))
    return msg[pos:pos + length]


def encode_record(r):
    if r["type"] == A:
        data = socket.inet_aton(r["rdata"])
    elif r["type"] == SOA:
        data = encode_name(r["rdata"][0]) + encode_name(r["rdata"][1]) + struct.pack("!5I", *r["rdata"][2:])
    else:
        data = r["rdata"]
    return encode_name(r["name"]) + struct.pack("!HHIH", r["type"], 1, max(0, int(r["ttl"])), len(data)) + data


def build(ident, flags, rcode, qname, qtype, answers=(), authority=()):
    header = struct.pack("!6H", ident, flags | rcode, 1, len(answers), len(authority), 0)
    question = encode_name(qname) + struct.pack("!2H", qtype, 1)
    return header + question + b"".join(encode_record(r) for r in list(answers) + list(authority))


def load_zone(path):
    """Lines of `name TTL type data`; `;` starts a comment."""
    records = []
    for line in open(path):
        line = line.split(";")[0].strip()
        if not line:
            continue
        name, ttl, rtype, *data = line.split()
        if rtype == "A":
            records.append({"name": name.lower(), "type": A, "ttl": int(ttl), "rdata": data[0]})
        elif rtype == "SOA":
            records.append({"name": name.lower(), "type": SOA, "ttl": int(ttl),
                            "rdata": [data[0].lower(), data[1].lower()] + [int(x) for x in data[2:7]]})
    return records


def serve_auth(ip, zone_source):
    zone_path = "/tmp/" + zone_source.split("/")[-1]
    shutil.copy(zone_source, zone_path)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, 53))
    while True:
        msg, client = sock.recvfrom(512)
        q = parse(msg)
        zone = load_zone(zone_path)                  # reread on every query: edits apply at once
        soa = next(r for r in zone if r["type"] == SOA)
        origin = soa["name"]
        rd = q["flags"] & 0x0100
        flags = 0x8000 | 0x0400 | rd                 # QR (a response) and AA (authoritative)
        if not (q["qname"] == origin or q["qname"].endswith("." + origin)):
            sock.sendto(build(q["id"], 0x8000 | rd, REFUSED, q["qname"], q["qtype"]), client)
            continue
        same_name = [r for r in zone if r["name"] == q["qname"]]
        answers = [r for r in same_name if r["type"] == q["qtype"]]
        negative = dict(soa, ttl=min(soa["ttl"], soa["rdata"][6]))   # RFC 2308: the smaller of the two
        if answers:
            sock.sendto(build(q["id"], flags, NOERROR, q["qname"], q["qtype"], answers), client)
        elif same_name:                              # the name exists, but has no record of this type
            sock.sendto(build(q["id"], flags, NOERROR, q["qname"], q["qtype"], authority=[negative]), client)
        else:
            sock.sendto(build(q["id"], flags, NXDOMAIN, q["qname"], q["qtype"], authority=[negative]), client)


def serve_resolver(ip, upstream):
    cache = {}                                       # (name, type) -> (expires_at, rcode, records)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, 53))
    up = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    up.settimeout(2)
    log = open("/tmp/resolver.log", "a", buffering=1)
    ident = 1
    while True:
        msg, client = sock.recvfrom(512)
        q = parse(msg)
        key = (q["qname"], q["qtype"])
        now = time.time()
        entry = cache.get(key)
        if entry and entry[0] > now:
            left = entry[0] - now
            what = "cache hit, %d s left" % left
        else:
            ident = (ident + 1) & 0xFFFF
            query = build(ident, 0, NOERROR, q["qname"], q["qtype"])       # RD off: just ask, don't recurse
            try:
                up.sendto(query, (upstream, 53))
                reply = parse(up.recvfrom(512)[0])
            except socket.timeout:
                sock.sendto(build(q["id"], 0x8080 | (q["flags"] & 0x0100), 2, q["qname"], q["qtype"]), client)
                log.write("%s %s: no answer from %s\n" % (time.strftime("%H:%M:%S"), q["qname"], upstream))
                continue
            rcode = reply["flags"] & 0x000F
            records = reply["records"]
            if rcode not in (NOERROR, NXDOMAIN):        # e.g. REFUSED for a name outside the zone
                sock.sendto(build(q["id"], 0x8080 | (q["flags"] & 0x0100), rcode, q["qname"], q["qtype"]), client)
                log.write("%s %s: rcode %d from %s, not cached\n" % (time.strftime("%H:%M:%S"), q["qname"], rcode, upstream))
                continue
            if rcode == NOERROR and any(r["section"] == "answer" for r in records):
                keep = min(r["ttl"] for r in records if r["section"] == "answer")
            else:                                    # negative: keep it for the SOA's TTL
                keep = min([r["ttl"] for r in records if r["type"] == SOA] or [0])
            cache[key] = entry = (now + keep, rcode, records)
            left = keep
            what = "cache miss, asked %s, keeping it %d s" % (upstream, keep)
        _, rcode, records = entry
        aged = [dict(r, ttl=int(left)) for r in records]                  # every TTL counts down together
        answers = [r for r in aged if r["section"] == "answer"]
        authority = [r for r in aged if r["section"] == "authority"]
        flags = 0x8000 | 0x0080 | (q["flags"] & 0x0100)                    # QR, RA (recursion available), RD
        sock.sendto(build(q["id"], flags, rcode, q["qname"], q["qtype"], answers, authority), client)
        log.write("%s %s %s\n" % (time.strftime("%H:%M:%S"), q["qname"], what))


if __name__ == "__main__":
    role = sys.argv[1] if len(sys.argv) > 1 else ""
    if role == "auth" and len(sys.argv) == 4:
        serve_auth(sys.argv[2], sys.argv[3])
    elif role == "resolver" and len(sys.argv) == 4:
        serve_resolver(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
