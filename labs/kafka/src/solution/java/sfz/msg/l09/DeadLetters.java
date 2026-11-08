package sfz.msg.l09;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.header.Header;
import org.apache.kafka.common.header.Headers;

import java.nio.charset.StandardCharsets;

/**
 * Builds dead-letter records: a copy of a record that could not be processed, plus headers that say where it came
 * from and why it failed, so someone can find it, fix the cause and replay it.
 */
public final class DeadLetters {
    public static final String ORIGINAL_TOPIC = "dlt.original.topic";
    public static final String ORIGINAL_PARTITION = "dlt.original.partition";
    public static final String ORIGINAL_OFFSET = "dlt.original.offset";
    public static final String EXCEPTION_CLASS = "dlt.exception.class";
    public static final String EXCEPTION_MESSAGE = "dlt.exception.message";

    private DeadLetters() {
    }

    /** The dead-letter topic of a topic: {@code payments} becomes {@code payments.DLT}. */
    public static String topicFor(String topic) {
        return topic + ".DLT";
    }

    /**
     * The record to write to {@code dltTopic} for {@code failed}, which failed with {@code error}.
     *
     * <ul>
     *   <li>Same key and value as the original. Leave the partition unset, so the producer picks it from the key
     *       and all of an account's dead letters stay in one partition, in order.</li>
     *   <li>Copy the original's headers, then add the five {@code dlt.*} headers above as UTF-8 strings:
     *       topic, partition and offset of the original, the exception's class name ({@code getName()}) and its
     *       message ({@code ""} when the message is null).</li>
     * </ul>
     */
    public static ProducerRecord<String, String> deadLetter(ConsumerRecord<String, String> failed, Throwable error, String dltTopic) {
        var record = new ProducerRecord<>(dltTopic, null, failed.key(), failed.value());
        for (Header h : failed.headers()) record.headers().add(h);              // keep what the producer sent
        record.headers()
                .add(ORIGINAL_TOPIC, utf8(failed.topic()))                      // where it came from ...
                .add(ORIGINAL_PARTITION, utf8(Integer.toString(failed.partition())))
                .add(ORIGINAL_OFFSET, utf8(Long.toString(failed.offset())))
                .add(EXCEPTION_CLASS, utf8(error.getClass().getName()))         // ... and why it failed
                .add(EXCEPTION_MESSAGE, utf8(error.getMessage() == null ? "" : error.getMessage()));
        return record;
    }

    /** The last header called {@code name} as a UTF-8 string, or null if there is none. */
    public static String header(Headers headers, String name) {
        Header h = headers.lastHeader(name);
        return h == null ? null : new String(h.value(), StandardCharsets.UTF_8);
    }

    private static byte[] utf8(String s) {
        return s.getBytes(StandardCharsets.UTF_8);
    }
}
