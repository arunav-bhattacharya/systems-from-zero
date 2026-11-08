package sfz.enc.l03.demo

import com.fasterxml.jackson.databind.DeserializationFeature
import com.fasterxml.jackson.databind.node.ObjectNode
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import kotlin.math.pow
import kotlin.random.Random

/** What version 1 knows about a customer. Version 2 adds preferredLanguage. */
data class CustomerV1(val id: Int, val name: String, val status: String)

// like Quarkus and Spring Boot: unknown properties are ignored, not rejected
val mapper = jacksonObjectMapper().disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)

/** v1 the usual way: decode into the data class, change it, encode it. */
fun dataClassTouch(stored: String, status: String): String =
    mapper.writeValueAsString(mapper.readValue<CustomerV1>(stored).copy(status = status))

/** v1 the careful way: change one property of the tree, keep the rest. */
fun treeTouch(stored: String, status: String): String =
    mapper.writeValueAsString((mapper.readTree(stored) as ObjectNode).put("status", status))

/** v2: knows everything. */
fun v2Touch(stored: String, status: String): String = treeTouch(stored, status)

/**
 * 1,000 customers each set a language on v2, then get 5 status updates that land on random instances.
 * Returns the share of languages gone at the end.
 */
fun lossRate(v2Percent: Int, v1: (String, String) -> String): Double {
    val rnd = Random(7)
    val store = (0 until 1000).associateWith { id ->
        """{"id":$id,"name":"customer-$id","status":"new","preferredLanguage":"de"}"""
    }.toMutableMap()
    repeat(5) {
        for (id in store.keys) {
            val doc = store.getValue(id)
            store[id] = if (rnd.nextInt(100) < v2Percent) v2Touch(doc, "active") else v1(doc, "active")
        }
    }
    return store.values.count { mapper.readTree(it).get("preferredLanguage") == null } / 1000.0
}

fun main() {
    println("v2 share   lost, data class   lost, tree   1 - p^5")
    for (p in listOf(10, 50, 90, 99, 100)) {
        println("%7d%%   %16.1f%%   %10.1f%%   %6.1f%%".format(
            p, 100 * lossRate(p, ::dataClassTouch), 100 * lossRate(p, ::treeTouch), 100 * (1 - (p / 100.0).pow(5))))
    }
}
