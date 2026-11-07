// arenas.c: 16 threads use malloc at once, then take turns building and freeing 16 MB each.
// glibc gives each thread its own arena (a separate heap), so each one keeps its freed memory.
//   gcc -O2 -pthread -o /tmp/arenas os/c/l08/arenas.c
//   /tmp/arenas                     glibc's default: up to 8 arenas per CPU
//   MALLOC_ARENA_MAX=1 /tmp/arenas  one shared heap for every thread
#define _GNU_SOURCE
#include <malloc.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define THREADS 16
#define OPS 200000           // malloc/free pairs per thread in the contention phase
#define BLOCKS 4096          // 4096 x 4000 B = about 16 MB per thread in the turn phase
#define SIZE 4000            // too big for glibc's per-thread cache, so every call goes to an arena

static pthread_barrier_t go;
static pthread_mutex_t turn_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t turn_cond = PTHREAD_COND_INITIALIZER;
static int turn = 0;
static void *keep[THREADS];
static char *volatile sink[THREADS];                         // stops the compiler from removing malloc/free pairs

static double now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e3 + ts.tv_nsec / 1e6;
}

static long status_mb(const char *name) {
    char line[256], key[64];
    long kb = -1, v;
    FILE *f = fopen("/proc/self/status", "r");
    while (fgets(line, sizeof line, f))
        if (sscanf(line, "%63[^:]: %ld kB", key, &v) == 2 && strcmp(key, name) == 0) { kb = v; break; }
    fclose(f);
    return kb / 1024;
}

static int arenas(void) {                                    // malloc_info writes one <heap nr=...> per arena
    char *buf; size_t len;
    FILE *f = open_memstream(&buf, &len);
    malloc_info(0, f);
    fclose(f);
    int n = 0;
    for (char *p = buf; (p = strstr(p, "<heap nr=")); p++) n++;
    free(buf);
    return n;
}

static void *worker(void *arg) {
    long id = (long)arg;
    pthread_barrier_wait(&go);
    for (int i = 0; i < OPS; i++) {                          // phase 1: everyone at once
        char *p = malloc(SIZE);
        p[0] = 1;
        sink[id] = p;
        free(p);
    }
    pthread_barrier_wait(&go);

    pthread_mutex_lock(&turn_lock);                          // phase 2: one thread at a time
    while (turn != id) pthread_cond_wait(&turn_cond, &turn_lock);
    char *b[BLOCKS];
    for (int i = 0; i < BLOCKS; i++) { b[i] = malloc(SIZE); memset(b[i], 1, SIZE); }
    for (int i = 0; i < BLOCKS - 1; i++) free(b[i]);         // free all but the last block
    keep[id] = b[BLOCKS - 1];
    turn++;
    pthread_cond_broadcast(&turn_cond);
    pthread_mutex_unlock(&turn_lock);
    pthread_barrier_wait(&go);                               // stay alive until everyone is done
    return NULL;
}

int main(void) {
    pthread_t t[THREADS];
    setvbuf(stdout, NULL, _IOLBF, 0);
    const char *max = getenv("MALLOC_ARENA_MAX");
    printf("MALLOC_ARENA_MAX=%s, %d threads\n", max ? max : "(unset)", THREADS);
    pthread_barrier_init(&go, NULL, THREADS + 1);
    for (long i = 0; i < THREADS; i++) pthread_create(&t[i], NULL, worker, (void *)i);

    double t0 = now_ms();
    pthread_barrier_wait(&go);                               // start phase 1
    pthread_barrier_wait(&go);                               // phase 1 done
    printf("%d x %d malloc+free pairs at once: %.0f ms\n", THREADS, OPS, now_ms() - t0);
    pthread_barrier_wait(&go);                               // phase 2 done
    printf("each thread built and freed 16 MB in turn: arenas %d, RSS %ld MB, VSZ %ld MB\n",
           arenas(), status_mb("VmRSS"), status_mb("VmSize"));
    for (int i = 0; i < THREADS; i++) pthread_join(t[i], NULL);
    return 0;
}
