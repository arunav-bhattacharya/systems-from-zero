plugins {
    // lets Gradle download a matching JDK when a module asks for a toolchain you don't have
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}

rootProject.name = "systems-from-zero-labs"

// one subproject per track; each has exercises (src/main), solutions (src/solution),
// shared tests (src/test) and runnable demos (src/demo)
include("net", "os", "sql", "nosql", "internals", "kafka", "redis", "bigdata")
