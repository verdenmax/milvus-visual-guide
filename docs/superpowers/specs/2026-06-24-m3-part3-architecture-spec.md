# M3 — Part 3 Distributed Architecture (L09–L14) — Spec

**Milestone:** M3 (Part 3 · 分布式架构 / Distributed architecture). Six lessons that open the
control plane: how the coordinators and nodes divide work, and what each coordinator owns. New
module `src/part3.py`. Part label: "第三部分 · 分布式架构" / "Part 3 · Distributed architecture".

Authoring standard (every lesson): content model (lead → analogy → **macro** → ≥3 diagrams/lang →
cited code file+symbol → key-points card → quiz); **zh ≥ 3500 CJK, aim ~4000**; strict zh/en parity;
gates 0/0. Cite real symbols verified in `/home/verden/course/milvus`.

## Lessons

### L09 — 控制面 vs 数据面 / Control plane vs data plane (`09-control-vs-data-plane.html`)
The organizing principle. Cover: the split between **coordinators** (control plane: metadata,
scheduling, assignment — they decide *who does what*) and **nodes** (data plane: execute writes/reads
— they *do the work*); the **component interfaces** in `internal/types/types.go` (`Component` base +
`RootCoord`, `DataCoord`, `QueryCoord`, `Proxy`, `QueryNode`, `DataNode`, and `MixCoord` which embeds
the three coordinator servers); the **MixCoord** physical packaging (one process today) vs the logical
three roles; how `internal/distributed/` wraps each as a gRPC server; service discovery + sessions via
etcd. Diagrams: a `layers` (control plane over data plane); a `table.t` (interface → role → plane →
package); a `cols` (coordinator vs node responsibilities) or a `flow`. Cite `internal/types/types.go`
(`MixCoord interface`).

### L10 — Proxy 网关 / The Proxy gateway (`10-proxy.html`)
The single entry point. Cover: the **gRPC/REST API surface** (milvuspb MilvusService); request
**validation + auth + rate limiting**; the **task scheduler** with three queues —
**`ddQueue`** (DDL: create/drop collection/partition/index), **`dmQueue`** (DML: insert/delete/upsert),
**`dqQueue`** (DQL: search/query) (`internal/proxy/task_scheduler.go`); timestamp/ID assignment from
the coordinator; how the proxy is **stateless** and scales horizontally; cross-shard **reduce** for
search results (deep in L29). Diagrams: a `vflow` (request → validate → enqueue → execute → reduce);
a `table.t` (queue → request kinds → ordering); a `flow` (client → proxy → coord/nodes); optionally a
`cols` (DML vs DQL path). Cite `internal/proxy/task_scheduler.go` (`taskScheduler`, the three queues).
**Read:** `internal/proxy/{task_scheduler.go,impl.go,task.go}`, `internal/distributed/proxy`.

### L11 — RootCoord (`11-rootcoord.html`)
The DDL + identity brain. Cover: **DDL** (create/drop/alter collection, partition, alias, database)
and the **meta table** (`internal/rootcoord` `IMetaTable`); the **TSO (timestamp oracle)** — a global
monotonic clock (`tso2.NewGlobalTSOAllocator` in `internal/rootcoord/root_coord.go`); **global ID
allocation**; how DDL flows through the streaming/DDL channel (light; deep in M7). Note RootCoord runs
inside MixCoord. Diagrams: a `vflow` (a create-collection DDL); a `table.t` (responsibility → mechanism);
a `cellgroup`/`timeline` (TSO monotonic timestamps) or `flow`. Cite `internal/rootcoord/root_coord.go`
(TSO allocator) and the meta-table type.
**Read:** `internal/rootcoord/{root_coord.go,meta_table.go}`, `internal/tso`.

### L12 — DataCoord (`12-datacoord.html`)
The write-side + storage brain. Cover: **segment allocation** (assign rows to growing segments) and
segment **lifecycle/state machine** (`SegmentState_*`); **flush** orchestration; **compaction**
scheduling (merge small/deleted segments — deep in L19); **garbage collection**; **channel assignment**
(which datanode/streamingnode handles which vchannel); and **index build scheduling** (DataCoord
schedules index tasks; run by a datanode worker — there is NO separate indexnode). Diagrams: a `vflow`/
`timeline` (segment alloc → seal → flush → compact → GC); a `table.t` (duty → trigger → effect); a
`flow` (datacoord ↔ datanode). Cite a datacoord segment/meta type or the compaction/GC trigger.
**Read:** `internal/datacoord/{services.go,segment_manager.go,compaction*.go,garbage_collector.go,index_*}`.

### L13 — QueryCoordV2 (`13-querycoord.html`)
The read-side brain. Cover: collection **load / release** (bring segments+indexes into QueryNodes);
**segment & channel (delegator/shard) assignment**; the **balancer** (spread segments across nodes,
rebalance on join/leave/skew); **replicas** (multiple in-memory copies for HA + throughput); the
**distribution / target** view (current vs desired). Diagrams: a `vflow` (load collection → assign →
balance); a `cols` (segment vs channel assignment, or replica HA); a `table.t` (concept → role);
`flow`. Cite a querycoordv2 type (e.g. the balancer or dist manager).
**Read:** `internal/querycoordv2/{services.go,balance/,dist/,meta/,observers/}`.

### L14 — 元数据与协调 / Metadata & coordination (`14-metadata-and-coordination.html`)
The glue. Cover: **etcd** as the metadata store + **service discovery / sessions** (components register,
watch each other); the **metastore / catalog** abstraction (`internal/metastore` — how coordinators
persist collection/segment/index meta, with etcd + object-storage backends); **kv** layer
(`internal/kv`); the **watch** mechanism (coordinators push channel/segment assignments, nodes watch);
snapshot/MVCC of meta. Diagrams: a `layers` (coordinators → metastore/catalog → kv → etcd/object store);
a `table.t` (what's stored where: etcd vs object storage); a `flow`/`vflow` (register → watch → assign).
Cite `internal/metastore` (the `Catalog` interface) and `internal/kv`.
**Read:** `internal/metastore/{catalog.go,kv/}`, `internal/kv`, `internal/util/sessionutil`.

## Wiring
New `src/part3.py` (LESSON_09..14); `registry.py` `import part3` + 6 keys; `shell.PAGES` += 6 (Part 3
label); `shell.SUBTITLES` += 6; `quizzes.QUIZZES` += 6.

## Definition of Done
Gates 0/0; rebuild no-diff; index pill "共 14 课 · 3 个部分"; nav chain L01..L14; two-stage review
passed; committed.

## Accuracy guardrails
- Coordinators = one **MixCoord** process today; the three are logical roles (`internal/coordinator/mix_coord.go`).
- **No indexnode** — DataCoord schedules index build, a datanode worker runs it.
- Proxy queues are exactly **ddQueue/dmQueue/dqQueue**.
- TSO lives in RootCoord; segment states from `SegmentState_*`.
- file+symbol citations; verify every symbol exists; small snippets only.
