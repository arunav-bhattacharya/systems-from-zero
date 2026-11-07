package sfz.os.l02

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.os.l02.ExitStatus.Exited
import sfz.os.l02.ExitStatus.Killed

class ProcessTableTest {

    @Test
    fun `shellCode is the exit code, or 128 plus the signal number`() {
        assertThat(Exited(0).shellCode()).isEqualTo(0)
        assertThat(Exited(2).shellCode()).isEqualTo(2)
        assertThat(Killed(Signal.SIGINT).shellCode()).isEqualTo(130)
        assertThat(Killed(Signal.SIGKILL).shellCode()).isEqualTo(137)
        assertThat(Killed(Signal.SIGTERM).shellCode()).isEqualTo(143)
    }

    @Test
    fun `a child that exits stays a zombie until its parent waits`() {
        val t = ProcessTable()
        val shell = t.fork(1)
        val ls = t.fork(shell)
        t.exec(ls, "ls")
        t.exit(ls, 2)

        assertThat(t.get(ls)!!.state).isEqualTo(State.ZOMBIE)
        assertThat(t.get(ls)!!.status).isEqualTo(Exited(2))
        assertThat(t.waitpid(shell)).isEqualTo(ls to Exited(2))
        assertThat(t.get(ls)).`as`("reaped, so the row is gone").isNull()
    }

    @Test
    fun `waitpid returns null while the child runs, and fails with ECHILD when there is no child`() {
        val t = ProcessTable()
        val shell = t.fork(1)
        val sleeper = t.fork(shell)
        assertThat(t.waitpid(shell)).isNull()
        assertThat(t.waitpid(shell, sleeper)).isNull()
        assertThatThrownBy { t.waitpid(sleeper) }.hasMessageContaining("ECHILD")
        assertThatThrownBy { t.waitpid(shell, 999) }.hasMessageContaining("ECHILD")
    }

    @Test
    fun `waitpid can pick one child by pid`() {
        val t = ProcessTable()
        val shell = t.fork(1)
        val a = t.fork(shell)
        val b = t.fork(shell)
        t.exit(a, 0)
        t.exit(b, 1)
        assertThat(t.waitpid(shell, b)).isEqualTo(b to Exited(1))
        assertThat(t.get(a)!!.state).`as`("a is still waiting to be reaped").isEqualTo(State.ZOMBIE)
    }

    @Test
    fun `SIGTERM runs a handler, SIGKILL ends the process anyway`() {
        val t = ProcessTable()
        val shell = t.fork(1)
        val jvm = t.fork(shell)
        t.exec(jvm, "java")
        t.handle(jvm, Signal.SIGTERM)                  // like the JVM's shutdown-hook handler

        t.kill(jvm, Signal.SIGTERM)
        assertThat(t.get(jvm)!!.state).isEqualTo(State.RUNNING)
        assertThat(t.get(jvm)!!.received).containsExactly(Signal.SIGTERM)

        t.kill(jvm, Signal.SIGKILL)
        assertThat(t.waitpid(shell)).isEqualTo(jvm to Killed(Signal.SIGKILL))
        assertThatThrownBy { t.handle(shell, Signal.SIGKILL) }.hasMessageContaining("EINVAL")
    }

    @Test
    fun `a signal with no handler terminates, except SIGCHLD which is ignored`() {
        val t = ProcessTable()
        val shell = t.fork(1)
        val worker = t.fork(shell)
        t.kill(worker, Signal.SIGCHLD)
        assertThat(t.get(worker)!!.state).isEqualTo(State.RUNNING)
        t.kill(worker, Signal.SIGTERM)
        assertThat(t.waitpid(shell)).isEqualTo(worker to Killed(Signal.SIGTERM))
    }

    @Test
    fun `exec keeps the pid but drops the handlers, so SIGTERM kills the new program`() {
        val t = ProcessTable()
        val shell = t.fork(1)
        t.handle(shell, Signal.SIGTERM)
        val child = t.fork(shell)
        assertThat(t.get(child)!!.handled).containsExactly(Signal.SIGTERM)   // fork copies handlers
        t.exec(child, "sleep")
        t.kill(child, Signal.SIGTERM)
        assertThat(t.get(child)!!.state).isEqualTo(State.ZOMBIE)
        assertThat(t.get(child)!!.program).isEqualTo("sleep")
        assertThat(t.get(child)!!.ppid).isEqualTo(shell)
    }

    @Test
    fun `kill on a zombie does nothing, and on a missing pid fails with ESRCH`() {
        val t = ProcessTable()
        val shell = t.fork(1)
        val child = t.fork(shell)
        t.exit(child, 0)
        t.kill(child, Signal.SIGKILL)
        assertThat(t.get(child)!!.status).isEqualTo(Exited(0))
        assertThatThrownBy { t.kill(4242, Signal.SIGTERM) }.hasMessageContaining("ESRCH")
    }

    @Test
    fun `orphans go to PID 1, and a real init reaps them when they die`() {
        val t = ProcessTable()
        val shell = t.fork(1)
        val jvm = t.fork(shell)
        val helper = t.fork(jvm)
        t.exit(jvm, 0)

        assertThat(t.get(helper)!!.ppid).`as`("re-parented").isEqualTo(1)
        assertThat(t.get(jvm)!!.state).`as`("the shell has not waited yet").isEqualTo(State.ZOMBIE)
        t.exit(helper, 0)
        assertThat(t.get(helper)).`as`("init reaped it").isNull()
        assertThatThrownBy { t.exit(1, 0) }.isInstanceOf(IllegalStateException::class.java)
    }

    @Test
    fun `a PID 1 that never waits collects zombies, like a JVM started as PID 1 in a container`() {
        val t = ProcessTable(initReaps = false)
        t.exec(1, "java")                   // the image's entrypoint is the JVM itself
        val script = t.fork(1)
        val curl = t.fork(script)
        t.exit(script, 0)                   // the script dies first: curl is now an orphan
        t.exit(curl, 0)

        assertThat(t.get(curl)!!.ppid).isEqualTo(1)
        assertThat(t.get(curl)!!.state).isEqualTo(State.ZOMBIE)
        assertThat(t.children(1)).containsExactly(script, curl)
        assertThat(t.waitpid(1, curl)).`as`("what tini or docker --init does").isEqualTo(curl to Exited(0))
    }
}
