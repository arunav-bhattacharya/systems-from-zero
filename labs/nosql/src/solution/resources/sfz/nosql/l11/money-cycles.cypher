// Lesson nosql-11, lab part 4: money that goes round in a circle.
// Find chains of 3 to 6 transfers that end at the account where they started.
// Columns: cycle (the account ids in transfer order, starting AND ending at the cycle's smallest id),
//          movedMinor (the sum of the transfers' amountMinor)
// Each cycle once. Order: by cycle.
MATCH p = (a:Account)-[:TRANSFERRED_TO]->{3,6}(a)
WHERE all(n IN nodes(p) WHERE a.id <= n.id)                   // keep only the rotation that starts smallest
RETURN [n IN nodes(p) | n.id] AS cycle,
       reduce(total = 0, t IN relationships(p) | total + t.amountMinor) AS movedMinor
ORDER BY cycle
