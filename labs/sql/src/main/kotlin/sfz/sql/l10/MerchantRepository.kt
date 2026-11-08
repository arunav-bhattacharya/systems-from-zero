package sfz.sql.l10

import java.sql.Connection

/** One row of merchants. */
data class Merchant(val merchantId: Long, val name: String, val mcc: String, val countryCode: String)

/**
 * Lesson sql-10, exercise 1 of 5: a repository that cannot be injected (a trap).
 *
 * Both methods below build their SQL by pasting the caller's strings into it. They work for
 * "Northwind Grocers". A name with an apostrophe, such as "Mama's Kitchen", breaks the SQL, and a
 * name written by an attacker becomes SQL that runs: `' OR '1'='1` finds every merchant, and a
 * name that closes the VALUES list can append a statement of its own.
 *
 * Rewrite both with a PreparedStatement and `?` placeholders, so the server receives the values
 * separately from the SQL text and stores or compares them as data. Keep the signatures.
 * - [create] inserts a merchant and returns the merchant_id the database generated. Use
 *   `conn.prepareStatement(sql, arrayOf("merchant_id"))` and read `generatedKeys`, or
 *   `INSERT ... RETURNING merchant_id` with executeQuery.
 * - [findByName] returns the merchants whose name is exactly [name], by merchant_id.
 * Close every statement and result set (`use { }`). Don't commit: the caller owns the transaction.
 *
 * Check it: ./gradlew :sql:test --tests 'sfz.sql.l10.*'   (from the labs folder)
 */
class MerchantRepository(private val conn: Connection) {

    fun create(name: String, mcc: String, countryCode: String): Long =
        conn.createStatement().use { st ->
            st.executeQuery(
                "INSERT INTO merchants (name, mcc, country_code) " +
                    "VALUES ('$name', '$mcc', '$countryCode') RETURNING merchant_id",
            ).use { rs ->
                rs.next()
                rs.getLong(1)
            }
        }

    fun findByName(name: String): List<Merchant> =
        conn.createStatement().use { st ->
            st.executeQuery(
                "SELECT merchant_id, name, mcc, country_code FROM merchants " +
                    "WHERE name = '$name' ORDER BY merchant_id",
            ).use { rs ->
                buildList {
                    while (rs.next()) add(Merchant(rs.getLong(1), rs.getString(2), rs.getString(3), rs.getString(4)))
                }
            }
        }
}
