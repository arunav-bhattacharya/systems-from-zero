package sfz.dist.l01.demo

/**
 * Lesson dist-01, sections 2 and 3: 1,000 payments through a faulty network, audited against the
 * issuer's own records.
 *
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l01.demo.AuditDemoKt -Pargs='oneway'
 *      one-way faults: only requests, or only replies, are lost
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l01.demo.AuditDemoKt -Pargs='retries'
 *      retries with and without an idempotency key, and a network that duplicates packets
 * Optional second argument: the loss rate (default 0.3 for oneway, 0.2 for retries).
 */
fun main(args: Array<String>) {
    val mode = args.firstOrNull() ?: "oneway"
    val loss = args.getOrNull(1)?.toDouble() ?: if (mode == "oneway") 0.3 else 0.2
    println("1,000 payments, one every 10 ms; the issuer takes 50 ms; timeout 1,000 ms per attempt")
    println()
    println("%-40s %8s %8s %18s %15s %14s".format("scenario", "approved", "unknown", "unknown, charged", "double-charged", "extra charges"))
    val rows = when (mode) {
        "oneway" -> listOf(
            "requests lost ($loss), replies fine" to payments(requests = Faults(loss = loss)),
            "requests fine, replies lost ($loss)" to payments(replies = Faults(loss = loss)),
            "both directions lost (${loss / 2} each)" to payments(faults = Faults(loss = loss / 2)),
        )
        else -> listOf(
            "loss $loss, 1 attempt, no key check" to payments(faults = Faults(loss = loss), dedupe = false),
            "loss $loss, 3 attempts, no key check" to payments(faults = Faults(loss = loss), maxAttempts = 3, dedupe = false),
            "loss $loss, 3 attempts, key checked" to payments(faults = Faults(loss = loss), maxAttempts = 3, dedupe = true),
            "duplicates 0.2, no key check" to payments(faults = Faults(duplicate = 0.2), dedupe = false),
            "duplicates 0.2, key checked" to payments(faults = Faults(duplicate = 0.2), dedupe = true),
        )
    }
    for ((name, run) in rows) {
        val a = run.audit
        println("%-40s %8d %8d %18d %15d %14d".format(name, a.approved, a.unknown, a.unknownButCharged, a.doubleCharged, a.extraCharges))
    }
}
