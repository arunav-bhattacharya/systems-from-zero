package sfz.os.l02

enum class Signal(val number: Int) {
    SIGHUP(1), SIGINT(2), SIGQUIT(3), SIGKILL(9), SIGTERM(15), SIGCHLD(17);

    val catchable: Boolean get() = this != SIGKILL
}

sealed interface ExitStatus {
    data class Exited(val code: Int) : ExitStatus
    data class Killed(val signal: Signal) : ExitStatus
}

// bash folds "killed by signal N" into one number: 128 + N. So 137 means SIGKILL, 143 SIGTERM.
fun ExitStatus.shellCode(): Int = when (this) {
    is ExitStatus.Exited -> code
    is ExitStatus.Killed -> 128 + signal.number
}

enum class State { RUNNING, ZOMBIE }

class Process(val pid: Int, var ppid: Int, var program: String) {
    var state: State = State.RUNNING
    var status: ExitStatus? = null
    val handled: MutableSet<Signal> = mutableSetOf()
    val received: MutableList<Signal> = mutableListOf()
}

class ProcessTable(private val initReaps: Boolean = true) {
    private val table = linkedMapOf(1 to Process(1, 0, "init"))
    private var nextPid = 2

    fun get(pid: Int): Process? = table[pid]

    fun children(pid: Int): List<Int> = table.values.filter { it.ppid == pid }.map { it.pid }

    fun fork(parent: Int): Int {
        val p = running(parent)
        val child = Process(nextPid++, parent, p.program)
        child.handled += p.handled
        table[child.pid] = child
        return child.pid
    }

    fun exec(pid: Int, program: String) {
        val p = running(pid)
        p.program = program
        p.handled.clear()
    }

    fun handle(pid: Int, signal: Signal) {
        require(signal.catchable) { "EINVAL: $signal cannot be caught" }
        running(pid).handled += signal
    }

    fun exit(pid: Int, code: Int) {
        terminate(running(pid), ExitStatus.Exited(code))
    }

    fun kill(pid: Int, signal: Signal) {
        val p = table[pid] ?: throw NoSuchElementException("ESRCH: no process $pid")
        if (p.state == State.ZOMBIE) return                     // already dead: nothing left to signal
        when {
            signal == Signal.SIGKILL -> terminate(p, ExitStatus.Killed(signal))  // the kernel never asks the process
            signal in p.handled -> p.received += signal          // the handler runs; the process carries on
            signal == Signal.SIGCHLD -> Unit                     // default action: ignore
            else -> terminate(p, ExitStatus.Killed(signal))      // default action: terminate
        }
    }

    fun waitpid(parent: Int, child: Int = -1): Pair<Int, ExitStatus>? {
        val mine = table.values.filter { it.ppid == parent && (child == -1 || it.pid == child) }
        check(mine.isNotEmpty()) { "ECHILD: process $parent has no child ${if (child == -1) "" else child}".trim() }
        val zombie = mine.firstOrNull { it.state == State.ZOMBIE } ?: return null   // would block
        table.remove(zombie.pid)                                 // reaped: the row and its pid are free
        return zombie.pid to zombie.status!!
    }

    // exit() and death by signal end the same way
    private fun terminate(p: Process, status: ExitStatus) {
        check(p.pid != 1) { "PID 1 cannot exit: the kernel would panic" }
        p.state = State.ZOMBIE                                   // 1. dead, but the status waits for the parent
        p.status = status
        table.values.filter { it.ppid == p.pid }.forEach { it.ppid = 1 }   // 2. orphans go to init
        if (initReaps) {                                         // 3. a real init calls wait() in a loop
            table.values.filter { it.ppid == 1 && it.state == State.ZOMBIE }
                .map { it.pid }
                .forEach { table.remove(it) }
        }
    }

    private fun running(pid: Int): Process {
        val p = table[pid] ?: throw NoSuchElementException("ESRCH: no process $pid")
        check(p.state == State.RUNNING) { "process $pid is a zombie" }
        return p
    }
}
