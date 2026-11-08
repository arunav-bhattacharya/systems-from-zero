package sfz.msg.l01

import java.util.TreeMap

/**
 * A payment event as the producer published it. [key] is the account it belongs to, and [seq] is its place in that
 * account's history: 0, 1, 2, ... The broker never looks inside a message; [OrderCheck] does.
 */
data class Message(val key: String, val seq: Int)

/**
 * One delivery of one message to one consumer.
 *
 * - [tag] numbers the deliveries of one queue: 1, 2, 3, ... A redelivery of the same message gets a new tag.
 * - [redelivered] is true when the broker has handed this message out before (RabbitMQ's `redeliver` flag).
 * - [deliveryCount] is how many times the message came back to the queue before this delivery: 0 the first time.
 *   RabbitMQ quorum queues show it to consumers as the `x-delivery-count` header.
 */
data class Delivery(
    val tag: Long,
    val consumer: String,
    val message: Message,
    val redelivered: Boolean,
    val deliveryCount: Int,
)

/**
 * One queue of a message broker, kept in memory. It follows the rules of an AMQP 0-9-1 queue such as RabbitMQ's:
 *
 * - messages wait in publish order, and [deliver] hands out the one at the head;
 * - a delivered message stays in the queue, unacknowledged, until its consumer calls [ack]; only then is it gone;
 * - each consumer may hold at most `prefetch` unacknowledged deliveries; with auto-ack a delivery counts as
 *   acknowledged the moment it leaves, and prefetch no longer applies;
 * - when a consumer disconnects (or crashes), every delivery it had not acknowledged goes back to the queue at its
 *   original position, and its next delivery is marked redelivered;
 * - a message that has come back more than [deliveryLimit] times goes to [deadLetters], or is dropped if there is none.
 */
class MiniQueue(val name: String, val deliveryLimit: Int = 20, val deadLetters: MiniQueue? = null) {

    /** A message in the queue. [position] is its place in publish order and never changes. */
    private class Entry(val position: Long, val message: Message, val returns: Int)

    /** A delivered message that its consumer has not acknowledged yet. */
    private class InFlight(val entry: Entry, val consumer: String)

    private class Subscription(val prefetch: Int, val autoAck: Boolean)

    private val waiting = TreeMap<Long, Entry>()              // ready messages by position: firstEntry() is the head
    private val inFlight = LinkedHashMap<Long, InFlight>()    // delivery tag -> unacknowledged delivery, oldest first
    private val subscriptions = HashMap<String, Subscription>()
    private val droppedMessages = ArrayList<Message>()
    private var nextPosition = 0L
    private var nextTag = 1L

    /** How many messages are waiting to be delivered. */
    val ready: Int get() = waiting.size

    /** How many messages have been delivered and not yet acknowledged, over all consumers. */
    val unacked: Int get() = inFlight.size

    /** How many messages [consumer] holds without having acknowledged them. */
    fun unackedBy(consumer: String): Int = inFlight.values.count { it.consumer == consumer }

    /** The messages this queue threw away because there was no [deadLetters] queue to send them to. */
    val dropped: List<Message> get() = droppedMessages.toList()

    /** Registers [consumer]. Subscribing again replaces its settings. A [prefetch] below 1 is an error. */
    fun subscribe(consumer: String, prefetch: Int, autoAck: Boolean = false) {
        require(prefetch >= 1) { "prefetch must be at least 1" }
        subscriptions[consumer] = Subscription(prefetch, autoAck)
    }

    /** A producer's message joins the back of the queue. */
    fun publish(message: Message) {
        waiting[nextPosition] = Entry(nextPosition, message, 0)
        nextPosition++
    }

    /**
     * Hands the message at the head of the queue to [consumer], or returns null when nothing is ready or the consumer
     * already holds `prefetch` unacknowledged deliveries. A consumer that has not subscribed is an
     * [IllegalStateException].
     */
    fun deliver(consumer: String): Delivery? {
        val sub = subscriptions[consumer] ?: throw IllegalStateException("$consumer has not subscribed to $name")
        if (!sub.autoAck && unackedBy(consumer) >= sub.prefetch) return null   // at its prefetch: wait for an ack
        val head = waiting.pollFirstEntry()?.value ?: return null               // nothing ready
        val tag = nextTag++
        if (!sub.autoAck) inFlight[tag] = InFlight(head, consumer)             // auto-ack: gone the moment it leaves
        return Delivery(tag, consumer, head.message, redelivered = head.returns > 0, deliveryCount = head.returns)
    }

    /** The consumer is done with delivery [tag]: the message leaves the queue for good. An unknown tag is an error. */
    fun ack(tag: Long) {
        inFlight.remove(tag) ?: throw IllegalStateException("no unacknowledged delivery with tag $tag")
    }

    /**
     * The consumer gives delivery [tag] back. With [requeue] the message returns to its original position (and counts
     * towards the delivery limit); without it the message goes straight to the dead letters. An unknown tag is an error.
     */
    fun reject(tag: Long, requeue: Boolean) {
        val pending = inFlight.remove(tag) ?: throw IllegalStateException("no unacknowledged delivery with tag $tag")
        if (requeue) giveBack(pending.entry) else deadLetter(pending.entry.message)
    }

    /**
     * [consumer]'s connection closed: it crashed, or it shut down without acknowledging everything. Every delivery it
     * had not acknowledged goes back, oldest first, and the consumer is no longer subscribed.
     */
    fun disconnect(consumer: String) {
        val tags = inFlight.filterValues { it.consumer == consumer }.keys.toList()   // copy: we remove while we walk
        for (tag in tags) giveBack(inFlight.remove(tag)!!.entry)
        subscriptions.remove(consumer)
    }

    /** One more return: back to the original position, or to the dead letters once over the limit. */
    private fun giveBack(entry: Entry) {
        val returns = entry.returns + 1
        if (returns > deliveryLimit) {
            deadLetter(entry.message)
        } else {
            waiting[entry.position] = Entry(entry.position, entry.message, returns)   // same position: the head again
        }
    }

    private fun deadLetter(message: Message) {
        val dlq = deadLetters
        if (dlq != null) dlq.publish(message) else droppedMessages += message
    }
}
