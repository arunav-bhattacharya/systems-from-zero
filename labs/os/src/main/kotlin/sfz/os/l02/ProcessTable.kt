package sfz.os.l02

/** The signals this model knows, with their Linux numbers. */
enum class Signal(val number: Int) {
    SIGHUP(1), SIGINT(2), SIGQUIT(3), SIGKILL(9), SIGTERM(15), SIGCHLD(17);

    /** SIGKILL can never be caught, blocked or ignored. (SIGSTOP can't either; it is not modeled.) */
    val catchable: Boolean get() = this != SIGKILL
}

/** How a process ended, as `wait()` reports it to the parent. */
sealed interface ExitStatus {
    /** The process called `exit(code)` (or returned `code` from main). */
    data class Exited(val code: Int) : ExitStatus

    /** A signal's default action terminated the process. */
    data class Killed(val signal: Signal) : ExitStatus
}

/**
 * The number bash stores in `$?` for this status: the exit code itself,
 * or 128 plus the signal number when a signal killed the process (SIGKILL gives 137).
 */
fun ExitStatus.shellCode(): Int {
    TODO("Exited: the code. Killed: 128 + signal number.")
}

enum class State { RUNNING, ZOMBIE }

/** One row of the kernel's process table: a very small `task_struct`. */
class Process(val pid: Int, var ppid: Int, var program: String) {
    var state: State = State.RUNNING

    /** Set when the process ends; the parent collects it with [ProcessTable.waitpid]. */
    var status: ExitStatus? = null

    /** Signals this program installed a handler for (with `sigaction`). */
    val handled: MutableSet<Signal> = mutableSetOf()

    /** Signals delivered to a handler, in order. The process kept running for each one. */
    val received: MutableList<Signal> = mutableListOf()
}

/**
 * A model of how Linux creates, ends and cleans up processes.
 *
 * PID 1 (`init`) exists from the start. In a normal Linux system init reaps every orphan that
 * dies. In a container, PID 1 is whatever program the image starts, and many programs (a JVM,
 * `sleep`, a shell script that `exec`s) never reap children they did not start. Model that with
 * `initReaps = false`.
 *
 * [fork], [exec] and [handle] are written for you. Write [exit], [kill] and [waitpid].
 */
class ProcessTable(private val initReaps: Boolean = true) {
    private val table = linkedMapOf(1 to Process(1, 0, "init"))
    private var nextPid = 2

    /** The row for [pid], or null when there is none (never created, or already reaped). */
    fun get(pid: Int): Process? = table[pid]

    /** Pids whose parent is [pid], living or zombie. */
    fun children(pid: Int): List<Int> = table.values.filter { it.ppid == pid }.map { it.pid }

    /**
     * fork(): a new process that is a copy of [parent]: same program, same signal handlers,
     * a new pid, and [parent] as its parent. Returns the child's pid.
     */
    fun fork(parent: Int): Int {
        val p = running(parent)
        val child = Process(nextPid++, parent, p.program)
        child.handled += p.handled                    // the child runs the same code, so the same handlers
        table[child.pid] = child
        return child.pid
    }

    /**
     * execve(): [pid] keeps its pid, its parent and its open files, but now runs [program].
     * Caught signals go back to their default action, because the handler code no longer exists.
     */
    fun exec(pid: Int, program: String) {
        val p = running(pid)
        p.program = program
        p.handled.clear()
    }

    /** sigaction(): install a handler for [signal] in [pid]. Fails like Linux (EINVAL) for SIGKILL. */
    fun handle(pid: Int, signal: Signal) {
        require(signal.catchable) { "EINVAL: $signal cannot be caught" }
        running(pid).handled += signal
    }

    /**
     * exit(): [pid] stops running. Do these things in order:
     * 1. It becomes a ZOMBIE with status `Exited(code)`. Its row stays in the table: the parent has not
     *    collected the status yet.
     * 2. Every child of [pid] (running or zombie) is re-parented to PID 1.
     * 3. If [initReaps] is true, init reaps at once every zombie whose parent is now PID 1,
     *    which may include [pid] itself.
     *
     * PID 1 cannot exit (on Linux that is a kernel panic): throw IllegalStateException.
     */
    fun exit(pid: Int, code: Int) {
        TODO("become a zombie, re-parent the children to 1, let init reap if it does that")
    }

    /**
     * kill(): send [signal] to [pid].
     * - No row for [pid]: throw NoSuchElementException with a message containing "ESRCH".
     * - A zombie: nothing happens. It is already dead.
     * - SIGKILL: the process ends with `Killed(SIGKILL)`, whatever handlers it has.
     * - A signal in [Process.handled]: add it to [Process.received]; the process keeps running.
     * - SIGCHLD with no handler: nothing happens (its default action is to ignore it).
     * - Any other signal: the default action ends the process with `Killed(signal)`.
     * A process killed by a signal goes through the same steps as [exit]: zombie, re-parent, init reaps.
     */
    fun kill(pid: Int, signal: Signal) {
        TODO("dispatch on the cases above; share the zombie/re-parent/reap steps with exit")
    }

    /**
     * waitpid(): [parent] collects a dead child. [child] is a pid, or -1 for any child.
     * - If a matching child is a zombie: remove its row (it is reaped) and return its pid and status.
     * - If matching children exist but all still run: return null. (The real call would block,
     *   or return 0 with WNOHANG.)
     * - If there is no matching child at all: throw IllegalStateException with a message containing "ECHILD".
     */
    fun waitpid(parent: Int, child: Int = -1): Pair<Int, ExitStatus>? {
        TODO("look for zombie children of parent; reap one, or return null, or fail with ECHILD")
    }

    private fun running(pid: Int): Process {
        val p = table[pid] ?: throw NoSuchElementException("ESRCH: no process $pid")
        check(p.state == State.RUNNING) { "process $pid is a zombie" }
        return p
    }
}
