package sfz.derive.l06.demo

import kotlin.random.Random

// An invented fraud model, built to show one mechanism. 20,000 card payments; 30% come from
// neighbourhood B. Real fraud is 1% in both groups. The model never sees the group. It sees a
// postcode risk score learned from past chargeback investigations, and investigators used to check
// B's postcodes far more often, so B's postcodes carry more recorded fraud. It flags the riskiest 5%.

private class Payment(val groupB: Boolean, val fraud: Boolean, val postcodeRisk: Double, val behaviour: Double)

private fun report(name: String, payments: List<Payment>, score: (Payment) -> Double) {
    val cut = payments.map(score).sortedDescending()[payments.size / 20]          // flag the top 5%
    println("-- $name")
    println("   group  payments  fraud  caught  false alarms  false-positive rate")
    for ((label, g) in listOf("A" to payments.filter { !it.groupB }, "B" to payments.filter { it.groupB })) {
        val flagged = g.filter { score(it) > cut }
        val fp = flagged.count { !it.fraud }
        val honest = g.count { !it.fraud }
        println("   %-5s %9d %6d %7d %13d %19.1f%%".format(label, g.size, g.count { it.fraud }, flagged.count { it.fraud }, fp, 100.0 * fp / honest))
    }
}

fun main() {
    val rnd = Random(11)
    fun gauss() = rnd.nextDouble().let { u -> Math.sqrt(-2 * Math.log(1 - u)) * Math.cos(2 * Math.PI * rnd.nextDouble()) }
    val payments = List(20_000) {
        val b = rnd.nextDouble() < 0.3
        val fraud = rnd.nextDouble() < 0.01
        val postcode = (if (b) 0.6 else 0.3) + 0.1 * gauss()                         // reflects past investigations, not fraud
        val behaviour = (if (fraud) 1.5 else 0.0) + 0.5 * gauss()                    // device, velocity, amount: real signal
        Payment(b, fraud, postcode, behaviour)
    }
    report("model A: postcode risk + behaviour (no group column)", payments) { it.postcodeRisk + it.behaviour }
    report("model B: behaviour only", payments) { it.behaviour }
}
