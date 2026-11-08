package sfz.cache.l01.demo;

import java.util.Arrays;
import java.util.Random;

/** How much of the traffic the most popular keys get under Zipf popularity, for four values of alpha. */
public class SkewDemo {
    public static void main(String[] args) {
        int n = 1_000_000;                                 // a million merchants
        System.out.println("alpha  top 0.1%  top 1%  top 10%   distinct keys in 1M requests  seen once");
        for (double alpha : new double[] {0.6, 0.8, 1.0, 1.2}) {
            double[] cdf = cdf(n, alpha);
            // draw a million requests and count how many different keys they touched
            Random random = new Random(42);
            int[] seen = new int[n];
            for (int i = 0; i < 1_000_000; i++) {
                int k = Arrays.binarySearch(cdf, random.nextDouble());
                seen[k >= 0 ? k : -k - 1]++;               // first cdf entry above the draw
            }
            int distinct = 0, once = 0;
            for (int c : seen) { if (c > 0) distinct++; if (c == 1) once++; }
            System.out.printf("%5.1f  %7.1f%%  %5.1f%%  %6.1f%%   %,28d  %8.0f%%%n", alpha,
                    100 * cdf[n / 1000 - 1], 100 * cdf[n / 100 - 1], 100 * cdf[n / 10 - 1],
                    distinct, 100.0 * once / distinct);
        }
    }

    /** cdf[k - 1] = share of requests for keys 1..k, with key k weighted 1 / k^alpha. */
    static double[] cdf(int n, double alpha) {
        double[] cdf = new double[n];
        double total = 0;
        for (int k = 1; k <= n; k++) total += Math.pow(k, -alpha);
        double running = 0;
        for (int k = 1; k <= n; k++) { running += Math.pow(k, -alpha) / total; cdf[k - 1] = running; }
        cdf[n - 1] = 1.0;
        return cdf;
    }
}
