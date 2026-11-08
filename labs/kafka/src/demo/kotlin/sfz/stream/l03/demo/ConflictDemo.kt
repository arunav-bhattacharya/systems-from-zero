package sfz.stream.l03.demo

/**
 * Lesson stream-03, Try it 2: two command handlers withdraw 80.00 from an account that holds
 * 100.00, each after checking the balance it loaded. First with a store that appends blindly, then
 * with a store that checks the stream version the handler saw.
 */

class VersionConflict(msg: String) : RuntimeException(msg)

class Stream(private val checkVersion: Boolean) {
    val events = mutableListOf<Long>()                  // signed amounts in cents, oldest first

    fun load(): Pair<Long, Int> = events.sum() to events.size   // (balance, version)

    fun append(expectedVersion: Int, amount: Long) {
        if (checkVersion && events.size != expectedVersion) {
            throw VersionConflict("expected version $expectedVersion, stream is at ${events.size}")
        }
        events += amount
    }
}

/** The aggregate's rule: no withdrawal larger than the balance it knows about. */
fun withdraw(stream: Stream, name: String, cents: Long, loaded: Pair<Long, Int>) {
    val (balance, version) = loaded
    if (cents > balance) { println("  $name: rejected, balance is ${eur(balance)}"); return }
    try {
        stream.append(version, -cents)
        println("  $name: saw v$version, balance ${eur(balance)}: appended MoneyWithdrawn -${eur(cents)} as event ${stream.events.size}")
    } catch (e: VersionConflict) {
        println("  $name: conflict, ${e.message}")
        val fresh = stream.load()
        print("  $name: reloads v${fresh.second}, balance ${eur(fresh.first)}, and decides again -> ")
        if (cents > fresh.first) println("rejected: insufficient funds") else { stream.append(fresh.second, -cents); println("appended") }
    }
}

fun main() {
    for (check in listOf(false, true)) {
        val stream = Stream(checkVersion = check)
        stream.append(0, 0)                              // v1 AccountOpened (amount 0)
        stream.append(1, 10_000)                         // v2 MoneyDeposited 100.00
        println(if (check) "append with expected version:" else "append without a version check:")
        val a = stream.load()                            // both handlers load before either appends
        val b = stream.load()
        withdraw(stream, "handler A", 8_000, a)
        withdraw(stream, "handler B", 8_000, b)
        println("  final: ${stream.events.size} events, balance ${eur(stream.events.sum())}")
        println()
    }
}
