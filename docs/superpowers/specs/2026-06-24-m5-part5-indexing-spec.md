# M5 — Part 5 Indexing (L21–L24) — Spec

**Milestone:** M5 (Part 5 · 索引 / Indexing). Four lessons on how Milvus builds and serves indexes —
vector (Knowhere) and scalar/full-text (tantivy). New module `src/part5.py`. Part label:
"第五部分 · 索引" / "Part 5 · Indexing".

Authoring standard: content model (lead → analogy → macro → ≥3 diagrams/lang → cited code
file+symbol → key card → quiz); **zh ≥ 3700 CJK, aim ~3900**; strict zh/en parity; gates 0/0
(incl. the undefined-CSS-class guard — only use classes defined in `shell.py`). Verify every symbol
in `/home/verden/course/milvus`.

## Lessons

### L21 — 索引服务 / The index service (`21-index-service.html`)
How index build is scheduled. Cover: **DataCoord owns the index meta + scheduling**
(`internal/datacoord/index_service.go`, `index_meta.go`, `index_inspector.go`); a **datanode/worker
builds** the index (there is **NO separate indexnode** — the build runs on a worker that implements
`workerpb.IndexNodeClient`, recall L09/L12); the **index lifecycle** (CreateIndex → build task per
sealed segment → index files persisted → loadable); auto-index. Diagrams: a `vflow` (CreateIndex →
DataCoord schedules → worker builds → index files); a `flow`; a `table.t` (stage → who → output).
Cite `internal/datacoord/index_service.go` (CreateIndex / index task) — verify symbol.

### L22 — Knowhere 向量索引内核 / Knowhere vector indexes (`22-knowhere.html`)
The vector-search kernel. Cover: **Knowhere is the upstream library** Milvus calls for vector
index build/search; the **index families** and their tradeoffs — **FLAT** (brute force), **IVF_FLAT/
IVF_SQ8/IVF_PQ** (cluster + optional quantization), **HNSW** (graph), **DiskANN** (disk graph),
**SCANN**, **GPU (CAGRA/GPU_IVF_*)**, and **sparse** (`SPARSE_INVERTED_INDEX`/`SPARSE_WAND`); index
build/search **params** (nlist/nprobe, M/ef, etc.); the metric must match the field. CITATION CARE:
most vector index names are **Knowhere `IndexEnum` constants in the upstream lib**, not defined in
milvus core — cite the milvus-side references that DO exist (e.g. `internal/core/src/common/Utils.h`
has `INDEX_DISKANN`, `index/Utils.cpp` has the IVF/sparse enums) and present the rest as Knowhere
index names without a false milvus-file attribution. Diagrams: a `table.t` (family → idea → params →
when); a `cols`/`layers` (in-memory vs disk vs GPU); a `trace`/`vflow` (HNSW or IVF search). 
**Read:** `internal/core/src/index/{Utils.cpp,VectorMemIndex.cpp,VectorDiskIndex.cpp}`, `common/Utils.h`.

### L23 — 构建与加载索引 / Build & load (`23-index-build-and-load.html`)
The data path of an index. Cover: a **sealed segment**'s raw vectors → **build task** (worker reads
binlogs, calls Knowhere build) → **index files written to object storage** → **QueryNode loads** the
index into memory (or mmaps it) when the collection is loaded (recall L13 load/release); growing
segments use brute-force until indexed; index versioning
(`internal/datacoord/index_engine_version_manager.go`). Diagrams: a `vflow`/`timeline` (sealed →
build → object storage → querynode load → searchable); a `flow`; a `table.t` (artifact → where). Cite
the build task or load path — verify file+symbol.
**Read:** `internal/datacoord/index_*`, `internal/core/src/index` (build/load), `internal/querynodev2/segments` (load).

### L24 — 标量与全文索引 / Scalar & full-text (`24-scalar-and-fulltext.html`)
Beyond vectors. Cover: **scalar indexes** to accelerate the filter part of hybrid search —
**inverted** (tantivy-backed, `InvertedIndexTantivy`), **bitmap** (`BitmapIndex`, low-cardinality),
**sort/STL_SORT** (`ScalarIndexSort`/`StringIndexSort`, range), **ngram** (`NgramInvertedIndex`),
**hybrid** (`HybridScalarIndex` auto-picks), **JSON** index; and **full-text search (BM25)** via the
Rust **tantivy** engine (`internal/core/src/index/InvertedIndexTantivy.{cpp,h}` + `thirdparty/tantivy`,
the Rust binding). How scalar filtering + vector search combine (hybrid). Diagrams: a `table.t` (scalar
index → data → best for); a `layers`/`cols` (scalar vs vector vs full-text); a `vflow`/`flow`
(filter + ANN). Cite `internal/core/src/index/InvertedIndexTantivy.h` (or BitmapIndex/ScalarIndexSort)
— verify.
**Read:** `internal/core/src/index/{ScalarIndex.h,BitmapIndex.h,ScalarIndexSort.h,InvertedIndexTantivy.h,NgramInvertedIndex.h,HybridScalarIndex.h}`, `internal/core/thirdparty/tantivy`.

## Wiring
New `src/part5.py` (LESSON_21..24); `registry.py` `import part5` + 4 keys; `shell.PAGES` += 4 (Part 5
label); `shell.SUBTITLES` += 4; `quizzes.QUIZZES` += 4.

## Definition of Done
Gates 0/0; rebuild no-diff; index pill "共 24 课 · 5 个部分"; nav chain L01..L24; two-stage review
passed; committed.

## Accuracy guardrails
- Index build scheduled by **DataCoord**, run by a **worker** (no indexnode).
- Most vector index enums are **Knowhere library** constants — do NOT attribute them to milvus core
  files that don't contain them (the L05 mistake). Cite only what's verified in the cited file.
- tantivy is Rust, called from C++ via `InvertedIndexTantivy` + the binding under `thirdparty/tantivy`.
- file+symbol citations; proto types in `milvus-proto/go-api/v3/...pb`; small snippets.
