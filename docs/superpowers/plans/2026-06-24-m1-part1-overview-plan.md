# M1 — Part 1 Overview (L02–L03) — Plan

Executed via subagent-driven development: one implementer builds both lessons, then spec + code
reviews. Spec: `docs/superpowers/specs/2026-06-24-m1-part1-overview-spec.md`.

## Task 1 — L02 项目全景地图 / The project map
1. Read the Milvus source to get the component model right (esp. the MixCoord merge):
   `cmd/components/`, `cmd/roles/roles.go`, `internal/distributed/`,
   `internal/coordinator/mix_coord.go`, `internal/types/types.go`, top-level `internal/`, `pkg/`,
   `client/`.
2. Author `part1.LESSON_02` (zh+en) per the content model: lead, analogy card, macro card,
   ≥3 diagrams/lang (a `layers` of the 4 groups + core + SDK; a `table.t` component→language→
   responsibility→package; a `cols` Standalone-vs-Cluster or repo-layout `vflow`), a cited-code
   `.codefile` (file+symbol), key-points card.
3. Add the `quizzes.QUIZZES["02-project-map.html"]` entry (2–4 MCQs + 1–2 open).
4. Wire: `shell.PAGES` += L02; `shell.SUBTITLES` += L02; `registry.CONTENT` += L02.

## Task 2 — L03 一次请求的一生 / Life of a request
1. Read: `internal/proxy` (task scheduler + insert/search task entries), `internal/datanode`,
   `internal/streamingnode`, `internal/querynodev2` (delegator), `internal/core/src/segcore`,
   `internal/tso`; `docs/developer_guides/chap01_system_overview.md`, `docs/.../proxy-reduce.md`.
2. Author `part1.LESSON_03` (zh+en): trace insert + search end-to-end at 10,000 ft. Diagrams:
   a `vflow`/`trace` of insert, a `vflow`/`flow` of search, a `timeline`/`cols` write-vs-read; cited
   code from `internal/proxy`. key-points card. Forward-reference deep lessons (write path M4, query
   path M6, consistency L30).
3. Add `quizzes.QUIZZES["03-life-of-a-request.html"]`.
4. Wire: `shell.PAGES` += L03; `shell.SUBTITLES` += L03; `registry.CONTENT` += L03.

## Verify (both tasks)
`cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py`
→ 0 errors, 0 warnings; rebuild produces no diff; index pill reads "共 3 课 · 1 个部分"; nav chain
L01↔L02↔L03 correct.

## Commit
One commit for the milestone: `M1: Part 1 overview — L02 project map + L03 life of a request`
(sign-off + Co-authored-by Copilot trailer).

## Guardrails
- MixCoord is the unified coordinator today (don't show 3 separate coordinator processes as default).
- No separate indexnode. Cite file+symbol, not line numbers. Small snippets only.
- zh ≥ 3000 CJK (target ~4000); zh/en strict parity (same diagram inventory).
