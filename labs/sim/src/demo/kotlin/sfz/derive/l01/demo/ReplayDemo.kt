package sfz.derive.l01.demo

import kotlin.random.Random

/**
 * Try it, derive-01 section 4: replay 30 days into v2, by processing time and by event time.
 *
 * The same world as the lab: 30 days x 200 payments, 3% of them uploaded 6 to 10 hours late.
 * Today at 09:00 two copies of v2 start from offset 0 and read 400 records a minute while 5 new
 * payments arrive each minute. One buckets by the minute it processes a record (processing
 * time), the other by the minute the payment happened (event time).
 *
 * Pass a batch size to change the replay speed: -Pargs=100
 */
private const val DAY = 1440L

private data class Pay(val merchant: String, val eventTime: Long, val refund: Boolean, val cents: Long)

fun main(args: Array<String>) {
    val batch = args.firstOrNull()?.toInt() ?: 400
    val random = Random(2026)
    val merchants = (1..20).map { "m-%02d".format(it) }
    fun pay(t: Long): Pay {
        val refund = random.nextDouble() < 0.1
        return Pay(merchants[random.nextInt(20)], t, refund, if (refund) 500 + random.nextLong(3_000) else 500 + random.nextLong(19_500))
    }

    // history: the log holds payments in the order they arrived
    val log = ArrayList<Pay>()
    val history = (0 until 30).flatMap { d ->
        (0 until 200).map {
            val p = pay(d * DAY + 8 * 60 + random.nextLong(14 * 60))
            val delay = if (random.nextDouble() < 0.03) 360 + random.nextLong(240) else random.nextLong(3)
            p.eventTime + delay to p
        }
    }.sortedWith(compareBy({ it.first }, { it.second.eventTime }))
    for ((_, p) in history) log += p

    val v2Processing = HashMap<Pair<String, Long>, Long>()
    val v2Event = HashMap<Pair<String, Long>, Long>()
    fun net(p: Pay) = if (p.refund) -p.cents else p.cents

    // today, 09:00: start both v2 jobs at offset 0
    var now = 30 * DAY + 9 * 60
    var position = 0
    var minutes = 0
    do {
        now += 1
        minutes++
        repeat(5) { log += pay(now) }
        val stop = minOf(log.size, position + batch)
        for (i in position until stop) {
            v2Processing.merge(log[i].merchant to now / DAY, net(log[i]), Long::plus)
            v2Event.merge(log[i].merchant to log[i].eventTime / DAY, net(log[i]), Long::plus)
        }
        position = stop
    } while (position < log.size)

    println("v2 read ${"%,d".format(log.size)} records in $minutes minutes ($batch a minute, 5 new a minute)")
    println()
    println("net revenue, all merchants, by day:")
    println("  day   v2 by processing time   v2 by event time")
    fun total(m: Map<Pair<String, Long>, Long>, day: Long) = merchants.sumOf { m[it to day] ?: 0 }
    for (day in listOf(0L, 1L, 2L, 28L, 29L, 30L)) {
        if (day == 28L) println("  ...")
        println("  %3d   %21s   %16s".format(day, "%,.2f".format(total(v2Processing, day) / 100.0), "%,.2f".format(total(v2Event, day) / 100.0)))
    }
}
