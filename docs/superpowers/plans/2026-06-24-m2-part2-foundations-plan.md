# M2 — Part 2 Foundations (L04–L08) — Plan

Subagent-driven; one implementer builds all 5 lessons into `src/part2.py`, then spec + code reviews.
Spec: `docs/superpowers/specs/2026-06-24-m2-part2-foundations-spec.md`.

## Tasks (one implementer, sequential)
- **L04 Embeddings & similarity** — vectors, L2/IP/COSINE (+HAMMING/JACCARD for binary, IP for
  sparse), normalization, the ANN problem. Cite `pkg/util/metric/metric_type.go`.
- **L05 ANN intuition** — FLAT/IVF/HNSW/PQ/DiskANN families, the speed↔memory↔recall triangle, key
  params (nlist/nprobe, M/ef). Don't fabricate Knowhere paths.
- **L06 Data model** — collection/schema/field/primary-key/dynamic-field/partition/partition-key;
  current DataTypes incl. sparse/float16/bfloat16/int8 vectors. Read `pkg/proto/**/schema*.go`
  (current enum + FieldSchema), cite file+symbol.
- **L07 Segments & log-as-data** — segment unit; Growing→Sealed→Flushing→Flushed→Dropped
  (`SegmentState_*`); vchannel→pchannel; "log as data"; columnar layout. Read `internal/datacoord`,
  `pkg/proto/**/data_coord*.go`.
- **L08 Dependencies & deploy shapes** — etcd / object storage / MQ·WAL (Pulsar/Kafka/woodpecker/
  RocksMQ); Lite vs Standalone vs Cluster. Read `configs/milvus.yaml`, `deployments/`.

Each lesson: content model, **zh ≥ 3500 CJK (aim ~4000)**, ≥3 diagrams/lang, analogy + key-points
cards, cited code (file+symbol), bilingual parity, quiz (2–4 mcq + 1–2 open).

## Wiring
New `src/part2.py` (LESSON_04..08); `registry.py` `import part2` + 5 keys; `shell.PAGES` += 5 (Part 2
label "第二部分 · 前置基础" / "Part 2 · Foundations"); `shell.SUBTITLES` += 5; `quizzes.QUIZZES` += 5.

## Verify
`cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py`
→ 0/0; rebuild no-diff; index pill "共 8 课 · 2 个部分"; nav chain L01..L08 correct.

## Commit
`M2: Part 2 foundations — L04 embeddings, L05 ANN, L06 data model, L07 segments, L08 deps & deploy`
(sign-off + Co-authored-by Copilot).

## Guardrails
Current DataType set (incl. sparse/float16/bfloat16/int8); SegmentState names from code; exact metric
names; verify MQ defaults (RocksMQ standalone, woodpecker built-in WAL) before stating; no fabricated
Knowhere paths; file+symbol citations, small snippets.
