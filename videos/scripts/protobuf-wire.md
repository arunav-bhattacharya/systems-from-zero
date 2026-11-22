# Numbers instead of names: how Protobuf writes a payment in 42 bytes

- Slug / scene: `protobuf-wire`, `videos/scenes/protobuf_wire.py:ProtobufWire`
- Lesson: `enc-02`, section 0, "Put a number on each field: how Protobuf writes a record"
- Audience / level: a complete newcomer who has seen the previous lesson's payment as JSON (116 bytes). Doesn't know
  what a schema, a field number, a wire type, hex or a varint is.
- Length: 4:31 (~720 words of narration, two pauses, silent builds)
- Poster: `POSTER=184` (all six byte lines next to the .proto, "42 bytes (JSON: 116)")
- Format: animated explainer (Manim, Kokoro `af_heart`), 2560x1440 at 30 fps
- The learner's real question: if the names take half the bytes, can we drop them? And if we do, how does the reader
  know which value is which, and where each one ends?
- Misconception to steelman and break: (1) "`= 1` in the .proto is a default value" (it's the box number); (2) "a
  varint always saves space", broken by the payment number (9 bytes, against 8 as `fixed64`) and -1 (10 bytes as
  `int64`, 1 as `sint64`).
- Concept chain: names fill the bytes → a schema shared by both sides lets numbers replace names → each field is a key
  (field number × 8 + wire type) and a value → the wire type says where the value ends → varints: 7 bits a byte, top
  bit "more" → the whole record, 42 bytes → the declared type decides the bytes (hardest last)
- Analogy family: the lesson's café catering form. Numbered boxes, the blank form on the kitchen wall, cooks who read
  by box number; box 6 and the night cook as the open loop into the next section.
- Open loops: "how does the reader know which value is which?" planted in scene 1 → scenes 2 and 4; "a reader that
  doesn't know field 5 can still skip it" planted in scene 8 → the next section (unknown fields).
- Assumptions: every number and byte is the lesson's (116, 84, 39, 42 bytes; the .proto; keys 08, 12, 18, 22, 2a;
  4000 = a0 1f; 9 bytes for the payment number, 8 as fixed64; -1 in 10 bytes as int64, 1 as sint64; ZigZag 0→0,
  -1→1, 1→2, -2→3). The varint bytes and "Fern Bakery" bytes were re-checked in Python.

## The one picture

Left: the café's form on the kitchen wall, which becomes the `.proto` schema (five numbered fields). Right: the
payment's bytes, one line per field: a gold key, the value bytes, and what they mean in grey. Bottom: a zoom strip
where a key or a varint is taken apart bit by bit. Captions under it. Gold = keys and field numbers, teal = values,
red = a cost.

## Scene 1 · The names fill the bytes · 0:00–0:35 · [QUESTION] [FAMILIAR] [PAIN] [LOOP-PLANT]

VO: Here's our card payment again, written as JSON text: 116 bytes. Look at what fills them. paymentId, merchant,
amountMinor, currency, tags. The names of the fields, spelled out, in every single record.

Even MessagePack, the binary form of JSON that keeps the names, needs 84 bytes. Drop the names, write just the five
values, and it's 39. But then how does the reader know which value is which?

SCREEN: Title card. The JSON in two lines, the five names lighting up gold. Three bars: JSON 116, MessagePack 84, bare
values 39; a "?" by the 39.

## Scene 2 · The form on the wall · 0:35–1:10 · [ANALOGY] [MAP] [NAME]

VO: Picture a café that takes catering orders on a paper form. Every box has a number: box 1 is the name, box 3 the
amount, box 5 any notes. The cooks keep a blank copy on the wall, and read each order by box number, never by the
printed questions.

Map it. The blank form on the wall is a schema: a description of a record's fields and their types, kept apart from the
data. Both sides keep a copy. And the box numbers are field numbers. They travel in the bytes, in place of the names.

SCREEN: A paper form with boxes 1 to 5 ("name", "amount", "notes" on 1, 3, 5), "on the kitchen wall". Captions map it:
"the blank form: a schema", "box numbers: field numbers".

## Scene 3 · Protobuf and its .proto file · 1:10–1:40 · [NAME] [BREAK] [JOKE:shared-enemy]

VO: Protocol Buffers, or Protobuf, is the most common way to do this in Java and Kotlin programs. You write the form in a
.proto file. Each line names a field, its type, and a number. And careful: equals 1 is not a default value. It's the box
number. It looks like a default, and that has fooled more of us than anyone admits.

SCREEN: The form turns into the `.proto` text (`message Authorization { int64 payment_id = 1; ... repeated string
tags = 5; }`). The `= 1` to `= 5` glow gold; caption "= 1 is not a default value: it's the field number".

## Scene 4 · The key · 1:40–2:30 · [SHRINK] [PREDICT] [PAUSE] [SHOW]

VO: Now the bytes. Each field becomes a key, then a value. The key packs two things into one number: the field number
times eight, plus a wire type. The wire type tells the reader how to find where the value ends.

Type 0 is a varint, a whole number. Type 2 is a length, followed by that many bytes, for text and lists. Programmers
write bytes in hex, base sixteen, two digits a byte. Field 1 is a varint, so its key is 1 times 8, plus 0: hex 08. Field
2 is text. What's its key? Pause and work it out.

(three seconds)

2 times 8 is 16, plus 2 is 18. In hex, that's 12. After it comes the length, 11, written 0b, then the 11 bytes of Fern
Bakery.

SCREEN: Zoom strip: "key = field number × 8 + wire type"; "0: varint, 1 to 10 bytes", "2: a length, then that many
bytes". The first byte line: key 08 (gold), "field 1, wire type 0". Then "field 2, wire type 2 → key ?"; countdown;
"2 × 8 + 2 = 18 = hex 12". The second line appears: 12 | 0b 46 65 72 6e 20 42 ... | "Fern Bakery".

## Scene 5 · The varint · 2:30–3:15 · [SHOW] [NAME]

VO: Whole numbers use a varint: as few bytes as the number needs. Each byte holds seven bits of the number, lowest bits
first. Its eighth bit, the top one, is a little flag that says: more to come.

Take the amount, 4000. Its lowest seven bits are worth 32, and more is coming, so the flag is set: a0. What's left is
31, with the flag clear: 1f. So 4000 is two bytes, a0 1f. Check it: 32, plus 31 times 128, is 4000.

SCREEN: Zoom strip: "4000 = 1111 1010 0000"; the low seven bits split off (worth 32), a flag bit 1 in front → "a0"; the
rest (31) with a flag 0 → "1f". "32 + 31 × 128 = 4000". The third line appears: 18 | a0 1f | 4000.

## Scene 6 · The whole payment · 3:15–3:35 · [SHOW]

VO: Now the whole payment. Field 1, the payment number. Field 2, Fern Bakery. Field 3, 4000. Field 4, EUR. And field 5
twice, once per tag. 42 bytes, against 116 for JSON. Numbers, wire types and values, and not one name.

SCREEN: The rest of the lines: 08 | 91 80 ed 83 b4 b4 ec d4 19 | 1849204436731904017; 22 | 03 45 55 52 | "EUR";
2a | 04 63 61 72 64 | "card"; 2a | 03 33 64 73 | "3ds". A counter "42 bytes (JSON: 116)".

## Scene 7 · Is a varint always smaller? · 3:35–4:20 · [BREAK] [GUARDRAIL]

VO: So should every number be a varint? Let's be fair to them. Anything below 128 takes one byte. But the payment number
is huge and random-looking. As a varint it takes 9 bytes. Declared as fixed64, a type that always uses 8, it takes 8.

Negative numbers are worse. A computer stores minus 1 with all 64 bits set, so a plain int64 needs 10 bytes for it. The
type sint64 first applies ZigZag: 0 becomes 0, minus 1 becomes 1, 1 becomes 2, minus 2 becomes 3. Then minus 1 takes
one byte.

So the type you declare decides the bytes. Pick it for the values you expect.

SCREEN: The payment number's 9 value bytes glow red; zoom: "int64 (varint): 9 bytes   fixed64: 8 bytes". Then
"-1 as int64: 10 bytes   -1 as sint64: 1 byte" and the ZigZag pairs "0→0  -1→1  1→2  -2→3". Caption "the type you
declare decides the bytes".

## Scene 8 · The moral, a check, and the box-6 loop · 4:20–5:00 · [MORAL] [PREDICT] [PAUSE] [LOOP-PLANT]

VO: So: put a number on each field, and let the bytes carry numbers, not names. Both sides keep the form, and every
value says how long it is.

One quick check. Field 3, the amount, is a varint. What's its key byte? Pause and think.

(three seconds)

3 times 8, plus 0, is 24. In hex, 18. That's the 18 in front of a0 1f.

And "every value says how long it is" matters more than it looks. A reader that didn't know field 5 could still read
its length and skip exactly that many bytes. Next, the café adds box 6, and the night cook still has last month's form.

SCREEN: Captions "numbers, not names", "every value says how long it is". For the check, line 3's key becomes "?";
countdown; "3 × 8 + 0 = 24 = hex 18" and the key comes back. Then a yellow cursor reads the field 5 key, the length
04, and jumps over four bytes, then 03 and three bytes ("skipped: 4 bytes", "skipped: 3 bytes"). A "6" box ghosts in
at the bottom of the form.

---

### Beat check

- QUESTION + PAIN (scene 1) on the measured cost of names; the question "which value is which?" is answered by the
  analogy and the key.
- ANALOGY + MAP (scene 2), NAME (scenes 2, 3) after the picture; BREAK of "= 1 is a default" (scene 3).
- PREDICT with PAUSE: the key for field 2 (scene 4), the check (scene 8).
- BREAK of "varints always save space" (scene 7), then GUARDRAIL (pick the type for the values) and MORAL.
- Light moments: "= 1 has fooled more of us than anyone admits" (1:35), "a little flag that says: more to come" (2:40).

### Accuracy notes for the producer

- Wire types 1 and 5 (fixed 8 and 4 bytes) are mentioned in the lesson, not in the video; the zoom strip lists only 0
  and 2.
- "9 bytes" for the payment number and "10 bytes" for -1 as int64 count the value only; the lesson's demo prints 10 and
  11 with the one-byte key.
- MessagePack's 84 bytes and the bare list's 39 are from the previous lesson, as this section quotes them.
- The "Fern Bakery" bytes are cut after `42` with "…" as in the lesson; the full value is 11 bytes.
- Left to the next section: what an old reader does with an unknown field, forward and backward compatibility.
