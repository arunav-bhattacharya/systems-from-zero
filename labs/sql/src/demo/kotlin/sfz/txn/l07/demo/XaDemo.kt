package sfz.txn.l07.demo

import org.postgresql.xa.PGXADataSource
import javax.transaction.xa.XAResource
import javax.transaction.xa.Xid

/**
 * Lesson txn-07: what a JTA transaction manager (Narayana in Quarkus, for example) does with two
 * XA resources, done by hand with pgJDBC's XA data source.
 *
 * Phase 1 runs on both databases and prepares them, then the "coordinator" drops its connections
 * without committing. A second pass plays the restarted transaction manager: it asks each
 * resource which branches are in doubt (XAResource.recover) and commits them.
 *
 * It needs the databases from the lesson's Try-its: start env/postgres.yml, switch on prepared
 * transactions and create `wallets` and `payouts`. Run from the labs folder:
 *   ./gradlew :sql:demo -Pmain=sfz.txn.l07.demo.XaDemoKt
 * Set SFZ_PG_URL (default jdbc:postgresql://localhost:5432/) to point it somewhere else.
 */

/** An XA transaction id: a format id, a global transaction id and a branch qualifier. */
private class TxXid(private val gtrid: String, private val bqual: String) : Xid {
    override fun getFormatId(): Int = 1001
    override fun getGlobalTransactionId(): ByteArray = gtrid.toByteArray()
    override fun getBranchQualifier(): ByteArray = bqual.toByteArray()
}

private val base = System.getenv("SFZ_PG_URL") ?: "jdbc:postgresql://localhost:5432/"

private fun source(db: String) = PGXADataSource().apply {
    setURL(base + db)
    user = "sfz"
    password = "sfz"
}

fun main() {
    val branches = listOf(
        "wallets" to "UPDATE wallets SET balance_minor = balance_minor - 1500 WHERE id = 'w-17'",
        "payouts" to "UPDATE merchant_balances SET balance_minor = balance_minor + 1500 WHERE id = 'm-cafe'",
    )

    println("== phase 1: start, work, end and prepare each branch of txf-7")
    for ((db, sql) in branches) {
        val xa = source(db).xaConnection
        val resource = xa.xaResource
        val xid = TxXid("txf-7", db)                    // same global id, one branch per database
        resource.start(xid, XAResource.TMNOFLAGS)       // associate the connection with the branch
        xa.connection.createStatement().use { it.executeUpdate(sql) }
        resource.end(xid, XAResource.TMSUCCESS)         // the work for this branch is done
        val vote = resource.prepare(xid)                // pgJDBC sends PREPARE TRANSACTION here
        println("%-8s prepare -> %s".format(db, if (vote == XAResource.XA_OK) "XA_OK, a yes vote" else "$vote"))
        xa.close()                                      // the coordinator dies before phase 2
    }

    println("== what PostgreSQL holds now")
    source("wallets").connection.use { c ->
        c.createStatement().executeQuery("SELECT gid, database FROM pg_prepared_xacts ORDER BY database").use { rs ->
            while (rs.next()) println("%-8s %s".format(rs.getString(2), rs.getString(1)))
        }
    }

    println("== recovery: a restarted transaction manager asks each resource what is in doubt")
    for ((db, _) in branches) {
        val xa = source(db).xaConnection
        val resource = xa.xaResource
        for (xid in resource.recover(XAResource.TMSTARTRSCAN or XAResource.TMENDRSCAN)) {
            val gtrid = String(xid.globalTransactionId)
            val bqual = String(xid.branchQualifier)
            println("%-8s in doubt: formatId %d, global id %s, branch %s".format(db, xid.formatId, gtrid, bqual))
            // a real transaction manager looks gtrid up in its own log; this one decided COMMIT
            resource.commit(xid, false)                 // COMMIT PREPARED
            println("%-8s commit -> done".format(db))
        }
        xa.close()
    }

    source("wallets").connection.use { c ->
        c.createStatement().executeQuery("SELECT balance_minor FROM wallets WHERE id = 'w-17'").use { rs ->
            rs.next(); println("w-17 is now ${rs.getLong(1)}")
        }
    }
}
