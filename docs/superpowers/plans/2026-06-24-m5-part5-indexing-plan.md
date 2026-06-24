# M5 — Part 5 Indexing (L21–L24) — Plan

Subagent-driven; ONE implementer builds all 4 lessons into a new `src/part5.py` (4 lessons fits a
single dispatch — M2's 5-lesson run succeeded; only the 6-lesson M3 overran). Then spec + code reviews.
Spec: `docs/superpowers/specs/2026-06-24-m5-part5-indexing-spec.md`.

## Tasks (one implementer, write incrementally)
- **L21 Index service** — DataCoord owns index meta + scheduling (`internal/datacoord/index_service.go`,
  `index_meta.go`, `index_inspector.go`); a worker builds (no indexnode); index lifecycle.
- **L22 Knowhere vector indexes** — FLAT/IVF(_FLAT/SQ8/PQ)/HNSW/DiskANN/SCANN/GPU(CAGRA)/sparse;
  params (nlist/nprobe, M/ef). CITATION CARE: most index names are Knowhere-lib enums — cite only what's
  in the cited milvus file (`common/Utils.h` has INDEX_DISKANN; `index/Utils.cpp` has IVF/sparse), present
  the rest as Knowhere names without false file attribution.
- **L23 Build & load** — sealed segment → build task (worker reads binlogs, calls Knowhere) → index files
  in object storage → QueryNode loads; growing uses brute force; index versioning.
- **L24 Scalar & full-text** — inverted (tantivy `InvertedIndexTantivy`), bitmap (`BitmapIndex`),
  sort (`ScalarIndexSort`), ngram (`NgramInvertedIndex`), hybrid (`HybridScalarIndex`), JSON; full-text
  BM25 via Rust **tantivy** (`internal/core/src/index/InvertedIndexTantivy.{cpp,h}` + `thirdparty/tantivy`).

Each lesson: content model (lead→analogy→macro→≥3 diagrams/lang→cited code file+symbol→key card);
**zh ≥ 3700, aim ~3900**; bilingual parity; quiz (2–4 mcq + 1–2 open). Inline the key facts in the
brief; grep only to confirm symbols; write each lesson to the file as you go (don't over-research).

## Wiring
New `src/part5.py` (LESSON_21..24); `registry.py` `import part5` + 4 keys; `shell.PAGES` += 4 (Part 5
label "第五部分 · 索引" / "Part 5 · Indexing"); `shell.SUBTITLES` += 4; `quizzes.QUIZZES` += 4.

## Verify / Commit
Gates 0/0; rebuild no-diff; index pill "共 24 课 · 5 个部分"; nav L01..L24. Commit
`M5: Part 5 indexing — L21 index service, L22 Knowhere, L23 build & load, L24 scalar & full-text`.

## Review (after)
Two-stage (spec + quality, opus-4.8 max); fix loop; mark M5 done.

## Guardrails
DataCoord schedules index build, worker runs it (no indexnode); don't attribute Knowhere enums to
milvus files that lack them (the L05 mistake); tantivy is Rust via `InvertedIndexTantivy`; only use
defined CSS classes (validator enforces); file+symbol citations verified.

## Titles / files
"第五部分 · 索引" / "Part 5 · Indexing". Files: 21-index-service, 22-knowhere, 23-index-build-and-load,
24-scalar-and-fulltext.
