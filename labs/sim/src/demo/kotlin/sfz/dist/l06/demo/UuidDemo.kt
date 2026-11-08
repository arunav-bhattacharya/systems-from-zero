package sfz.dist.l06.demo

import kotlin.uuid.ExperimentalUuidApi
import kotlin.uuid.Uuid

/**
 * Lesson dist-06, worked example: Kotlin's UUIDv7 generator. Five ids made in a row, with the 48-bit millisecond
 * timestamp read back out of each one.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l06.demo.UuidDemoKt -q
 */
@OptIn(ExperimentalUuidApi::class)
fun main() {
    val ids = List(5) { Uuid.generateV7() }
    for (id in ids) {
        val ms = id.toLongs { high, _ -> high ushr 16 }               // the top 48 bits: Unix time in ms
        println("$id  ms=$ms  version=${id.toString()[14]}")
    }
    println("increasing: ${ids.zipWithNext().all { (a, b) -> a < b }}")
}
