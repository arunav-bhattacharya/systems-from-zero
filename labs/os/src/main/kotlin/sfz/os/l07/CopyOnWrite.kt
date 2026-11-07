package sfz.os.l07

/**
 * Physical memory as the kernel's memory controller sees it: numbered frames, each with a count of
 * the page-table entries that point at it. [limit] plays the part of a cgroup's `memory.max`, in frames.
 * A frame shared by two processes is charged once.
 */
class Ram(val limit: Int) {
    private val refs = HashMap<Int, Int>()          // frame -> page-table entries pointing at it
    private val freeList = ArrayDeque<Int>()
    private var nextFrame = 0

    /** Frames in use right now: what `memory.current` would show. */
    val used: Int get() = refs.size

    /** A zeroed frame with one reference, or null when [limit] frames are already in use. */
    fun allocate(): Int? {
        if (used >= limit) return null
        val frame = freeList.removeFirstOrNull() ?: nextFrame++
        refs[frame] = 1
        return frame
    }

    /** One more page-table entry points at [frame]. */
    fun share(frame: Int) {
        refs[frame] = refCount(frame) + 1
    }

    /** One page-table entry stopped pointing at [frame]; the last one to let go frees it. */
    fun release(frame: Int) {
        val n = refCount(frame) - 1
        check(n >= 0) { "frame $frame is not in use" }
        if (n == 0) {
            refs.remove(frame)
            freeList.addLast(frame)
        } else {
            refs[frame] = n
        }
    }

    fun refCount(frame: Int): Int = refs[frame] ?: 0
}

/** A page-table entry: the frame, and whether a write may go straight through without a fault. */
class Pte(var frame: Int, var writable: Boolean)

/** One process: its regions (what `/proc/<pid>/maps` lists) and the page-table entries of pages it has touched. */
class Process(val pid: Int, val name: String) {
    /** Valid virtual page numbers, private and writable, like an anonymous `mmap` or the heap. */
    val regions: MutableList<LongRange> = mutableListOf()

    /** Page-table entries, by virtual page number. Only touched pages have one. */
    val pages: MutableMap<Long, Pte> = HashMap()

    /** -1000 to 1000, added to the OOM badness score as thousandths of the memory limit. -1000 means never kill. */
    var oomScoreAdj: Int = 0

    var alive: Boolean = true

    /** Resident pages, shared ones included: what `ps` shows as RSS (in pages). */
    val rss: Int get() = pages.size
}

/** The four numbers of `/proc/<pid>/smaps_rollup` this lab cares about, in pages. */
data class Smaps(val rss: Int, val shared: Int, val private: Int, val pss: Double)

/** What a write had to do. */
enum class Fault {
    /** The entry was writable: no fault at all. */
    NONE,
    /** First touch of the page: the kernel mapped a zeroed frame. */
    ZERO_FILL,
    /** The page was shared copy-on-write: the kernel copied it into a new frame for this process. */
    COPY,
    /** The page was marked copy-on-write but nobody else uses its frame any more: the kernel made it writable again. */
    REUSE,
    /** No frame could be found, and the OOM killer chose the writing process itself. */
    KILLED,
}

/**
 * A model of how Linux shares memory between processes: fork with copy-on-write, demand paging,
 * and the OOM killer when the memory limit is reached.
 *
 * [spawn], [mmap], [read], [exit] and [kill] are written for you. Write [fork], [write], [smaps]
 * and [oomVictim].
 */
class Kernel(limitFrames: Int) {
    val ram = Ram(limitFrames)
    private val table = linkedMapOf<Int, Process>()   // creation order, oldest first
    private var nextPid = 1

    /** Pages copied by copy-on-write faults so far. */
    var copies = 0L; private set
    /** First-touch faults that mapped a zeroed frame. */
    var zeroFills = 0L; private set
    /** PIDs the OOM killer has killed, in order. */
    val oomKills: MutableList<Int> = mutableListOf()

    val processes: Collection<Process> get() = table.values

    fun spawn(name: String): Process = Process(nextPid++, name).also { table[it.pid] = it }

    /** Reserve [pages] new pages after everything [p] has mapped. Like `mmap`, it costs no frames. */
    fun mmap(p: Process, pages: Long): LongRange {
        val start = (p.regions.maxOfOrNull { it.last + 1 } ?: 0x40000L)
        return (start until start + pages).also { p.regions += it }
    }

    /** A read never copies. An untouched page reads as zeros without a frame (Linux maps its shared zero page). */
    fun read(p: Process, vpn: Long) {
        check(p.alive) { "${p.name} is dead" }
        check(p.regions.any { vpn in it }) { "SIGSEGV: page $vpn is in no region of ${p.name}" }
    }

    /** The process exits: every page-table entry goes, and each frame loses one reference. */
    fun exit(p: Process) {
        for (pte in p.pages.values) ram.release(pte.frame)
        p.pages.clear()
        p.alive = false
        table.remove(p.pid)
    }

    /** SIGKILL from the OOM killer: the same clean-up as [exit], and the kill is recorded. */
    fun kill(p: Process) {
        oomKills += p.pid
        exit(p)
    }

    /** A free frame for a fault in [faulting], killing processes until one is free. Null if [faulting] itself died. */
    private fun frameFor(faulting: Process): Int? {
        while (true) {
            ram.allocate()?.let { return it }
            val victim = oomVictim() ?: return null           // nobody may be killed: the fault fails
            kill(victim)
            if (victim === faulting) return null
        }
    }

    /**
     * fork(): a new process whose page table points at the parent's frames. Nothing is copied.
     * Every entry, in the parent and in the child, becomes read-only, so the first write by
     * either side faults and can be copied then.
     */
    fun fork(parent: Process, name: String = parent.name): Process {
        TODO("spawn a child with the parent's regions and oomScoreAdj; for every parent entry: make it read-only, give the child a read-only entry for the same frame, and ram.share the frame")
    }

    /**
     * A store to page [vpn] of [p]: the page-fault handler's decisions.
     * Writable entry: nothing to do. No entry: map a zeroed frame. Read-only entry: if another
     * entry still points at the frame, copy it into a new frame; if this is the last one, make it writable.
     * Any new frame comes from [frameFor], which may run the OOM killer.
     */
    fun write(p: Process, vpn: Long): Fault {
        TODO("check alive and region; no entry: frameFor, map it writable, ZERO_FILL; writable: NONE; read-only with refCount 1: make writable, REUSE; else frameFor a new frame, release the old one, point the entry at the new one, COPY. A null from frameFor is KILLED")
    }

    /** RSS, shared and private pages, and PSS: each page counts 1 / (number of entries pointing at its frame). */
    fun smaps(p: Process): Smaps {
        TODO("for each entry look up ram.refCount(frame): more than 1 is shared; PSS adds 1.0 / refCount")
    }

    /**
     * The process the OOM killer picks: the highest badness, where badness is RSS (shared pages
     * included) plus oomScoreAdj thousandths of the limit. -1000 is never picked. On a tie the
     * newer process wins, as in the kernel's scan. Null when nobody can be picked.
     */
    fun oomVictim(): Process? {
        TODO("skip oomScoreAdj == -1000; badness = rss + oomScoreAdj * ram.limit / 1000; keep the highest, and let a later process with an equal score replace an earlier one")
    }
}
