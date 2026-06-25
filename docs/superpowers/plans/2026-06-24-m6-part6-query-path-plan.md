# M6 — Part 6 The Query Path (L25–L30) — Plan

Subagent-driven. **Split into TWO dispatches** (6 lessons; heavy C++ segcore reading): **M6a = L25–L27**,
**M6b = L28–L30**, sequential. Then one combined two-stage review over all of Part 6. Spec:
`docs/superpowers/specs/2026-06-24-m6-part6-query-path-spec.md`.

## Dispatch M6a — L25–L27 (Proxy search → delegator → segcore)
- **L25 Search via Proxy** — `internal/proxy/task_search.go`; parse; derive guarantee-ts from
  consistency level (`parseGuaranteeTsFromConsistency`, `internal/proxy/util.go`); build search plan;
  scatter to shards; reduce (deep L29).
- **L26 QueryNodeV2 & delegator** — `internal/querynodev2/delegator/delegator.go`/`delegator_data.go`;
  shard leader; load sealed (index) + growing (WAL tail) segments; segment distribution; scatter+merge.
- **L27 Segcore (C++)** — cgo boundary (`internal/core/src/segcore/segment_c.h` → `LocalSegment`);
  `SegmentInterface` (`SegmentInterface.h:81`), SegmentSealed vs SegmentGrowing; sealed=index search,
  growing=brute force; columnar/mmap (deep Part 8).
Implementer creates `src/part6.py` with LESSON_25..27, wires 3, builds 0/0+no-diff
(index pill "共 27 课 · 6 个部分"), commits "M6a: …".

## Dispatch M6b — L28–L30 (exec → reduce → consistency)
- **L28 Execution engine** — plan/expr/exec (`internal/core/src/{plan,query,expr,exec}`); expression
  tree for scalar filter; vectorized exec; filter + vector search (hybrid).
- **L29 Reduce** — three levels: per-segment (`internal/core/src/segcore/reduce/Reduce.cpp`), per-node
  (delegator), cross-shard (Proxy, `docs/developer_guides/proxy-reduce.md`); dedup by PK, sort, offset/limit.
- **L30 Consistency & timestamps** — TSO; guarantee-ts; consistency levels
  (`commonpb.ConsistencyLevel_{Strong,Bounded,Session,Eventually,Customized}`); MVCC; QueryNode waits
  until served-ts ≥ guarantee-ts (`docs/developer_guides/how-guarantee-ts-works.md`).
Implementer appends LESSON_28..30 to `src/part6.py`, wires 3, builds 0/0+no-diff (index pill
"共 30 课 · 6 个部分"), commits "M6b: …".

## Per-lesson standard
Content model; **zh ≥ 3700, aim ~3900**; bilingual parity; quiz (2–4 mcq + 1–2 open). Facts INLINE in
the brief; grep only to confirm symbols; write each lesson to the file as you go. Only defined CSS classes.

## Review (after M6b)
Two-stage (spec + quality, opus-4.8 max) over L25–L30; fix loop; mark M6 done.

## Guardrails
Segcore is C++ via cgo (`segment_c.h`); sealed=index / growing=brute force; three reduce levels;
consistency levels exactly the 5 enum names; guarantee-ts wait + MVCC; verify every citation's exact
file; proto types in milvus-proto/go-api/v3.

## Part label / titles / files
"第六部分 · 查询链路" / "Part 6 · The query path". Files: 25-search-via-proxy,
26-querynode-and-delegator, 27-segcore, 28-execution-engine, 29-reduce, 30-consistency-and-timestamps.
