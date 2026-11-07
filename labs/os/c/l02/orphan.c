// orphan.c: the parent exits first. The kernel gives the living child a new parent.
//   gcc -O2 -o /tmp/orphan os/c/l02/orphan.c && /tmp/orphan
#include <stdio.h>
#include <unistd.h>

int main(void) {
    pid_t pid = fork();
    if (pid == 0) {
        printf("child %d: my parent is %d\n", getpid(), getppid());
        fflush(stdout);
        sleep(2);                                 // the parent exits during this sleep
        printf("child %d: my parent is now %d\n", getpid(), getppid());
        return 0;
    }
    sleep(1);
    printf("parent %d: exiting without waiting\n", getpid());
    return 0;
}
