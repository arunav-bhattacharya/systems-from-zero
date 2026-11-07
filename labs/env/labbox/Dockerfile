# The lab box: Ubuntu 24.04 with JDK 25 and the Linux tools the networking and OS lessons use.
# Native arm64 on Apple Silicon (never --platform linux/amd64: emulation breaks strace and perf).
FROM eclipse-temurin:25-jdk-noble

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      strace ltrace gdb procps psmisc sysstat util-linux lsof htop file less vim-tiny man-db \
      build-essential python3 \
      iproute2 iputils-ping iputils-tracepath traceroute mtr-tiny dnsutils curl netcat-openbsd socat \
      openssl ca-certificates tcpdump tshark ethtool iptables nftables conntrack bridge-utils \
      stress-ng fio time numactl cgroup-tools libcap2-bin bpfcc-tools bpftrace \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /labs
CMD ["bash", "-l"]
