package sfz.repl.l01.demo

/**
 * Lesson repl-01, section 1: two clients update one payment on two copies.
 *
 * Without a leader each client sends its update to both copies itself, and the network decides the
 * order each copy sees. With a leader, the leader numbers the updates and both copies apply them in
 * that order. Run: ./gradlew :sim:demo -Pmain=sfz.repl.l01.demo.OrderDemoKt
 * Optional: -Pargs='3 9' sets the delays (ms) from client B to copy X and to copy Y.
 */
fun main(args: Array<String>) {
    val bToX = args.getOrNull(0)?.toLong() ?: 9
    val bToY = args.getOrNull(1)?.toLong() ?: 3
    // one-way delays in ms: client A is close to copy X, client B (by default) is close to copy Y
    val delay = mapOf(("A" to "X") to 2L, ("A" to "Y") to 8L, ("B" to "X") to bToX, ("B" to "Y") to bToY)

    println("Payment pay-77 starts as 'authorized'. At 0 ms client A sends 'captured'; at 1 ms client B sends 'refunded'.")
    println()
    println("No leader: each client writes to both copies")
    val sim = Sim()
    val copies = mutableMapOf("X" to mutableListOf<String>(), "Y" to mutableListOf())
    fun send(client: String, at: Long, status: String) {
        for (copy in listOf("X", "Y")) {
            val arrive = at + delay.getValue(client to copy)
            sim.at(arrive) {
                copies.getValue(copy) += status
                println("  %3d ms  copy %s applies %-9s (from client %s)".format(sim.now, copy, status, client))
            }
        }
    }
    sim.at(0) { send("A", 0, "captured") }
    sim.at(1) { send("B", 1, "refunded") }
    sim.runUntil(100)
    println("  copy X says pay-77 is ${copies.getValue("X").last()}, copy Y says ${copies.getValue("Y").last()}")
    println()

    println("One leader (copy X): it puts the updates in its log, the follower (copy Y) applies the log in order")
    val sim2 = Sim()
    val log = mutableListOf<String>()
    val follower = mutableListOf<String>()
    fun write(client: String, at: Long, status: String) {
        val arriveAtLeader = at + delay.getValue(client to "X")
        sim2.at(arriveAtLeader) {
            log += status
            val position = log.size
            println("  %3d ms  leader X logs position %d: %-9s (from client %s)".format(sim2.now, position, status, client))
            sim2.after(6) {
                // the follower applies only the next position, so it can't see 2 before 1
                follower += log[position - 1]
                println("  %3d ms  follower Y applies position %d: %s".format(sim2.now, position, log[position - 1]))
            }
        }
    }
    sim2.at(0) { write("A", 0, "captured") }
    sim2.at(1) { write("B", 1, "refunded") }
    sim2.runUntil(100)
    println("  leader X says pay-77 is ${log.last()}, follower Y says ${follower.last()}")
}
