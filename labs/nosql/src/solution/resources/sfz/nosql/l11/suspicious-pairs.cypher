// Lesson nosql-11, lab part 2: pairs of accounts that share at least $minShared devices or phones.
// Parameters: $minShared (an integer)
// Columns: first, second (account ids, first < second), shared (the identifier ids, sorted)
// Order: by first, then second.
MATCH (a:Account)-[:USES]->(x)<-[:USES]-(b:Account)
WHERE a.id < b.id                       // each pair once, not twice
WITH a, b, x ORDER BY x.id              // so collect() builds a sorted list
WITH a, b, collect(x.id) AS shared
WHERE size(shared) >= $minShared
RETURN a.id AS first, b.id AS second, shared
ORDER BY first, second
