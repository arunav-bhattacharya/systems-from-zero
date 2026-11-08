package sfz.derive.l04.demo

// The same 1,000 wallet-to-wallet transfers and the same faults, through three designs.
// Faults: consumers crash about once every 100 messages and replay what they hadn't saved,
// 5% of clients send their transfer twice, and in the first design the API sometimes crashes
// between its two writes.
fun main() {
    val config = TransferConfig()
    val expected = config.expectedTotal
    fun money(total: Long) = "money in the system: $total (should be $expected, off by ${total - expected})"

    val broken = runSeparateSteps(config)
    println("-- debit and credit as two separate writes, applied with balance += delta")
    println("   half-written transfers ${broken.halfWritten}, debits refused on their own ${broken.declinedDebits}, steps applied twice ${broken.reapplied}")
    println("   ${money(broken.totalMoney)}")

    val calm = runSeparateSteps(config.copy(crashChance = 0.0, clientRetryChance = 0.0, apiCrashChance = 0.0))
    println("-- the same two writes with no faults at all")
    println("   debits refused on their own ${calm.declinedDebits}")
    println("   ${money(calm.totalMoney)}")

    val noIds = runTransfers(config.copy(dedupe = false))
    println("-- one logged request, debit and credit derived from it, request ids not checked")
    println("   crashes ${noIds.crashes}, credits sent ${noIds.creditsSent} for ${noIds.accepted} accepted transfers")
    println("   ${money(noIds.totalMoney)}")

    val good = runTransfers(config)
    println("-- one logged request, debit and credit derived from it, request ids checked")
    println("   crashes ${good.crashes}, credits sent ${good.creditsSent} for ${good.accepted} accepted transfers")
    println("   ${money(good.totalMoney)}")
}
