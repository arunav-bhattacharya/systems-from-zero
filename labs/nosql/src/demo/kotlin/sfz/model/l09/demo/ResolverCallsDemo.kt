package sfz.model.l09.demo

/**
 * One GraphQL query, resolved field by field:
 *   { payments(merchant: "M-0042", last: N) { id amountMinor account { iban customer { name } } } }
 * Each backend call sleeps 2 ms, a round trip to another service or a database on the same network.
 */
private var calls = 0
private fun roundTrip() { calls++; Thread.sleep(2) }

private data class Pay(val id: Int, val accountId: Int)
private data class Acct(val id: Int, val customerId: Int)

// the three resolvers a naive server runs: Query.payments, Payment.account, Account.customer
private fun payments(n: Int): List<Pay> { roundTrip(); return (1..n).map { Pay(it, it % 12) } }
private fun account(id: Int): Acct { roundTrip(); return Acct(id, id % 5) }
private fun customer(id: Int): String { roundTrip(); return "Customer $id" }

fun main() {
    payments(1).forEach { account(it.accountId) }               // warm up the JIT, untimed
    println("payments  backend calls  time")
    for (n in listOf(10, 50, 200)) {
        calls = 0
        val start = System.nanoTime()
        val response = payments(n).map { p ->
            val a = account(p.accountId)                         // once per payment
            Triple(p.id, a.id, customer(a.customerId))           // once per account
        }
        val ms = (System.nanoTime() - start) / 1_000_000
        check(response.size == n)
        println("%8d  %13d  %d ms".format(n, calls, ms))
    }
}
