package sfz.enc.l02.demo

import org.apache.avro.Schema
import org.apache.avro.SchemaCompatibility
import org.apache.avro.SchemaCompatibility.SchemaCompatibilityType.COMPATIBLE

fun payment(vararg fields: String): Schema = Schema.Parser().parse(
    """{"type": "record", "name": "Payment", "fields": [${fields.joinToString(",")}]}"""
)

fun canRead(reader: Schema, writer: Schema) =
    SchemaCompatibility.checkReaderWriterCompatibility(reader, writer).type == COMPATIBLE

/** Which schema changes pass which compatibility mode, decided by Avro's own reader/writer rules. */
fun main() {
    val id = """{"name": "paymentId", "type": "long"}"""
    val amount = """{"name": "amount", "type": "int"}"""
    val old = payment(id, amount, """{"name": "channel", "type": "string", "default": "card"}""")
    val changes = listOf(
        "add a field with a default" to payment(id, amount, """{"name": "channel", "type": "string", "default": "card"}""", """{"name": "fee", "type": "int", "default": 0}"""),
        "add a field without a default" to payment(id, amount, """{"name": "channel", "type": "string", "default": "card"}""", """{"name": "fee", "type": "int"}"""),
        "remove a field that had a default" to payment(id, amount),
        "remove a field without a default" to payment(id, """{"name": "channel", "type": "string", "default": "card"}"""),
        "widen amount from int to long" to payment(id, """{"name": "amount", "type": "long"}""", """{"name": "channel", "type": "string", "default": "card"}"""),
        "rename amount, no alias" to payment(id, """{"name": "amountMinor", "type": "int"}""", """{"name": "channel", "type": "string", "default": "card"}"""),
        "rename amount, with an alias" to payment(id, """{"name": "amountMinor", "type": "int", "aliases": ["amount"]}""", """{"name": "channel", "type": "string", "default": "card"}"""),
    )
    println("%-36s %-9s %-9s %s".format("change", "BACKWARD", "FORWARD", "FULL"))
    for ((what, new) in changes) {
        val backward = canRead(new, old) // new readers, old data
        val forward = canRead(old, new)  // old readers, new data
        println("%-36s %-9s %-9s %s".format(what, yes(backward), yes(forward), yes(backward && forward)))
    }

    // the non-transitive trap
    val v1 = payment(id, amount)
    val v2 = payment(id)
    val v3 = payment(id, """{"name": "amount", "type": "string", "default": ""}""")
    println()
    println("v2 reads v1: ${yes(canRead(v2, v1))}   v3 reads v2: ${yes(canRead(v3, v2))}   v3 reads v1: ${yes(canRead(v3, v1))}")
    println(SchemaCompatibility.checkReaderWriterCompatibility(v3, v1).result.incompatibilities.first().message)
}

fun yes(b: Boolean) = if (b) "yes" else "no"
