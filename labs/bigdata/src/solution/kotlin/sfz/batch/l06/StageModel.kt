package sfz.batch.l06

/** One step of a pipeline, as Spark's scheduler sees it. */
sealed interface Step {
    val name: String
}

/** Reading the input, already cut into [partitions] input partitions (lesson 3's splits). */
data class Read(override val name: String, val partitions: Int) : Step

/**
 * A narrow step: each output partition needs exactly one input partition. `where`, `select`,
 * `withColumn`. A task can run it on its own partition without waiting for anyone.
 */
data class Narrow(override val name: String) : Step

/**
 * A wide step: an output partition needs rows from every input partition. `groupBy`, `join`,
 * `distinct`, `orderBy`, `repartition`. It needs a shuffle into [partitions] partitions.
 */
data class Wide(override val name: String, val partitions: Int) : Step

/** One stage: the steps its tasks run back to back, and how many tasks it has (one per partition). */
data class Stage(val steps: List<String>, val tasks: Int)

/** A small model of how Spark's scheduler cuts a job into stages and tasks. */
object StageModel {

    /**
     * Cuts [pipeline] into stages, in order.
     *
     * The pipeline starts with one [Read] and has no other `Read` (anything else is an
     * `IllegalArgumentException`). The first stage has one task per input partition. Narrow steps
     * join the stage they are in. Each [Wide] step ends the current stage and starts a new one with
     * `partitions` tasks; the model lists the wide step at the start of that new stage. (In Spark the
     * map half of the wide step, writing the shuffle files, runs at the end of the stage before.)
     */
    fun stages(pipeline: List<Step>): List<Stage> {
        val first = pipeline.firstOrNull()
        require(first is Read) { "a pipeline starts by reading its input" }
        require(pipeline.drop(1).none { it is Read }) { "this model handles one input" }
        val stages = mutableListOf<Stage>()
        var steps = mutableListOf(first.name)
        var tasks = first.partitions                       // stage 1: one task per input partition
        for (step in pipeline.drop(1)) {
            when (step) {
                is Narrow -> steps += step.name            // pipelined into the same tasks
                is Wide -> {
                    stages += Stage(steps, tasks)          // the shuffle ends this stage...
                    steps = mutableListOf(step.name)       // ...and its read side starts the next
                    tasks = step.partitions
                }
                is Read -> error("unreachable")
            }
        }
        stages += Stage(steps, tasks)
        return stages
    }

    /**
     * How many rounds a stage of [tasks] tasks needs on [slots] task slots (cores): each slot runs
     * one task at a time. 8 tasks on 2 slots take 4 rounds, called waves.
     */
    fun waves(tasks: Int, slots: Int): Int {
        require(slots > 0) { "need at least one slot" }
        return (tasks + slots - 1) / slots
    }
}
