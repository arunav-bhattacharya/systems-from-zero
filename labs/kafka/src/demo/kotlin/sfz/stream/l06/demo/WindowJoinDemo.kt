package sfz.stream.l06.demo

import org.apache.kafka.common.serialization.Serdes
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import org.apache.kafka.streams.StreamsBuilder
import org.apache.kafka.streams.kstream.Consumed
import org.apache.kafka.streams.kstream.JoinWindows
import org.apache.kafka.streams.kstream.Produced
import org.apache.kafka.streams.kstream.StreamJoined
import org.apache.kafka.streams.kstream.ValueJoiner
import java.time.Duration

/**
 * A stream-stream join: each card authorization with its capture, if the capture comes within 10 minutes of it
 * (either side may arrive first), with 1 minute of grace for late records. A left join, so an authorization with
 * no capture comes out too, once its window has closed.
 */
fun main() {
    val builder = StreamsBuilder()
    val captures = builder.stream("captures", Consumed.with(Serdes.String(), Serdes.String()))
    builder.stream("authorizations", Consumed.with(Serdes.String(), Serdes.String()))
        .leftJoin(
            captures,
            ValueJoiner<String, String?, String> { auth, capture -> if (capture == null) "$auth NOT CAPTURED" else "$auth captured $capture" },
            JoinWindows.ofTimeDifferenceAndGrace(Duration.ofMinutes(10), Duration.ofMinutes(1)),
            StreamJoined.with(Serdes.String(), Serdes.String(), Serdes.String()),
        )
        .to("auth-outcomes", Produced.with(Serdes.String(), Serdes.String()))

    drive(builder.build(), "window-join-demo") { driver ->
        val auths = driver.createInputTopic("authorizations", StringSerializer(), StringSerializer())
        val caps = driver.createInputTopic("captures", StringSerializer(), StringSerializer())
        val out = driver.createOutputTopic("auth-outcomes", StringDeserializer(), StringDeserializer())
        println("join state: " + driver.allStateStores.keys.sorted())
        val arrivals = listOf(
            Triple("auth", "p-1", "10:00"), Triple("auth", "p-2", "10:01"), Triple("capture", "p-1", "10:04"),
            Triple("capture", "p-3", "10:05"), Triple("auth", "p-3", "10:03"), Triple("auth", "p-4", "10:20"),
            Triple("capture", "p-4", "10:22"),
        )
        for ((i, a) in arrivals.withIndex()) {
            val (kind, payment, time) = a
            if (kind == "auth") auths.pipeInput(payment, "auth@$time", at(time)) else caps.pipeInput(payment, "@$time", at(time))
            val emitted = out.readKeyValuesToList().joinToString { "${it.key}: ${it.value}" }
            println("%d. %-7s %s at %s  ->  %s".format(i + 1, kind, payment, time, emitted.ifEmpty { "(nothing yet)" }))
        }
    }
}
