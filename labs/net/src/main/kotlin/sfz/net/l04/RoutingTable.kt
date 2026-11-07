package sfz.net.l04

/**
 * One line of `ip route`: packets for [prefix] leave through the card [dev]. When [via] is set they go to
 * that router (the frame carries the router's MAC); when it is null the destination is on that link and
 * gets the frame directly.
 */
data class Route(val prefix: Prefix, val dev: String, val via: Int? = null) {
    override fun toString() = "$prefix" + (via?.let { " via ${Ip.format(it)}" } ?: "") + " dev $dev"

    companion object {
        /** Reads the lines `ip route` prints: `"default via 10.10.1.1 dev eth0"`, `"10.10.1.0/24 dev eth0"`. */
        fun parse(line: String): Route {
            val words = line.trim().split(Regex("\\s+"))
            fun after(key: String) = words.indexOf(key).takeIf { it >= 0 }?.let { words[it + 1] }
            val dev = after("dev") ?: throw IllegalArgumentException("no dev in: $line")
            return Route(Prefix.parse(words[0]), dev, after("via")?.let(Ip::parse))
        }
    }
}

/** A routing table: the list `ip route` prints, and the one question a router asks it for every packet. */
class RoutingTable(val routes: List<Route>) {
    /**
     * The route for [dst]. Of all the routes whose prefix contains [dst], pick the one with the longest
     * prefix: it describes the destination most precisely. A /32 beats a /24, a /24 beats a /16, and
     * the default route (/0) matches everything, so it wins only when nothing else matches.
     * Returns null when no route matches (a table without a default route).
     */
    fun lookup(dst: Int): Route? {
        TODO("keep the routes whose prefix contains dst, return the one with the largest prefix length")
    }

    override fun toString() = routes.joinToString("\n")

    companion object {
        /** `RoutingTable.of("default via 10.10.1.1 dev eth0", "10.10.1.0/24 dev eth0")` */
        fun of(vararg lines: String) = RoutingTable(lines.map(Route::parse))
    }
}
