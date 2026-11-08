package sfz.enc.l03

import com.fasterxml.jackson.databind.DeserializationFeature
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.databind.node.ObjectNode
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue

/**
 * A customer document, stored as JSON in one column (think `jsonb`), as version 1 of the service knows it.
 * Version 2 adds `preferredLanguage`, which v1 has never heard of.
 */
data class CustomerV1(val id: Int, val name: String, val status: String)

/** How a v1 instance handles "update this customer's status": read the stored JSON, change status, write it back. */
fun interface V1Codec {
    fun touch(stored: String, newStatus: String): String
}

/** The JSON settings both versions use. Like Quarkus and Spring Boot, it ignores unknown properties instead of failing. */
val mapper: ObjectMapper = jacksonObjectMapper().disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)

/** The usual v1 code: decode into the data class, change it, encode the data class. Fields v1 doesn't know vanish. */
val DataClassCodec = V1Codec { stored, newStatus ->
    val c: CustomerV1 = mapper.readValue(stored)
    mapper.writeValueAsString(c.copy(status = newStatus))
}

/**
 * Your fix: the same update, but every property that was in [stored] is still there afterwards,
 * including ones this version doesn't know. Work on the JSON tree (`mapper.readTree(stored) as ObjectNode`).
 */
val PreservingCodec = V1Codec { stored, newStatus ->
    TODO("read the tree, put the new status, write the tree")
}

/** Version 2 of the service. It knows `preferredLanguage`. Complete: you don't change it. */
object V2 {
    fun create(id: Int): String = mapper.writeValueAsString(CustomerV1(id, "customer-$id", "new"))

    fun setLanguage(stored: String, language: String): String =
        mapper.writeValueAsString((mapper.readTree(stored) as ObjectNode).put("preferredLanguage", language))

    fun touch(stored: String, newStatus: String): String =
        mapper.writeValueAsString((mapper.readTree(stored) as ObjectNode).put("status", newStatus))

    fun languageOf(stored: String): String? = mapper.readTree(stored).get("preferredLanguage")?.asText()
}

object RollingUpgrade {
    /**
     * A rollout in progress: [v2Percent] of the instances run version 2, the rest run version 1 with [v1].
     *
     * 1. Create [customers] documents with `V2.create(id)` (ids 0 until customers).
     * 2. Every customer sets a language once, through the new screen that only v2 serves: `V2.setLanguage(doc, "de")`.
     * 3. Then each customer gets [updatesPerCustomer] status updates (`"active"`), each sent to a random instance:
     *    v2 when `rnd.nextInt(100) < v2Percent`, otherwise v1. Use `Random(seed)` so runs repeat exactly.
     *
     * Returns the share of customers whose language is gone at the end (0.0 to 1.0).
     */
    fun lossRate(v2Percent: Int, v1: V1Codec, customers: Int = 1_000, updatesPerCustomer: Int = 5, seed: Long = 7): Double {
        require(v2Percent in 1..100) { "with no v2 instance nobody can set a language" }
        TODO("build the store, set every language through V2, route the updates, count lost languages")
    }
}
