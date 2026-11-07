// cost.c: what does one trip into the kernel cost?
// Times N real getpid system calls against N clock_gettime calls, which the
// vDSO answers in user space without entering the kernel.
//   gcc -O2 -o /tmp/cost os/c/l01/cost.c && /tmp/cost
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

static long long now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

int main(int argc, char **argv) {
    long n = argc > 1 ? atol(argv[1]) : 1000000;
    struct timespec ts;
    long sink = 0;

    long long t0 = now_ns();
    for (long i = 0; i < n; i++) sink += syscall(SYS_getpid);   // trap: user mode -> kernel -> back
    long long t1 = now_ns();
    for (long i = 0; i < n; i++) {                               // vDSO: stays in user mode
        clock_gettime(CLOCK_MONOTONIC, &ts);
        sink += ts.tv_nsec & 1;
    }
    long long t2 = now_ns();

    printf("getpid (system call):    %5.1f ns per call\n", (double)(t1 - t0) / n);
    printf("clock_gettime (vDSO):    %5.1f ns per call\n", (double)(t2 - t1) / n);
    return sink == 42;   // use sink so the compiler keeps both loops
}
