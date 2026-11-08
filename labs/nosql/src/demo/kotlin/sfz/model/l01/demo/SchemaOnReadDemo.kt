package sfz.model.l01.demo

import org.bson.Document

/**
 * Schema-on-read: the store keeps whatever shape each record was written in,
 * and the code that reads carries the schema. Merchant records from three years of onboarding.
 */
fun main() {
    val stored = listOf(
        """{"_id": "M-0042", "name": "Northwind Bikes", "country": "FR"}""",                          // first version
        """{"_id": "M-0051", "legalName": "Volt Electronics SARL", "tradingName": "Volt", "country": "FR"}""", // name split in two
        """{"_id": "M-0063", "legalName": "Kools GmbH", "country": "DE", "vatId": "DE811907980"}""",     // German forms add a VAT id
        """{"_id": "M-0077", "Name": "Brightside Cafe", "country": "IE"}""",                           // an import job's typo
    ).map(Document::parse)                                   // a document store accepts all four as they are

    // the schema lives here, in the reader: every shape the data has ever had
    fun displayName(d: Document): String =
        d.getString("tradingName") ?: d.getString("legalName") ?: d.getString("name") ?: "<no name>"

    for (d in stored) {
        println("%-7s %-28s fields=%s".format(d.getString("_id"), displayName(d), d.keys.drop(1)))
    }
}
