package sfz.cache.l10.demo;

import redis.clients.jedis.Connection;
import redis.clients.jedis.HostAndPort;
import redis.clients.jedis.RedisClient;
import redis.clients.jedis.RedisClusterClient;
import redis.clients.jedis.exceptions.JedisDataException;
import redis.clients.jedis.exceptions.JedisMovedDataException;
import redis.clients.jedis.util.JedisClusterCRC16;

import java.util.List;
import java.util.Set;

/**
 * Talks to the three-node cluster from env/redis-cluster.yml: first with a plain client that knows only node 1,
 * then with Jedis's cluster client, which loads the slot table and sends each key to its owner.
 * Start the cluster first: docker compose -f env/redis-cluster.yml up -d --wait
 */
public class ClusterDemo {
    public static void main(String[] args) {
        // a plain client: one node, no slot table
        try (RedisClient node1 = RedisClient.builder().hostAndPort("127.0.0.1", 7001).build()) {
            try {
                node1.get("payment:42");
            } catch (JedisMovedDataException e) {
                System.out.println("plain client on 7001, GET payment:42 -> MOVED " + e.getSlot() + " " + e.getTargetNode());
            }
        }

        // a cluster client: give it one node, it asks for the whole slot table (CLUSTER SLOTS) and connects to every node
        try (RedisClusterClient cluster = RedisClusterClient.builder()
                .nodes(Set.of(new HostAndPort("127.0.0.1", 7001)))
                .build()) {
            for (String key : List.of("payment:42", "payment:43", "{merchant:7}:payments", "{merchant:7}:refunds")) {
                cluster.set(key, "approved");
                int slot = JedisClusterCRC16.getSlot(key);
                try (Connection owner = cluster.getConnectionFromSlot(slot)) {   // borrowed from that node's pool
                    System.out.printf("%-22s slot %5d  on %s%n", key, slot, owner.getHostAndPort());
                }
            }
            // Jedis 8 splits a cross-slot MSET into one MSET per slot and sends each to its node:
            // it succeeds, but the halves are separate commands, not one atomic step
            System.out.println("MSET payment:42 payment:43 -> " + cluster.mset("payment:42", "settled", "payment:43", "settled"));
            // the same command sent as raw MSET to one node is refused by the server
            try (RedisClient node2 = RedisClient.builder().hostAndPort("127.0.0.1", 7002).build()) {
                node2.mset("payment:42", "x", "payment:43", "y");
            } catch (JedisDataException e) {
                System.out.println("raw MSET on one node    -> " + e.getMessage());
            }
            System.out.println("MSET with one hash tag  -> "
                    + cluster.mset("{merchant:7}:payments", "10", "{merchant:7}:refunds", "2"));
        }
    }
}
