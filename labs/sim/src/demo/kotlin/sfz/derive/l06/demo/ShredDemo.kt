package sfz.derive.l06.demo

// 1,000 payment events by 50 customers. Names and emails are encrypted with one key per customer.
// One customer asks to be erased. We forget their key, replay the log, and then restore last
// night's key backup, first naively and then with the erasure ledger.
fun main() {
    val keys = KeyStore(seed = 3)
    val store = EventStore(keys)
    Customers.seed(store, seed = 9)
    val ana = Customers.subject(17)
    val anas = store.all.count { it.subject == ana }
    val hits = String(store.rawBytes(), Charsets.ISO_8859_1).windowed(9).count { it == "zz-plain-" }
    println("${store.all.size} events, ${Customers.merchants.size} merchants; $ana has $anas events")
    println("plaintext emails found in the raw log: $hits")

    val backup = keys.backup()                                     // last night's backup of the key store
    val before = rebuild(store, keys)
    println("\nbefore: decryptable ${decryptable(store, keys, ana)} of $anas, row ${before.customers[ana]}")

    val ledger = ErasureLedger()
    erase(ana, keys, ledger)
    val after = rebuild(store, keys)
    println("after:  decryptable ${decryptable(store, keys, ana)} of $anas, row ${after.customers[ana]}")
    println("events still in the log: ${store.all.size}; merchant totals unchanged: ${after.merchantTotals == before.merchantTotals}")

    keys.restore(backup, ErasureLedger())
    println("\nrestore the backup, no ledger:   decryptable ${decryptable(store, keys, ana)} of $anas")
    keys.restore(backup, ledger)
    println("restore the backup, with ledger: decryptable ${decryptable(store, keys, ana)} of $anas")
}
