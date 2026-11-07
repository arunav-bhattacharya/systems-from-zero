package sfz.redis.l05;

/**
 * A merchant profile, the kind of row a payment service reads on every authorization. Done for you.
 *
 * <p>In Redis it is stored as one string, {@code id|name|country|mcc}, for example
 * {@code m-17|Fietsen Utrecht|NL|5940}. Names never contain {@code |} in this lab.
 */
public record Merchant(String id, String name, String country, int mcc) {

    /** The string stored in Redis. */
    public String encode() {
        return id + "|" + name + "|" + country + "|" + mcc;
    }

    /** The inverse of {@link #encode()}. */
    public static Merchant decode(String s) {
        String[] f = s.split("\\|", -1);
        if (f.length != 4) throw new IllegalArgumentException("not an encoded merchant: " + s);
        return new Merchant(f[0], f[1], f[2], Integer.parseInt(f[3]));
    }
}
