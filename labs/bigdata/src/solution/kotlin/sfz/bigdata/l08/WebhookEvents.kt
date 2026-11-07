package sfz.bigdata.l08

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.coalesce
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.try_parse_json
import org.apache.spark.sql.functions.try_variant_get
import org.apache.spark.sql.functions.variant_get

/**
 * Webhook events from a fraud-scoring vendor, one JSON document per event. The vendor changes the
 * shape now and then: newer events send `amount` as an object, some send the risk score as text,
 * and capture events have no `risk` at all.
 */
object WebhookEvents {

    /**
     * Parses each `body` (STRING) once, into a column `event` of type VARIANT, next to `event_id`.
     * A body that isn't valid JSON gives a null `event`; the row stays. Columns: `event_id`, `event`.
     */
    fun parse(raw: Dataset<Row>): Dataset<Row> =
        // parse once: field names go into the variant's dictionary, values into a typed binary tree.
        // parse_json would fail the job on the broken body; try_parse_json gives null instead
        raw.select(col("event_id"), try_parse_json(col("body")).alias("event"))

    /**
     * For every card country (`$.card.country`), how many events have a risk score
     * (`$.risk.score`) above 0.8. The score may be a JSON number or a JSON string such as "0.85".
     * Events without a score don't count. Columns: `country` (STRING), `high_risk` (BIGINT).
     */
    fun highRiskByCountry(events: Dataset<Row>): Dataset<Row> =
        // try_variant_get casts "0.85" to 0.85 and gives null where there's no score, so the filter drops those
        events.where(try_variant_get(col("event"), "$.risk.score", "double").gt(0.8))
            .groupBy(variant_get(col("event"), "$.card.country", "string").alias("country"))
            .count()
            .withColumnRenamed("count", "high_risk")

    /**
     * The amount of every event in minor units, as BIGINT. Older events send a number of minor
     * units, `"amount": 1250`. Newer ones send `"amount": {"value": "12.50", "currency": "EUR"}`,
     * a decimal string in major units. Both must come out as 1250. Columns: `event_id`,
     * `amount_minor` (null if the event has no readable amount).
     */
    fun amountMinor(events: Dataset<Row>): Dataset<Row> =
        events.select(
            col("event_id"),
            coalesce(
                // old shape: a number at $.amount (an object there gives null, not an error)
                try_variant_get(col("event"), "$.amount", "bigint"),
                // new shape: a decimal string in major units at $.amount.value
                try_variant_get(col("event"), "$.amount.value", "decimal(12,2)").multiply(100).cast("bigint"),
            ).alias("amount_minor"),
        )
}
