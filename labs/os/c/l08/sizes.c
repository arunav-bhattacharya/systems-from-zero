// sizes.c: ask malloc for blocks of different sizes and watch which system calls it makes.
//   gcc -O2 -o /tmp/sizes os/c/l08/sizes.c
//   strace -o /tmp/sizes.txt -e trace=brk,mmap,munmap,write /tmp/sizes > /dev/null; cat /tmp/sizes.txt
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void say(const char *msg) {                        // a marker line in the strace output
    if (write(1, msg, strlen(msg)) < 0) exit(1);
}

static char *use(char *p, size_t n) {                     // write to the block, so the compiler keeps it
    memset(p, 7, n);
    return p;
}

int main(void) {
    say("malloc 1000 bytes\n");
    char *a = use(malloc(1000), 1000);
    say("malloc 1000 bytes again\n");
    char *b = use(malloc(1000), 1000);
    say("malloc 100 KB\n");
    char *c = use(malloc(100 << 10), 100 << 10);
    say("malloc 200 KB\n");
    char *d = use(malloc(200 << 10), 200 << 10);
    say("malloc 1 MB\n");
    char *e = use(malloc(1 << 20), 1 << 20);
    say("free the 1 MB block\n");
    free(e);
    say("malloc 1 MB again\n");
    char *f = use(malloc(1 << 20), 1 << 20);
    say("done\n");
    printf("%d\n", a[0] + b[0] + c[0] + d[0] + f[0]);
    return 0;
}
