package sfz.nosql.support

import software.amazon.awssdk.core.SdkRequest
import software.amazon.awssdk.core.interceptor.Context
import software.amazon.awssdk.core.interceptor.ExecutionAttributes
import software.amazon.awssdk.core.interceptor.ExecutionInterceptor
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Records every request a client sends, so a test can say "this took exactly one Query".
 * Attach it with [TestDynamoDb.clientWith].
 */
class RequestLog : ExecutionInterceptor {
    private val seen = CopyOnWriteArrayList<SdkRequest>()

    override fun beforeExecution(context: Context.BeforeExecution, executionAttributes: ExecutionAttributes) {
        seen += context.request()
    }

    /** Every request since the last [clear], oldest first. */
    val requests: List<SdkRequest> get() = seen.toList()

    /** Simple class names of the requests, such as `QueryRequest`. */
    val names: List<String> get() = seen.map { it.javaClass.simpleName }

    fun clear() = seen.clear()
}
