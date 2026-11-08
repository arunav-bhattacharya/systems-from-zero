# Encoding, schema evolution, modes of dataflow, and durable execution (state as of 7 Nov 2026)

How to read the citations:
- **DDIA 2e** is *Designing Data-Intensive Applications*, 2nd edition, by Kleppmann and Riccomini. It is the local PDF at `/Users/arunav/Documents/learn/books & pdfs/architecture and software design/Designing Data-Intensive Applications ... (Martin Kleppmann, Chris Riccomini).pdf`. Chapter 5, "Encoding and Evolution", runs from printed p.161 to p.196 (PDF pp.185–220). Citations give the printed page and then the PDF page, for example "p.165 / PDF 189". Every DDIA point below is a paraphrase.
- **GitHub releases API** means `api.github.com/repos/<repo>/releases` (or `/tags`), queried on 7 Nov 2026. Each entry links to the repo's releases page.
- **[local check]** means a value I computed in Python during this session.
- **(not re-fetched)** marks a source I cite from prior knowledge of a stable standards document and did not open this session.

---

## 1. Why encode at all; language-specific serialization; JSON/XML/CSV problems; JSON Schema; binary JSON

### Takeaway
In memory, data is a web of objects tied together by pointers, and a pointer means nothing to another process. Anything written to disk or sent over a network therefore has to be flattened into self-contained bytes. Language-native serializers make this one line of code, but they are tied to one language, version badly, and are a long-running remote-code-execution vector. Java serialization is the textbook case: by Oracle's own estimate it is involved in roughly a third to a half of Java vulnerabilities. JSON is the lingua franca, yet it silently corrupts integers above 2^53, has no binary type (Base64 adds about 33%), and has no schema unless you add JSON Schema. Binary JSON variants save little: MessagePack encodes the DDIA example in 66 bytes against JSON's 81, because the field names still travel with every record.

### Cited Findings

**DDIA's framing**
- Programs hold data in two forms. In memory it lives in objects, structs, lists and hash tables, tuned for CPU access through pointers. For files and networks it must be a self-contained byte sequence, because "a pointer wouldn't make sense to any other process". Going from memory to bytes is *encoding* (also called serialization or marshaling). Going back is *decoding* (parsing, deserialization, unmarshaling). The book uses "encoding" because "serialization" also has a transactions meaning in Chapter 8 — DDIA 2e p.163–164 / PDF 187–188.
- Zero-copy formats such as Cap'n Proto and FlatBuffers are built to be used as-is at runtime and on disk or network, with no explicit conversion step — DDIA 2e p.164 / PDF 188.
- DDIA defines both compatibility directions. Backward compatibility means newer code can read data written by older code. Forward compatibility means older code can read data written by newer code. Forward is harder because old code has to ignore additions it cannot know about — DDIA 2e p.162 / PDF 186.
- For APIs, an old client calling a new service needs backward compatibility on the request and forward compatibility on the response. A new client calling an old service needs the reverse — DDIA 2e p.162 / PDF 186.

**Language-specific formats (Java `Serializable`, Python `pickle`, Ruby `Marshal`, Kryo)**
- *Problem solved:* saving and restoring objects with almost no code.
- *Where it breaks*, per DDIA:
  - The format is tied to one language.
  - Decoding has to instantiate arbitrary classes, which is a security hole: an attacker who controls the bytes can often get remote code execution.
  - Versioning is an afterthought.
  - Performance is poor; Java's built-in serialization is "notorious" for bad performance and bloated output.
  - DDIA concludes it is a bad idea for anything beyond very transient use — DDIA 2e p.164–165 / PDF 188–189.
- *Named incident:* Frohoff and Lawrence presented "Marshalling Pickles" at AppSecCali 2015. Public disclosure of the Apache Commons Collections gadget chain came in November 2015. Stephen Breen of Foxglove Security then used Frohoff's ysoserial tool against WebSphere, JBoss, Jenkins, WebLogic and OpenNMS, and Oracle shipped emergency WebLogic mitigations — [PCWorld](https://www.pcworld.com/article/424388/thousands-of-java-applications-vulnerable-to-nine-month-old-remote-code-execution-exploit.html). The WebLogic bug is CVE-2015-4852 — [Pwnies nominee write-up](https://pwnies.com/apache-commons-collections-java-object-deserialization-rce-in-weblogic-and-everything-else-in-the-world-cve-2015-4852/). DDIA cites the Foxglove post as ref [2] (p.193 / PDF 217).
- *Key teaching point, the gadget chain:* the exploit payloads only use classes already on the classpath, from Groovy, Spring or Commons Collections — [PCWorld](https://www.pcworld.com/article/424388/thousands-of-java-applications-vulnerable-to-nine-month-old-remote-code-execution-exploit.html).
  - Apache's fix (COLLECTION-580) disabled deserialization of `InvokerTransformer` in the 3.2 and 4.0 branches.
  - Apache also warned that this "is not the only known" usable gadget — [Apache Commons statement](https://news.apache.org/?p=4237).
  - A commonly missed nuance: an application is vulnerable only if it deserializes attacker-controlled data — [Veracode](https://veracode.com/blog/managing-appsec/lets-calm-down-about-apache-commons-collections).
- *Scale:* at Devoxx UK 2018, Mark Reinhold, then Oracle's chief Java platform architect, called serialization a "horrible mistake in 1997". He estimated that at least a third, and possibly half, of Java vulnerabilities have involved serialization, and called removing it a long-term goal — [InfoWorld](https://www.infoworld.com/article/3275924/oracle-plans-to-dump-risky-java-serialization.html); [ADTmag](https://adtmag.com/Articles/2018/05/30/java-serialization.aspx).
- *Improvement:* JEP 290, "Filter Incoming Serialization Data", delivered in Java 9.
  - A filter sees each object's class *before* instantiation and can allow or reject classes by pattern (`!` rejects, `pkg.*`, `pkg.**`).
  - It can also cap `maxdepth`, `maxrefs`, `maxbytes` and `maxarray`.
  - It is set process-wide with the `jdk.serialFilter` system or security property. JEP 415, "Context-Specific Deserialization Filters", is listed as related — [JEP 290](https://openjdk.org/jeps/290).
  - A cheat sheet lists backports to 8u121, 7u131 and 6u141 — [Java Deserialization Cheat Sheet](https://github.com/klausware/Java-Deserialization-Cheat-Sheet). The JEP page itself does not confirm the backports.
- DDIA also cites Brian Goetz's 2019 "Towards Better Serialization" (OpenJDK) as the record-based direction — DDIA 2e ref [4], p.193 / PDF 217.

**JSON, XML, CSV**
- DDIA's list of problems — DDIA 2e p.165–166 / PDF 189–190:
  - XML is verbose.
  - XML and CSV cannot tell a number from a string of digits without an external schema.
  - JSON separates strings from numbers, but not integers from floats, and it specifies no precision.
  - Integers above 2^53 cannot be represented exactly in an IEEE 754 double, so JavaScript parsers corrupt them. X (Twitter) post IDs are 64-bit, so its API returns each ID twice, once as a number and once as a decimal string.
  - Neither JSON nor XML has binary strings, so binary data travels as Base64, about one-third larger.
  - CSV has no schema, and its escaping is vague. RFC 4180 exists, but not all parsers follow it.
- Base64 makes data 4/3 ≈ 1.33× larger [local check]. 2^53+1 = 9007199254740993 parses as a double to 9007199254740992 [local check].
- RFC 8259 §6 warns that implementations commonly use IEEE 754 doubles, so only integers in [−(2^53)+1, 2^53−1] are interoperable — [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259#section-6) (not re-fetched).
- The Protobuf JSON mapping encodes `int64`/`uint64`/`fixed64` as decimal *strings* for this reason — [Protobuf JSON mapping](https://protobuf.dev/programming-guides/json/) (not re-fetched).
- DDIA's view is that JSON, XML and CSV will stay dominant for exchange *between organizations*, because getting organizations to agree on anything costs more than inefficiency does — DDIA 2e p.166 / PDF 190.

**JSON Schema**
- It is used in OpenAPI, in the Confluent and Apicurio registries, in PostgreSQL's `pg_jsonschema` and in MongoDB's `$jsonSchema`.
- It has primitive types plus a separate validation vocabulary, for example a port with minimum 1 and maximum 65,535.
- The content model is open by default (`additionalProperties: true`). A JSON Schema therefore mostly says what is *not* allowed.
- Integer-keyed maps need `patternProperties` plus `additionalProperties: false`.
- `if/else`, `$ref` to remote schemas and similar features make schemas powerful but hard to evolve compatibly. DDIA cites Andy Coates's 2024 "Evolving JSON Schemas" posts on this — DDIA 2e p.166–167 / PDF 190–191.
- *Current version:* json-schema.org lists **2020-12** as current, with 2019-09 before it — [json-schema.org/specification](https://json-schema.org/specification).
  - The project's process documents describe a new naming scheme with URLs like `json-schema.org/v1/2026/core.html`, meaning "version 1, release 2026" — [process overview mirror](https://www.mintlify.com/json-schema-org/json-schema-spec/process/overview).
  - One .NET library already ships a "v1 release 2026" meta-schema — [json-everything](https://docs.json-everything.net/api/JsonSchema.Net/MetaSchemas).
  - **Conflict:** the official specification page did not show v1/2026 as released on 7 Nov 2026, so treat 2020-12 as current.

**Binary JSON variants (MessagePack, CBOR, BSON, Smile…)**
- These formats extend the types (separate int and float, binary strings) but keep JSON's data model and have no schema. Every record therefore still carries every field name. None of them is as widely adopted as text JSON — DDIA 2e p.167 / PDF 191.
- *Worked example*, using DDIA's `{"userName":"Martin","favoriteNumber":1337,"interests":["daydreaming","hacking"]}`:
  - The first byte, `0x83`, means "map with 3 entries" (high nibble `0x80`, low nibble 3). `0xa8` means "string of 8 bytes".
  - Total is **66 bytes**, against 81 for minified JSON. DDIA doubts the small saving is worth losing readability — DDIA 2e p.168–169 / PDF 192–193.
  - Minified JSON is 81 bytes [local check]. Kleppmann's 2012 post says 82 bytes for the same record, presumably a whitespace difference — [Kleppmann 2012](https://martin.kleppmann.com/2012/12/05/schema-evolution-in-avro-protocol-buffers-thrift.html).
- CBOR is the IETF-standardized member of the family (RFC 8949, which obsoletes RFC 7049) — [RFC 8949](https://www.rfc-editor.org/rfc/rfc8949) (not re-fetched).
- Library version: msgpack-java v0.9.12, released 2026-05-03 — [GitHub releases API](https://github.com/msgpack/msgpack-java/releases).

### Inferences
- **Concept ladder for teaching:**
  - *Problem:* pointers don't cross process boundaries.
  - *Simplest fix:* `ObjectOutputStream`.
  - *Breaks:* CVE-2015-4852, plus Reinhold's one-third-to-half estimate.
  - *Next step:* language-neutral text (JSON).
  - *Breaks:* 2^53 IDs, Base64 bloat, no schema.
  - *Next step:* JSON Schema or binary JSON.
  - *Breaks:* field names still repeated (66 vs 81 bytes), and evolution rules are complex.
  - *Next step:* schema-driven binary formats (section 2).
- **Misconceptions to address:**
  1. "Serialization bugs are a Commons Collections bug." The root cause is deserializing untrusted bytes into arbitrary classes. The gadget is just whatever happens to be on the classpath.
  2. "JSON numbers are 64-bit." The spec sets no precision, and interoperability stops at 2^53.
  3. "Binary JSON is much smaller." The saving here was about 19%.
  4. "A JSON Schema lists what's allowed." By default it lists what is forbidden, because extra properties pass.
  5. "Backward compatible means old code can read new data." That is forward compatibility. Learners swap the two constantly, so drill the definitions with the API request/response rule.
- JEP 290 limits (`maxdepth`, `maxarray`) are also the right tool against deserialization *denial of service*, not just RCE. That makes a safe lab possible (section 7).

### Gaps
- I did not verify the JEP 290 backport releases on an Oracle or OpenJDK page; only a third-party cheat sheet lists them. I did not open JEP 415, so its delivery in Java 17 is unconfirmed.
- I did not fetch CBOR, BSON or Smile specs or size comparisons. I found no current adoption numbers for binary JSON formats.
- The JSON Schema "v1/2026" release status is ambiguous (see the conflict above).

---

## 2. Schema-driven binary formats (Protobuf, Avro, Thrift, FlatBuffers/Cap'n Proto, Arrow IPC), compatibility rules, schema registries

### Takeaway
Protobuf and Thrift identify each field by a *number* (its tag) and a wire type. Old readers can therefore skip unknown tags (forward compatibility), and new readers fill in defaults for missing ones (backward compatibility). The cardinal sin is reusing or retyping a tag number. Avro sends no tags at all: decoding needs the exact writer's schema, plus a reader's schema that Avro reconciles by field *name* using defaults. That suits dynamically generated schemas, but it means every reader must be able to find the writer's schema, through a file header, a registry ID or connection negotiation. Schema registries turn "compatibility" from a code-review opinion into an automated gate:
- Confluent defaults to BACKWARD (non-transitive) and recommends BACKWARD_TRANSITIVE for Protobuf.
- Buf's `buf breaking` defaults to FILE-level source compatibility and recommends WIRE_JSON as the minimum.

As of Nov 2026, Protobuf has moved from `proto2`/`proto3` to **editions**. Edition 2024 shipped in protoc v32 (2025), and edition 2026 is in development.

### Cited Findings

**Protocol Buffers: encoding**
- The DDIA record takes **33 bytes** in Protobuf, against 66 for MessagePack and 81 for JSON. Field names are replaced by tags 1, 2, 3. The type and tag are packed into one byte, and 1337 takes two bytes as a varint — DDIA 2e p.169–170 / PDF 193–194.
- DDIA says varints encode −64 to 63 in one byte and −8,192 to 8,191 in two — DDIA 2e p.170 / PDF 194. That is the ZigZag (`sint64`) behaviour. Plain `int64` encodes negatives in 10 bytes; see the next bullets.
- Varints take 1–10 bytes. Each byte uses its high bit as a continuation flag and carries 7 payload bits, least significant group first. 150 encodes as `96 01` — [Protobuf encoding guide](https://protobuf.dev/programming-guides/encoding/).
- Field key = `(field_number << 3) | wire_type`. The wire types are:

  | ID | Name | Used for |
  |---|---|---|
  | 0 | VARINT | int32, int64, uint32, uint64, sint32, sint64, bool, enum |
  | 1 | I64 | fixed64, sfixed64, double |
  | 2 | LEN | string, bytes, embedded messages, packed repeated fields |
  | 3 | SGROUP | group start (deprecated) |
  | 4 | EGROUP | group end (deprecated) |
  | 5 | I32 | fixed32, sfixed32, float |

  — [Protobuf encoding guide](https://protobuf.dev/programming-guides/encoding/)
- **Where naive ints break:** negative `int32`/`int64` values use two's complement, so they always take **10 bytes**. ZigZag (`sint32`/`sint64`) maps 0→0, −1→1, 1→2, −2→3 — [Protobuf encoding guide](https://protobuf.dev/programming-guides/encoding/). −1 as an int64 varint is `ff ff ff ff ff ff ff ff ff 01`, 10 bytes [local check].
- From Edition 2023, repeated scalars are packed by default. Parsers must accept both packed and unpacked forms — [encoding guide](https://protobuf.dev/programming-guides/encoding/).
- For non-repeated fields, the last value wins. Concatenating two encoded messages is the same as `MergeFrom` — [encoding guide](https://protobuf.dev/programming-guides/encoding/).
- A serialized message must be smaller than 2 GiB — [encoding guide](https://protobuf.dev/programming-guides/encoding/).
- Field numbers run from 1 to 536,870,911. Numbers 19,000–19,999 are reserved for the implementation, and fields 1–15 take one byte to encode — [proto3 guide](https://protobuf.dev/programming-guides/proto3/).
- Worked hex for the DDIA record [local check]. The 1337 varint is `b9 0a`.

  | Field | Bytes | Count |
  |---|---|---|
  | `user_name` | `0a 06 'Martin'` | 8 |
  | `favorite_number` | `10 b9 0a` | 3 |
  | `interests[0]` | `1a 0b 'daydreaming'` | 13 |
  | `interests[1]` | `1a 07 'hacking'` | 9 |
  | **Total** | | **33** (matches DDIA) |

**Protocol Buffers: evolution rules**
- You can rename a field, because names never appear on the wire. You cannot change a tag, because that invalidates all existing data — DDIA 2e p.171 / PDF 195.
- Forward compatibility comes from old code skipping unknown tags, using the type annotation to know how many bytes to skip. Old code *preserves* those bytes, which avoids the Figure 5-1 data-loss problem — DDIA 2e p.171 / PDF 195.
- Backward compatibility comes from defaults: an empty string or 0 when a field is missing — DDIA 2e p.171 / PDF 195.
- Never reuse a deleted tag; `reserved` it. Widening int32 to int64 is safe in one direction only, because old 32-bit readers truncate — DDIA 2e p.171 / PDF 195.
- Google's dos and don'ts — [Proto best practices](https://protobuf.dev/best-practices/dos-donts/):
  - Don't reuse a tag number, even if you think the field is unused. Old data in logs and old code on other servers still depend on it.
  - Reserve deleted numbers and names, and do the same for enum values.
  - Don't change a field's type. Don't change a default, because the two sides of the change will read unset values differently.
  - Repeated → scalar loses data. Scalar → repeated is OK in proto2, or in proto3 with `[packed=false]`.
  - Don't add `required`.
  - Include a `FOO_UNSPECIFIED = 0` enum value, and prefer an enum to a bool for any state that may grow.
  - Don't use text format or JSON for interchange, because renamed fields break old parsers.
  - Don't rely on byte-for-byte serialization stability, for example in cache keys.
  - Use separate messages for RPC APIs and for storage.
  - The page states that clients and servers are never updated at exactly the same time.
- Compatible scalar groups:
  - `int32`, `uint32`, `int64`, `uint64` and `bool` are mutually compatible.
  - `sint32`/`sint64` are compatible only with each other.
  - `string` and `bytes` are compatible if the bytes are valid UTF-8.
  - Enums are compatible with int32/uint32/int64/uint64.
  - Moving existing fields into an existing `oneof` is unsafe.
  - The first enum value must be zero, and unknown enum values are preserved.
  - With implicit presence you "cannot determine" whether a zero was set or omitted, so `optional` is recommended.
  — [proto3 guide](https://protobuf.dev/programming-guides/proto3/)
- **Historical change worth teaching:** early proto3 *discarded* unknown fields, which is exactly the Figure 5-1 bug. Protobuf 3.5.0 (Nov 2017) made C++, Java and Python preserve them by default, with Ruby and C# following in 3.5.1. Java code that wants the old behaviour must wrap its parser in `DiscardUnknownFieldsParser` — [protobuf CHANGES.txt](https://github.com/protocolbuffers/protobuf/blob/383a4941d5b1aa3c0afbdc24dd0e5d63d263fc3a/CHANGES.txt); [fuchsia mirror v3.5.2](https://fuchsia.googlesource.com/third_party/protobuf/+/v3.5.2/CHANGES.txt).

**Protocol Buffers: editions (changed since most textbooks, including DDIA, which shows `syntax = "proto3"` on p.169)**
- Editions replace the `syntax` line, for example `edition = "2024"`.
- Each edition is a bundle of *feature* defaults: `field_presence` (EXPLICIT / IMPLICIT / LEGACY_REQUIRED), `enum_type` (OPEN / CLOSED), `repeated_field_encoding` (PACKED / EXPANDED), `utf8_validation`, `enforce_naming_style`, `default_symbol_visibility` and others.
- Features can be overridden per file, message, field, enum and so on.
- The wire format does not change, so old data stays readable, but generated code can change.
- Edition 2023 merged proto2 and proto3 into one baseline. Edition 2024 added `import option`, `export`/`local` symbol visibility, and removed `import weak`, `ctype` and `java_multiple_files` (replaced by `nest_in_file_class`).
- Editions are planned roughly yearly.
— [Protobuf editions overview](https://protobuf.dev/editions/overview/)
- Edition 2024 shipped in protoc **v32**, with generator support for C++, Java, Kotlin, Python, Rust and others — [protobuf Google Group](https://groups.google.com/g/protobuf/c/32zrPYtpMzw); [v32.0 notes](https://newreleases.io/project/github/protocolbuffers/protobuf/release/v32.0).
- **Edition 2026 is in development.** The v36.0 notes (2026-08-20) say edition 2026 makes `default_symbol_visibility` STRICT and adds an `enforce_proto_limits` feature. One commit calls 2026 "the current (unreleased) edition" — [protobuf v36.0 release](https://github.com/protocolbuffers/protobuf/releases/tag/v36.0).
- **Versions:** protobuf v36.0 (2026-08-20), v36.1 (2026-08-31), **v36.2 (2026-09-17)**, and v37.0-rc1 (2026-10-15) — [GitHub releases API](https://github.com/protocolbuffers/protobuf/releases). The Java runtime numbering is `4.36.x`, per the "4.36-dev" string in `version.json` — [chromium mirror of version.json](https://chromium.googlesource.com/external/github.com/protocolbuffers/protobuf/+/refs/heads/36.x/version.json).

**Thrift**
- It came from Facebook, and most of what DDIA says about Protobuf applies to it — DDIA 2e p.169 / PDF 193.
- The example record takes 59 bytes in Thrift BinaryProtocol and 34 in CompactProtocol, against 33 for Protobuf and 32 for Avro — [Kleppmann 2012](https://martin.kleppmann.com/2012/12/05/schema-evolution-in-avro-protocol-buffers-thrift.html).
- Kleppmann's post also notes that `required` adds a runtime check. If a sender and receiver disagree about whether a field is required, the result is runtime errors — [Kleppmann 2012](https://martin.kleppmann.com/2012/12/05/schema-evolution-in-avro-protocol-buffers-thrift.html).
- Latest release: Apache Thrift **v0.25.0 (2026-09-30)**. Releases now come several times a year (0.23.0 Apr, 0.24.0 Jul, 0.25.0 Sep 2026) — [GitHub releases API](https://github.com/apache/thrift/releases).

**Avro**
- It started in 2009 as a Hadoop subproject because Protobuf fit Hadoop poorly. It has two schema languages, Avro IDL and JSON, and no tag numbers.
- The DDIA record takes **32 bytes**, the most compact of all. The bytes are just concatenated values, so nothing in the data identifies a field or its type.
- Decoding therefore needs the *exact* writer's schema — DDIA 2e p.172 / PDF 196.
- Worked bytes [local check]. Each count, length and union index is written as a zigzag varint.

  | Field | Bytes | Count |
  |---|---|---|
  | `userName` | `0c` + 'Martin' (length 6 → `0c`) | 7 |
  | `favoriteNumber` | `02` (union branch 1) + `f2 14` (1337 zigzag → 2674) | 3 |
  | `interests` | `04` (2 items) + `16` 'daydreaming' + `0e` 'hacking' + `00` (end of blocks) | 22 |
  | **Total** | | **32** |
- **Writer's vs reader's schema.** Resolution matches fields by *name*, and order may differ. A field only in the writer's schema is ignored. A field only in the reader's schema takes the reader's default, and with no default it is an error — DDIA 2e p.173–174 / PDF 197–198; [Avro spec](https://avro.apache.org/docs/++version++/specification/).
- **Evolution rules** — DDIA 2e p.175 / PDF 199:
  - Add or remove only fields that have defaults. Adding a field without a default breaks backward compatibility. Removing a field without a default breaks forward compatibility.
  - `null` is a valid default only if it is the first branch of a union.
  - Renaming via aliases is backward compatible but not forward compatible, and so is adding a union branch.
- **Spec detail** — [Avro spec](https://avro.apache.org/docs/++version++/specification/):
  - Allowed promotions are int→long/float/double, long→float/double, float→double, and string↔bytes.
  - An unknown enum symbol maps to the reader's enum `default`, if one is declared.
  - A union resolves to the reader's first matching branch.
  - **Object container file:** magic `Obj` followed by byte 1, a metadata map (`avro.schema` required, `avro.codec` optional), and a **16-byte sync marker**. Then come blocks: object count, byte size, data, sync marker. Codecs `null` and `deflate` are required; bzip2, snappy (with a CRC32 per block), xz and zstandard are optional.
  - **Single-object encoding:** marker `C3 01`, then an 8-byte little-endian CRC-64-AVRO fingerprint of the writer's schema, then the data.
  - **Parsing Canonical Form** normalizes schemas so they can be fingerprinted with SHA-256, CRC-64-AVRO (Rabin) or MD5. The spec says fingerprints carry no security guarantees.
- **How readers find the writer's schema** — DDIA 2e p.175–176 / PDF 199–200:
  - In a big file, the schema sits once in the header.
  - In a database of individually written records, each record carries a version number pointing into a schema table. Confluent Schema Registry and LinkedIn Espresso work this way.
  - On a network connection, the two sides negotiate the schema when the connection opens (Avro RPC).
- **Why no tags matters:** Avro suits *dynamically generated* schemas, such as dumping a relational database where each table becomes a record and each column a field. A schema change then just produces a new writer schema. Protobuf would need tag numbers assigned by hand, and they could never be reused — DDIA 2e p.176–177 / PDF 200–201.
- **Version:** Avro **1.12.2, announced 12 Aug 2026**. 1.12.1 came on 16 Oct 2025 and 1.12.0 in Aug 2024 — [Avro blog](https://avro.apache.org/blog/releases/); [Apache release catalog](https://release-catalog.apache.org/avro/index.html). The GitHub tag `release-1.12.2` shows 2026-08-23 — [GitHub releases API](https://github.com/apache/avro/releases). DDIA cites the 1.12.0 spec from Aug 2024 (ref [17]), so there is no conceptual change, only patch releases.

**The merits of schemas (DDIA)**
- Schema languages like Protobuf's and Avro's are simpler than JSON Schema or XML Schema. They have no regex or range validation, which is part of why they have wide language support.
- They descend from ASN.1 (1984), whose DER encoding still carries X.509 certificates. ASN.1 also evolves via tag numbers, but it is very complex — DDIA 2e p.177 / PDF 201.
- Benefits — DDIA 2e p.177–178 / PDF 201–202:
  - Encodings are compact because field names are omitted.
  - The schema is documentation that can't go stale, because decoding requires it.
  - A schema database lets you check compatibility *before deploy*.
  - Code generation catches type errors at compile time.

**Zero-copy formats: FlatBuffers, Cap'n Proto, Arrow IPC**
- FlatBuffers and Cap'n Proto are designed for use at runtime and on the wire with no conversion step — DDIA 2e p.164 / PDF 188.
- **Versions:**
  - FlatBuffers v25.12.19 (2025-12-19), re-tagged 2026-02-06 — [GitHub releases API](https://github.com/google/flatbuffers/releases).
  - Cap'n Proto's latest tag is v1.5.0; the date was not retrieved — [GitHub tags](https://github.com/capnproto/capnproto/tags).
- **Arrow IPC** — [Arrow columnar format spec](https://arrow.apache.org/docs/format/Columnar.html):
  - The *streaming* format is a schema message, then dictionary batches, then record batches, with an optional end-of-stream marker.
  - The *file* format adds the magic `ARROW1` at both ends and a footer of block offsets for random access.
  - Each message is a 4-byte `0xFFFFFFFF` continuation marker, a 4-byte little-endian metadata length, a FlatBuffers `Message`, padding to 8 bytes, and a body whose length is a multiple of 8.
  - Buffers need at least 8-byte alignment, and 64-byte alignment is recommended for SIMD.
  - Arrays are rebuilt by pointer arithmetic with "no memory copying".
  - Dictionary batches can be deltas (`isDelta`) or replacements. The file format allows only one non-delta dictionary per ID.
- **Arrow versions:** Apache Arrow **26.0.1 (2026-11-03)** and 26.0.0 (2026-10-09). Arrow Java is released separately, with **v19.0.0 on 2026-03-16** — [GitHub releases API: arrow](https://github.com/apache/arrow/releases); [arrow-java](https://github.com/apache/arrow-java/releases).

**Schema registries and compatibility modes**
- **Confluent Schema Registry** — [Confluent schema evolution docs](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html):
  - The default mode is **BACKWARD, and it is non-transitive**: a new schema is checked only against the latest version.
  - BACKWARD and BACKWARD_TRANSITIVE: upgrade all **consumers first**.
  - FORWARD and FORWARD_TRANSITIVE: upgrade **producers first**, and make sure old-schema data is gone before upgrading consumers.
  - FULL and FULL_TRANSITIVE: upgrade in any order.
  - NONE: no checks.
  - Kafka Streams supports only the BACKWARD, BACKWARD_TRANSITIVE, FULL and FULL_TRANSITIVE modes.
  - The docs recommend BACKWARD_TRANSITIVE for Protobuf, "as adding new message types is not forward compatible".
  - For JSON Schema under the STRICT policy, a closed content model (`additionalProperties: false`) forbids adding or removing required fields. An open model allows more changes.
- The earlier course research already summarized the allowed-changes matrix (adding or removing optional fields and so on) — [prior notes, kafka.md](../Systems%20course%20curriculum%20research/kafka.md). That research also recorded image `confluentinc/cp-schema-registry:8.4.0`, pushed 2026-10-26 — [Docker Hub tags](https://hub.docker.com/v2/repositories/confluentinc/cp-schema-registry/tags?page_size=15) (from prior notes).
- **Confluent wire format** — [Confluent serdes docs](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html):
  - **Payload-prefix form:** magic byte `0`, a 4-byte big-endian schema ID, and then the payload. For Protobuf, a zigzag-varint "message indexes" array sits between them; a single top-level message is encoded as one `0` byte.
  - **New since Confluent Platform 8.1.1:** the schema GUID can travel in a Kafka *header* instead (`__key_schema_id` / `__value_schema_id`). The header value is a version byte `1` plus a 16-byte GUID. You enable it with `value.schema.id.serializer=...HeaderSchemaIdSerializer`.
  - Deserializers check the header first and fall back to the payload prefix, which supports rolling upgrades.
  - Caveat: Kafka Streams state stores dropped headers before 8.3, and switching from ID to GUID changes key partitioning.
  - **Subject strategies:** `TopicNameStrategy` (the default, `<topic>-value`), `RecordNameStrategy` and `TopicRecordNameStrategy`.
  - `auto.register.schemas` is on by default. For production the docs suggest `auto.register.schemas=false` with `use.latest.version=true`; `latest.compatibility.strict` defaults to true.
- **Apicurio Registry** (Red Hat): latest **3.3.4 (2026-11-03)** — [GitHub releases API](https://github.com/Apicurio/apicurio-registry/releases). DDIA names it alongside Confluent's registry as a JSON Schema host — DDIA 2e p.166 / PDF 190.
- **Buf `buf breaking`** — [Buf breaking rules](https://buf.build/docs/breaking/rules/):
  - **FILE** is the default. It protects generated source per file and is described as necessary for C++ and Python.
  - **PACKAGE** allows moving types between files within a package.
  - **WIRE_JSON** protects binary plus JSON encoding. It is recommended as the minimum, especially for Connect or gRPC JSON.
  - **WIRE** protects binary only.
  - Example rules: `FIELD_NO_DELETE`, `FIELD_SAME_TYPE`, `FIELD_NO_DELETE_UNLESS_NAME_RESERVED`, `FIELD_NO_DELETE_UNLESS_NUMBER_RESERVED`, `FIELD_WIRE_COMPATIBLE_TYPE` (int32→int64 OK) and `RESERVED_ENUM_NO_DELETE`.
  - Latest buf CLI: **v1.75.0 (2026-10-22)** — [GitHub releases API](https://github.com/bufbuild/buf/releases).

### Inferences
- **Concept ladder:**
  - *Problem:* JSON repeats field names and has no enforced contract.
  - *Simplest fix:* put a number on each field (Protobuf/Thrift).
  - *Breaks:* when someone reuses a number. The real-world analogue is Knight Capital's repurposed flag (section 3), and Google's own guidance warns old servers "will break".
  - *Improvement:* `reserved`, plus `buf breaking` in CI.
  - *Alternative design:* no numbers at all (Avro). This needs the writer schema at read time, which in turn needs a registry, and that brings modes and upgrade order.
- **What "compatibility mode" means operationally:** BACKWARD means "consumers upgrade first". People routinely flip that, so teach the mode name together with the deploy order.
- **Non-transitive trap:** under the default BACKWARD, v3 is checked only against v2. A chain of individually compatible steps can therefore leave v3 unable to read v1 data still sitting in a compacted topic or a database. Use the *_TRANSITIVE modes whenever old data is retained.
- **Misconceptions:**
  1. "Protobuf `required`/defaults make data safe." Proto3 can't distinguish 0 from unset under implicit presence, and changing a default is itself a breaking change.
  2. "int32→int64 is always safe." It is safe only for new readers; old readers truncate.
  3. "Avro embeds the schema in every message." It does not, except with single-object encoding, which embeds only an 8-byte fingerprint.
  4. "Registry compatibility == runtime safety." The registry checks schemas, not semantics: renaming meaning without changing types passes every check.
  5. "Editions changed the wire format." They did not; only feature defaults and codegen changed.
- The proto3 unknown-field history (dropped in 3.0–3.4, preserved again from 3.5) is a ready-made "where it broke" example for Figure 5-1, with a real fix in a real release.

### Gaps
- I did not retrieve Apicurio's compatibility-rule semantics, or whether they match Confluent's exactly. I did not research Buf Schema Registry features (hosting, breaking-change policies, pricing) in 2026.
- No release date found for Cap'n Proto v1.5.0.
- I found no official date for edition 2026 GA; it appears still unreleased as of v36/v37-rc1.
- The Confluent allowed-changes matrix was hard to read from the flattened page. The authoritative table needs a manual look.
- I found no public, named production outage caused specifically by Protobuf tag reuse. Google's guidance describes the risk only hypothetically.

---

## 3. Dataflow through databases: "data outlives code", rolling upgrades, migrations (expand/contract)

### Takeaway
Writing to a database is "sending a message to your future self", so backward compatibility is mandatory. During a rolling upgrade, old and new code share the database at the same time, so forward compatibility matters too. An old service that reads a record, updates it and writes it back will silently delete fields it doesn't know about, unless its model preserves unknown fields. Data written five years ago is still in its original encoding ("data outlives code"). Large reshapes therefore go through multi-phase expand/contract migrations. Stripe's version is four phases: dual-write, switch reads, switch writes, delete old. The most expensive mixed-version incident on record is Knight Capital (2012). One of eight servers kept old code while a flag was repurposed, and the firm lost more than $460 million in 45 minutes.

### Cited Findings
- **DDIA on databases** — DDIA 2e p.178–180 / PDF 202–204:
  - The writer encodes and the reader decodes, and the reader may simply be a later version of the same process, hence the "message to your future self" image.
  - Many processes share a database, and a rolling upgrade leaves some on new code and some on old. A value written by new code can therefore be read by old code, so forward compatibility is often required.
  - "Data outlives code": the database may hold values written 5 ms ago next to values written 5 years ago. A deployment replaces code in minutes, but the data stays in its original encoding unless it is rewritten.
  - Rewriting is expensive, so databases defer it. LSM compaction rewrites into the latest format, and adding a nullable column needs no rewrite, because nulls are filled in at read time.
  - Complex changes still need application-level rewrites, for example single-valued → multivalued, or splitting data into a new table. DDIA cites Stripe's "Online Migrations at Scale" here.
  - DDIA calls keeping forward and backward compatibility across such migrations an open research problem, citing Project Cambria (2020) on lenses.
  - Archival dumps are usually written in the latest schema, a good fit for Avro container files or Parquet.
- **The Figure 5-1 hazard:** suppose new code adds a field and writes a record, and old code then reads, updates and writes it back. If the record was decoded into a model object that doesn't preserve unknown fields, the new field is lost — DDIA 2e p.162–163 / PDF 186–187. The same caution applies to consumers that republish messages — DDIA 2e p.191 / PDF 215.
- **Google's advice:** use different message types for storage and for APIs, with a translation layer, so storage formats can change without touching external clients — [Proto dos and don'ts](https://protobuf.dev/best-practices/dos-donts/).
- **Named incident: Knight Capital, 1 Aug 2012**, from the SEC order (Release 34-70694, 16 Oct 2013) — [SEC order PDF](https://www.sec.gov/files/litigation/admin/2013/34-70694.pdf); [SEC press release](https://www.sec.gov/newsroom/press-releases/2013-222):
  - New Retail Liquidity Program (RLP) code was meant to replace long-unused "Power Peg" code, and it **repurposed a flag** that used to activate Power Peg.
  - The code went out in stages over successive days. A technician **did not copy it to one of the eight SMARS servers**, and no second technician reviewed the deployment.
  - On that eighth server the flag therefore triggered Power Peg. While it handled 212 small retail orders, SMARS sent millions of orders in **45 minutes**, with over **4 million executions in 154 stocks** and **more than 397 million shares**.
  - Knight ended with about $3.5 billion net long in 80 stocks and about $3.15 billion net short in 74 stocks, and **lost over $460 million**.
  - 97 automated error emails went out before the open, and nobody acted on them. The penalty was $12 million.
- **Stripe, "Online migrations at scale"** (Jacqueline Xu, 2 Feb 2017) — [Stripe blog](https://stripe.com/blog/online-migrations):
  - The four steps:
    1. **Dual-write** to the old and new stores, and backfill.
    2. **Change reads** to the new store, checked with GitHub's Scientist, which compares old and new read paths in production.
    3. **Change writes** to the new store only.
    4. **Remove** the old data.
  - The example moved subscriptions from a field (later an array) on Customer into their own table, covering "hundreds of millions" of Subscription objects.
  - Doing it one object per second would take over **3 years per 100 million**. Stripe used Hadoop with MapReduce/Scalding on snapshots to find the records to migrate.
- **Expand/contract (ParallelChange):** expand to support both old and new, migrate clients, then contract to remove the old — [Fowler bliki, ParallelChange (Danilo Sato, 2014)](https://martinfowler.com/bliki/ParallelChange.html) (not re-fetched).
- **Lab database:** the prior research pinned PostgreSQL 18.6 for labs. PG 18.0 shipped 25 Sep 2025, and PG 14 reaches end of life on 12 Nov 2026 — [prior report](../../reports/Systems%20course%20curriculum%20research.md), citing [PostgreSQL versioning](https://www.postgresql.org/support/versioning/).

### Inferences
- **Concept ladder:**
  - *Problem:* code changes while data persists.
  - *Simplest approach:* stop the world, migrate, then deploy.
  - *Breaks:* downtime grows with data size (Stripe: more than 3 years per 100M records at 1 per second), and rolling deploys are the norm anyway.
  - *Improvement 1:* additive, nullable changes that old code ignores and new code defaults.
  - *Breaks:* when old code round-trips records and drops fields (Figure 5-1), or when a field or flag is repurposed (Knight).
  - *Improvement 2:* expand/contract with dual-writes, shadow reads (Scientist) and a contract step only after every reader and writer has upgraded.
- **Knight teaches three things at once:**
  1. A rolling or staged deploy creates a mixed-version fleet whether you plan for it or not.
  2. *Repurposing* an identifier is the database and flag equivalent of reusing a Protobuf tag. Same bits, new meaning, no error.
  3. Dead code that is still callable is part of your compatibility surface.
- **Misconceptions:**
  1. "Adding a column is always safe." It is safe for schema, but ORMs that select `*` into fixed records, or that write whole rows back, can null out or drop new data.
  2. "Migrations are a deploy step." At scale they are a weeks-long, multi-deploy *process*.
  3. "Schemaless databases avoid migrations." They defer the migration to read time, so every reader must handle every historical shape (DDIA's schema-on-read framing, p.161 / PDF 185).

### Gaps
- I did not fetch PostgreSQL docs on which `ALTER TABLE` forms avoid a table rewrite, such as `ADD COLUMN ... DEFAULT` with a non-volatile default. The writer should verify this against PG 18 docs before stating it.
- I did not research online schema-change tools (gh-ost, pg-osc, pgroll) or their 2026 versions.
- I did not open Project Cambria (DDIA ref [29]).

---

## 4. Dataflow through services: REST/OpenAPI, RPC history and fallacies, gRPC/Connect, GraphQL, versioning, idempotency keys, discovery, load balancers, meshes

### Takeaway
A network call is not a function call:
- It can time out with an *unknown* outcome.
- A retry can execute the action twice.
- Latency varies by orders of magnitude.
- Arguments must be encoded.
- Types differ across languages.

These points have been made since Waldo et al. (1994) and the eight fallacies (Deutsch 1994, Gosling 1997). REST treats network state transfer as its own thing. gRPC and Connect bring Protobuf contracts back but expose deadlines and status codes. gRPC's long-lived HTTP/2 connections defeat L4 load balancers, so balancing must happen per request, at L7 or in the client. Since services usually deploy before clients, requests need backward compatibility and responses need forward compatibility. Public APIs live "perhaps indefinitely", which is why Stripe pins each account to a dated version and transforms responses backwards. Retries are made safe with client-generated idempotency keys. Stripe's keys are up to 255 characters, prunable after 24 hours, and accepted on POST only.

### Cited Findings

**DDIA's framing of services**
- A service is a server's API. Unlike a database, which accepts arbitrary queries, a service exposes application-specific inputs and outputs, which gives encapsulation (citing Helland's "Data on the Outside vs Data on the Inside").
- In microservices, each team releases independently, so old and new clients and servers coexist and encodings must stay compatible — DDIA 2e p.180–181 / PDF 204–205.
- REST builds on HTTP principles: URLs identify resources, and HTTP handles caching, authentication and content negotiation (Fielding's 2000 thesis; "REST APIs must be hypertext-driven", 2008).
- The two most popular service IDLs are **OpenAPI** (Swagger) for JSON web services and **Protocol Buffers** for gRPC — DDIA 2e p.181 / PDF 205.
- DDIA's OpenAPI example uses `openapi: 3.0.0` with a FastAPI implementation. Some frameworks are code-first (FastAPI generates the IDL) and some are definition-first (gRPC generates scaffolding). Both can generate clients, documentation and compatibility checks — DDIA 2e p.182–183 / PDF 206–207.
- **Compatibility for RPC:** assume servers update first and clients second. Then requests need backward compatibility and responses need forward compatibility.
  - gRPC and Avro RPC inherit the rules of their encoding.
  - For JSON REST, adding optional request parameters and adding response fields usually count as compatible.
  - Across organizations the provider can't force upgrades, so compatibility may be needed "perhaps indefinitely", which leads to multiple API versions running side by side — DDIA 2e p.186 / PDF 210.
- **API versioning has no consensus.** Options include a version in the URL, in the `Accept` header, or stored server-side per API key and changed through an admin interface (Stripe). DDIA cites Troy Hunt's "three different wrong ways" (2014) — DDIA 2e p.186 / PDF 210.

**OpenAPI and GraphQL status (newer than DDIA's examples)**
- **OpenAPI 3.2.0** was released in Sep 2025: GitHub tag 2025-09-19, announced 23 Sep 2025. It is backward compatible with 3.1 and adds:
  - Formal streaming support (`itemSchema` for sequential and streamed items).
  - The HTTP **QUERY** method and `additionalOperations` for other methods.
  - A `querystring` parameter location.
  - The OAuth 2.0 Device Authorization flow.
  - Hierarchical tags.

  Swagger tooling support arrived in Apr 2026 — [Nordic APIs](https://nordicapis.com/whats-new-in-openapi-specification-v3-2-0/); [Swagger blog](https://swagger.io/blog/swagger-launches-support-for-openapi-3-2-0/). **3.2.1** is tagged 2026-09-10 — [GitHub releases API](https://github.com/OAI/OpenAPI-Specification/releases). DDIA cites 3.1.0 (ref [33]) and shows a 3.0.0 example.
- **GraphQL:** the **September 2025 edition** is the first spec release since October 2021. It adds `@oneOf` input objects, schema coordinates and descriptions on executable documents, from 30 contributors and more than 100 changes — [GraphQL blog](https://graphql.org/blog/2025-09-08-september-edition/); [GitHub release](https://github.com/graphql/graphql-spec/releases/tag/September2025). DDIA covers GraphQL as a query language in Ch. 3 ("GraphQL" section, PDF p.122 per the outline, so roughly printed p.98), not in Ch. 5.

**History and critique of RPC**
- EJB and Java RMI work only in Java, and DCOM only on Microsoft platforms. CORBA was excessively complex, with no backward or forward compatibility. SOAP/WS-* suffered from complexity and compatibility problems.
- All of these build on RPC, which dates from the 1970s (DDIA cites Birrell & Nelson, ACM TOCS 1984) and aims for **location transparency** — DDIA 2e p.183 / PDF 207.
- **Why the abstraction is flawed** — DDIA 2e p.183–184 / PDF 207–208:
  - A network request can be lost, or the remote machine can be slow.
  - A timeout leaves you not knowing whether the request ran.
  - Retrying can execute the action twice unless the protocol has deduplication (idempotence).
  - Latency ranges from under 1 ms to seconds.
  - Parameters must be encoded, which is awkward for big or mutable objects.
  - Cross-language type mapping is lossy (JavaScript and 2^53 again).
  - Part of REST's appeal is that it treats state transfer as different from a function call.
- **Waldo, Wyant, Wollrath, Kendall, "A Note on Distributed Computing"** (Sun Labs TR-94-29, Nov 1994; DDIA ref [39]):
  - The paper rejects the "unified objects" vision that local and remote objects can be treated the same.
  - It names the differences: **latency, memory access** (pointers aren't valid in another address space), **partial failure** (a dead link looks like a dead peer) and **concurrency**.
  - It concludes that interfaces must expose these differences at every stage of design.
  — [Waldo's Harvard page](https://waldo.scholars.harvard.edu/publications/note-distributed-computing); [freeCodeCamp summary](https://www.freecodecamp.org/news/a-note-on-distributed-systems-3c796f1eb0a0/); [econner outline](https://econner.github.io/2013/09/a_note_on_distributed_computing.html). These are secondary summaries; the original PDF returned 403/404.
- **Fallacies of distributed computing.** L. Peter Deutsch compiled seven in **1994**, building on four from Bill Joy and "Dave" Lyon; James Gosling added the eighth around **1997**. The list:
  1. The network is reliable.
  2. Latency is zero.
  3. Bandwidth is infinite.
  4. The network is secure.
  5. Topology doesn't change.
  6. There is one administrator.
  7. Transport cost is zero.
  8. The network is homogeneous.

  — [Wikipedia](https://en.wikipedia.org/wiki/Fallacies_of_distributed_computing). Note that Wikipedia currently says "Dave Lyon", while the task brief and other tellings say Tom Lyon; check before printing.

**gRPC and Connect**
- **gRPC load balancing.** gRPC multiplexes many RPCs on one long-lived HTTP/2 connection, so an L3/L4 balancer, which decides once per *connection*, pins all of a client's calls to one backend.
  - An L7 balancer can spread a client's *streams* across backends.
  - The options are a proxy at L4 or L7, thick client-side balancing, or a lookaside balancer — [gRPC blog, "gRPC Load Balancing" (17 Jun 2017)](https://grpc.io/blog/grpc-load-balancing/).
- **The Kubernetes form of the problem.** kube-proxy balances per connection, so gRPC traffic piles onto one pod. Fixes:
  - An L7 mesh or proxy (Linkerd, Istio, Envoy).
  - Client-side round-robin over a *headless* Service (`clusterIP: None`).
  - Max connection age as a mitigation.

  — [Kubernetes blog, William Morgan, 7 Nov 2018](https://kubernetes.io/blog/2018/11/07/grpc-load-balancing-on-kubernetes-without-tears/). Only the title, author and date came from the page; the fix list is the tool's background summary, so verify it against the article body.
- **Versions:**
  - grpc-java **1.85.1 (2026-10-20)**.
  - gRPC core **1.85.1 (2026-10-30)**, with patch releases on older lines into November.
  - grpc-kotlin **1.5.0 (2025-09-16)**, which has had no release since.

  — [GitHub releases API: grpc-java](https://github.com/grpc/grpc-java/releases), [grpc](https://github.com/grpc/grpc/releases), [grpc-kotlin](https://github.com/grpc/grpc-kotlin/releases)
- **Connect RPC** (made by Buf; a CNCF sandbox project) — [Connect docs](https://connectrpc.com/docs/introduction/):
  - Servers speak **gRPC, gRPC-Web and the Connect protocol**, and clients default to Connect.
  - The Connect protocol works over HTTP/1.1, HTTP/2 and HTTP/3, and plain `curl` with JSON works.
  - Language status: Go, TypeScript and Swift are stable; **Kotlin and Python are beta**; Rust is pre-1.0.
  - Versions: **connect-go v2.0.2 (2026-10-21)**, a new major (v2.0.0 in Oct 2026 with a `connect-go-v2-migrate` tool), and **connect-kotlin v0.10.0 (2026-10-22)** — [GitHub releases API: connect-go](https://github.com/connectrpc/connect-go/releases), [connect-kotlin](https://github.com/connectrpc/connect-kotlin/releases).

**Versioning at scale: Stripe**
- Stripe uses rolling **date-named** versions, for example `2017-05-24`. An account is **pinned on its first request**, and a `Stripe-Version` header overrides the pin for one request. Resolution order is header, then OAuth app version, then the account pin.
- Each backwards-incompatible change is a **version change module**. Responses are generated at the current version, and the modules are applied *in reverse* until the target version is reached.
- Changes with side effects beyond the response are flagged and harder to support.
- Stripe had kept compatibility with every version since 2011, through "almost a hundred backwards-incompatible upgrades over the past six years" — [Stripe blog, Brandur Leach, 5 Aug 2017](https://stripe.com/blog/api-versioning).
- **Changed since 2024:** starting with `2024-09-30.acacia`, Stripe ships **monthly non-breaking** versions, and only **twice-yearly named major releases** (Acacia, Basil, …) may break — [Stripe API versioning docs](https://docs.stripe.com/api-versions). The search tool reported `2026-09-30.endive` as the current version on the main page, while other pages showed `2026-07-29.dahlia`. Verify on the page before quoting a current version.

**Idempotency keys**
- **Stripe API rules** — [Stripe docs, Idempotent requests](https://docs.stripe.com/api/idempotent_requests):
  - The client generates the key; a V4 UUID or other high-entropy string is recommended, and sensitive data such as emails should not be used.
  - Keys are **up to 255 characters**.
  - Under API v1, Stripe stores the status code and body of the first request *once endpoint execution begins*, and replays it, **including 500s**.
  - Keys can be pruned once they are **at least 24 hours old**; a reused key after pruning is treated as a new request.
  - Reusing a key with different parameters is an error.
  - Requests that fail validation, or conflict with a concurrent request, are not stored and can be retried.
  - **All POSTs** accept keys. GET and DELETE are idempotent by definition, so a key has no effect.
  - Under API v2, retries drive failed or partial work to completion instead of replaying a stored error.
- **How to build it: Brandur Leach, "Implementing Stripe-like Idempotency Keys in Postgres" (27 Oct 2017)** — [brandur.org](https://brandur.org/idempotency-keys):
  - *Foreign state mutations*, such as charging a card, sending email or writing to Kafka, can't be rolled back. Local work is split into **atomic phases**, each a `SERIALIZABLE` transaction committed between foreign calls.
  - Each phase records a **recovery point** (`started` → `ride_created` → `charge_created` → `finished`) on an `idempotency_keys` row. The row holds `locked_at`, the request method, path and params (JSONB), the response code and body, and a unique index on (user, key).
  - Concurrent use of a key gets **409 Conflict**.
  - A *completer* process finishes abandoned requests, and a *reaper* deletes keys after about 72 hours.
  - The foreign call carries its own idempotency key downstream, so a crash while waiting on Stripe can't double-charge.
  - Non-ACID stores can't implement atomic phases.
- **Standardization:** IETF `draft-ietf-httpapi-idempotency-key-header`. Revision **-07** was posted 2025-10-15 and marked expired 2026-04-18 on Datatracker. Editor's copies dated 2026 exist, but I could not confirm a newer published revision. **It is not an RFC** — [Datatracker history](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/history/); [draft text](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header).

**Service discovery, load balancers, meshes**
- **DDIA's progression** — DDIA 2e p.184–186 / PDF 208–210:
  - Hard-coding an IP and port breaks when a server moves.
  - Hardware load balancers.
  - Software load balancers (NGINX, HAProxy).
  - DNS with multiple A records, where caching and slow propagation mean clients can see stale IPs.
  - Discovery registries (etcd, ZooKeeper): instances register host, port and metadata such as shard ownership and datacenter, and send heartbeats. Clients look up endpoints and connect directly, which allows smarter balancing.
  - **Service meshes**: a client library or sidecar on both sides handles TLS and observability. Common on Kubernetes (Istio, Linkerd); simpler deployments should stay with software load balancers.
- **Versions (Nov 2026):**
  - Istio **1.31.4 (2026-11-06)**, with 1.32.0-rc.2 out.
  - Linkerd **edge-26.11.1 (2026-11-02)**. The open-source project ships only edge releases.
  - Envoy **1.40.2 (2026-10-27)**.

  — [GitHub releases API: istio](https://github.com/istio/istio/releases), [linkerd2](https://github.com/linkerd/linkerd2/releases), [envoy](https://github.com/envoyproxy/envoy/releases)
- The networking research for this course covers L4 vs L7 balancing, the PROXY protocol and Envoy terminology, so don't repeat it here — [prior networking notes](../Systems%20course%20curriculum%20research/networking.md).

### Inferences
- **Concept ladders:**
  - *RPC:*
    - *Problem:* call code on another machine.
    - *Simplest:* a local-looking stub (RMI/CORBA).
    - *Breaks:* timeouts with unknown outcome, duplicate execution on retry, latency spikes (Waldo; the fallacies).
    - *Improvement:* make the network explicit. Use deadlines, status codes, idempotency keys, and contract-first IDLs with compatibility checks.
  - *Load balancing:*
    - *Simplest:* DNS or an L4 balancer.
    - *Breaks:* stale DNS, and gRPC pinning on long-lived HTTP/2.
    - *Improvement:* per-request L7 balancing, a mesh, or client-side round-robin over discovered endpoints.
  - *Versioning:*
    - *Simplest:* `/v1/` → `/v2/`.
    - *Breaks:* every major forks the code base, and clients never migrate.
    - *Improvement:* additive evolution by default, plus per-client pinning and backward transforms (Stripe), with breaking changes batched twice a year.
  - *Retries:*
    - *Simplest:* "just retry".
    - *Breaks:* double charges.
    - *Improvement:* idempotency keys, which need atomic storage of key and result, parameter fingerprinting, conflict handling and an expiry policy.
- **Misconceptions:**
  1. "REST means JSON over HTTP with nice URLs." Fielding's constraint includes hypertext.
  2. "gRPC is just faster REST." Its connection model changes load balancing, and browsers need gRPC-Web or Connect.
  3. "An idempotency key makes any endpoint safe." Only if the server checks and stores atomically, rejects parameter mismatches, and the client retries *within the retention window* (24 h at Stripe).
  4. "PUT and DELETE are safe to retry, so all is fine." They are idempotent in HTTP semantics, but a server implementation can still have side effects.
  5. "A service mesh makes the network reliable." It moves retries, TLS and balancing into infrastructure, but can't remove partial failure.
- GraphQL's answer to versioning is to evolve a single schema by adding fields and deprecating old ones. The Sept 2025 `@oneOf` addition is itself an evolution-friendly input pattern. (The deprecation philosophy is not sourced here; see Gaps.)

### Gaps
- I could not open the original Waldo et al. PDF (403/404). One secondary summary says a remote call is "four to five times slower" than a local one. That figure is suspect, and the writer should check the original's wording on the size of the latency difference before using any number.
- I did not fetch gRPC docs on deadlines, status codes, retry and hedging policy, or xDS proxyless balancing, nor gRPC JSON transcoding.
- I did not fetch GraphQL best-practice guidance on versioning, deprecation, persisted queries or N+1 with DataLoader; those statements above are unsourced framing.
- I did not check Istio ambient-mode or Linkerd release-model specifics in 2026.
- I could not confirm the current Stripe API version string (endive vs dahlia).

---

## 5. Dataflow through messages: brokers, event-driven architecture, actors

### Takeaway
With a broker in the middle:
- The sender doesn't wait.
- The broker buffers, redelivers and fans out.
- Senders don't need discovery.

None of this removes the encoding problem. Messages are opaque bytes, so teams pair brokers with Protobuf, Avro or JSON plus a schema registry, or describe them with AsyncAPI. A consumer that republishes must preserve unknown fields. Distributed actor frameworks (Akka/Pekko, Orleans, Erlang/OTP) apply location transparency to messages, and this works better than in RPC because actors already assume messages can be lost. Rolling upgrades still need compatible message encodings.

### Cited Findings
- **Event-driven architecture** — DDIA 2e p.189–190 / PDF 213–214:
  - Messages, or events, go through a broker (also called an event broker, message queue or message-oriented middleware) that stores them temporarily.
  - Advantages: buffering when the recipient is down or overloaded, automatic redelivery after a crash, no service discovery, fan-out to many recipients, and logical decoupling.
  - The model is asynchronous fire-and-forget. RPC-style request/response can be layered on top with a reply channel.
- **Broker landscape and patterns** — DDIA 2e p.190 / PDF 214:
  - Commercial products came first (TIBCO, IBM WebSphere, webMethods), then open source (RabbitMQ, ActiveMQ, HornetQ, NATS, Redpanda, Kafka), then cloud services (Kinesis, Azure Service Bus, Google Pub/Sub). The detailed comparison is in DDIA Ch. 12.
  - Two patterns: a **queue**, where one consumer gets each message, and a **topic**, where every subscriber gets it.
  - Brokers impose no data model, so the common practice is Protobuf, Avro or JSON plus a schema registry. **AsyncAPI** is the messaging counterpart of OpenAPI.
  - Durability varies. Many brokers delete messages once consumed, and event sourcing needs indefinite retention.
- **Republishing consumers must preserve unknown fields** (the Figure 5-1 problem again) — DDIA 2e p.191 / PDF 215.
- **Actors** — DDIA 2e p.191 / PDF 215:
  - Each actor has private state and processes one message at a time, which avoids locks. Delivery is not guaranteed.
  - Distributed frameworks (Akka, Orleans, Erlang/OTP) use the same message passing across nodes, with encoding done transparently.
  - Location transparency works better here than in RPC because loss is already assumed.
  - Rolling upgrades still need forward and backward compatible message encodings. DDIA cites the Orleans "virtual actors" MSR technical report (2014).
- **Versions:**
  - Microsoft Orleans **v10.4.2 (2026-10-30)** — [GitHub releases API](https://github.com/dotnet/orleans/releases).
  - Apache Pekko, the Apache-licensed fork of Akka: the GitHub tag list's newest entry is `v2.0.0` — [GitHub tags](https://github.com/apache/pekko/tags). The Apache catalog shows 2.0.0-M3 from May 2026, and the 2.0 release notes describe the milestones as experimental — [Pekko 2.0 release notes](https://pekko.apache.org/docs/pekko/2.0/release-notes/releases-2.0.html); [Apache release catalog](https://release-test.apache.org/api/cle/release/pekko/2.0.0-m3). **Conflict:** I could not confirm a GA announcement for Pekko 2.0.0.
  - Apache Kafka 4.4.0 was announced 22 Oct 2026 — [prior Kafka notes](../Systems%20course%20curriculum%20research/kafka.md), citing [Kafka blog](https://kafka.apache.org/blog/2026/10/22/apache-kafka-4.4.0-release-announcement/).
- **Header-borne schema IDs** (Confluent Platform 8.1.1+) change how messages carry their writer schema. Kafka Streams state stores dropped headers before 8.3 — [Confluent serdes docs](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html). This is a concrete example of metadata lost by an intermediate hop.

### Inferences
- **Concept ladder:**
  - *Problem:* synchronous RPC couples availability, because if B is down, A fails.
  - *Simplest fix:* put a queue between them.
  - *Breaks:*
    - Duplicates on redelivery, which means at-least-once delivery and idempotent consumers.
    - Ordering only within a partition.
    - Poison messages.
    - The dual-write problem when a service updates its database *and* publishes.
    - Schema drift across many independent consumers.
  - *Improvement:* registry-enforced compatibility, idempotent consumers, and the transactional outbox. The outbox and Debezium are covered in the Kafka track of the prior research.
- For this chapter, keep messaging focused on *encoding and evolution*. Delivery semantics, partitions and exactly-once belong to the stream-processing and Kafka lessons.
- **Misconceptions:**
  1. "Async messaging removes coupling." It removes *temporal* coupling, but the schema coupling remains and is spread across unknown consumers.
  2. "Actors guarantee delivery." DDIA explicitly says messages can be lost.
  3. "A message broker is a database." Many delete messages on consumption (DDIA p.190).

### Gaps
- I did not research AsyncAPI's current version (3.x) or its 2026 status.
- I did not verify Akka's 2022 licence change or the current Akka product name, versions and licence terms. The akka/akka repo redirected, and akka-core tags show v10.x, whose meaning I couldn't interpret.

---

## 6. Durable execution and workflow engines (Temporal, Restate, DBOS, AWS Step Functions and Lambda durable functions, Cadence, Azure Durable Functions); sagas; what "exactly-once" means

### Takeaway
Durable execution makes a multi-step process survive crashes. It records every step's result in a durable log (Temporal's event history, Restate's journal, DBOS's Postgres checkpoints). After a crash it *replays* the code, substituting recorded results for steps that already finished. Two consequences follow, and every engine's documentation admits both:
1. **Side effects run at-least-once.** An activity or step can crash after doing its work and before its completion is recorded. "Exactly-once" in vendor claims means the workflow's recorded progress is applied once, so external calls still need idempotency keys. DDIA says the same.
2. **Workflow code must be deterministic.** Replayed code must emit the same commands in the same order, so changing code under in-flight executions breaks replay. The remedies are patching (`Workflow.getVersion`), pinning executions to the deployment that started them (Temporal Worker Versioning, GA in 2026; Restate's immutable deployments), or immutable definitions (Step Functions).

Nov 2026 versions:

| Product | Latest release |
|---|---|
| Temporal Server | 1.32.2 |
| Temporal Java SDK | 1.40.0 |
| Restate | 1.8.1 |
| Restate Java/Kotlin SDK | 2.11.0 |
| DBOS Java | 1.2.0 (1.0 GA Jul 2026) |
| Cadence | 1.4.5 |
| Azure Durable Task Java | 1.10.0 |
| AWS Lambda durable functions | Java SDK GA Apr 2026 |

Temporal has **no released first-class Kotlin SDK**: Kotlin uses the Java SDK plus the `temporal-kotlin` extension module, and a coroutine-based Kotlin SDK exists only as an approved proposal.

### Cited Findings

**DDIA's framing**
- **Basic terms** — DDIA 2e p.187–188 / PDF 211–212:
  - A payment takes several service calls (fraud check, card debit, bank deposit). That sequence is a **workflow**, made of **tasks**; Temporal calls them *activities*, and others say *durable functions*.
  - Workflows are defined in code, in a DSL, or in markup such as BPEL or BPMN.
  - An engine has an **orchestrator** that schedules and an **executor** that runs tasks. Triggers can be a schedule, a web service or a human.
- **Kinds of engine** — DDIA 2e p.188 / PDF 212:
  - ETL orchestrators: Airflow, Dagster, Prefect.
  - BPMN and low-code engines: Camunda, Orkes.
  - Durable-execution engines: Temporal, Restate.
- **DDIA's motivation for durable execution:** a crash mid-workflow could charge the card but never deposit the money. You can't wrap two services, or a third-party gateway, in one database transaction.
  - DDIA says durable-execution frameworks provide "exactly-once semantics for workflows". On re-execution they skip calls that already succeeded and return the logged results, which works because all RPCs and state changes are logged durably, like a write-ahead log.
  - Example 5-5 is a Temporal Python workflow using `execute_activity(..., start_to_close_timeout=15s)` — DDIA 2e p.188 / PDF 212.
- **DDIA's caveats** — DDIA 2e p.189 / PDF 213:
  - External services must still be **idempotent**, using unique IDs.
  - Calls are logged in order, so **reordering code can cause undefined behaviour**. It is safer to deploy new code separately and keep old executions on old code (citing Restate's "immutability problem" post).
  - Random numbers and clocks break replay. Frameworks provide deterministic substitutes, and Temporal has a static checker, "Workflow Check".
  - Determinism is covered again in Ch. 9.

**Temporal: mechanics**
- The worker sends **commands** (`ScheduleActivityTask`, `StartTimer`, `CompleteWorkflowExecution`), and the service records **events** (`ActivityTaskScheduled`, `ActivityTaskStarted`, `ActivityTaskCompleted`, `TimerStarted`/`TimerFired`) in the durable event history — [Temporal docs, Event History (Java)](https://docs.temporal.io/encyclopedia/event-history/event-history-java).
- Replay re-runs the code and compares the commands it generates with the history. A mismatch is a **non-determinism error**, which counts as a *workflow task failure* and is retried by default rather than failing the workflow. You fix it by correcting the code or by versioning.
- `Workflow.sleep` is safe because it becomes a timer. `java.util.Random` inside a workflow is the docs' standard non-determinism example. I/O belongs in activities.
- **Limits:**
  - Event history has a hard limit of **51,200 events or 50 MB**, with warnings at **10,240 events or 10 MB**.
  - Pending activities, child workflows, signals and cancellation requests default to **2,000 each**.
  - Workflows default to 30 in-flight Nexus operations.
  - Exceeding a pending limit fails the workflow task, which is then retried.
  — [Temporal docs, limits](https://docs.temporal.io/workflow-execution/limits)
- **Messages:**
  - **Signals** are async writes with no response.
  - **Queries** are reads that never touch history and work on closed workflows.
  - **Updates** are synchronous tracked writes, can have validators, and are recorded in history once accepted.
  — [Temporal docs, message passing](https://docs.temporal.io/encyclopedia/workflow-message-passing)
- **Exactly-once vs at-least-once:**
  - Activities retry without limit by default, so they are **at-least-once**. `maximumAttempts=1` gives at-most-once, where zero executions is possible — [Temporal blog, idempotency and durable execution](https://temporal.io/blog/idempotency-and-durable-execution); [Temporal community forum](https://community.temporal.io/t/execution-guarantees-of-activities/3405).
  - The docs advise idempotent activities, and splitting multi-step work so that only the failed step reruns — [Temporal docs, Activity Definition](https://docs.temporal.io/encyclopedia/activities/activity-definition).
  - The docs' "exactly once" phrase refers to how activity *completion is observed and recorded*, not to the side effect itself — [summary of Temporal docs and forum](https://docs.temporal.io/encyclopedia/activities/activity-definition).

**Temporal: versioning**
- **Patching in Java:** `Workflow.getVersion("checksumAdded", Workflow.DEFAULT_VERSION, 1)` records a **marker** in history, so replays take the same branch.
  - To retire a patch, keep `getVersion(id, 1, 1)` until all old histories leave retention, then remove it.
  - From Java SDK 1.30.0, `setEnableUpsertVersionSearchAttributes(true)` exposes versions in the `TemporalChangeVersion` search attribute.
  - The alternative is versioning by workflow *type* (`PizzaWorkflowV2`).
  - The pre-2025 experimental build-ID versioning was scheduled for removal from the server in **March 2026**.
  — [Temporal docs, Java versioning](https://docs.temporal.io/develop/java/versioning)
- **Worker Versioning** — [Temporal docs, Worker Versioning](https://docs.temporal.io/worker-versioning):
  - Concepts: a Worker Deployment, and a Deployment Version identified by deployment name plus Build ID.
  - **Pinned** workflows finish on the version that started them. **Auto-Upgrade** workflows move to the current version and must be replay-safe, typically through patching.
  - **Ramping** sends a percentage of new and auto-upgrade work to a new version.
  - Version statuses: Inactive, Active (Current or Ramping), Draining and Drained.
- **Worker Versioning is GA:**
  - The Durable Digest of March 2026 announced GA, and the Replay 2026 product announcements (May 2026) repeated it — [Temporal blog, Replay 2026](https://temporal.io/blog/replay-2026-product-announcements); [Durable Digest Mar 2026](https://temporal.io/blog/durable-digest-march-2026).
  - A secondary source dates the GA blog post to 30 Mar 2026 and says OSS server v1.31.0 (29 Apr 2026) declared the Worker Deployment API GA. This is unverified against Temporal's own release notes — [youngju.dev](https://www.youngju.dev/split/2026-07-17-temporal-worker-versioning-ga-replay-deploy-problem).
- **Versions:**
  - Temporal Server **v1.32.0 (2026-09-11)**, with Standalone Activities GA and Standalone Nexus Operations in pre-release. Latest patches are **v1.32.2, v1.31.5 and v1.30.9 (all 2026-11-02)**.
  - Java SDK **v1.40.0 (2026-09-29)**. Its breaking change made `ActivitySerializationContext` getters `@Nullable`, and it enabled the SDK flags `CANCEL_AWAIT_TIMER_ON_CONDITION` and `VERSION_WAIT_FOR_MARKER`.
  - CLI **v1.10.0 (2026-11-03)**.
  - Standalone Nexus needs Java SDK v1.36.1 or later.
  — [GitHub releases API: temporal](https://github.com/temporalio/temporal/releases), [sdk-java](https://github.com/temporalio/sdk-java/releases), [cli](https://github.com/temporalio/cli/releases)
  - The sdk-java repo contains `temporal-kotlin`, `temporal-workflowcheck`, `temporal-testing`, `temporal-test-server` and the Spring Boot starter modules — [sdk-java repo contents](https://github.com/temporalio/sdk-java).
- **Kotlin status:**
  - `temporal-kotlin` is a *support module* for the Java SDK. It adds Kotlin method references for `Async` stubs and DSL-like extensions — [temporal-kotlin README](https://github.com/temporalio/sdk-java/blob/master/temporal-kotlin/README.md).
  - A coroutine-first **Kotlin SDK proposal** (temporalio/proposals PR #104) was merged on **16 Jan 2026**. It describes itself as an experiment in using LLMs for design and implementation, targets Kotlin 1.8+ and kotlinx-coroutines 1.7+, and keeps interop with the Java SDK — [proposal PR mirror](https://gh.r-mj.com/temporalio/proposals/pull/104).
  - I found no release, version number or docs site for that SDK. The only Kotlin-named repo in the temporalio org is `temporal-devdays-kotlin`, created 2026-10-06 — [GitHub search API](https://github.com/temporalio/temporal-devdays-kotlin).
- **A real "where it breaks" example from 2026:**
  - Kotlin **2.4 compiles method references passed to `Async.function`/`Async.procedure` differently from Kotlin 2.2**.
  - Java SDK versions through 1.40 don't recognize the 2.4 form, so they run it on a new workflow thread. That changes command ordering and causes a **`NonDeterministicException` on replay** of workflows started under Kotlin 2.2.
  - The module now unwraps the 2.4 form. The escape hatch is `-Dtemporal.kotlin.disableStaticAdapterUnwrapping`.
  — [temporal-kotlin README on master](https://github.com/temporalio/sdk-java/blob/master/temporal-kotlin/README.md)
  - In short, a *compiler upgrade* with no source change broke determinism.

**Restate**
- **Model** — [Restate docs, durable execution](https://docs.restate.dev/concepts/durable_execution):
  - A handler's steps (service calls, state updates, timers, side effects) and their results go into a **journal**. On failure Restate replays it, skips completed steps, and retries failures with exponential backoff.
  - The Restate Server is a **single Rust binary**, run as one node or as an HA cluster with consensus. It sits *in front of* services, which can run as containers, Lambdas or Kubernetes pods. It proxies calls, and invocations come in over HTTP, Kafka or programmatically.
  - **Virtual Objects** have keyed state and a single-writer guarantee: only one handler modifies an object's state at a time.
  - Restate claims each invocation runs "exactly once regardless of failures". Idempotency-keyed requests are deduplicated.
  - SDKs: TypeScript, **Java, Kotlin**, Python, Go, Rust, Ruby.
- **Versioning philosophy** — [Restate blog, "Solving durable execution's immutability problem" (Jack Kleeman, 2 Feb 2024)](https://restate.dev/blog/solving-durable-executions-immutability-problem/):
  - Each registered deployment is immutable. In-flight requests stay on the deployment they started on, and new ones go to the new deployment. Lambda versions make this easy; containers run old and new side by side, and bounded request durations (about an hour) keep that manageable.
  - The post contrasts Azure (deploy side by side), Temporal (worker build IDs plus patching, with patches that "accumulate") and Step Functions (immutable versioned ASL).
  - It admits that weeks-long handlers remain hard.
- **Versions** — [GitHub releases API: restate](https://github.com/restatedev/restate/releases), [sdk-java](https://github.com/restatedev/sdk-java/releases):
  - Restate **v1.8.0 (2026-10-14)** turned VQueues (the flow-control scheduler) on by default and made **service protocol v7** the default. v7 brings direct failure handling, lighter `ctx.run()` acknowledgements, and propagation of scope, limit key and idempotency key.
  - Upgrading requires all nodes on v1.7.3 or later first, and each partition is briefly unavailable during a one-time migration.
  - v1.8.1 came on 2026-10-21, with a hotfix on 2026-11-02.
  - **sdk-java (Java and Kotlin) v2.11.0 (2026-10-28).**

**DBOS**
- **Model** — [DBOS Java workflow tutorial](https://docs.dbos.dev/java/tutorials/workflow-tutorial):
  - A library, not a server: workflow state is checkpointed to **Postgres**, and the only dependency is Postgres — [GitHub repo](https://github.com/dbos-inc/dbos-transact-java).
  - `@Workflow` methods resume "from the last completed step" after a restart. Steps are invoked with `dbos.runStep(...)`.
  - Workflows must be deterministic, so I/O, randomness, time and threads belong inside steps.
  - Steps are "tried *at least once* but are never re-executed after they complete".
  - A **workflow ID** set with `withWorkflowId` works as an idempotency key: the same ID executes only once.
  - An uncaught exception puts the workflow in the `ERROR` state, and it is not recovered.
- **Versions:**
  - **DBOS Transact Java 1.0.0 (2026-07-01)**, 1.1.0 (2026-09-24) and **1.2.0 (2026-10-01)**. Python is at 3.4.0 (2026-10-28) — [GitHub releases API](https://github.com/dbos-inc/dbos-transact-java/releases).
  - DBOS described 1.0 as production-ready, with a stable API and SemVer from then on, and added LISTEN/NOTIFY durable streams and JSONB workflow attributes — [DBOS blog, July 2026](https://dbos.dev/blog/new-in-dbos-july-2026).

**AWS Step Functions and Lambda durable functions**
- **Step Functions** — [AWS docs, choosing workflow type](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html):

  | | Standard | Express (async) | Express (sync) |
  |---|---|---|---|
  | Max duration | 1 year | 5 minutes | 5 minutes |
  | Execution semantics | **Exactly-once** | **At-least-once** | **At-most-once** |
  | State between transitions | Persisted | Not persisted | Not persisted |
  | Idempotency | Same-name `StartExecution` on a running execution returns an idempotent response | Not managed | Not managed |
  | History | Kept 90 days | Only via CloudWatch Logs | Only via CloudWatch Logs |
  | `.sync` / `.waitForTaskToken` / Activities / Distributed Map | Supported | Not supported | Not supported |
  | Billing | Per state transition | Executions, duration, memory | Executions, duration, memory |

  - Standard is exactly-once **"unless you have specified `Retry` behavior"** in ASL, and AWS recommends it for non-idempotent actions such as payments.
  - Workflow type can't be changed after creation.
- **Lambda durable functions** were announced **2 Dec 2025** (re:Invent).
  - Progress is checkpointed automatically, and execution can be suspended for **up to one year** with no compute charge while waiting.
  - On resume the handler runs **from the beginning**, and checkpointed steps return their saved results. This is the replay model, implemented by an open-source Durable Execution SDK that wraps the handler.
  - Launch support: US East (Ohio), Python 3.13/3.14 and Node.js 22/24.
  — [AWS What's New](https://aws.amazon.com/about-aws/whats-new/2025/12/lambda-durable-multi-step-applications-ai-workflows/); [Classmethod write-up](https://dev.classmethod.jp/en/articles/lambda-durable-function-25); [InfoQ](https://infoq.com/news/2025/12/aws-lambda-durable-functions/)
  - **Java:** developer preview on 26 Feb 2026, then **GA on 21 Apr 2026**, for Java 17+, with steps, waits, callbacks, durable invocation and a local emulator — [AWS What's New, Java preview](https://aws.amazon.com/about-aws/whats-new/2026/02/lambda-durable-execution-java-preview); [Java GA](https://aws.amazon.com/about-aws/whats-new/2026/04/lambda-durable-execution-java-ga/).
  - AWS also publishes idempotency best practices for durable execution — [AWS durable execution docs, idempotency](https://docs.aws.amazon.com/durable-execution/patterns/best-practices/idempotency/).

**Cadence**
- Cadence was created at Uber. It was accepted into the **CNCF Sandbox on 22 May 2025**, and Uber announced this on 6 Oct 2025 — [CNCF project page](https://www.cncf.io/projects/cadence-workflow/); [Uber blog](https://www.uber.com/blog/cadence-workflow-joins-the-cloud-native-computing-foundation/).
- The team reports cutting DB cost by **60% in 2025** — [Cadence blog, "Cadence in 2025"](https://cadenceworkflow.io/blog/2026/01/13/2026-01-13-cadence-in-2025/cadence-in-2025).
- **Versions:** server **v1.4.5 (2026-10-30)**; Java client tag **v4.0.0**, date not retrieved — [GitHub releases API](https://github.com/cadence-workflow/cadence/releases); [cadence-java-client tags](https://github.com/cadence-workflow/cadence-java-client/tags).

**Azure Durable Functions / Durable Task**
- The **Durable Task Scheduler** Dedicated SKU went **GA on 20 Nov 2025**, and the Consumption SKU went **GA in Apr 2026**. Microsoft now recommends it as the backend for Durable Functions and the Durable Task SDKs — [Redmond Mag](https://redmondmag.com/blogs/redmond-dispatch/2025/11/microsoft-makes-durable-task-scheduler-generally-available.aspx); [Microsoft Learn](https://learn.microsoft.com/th-th/Azure/durable-task/scheduler/durable-task-scheduler); [Azure update AZ560957](https://mc.merill.net/message/AZ560957).
- **Versions:** Durable Functions extension **v3.16.1 (2026-10-27)**; **durabletask-java v1.10.0 (2026-10-28)** — [GitHub releases API: azure-functions-durable-extension](https://github.com/Azure/azure-functions-durable-extension/releases), [durabletask-java](https://github.com/microsoft/durabletask-java/releases).
- Restate's post characterizes Azure's versioning advice as "deploy new code alongside old" — [Kleeman 2024](https://restate.dev/blog/solving-durable-executions-immutability-problem/).

**Sagas and compensation**
- The original saga paper is Garcia-Molina and Salem, "Sagas", SIGMOD 1987. It describes a long-lived transaction as a sequence T1…Tn of local transactions, each with a compensating Ci, run in reverse on failure — [ACM DL, doi:10.1145/38713.38742](https://dl.acm.org/doi/10.1145/38713.38742) (not re-fetched).
- Durable-execution engines are a common place to implement sagas: the compensations live in workflow code and run durably. For example, a workflow that has charged a card but fails to deposit runs a refund activity. DDIA's payment example (p.188) is exactly this scenario.

### Inferences
- **Concept ladder for durable execution:**
  1. *Problem:* a multi-step business process spans services, and a crash between steps leaves money charged but not deposited.
  2. *Simplest:* a cron job or queue consumer with a `status` column ("charged", "deposited"). This is a hand-rolled state machine, Brandur's recovery points.
     - *Breaks:* every process reinvents locking, retries, timers, the completer and the reaper. Timers that span days, and human-in-the-loop waits, become polling loops.
  3. *Next:* a declarative state machine (Step Functions ASL, BPMN).
     - *Breaks:* logic in YAML or JSON is hard to test and refactor. Express mode trades the exactly-once guarantee for throughput.
  4. *Next:* durable execution in ordinary code (Temporal, Restate, DBOS, Lambda durable functions). The engine logs each step's result and replays.
     - *Breaks:* determinism and versioning (code changes, even compiler changes such as Kotlin 2.4, break in-flight replays); history size (51,200 events); side effects that are still at-least-once.
  5. *Improvements:*
     - Version-pinned deployments (Temporal Worker Versioning, Restate immutable deployments).
     - Patching markers.
     - Continue-as-new for long histories.
     - Idempotency keys derived from workflow ID plus step ID for every external call.
- **What "exactly-once" means in each claim:**

  | Claim | What it actually means |
  |---|---|
  | Step Functions Standard | The state machine's transitions are applied once, *unless* `Retry` is configured; then a task can run again. |
  | Temporal | The workflow's recorded decisions are applied once, and each activity's completion is recorded once. The activity body is at-least-once. |
  | Restate | Each invocation runs exactly once from the system's point of view. `ctx.run` blocks are journaled once complete but can re-run if the crash happens before the journal entry is acknowledged. That last part is my inference from the journal model; the docs page doesn't spell it out. |
  | DBOS | Steps are at-least-once and never re-run after completion. A workflow ID dedupes whole workflows. |
  | DDIA | DDIA's "exactly-once semantics for workflows" should be taught as *effectively-once* = at-least-once execution + deduplication through idempotency. DDIA itself adds the idempotency caveat on the next page. |

- **Architectural contrast for teaching:**
  - *Temporal and Cadence:* a separate cluster (history, matching and frontend services plus a database). Workers *poll* task queues, and the full event history is replayed.
  - *Restate:* a single binary in front of services that *pushes* invocations, with a journal per invocation and keyed virtual objects.
  - *DBOS:* a library inside your app with only Postgres, so checkpoints are database rows.
  - *Step Functions:* managed, JSON or ASL, with no code replay.
  - *Lambda durable functions:* code-first replay inside Lambda.
  - All of them reduce to the same idea: a log of step results plus deterministic re-execution.
- **Misconceptions:**
  1. "Durable execution makes my payment API call happen exactly once." Only with an idempotency key the payment provider honours.
  2. "Retries are free." Unlimited retries by default can hammer a downstream service, so set timeouts and backoff.
  3. "I can edit a workflow any time." Only if nothing is in flight, or you patch or pin.
  4. "Determinism means no I/O." It means the *sequence of commands* must be a pure function of history. I/O is fine inside activities or steps.
  5. "Sagas give ACID." They give eventual compensation with *no isolation*: other parties can see the charged-but-not-deposited state in between.
- **For a Kotlin/JVM course in Nov 2026:**
  - Temporal is reached through the Java SDK 1.40 plus `temporal-kotlin`, in blocking style, not coroutines.
  - Restate has a first-party Kotlin SDK (sdk-java 2.11, `dev.restate:sdk-kotlin-*`).
  - DBOS Java 1.2 works from Kotlin as a plain JVM library.
  - AWS has a Java 17+ durable execution SDK.
  - Azure has durabletask-java 1.10.

### Gaps
- I did not fetch Temporal's own statement of the Worker Versioning GA date or the minimum server and SDK versions. The Java annotation names for versioning behaviour (for example a PINNED/AUTO_UPGRADE annotation) were not on the fetched page.
- I did not verify that `io.temporal.workflow.Saga` (the Java SDK saga helper) still exists in 1.40.
- No public release of the coroutine-based Temporal Kotlin SDK found; its status is unconfirmed.
- I did not open the DBOS "Upgrading Workflow Code" tutorial, so DBOS's versioning story (application-version tagging and recovery) is unverified. The names of DBOS system tables in Postgres are unverified.
- I did not open Restate's docs on `ctx.run` semantics for crashes between the side effect and the journal acknowledgement.
- Temporal's origin as a fork by Cadence's creators (2019) is widely reported, but I did not source it this session.
- I found no public benchmark numbers (throughput, latency per step) comparable across engines.
- Azure Durable Functions' "exactly-once" claims and replay rules were not fetched.

---

## 7. Hands-on lab ideas (laptop-runnable: Kotlin on JVM 21+, Gradle, Testcontainers or Docker Compose, or pure Kotlin)

### Takeaway
Each lab makes one invisible property visible as a number or an anomaly the learner can reproduce. The labs cover:
- bytes on the wire (33 vs 32 vs 66 vs 81),
- a corrupted ID (2^53+1 becomes 2^53),
- fields silently dropped by old code during a rolling upgrade,
- a CI build that turns red on a breaking schema change,
- gRPC traffic stuck on one backend,
- duplicate charges without idempotency keys,
- a Temporal workflow that survives `kill -9` but double-executes a non-idempotent activity and breaks on reordered code.

### Cited Findings (tooling facts the labs depend on)
- **JDK:** JDK 25 is the current LTS (25.0.5 installed locally), and JDK 27 went GA on 15 Sep 2026 — [prior networking notes](../Systems%20course%20curriculum%20research/networking.md), citing [JDK 27 project page](https://openjdk.org/projects/jdk/27/).
- **Kafka and Testcontainers:** prior research pinned `org.testcontainers.kafka.KafkaContainer` with `apache/kafka-native:4.4.0`; the older `org.testcontainers.containers.KafkaContainer` is deprecated — [prior report](../../reports/Systems%20course%20curriculum%20research.md), citing [Testcontainers Kafka](https://java.testcontainers.org/modules/kafka/).
- **Schema Registry image:** `confluentinc/cp-schema-registry:8.4.0`. The earlier Kafka-track lab registers Avro v1, v2 (an optional field with a default, which should pass BACKWARD) and v3 (a required field without a default, which the registry should reject with HTTP 409) through the REST API — [prior Kafka notes](../Systems%20course%20curriculum%20research/kafka.md).
- **Library versions (GitHub releases API):** protobuf v36.2 (Java 4.36.x), Avro 1.12.2, msgpack-java 0.9.12, buf v1.75.0, grpc-java 1.85.1, grpc-kotlin 1.5.0, connect-kotlin 0.10.0, Temporal CLI 1.10.0, Temporal Java SDK 1.40.0, Restate 1.8.1, Restate SDK 2.11.0, DBOS Java 1.2.0, Envoy 1.40.2 — see the release links in sections 2, 4 and 6.
- **Expected byte counts** for the DDIA record: JSON 81, MessagePack 66, Protobuf 33, Avro 32 (DDIA p.169–172), Thrift Binary 59 and Compact 34 (Kleppmann 2012). Varint 1337 is `b9 0a`, Avro zigzag 1337 is `f2 14`, and int64 −1 takes 10 bytes [local check].
- **Behaviours the labs reproduce:**
  - Unknown-field preservation is default in protobuf-java, and `DiscardUnknownFieldsParser` turns it off — [protobuf CHANGES.txt](https://github.com/protocolbuffers/protobuf/blob/383a4941d5b1aa3c0afbdc24dd0e5d63d263fc3a/CHANGES.txt).
  - Temporal non-determinism errors are retried workflow-task failures — [Temporal docs](https://docs.temporal.io/encyclopedia/event-history/event-history-java).
  - Temporal activities are at-least-once — [Temporal blog](https://temporal.io/blog/idempotency-and-durable-execution).
  - JEP 290 filters reject by class pattern and by depth or array limits — [JEP 290](https://openjdk.org/jeps/290).
  - Stripe-style keys behave as described in section 4 — [Stripe docs](https://docs.stripe.com/api/idempotent_requests); [brandur.org](https://brandur.org/idempotency-keys).

### Inferences (lab designs)

**Lab 1. "Bytes by hand" (pure Kotlin, no containers)**
- *Concept:* encoding as bytes, and the cost of field names.
- *Setup:* one Gradle module with Jackson, msgpack-java, protobuf-java 4.36 (Gradle protobuf plugin) and avro 1.12.2. Encode DDIA's `Person` record in each format and print hex dumps.
- *Measure:*
  - Sizes: 81 / 66 / 33 / 32 bytes.
  - Decode the Protobuf bytes **by hand** with a 30-line varint parser the learner writes: tag byte → field number and wire type, then `b9 0a` → 1337.
  - Re-encode `favorite_number = -1` as `int64` (10 bytes) and as `sint64` (1 byte).
  - Write an Avro object container file and find the `Obj\x01` magic and the 16-byte sync marker at the end of the header.
- *Stretch:* use Avro single-object encoding and find `C3 01` followed by the 8-byte fingerprint.

**Lab 2. "The 2^53 bug" (pure Kotlin)**
- *Concept:* JSON number precision.
- *Setup:* generate 64-bit snowflake-like IDs above 2^53. Round-trip them through a JSON parser configured to read numbers as `Double` (Jackson `USE_BIG_INTEGER_FOR_INTS` off, mapping into `Double`) and, optionally, through Node's `JSON.parse` in a container.
- *Measure:* the share of 10,000 IDs that come back changed. For random IDs above 2^53, essentially all odd values change. Then fix it with string IDs (as the X API does) or the Protobuf JSON int64-as-string mapping, and see 0 corruptions.

**Lab 3. "Old code eats new fields": rolling-upgrade simulation (pure Kotlin, then Postgres via Testcontainers)**
- *Concept:* Figure 5-1, forward compatibility and unknown fields.
- *Setup:* three "service instances" in one JVM, each version v1 or v2, behind a random router. v2 adds `loyalty_tier`.
  - Each request reads a record from a shared store (an in-memory map, then a PG 18 `bytea` or `jsonb` column), modifies another field, and writes the record back.
  - Run the rollout at 0%, 33%, 66% and 100% v2.
- *Measure:* the fraction of records whose `loyalty_tier` is lost, under four model strategies:

  | Model strategy | Expected outcome |
  |---|---|
  | Protobuf with default parser | Preserved: 0% loss |
  | Protobuf with `DiscardUnknownFieldsParser` | Lost |
  | Jackson data class with `FAIL_ON_UNKNOWN_PROPERTIES=false` | Silently lost |
  | Jackson defaults | Old instance throws on unknown property |
  | Avro decoded with reader schema v1 and re-encoded with v1 | Lost |

  Learners chart loss rate against rollout percentage.
- *Twist, the Knight analogue:* v3 **reuses** tag 2 with a new meaning but the same wire type, and the learner observes silent misinterpretation. Then a type change to a different wire type makes the field an unknown field. Then fix both with `reserved 2;` and watch `buf breaking` catch them (Lab 4).

**Lab 4. "Red build on a breaking change": compatibility test suite (Gradle plus Testcontainers)**
- *Concept:* registries and compatibility modes as CI gates.
- *Part A, Protobuf:* a Gradle task runs `buf breaking --against '.git#branch=main'`.
  - Commits that delete a field without reserving it, change `int64`→`string`, or renumber a field each fail.
  - Compare the FILE, WIRE_JSON and WIRE categories, and record which commits each category catches. A field *rename* fails FILE and WIRE_JSON but passes WIRE.
- *Part B, Avro and Schema Registry:*
  - Testcontainers starts `apache/kafka-native:4.4.0` plus `cp-schema-registry:8.4.0`.
  - JUnit tests POST to `/compatibility/subjects/{s}/versions/latest`, assert `is_compatible`, and loop over every mode.
  - Measure a matrix of change type (add optional with default, add required, remove field, rename with alias, widen int→long, add enum symbol) against mode (BACKWARD, FORWARD, FULL and the TRANSITIVE variants).
  - Show the non-transitive trap: v1→v2→v3 each pass BACKWARD, but v3 can't read v1. Prove it by decoding v1 bytes with a v3 reader, then switch to BACKWARD_TRANSITIVE and watch the registry reject v3.
- *Part C, no container:* the same matrix with Avro's in-JVM `SchemaCompatibility.checkReaderWriterCompatibility`, for fast unit tests.

**Lab 5. "Expand/contract on a live table" (Testcontainers Postgres 18)**
- *Concept:* data outlives code, and migrations as a process.
- *Setup:* two app versions run concurrently against one database, each issuing 200 requests per second.
- *Naive migration:* `ALTER TABLE ... RENAME COLUMN email TO email_address` while v1 is still running. Measure v1's error count and error rate.
- *Expand/contract migration:*
  1. Add the new column.
  2. Dual-write.
  3. Backfill in batches.
  4. Switch reads, with a shadow-read comparison counter in the style of Scientist.
  5. Switch writes.
  6. Drop the old column after v1 is gone.
- *Measure:* 0 errors, the mismatch counter, backfill throughput (rows per second), and an estimate of how long 100M rows would take, compared with Stripe's figure of more than 3 years at one row per second.

**Lab 6. "Retry storm": idempotency keys (Ktor or Spring Boot plus Testcontainers Postgres)**
- *Concept:* unknown outcomes and idempotency.
- *Setup:* a `POST /charges` endpoint and a fault-injecting proxy, for example Toxiproxy via Testcontainers, that drops 30% of *responses* after the server commits. The client retries up to 3 times.
- *Measure:*
  - Duplicate charges per 1,000 logical payments: no key, versus a naive key check (read-then-insert, which races under concurrent retries), versus Brandur's design (unique `(user_id, key)`, `SERIALIZABLE` phases, recovery points, 409 on concurrent use, and a parameter fingerprint that rejects mismatches).
  - Show that a retry *after* key expiry, with the expiry set to 5 s in the lab instead of 24 h, creates a duplicate again.

**Lab 7. "One busy pod": gRPC load-balancing skew (Docker Compose)**
- *Concept:* L4 vs L7 balancing for HTTP/2.
- *Setup:* three replicas of a grpc-kotlin server that each count requests. The client uses one channel and sends 10,000 unary RPCs, routed three ways:
  - (a) through HAProxy or nginx in TCP (L4) mode,
  - (b) through Envoy 1.40 as an L7 HTTP/2 proxy,
  - (c) through client-side `round_robin` against a DNS name that returns all three IPs.
- *Measure:* per-replica counts. Expect roughly 10,000 / 0 / 0 for (a) and roughly 3,333 each for (b) and (c). Then add `maxConnectionAge` on the servers and show that (a) improves only partially.
- *Optional:* run the same service with Connect-Kotlin and call it with `curl` and JSON over HTTP/1.1.

**Lab 8. "Kill the worker": Temporal in Kotlin (Temporal CLI dev server or Docker Compose)**
- *Concept:* durable execution, replay, at-least-once activities, determinism.
- *Setup:* `temporal server start-dev` (CLI 1.10.0). A Kotlin worker on the Java SDK 1.40 plus `temporal-kotlin` runs `PaymentWorkflow` with five activities: fraud check → reserve → charge → deposit → notify. Each activity sleeps 3 s and appends a row to a side-effect ledger, either Postgres or a file.
- *Run 1:* `kill -9` the worker during `charge`, then restart it.
  - Measure ledger rows per activity: completed steps show 1, and the interrupted step shows 1 or 2. Make the 2 visible by crashing *after* the side effect and *before* the activity returns.
  - Use `temporal workflow show` to see the events (`ActivityTaskScheduled/Started/Completed`) and count them.
- *Run 2:* fix the duplicate by passing `workflowId + activityId` as an idempotency key to a fake payment service that dedupes.
  - Measure: 0 duplicates across 100 crash runs, driven by a script that kills at random times.
- *Run 3, determinism:* swap the order of `reserve` and `fraud check` while a workflow is paused on a timer, then restart. Observe a `NonDeterministicException` as a repeating workflow-task failure. Fix it with `Workflow.getVersion("reorder", DEFAULT_VERSION, 1)`, and add a `WorkflowReplayer` test against a saved history JSON, so the regression is caught in CI.
- *Run 4, Kotlin-specific:* reproduce or discuss the Kotlin 2.2 → 2.4 `Async` method-reference change described in the `temporal-kotlin` README. This shows that a toolchain upgrade can break replay.
- *Stretch, saga:* inject a permanent failure in `deposit` and run compensations (a refund, then releasing the reservation) in reverse. Verify the ledger nets to zero.
- *Stretch, limits:* loop signals until the 10,240-event warning appears, then implement continue-as-new.

**Lab 9. Same workflow, different engines (Testcontainers)**
- *Concept:* the shared "log of step results plus replay" idea across architectures.
- *DBOS Java 1.2 with Postgres 18:* kill the JVM mid-workflow and restart. Inspect the checkpoint rows in Postgres to see the recorded step outputs. Show that the same workflow ID started twice executes once.
- *Restate 1.8 (Docker) with the Kotlin SDK 2.11:* kill the service container mid-handler. Restate re-invokes it and replays the journal; inspect it with `restate invocations journal`. Use a Virtual Object to show single-writer access per key: concurrent increments of one key produce no lost updates.
- *Measure:* per engine, the duplicate-side-effect count with and without idempotency keys, and the recovery time after restart.

**Lab 10. "Deserialization is code execution" (pure Kotlin, safe)**
- *Concept:* why language-native serialization is dangerous.
- *Setup:* define a harmless class whose `readObject` increments a global counter and logs. Serialize it, then deserialize the bytes in code that expects an unrelated type.
- *Observe:* the counter increments *before* the `ClassCastException`, which proves code ran during decoding.
- Then apply a JEP 290 filter (`-Djdk.serialFilter=!com.example.*;maxdepth=20`) and observe `InvalidClassException` / `REJECTED` with the counter unchanged.
- Add a nested-collection payload and measure deserialization time as nesting depth grows, before and after `maxdepth`.
- This shows the gadget principle without shipping real exploit chains.

**Course-level notes**
- Labs 1–4 need no network services except Lab 4B. Labs 5–9 need Docker.
- Each lab ends with a single assertion in a JUnit test (byte count, loss %, duplicate count, per-replica skew, NDE observed), so automated QA can confirm the anomaly reproduces.

### Gaps
- I did not verify the current Gradle version, the Gradle protobuf plugin version, or the Testcontainers version for Nov 2026. The writer should pin them from Maven Central or Gradle Plugin Portal. Maven Central's search index returned stale data (temporal-sdk 1.30.1, June 2025), so use the GitHub releases listed above or Maven Central's directory listing.
- I did not verify a Testcontainers module or official image for the Temporal dev server, nor the Restate Testcontainers helper. The CLI `temporal server start-dev` route is safe.
- I did not check Jackson 3.x defaults (`jackson-databind` 3.3.0 tag seen) for `FAIL_ON_UNKNOWN_PROPERTIES` and integer handling. Lab 2 and Lab 3 outcomes depend on them, so pin Jackson 2.x or 3.x explicitly and assert the behaviour in a test.
- I did not confirm Toxiproxy's current Testcontainers module or image version.
