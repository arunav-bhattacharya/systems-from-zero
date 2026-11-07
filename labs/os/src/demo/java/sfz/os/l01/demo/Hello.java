package sfz.os.l01.demo;

/**
 * The smallest JVM program: print one line and exit.
 *
 * <p>Run it under strace in the lab box to count the system calls the JVM makes
 * before and after this one line. Java (not Kotlin) because the lab box has a JDK
 * and no Kotlin compiler.
 */
public class Hello {
    public static void main(String[] args) {
        System.out.println("hello from the JVM");
    }
}
