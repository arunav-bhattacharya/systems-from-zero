package sfz.nosql.l08

import com.mongodb.client.FindIterable
import com.mongodb.client.MongoCollection
import com.mongodb.client.MongoDatabase
import com.mongodb.client.model.Accumulators
import com.mongodb.client.model.Aggregates
import com.mongodb.client.model.CreateCollectionOptions
import com.mongodb.client.model.Filters
import com.mongodb.client.model.IndexOptions
import com.mongodb.client.model.Indexes
import com.mongodb.client.model.Sorts
import com.mongodb.client.model.Updates
import com.mongodb.client.model.ValidationOptions
import org.bson.Document
import org.bson.conversions.Bson
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneOffset
import java.util.Date

/** One refund of a payment. A payment has a handful at most, so they live inside it. */
data class Refund(val refundId: String, val amountMinor: Long, val at: Instant)

/** A card payment, the way the payments service sees it. */
data class Payment(
    val paymentId: String,
    val accountId: String,
    val merchantId: String,
    val status: String,
    val amountMinor: Long,
    val currency: String,
    val createdAt: Instant,
    val refunds: List<Refund> = emptyList(),
)

/** One line of a merchant's daily report: how many payments had this status, and their totals. */
data class StatusTotal(val status: String, val count: Int, val amountMinor: Long, val refundedMinor: Long)

/**
 * Payments as MongoDB documents: one document per payment, its refunds embedded in it.
 *
 * Your job: [toDocument], [addRefund], [createIndexes], [recentByMerchantStatus] and
 * [dailyTotalsPipeline]. Everything else is given.
 */
object PaymentDocs {
    /** The name of the compound index for AP3 (a merchant's payments with one status, newest first). */
    const val AP3_INDEX = "merchant_status_created"

    /** The name of the index on the refund ids inside the refunds array. */
    const val REFUND_INDEX = "refund_id"

    /**
     * The `payments` collection's validator: the shape every payment document must have. Given.
     * `long` and `date` are BSON types: a 64-bit integer and a UTC datetime in milliseconds.
     * `maxItems` keeps the embedded array bounded, which is what made embedding safe.
     */
    val schema: Document = Document.parse(
        """
        { "${'$'}jsonSchema": {
            "bsonType": "object",
            "required": ["_id", "accountId", "merchantId", "status", "amountMinor", "currency", "createdAt", "refundedMinor", "refunds"],
            "properties": {
              "_id":           { "bsonType": "string", "pattern": "^pay-" },
              "status":        { "enum": ["AUTHORIZED", "SETTLED", "FAILED"] },
              "amountMinor":   { "bsonType": "long", "minimum": 1 },
              "currency":      { "bsonType": "string", "minLength": 3, "maxLength": 3 },
              "createdAt":     { "bsonType": "date" },
              "refundedMinor": { "bsonType": "long", "minimum": 0 },
              "refunds": {
                "bsonType": "array", "maxItems": 20,
                "items": {
                  "bsonType": "object", "required": ["refundId", "amountMinor", "at"],
                  "properties": {
                    "refundId":    { "bsonType": "string" },
                    "amountMinor": { "bsonType": "long", "minimum": 1 },
                    "at":          { "bsonType": "date" }
                  }
                }
              }
            }
        } }
        """.trimIndent()
    )

    /** Creates the `payments` collection in [db] with [schema] as its validator, and returns it. Given. */
    fun createCollection(db: MongoDatabase): MongoCollection<Document> {
        db.createCollection("payments", CreateCollectionOptions().validationOptions(ValidationOptions().validator(schema)))
        return db.getCollection("payments")
    }

    /**
     * One payment as one document, in the shape [schema] describes:
     *
     * - `_id` is the payment id, then `accountId`, `merchantId`, `status`, `amountMinor`, `currency`;
     * - `createdAt` as a BSON date (`java.util.Date`), not a string;
     * - `refunds`: an array with one sub-document per refund (`refundId`, `amountMinor`, `at` as a date);
     * - `refundedMinor`: the sum of the refunds, so a query never has to add them up.
     *
     * Kotlin `Long` values become BSON `long` (int64); an `Int` would become int32 and fail the schema.
     */
    fun toDocument(p: Payment): Document {
        return Document("_id", p.paymentId)
            .append("accountId", p.accountId)
            .append("merchantId", p.merchantId)
            .append("status", p.status)
            .append("amountMinor", p.amountMinor) // Long -> BSON int64
            .append("currency", p.currency)
            .append("createdAt", Date.from(p.createdAt)) // BSON date: UTC milliseconds
            .append("refundedMinor", p.refunds.sumOf { it.amountMinor })
            // embedded: read with the payment, written with the payment, never more than a few
            .append("refunds", p.refunds.map(::refundDocument))
    }

    /** One refund as an embedded sub-document. Given. */
    fun refundDocument(r: Refund): Document =
        Document("refundId", r.refundId).append("amountMinor", r.amountMinor).append("at", Date.from(r.at))

    /**
     * Adds [refund] to payment [paymentId] with ONE `updateOne`, and returns whether it was applied.
     *
     * The filter matches only when the payment exists, is `SETTLED`, and
     * `refundedMinor + refund.amountMinor <= amountMinor` (use `Filters.expr`, which compares two
     * fields of the same document). The update pushes the refund onto `refunds` and increments
     * `refundedMinor`. MongoDB checks the filter and applies the update to one document atomically,
     * so two refunds racing for the last 1,000 can't both win.
     */
    fun addRefund(payments: MongoCollection<Document>, paymentId: String, refund: Refund): Boolean {
        val fitsInAmount = Filters.expr(
            Document("\$lte", listOf(Document("\$add", listOf("\$refundedMinor", refund.amountMinor)), "\$amountMinor"))
        )
        val result = payments.updateOne(
            Filters.and(Filters.eq("_id", paymentId), Filters.eq("status", "SETTLED"), fitsInAmount),
            Updates.combine(
                Updates.push("refunds", refundDocument(refund)),
                Updates.inc("refundedMinor", refund.amountMinor),
            ),
        )
        return result.modifiedCount == 1L
    }

    /**
     * Creates two indexes:
     *
     * - [AP3_INDEX]: `{ merchantId: 1, status: 1, createdAt: -1 }`, equality fields first, then the
     *   sort (lesson 2's ESR rule);
     * - [REFUND_INDEX]: `{ "refunds.refundId": 1 }`. The field is inside an array, so MongoDB makes it
     *   a multikey index: one index entry per refund, each pointing at its payment.
     */
    fun createIndexes(payments: MongoCollection<Document>) {
        payments.createIndex(
            Indexes.compoundIndex(Indexes.ascending("merchantId", "status"), Indexes.descending("createdAt")),
            IndexOptions().name(AP3_INDEX),
        )
        payments.createIndex(Indexes.ascending("refunds.refundId"), IndexOptions().name(REFUND_INDEX))
    }

    /**
     * AP3: [merchantId]'s payments with [status], newest first, at most [limit]. Return the
     * `FindIterable` without running it: the tests call `explain()` on it to see what it reads.
     */
    fun recentByMerchantStatus(payments: MongoCollection<Document>, merchantId: String, status: String, limit: Int): FindIterable<Document> {
        // equality on the first two index fields, then the order of the third: one walk of the index
        return payments.find(Filters.and(Filters.eq("merchantId", merchantId), Filters.eq("status", status)))
            .sort(Sorts.descending("createdAt"))
            .limit(limit)
    }

    /**
     * The aggregation for [dailyTotals]: [merchantId]'s payments created on [day] (UTC), grouped by
     * status, sorted by status.
     *
     * 1. `$match` on `merchantId` and `createdAt >= day 00:00 UTC` and `< the next day 00:00 UTC`.
     *    Put it first, so MongoDB can use an index for it.
     * 2. `$group` with `_id: "$status"`, `count` (sum of 1), `amountMinor` and `refundedMinor` (sums).
     * 3. `$sort` by `_id`.
     */
    fun dailyTotalsPipeline(merchantId: String, day: LocalDate): List<Bson> {
        val from = Date.from(day.atStartOfDay(ZoneOffset.UTC).toInstant())
        val until = Date.from(day.plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant())
        return listOf(
            // WHERE merchant_id = ? AND created_at >= ? AND created_at < ?
            Aggregates.match(Filters.and(Filters.eq("merchantId", merchantId), Filters.gte("createdAt", from), Filters.lt("createdAt", until))),
            // GROUP BY status, with COUNT(*) and two SUMs
            Aggregates.group(
                "\$status",
                Accumulators.sum("count", 1),
                Accumulators.sum("amountMinor", "\$amountMinor"),
                Accumulators.sum("refundedMinor", "\$refundedMinor"),
            ),
            // ORDER BY status
            Aggregates.sort(Sorts.ascending("_id")),
        )
    }

    /** Runs [dailyTotalsPipeline] and turns each result document into a [StatusTotal]. Given. */
    fun dailyTotals(payments: MongoCollection<Document>, merchantId: String, day: LocalDate): List<StatusTotal> =
        payments.aggregate(dailyTotalsPipeline(merchantId, day)).map { d ->
            StatusTotal(
                status = d.getString("_id"),
                count = (d["count"] as Number).toInt(),
                amountMinor = (d["amountMinor"] as Number).toLong(),
                refundedMinor = (d["refundedMinor"] as Number).toLong(),
            )
        }.toList()
}
