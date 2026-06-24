# Milvus Visual Guide — Design Spec

**Date:** 2026-06-24
**Status:** Approved (approach), in execution
**Author:** @verdenmax (driven autonomously)

## 1. Purpose

A **visual, bilingual (中文 + English)** learning guide that explains the **internals of
[Milvus](https://github.com/milvus-io/milvus)** — the distributed vector database written in
Go + C++ + Rust. The guide takes a reader from *"what is a vector database"* all the way to
*"how the write/query paths work inside the code"* and *"how to build, test and contribute a PR"*.

It is modeled **directly** on the sibling project `~/course/llama-cpp-visual-guide`: same
zero-dependency Python-generator architecture, same visual design system, same per-lesson
pedagogy (life analogy → macro picture → diagrams → cited code → self-test quiz), same bilingual
in-page toggle, same GitHub-Pages delivery.

### Audience & depth
- Primary: engineers who want to **understand Milvus internals** and eventually contribute.
- Starts from first principles (vectors, ANN, the data model) so a motivated newcomer can follow.
- Builds up to deep internals: the streaming write path, indexing/Knowhere, the query path and
  the C++ `segcore`, the coordinators, consistency/timestamps, and the contribution workflow.

### Non-goals
- Not a user manual / API reference (milvus.io docs already do that). We cite the SDK only as the
  entry point into the internals.
- Not a fork or mirror of Milvus source. We **quote small, cited snippets only** and explain them.

## 2. Architecture (tech) — cloned from the reference, retargeted to Milvus

Pure **Python 3, zero runtime dependencies**. Generators under `src/` emit committed static HTML.

```
milvus-visual-guide/
  src/
    part1.py .. part10.py   bilingual lesson content; one module per Part; each exports
                            LESSON_NN = {"zh": <html>, "en": <html>}
    quizzes.py              per-lesson self-test (mcq + open); deterministic option shuffle
    shell.py                CSS design system + PAGES list + bi()/esc()/head_meta()
                            + page() (lesson shell) + index_page() (TOC) + SUBTITLES
    registry.py             ordered filename -> {"zh","en"} content map (imports part1..N)
    build.py                writes index.html + lessons/NN-*.html
    build_print.py          writes print_zh.html + print_en.html (one page per lesson)
    check_html.py           structural + quality gates (CI-blocking on ERROR)
    check_links.py          internal relative-link resolver
  lessons/                  generated lesson pages (committed, must rebuild with no diff)
  index.html                generated TOC (committed)
  print_zh.html print_en.html   generated print/PDF editions (committed)
  docs/superpowers/specs/   design specs (this file + per-milestone specs)
  docs/superpowers/plans/   roadmap + per-milestone implementation plans
  .github/workflows/        ci.yml (build+validate+no-diff), deploy.yml (Pages)
  README.md  LICENSE(MIT)  LICENSE-CONTENT(CC BY 4.0)  .gitignore
```

### Single source of truth & invariants
- `shell.PAGES` is the ordered page list `(filename, title_zh, title_en, part_zh, part_en)`.
  `registry.CONTENT` must have exactly one non-empty bilingual entry per `PAGES` filename.
  `check_html.py` enforces this alignment (no orphan keys, no missing entries).
- Generated HTML is committed and must be **byte-identical** on rebuild (CI `git diff --exit-code`).
- Navigation uses **relative `href`** links so the site works via `file://` or any static host.
- Bilingual contract: every page carries `data-lang="zh"` (default); CSS hides the inactive
  language; a topbar toggle + `localStorage` switch persists the choice.

### Theme (Milvus identity)
- Accent recolored from llama orange to **Milvus blue** (`--accent` ≈ `#1296db`), with matching
  dark-mode variant. Topbar mark uses 🐦 (Milvus bird). Titles: "Milvus 图解教程 / Milvus Visual Guide".
- All other design tokens (cards, flow/vflow/layers/cols/cellgroup/timeline/trace, code blocks,
  accordion, TOC search) are carried over unchanged — they are subject-agnostic.

## 3. Content model — what every lesson contains

Each lesson is a self-contained bilingual page. Authoring target per lesson:

1. **Lead paragraph** (`.lead`) — one-paragraph hook: what this lesson is about and why it matters.
2. **Life analogy card** (`.card.analogy`, 🔌/类比) — map the concept onto an everyday situation.
3. **Macro card** (`.card.macro`, 🌍) — the big-picture takeaway in 2–3 sentences.
4. **2–5 `<h2>` sections** mixing prose with **≥3 visual blocks per language** chosen from:
   `flow`, `vflow`, `layers`, `cols`, `cellgroup`, `timeline`, `trace`, `table.t`.
5. **Cited code** via `.codefile` — *small* snippets with a `file + symbol` caption
   (line numbers drift, so cite symbols). Never paste large source; explain, don't copy.
6. **Key-points card** (`.card.key`, 本课要点 / Key points) — bulleted recap.
7. **Self-test** (`quizzes.py`) — 2–4 design-insight MCQs (with "why") + 1–2 open questions.

### Quality gates (enforced by `check_html.py`, adapted from reference)
- ERROR (CI-blocking): balanced `div/details/table/pre/summary`; `details==summary`; exactly one
  `<h1>`; `<title>` + meta description present; both `lang-zh` and `lang-en` blocks present; no
  unescaped `<` inside `<pre>`; prev/next nav matches `PAGES`; TOC lists every page; the
  "共 N 课 · N 个部分" pill matches `PAGES`; registry has non-empty zh+en per page; no orphan keys.
- WARN (visible, non-blocking, but we drive to zero): per-lesson **≥ 3000 CJK chars** (zh),
  **≥ 6 visual blocks** (counting both languages, i.e. ≥3/lang), an analogy card and a
  key-points card present.
- Cross-reference guard: "第 N 课" references must be within `1..MAX_LESSON`.

## 4. Source-accuracy discipline

Milvus is large and evolves fast. Every content milestone MUST, before writing:
1. Read the relevant `docs/developer_guides/chap*.md` + `docs/agent_guides/*` + `docs/design-docs`.
2. Read the **actual source** for the components in scope (Key Packages, see roadmap).
3. Cross-check doc vs code; when they disagree, the **code wins** and we note it.

Cited facts use `file + symbol` (e.g. `internal/core/src/segcore/SegmentSealedImpl.cpp ::Search`),
never bare line numbers. Verified-against-source is stated on the index page.

## 5. Licensing & disclaimer

- **Code** (`src/` generators + validators) — **MIT**, `LICENSE`.
- **Content** (lesson prose + diagrams authored in `src/part*.py` / `src/quizzes.py` and rendered
  into the HTML) — **CC BY 4.0**, `LICENSE-CONTENT`.
- **Disclaimer** (README + index): third-party, **unofficial** educational material *about* Milvus;
  contains **no Milvus source code** beyond small, cited snippets; **Milvus itself is Apache-2.0**
  licensed by its authors (note: this differs from llama.cpp's MIT — phrasing updated accordingly).

## 6. Curriculum — 10 parts, ~46 lessons

See the per-milestone specs for the detailed scope of each lesson. Overview:

| Part | Title (zh / en) | Lessons |
| --- | --- | --- |
| 1 | 宏观全景 / Overview | L01–03 |
| 2 | 前置基础 / Foundations | L04–08 |
| 3 | 分布式架构 / Distributed architecture | L09–14 |
| 4 | 写入链路 / The write path | L15–20 |
| 5 | 索引 / Indexing | L21–24 |
| 6 | 查询链路 / The query path | L25–30 |
| 7 | 流式系统 / Streaming system (deep) | L31–33 |
| 8 | C++ 内核 / C++ core internals | L34–37 |
| 9 | API·工具·运维 / API, tools & ops | L38–41 |
| 10 | 实战与贡献 / Practice & contributing | L42–46 |

Lesson titles are enumerated in `docs/superpowers/plans/2026-06-24-milvus-visual-guide-roadmap.md`.
Final lesson counts per part may shift by ±1 as research firms up each milestone; `MAX_LESSON`
in `check_html.py` is updated as parts land.

## 7. Risks & mitigations

- **Scope/accuracy drift** — Milvus internals are deep and version-sensitive. Mitigation: per-part
  source reading + code-wins cross-check + symbol-based citations.
- **Content volume** — ~46 rich bilingual lessons. Mitigation: milestone-by-milestone delivery;
  heavy lesson drafting delegated to subagents with a strict format brief + the milestone spec,
  then two-stage review and validator gates before commit.
- **Pipeline regressions** — Mitigation: validators + no-diff rebuild run after every milestone;
  CI mirrors them.

## 8. Definition of done (whole project)

All 12 milestones complete; `build.py`/`build_print.py` regenerate with **no diff**;
`check_html.py` + `check_links.py` pass with **0 errors and 0 warnings**; CI + deploy workflows
green; README documents build/validate/print; dual licenses present.
