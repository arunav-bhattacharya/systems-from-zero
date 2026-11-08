package sfz.model.l09

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class TripleStoreTest {
    // who owns merchant M-0042, and what else those companies hold: one fact per triple
    private fun ownership() = TripleStore().apply {
        add("M-0042", "name", "Northwind Bikes")
        add("C-7", "owns", "M-0042")
        add("C-2", "owns", "C-7")
        add("C-9", "owns", "C-7")
        add("C-2", "owns", "M-0051")
        add("C-2", "country", "LU")
        add("C-9", "country", "CY")
        add("M-0051", "name", "Volt Electronics")
    }

    @Test
    fun `a triple store is a set, so the same statement is stored once`() {
        val store = ownership()
        assertThat(store.add("C-7", "owns", "M-0042")).isFalse()
        assertThat(store.size()).isEqualTo(8)
    }

    @Test
    fun `a pattern with one variable binds it once per matching triple, in insertion order`() {
        assertThat(ownership().match(Pattern("?owner", "owns", "C-7")))
            .containsExactly(mapOf("?owner" to "C-2"), mapOf("?owner" to "C-9"))
    }

    @Test
    fun `constants must match exactly and a pattern can match nothing`() {
        val store = ownership()
        assertThat(store.match(Pattern("C-7", "owns", "?what"))).containsExactly(mapOf("?what" to "M-0042"))
        assertThat(store.match(Pattern("C-7", "country", "?c"))).isEmpty()
        assertThat(store.match(Pattern("C-2", "owns", "C-7"))).containsExactly(emptyMap())   // a yes/no question
    }

    @Test
    fun `a variable already bound in the given bindings must agree with the triple`() {
        val given = mapOf("?company" to "C-9")
        assertThat(ownership().match(Pattern("?company", "country", "?country"), given))
            .containsExactly(mapOf("?company" to "C-9", "?country" to "CY"))
    }

    @Test
    fun `the same variable twice in one pattern must take the same value`() {
        val store = ownership()
        store.add("C-5", "owns", "C-5")     // a company that holds its own shares
        assertThat(store.match(Pattern("?x", "owns", "?x"))).containsExactly(mapOf("?x" to "C-5"))
    }

    @Test
    fun `a basic graph pattern joins its patterns on the shared variables`() {
        // SPARQL: SELECT ?owner ?country WHERE { ?owner owns ?mid . ?mid owns M-0042 . ?owner country ?country }
        val rows = ownership().query(listOf(
            Pattern("?owner", "owns", "?mid"),
            Pattern("?mid", "owns", "M-0042"),
            Pattern("?owner", "country", "?country"),
        ))
        assertThat(rows.map { it["?owner"] to it["?country"] }).containsExactly("C-2" to "LU", "C-9" to "CY")
        assertThat(rows).allSatisfy { assertThat(it["?mid"]).isEqualTo("C-7") }
    }
}
