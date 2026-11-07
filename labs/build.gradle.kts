import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import org.jetbrains.kotlin.gradle.dsl.KotlinJvmProjectExtension

plugins {
    kotlin("jvm") version "2.4.21" apply false
}

// every library version in one place; modules read them with versions["name"]
val versions = mapOf(
    "junit" to "6.1.3",
    "assertj" to "3.27.7",
    "coroutines" to "1.11.0",
    "testcontainers" to "2.0.5",
    "slf4j" to "2.0.20",
    "postgres" to "42.7.14",
    "hikari" to "7.1.0",
    "kafka" to "4.4.0",
    "lettuce" to "7.9.0.RELEASE",
    "jedis" to "8.0.2",
    "mongodb" to "5.14.0",
    "cassandra" to "4.19.4",
)
extra["versions"] = versions

subprojects {
    apply(plugin = "org.jetbrains.kotlin.jvm")

    repositories { mavenCentral() }

    val sourceSets = extensions.getByType<SourceSetContainer>()
    // the reference answers: same class names, signatures and resource paths as the exercises in src/main
    val solution = sourceSets.create("solution")
    // small programs for the "Try it" steps, run with ./gradlew :<track>:demo -Pmain=<class>
    val demo = sourceSets.create("demo")

    configurations["solutionImplementation"].extendsFrom(configurations["implementation"])
    configurations["solutionRuntimeOnly"].extendsFrom(configurations["runtimeOnly"])
    configurations["demoImplementation"].extendsFrom(configurations["implementation"])
    configurations["demoRuntimeOnly"].extendsFrom(configurations["runtimeOnly"])

    dependencies {
        "testImplementation"(platform("org.junit:junit-bom:${versions["junit"]}"))
        "testImplementation"("org.junit.jupiter:junit-jupiter")
        "testImplementation"("org.assertj:assertj-core:${versions["assertj"]}")
        "testImplementation"(kotlin("test"))
        "testRuntimeOnly"("org.junit.platform:junit-platform-launcher")
    }

    extensions.configure<JavaPluginExtension> {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    tasks.withType<JavaCompile>().configureEach {
        options.release.set(21)
        options.encoding = "UTF-8"
    }
    extensions.configure<KotlinJvmProjectExtension> {
        compilerOptions { jvmTarget.set(JvmTarget.JVM_21) }
    }

    fun Test.common() {
        useJUnitPlatform()
        // a stuck test fails after 60 s instead of hanging the build; starting a container gets 3 minutes
        systemProperty("junit.jupiter.execution.timeout.default", "60 s")
        systemProperty("junit.jupiter.execution.timeout.beforeall.method.default", "180 s")
        systemProperty("junit.jupiter.execution.timeout.thread.mode.default", "SEPARATE_THREAD")
        jvmArgs("-XX:+EnableDynamicAgentLoading", "-Xshare:off")
        testLogging {
            events("passed", "failed", "skipped")
            exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL
            showStandardStreams = false
        }
        outputs.upToDateWhen { false }
    }

    // ./gradlew :<track>:test runs the tests against YOUR code in src/main
    tasks.named<Test>("test") { common() }

    // ./gradlew :<track>:solutionTest runs the same tests against the reference answers
    tasks.register<Test>("solutionTest") {
        description = "Runs the track's tests against the reference solutions."
        group = "verification"
        common()
        val testSet = sourceSets["test"]
        testClassesDirs = testSet.output.classesDirs
        classpath = testSet.output + solution.output + configurations["testRuntimeClasspath"]
    }

    tasks.register<JavaExec>("demo") {
        description = "Runs a demo: ./gradlew :<track>:demo -Pmain=fully.qualified.MainClass [-Pargs='a b']"
        group = "application"
        classpath = demo.runtimeClasspath
        mainClass.set(providers.gradleProperty("main").orElse("missing.PassMainWithDashPmain"))
        args = providers.gradleProperty("args").map { it.split(" ").filter(String::isNotBlank) }.getOrElse(emptyList())
        jvmArgs("-Xshare:off")
        standardInput = System.`in`
    }
}
