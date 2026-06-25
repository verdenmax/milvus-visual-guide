# Part 12 — Design Themes (synthesis) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new Part 12 of 6 bilingual cross-cutting "design theme" capstone chapters (L51–L56) that synthesize the existing module-by-module lessons around six big design goals.

**Architecture:** Reuse the existing zero-dependency Python generator. Each chapter is a `LESSON_NN = {"zh", "en"}` HTML-fragment dict in a new `src/part12.py`, wired through `registry.py` / `shell.py` (PAGES + SUBTITLES) / `quizzes.py`, validated by the existing `check_html.py` / `check_links.py` gates, and built by `build.py` / `build_print.py`. Generated output is committed in sync with sources.

**Tech Stack:** Python 3 (stdlib only). Same CSS diagram vocabulary as the existing 50 lessons (layers / vflow / flow / cols / cellgroup / timeline / trace + `<table class="t">`).

**Spec:** `docs/superpowers/specs/2026-06-25-part12-design-themes-spec.md`

---

## File Structure

- Create: `src/part12.py` — the 6 lesson dicts `LESSON_51 … LESSON_56` (one Part 12 module, mirrors part11.py).
- Modify: `src/registry.py` — `import part12`; append the 6 filename → dict entries (in order) to `CONTENT`.
- Modify: `src/shell.py` — append 6 `PAGES` tuples and 6 `SUBTITLES` entries (PLAIN `&`/`<`, escaped at render).
- Modify: `src/quizzes.py` — append 6 quiz entries (3 MCQ + 1 open each).
- Modify: `src/check_html.py` — bump `MAX_LESSON` 50 → 56.
- Modify: `README.md` — 11→12 parts, 50→56 lessons (badges, status, table, part-module range, Chinese section).
- Generated (committed): `index.html`, `lessons/51..56-*.html`, `print_zh.html`, `print_en.html` (produced by build, not hand-edited).

## Lesson numbering & filenames (fixed)

| # | filename | zh title | en title |
|---|---|---|---|
| L51 | `51-design-log-as-data.html` | 日志即数据：为什么整个系统都围着 WAL 转 | Log as data: why the whole system orbits the WAL |
| L52 | `52-design-query-while-write.html` | 边写边查还保证正确：一致性是怎么炼成的 | Query-while-you-write, correctly: how consistency is forged |
| L53 | `53-design-storage-compute-separation.html` | 存算分离：为什么节点可以是“无状态”的 | Storage–compute separation: why nodes can be stateless |
| L54 | `54-design-scale-to-billions.html` | 扩展到十亿级：分而治之的艺术 | Scaling to billions: the art of divide-and-conquer |
| L55 | `55-design-two-languages.html` | 两种语言，一套系统：C++ 内核与 Go 编排的分工 | Two languages, one system: the C++ kernel / Go orchestration split |
| L56 | `56-design-failure-as-default.html` | 故障是常态：系统如何自愈 | Failure as the default: how the system heals itself |

Part label (PAGES cols 4–5): `第十二部分 · 设计专题（综合）` / `Part 12 · Design themes (synthesis)`.

## Shared per-chapter template (every chapter follows this)

Each chapter is the same three-beat arc (from the spec). The reusable shape:

```
LESSON_NN = {
    "zh": r"""
<p class="lead" ...>            # 1–2 sentence hook naming the design goal
<div class="card analogy">…</div>   # everyday analogy for the goal
<h2>目标：…为什么非做不可</h2>      # the goal + what breaks without it
<p>…</p>
<div class="card macro">…</div>     # big-picture framing of the synthesis
<h2>各模块为它做了什么（一）…</h2>  # per-module efforts, grouped (2–3 h2 sections)
<p>… 第 N 课 …</p>                  # cross-reference the synthesized lessons
<DIAGRAM>                            # flow/layers/trace tying modules together
… (≥3 true diagrams total per language, identical zh/en inventory)
<h2>代价与取舍：放弃了什么</h2>      # payoff + the rejected alternative
<p>…</p>
<div class="card key"><div class="tag">📌 本课要点</div><ul>…5 bullets…</ul></div>
""",
    "en": r"""…faithful, balanced English counterpart, same sections + same diagram inventory…""",
}
```

Hard requirements per chapter (checked by `check_html.py`):
- zh ≥ 3000 CJK (aim ~3500); en a balanced counterpart (not a thin abridgement).
- ≥ 3 true diagrams **per language**; **identical** zh/en diagram inventory.
- `card analogy` + `card macro` + `card key` ("本课要点"/"Key points") in both langs.
- No `<h1>` in body; escape literal `<`/`&`; cross-refs "第 N 课"/"Lesson N" with N ≤ 56.
- Only the defined CSS classes (no new vocabulary).

## Per-chapter authoring micro-workflow (used inside each Task below)

1. **Research** the factual claims against the Milvus source at `/home/verden/course/milvus` (the chapter synthesizes already-covered material, but every cited file/symbol/number must still be verified).
2. Draft `zh` into a temp file, append to `part12.py`.
3. Verify CJK ≥ 3000: `python3 -c "import importlib,part12,re; importlib.reload(part12); print(len(re.findall(r'[\u4e00-\u9fff]', part12.LESSON_NN['zh'])))"`; pad with real content until ≥3000 (~3500).
4. Write `en` at structural + substantive parity (same h2 sections, same diagram inventory).
5. Wire: registry mapping, `PAGES` tuple, `SUBTITLES` entry, quiz entry.
6. `cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py` → 0/0 and all links resolve.
7. Commit with `-s` + Co-authored-by trailer.

---
## Task 1: Part 12 scaffolding

**Files:**
- Create: `src/part12.py`
- Modify: `src/registry.py`
- Modify: `src/check_html.py`

- [ ] **Step 1: Create `src/part12.py` with a module header** (no lessons yet)

```python
# Part 12 — Design themes (synthesis). Cross-cutting capstone chapters L51–L56.
# Each lesson is a bilingual HTML fragment dict, same shape as part1..part11.
```

- [ ] **Step 2: Bump MAX_LESSON** in `src/check_html.py` from `MAX_LESSON = 50` to `MAX_LESSON = 56`.

Run: `cd src && grep -n "MAX_LESSON =" check_html.py`
Expected: shows `MAX_LESSON = 56`.

- [ ] **Step 3: Import part12 in `src/registry.py`** (add `import part12` alongside the other `import partN`).

- [ ] **Step 4: Verify nothing breaks** (no lessons added yet, registry import only)

Run: `cd src && python3 -c "import registry; print(len(registry.CONTENT))"`
Expected: `50` (unchanged — part12 has no entries yet).

- [ ] **Step 5: Commit**

```bash
git add src/part12.py src/registry.py src/check_html.py
git commit -s -m "feat(part12): scaffold design-themes module + bump MAX_LESSON to 56"
```

---

## Task 2: L51 — 日志即数据 / Log as data

**Files:**
- Modify: `src/part12.py` (add `LESSON_51`)
- Modify: `src/registry.py` (map `51-design-log-as-data.html` → `part12.LESSON_51`)
- Modify: `src/shell.py` (PAGES tuple + SUBTITLES for L51)
- Modify: `src/quizzes.py` (quiz for `51-design-log-as-data.html`)

**Goal of the chapter:** Make writes fast, durable, and replayable by treating the
append-only log (WAL) as the single source of truth; segments/indexes are derived
views. Show what each module does in service of "the log is the truth".

**Three-beat content:**
1. **Goal & why** — Without a log-as-truth design you must choose between "write fast"
   and "query fast" and you can't recover cleanly after a crash. Analogy: a restaurant
   that writes every order on one ever-growing ticket roll (the log); the kitchen
   board, receipts, and ledger are all *rebuilt* from that roll.
2. **Per-module efforts (2–3 h2):**
   - *Write side*: Proxy appends to the WAL (第 15 课), the StreamingNode owns the WAL
     and stamps a monotonic TimeTick (第 16 课 / 第 31 课); the write returns success
     the moment it is logged.
   - *Materialize side*: DataNode follows the log to build growing segments and flush
     binlogs (第 17 课); indexes are built later (第 21/23 课). These are *derived*.
   - *Consume side*: QueryNode's delegator replays the WAL tail to keep growing data
     fresh (第 26 课); DDL rides the same log (第 32 课); replication just replays the
     log into another cluster (第 33 课); crash recovery = replay from checkpoint.
3. **Payoff & tradeoff** — decouples write-speed from query-speed, makes recovery a
   replay, makes many consumers independent; cost is eventual-materialization latency
   and the "log is now the most critical thing to protect" (主次反转 / inversion).

**Diagrams (≥3 per lang, identical inventory):**
- `flow`: Client → Proxy(append) → WAL → {DataNode flush, QueryNode consume, Replicator} (one log, many consumers).
- `layers`: WAL as the trunk (l-main) with segments / indexes / replica as derived layers.
- `trace` or `timeline`: a single write's TimeTick flowing to each consumer at its own pace.

- [ ] **Step 1: Research facts** against `/home/verden/course/milvus`

Verify: Proxy WAL append path (`streaming.WAL().AppendMessages`), TimeTick interceptor,
DataNode flusher follows WAL, delegator consumes WAL tail, Replicate interceptor preserves
TimeTick. (Most already verified in the L16/L26/L31/L33 audit; re-confirm any new symbol.)

- [ ] **Step 2: Write `LESSON_51["zh"]`** following the shared template (3-beat arc, the
  3 diagrams above, analogy+macro+key cards). Append to `src/part12.py`.

- [ ] **Step 3: Verify CJK ≥ 3000**

Run: `cd src && python3 -c "import importlib,part12,re; importlib.reload(part12); print(len(re.findall(r'[\u4e00-\u9fff]', part12.LESSON_51['zh'])))"`
Expected: ≥ 3000 (pad with real content until ~3500 if short).

- [ ] **Step 4: Write `LESSON_51["en"]`** at structural + substantive parity (same h2s, same diagram inventory).

- [ ] **Step 5: Wire registry / PAGES / SUBTITLES / quiz**
  - `registry.py`: add `"51-design-log-as-data.html": part12.LESSON_51,` in order.
  - `shell.py` PAGES: `("51-design-log-as-data.html", "日志即数据：为什么整个系统都围着 WAL 转", "Log as data: why the whole system orbits the WAL", "第十二部分 · 设计专题（综合）", "Part 12 · Design themes (synthesis)"),`
  - `shell.py` SUBTITLES: a one-line zh/en subtitle entry.
  - `quizzes.py`: 3 MCQ (4 opts, correct first, answer:0, bilingual q/opts/why) + 1 open, keyed `"51-design-log-as-data.html"`.

- [ ] **Step 6: Build + gates**

Run: `cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py`
Expected: `0 error(s), 0 warning(s)` and `all internal links resolve`.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -s -m "feat(part12): L51 log-as-data design theme"
```

---
## Task 3: L52 — 边写边查还保证正确 / Query-while-you-write, correctly

**Files:** `src/part12.py` (LESSON_52), `src/registry.py`, `src/shell.py`, `src/quizzes.py`

**Goal of the chapter:** Let a reader see freshly-written data immediately (with a
freshness level *they* choose) while results stay correct and self-consistent in a
distributed system. Show how the timestamp machinery makes this possible.

**Three-beat content:**
1. **Goal & why** — "Insert then immediately search and find it" is table stakes for a
   vector DB, but in a distributed system writes flow asynchronously, so naïvely you'd
   either block everything (slow) or return stale/garbled results (wrong). Analogy:
   a library where every book gets a timestamped check-in slip; a query says "show me
   the shelf as of 3:00pm" and the desk waits only until every aisle has filed up to 3:00.
2. **Per-module efforts (2–3 h2):**
   - *Stamping*: RootCoord's TSO hands out a global monotonic timestamp; every write and
     read is stamped (第 11 / 第 30 课).
   - *Choosing freshness*: the Proxy derives a guarantee ts Tg from the consistency level
     (Strong/Bounded/Session/Eventually/Customized) (第 25 / 第 30 课).
   - *Waiting + visibility*: the QueryNode waits until its tsafe ≥ Tg (第 26 / 第 30 课);
     segcore applies MVCC — a row is visible iff insert ts ≤ Tg and no tombstone ≤ Tg
     (第 20 tombstones / 第 30 MVCC); growing+sealed segments make new data visible (第 7 课).
3. **Payoff & tradeoff** — read-your-writes + a freshness/latency dial in the caller's
   hands; cost is the wait under Strong and the per-vchannel tsafe dependency.

**Diagrams (≥3 per lang):**
- `timeline`: write TimeTicks rising; a read with Tg suspends until tsafe ≥ Tg, then answers.
- `cellgroup`: MVCC visibility — rows with insert/delete ts vs a Tg, who is visible.
- `flow`: TSO → Proxy(derive Tg) → QueryNode(wait tsafe) → segcore(MVCC) → result.

- [ ] **Step 1: Research** — re-confirm `parseGuaranteeTsFromConsistency`, tsafe/TimeTick,
  MVCC visibility rule, Strong=tMax / Bounded=tMax−gracefulTime / Eventually=1 (from L30 audit).
- [ ] **Step 2: Write `LESSON_52["zh"]`** (3-beat arc + the 3 diagrams + 3 cards).
- [ ] **Step 3: Verify CJK ≥ 3000** (`reload part12; count LESSON_52['zh']`); pad to ~3500.
- [ ] **Step 4: Write `LESSON_52["en"]`** at parity.
- [ ] **Step 5: Wire** registry / PAGES (`52-design-query-while-write.html`, titles from the table) / SUBTITLES / quiz.
- [ ] **Step 6: Build + gates** → 0/0, links resolve.
- [ ] **Step 7: Commit** `feat(part12): L52 query-while-write consistency design theme`

---

## Task 4: L53 — 存算分离 / Storage–compute separation

**Files:** `src/part12.py` (LESSON_53), `src/registry.py`, `src/shell.py`, `src/quizzes.py`

**Goal of the chapter:** Scale compute and storage independently and fail over fast by
keeping worker nodes (near-)stateless — durable bytes live in object storage, metadata in
etcd, and nodes just process.

**Three-beat content:**
1. **Goal & why** — coupling compute to local disk means you can't scale them separately
   and a node crash risks data. Analogy: a kitchen (compute) that owns no pantry — all
   ingredients live in a shared warehouse (object storage); any cook can be added/replaced
   because nothing important lives *in* the cook.
2. **Per-module efforts (2–3 h2):**
   - *Durable bytes elsewhere*: binlogs + index files go to object storage (第 8 / 第 18 课);
     it's the decoupling point between the build side (DataNode worker, 第 21/23 课) and the
     load side (QueryNode, 第 23 课), which need never talk directly.
   - *Load cheaply*: QueryNode loads via mmap so an index bigger than RAM still serves (第 35 课).
   - *State lives in the control plane*: metadata in etcd via the Catalog/kv layers (第 14 课);
     QueryCoord assigns/balances segments (第 13 课); a lost node's work is reassigned and
     reloaded from object storage (fast failover, ties to 第 56 课).
3. **Payoff & tradeoff** — elastic, independent scaling + cheap durability + fast failover;
   cost is object-storage latency (mitigated by caching/mmap/growing segments) and an
   extra network hop vs local disk.

**Diagrams (≥3 per lang):**
- `layers`: control plane (etcd metadata) / compute (stateless DataNode+QueryNode) / storage (object storage) as separated tiers.
- `flow`: build side → object storage → load side (object storage as the decoupling pivot).
- `cols`: "stateful local-disk node" vs "stateless node + shared storage" tradeoff.

- [ ] **Step 1: Research** — object storage usage (binlog/index), `loadSealedSegment` + mmap,
  Catalog/kv → etcd, segment reassignment on node loss (from L08/L18/L23/L35/L13/L14 audit).
- [ ] **Step 2: Write `LESSON_53["zh"]`** (3-beat + 3 diagrams + 3 cards).
- [ ] **Step 3: Verify CJK ≥ 3000**; pad to ~3500.
- [ ] **Step 4: Write `LESSON_53["en"]`** at parity.
- [ ] **Step 5: Wire** registry / PAGES (`53-design-storage-compute-separation.html`) / SUBTITLES / quiz.
- [ ] **Step 6: Build + gates** → 0/0, links resolve.
- [ ] **Step 7: Commit** `feat(part12): L53 storage-compute separation design theme`

---
## Task 5: L54 — 扩展到十亿级 / Scaling to billions

**Files:** `src/part12.py` (LESSON_54), `src/registry.py`, `src/shell.py`, `src/quizzes.py`

**Goal of the chapter:** Serve billions of vectors at low latency and cost by dividing the
problem so only tiny, K-scale data ever moves and everything runs in parallel.

**Three-beat content:**
1. **Goal & why** — a single machine can't hold or scan a billion vectors; brute force is
   hopeless. Analogy: a nationwide manhunt run by precincts — each precinct searches its own
   district and reports only its top suspects upward; headquarters never sees every citizen.
2. **Per-module efforts (2–3 h2):**
   - *Cut the data up*: collections are split into immutable segments across shards
     (第 7 / 第 12 课); a shard = a vchannel = a parallel unit.
   - *Scatter then gather*: Proxy fans a search out to shards → delegators → segments; each
     computes a local topK; results converge through the three-level reduce (segment → node
     → Proxy), each level passing only K candidates up (第 3 / 第 25 / 第 29 课).
   - *Make each unit cheap*: per-segment ANN index instead of brute force (第 21/23 课); scalar
     filter pushdown (bitset) prunes before the expensive vector step (第 28 课).
3. **Payoff & tradeoff** — near-linear horizontal scale and tiny network traffic; cost is
   approximate recall (set in-segment, not by reduce) and the cost of deep pagination / huge K.

**Diagrams (≥3 per lang):**
- `trace`: scatter-gather — q → shards → segments → local topK → node topK → global topK.
- `flow`: divide (segments/shards) → conquer (parallel ANN) → combine (reduce).
- `cellgroup` or `cols`: "only K flows per level" vs "pull all vectors back" (why it scales).

- [ ] **Step 1: Research** — segmentation, scatter-gather fan-out, three-level reduce
  (segment/node/Proxy), scalar bitset pushdown (from L07/L12/L25/L28/L29 audit).
- [ ] **Step 2: Write `LESSON_54["zh"]`** (3-beat + 3 diagrams + 3 cards).
- [ ] **Step 3: Verify CJK ≥ 3000**; pad to ~3500.
- [ ] **Step 4: Write `LESSON_54["en"]`** at parity.
- [ ] **Step 5: Wire** registry / PAGES (`54-design-scale-to-billions.html`) / SUBTITLES / quiz.
- [ ] **Step 6: Build + gates** → 0/0, links resolve.
- [ ] **Step 7: Commit** `feat(part12): L54 scale-to-billions design theme`

---

## Task 6: L55 — 两种语言，一套系统 / Two languages, one system

**Files:** `src/part12.py` (LESSON_55), `src/registry.py`, `src/shell.py`, `src/quizzes.py`

**Goal of the chapter:** Get raw numeric speed AND distributed-systems development velocity
by splitting the system: a C++ kernel for the hot compute path, Go for orchestration, joined
by a deliberately thin cgo boundary.

**Three-beat content:**
1. **Goal & why** — pure Go can't match hand-tuned SIMD/GPU numeric kernels; pure C++ makes
   distributed orchestration painful and slow to build. Analogy: a race team — a custom-built
   engine (C++ kernel) bolted into a comfortable, serviceable chassis (Go) — each chosen for
   what it's best at.
2. **Per-module efforts (2–3 h2):**
   - *Hot path in C++*: segcore + Knowhere/FAISS do filtering, ANN search, reduce, and own the
     columnar data layout / SIMD / GPU (第 22 / 第 27 / 第 34 / 第 36 课).
   - *Orchestration in Go*: coordinators and nodes do scheduling, RPC, metadata, WAL plumbing
     (第 9–13 课) — where Go's concurrency and ecosystem shine.
   - *A thin, careful bridge*: cgo joins them with coarse-grained, zero-copy calls that also
     carry trace/timeout/error context (第 34 课); plus a little Rust (tantivy full-text, 第 24 课).
3. **Payoff & tradeoff** — best-of-both performance and velocity; cost is the cgo boundary's
   fixed per-call overhead (hence "coarse-grained, zero-copy, batch") and two-language build
   complexity (第 42 课).

**Diagrams (≥3 per lang):**
- `layers`: Go orchestration (top) / cgo boundary (thin middle) / C++ kernel + Knowhere (bottom) / + Rust tantivy.
- `flow`: a search crossing Go → cgo → segcore → back, batched (one crossing per segment).
- `cols`: "what Go is best at" vs "what C++ is best at" (why split here).

- [ ] **Step 1: Research** — segcore/Knowhere C++, cgo bridge (coarse-grained/zero-copy/context),
  tantivy=Rust, two-stage build (from L22/L27/L34/L36/L24/L42 audit). No mis-attribution of
  Knowhere algorithms to milvus core.
- [ ] **Step 2: Write `LESSON_55["zh"]`** (3-beat + 3 diagrams + 3 cards).
- [ ] **Step 3: Verify CJK ≥ 3000**; pad to ~3500.
- [ ] **Step 4: Write `LESSON_55["en"]`** at parity.
- [ ] **Step 5: Wire** registry / PAGES (`55-design-two-languages.html`) / SUBTITLES / quiz.
- [ ] **Step 6: Build + gates** → 0/0, links resolve.
- [ ] **Step 7: Commit** `feat(part12): L55 two-languages design theme`

---
## Task 7: L56 — 故障是常态 / Failure as the default

**Files:** `src/part12.py` (LESSON_56), `src/registry.py`, `src/shell.py`, `src/quizzes.py`

**Goal of the chapter:** Survive crashes with no data loss and no downtime by assuming
failure is normal and building self-healing in from the start.

**Three-beat content:**
1. **Goal & why** — at scale something is always crashing; a design that assumes "happy path"
   loses data or stalls. Analogy: a city's power grid — built to reroute around any failed
   substation automatically, because outages are expected, not exceptional.
2. **Per-module efforts (2–3 h2):**
   - *Never lose committed work*: WAL + checkpoint + replay (第 16 / 第 31 课); recovery = resume
     replaying from the last checkpoint; replication keeps an off-site replayable copy (第 33 课).
   - *Reconcile back to intent*: DataCoord's index inspector re-dispatches failed builds (第 21 课);
     QueryCoord's balancer reassigns segments off a dead node (第 13 课) — declared state vs actual
     state, continuously converged.
   - *Detect + coordinate*: etcd session + lease detect node liveness (第 14 课); the Broadcaster
     makes DDL all-or-nothing so a half-applied change can't corrupt metadata (第 32 课); index
     engine versioning keeps rolling upgrades non-disruptive (第 23 课).
3. **Payoff & tradeoff** — durability + self-healing + zero-downtime upgrades; cost is the
   bookkeeping (checkpoints, reconciliation loops, version negotiation) and eventual—not
   instant—recovery.

**Diagrams (≥3 per lang):**
- `flow`: node dies → lease expires → segments/tasks reassigned → reload from object storage → replay WAL tail → back to live.
- `vflow`: checkpoint → crash → replay-from-checkpoint → caught up.
- `cols` or `layers`: the layers of resilience (log/replay · reconcile · session/lease · atomic DDL).

- [ ] **Step 1: Research** — checkpoint/replay, index inspector reconcile, balancer reassign,
  session+lease, Broadcaster atomic DDL, index-engine version negotiation (from L13/L14/L21/L23/L31/L32 audit).
- [ ] **Step 2: Write `LESSON_56["zh"]`** (3-beat + 3 diagrams + 3 cards). As the final lesson of the guide, end with a one-paragraph send-off tying the six design themes together.
- [ ] **Step 3: Verify CJK ≥ 3000**; pad to ~3500.
- [ ] **Step 4: Write `LESSON_56["en"]`** at parity.
- [ ] **Step 5: Wire** registry / PAGES (`56-design-failure-as-default.html`) / SUBTITLES / quiz.
- [ ] **Step 6: Build + gates** → 0/0, links resolve.
- [ ] **Step 7: Commit** `feat(part12): L56 failure-as-default design theme`

---

## Task 8: Finalize — counts, closers, full validation

**Files:** `README.md`, plus any prior-lesson closer that should point forward to Part 12.

- [ ] **Step 1: Update `README.md`** — 11→12 parts, 50→56 lessons:
  - badges `parts-11`→`parts-12`, `lessons-50`→`lessons-56`;
  - status line "11 parts / 50 lessons" → "12 parts / 56 lessons" (EN + 中文);
  - parts table: add a Part 12 row (`Design themes (synthesis) … | L51-56`);
  - project structure `part1.py .. part11.py` → `part1.py .. part12.py`;
  - Chinese section: "十一个部分"→"十二个部分", add `⑫ 设计专题（L51-56）`.

- [ ] **Step 2: (Optional) Update the L50 closer** to point readers onward to Part 12, if it
  currently reads as the end of the guide. Keep it light; do not renumber anything.

- [ ] **Step 3: Clean full rebuild + all gates**

Run: `cd src && rm -rf ../lessons ../print 2>/dev/null; python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py`
Expected: 56 lessons checked, `0 error(s), 0 warning(s)`, `all internal links resolve`.

- [ ] **Step 4: Verify quiz integrity** (56 - 1 glossary = 55 quizzes, each 3 MCQ×4 opts, answer 0, 1 open)

Run: `cd src && python3 -c "import quizzes; bad=[(k,len(q['mcq'])) for k,q in quizzes.QUIZZES.items() if len(q['mcq'])!=3]; print('bad:', bad or 'NONE', '| total:', len(quizzes.QUIZZES))"`
Expected: `bad: NONE | total: 55`.

- [ ] **Step 5: Confirm index pill + homepage** show "共 56 课 · 12 个部分".

- [ ] **Step 6: Commit + push**

```bash
git add -A
git commit -s -m "feat(part12): finalize design themes — 12 parts / 56 lessons"
git push origin master
```

---

## Self-Review (run after writing all tasks)

- **Spec coverage:** all 6 spec chapters → Tasks 2–7; placement/wiring/MAX_LESSON → Tasks 1 & 8;
  format requirements → embedded in every chapter task's steps. ✓
- **Placeholder scan:** each chapter task carries its concrete goal, per-module sections (with
  lesson cross-refs), and named diagrams — no "TBD"/"similar to". ✓
- **Consistency:** filenames/titles match the spec table and the PAGES wiring lines; MAX_LESSON=56
  matches the ≤56 cross-ref rule; quiz shape (3 MCQ + 1 open) matches existing convention. ✓
