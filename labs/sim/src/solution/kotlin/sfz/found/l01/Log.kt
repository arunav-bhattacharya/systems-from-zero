package sfz.found.l01

import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardOpenOption.APPEND
import java.nio.file.StandardOpenOption.CREATE

// This file is finished. Read it, then write the views in Views.kt.

/** What happened to a payment. */
enum class Kind { AUTHORIZED, CAPTURED, REFUNDED }

/**
 * One record in the system of record: a fact that happened, written once and never changed.
 * Amounts are in cents so that every sum is exact. One record is one line of the log file:
 * `pay-000001 m-cafe 2026-03-02 AUTHORIZED 4000`.
 */
data class PaymentEvent(
    val paymentId: String,
    val merchant: String,
    val day: String,
    val kind: Kind,
    val amountCents: Long,
) {
    fun toLine(): String = "$paymentId $merchant $day $kind $amountCents"

    companion object {
        fun parse(line: String): PaymentEvent {
            val p = line.split(' ')
            return PaymentEvent(p[0], p[1], p[2], Kind.valueOf(p[3]), p[4].toLong())
        }
    }
}

/**
 * The system of record: an append-only file with one event per line. Nothing is ever changed or
 * deleted, so reading it from the start always gives the same events in the same order.
 * The offset of an event is its line number, counting from 0.
 *
 * A real database would also call fsync after each append so that the line survives a power cut
 * (the Operating systems track covers that). This lab skips it to stay fast.
 */
class PaymentLog(private val file: Path) {
    private var count: Long = if (Files.exists(file)) Files.newBufferedReader(file).useLines { it.count().toLong() } else 0L

    /** Appends one event at the end of the file and returns its offset. */
    fun append(e: PaymentEvent): Long {
        Files.writeString(file, e.toLine() + "\n", CREATE, APPEND)
        return count++
    }

    /** How many events the log holds. */
    fun size(): Long = count

    /** Reads every event from [from] to the end, in log order, and hands each one to [each]. */
    fun replay(from: Long = 0, each: (offset: Long, e: PaymentEvent) -> Unit) {
        if (!Files.exists(file)) return
        Files.newBufferedReader(file).useLines { lines ->
            lines.forEachIndexed { i, line -> if (i >= from) each(i.toLong(), PaymentEvent.parse(line)) }
        }
    }
}

/**
 * Derived data: anything computed from the log. Because it is computed, it can be thrown away and
 * built again from the log at any time.
 */
interface View {
    /** Folds one more event into the view. Events arrive in log order. */
    fun apply(e: PaymentEvent)

    /** Forgets everything, as if the view had just been created. */
    fun clear()
}

/**
 * The write path: every event goes into the log first, and only then into the derived views.
 * If the process dies between the two steps, the log still has the event, and a rebuild puts it
 * into the views. The other order could leave a view holding a payment the log never recorded.
 */
class PaymentService(private val log: PaymentLog, private val views: List<View>) {
    fun record(e: PaymentEvent): Long {
        val offset = log.append(e)
        for (v in views) v.apply(e)
        return offset
    }
}
