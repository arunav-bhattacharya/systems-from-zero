// Lesson model-08, lab part 3: the ring around one account.
// Parameters: $accountId (where to start), $skipKinds (a list of Device kinds not to walk through)
// One step is account -USES-> identifier <-USES- account. Return every account 1 to 3 steps away
// (never the start itself), with the fewest steps that reach it.
// Columns: account, steps. Order: by steps, then account.
// Use a quantified path pattern: (start) ((...)-[:USES]->(x)<-[:USES]-(...)){1,3} (other).
// Replace the line below with your query.
RETURN 'TODO: walk the ring' AS todo
