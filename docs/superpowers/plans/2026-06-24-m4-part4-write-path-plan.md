# M4 — Part 4 The Write Path (L15–L20) — Plan

Subagent-driven. **Split into TWO implementer dispatches** (6-lesson milestones overran one agent in
M3): **M4a = L15–L17**, **M4b = L18–L20**, sequential (M4b after M4a integrates). Then one combined
two-stage review over all of Part 4. Spec: `docs/superpowers/specs/2026-06-24-m4-part4-write-path-spec.md`.

## Dispatch M4a — L15–L17 (Proxy insert → WAL → flush)
- **L15 Insert via Proxy** — validate, PK auto-fill + hash to vchannels (`assignChannelsByPK`),
  timestamp, `StreamingClient.Append`; `internal/proxy/task_insert*.go`.
- **L16 Streaming & WAL (light)** — WAL = single source of truth; Message + TimeTick; PChannel/
  VChannel/CChannel; StreamingClient/StreamingNode/StreamingCoord; "log as data". Read the streaming
  agent-guide sub-docs (message, streaming-client, channel).
- **L17 DataNode & flush** — WAL → growing segment → flush → binlog; reconcile StreamingNode (shard
  mgmt / recovery storage) vs DataNode (flush/persist) — VERIFY current split. Read wal/recovery-storage,
  wal/shard-management.
Implementer creates `src/part4.py` with LESSON_15..17, wires registry/PAGES/SUBTITLES/quizzes for the 3,
builds to 0/0 + no-diff (index pill "共 17 课 · 4 个部分"), commits "M4a: …".

## Dispatch M4b — L18–L20 (storage → housekeeping → mutations)
- **L18 Binlog & storage format** — insert/delete/stats binlogs; columnar; object-storage path layout;
  `internal/storage` serializer.
- **L19 Compaction & GC** — compaction (merge/apply-deletes/clustering) scheduled by DataCoord, run by
  datanode worker; GC of orphaned objects. `internal/datacoord/compaction*`, `garbage_collector.go`.
- **L20 Delete & upsert** — delete messages → delete binlogs; bloom filters; upsert = delete+insert;
  MVCC by timestamp; deletes applied at compaction. Forward-ref L30.
Implementer appends LESSON_18..20 to `src/part4.py`, wires the 3, builds to 0/0 + no-diff (index pill
"共 20 课 · 4 个部分"), commits "M4b: …".

## Per-lesson standard
Content model (lead→analogy→macro→≥3 diagrams/lang→cited code file+symbol→key card); **zh ≥ 3700,
aim ~3900**; bilingual parity; quiz (2–4 mcq + 1–2 open). Verify EVERY citation's exact file in
`/home/verden/course/milvus` (proto types in `milvus-proto/go-api/v3/...pb`).

## Review (after M4b)
Two-stage (spec + quality, opus-4.8 max) over L15–L20 together; fix loop; mark M4 done.

## Guardrails
DML path = StreamingClient.Append → StreamingNode → WAL Backend (not bare Proxy→MQ→DataNode); WAL =
single source of truth; StreamingCoord inside RootCoord; one WAL topic per PChannel; compaction/index
by DataCoord + datanode worker (no indexnode); reconcile StreamingNode vs DataNode from the streaming
sub-docs + code.

## Part label / titles
"第四部分 · 写入链路" / "Part 4 · The write path". Files: 15-insert-via-proxy, 16-streaming-and-wal,
17-datanode-and-flush, 18-binlog-and-storage, 19-compaction-and-gc, 20-delete-and-upsert.
