package sfz.enc.l03

import com.fasterxml.jackson.databind.DeserializationFeature
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.databind.node.ObjectNode
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import kotlin.random.Random

data class CustomerV1(val id: Int, val name: String, val status: String)

fun interface V1Codec {
    fun touch(stored: String, newStatus: String): String
}

val mapper: ObjectMapper = jacksonObjectMapper().disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)

val DataClassCodec = V1Codec { stored, newStatus ->
    val c: CustomerV1 = mapper.readValue(stored)
    mapper.writeValueAsString(c.copy(status = newStatus))
}

// change only what this version owns; the tree carries every other property through untouched
val PreservingCodec = V1Codec { stored, newStatus ->
    val tree = mapper.readTree(stored) as ObjectNode
    tree.put("status", newStatus)
    mapper.writeValueAsString(tree)
}

object V2 {
    fun create(id: Int): String = mapper.writeValueAsString(CustomerV1(id, "customer-$id", "new"))

    fun setLanguage(stored: String, language: String): String =
        mapper.writeValueAsString((mapper.readTree(stored) as ObjectNode).put("preferredLanguage", language))

    fun touch(stored: String, newStatus: String): String =
        mapper.writeValueAsString((mapper.readTree(stored) as ObjectNode).put("status", newStatus))

    fun languageOf(stored: String): String? = mapper.readTree(stored).get("preferredLanguage")?.asText()
}

object RollingUpgrade {
    fun lossRate(v2Percent: Int, v1: V1Codec, customers: Int = 1_000, updatesPerCustomer: Int = 5, seed: Long = 7): Double {
        require(v2Percent in 1..100) { "with no v2 instance nobody can set a language" }
        val rnd = Random(seed)
        val store = HashMap<Int, String>()
        for (id in 0 until customers) store[id] = V2.setLanguage(V2.create(id), "de") // new data, written by v2
        repeat(updatesPerCustomer) {
            for (id in 0 until customers) {
                val doc = store.getValue(id)
                // the load balancer doesn't know which version understands the document
                store[id] = if (rnd.nextInt(100) < v2Percent) V2.touch(doc, "active") else v1.touch(doc, "active")
            }
        }
        val lost = store.values.count { V2.languageOf(it) == null }
        return lost.toDouble() / customers
    }
}
