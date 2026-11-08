package sfz.cons.l01

/**
 * Lesson cons-01: which consistency models does a history satisfy?
 *
 * Every model on the ladder asks the same question with different rules: is there an order of the
 * operations that a single copy could have produced (each read returns the latest write before it),
 * and that respects some "a must come before b" relation? [Search] answers that question. Your job is
 * to say, for each model, WHICH operations must be put in order and WHICH relation the order must
 * respect. Strongest first:
 *
 * - LINEARIZABLE: one order of all operations, respecting real time ([realTime]).
 * - SEQUENTIAL: one order of all operations, respecting each process's own order ([programOrder]).
 * - CAUSAL: for EACH process separately, an order of all writes plus that process's own operations,
 *   respecting [causalOrder]. Different processes may see concurrent writes in different orders.
 * - READ_YOUR_WRITES: for each process, an order of all writes plus its operations in which each of
 *   its reads comes after its own earlier writes.
 * - MONOTONIC_READS: for each process, an order of all writes plus its operations in which its reads
 *   stay in the order it made them (so what it has seen never "un-happens").
 * - EVENTUAL: true for every finite history. It promises only that copies agree once writes stop.
 */
enum class Model { LINEARIZABLE, SEQUENTIAL, CAUSAL, READ_YOUR_WRITES, MONOTONIC_READS, EVENTUAL }

/** Real-time order: [a] had its answer before [b] was sent, so everyone agrees [a] came first. */
fun realTime(a: Op, b: Op): Boolean = TODO("exercise 1: a ended before b started")

/** Program order: [a] and [b] ran in the same process, [a] first. */
fun programOrder(a: Op, b: Op): Boolean = TODO("exercise 1: same process, and a started before b")

/**
 * Causal order ("happens before") in [h]: the smallest relation that contains program order and
 * reads-from (a write comes before every read that returned its value, see [History.writeOf]) and
 * is transitive. Build it once, for example as a set of (a.id, b.id) pairs, and return a function
 * that looks pairs up.
 */
fun causalOrder(h: History): (Op, Op) -> Boolean = TODO("exercise 2: program order plus reads-from, closed under transitivity")

/** Does [h] satisfy [model]? Use [Search.exists] with the ops and the relation the model demands. */
fun satisfies(h: History, model: Model): Boolean = TODO("exercise 3: one case per model")

/** Every model [h] satisfies (given). */
fun classify(h: History): Set<Model> = Model.entries.filter { satisfies(h, it) }.toSet()
