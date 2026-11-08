package sfz.derive.l04.demo

// 2,000 users claim handles drawn from 200 popular ones. Three designs, same claims, same seed.
fun main() {
    val claims = Workload.claims(seed = 42)
    val wanted = claims.map { it.username }.toSet().size
    println("${claims.size} claims for $wanted different handles\n")
    println("design                                  granted  duplicates  p50 wait  p99 wait")
    fun row(name: String, run: ClaimRun) = println(
        "%-38s %8d %11d %9d %9d".format(name, run.granted, run.duplicates, percentile(run.waits, 0.5), percentile(run.waits, 0.99)),
    )
    row("check-then-insert, 64 servers", checkThenInsert(claims, servers = 64, seed = 1))
    row("log keyed by handle, 8 partitions", throughLog(claims, clients = 64, partitions = 8, seed = 1))
    row("log keyed by userId, 8 partitions", throughLog(claims, clients = 64, partitions = 8, seed = 1, keyOf = Claim::userId))
    println("\nwaits are in scheduler steps; more partitions, shorter queues:")
    for (n in listOf(1, 2, 4, 8, 16)) row("log keyed by handle, $n partition${if (n > 1) "s" else ""}", throughLog(claims, 64, n, seed = 1))
}
