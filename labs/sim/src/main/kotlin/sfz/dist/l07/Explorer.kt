package sfz.dist.l07

/**
 * Lesson dist-07: a tiny model checker. [explore] starts from the first state of a model, takes
 * every step the model allows from every state it reaches, and checks a safety rule (the
 * invariant) in each state. It goes breadth first, so the first broken state it meets is one of the
 * fewest steps from the start, and the trace it returns is a shortest way to break the rule. TLA+'s
 * model checker, TLC, does the same job on a written specification, with much better bookkeeping.
 *
 * A state must be an immutable value with a proper equals and hashCode (a data class of data
 * classes, lists, sets and maps), so that two paths reaching the same state count it once.
 */

/** What one exploration found. */
data class Exploration<S>(
    /** How many different states the explorer reached; a state reached by two paths counts once. */
    val states: Int,
    /** The step labels from the first state to a state that breaks the invariant, or null if none does. */
    val violation: List<String>?,
    /** The state that breaks the invariant, or null. */
    val badState: S?,
    /** Reached states where no step is possible and `done` is false: the system is stuck for good. */
    val stuck: Int,
)

/** Thrown when a model has more states than the explorer is willing to visit. */
class TooManyStates(limit: Int) : RuntimeException("more than $limit states: make the model smaller")

/**
 * The step labels that lead from the first state to [state], read back through [parent], which
 * maps every reached state to the state it was first reached from and the step taken (null for the
 * first state). Given.
 */
fun <S> traceTo(state: S, parent: Map<S, Pair<S, String>?>): List<String> {
    val steps = ArrayDeque<String>()
    var at = state
    while (true) {
        val (from, label) = parent.getValue(at) ?: break
        steps.addFirst(label)
        at = from
    }
    return steps.toList()
}

/**
 * Exercise 1 of 4: visit every state reachable from [initial], breadth first.
 *
 * Keep `parent`, a map from each state you have reached to how you first reached it (the previous
 * state and the step label; null for [initial]). It doubles as the visited set. Take states from
 * the front of a queue. For each one: if [invariant] is false, stop and return the trace to it
 * ([traceTo]) and the state itself. Otherwise ask [next] for its steps; if there are none and
 * [done] is false, count it as stuck. Put every state you have not seen before in `parent` and at
 * the back of the queue. Throw [TooManyStates] once `parent` holds more than [limit] states.
 *
 * When the queue is empty you have seen everything: return the number of states, no violation,
 * and the stuck count.
 */
fun <S> explore(
    initial: S,
    next: (S) -> List<Pair<String, S>>,
    invariant: (S) -> Boolean,
    done: (S) -> Boolean = { true },
    limit: Int = 2_000_000,
): Exploration<S> =
    TODO("breadth-first search: a parent map as the visited set, a queue, check the invariant on each state")
