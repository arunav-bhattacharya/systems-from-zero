package sfz.repl.l02

/**
 * A leader and a follower for the tests. The leader's clock starts at 1,000,000 ms and moves 10 ms
 * per statement; the follower replays each statement 350 ms after the leader ran it, so its now()
 * reads 350 ms later. They seed their random generators differently, as two machines would.
 */
class TwoServers(lagMs: Long = 350) {
    var time: Long = 1_000_000
    val leader = Leader({ time }, seed = 1)
    val follower = Server("follower", { time + lagMs }, seed = 2)

    fun run(vararg statements: Statement) = statements.forEach { time += 10; leader.run(it) }

    /** Six payments, merchants m1 and m2 in turn. */
    fun sixPayments() = run(
        Statement.Insert("m1", 1_250), Statement.Insert("m2", 4_000), Statement.Insert("m1", 990),
        Statement.Insert("m2", 15_000), Statement.Insert("m1", 2_500), Statement.Insert("m2", 700),
    )
}
