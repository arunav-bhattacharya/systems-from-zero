package sfz.model.l09

// What the backend stores: three kinds of record, linked by id.
data class Payment(val id: String, val merchantId: String, val accountId: String, val amountMinor: Long)
data class Account(val id: String, val customerId: String, val iban: String)
data class Customer(val id: String, val name: String)

/**
 * The backend the GraphQL server sits on: a payments service, an accounts service and a
 * customers service, or three tables. Every method is ONE round trip, and [calls] counts them,
 * the way `pg_stat_statements` counts statements. [log] records each call, for your debugging.
 */
class Backend(payments: List<Payment>, accounts: List<Account>, customers: List<Customer>) {
    private val payments = payments.toList()
    private val accounts = accounts.associateBy { it.id }
    private val customers = customers.associateBy { it.id }

    var calls = 0
        private set
    val log = mutableListOf<String>()

    private fun call(what: String) { calls++; log += what }

    /** A merchant's newest payments, at most [last]. One call. */
    fun paymentsOfMerchant(merchantId: String, last: Int): List<Payment> {
        call("paymentsOfMerchant($merchantId, $last)")
        return payments.filter { it.merchantId == merchantId }.takeLast(last).reversed()
    }

    /** One account by id. One call. */
    fun account(id: String): Account? { call("account($id)"); return accounts[id] }

    /** Many accounts in one call: `WHERE id IN (...)`. Ids that don't exist are left out of the map. */
    fun accounts(ids: Set<String>): Map<String, Account> {
        call("accounts(${ids.size} ids)")
        return ids.mapNotNull { accounts[it] }.associateBy { it.id }
    }

    /** One customer by id. One call. */
    fun customer(id: String): Customer? { call("customer($id)"); return customers[id] }

    /** Many customers in one call. */
    fun customers(ids: Set<String>): Map<String, Customer> {
        call("customers(${ids.size} ids)")
        return ids.mapNotNull { customers[it] }.associateBy { it.id }
    }
}

// The response, shaped like the query a client sent:
//   { payments(merchant: "M-0042", last: 50) { id amountMinor account { iban customer { name } } } }
data class CustomerView(val name: String)
data class AccountView(val iban: String, val customer: CustomerView?)
data class PaymentView(val id: String, val amountMinor: Long, val account: AccountView?)

/**
 * The way a GraphQL server runs that query if every field has its own resolver: the `payments`
 * resolver runs once, then the `account` resolver runs once PER PAYMENT, then the `customer`
 * resolver once PER ACCOUNT. Given. Count the calls: 1 + N + N.
 */
object NaiveResolvers {
    fun resolve(backend: Backend, merchantId: String, last: Int): List<PaymentView> =
        backend.paymentsOfMerchant(merchantId, last).map { p ->
            val account = backend.account(p.accountId)                     // Payment.account resolver
            PaymentView(p.id, p.amountMinor, account?.let { a ->
                val customer = backend.customer(a.customerId)              // Account.customer resolver
                AccountView(a.iban, customer?.let { CustomerView(it.name) })
            })
        }
}

/**
 * The same query with batching, the DataLoader idea: resolve one LEVEL of the tree at a time.
 *
 * 1. Fetch the payments (one call).
 * 2. Collect the DISTINCT account ids of all of them and fetch them with [Backend.accounts]
 *    (one call). Skip the call when there are no ids.
 * 3. Collect the distinct customer ids of the accounts you got and fetch them with
 *    [Backend.customers] (one call, skipped when there are none).
 * 4. Build the same views [NaiveResolvers] builds, in the same order. A payment whose account
 *    doesn't exist gets `account = null`; an account whose customer doesn't exist gets `customer = null`.
 *
 * However many payments there are, that's at most 3 calls.
 */
object BatchedResolvers {
    fun resolve(backend: Backend, merchantId: String, last: Int): List<PaymentView> {
        TODO("one call per level: payments, then the distinct accounts, then the distinct customers")
    }
}
