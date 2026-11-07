package sfz.redis.l05;

/** The system of record for merchants: in production an Oracle table behind a 120 ms query. Done for you. */
public interface MerchantRepository {

    /** The merchant with this id, or null if there is none. Slow: every call is a database round trip. */
    Merchant find(String id);
}
