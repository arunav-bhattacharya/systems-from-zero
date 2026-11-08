package sfz.shard.l05

import kotlin.random.Random

/** One application state (STATUS, LOAD, SCHEMA, DC, RACK, TOKENS) and the version it was set at. */
data class Versioned(val value: String, val version: Int)

/**
 * What the cluster knows about one node, in the shape gossip carries it: the node's [generation]
 * (the time it last started, in seconds), the version of its latest [heartbeat], and its
 * application [states]. Versions come from ONE counter per node, shared by the heartbeat and every
 * state, so "newer" is a single number comparison inside one generation.
 */
data class EndpointState(val generation: Int, val heartbeat: Int, val states: Map<String, Versioned> = emptyMap()) {
    /** The highest version anywhere in this state. A digest carries it. Given. */
    val maxVersion: Int get() = maxOf(heartbeat, states.values.maxOfOrNull { it.version } ?: 0)

    /**
     * The parts newer than [version]: the heartbeat (always, as Cassandra sends it) plus every
     * state with a higher version. Null when nothing here is newer. Given.
     */
    fun newerThan(version: Int): EndpointState? =
        if (maxVersion <= version) null else EndpointState(generation, heartbeat, states.filterValues { it.version > version })
}

/** "I know [endpoint] at [generation], up to [maxVersion]." A Syn is a list of these: three numbers per node. */
data class Digest(val endpoint: String, val generation: Int, val maxVersion: Int)

/** The reply to a Syn: digests of what the receiver wants ([requests]) and the [states] it has that are newer. */
data class Ack(val requests: List<Digest>, val states: Map<String, EndpointState>)

/**
 * One Cassandra node's gossip state: its map of every endpoint it knows, itself included.
 *
 * One exchange between two nodes is three messages (see [GossipCluster.exchange]):
 * 1. GossipDigestSyn: the initiator sends [digests], one per endpoint it knows.
 * 2. GossipDigestAck: the receiver runs [examine] and replies with what it wants and what it has that is newer.
 * 3. GossipDigestAck2: the initiator [apply]s those states and sends what was asked for ([answer]).
 */
class GossipNode(val name: String, generation: Int) {
    /** endpoint -> what this node knows about it. Sorted so printouts are stable. */
    val endpoints: MutableMap<String, EndpointState> = sortedMapOf(name to EndpointState(generation, 0))

    /** One version counter for the heartbeat and every state, as in Cassandra. It restarts from 0 when the node does. */
    private var version = 0

    /** This node's own state. Given. */
    val self: EndpointState get() = endpoints.getValue(name)

    /** One gossip round starts here: the node bumps its own heartbeat to the next version. Given. */
    fun beat() {
        endpoints[name] = self.copy(heartbeat = ++version)
    }

    /** Sets one of this node's application states, such as STATUS or LOAD, at the next version. Given. */
    fun set(key: String, value: String) {
        endpoints[name] = self.copy(states = self.states + (key to Versioned(value, ++version)))
    }

    /** The Syn: one digest per endpoint this node knows. Given. */
    fun digests(): List<Digest> = endpoints.map { (ep, s) -> Digest(ep, s.generation, s.maxVersion) }

    /**
     * The receiver's side of a Syn (Cassandra's `examineGossiper`). For each digest in [syn], compare
     * it with what this node knows about that endpoint:
     * - unknown here, or a higher generation there: request everything, `Digest(ep, theirGeneration, 0)`;
     * - a lower generation there: send everything this node has, `newerThan(0)`;
     * - same generation, higher version there: request what is newer than ours, `Digest(ep, gen, ourMaxVersion)`;
     * - same generation, lower version there: send what is newer than theirs, `newerThan(theirMaxVersion)`;
     * - the same: nothing.
     * Endpoints that the syn doesn't mention are left alone.
     */
    fun examine(syn: List<Digest>): Ack {
        val requests = mutableListOf<Digest>()
        val states = sortedMapOf<String, EndpointState>()
        for (d in syn) {
            val local = endpoints[d.endpoint]
            when {
                // never heard of it, or it restarted since: ask for the whole state
                local == null || d.generation > local.generation -> requests += Digest(d.endpoint, d.generation, 0)
                // the sender is behind a restart: give it the whole new state
                d.generation < local.generation -> states[d.endpoint] = local.newerThan(0)!!
                // same life of the node: compare one number
                d.maxVersion > local.maxVersion -> requests += Digest(d.endpoint, d.generation, local.maxVersion)
                d.maxVersion < local.maxVersion -> states[d.endpoint] = local.newerThan(d.maxVersion)!!
            }
        }
        return Ack(requests, states)
    }

    /**
     * Merges states received in an Ack or an Ack2 (Cassandra's `applyStateLocally`), and returns the
     * endpoints whose heartbeat moved forward: a failure detector counts those as heartbeats heard.
     * - Never take another node's view of yourself.
     * - Unknown endpoint, or a higher generation: replace the whole state (the node restarted).
     * - Same generation: keep the higher heartbeat, and take each state whose version is higher than ours.
     * - Lower generation: ignore it, it describes a life of that node that is over.
     */
    fun apply(states: Map<String, EndpointState>): Set<String> {
        val moved = sortedSetOf<String>()
        for ((ep, remote) in states) {
            if (ep == name) continue
            val local = endpoints[ep]
            if (local == null || remote.generation > local.generation) {
                endpoints[ep] = remote // a new node, or a new life of an old one: versions start again
                moved += ep
            } else if (remote.generation == local.generation) {
                val merged = local.states.toMutableMap()
                for ((key, value) in remote.states) {
                    if (value.version > (merged[key]?.version ?: 0)) merged[key] = value
                }
                if (remote.heartbeat > local.heartbeat) moved += ep
                endpoints[ep] = EndpointState(local.generation, maxOf(local.heartbeat, remote.heartbeat), merged)
            }
            // remote.generation < local.generation: stale news about a previous life, drop it
        }
        return moved
    }

    /** The Ack2: for each request in an Ack, what this node has that is newer than the version asked for. Given. */
    fun answer(requests: List<Digest>): Map<String, EndpointState> =
        requests.mapNotNull { d -> endpoints[d.endpoint]?.newerThan(d.maxVersion)?.let { d.endpoint to it } }.toMap()
}

/**
 * Many [GossipNode]s and a network between them. Each [round] is one second of Cassandra's gossip:
 * every running node beats its heartbeat, then exchanges digests with one random peer it knows, and
 * sometimes also with a seed. Everything here is given.
 */
class GossipCluster(names: List<String>, val seeds: Set<String>, randomSeed: Long = 1) {
    private val random = Random(randomSeed)

    /** Generations are start times in seconds. All nodes here started at the same moment. */
    val startedAt = 1_794_100_000

    private val members = LinkedHashMap(names.associateWith { GossipNode(it, startedAt) })
    val nodes: Map<String, GossipNode> get() = members
    private val running = names.toMutableSet()

    /** The round each observer last saw each endpoint's heartbeat move: observer -> endpoint -> round. */
    val lastHeard: Map<String, MutableMap<String, Int>> = names.associateWith { HashMap<String, Int>() }

    var round = 0
        private set

    /** Messages sent so far (3 per completed exchange, 1 per Syn lost to a stopped node) and states carried. */
    var messages = 0
        private set
    var statesCarried = 0
        private set

    init {
        // start converged: every node already knows every other node's state
        for (n in nodes.values) for (m in nodes.values) if (n !== m) n.endpoints[m.name] = m.self
    }

    fun isRunning(name: String) = name in running

    /** One gossip round. Nodes act one after the other in a random order, as real nodes fire at different moments of the second. */
    fun round() {
        round++
        for (name in running.shuffled(random)) {
            val node = nodes.getValue(name)
            node.beat()
            val peers = (node.endpoints.keys - name).toList()
            if (peers.isEmpty()) continue
            val target = peers.random(random)
            exchange(node, target)
            // Cassandra also gossips to a seed, with probability seeds / known nodes, if the peer wasn't one
            if (target !in seeds && seeds.isNotEmpty() && random.nextDouble() < seeds.size.toDouble() / peers.size) {
                (seeds - name).randomOrNull(random)?.let { exchange(node, it) }
            }
        }
    }

    /** Syn, Ack, Ack2 between [from] and [toName]. A Syn to a stopped node is lost and nothing else happens. */
    fun exchange(from: GossipNode, toName: String) {
        messages++
        if (toName !in running) return
        val to = nodes.getValue(toName)
        val ack = to.examine(from.digests())   // 1. Syn ->   2. <- Ack
        heard(from.name, from.apply(ack.states))
        val ack2 = from.answer(ack.requests)   // 3. Ack2 ->
        heard(to.name, to.apply(ack2))
        messages += 2
        statesCarried += ack.states.size + ack2.size
    }

    private fun heard(observer: String, endpoints: Set<String>) {
        for (ep in endpoints) lastHeard.getValue(observer)[ep] = round
    }

    /** The process stops: no more heartbeats, and Syns sent to it are lost. */
    fun stop(name: String) {
        running -= name
    }

    /**
     * The node starts again with a new generation (a later start time) and an empty version counter,
     * like a restarted JVM. Before gossiping it asks a seed for everything it knows: Cassandra's shadow round.
     */
    fun restart(name: String, generation: Int) {
        val fresh = GossipNode(name, generation)
        members[name] = fresh
        val seed = (seeds - name).first { it in running }
        for ((ep, s) in nodes.getValue(seed).endpoints) if (ep != name) fresh.endpoints[ep] = s
        running += name
    }

    /** True when every running node holds [endpoint]'s state at least at [generation] and [version]. */
    fun everyoneKnows(endpoint: String, generation: Int, version: Int): Boolean = running.all { n ->
        val s = nodes.getValue(n).endpoints[endpoint]
        s != null && (s.generation > generation || (s.generation == generation && s.maxVersion >= version))
    }

    companion object {
        /** A cluster of [n] nodes named node-01, node-02, ..., with node-01 as the only seed. */
        fun of(n: Int, randomSeed: Long = 1): GossipCluster {
            val names = (1..n).map { "node-%02d".format(it) }
            return GossipCluster(names, setOf(names.first()), randomSeed)
        }
    }
}
