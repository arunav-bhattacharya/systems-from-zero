package sfz.found.l04

import kotlin.math.floor

// Reference answers for Delivery.kt.

data class QueuedPost(val atSecond: Double, val writes: Long)

fun deliverySeconds(posts: List<QueuedPost>, writesPerSecond: Double): List<Double> {
    var queueFreeAt = 0.0                                   // when the workers finish the post ahead
    return posts.map { p ->
        val start = maxOf(p.atSecond, queueFreeAt)          // wait behind whatever is ahead in the queue
        val finish = start + p.writes / writesPerSecond
        queueFreeAt = finish
        finish - p.atSecond                                 // waiting time plus its own fan-out time
    }
}

fun celebrityThreshold(writesPerSecond: Double, deadlineSeconds: Double): Long =
    floor(writesPerSecond * deadlineSeconds).toLong()
