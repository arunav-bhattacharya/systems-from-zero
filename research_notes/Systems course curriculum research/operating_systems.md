# Operating Systems track: research notes (as of 2026-11-07)

Source tags used throughout:
- **(V)** = page fetched in this research session and the claim was read on it.
- **(S)** = only seen in a search-result snippet; the page itself was not fetched.
- **(R)** = canonical reference (OSTEP, man7.org, LWN, etc.) cited from prior knowledge; the URL was NOT fetched this session. The lesson writer should spot-check these before publishing.

Audience assumption: senior Java/Kotlin backend engineer on an Apple Silicon Mac. Every concept should land on a JVM-in-production symptom (exit code 137, "unable to create native thread", GC thread oversubscription, page-cache-heavy services like Kafka, fsync-dependent stores, Netty/epoll, virtual thread pinning).

---

## 1. Teaching order and scope: canonical concepts and the facts each lesson needs

### Takeaway
Teach in OSTEP's order (virtualization of CPU, then memory, then concurrency, then persistence), but pull system calls and `/proc` to the very front so the learner has a "microscope" (strace, /proc) from lesson 1, and end with containers, which are just a composition of everything before (namespaces + cgroups + seccomp on one shared kernel). Several "textbook" facts are now outdated for Linux: the scheduler is EEVDF (not CFS) since 6.6, sched_ext exists since 6.12, and JVM thread facts changed with JDK 21/24.

### Cited Findings

**Kernel role, user vs kernel mode, system calls**
- OSTEP frames the CPU-virtualization mechanism as "limited direct execution": user code runs directly on the CPU in user mode, and traps into the kernel (system calls, interrupts, exceptions) for privileged work; the kernel regains control via timer interrupts — (R) [OSTEP ch. 6, Mechanism: Limited Direct Execution](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-mechanisms.pdf)
- `strace` traces system calls and signals via ptrace; `-c` gives per-syscall counts/time, `-f` follows children/threads — (R) [strace(1)](https://man7.org/linux/man-pages/man1/strace.1.html)
- Some "syscalls" (e.g. `clock_gettime`, `gettimeofday`) are served from the vDSO in user space and therefore do not appear in strace output — (R) [vdso(7)](https://man7.org/linux/man-pages/man7/vdso.7.html)
- The Docker default seccomp profile is an allowlist that "disables around 44 system calls out of 300+" — (V) [Docker seccomp docs](https://docs.docker.com/engine/security/seccomp/). Useful number for "how many syscalls does Linux have" framing.

**Processes**
- Process API: `fork()` creates a near-copy of the caller, `exec*()` replaces the program image, `wait()/waitpid()` reaps a child; separation of fork and exec is what lets a shell set up redirection/pipes in between — (R) [OSTEP ch. 5, Process API](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-api.pdf); (R) [fork(2)](https://man7.org/linux/man-pages/man2/fork.2.html), [execve(2)](https://man7.org/linux/man-pages/man2/execve.2.html), [wait(2)](https://man7.org/linux/man-pages/man2/wait.2.html)
- Linux's PCB is `struct task_struct`; per-process state is exposed under `/proc/<pid>/` (status, maps, smaps, fd/, task/, sched, limits) — (R) [proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html)
- Zombie = child that exited but has not been reaped by its parent (state `Z`, `<defunct>`); orphan = child whose parent died, re-parented to init (or a subreaper) — (R) [wait(2)](https://man7.org/linux/man-pages/man2/wait.2.html), [prctl(2) PR_SET_CHILD_SUBREAPER](https://man7.org/linux/man-pages/man2/prctl.2.html)
- Signals: SIGKILL and SIGSTOP cannot be caught, blocked or ignored — (R) [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html)

**Threads and JVM mapping**
- Linux threads are tasks created with `clone()` sharing the address space (CLONE_VM, CLONE_THREAD...); each has its own TID visible in `/proc/<pid>/task/` — (R) [clone(2)](https://man7.org/linux/man-pages/man2/clone.2.html)
- A JVM platform thread is a thin wrapper over one OS thread (1:1) — (R) [JEP 444](https://openjdk.org/jeps/444) (the page was fetched, but this specific sentence was not in the extracted answer)
- Default Java thread stack size (`-Xss` / `-XX:ThreadStackSize`) in JDK 25: Linux/x64 1024 KB, Linux/AArch64 2048 KB, macOS/AArch64 2048 KB — (V) [JDK 25 java man page](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html). Note the Mac-based learner running arm64 Linux gets 2 MB stacks by default.
- Virtual threads were finalized in JDK 21 (JEP 444); the scheduler is "a work-stealing ForkJoinPool that operates in FIFO mode"; default parallelism = number of available processors, tunable with `jdk.virtualThreadScheduler.parallelism` and capped by `jdk.virtualThreadScheduler.maxPoolSize` — (V) [JEP 444](https://openjdk.org/jeps/444)
- JEP 444: "Virtual threads are not faster threads"; don't pool them, use semaphores to limit concurrency; `jcmd <pid> Thread.dump_to_file -format=json <file>` dumps virtual threads — (V) [JEP 444](https://openjdk.org/jeps/444)
- JEP 491 (delivered in JDK 24): virtual threads can block inside `synchronized` without pinning the carrier. Remaining pinning cases: blocking during class loading/symbolic resolution, inside class initializers, waiting for another thread's class init, and native code calling back into Java that blocks. `jdk.VirtualThreadPinned` JFR event remains; `jdk.tracePinnedThreads` was removed. Default max of 256 platform threads for the scheduler — (V) [JEP 491](https://openjdk.org/jeps/491)

**CPU scheduling**
- EEVDF: the kernel docs say Linux "began transitioning to EEVDF in version 6.6", moving away from CFS. Concepts: each task's lag (owed vs. over-served CPU time); only tasks with lag >= 0 are eligible; among eligible tasks the one with the earliest virtual deadline runs; sleeping tasks stay queued with "deferred dequeue" so they can't reset negative lag by briefly sleeping; tasks can request custom slices via `sched_setattr()` — (V) [docs.kernel.org EEVDF](https://docs.kernel.org/scheduler/sched-eevdf.html)
- Linux 6.12 completed the EEVDF transition started in 6.6; processes can request shorter time slices via `sched_setattr()` / `sched_attr::sched_runtime` — (V) [heise on Linux 6.12](https://heise.de/-9949941)
- Linux 6.12 was released 2024-11-17 — (V) [kernel.org releases](https://www.kernel.org/category/releases.html)
- sched_ext: "a scheduler class whose behavior can be defined by a set of BPF programs"; merged in 6.12 — (V) [docs.kernel.org sched_ext](https://docs.kernel.org/scheduler/sched-ext.html); (V) [heise](https://heise.de/-9949941)
- sched_ext requires `CONFIG_SCHED_CLASS_EXT=y` plus `CONFIG_BPF`, `CONFIG_BPF_SYSCALL`, `CONFIG_BPF_JIT`, `CONFIG_DEBUG_INFO_BTF`; check state via `/sys/kernel/sched_ext/state`, `/sys/kernel/sched_ext/root/ops`, `/sys/kernel/sched_ext/enable_seq` (0 = none loaded since boot), per-task `ext.enabled` in `/proc/self/sched`; on error/stall or SysRq-S the kernel "reverts all tasks back to the fair-class scheduler"; example schedulers `scx_simple`, `scx_qmap`, `scx_central`, `scx_flatcg`, `scx_userland` etc. in `tools/sched_ext`; no ABI stability guarantee — (V) [docs.kernel.org sched_ext](https://docs.kernel.org/scheduler/sched-ext.html)
- cgroup v2 CPU control: `cpu.max` format `"$MAX $PERIOD"`, default `"max 100000"` (applies to fair-class tasks only); `cpu.weight` default 100, range 1–10000 — (V) [cgroup v2 docs](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- `nice` maps to scheduler weights (nice 0 = 1024; each step ≈ 1.25x / "10% CPU" rule of thumb) — (R) [sched-nice-design](https://docs.kernel.org/scheduler/sched-nice-design.html); (R) [sched(7)](https://man7.org/linux/man-pages/man7/sched.7.html)
- Voluntary vs involuntary context switches per task are in `/proc/<pid>/status` (`voluntary_ctxt_switches`, `nonvoluntary_ctxt_switches`) — (R) [proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html)

**Synchronization**
- futex: a fast user-space lock where the uncontended path is a user-space atomic and the kernel is entered (`FUTEX_WAIT`/`FUTEX_WAKE`) only on contention; glibc pthread mutexes and HotSpot's park/unpark are built on it — (R) [futex(2)](https://man7.org/linux/man-pages/man2/futex.2.html), [futex(7)](https://man7.org/linux/man-pages/man7/futex.7.html)
- OSTEP covers locks (spin vs. sleep, two-phase locks referencing Linux futex), condition variables, semaphores, and the four deadlock conditions (mutual exclusion, hold-and-wait, no preemption, circular wait) — (R) [OSTEP ch. 28 Locks](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-locks.pdf), [ch. 31 Semaphores](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-sema.pdf), [ch. 32 Concurrency Bugs](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-bugs.pdf)
- `threads-max` default is set so thread structures take at most ~1/8 of RAM; max value FUTEX_TID_MASK (0x3fffffff) — (V) [sysctl/kernel docs](https://docs.kernel.org/admin-guide/sysctl/kernel.html)

**Virtual memory**
- Paging, page tables, TLBs, swapping/demand paging chapters — (R) [OSTEP ch. 18 Paging](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-paging.pdf), [ch. 19 TLBs](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-tlbs.pdf), [ch. 21–22 Beyond Physical Memory](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-beyondphys.pdf)
- Overcommit modes (`vm.overcommit_memory`): 0 = heuristic (default; obviously excessive requests refused); 1 = always overcommit; 2 = strict accounting, commit limit = swap + `overcommit_ratio` (default 50%) of RAM (or `overcommit_kbytes`). `/proc/meminfo` shows `CommitLimit` and `Committed_AS`. In mode 2 `MAP_NORESERVE` is ignored — (V) [overcommit-accounting](https://docs.kernel.org/mm/overcommit-accounting.html)
- `mmap(2)` maps files or anonymous memory; `MAP_PRIVATE` gives copy-on-write semantics — (R) [mmap(2)](https://man7.org/linux/man-pages/man2/mmap.2.html)
- JVM large pages: with `-XX:+UseLargePages` and no THP, hugetlbfs pages must be pre-allocated, e.g. `echo 4096 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages` (8 GB of 2 MB pages); `-XX:+UseTransparentHugePages` is the THP alternative; `-XX:+AlwaysPreTouch` touches every heap page at startup (off by default; otherwise pages are committed as used) — (V) [JDK 25 java man page](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html)
- THP modes in `/sys/kernel/mm/transparent_hugepage/enabled` (`always`/`madvise`/`never`) — (R) [docs.kernel.org THP](https://docs.kernel.org/admin-guide/mm/transhuge.html)

**Page cache, writeback, fsync**
- In cgroup v2, page cache is charged to the memory cgroup ("Userland memory - page cache and anonymous memory"), charged to the cgroup that instantiated it until released — (V) [cgroup v2 docs](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- Dirty writeback knobs `vm.dirty_ratio`, `vm.dirty_background_ratio`, `vm.dirty_expire_centisecs`, `vm.dirty_writeback_centisecs` — (R) [sysctl/vm docs](https://docs.kernel.org/admin-guide/sysctl/vm.html)
- `write()` returning success does not mean data is on stable storage; `fsync()`/`fdatasync()` flush; for a new file the directory must also be fsynced — (R) [fsync(2)](https://man7.org/linux/man-pages/man2/fsync.2.html)
- "fsyncgate" (2018): PostgreSQL discovered that after a writeback error Linux could mark pages clean so a retried `fsync()` succeeded with data lost; PostgreSQL moved to PANIC-on-fsync-failure — (R) [LWN: PostgreSQL's fsync() surprise](https://lwn.net/Articles/752063/)

**File systems**
- Files = inodes (metadata + block pointers) + directory entries (name -> inode number); hard links share an inode; a deleted-but-open file lives until the last fd closes — (R) [OSTEP ch. 39 Files and Directories](https://pages.cs.wisc.edu/~remzi/OSTEP/file-intro.pdf), [inode(7)](https://man7.org/linux/man-pages/man7/inode.7.html)
- Journaling (data vs. metadata journaling, ordered mode) — (R) [OSTEP ch. 42 Crash Consistency: FSCK and Journaling](https://pages.cs.wisc.edu/~remzi/OSTEP/file-journaling.pdf); ext4 `data=ordered` default — (R) [docs.kernel.org ext4](https://docs.kernel.org/admin-guide/ext4.html); XFS — (R) [docs.kernel.org xfs](https://docs.kernel.org/admin-guide/xfs.html)

**I/O models**
- epoll is the Linux scalable readiness API (`epoll_create1`, `epoll_ctl`, `epoll_wait`; level vs edge triggered) — (R) [epoll(7)](https://man7.org/linux/man-pages/man7/epoll.7.html); select/poll — (R) [select(2)](https://man7.org/linux/man-pages/man2/select.2.html), [poll(2)](https://man7.org/linux/man-pages/man2/poll.2.html)
- io_uring is a submission/completion ring API; syscalls `io_uring_setup`, `io_uring_enter`, `io_uring_register` — (V) names confirmed in [Docker seccomp docs](https://docs.docker.com/engine/security/seccomp/); (R) [io_uring(7)](https://man7.org/linux/man-pages/man7/io_uring.7.html)
- Kernel sysctl `kernel.io_uring_disabled`: 0 = all processes can create io_uring instances (default); 1 = unprivileged processes get `-EPERM` from `io_uring_setup()` unless in `kernel.io_uring_group` (default -1 → only CAP_SYS_ADMIN); 2 = disabled for everyone; existing instances keep working — (V) [sysctl/kernel docs](https://docs.kernel.org/admin-guide/sysctl/kernel.html)

**Containers**
- cgroup v2 memory: `memory.max` hard limit — "If a cgroup's memory usage reaches this limit and can't be reduced, the OOM killer is invoked in the cgroup"; `memory.high` throttles and "never invokes the OOM killer"; `memory.events` has `oom` and `oom_kill` counters; `memory.oom.group` kills the whole cgroup together; `memory.swap.max` caps swap — (V) [cgroup v2 docs](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- cgroup v2 pids: `pids.max` hard limit; `pids.events` `max` counts hits; fork/clone fail with `-EAGAIN` when the limit would be exceeded — (V) [cgroup v2 docs](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- PSI files `cpu.pressure`, `memory.pressure` per cgroup — (V) [cgroup v2 docs](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- Docker's default seccomp blocks `unshare`/`clone` namespace creation (except user namespaces), `setns`, `mount`, `bpf`, `perf_event_open` — (V) [Docker seccomp docs](https://docs.docker.com/engine/security/seccomp/)
- Namespaces overview — (R) [namespaces(7)](https://man7.org/linux/man-pages/man7/namespaces.7.html), [cgroups(7)](https://man7.org/linux/man-pages/man7/cgroups.7.html), [unshare(1)](https://man7.org/linux/man-pages/man1/unshare.1.html)

**Observability**
- Brendan Gregg's recommended CPU saturation tools: `mpstat -P ALL 1`, `top`/`pidstat 1`, `/proc/PID/schedstat`, `perf sched`, bcc `runqlat`/`runqlen`, `vmstat 1` `r` column; "the best CPU saturation metrics are measures of run queue (or scheduler) latency" — (V) [Gregg, Linux Load Averages](https://www.brendangregg.com/blog/2017-08-08/linux-load-averages.html)
- `perf_event_paranoid` default is 2 (restricts unprivileged perf; CAP_PERFMON bypasses) — (V) [sysctl/kernel docs](https://docs.kernel.org/admin-guide/sysctl/kernel.html)
- Gregg's tool maps and 60-second checklist — (R) [brendangregg.com/linuxperf.html](https://www.brendangregg.com/linuxperf.html), (R) [USE method](https://www.brendangregg.com/usemethod.html)

### Inferences
- Order that works for this audience: (1) kernel/syscalls/strace, (2) processes and signals, (3) threads and the JVM, (4) scheduling, (5) synchronization and deadlock, (6) virtual memory mechanics, (7) VM policy: COW, mmap, overcommit, OOM, swap, huge pages, (8) user-space allocation and RSS vs VSZ, (9) page cache and fsync, (10) file systems and FDs, (11) I/O models, (12) containers as OS features + observability capstone. Observability tools should be introduced incrementally (strace in L1, /proc in L2, top -H in L3, vmstat/pidstat in L4, perf in L4/5, bpftrace in L11/12) rather than saved for one lesson.
- Malloc/arenas fits better after VM (it's "user-space policy on top of brk/mmap"), and right before the page cache lesson because RSS confusion spans both.
- Because the learner is on Apple Silicon, all Linux labs run on arm64. On arm64 the generic syscall table has no legacy `open`, `fork`, `stat` etc.; strace shows `openat`, `clone`/`clone3`, `newfstatat`. Many x86-centric tutorials will look "wrong". (Derived from asm-generic unistd; flag for the writer to confirm in the lab itself, which it trivially will.)
- glibc's `fork()` is implemented with the `clone` syscall, so even on x86_64 strace rarely shows `fork`. Same verification approach.

### Gaps
- I did not fetch OSTEP or man7 pages this session; the concept-level citations are (R). They are stable, canonical URLs but should be spot-checked.
- No verified number for context-switch cost on modern hardware; recommend the lab measure it (`perf bench sched pipe`) rather than quoting a figure.
- EEVDF default base slice value and the debugfs tunable (`/sys/kernel/debug/sched/base_slice_ns`) not verified this session.
- glibc malloc arena defaults (e.g. arenas = 8 × cores on 64-bit; `MALLOC_ARENA_MAX`) not verified; cite [mallopt(3)](https://man7.org/linux/man-pages/man3/mallopt.3.html) (R) after checking.

---

## 2. Current facts as of November 2026

### Takeaway
As of 2026-11-07: mainline is 7.4-rc1, latest stable is 7.3.3, and the newest LTS is 6.18 (EOL Dec 2028); 5.10 and 5.15 LTS reach projected EOL in Dec 2026. EEVDF (6.6) and sched_ext (6.12) are both in every currently supported LTS from 6.12 up. io_uring remains restricted: blocked by Docker's default seccomp since Docker 25, disabled on Google production servers and ChromeOS, and switchable via `kernel.io_uring_disabled`. JDK 27 (GA 2026-09-15) is the current feature release; JDK 25 (GA 2025-09-16) is the current LTS; JDK 25 fixed a kernel-6.12-triggered container-detection bug.

### Cited Findings

**Kernel versions (kernel.org front page, fetched 2026-11-07)**
- mainline 7.4-rc1 (2026-11-01); stable 7.3.3 (2026-11-06); stable 7.2.15 marked [EOL] (2026-11-01); longterm 6.18.62, 6.12.116, 6.6.162, 6.1.192, 5.15.225, 5.10.274 (all 2026-11-06); linux-next next-20261105 — (V) [kernel.org](https://www.kernel.org/)
- LTS table: 6.18 released 2025-11-30, projected EOL Dec 2028; 6.12 released 2024-11-17, EOL Dec 2028; 6.6 released 2023-10-29, EOL Dec 2027; 6.1 released 2022-12-11, EOL Dec 2027; 5.15 and 5.10 EOL Dec 2026. All maintained by Greg Kroah-Hartman & Sasha Levin. New LTS kernels usually start with a 2-year projected EOL that can be extended; EOL dates "are not set in stone"; non-LTS stable kernels get only a few bugfix releases — (V) [kernel.org releases](https://www.kernel.org/category/releases.html)

**Scheduler**
- EEVDF transition began in 6.6 — (V) [docs.kernel.org EEVDF](https://docs.kernel.org/scheduler/sched-eevdf.html). Oddity: the same page says "(as a new option in 2024)", which conflicts with 6.6's Oct 2023 release date ((V) [kernel.org releases](https://www.kernel.org/category/releases.html)); treat "6.6, Oct 2023" as the fact.
- EEVDF transition completed and sched_ext merged in 6.12 — (V) [heise](https://heise.de/-9949941); secondary: "The EEVDF scheduler replaced CFS in version 6.6", merged under Peter Zijlstra — (S) [Linux Magazine](https://www.linux-magazine.com/index.php/Issues/2025/301/EEVDF/(language)/eng-US)
- The kernel docs still describe sched_ext's fallback as "the fair-class scheduler", i.e. EEVDF lives in the same fair class that CFS used — (V) [docs.kernel.org sched_ext](https://docs.kernel.org/scheduler/sched-ext.html)

**io_uring status and restrictions**
- Docker 25.0.0 began blocking `io_uring_setup`, `io_uring_enter`, `io_uring_register` in the default seccomp profile, synced from containerd's profile — (V) [Docker seccomp docs](https://docs.docker.com/engine/security/seccomp/) (says they "can be exploited to break out of containers", references moby#46762); (S) [moby PR #46762](https://github.com/moby/moby/pull/46762); (S) [Datadog Security Labs](https://securitylabs.datadoghq.com/articles/container-security-fundamentals-part-6)
- Real-world breakage: a moby issue reports apps failing with "operation not permitted"; TigerBeetle (no epoll fallback) fails to start under Docker 25+ — (S) [moby issue #47532](https://github-redirect.dependabot.com/moby/moby/issues/47532)
- Google (June 2023): "60% of the submissions exploited the io_uring component of the Linux kernel"; "we paid out around 1 million USD for io_uring alone"; ChromeOS: "We disabled io_uring (while we explore new ways to sandbox it)"; Android: "Our seccomp-bpf filter ensures that io_uring is unreachable to apps"; "It is disabled on production Google servers"; GKE Autopilot: "We are investigating disabling io_uring by default" — (V) [oss-security mirror of Google's post](https://seclists.org/oss-sec/2023/q2/235). The original [Google Security Blog post](https://security.googleblog.com/2023/06/learnings-from-kctf-vrps-42-linux.html) loaded but its body did not render for extraction.
- Kernel-level kill switch: `kernel.io_uring_disabled` (0/1/2) and `kernel.io_uring_group` — (V) [sysctl/kernel docs](https://docs.kernel.org/admin-guide/sysctl/kernel.html)

**cgroups v2**
- cgroup v2 interface files and semantics as listed in section 1 — (V) [cgroup v2 docs](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- Red Hat: cgroup v2 detection first shipped in OpenJDK 8u372 and 11.0.16; OpenJDK 17+ fully supports cgroup v2 (article dated 2025-11-27, OpenShift 4 context) — (S) [Red Hat Developer](https://developers.redhat.com/articles/2025/11/27/how-does-cgroups-v2-impact-java-and-nodejs-openshift-4)

**JDK**
- Releases: JDK 25 GA 2025-09-16; JDK 26 GA 2026-03-17; JDK 27 GA 2026-09-15; JDK 28 in development. The OpenJDK page does not label LTS releases — (V) [OpenJDK JDK project](https://openjdk.org/projects/jdk/). JDK 25 as current LTS is per vendor (Oracle/Temurin) roadmaps, not this page.
- Container support (JDK 25 man page, Linux only): container detection is on by default (`-XX:-UseContainerSupport` disables); use `-Xlog:os+container=trace` for full container logging; `-XshowSettings:system` "Shows host system or container configuration and continues" — (V) [JDK 25 java man page](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html)
- `-XX:ActiveProcessorCount=x` overrides the CPU count used to size GC and ForkJoinPool thread pools, "honored even if UseContainerSupport is not enabled" — (V) [JDK 25 java man page](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html)
- Heap ergonomics: `-XX:MaxRAM` default = min(available memory incl. container constraints, 128 GB); `-XX:MaxRAMPercentage` default 25%; `-XX:InitialRAMPercentage` default 1.5625%; `-XX:MinRAMPercentage` default 50% (applies to small heaps, ~125 MB) — (V) [JDK 25 java man page](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html)
- G1 is the default collector — (V) [JDK 25 java man page](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html); Bellsoft examples show a 1-CPU container getting Serial GC and 2 CPUs getting G1 (ergonomics: non-server-class machine) — (S) [Bellsoft Alpaquita docs](https://docs.bell-sw.com/alpaquita-linux/25-lts/containers/java-in-resource-constrained-containers/)
- Kernel/JDK interaction bug: JDK-8346874 — on kernel 6.12, commit 78567e2bc723 means `/proc/cgroups` no longer lists `cpuset`; the JVM logged "One or more required controllers disabled at kernel level", reported "System not containerized", and sized heap from host memory (`-m 2g` + `MaxRAMPercentage=50` ignored the limit). Closed as duplicate of JDK-8347129 ("cpuset cgroups controller is required for no good reason"), fix version 25. Affected versions listed: 11.0.25, 17.0.12, 21.0.5, 24, 25-EA — (V) [JDK-8346874](https://bugs.openjdk.org/browse/JDK-8346874)

### Inferences
- The 2026 LTS kernel has not been designated as of this fetch. kernel.org's pattern (6.1, 6.6, 6.12, 6.18 each the last release of their year) suggests 7.4, expected around Dec 2026, is the likely candidate. **Flag: may change after this note is written.**
- Since 5.10/5.15 hit EOL in Dec 2026, the course should say "any supported LTS today (6.1+) has EEVDF only if >= 6.6; sched_ext only if >= 6.12". RHEL/Ubuntu vendor kernels may backport differently.
- Because Kubernetes `RuntimeDefault` seccomp uses the container runtime's default profile, and Docker's profile was synced from containerd's, io_uring is likely blocked under `RuntimeDefault` on containerd clusters. Not verified for CRI-O.
- JDK-8346874 is a strong teaching story: an OS change (kernel 6.12) silently broke a JVM's container awareness. Learners on older JDK 17/21 builds plus a 6.12+ kernel should run `java -XshowSettings:system -version` to confirm detection. Backport status to 17u/21u was not checked.
- The Google io_uring data is from 2023. Present it as "why many platforms still restrict it", not as current exploit statistics.

### Gaps
- Which distros default to cgroup v2 (Fedora 31+, Ubuntu 21.10+, Debian 11+, RHEL 9 from memory) and systemd's cgroup v1 removal timeline: not verified this session. Recommend the writer fetch distro release notes or systemd NEWS.
- Whether JDK-8347129 was backported to JDK 17u/21u: not checked.
- Whether JDK 19+ ignores `cpu.weight`/cpu shares for CPU count (JDK-8281181, from memory): not verified.
- `kernel.io_uring_disabled` introduction version (believed 6.6): not verified.
- Netty io_uring transport status (incubator vs. core in Netty 4.2) not checked; JDK NIO itself uses epoll on Linux and kqueue on macOS (R, not verified).
- Any io_uring policy change by Google after 2023 not found.

---

## 3. Common misconceptions (with the correct model)

### Takeaway
Most misconceptions for backend engineers come from treating the OS as a black box with one number per resource (free memory, load average, %CPU, "the heap"). Each lesson should pick one misconception, break it with a lab, and replace it with the right metric.

### Cited Findings
- **"Load average = CPU usage."** Linux load average counts running + runnable + uninterruptible (D-state) threads (Matthias Urlichs, 1993 patch), so disk or lock waits raise it. The 1/5/15 values are exponentially damped sums sampled every 5 s; after one full minute of single-threaded CPU load the 1-min value reached only ~0.62. Peter Zijlstra's kernel comment: "Its a silly number but people think its important." Better: run-queue latency and per-CPU utilization — (V) [Gregg, Linux Load Averages](https://www.brendangregg.com/blog/2017-08-08/linux-load-averages.html)
- **"Free memory is wasted / my container is using all its memory."** Page cache is real, reclaimable memory and in cgroup v2 it is charged to the container's memory cgroup — (V) [cgroup v2 docs](https://docs.kernel.org/admin-guide/cgroup-v2.html). Read `memory.stat` (anon vs file) instead of one "usage" number. Classic explainer — (R) [linuxatemyram.com](https://www.linuxatemyram.com/)
- **"`free` / `/proc/meminfo` inside a container shows my container's limit."** It shows the VM/host kernel's view; the container's limit is in `/sys/fs/cgroup/memory.max` — (R) [proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html); the cgroup file is (V) [cgroup v2 docs](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- **"OOM means the host ran out of RAM."** In a container, hitting `memory.max` invokes the OOM killer inside that cgroup; `memory.events` `oom_kill` counts it; `memory.high` throttles without killing — (V) [cgroup v2 docs](https://docs.kernel.org/admin-guide/cgroup-v2.html). The JVM sees this as SIGKILL (exit 137 = 128 + 9), not `OutOfMemoryError`.
- **"The JVM heap is the container's memory."** Default `MaxRAMPercentage` is 25% of the container limit; heap is only part of RSS (metaspace, code cache, thread stacks, direct buffers, GC structures, malloc arenas) — (V) [JDK 25 java man page](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html). Setting `MaxRAMPercentage=100` invites a kernel OOM kill.
- **"Threads are cheap" / "virtual threads are faster."** Each platform thread is an OS thread with a default 1–2 MB reserved stack on Linux (2 MB on arm64) — (V) [JDK 25 java man page](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html); threads also count against `pids.max` (see lab). "Virtual threads are not faster threads" — they add throughput for blocking-heavy workloads — (V) [JEP 444](https://openjdk.org/jeps/444)
- **"`synchronized` pins virtual threads."** True only before JDK 24; JEP 491 removed it, though class-init and native-frame pinning remain — (V) [JEP 491](https://openjdk.org/jeps/491)
- **"`write()` returned, so it's on disk."** Data sits in the page cache until writeback or `fsync()`; new files need the directory fsynced too; fsync error semantics bit PostgreSQL ("fsyncgate") — (R) [fsync(2)](https://man7.org/linux/man-pages/man2/fsync.2.html), (R) [LWN 752063](https://lwn.net/Articles/752063/)
- **"Journaling file systems protect my data."** Default ext4 ordered mode journals metadata, not file contents; journaling gives consistency, not durability of un-fsynced writes — (R) [OSTEP ch. 42](https://pages.cs.wisc.edu/~remzi/OSTEP/file-journaling.pdf), (R) [ext4 docs](https://docs.kernel.org/admin-guide/ext4.html)
- **"A process at 100% CPU is the problem."** It may be the only thing doing work; the useful questions are saturation (run-queue latency, `vmstat` `r` vs. CPU count) and throttling (`cpu.stat` `nr_throttled` under `cpu.max`) — (V) [Gregg](https://www.brendangregg.com/blog/2017-08-08/linux-load-averages.html); (V) `cpu.max` semantics [cgroup v2 docs](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- **"`kill -9` is fine."** SIGKILL cannot be caught, so JVM shutdown hooks, log flushes, and graceful connection draining never run; a task in uninterruptible sleep doesn't die until it leaves D state — (R) [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html). Containers: `docker stop` sends SIGTERM then SIGKILL after a grace period; a shell-form `ENTRYPOINT` makes `sh` PID 1 and SIGTERM may never reach the JVM — (R) [Docker run reference / --init](https://docs.docker.com/reference/cli/docker/container/run/)
- **"Zombie = orphan" / "kill the zombie."** A zombie is already dead (only its exit status remains); you fix it by making the parent reap (or killing the parent so init reaps). An orphan is alive and re-parented. In containers, PID 1 must reap, hence `docker run --init` (tini) — (R) [wait(2)](https://man7.org/linux/man-pages/man2/wait.2.html)
- **"Containers are lightweight VMs."** All containers share one kernel; Docker's seccomp profile blocks ~44 syscalls precisely because a kernel bug is a host bug, and io_uring was blocked because it "can be exploited to break out of containers" — (V) [Docker seccomp docs](https://docs.docker.com/engine/security/seccomp/)
- **"CFS is the Linux scheduler."** EEVDF since 6.6; sched_ext lets BPF replace policy since 6.12 — (V) [EEVDF docs](https://docs.kernel.org/scheduler/sched-eevdf.html), [sched_ext docs](https://docs.kernel.org/scheduler/sched-ext.html)
- **"VSZ = memory usage."** Overcommit lets processes reserve far more address space than RAM+swap in mode 0/1; `Committed_AS` can exceed RAM — (V) [overcommit-accounting](https://docs.kernel.org/mm/overcommit-accounting.html). A JVM with `-Xmx8g` reserves 8 GB of VSZ but RSS grows only as pages are touched (unless `AlwaysPreTouch`) — (V) [JDK 25 man page](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html)
- **"pids.max limits processes, so my 1-process JVM is safe."** The pids controller counts tasks (threads too), so a JVM with many threads can hit it; clone fails with EAGAIN — EAGAIN behavior (V) [cgroup v2 docs](https://docs.kernel.org/admin-guide/cgroup-v2.html); the "threads count" part is (R)/needs the lab to confirm (doc wording says "processes").

### Inferences
- Rank for this audience by production pain: (1) container memory/OOM/heap sizing, (2) CPU quota throttling + GC/ForkJoin thread counts, (3) load average and %CPU misreads, (4) fsync durability, (5) threads cost, (6) signals/PID 1.
- `exit code 137` is the single most recognizable hook; open the VM-policy lesson with it.

### Gaps
- No fetched source this session for docker stop grace-period default (10 s) or tini behavior.
- No fetched source confirming pids controller counts threads; make it a lab result.

---

## 4. Lab environment on macOS (Apple Silicon)

### Takeaway
Use two tiers. Tier A: an arm64 Linux container under Docker Desktop / OrbStack / Colima covers roughly 70% of labs (syscalls, processes, threads, JVM, cgroup limits set by `docker run`, COW, mmap, epoll). Tier B: a real Linux VM (Lima, Multipass, OrbStack Linux machine, UTM) with a stock Ubuntu/Fedora kernel for anything that needs kernel-wide control or kernel tracing: perf with kernel symbols, bpftrace/BCC, sched_ext, drop_caches, swap/overcommit sysctls, mkfs on loop devices, io_uring sysctl, unshare-from-scratch with full cgroup delegation.

### Cited Findings
- Docker's default seccomp profile blocks `perf_event_open`, `bpf`, `unshare`/`clone` with namespace flags (except user namespaces), `setns`, `mount`, and io_uring syscalls; `--security-opt seccomp=unconfined` disables the filter; example `docker run --rm -it --security-opt seccomp=unconfined debian:latest unshare --map-root-user --user sh -c whoami` — (V) [Docker seccomp docs](https://docs.docker.com/engine/security/seccomp/)
- The same doc lists `ptrace` among blocked syscalls with the note that it was blocked on kernels before 4.8 to avoid a seccomp bypass — (V) [Docker seccomp docs](https://docs.docker.com/engine/security/seccomp/). Contradiction risk: from prior knowledge, Docker 19.03+ allows `ptrace` on kernels >= 4.8 in the default profile, so plain `strace <cmd>` usually works; attaching to an existing process (`strace -p`) still typically needs `--cap-add=SYS_PTRACE`. **Verify in the lab environment.**
- `perf_event_paranoid` defaults to 2, so even with seccomp relaxed, unprivileged perf is restricted; CAP_PERFMON (or `--privileged`) needed — (V) [sysctl/kernel docs](https://docs.kernel.org/admin-guide/sysctl/kernel.html)
- Docker Desktop's LinuxKit kernel "usually ships without BTF", so one tutorial recommends a full VM (Multipass/Lima) for eBPF — (S) [dev.to: eBPF on a Mac](https://dev.to/hyperredstart/ebpf-on-a-mac-a-5-minute-linux-vm-with-multipass-or-lima-5dng). Single blog, treat as a hint.
- eBPF-in-Docker-Desktop workarounds use `--privileged`, `--pid=host`, debugfs mounts and LinuxKit kernel headers; on Apple Silicon you need an arm64 image — (S) [singe/ebpf-docker-for-mac](https://github.com/singe/ebpf-docker-for-mac), (S) [hemslo/docker-bpf](https://github.com/hemslo/docker-bpf)
- OrbStack runs both containers and full Linux machines as a Docker Desktop replacement — (S) [OrbStack docs](https://docs.orbstack.dev/compare/docker-desktop). Whether its kernel exposes BTF/perf was not found.
- sched_ext needs `CONFIG_SCHED_CLASS_EXT` and BTF, i.e. a 6.12+ kernel built with it — (V) [sched_ext docs](https://docs.kernel.org/scheduler/sched-ext.html)

### Recommended `docker run` invocations (Tier A)
Flags below are built from the verified seccomp/cgroup facts above; exact behavior on the learner's Docker Desktop/OrbStack version should be smoke-tested once before publishing.

```bash
# Base image: native arm64 (default on Apple Silicon). Do NOT use --platform linux/amd64:
# emulated x86 (QEMU/Rosetta) breaks ptrace/strace and perf.

# L1–L3, L6–L8 (syscalls, processes, threads, VM, malloc) — JDK + tracing tools
docker run --rm -it --name oslab --hostname oslab \
  --cap-add=SYS_PTRACE \
  eclipse-temurin:25-jdk bash
apt-get update && apt-get install -y strace procps psmisc time gcc make python3 \
  gdb sysstat util-linux htop ltrace   # 'time' gives /usr/bin/time -v; util-linux gives fincore

# If strace says "Operation not permitted" despite SYS_PTRACE:
#   add --security-opt seccomp=unconfined

# L4 scheduling / CPU quota labs: let Docker write cpu.max for you
docker run --rm -it --cpus=1.5 --cpuset-cpus=0,1 eclipse-temurin:25-jdk bash
cat /sys/fs/cgroup/cpu.max      # expect "150000 100000"
cat /sys/fs/cgroup/cpu.stat     # nr_throttled, throttled_usec

# L7 OOM / L12 container limits
docker run --rm -it --memory=256m --memory-swap=256m --pids-limit=64 \
  eclipse-temurin:25-jdk bash
cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/pids.max
stat -fc %T /sys/fs/cgroup      # expect cgroup2fs

# L11 io_uring (blocked by default seccomp since Docker 25)
docker run --rm -it --security-opt seccomp=unconfined ubuntu:24.04 bash
apt-get update && apt-get install -y fio liburing-dev
cat /proc/sys/kernel/io_uring_disabled

# L12 "container by hand" inside a container (nested namespaces, mounts)
docker run --rm -it --privileged ubuntu:24.04 bash

# perf / bpftrace attempt in Docker Desktop (may fail: kernel headers/BTF/version mismatch)
docker run --rm -it --privileged --pid=host \
  -v /sys/kernel/debug:/sys/kernel/debug -v /sys/fs/bpf:/sys/fs/bpf \
  ubuntu:24.04 bash
```

### Recommended VM (Tier B)
```bash
# Lima (free, Apache-2.0)
brew install lima
limactl start --name=os --cpus=4 --memory=6 template://ubuntu    # Ubuntu LTS arm64 VM
limactl shell os
sudo apt-get update && sudo apt-get install -y linux-tools-$(uname -r) linux-tools-generic \
  bpftrace bpfcc-tools strace sysstat fio stress-ng openjdk-21-jdk gcc
ls /sys/kernel/btf/vmlinux        # BTF present => bpftrace/CO-RE tools work
# alternative: Multipass
brew install --cask multipass
multipass launch 24.04 --name os --cpus 4 --memory 6G --disk 20G
```
For sched_ext, use a distro kernel >= 6.12 with `CONFIG_SCHED_CLASS_EXT=y` (check `grep SCHED_CLASS_EXT /boot/config-$(uname -r)`); install `scx` schedulers from the distro or build from the sched-ext/scx repo.

### Lab-to-environment matrix
| Lab need | Docker (default) | Docker + flags | Needs VM |
|---|---|---|---|
| strace a command you start | likely works | `--cap-add=SYS_PTRACE` (+ `seccomp=unconfined` if needed) | no |
| `/proc`, ps, top -H, jstack, jcmd | yes | – | no |
| cgroup limits (memory/pids/cpu) | set via `--memory`, `--pids-limit`, `--cpus` | – | no |
| write arbitrary cgroup files / make sub-cgroups | no | `--privileged` (cgroupns may still limit) | easiest in VM |
| unshare user ns only | no (seccomp) | `seccomp=unconfined` | no |
| unshare pid/mount/net/uts + chroot | no | `--privileged` | cleaner in VM |
| io_uring | blocked | `seccomp=unconfined` | no |
| perf stat software events, perf bench | no (perf_event_open blocked) | `--privileged`, perf binary may mismatch LinuxKit kernel | recommended |
| perf hardware counters (cycles, cache-misses) | no | no | maybe not even in VM (see gaps) |
| bpftrace / BCC tools | no | `--privileged --pid=host` + debugfs, often fails without BTF | yes |
| sched_ext | no | no | yes (6.12+ kernel with config) |
| drop_caches, vm.* sysctls, swap on/off, THP mode | no (affects whole VM, /proc/sys read-only) | `--privileged` (changes Docker's whole VM) | yes |
| mkfs ext4/xfs on loop device | no | `--privileged` | yes |

### Inferences
- Default to Lima for Tier B: free, scriptable, stock Ubuntu kernel with BTF and matching `linux-tools`, and the learner can break it without touching Docker's VM.
- macOS itself is useful as a contrast only: kqueue vs epoll, 16 KB pages on Apple Silicon vs 4 KB in arm64 Ubuntu (`getconf PAGESIZE` on both is a nice 30-second demo), no `/proc`, `dtruss` crippled by SIP. Don't teach macOS internals.
- `--privileged` on Docker Desktop changes the shared Docker VM (sysctls, drop_caches) for every container; warn learners.

### Gaps
- Hardware PMU counters inside Apple Virtualization.framework guests: not verified. Expect `perf stat -e cycles` to be "not supported"; teach with software events (`task-clock`, `context-switches`, `page-faults`) and `perf bench`.
- OrbStack kernel BTF/perf/eBPF support: not found; test with `ls /sys/kernel/btf/vmlinux`.
- Exact Lima template names and flags (`template://ubuntu`, `--memory` units) and Multipass flag spelling: from prior knowledge, verify against [lima-vm.io](https://lima-vm.io/) (R) and [Multipass docs](https://canonical.com/multipass/docs) (R).
- Whether `eclipse-temurin:25-jdk` is Ubuntu-based with apt available (believed yes): not verified.
- Whether Docker Desktop's current LinuxKit kernel is >= 6.12 (affects sched_ext and the JDK-8346874 bug): not verified; `uname -r` in the first lab answers it.

---

## 5. Proposed lesson outline (12 lessons) with hands-on labs

### Takeaway
Twelve lessons, each anchored to a JVM production symptom and a lab that makes the mechanism visible. Ten run in a Docker container; L4 (partly), L9, L10 and parts of L11/L12 are better in a Lima VM. All lab facts below rely on findings cited in sections 1–4; commands are proposals the writer should run once to capture real output (don't publish invented numbers).

### Cited Findings
(Lab design relies on these verified facts: strace/seccomp behavior — [Docker seccomp](https://docs.docker.com/engine/security/seccomp/); cgroup files and EAGAIN/OOM semantics — [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html); JVM flags/defaults — [JDK 25 man page](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html); virtual threads — [JEP 444](https://openjdk.org/jeps/444), [JEP 491](https://openjdk.org/jeps/491); overcommit — [overcommit-accounting](https://docs.kernel.org/mm/overcommit-accounting.html); io_uring sysctl — [sysctl/kernel](https://docs.kernel.org/admin-guide/sysctl/kernel.html); EEVDF/sched_ext — [EEVDF](https://docs.kernel.org/scheduler/sched-eevdf.html), [sched_ext](https://docs.kernel.org/scheduler/sched-ext.html); load average and CPU tools — [Gregg](https://www.brendangregg.com/blog/2017-08-08/linux-load-averages.html). All (V).)

**L1. What a kernel does; user vs kernel mode; system calls** (Docker)
- Concepts: privilege levels (EL0/EL1 on arm64), traps, syscall table, limited direct execution, vDSO, seccomp as a syscall filter.
- Lab 1a: `strace -c -f java Hello.java` vs `strace -c /bin/true` vs a static C hello. Count syscalls and distinct calls; spot `clone3` (JVM threads), `mmap` (heap reservation, CDS archive), `openat` (lib/modules). Then `strace -f -e trace=execve,clone3,openat -o t.txt java Hello` and `grep -c clone3 t.txt` = threads the JVM starts before main.
- Lab 1b: Show the vDSO: a Java loop calling `System.nanoTime()` 1M times shows no `clock_gettime` in strace. Then show seccomp: in default Docker, `unshare --user` fails; with `--security-opt seccomp=unconfined` it succeeds.

**L2. Processes: fork/exec/wait, PCB, zombies, orphans, signals** (Docker)
- Concepts: task_struct, PID/PPID, process states (R, S, D, Z, T), `/proc/<pid>/status`, exit codes (128+signal), signal dispositions, PID 1 in containers.
- Lab 2a: Write a tiny shell (C or Python `os.fork/os.execvp/os.waitpid`): builtins `cd`, `exit`; then pipes with `os.pipe`+`dup2`; then Ctrl-C handling (shell ignores SIGINT, child gets default). Strace it to see `clone`, `execve`, `wait4`.
- Lab 2b: Create a zombie (`python3 -c 'import os,time; os.fork() or os._exit(0); time.sleep(60)' &` then `ps -o pid,ppid,stat,cmd`), then orphan it by killing the parent and watch PPID change. Signals with a JVM: add a shutdown hook, compare `kill -TERM` (hook runs, exit 143) vs `kill -KILL` (no hook, exit 137). Bonus: `docker run` with shell-form vs exec-form entrypoint and `--init`.

**L3. Threads, and how the JVM maps them to OS threads** (Docker)
- Concepts: clone flags, TIDs, `/proc/<pid>/task`, thread stacks (VSZ cost, default 2 MB on arm64 Linux), JVM's own threads (GC, JIT compiler, signal dispatcher), virtual threads on carrier ForkJoinPool, pinning.
- Lab 3a: Start a Java app; `ls /proc/<pid>/task | wc -l`, `top -H -p <pid>`, convert a hot TID to hex and find it as `nid=0x...` in `jstack`. Change `-XX:ActiveProcessorCount=1` vs 4 and count GC/compiler threads.
- Lab 3b: Launch 100k tasks that `Thread.sleep(1000)` with `Executors.newVirtualThreadPerTaskExecutor()` vs a platform-thread-per-task executor under `--pids-limit=512`. Platform version should fail with "unable to create native thread" (pids.max hit, `pids.events` increments); virtual version runs with ~#CPU carrier threads (`grep Threads /proc/<pid>/status`). Then pin: block inside a class static initializer (still pins post-JEP 491) and catch `jdk.VirtualThreadPinned` with JFR.

**L4. CPU scheduling: EEVDF, time slices, nice, quotas, context switches** (Docker + VM for perf)
- Concepts: run queue, fairness, lag/virtual deadline (EEVDF), slices and `sched_setattr`, nice weights, cgroup `cpu.max` throttling, `cpu.weight`, context-switch cost, sched_ext as "pluggable policy".
- Lab 4a: Pin two busy loops to one CPU (`taskset -c 0`), one at nice 0 and one at nice 10; observe the CPU split in `top`. Then in a container with `--cpus=0.5`, run a multi-threaded Java CPU burner; watch `cpu.stat` `nr_throttled`/`throttled_usec` climb and `Runtime.availableProcessors()` report 1. Discuss GC pause inflation from throttling.
- Lab 4b (VM): `perf bench sched pipe` to measure context-switch round-trip cost; `vmstat 1` `cs` and `r` columns under `stress-ng --cpu 8` on 4 vCPUs; per-task `voluntary_ctxt_switches` vs `nonvoluntary_ctxt_switches` for an I/O-bound vs CPU-bound process. Optional: on a 6.12+ kernel, load `scx_simple`, check `/sys/kernel/sched_ext/state` and `root/ops`, unload, confirm fallback.

**L5. Synchronization at the OS level and deadlock** (Docker)
- Concepts: atomics/CAS, spinlocks (kernel) vs sleeping locks, futex fast path, mutex, semaphore, condition variables, HotSpot park/unpark → futex, deadlock's four conditions and prevention by lock ordering/timeouts.
- Lab 5a: Java counter with `synchronized` / `ReentrantLock`, 1 thread vs 8 threads: `strace -f -c -e trace=futex` shows futex calls appear only under contention; compare with `AtomicLong`/`LongAdder`.
- Lab 5b: Classic two-lock deadlock in Java; `jstack` prints "Found one Java-level deadlock"; `/proc/<pid>/task/*/wchan` (or `cat /proc/<tid>/stack` in VM as root) shows futex wait. Fix with ordering and with `tryLock(timeout)`. Map each fix to the Coffman condition it breaks.

**L6. Virtual memory I: address spaces, page tables, TLB, page faults, demand paging** (Docker)
- Concepts: virtual vs physical, 4-level page tables, page size (4 KB arm64 Ubuntu vs 16 KB macOS), TLB and TLB misses, minor vs major faults, demand paging, `/proc/<pid>/maps` and `smaps`, RSS vs VSZ vs PSS.
- Lab 6a: `/usr/bin/time -v java -Xms1g -Xmx1g Alloc.java` with and without `-XX:+AlwaysPreTouch`: compare "Minor page faults", "Maximum resident set size", and start-up time. Same with a C program that mallocs 1 GB and touches every 4096th byte vs none.
- Lab 6b: Watch VSZ vs RSS of a JVM with `-Xmx4g` in `ps -o pid,vsz,rss`; read `/proc/<pid>/smaps_rollup`; `getconf PAGESIZE` in the container vs on macOS.

**L7. Virtual memory II: copy-on-write, mmap, huge pages, overcommit, OOM killer, swap** (Docker; swap/THP parts in VM)
- Concepts: COW after fork, `MAP_PRIVATE` vs `MAP_SHARED`, file-backed vs anonymous, `MappedByteBuffer`, THP vs hugetlbfs and TLB reach, overcommit modes and `Committed_AS`, global vs cgroup OOM, `oom_score_adj`, swap and `memory.swap.max`.
- Lab 7a: COW in C: allocate and touch 512 MB, fork, child reads `/proc/self/smaps_rollup` (Shared vs Private_Dirty), then writes 1 byte per page and re-reads. Python variant to show refcount writes trigger COW even on "read-only" access.
- Lab 7b: OOM-kill a JVM. In `--memory=256m --memory-swap=256m`, run `java -XshowSettings:system -version` (check container detection), then a heap hog with `-Xmx128m` (gets `java.lang.OutOfMemoryError`, JVM-level) vs `-Xmx512m` (kernel OOM kill, exit 137, `memory.events` `oom_kill` +1, `dmesg` in VM). Run java as a child of bash so the container survives to inspect counters. Extension: `MappedByteBuffer` a 1 GB file, touch it, show it in `/proc/<pid>/maps` and that RSS includes file pages.

**L8. Memory allocation: malloc, arenas, RSS vs VSZ, JVM native memory** (Docker)
- Concepts: brk vs mmap thresholds, glibc arenas per thread, fragmentation, why RSS doesn't drop after free, JVM NMT categories, direct buffers.
- Lab 8a: `java -XX:NativeMemoryTracking=summary ...` then `jcmd <pid> VM.native_memory summary`; compare its total with RSS. Spawn 64 threads doing malloc-heavy JNI-free work (e.g., `Deflater`), watch RSS, then rerun with `MALLOC_ARENA_MAX=2`.
- Lab 8b: C program: malloc many small blocks, free most, observe RSS stays; `malloc_trim(0)`; `strace -e brk,mmap,munmap` to see the threshold switch.

**L9. Page cache, dirty writeback, fsync** (VM preferred; partial in Docker)
- Concepts: unified page cache, read-ahead, dirty pages and writeback thresholds, `fsync`/`fdatasync`/`O_DIRECT`, rename-for-atomicity pattern, fsync errors, cgroup charging of page cache, why Kafka leans on the page cache.
- Lab 9a (VM): create a 2 GB file; `sync; echo 3 | sudo tee /proc/sys/vm/drop_caches`; `free -m`; `time cat big >/dev/null` twice; `fincore big` before/after (util-linux; vmtouch optional). In Docker instead: `cat /sys/fs/cgroup/memory.stat | grep -E '^(anon|file) '` before/after reading a file to show page cache charged to the container.
- Lab 9b: Java writer appending 4 KB records: plain `write` vs `FileChannel.force(false)` per record vs every 1000 records; measure throughput and watch `grep -E 'Dirty|Writeback' /proc/meminfo` and `strace -c -e trace=write,fsync,fdatasync`. Discuss write-temp + fsync + rename + fsync(dir).

**L10. File systems: inodes, directories, links, file descriptors, journaling (ext4 vs XFS)** (VM for mkfs; rest Docker)
- Concepts: inode vs dentry, hard vs soft links, fd table → open file description → inode, `O_APPEND`, fd inheritance on fork, `ulimit -n`, journaling modes, ext4 vs XFS trade-offs (high-level only).
- Lab 10a: `stat`, `ls -i`, `ln`/`ln -s`; delete a file a running process has open and recover it from `/proc/<pid>/fd/N`; show `df` vs `du` disagreement. Exhaust fds in Java under `ulimit -n 256` → "Too many open files"; count via `ls /proc/<pid>/fd | wc -l`.
- Lab 10b (VM): `fallocate -l 1G img; mkfs.ext4 img` and `mkfs.xfs img2`, loop-mount both, run the same fio/fsync workload, inspect `dumpe2fs -h` / `xfs_info`.

**L11. I/O models: blocking, non-blocking, select/poll/epoll, kqueue, io_uring** (Docker; io_uring with seccomp unconfined)
- Concepts: blocking read on a socket, O_NONBLOCK + EAGAIN, readiness (select/poll/epoll, kqueue on macOS) vs completion (io_uring), level vs edge triggered, C10K, how Java NIO Selector/Netty use epoll, how virtual threads change the calculus, io_uring security posture.
- Lab 11a: Two Java echo servers: thread-per-connection `ServerSocket` vs NIO `Selector`. Load with 2,000 idle connections (small Python client). Compare thread count, RSS, and `strace -f -c` (`epoll_wait`/`epoll_ctl` vs blocked `read`). Third variant: thread-per-connection on virtual threads; observe it uses epoll under the hood with few carriers.
- Lab 11b: io_uring: in default Docker run `fio --ioengine=io_uring ...` and see EPERM (seccomp); rerun with `--security-opt seccomp=unconfined`; compare `psync`, `libaio`, `io_uring` engines; check `/proc/sys/kernel/io_uring_disabled`. Discuss Google's and Docker's reasons.

**L12. Containers as OS features + observability capstone** (VM for full build; Docker `--privileged` works)
- Concepts: namespaces (pid, mount, net, uts, ipc, user, cgroup), cgroup v2 hierarchy and controllers, seccomp, capabilities, overlay filesystems, "containers aren't VMs", JVM container awareness end-to-end, USE method, PSI.
- Lab 12a: Container by hand: download Alpine minirootfs; `sudo unshare --pid --fork --mount --uts --ipc --net --mount-proc=rootfs/proc chroot rootfs /bin/sh`; set hostname, `ps` shows PID 1; from outside create `/sys/fs/cgroup/box`, write `memory.max=64M`, `pids.max=20`, move the shell's PID into `cgroup.procs`; run a fork bomb safely (`pids.events` max increments, fork returns EAGAIN) and a memory hog (`memory.events` oom_kill).
- Lab 12b: Observability capstone: run a "mystery" Java service with a planted problem (CPU throttling, page-cache thrash, or lock contention). Learners use Gregg's 60-second checklist (`uptime`, `dmesg | tail`, `vmstat 1`, `mpstat -P ALL 1`, `pidstat 1`, `iostat -xz 1`, `free -m`, `sar -n DEV 1`, `top`), PSI (`/proc/pressure/*`, `cpu.pressure`), then perf/bpftrace (`profile`, `runqlat`, `offcputime`, `opensnoop`) in the VM.

### Inferences
- If the track must be 10 lessons, merge L8 into L7 and L10 into L9 (memory allocation and file systems shrink to one lab each).
- Every lab should end with "the JVM symptom you'd see in production" so it doesn't read as a university course.
- Labs 3b, 7b and 12a share the cgroup v2 files; teach the files once in L3 (pids) and reuse.

### Gaps
- Exact syscall counts, fault counts and throughput numbers must be captured by running the labs; none were measured during this research.
- Alpine minirootfs download URL and `unshare --mount-proc` interplay with chroot should be tested; the command line above is a sketch.
- Whether `perf bench` works inside Docker without `perf_event_open` (believed yes, since it is a benchmark not a profiler) was not tested.

---

## 6. Teaching notes: misconceptions, analogies that work, what to cut

### Takeaway
Lead each lesson with a production symptom, use Java-familiar analogies (caches, executors, selectors), keep algorithms light and Linux-specific mechanisms heavy, and cut classic OS-course material that doesn't change how a backend engineer debugs.

### Cited Findings
- Load average is "a silly number", useful only for trends; teach run-queue latency instead — (V) [Gregg](https://www.brendangregg.com/blog/2017-08-08/linux-load-averages.html)
- Distinguish JVM `OutOfMemoryError` (heap) from kernel OOM kill (`memory.max` reached, `oom_kill` counter) — (V) [cgroup v2 docs](https://docs.kernel.org/admin-guide/cgroup-v2.html), (V) [JDK 25 man page](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html)
- Virtual threads are for throughput of waiting tasks, not speed; don't pool them — (V) [JEP 444](https://openjdk.org/jeps/444)
- Containers share one kernel; seccomp exists because a kernel bug is a host bug — (V) [Docker seccomp docs](https://docs.docker.com/engine/security/seccomp/)
- sched_ext policies are swappable at runtime with automatic fallback, a good illustration of "mechanism vs policy" — (V) [sched_ext docs](https://docs.kernel.org/scheduler/sched-ext.html)
- Julia Evans' zines (e.g. "So you want to be a wizard", "Linux debugging tools", strace zine) are a good tone reference for visuals — (R) [wizardzines.com](https://wizardzines.com/)

### Analogies that work for Java/Kotlin engineers (inferences, not sourced)
- System call = a REST call into a privileged service, with strace as the access log; vDSO = a client-side cache that avoids the round trip.
- Page table = a `HashMap<VirtualPage, Frame>` per process; TLB = a tiny L1 cache in front of that map (huge pages = fewer, bigger keys so the cache covers more).
- Page cache = a write-behind cache like Caffeine with async flush: fast reads, and `fsync` is the "flush and wait for ack" call.
- Copy-on-write = `CopyOnWriteArrayList` or Git branches: share until someone writes.
- futex = AQS fast path: CAS in user space, park in the kernel only on contention.
- epoll = Java NIO `Selector`; io_uring = a `CompletableFuture` submission queue shared with the kernel.
- cgroups = resource quotas on a Kubernetes namespace; namespaces = what the process can see; seccomp = an API gateway allowlist.
- Scheduler = a ForkJoinPool for the whole machine; EEVDF's virtual deadline = "who is most owed and wants a short turn goes next"; nice = weights in a weighted fair queue.
- Zombie = a completed `Future` nobody called `get()` on.

### What to cut or compress
- Scheduling algorithm zoo (FIFO/SJF/STCF/RR/MLFQ/lottery): one slide of history, then EEVDF and cgroup quotas. Keep MLFQ only as intuition for "interactive vs batch".
- Segmentation, base-and-bounds, inverted page tables, page replacement algorithm proofs (keep only LRU-approximation/clock intuition).
- Disk scheduling (elevator/SCAN), RAID levels, on-disk FFS layout details, FSCK internals beyond "why journals exist".
- Banker's algorithm (mention deadlock avoidance exists; teach lock ordering and timeouts).
- Kernel module writing, bootloaders, interrupts at the APIC level, assembly-level context switch.
- Real-time scheduling classes and PREEMPT_RT (one sentence).
- NUMA: a sidebar only, unless the audience runs large-heap JVMs on multi-socket hosts.
- macOS internals: use only as contrast (kqueue, 16 KB pages, no /proc).

### Inferences
- Write lesson intros around incidents: "Pod restarted with exit 137", "p99 doubled after moving to 2-CPU pods", "load average 40 on an idle box" (D-state on NFS), "lost writes after power failure", "Too many open files".
- Pair every metric with the file it comes from (`/proc/meminfo`, `/sys/fs/cgroup/*`, `/proc/<pid>/status`), so the course teaches where tools get data, not just tool names.

### Gaps
- No user-research or course-completion data on which analogies work best; these are judgment calls.
- Julia Evans' zine titles and pricing (some zines are paid; several comics are free on the site) not verified this session.

---

## 7. Verified URLs

### Takeaway
Sixteen URLs were fetched and confirmed to load with the content cited above on 2026-11-07. Everything else in these notes marked (S) or (R) was not fetched and should be checked before it goes into a published lesson.

### Cited Findings
Fetched and confirmed (content read):
- https://www.kernel.org/ — current mainline/stable/longterm versions
- https://www.kernel.org/category/releases.html — LTS table with release and EOL dates
- https://docs.kernel.org/scheduler/sched-eevdf.html — EEVDF concepts and version
- https://docs.kernel.org/scheduler/sched-ext.html — sched_ext config, sysfs, fallback, examples
- https://docs.kernel.org/admin-guide/cgroup-v2.html — cpu.max, cpu.weight, memory.max/high/events/oom.group/swap.max, pids.max/events, PSI, page cache charging (long page; first 100k chars read)
- https://docs.kernel.org/admin-guide/sysctl/kernel.html — io_uring_disabled/io_uring_group, threads-max, pid_max, perf_event_paranoid, kptr_restrict
- https://docs.kernel.org/mm/overcommit-accounting.html — overcommit modes
- https://docs.docker.com/engine/security/seccomp/ — default profile, blocked syscalls incl. io_uring, ptrace note, unconfined example
- https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html — UseContainerSupport, ActiveProcessorCount, MaxRAM*, Xss defaults, AlwaysPreTouch, large pages, XshowSettings:system
- https://bugs.openjdk.org/browse/JDK-8346874 — kernel 6.12 cpuset /proc/cgroups regression, fixed in 25
- https://openjdk.org/jeps/444 — virtual threads (JDK 21)
- https://openjdk.org/jeps/491 — synchronized without pinning (JDK 24)
- https://openjdk.org/projects/jdk/ — JDK release GA dates (25, 26, 27; 28 in development)
- https://www.brendangregg.com/blog/2017-08-08/linux-load-averages.html — load average semantics and better metrics
- https://seclists.org/oss-sec/2023/q2/235 — mirror of Google's kCTF/io_uring post with exact quotes
- https://heise.de/-9949941 — Linux 6.12: sched_ext merged, EEVDF completed, sched_runtime slices

Loaded but body not extractable:
- https://security.googleblog.com/2023/06/learnings-from-kctf-vrps-42-linux.html (title only rendered; use the oss-sec mirror above)

### Inferences
- The kernel.org and OpenJDK pages are the ones most likely to change after this date; recheck them when the lessons are finalized.

### Gaps
Seen only in search snippets (S), not fetched:
- https://github.com/moby/moby/pull/46762 ; https://github-redirect.dependabot.com/moby/moby/issues/47532 ; https://securitylabs.datadoghq.com/articles/container-security-fundamentals-part-6 ; https://developers.redhat.com/articles/2025/11/27/how-does-cgroups-v2-impact-java-and-nodejs-openshift-4 ; https://docs.bell-sw.com/alpaquita-linux/25-lts/containers/java-in-resource-constrained-containers/ ; https://dev.to/hyperredstart/ebpf-on-a-mac-a-5-minute-linux-vm-with-multipass-or-lima-5dng ; https://github.com/singe/ebpf-docker-for-mac ; https://github.com/hemslo/docker-bpf ; https://docs.orbstack.dev/compare/docker-desktop ; https://www.linux-magazine.com/index.php/Issues/2025/301/EEVDF/(language)/eng-US ; https://www.phoronix.com/news/Google-Restricting-IO_uring

Canonical references cited from prior knowledge (R), not fetched this session:
- OSTEP: https://pages.cs.wisc.edu/~remzi/OSTEP/ (chapter PDFs cpu-mechanisms, cpu-api, threads-locks, threads-sema, threads-bugs, vm-paging, vm-tlbs, vm-beyondphys, file-intro, file-journaling)
- man7.org: strace(1), unshare(1), fork(2), execve(2), wait(2), clone(2), prctl(2), futex(2), mmap(2), fsync(2), select(2), poll(2), mallopt(3), proc(5), signal(7), futex(7), epoll(7), io_uring(7), vdso(7), inode(7), namespaces(7), cgroups(7), sched(7)
- docs.kernel.org: scheduler/sched-nice-design.html, admin-guide/mm/transhuge.html, admin-guide/sysctl/vm.html, admin-guide/ext4.html, admin-guide/xfs.html
- https://lwn.net/Articles/752063/ (fsyncgate)
- https://www.brendangregg.com/linuxperf.html ; https://www.brendangregg.com/usemethod.html
- https://www.linuxatemyram.com/ ; https://wizardzines.com/
- https://lima-vm.io/ ; https://canonical.com/multipass/docs ; https://docs.docker.com/reference/cli/docker/container/run/
