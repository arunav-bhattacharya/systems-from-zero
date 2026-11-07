package sfz.kafka.l11

/** The field types of the model. Avro has more (bytes, arrays, maps, unions, nested records); these are enough. */
enum class FieldType { INT, LONG, FLOAT, DOUBLE, STRING, BOOLEAN }

/** One field of a record schema. [hasDefault] means the schema gives it a default value. */
data class Field(val name: String, val type: FieldType, val hasDefault: Boolean = false)

/** An Avro record schema, cut down to a name and a list of fields. */
data class RecordSchema(val name: String, val fields: List<Field>)

/** The compatibility modes of Schema Registry. BACKWARD is the registry's default. */
enum class Mode { NONE, BACKWARD, BACKWARD_TRANSITIVE, FORWARD, FORWARD_TRANSITIVE, FULL, FULL_TRANSITIVE }

/**
 * What a schema registry checks before it accepts a new version of a schema, built on Avro's rule for reading data
 * written with one schema (the writer's) using another (the reader's).
 */
object CompatibilityChecker {
    /**
     * Avro's type promotions: a reader may read a writer's INT as LONG, FLOAT or DOUBLE, a LONG as FLOAT or DOUBLE,
     * and a FLOAT as DOUBLE. Every type can of course be read as itself.
     */
    @JvmStatic
    fun canPromote(writer: FieldType, reader: FieldType): Boolean = writer == reader || when (writer) {
        FieldType.INT -> reader in setOf(FieldType.LONG, FieldType.FLOAT, FieldType.DOUBLE)
        FieldType.LONG -> reader in setOf(FieldType.FLOAT, FieldType.DOUBLE)
        FieldType.FLOAT -> reader == FieldType.DOUBLE
        else -> false
    }

    /**
     * The problems a consumer using [reader] meets when it reads a record written with [writer]; empty if there are
     * none. One string per problem, in this order:
     *
     * - `"NAME_MISMATCH: writer <writer name>, reader <reader name>"` if the record names differ (and nothing else);
     * - then, for each reader field in the reader's order:
     *   - the writer has a field of that name whose type can't be promoted to the reader's:
     *     `"TYPE_MISMATCH: <field> (writer <TYPE>, reader <TYPE>)"`;
     *   - the writer has no field of that name and the reader's field has no default:
     *     `"READER_FIELD_MISSING_DEFAULT_VALUE: <field>"`.
     *
     * A writer field the reader doesn't know is no problem: the reader skips it.
     */
    @JvmStatic
    fun readProblems(reader: RecordSchema, writer: RecordSchema): List<String> {
        if (reader.name != writer.name) return listOf("NAME_MISMATCH: writer ${writer.name}, reader ${reader.name}")
        val written = writer.fields.associateBy { it.name }
        return reader.fields.mapNotNull { field ->
            val w = written[field.name]
            when {
                // the writer wrote this field: the reader must be able to read its type
                w != null && !canPromote(w.type, field.type) -> "TYPE_MISMATCH: ${field.name} (writer ${w.type}, reader ${field.type})"
                // the writer never wrote it: only a default can fill it in
                w == null && !field.hasDefault -> "READER_FIELD_MISSING_DEFAULT_VALUE: ${field.name}"
                else -> null
            }
        }
    }

    /**
     * What the registry says about registering [candidate] in a subject that already holds [registered] (oldest
     * first) under [mode]: the problems, each once, in the order found; empty means it is accepted.
     *
     * - The first version of a subject is always accepted, and NONE accepts everything.
     * - BACKWARD: consumers on the candidate can read data written with the latest version (candidate reads latest).
     * - FORWARD: consumers on the latest version can read data written with the candidate (latest reads candidate).
     * - FULL: both, backward problems first.
     * - The _TRANSITIVE modes check the same against every registered version, oldest first, not just the latest.
     */
    @JvmStatic
    fun check(mode: Mode, candidate: RecordSchema, registered: List<RecordSchema>): List<String> {
        if (registered.isEmpty() || mode == Mode.NONE) return emptyList()
        val against = when (mode) {
            Mode.BACKWARD_TRANSITIVE, Mode.FORWARD_TRANSITIVE, Mode.FULL_TRANSITIVE -> registered
            else -> listOf(registered.last())
        }
        val backward = mode in setOf(Mode.BACKWARD, Mode.BACKWARD_TRANSITIVE, Mode.FULL, Mode.FULL_TRANSITIVE)
        val forward = mode in setOf(Mode.FORWARD, Mode.FORWARD_TRANSITIVE, Mode.FULL, Mode.FULL_TRANSITIVE)
        val problems = mutableListOf<String>()
        for (old in against) {
            if (backward) problems += readProblems(reader = candidate, writer = old) // new consumers, old data
            if (forward) problems += readProblems(reader = old, writer = candidate)  // old consumers, new data
        }
        return problems.distinct()
    }
}
