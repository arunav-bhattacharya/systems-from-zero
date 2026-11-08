package sfz.txn.l08

import com.mongodb.ErrorCategory
import com.mongodb.MongoException
import com.mongodb.MongoWriteException
import com.mongodb.ReadConcern
import com.mongodb.TransactionOptions
import com.mongodb.WriteConcern
import com.mongodb.client.ClientSession
import com.mongodb.client.MongoClient
import com.mongodb.client.MongoCollection
import com.mongodb.client.MongoDatabase
import com.mongodb.client.model.Filters
import com.mongodb.client.model.Updates
import org.bson.Document

/** What [MongoTransfers.transfer] did. */
sealed interface TransferResult {
    /** Committed. [attempts] is how many times the whole transaction ran (1 if nothing got in the way). */
    data class Done(val attempts: Int) : TransferResult

    /** The source account didn't have the money. Nothing was written. */
    data object InsufficientFunds : TransferResult

    /** This transfer id is already in the ledger: an earlier attempt committed. Nothing was written. */
    data object AlreadyDone : TransferResult
}

/**
 * Transfers between account documents `{ _id: "A-1001", balanceMinor: 10000 }` in one MongoDB
 * multi-document transaction, with a ledger document per transfer `{ _id: transferId, ... }`.
 * Needs a replica set: a standalone server refuses transactions.
 */
class MongoTransfers(private val client: MongoClient, db: MongoDatabase) {
    val accounts: MongoCollection<Document> = db.getCollection("accounts")
    val ledger: MongoCollection<Document> = db.getCollection("ledger")

    /** Given: read from one snapshot, commit only once a majority has the writes. Set them on every transaction. */
    val options: TransactionOptions = TransactionOptions.builder()
        .readConcern(ReadConcern.SNAPSHOT)
        .writeConcern(WriteConcern.MAJORITY)
        .build()

    /**
     * Moves [amountMinor] from [from] to [to] as ONE transaction on a session from `client.startSession()`.
     * Pass the session as the first argument of every operation, or it runs outside the transaction.
     *
     * 1. Insert the ledger document `{ _id: transferId, from, to, amountMinor }` first. A duplicate key
     *    (`ErrorCategory.DUPLICATE_KEY`) means an earlier attempt committed: abort, return [TransferResult.AlreadyDone].
     * 2. Debit with ONE guarded update: filter `_id = from AND balanceMinor >= amountMinor`, `$inc` by minus
     *    the amount. Modified nothing? Abort and return [TransferResult.InsufficientFunds].
     * 3. Credit `to` with `$inc`.
     * 4. Commit. If the commit fails with the error label `UnknownTransactionCommitResult`, commit again.
     *
     * Any error with the label `TransientTransactionError` (a write conflict with another transaction,
     * a primary stepping down) means "run the whole thing again": abort, wait a moment ([backoff]),
     * and start a new transaction from step 1, up to [maxAttempts] attempts. Other errors: rethrow.
     */
    fun transfer(transferId: String, from: String, to: String, amountMinor: Long, maxAttempts: Int = 50): TransferResult {
        TODO("one session; loop: startTransaction(options), ledger insert, guarded debit, credit, commit; retry on TransientTransactionError")
    }


    /** Aborts the session's transaction if it still has one. Given. */
    fun abortQuietly(session: ClientSession) {
        if (session.hasActiveTransaction()) runCatching { session.abortTransaction() }
    }

    /** How long to wait before attempt [attempt] + 1: a little longer each time, with some jitter. Given. */
    fun backoff(attempt: Int): Long = minOf(10L * attempt, 100L) + (0..10).random()
}
