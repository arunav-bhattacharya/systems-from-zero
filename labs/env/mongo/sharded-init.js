// Builds the cluster in env/mongo-sharded.yml. Run on the mongos; safe to run again and again.
// Each shard is a replica set, so a shard is added as "<set name>/<one member>".
const shards = [
  ["shard1", "shard1/shard1:27017"],
  ["shard2", "shard2/shard2:27017"],
];
const listed = () => db.adminCommand({ listShards: 1 }).shards.map((s) => s._id);
for (const [id, host] of shards) {
  if (!listed().includes(id)) sh.addShard(host);
}
if (listed().length !== shards.length) throw new Error("shards not added yet");
