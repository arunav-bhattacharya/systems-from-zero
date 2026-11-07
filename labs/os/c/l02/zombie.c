// zombie.c: the child exits at once, but the parent waits before it reaps it.
// For those seconds the child is a zombie: dead, with only its exit status left.
//   gcc -O2 -o /tmp/zombie os/c/l02/zombie.c && /tmp/zombie 10
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char **argv) {
    int delay = argc > 1 ? atoi(argv[1]) : 10;
    pid_t pid = fork();
    if (pid == 0) _exit(7);                       // child: exit with status 7, right away

    printf("parent %d forked child %d; reaping it in %d s\n", getpid(), pid, delay);
    fflush(stdout);
    sleep(delay);                                 // the child stays a zombie all this time

    int status;
    waitpid(pid, &status, 0);                     // reap: the kernel frees the zombie's entry
    printf("parent reaped %d, exit status %d\n", pid, WEXITSTATUS(status));
    return 0;
}
