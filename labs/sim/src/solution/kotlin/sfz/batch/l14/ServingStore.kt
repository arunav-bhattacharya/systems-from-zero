package sfz.batch.l14

import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardCopyOption

/**
 * Given: a read-only store file, the shape of an SSTable: one `key<TAB>value` line per entry, keys
 * in strictly increasing order. Opening it loads the keys and values into arrays; [get] is a binary
 * search. Nothing ever changes the file after it is written.
 */
class SortedFile private constructor(private val keys: Array<String>, private val values: Array<String>) {
    val size: Int get() = keys.size

    fun get(key: String): String? {
        val i = keys.binarySearch(key)
        return if (i >= 0) values[i] else null
    }

    companion object {
        fun open(path: Path): SortedFile {
            val lines = Files.readAllLines(path)
            val keys = Array(lines.size) { lines[it].substringBefore('\t') }
            val values = Array(lines.size) { lines[it].substringAfter('\t') }
            for (i in 1 until keys.size) check(keys[i - 1] < keys[i]) { "$path is not sorted at line ${i + 1}" }
            return SortedFile(keys, values)
        }
    }
}

/**
 * Lesson batch-14: a read-only key-value store that a batch job rebuilds and swaps in whole.
 *
 * Under [root], every build is a new folder `v1`, `v2`, ... holding one file, `data`. The file
 * `CURRENT` holds the name of the version that readers use. Nothing in a version folder changes
 * after its build; the only thing that ever changes is `CURRENT`.
 */
class ServingStore(val root: Path) {
    init {
        Files.createDirectories(root)
    }

    /**
     * Exercise 2. Writes [entries] as a new version and returns its name: `v1` for the first build,
     * then one more than the highest version folder already under [root]. Sort the entries by key
     * and write them as `key<TAB>value` lines to `<version>/data`. Refuse a duplicate key with
     * [IllegalArgumentException], the way RocksDB's SstFileWriter refuses keys out of order, and
     * check it before you create anything. Never touch `CURRENT` or any other version.
     */
    fun build(entries: List<Pair<String, String>>): String {
        val sorted = entries.sortedBy { it.first }
        for (i in 1 until sorted.size) {
            require(sorted[i - 1].first != sorted[i].first) { "duplicate key ${sorted[i].first}" }
        }
        val taken = Files.list(root).use { s -> s.toList() }.map { it.fileName.toString() }
            .filter { it.matches(Regex("v\\d+")) }.map { it.drop(1).toInt() }
        val version = "v${(taken.maxOrNull() ?: 0) + 1}"
        val dir = Files.createDirectories(root.resolve(version))
        // a new folder nobody reads yet: a crash here leaves garbage, never a half-written live store
        Files.write(dir.resolve("data"), sorted.map { "${it.first}\t${it.second}" })
        return version
    }

    /**
     * Exercise 3. Makes [version] the live one in one atomic step: write its name to a temporary
     * file next to `CURRENT`, then move that file over `CURRENT` with
     * [StandardCopyOption.ATOMIC_MOVE]. A reader then sees the old name or the new one, never a
     * missing or half-written file. Publishing an older version is how you roll back.
     */
    fun publish(version: String) {
        require(Files.isRegularFile(root.resolve(version).resolve("data"))) { "no such version: $version" }
        val tmp = Files.createTempFile(root, "CURRENT", ".tmp")
        Files.writeString(tmp, version)
        // rename(2) under the hood: the pointer flips from the old name to the new one at once
        Files.move(tmp, root.resolve("CURRENT"), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
    }

    /** Exercise 3. The name in `CURRENT`, or null before the first publish. */
    fun current(): String? {
        val f = root.resolve("CURRENT")
        return if (Files.exists(f)) Files.readString(f).trim() else null
    }

    /** Exercise 3. Opens the live version: read `CURRENT` once, then open that version's `data`. */
    fun open(): SortedFile {
        val version = checkNotNull(current()) { "nothing published yet" }
        return SortedFile.open(root.resolve(version).resolve("data"))
    }
}
