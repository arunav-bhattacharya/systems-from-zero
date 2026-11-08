// Lesson nosql-15: helpers for the sharded-cluster Try-its in env/mongo-sharded.yml.
// Inside mongosh on the mongos: load("/sfz/nosql-15-payments.js")
//   payments(n, from)   n payment documents, pay-<from> to pay-<from + n - 1>, one minute apart
//   ledger(n, from)     n ledger entries of about 1 KB each, one second apart, in time order
//   onShard(coll)       how many documents of coll each shard owns, and how many old copies it still holds
//   moves(coll)         the chunk migrations the balancer committed for coll, oldest first
const start = new Date("2026-11-07T00:00:00Z").getTime();

globalThis.payments = function (n, from = 0) {
  const docs = [];
  for (let i = from; i < from + n; i++) {
    docs.push({
      _id: "pay-" + (100000 + i),
      accountId: "A-" + (1001 + (i % 500)),
      merchantId: i % 5 === 0 ? "M-0042" : "M-" + (1000 + (i % 400)),
      status: i % 7 === 3 ? "FAILED" : "SETTLED",
      amountMinor: 500 + ((i * 7919) % 9501),
      currency: "EUR",
      createdAt: new Date(start + i * 60000),
    });
  }
  return docs;
};

const pad = "x".repeat(900); // makes each ledger entry about 1 KB, so a few thousand fill a megabyte
globalThis.ledger = function (n, from = 0) {
  const docs = [];
  for (let i = from; i < from + n; i++) {
    docs.push({
      _id: "led-" + (100000 + i),
      accountId: "A-" + (1001 + (i % 500)),
      amountMinor: 500 + ((i * 7919) % 9501),
      createdAt: new Date(start + i * 1000),
      memo: pad,
    });
  }
  return docs;
};

// $shardedDataDistribution asks every shard. "owned" documents are in chunks the config servers
// assign to that shard; "orphaned" ones are copies left behind by a migration, deleted later.
globalThis.onShard = function (coll) {
  const out = {};
  const ns = db.getName() + "." + coll;
  db.getSiblingDB("admin").aggregate([{ $shardedDataDistribution: {} }, { $match: { ns } }]).forEach((d) =>
    d.shards.forEach((s) => (out[s.shardName] = { owned: s.numOwnedDocuments, orphaned: s.numOrphanedDocs })));
  return out;
};

// every committed migration is written to the config servers' changelog
globalThis.moves = function (coll) {
  const ns = db.getName() + "." + coll;
  const show = (k) => (k instanceof Date ? k.toISOString().slice(11, 19) : k && k._bsontype ? k._bsontype : String(k));
  return db.getSiblingDB("config").changelog.find({ what: "moveChunk.commit", ns }).sort({ time: 1 }).toArray()
    .map((c) => c.time.toISOString().slice(11, 19) + "  " + c.details.from + " -> " + c.details.to + "  createdAt " +
      show(Object.values(c.details.min)[0]) + " to " + show(Object.values(c.details.max)[0]));
};
print("loaded: payments(n, from), ledger(n, from), onShard(coll), moves(coll)");
