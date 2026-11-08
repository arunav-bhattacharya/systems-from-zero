package sfz.dist.l02

/**
 * Lesson dist-02, exercise 3: why redundancy makes a gray failure hit more requests, not fewer.
 *
 * A request fans out to [fanOut] servers. Each sub-request crosses one of [paths] equal paths (core
 * switches), picked at random. One path is gray: it drops or delays some packets but still looks
 * healthy. Returns the chance that the request touches that path at least once:
 * 1 - ((paths - 1) / paths) ^ fanOut.
 */
fun chanceToTouchGray(paths: Int, fanOut: Int): Double {
    TODO("Exercise 3: 1 - ((paths - 1) / paths) ^ fanOut")
}
