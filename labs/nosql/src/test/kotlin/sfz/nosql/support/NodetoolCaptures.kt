package sfz.nosql.support

/**
 * Reads `nodetool` output captured from the three-node cluster (env/cassandra-cluster.yml) and kept
 * as test resources, so the lessons on Cassandra's ring (shard-05, shard-06) can check their models
 * against what a real cluster printed. Lines starting with `#` are comments added when capturing.
 */
object NodetoolCaptures {
    /** One line of `nodetool ring`: who owns which token. */
    data class RingLine(val address: String, val rack: String, val status: String, val state: String, val token: Long)

    /** One `TokenRange(...)` of `nodetool describering`: the range (start, end] and its replicas, in order. */
    data class DescribedRange(val start: Long, val end: Long, val endpoints: List<String>)

    /** One "Bootstrap: range ... exists on ..." line from a joining node's system.log. */
    data class StreamSource(val start: Long, val end: Long, val source: String, val keyspace: String)

    /** The text of a test resource, without comment lines. */
    fun text(resource: String): List<String> {
        val stream = NodetoolCaptures::class.java.getResourceAsStream(resource)
            ?: error("missing test resource $resource")
        return stream.bufferedReader().readLines().filterNot { it.startsWith("#") }
    }

    private val ringLine = Regex("""^(\d+\.\d+\.\d+\.\d+)\s+(\S+)\s+(Up|Down)\s+(\S+)\s+.*?\s(-?\d+)\s*$""")

    /** Parses `nodetool ring`. The lone token on the line under the header (the highest token, repeated) is skipped. */
    fun ring(resource: String): List<RingLine> = text(resource).mapNotNull { line ->
        ringLine.find(line)?.destructured?.let { (address, rack, status, state, token) ->
            RingLine(address, rack, status, state, token.toLong())
        }
    }

    /** Parses lines of `== <key>` followed by the addresses `nodetool getendpoints` printed for it. */
    fun endpoints(resource: String): Map<String, List<String>> {
        val result = LinkedHashMap<String, MutableList<String>>()
        var key: String? = null
        for (line in text(resource).map(String::trim).filter(String::isNotEmpty)) {
            if (line.startsWith("== ")) key = line.removePrefix("== ").trim().also { result[it] = mutableListOf() }
            else result.getValue(key ?: error("address before any key: $line")) += line
        }
        return result
    }

    private val describedRange = Regex("""TokenRange\(start_token:(-?\d+), end_token:(-?\d+), endpoints:\[([^\]]*)]""")

    /** Parses `nodetool describering <keyspace>`. */
    fun describering(resource: String): List<DescribedRange> = text(resource).mapNotNull { line ->
        describedRange.find(line)?.destructured?.let { (start, end, eps) ->
            DescribedRange(start.toLong(), end.toLong(), eps.split(",").map(String::trim))
        }
    }

    private val streamSource =
        Regex("""Bootstrap: range Full\(/[\d.]+:\d+,\((-?\d+),(-?\d+)]\) exists on Full\(/([\d.]+):\d+,.*\) for keyspace (\w+)""")

    /** Parses a joining node's "Bootstrap: range (a,b] exists on <source>" lines: where each range was streamed from. */
    fun streamSources(resource: String): List<StreamSource> = text(resource).mapNotNull { line ->
        streamSource.find(line)?.destructured?.let { (start, end, source, keyspace) ->
            StreamSource(start.toLong(), end.toLong(), source, keyspace)
        }
    }
}
