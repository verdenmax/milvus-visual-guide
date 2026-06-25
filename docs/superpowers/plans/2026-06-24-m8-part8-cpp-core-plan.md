# M8 — Part 8 C++ Core Internals (L34–L37) — Plan

Subagent-driven; ONE implementer builds 4 lessons into a new `src/part8.py`. Provide PRE-VERIFIED
citations inline + "write first, don't over-research" (a prior dispatch burned its budget reading).
Spec: `docs/superpowers/specs/2026-06-24-m8-part8-cpp-core-spec.md`.

## Tasks (write incrementally)
- **L34 core layout** — `internal/core/src` dirs: segcore/index/query/exec/expr/mmap/storage/common/plan/
  bitset/clustering; the cgo bridge (`*_c.h`); core under QueryNode (search) + index worker (build).
- **L35 mmap & chunked columns** — `internal/core/src/mmap/{ChunkedColumn.h,ChunkedColumnInterface.h,
  ChunkData.h,ChunkVector.h}`; columnar layout; chunks for SIMD/bounded alloc; mmap vs in-memory;
  growing(mutable) vs sealed(mmap-able).
- **L36 expr & vectorized exec** — logical expr tree `internal/core/src/expr/ITypeExpr.h`; exec engine
  `internal/core/src/exec/{Task.h,Driver.h,QueryContext.h}` + physical ops `exec/expression/*.h`
  (BinaryArithOpEvalRangeExpr.h, AlwaysTrueExpr.h); predicate eval over chunks → bitset → prune ANN.
- **L37 GPU acceleration** — Knowhere GPU indexes (CAGRA, GPU_IVF_FLAT/PQ, GPU_BRUTE_FORCE) — present as
  Knowhere names (NOT milvus-core files, L22 discipline); CPU vs GPU tradeoff (VRAM/transfer); index
  engine version negotiation (`internal/datacoord/index_engine_version_manager.go`).

Each: content model; **zh ≥ 3700, aim ~3900**; bilingual parity; quiz (3 mcq + 1 open). Only defined CSS
classes. All these paths are PRE-VERIFIED — inline them in the brief; implementer writes, doesn't re-research.

## Wiring
New `src/part8.py` (LESSON_34..37); `registry.py` `import part8` + 4 keys; `shell.PAGES` += 4 (Part 8
label "第八部分 · C++ 内核" / "Part 8 · C++ core internals"); `shell.SUBTITLES` += 4; `quizzes.QUIZZES` += 4.

## Verify / Commit
Gates 0/0; rebuild no-diff; index pill "共 37 课 · 8 个部分"; nav L01..L37. Commit
`M8: Part 8 C++ core internals — L34 core layout, L35 mmap & chunks, L36 expr & exec, L37 GPU`.

## Review (after)
Two-stage (spec + quality, opus-4.8 max); fix loop; mark M8 done.

## Guardrails
Core is C++ via cgo; GPU index enums are Knowhere's (don't false-attribute); chunked columns + mmap in
`internal/core/src/mmap`; exec in `exec`, logical expr in `expr`; file+symbol citations verified.

## Titles / files
"第八部分 · C++ 内核" / "Part 8 · C++ core internals". Files: 34-core-layout, 35-mmap-and-chunks,
36-expr-and-exec, 37-gpu-acceleration.
