package sfz.batch.l02

import java.io.BufferedReader
import java.io.Closeable
import java.nio.file.Files
import java.nio.file.Path
import java.util.PriorityQueue

/**
 * How many merge passes turn [runs] sorted runs into one, when each merge reads at most [fanIn] runs.
 * Each pass turns r runs into ceil(r / fanIn). 100 runs with a fan-in of 16 take 2 passes
 * (100 -> 7 -> 1); with 128 they take 1. Zero or one run needs no merging at all.
 */
fun mergePasses(runs: Int, fanIn: Int): Int {
    require(runs >= 0 && fanIn >= 2)
    TODO("while more than one run is left: runs = ceil(runs / fanIn) and count a pass")
}

/** Finished. One open run file, read one line at a time. Close it when you are done. */
class RunReader(private val reader: BufferedReader, private val onClose: () -> Unit) : Closeable {
    /** The next line of the run, or null at its end. */
    fun next(): String? = reader.readLine()

    override fun close() {
        reader.close()
        onClose()
    }
}

/**
 * Finished. The scratch folder of one sort, like the temporary files GNU sort writes to `-T` or
 * `$TMPDIR`. It writes and opens run files and counts what the sort did with them.
 */
class RunStore(val dir: Path) {
    /** Every run file written: the first runs and every merged run. */
    var runsWritten = 0
        private set

    /** Lines written to disk, summed over all runs: the sort's I/O. */
    var linesWritten = 0L
        private set

    /** How many runs are open right now, and the most that were ever open at once. */
    var openNow = 0
        private set
    var maxOpenAtOnce = 0
        private set

    init {
        Files.createDirectories(dir)
    }

    /** Writes [lines] (in the order given, one per line) to a new run file and returns its path. */
    fun write(lines: Sequence<String>): Path {
        val file = dir.resolve("run-%05d.txt".format(runsWritten++))
        Files.newBufferedWriter(file).use { w ->
            for (line in lines) {
                w.write(line)
                w.newLine()
                linesWritten++
            }
        }
        return file
    }

    /** Opens a run for reading. */
    fun open(run: Path): RunReader {
        openNow++
        maxOpenAtOnce = maxOf(maxOpenAtOnce, openNow)
        return RunReader(Files.newBufferedReader(run)) { openNow-- }
    }

    fun delete(run: Path) = Files.delete(run)

    /** The run files still on disk. */
    fun files(): List<Path> = Files.list(dir).use { s -> s.sorted().toList() }
}

/** What a sort did: the one sorted run it left (null for empty input), the runs it started with, and its merge passes. */
data class SortResult(val output: Path?, val runs: Int, val mergePasses: Int)

/**
 * An external merge sort of lines, the way GNU sort handles input bigger than its buffer.
 * At most [runSize] lines are in memory while it builds runs, and a merge reads at most [fanIn]
 * runs at once (GNU sort's `--batch-size`, 16 by default).
 */
class ExternalSorter(val runSize: Int, val fanIn: Int, val store: RunStore) {
    init {
        require(runSize >= 1) { "runSize must be at least 1" }
        require(fanIn >= 2) { "a merge needs at least 2 inputs" }
    }

    /**
     * Phase 1, run generation: read [keys] [runSize] at a time, sort each batch in memory, and write
     * each sorted batch as one run with [RunStore.write]. Returns the runs in the order written.
     */
    fun writeRuns(keys: Sequence<String>): List<Path> {
        TODO("take runSize keys at a time, sort them, store.write each sorted batch")
    }

    /**
     * One merge: a k-way merge of up to [fanIn] sorted [runs] into one new sorted run. Open every
     * input once, all at the same time, keep the current line of each in a priority queue, and
     * repeatedly write the smallest and replace it with the next line from the same run. Then close
     * and delete the inputs. Memory: one line per input, whatever the runs' sizes.
     */
    fun mergeGroup(runs: List<Path>): Path {
        require(runs.size in 1..fanIn) { "a merge reads 1 to $fanIn runs, got ${runs.size}" }
        TODO("open every run with store.open, merge with a PriorityQueue of (line, reader), store.write the result, close and delete the inputs")
    }

    /**
     * Finished. Phase 1 writes the runs; then each merge pass merges them in groups of [fanIn] until
     * one run is left. A group of one (the leftover at the end of a pass) moves on unchanged.
     */
    fun sort(keys: Sequence<String>): SortResult {
        var runs = writeRuns(keys)
        val initialRuns = runs.size
        var passes = 0
        while (runs.size > 1) {
            runs = runs.chunked(fanIn).map { group -> if (group.size == 1) group[0] else mergeGroup(group) }
            passes++
        }
        return SortResult(runs.singleOrNull(), initialRuns, passes)
    }
}

/**
 * Finished. `sort | uniq -c` out of core: sort the keys with [sorter], then count runs of equal
 * neighbours while reading the single sorted run back.
 */
fun countBySorting(keys: Sequence<String>, sorter: ExternalSorter): List<KeyCount> {
    val result = sorter.sort(keys)
    val sorted = result.output ?: return emptyList()
    return sorter.store.open(sorted).use { r -> countAdjacent(generateSequence { r.next() }) }
}
