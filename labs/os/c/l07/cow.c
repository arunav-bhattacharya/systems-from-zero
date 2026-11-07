// cow.c: fork a process that holds 512 MB, then let the child write to some of it.
// fork shares every page; the kernel copies a page only when one side writes to it.
//   gcc -O2 -o /tmp/cow os/c/l07/cow.c
//   /tmp/cow 512 4      512 MB, the child writes one byte in every 4th page
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static double now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e3 + ts.tv_nsec / 1e6;
}

static long minor_faults(void) {
    struct rusage ru;
    getrusage(RUSAGE_SELF, &ru);
    return ru.ru_minflt;
}

// one "Name:   123 kB" line from /proc/self/smaps_rollup, in MB
static long rollup_mb(const char *name) {
    char line[256], key[64];
    long kb = -1, v;
    FILE *f = fopen("/proc/self/smaps_rollup", "r");
    while (fgets(line, sizeof line, f))
        if (sscanf(line, "%63[^:]: %ld kB", key, &v) == 2 && strcmp(key, name) == 0) { kb = v; break; }
    fclose(f);
    return kb / 1024;
}

static void report(const char *who) {
    printf("%-22s Rss %4ld MB  Pss %4ld MB  Shared %4ld MB  Private %4ld MB\n", who,
           rollup_mb("Rss"), rollup_mb("Pss"), rollup_mb("Shared_Dirty"), rollup_mb("Private_Dirty"));
}

int main(int argc, char **argv) {
    size_t mb = argc > 1 ? atol(argv[1]) : 512;
    long stride = argc > 2 ? atol(argv[2]) : 4;
    size_t size = mb << 20;
    long page = sysconf(_SC_PAGESIZE);
    long pages = size / page;
    setvbuf(stdout, NULL, _IOLBF, 0);                        // print each line now, before fork copies the buffer

    char *p = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) { perror("mmap"); return 1; }
    madvise(p, size, MADV_NOHUGEPAGE);                       // 4 KB pages, so each copy is one page
    memset(p, 1, size);                                      // touch every page: all of it is in RAM now

    // the simplest fork would copy everything; this is what copying 512 MB costs
    char *copy = malloc(size);
    double t0 = now_ms();
    memcpy(copy, p, size);
    printf("copying %zu MB with memcpy: %.0f ms\n", mb, now_ms() - t0);
    free(copy);

    report("parent before fork");
    t0 = now_ms();
    pid_t pid = fork();                                      // shares all 131,072 pages, copies none
    if (pid == 0) {
        printf("fork returned in the child after %.1f ms\n", now_ms() - t0);
        report("child after fork");
        long f0 = minor_faults();
        double t1 = now_ms();
        for (long i = 0; i < pages; i += stride) p[i * page] = 2;   // first write to a shared page: a copy
        double ms = now_ms() - t1;
        long faults = minor_faults() - f0;
        printf("child wrote to %ld of %ld pages: %ld page faults in %.0f ms (%.2f us each)\n",
               (pages + stride - 1) / stride, pages, faults, ms, ms * 1000 / faults);
        report("child after writes");
        _exit(0);
    }
    waitpid(pid, NULL, 0);
    report("parent after child exit");
    return 0;
}
