package sfz.enc.l01

import com.fasterxml.jackson.module.kotlin.readValue
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.InvalidClassException
import java.io.ObjectInputStream
import java.io.ObjectOutputStream
import java.io.Serializable
import java.util.concurrent.atomic.AtomicInteger

/**
 * A harmless stand-in for a gadget: a class on the classpath whose readObject runs code.
 * Real exploit chains do the same thing with classes from libraries you already depend on.
 */
class Tripwire(val note: String) : Serializable {
    private fun readObject(input: ObjectInputStream) {
        input.defaultReadObject()
        fired.incrementAndGet() // code chosen by whoever wrote the bytes, running inside your decoder
    }

    companion object {
        private const val serialVersionUID = 1L
        val fired = AtomicInteger()
    }
}

class SafeDeserializerTest {
    private fun serialize(o: Any): ByteArray =
        ByteArrayOutputStream().also { out -> ObjectOutputStream(out).use { it.writeObject(o) } }.toByteArray()

    @BeforeEach
    fun reset() = Tripwire.fired.set(0)

    @Test
    fun `reads a real authorization back`() {
        assertThat(SafeDeserializer.readAuthorization(serialize(Authorization.SAMPLE))).isEqualTo(Authorization.SAMPLE)
    }

    @Test
    fun `reads an authorization whose tags list came from Jackson`() {
        val fromJson = Formats.json.readValue<Authorization>(Formats.json.writeValueAsString(Authorization.SAMPLE))
        assertThat(fromJson.tags).isInstanceOf(java.util.ArrayList::class.java)
        assertThat(SafeDeserializer.readAuthorization(serialize(fromJson))).isEqualTo(Authorization.SAMPLE)
    }

    @Test
    fun `without a filter the bytes run code before the cast fails, with it nothing runs`() {
        val bytes = serialize(Tripwire("hello"))

        // the naive decoder: readObject runs Tripwire's code, and only then does the cast fail
        assertThatThrownBy { ObjectInputStream(ByteArrayInputStream(bytes)).use { it.readObject() as Authorization } }
            .isInstanceOf(ClassCastException::class.java)
        assertThat(Tripwire.fired.get()).isEqualTo(1)

        // yours: the filter rejects the class before an object exists
        assertThatThrownBy { SafeDeserializer.readAuthorization(bytes) }
            .isInstanceOf(InvalidClassException::class.java)
            .hasMessageContaining("REJECTED")
        assertThat(Tripwire.fired.get()).isEqualTo(1)
    }

    @Test
    fun `allowing the whole package would let the tripwire in, so the list names one class`() {
        // Tripwire lives in sfz.enc.l01 too: a pattern like sfz.enc.l01.* would accept it
        assertThatThrownBy { SafeDeserializer.readAuthorization(serialize(Tripwire("same package"))) }
            .isInstanceOf(InvalidClassException::class.java)
        assertThat(Tripwire.fired.get()).isZero()
    }

    @Test
    fun `rejects a graph deeper than 5 objects even when every class is allowed`() {
        var nested: Any = arrayListOf("card")
        repeat(8) { nested = arrayListOf(nested) } // lists inside lists: allowed classes, absurd depth
        @Suppress("UNCHECKED_CAST")
        val deep = Authorization(1, "Fern Bakery", 4000, "EUR", nested as List<String>)
        assertThatThrownBy { SafeDeserializer.readAuthorization(serialize(deep)) }
            .isInstanceOf(InvalidClassException::class.java)
            .hasMessageContaining("REJECTED")
    }
}
