package sfz.os.l10

/** A failed call, named by its errno: ENOENT, EEXIST, EPERM, EBADF, EMFILE, EISDIR, ELOOP. */
class FsError(val errno: String, detail: String) : RuntimeException("$errno: $detail")

enum class Type { FILE, DIRECTORY, SYMLINK }

/**
 * An inode: the file itself. It has a number, a type, a link count and the data, and no name.
 * [openFiles] counts the open file descriptions that point at it (the kernel's in-memory reference).
 */
class Inode(val number: Int, val type: Type) {
    var links = 0
    var openFiles = 0
    val data = StringBuilder()                          // the file's bytes, as text to keep the model readable
    val entries = LinkedHashMap<String, Int>()          // for a directory: name -> inode number
    var target = ""                                     // for a symlink: the path it holds

    val size: Int get() = if (type == Type.SYMLINK) target.length else data.length
}

enum class Flag { READ, WRITE, APPEND, CREATE, TRUNC }

/** An open file description: what one open() made. It holds the offset and the flags, and points at an inode. */
class OpenFile(val inode: Inode, val flags: Set<Flag>) {
    var offset = 0
    /** How many file descriptors, in any process, point at this description. */
    var refs = 1
}

/** A process as far as files go: its file descriptor table (fd number -> open file description). */
class Proc(val pid: Int, val limit: Int) {
    val fds = sortedMapOf<Int, OpenFile>()
}

/**
 * A tiny file system plus the kernel's file tables, close to Linux:
 * - a directory maps names to inode numbers; the inode has no name of its own
 * - a hard link is one more name for an inode, a symlink is a small inode that holds a path
 * - open() makes an open file description (offset + flags) and puts it in the lowest free fd slot
 * - fork() copies the fd table, so both processes point at the same descriptions
 * - an inode is freed when it has no names and no open descriptions
 */
class FileSystem {
    private val inodes = HashMap<Int, Inode>()
    private var nextInode = 2
    private var nextPid = 100
    val root: Inode = newInode(Type.DIRECTORY).also { it.links = 2; it.entries["."] = it.number; it.entries[".."] = it.number }

    /** Inodes still in the inode table: what df counts. */
    val liveInodes: Collection<Inode> get() = inodes.values

    fun inode(number: Int): Inode = inodes[number] ?: throw FsError("ENOENT", "inode $number")

    private fun newInode(type: Type): Inode = Inode(nextInode++, type).also { inodes[it.number] = it }

    /** A new process with fds 0, 1 and 2 already open on a terminal, and [extra] more (the JVM has its modules file open). */
    fun spawn(limit: Int = 1024, extra: Int = 0): Proc {
        val p = Proc(nextPid++, limit)
        val tty = newInode(Type.FILE)
        for (fd in 0 until 3 + extra) p.fds[fd] = OpenFile(tty, setOf(Flag.READ, Flag.WRITE)).also { tty.openFiles++ }
        return p
    }

    // ---------- names: written for you ----------

    /** The directory that holds [path] and the last name in it. A path without a leading / starts at [from]. */
    private fun parent(path: String, from: Inode = root, depth: Int = 0): Pair<Inode, String> {
        val parts = path.trim('/').split('/')
        var dir = if (path.startsWith("/")) root else from
        for (name in parts.dropLast(1)) dir = step(dir, name, follow = true, depth = depth)
        if (dir.type != Type.DIRECTORY) throw FsError("ENOTDIR", path)
        return dir to parts.last()
    }

    private fun step(dir: Inode, name: String, follow: Boolean, depth: Int): Inode {
        val n = dir.entries[name] ?: throw FsError("ENOENT", name)
        val node = inode(n)
        if (node.type == Type.SYMLINK && follow) {
            if (depth > 8) throw FsError("ELOOP", name)
            return walk(node.target, dir, true, depth + 1)   // a relative target starts in the link's directory
        }
        return node
    }

    private fun walk(path: String, from: Inode, follow: Boolean, depth: Int): Inode {
        if (path.trim('/').isEmpty()) return if (path.startsWith("/")) root else from
        val (dir, name) = parent(path, from, depth)
        return step(dir, name, follow, depth)
    }

    /** Walk [path] from the root. With [follow], a symlink at the end is replaced by what it points to. */
    fun resolve(path: String, follow: Boolean = true): Inode = walk(path, root, follow, 0)

    fun exists(path: String): Boolean = try { resolve(path); true } catch (e: FsError) { false }

    fun mkdir(path: String): Inode {
        val (dir, name) = parent(path)
        if (name in dir.entries) throw FsError("EEXIST", path)
        val d = newInode(Type.DIRECTORY)
        d.entries["."] = d.number
        d.entries[".."] = dir.number
        d.links = 2                                     // its name in the parent, and its own "."
        dir.links++                                     // the new directory's ".." points back
        dir.entries[name] = d.number
        return d
    }

    /** A symlink at [path] that holds [target]. The target doesn't have to exist. */
    fun symlink(target: String, path: String): Inode {
        val (dir, name) = parent(path)
        if (name in dir.entries) throw FsError("EEXIST", path)
        val s = newInode(Type.SYMLINK)
        s.target = target
        s.links = 1
        dir.entries[name] = s.number
        return s
    }

    /** rename(): one directory entry changes; the inode doesn't move or change. */
    fun rename(from: String, to: String) {
        val (fromDir, fromName) = parent(from)
        val n = fromDir.entries[fromName] ?: throw FsError("ENOENT", from)
        val (toDir, toName) = parent(to)
        toDir.entries[toName]?.let { old -> if (old != n) dropName(inode(old)) }   // the replaced file loses a name
        fromDir.entries.remove(fromName)
        toDir.entries[toName] = n
    }

    /** The file is gone for good only when nothing names it and nothing has it open. */
    private fun release(node: Inode) {
        if (node.links == 0 && node.openFiles == 0) inodes.remove(node.number)
    }

    private fun dropName(node: Inode) {
        node.links--
        release(node)
    }

    // ---------- the lab: links ----------

    /** ln: give the inode behind [existing] a second name, [newPath]. Directories can't be hard-linked (EPERM). */
    fun link(existing: String, newPath: String) {
        val node = resolve(existing, follow = false)
        if (node.type == Type.DIRECTORY) throw FsError("EPERM", "hard link to a directory")
        val (dir, name) = parent(newPath)
        if (name in dir.entries) throw FsError("EEXIST", newPath)
        dir.entries[name] = node.number                 // a new name -> the same inode number
        node.links++
    }

    /** rm: remove one name. The inode survives while another name or an open description refers to it. */
    fun unlink(path: String) {
        val (dir, name) = parent(path)
        val n = dir.entries[name] ?: throw FsError("ENOENT", path)
        val node = inode(n)
        if (node.type == Type.DIRECTORY) throw FsError("EISDIR", path)
        dir.entries.remove(name)
        dropName(node)                                  // links - 1, and free it only if nothing else holds it
    }

    // ---------- the lab: descriptors ----------

    /**
     * open(): find (or with CREATE, create) the file, make a new open file description with offset 0,
     * and put it in the lowest free fd slot. Fails with EMFILE when the process already has [Proc.limit] fds.
     */
    fun open(p: Proc, path: String, flags: Set<Flag>): Int {
        if (p.fds.size >= p.limit) throw FsError("EMFILE", "too many open files")
        val node = if (Flag.CREATE in flags && !exists(path)) {
            val (dir, name) = parent(path)
            newInode(Type.FILE).also { it.links = 1; dir.entries[name] = it.number }
        } else resolve(path)
        if (node.type == Type.DIRECTORY && Flag.WRITE in flags) throw FsError("EISDIR", path)
        if (Flag.TRUNC in flags) node.data.setLength(0)
        var fd = 0
        while (fd in p.fds) fd++                        // POSIX: the lowest-numbered free descriptor
        p.fds[fd] = OpenFile(node, flags)
        node.openFiles++
        return fd
    }

    private fun desc(p: Proc, fd: Int): OpenFile = p.fds[fd] ?: throw FsError("EBADF", "fd $fd")

    /** write(): at the description's offset, or with APPEND at the end of the file; then move the offset. */
    fun write(p: Proc, fd: Int, text: String): Int {
        val f = desc(p, fd)
        val d = f.inode.data
        if (Flag.APPEND in f.flags) f.offset = d.length // move to the end and write, as one step
        while (d.length < f.offset) d.append('\u0000')   // writing past the end leaves a hole of zeros
        val end = minOf(f.offset + text.length, d.length)
        d.replace(f.offset, end, text)                  // overwrite what's there, extend if needed
        f.offset += text.length                         // every fd sharing this description sees the new offset
        return text.length
    }

    /** read(): up to [n] characters from the offset, moving it. Written for you. */
    fun read(p: Proc, fd: Int, n: Int): String {
        val f = desc(p, fd)
        val d = f.inode.data
        if (f.offset >= d.length) return ""
        val s = d.substring(f.offset, minOf(d.length, f.offset + n))
        f.offset += s.length
        return s
    }

    /** close(): drop the fd. When the last fd for a description goes, the description goes, and maybe the file. */
    fun close(p: Proc, fd: Int) {
        val f = p.fds.remove(fd) ?: throw FsError("EBADF", "fd $fd")
        f.refs--
        if (f.refs == 0) {
            f.inode.openFiles--
            release(f.inode)                            // a deleted file disappears here
        }
    }

    /** dup2(): make [newFd] point at the same description as [oldFd]. Written for you. */
    fun dup2(p: Proc, oldFd: Int, newFd: Int): Int {
        val f = desc(p, oldFd)
        if (oldFd == newFd) return newFd
        if (newFd in p.fds) close(p, newFd)
        p.fds[newFd] = f
        f.refs++
        return newFd
    }

    /** fork(): the child gets a copy of the fd table, pointing at the SAME open file descriptions. */
    fun fork(parent: Proc): Proc {
        val child = Proc(nextPid++, parent.limit)
        for ((fd, f) in parent.fds) {
            child.fds[fd] = f                           // same object: shared offset and flags
            f.refs++
        }
        return child
    }

    /** exit(): close everything the process has open. Written for you. */
    fun exit(p: Proc) {
        for (fd in p.fds.keys.toList()) close(p, fd)
    }

    // ---------- df and du: written for you ----------

    /** df: space used by every inode the file system still has, named or not, in 4 KB blocks. */
    fun dfBlocks(): Int = inodes.values.filter { it.type == Type.FILE }.sumOf { blocks(it) }

    /** du: walk the names under [path] and add up what they reach, counting each inode once. */
    fun duBlocks(path: String = "/"): Int {
        val seen = HashSet<Int>()
        fun walk(node: Inode): Int {
            if (!seen.add(node.number)) return 0
            return when (node.type) {
                Type.FILE -> blocks(node)
                Type.SYMLINK -> 0
                Type.DIRECTORY -> node.entries.filterKeys { it != "." && it != ".." }.values.sumOf { walk(inode(it)) }
            }
        }
        return walk(resolve(path, follow = false))
    }

    private fun blocks(node: Inode): Int = (node.size + BLOCK - 1) / BLOCK

    /** What `ls -l /proc/<pid>/fd/<fd>` would print after the arrow: the path, plus " (deleted)" once no name is left. */
    fun procFd(p: Proc, fd: Int, path: String): String = if (desc(p, fd).inode.links == 0) "$path (deleted)" else path

    companion object {
        const val BLOCK = 4096
    }
}
