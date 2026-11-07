package sfz.os.support

/**
 * Real output captured in the lab box (strace logs, jstack dumps, ps listings) lives in
 * src/test/resources/sfz/os/lNN/. Tests read it through here, so a missing file fails
 * with its name instead of a NullPointerException.
 */
object Captured {
    fun text(path: String): String {
        val url = Captured::class.java.getResource(path)
            ?: error("test resource $path is missing (expected under src/test/resources)")
        return url.readText()
    }

    fun lines(path: String): List<String> = text(path).lines().filter { it.isNotEmpty() }
}
