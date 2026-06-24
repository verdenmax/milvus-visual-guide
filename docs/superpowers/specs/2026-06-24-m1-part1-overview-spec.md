# M1 — Part 1 Overview (L02–L03) — Spec

**Milestone:** M1 (Part 1 · 宏观全景 / Overview). L01 shipped in M0; M1 adds **L02** and **L03**,
completing Part 1.

## Scope

Two bilingual lessons, authored to the content model in the design spec (lead → analogy card →
macro card → ≥3 diagrams/lang → cited code (file+symbol) → key-points card → quiz). zh ≥ 3000 CJK
(target ~4000). All quality gates 0/0.

### L02 — 项目全景地图 / The project map
**Goal:** a mental map of the codebase: which language does what, the runtime components, the repo
layout, and the external dependencies. The reader should be able to place any later topic on this map.

Must cover (verify against code — **code wins over older docs**):
- **Three languages, three jobs:** Go = distributed control plane (most of `internal/`), C++ =
  compute kernels (`internal/core/`: segcore, index, query, exec, expr), Rust = full-text index
  (`internal/core/thirdparty/tantivy`).
- **Runtime components** (from `cmd/components/` + `cmd/roles/roles.go` + `internal/distributed/`):
  **MixCoord, Proxy, QueryNode, DataNode, StreamingNode, CDC**. CRITICAL ACCURACY POINT: current
  Milvus **merges the three coordinators (Root/Data/Query) into a single `MixCoord` process**
  (`internal/coordinator/mix_coord.go`, `typeutil.MixCoordRole`); the three coordinator *roles*
  still exist as internal modules (`internal/rootcoord`, `internal/datacoord`,
  `internal/querycoordv2`) but deploy together. Standalone runs all components in one process;
  Cluster runs them as separate pods.
- **Repo layout:** `cmd/` (entrypoints), `internal/` (core logic), `pkg/` (shared libs; own
  go.mod `github.com/milvus-io/milvus/pkg/v3`), `client/` (Go SDK `milvusclient`), `configs/`
  (`milvus.yaml`), `deployments/`, `scripts/`, `tests/`, `docs/`.
- **Key `internal/` dirs:** proxy, rootcoord, datacoord, querycoordv2, querynodev2, datanode,
  streamingnode, streamingcoord, coordinator (mixcoord), core (C++), storage, metastore, kv,
  distributed (gRPC servers), types (interfaces `internal/types/types.go`), util.
- **External dependencies:** etcd (metadata), object storage (MinIO/S3; binlogs + index files),
  message queue / WAL (Pulsar / Kafka / built-in woodpecker).
- A **"four groups" mental model** for navigation: ① 接入层 Proxy ② 协调层 MixCoord
  ③ 工作节点 Query/Data/Streaming Node ④ 存储与依赖 etcd/对象存储/MQ — plus the C++ core under the
  worker nodes and the SDK/API on top.

**Diagrams (≥3/lang):** a `layers` diagram (the 4 groups + core + SDK); a `table.t` mapping
component → language → responsibility → internal package; a `cols` (Standalone vs Cluster) or a
`flow`/`vflow` of the repo layout. Cited code: a small snippet from `cmd/roles/roles.go` or
`internal/types/types.go` (file+symbol caption).
**Key packages to read:** `cmd/components/`, `cmd/roles/roles.go`, `internal/distributed/`,
`internal/coordinator/mix_coord.go`, `internal/types/types.go`, top of `internal/`, `pkg/`, `client/`.

### L03 — 一次请求的一生 / Life of a request
**Goal:** trace an **insert** and a **search** end-to-end at 10,000 ft, naming the components they
pass through and the role of timestamps — a skeleton later parts flesh out. Keep it high-level;
forward-reference deep lessons.

Must cover (verify against code):
- **Insert path:** client/SDK → **Proxy** (validate schema, auto-fill primary key if absent, assign
  a **timestamp** from the TSO, hash rows by PK to **vchannels/shards**) → append to the
  **WAL / streaming log** → **StreamingNode/DataNode** consume the log → rows land in a **growing
  segment** → on size/time threshold **flush** to **binlog** in object storage → **DataCoord** tracks
  segment metadata. Mention "log as data" + atomic-visibility of a batch.
- **Search path:** client/SDK → **Proxy** (parse, derive a **guarantee timestamp** from the
  consistency level, build a search plan) → routed by shard to **QueryNode(s)** (the **delegator** /
  shard leader knows which sealed + growing **segments** to hit) → in-segment search runs in
  **segcore (C++)** → per-segment topK → **reduce/merge** on the node → **Proxy** reduces across
  shards → client.
- **Timestamps/MVCC (light):** every request gets a ts; reads use a guarantee ts so they observe a
  consistent snapshot. Defer detail to L30.

**Diagrams (≥3/lang):** a `vflow` or `trace` of the insert path; a second `vflow`/`flow` of the
search path; a `timeline` or `cols` contrasting write vs read; optionally a `table.t` (component →
role in the request). Cited code: a small snippet from `internal/proxy` (e.g. an insert/search task
entry) with a file+symbol caption.
**Key packages to read:** `internal/proxy` (task scheduler, insert/search task), `internal/datanode`,
`internal/streamingnode`, `internal/querynodev2` (delegator), `internal/core/src/segcore`,
`internal/tso`; docs `developer_guides/chap01_system_overview.md` (concept), `proxy-reduce.md`.

## Wiring updates (single source of truth)
- `shell.PAGES`: append L02 (`02-project-map.html`) and L03 (`03-life-of-a-request.html`), both
  Part 1.
- `shell.SUBTITLES`: add concise zh/en subtitles for L02, L03.
- `registry.CONTENT`: add the two keys → `part1.LESSON_02`, `part1.LESSON_03`.
- `src/part1.py`: add `LESSON_02`, `LESSON_03` (bilingual dicts).
- `src/quizzes.py`: add `QUIZZES` entries for both (2–4 MCQs + 1–2 open each).

## Definition of Done
`build.py` + `build_print.py` + `check_html.py` + `check_links.py` → 0 errors, 0 warnings;
rebuild no-diff; index shows "共 3 课 · 1 个部分"; nav chain L01↔L02↔L03 correct; two-stage review
passed; committed.

## Accuracy guardrails (must hold)
- Coordinators are deployed as one **MixCoord** today — do NOT depict three separate coordinator
  processes as the default; explain the logical-vs-physical split.
- Index building is **not** a separate `indexnode` — it is scheduled by DataCoord and run by a
  datanode worker (relevant if mentioned; deep in M5).
- Cite source as **file + symbol**, never bare line numbers. No large source copy beyond a few lines.
