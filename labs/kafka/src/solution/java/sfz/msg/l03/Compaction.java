package sfz.msg.l03;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class Compaction {
    private Compaction() {}

    public static List<Rec> compact(List<Rec> closed, long nowMs, long deleteRetentionMs) {
        // pass 1: the cleaner's "offset map": key -> the offset of its last record
        Map<String, Long> lastOffset = new HashMap<>();
        for (Rec r : closed) {
            lastOffset.put(r.getKey(), r.getOffset()); // later records overwrite earlier ones
        }

        // pass 2: copy the survivors in their original order; offsets are never rewritten
        List<Rec> kept = new ArrayList<>();
        for (Rec r : closed) {
            if (r.getOffset() != lastOffset.get(r.getKey())) continue;          // an older value: gone
            boolean tombstone = r.getValue() == null;
            if (tombstone && nowMs - r.getTimestampMs() > deleteRetentionMs) continue; // delete seen long enough
            kept.add(r);
        }
        return kept;
    }
}
