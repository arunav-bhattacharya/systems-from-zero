package sfz.nosql.support

import org.neo4j.driver.AuthTokens
import org.neo4j.driver.Driver
import org.neo4j.driver.GraphDatabase
import org.neo4j.driver.Record
import org.neo4j.driver.summary.Plan
import org.testcontainers.neo4j.Neo4jContainer
import org.testcontainers.utility.DockerImageName

/**
 * One Neo4j server for the whole test JVM, started the first time a test touches it (lesson 11).
 *
 * Neo4j Community has a single user database, so tests can't each get their own: call [reset]
 * with a seed file before each test instead. JUnit runs test classes one after another, so no
 * two Neo4j tests share the graph at the same time. Testcontainers removes the container when
 * the JVM exits.
 */
object TestNeo4j {
    /** Pinned: the same image as `labs/env/neo4j.yml`. */
    const val IMAGE = "neo4j:2026.10.1"

    private val container: Neo4jContainer by lazy {
        Neo4jContainer(DockerImageName.parse(IMAGE))
            .withoutAuthentication()
            // small heap and page cache, and a memory limit, to keep the shared Docker VM happy
            .withEnv("NEO4J_server_memory_heap_initial__size", "256m")
            .withEnv("NEO4J_server_memory_heap_max__size", "384m")
            .withEnv("NEO4J_server_memory_pagecache_size", "64m")
            .withEnv("NEO4J_dbms_usage__report_enabled", "false")
            .withCreateContainerCmdModifier { cmd -> cmd.hostConfig?.withMemory(1024L * 1024 * 1024) }
            .also { it.start() }
    }

    /** One driver for every test. Never close it. */
    val driver: Driver by lazy { GraphDatabase.driver(container.boltUrl, AuthTokens.none()).also { it.verifyConnectivity() } }

    /** Runs one Cypher statement and returns its records. */
    fun run(cypher: String, params: Map<String, Any?> = emptyMap()): List<Record> =
        driver.executableQuery(cypher).withParameters(params).execute().records()

    /**
     * Wipes the graph, drops every constraint and index the tests may have made, then runs the
     * statements in the classpath resource [seed], one per `;`.
     */
    fun reset(seed: String) {
        run("MATCH (n) DETACH DELETE n")
        run("SHOW CONSTRAINTS YIELD name").forEach { run("DROP CONSTRAINT ${it["name"].asString()}") }
        run("SHOW INDEXES YIELD name, type WHERE type <> 'LOOKUP'").forEach { run("DROP INDEX ${it["name"].asString()} IF EXISTS") }
        statements(resource(seed)).forEach { run(it) }
    }

    /** The text of a classpath resource, such as `/sfz/model/l08/ring.cypher`. */
    fun resource(path: String): String =
        (TestNeo4j::class.java.getResource(path) ?: error("missing resource $path")).readText()

    /** Splits a Cypher file into statements: comments dropped, one statement per `;` (a final one may omit it). */
    fun statements(text: String): List<String> =
        text.lines().filterNot { it.trimStart().startsWith("//") }.joinToString("\n")
            .split(Regex(";\\s*(\\n|$)")).map { it.trim() }.filter { it.isNotEmpty() }

    /** Every operator name in the plan of `EXPLAIN <cypher>`, depth first, such as `NodeUniqueIndexSeek`. */
    fun operators(cypher: String, params: Map<String, Any?> = emptyMap()): List<String> {
        val summary = driver.executableQuery("EXPLAIN $cypher").withParameters(params).execute().summary()
        fun walk(p: Plan): List<String> = listOf(p.operatorType().substringBefore('@')) + p.children().flatMap(::walk)
        return walk(summary.plan())
    }
}
