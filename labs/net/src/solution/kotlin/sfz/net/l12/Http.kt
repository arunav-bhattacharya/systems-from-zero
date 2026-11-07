package sfz.net.l12

/**
 * One outgoing call. A POST is safe to send twice only with an [idempotencyKey] that the server
 * remembers, so that a second copy returns the first result instead of charging the card again.
 */
data class Request(val method: String, val path: String, val idempotencyKey: String? = null)

/** How one attempt ended. Finished: the pool, the policy and the tests share these types. */
sealed interface Outcome {
    /** The server answered with this HTTP status code. */
    data class Status(val code: Int) : Outcome

    /** Connection refused: an RST answered the SYN. The request was never sent. */
    data object ConnectRefused : Outcome

    /** No answer to the SYN within the connect timeout. The request was never sent. */
    data object ConnectTimeout : Outcome

    /**
     * The connection was reset after the request was written and before any byte of the answer.
     * The client can't tell whether a server acted on the request.
     */
    data object Reset : Outcome

    /** The request went out and no answer came within the read timeout. The server may have acted on it. */
    data object ReadTimeout : Outcome
}

/** One TCP connection, as the pool sees it. After any outcome other than [Outcome.Status] it is dead. */
interface Connection {
    val id: Int
    fun send(request: Request): Outcome
    fun close()
}
