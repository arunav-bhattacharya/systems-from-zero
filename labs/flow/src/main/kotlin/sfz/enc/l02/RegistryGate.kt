package sfz.enc.l02

import org.apache.avro.Schema

/** The compatibility modes of a schema registry, with Confluent's names. */
enum class Mode { NONE, BACKWARD, BACKWARD_TRANSITIVE, FORWARD, FORWARD_TRANSITIVE, FULL, FULL_TRANSITIVE }

/**
 * The check a schema registry runs before it accepts a new version of a schema, built on Avro's own
 * reader/writer resolution rules.
 */
object RegistryGate {
    /**
     * True when code that uses [reader] can decode data written with [writer].
     * Use `SchemaCompatibility.checkReaderWriterCompatibility(reader, writer).type`.
     */
    fun canRead(reader: Schema, writer: Schema): Boolean {
        TODO("ask Avro's SchemaCompatibility and compare the type with COMPATIBLE")
    }

    /**
     * Should the registry accept [candidate] as the next version, given the versions already
     * [registered] (oldest first) and the subject's [mode]?
     *
     * - BACKWARD: a reader on the candidate reads data written with the latest registered version.
     * - FORWARD: a reader on the latest registered version reads data written with the candidate.
     * - FULL: both.
     * - The _TRANSITIVE modes check against every registered version, not just the latest.
     * - NONE, or nothing registered yet: accept.
     */
    fun isCompatible(candidate: Schema, registered: List<Schema>, mode: Mode): Boolean {
        TODO("pick the versions to check against, then the direction(s) for the mode")
    }
}
