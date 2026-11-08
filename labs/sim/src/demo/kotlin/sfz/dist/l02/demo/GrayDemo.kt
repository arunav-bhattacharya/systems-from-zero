package sfz.dist.l02.demo

/**
 * Lesson dist-02, section 4: gray failure.
 *
 * Part 1: one of N core switches drops packets but still answers its own health checks. How many
 * requests touch it, as the fan-out grows?
 * Part 2: a payments service whose 20 database connections are all stuck behind a lock from 20 s to
 * 50 s. Its process and its HTTP threads are fine. Every 10 s the demo prints what users saw, what a
 * shallow health check (is the process up?) said, and what a deep one (borrow a connection and run
 * `SELECT 1` within 500 ms) said.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l02.demo.GrayDemoKt
 */
fun main() {
    println("Chance that one request touches the one gray switch")
    println("%-10s %10s %10s %10s %10s".format("switches", "fan-out 1", "10", "100", "1,000"))
    for (paths in listOf(4, 16, 64)) {
        val cells = listOf(1, 10, 100, 1_000).map { "%9.1f%%".format(100 * chanceToTouchGray(paths, it)) }
        println("%-10d %10s %10s %10s %10s".format(paths, *cells.toTypedArray()))
    }

    println()
    println("A payments service, 100 requests a second; all 20 database connections stuck from 20 s to 50 s")
    println("%-10s %16s %22s %20s".format("seconds", "users served", "shallow check (live)", "deep check (ready)"))
    val stuck = 20_000L until 50_000L
    for (window in 0L until 70_000L step 10_000L) {
        var served = 0
        var asked = 0
        var shallowUp = 0
        var deepUp = 0
        for (t in window until window + 10_000L step 10L) {        // a request every 10 ms
            asked++
            if (t !in stuck) served++                                // a user's payment needs a connection
            if (t % 1_000L == 0L) {                                  // the load balancer checks every second
                shallowUp++                                          // the HTTP thread answers: the process is up
                if (t !in stuck) deepUp++                            // SELECT 1 needs a connection too
            }
        }
        println("%-10s %15d%% %18d of 10 %16d of 10".format("${window / 1_000}-${window / 1_000 + 10}", 100 * served / asked, shallowUp, deepUp))
    }
}
