# M7 — Part 7 Streaming System, Deep Dive (L31–L33) — Plan

Subagent-driven; ONE implementer builds 3 lessons into a new `src/part7.py` (3 lessons fits a single
dispatch, but the streaming docs are heavy — so put KEY FACTS inline + cap research + write each lesson
as you go). Then spec + code reviews. Spec: `docs/superpowers/specs/2026-06-24-m7-part7-streaming-spec.md`.

## Tasks (one implementer, write incrementally)
- **L31 WAL architecture** — StreamingCoord (balancer/channel-mgmt/resource, inside RootCoord) assigns
  PChannels→StreamingNodes; StreamingNode WAL per PChannel: adaptor + interceptor chain (TimeTick/Txn/
  Shard/Lock), scanner (read), RecoveryStorage (checkpoint + recovery); WAL Backend (Kafka/Pulsar/
  Woodpecker/RMQ via walimpls), one topic per PChannel; TimeTick clock. Cite `internal/streamingnode/
  server/wal/` or `internal/streamingcoord/server/`.
- **L32 DDL/DCL via log** — Broadcaster (`internal/streamingcoord/server/broadcaster`): Broadcast →
  cross-PChannel atomic fan-out + resource locking + ACK; message semantics (collection/partition/
  database/alias/rbac/txn); transactions. Cite the broadcaster.
- **L33 Replication & CDC** — `internal/cdc` (controller/replication/cluster); star-topology cross-cluster
  WAL replication (Primary WAL → CDC ChannelReplicator → Secondary Proxy → Secondary WAL); role mgmt.
  Cite `internal/cdc/replication` or `controller`.

**MANDATORY:** implementer reads the streaming-system top-level doc + sub-docs (channel, message +
message-semantic-*, streaming-client, coordination/{broadcaster,channel_management}, wal/{timetick_and_txn,
lock,shard-management,recovery-storage}, walbackend, replication/replicate) before writing — BUT to avoid
the M4a budget-burn, the brief will inline the key facts and tell it to skim/confirm rather than read
everything end-to-end, and to write each lesson to the file as drafted.

Each lesson: content model; **zh ≥ 3700, aim ~3900**; bilingual parity; quiz (3 mcq + 1 open). Only
defined CSS classes. Verify every citation's exact file.

## Wiring
New `src/part7.py` (LESSON_31..33); `registry.py` `import part7` + 3 keys; `shell.PAGES` += 3 (Part 7
label "第七部分 · 流式系统" / "Part 7 · Streaming system"); `shell.SUBTITLES` += 3; `quizzes.QUIZZES` += 3.

## Verify / Commit
Gates 0/0; rebuild no-diff; index pill "共 33 课 · 7 个部分"; nav L01..L33. Commit
`M7: Part 7 streaming system — L31 WAL architecture, L32 DDL/DCL via log, L33 replication & CDC`.

## Review (after)
Two-stage (spec + quality, opus-4.8 max); fix loop; mark M7 done.

## Guardrails
WAL = single source of truth; TimeTick monotonic; one topic per PChannel; StreamingCoord singleton in
RootCoord; StreamingNode interceptor chain + RecoveryStorage; DDL/DCL via Broadcaster (atomic+lock+ACK);
CDC = star-topology WAL replication; file+symbol citations verified.

## Titles / files
"第七部分 · 流式系统" / "Part 7 · Streaming system". Files: 31-wal-architecture, 32-ddl-dcl-via-log,
33-replication-and-cdc.
