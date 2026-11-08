package sfz.derive.l02

/**
 * The derived view: account to balance in cents. [apply] is the derivation function, ordinary
 * application code that turns one log entry into changes of the view.
 */
class Balances(opening: Map<String, Long>) {
    private val balances = HashMap(opening)

    fun get(account: String): Long = balances[account] ?: 0

    /** Takes the cents off `from`, adds them to `to`, and returns the two changes as diffs. */
    fun apply(e: Entry): List<Diff> {
        val t = e.transfer
        balances.merge(t.from, -t.cents, Long::plus)
        balances.merge(t.to, t.cents, Long::plus)
        // the diffs carry the entry's offset, so whoever receives them can tell old from new
        return listOf(Diff(e.offset, t.from, -t.cents), Diff(e.offset, t.to, t.cents))
    }
}
