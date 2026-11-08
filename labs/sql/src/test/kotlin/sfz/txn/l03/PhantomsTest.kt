package sfz.txn.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.sql.support.CourseDb
import sfz.sql.support.Session
import sfz.sql.support.Sessions
import sfz.sql.support.exerciseSql
import sfz.sql.support.sessions
import sfz.sql.support.splitStatements

/**
 * Lesson txn-03. Your files are src/main/resources/sfz/txn/l03/off_call.sql, book_room.sql and
 * no_overlap.sql.
 *
 * Write skew and phantoms happen between transactions, so these tests run two real sessions at
 * once and commit for real. Each test first builds three small tables of its own in the course
 * database (on_call, rooms and room_bookings, seeded as below) and drops them again at the end.
 */
class PhantomsTest {

    private val drop = "DROP TABLE IF EXISTS room_bookings, rooms, on_call"

    private val fixture = """
        $drop;
        CREATE TABLE on_call (
            shift_id bigint  NOT NULL,
            doctor   text    NOT NULL,
            on_call  boolean NOT NULL DEFAULT true,
            PRIMARY KEY (shift_id, doctor)
        );
        INSERT INTO on_call VALUES
            (1201, 'Okafor', true), (1201, 'Lind', true), (1201, 'Haas', false),
            (1202, 'Ruiz', true), (1202, 'Chen', true);
        CREATE TABLE rooms (room_id bigint PRIMARY KEY, name text NOT NULL);
        INSERT INTO rooms VALUES (4, 'Ledger'), (7, 'Clearing');
        CREATE TABLE room_bookings (
            booking_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            room_id    bigint    NOT NULL REFERENCES rooms,
            during     tstzrange NOT NULL,
            booked_by  text      NOT NULL
        );
        INSERT INTO room_bookings (room_id, during, booked_by) VALUES
            (4, '[2026-12-01 09:00+00,2026-12-01 10:00+00)', 'risk team'),
            (7, '[2026-12-01 12:00+00,2026-12-01 13:00+00)', 'card ops');
    """

    /** Builds the three tables, runs [block] in two sessions, and drops the tables again. */
    private fun lab(block: Sessions.() -> Unit) {
        CourseDb.connect().use { c -> c.createStatement().use { it.execute(fixture) } }
        sessions(cleanup = drop, block = block)
    }

    private fun Sessions.query(sql: String) = a.run(sql)!!

    private fun List<String>.waits() = filter { "waits for a lock" in it }

    // ---------------------------------------------------------------- off_call.sql

    private fun offCallScript() = splitStatements(exerciseSql("txn/l03", "off_call"))

    private fun offCall(session: Session, shift: Long, doctor: String) {
        session.run("CREATE TEMP TABLE off_call_request (shift_id bigint NOT NULL, doctor text NOT NULL)")
        session.run("INSERT INTO off_call_request VALUES ($shift, '$doctor')")
    }

    private fun Sessions.onCall(shift: Long): List<Any?> =
        query("SELECT doctor FROM on_call WHERE shift_id = $shift AND on_call ORDER BY doctor").column("doctor")

    @Test
    fun `off_call lets one doctor go while another stays on call`() = lab {
        offCall(a, 1201, "Okafor")
        val log = interleave(offCallScript(), emptyList())
        assertThat(onCall(1201)).describedAs(log.joinToString("\n")).containsExactly("Lind")
    }

    @Test
    fun `off_call keeps the last doctor on call`() = lab {
        a.run("UPDATE on_call SET on_call = false WHERE shift_id = 1201 AND doctor = 'Lind'")
        offCall(a, 1201, "Okafor")
        val log = interleave(offCallScript(), emptyList())
        assertThat(onCall(1201)).describedAs(log.joinToString("\n")).containsExactly("Okafor")
    }

    @Test
    fun `two doctors who go off call at the same moment leave one of them on call`() = lab {
        offCall(a, 1201, "Okafor")
        offCall(b, 1201, "Lind")
        val log = interleave(offCallScript(), offCallScript())
        assertThat(onCall(1201))
            .describedAs("shift 1201 must keep a doctor on call; what happened:\n" + log.joinToString("\n"))
            .hasSize(1)
    }

    @Test
    fun `doctors on different shifts do not wait for each other`() = lab {
        offCall(a, 1201, "Okafor")
        offCall(b, 1202, "Ruiz")
        val log = interleave(offCallScript(), offCallScript())
        assertThat(log.waits()).describedAs("lock only the rows of the doctor's own shift:\n" + log.joinToString("\n")).isEmpty()
        assertThat(onCall(1201) + onCall(1202)).describedAs(log.joinToString("\n")).containsExactly("Lind", "Chen")
    }

    // ---------------------------------------------------------------- book_room.sql

    private fun bookScript() = splitStatements(exerciseSql("txn/l03", "book_room"))

    private fun booking(session: Session, room: Long, from: String, to: String, who: String) {
        session.run("CREATE TEMP TABLE booking_request (room_id bigint NOT NULL, during tstzrange NOT NULL, booked_by text NOT NULL)")
        session.run("INSERT INTO booking_request VALUES ($room, tstzrange('2026-12-01 $from+00', '2026-12-01 $to+00'), '$who')")
    }

    private fun Sessions.bookings(room: Long): List<Any?> =
        query("SELECT booked_by FROM room_bookings WHERE room_id = $room ORDER BY lower(during), booked_by").column("booked_by")

    @Test
    fun `book_room books a free slot`() = lab {
        booking(a, 4, "12:00", "13:00", "settlement review")
        val log = interleave(bookScript(), emptyList())
        assertThat(bookings(4)).describedAs(log.joinToString("\n")).containsExactly("risk team", "settlement review")
    }

    @Test
    fun `book_room refuses a slot that overlaps an existing booking`() = lab {
        booking(a, 4, "09:30", "10:30", "settlement review")
        val log = interleave(bookScript(), emptyList())
        assertThat(bookings(4)).describedAs(log.joinToString("\n")).containsExactly("risk team")
    }

    @Test
    fun `two overlapping bookings at the same moment, and only one gets the room`() = lab {
        booking(a, 4, "12:00", "13:00", "settlement review")
        booking(b, 4, "12:30", "13:30", "card ops")
        val log = interleave(bookScript(), bookScript())
        val overlaps = query(
            """
            SELECT count(*) AS n FROM room_bookings x JOIN room_bookings y
              ON x.room_id = y.room_id AND x.booking_id < y.booking_id AND x.during && y.during
            """,
        ).column("n").single()
        assertThat(overlaps)
            .describedAs("room 4 was booked twice for the same time; what happened:\n" + log.joinToString("\n") + "\nbookings: " + bookings(4))
            .isEqualTo(0L)
        assertThat(bookings(4)).hasSize(2)
    }

    @Test
    fun `back-to-back bookings at the same moment both get the room`() = lab {
        booking(a, 4, "12:00", "13:00", "settlement review")
        booking(b, 4, "13:00", "14:00", "card ops")
        val log = interleave(bookScript(), bookScript())
        assertThat(bookings(4)).describedAs("[12:00,13:00) and [13:00,14:00) do not overlap:\n" + log.joinToString("\n"))
            .containsExactly("risk team", "settlement review", "card ops")
    }

    @Test
    fun `bookings of different rooms do not wait for each other`() = lab {
        booking(a, 4, "12:00", "13:00", "settlement review")
        booking(b, 7, "14:00", "15:00", "fraud ops")
        val log = interleave(bookScript(), bookScript())
        assertThat(log.waits()).describedAs("lock only what belongs to the booking's own room:\n" + log.joinToString("\n")).isEmpty()
        assertThat(bookings(4) + bookings(7)).containsExactly("risk team", "settlement review", "card ops", "fraud ops")
    }

    // ---------------------------------------------------------------- no_overlap.sql

    private fun Sessions.addConstraint() {
        a.run(exerciseSql("txn/l03", "no_overlap"))
    }

    private fun insert(room: Long, from: String, to: String, who: String) =
        "INSERT INTO room_bookings (room_id, during, booked_by) VALUES ($room, tstzrange('2026-12-01 $from+00', '2026-12-01 $to+00'), '$who')"

    @Test
    fun `no_overlap makes the database refuse an overlapping booking`() = lab {
        addConstraint()
        assertThat(a.sqlStateOf(insert(4, "09:30", "10:30", "settlement review")))
            .describedAs("a booking of room 4 from 09:30 overlaps the 09:00-10:00 booking; expected exclusion_violation (23P01)")
            .isEqualTo("23P01")
        assertThat(bookings(4)).containsExactly("risk team")
    }

    @Test
    fun `no_overlap still allows back-to-back bookings and other rooms at the same time`() = lab {
        addConstraint()
        assertThat(a.sqlStateOf(insert(4, "10:00", "11:00", "settlement review"))).describedAs("10:00-11:00 starts as 09:00-10:00 ends").isNull()
        assertThat(a.sqlStateOf(insert(7, "09:30", "10:30", "fraud ops"))).describedAs("room 7 is free at 09:30").isNull()
        assertThat(bookings(4)).containsExactly("risk team", "settlement review")
    }

    @Test
    fun `with no_overlap, a plain insert that overlaps an uncommitted booking waits, then fails`() = lab {
        addConstraint()
        a.run("BEGIN")
        a.run(insert(4, "15:00", "16:00", "payroll"))
        b.run("BEGIN")
        val second = b.start(insert(4, "15:30", "16:30", "fraud ops"))
        second.awaitBlocked()                      // the constraint check waits for A's transaction
        a.run("COMMIT")
        assertThat(second.sqlState()).describedAs("B's insert overlaps A's committed booking").isEqualTo("23P01")
        b.run("ROLLBACK")
        assertThat(bookings(4)).containsExactly("risk team", "payroll")
    }
}
