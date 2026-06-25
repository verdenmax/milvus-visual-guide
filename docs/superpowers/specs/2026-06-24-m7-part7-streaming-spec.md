# M7 — Part 7 Streaming System, Deep Dive (L31–L33) — Spec

**Milestone:** M7 (Part 7 · 流式系统 / Streaming system). Three lessons that go DEEP on the WAL
subsystem introduced lightly in L16. New module `src/part7.py`. Part label:
"第七部分 · 流式系统" / "Part 7 · Streaming system".

**MANDATORY READING (per repo procedure for a subsystem deep-dive):** the implementer MUST read the
streaming-system top-level doc AND its sub-documents before writing:
`docs/agent_guides/streaming-system/streaming-system.md` + `channel/channel.md`, `message/message.md`
(+ the `message/message-semantic-*.md` set), `streaming-client/streaming-client.md`,
`coordination/{broadcaster.md,channel_management.md}`, `wal/{timetick_and_txn.md,lock.md,
shard-management.md,recovery-storage.md}`, `walbackend/walbackend.md`, `replication/replicate.md`.
Then cross-check against code.

Authoring standard: content model (lead → analogy → macro → ≥3 diagrams/lang → cited code file+symbol
→ key card → quiz); **zh ≥ 3700 CJK, aim ~3900**; strict zh/en parity; gates 0/0 (incl. CSS-class
guard). Verify symbols in `/home/verden/course/milvus`.

## Lessons

### L31 — WAL 架构 / WAL architecture (`31-wal-architecture.html`)
The engine room. Cover: **StreamingCoord** (singleton inside RootCoord — `internal/streamingcoord/
server/{balancer,channel management,resource}`) assigns **PChannels → StreamingNodes**; **StreamingNode**
runs the WAL per PChannel (`internal/streamingnode/server/wal/`) — the **adaptor** + the **interceptor
chain** (**TimeTick**, **Txn**, **Shard/segment-assignment**, **Lock**), the **scanner** (read), and
**RecoveryStorage** (`wal/recovery`, checkpoint + WAL-based state recovery); the **WAL Backend**
abstraction (`walimpls`) over **Kafka / Pulsar / Woodpecker / RocksMQ**, one topic per PChannel;
**TimeTick** as the monotonic clock. Diagrams: a `layers` (StreamingCoord → StreamingNode → WAL
backend); a `vflow`/`flow` (Append → interceptors → backend → scanner/recovery); a `table.t`
(component → responsibility → package). Cite a real type in `internal/streamingnode/server/wal/` or
`internal/streamingcoord/server/`.

### L32 — 通过日志的 DDL/DCL / DDL/DCL through the log (`32-ddl-dcl-via-log.html`)
Why DDL is special. Cover: DML goes to one PChannel, but **DDL/DCL** (create/drop collection, partition,
database, alias, RBAC) must apply **atomically across many PChannels** — so it goes through the
**Broadcaster** (`internal/streamingcoord/server/broadcaster`): `StreamingClient.Broadcast` →
StreamingCoord Broadcaster → all relevant PChannels with **resource locking** + **ACK** tracking; the
**message semantics** (`message/message-semantic-{collection,partition,database,alias,rbac,txn}.md`) —
each event is a typed Message; **transactions** (`wal/timetick_and_txn.md`). Diagrams: a `flow`/`vflow`
(Broadcast → lock → fan-out to PChannels → ACK); a `table.t` (DML vs DDL/DCL path); a `cols` (single-
channel vs broadcast). Cite the broadcaster (`internal/streamingcoord/server/broadcaster`) — verify.

### L33 — 复制与 CDC / Replication & CDC (`33-replication-and-cdc.html`)
Cross-cluster. Cover: **star-topology cross-cluster WAL replication** (`internal/cdc` — `controller`,
`replication`, `cluster`): **Primary WAL → CDC ChannelReplicator → Secondary Proxy → Secondary WAL
(Replicate Interceptor) → WAL Backend** (`replication/replicate.md`); role management (primary/secondary);
how CDC reuses the WAL-as-source-of-truth design (you replicate the log, and the secondary replays it).
Diagrams: a `flow`/`vflow` (primary WAL → replicator → secondary); a `layers`/`cols` (primary vs
secondary roles); a `table.t` (component → role). Cite a type in `internal/cdc/replication` or
`internal/cdc/controller` — verify.

## Wiring
New `src/part7.py` (LESSON_31..33); `registry.py` `import part7` + 3 keys; `shell.PAGES` += 3 (Part 7
label); `shell.SUBTITLES` += 3; `quizzes.QUIZZES` += 3.

## Definition of Done
Gates 0/0; rebuild no-diff; index pill "共 33 课 · 7 个部分"; nav L01..L33; two-stage review passed;
committed.

## Accuracy guardrails
- WAL = single source of truth; TimeTick monotonic LSN; one WAL topic per PChannel.
- StreamingCoord is a singleton inside RootCoord; StreamingNode owns per-PChannel WAL (interceptor
  chain: TimeTick/Txn/Shard/Lock) + RecoveryStorage.
- DDL/DCL uses the **Broadcaster** (atomic cross-PChannel + locking + ACK); DML is single-PChannel Append.
- CDC = star-topology WAL replication via `internal/cdc`.
- file+symbol citations verified; proto types in `milvus-proto/go-api/v3/...pb`; only defined CSS classes.
