package sfz.model.l09

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class ResolversTest {
    // 60 payments for M-0042 from 12 accounts; the accounts belong to 5 customers.
    // pay-0057's account A-404 doesn't exist (it was closed), and A-11's customer is missing.
    private fun backend(): Backend {
        val payments = (1..60).map { i ->
            val account = if (i == 57) "A-404" else "A-${i % 12}"
            Payment("pay-%04d".format(i), "M-0042", account, 1_000L + i)
        } + Payment("pay-9999", "M-0051", "A-1", 5_000)
        val accounts = (0 until 12).map { a -> Account("A-$a", if (a == 11) "C-gone" else "C-${a % 5}", "LU00 0000 %04d".format(a)) }
        val customers = (0 until 5).map { Customer("C-$it", "Customer $it") }
        return Backend(payments, accounts, customers)
    }

    @Test
    fun `naive resolvers make one call for the list plus one per payment and one per account`() {
        val b = backend()
        val views = NaiveResolvers.resolve(b, "M-0042", 50)
        assertThat(views).hasSize(50)
        assertThat(views.first().id).isEqualTo("pay-0060")              // newest first
        // 1 + 50 accounts + 49 customers (one payment has no account, so no customer lookup)
        assertThat(b.calls).isEqualTo(100)
    }

    @Test
    fun `batched resolvers return exactly what the naive ones return`() {
        val expected = NaiveResolvers.resolve(backend(), "M-0042", 50)
        assertThat(BatchedResolvers.resolve(backend(), "M-0042", 50)).isEqualTo(expected)
    }

    @Test
    fun `batched resolvers make one call per level, whatever the number of payments`() {
        for (last in listOf(5, 50)) {
            val b = backend()
            BatchedResolvers.resolve(b, "M-0042", last)
            assertThat(b.calls).describedAs("calls for last = $last").isEqualTo(3)
        }
    }

    @Test
    fun `each level asks for distinct ids only`() {
        val b = backend()
        BatchedResolvers.resolve(b, "M-0042", 50)
        // 50 payments use 12 real accounts plus A-404; those 12 accounts belong to 5 customers plus C-gone
        assertThat(b.log).containsExactly("paymentsOfMerchant(M-0042, 50)", "accounts(13 ids)", "customers(6 ids)")
    }

    @Test
    fun `missing records become nulls, not errors`() {
        val views = BatchedResolvers.resolve(backend(), "M-0042", 60).associateBy { it.id }
        assertThat(views.getValue("pay-0057").account).isNull()
        assertThat(views.getValue("pay-0011").account!!.customer).isNull()     // A-11's customer is gone
        assertThat(views.getValue("pay-0012").account!!.customer).isEqualTo(CustomerView("Customer 0"))
    }

    @Test
    fun `a merchant with no payments costs one call`() {
        val b = backend()
        assertThat(BatchedResolvers.resolve(b, "M-0000", 50)).isEmpty()
        assertThat(b.calls).isEqualTo(1)
    }
}
