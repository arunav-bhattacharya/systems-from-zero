#!/usr/bin/env python3
"""Send one IPv6 Router Advertisement: the message a router multicasts so that hosts can give
themselves an address (SLAAC). Lesson 5 of the networking track runs it on `api`, which plays the router.

usage: python3 /labs/env/net/send-ra.py PREFIX [IFACE]     e.g. 2001:db8:6::/64 eth0
"""
import ipaddress
import socket
import struct
import sys

net = ipaddress.ip_network(sys.argv[1] if len(sys.argv) > 1 else "2001:db8:6::/64")
iface = sys.argv[2] if len(sys.argv) > 2 else "eth0"
index = socket.if_nametoindex(iface)

# ICMPv6 type 134, Router Advertisement: suggested hop limit 64, no flags, router lifetime 1800 s
# (hosts may use this router as their default route), reachable time and retrans timer unspecified.
# The kernel computes the ICMPv6 checksum for raw ICMPv6 sockets, so it stays 0 here.
ra = struct.pack("!BBHBBHII", 134, 0, 0, 64, 0, 1800, 0, 0)
# Prefix Information option (type 3, length 4 x 8 bytes). Flags 0xC0: on-link (L) and autonomous (A),
# so every host on the link may build its own address in this prefix. Valid 1 day, preferred 4 hours.
ra += struct.pack("!BBBBIII", 3, 4, net.prefixlen, 0xC0, 86400, 14400, 0) + net.network_address.packed

s = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_ICMPV6)
s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 255)  # hosts drop an RA with any other hop limit
s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, index)
s.sendto(ra, ("ff02::1", 0, 0, index))                               # ff02::1: every node on this link
print(f"sent a Router Advertisement for {net} to ff02::1 on {iface}")
