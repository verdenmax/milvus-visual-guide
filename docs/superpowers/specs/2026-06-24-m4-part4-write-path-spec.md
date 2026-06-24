# M4 — Part 4 The Write Path (L15–L20) — Spec

**Milestone:** M4 (Part 4 · 写入链路 / The write path). Six lessons tracing a write from the SDK to
durable storage, through the **streaming WAL**. New module `src/part4.py`. Part label:
"第四部分 · 写入链路" / "Part 4 · The write path".

Authoring standard: content model (lead → analogy → macro → ≥3 diagrams/lang → cited code
file+symbol → key card → quiz); **zh ≥ 3700 CJK, aim ~3900–4000**; strict zh/en parity; gates 0/0.
Verify all symbols in `/home/verden/course/milvus`.

## CRITICAL — current write path (per `docs/agent_guides/streaming-system/streaming-system.md`)
The WAL is the **single source of truth**. The DML path is:
**Client → Proxy → `StreamingClient.Append` → StreamingNode → WAL Backend.** TimeTick is the
PChannel-level monotonically-increasing log sequence number. **StreamingCoord** (singleton) runs
**inside the RootCoord process**; **StreamingNode** manages a subset of **PChannels** and owns
**TimeTick & Txn, Lock, Shard Management (segment assignment), RecoveryStorage (checkpoint + persist)**.
WAL Backend = Kafka / Pulsar / Woodpecker / RMQ, **one topic per PChannel**. Channels:
**PChannel** (physical) ← **VChannel** (logical per-shard) + **CChannel** (control, cluster-wide order).
The implementer MUST read the streaming sub-docs (message, wal/shard-management, wal/recovery-storage,
streaming-client, walbackend, wal/timetick_and_txn) AND the code, and reconcile the **StreamingNode-vs-
DataNode** division of labor precisely (StreamingNode produces/consumes the WAL + assigns segments;
DataNode handles flush/compaction of binlogs to object storage — VERIFY current boundaries).

## Lessons

### L15 — 经 Proxy 的插入 / Insert via Proxy (`15-insert-via-proxy.html`)
The proxy side of a write. Cover: schema validation; primary-key auto-fill + **hashing rows by PK to
VChannels/shards** (`assignChannelsByPK` / `checkPrimaryFieldData`); timestamp assignment;
`StreamingClient.Append` of insert messages; atomic batch visibility. The insert task lives in
`internal/proxy/task_insert*.go` (e.g. `task_insert_streaming.go`). Diagrams: a `vflow` (validate →
assign PK → hash to vchannels → append to WAL); a `flow`; a `table.t` (proxy step → purpose). Cite the
insert task + `assignChannelsByPK`.

### L16 — 流式系统与 WAL / Streaming & WAL (`16-streaming-and-wal.html`)
The WAL backbone (light intro; deep dive in Part 7/M7). Cover: WAL as single source of truth; the
**Message** model + **TimeTick**; PChannel/VChannel/CChannel; `StreamingClient.Append/Broadcast`;
StreamingNode/StreamingCoord roles; "log as data" → other data forms catch up by replaying. Diagrams:
a `layers`/`flow` (Proxy → StreamingClient → StreamingNode → WAL Backend); a `cellgroup`/`timeline`
(TimeTick-ordered log entries); a `table.t` (channel type → scope → purpose). Cite
`internal/streamingnode` or `internal/distributed/streaming` (StreamingClient API) — verify.
**Read:** `docs/agent_guides/streaming-system/{streaming-system.md,message/message.md,streaming-client/streaming-client.md,channel/channel.md}`.

### L17 — DataNode 与 flush / DataNode & flush (`17-datanode-and-flush.html`)
From WAL to durable segments. Cover: how WAL entries become a **growing segment** (in-memory,
consumed from the stream); the **flush** trigger (size/time) sealing it and writing **binlogs** to
object storage; the StreamingNode RecoveryStorage / Shard-Management role in segment assignment vs the
DataNode's flush/persistence role (VERIFY the current split). Diagrams: a `vflow`/`timeline` (consume →
grow → seal → flush → binlog); a `flow`; a `cols` (growing vs sealed, recap). Cite a flush/sync type
in `internal/flushcommon` or `internal/datanode`.
**Read:** `internal/datanode`, `internal/flushcommon`, `docs/agent_guides/streaming-system/wal/{recovery-storage.md,shard-management.md}`.

### L18 — Binlog 与存储格式 / Binlog & storage format (`18-binlog-and-storage.html`)
The on-disk format. Cover: **insert binlog / delete binlog / stats binlog** (+ index files);
the columnar layout; the object-storage path layout (collection/partition/segment/field); the
`internal/storage` serialization; storage v2 if relevant. Diagrams: a `layers`/`table.t` (binlog kind
→ content → path); a `cellgroup` (columnar field chunks); a `vflow` (rows → serialize → binlog object).
Cite `internal/storage` (the binlog serializer/`PayloadWriter` or event format) — verify.
**Read:** `internal/storage`, `docs/developer_guides/chap08_binlog.md` (note: cross-check vs code),
`internal/storagev2` if used.

### L19 — Compaction 与 GC / Compaction & GC (`19-compaction-and-gc.html`)
Housekeeping. Cover: **compaction** (merge small segments, apply deletes, clustering/sort compaction
types) scheduled by **DataCoord**, executed by a datanode worker; **garbage collection** (drop orphaned
binlogs/segments from object storage); why compaction matters for read efficiency. Diagrams: a `vflow`/
`timeline` (many small + deletes → compact → fewer clean segments); a `table.t` (compaction type →
trigger → effect); a `flow` (DataCoord schedules → datanode executes → GC). Cite a compaction
type/trigger in `internal/datacoord/compaction*` or `internal/compaction`.
**Read:** `internal/datacoord/compaction*.go`, `internal/compaction`, `internal/datacoord/garbage_collector.go`.

### L20 — 删除与 Upsert / Delete & upsert (`20-delete-and-upsert.html`)
Mutations + MVCC. Cover: deletes as **delete messages** in the WAL → **delete binlogs**; **bloom
filters** (per-segment PK membership to route a delete to the right segment); **upsert** = delete +
insert; **MVCC by timestamp** (a row version is visible iff its ts ≤ the read's guarantee ts — deletes
mask older versions); compaction applies deletes physically. Diagrams: a `vflow`/`timeline` (delete →
delete-log → masked at read → applied at compaction); a `cellgroup` (a row + tombstone by ts); a
`table.t` (op → mechanism). Cite the delete path / bloom-filter usage (`internal/querynodev2` or
`internal/storage`) — verify. Forward-ref consistency (L30).
**Read:** delete handling in `internal/datanode`/`internal/querynodev2`, bloom-filter usage, MVCC notes.

## Wiring
New `src/part4.py` (LESSON_15..20); `registry.py` `import part4` + 6 keys; `shell.PAGES` += 6 (Part 4
label); `shell.SUBTITLES` += 6; `quizzes.QUIZZES` += 6.

## Definition of Done
Gates 0/0; rebuild no-diff; index pill "共 20 课 · 4 个部分"; nav chain L01..L20; two-stage review
passed; committed.

## Accuracy guardrails
- DML write path is via **StreamingClient.Append → StreamingNode → WAL Backend** (NOT a bare
  "Proxy → MQ → DataNode" model). WAL = single source of truth; TimeTick ordering.
- StreamingCoord runs inside RootCoord; one WAL topic per PChannel.
- Compaction/index scheduled by **DataCoord**, run by a **datanode worker** (no indexnode).
- Proto types in `milvus-proto/go-api/v3/...pb`; verify the exact file for every cited symbol.
- Reconcile StreamingNode vs DataNode roles from the streaming sub-docs + code; don't guess.
