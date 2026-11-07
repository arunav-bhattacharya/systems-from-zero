// hello.c: print one line with the write system call, then exit.
// Build it twice in the lab box and compare the system calls:
//   gcc -O2 -o /tmp/hello os/c/l01/hello.c                  (dynamically linked)
//   gcc -O2 -static -o /tmp/hello-static os/c/l01/hello.c   (no dynamic loader)
#include <unistd.h>

int main(void) {
    const char msg[] = "hello from C\n";
    if (write(1, msg, sizeof msg - 1) < 0)   // fd 1 is standard output
        return 1;
    return 0;                                // libc then calls exit_group(0)
}
