// tlb.c: what a TLB miss costs. Visit one cache line in each page of a buffer, in random
// order, so every access lands on a different page. Run it with 4 KB pages, then with
// 2 MB huge pages. The data cache sees the same lines both times; only the number of
// address translations the TLB has to hold changes.
//   gcc -O2 -o /tmp/tlb os/c/l06/tlb.c
//   /tmp/tlb 4k; /tmp/tlb huge
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>

static double now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e9 + ts.tv_nsec;
}

static double chase(size_t mb, int huge) {
    size_t size = mb << 20, page = 4096, pages = size / page;
    char *buf = mmap(NULL, size + (2 << 20), PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    char *p = (char *)(((uintptr_t)buf + (2 << 20) - 1) & ~(uintptr_t)((2 << 20) - 1));   // 2 MB aligned
    madvise(p, size, huge ? MADV_HUGEPAGE : MADV_NOHUGEPAGE);
    memset(p, 0, size);                                       // fault everything in first

    size_t *order = malloc(pages * sizeof *order);            // a random cycle through all pages
    for (size_t i = 0; i < pages; i++) order[i] = i;
    srand(42);
    for (size_t i = pages - 1; i > 0; i--) { size_t j = rand() % (i + 1); size_t t = order[i]; order[i] = order[j]; order[j] = t; }
    // one 64-byte line per page, at a different place in each page so the visits spread over the cache
    #define SLOT(pg) ((char **)(p + (pg) * page + (((pg) * 7) % 64) * 64))
    for (size_t i = 0; i < pages; i++)                        // each visited line holds the address of the next one
        *SLOT(order[i]) = (char *)SLOT(order[(i + 1) % pages]);
    char **cur = SLOT(order[0]);
    free(order);
    long steps = 20000000;
    double t0 = now_ns();
    for (long i = 0; i < steps; i++) cur = (char **)*cur;     // one dependent load per page visit
    double ns = (now_ns() - t0) / steps;
    if (cur == NULL) puts("unreachable");
    munmap(buf, size + (2 << 20));
    return ns;
}

int main(int argc, char **argv) {
    size_t sizes[] = {1, 16, 64, 256, 1024};
    printf("buffer    pages(4 KB)   4 KB pages   2 MB pages\n");
    for (int i = 0; i < 5; i++) {
        double small = chase(sizes[i], 0), huge = chase(sizes[i], 1);
        printf("%5zu MB  %10zu   %7.1f ns   %7.1f ns\n", sizes[i], (sizes[i] << 20) / 4096, small, huge);
    }
    return 0;
}
