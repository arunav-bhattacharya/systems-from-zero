package sfz.redis.support

import org.junit.jupiter.api.extension.AfterEachCallback
import org.junit.jupiter.api.extension.BeforeAllCallback
import org.junit.jupiter.api.extension.ExtensionContext
import org.junit.jupiter.api.extension.ParameterContext
import org.junit.jupiter.api.extension.ParameterResolver

/**
 * JUnit extension for tests that talk to the shared Redis server.
 *
 * - Before the class's first test it starts [TestRedis] (or reuses it), so container start-up
 *   never counts against a test's own `@Timeout`.
 * - A test method that declares a [KeySpace] parameter gets a fresh prefix, and every key under
 *   it is deleted after the test.
 *
 * ```kotlin
 * @ExtendWith(WithRedis::class)
 * class LeaderboardTest {
 *     @Test
 *     fun `ties sort by member`(keys: KeySpace) {
 *         val board = keys("board")          // "t:LeaderboardTest:7:board"
 *         TestRedis.jedis.zadd(board, 10.0, "m-1")
 *     }
 * }
 * ```
 */
class WithRedis : BeforeAllCallback, ParameterResolver, AfterEachCallback {
    override fun beforeAll(context: ExtensionContext) {
        check(TestRedis.jedis.ping() == "PONG") { "the test Redis did not answer PING" }
    }

    override fun supportsParameter(parameterContext: ParameterContext, extensionContext: ExtensionContext): Boolean =
        parameterContext.parameter.type == KeySpace::class.java

    override fun resolveParameter(parameterContext: ParameterContext, extensionContext: ExtensionContext): Any {
        val space = KeySpace.fresh(extensionContext.requiredTestClass.simpleName)
        extensionContext.getStore(NAMESPACE).put(extensionContext.uniqueId, space)
        return space
    }

    override fun afterEach(context: ExtensionContext) {
        context.getStore(NAMESPACE).remove(context.uniqueId, KeySpace::class.java)?.clear()
    }

    private companion object {
        val NAMESPACE: ExtensionContext.Namespace = ExtensionContext.Namespace.create(WithRedis::class.java)
    }
}
