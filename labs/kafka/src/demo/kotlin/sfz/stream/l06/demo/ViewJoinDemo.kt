package sfz.stream.l06.demo

import org.apache.kafka.common.serialization.Serdes
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import org.apache.kafka.streams.StreamsBuilder
import org.apache.kafka.streams.kstream.Consumed
import org.apache.kafka.streams.kstream.Produced
import org.apache.kafka.streams.kstream.ValueJoiner
import java.util.function.Function

/**
 * A table-table join kept up to date as either side changes: cards (card id -> account id) joined with account
 * tiers (account id -> tier) on the card's account, a foreign-key join. The result is a table, card -> tier, and the
 * output topic is its changelog.
 */
fun main() {
    val builder = StreamsBuilder()
    val consumed = Consumed.with(Serdes.String(), Serdes.String())
    val tiers = builder.table("account-tiers", consumed)
    builder.table("cards", consumed)
        .join(tiers, Function<String, String> { account -> account },                 // which tiers row: the card's account
            ValueJoiner<String, String, String> { account, tier -> "$account $tier" })
        .toStream()
        .to("card-tiers", Produced.with(Serdes.String(), Serdes.String()))

    drive(builder.build(), "view-join-demo") { driver ->
        val cards = driver.createInputTopic("cards", StringSerializer(), StringSerializer())
        val accountTiers = driver.createInputTopic("account-tiers", StringSerializer(), StringSerializer())
        val view = driver.createOutputTopic("card-tiers", StringDeserializer(), StringDeserializer())
        fun step(what: String, change: () -> Unit) {
            change()
            val out = view.readKeyValuesToList().joinToString { "${it.key} -> ${it.value ?: "(deleted)"}" }
            println("%-34s view changes: %s".format(what, out.ifEmpty { "none" }))
        }
        step("tiers: acct-1 silver, acct-2 gold") { accountTiers.pipeInput("acct-1", "silver"); accountTiers.pipeInput("acct-2", "gold") }
        step("cards: card-1, card-2 on acct-1") { cards.pipeInput("card-1", "acct-1"); cards.pipeInput("card-2", "acct-1") }
        step("card: card-3 on acct-2") { cards.pipeInput("card-3", "acct-2") }
        step("tier: acct-1 becomes gold") { accountTiers.pipeInput("acct-1", "gold") }
        step("card: card-3 moves to acct-1") { cards.pipeInput("card-3", "acct-1") }
        step("card: card-2 is deleted") { cards.pipeInput("card-2", null as String?) }
        step("tier: acct-1 is deleted") { accountTiers.pipeInput("acct-1", null as String?) }
    }
}
