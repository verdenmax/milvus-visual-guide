# Guide Enhancements: Searchable Glossary, Cover Images, Capstone Lesson — Design Spec

**Date:** 2026-06-26
**Status:** Approved (scope confirmed by user)

## Goal

Three polish additions on top of the now-complete 56-lesson guide:

1. **Searchable, cross-linked glossary** — turn L46 into a real "term quick-lookup" hub.
2. **Six shareable cover images** — branded 1200×630 cards of the guide's most iconic figures.
3. **Capstone lesson L57** — an end-to-end "life of a row, from write to searchable" synthesis.

All three keep the existing architecture: zero runtime dependencies, Python-generated
static HTML, bilingual via `.lang-zh`/`.lang-en` CSS toggle, themed palette vars, and
the `build.py` + `build_print.py` + `check_html.py` + `check_links.py` gate chain.

## Why

The guide teaches Milvus thoroughly but three seams remain:
- The glossary (L46) aggregates ~80 terms across courses, yet has **no search** and its
  "第 N 课 / Lesson N" references are **plain text**, not navigable.
- The figures are locked inside lesson pages; there is **nothing shareable** that
  captures the essence of the project at a glance (for README, social, slides).
- Every path is taught **separately** (write / index / query). A learner lacks one
  page that follows a *single row* across all of them — the payoff that ties the
  course together.

## Scope

### Feature 1 — Searchable cross-linked glossary (enhance L46 only)

- Add a **live filter** search box at the top of the glossary content (own `<input>` +
  inline `<script>` embedded in the L46 content HTML, both languages). The filter
  hides non-matching `<tr>` rows across every `table.t`, matching the row's combined
  zh+en text, and shows an empty-state line when nothing matches. Also hide a table's
  heading row / section when all its body rows are filtered out.
- **Linkify lesson references:** a build-time transform rewrites each glossary lesson
  cell ("第 N 课" / "Lesson N", and ranges like "第 9–14 课") into an `<a>` to the
  corresponding lesson file, using the `shell.PAGES` index (lesson N → `PAGES[N-1][0]`).
  Multiple numbers in one cell each become links. Non-lesson cells (e.g. "—") untouched.
- Zero new page, zero new dependency. The existing index.html title-search is unchanged.

**Out of scope:** a global full-text search across all lesson bodies (would need a
client-side index build; not warranted). Glossary search is row/term-level only.

### Feature 2 — Six shareable cover images (new `src/build_covers.py` → `assets/covers/`)

- A standalone generator composes **6 branded cover cards** at **1200×630** (standard
  social/OG ratio). Each card = a dark branded frame (project title + lesson label +
  `verdenmax.github.io/milvus-visual-guide` URL band) wrapping one key figure, drawn
  by **re-using the existing figure SVG markup** (scaled/positioned into the card), so
  covers stay faithful to the lessons and inherit the same palette (emitted with the
  **light-mode** palette values inlined, since share cards render on their own).
- Output per cover: **`<slug>.svg`** (source of truth) and **`<slug>.png`** (rendered
  via headless chromium at 2× for crisp social previews). Both committed.
- A small **gallery page** `assets/covers.html` (bilingual, same shell look) shows the
  6 covers with download links; **README** gets a "Cover gallery" link.
- The 6 figures (the essence of Milvus):
  1. `03` 一次请求的一生 / Life of a request
  2. `09` 控制面 vs 数据面 / Control plane vs data plane
  3. `51` 日志即数据 / Log as data (the WAL hub)
  4. `12` 段生命周期状态机 / Segment lifecycle state machine
  5. `26` 两层扇出查询 / Two-layer fan-out query
  6. `53` 存算分离 / Storage–compute separation
- **PNG rendering is local-only and committed**, NOT part of `build.py` (GitHub Actions
  has no chromium). `build_covers.py` is a manual/idempotent tool; CI just serves the
  committed assets. SVGs are the versioned source; PNGs are regenerable artifacts.

**Out of scope:** wiring per-lesson OG `og:image` meta to the covers (nice-to-have;
the gallery + README link is the committed deliverable). Animated/interactive covers.

### Feature 3 — Capstone lesson L57 (new Part 13 · 终章 / Capstone)

- New **`src/part13.py`** holding `LESSON_57 = {"zh": ..., "en": ...}`, a full lesson
  matching the others' depth (≥3000 zh CJK, multiple sections, source citations,
  folded deep-dives, cross-links, optional self-test).
- Title: **"一条数据的一生：从写入到被搜到" / "Life of a row: from write to searchable"**.
- It traces ONE inserted row through the whole system, in order:
  `SDK insert → Proxy (validate / assign ts) → WAL·MQ (ordered, durable) →
   StreamingNode/DataNode growing segment → seal → flush → binlog in object store →
   index build → QueryNode load (sealed + growing) → delegator → segcore →
   reduce → visible once tsafe ≥ the row's ts`.
- Anchored by a **large end-to-end timeline SVG** (the row's journey with the
  durability and visibility boundaries marked) plus 2–4 zoom-in SVGs, all bilingual
  and obeying every SVG convention (themed only via inline `style` var(); no
  `<marker>`/`<defs>`/gradients/`id`; classes limited to fig/figcap/mono; viewBox
  clip-safe; zh/en parity). Each stage cross-links to its detailed lesson.
- Wiring:
  - `registry.py`: `import part13`; add `"57-capstone-life-of-a-row.html": part13.LESSON_57`.
  - `shell.PAGES`: append the L57 tuple with part labels `"第十三部分 · 终章"` /
    `"Part 13 · Capstone"`.
  - `shell.SUBTITLES`: add an L57 subtitle.
  - `check_html.py`: bump `MAX_LESSON = 56 → 57`.
  - Quizzes optional (a small self-test in `quizzes.py` for L57, or none — `render`
    returns '' for unknown fname).

## Architecture / data flow (unchanged contracts)

- `registry.CONTENT[fname]` → `{zh, en}`; `shell.PAGES` is the ordered page list and
  single source for nav/index/print; `build.py` writes `lessons/*.html` + `index.html`;
  `build_print.py` concatenates all PAGES into `print_zh.html` / `print_en.html`
  (CI checks these stay in sync). Adding L57 to PAGES + CONTENT flows everywhere
  automatically. The glossary search/linkify lives inside L46's content HTML, so it
  ships through the same pipeline with no shell changes.
- `build_covers.py` is independent of the lesson pipeline; it reads figure markup,
  writes `assets/covers/*.svg|png` + `assets/covers.html`. It is the only new
  chromium-using tool and runs locally only.

## Error handling / edge cases

- Glossary linkify: only rewrite integers in `1..len(PAGES)`; leave out-of-range or
  non-numeric cells as plain text (defensive — avoids dead links). Idempotent (don't
  double-wrap an already-linked cell).
- Glossary filter JS: guard on element existence (like `SEARCH_JS`), no-op if absent;
  must not break the print build (script simply doesn't run there).
- Covers: `build_covers.py` must be idempotent (re-run → byte-identical svg) and must
  fail loudly if a source figure can't be located. PNG step degrades gracefully if
  chromium is missing (warn + skip), so the tool still emits SVGs.
- L57: must pass all gates (`check_html` 0/0 incl. MIN_CJK and the class/var guard,
  `check_links` all internal links resolve incl. the new cross-links and any link to
  L57 from other lessons), and the rebuild must be idempotent.

## Testing / verification

- `python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py`
  → "0 error(s), 0 warning(s)" and "all N internal links resolve" (N grows with L57's
  links). Idempotent second build (no diff).
- Every **new** SVG (L57 figures + 6 covers) XML-valid and convention-compliant;
  render-verify each in both languages (light + dark for lessons) via headless chromium
  — no overflow/clipping/collision, zh/en parity.
- Covers: visually inspect all 6 PNGs at 1200×630.
- Live check after deploy: CI + "Deploy to GitHub Pages" both green; curl L46 (search
  box + a linkified ref present), L57 (exists, 200), and a cover asset (200).

## Out of scope (whole spec)

- Global lesson-body full-text search; OG-image wiring; PDF cover embedding;
  any change to the existing 56 lessons' prose beyond adding cross-links to L57 where
  it naturally helps (e.g. a "see the capstone" pointer) — kept minimal.
