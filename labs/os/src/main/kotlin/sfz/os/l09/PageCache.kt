package sfz.os.l09

/**
 * The storage device: the only thing that survives a power cut. One directory (name -> inode
 * number), and for each inode its size and its 4 KB pages. Written for you.
 */
class Disk {
    val directory: MutableMap<String, Int> = HashMap()
    val sizes: MutableMap<Int, Int> = HashMap()
    val pages: MutableMap<Pair<Int, Int>, ByteArray> = HashMap()
    /** Pages written to the device, and cache flushes the device was asked for (one per fsync). */
    var pageWrites = 0
    var flushes = 0

    /** What a program would read from [name] after a reboot: null if the name isn't there. */
    fun contents(name: String): ByteArray? {
        val inode = directory[name] ?: return null
        val size = sizes[inode] ?: 0
        val out = ByteArray(size)
        for (i in 0 until (size + PAGE - 1) / PAGE) {
            val page = pages[inode to i] ?: continue           // never written back: reads as zeros
            page.copyInto(out, i * PAGE, 0, minOf(PAGE, size - i * PAGE))
        }
        return out
    }

    companion object {
        const val PAGE = 4096
    }
}

/** Thrown when the simulated power cut hits in the middle of a sequence of calls. */
class PowerCut : RuntimeException("power cut")

/**
 * A tiny kernel over one [Disk]: files made of 4 KB pages, a page cache with dirty pages, a
 * flusher thread, a journal that commits metadata, fsync, and a crash.
 *
 * The rules, close to Linux with ext4:
 * - write() copies into cached pages and marks them dirty. Nothing reaches the disk.
 * - The flusher wakes every [wakeMs] and writes back pages that have been dirty for [expireMs] or more.
 * - The journal commits metadata (file sizes, the directory) every [commitMs], whether or not the data is on disk yet.
 * - fsync(file) writes the file's dirty pages and its size, then asks the device to flush.
 * - fsyncDir() writes the directory.
 * - crash() throws away everything that is only in RAM.
 *
 * Everything except [write], [fsync] and [tick] is written for you.
 */
class Kernel(
    val disk: Disk = Disk(),
    val expireMs: Long = 30_000,
    val wakeMs: Long = 5_000,
    val commitMs: Long = 5_000,
) {
    /** One cached page of one file. */
    class Page(val data: ByteArray, var dirty: Boolean = false, var dirtiedAt: Long = 0)

    /** The simulated clock, in milliseconds. */
    var now = 0L; private set

    private val cache = HashMap<Pair<Int, Int>, Page>()
    private val directory = HashMap(disk.directory)                         // what programs see
    private val sizes = HashMap(disk.sizes)
    private var nextInode = (disk.sizes.keys.maxOrNull() ?: 0) + 1
    private var metadataDirty = false

    /** Reads that had to go to the disk, and reads served from RAM. */
    var cacheMisses = 0; private set
    var cacheHits = 0; private set

    /** Cut the power before the next call once this many more calls have run (null: never). */
    var powerCutAfter: Int? = null

    val dirtyPages: Int get() = cache.values.count { it.dirty }
    val cachedPages: Int get() = cache.size

    private fun step() {
        val left = powerCutAfter ?: return
        if (left == 0) throw PowerCut()
        powerCutAfter = left - 1
    }

    /** The cached page [index] of [inode], read from disk (or zeros) on a miss. */
    private fun page(inode: Int, index: Int): Page {
        cache[inode to index]?.let { cacheHits++; return it }
        cacheMisses++
        val fromDisk = disk.pages[inode to index]?.copyOf() ?: ByteArray(Disk.PAGE)
        return Page(fromDisk).also { cache[inode to index] = it }
    }

    fun create(name: String): Int {
        step()
        val inode = nextInode++
        directory[name] = inode
        sizes[inode] = 0
        metadataDirty = true
        return inode
    }

    fun open(name: String): Int = directory[name] ?: error("ENOENT: $name")

    fun exists(name: String): Boolean = name in directory

    fun size(inode: Int): Int = sizes.getValue(inode)

    fun read(inode: Int, offset: Int, length: Int): ByteArray {
        val end = minOf(offset + length, size(inode))
        val out = ByteArray(maxOf(0, end - offset))
        var pos = offset
        while (pos < end) {
            val p = page(inode, pos / Disk.PAGE)
            val inPage = pos % Disk.PAGE
            val n = minOf(Disk.PAGE - inPage, end - pos)
            p.data.copyInto(out, pos - offset, inPage, inPage + n)
            pos += n
        }
        return out
    }

    fun readAll(name: String): ByteArray = open(name).let { read(it, 0, size(it)) }

    /** Change the size. Pages past the new end leave the cache, and their bytes are gone. */
    fun truncate(inode: Int, newSize: Int) {
        step()
        sizes[inode] = newSize
        cache.keys.filter { it.first == inode && it.second * Disk.PAGE >= newSize }.forEach { cache.remove(it) }
        val last = cache[inode to newSize / Disk.PAGE]
        last?.data?.fill(0, newSize % Disk.PAGE, Disk.PAGE)
        metadataDirty = true
    }

    /** rename(): one step in RAM, so no program ever sees the name missing. On disk it waits for the journal. */
    fun rename(from: String, to: String) {
        step()
        directory[to] = directory.remove(from) ?: error("ENOENT: $from")
        metadataDirty = true
    }

    /** fsync on the directory: write the directory as programs see it now. */
    fun fsyncDir() {
        step()
        disk.directory.clear()
        disk.directory.putAll(directory)
        disk.flushes++
    }

    /** A journal commit: sizes and the directory go to disk, data pages don't. */
    fun commitMetadata() {
        if (!metadataDirty) return
        disk.directory.clear()
        disk.directory.putAll(directory)
        disk.sizes.putAll(sizes)
        metadataDirty = false
    }

    /** Write back every dirty page of every file, like `sync` (data only; call [commitMetadata] too for a full sync). */
    fun writeBackAll() {
        for ((key, p) in cache) if (p.dirty) writeBack(key, p)
    }

    private fun writeBack(key: Pair<Int, Int>, p: Page) {
        disk.pages[key] = p.data.copyOf()
        disk.pageWrites++
        p.dirty = false
    }

    /** The power goes out: the cache and every unwritten change are lost. The machine boots from [disk]. */
    fun crash(): Kernel = Kernel(disk, expireMs, wakeMs, commitMs)

    /**
     * write(): copy [bytes] into the cached pages of [inode] at [offset] (reading a page in first
     * with [page] when it isn't cached), mark each page dirty, and note the time a page went from
     * clean to dirty in dirtiedAt. A write past the end grows the size, which is metadata.
     * Call [step] first, like every other change.
     */
    fun write(inode: Int, offset: Int, bytes: ByteArray) {
        TODO("step(); for each page the bytes cover: page(inode, index), copy the bytes in, and if it was clean mark it dirty with dirtiedAt = now; if the write ends past size(inode), grow sizes[inode] and set metadataDirty")
    }

    /**
     * fsync(): write back every dirty page of [inode], put its size on disk, and count one device
     * flush. Other files' dirty pages stay dirty. Call [step] first.
     */
    fun fsync(inode: Int) {
        TODO("step(); writeBack every dirty cached page of this inode only; disk.sizes[inode] = size(inode); disk.flushes++")
    }

    /**
     * Let [ms] milliseconds pass. At every multiple of [commitMs] the journal commits
     * ([commitMetadata]); at every multiple of [wakeMs] the flusher writes back each page that has
     * been dirty for at least [expireMs]. Then the clock stops at now + ms.
     */
    fun tick(ms: Long) {
        TODO("walk the clock to each next multiple of commitMs or wakeMs up to now + ms: commitMetadata() on commits, writeBack pages dirty for >= expireMs on wake-ups; finish with now = now + ms")
    }
}

/** Two ways to replace a small file, such as a payment router's config. */
object Config {
    /** The tempting way: truncate the file and write the new bytes in place, then fsync. Written for you. */
    fun overwrite(k: Kernel, name: String, content: ByteArray) {
        val inode = if (k.exists(name)) k.open(name) else k.create(name)
        k.truncate(inode, 0)
        k.write(inode, 0, content)
        k.fsync(inode)
    }

    /**
     * The safe way. Write the new bytes to "[name].tmp", fsync it, rename it over [name], then
     * fsync the directory. A crash at any point leaves either the old file or the new one, and
     * once this returns the new one survives a crash.
     */
    fun replace(k: Kernel, name: String, content: ByteArray) {
        TODO("create the file name + .tmp, write the content to it, fsync it, rename it over name, then fsyncDir")
    }
}
