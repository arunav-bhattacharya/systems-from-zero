// Lesson nosql-11, lab part 3: the ring around one account.
// Parameters: $accountId (where to start), $skipKinds (a list of Device kinds not to walk through)
// One step is account -USES-> identifier <-USES- account. Return every account 1 to 3 steps away
// (never the start itself), with the fewest steps that reach it.
// Columns: account, steps. Order: by steps, then account.
MATCH (start:Account {id: $accountId})                       // an index seek, once the constraint exists
      ((:Account)-[:USES]->(x WHERE NOT coalesce(x.kind, '') IN $skipKinds)<-[:USES]-(:Account)){1,3}
      (other:Account)
WHERE other <> start
RETURN other.id AS account, min(size(x)) AS steps            // x is a list: one identifier per step
ORDER BY steps, account
