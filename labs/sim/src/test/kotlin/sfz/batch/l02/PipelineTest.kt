package sfz.batch.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

class PipelineTest {
    private val line =
        "10.0.17.4 - - [07/Nov/2026:00:00:00 +0000] \"POST /v1/authorizations HTTP/1.1\" 201 512 \"-\" \"acquirer-sdk/4.2\""

    @Test
    fun `field picks the n-th blank-separated field, like awk's dollar n`() {
        assertThat(field(line, 1)).isEqualTo("10.0.17.4")
        assertThat(field(line, 7)).isEqualTo("/v1/authorizations")
        assertThat(field(line, 9)).isEqualTo("201")
        assertThat(field("  card\t\tmerchant   amount", 2)).isEqualTo("merchant")   // runs of blanks are one separator
        assertThat(field("one two", 3)).isNull()
        assertThrows<IllegalArgumentException> { field(line, 0) }
    }

    @Test
    fun `uniq -c counts only neighbours, so unsorted input splits a key`() {
        val unsorted = sequenceOf("/v1/captures", "/v1/captures", "/healthz", "/v1/captures")
        assertThat(countAdjacent(unsorted)).containsExactly(
            KeyCount("/v1/captures", 2), KeyCount("/healthz", 1), KeyCount("/v1/captures", 1),
        )
        assertThat(countAdjacent(unsorted.sorted())).containsExactly(
            KeyCount("/healthz", 1), KeyCount("/v1/captures", 3),
        )
        assertThat(countAdjacent(emptySequence())).isEmpty()
    }

    @Test
    fun `the whole pipeline finds the busiest paths of a generated log`() {
        val paths = AccessLog.lines(100_000, distinctPaths = 10_000).map { field(it, 7)!! }.toList()
        // awk '{print $7}' | sort | uniq -c | sort -rn | head -5
        val top = topN(countAdjacent(paths.sorted().asSequence()), 5)
        val expected = paths.groupingBy { it }.eachCount()
            .map { KeyCount(it.key, it.value.toLong()) }
            .sortedWith(compareByDescending<KeyCount> { it.count }.thenBy { it.key })
            .take(5)
        assertThat(top).isEqualTo(expected)
        assertThat(top.first().key).isEqualTo("/v1/authorizations")
        assertThat(top.map { it.key }).containsExactlyElementsOf(AccessLog.endpoints.take(5))
    }
}
