package sfz.enc.l01.demo

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.InvalidClassException
import java.io.ObjectInputFilter
import java.io.ObjectInputStream
import java.io.ObjectOutputStream
import java.io.Serializable

/** A harmless class with a readObject method, standing in for a gadget on the classpath. */
class AuditHook(val note: String) : Serializable {
    private fun readObject(input: ObjectInputStream) {
        input.defaultReadObject()
        println("  AuditHook.readObject ran, note = '$note'")
    }
}

fun serialize(o: Any): ByteArray =
    ByteArrayOutputStream().also { out -> ObjectOutputStream(out).use { it.writeObject(o) } }.toByteArray()

/** Shows that Java deserialization runs code chosen by the bytes, and that a JEP 290 filter stops it. */
fun main() {
    val auth = Authorization(1849204436731904017, "Fern Bakery", 4000, "EUR", listOf("card", "3ds"))
    val bytes = serialize(auth)
    println("1. An Authorization takes ${bytes.size} bytes. The first four: " +
        bytes.take(4).joinToString(" ") { "%02x".format(it) })
    val text = String(bytes, Charsets.ISO_8859_1)
    println("   The bytes name the class: ${text.contains("sfz.enc.l01.demo.Authorization")}")

    // bytes from "a client": they name AuditHook, not Authorization
    val hostile = serialize(AuditHook("chosen by whoever wrote the bytes"))

    println("2. Decode them expecting an Authorization, with no filter:")
    try {
        val a = ObjectInputStream(ByteArrayInputStream(hostile)).use { it.readObject() } as Authorization
        println("  got $a")
    } catch (e: ClassCastException) {
        println("  ClassCastException, but only after readObject had run")
    }

    println("3. The same bytes with a JEP 290 allow-list filter:")
    val filter = ObjectInputFilter.Config.createFilter(
        "maxdepth=5;sfz.enc.l01.demo.Authorization;java.util.Arrays\$ArrayList;java.lang.String;!*"
    )
    try {
        ObjectInputStream(ByteArrayInputStream(hostile)).use {
            it.setObjectInputFilter(filter)
            it.readObject() as Authorization
        }
    } catch (e: InvalidClassException) {
        println("  ${e.javaClass.simpleName}: ${e.message}")
    } catch (e: ClassCastException) {
        println("  the filter let AuditHook through: ClassCastException after readObject ran")
    }
    val ok = ObjectInputStream(ByteArrayInputStream(bytes)).use {
        it.setObjectInputFilter(filter)
        it.readObject() as Authorization
    }
    println("   A real Authorization still passes: ${ok == auth}")
}
