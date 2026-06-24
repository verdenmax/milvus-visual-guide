# M2 — Part 2 Foundations (L04–L08) — Spec

**Milestone:** M2 (Part 2 · 前置基础 / Foundations). Five lessons that give a newcomer the
conceptual + Milvus-specific groundwork the rest of the guide assumes. New module `src/part2.py`
(one module per Part). Part label: "第二部分 · 前置基础" / "Part 2 · Foundations".

Authoring standard for every lesson: content model (lead → analogy card → macro card → ≥3
diagrams/lang → cited code (file+symbol where a Milvus claim is made) → key-points card → quiz);
**zh ≥ 3500 CJK, aim ~4000** (push past M1's ~3000 floor — the user wants depth); strict zh/en
parity; gates 0/0.

## Lessons

### L04 — 向量与相似度 / Embeddings & similarity (`04-embeddings-and-similarity.html`)
Mostly conceptual (deepens L01). Cover: what an embedding is; the vector space; **distance/similarity
metrics** and when to use each — **L2** (Euclidean), **IP** (inner product), **COSINE**; the link
between normalization and IP/COSINE; binary-vector metrics **HAMMING / JACCARD**; sparse vectors use
**IP**. The **ANN problem** statement (why exact kNN is too slow). Milvus tie-in: the metric names are
exactly Milvus's (`pkg/util/metric/metric_type.go`). Diagrams: a `cellgroup`/`trace` showing distance
computation; a `table.t` (metric → meaning → typical use → vector kind); a `cols` (normalized vs not,
or L2 vs IP). Cited code: `pkg/util/metric/metric_type.go` (the metric constants).

### L05 — ANN 算法直觉 / ANN intuition (`05-ann-algorithms.html`)
Conceptual, with Milvus index names. Build intuition for the main index families: **FLAT** (brute
force, exact), **IVF** (cluster into buckets, probe a few — `nlist`/`nprobe`), **HNSW** (navigable
small-world graph — `M`/`efConstruction`/`ef`), **PQ / quantization** (compress vectors), **DiskANN**
(disk-resident graph). The universal tradeoff triangle: **speed ↔ memory ↔ recall**. Milvus tie-in:
these are Knowhere index types you pick per collection (deep build/scheduling in Part 5). Diagrams: a
`cols` or `layers` of index families; a `table.t` (index → idea → key params → when to use); a
`vflow`/`trace` of an IVF or HNSW search; optionally a `flow`. Cited code: an index-type list if a
concise Milvus/Knowhere reference exists, else keep to a `table.t` of names (don't fabricate a path).

### L06 — 数据模型 / Data model (`06-data-model.html`)
Milvus-specific — VERIFY against the current proto/code. Cover: **collection** (≈ table) → **schema**
→ **fields** (`FieldSchema`: name, DataType, is_primary_key, auto_id, type_params incl. `dim`/`max_length`,
nullable/default where applicable); the **primary key**; the **dynamic field** (`$meta` / enable_dynamic_field);
the **partition** and the **partition key**; supported **DataTypes** including scalar (Bool, Int8/16/32/64,
Float, Double, VarChar, JSON, Array) and **vector** types (FloatVector, BinaryVector, **Float16Vector,
BFloat16Vector, Int8Vector, SparseFloatVector**). Diagrams: a `table.t` (DataType → kind → notes); a
`layers`/`cols` (collection → partition → segment, or schema anatomy); a `vflow` (schema → collection
→ insert rows). Cited code: the schema proto (`pkg/proto/.../schema.pb.go` `FieldSchema`/`CollectionSchema`)
or `internal/core/src/common` schema — file+symbol.
**Read:** `pkg/proto/**/schema*.go` (current DataType enum + FieldSchema), `docs/developer_guides/chap02_schema.md`
(note: older — code wins; the doc's DataType list is incomplete), `client/entity` (Go SDK schema) for terms.

### L07 — Segment 与日志即数据 / Segments & log-as-data (`07-segments.html`)
Milvus-specific — VERIFY. Cover: the **segment** as the unit of data + index; **growing** (in-memory,
being written via the stream) vs **sealed** (immutable, flushed) — the lifecycle
**Growing → Sealed → Flushing → Flushed → (Dropped)** (`SegmentState_*` in the datacoord proto);
**vchannel** (virtual shard) → **pchannel** (physical MQ topic) mapping; a collection is sharded into
N vchannels; the **"log as data"** model (writes are an append-only, replayable, timestamped log; the
other data forms catch up by replaying it); columnar physical layout inside a segment. Diagrams: a
`vflow`/`timeline` of the segment lifecycle; a `flow` (insert → vchannel → growing → seal → flush →
binlog); a `cols` (growing vs sealed); optionally a `table.t` of segment states. Cited code: the
`SegmentState` enum or a datacoord segment type — file+symbol.
**Read:** `internal/datacoord` (segment states/lifecycle), `pkg/proto/**/data_coord*.go` (`SegmentState`),
`internal/flushcommon`, `docs/developer_guides/chap01_system_overview.md` (data organization).

### L08 — 依赖与部署形态 / Dependencies & deploy shapes (`08-dependencies-and-deployment.html`)
Milvus-specific — VERIFY. Cover the **three external dependencies** and what each stores/does:
**etcd** (metadata + service discovery), **object storage** (MinIO/S3/local — binlogs + index files +
delta logs), **message queue / WAL** (Pulsar / Kafka / **woodpecker** built-in / RocksMQ for standalone);
then the **deploy shapes**: **Milvus Lite** (pip, in-process, local file), **Standalone** (one process,
all roles, RocksMQ/woodpecker + local/MinIO + embedded etcd), **Cluster** (K8s, separate pods, external
deps). Diagrams: a `layers` (the dependency stack under Milvus); a `table.t` (dependency → role →
examples); a `cols`/`table.t` (Lite vs Standalone vs Cluster). Cited code/config: `configs/milvus.yaml`
(etcd/minio/mq sections) and/or `deployments/` — file+section.
**Read:** `configs/milvus.yaml`, `deployments/docker-compose/`, `internal/util/dependency`, the
message-queue selection (`mq.type`, woodpecker), `docs/` deployment material.

## Wiring
- New `src/part2.py` with `LESSON_04..LESSON_08`.
- `registry.py`: `import part2` and add the 5 keys.
- `shell.PAGES`: append 5 tuples (Part 2 label). `shell.SUBTITLES`: add 5.
- `quizzes.QUIZZES`: add 5 entries.

## Definition of Done
Gates 0/0; rebuild no-diff; index pill "共 8 课 · 2 个部分"; nav chain L01..L08 correct; two-stage
review passed; committed.

## Accuracy guardrails
- Use the **current** DataType set (include sparse/float16/bfloat16/int8 vectors) — the old doc's enum
  is incomplete.
- Segment lifecycle names must match `SegmentState_*` in code.
- Metric names exactly Milvus's (L2/IP/COSINE/HAMMING/JACCARD).
- woodpecker is a real built-in WAL option; RocksMQ is the standalone default MQ — verify before stating
  defaults.
- Don't fabricate file paths for Knowhere (it's an upstream lib); cite Milvus-side references only.
- file+symbol citations; small snippets only.
