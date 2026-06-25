# Part 12 — Design Themes (synthesis) · Design Spec

Date: 2026-06-25
Status: approved (user approved the 6-chapter set on 2026-06-25)

## Motivation

The existing 50 lessons explain Milvus **module by module** (proxy, datacoord,
segcore, …). This new part adds **cross-cutting synthesis chapters**: each one
takes a single **design goal / "why is it built this way" question** and shows
**what every module contributes toward that goal, and why the goal matters**.
These are capstone "aha" chapters that tie the per-module lessons together into
the handful of big ideas that define Milvus's architecture.

This directly answers a learner's most valuable question — not "what does
component X do" (the first 50 lessons) but "**why is the whole system shaped
this way**".

## Per-chapter structure (fixed)

Every chapter follows the same three-beat arc, stated explicitly so the chapters
read consistently:

1. **The goal & why it matters** — name the design goal in one line; explain why
   Milvus *must* achieve it (what breaks without it). Open with the analogy card.
2. **What each module does toward it** — walk the modules already taught and show
   the concrete effort each makes in service of this one goal (this is the
   cross-cutting "synthesis" body; heavy use of flow / layers / trace diagrams
   that connect modules). Cite the lessons being synthesized ("第 N 课").
3. **The payoff & the tradeoffs** — what the design buys, what it costs, and the
   alternative Milvus deliberately rejected. Close with the macro + key cards.

## The 6 chapters

| # | File | zh title | en title | Modules synthesized |
|---|---|---|---|---|
| L51 | `51-design-log-as-data.html` | 日志即数据：为什么整个系统都围着 WAL 转 | Log as data: why the whole system orbits the WAL | proxy append (L15), streaming/WAL (L16/L31), datanode flush (L17), querynode consume-tail (L26), DDL-in-log (L32), replication replay (L33), checkpoint+replay recovery |
| L52 | `52-design-query-while-write.html` | 边写边查还保证正确：一致性是怎么炼成的 | Query-while-you-write, correctly: how consistency is forged | TSO (L11), guarantee ts (L25), growing/sealed (L07), tsafe wait (L26/L30), MVCC (L30), tombstones (L20) |
| L53 | `53-design-storage-compute-separation.html` | 存算分离：为什么节点可以是"无状态"的 | Storage–compute separation: why nodes can be stateless | object storage (L08/L18), build side (L21/L23), load side via mmap (L23/L35), metadata in etcd (L14), elastic scaling (L13), failover |
| L54 | `54-design-scale-to-billions.html` | 扩展到十亿级：分而治之的艺术 | Scaling to billions: the art of divide-and-conquer | segmentation (L07/L12), scatter-gather (L03/L25), three-level reduce (L29), scalar pushdown (L28), per-segment index (L21/L23) |
| L55 | `55-design-two-languages.html` | 两种语言，一套系统：C++ 内核与 Go 编排的分工 | Two languages, one system: the C++ kernel / Go orchestration split | segcore + Knowhere hot path (L22/L27/L34), cgo bridge (L34), Go coordinators/nodes (L09–L13), tantivy/Rust (L24) |
| L56 | `56-design-failure-as-default.html` | 故障是常态：系统如何自愈 | Failure as the default: how the system heals itself | checkpoint+replay (L31), reconciliation/inspector/balancer (L13/L21), session+lease (L14), Broadcaster atomic DDL (L32), rolling upgrade / index versioning (L23), stateless workers (L53) |

Part label: **第十二部分 · 设计专题（综合）** / **Part 12 · Design themes (synthesis)**.
Placed after Part 11 (advanced topics); does not renumber existing lessons.

## Format requirements (identical to existing lessons)

- Bilingual `LESSON_NN = {"zh": …, "en": …}` HTML fragments in a new `src/part12.py`.
- zh ≥ 3000 CJK (aim ~3500); en a faithful, balanced counterpart.
- ≥ 3 true diagrams **per language**, identical zh/en diagram inventory; use only
  the defined CSS vocabulary (layers/vflow/flow/cols/cellgroup/timeline/trace +
  `<table class="t">`). These chapters lean on **flow / layers / trace** to draw
  the cross-module connections.
- Required cards in both languages: `card analogy`, `card macro`, `card key`
  ("本课要点" / "Key points").
- Exactly the shell-added single `<h1>`; no `<h1>` in body. Escape `<`/`&`.
- Cross-refs "第 N 课" / "Lesson N" with N ≤ 56.
- Per-lesson quiz in `quizzes.py`: exactly 3 MCQ (4 opts, correct option first,
  answer:0, bilingual q/opts/why) + 1 open question (bilingual).

## Wiring / tooling changes

- New `src/part12.py` (6 lesson dicts).
- `src/registry.py`: import part12; map the 6 filenames → dicts in order.
- `src/shell.py`: add 6 `PAGES` tuples (filename, zh-title, en-title, zh-part
  label, en-part label) using PLAIN `&`/`<` (esc'd at render); add 6 `SUBTITLES`.
- `src/quizzes.py`: add 6 quiz entries.
- `src/check_html.py`: bump `MAX_LESSON` 50 → 56.
- README + index pill update to 12 parts / 56 lessons.

## Acceptance criteria

- `build.py` + `build_print.py` succeed; `check_html.py` 0 error / 0 warning;
  `check_links.py` all internal links resolve; idempotent rebuild (no diff).
- Each new chapter: 3 cards both langs, ≥3 diagrams both langs with matching
  inventory, zh ≥ 3000 CJK, valid quiz (3 MCQ + 1 open).
- Generated output committed in sync with sources (CI's in-sync gate passes).
- Factual claims about Milvus cross-checked against the source at
  `/home/verden/course/milvus` before writing.

## Non-goals

- No new diagram CSS classes (reuse the existing vocabulary).
- No renumbering of L01–L50; Part 12 is appended.
- Not a re-explanation of each module from scratch — these chapters **synthesize
  and cross-reference** the existing lessons, they do not duplicate them.
