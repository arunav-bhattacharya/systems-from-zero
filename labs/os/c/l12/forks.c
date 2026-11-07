// forks.c: a polite fork bomb. It forks children that only sleep, until fork() fails or it has made
// MAX of them, then prints why it stopped, kills the children and reaps them.
//   gcc -O2 -o /tmp/forks os/c/l12/forks.c && /tmp/forks 500
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char **argv) {
    int max = argc > 1 ? atoi(argv[1]) : 500;
    pid_t *kids = calloc(max, sizeof(pid_t));
    int n = 0;
    setvbuf(stdout, NULL, _IOLBF, 0);
    while (n < max) {
        pid_t pid = fork();
        if (pid == 0) { pause(); _exit(0); }           // child: sleep until killed
        if (pid < 0) {
            printf("fork number %d failed: %s (%s)\n", n + 1, errno == EAGAIN ? "EAGAIN" : "?", strerror(errno));
            break;
        }
        kids[n++] = pid;
    }
    printf("%d children running\n", n);
    for (int i = 0; i < n; i++) kill(kids[i], SIGKILL);
    for (int i = 0; i < n; i++) waitpid(kids[i], NULL, 0);
    return 0;
}
