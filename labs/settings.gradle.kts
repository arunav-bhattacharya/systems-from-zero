plugins {
    // lets Gradle download a matching JDK when a module asks for a toolchain you don't have
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}

rootProject.name = "systems-from-zero-labs"

// one subproject per toolchain; a lesson lives in package sfz.<track>.lNN of the module whose libraries it needs.
// Each has exercises (src/main), solutions (src/solution),
// shared tests (src/test) and runnable demos (src/demo)
include("net", "os", "sql", "nosql", "internals", "kafka", "redis", "bigdata", "sim", "flow")
