@Suppress("UNCHECKED_CAST")
val versions = rootProject.extra["versions"] as Map<String, String>

// JDK only: you build the storage engine pieces yourself. The exercises, solutions and tests need nothing else.
dependencies {
    // demos may run the reference solutions (the Raft demo prints a timeline of the lab's simulator)
    "demoImplementation"(sourceSets["solution"].output)
    // store-11's column-store demo runs DuckDB in-process (the first run downloads the driver, about 80 MB)
    "demoImplementation"("org.duckdb:duckdb_jdbc:2.0.0.1")
}

// DuckDB loads a native library; allow it without a warning on JDK 24 and newer
tasks.named<JavaExec>("demo") {
    jvmArgs("--enable-native-access=ALL-UNNAMED")
}
