package sfz.enc.l01

import java.io.InvalidClassException

/**
 * Reading Java-serialized bytes without letting the bytes choose which code runs.
 *
 * `ObjectInputStream.readObject()` creates whatever class the bytes name and runs its `readObject`
 * method, before your cast to the type you expected. A JEP 290 filter is asked about each class
 * before it is created, and can reject it.
 */
object SafeDeserializer {
    /**
     * Decodes one [Authorization] from [bytes] made by `ObjectOutputStream`.
     *
     * Install a filter on the stream (`ObjectInputFilter.Config.createFilter(pattern)` and
     * `stream.setObjectInputFilter(...)`) BEFORE calling `readObject`. The filter must:
     * - allow exactly `sfz.enc.l01.Authorization`, not every class in its package;
     * - allow the JDK classes an Authorization contains: `java.util.ArrayList`, `java.util.Arrays$ArrayList`,
     *   `java.lang.String` and `java.lang.Object` (the filter checks an array by its element type, and
     *   `ArrayList` asks about an `Object[]` before it fills itself);
     * - reject a graph deeper than 5 objects (`maxdepth=5`);
     * - reject every other class (`!*` at the end).
     *
     * A rejected class makes `readObject` throw [InvalidClassException]. Let it propagate.
     */
    fun readAuthorization(bytes: ByteArray): Authorization {
        TODO("open an ObjectInputStream, set the filter, readObject, cast to Authorization")
    }
}
