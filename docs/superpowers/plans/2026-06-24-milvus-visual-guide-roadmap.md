# Milvus Visual Guide — Roadmap (milestones)

Companion to `specs/2026-06-24-milvus-visual-guide-design.md`. Each milestone ships its own
**spec** (`specs/…`) and **plan** (`plans/…`), is fully built + validated + reviewed, then
committed. Lesson titles below are the zh / en page titles; `NN` = global lesson number.

**Per-milestone Definition of Done:** lessons authored to the content model; `shell.PAGES`,
`SUBTITLES`, `registry.CONTENT`, `quizzes.QUIZZES` updated; `build.py` + `build_print.py` +
`check_html.py` + `check_links.py` pass (0 errors, 0 warnings); rebuild produces no diff;
two-stage review passed; committed with sign-off.

---

## M0 · Scaffold & pipeline
**Deliverable:** the full Python pipeline + project chrome, proving the toolchain end-to-end by
shipping **L01** as the baseline lesson. No content beyond L01.
- `src/shell.py` (Milvus-themed CSS, PAGES seeded with L01, page/index_page, bi/esc/head_meta).
- `src/registry.py`, `src/part1.py` (L01 only), `src/quizzes.py` (L01 quiz + validator).
- `src/build.py`, `src/build_print.py`, `src/check_html.py`, `src/check_links.py`.
- `.github/workflows/ci.yml` + `deploy.yml`; `README.md`; `LICENSE`; `LICENSE-CONTENT`; `.gitignore`.
- `check_html.py` `MAX_LESSON` starts small and grows per part.
**Key reading:** README.md, README_CN.md (Milvus pitch); the reference `src/` (format).

## M1 · Part 1 — 宏观全景 / Overview (L01–03)
- **L01** Milvus 是什么 / What is Milvus — vector DB, unstructured data, ANN, why a *distributed* DB.
- **L02** 项目全景地图 / The project map — Go + C++ + Rust; coordinators vs nodes; repo layout;
  external deps (etcd / object storage / message-queue·WAL).
- **L03** 一次请求的一生 / Life of a request — insert→search end-to-end at 10,000 ft.
**Key packages:** `cmd/`, `internal/` (top level), `internal/types/types.go`, `internal/distributed`;
docs `developer_guides/chap01_system_overview.md`, README.

## M2 · Part 2 — 前置基础 / Foundations (L04–08)
- **L04** 向量与相似度 / Embeddings & similarity — vectors, L2/IP/cosine, the ANN problem.
- **L05** ANN 算法直觉 / ANN intuition — brute force, IVF, HNSW (graph), PQ, DiskANN — tradeoffs.
- **L06** 数据模型 / Data model — collection, partition, schema, fields, primary key, dynamic field.
- **L07** Segment 与日志即数据 / Segments & log-as-data — growing vs sealed, channels (vchannel/pchannel),
  the append-only mindset.
- **L08** 依赖与部署形态 / Dependencies & deploy shapes — etcd (meta), object storage (binlogs),
  message queue / WAL; standalone vs cluster vs Milvus Lite.
**Key packages:** `pkg/util/typeutil`, `internal/core/src/common` (schema), `internal/storage`;
docs `developer_guides/chap02_schema.md`, README, deployments/, configs/milvus.yaml.

## M3 · Part 3 — 分布式架构 / Distributed architecture (L09–14)
- **L09** 控制面 vs 数据面 / Control plane vs data plane — coordinators, nodes, `types.go` interfaces.
- **L10** Proxy 网关 / The Proxy gateway — gRPC API surface, request routing, rate-limit, auth, task scheduler.
- **L11** RootCoord — DDL, collection/partition metadata, TSO (timestamp oracle), global ID alloc.
- **L12** DataCoord — segment allocation, flush, compaction scheduling, GC, channel assignment.
- **L13** QueryCoordV2 — collection load/release, segment & channel assignment, balance, replicas.
- **L14** 元数据与协调 / Metadata & coordination — etcd usage, metastore/catalog, watch.
**Key packages:** `internal/proxy`, `internal/rootcoord`, `internal/datacoord`, `internal/querycoordv2`,
`internal/metastore`, `internal/tso`, `internal/types/types.go`; docs `chap05/06/07/09`.

## M4 · Part 4 — 写入链路 / The write path (L15–20)
- **L15** 经 Proxy 的插入 / Insert via Proxy — validation, hashing rows to channels, row→segment assignment.
- **L16** 流式系统与 WAL / Streaming & WAL — turning writes into an append-only log (light intro; deep in M7).
- **L17** DataNode 与 flush / DataNode & flush — consuming the stream, growing segments, flush to binlog.
- **L18** Binlog 与存储格式 / Binlog & storage format — insert/delete/stats binlogs, object-storage layout.
- **L19** Compaction 与 GC / Compaction & GC — merging segments, delete handling, garbage collection.
- **L20** 删除与 Upsert / Delete & upsert — delete log, bloom filters, MVCC by timestamp.
**Key packages:** `internal/proxy` (insert task), `internal/streamingnode`, `internal/datanode`,
`internal/flushcommon`, `internal/storage`, `internal/compaction`; docs `chap04`, `chap08_binlog.md`,
`docs/agent_guides/streaming-system/streaming-system.md`.

## M5 · Part 5 — 索引 / Indexing (L21–24)
- **L21** 索引服务 / Index service — how index build is scheduled by DataCoord and run by the
  datanode index worker (no separate indexnode); index meta lifecycle.
- **L22** Knowhere 内核 / Knowhere — the vector-search kernel library; FLAT, IVF_*, HNSW, DiskANN,
  SCANN, GPU/CAGRA; index params.
- **L23** 构建与加载索引 / Build & load — sealed segment → index files → object storage → querynode load.
- **L24** 标量与全文索引 / Scalar & full-text — inverted/bitmap/sort, JSON, the Rust **tantivy** full-text index.
**Key packages:** `internal/datacoord` (index meta/scheduler), `internal/core/src/index`,
`internal/core/src/indexbuilder`, `internal/core/thirdparty/tantivy`; (Knowhere is an upstream lib).

## M6 · Part 6 — 查询链路 / The query path (L25–30)
- **L25** 经 Proxy 的搜索 / Search via Proxy — parse, build search plan, dispatch to shards.
- **L26** QueryNodeV2 与 delegator / QueryNodeV2 & the delegator — shard leader, loading sealed +
  growing segments, segment distribution.
- **L27** Segcore (C++) — how a search runs inside one segment; the `SegmentInterface`.
- **L28** 执行引擎 / Execution engine — plan → expr → exec; scalar filtering + vector search.
- **L29** Reduce 与结果归并 / Reduce & result assembly — per-segment topK → merge → proxy reduce.
- **L30** 一致性与时间戳 / Consistency & timestamps — TSO, guarantee-ts, consistency levels, MVCC.
**Key packages:** `internal/proxy` (search task), `internal/querynodev2`,
`internal/core/src/segcore`, `internal/core/src/query`, `internal/core/src/exec`,
`internal/core/src/expr`; docs `proxy-reduce.md`, `how-guarantee-ts-works.md`.

## M7 · Part 7 — 流式系统 / Streaming system, deep (L31–33)
- **L31** WAL 架构 / WAL architecture — streamingcoord, streamingnode, the WAL abstraction, woodpecker.
- **L32** 通过日志的 DDL/DCL / DDL/DCL through the log — schema changes as messages.
- **L33** 复制与 CDC / Replication & CDC — cross-cluster replication, change data capture.
**Key packages:** `internal/streamingcoord`, `internal/streamingnode`, `internal/cdc`,
`internal/rootcoord` (ddl callbacks); docs `docs/agent_guides/streaming-system/streaming-system.md`
(and its sub-documents — read all for this part).

## M8 · Part 8 — C++ 内核 / C++ core internals (L34–37)
- **L34** core 布局 / The core layout — `segcore`, `index`, `query`, `exec`, `expr`, `mmap`, `storage`, `common`.
- **L35** mmap 与列式分块 / mmap & chunked columns — column storage, the chunk manager, mmap.
- **L36** 表达式与向量化执行 / Expr & vectorized exec — the expression tree, the exec engine, filtering.
- **L37** GPU 加速 / GPU acceleration — CAGRA / GPU indexes, CPU↔GPU dispatch (via Knowhere).
**Key packages:** `internal/core/src/{segcore,mmap,exec,expr,query,storage,common}`,
`internal/core/src/index`.

## M9 · Part 9 — API·工具·运维 / API, tools & ops (L38–41)
- **L38** gRPC API 与 SDK / gRPC API & SDK — MilvusClient / pymilvus; the proxy API surface; milvuspb.
- **L39** 可观测性 / Observability — `mlog` logging, metrics, tracing (Jaeger).
- **L40** 配置 / Configuration — paramtable & `configs/milvus.yaml`.
- **L41** 部署 / Deployment — docker-compose, K8s operator, Helm; standalone vs cluster.
**Key packages:** `pkg/proto`/`milvuspb`, `internal/distributed`, `pkg/.../mlog`,
`pkg/util/paramtable`, `configs/milvus.yaml`, `deployments/`; docs `observability/logging.md`.

## M10 · Part 10 — 实战与贡献 / Practice & contributing (L42–46)
- **L42** 本地构建与运行 / Build & run locally — `scripts/start_standalone.sh`, embedded standalone, Makefile.
- **L43** 测试约定 / Testing conventions — `go test -tags dynamic,test -gcflags=...`, mockery, `make test-*`.
- **L44** 错误·proto·规范 / Errors, proto & conventions — `merr`, proto generation, import order, paramtable.
- **L45** 读码与提 PR / Reading code & contributing — PR/commit conventions, DCO, the contribution flow.
- **L46** 术语表·索引 / Glossary & index — one-line glossary + concept dependency map + jump links.
**Key packages:** `Makefile`, `scripts/`, `DEVELOPMENT.md`, `CONTRIBUTING.md`, `CODE_REVIEW.md`,
`pkg/util/merr`, `docs/dev/error_handling_guide.md`. (L46 is `SOFT_EXEMPT` from CJK/diagram floors.)

## M11 · Polish
- Print/PDF editions verified (one page per lesson, details expanded); CI `print-pdf` job.
- `check_html.py` `MAX_LESSON` finalized; 0 warnings across all lessons.
- README finalized (badges, build/validate/print, structure, license, 中文说明).
- Optional: concept dependency graph on the glossary page; final no-diff + link sweep.

---

## Build order rationale
M0 proves the toolchain with one lesson before any bulk content. Parts then follow the natural
"data lifecycle" arc: understand it (1–2) → architecture (3) → write (4) → index (5) → read (6) →
the streaming subsystem that underpins writes (7) → the C++ compute layer under reads (8) →
operate it (9) → contribute (10) → polish (11). Each part depends only on the scaffold (M0) and,
loosely, on concepts introduced earlier — so cross-references always point backward or are
forward-ref-safe per `check_html.py`.

