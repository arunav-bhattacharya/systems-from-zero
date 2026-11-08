package sfz.model.l08

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.neo4j.driver.Record
import sfz.nosql.support.TestNeo4j

/**
 * Runs YOUR Cypher files from src/main/resources/sfz/model/l08/ against a real Neo4j, on the fraud
 * graph from the lesson (labs/env/neo4j/nosql-11-fraud.cypher), reloaded before every test.
 */
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class FraudGraphTest {
    private fun query(name: String): String = TestNeo4j.statements(TestNeo4j.resource("/sfz/model/l08/$name.cypher")).single()

    private fun run(name: String, params: Map<String, Any?> = emptyMap()): List<Record> = TestNeo4j.run(query(name), params)

    @BeforeAll
    fun start() {
        TestNeo4j.driver // starts the container: up to a minute or two the first time
    }

    @BeforeEach
    fun seed() = TestNeo4j.reset("/sfz/model/l08/fraud-graph.cypher")

    @Test
    fun `the seed graph is what the lesson describes`() {
        val counts = TestNeo4j.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label")
            .associate { it["label"].asString() to it["n"].asInt() }
        assertThat(counts).containsExactlyEntriesOf(linkedMapOf("Account" to 13, "Device" to 9, "Phone" to 6))
    }

    @Test
    fun `schema makes Account id unique, so a second A-3101 is refused`() {
        run("schema")
        val constraints = TestNeo4j.run("SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties")
        assertThat(constraints.map { it["name"].asString() }).containsExactly("account_id")
        assertThat(constraints.single()["type"].asString()).isEqualTo("NODE_PROPERTY_UNIQUENESS")
        assertThat(constraints.single()["properties"].asList()).containsExactly("id")
        assertThatThrownBy { TestNeo4j.run("CREATE (:Account {id: 'A-3101'})") }
            .hasMessageContaining("already exists")
    }

    @Test
    fun `suspicious pairs share at least two identifiers, each pair once, identifiers sorted`() {
        val rows = run("suspicious-pairs", mapOf("minShared" to 2))
        assertThat(rows.map { listOf(it["first"].asString(), it["second"].asString(), it["shared"].asList()) })
            .containsExactly(
                listOf("A-3101", "A-3102", listOf("D-77", "P-0177")),
                listOf("A-3103", "A-3104", listOf("D-81", "P-0181")),
            )
    }

    @Test
    fun `with minShared 1 the store kiosk pairs up customers who have nothing in common`() {
        val rows = run("suspicious-pairs", mapOf("minShared" to 1))
        assertThat(rows).hasSize(16)
        assertThat(rows.map { it["first"].asString() to it["second"].asString() }).contains("A-1001" to "A-2002", "A-3102" to "A-3103")
        assertThat(rows.map { it["first"].asString() }).isSorted()
        assertThat(rows).allSatisfy { assertThat(it["first"].asString()).isLessThan(it["second"].asString()) }
    }

    @Test
    fun `the ring around A-3101 is four accounts within three steps when the kiosk is skipped`() {
        val rows = run("ring", mapOf("accountId" to "A-3101", "skipKinds" to listOf("store kiosk")))
        assertThat(rows.map { it["account"].asString() to it["steps"].asInt() })
            .containsExactly("A-3102" to 1, "A-3103" to 2, "A-3104" to 3, "A-3105" to 3)
    }

    @Test
    fun `walking through the kiosk pulls four innocent customers into the ring at step three`() {
        val rows = run("ring", mapOf("accountId" to "A-3101", "skipKinds" to emptyList<String>()))
        assertThat(rows.map { it["account"].asString() to it["steps"].asInt() }).containsExactly(
            "A-3102" to 1, "A-3103" to 2,
            "A-1001" to 3, "A-2002" to 3, "A-3104" to 3, "A-3105" to 3, "A-4002" to 3, "A-4003" to 3,
        )
        // the start is never in its own ring, and nothing is further than three steps
        assertThat(rows.map { it["account"].asString() }).doesNotContain("A-3101", "A-4004")
    }

    @Test
    fun `with the constraint in place the ring query starts from an index seek, not a label scan`() {
        run("schema")
        val ops = TestNeo4j.operators(query("ring"), mapOf("accountId" to "A-3101", "skipKinds" to listOf("store kiosk")))
        assertThat(ops).anyMatch { it.startsWith("NodeUniqueIndexSeek") }
        assertThat(ops).noneMatch { it.startsWith("NodeByLabelScan") || it.startsWith("AllNodesScan") }
    }

    @Test
    fun `money cycles of three to six transfers are found once each, starting at the smallest id`() {
        val rows = run("money-cycles")
        assertThat(rows.map { it["cycle"].asList() to it["movedMinor"].asLong() }).containsExactly(
            listOf("A-3101", "A-3103", "A-3104", "A-3101") to 282_000L,
            listOf("A-3102", "A-3105", "A-4004", "A-3103", "A-3102") to 192_500L,
        )
    }

    @Test
    fun `two friends paying each other back is not a cycle, and neither is a seven-transfer loop`() {
        TestNeo4j.run(
            """
            UNWIND range(1, 7) AS i
            MERGE (a:Account {id: 'B-' + i})
            WITH collect(a) AS ring
            UNWIND range(0, 6) AS i
            WITH ring[i] AS a, ring[(i + 1) % 7] AS b
            CREATE (a)-[:TRANSFERRED_TO {amountMinor: 100}]->(b)
            """.trimIndent(),
        )
        val cycles = run("money-cycles").map { it["cycle"].asList() }
        assertThat(cycles).hasSize(2) // only the two from the seed: A-1001 <-> A-2002 is length 2, B-1..B-7 is length 7
        assertThat(cycles.flatten()).doesNotContain("A-1001", "B-1")
    }
}
