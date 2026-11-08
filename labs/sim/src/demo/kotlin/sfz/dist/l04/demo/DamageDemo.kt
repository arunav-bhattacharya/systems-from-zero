package sfz.dist.l04.demo

/**
 * Lesson dist-04, section 4: stale writes against pause length. Each cell is the total over 20 runs of ten virtual
 * minutes, with pauses arriving at random on both holders, on average every 5 s. The last column gives the careful
 * holder a 10 s lease (renewed below 5 s) instead of 2 s. Runs in about two seconds.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l04.demo.DamageDemoKt -q
 */
fun main() {
    val pauses = listOf(250L, 500L, 1_000L, 1_500L, 2_000L, 3_000L, 5_000L, 8_000L)
    val seeds = 1..20
    val tenSeconds = Scenario(ttlMs = 10_000, renewBelowMs = 5_000)
    val columns = listOf(
        "naive" to sweep(Naive, pauses, seeds),
        "careful 0" to sweep(Careful(0), pauses, seeds),
        "careful 200" to sweep(Careful(200), pauses, seeds),
        "careful 500" to sweep(Careful(500), pauses, seeds),
        "careful, 10 s" to sweep(Careful(200), pauses, seeds, tenSeconds),
    )
    println("stale writes in 20 runs of 10 minutes; lease 2 s unless marked, work 60 ms, send 5 ms")
    println("pause ms " + columns.joinToString("") { "%14s".format(it.first) })
    for (pause in pauses) {
        println("%,8d ".format(pause) + columns.joinToString("") { "%,14d".format(it.second.getValue(pause)) })
    }

    println()
    for ((name, policy) in listOf("naive" to Naive, "careful 200" to Careful(200))) {
        val runs = seeds.map { simulate(Scenario(seed = it, pauseMs = 3_000), policy) }
        println("%-12s with 3 s pauses: %,d writes, %,d stale, %,d of those landed after a newer holder's write".format(
            name, runs.sumOf { it.writes.size }, runs.sumOf { staleWrites(it).size }, runs.sumOf { clobbers(it).size }))
    }
}
