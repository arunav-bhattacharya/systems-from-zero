package sfz.batch.l09

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row

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
    fun parse(raw: Dataset<Row>): Dataset<Row> {
        TODO("parse the JSON text into a VARIANT column with try_parse_json")
    }

    /**
     * For every card country (`$.card.country`), how many events have a risk score
     * (`$.risk.score`) above 0.8. The score may be a JSON number or a JSON string such as "0.85".
     * Events without a score don't count. Columns: `country` (STRING), `high_risk` (BIGINT).
     */
    fun highRiskByCountry(events: Dataset<Row>): Dataset<Row> {
        TODO("read the nested fields out of the VARIANT with variant_get / try_variant_get")
    }

    /**
     * The amount of every event in minor units, as BIGINT. Older events send a number of minor
     * units, `"amount": 1250`. Newer ones send `"amount": {"value": "12.50", "currency": "EUR"}`,
     * a decimal string in major units. Both must come out as 1250. Columns: `event_id`,
     * `amount_minor` (null if the event has no readable amount).
     */
    fun amountMinor(events: Dataset<Row>): Dataset<Row> {
        TODO("try the old shape, then the new one, and keep the first that works")
    }
}
