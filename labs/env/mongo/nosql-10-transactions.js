// Lesson txn-08: two transactions collide on one document, then an outside write waits and a
// transaction outlives its time limit. Run against env/mongo.yml (a one-member replica set):
//   docker compose -f env/mongo.yml exec mongo mongosh sfz --quiet /sfz/nosql-10-transactions.js
db.accounts.drop()
db.accounts.insertMany([{ _id: "A-1001", balanceMinor: 10000 }, { _id: "A-2002", balanceMinor: 5000 }])

// two sessions, two transactions, each with its own snapshot
const opts = { readConcern: { level: "snapshot" }, writeConcern: { w: "majority" } }
const s1 = db.getMongo().startSession(), a1 = s1.getDatabase("sfz").accounts
const s2 = db.getMongo().startSession(), a2 = s2.getDatabase("sfz").accounts
s1.startTransaction(opts)
s2.startTransaction(opts)
print("tx1 reads A-1001:", a1.findOne({ _id: "A-1001" }).balanceMinor)
print("tx2 reads A-1001:", a2.findOne({ _id: "A-1001" }).balanceMinor)

// tx1 debits 30.00 first; tx2 then tries to debit 80.00 from the same document
print("tx1 debit 3000:", a1.updateOne({ _id: "A-1001", balanceMinor: { $gte: 3000 } }, { $inc: { balanceMinor: -3000 } }).modifiedCount)
try {
  a2.updateOne({ _id: "A-1001", balanceMinor: { $gte: 8000 } }, { $inc: { balanceMinor: -8000 } })
} catch (e) {
  print("tx2 debit 8000:", e.codeName, JSON.stringify(e.errorLabels))
}
print("outside, before tx1 commits:", db.accounts.findOne({ _id: "A-1001" }).balanceMinor)
a1.updateOne({ _id: "A-2002" }, { $inc: { balanceMinor: 3000 } })
s1.commitTransaction()
print("outside, after tx1 commits:", db.accounts.findOne({ _id: "A-1001" }).balanceMinor)

// the retry is a NEW transaction with a new snapshot: it sees 7000, and its condition is false
s2.abortTransaction()
s2.startTransaction(opts)
print("tx2 retry reads A-1001:", a2.findOne({ _id: "A-1001" }).balanceMinor)
print("tx2 retry debit 8000:", a2.updateOne({ _id: "A-1001", balanceMinor: { $gte: 8000 } }, { $inc: { balanceMinor: -8000 } }).modifiedCount)
s2.abortTransaction()

// a plain write, outside any transaction, to a document an open transaction has changed: it waits
s1.startTransaction(opts)
a1.updateOne({ _id: "A-1001" }, { $inc: { balanceMinor: -100 } })
let t = Date.now()
try {
  db.runCommand({ update: "accounts", updates: [{ q: { _id: "A-1001" }, u: { $inc: { balanceMinor: -1 } } }], maxTimeMS: 2000 })
} catch (e) { print("outside write:", e.codeName, "after", Date.now() - t, "ms") }
s1.abortTransaction()

// the time limit: 60 seconds by default; set it to 5 to watch it, then put it back
print("transactionLifetimeLimitSeconds:", db.adminCommand({ getParameter: 1, transactionLifetimeLimitSeconds: 1 }).transactionLifetimeLimitSeconds)
db.adminCommand({ setParameter: 1, transactionLifetimeLimitSeconds: 5 })
s1.startTransaction(opts)
a1.updateOne({ _id: "A-1001" }, { $inc: { balanceMinor: -100 } })
sleep(12000) // a slow call to the card issuer, say
try { s1.commitTransaction() } catch (e) { print("commit after 12 s:", e.codeName) }
db.adminCommand({ setParameter: 1, transactionLifetimeLimitSeconds: 60 })
print("A-1001 at the end:", db.accounts.findOne({ _id: "A-1001" }).balanceMinor)
