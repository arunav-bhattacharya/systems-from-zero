package sfz.dist.l06.demo

/**
 * Lesson dist-06, section 4: a Snowflake-style generator when NTP steps its clock back 1 s, before and after the
 * fix; then two machines whose clocks are 40 ms apart.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l06.demo.SnowflakeDemoKt -q
 */
fun main() {
    val t0 = SnowflakeIds.EPOCH_MS + 26_000_000_000L          // some day in 2026
    for (fixed in listOf(false, true)) {
        var wall = t0
        val next: () -> Long = if (fixed) SnowflakeIds(7) { wall }::next else NaiveSnowflake(7) { wall }::next
        val made = mutableListOf<Long>()
        for (i in 0 until 6) {
            if (i == 3) wall -= 1_000                            // NTP steps the clock back one second
            made += next()
            if (i != 2) wall += 500
        }
        println(if (fixed) "fixed generator:" else "naive generator:")
        for ((i, id) in made.withIndex()) {
            val back = if (i > 0 && id <= made[i - 1]) "   <- not larger than the one before" else ""
            println("  id %d  ms +%d  seq %d%s".format(id, SnowflakeIds.timestampOf(id) - t0, SnowflakeIds.sequenceOf(id), back))
        }
        println("  ${made.toSet().size} distinct of ${made.size}, increasing: ${made.zipWithNext().all { (a, b) -> a < b }}")
    }

    // pay-81723: machine 1 authorizes, tells machine 2, which captures 5 ms later. Machine 1's clock is 40 ms ahead.
    var real = t0
    val m1 = SnowflakeIds(1) { real + 40 }
    val m2 = SnowflakeIds(2) { real }
    val auth = m1.next()
    real += 5                                                    // the message takes 5 ms
    val capture = m2.next()
    println("two machines, 40 ms apart: authorization id $auth, capture id $capture, capture sorts first: ${capture < auth}")
}

/** The generator from the start of the section, with its two bugs (the lab's stub). */
private class NaiveSnowflake(val machine: Int, val clock: () -> Long) {
    private var lastMs = -1L
    private var sequence = 0
    fun next(): Long {
        val ms = clock()
        sequence = if (ms == lastMs) (sequence + 1) and SnowflakeIds.MAX_SEQUENCE else 0
        lastMs = ms
        return SnowflakeIds.compose(ms, machine, sequence)
    }
}
