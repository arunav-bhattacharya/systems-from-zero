// touch.c: reserve memory, then touch it one page at a time, and count the page faults.
// mmap only reserves addresses. The kernel finds a physical page on the first touch.
//   gcc -O2 -o /tmp/touch os/c/l06/touch.c
//   /tmp/touch 1024 none      reserve 1 GB, touch nothing
//   /tmp/touch 1024 4k        touch one byte in every 4 KB page
//   /tmp/touch 1024 huge      the same, but ask for 2 MB transparent huge pages
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>

static long minor_faults(void) {
    struct rusage ru;
    getrusage(RUSAGE_SELF, &ru);
    return ru.ru_minflt;
}

// one "Name:   123 kB" line from /proc/self/status: VmRSS is resident memory, VmPTE the page tables
static long status_kb(const char *name) {
    char line[256], key[64];
    long kb = -1, v;
    FILE *f = fopen("/proc/self/status", "r");
    while (fgets(line, sizeof line, f))
        if (sscanf(line, "%63[^:]: %ld kB", key, &v) == 2 && strcmp(key, name) == 0) { kb = v; break; }
    fclose(f);
    return kb;
}

static double now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e3 + ts.tv_nsec / 1e6;
}

int main(int argc, char **argv) {
    size_t mb = argc > 1 ? atol(argv[1]) : 1024;
    const char *mode = argc > 2 ? argv[2] : "4k";
    size_t size = mb << 20;
    long page = sysconf(_SC_PAGESIZE);

    // reserve size bytes of address space; nothing is in RAM yet
    char *p = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) { perror("mmap"); return 1; }
    madvise(p, size, strcmp(mode, "huge") == 0 ? MADV_HUGEPAGE : MADV_NOHUGEPAGE);
    printf("reserved %zu MB at %p, page size %ld bytes, RSS %ld MB, page tables %ld KB\n",
           mb, (void *)p, page, status_kb("VmRSS") / 1024, status_kb("VmPTE"));

    long f0 = minor_faults();
    double t0 = now_ms();
    if (strcmp(mode, "none") != 0)
        for (size_t off = 0; off < size; off += page) p[off] = 1;   // first write to each page: a fault
    double ms = now_ms() - t0;
    long faults = minor_faults() - f0;

    printf("touched (%s): %ld page faults in %.0f ms", mode, faults, ms);
    if (faults > 1000) printf(" (%.2f us each)", ms * 1000 / faults);
    printf(", RSS %ld MB, page tables %ld KB\n", status_kb("VmRSS") / 1024, status_kb("VmPTE"));
    return 0;
}
