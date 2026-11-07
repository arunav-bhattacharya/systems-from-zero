// hog.c: takes memory 16 MB at a time and writes to every page, until it holds MAX MB or the
// kernel stops it.
//   gcc -O2 -o /tmp/hog os/c/l12/hog.c && /tmp/hog 256
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    int max = argc > 1 ? atoi(argv[1]) : 256;
    setvbuf(stdout, NULL, _IOLBF, 0);
    for (int mb = 16; mb <= max; mb += 16) {
        char *p = malloc(16 << 20);
        if (!p) { printf("malloc failed at %d MB\n", mb); return 1; }
        memset(p, 1, 16 << 20);                         // touch every page: now it's charged to the cgroup
        printf("holding %d MB\n", mb);
    }
    return 0;
}
