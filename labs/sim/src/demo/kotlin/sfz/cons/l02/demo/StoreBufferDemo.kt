package sfz.cons.l02.demo

import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicIntegerArray
import kotlin.concurrent.thread

/**
 * Lesson cons-02: your laptop's memory is not linearizable either. This is the classic "store
 * buffering" test, on real threads and real cores (not a simulation).
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l02.demo.StoreBufferDemoKt -q
 *
 * For each slot i, thread 1 runs  x[i] = 1; r1 = y[i]  and thread 2 runs  y[i] = 1; r2 = x[i].
 * In any single order of those four steps, at least one thread's read comes after the other's write,
 * so r1 = 0 and r2 = 0 together is impossible for one copy of memory. Plain arrays allow it: each
 * core may park its write in a store buffer (and the JIT may move the read up) so both reads run
 * first. AtomicIntegerArray's get and set have volatile semantics, which forbids that.
 */
fun main() {
    val slots = 200_000
    val rounds = 25
    println("%-28s %12s %14s".format("memory", "trials", "both read 0"))
    for (volatile in listOf(false, true)) {
        var both = 0L
        repeat(rounds) { both += round(slots, volatile) }
        println("%-28s %,12d %,14d".format(if (volatile) "volatile (AtomicIntegerArray)" else "plain IntArray", slots.toLong() * rounds, both))
    }
}

/** One round: both threads start together and walk the same slots, so they collide on many of them. */
private fun round(slots: Int, volatile: Boolean): Int {
    val r1 = IntArray(slots)
    val r2 = IntArray(slots)
    val ready = AtomicInteger(0)
    val t1: Thread
    val t2: Thread
    if (volatile) {
        val x = AtomicIntegerArray(slots)
        val y = AtomicIntegerArray(slots)
        t1 = thread { ready.incrementAndGet(); while (ready.get() < 2) Thread.onSpinWait(); for (i in 0 until slots) { x.set(i, 1); r1[i] = y.get(i) } }
        t2 = thread { ready.incrementAndGet(); while (ready.get() < 2) Thread.onSpinWait(); for (i in 0 until slots) { y.set(i, 1); r2[i] = x.get(i) } }
    } else {
        val x = IntArray(slots)
        val y = IntArray(slots)
        t1 = thread { ready.incrementAndGet(); while (ready.get() < 2) Thread.onSpinWait(); for (i in 0 until slots) { x[i] = 1; r1[i] = y[i] } }
        t2 = thread { ready.incrementAndGet(); while (ready.get() < 2) Thread.onSpinWait(); for (i in 0 until slots) { y[i] = 1; r2[i] = x[i] } }
    }
    t1.join(); t2.join()
    return (0 until slots).count { r1[it] == 0 && r2[it] == 0 }
}
