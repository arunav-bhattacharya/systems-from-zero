@Suppress("UNCHECKED_CAST")
val versions = rootProject.extra["versions"] as Map<String, String>

// The AWS SDK for Java 2.x moves fast; pinned here because the root versions map is not ours to edit.
val awsSdk = "2.57.11"
// Neo4j's Java driver (lesson 11), pinned here for the same reason
val neo4jDriver = "6.3.0"

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:${versions["coroutines"]}")
    implementation("org.mongodb:mongodb-driver-sync:${versions["mongodb"]}")
    implementation("org.apache.cassandra:java-driver-core:${versions["cassandra"]}")
    // DynamoDB: the low-level client plus the Enhanced Client (table schemas, typed items)
    implementation("software.amazon.awssdk:dynamodb-enhanced:$awsSdk")
    implementation("software.amazon.awssdk:dynamodb:$awsSdk")
    implementation("org.neo4j.driver:neo4j-java-driver:$neo4jDriver")
    runtimeOnly("org.slf4j:slf4j-simple:${versions["slf4j"]}")
    testImplementation("org.testcontainers:testcontainers:${versions["testcontainers"]}")
    testImplementation("org.testcontainers:testcontainers-mongodb:${versions["testcontainers"]}")
    testImplementation("org.testcontainers:testcontainers-cassandra:${versions["testcontainers"]}")
    testImplementation("org.testcontainers:testcontainers-neo4j:${versions["testcontainers"]}")
    testImplementation("org.testcontainers:testcontainers-junit-jupiter:${versions["testcontainers"]}")
}
