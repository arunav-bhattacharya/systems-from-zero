// Lesson nosql-02: 1,000 payments for 50 accounts and 5 merchants, plus one account document.
// Inside mongosh: load("/sfz/nosql-02-payments.js")   (it starts from scratch each time)
db.payments.drop();
db.accounts.drop();

const start = new Date("2026-11-07T00:00:00Z").getTime();
const payments = [];
for (let i = 0; i < 1000; i++) {
  payments.push({
    _id: "pay-" + (81000 + i),
    accountId: "A-" + (1001 + (i % 50)),
    merchantId: "M-00" + (40 + (i % 5)),
    status: i % 7 === 3 ? "FAILED" : "SETTLED",
    amountMinor: 500 + ((i * 7919) % 9501),
    currency: "EUR",
    createdAt: new Date(start + i * 60000),
  });
}
db.payments.insertMany(payments);

// the account embeds what its screen shows: the owner, the currency, the last few payments
db.accounts.insertOne({ _id: "A-1001", customerId: "C-77", currency: "EUR", recentPayments: [] });
// cost(cursor): run explain and keep only what the lesson looks at
globalThis.cost = function (cursor) {
  const e = cursor.explain("executionStats");
  const stages = [];
  for (let s = e.queryPlanner.winningPlan; s; s = s.inputStage) stages.push(s.stage);
  return {
    plan: stages.join(" > "),
    returned: e.executionStats.nReturned,
    keysExamined: e.executionStats.totalKeysExamined,
    docsExamined: e.executionStats.totalDocsExamined,
  };
};
print("payments: " + db.payments.countDocuments() + ", accounts: " + db.accounts.countDocuments());
