// pcache.c: how much of a file is in the page cache, and drop one file's pages from it.
// It asks the kernel with mincore() over a read-only mapping, which reads nothing from disk.
//   gcc -O2 -o /tmp/pcache os/c/l09/pcache.c
//   /tmp/pcache FILE           count the file's pages that are cached
//   /tmp/pcache FILE evict     write back and drop this file's cached pages (no other file is touched)
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: pcache FILE [evict]\n"); return 2; }
    int fd = open(argv[1], O_RDONLY);
    if (fd < 0) { perror(argv[1]); return 1; }
    struct stat st;
    fstat(fd, &st);
    long page = sysconf(_SC_PAGESIZE);
    size_t pages = (st.st_size + page - 1) / page;

    if (argc > 2 && strcmp(argv[2], "evict") == 0) {
        fdatasync(fd);                                       // dirty pages can't be dropped; clean them first
        posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);        // drop this file's clean pages
    }
    if (pages == 0) { printf("%s: empty\n", argv[1]); return 0; }

    void *p = mmap(NULL, st.st_size, PROT_READ, MAP_SHARED, fd, 0);
    if (p == MAP_FAILED) { perror("mmap"); return 1; }
    unsigned char *vec = malloc(pages);
    if (mincore(p, st.st_size, vec) != 0) { perror("mincore"); return 1; }   // bit 0: page is resident
    size_t cached = 0;
    for (size_t i = 0; i < pages; i++) cached += vec[i] & 1;
    printf("%s: %zu of %zu pages cached (%zu MB of %zu MB)\n", argv[1], cached, pages,
           cached * page >> 20, (size_t)st.st_size >> 20);
    return 0;
}
