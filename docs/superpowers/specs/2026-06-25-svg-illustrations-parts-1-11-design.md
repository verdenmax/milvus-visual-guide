# SVG Illustrations for Parts 1–11 — Design Spec

**Date:** 2026-06-25
**Status:** Approved (scope confirmed by user)

## Goal

Add hand-drawn, theme-aware, **bilingual** inline-SVG illustrations across the
50 lessons of Parts 1–11 — one to two per lesson, only where a concrete picture
teaches the idea better than prose or the existing CSS-class diagrams. This
extends the SVG visual language already shipped in Part 12 (L51–L56) to the rest
of the guide.

## Why

The guide's first eleven parts (lessons 01–50) currently contain **zero inline
SVGs**; they rely on CSS-class diagrams (`layers`/`flow`/`cols`/`trace`/
`timeline`/`cellgroup`/`vflow`). Those are good for boxes-and-arrows structure
but cannot express the *geometric*, *algorithmic*, and *data-structure* ideas at
the heart of a vector database: distance metrics, HNSW/IVF/PQ, columnar/mmap
layout, expression trees, hierarchical reduce, MVCC, reconcile loops. A learner
understands these far faster from a drawn example. Part 12 proved the SVG
approach renders cleanly in both light and dark mode and passes all gates; this
spec rolls it out everywhere it pays off.

## Scope

**In scope:** ~53 new bilingual SVG illustrations (≈106 `<svg>` instances, zh+en)
distributed across ~40 lessons in Parts 1–11, prioritized by visual payoff.

**Out of scope (no SVG added):** pure command/listing/index lessons where a
drawing adds nothing —
- `38-api-and-sdks` (API/code listing)
- `42-build-and-run` (shell commands)
- `43-testing` (shell commands)
- `45-contributing-prs` (process/checklist)
- `46-glossary` (alphabetical index, has no diagrams by design)

**Stretch (optional, only if time remains):** a second SVG on the richest Part 12
chapters (L53 failover sequence, L55 cgo). Not required for completion.

## Non-goals

- No change to lesson prose, quizzes, navigation, or the CSS-diagram inventory.
  SVGs are *added*, never replacing existing diagrams.
- No new build/gate tooling. Existing `check_html.py` / `check_links.py` must
  keep passing unchanged.
- No raster assets, no external SVG files, no JS. Everything is inline SVG in the
  lesson body string.

## Technical conventions (established in Part 12, reused verbatim)

These are hard rules, already validated against the build gates:

1. **Wrapper:** each illustration is
   `<div class="fig"> <svg …>…</svg> <div class="figcap">…</div> </div>`.
   `.fig` and `.figcap` are defined in `shell.CSS`. The optional `<b>` highlight
   inside `.figcap` uses `--accent-ink`.
2. **Bilingual:** every SVG is authored twice — once in the lesson's `zh` body,
   once in the `en` body — with translated text labels and caption. Same drawing,
   same viewBox.
3. **Theme-aware via inline `style`, never presentation attributes.** SVG
   presentation attributes (`fill="…"`, `stroke="…"`) do **not** support
   `var()`. All themeable color MUST be set with inline
   `style="fill:var(--ink)"` / `style="stroke:var(--line)"` etc., drawing from
   the page's CSS custom properties (`--ink,--panel,--panel-2,--accent,
   --accent-soft,--accent-ink,--blue,--amber,--purple,--red,--teal,--line,
   --muted,--faint` and their `-soft` variants). The class guard ignores
   `style=`. Static, non-themed shapes may use plain attributes.
4. **Accessibility:** root `<svg>` carries `role="img"` and a descriptive
   `aria-label="…"`. Use `viewBox` (no fixed width/height on the root beyond
   what `.fig svg` CSS controls) so it scales responsively.
5. **No `<marker>` elements.** zh and en SVGs share one rendered page, so marker
   `id`s would collide. Draw arrowheads as inline `<path>` triangles.
6. **Monospace text** uses `class="mono"` (globally defined). All other text
   inherits the UI font from `.fig svg` and defaults to `--ink` fill.
7. **Only defined classes.** The class guard requires every `class="…"` token to
   exist in `shell.CSS`. Use only `fig`, `figcap`, `mono` inside SVG/figure
   markup. Everything else is styled inline.

## Gate-safety (verified)

- `check_html.py` balance-checks only `div/details/table/pre/summary` — SVG tags
  are exempt.
- Diagram count uses the 7 `DIAGRAM_CLASSES` + `<table class="t">`; **SVGs are
  not counted**, so the existing ≥3-diagrams-per-language floor is unaffected
  (we are adding, not removing CSS diagrams).
- Raw `<` is only rejected inside `<pre>`; SVG lives outside `<pre>`.
- Lesson bodies are emitted **raw** (`shell.py` page()), so inline SVG passes
  through verbatim.
- `MIN_CJK=3000`: SVG text is mostly short labels. Adding an SVG slightly raises
  CJK count (good) but must not be relied on to *reach* the floor; lessons
  already pass. Re-check after each part.

## Per-lesson SVG catalog

Each entry: **lesson — count — concept(s)**. "Concept" describes what the drawing
shows; exact labels are finalized against the lesson's real text at draw time.
Anchor = where in the body it goes (near the matching prose).

### Part 1 — Overview (3 SVGs)

- **L01 what-is-milvus — 1** — *"相似变距离" kNN picture:* a query point ★ in 2D
  with scattered candidate points; the k nearest highlighted by a radius circle;
  the rest greyed. Caption: search = find nearest neighbors by distance.
  Anchor: near "把'相似'变成'距离'".
- **L02 project-map — 1** — *Logical-one vs physical-two:* one logical
  "collection" box on the left ↔ on the right two physical shapes: **standalone**
  (one process box containing all roles) vs **cluster** (many separate role
  boxes). Anchor: near "逻辑一张图，物理两种形态".
- **L03 life-of-a-request — 1** — *Crash & replay:* a horizontal WAL tape
  (durable) under an in-memory state box; a lightning bolt wipes memory; replay
  arrow rebuilds state from the tape. Anchor: near "崩溃与重放".

### Part 2 — Foundations (8 SVGs)

- **L04 embeddings-and-similarity — 2** —
  (a) *Metrics geometry:* two vectors **u**, **v** from origin; annotate L2 as the
  connecting segment length, cosine as the angle θ between them, inner product as
  projection. One picture, three rulers. Anchor: near "度量：衡量'像不像'".
  (b) *Three rulers, one pair → three numbers:* the same two concrete vectors fed
  to L2 / cosine / IP yielding three different scores side by side. Anchor: near
  "一个算到底的例子".
- **L05 ann-algorithms — 2** —
  (a) *HNSW greedy descent:* a 3-layer graph (sparse top → dense bottom); the
  search path hops across the top layer then drills down, converging on the
  nearest node. Anchor: near the HNSW family entry.
  (b) *IVF Voronoi cells:* points partitioned into nlist cells; a query lands in
  one cell, only the nprobe nearest cells are scanned (highlighted), the rest
  skipped (greyed). Anchor: near the IVF family entry.
- **L06 data-model — 1** — *Hierarchy + partition-key routing:* collection →
  partitions → segments → entities nesting; a partition-key value routes an
  incoming row to one partition by hash. Anchor: near "分区与分区键".
- **L07 segments — 2** —
  (a) *Segment lifecycle:* growing (mutable, in memory) → sealed (immutable) →
  indexed (searchable) as three states on an arrow, with what changes at each.
  Anchor: near "一条数据的一生".
  (b) *Columnar layout:* a row table tipped 90° into per-field column runs (pk,
  vector, scalar) stored contiguously. Anchor: near "列式布局".
- **L08 dependencies-and-deployment — 1** — *Three external deps as a triptych:*
  etcd = ledger (metadata), object store = warehouse (binlogs/indexes), MQ = log
  (WAL), each with its icon and one-line job. Anchor: near "三大外部依赖".

### Part 3 — Architecture (7 SVGs)

- **L09 control-vs-data-plane — 1** — *Two planes + boundary discipline:* top
  control plane (coordinators, thin arrows = decisions/metadata) vs bottom data
  plane (nodes, thick arrows = bulk data); a dashed line marks "data never flows
  through a coordinator". Anchor: near "三条边界纪律".
- **L10 proxy — 2** —
  (a) *Four gates:* a request passes a pipeline of gates auth → authz →
  db-route → rate-limit before entering; a rejected request bounces at a gate.
  Anchor: near "四道关卡".
  (b) *Read vs write split:* one proxy, two divergent internal paths (write →
  WAL append; read → scatter-gather to query nodes). Anchor: near "读与写：两条不同的路".
- **L11 rootcoord — 1** — *TSO: one clock, many readers:* a single monotonic
  counter issuing strictly increasing timestamps to several proxies pulling
  concurrently. Anchor: near "TSO，全集群的统一时钟".
- **L12 datacoord — 1** — *Segment four-state journey:* growing → sealed →
  flushed → (compacted/dropped) with the background action that drives each
  transition (alloc / seal / flush / compact+gc). Anchor: near "段的一生：四个状态".
- **L13 querycoord — 1** — *Distribution vs target reconcile:* current
  distribution (what nodes hold) ≠ target (what should be loaded); the balancer
  emits move/load actions to close the gap; loops forever. Anchor: near
  "分布 vs 目标：永不停歇的校正".
- **L14 metadata-and-coordination — 1** — *etcd as shared truth:* all
  coordinators read/write one etcd hub (watch + CAS); nodes derive state from it.
  Anchor: near the coordination synthesis.

### Part 4 — Write Path (7 SVGs)

- **L15 insert-via-proxy — 1** — *Insert pipeline + atomic batch:* validate →
  hash-to-shard → assign timestamp → append to WAL, with the whole batch
  succeeding or failing as one unit. Anchor: near "原子批与'写成功'的含义".
- **L16 streaming-and-wal — 1** — *WAL is the source, others are projections:*
  one WAL hub feeding three derived forms (in-memory growing segment, flushed
  binlog, query-node copy) — all reconstructable by replay. Anchor: near
  "日志即数据：其他形态靠回放追上".
- **L17 datanode-and-flush — 1** — *One row's flush journey:* row buffered in a
  growing segment in memory → size/time threshold trips → flushed as a binlog
  object to storage. Anchor: near "一行数据落盘的全程".
- **L18 binlog-and-storage — 2** —
  (a) *One segment, a file family:* a segment node fanning out to its products —
  per-field insert binlogs, delete log, stats/BM25, index files. Anchor: near
  "一个段，一族文件".
  (b) *Object-store path layout:* the directory tree
  `files/insert_log/{collID}/{partID}/{segID}/{fieldID}/…` as a labeled path.
  Anchor: near "对象存储里的路径布局".
- **L19 compaction-and-gc — 1** — *Compaction merge:* several small segments plus
  a delete log flowing into one merged, sorted, tombstone-applied segment; GC
  sweeps the now-orphaned old objects. Anchor: near the compaction explanation.
- **L20 delete-and-upsert — 1** — *Bloom-filter delete routing:* a delete-by-PK
  tests each segment's bloom filter; only maybe-matching segments get the
  tombstone; definite-miss segments are skipped. Anchor: near "用布隆过滤器路由一条删除".

### Part 5 — Indexing (5 SVGs)

- **L21 index-service — 1** — *Per-segment index build:* each sealed segment
  becomes an independent build task; one task failing only retries that segment,
  not the whole collection. Anchor: near "为什么'按段'建索引".
- **L22 knowhere — 2** —
  (a) *IVF skips most data:* query → coarse quantizer picks nprobe nearest cells;
  only those cells' vectors are distance-scored; the bulk is skipped. Anchor:
  near "一次 IVF 检索是怎么跳过大半数据的".
  (b) *PQ quantization:* a vector split into M sub-vectors, each mapped to the
  nearest centroid in its sub-codebook, producing a compact M-byte code. Anchor:
  near the PQ/quantization discussion.
- **L23 index-build-and-load — 1** — *Index version management:* an old-format
  (v1) index plus a new (v2) builder; on format upgrade the segment is rebuilt /
  the loader bridges versions. Anchor: near "索引版本管理".
- **L24 scalar-and-fulltext — 1** — *Scalar filter + ANN cooperation:* a scalar
  index yields a bitmap of allowed rows; that bitmap is AND-ed into the ANN
  traversal so only passing candidates are returned (filtered search). Anchor:
  near "标量过滤 + 向量 ANN：一次混合查询怎么协同".

### Part 6 — Query Path (7 SVGs)

- **L25 search-via-proxy — 1** — *Search round-trip:* SDK → proxy → delegator
  fans out to segments → partial results fan in → reduce → result returns. The
  full scatter-gather loop as a sequence. Anchor: near "数据怎么流：从 SDK 到结果".
- **L26 querynode-and-delegator — 1** — *Roles org chart:* the delegator
  (router + merger) sitting over growing + sealed segments and dispatching to
  worker query nodes. Anchor: near "谁是谁：一张角色对照表".
- **L27 segcore — 1** — *Two segment kinds, one interface:* a mutable growing
  segment and an immutable indexed sealed segment both served through one C++
  segment interface. Anchor: near the segcore overview.
- **L28 execution-engine — 2** —
  (a) *Filter string → expression tree:* a predicate like `age > 30 AND city ==
  "NYC"` parsed into a tree of typed nodes. Anchor: near "从过滤字符串到表达式树".
  (b) *Vectorized chunk execution:* a column processed one chunk (batch of N
  rows) at a time through the operator, not row-by-row. Anchor: near
  "向量化执行引擎：一块一块地算".
- **L29 reduce — 1** — *Concrete hierarchical reduce walk-through:* four segments
  each returning a top-3 with real scores → merged per shard → final global top-3,
  showing which rows survive each merge. Anchor: near "一个具体例子：走一遍".
- **L30 consistency-and-timestamps — 1** — *Five levels on a freshness↔latency
  dial:* Strong / Bounded / Session / Eventually placed on a spectrum from
  "freshest, waits longest" to "stalest, no wait"; the `serviceTS ≥ guaranteeTS`
  gate shown as the wait. Anchor: near "五种一致性级别".

### Part 7 — Streaming (3 SVGs)

- **L31 wal-architecture — 1** — *Interceptor chain "过五关":* a write threads
  through ordered interceptors (timetick, ddl, dedup, …) before landing in the
  WAL; each adds/checks something. Anchor: near "拦截器链：每次写入都要'过五关'".
- **L32 ddl-dcl-via-log — 1** — *DML vs DDL on the log:* a single DML entry vs a
  DDL transaction = a grouped set of entries committed together; messages are
  typed. Anchor: near "DML vs DDL：一条日志 vs 一群日志".
- **L33 replication-and-cdc — 1** — *Replicate the log, not the state:* primary
  WAL ships log entries to standbys that replay them; star topology, one primary
  many standbys. Anchor: near "复制的本质" or "角色与拓扑：星型".

### Part 8 — C++ Core (5 SVGs)

- **L34 core-layout — 1** — *cgo handshake + submodule map:* the Go side and C++
  side separated by the cgo boundary; a labeled batched call crosses; the core's
  submodules (segcore, index, exec, common) mapped on the C++ side. Anchor: near
  "cgo 桥：Go 与 C++ 怎么握手".
- **L35 mmap-and-chunks — 2** —
  (a) *Row vs column storage:* the same records stored row-major vs column-major;
  a scan of one field touches scattered bytes (row) vs one contiguous run
  (column). Anchor: near "为什么按列存，而不是按行存".
  (b) *mmap over page cache:* a file on disk mapped into virtual address space;
  pages fault into the OS page cache lazily on first touch, shared with RAM.
  Anchor: near the mmap/chunk discussion.
- **L36 expr-and-exec — 1** — *Logical → physical lowering → pipeline:* a logical
  expression "lowered" into a physical plan, then streamed through the execution
  pipeline operators. Anchor: near "计划如何被'降级'成可执行码".
- **L37 gpu-acceleration — 1** — *Why vectors suit the GPU:* one query vector vs
  thousands of DB vectors = thousands of independent distance computations mapped
  onto parallel SIMT lanes. Anchor: near "为什么向量检索特别适合 GPU".

### Part 9 — Operations (3 SVGs)

- **L39 observability — 1** — *Three pillars converging on one trace:* metrics,
  logs, traces as three lanes; a single request id stitches a trace span across
  proxy → coord → node. Anchor: near "三者合一：在分布式系统里追一个请求".
- **L40 configuration — 1** — *Layered config resolution:* sources stacked by
  priority (built-in default < yaml file < env var < runtime override) collapsing
  to one effective value. Anchor: near "配置从哪来：分层数据源与优先级".
- **L41 deployment — 1** — *Deployment ladder + independent scaling:* embedded →
  standalone → cluster as rungs; in cluster mode each component scales on its own
  axis. Anchor: near "从一行命令到一个集群：部署的阶梯".

### Part 10 — Contributing (1 SVG)

- **L44 code-conventions — 1** — *Input-error vs system-error → retry decision:*
  the blame test branching to two outcomes — client-fixable input error (no
  retry) vs transient system error (retriable). Anchor: near "它决定了'要不要重试'".

### Part 11 — Advanced (4 SVGs)

- **L47 bulk-import — 1** — *Two write paths converge:* streaming (row-by-row via
  WAL) vs bulk import (whole files → direct segment build), meeting at the same
  sealed-segment state. Anchor: near "它和流式写入怎么分工".
- **L48 hybrid-search-rerank — 1** — *RRF fusion:* two ranked lists (vector ANN +
  BM25) merged by reciprocal-rank scoring into one final ordering; show a row
  that ranks mid in both winning overall. Anchor: near "融合：RRF / 加权 / 模型重排".
- **L49 quota-and-rate-limiting — 1** — *Two-stage brake:* as load climbs, first
  a soft throttle (slow down) then a hard reject at the ceiling; backpressure
  curve. Anchor: near "两档刹车：限速与强制拒绝".
- **L50 advanced-features-tour — 1** — *Resource-group + database isolation:*
  tenants mapped to separate resource groups (node pools) and databases so
  workloads don't contend. Anchor: near "隔离与多租户：资源组 + 数据库".

## Success criteria

1. ~53 new bilingual illustrations added (≈106 `<svg>` instances), each wrapped
   in `.fig`/`.figcap`, present in **both** zh and en bodies of its lesson.
2. `cd src && python3 build.py && python3 build_print.py && python3 check_html.py
   && python3 check_links.py` → **"0 error(s), 0 warning(s)"** and **all internal
   links resolve** (count may rise as TOC unaffected; links count stays ≥224).
3. Every new `<svg>` is well-formed XML and uses only inline `style` for themed
   color (no `var()` in presentation attributes), `role="img"`+`aria-label`, no
   `<marker>`, only `fig`/`figcap`/`mono` classes.
4. Visual QA: a sampled render in **both** light and dark mode shows correct
   theming and legible layout (chromium screenshot spot-check per part).
5. Out-of-scope lessons (L38/42/43/45/46) unchanged.
6. Two-stage subagent review (spec-compliance + code-quality, opus) run per
   part-batch; no HIGH issues; any factual claim in an SVG verified against
   Milvus source or the lesson's own (already fact-checked) prose.

## Execution approach

- Work **part-by-part** (Part 1 → Part 11). For each part:
  1. Draw every SVG for that part in both languages, following the conventions,
     anchored as the catalog specifies, refining labels against the real text.
  2. Run the four build/gate commands; fix to 0/0 and links-resolve.
  3. Verify each new `<svg>` is well-formed XML; spot-render light+dark.
  4. Run the two-stage subagent review (opus, current model); address findings.
  5. **Commit that part** (`-s`, Co-authored-by trailer) so progress is durable.
- Push all commits at the end; confirm the deploy workflow succeeds and the live
  site serves the new SVGs.

## Risks & mitigations

- **Visual inconsistency across many SVGs** → reuse the Part-12 idioms (panel
  look, arrowhead paths, palette vars, caption with `<b>` highlight); keep a
  consistent viewBox aspect and stroke weight.
- **Factual drift in a drawn example** → every illustrated mechanism must match
  the lesson's already-fact-checked prose; when a number/threshold is shown, keep
  it illustrative (clearly an example) rather than asserting a specific config.
- **CJK floor regressions from edits** → re-run `check_html.py` after each part;
  SVG text only adds CJK, but verify.
- **zh/en divergence** → author both languages together per SVG; the per-part
  review checks parity.
