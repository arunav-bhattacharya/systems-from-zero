package sfz.redis.l06

import redis.clients.jedis.RedisClient
import redis.clients.jedis.exceptions.JedisNoScriptException

class ScriptedLedger(private val redis: RedisClient) {

    companion object {
        // the whole read-check-write runs inside one command, so no other client can run in between
        const val TRANSFER = """
            local balance = tonumber(redis.call('GET', KEYS[1]) or '0')
            local amount = tonumber(ARGV[1])
            if balance < amount then
                return 0
            end
            redis.call('DECRBY', KEYS[1], amount)
            redis.call('INCRBY', KEYS[2], amount)
            return 1
        """
    }

    @Volatile
    private var sha: String? = null

    fun transfer(from: String, to: String, amount: Long): Boolean {
        val keys = listOf(from, to)
        val args = listOf(amount.toString())
        val result = try {
            redis.evalsha(sha ?: load(), keys, args)                // only the 40-character SHA1 goes over the wire
        } catch (e: JedisNoScriptException) {
            redis.evalsha(load(), keys, args)                       // cache lost (restart, failover, SCRIPT FLUSH): reload
        }
        return result == 1L
    }

    fun openAccounts(balances: Map<String, Long>) {
        // one write of every SET and one read of every reply, instead of a round trip each
        redis.pipelined().use { pipe ->
            balances.forEach { (account, cents) -> pipe.set(account, cents.toString()) }
            pipe.sync()
        }
    }

    private fun load(): String = redis.scriptLoad(TRANSFER).also { sha = it }
}
