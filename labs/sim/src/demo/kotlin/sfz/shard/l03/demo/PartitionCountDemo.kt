package sfz.shard.l03.demo

/** Fixed partitions spread over N nodes: the busiest node holds ceil(P / N), the quietest floor(P / N). */
fun main() {
    println("partitions  nodes  per node (min to max)  busiest node vs average")
    for (p in listOf(12, 480, 512)) {
        for (n in listOf(5, 13, 32, 40, 48, 96)) {
            val min = p / n
            val max = (p + n - 1) / n
            val ratio = max / (p.toDouble() / n)
            val note = if (min == 0) "  <- some nodes hold nothing" else ""
            println("%10d  %5d  %9d to %-9d  %22.2f%s".format(p, n, min, max, ratio, note))
        }
    }
}
