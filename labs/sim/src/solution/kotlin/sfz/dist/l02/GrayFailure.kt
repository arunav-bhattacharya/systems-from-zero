package sfz.dist.l02

import kotlin.math.pow

/**
 * Lesson dist-02, exercise 3: why redundancy makes a gray failure hit more requests, not fewer.
 *
 * A request fans out to [fanOut] servers. Each sub-request crosses one of [paths] equal paths (core
 * switches), picked at random. One path is gray: it drops or delays some packets but still looks
 * healthy. Returns the chance that the request touches that path at least once:
 * 1 - ((paths - 1) / paths) ^ fanOut.
 */
fun chanceToTouchGray(paths: Int, fanOut: Int): Double {
    require(paths >= 1 && fanOut >= 0) { "paths >= 1, fanOut >= 0" }
    val missOne = (paths - 1).toDouble() / paths           // one sub-request avoids the gray path
    return 1.0 - missOne.pow(fanOut)                       // all of them avoid it, or not
}
