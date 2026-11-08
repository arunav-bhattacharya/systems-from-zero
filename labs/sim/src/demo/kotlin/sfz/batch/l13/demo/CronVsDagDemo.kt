package sfz.batch.l13.demo

import kotlin.random.Random

/**
 * Thirty nights of a two-job pipeline. Job 1 imports the acquirer's settlement file, which usually
 * lands at about 00:30 but some nights is hours late. Job 2 builds the settlement report from it.
 * With cron, job 2 starts at 02:00 every night, a guess that "job 1 is surely done by then". With
 * a DAG, job 2 starts when job 1 finishes.
 */
fun main() {
    val rnd = Random(2026)
    fun clock(m: Int) = "%02d:%02d".format(m / 60, m % 60)
    var wrong = 0
    val cronReady = mutableListOf<Int>()
    val dagReady = mutableListOf<Int>()
    println("night  file lands  import done  cron report (02:00)        DAG report")
    for (night in 1..30) {
        val late = rnd.nextDouble() < 0.1
        val lands = 30 + if (late) 60 + rnd.nextInt(120) else rnd.nextInt(15)
        val imported = lands + 40 + rnd.nextInt(40)                  // the import takes 40 to 80 minutes
        val cronOk = imported <= 120
        if (!cronOk) wrong++
        cronReady += 120 + 10
        dagReady += imported + 10                                     // the report itself takes 10 minutes
        if (!cronOk || night <= 3) {
            println("%5d  %10s  %11s  %-25s  %s".format(night, clock(lands), clock(imported),
                if (cronOk) "${clock(130)}, right" else "${clock(130)}, read a partial day", "${clock(imported + 10)}, right"))
        }
    }
    println("(nights 4 to 30 not shown unless cron got them wrong)")
    println("cron: $wrong of 30 reports built from a partial import; every report ready at ${clock(130)}")
    println("DAG:  0 of 30 wrong; reports ready at a median ${clock(dagReady.sorted()[15])}, the latest at ${clock(dagReady.max())}")
}
