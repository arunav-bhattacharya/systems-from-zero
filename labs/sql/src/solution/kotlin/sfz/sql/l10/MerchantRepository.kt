package sfz.sql.l10

import java.sql.Connection

/** One row of merchants. */
data class Merchant(val merchantId: Long, val name: String, val mcc: String, val countryCode: String)

/**
 * Lesson sql-10, exercise 1 of 5: a repository that cannot be injected. Reference answer.
 *
 * The SQL text is a constant with `?` placeholders. pgJDBC sends it in a Parse message and the
 * values in a separate Bind message, so the server has finished parsing the SQL before it sees
 * a single value: a quote in a name is just a character.
 */
class MerchantRepository(private val conn: Connection) {

    fun create(name: String, mcc: String, countryCode: String): Long =
        // naming the key column works on every driver; RETURN_GENERATED_KEYS makes pgJDBC append
        // RETURNING * (every column) and makes Oracle's driver return the ROWID instead of the id
        conn.prepareStatement(
            "INSERT INTO merchants (name, mcc, country_code) VALUES (?, ?, ?)",
            arrayOf("merchant_id"),
        ).use { ps ->
            ps.setString(1, name)
            ps.setString(2, mcc)
            ps.setString(3, countryCode)
            ps.executeUpdate()
            ps.generatedKeys.use { keys ->
                keys.next()
                keys.getLong("merchant_id")
            }
        }

    fun findByName(name: String): List<Merchant> =
        conn.prepareStatement(
            "SELECT merchant_id, name, mcc, country_code FROM merchants WHERE name = ? ORDER BY merchant_id",
        ).use { ps ->
            ps.setString(1, name)                                  // a value, never SQL
            ps.executeQuery().use { rs ->
                buildList {
                    while (rs.next()) add(Merchant(rs.getLong(1), rs.getString(2), rs.getString(3), rs.getString(4)))
                }
            }
        }
}
