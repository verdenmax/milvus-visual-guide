# M8 — Part 8 C++ Core Internals (L34–L37) — Spec

**Milestone:** M8 (Part 8 · C++ 内核 / C++ core internals). Four lessons into the C++ engine
(`internal/core/src`) that powers reads (and index build). New module `src/part8.py`. Part label:
"第八部分 · C++ 内核" / "Part 8 · C++ core internals".

Authoring standard: content model (lead → analogy → macro → ≥3 diagrams/lang → cited code file+symbol
→ key card → quiz); **zh ≥ 3700 CJK, aim ~3900**; strict zh/en parity; gates 0/0 (CSS-class guard).
Verify symbols in `/home/verden/course/milvus/internal/core/src`.

## Lessons

### L34 — core 布局 / The C++ core layout (`34-core-layout.html`)
The map of `internal/core/src`. Cover: the sub-directories and what each does — **segcore** (segment
search engine, the cgo entry), **index** (Knowhere wrappers + scalar indexes), **query** (search/retrieve
plan structures), **exec** (vectorized execution engine), **expr** (expression tree), **mmap** (chunked
columnar storage), **storage** (binlog/payload I/O), **common** (shared types), **plan**, **bitset**,
**clustering**; the **cgo bridge** (`*_c.h`/`*_c.cpp` C-ABI files Go calls into — recall L02/L27); how the
core sits under QueryNode (search) + the index worker (build). Diagrams: a `layers`/`table.t` (directory →
responsibility); a `flow` (Go → cgo → core subsystems); a `cols` (build path vs search path). Cite a
real `*_c.h` (e.g. `segcore/segment_c.h`) or a subsystem header.

### L35 — mmap 与列式分块 / mmap & chunked columns (`35-mmap-and-chunks.html`)
How segment data lives in memory. Cover: the **columnar** in-segment layout (a field = a column);
the **chunked column** abstraction (`internal/core/src/mmap/ChunkedColumn.h`,
`ChunkedColumnInterface.h`, `ChunkData.h`, `ChunkVector.h`) — data split into fixed chunks for SIMD +
bounded allocation; **mmap** (memory-map index/data files from object-storage-backed local files so the
OS pages them in on demand, shrinking RAM) vs fully-in-memory; growing (mutable) vs sealed (mmap-able).
Diagrams: a `cellgroup` (a column split into chunks); a `cols` (in-memory vs mmap); a `vflow`/`layers`
(file → mmap → chunked column → search). Cite `internal/core/src/mmap/ChunkedColumn.h` (a class/interface)
— grep-verify.

### L36 — 表达式与向量化执行 / Expr & vectorized exec (`36-expr-and-exec.html`)
How a filter runs fast. Cover: the **logical expression tree** (`internal/core/src/expr/ITypeExpr.h` —
the boolean/arith predicates compiled from the filter string); the **vectorized execution engine**
(`internal/core/src/exec/{Task.h,Driver.h,QueryContext.h}` + physical operators in
`internal/core/src/exec/expression/*.h`, e.g. `BinaryArithOpEvalRangeExpr.h`, `AlwaysTrueExpr.h`);
how exec evaluates predicates over chunks producing a **bitset**, which then **prunes** the vector
search (filter-then-search). Diagrams: a `vflow`/`flow` (filter string → expr tree → exec operators →
bitset → ANN); a `layers` (logical expr → physical exec); a `table.t` (expr/exec piece → role). Cite
`internal/core/src/expr/ITypeExpr.h` and an `exec/expression` operator — grep-verify.

### L37 — GPU 加速 / GPU acceleration (`37-gpu-acceleration.html`)
Optional speed. Cover: **Knowhere GPU indexes** — **CAGRA** (GPU graph index) and **GPU_IVF_FLAT/
GPU_IVF_PQ/GPU_BRUTE_FORCE** — these are **Knowhere library** capabilities (NOT defined in milvus core,
same caution as L22 — present as Knowhere names, don't false-attribute to a milvus file); **CPU vs GPU
tradeoff** (GPU wins for huge batch/high-QPS builds & search, costs VRAM + transfer); how Milvus selects
the index engine / device (the **index engine version** negotiation, `internal/datacoord/
index_engine_version_manager.go`, recall L23); the build-on-GPU / search path. Diagrams: a `cols`
(CPU vs GPU); a `table.t` (GPU index → idea → when); a `vflow`/`flow` (build/search on GPU). Cite the
index-engine-version manager (milvus-side, grep-verify); present GPU index names as Knowhere's.

## Wiring
New `src/part8.py` (LESSON_34..37); `registry.py` `import part8` + 4 keys; `shell.PAGES` += 4 (Part 8
label); `shell.SUBTITLES` += 4; `quizzes.QUIZZES` += 4.

## Definition of Done
Gates 0/0; rebuild no-diff; index pill "共 37 课 · 8 个部分"; nav L01..L37; two-stage review passed;
committed.

## Accuracy guardrails
- segcore/core is **C++**, reached via **cgo**; don't depict as Go.
- **GPU index enums are Knowhere's** — present as Knowhere names, don't attribute to milvus core files
  (repeat of the L22 discipline).
- Chunked columns + mmap live in `internal/core/src/mmap`; exec engine in `exec`, logical expr in `expr`.
- file+symbol citations verified in the exact file; only defined CSS classes; small snippets.
