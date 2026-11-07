// share.c: two processes write records to one log file, three ways.
//   1. open, then fork: both file descriptors point at ONE open file description, so one offset
//   2. fork, then each opens: two descriptions, two offsets, and the second writer overwrites the first
//   3. fork, then each opens with O_APPEND: two descriptions, but every write goes to the end
// The child writes its three records and exits; then the parent writes its three. The offsets
// come from /proc/self/fdinfo, the kernel's own view of the description.
//   gcc -O2 -o /tmp/share os/c/l10/share.c && /tmp/share /tmp/auth.log
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static long pos(int fd) {                        // the "pos:" line of /proc/self/fdinfo/<fd>
    char path[64], line[128];
    snprintf(path, sizeof path, "/proc/self/fdinfo/%d", fd);
    FILE *f = fopen(path, "r");
    long p = -1;
    while (f && fgets(line, sizeof line, f))
        if (sscanf(line, "pos: %ld", &p) == 1) break;
    if (f) fclose(f);
    return p;
}

static void records(int fd, const char *who) {
    char rec[32];
    for (int i = 1; i <= 3; i++) {
        int n = snprintf(rec, sizeof rec, "%-6s auth %d\n", who, i);   // 14 bytes each
        if (write(fd, rec, n) != n) { perror("write"); exit(1); }
    }
}

static void show(const char *file) {
    struct stat st;
    stat(file, &st);
    printf("   file: %lld bytes\n", (long long)st.st_size);
    FILE *f = fopen(file, "r");
    char line[64];
    while (fgets(line, sizeof line, f)) printf("     %s", line);
    fclose(f);
}

static void run(const char *file, int mode) {
    int flags = O_WRONLY | O_CREAT | O_TRUNC;
    int fd = -1;
    if (mode == 1) fd = open(file, flags, 0644);         // one open, before the fork
    else close(open(file, flags, 0644));                 // just create the empty file
    if (mode == 3) flags = O_WRONLY | O_APPEND;
    else flags = O_WRONLY;

    pid_t child = fork();
    if (child == 0) {
        if (mode != 1) fd = open(file, flags);           // the child's own open
        records(fd, "child");
        printf("   child wrote 3 records, its offset is now %ld\n", pos(fd));
        fflush(stdout);
        _exit(0);
    }
    if (mode != 1) fd = open(file, flags);               // the parent's own open
    waitpid(child, NULL, 0);
    printf("   parent's offset before it writes: %ld\n", pos(fd));
    records(fd, "parent");
    printf("   parent wrote 3 records, its offset is now %ld\n", pos(fd));
    close(fd);
    show(file);
}

int main(int argc, char **argv) {
    const char *file = argc > 1 ? argv[1] : "/tmp/auth.log";
    setvbuf(stdout, NULL, _IOLBF, 0);
    printf("1. open, then fork (one shared description)\n");
    run(file, 1);
    printf("2. fork, then each process opens the file\n");
    run(file, 2);
    printf("3. fork, then each opens it with O_APPEND\n");
    run(file, 3);
    unlink(file);
    return 0;
}
