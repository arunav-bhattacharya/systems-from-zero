package sfz.derive.l02

/**
 * The derived view: account to balance in cents. [apply] is the derivation function, ordinary
 * application code that turns one log entry into changes of the view.
 */
class Balances(opening: Map<String, Long>) {
    private val balances = HashMap(opening)

    fun get(account: String): Long = balances[account] ?: 0

    /**
     * TODO: take the transfer's cents off its `from` account and add them to its `to` account.
     * Return the two changes as diffs carrying the entry's offset: the `from` diff first, with a
     * negative delta, then the `to` diff.
     */
    fun apply(e: Entry): List<Diff> {
        TODO("move the money and return the two diffs")
    }
}
