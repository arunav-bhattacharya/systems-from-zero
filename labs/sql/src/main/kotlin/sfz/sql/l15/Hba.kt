package sfz.sql.l15

import java.net.InetAddress

/** How a client reached the server: the Unix-domain socket on the same machine, or TCP/IP. */
enum class Transport { SOCKET, TCP }

/**
 * One connection attempt, as the postmaster sees it before any password is checked.
 *
 * [address] is the client's IP address for TCP ("10.20.0.7", "::1") and null for the socket.
 * [replication] marks a physical replication connection (a standby, pg_basebackup), which asks
 * for no database at all. [memberOf] lists the roles [user] belongs to, directly or through other
 * roles; a "+role" entry in the user column matches them.
 */
data class Attempt(
    val transport: Transport,
    val user: String,
    val database: String = "",
    val address: String? = null,
    val ssl: Boolean = false,
    val replication: Boolean = false,
    val memberOf: Set<String> = emptySet(),
)

/** One rule of pg_hba.conf. [address] is a CIDR block or "all", and null on a local line. */
data class HbaLine(
    val lineNumber: Int,
    val type: String,
    val databases: List<String>,
    val users: List<String>,
    val address: String?,
    val method: String,
)

/** What pg_hba.conf decided for one attempt. */
sealed interface Decision {
    /** Line [line] matched. The server now runs [method]; "trust" lets the client straight in. */
    data class Authenticate(val line: Int, val method: String) : Decision

    /** Line [line] matched, and its method is reject. */
    data class Rejected(val line: Int) : Decision

    /** No line matched, so the server refuses the connection. */
    data object NoEntry : Decision
}

object Hba {
    private val TYPES = setOf("local", "host", "hostssl", "hostnossl")

    /**
     * Parses the text of a pg_hba.conf file (given, not an exercise). Blank lines and comments
     * are skipped; line numbers count every line of the text, as pg_hba_file_rules does.
     * This model knows the four common types and addresses written as CIDR blocks or "all";
     * PostgreSQL also accepts host names, samehost, samenet and a separate netmask column.
     */
    fun parse(text: String): List<HbaLine> = text.lines().mapIndexedNotNull { i, raw ->
        val n = i + 1
        val line = raw.substringBefore('#').trim()
        if (line.isEmpty()) return@mapIndexedNotNull null
        val f = line.split(Regex("\\s+"))
        val type = f[0]
        require(type in TYPES) { "line $n: unknown connection type '$type' (this model knows ${TYPES.joinToString()})" }
        if (type == "local") {
            require(f.size >= 4) { "line $n: a local line needs database, user and method" }
            HbaLine(n, type, f[1].split(','), f[2].split(','), null, f[3])
        } else {
            require(f.size >= 5) { "line $n: a $type line needs database, user, address and method" }
            val address = f[3]
            require(address == "all" || '/' in address) { "line $n: write the address as a CIDR block such as 10.0.0.0/8, or all" }
            HbaLine(n, type, f[1].split(','), f[2].split(','), address, f[4])
        }
    }

    /**
     * The bytes of an IP address literal (given): 4 for IPv4 ("10.1.2.3"), 16 for IPv6 ("::1").
     * It never looks a host name up.
     */
    fun ipBytes(text: String): ByteArray {
        require(text.isNotEmpty() && (':' in text || text.all { it.isDigit() || it == '.' })) { "not an IP address: '$text'" }
        val bytes = InetAddress.getByName(text).address
        // Java turns ::ffff:10.1.2.3 into the 4-byte IPv4 address; PostgreSQL treats it as IPv6
        return if (':' in text && bytes.size == 4) ByteArray(10) + byteArrayOf(-1, -1) + bytes else bytes
    }

    /**
     * Lesson sql-15, exercise 1 of 3 (part a): is [address] inside the block [cidr]?
     *
     * "10.1.0.0/16" means: the first 16 bits of the address must equal the first 16 bits of
     * 10.1.0.0. So 10.1.255.255 is inside and 10.2.0.0 is not. /32 is one IPv4 address, /0 is
     * every IPv4 address, and a prefix need not end on a byte (192.168.1.128/25 is .128 to .255).
     * An IPv4 block never matches an IPv6 address and an IPv6 block never matches an IPv4 one,
     * even 127.0.0.1/32 against ::1: compare the sizes of the two byte arrays first.
     */
    fun inCidr(address: String, cidr: String): Boolean =
        TODO("compare the first n bits of the two addresses; different sizes never match")

    /**
     * Lesson sql-15, exercise 1 of 3 (part b): what does pg_hba.conf decide for [attempt]?
     *
     * Walk [lines] from the top. The first line whose four columns all match decides, and no
     * later line is ever looked at: if that line's method is reject, the result is Rejected;
     * otherwise it is Authenticate with that line's method (and if the password then turns out
     * wrong, the client is refused; PostgreSQL never falls through to the next line). If no line
     * matches, the result is NoEntry.
     *
     * The columns:
     * - type: local matches only the socket; host matches any TCP connection; hostssl only TCP
     *   with SSL; hostnossl only TCP without SSL.
     * - database (a list): "all" matches every database, but never a replication connection;
     *   "replication" matches only replication connections; "sameuser" matches when the
     *   database is named like the user; "samerole" when the user is a member of the role the
     *   database is named after; any other entry is a database name.
     * - user (a list): "all"; "+role" matches the role itself and every member of it
     *   ([Attempt.memberOf]); any other entry is a role name.
     * - address (host lines only): "all", or a CIDR block (use [inCidr]).
     */
    fun decide(lines: List<HbaLine>, attempt: Attempt): Decision =
        TODO("walk the lines from the top; the first line whose type, database, user and address match decides")

    /** The message a client sees when [decision] refuses [attempt], worded as PostgreSQL 18 words it (given). */
    fun message(decision: Decision, attempt: Attempt): String {
        val host = "host \"${attempt.address ?: "[local]"}\", user \"${attempt.user}\""
        val enc = if (attempt.ssl) "SSL encryption" else "no encryption"
        return when (decision) {
            is Decision.Authenticate -> "line ${decision.line}: authenticate with ${decision.method}"
            is Decision.Rejected ->
                if (attempt.replication) "FATAL:  pg_hba.conf rejects replication connection for $host, $enc"
                else "FATAL:  pg_hba.conf rejects connection for $host, database \"${attempt.database}\", $enc"
            Decision.NoEntry ->
                if (attempt.replication) "FATAL:  no pg_hba.conf entry for replication connection from $host, $enc"
                else "FATAL:  no pg_hba.conf entry for $host, database \"${attempt.database}\", $enc"
        }
    }
}
