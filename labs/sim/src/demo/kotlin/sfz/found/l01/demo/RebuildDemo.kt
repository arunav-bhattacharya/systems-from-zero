package sfz.found.l01.demo

/**
 * One log, three derived views. The views are kept up to date as events arrive, then one of them
 * misses an update, and finally all of them are thrown away and rebuilt from the log.
 */
private data class Event(val id: String, val merchant: String, val day: String, val kind: String, val cents: Long)

private val log = mutableListOf<Event>()                              // the system of record
private val index = HashMap<String, String>()                         // payment id -> latest status
private val daily = HashMap<Pair<String, String>, Long>()             // (merchant, day) -> net cents
private val balanceCache = HashMap<String, Long>()                    // merchant -> all-time balance

private fun balanceFromLog(merchant: String): Long =                 // the slow path: read everything
    log.filter { it.merchant == merchant }.sumOf { if (it.kind == "CAPTURED") it.cents else if (it.kind == "REFUNDED") -it.cents else 0 }

private fun balance(merchant: String) = balanceCache.getOrPut(merchant) { balanceFromLog(merchant) }

private fun applyToViews(e: Event, tellCache: Boolean = true) {
    index[e.id] = e.kind
    val delta = when (e.kind) { "CAPTURED" -> e.cents; "REFUNDED" -> -e.cents; else -> 0 }
    if (delta != 0L) daily.merge(e.merchant to e.day, delta, Long::plus)
    if (tellCache) balanceCache.remove(e.merchant)
}

private fun record(e: Event, tellCache: Boolean = true) {
    log += e                       // 1. the log first
    applyToViews(e, tellCache)     // 2. then every derived view
}

private fun show(title: String) {
    println("-- $title")
    println("   index:  pay-1=${index["pay-1"]} pay-2=${index["pay-2"]} pay-3=${index["pay-3"]}")
    println("   daily:  m-cafe 03-02=${daily["m-cafe" to "2026-03-02"] ?: 0} m-cafe 03-03=${daily["m-cafe" to "2026-03-03"] ?: 0} m-books 03-02=${daily["m-books" to "2026-03-02"] ?: 0}")
    println("   cache:  m-cafe balance=${balance("m-cafe")}   (log says ${balanceFromLog("m-cafe")})")
}

fun main() {
    record(Event("pay-1", "m-cafe", "2026-03-02", "AUTHORIZED", 4000))
    record(Event("pay-2", "m-books", "2026-03-02", "AUTHORIZED", 1250))
    record(Event("pay-1", "m-cafe", "2026-03-02", "CAPTURED", 4000))
    record(Event("pay-2", "m-books", "2026-03-02", "CAPTURED", 1250))
    record(Event("pay-3", "m-cafe", "2026-03-02", "AUTHORIZED", 900))
    record(Event("pay-3", "m-cafe", "2026-03-02", "CAPTURED", 900))
    show("live views after ${log.size} events")

    // a refund arrives, but the message that should clear the cache is lost
    record(Event("pay-1", "m-cafe", "2026-03-03", "REFUNDED", 4000), tellCache = false)
    show("after a refund the cache never heard about")

    // drop every derived view and rebuild it from the log
    index.clear(); daily.clear(); balanceCache.clear()
    log.forEach { applyToViews(it) }
    show("all views dropped and rebuilt from ${log.size} log records")
}
