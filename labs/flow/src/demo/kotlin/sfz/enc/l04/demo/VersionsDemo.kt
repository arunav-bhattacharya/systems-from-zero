package sfz.enc.l04.demo

import com.fasterxml.jackson.databind.node.ObjectNode
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper

/**
 * Stripe-style dated API versions. The server builds every response at the newest version, then walks back
 * through the breaking changes newer than the caller's pinned version, undoing each one.
 */

private val json = jacksonObjectMapper()

/** One breaking change: the version it shipped in, and how to turn a newer response into the older shape. */
class VersionChange(val version: String, val what: String, val undo: (ObjectNode) -> Unit)

// newest first. Adding a field is not breaking, so it needs no entry here.
private val changes = listOf(
    VersionChange("2026-04-01", "amount became an object with value and currency") { r ->
        val amount = r.remove("amount") as ObjectNode
        r.put("amount", amount.get("value").asLong())
        r.put("currency", amount.get("currency").asText())
    },
    VersionChange("2025-10-01", "status 'authorized' was renamed 'requires_capture'") { r ->
        if (r.get("status").asText() == "requires_capture") r.put("status", "authorized")
    },
)

/** Renders [latest] for a caller pinned to [pinned]: undo every change newer than the pin, newest first. */
fun render(latest: ObjectNode, pinned: String): ObjectNode {
    val r = latest.deepCopy()
    changes.filter { it.version > pinned }.forEach { it.undo(r) } // ISO dates compare correctly as strings
    return r
}

fun main() {
    val latest = json.readTree(
        """{"id":"ch_77","status":"requires_capture","amount":{"value":4000,"currency":"eur"},"risk_score":12}""",
    ) as ObjectNode
    println("built once, at the newest version:")
    println("  " + json.writeValueAsString(latest))
    for ((account, pin) in listOf("acct_old" to "2025-06-15", "acct_mid" to "2025-11-20", "acct_new" to "2026-05-01")) {
        println("$account, pinned to $pin:")
        println("  " + json.writeValueAsString(render(latest, pin)))
    }
}
