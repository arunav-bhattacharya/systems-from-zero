@Suppress("UNCHECKED_CAST")
val versions = rootProject.extra["versions"] as Map<String, String>

dependencies {
    implementation("org.postgresql:postgresql:${versions["postgres"]}")
    implementation("com.zaxxer:HikariCP:${versions["hikari"]}")
    // schema migrations (lesson 14); Flyway keeps PostgreSQL support in a separate module
    implementation("org.flywaydb:flyway-core:13.12.1")
    implementation("org.flywaydb:flyway-database-postgresql:13.12.1")
    testImplementation("org.testcontainers:testcontainers-postgresql:${versions["testcontainers"]}")
    testImplementation("org.testcontainers:testcontainers-junit-jupiter:${versions["testcontainers"]}")
    testRuntimeOnly("org.slf4j:slf4j-simple:${versions["slf4j"]}")
    "demoRuntimeOnly"("org.slf4j:slf4j-simple:${versions["slf4j"]}")
}
