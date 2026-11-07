package sfz.net.support

/**
 * A clock the test moves by hand, for anything with a timeout: ARP entries, NAT mappings,
 * TIME_WAIT, DNS TTLs.
 *
 * Lab classes that expire state take a `clock: () -> Long` (milliseconds) and default to
 * `System::currentTimeMillis`. Pass a ManualClock instead, then call [advance] to jump ahead
 * without sleeping, so the tests stay fast and give the same answer every run.
 */
class ManualClock(var nowMillis: Long = 1_000_000L) : () -> Long {
    override fun invoke(): Long = nowMillis

    fun advance(millis: Long) {
        require(millis >= 0) { "time only moves forward" }
        nowMillis += millis
    }

    fun advanceSeconds(seconds: Long) = advance(seconds * 1_000)
}
