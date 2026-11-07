package sfz.os.l12

/** A failed call, named by its errno. fork() past pids.max fails with EAGAIN. */
class SysError(val errno: String, detail: String) : RuntimeException("$errno: $detail")

/**
 * A cgroup v2 directory: a set of tasks the kernel counts and limits together. Limits apply to the
 * whole subtree: a task in a child cgroup counts against every ancestor's pids.max and memory.max.
 * Counters are named after the lines of the real files.
 */
class Cgroup(val name: String, val parent: Cgroup? = null) {
    val children = mutableListOf<Cgroup>()
    /** Tasks directly in this cgroup (its `cgroup.procs`, threads included). */
    val tasks = LinkedHashSet<Task>()

    /** `pids.max` and `memory.max`; null means "max", no limit. Memory is in MB to keep the numbers small. */
    var pidsMax: Int? = null
    var memoryMaxMb: Int? = null

    /** `pids.events`: max. How often a fork failed because this cgroup's pids.max was reached. */
    var pidsEventsMax = 0
    /** `memory.events`: max (hit the limit), oom (reclaim failed, the OOM killer ran), oom_kill (tasks killed). */
    var memoryEventsMax = 0
    var memoryEventsOom = 0
    var memoryEventsOomKill = 0

    init {
        parent?.children?.add(this)
    }

    fun subtree(): List<Cgroup> = listOf(this) + children.flatMap { it.subtree() }

    /** Every live task in this cgroup and below it. */
    fun allTasks(): List<Task> = subtree().flatMap { it.tasks }

    /** `pids.current`: tasks in the subtree. */
    val pidsCurrent: Int get() = allTasks().size

    /** `memory.current`, in MB: what the subtree's tasks have in RAM. */
    val memoryCurrentMb: Int get() = allTasks().sumOf { it.rssMb }

    /** This cgroup and its ancestors, nearest first. */
    fun lineage(): List<Cgroup> = generateSequence(this) { it.parent }.toList()

    /** The path `/proc/<pid>/cgroup` shows: "0::/ledger". */
    val path: String get() = if (parent == null) "/" else lineage().reversed().drop(1).joinToString("/", prefix = "/") { it.name }
}

/**
 * A PID namespace: its own numbering, starting at 1. A namespace created inside another is nested,
 * and a task in it has a PID at every level, which is what the NSpid line of /proc/<pid>/status lists.
 */
class PidNamespace(val parent: PidNamespace? = null) {
    private var next = 1
    fun allocate(): Int = next++
    /** This namespace and its ancestors, outermost (the host) first. */
    fun levels(): List<PidNamespace> = generateSequence(this) { it.parent }.toList().reversed()
}

/** A task: a process or a thread. [pids] holds one PID per namespace level, host first. */
class Task(val name: String, val ns: PidNamespace, val pids: List<Int>, var cgroup: Cgroup) {
    var rssMb = 0
    var alive = true
    var killedBy: String? = null

    /** The PID as the host sees it. */
    val hostPid: Int get() = pids.first()
    /** The PID inside its own namespace. */
    val pid: Int get() = pids.last()
    /** The NSpid line of /proc/<pid>/status, as the host reads it: "NSpid:\t123\t1". */
    val nsPidLine: String get() = "NSpid:\t" + pids.joinToString("\t")
}

/** The one kernel every container shares. */
class Host {
    val hostNs = PidNamespace()
    val root = Cgroup("")
    private val all = mutableListOf<Task>()

    val tasks: List<Task> get() = all.filter { it.alive }

    /** PID 1 of the host: systemd, or Docker Desktop's init. Every other host task gets a higher PID. */
    val init: Task = newTask("init", hostNs, root)

    // ---------- written for you ----------

    /** Make a task with a PID at every level of [ns]. */
    private fun newTask(name: String, ns: PidNamespace, cg: Cgroup): Task {
        val t = Task(name, ns, ns.levels().map { it.allocate() }, cg)
        cg.tasks += t
        all += t
        return t
    }

    /** A task the host starts directly, with no limits checked (systemd, containerd, a shell). */
    fun boot(name: String, cg: Cgroup = root): Task = newTask(name, hostNs, cg)

    /** mkdir /sys/fs/cgroup/<parent>/<name> */
    fun mkdir(name: String, parent: Cgroup = root): Cgroup = Cgroup(name, parent)

    /** echo <pid> > cgroup.procs: move the task. Its memory moves with it here (on Linux, new charges go to the new group). */
    fun move(t: Task, to: Cgroup) {
        t.cgroup.tasks -= t
        to.tasks += t
        t.cgroup = to
    }

    /** unshare --pid --fork: [t] makes a child in a NEW PID namespace nested in its own. The child is PID 1 there. */
    fun forkIntoNewPidNamespace(t: Task, name: String): Task {
        checkPids(t.cgroup)
        return newTask(name, PidNamespace(t.ns), t.cgroup)
    }

    /** The task a PID names, as seen from inside [ns]. */
    fun find(ns: PidNamespace, pid: Int): Task? = tasks.firstOrNull { it.ns.levels().contains(ns) && it.pids[ns.levels().size - 1] == pid }

    /** SIGKILL. When a namespace's PID 1 dies, the kernel kills every other task in that namespace (and below it). */
    fun kill(t: Task, why: String = "SIGKILL") {
        if (!t.alive) return
        check(t !== init) { "the host's init can't be killed" }
        t.alive = false
        t.killedBy = why
        t.rssMb = 0
        t.cgroup.tasks -= t
        if (t.pid == 1) tasks.filter { t.ns in it.ns.levels() }.forEach { kill(it, "SIGKILL: PID 1 of its namespace died") }
    }

    // ---------- the lab ----------

    /**
     * The pids controller's check, done before every fork or clone. Walk from [cg] up to the root;
     * the first cgroup whose pidsMax would be passed by one more task gets pidsEventsMax + 1, and the
     * call fails with SysError("EAGAIN").
     */
    fun checkPids(cg: Cgroup) {
        for (c in cg.lineage()) {
            val max = c.pidsMax ?: continue
            if (c.pidsCurrent + 1 > max) {
                c.pidsEventsMax++                                  // pids.events: max
                throw SysError("EAGAIN", "pids.max of ${c.path} is $max")
            }
        }
    }

    /** fork(): a new process in the parent's cgroup and PID namespace, if the pids controller allows it. */
    fun fork(parent: Task, name: String = parent.name): Task {
        checkPids(parent.cgroup)
        return newTask(name, parent.ns, parent.cgroup)
    }

    /** A thread is a task too, so it is checked and counted exactly like fork (lesson 3 of this track). */
    fun startThread(owner: Task, name: String): Task = fork(owner, name)

    /**
     * [t] touches [mb] more memory. Charge it to [t]'s cgroup; then, for each cgroup from [t]'s up to
     * the root that now has memoryCurrentMb above memoryMaxMb:
     *  - count memoryEventsMax and memoryEventsOom (this model has no page cache to reclaim, so
     *    reclaim always fails),
     *  - kill the live task in THAT cgroup's subtree with the biggest rssMb (ties: the newest), count
     *    memoryEventsOomKill, and repeat until the cgroup is under its limit.
     * Returns the tasks killed, in order.
     */
    fun touch(t: Task, mb: Int): List<Task> {
        check(t.alive) { "task ${t.name} is dead" }
        t.rssMb += mb
        val killed = mutableListOf<Task>()
        for (c in t.cgroup.lineage()) {
            val max = c.memoryMaxMb ?: continue
            if (c.memoryCurrentMb <= max) continue
            c.memoryEventsMax++                                    // hit memory.max
            c.memoryEventsOom++                                    // nothing to reclaim: the OOM killer runs
            while (c.memoryCurrentMb > max) {
                val victim = c.allTasks().maxWith(compareBy<Task> { it.rssMb }.thenBy { it.hostPid })   // biggest, not guiltiest
                kill(victim, "SIGKILL: OOM in ${c.path}")
                c.memoryEventsOomKill++
                killed += victim
            }
        }
        return killed
    }
}

/** What the JVM reads from the cgroup files when it starts (JDK 25, UseContainerSupport on). */
object JvmView {
    /**
     * Runtime.availableProcessors(): the quota divided by the period from `cpu.max`, rounded UP, never
     * more than the CPUs the task may run on ([cpusetCpus], from cpuset.cpus.effective). "max" means
     * no quota: then it's just [cpusetCpus].
     */
    fun availableProcessors(cpuMax: String, cpusetCpus: Int): Int {
        val (quota, period) = cpuMax.trim().split(Regex("\\s+"))
        if (quota == "max") return cpusetCpus
        val cpus = Math.ceil(quota.toDouble() / period.toDouble()).toInt()   // 150000 / 100000 = 1.5 -> 2
        return cpus.coerceIn(1, cpusetCpus)
    }

    /**
     * The collector HotSpot picks when you don't choose one: G1 on a "server-class machine" (at least
     * 2 CPUs and at least 1792 MB of memory), Serial otherwise.
     */
    fun defaultGc(cpus: Int, memoryMb: Int): String {
        return if (cpus >= 2 && memoryMb >= 1792) "G1" else "Serial"   // 1792 MB: 2 GB minus 256 MB of slack
    }
}
