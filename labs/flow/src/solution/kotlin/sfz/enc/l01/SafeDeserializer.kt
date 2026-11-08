package sfz.enc.l01

import java.io.ByteArrayInputStream
import java.io.ObjectInputFilter
import java.io.ObjectInputStream

object SafeDeserializer {
    // an allow-list: exact class names, the limit first, and !* so anything unlisted is REJECTED.
    // java.lang.Object is there because ArrayList asks the filter about an Object[] of its size before it fills it
    private val filter: ObjectInputFilter = ObjectInputFilter.Config.createFilter(
        "maxdepth=5;sfz.enc.l01.Authorization;java.util.ArrayList;java.util.Arrays\$ArrayList;java.lang.String;java.lang.Object;!*"
    )

    fun readAuthorization(bytes: ByteArray): Authorization =
        ObjectInputStream(ByteArrayInputStream(bytes)).use { input ->
            input.setObjectInputFilter(filter) // must be set before the first readObject
            // the filter runs before each object is created; the cast runs only after readObject returns
            input.readObject() as Authorization
        }
}
