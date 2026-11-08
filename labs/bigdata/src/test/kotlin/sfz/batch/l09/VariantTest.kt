package sfz.batch.l09

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.RowFactory
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.types.DataTypes
import org.apache.spark.sql.types.StructType
import org.apache.spark.sql.types.VariantType
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.bigdata.support.LocalSpark

class VariantTest {
    private val spark: SparkSession = LocalSpark.isolated()

    private val raw: Dataset<Row> = spark.createDataFrame(listOf(
        RowFactory.create("e1", """{"type":"authorization","amount":1250,"card":{"country":"NL","bin":"411111"},"risk":{"score":0.93}}"""),
        RowFactory.create("e2", """{"type":"authorization","amount":{"value":"12.50","currency":"EUR"},"card":{"country":"DE"},"risk":{"score":0.12,"rules":["velocity"]}}"""),
        RowFactory.create("e3", """{"type":"capture","amount":990,"card":{"country":"NL"}}"""),
        RowFactory.create("e4", """{"type":"authorization","amount":{"value":"99.90","currency":"EUR"},"card":{"country":"DE"},"risk":{"score":"0.85"}}"""),
        RowFactory.create("e5", """{"type":"authorization","amount":12"""),
        RowFactory.create("e6", """{"type":"authorization","card":{"country":"NL"},"amount":5000,"risk":{"score":0.81}}"""),
    ), StructType().add("event_id", DataTypes.StringType, false).add("body", DataTypes.StringType, false))

    @Test
    fun `parse stores each body as a VARIANT and keeps a broken body as a null event`() {
        val events = WebhookEvents.parse(raw)
        assertThat(events.columns()).containsExactly("event_id", "event")
        assertThat(events.schema().apply("event").dataType()).isInstanceOf(VariantType::class.java)
        val byId = events.collectAsList().associate { it.getString(0) to it.get(1) }
        assertThat(byId).hasSize(6)
        assertThat(byId["e5"]).describedAs("the broken body").isNull()
        assertThat(byId["e1"]).isNotNull()
        // the variant keeps every field: nothing was dropped to fit a fixed schema
        val e2 = events.where("event_id = 'e2'").selectExpr("schema_of_variant(event)").first().getString(0)
        assertThat(e2).contains("rules: ARRAY<STRING>").contains("currency: STRING")
    }

    @Test
    fun `highRiskByCountry reads nested fields, including a score sent as text`() {
        val out = WebhookEvents.highRiskByCountry(WebhookEvents.parse(raw))
        assertThat(out.columns()).containsExactly("country", "high_risk")
        assertThat(out.collectAsList().associate { it.getString(0) to it.getLong(1) }).isEqualTo(mapOf("NL" to 2L, "DE" to 1L))
    }

    @Test
    fun `amountMinor reads both shapes of amount as minor units`() {
        val out = WebhookEvents.amountMinor(WebhookEvents.parse(raw))
        assertThat(out.columns()).containsExactly("event_id", "amount_minor")
        val byId = out.collectAsList().associate { it.getString(0) to it.get(1) }
        assertThat(byId).isEqualTo(mapOf("e1" to 1250L, "e2" to 1250L, "e3" to 990L, "e4" to 9990L, "e5" to null, "e6" to 5000L))
    }
}
