// bulk.c: what would it cost to ask the kernel for every allocation?
// Times 100,000 rounds of mmap + one write + munmap of a page against malloc + one write + free of 64 bytes.
//   gcc -O2 -o /tmp/bulk os/c/l08/bulk.c && /tmp/bulk
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>

#define N 100000

static double now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e9 + ts.tv_nsec;
}

static char *volatile sink;                                  // stops the compiler from removing the pairs

int main(void) {
    double t0 = now_ns();
    for (int i = 0; i < N; i++) {
        char *p = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        p[0] = 1;                                            // first touch: a page fault and a zeroed page
        sink = p;
        munmap(p, 4096);
    }
    double t1 = now_ns();
    for (int i = 0; i < N; i++) {
        char *p = malloc(64);                                // from malloc's own free lists: no kernel
        p[0] = 1;
        sink = p;
        free(p);
    }
    double t2 = now_ns();
    printf("mmap + write + munmap: %6.0f ns each\n", (t1 - t0) / N);
    printf("malloc + write + free: %6.0f ns each\n", (t2 - t1) / N);
    return 0;
}
