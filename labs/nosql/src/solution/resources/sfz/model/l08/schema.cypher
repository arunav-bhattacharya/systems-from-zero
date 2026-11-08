// Lesson model-08, lab part 1: give every query a fast way in.
// One statement that makes Account.id unique. The uniqueness constraint also builds an index on it,
// so a pattern that starts at (:Account {id: $accountId}) begins with an index seek, not a label scan.
CREATE CONSTRAINT account_id IF NOT EXISTS
FOR (a:Account) REQUIRE a.id IS UNIQUE
