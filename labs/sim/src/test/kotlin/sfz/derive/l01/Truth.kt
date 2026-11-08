package sfz.derive.l01

/**
 * Test helpers: what the tables should hold, computed the slow way, straight from the log, with
 * no jobs involved. This is the batch recomputation a kappa job has to match.
 */
object Truth {
    /** Net cents per (merchant, day the payment happened), optionally leaving one payment out. */
    fun netByEventDay(log: EventLog, except: String? = null): Map<Pair<String, Long>, Long> {
        val out = HashMap<Pair<String, Long>, Long>()
        for (r in log.read(0, Int.MAX_VALUE)) {
            val e = r.event
            if (e.paymentId == except) continue
            out.merge(e.merchant to dayOf(e.eventTime), if (e.kind == Kind.CAPTURED) e.cents else -e.cents, Long::plus)
        }
        return out
    }

    /** What v1 should hold: gross captured cents per (merchant, day the record arrived). */
    fun grossByArrivalDay(world: World, except: String? = null): Map<Pair<String, Long>, Long> {
        val out = HashMap<Pair<String, Long>, Long>()
        for (r in world.log.read(0, Int.MAX_VALUE)) {
            val e = r.event
            if (e.paymentId == except || e.kind != Kind.CAPTURED) continue
            out.merge(e.merchant to dayOf(world.arrivedAt(r.offset)), e.cents, Long::plus)
        }
        return out
    }

    /** Ticks the world until v2 has read everything. Returns the number of ticks it took. */
    fun catchUp(world: World, migration: Migration, live: Int = 5): Int {
        val v2 = checkNotNull(migration.v2) { "start v2 first" }
        var ticks = 0
        do {
            world.tick(migration, live)
            ticks++
            check(ticks < 100_000) { "v2 never caught up" }
        } while (v2.lag > 0)
        return ticks
    }
}
