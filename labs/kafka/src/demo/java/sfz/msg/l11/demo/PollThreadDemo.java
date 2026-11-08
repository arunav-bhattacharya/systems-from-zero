package sfz.msg.l11.demo;

import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.errors.WakeupException;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;

/**
 * The Java shape of the Kotlin Flow wrapper: one thread owns the consumer and hands records to a worker through a
 * small queue; when the worker has had enough, wakeup() ends a poll that would otherwise block for 10 seconds.
 */
public class PollThreadDemo {
    public static void main(String[] args) throws Exception {
        String bootstrap = "localhost:9092";
        TopicPartition tp = new TopicPartition("notifications-" + System.currentTimeMillis() % 100_000, 0);
        try (var admin = Admin.create(Map.<String, Object>of("bootstrap.servers", bootstrap))) {
            admin.createTopics(List.of(new NewTopic(tp.topic(), 1, (short) 1))).all().get();
        }
        try (var p = new KafkaProducer<>(Map.<String, Object>of("bootstrap.servers", bootstrap), new StringSerializer(), new StringSerializer())) {
            for (int i = 0; i < 5; i++) p.send(new ProducerRecord<>(tp.topic(), 0, "acct-" + i, "notify-" + i)).get();
        }
        var consumer = new KafkaConsumer<>(Map.<String, Object>of("bootstrap.servers", bootstrap), new StringDeserializer(), new StringDeserializer());
        BlockingQueue<ConsumerRecord<String, String>> handoff = new ArrayBlockingQueue<>(16);   // small: a slow worker slows polling

        Thread pollThread = new Thread(() -> {
            consumer.assign(List.of(tp));                              // every consumer call on this one thread
            consumer.seekToBeginning(List.of(tp));
            try {
                while (true) {
                    ConsumerRecords<String, String> batch = consumer.poll(Duration.ofSeconds(10));
                    if (!batch.isEmpty()) System.out.println("poll returned " + batch.count() + " records on " + Thread.currentThread().getName());
                    for (ConsumerRecord<String, String> r : batch) handoff.put(r);
                }
            } catch (WakeupException e) {
                System.out.println("poll on " + Thread.currentThread().getName() + " threw WakeupException: the worker is done");
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } finally {
                consumer.close();
                System.out.println("consumer closed on " + Thread.currentThread().getName());
            }
        }, "kafka-poll");
        pollThread.start();

        long lastRecordAt = 0;
        for (int i = 0; i < 5; i++) {
            ConsumerRecord<String, String> r = handoff.poll(30, TimeUnit.SECONDS);
            System.out.println("worker got offset " + r.offset() + " on " + Thread.currentThread().getName());
            lastRecordAt = System.nanoTime();
        }
        consumer.wakeup();                                             // the one call another thread may make
        pollThread.join();
        System.out.printf("the poll thread ended %.0f ms after the fifth record, although poll's timeout is 10 s%n", (System.nanoTime() - lastRecordAt) / 1e6);
    }
}
