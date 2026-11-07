package sfz.os.l11

/** The kernel's side of one connected socket: bytes that arrived and nobody has read yet. */
class SimSocket(val fd: Int) {
    val queue = StringBuilder()                         // the receive queue
    var peerClosed = false                              // the other side sent FIN

    /** Readable means a read() would not return EAGAIN: there are bytes, or end of file. */
    val readable: Boolean get() = queue.isNotEmpty() || peerClosed
}

/** What read() on a non-blocking socket returns. */
sealed interface ReadResult {
    data class Data(val text: String) : ReadResult
    /** EAGAIN: nothing there yet; try again later. */
    data object Again : ReadResult
    /** 0 bytes: the peer closed the connection. */
    data object Eof : ReadResult
}

enum class Trigger { LEVEL, EDGE }

/**
 * The parts of the kernel this lab needs: sockets, the network delivering bytes to them, a
 * non-blocking read(), and the epoll instances that watch them. Written for you.
 */
class Kernel {
    private var nextFd = 3
    private val watchers = mutableListOf<Epoll>()

    /** System calls made, and how many of the reads returned EAGAIN. */
    var reads = 0; private set
    var eagains = 0; private set

    fun socket(): SimSocket = SimSocket(nextFd++)

    fun epoll(): Epoll = Epoll().also { watchers += it }

    /** A packet arrives: the bytes join the receive queue, and every epoll watching the socket hears about it. */
    fun arrive(s: SimSocket, text: String) {
        s.queue.append(text)
        watchers.forEach { it.onArrive(s) }
    }

    /** The peer closes: end of file is readable, so watchers hear about it too. */
    fun hangUp(s: SimSocket) {
        s.peerClosed = true
        watchers.forEach { it.onArrive(s) }
    }

    /** read() with O_NONBLOCK: up to [max] bytes, or EAGAIN at once when the queue is empty. */
    fun read(s: SimSocket, max: Int): ReadResult {
        reads++
        if (s.queue.isEmpty()) {
            if (s.peerClosed) return ReadResult.Eof
            eagains++
            return ReadResult.Again
        }
        val n = minOf(max, s.queue.length)
        val out = s.queue.substring(0, n)
        s.queue.delete(0, n)
        return ReadResult.Data(out)
    }
}

/**
 * poll(): the caller hands over the whole list on every call, and the kernel checks every socket in it.
 * [examined] counts the checks. Written for you, to compare with [Epoll].
 */
class Poll {
    var examined = 0L; private set

    fun poll(sockets: List<SimSocket>): List<SimSocket> {
        examined += sockets.size
        return sockets.filter { it.readable }
    }
}

/**
 * epoll: an interest list you fill once with [add], and a ready list the kernel fills when data
 * arrives ([onArrive], called by [Kernel.arrive]). epoll_wait only looks at the ready list, so 2,000
 * idle sockets cost it nothing. [examined] counts the ready-list entries [wait] looked at.
 */
class Epoll {
    private val interest = HashMap<SimSocket, Trigger>()
    private val ready = LinkedHashSet<SimSocket>()      // in arrival order, each socket at most once
    var examined = 0L; private set

    /** epoll_ctl(EPOLL_CTL_ADD): watch [s]. A socket that is already readable goes on the ready list at once. */
    fun add(s: SimSocket, trigger: Trigger) {
        interest[s] = trigger
        if (s.readable) ready += s
    }

    fun remove(s: SimSocket) {
        interest.remove(s)
        ready.remove(s)
    }

    /** The kernel's callback (only [Kernel] calls it): something arrived on [s]. */
    fun onArrive(s: SimSocket) {
        if (s in interest) ready += s
    }

    /**
     * epoll_wait: report up to [max] sockets from the ready list, oldest first.
     * - LEVEL: report a socket while it is still readable, and leave it on the list, so the next
     *   wait checks it again. A socket that is no longer readable is dropped without being reported.
     * - EDGE: report the socket and take it off the list. Only a new arrival puts it back, however
     *   many bytes are still waiting.
     */
    fun wait(max: Int = 64): List<SimSocket> {
        TODO("wait: walk the ready list; LEVEL keeps readable sockets listed, EDGE removes what it reports")
    }
}

/**
 * The loop at the heart of every NIO server: wait for ready sockets, then read from each one.
 * [chunk] is the buffer size. With [drain], it reads each ready socket until EAGAIN; without it,
 * it reads once per wake-up.
 */
class EventLoop(val kernel: Kernel, val epoll: Epoll, val chunk: Int, val drain: Boolean) {
    /** Everything read so far, per socket. */
    val received = HashMap<SimSocket, StringBuilder>()
    /** Sockets whose peer closed, in the order the loop saw end of file. */
    val closed = mutableListOf<SimSocket>()

    fun watch(s: SimSocket, trigger: Trigger) = epoll.add(s, trigger)

    /**
     * One turn: one [Epoll.wait], then for each socket it returned, read [chunk] bytes, either once or
     * (with [drain]) again and again until read() says EAGAIN. Data goes into [received]. End of file
     * adds the socket to [closed] and removes it from the epoll. Returns how many sockets were handled.
     */
    fun turn(): Int {
        TODO("turn: one wait, then read each ready socket once, or until EAGAIN with drain")
    }
}
