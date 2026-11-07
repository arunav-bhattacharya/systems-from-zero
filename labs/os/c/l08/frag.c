// frag.c: allocate 200,000 small blocks, free most of them, and watch RSS not come down.
//   gcc -O2 -o /tmp/frag os/c/l08/frag.c
//   /tmp/frag 32       keep every 32nd block, free the rest
//   /tmp/frag 200000   keep only the last block
#include <malloc.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define BLOCKS 200000
#define SIZE 1000

static char *heap_start;

static void report(const char *what) {
    char line[256];
    long kb = -1;
    FILE *f = fopen("/proc/self/status", "r");
    while (fgets(line, sizeof line, f))
        if (sscanf(line, "VmRSS: %ld kB", &kb) == 1) break;
    fclose(f);
    // sbrk(0) is the current end of the heap: everything malloc got from brk lies below it
    printf("%-24s RSS %4ld MB, heap %4ld MB\n", what, kb / 1024, (long)((char *)sbrk(0) - heap_start) >> 20);
}

int main(int argc, char **argv) {
    long keep = argc > 1 ? atol(argv[1]) : 32;
    static char *block[BLOCKS];
    char label[64];
    setvbuf(stdout, NULL, _IOLBF, 0);
    heap_start = sbrk(0);
    report("start:");

    for (int i = 0; i < BLOCKS; i++) { block[i] = malloc(SIZE); memset(block[i], 1, SIZE); }
    snprintf(label, sizeof label, "malloc %d x %d B:", BLOCKS, SIZE);
    report(label);

    long kept = 0;
    for (int i = 0; i < BLOCKS; i++) {
        if (i % keep == keep - 1) { kept++; continue; }      // a few long-lived blocks stay
        free(block[i]);
    }
    snprintf(label, sizeof label, "free all but %ld:", kept);
    report(label);

    malloc_trim(0);                                          // ask glibc to give back whole free pages
    report("after malloc_trim(0):");

    for (int i = 0; i < BLOCKS; i++)
        if (i % keep == keep - 1) free(block[i]);
    report("free the rest:");
    return 0;
}
