// promise.c: ask for far more memory than the machine has, then use some of it.
// The kernel says yes to the request (overcommit) and finds RAM page by page as it is touched.
//   gcc -O2 -o /tmp/promise os/c/l07/promise.c
//   /tmp/promise 100 0       reserve 100 GB, touch nothing
//   /tmp/promise 4 1024      reserve 4 GB, then touch 1 GB of it, 64 MB at a time
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

// one "Name:   123 kB" line from a /proc file, in MB
static long field_mb(const char *path, const char *name) {
    char line[256], key[64];
    long kb = -1, v;
    FILE *f = fopen(path, "r");
    while (fgets(line, sizeof line, f))
        if (sscanf(line, "%63[^:]: %ld kB", key, &v) == 2 && strcmp(key, name) == 0) { kb = v; break; }
    fclose(f);
    return kb / 1024;
}

static void commit(const char *when) {
    printf("%-16s CommitLimit %6ld MB   Committed_AS %7ld MB   MemTotal %5ld MB\n", when,
           field_mb("/proc/meminfo", "CommitLimit"), field_mb("/proc/meminfo", "Committed_AS"),
           field_mb("/proc/meminfo", "MemTotal"));
}

int main(int argc, char **argv) {
    size_t gb = argc > 1 ? atol(argv[1]) : 100;
    size_t touch_mb = argc > 2 ? atol(argv[2]) : 0;
    size_t size = gb << 30;
    setvbuf(stdout, NULL, _IOLBF, 0);

    FILE *f = fopen("/proc/sys/vm/overcommit_memory", "r");
    int mode = -1;
    if (f) { if (fscanf(f, "%d", &mode) != 1) mode = -1; fclose(f); }
    printf("vm.overcommit_memory = %d\n", mode);
    commit("before mmap");
    char *p = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) { perror("mmap"); return 1; }
    printf("mmap of %zu GB returned %p\n", gb, (void *)p);
    commit("after mmap");

    for (size_t off = 0; off < (touch_mb << 20); off += 4096) {
        p[off] = 1;                                          // the kernel finds a frame now, or kills us
        if ((off + 4096) % (64 << 20) == 0)
            printf("touched %4zu MB, RSS %4ld MB\n", (off + 4096) >> 20, field_mb("/proc/self/status", "VmRSS"));
    }
    return 0;
}
