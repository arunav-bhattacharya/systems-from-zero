package sfz.derive.l03

import kotlin.random.Random

/*
 * Lesson derive-03 (given, nothing to change in this file).
 */

/** How much of the pipeline removes duplicates. Each variant includes the ones before it. */
enum class Variant {
    /** Nothing removes duplicates. */
    NONE,

    /** Plus TCP-style sequence numbers within one connection. */
    TRANSPORT,

    /** Plus the broker's idempotent producer and exactly-once inside the broker. */
    BROKER,

    /** Plus a request id made on the phone, carried to the ledger and kept unique there. */
    END_TO_END,
}

/** The chance of each fault, per event. */
data class Rates(
    /** The network delivers one request twice on the same connection (a retransmission). */
    val duplicatePacket: Double = 0.02,
    /** The server did the work, and the response never reached the phone, which times out and retries. */
    val lostResponse: Double = 0.03,
    /** The broker appended the record, and its ack to the producer was lost, so the producer resends. */
    val lostAck: Double = 0.02,
    /** The consumer wrote the ledger row, then died before committing its offset, so it gets the record again. */
    val consumerCrash: Double = 0.015,
)

/**
 * Which fault hits which event. Each decision is a hash of the seed, the kind of fault and the
 * event's name ("i17/a2" for the second attempt of transfer 17), so it doesn't depend on the order
 * code asks, or on how many other events happened. The same seed gives the same faults in every
 * variant.
 */
class Faults(private val seed: Long, val rates: Rates = Rates()) {
    private fun hit(kind: String, key: String, rate: Double): Boolean =
        Random(seed * 31 + "$kind/$key".hashCode()).nextDouble() < rate

    fun duplicatePacket(intent: Int, attempt: Int) = hit("dup", "i$intent/a$attempt", rates.duplicatePacket)
    fun lostResponse(intent: Int, attempt: Int) = hit("resp", "i$intent/a$attempt", rates.lostResponse)
    fun lostAck(trace: String) = hit("ack", trace, rates.lostAck)
    fun consumerCrash(trace: String, delivery: Int) = hit("crash", "$trace/d$delivery", rates.consumerCrash)
}
