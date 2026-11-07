// wait.c: three ways to wait for data on a socket. A child process plays the card issuer: it
// answers on one end of a socket pair after one second. The parent waits on the other end:
//   block    read() and let the kernel put the thread to sleep until the bytes arrive
//   spin     O_NONBLOCK: read() returns EAGAIN at once, so loop and ask again
//   epoll    O_NONBLOCK, plus epoll_wait() to sleep until the kernel says the socket is readable
// It prints how long the wait took, how many read() calls failed with EAGAIN, and the CPU it used.
//   gcc -O2 -o /tmp/wait os/c/l11/wait.c && /tmp/wait block && /tmp/wait spin && /tmp/wait epoll
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

static double cpu(void) {
    struct rusage u;
    getrusage(RUSAGE_SELF, &u);
    return u.ru_utime.tv_sec + u.ru_utime.tv_usec / 1e6 + u.ru_stime.tv_sec + u.ru_stime.tv_usec / 1e6;
}

int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "block";
    int sv[2];
    socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
    if (fork() == 0) {                                  // the "issuer": answers after one second
        close(sv[0]);
        sleep(1);
        if (write(sv[1], "APPROVED", 8) != 8) _exit(1);
        sleep(1);                                       // stay alive until the parent has read
        _exit(0);
    }
    close(sv[1]);
    int fd = sv[0];
    if (strcmp(mode, "block") != 0) fcntl(fd, F_SETFL, fcntl(fd, F_GETFL) | O_NONBLOCK);

    char buf[64];
    long eagain = 0;
    ssize_t n = 0;
    double t0 = now(), c0 = cpu();
    if (strcmp(mode, "epoll") == 0) {
        int ep = epoll_create1(0);
        struct epoll_event ev = {.events = EPOLLIN, .data.fd = fd};
        epoll_ctl(ep, EPOLL_CTL_ADD, fd, &ev);          // register once
        struct epoll_event ready[8];
        int k = epoll_wait(ep, ready, 8, -1);           // sleep until something is readable
        printf("epoll_wait returned %d ready socket(s)\n", k);
    }
    while ((n = read(fd, buf, sizeof buf)) < 0 && errno == EAGAIN)
        eagain++;                                       // spin: nothing yet, ask again
    printf("%-5s got %zd bytes after %.2f s; read() failed with EAGAIN %ld times; CPU used %.2f s\n",
           mode, n, now() - t0, eagain, cpu() - c0);
    wait(NULL);
    return 0;
}
