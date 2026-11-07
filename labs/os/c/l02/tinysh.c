// tinysh.c: a shell in 50 lines. Read a command, fork, exec it, wait for it.
// Supports one redirection, "cmd args > file", to show why fork and exec are two calls.
//   gcc -O2 -o /tmp/tinysh os/c/l02/tinysh.c && /tmp/tinysh
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    char line[1024];
    char *argv[64];
    for (;;) {
        fputs("tinysh$ ", stdout);
        fflush(stdout);
        if (!fgets(line, sizeof line, stdin)) break;                 // end of input (Ctrl-D)
        int argc = 0;
        for (char *tok = strtok(line, " \t\n"); tok && argc < 63; tok = strtok(NULL, " \t\n"))
            argv[argc++] = tok;
        argv[argc] = NULL;
        if (argc == 0) continue;
        if (strcmp(argv[0], "exit") == 0) break;                     // a builtin runs inside the shell

        pid_t pid = fork();                                           // 1. copy this process
        if (pid < 0) { perror("fork"); continue; }
        if (pid == 0) {                                               // child: still tinysh's code
            for (int i = 0; i < argc; i++) {
                if (strcmp(argv[i], ">") == 0 && argv[i + 1]) {       // between fork and exec:
                    int fd = open(argv[i + 1], O_WRONLY | O_CREAT | O_TRUNC, 0644);
                    if (fd < 0) { perror(argv[i + 1]); _exit(1); }
                    dup2(fd, 1);                                      // make fd 1 the file
                    close(fd);
                    argv[i] = NULL;                                   // the program never sees "> file"
                    break;
                }
            }
            execvp(argv[0], argv);                                    // 2. replace the program image
            perror(argv[0]);                                          // only runs if exec failed
            _exit(127);
        }
        int status;
        waitpid(pid, &status, 0);                                     // 3. wait, collect the status
        if (WIFEXITED(status))
            printf("[pid %d exited with status %d]\n", pid, WEXITSTATUS(status));
        else if (WIFSIGNALED(status))
            printf("[pid %d killed by signal %d; bash would show $? = %d]\n",
                   pid, WTERMSIG(status), 128 + WTERMSIG(status));
    }
    return 0;
}
