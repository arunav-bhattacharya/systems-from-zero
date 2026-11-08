package sfz.dist.l08

/**
 * Lesson dist-08: primary-backup replication of one register, twice.
 *
 * [NaivePrimaryBackup] is given and stays as it is: the simulator finds its bug. [PrimaryBackup] is
 * yours to fix (exercise 3).
 *
 * The design both share:
 * - the primary applies a client write, sends Replicate to the backup, and acknowledges the client
 *   only when the backup confirms (synchronous replication). It resends Replicate every
 *   [RESEND_EVERY_MS] until it hears back.
 * - the primary sends a heartbeat every [HEARTBEAT_EVERY_MS]. A backup that hears nothing from the
 *   primary for [FAILOVER_AFTER_MS] promotes itself, announces itself to the registry, and from then
 *   on runs alone: it treats its peer as dead and acknowledges writes itself.
 * - only a primary answers clients. A node that isn't primary ignores client requests, and the
 *   client's timeout sends them elsewhere.
 */
class NaivePrimaryBackup(
    override val name: String,
    private val peer: String,
    startsAsPrimary: Boolean,
) : Server {
    override var value = 0
        private set
    override var isPrimary = startsAsPrimary
        private set
    private var alone = false                              // promoted: the peer is presumed dead
    private var lastHeard = 0L
    private val waiting = mutableMapOf<Int, Int>()         // op -> value, waiting for the backup's ok
    private lateinit var env: Env

    override fun start(env: Env) {
        this.env = env
        env.after(HEARTBEAT_EVERY_MS, "heartbeat")
        env.after(10, "check")
    }

    override fun onMessage(from: String, msg: Msg) {
        if (from == peer) lastHeard = env.now
        when (msg) {
            is Write -> if (isPrimary) {
                value = msg.value
                if (alone) {
                    env.send("client", Ack(msg.op))
                } else {
                    waiting[msg.op] = msg.value
                    env.send(peer, Replicate(msg.op, msg.value, 1))
                    env.after(RESEND_EVERY_MS, "resend ${msg.op}")
                }
            }
            is Read -> if (isPrimary) env.send("client", ReadOk(msg.op, value))
            is Replicate -> {
                value = msg.value                          // the bug: whoever sends it, whatever we are now
                env.send(peer, ReplicateOk(msg.op, msg.epoch))
            }
            is ReplicateOk -> if (waiting.remove(msg.op) != null) env.send("client", Ack(msg.op))
            is Heartbeat, is Refused, is Ack, is ReadOk -> {}
        }
    }

    override fun onTimer(timer: String) {
        when {
            timer == "heartbeat" -> {
                if (isPrimary) env.send(peer, Heartbeat(1))
                env.after(HEARTBEAT_EVERY_MS, "heartbeat")
            }
            timer == "check" -> {
                if (!isPrimary && env.now - lastHeard > FAILOVER_AFTER_MS) {
                    isPrimary = true
                    alone = true
                    env.log("heard nothing from $peer for $FAILOVER_AFTER_MS ms: promoting myself")
                    env.announcePrimary()
                }
                env.after(10, "check")
            }
            timer.startsWith("resend ") -> {
                val op = timer.removePrefix("resend ").toInt()
                val v = waiting[op] ?: return
                env.send(peer, Replicate(op, v, 1))
                env.after(RESEND_EVERY_MS, timer)
            }
        }
    }
}

/**
 * Exercise 3 of 3: fence the old primary with epochs.
 *
 * The naive protocol's bug: when n1 pauses (or loses its link to n2) for longer than the failover
 * timeout, n2 promotes itself and acknowledges new writes. When n1 comes back it still believes it
 * is primary, and its late Replicate for an old write overwrites n2's newer value.
 *
 * The fix is a fencing token, as in lesson 5 of this track:
 * - every node keeps an [epoch], starting at 1. A node that promotes itself adds 1.
 * - every Replicate and Heartbeat carries the sender's epoch.
 * - a node that receives a Replicate or Heartbeat from an older epoch refuses it: it applies nothing
 *   and answers `Refused(myEpoch)`.
 * - a node that sees a newer epoch in any message from its peer (Replicate, Heartbeat, Refused)
 *   takes that epoch, and if it was primary it steps down: no longer primary, and it forgets the
 *   writes it was waiting to acknowledge. Log the step-down with `env.log("... steps down")`.
 */
class PrimaryBackup(
    override val name: String,
    private val peer: String,
    startsAsPrimary: Boolean,
) : Server {
    override var value = 0
        private set
    override var isPrimary = startsAsPrimary
        private set
    var epoch = 1
        private set
    private var alone = false                              // promoted: the peer is presumed dead
    private var lastHeard = 0L
    private val waiting = mutableMapOf<Int, Int>()         // op -> value, waiting for the backup's ok
    private lateinit var env: Env

    override fun start(env: Env) {
        this.env = env
        env.after(HEARTBEAT_EVERY_MS, "heartbeat")
        env.after(10, "check")
    }

    override fun onMessage(from: String, msg: Msg) {
        if (from == peer) lastHeard = env.now
        when (msg) {
            is Write -> if (isPrimary) {
                value = msg.value
                if (alone) {
                    env.send("client", Ack(msg.op))
                } else {
                    waiting[msg.op] = msg.value
                    env.send(peer, Replicate(msg.op, msg.value, 1))
                    env.after(RESEND_EVERY_MS, "resend ${msg.op}")
                }
            }
            is Read -> if (isPrimary) env.send("client", ReadOk(msg.op, value))
            is Replicate -> {
                value = msg.value                          // the bug: whoever sends it, whatever we are now
                env.send(peer, ReplicateOk(msg.op, msg.epoch))
            }
            is ReplicateOk -> if (waiting.remove(msg.op) != null) env.send("client", Ack(msg.op))
            is Heartbeat, is Refused, is Ack, is ReadOk -> {}
        }
    }

    override fun onTimer(timer: String) {
        when {
            timer == "heartbeat" -> {
                if (isPrimary) env.send(peer, Heartbeat(1))
                env.after(HEARTBEAT_EVERY_MS, "heartbeat")
            }
            timer == "check" -> {
                if (!isPrimary && env.now - lastHeard > FAILOVER_AFTER_MS) {
                    isPrimary = true
                    alone = true
                    env.log("heard nothing from $peer for $FAILOVER_AFTER_MS ms: promoting myself")
                    env.announcePrimary()
                }
                env.after(10, "check")
            }
            timer.startsWith("resend ") -> {
                val op = timer.removePrefix("resend ").toInt()
                val v = waiting[op] ?: return
                env.send(peer, Replicate(op, v, 1))
                env.after(RESEND_EVERY_MS, timer)
            }
        }
    }
}
