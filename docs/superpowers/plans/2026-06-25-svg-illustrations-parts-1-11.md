# SVG Illustrations for Parts 1–11 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ~53 bilingual, theme-aware, hand-drawn inline SVG illustrations across 45 lessons (Parts 1–11) of the Milvus Visual Guide, one part per task, with gates + review + commit per part.

**Architecture:** Each SVG is inline markup inserted into a lesson's `zh` and `en` body strings in `src/partN.py`, wrapped in a `.fig`/`.figcap` figure, themed via inline `style="…var(--…)…"`. No new tooling; existing `check_html.py`/`check_links.py` gates must keep passing. Build regenerates `lessons/*.html`.

**Tech Stack:** Python string templates (`src/part*.py`), inline SVG, the guide's CSS custom-property palette in `shell.CSS`. Validation: `build.py`, `build_print.py`, `check_html.py`, `check_links.py`, `xmllint`/python `ElementTree` for well-formedness, `chromium --headless` for render QA.

---

## Reference: the shared SVG idiom (reuse for every illustration)

Every illustration follows this skeleton. Copy it, change the drawing, translate
the text. **This is the single source of truth for the conventions** — do not
deviate.

```html
<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="SHORT DESCRIPTION">
    <!-- panel background is supplied by .fig CSS; draw inside the viewBox -->

    <!-- a themed box -->
    <rect x="40" y="40" width="160" height="56" rx="10"
          style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/>
    <text x="120" y="74" text-anchor="middle"
          style="fill:var(--accent-ink);font-weight:700">Label</text>

    <!-- a neutral box -->
    <rect x="40" y="140" width="160" height="48" rx="8"
          style="fill:var(--panel-2);stroke:var(--line);stroke-width:1.5"/>
    <text x="120" y="169" text-anchor="middle" style="fill:var(--ink)">text</text>

    <!-- monospace value -->
    <text x="120" y="200" text-anchor="middle" class="mono"
          style="fill:var(--muted)">tsafe=104</text>

    <!-- a connector + arrowhead drawn as an inline path (NO &lt;marker&gt;) -->
    <line x1="200" y1="68" x2="320" y2="68"
          style="stroke:var(--line);stroke-width:2"/>
    <path d="M320,68 l-10,-5 l0,10 z" style="fill:var(--line)"/>

    <!-- a dashed "logical" connector -->
    <line x1="120" y1="96" x2="120" y2="140"
          style="stroke:var(--accent);stroke-width:1.5;stroke-dasharray:4 4"/>
  </svg>
  <div class="figcap"><b>Headline takeaway</b>：one sentence tying the picture to the lesson's point.</div>
</div>
```

**Rules baked into the skeleton (from the spec):**
- Themed color → inline `style` with `var(--…)`. Never `fill="var(--…)"` (presentation attrs ignore var()).
- Arrowheads → inline `<path>` triangles. **No `<marker>`** (id collisions across zh/en on one page).
- Root `<svg>` → `viewBox` + `role="img"` + `aria-label`. No fixed width/height (responsive via `.fig svg`).
- Classes allowed inside SVG/figure → only `fig`, `figcap`, `mono`. Everything else inline.
- Author **zh and en separately** — two `<div class="fig">…</div>` blocks, one per language body.

## Palette quick-reference (CSS vars available; all have dark-mode swaps)

| token | use |
|---|---|
| `--ink` | default text / strong strokes |
| `--muted`, `--faint` | secondary text, faint guides |
| `--panel`, `--panel-2` | neutral box fills |
| `--line` | borders, connectors, arrowheads |
| `--accent`, `--accent-soft`, `--accent-ink` | primary highlight (box fill / border / text) |
| `--blue`, `--teal`, `--amber`, `--purple`, `--red` | categorical accents (+ `-soft` variants) |

## Per-part workflow (identical for Tasks 1–11)

Each task below lists the SVGs to draw. For **every** task, these are the steps
(the per-lesson drawing is the only thing that varies):

1. **Draw + insert** each SVG for the part, both languages, at the catalog
   anchor, using the idiom above and the lesson's real text for labels.
2. **Build + gates** — run:
   `cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py`
   Expected: `0 error(s), 0 warning(s)` and `all … internal links resolve`.
3. **XML well-formedness** — every new `<svg>` parses (python `ElementTree` on
   each extracted `<svg>…</svg>`). Expected: all parse, 0 errors.
4. **Render QA** — chromium-screenshot the changed lesson(s); eyeball light+dark.
5. **Two-stage review** — dispatch spec-compliance subagent then code-quality
   subagent (opus, current model, long context) on the part's diff. Address
   findings.
6. **Commit** the part (`git add -A && git commit -s` + Co-authored-by trailer).

---
### Task 1: Part 1 (L01–L03) — 3 SVGs

**Files:** Modify `src/part1.py` (LESSON_01, LESSON_02, LESSON_03; zh+en each).

- [ ] **L01 — kNN "相似变距离".** viewBox ~ `0 0 760 320`. Scatter ~14 candidate
  dots (`--faint`), one query ★ (`--accent`), a dashed circle (`--accent`,
  dashed) enclosing the k=4 nearest (filled `--accent-soft`); faint lines query→
  each near point labeled "距离/distance". Anchor (zh): `把"相似"变成"距离"`; (en):
  the parallel "turn similarity into distance" heading. figcap: search = nearest
  by distance.
- [ ] **L02 — logical-one vs physical-two.** Left: one `--accent-soft` box
  "collection / 逻辑集合". Arrow → right: two stacked groups — "standalone" (one
  outer box containing 3 small role chips) and "cluster" (4 separate role boxes).
  Anchor (zh): `逻辑一张图，物理两种形态`; (en) parallel. figcap: same logical
  model, two physical shapes.
- [ ] **L03 — crash & replay.** A long WAL "tape" of cells (101..105) at bottom
  (`--panel-2`, durable). Above it an in-memory box; a `--red` bolt strikes it
  ("crash"); a `--teal` replay arrow from tape → rebuilt memory box. Anchor (zh):
  `崩溃与重放`; (en) parallel. figcap: state is replayable from the log.

### Task 2: Part 2 (L04–L08) — 8 SVGs

**Files:** Modify `src/part2.py` (LESSON_04, 05, 06, 07, 08; zh+en each).

- [ ] **L04a — metrics geometry.** Origin O; two vectors **u**,**v** as arrows
  (paths). Mark: L2 = dashed segment u→v tip (`--amber`); cosine = arc of angle θ
  at O (`--purple`); IP = projection foot of v onto u (`--teal`). Legend chips.
  Anchor (zh): `度量：衡量"像不像"`; (en) parallel.
- [ ] **L04b — three rulers, three numbers.** Same concrete pair (e.g. u=[1,0],
  v=[0.7,0.7]) → three result chips: `L2≈0.77`, `cos≈0.70`, `IP≈0.70` (mono),
  each colored as in L04a. Anchor (zh): `一个算到底的例子`; (en) parallel. Keep
  numbers clearly illustrative.
- [ ] **L05a — HNSW greedy descent.** Three stacked layers (top sparse → bottom
  dense), nodes as dots, a highlighted path (`--accent`) entering top, hopping,
  dropping a layer, converging on target ●. Anchor: the HNSW family entry.
- [ ] **L05b — IVF Voronoi cells.** ~9 cells (light polygons / a 3×3 grid of
  centroids with thin cell borders `--line`); query ★; the nprobe=2 nearest cells
  filled `--accent-soft` ("scanned"), the rest `--faint` ("skipped"). Anchor: the
  IVF family entry.
- [ ] **L06 — hierarchy + partition-key routing.** Nested boxes collection ⊃
  partition ⊃ segment ⊃ entity; a separate incoming row with key=`user_42`, a
  `hash()` chip, arrow routing it to one partition. Anchor (zh): `分区与分区键`.
- [ ] **L07a — segment lifecycle.** Three states on an arrow: growing (mutable,
  `--blue-soft`) → sealed (immutable, `--amber-soft`) → indexed (searchable,
  `--teal-soft`); under each, one line of what changes. Anchor (zh): `一条数据的一生`.
- [ ] **L07b — columnar layout.** A small row table (3 rows × pk/vector/scalar)
  with a "tip 90°" arrow into three contiguous column runs. Anchor (zh): `列式布局`.
- [ ] **L08 — three external deps triptych.** Three panels: etcd = 账本/ledger
  (metadata), object store = 仓库/warehouse (binlogs+indexes), MQ = 日志/log
  (WAL). Icon + one-line job each. Anchor (zh): `三大外部依赖`.

### Task 3: Part 3 (L09–L14) — 7 SVGs

**Files:** Modify `src/part3.py` (LESSON_09–14; zh+en each).

- [ ] **L09 — two planes + boundary.** Top band "control plane" (coords; thin
  arrows = decisions/metadata). Bottom band "data plane" (nodes; thick arrows =
  bulk data). A dashed divider with the rule "数据不穿过协调者 / data never flows
  through a coordinator". Anchor (zh): `三条边界纪律`.
- [ ] **L10a — four gates.** A request token passing 4 sequential gates auth →
  authz → db-route → rate-limit; one variant bounces (`--red`) at rate-limit.
  Anchor (zh): `四道关卡`.
- [ ] **L10b — read vs write split.** One proxy box, two diverging arrows: write
  → WAL append; read → fan-out to query nodes → gather. Anchor (zh):
  `读与写：两条不同的路`.
- [ ] **L11 — TSO one clock, many readers.** A central monotonic counter
  (…1003,1004,1005) issuing increasing ts to 3 proxies pulling concurrently; note
  "strictly increasing, never reused". Anchor (zh): `TSO，全集群的统一时钟`.
- [ ] **L12 — segment four-state journey.** growing → sealed → flushed →
  compacted/dropped on an arrow; under each transition the driver (alloc / seal /
  flush / compact+gc). Anchor (zh): `段的一生：四个状态`.
- [ ] **L13 — distribution vs target reconcile.** Left "current" (node holdings),
  right "target"; a `≠`; balancer emits move/load actions closing the gap; a loop
  arrow "永不停歇". Anchor (zh): `分布 vs 目标`.
- [ ] **L14 — etcd shared-truth hub.** One central etcd cylinder; coords around it
  with watch (read) + CAS (write) arrows; nodes derive state below. Anchor: the
  coordination synthesis paragraph.

### Task 4: Part 4 (L15–L20) — 7 SVGs

**Files:** Modify `src/part4.py` (LESSON_15–20; zh+en each).

- [ ] **L15 — insert pipeline + atomic batch.** validate → hash-to-shard →
  assign-ts → append-WAL as 4 stages; a bracket around the batch labeled
  "all-or-nothing / 原子批". Anchor (zh): `原子批与"写成功"的含义`.
- [ ] **L16 — WAL source + 3 projections.** One WAL hub → three derived forms
  (in-memory growing segment, flushed binlog, query-node copy), each with a
  "replay catches up" note. Anchor (zh): `日志即数据：其他形态靠回放追上`.
- [ ] **L17 — one row's flush journey.** row → growing segment buffer (memory) →
  threshold trips (size/time) → flush → binlog object in storage. Anchor (zh):
  `一行数据落盘的全程`.
- [ ] **L18a — one segment, a file family.** A segment node fanning to: per-field
  insert binlogs (×3), delete log, stats/BM25, index files — grouped/colored by
  kind. Anchor (zh): `一个段，一族文件`.
- [ ] **L18b — object-store path layout.** A path crumb
  `files/insert_log/{collID}/{partID}/{segID}/{fieldID}/log` drawn as nested
  segments (mono), with one leaf highlighted. Anchor (zh): `对象存储里的路径布局`.
- [ ] **L19 — compaction merge.** 3 small segments + a delete log → merge box →
  one clean sorted segment; orphaned old objects marked for GC (`--faint`, ✗).
  Anchor: the compaction explanation.
- [ ] **L20 — bloom-filter delete routing.** A delete(pk=42) tested against each
  segment's bloom filter; "maybe" segments (`--accent-soft`) get the tombstone,
  "definitely-not" segments (`--faint`) skipped. Anchor (zh): `用布隆过滤器路由一条删除`.

---
### Task 5: Part 5 (L21–L24) — 5 SVGs

**Files:** Modify `src/part5.py` (LESSON_21–24; zh+en each).

- [ ] **L21 — per-segment index build.** Several sealed segments → each its own
  build task chip; one task `--red` "failed → retry" while the others stay green
  "done". Anchor (zh): `为什么"按段"建索引`.
- [ ] **L22a — IVF skips most data.** query ★ → coarse quantizer → picks nprobe
  nearest cells (filled `--accent-soft`, "scored"); the rest `--faint`
  ("skipped"); a fraction note "只算 ~nprobe/nlist". Anchor (zh):
  `一次 IVF 检索是怎么跳过大半数据的`.
- [ ] **L22b — PQ quantization.** A vector split into M=4 sub-vectors; each maps
  (arrow) to nearest centroid id in its sub-codebook; output a compact code
  `[12, 7, 30, 3]` (mono). Anchor: the PQ/quantization discussion.
- [ ] **L23 — index version management.** old v1 index block + new v2 builder;
  on upgrade either rebuild (arrow → v2) or loader bridges; note "格式升级了，老索引
  怎么办". Anchor (zh): `索引版本管理`.
- [ ] **L24 — scalar filter + ANN cooperation.** scalar index → bitmap of allowed
  rows (1/0 strip); ANN traversal AND-s the bitmap so only passing candidates
  return. Anchor (zh): `标量过滤 + 向量 ANN：一次混合查询怎么协同`.

### Task 6: Part 6 (L25–L30) — 7 SVGs

**Files:** Modify `src/part6.py` (LESSON_25–30; zh+en each).

- [ ] **L25 — search round-trip.** SDK → proxy → delegator fans out to segments
  (scatter) → partials fan in (gather) → reduce → result back to SDK; number the
  hops 1..6. Anchor (zh): `数据怎么流：从 SDK 到结果`.
- [ ] **L26 — roles org chart.** delegator (router+merger) atop growing+sealed
  segments, dispatching to worker query nodes; label who-does-what. Anchor (zh):
  `谁是谁：一张角色对照表`.
- [ ] **L27 — two segment kinds, one interface.** mutable growing segment +
  immutable indexed sealed segment, both behind one "C++ segment interface" bar.
  Anchor: the segcore overview paragraph.
- [ ] **L28a — filter string → expr tree.** `age > 30 AND city == "NYC"` parsed
  into a tree: AND root, two comparison children with typed leaves. Anchor (zh):
  `从过滤字符串到表达式树`.
- [ ] **L28b — vectorized chunk execution.** a long column processed chunk-by-
  chunk (batches of N) through an operator, not row-by-row; one chunk highlighted
  "in flight". Anchor (zh): `向量化执行引擎：一块一块地算`.
- [ ] **L29 — concrete hierarchical reduce.** 4 segments each top-3 (real scores)
  → per-shard merge → global top-3; trace which rows survive each level (mono
  score chips). Anchor (zh): `一个具体例子：走一遍`.
- [ ] **L30 — five consistency levels dial.** A horizontal spectrum: Strong (waits
  longest, freshest) → Bounded → Session → Eventually (no wait, stalest); mark the
  `serviceTS ≥ guaranteeTS` gate as the "wait". Anchor (zh): `五种一致性级别`.

### Task 7: Part 7 (L31–L33) — 3 SVGs

**Files:** Modify `src/part7.py` (LESSON_31–33; zh+en each).

- [ ] **L31 — interceptor chain "过五关".** A write threading ordered interceptors
  (timetick → ddl → dedup → … → WAL), each a gate adding/checking something.
  Anchor (zh): `拦截器链：每次写入都要"过五关"`.
- [ ] **L32 — DML vs DDL on the log.** Top: one DML cell on the log. Bottom: a DDL
  "transaction" = a bracketed group of cells committed together; both typed.
  Anchor (zh): `DML vs DDL：一条日志 vs 一群日志`.
- [ ] **L33 — replicate the log, star topology.** primary WAL → ship log → 3
  standbys replay; star layout, "复制日志而非状态 / replicate log not state".
  Anchor (zh): `复制的本质` or `角色与拓扑：星型`.

### Task 8: Part 8 (L34–L37) — 5 SVGs

**Files:** Modify `src/part8.py` (LESSON_34–37; zh+en each).

- [ ] **L34 — cgo handshake + submodule map.** A vertical cgo boundary: Go side
  left, C++ side right; one batched call crossing (arrow); C++ submodules
  (segcore, index, exec, common) mapped as chips. Anchor (zh):
  `cgo 桥：Go 与 C++ 怎么握手`.
- [ ] **L35a — row vs column storage.** Same 3 records stored row-major vs
  column-major; a "scan field=vector" highlight touches scattered cells (row) vs
  one contiguous run (column). Anchor (zh): `为什么按列存，而不是按行存`.
- [ ] **L35b — mmap over page cache.** A file on disk (pages) mapped into virtual
  address space; only touched pages fault into the OS page cache (RAM); untouched
  pages stay on disk (`--faint`). Anchor: the mmap/chunk discussion.
- [ ] **L36 — logical → physical lowering → pipeline.** logical expr block →
  "lower" arrow → physical plan → streamed through pipeline operators. Anchor
  (zh): `计划如何被"降级"成可执行码`.
- [ ] **L37 — why vectors suit GPU.** one query vector vs a column of many DB
  vectors → many independent distance calcs mapped onto a grid of SIMT lanes (all
  fire in parallel). Anchor (zh): `为什么向量检索特别适合 GPU`.

---
### Task 9: Part 9 (L39–L41) — 3 SVGs

**Files:** Modify `src/part9.py` (LESSON_39, 40, 41; zh+en each). *(L38 skipped.)*

- [ ] **L39 — three pillars on one trace.** Three lanes metrics / logs / traces;
  one request id stitches a trace span across proxy → coord → node (linked
  spans). Anchor (zh): `三者合一：在分布式系统里追一个请求`.
- [ ] **L40 — layered config resolution.** Stacked sources by priority: default <
  yaml file < env var < runtime override → collapse to one effective value chip
  (highlight the winning layer). Anchor (zh): `配置从哪来：分层数据源与优先级`.
- [ ] **L41 — deployment ladder + independent scaling.** Three rungs embedded →
  standalone → cluster; at cluster, show 3 components each scaling on its own axis
  (×N chips). Anchor (zh): `从一行命令到一个集群：部署的阶梯`.

### Task 10: Part 10 (L44) — 1 SVG

**Files:** Modify `src/part10.py` (LESSON_44; zh+en). *(L42/43/45/46 skipped.)*

- [ ] **L44 — input vs system error → retry.** The "blame test" diamond branching
  to two outcomes: input error (client must fix, **no retry**, `--amber`) vs
  system/transient error (**retriable**, `--teal`). Anchor (zh):
  `它决定了"要不要重试"`.

### Task 11: Part 11 (L47–L50) — 4 SVGs

**Files:** Modify `src/part11.py` (LESSON_47–50; zh+en each).

- [ ] **L47 — two write paths converge.** streaming (row-by-row → WAL) vs bulk
  import (files → direct segment build); both arrive at the same sealed-segment
  state. Anchor (zh): `它和流式写入怎么分工`.
- [ ] **L48 — RRF fusion.** two ranked lists (vector ANN + BM25) merged by
  reciprocal-rank into one final order; highlight a row ranked mid in both that
  wins overall (mono rank/score chips). Anchor (zh): `融合：RRF / 加权 / 模型重排`.
- [ ] **L49 — two-stage brake.** a load/throughput curve rising; first a soft
  throttle zone (`--amber`, "slow down") then a hard reject wall (`--red`) at the
  ceiling. Anchor (zh): `两档刹车：限速与强制拒绝`.
- [ ] **L50 — resource-group + database isolation.** tenants A/B mapped to
  separate resource groups (node pools) and databases so workloads don't contend
  (two non-overlapping lanes). Anchor (zh): `隔离与多租户：资源组 + 数据库`.

---

### Task 12: Final — push + verify deploy

**Files:** none (git + verification only).

- [ ] **Re-run full gates once more** across the whole repo:
  `cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py`
  Expected: `0 error(s), 0 warning(s)`, links resolve.
- [ ] **Confirm SVG inventory:** every covered lesson now has the expected SVG
  count (2 per language for the 8 two-SVG lessons, 1 otherwise); all `<svg>`
  well-formed. (`grep -c '<svg viewBox' lessons/<file>` == 2× per-lang count.)
- [ ] **Push:** `git push origin master`.
- [ ] **Verify deploy:** wait for the Pages workflow to go green; curl a couple of
  Part-1/Part-6 lessons on the live site and confirm `<svg viewBox` is present.
- [ ] **Report** a concise summary to the user (counts per part, live URL).

## Notes for the executor

- **Anchors:** the zh anchor strings above are the unique heading/phrase to locate
  the insertion point with an `edit` (place the `.fig` block just *before* the
  matching `<h2>`/`<p>`). The en body uses the parallel English heading — find it
  the same way; en text may wrap across source lines, so anchor on a unique
  line-final fragment. A few headings are NOT unique across chapters — always
  include enough surrounding context in the `edit` `old_str`.
- **CJK floor:** Part-12 prose was English-dense and undershot `MIN_CJK=3000`;
  Parts 1–11 prose is CJK-heavier and already passes, but re-run `check_html.py`
  after each part — SVG labels add a little CJK, never remove it.
- **Two-SVG lessons** (draw both): L04, L05, L07, L10, L18, L22, L28, L35.
- **Skipped lessons** (do NOT touch): L38, L42, L43, L45, L46.
- **Commit message** per part: `feat(partN): add SVG illustrations to <lessons>`
  + Co-authored-by trailer; sign with `-s`.
