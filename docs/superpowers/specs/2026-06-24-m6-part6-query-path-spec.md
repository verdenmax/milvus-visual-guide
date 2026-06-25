# M6 — Part 6 The Query Path (L25–L30) — Spec

**Milestone:** M6 (Part 6 · 查询链路 / The query path). Six lessons tracing a search from the SDK to
results — the read-path counterpart to Part 4, descending into the C++ **segcore**. New module
`src/part6.py`. Part label: "第六部分 · 查询链路" / "Part 6 · The query path".
**Dispatch as TWO halves** (like M4): **M6a = L25–L27**, **M6b = L28–L30**.

Authoring standard: content model (lead → analogy → macro → ≥3 diagrams/lang → cited code
file+symbol → key card → quiz); **zh ≥ 3700 CJK, aim ~3900**; strict zh/en parity; gates 0/0 (incl.
undefined-CSS-class guard). Verify every symbol in `/home/verden/course/milvus`.

## Lessons

### L25 — 经 Proxy 的搜索 / Search via Proxy (`25-search-via-proxy.html`)
The proxy side of a read. Cover: the **search task** (`internal/proxy/task_search.go`); parse the
request; derive a **guarantee timestamp** from the **consistency level** (`parseGuaranteeTsFromConsistency`
in `internal/proxy/util.go` — reuse from L03); build a **search plan** (vector field + metric + topK +
scalar filter expr); **scatter** to the shards (delegators); then **reduce** results across shards
(deep L29). Diagrams: a `vflow` (parse → plan → guarantee-ts → scatter → reduce); a `flow`; a `table.t`
(consistency level → guarantee ts). Cite `task_search.go` / `parseGuaranteeTsFromConsistency`.

### L26 — QueryNodeV2 与 delegator / QueryNodeV2 & the delegator (`26-querynode-and-delegator.html`)
The shard read coordinator. Cover: the **delegator / shard leader** (`internal/querynodev2/delegator/
delegator.go`, `delegator_data.go`) that owns a vchannel's read; **loading sealed + growing segments**
(sealed from index via QueryCoord load, growing from the streaming tail); **segment distribution** across
QueryNodes (workers); the delegator **scatters** the search to local + worker segments and merges; how
growing data stays fresh (consumes the WAL tail). Diagrams: a `flow`/`vflow` (delegator → sealed+growing
→ workers → merge); a `cols` (sealed vs growing); a `table.t` (role → who). Cite `delegator.go` (the
delegator interface / `Search`).
**Read:** `internal/querynodev2/delegator/`, `internal/querynodev2/segments/`.

### L27 — Segcore（C++）/ Segcore (C++) (`27-segcore.html`)
Inside one segment. Cover: **segcore** is the C++ engine that runs a search within a single segment,
reached over the **cgo** boundary (`internal/core/src/segcore/segment_c.h` C API → `LocalSegment` in Go,
recall L02); the **`SegmentInterface`** (`SegmentInterface.h:81`) + `SegmentSealed` vs `SegmentGrowing`
impls; **sealed** segments search via the loaded **index** (Knowhere), **growing** via **brute force**;
columnar/chunked data + mmap (deep in Part 8). Diagrams: a `layers`/`flow` (Go → cgo → segcore →
SegmentSealed/Growing); a `cols` (sealed/index vs growing/brute-force); a `vflow`/`trace` (a search inside
a segment). Cite `SegmentInterface.h` (`SegmentInterface`) or `segment_c.h` (the C API).
**Read:** `internal/core/src/segcore/{SegmentInterface.h,segment_c.h,SegmentSealedImpl.h}`.

### L28 — 执行引擎：plan / expr / exec / Execution engine (`28-execution-engine.html`)
How a query plan runs. Cover: the **search/retrieve plan** (`internal/core/src/plan` /
`query/Plan*`); the **expression tree** for scalar filtering (`internal/core/src/expr` —
predicates compiled from the boolean filter); the **vectorized execution** engine
(`internal/core/src/exec` — physical operators: filter then vector search); how filtering narrows the
candidate set before/with ANN (hybrid). Diagrams: a `vflow`/`flow` (plan → expr filter → vector search →
results); a `layers` (plan/expr/exec); a `table.t` (stage → component → output). Cite a real type in
`internal/core/src/exec` or `expr` (grep-verify).
**Read:** `internal/core/src/{plan,query,expr,exec}`.

### L29 — Reduce 与结果归并 / Reduce & result assembly (`29-reduce.html`)
Merging topK across the fan-out. Cover the **three reduce levels**: per-segment topK (**segcore**
`internal/core/src/segcore/reduce/Reduce.cpp`), per-node merge across a node's segments (**delegator**),
and **cross-shard reduce on the Proxy** (`docs/developer_guides/proxy-reduce.md`); dedup by PK, sort by
distance, apply offset/limit; why distributed topK needs hierarchical merging. Diagrams: a `vflow`/
`trace` (segment topK → node merge → proxy merge → final); a `flow`; a `table.t` (level → where → what).
Cite `segcore/reduce/Reduce.cpp` (the reduce) and reference `proxy-reduce.md`.
**Read:** `internal/core/src/segcore/reduce/`, `internal/querynodev2/delegator/`, `docs/developer_guides/proxy-reduce.md`.

### L30 — 一致性与时间戳 / Consistency & timestamps (`30-consistency-and-timestamps.html`)
The payoff lesson (forward-ref'd since L03/L20). Cover: the **TSO** global clock (recall L11); the
**guarantee timestamp** a read carries; the **consistency levels** (`commonpb.ConsistencyLevel_*`:
**Strong, Bounded, Session, Eventually, Customized**) and what guarantee-ts each maps to; **MVCC** —
a read at ts T sees writes with ts ≤ T (and not deleted by ts ≤ T); how a QueryNode **waits** until its
served data (the consumed WAL tail / TimeTick) ≥ guarantee-ts before answering (`how-guarantee-ts-works`).
Diagrams: a `timeline` (writes ts vs read guarantee-ts vs served-ts); a `table.t` (level → guarantee ts →
tradeoff); a `vflow` (request → guarantee-ts → wait-until-served → read). Cite `parseGuaranteeTsFromConsistency`
+ the consistency enum.
**Read:** `docs/developer_guides/how-guarantee-ts-works.md`, `internal/proxy/util.go`, `internal/querynodev2` (wait-for-tsafe).

## Wiring
New `src/part6.py` (LESSON_25..30); `registry.py` `import part6` + 6 keys; `shell.PAGES` += 6 (Part 6
label); `shell.SUBTITLES` += 6; `quizzes.QUIZZES` += 6.

## Definition of Done
Gates 0/0; rebuild no-diff; index pill "共 30 课 · 6 个部分"; nav L01..L30; two-stage review (over
L25–L30) passed; committed.

## Accuracy guardrails
- Segcore is **C++**, reached via **cgo** (`segment_c.h`); don't depict it as Go.
- **Sealed = index search, Growing = brute force.** Three reduce levels (segment / node / proxy).
- Consistency levels exactly `ConsistencyLevel_{Strong,Bounded,Session,Eventually,Customized}`.
- Guarantee-ts + MVCC: a read waits until served data ≥ guarantee-ts.
- file+symbol citations verified; proto types in `milvus-proto/go-api/v3/...pb`; only defined CSS classes.
