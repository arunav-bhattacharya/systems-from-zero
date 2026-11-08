package sfz.txn.l06

import redis.clients.jedis.RedisClient

/**
 * The same balances as [WatchTransfer], with the transfer done by a Lua script on the server, and accounts
 * opened in bulk with a pipeline.
 */
class ScriptedLedger(private val redis: RedisClient) {

    companion object {
        /**
         * The transfer script. KEYS[1] is the source, KEYS[2] the destination, ARGV[1] the amount in cents.
         * Write it so that it:
         *
         * 1. reads the source balance: `tonumber(redis.call('GET', KEYS[1]) or '0')` (a missing key comes back
         *    as `false`, so `or '0'` makes it 0),
         * 2. returns 0 if the balance is smaller than `tonumber(ARGV[1])`,
         * 3. otherwise runs DECRBY on KEYS[1] and INCRBY on KEYS[2] with the amount, and returns 1.
         */
        const val TRANSFER = """
            return redis.error_reply('TODO: write the transfer script')
        """
    }

    /** The SHA1 of [TRANSFER] once it is loaded. Use it. */
    @Volatile
    private var sha: String? = null

    /**
     * Runs [TRANSFER] and returns true if the money moved. Send it with
     * `redis.evalsha(sha, listOf(from, to), listOf(amount.toString()))`, loading it first with
     * `redis.scriptLoad(TRANSFER)` if [sha] is still null. The server's script cache can be emptied at any time
     * (a restart, a failover, SCRIPT FLUSH): then EVALSHA throws `JedisNoScriptException`. Catch it, load the
     * script again and retry once. The script returns a Lua number, which arrives as a `Long`.
     */
    fun transfer(from: String, to: String, amount: Long): Boolean {
        TODO("lesson 6 lab: EVALSHA, and SCRIPT LOAD again on NOSCRIPT")
    }

    /**
     * SETs every account to its balance in cents, with one pipeline: `redis.pipelined().use { pipe -> ... }`,
     * a `pipe.set(...)` per account, then `pipe.sync()`. Not one round trip per account.
     */
    fun openAccounts(balances: Map<String, Long>) {
        TODO("lesson 6 lab: one pipeline of SETs")
    }
}
