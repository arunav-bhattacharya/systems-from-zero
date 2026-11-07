// spin.c: a CPU-bound task that reports how much CPU the scheduler gave it.
// It spins for the given number of wall-clock seconds, then prints the CPU time it
// received and how often the kernel switched it out.
//   gcc -O2 -o /tmp/spin os/c/l04/spin.c
//   taskset -c 0 /tmp/spin 10 & taskset -c 0 nice -n 10 /tmp/spin 10 & wait
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>

static double now_s(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

int main(int argc, char **argv) {
    double seconds = argc > 1 ? atof(argv[1]) : 10;
    double start = now_s();
    volatile unsigned long work = 0;
    while (now_s() - start < seconds) {
        for (int i = 0; i < 10000; i++) work++;      // burn CPU; never sleeps, never blocks
    }
    double wall = now_s() - start;

    struct rusage ru;
    getrusage(RUSAGE_SELF, &ru);
    double cpu = ru.ru_utime.tv_sec + ru.ru_utime.tv_usec / 1e6 + ru.ru_stime.tv_sec + ru.ru_stime.tv_usec / 1e6;
    printf("pid %d nice %2d: %.2f s of CPU in %.2f s (%.0f%%), switched out %ld times\n",
           getpid(), getpriority(PRIO_PROCESS, 0), cpu, wall, 100 * cpu / wall, ru.ru_nivcsw);
    return 0;
}
