# M3 — Part 3 Distributed Architecture (L09–L14) — Plan

Subagent-driven; one implementer builds all 6 lessons into a new `src/part3.py`, then spec + code
reviews. Spec: `docs/superpowers/specs/2026-06-24-m3-part3-architecture-spec.md`.

## Tasks (one implementer, sequential)
- **L09 Control vs data plane** — coordinators (decide) vs nodes (execute); `internal/types/types.go`
  interfaces (Component + RootCoord/DataCoord/QueryCoord/Proxy/QueryNode/DataNode + MixCoord);
  MixCoord packaging; `internal/distributed/` gRPC wrappers; etcd discovery.
- **L10 Proxy** — gRPC/REST API (milvuspb); validate/auth/rate-limit; task scheduler with
  **ddQueue/dmQueue/dqQueue** (`internal/proxy/task_scheduler.go`); stateless + horizontal scale;
  cross-shard reduce (deep L29).
- **L11 RootCoord** — DDL + meta table (`IMetaTable`); **TSO** (`tso2.NewGlobalTSOAllocator` in
  `internal/rootcoord/root_coord.go`); global ID alloc; DDL via streaming (light, deep M7).
- **L12 DataCoord** — segment allocation + lifecycle (`SegmentState_*`); flush; compaction (deep L19);
  GC; channel assignment; index build scheduling (no indexnode).
- **L13 QueryCoordV2** — load/release; segment & channel (delegator) assignment; balancer; replicas;
  distribution/target view.
- **L14 Metadata & coordination** — etcd meta + service discovery/sessions; metastore/catalog
  (`internal/metastore`); kv (`internal/kv`); watch mechanism; what's stored where (etcd vs object store).

Each lesson: content model (lead→analogy→macro→≥3 diagrams/lang→cited code→key card), **zh ≥ 3700
CJK (aim ~4000 — do NOT sit at the 3500 floor)**, bilingual parity, quiz (2–4 mcq + 1–2 open). Verify
every cited symbol in `/home/verden/course/milvus`.

## Wiring
New `src/part3.py` (LESSON_09..14); `registry.py` `import part3` + 6 keys; `shell.PAGES` += 6 (Part 3
label "第三部分 · 分布式架构" / "Part 3 · Distributed architecture"); `shell.SUBTITLES` += 6;
`quizzes.QUIZZES` += 6.

## Verify
`cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py`
→ 0/0; rebuild no-diff; index pill "共 14 课 · 3 个部分"; nav chain L01..L14 correct.

## Commit
`M3: Part 3 distributed architecture — L09 planes, L10 proxy, L11 rootcoord, L12 datacoord, L13 querycoord, L14 metadata`
(sign-off + Co-authored-by Copilot).

## Guardrails
MixCoord is the unified coordinator; no indexnode; proxy queues ddQueue/dmQueue/dqQueue; TSO in
RootCoord; SegmentState names from code; file+symbol citations verified; small snippets.
