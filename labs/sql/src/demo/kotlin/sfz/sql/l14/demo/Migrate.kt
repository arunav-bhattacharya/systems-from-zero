package sfz.sql.l14.demo

import org.flywaydb.core.Flyway
import org.flywaydb.core.api.FlywayException

/**
 * Lesson sql-14, Try it 5: Flyway applies the migrations in src/demo/resources/sfz/sql/l14/demo/migration
 * to schema l14_demo of database course, and records them in l14_demo.flyway_schema_history.
 *
 *   ./gradlew :sql:demo -Pmain=sfz.sql.l14.demo.MigrateKt      (from the labs folder)
 *
 * Start over with DROP SCHEMA l14_demo CASCADE; in psql.
 */
fun main() {
    println("server: ${Db.url}")
    val flyway = Flyway.configure()
        .dataSource(Db.url, Db.USER, Db.PASSWORD)
        .schemas("l14_demo")                                   // created if missing; holds the history table
        .locations("classpath:sfz/sql/l14/demo/migration")
        .load()

    fun info(title: String) {
        println(title)
        flyway.info().all().forEach { m -> println("  version %-4s %-28s %s".format(m.version ?: "-", m.description, m.state)) }
    }

    info("before migrate:")
    try {
        val result = flyway.migrate()
        println("migrate: ${result.migrationsExecuted} migration(s) applied, schema now at version ${result.targetSchemaVersion ?: result.initialSchemaVersion}")
    } catch (e: FlywayException) {
        println("migrate refused: ${e.message?.lineSequence()?.filter { it.isNotBlank() }?.take(4)?.joinToString("\n  ")}")
        return
    }
    info("after migrate:")
}
