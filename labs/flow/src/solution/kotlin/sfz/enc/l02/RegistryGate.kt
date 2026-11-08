package sfz.enc.l02

import org.apache.avro.Schema
import org.apache.avro.SchemaCompatibility
import org.apache.avro.SchemaCompatibility.SchemaCompatibilityType

enum class Mode { NONE, BACKWARD, BACKWARD_TRANSITIVE, FORWARD, FORWARD_TRANSITIVE, FULL, FULL_TRANSITIVE }

object RegistryGate {
    fun canRead(reader: Schema, writer: Schema): Boolean =
        SchemaCompatibility.checkReaderWriterCompatibility(reader, writer).type == SchemaCompatibilityType.COMPATIBLE

    fun isCompatible(candidate: Schema, registered: List<Schema>, mode: Mode): Boolean {
        if (mode == Mode.NONE || registered.isEmpty()) return true
        // non-transitive modes look only at the latest version; that's the trap the tests show
        val against = if (mode.name.endsWith("_TRANSITIVE")) registered else listOf(registered.last())
        return against.all { old ->
            when (mode) {
                Mode.BACKWARD, Mode.BACKWARD_TRANSITIVE -> canRead(candidate, old) // new readers, old data
                Mode.FORWARD, Mode.FORWARD_TRANSITIVE -> canRead(old, candidate)   // old readers, new data
                Mode.FULL, Mode.FULL_TRANSITIVE -> canRead(candidate, old) && canRead(old, candidate)
                Mode.NONE -> true
            }
        }
    }
}
