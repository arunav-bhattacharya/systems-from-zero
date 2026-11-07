package sfz.net.l12

/**
 * A load balancer in front of the issuer, the way a cloud network load balancer or a NAT gateway
 * behaves: it forgets a connection that has carried nothing for [idleTimeoutMs], without telling the
 * client, and answers the next request on it with a reset. Every other request gets a 200.
 */
class FakeLb(private val idleTimeoutMs: Long, private val clock: () -> Long) {
    var opened = 0
        private set
    val resets = mutableListOf<Int>()
    val closedByClient = mutableListOf<Int>()

    fun connect(): Connection = object : Connection {
        override val id = ++opened
        private var lastActivity = clock()
        private var dead = false

        override fun send(request: Request): Outcome {
            check(!dead) { "connection $id was already closed" }
            if (clock() - lastActivity >= idleTimeoutMs) {             // the LB forgot it: RST
                dead = true
                resets += id
                return Outcome.Reset
            }
            lastActivity = clock()
            return Outcome.Status(200)
        }

        override fun close() {
            if (!dead) closedByClient += id
            dead = true
        }
    }
}
