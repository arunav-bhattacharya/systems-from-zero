// counter.c: threads add to one shared counter under a pthread mutex.
// With one thread the lock is never contended and never enters the kernel.
// With several, the losers sleep in futex(FUTEX_WAIT) and the winner wakes them.
//   gcc -O2 -pthread -o /tmp/counter os/c/l05/counter.c
//   strace -f -c -e trace=futex /tmp/counter 1
//   strace -f -c -e trace=futex /tmp/counter 4
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

#define ADDS 1000000

static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static long balance = 0;

static void *deposit(void *arg) {
    for (int i = 0; i < ADDS; i++) {
        pthread_mutex_lock(&lock);      // fast path: one atomic instruction, no system call
        balance += 1;
        pthread_mutex_unlock(&lock);    // wakes a sleeper only if one is waiting
    }
    return NULL;
}

int main(int argc, char **argv) {
    int n = argc > 1 ? atoi(argv[1]) : 1;
    pthread_t t[64];
    for (int i = 0; i < n; i++) pthread_create(&t[i], NULL, deposit, NULL);
    for (int i = 0; i < n; i++) pthread_join(t[i], NULL);
    printf("%d threads: balance = %ld (expected %ld)\n", n, balance, (long)n * ADDS);
    return 0;
}
