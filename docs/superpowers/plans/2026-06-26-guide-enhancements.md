# Guide Enhancements (Searchable Glossary · Cover Images · Capstone L57) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three polish features to the completed 56-lesson Milvus Visual Guide — a searchable, cross-linked glossary (L46); six branded shareable cover images; and an end-to-end capstone lesson (L57) — without breaking the zero-dependency, bilingual, Python-generated static-site architecture.

**Architecture:** Lessons are generated from `src/part*.py` (each exports `LESSON_NN = {"zh":html,"en":html}`), registered in `registry.CONTENT`, ordered in `shell.PAGES`, and assembled by `shell.page()` / `shell.index_page()`. `build.py` writes `lessons/*.html` + `index.html`; `build_print.py` writes `print_{zh,en}.html`. Quality gates: `check_html.py` (0/0) + `check_links.py` (all internal links resolve). Bilingual via `.lang-zh`/`.lang-en` CSS toggle; themed palette vars in `shell.CSS`. The covers tool (`build_covers.py`) is an independent, local-only (chromium) generator that writes committed assets.

**Tech Stack:** Python 3 (stdlib only), inline HTML/CSS/SVG/JS (no framework, no runtime deps), headless `chromium` for local PNG rendering + render-verification.

---

## Verification model (this codebase has no unit-test harness — these ARE the tests)

Run from `src/` unless noted. The canonical gate chain (must end clean):

```bash
cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py
```
Expected tail: `Checked NN lessons + index - 0 error(s), 0 warning(s).` and `all <N> internal links resolve`.

**Idempotency:** running `build.py && build_print.py` twice must leave `git status` unchanged on the second run.

**Render-verify (new SVGs only):** use the harness re-created in Task 0 to screenshot every new/changed figure (both languages, light mode) and visually confirm: no text overflow past its rect, no viewBox clipping (x≈760/y≈300), no label/arrow collisions, zh/en parity.

**SVG conventions (hard rules, enforced by `check_html.py` + review):** wrapper `<div class="fig"><svg viewBox="0 0 760 300" role="img" aria-label="…">…</svg><div class="figcap">…</div></div>`; themed color ONLY via inline `style="…var(--…)…"` (NOT presentation attrs like `fill="var()"`); NO `<marker>` (inline `<path>` triangles), NO `<defs>`/gradients/`id`s; classes inside `<svg>` limited to `fig`/`figcap`/`mono`; `.fig svg` is `overflow:hidden`. Palette vars (light+dark in `shell.CSS`): `--ink,--muted,--faint,--panel,--panel-2,--line,--accent(-soft/-ink),--blue(-soft),--teal(-soft),--amber(-soft),--purple(-soft),--red(-soft)`.

**Commit convention:** `git commit -s` (appends `Signed-off-by: verdenmax` last) + trailer `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`. `core.sshCommand="ssh -p 22"` is already set for push.

---

## File map (what each task touches)

| File | Create/Modify | Responsibility |
|------|---------------|----------------|
| `src/part13.py` | Create | `LESSON_57` capstone content (zh+en), end-to-end timeline + zoom-in SVGs |
| `src/registry.py` | Modify | `import part13` + `"57-…": part13.LESSON_57` |
| `src/shell.py` | Modify | `PAGES` append L57 (+ Part 13 labels); `SUBTITLES` L57; CSS `tr.hide` rule |
| `src/check_html.py` | Modify | `MAX_LESSON 56 → 57` |
| `src/quizzes.py` | Modify | optional L57 self-test block |
| `src/part10.py` | Modify | `LESSON_46`: glossary search box + empty-state + filter `<script>`; linkify lesson refs via `import shell` |
| `src/build_covers.py` | Create | compose 6 branded 1200×630 cover SVGs from lesson figures, render PNGs, emit gallery |
| `assets/covers/*.svg`, `*.png` | Create (committed outputs) | the 6 shareable covers |
| `assets/covers.html` | Create (generated) | bilingual cover gallery with download links |
| `README.md` | Modify | add "Cover gallery" link |

Task order: **Task 0** (harness) → **Tasks 1–4** Capstone L57 → **Tasks 5–7** Glossary → **Tasks 8–11** Covers → **Task 12** final integration. Features are independent; this order finalizes lesson content before covers read it.

---

## Task 0: Re-create the render-verify harness

**Files:** Create `/tmp/cover_render.py` (throwaway, not committed).

- [ ] **Step 1: Write the harness** (renders every `.fig` of a built lesson, stacked, one PNG per language, light mode)

```python
#!/usr/bin/env python3
# Usage: python3 /tmp/cover_render.py <lesson_number e.g. 57> <outdir>
import re, glob, subprocess, sys, os, tempfile
def main():
    lesson, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    f = glob.glob(f"lessons/{lesson}-*.html")[0]
    html = open(f).read()
    style = re.search(r'<style>(.*?)</style>', html, re.S).group(1)
    style = re.sub(r'@media \(prefers-color-scheme: dark\)\{.*?\n\}', '', style, flags=re.S)
    figs = re.findall(r'<div class="fig">.*?</div>\s*</div>', html, re.S)
    half = len(figs)//2
    for lang, fs in [("zh", figs[:half]), ("en", figs[half:])]:
        body = "\n".join(f'<div style="margin:14px 0;border:1px solid #ccc">{x}'
                         f'<div style="font:11px sans-serif;color:#999;padding:2px 6px">L{lesson}-{lang} fig#{i}</div></div>'
                         for i, x in enumerate(fs))
        doc = f'<!doctype html><meta charset="utf-8"><style>{style}\nbody{{background:#fff;color:#1d2129;max-width:820px;margin:0 auto;padding:10px}}</style><body>{body}'
        p = os.path.join(outdir, f"L{lesson}_{lang}")
        open(p+".html","w").write(doc)
        udd = tempfile.mkdtemp(prefix="chr_")
        subprocess.run(["chromium","--headless","--no-sandbox","--hide-scrollbars",
            f"--user-data-dir={udd}","--force-device-scale-factor=2",
            f"--window-size=880,{140+len(fs)*420}", f"--screenshot={p}.png", p+".html"],
            capture_output=True)
        print(f"rendered {p}.png ({len(fs)} fig(s))")
if __name__ == "__main__": main()
```

- [ ] **Step 2: Verify chromium is available**

Run: `which chromium`
Expected: `/usr/bin/chromium`

(No commit — `/tmp` only.)

---

## Task 1: Scaffold capstone L57 + wire it into the pipeline

Prove the pipeline accepts a 57th lesson before authoring content.

**Files:**
- Create: `src/part13.py`
- Modify: `src/registry.py` (imports + CONTENT)
- Modify: `src/shell.py` (`PAGES`, `SUBTITLES`, CSS `tr.hide`)
- Modify: `src/check_html.py:35` (`MAX_LESSON`)

- [ ] **Step 1: Create `src/part13.py` with a minimal valid stub**

```python
"""Part 13 - Capstone (synthesis): the life of one row, end to end."""

LESSON_57 = {
    "zh": """
<p class="lead">这一章是全课的<strong>收束</strong>：我们只跟着<strong>一行数据</strong>，从你调用 <span class="mono">insert</span> 的那一刻，一路看到它<strong>变得持久</strong>、<strong>能被搜到</strong>，最后被<strong>高效地长期服务</strong>。前面每条链路（写入·索引·查询）都讲过了，这里把它们<strong>串成一条线</strong>。</p>
""",
    "en": """
<p class="lead">This capstone <strong>ties the whole course together</strong> by following a <strong>single row</strong>: from the instant you call <span class="mono">insert</span>, through becoming <strong>durable</strong>, then <strong>searchable</strong>, and finally <strong>served efficiently</strong> for the long run. Every path (write / index / query) was taught separately; here we <strong>thread them into one line</strong>.</p>
""",
}
```

- [ ] **Step 2: Register in `src/registry.py`**

Add after the `import part12` line:
```python
import part13
```
Add after the `"56-design-failure-as-default.html": part12.LESSON_56,` line (before the closing `}`):
```python
    "57-capstone-life-of-a-row.html": part13.LESSON_57,
```

- [ ] **Step 3: Append the L57 page to `src/shell.py` `PAGES`** (after the `56-design-failure-as-default.html` tuple, before the closing `]`)

```python
    ("57-capstone-life-of-a-row.html", "终章 · 一条数据的一生：从写入到被搜到", "Capstone · Life of a row: from write to searchable",
     "第十三部分 · 终章", "Part 13 · Capstone"),
```

- [ ] **Step 4: Add an L57 entry to `src/shell.py` `SUBTITLES`** (anywhere inside the dict)

```python
    "57-capstone-life-of-a-row.html": ("把写入·索引·查询三条链路串成一行数据的旅程", "thread the write / index / query paths into one row's journey"),
```

- [ ] **Step 5: Add a generic `tr.hide` CSS rule** for the glossary filter (used later). In `src/shell.py` `CSS`, immediately after the line `.toc a.hide, .toc .toc-part.hide { display: none; }` add:

```css
.t tr.hide { display: none; }
```

- [ ] **Step 6: Bump `MAX_LESSON` in `src/check_html.py:35`**

Change `MAX_LESSON = 56` to:
```python
MAX_LESSON = 57  # planned final lesson count (incl. Part 13 capstone); cross-refs may point forward
```

- [ ] **Step 7: Build + gates** (the stub will WARN on MIN_CJK — that is expected until Task 2)

Run: `cd src && python3 build.py && python3 build_print.py && python3 check_links.py`
Expected: `Wrote 58 files`, print built, `all <N> internal links resolve`.
Run: `python3 check_html.py`
Expected: `Checked 57 lessons + index` with at most the single MIN_CJK WARN for lesson 57 (no ERRORs). Note: do NOT commit yet if you prefer a clean gate; otherwise commit and let Task 2 clear the warning.

- [ ] **Step 8: Commit**

```bash
cd .. && git add src/part13.py src/registry.py src/shell.py src/check_html.py && \
git commit -s -m "feat(part13): scaffold capstone L57 and wire into pipeline

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 2: Author the full L57 Chinese content

Replace the `"zh"` stub in `src/part13.py` with the full lesson (target ≥4000 CJK chars to clear `MIN_CJK=3000` comfortably). Follow the existing lesson voice (warm, second-person, source-grounded) and structure used in `part12.py`. Edit the large file **incrementally** (one section per edit).

**Files:** Modify `src/part13.py` (the `"zh"` value).

**Required structure (sections, in order):**

1. `<p class="lead">…</p>` — the opener (keep/extend the stub's lead).
2. **Fig 1 — the end-to-end two-lane timeline** (the centerpiece). Paste this scaffold verbatim, then **render-verify (Task 4) and nudge coordinates only if overlap appears**:

```html
<div class="fig"><svg viewBox="0 0 760 300" role="img" aria-label="一条数据的一生：前台路 SDK 插入→Proxy 盖时间戳与主键→写入 WAL 即持久→进入 growing 段→tsafe 追上即可见；后台路 封段→flush 成 binlog→建索引→QueryNode 加载→接力服务，后台不阻塞可见">
  <text x="380" y="22" text-anchor="middle" style="fill:var(--ink);font-weight:700">一条数据的一生：前台「写入→持久→可见」，后台「落盘→索引→加载」</text>
  <rect x="16" y="70" width="110" height="44" rx="9" style="fill:var(--blue-soft);stroke:var(--blue)"/><text x="71" y="90" text-anchor="middle" style="fill:var(--blue);font-weight:700">SDK</text><text x="71" y="107" text-anchor="middle" style="fill:var(--muted)">insert · 行</text>
  <rect x="170" y="70" width="110" height="44" rx="9" style="fill:var(--blue-soft);stroke:var(--blue)"/><text x="225" y="90" text-anchor="middle" style="fill:var(--blue);font-weight:700">Proxy</text><text x="225" y="107" text-anchor="middle" style="fill:var(--muted)">盖 ts · PK</text>
  <rect x="324" y="70" width="110" height="44" rx="9" style="fill:var(--amber-soft);stroke:var(--amber)"/><text x="379" y="90" text-anchor="middle" style="fill:var(--amber);font-weight:700">WAL / MQ</text><text x="379" y="107" text-anchor="middle" style="fill:var(--muted)">顺序 · 持久</text>
  <rect x="478" y="70" width="110" height="44" rx="9" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="533" y="90" text-anchor="middle" style="fill:var(--teal);font-weight:700">growing 段</text><text x="533" y="107" text-anchor="middle" style="fill:var(--muted)">驻内存</text>
  <rect x="632" y="70" width="110" height="44" rx="9" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="687" y="90" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">可见 ✓</text><text x="687" y="107" text-anchor="middle" style="fill:var(--muted)">tsafe ≥ ts</text>
  <line x1="126" y1="92" x2="168" y2="92" style="stroke:var(--line);stroke-width:2"/><path d="M168,92 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="280" y1="92" x2="322" y2="92" style="stroke:var(--line);stroke-width:2"/><path d="M322,92 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="434" y1="92" x2="476" y2="92" style="stroke:var(--line);stroke-width:2"/><path d="M476,92 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="588" y1="92" x2="630" y2="92" style="stroke:var(--line);stroke-width:2"/><path d="M630,92 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="456" y1="58" x2="456" y2="124" style="stroke:var(--accent);stroke-width:1.5;stroke-dasharray:4 3"/><text x="456" y="50" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700;font-size:11px">持久✓ 不丢</text>
  <path d="M533,114 C533,150 360,156 268,190" style="fill:none;stroke:var(--muted);stroke-width:1.5;stroke-dasharray:5 3"/><path d="M268,190 l9,-3 l-2,10 z" style="fill:var(--muted)"/><text x="470" y="132" text-anchor="middle" style="fill:var(--muted);font-size:11px">满/超时</text>
  <rect x="188" y="192" width="128" height="44" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="252" y="212" text-anchor="middle" style="fill:var(--ink);font-weight:700">seal 封段</text><text x="252" y="229" text-anchor="middle" style="fill:var(--muted)">只读</text>
  <rect x="332" y="192" width="128" height="44" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="396" y="212" text-anchor="middle" style="fill:var(--ink);font-weight:700">flush</text><text x="396" y="229" text-anchor="middle" style="fill:var(--muted)">binlog → 对象存储</text>
  <rect x="476" y="192" width="128" height="44" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="540" y="212" text-anchor="middle" style="fill:var(--ink);font-weight:700">index</text><text x="540" y="229" text-anchor="middle" style="fill:var(--muted)">建索引 · Knowhere</text>
  <rect x="620" y="192" width="128" height="44" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="684" y="212" text-anchor="middle" style="fill:var(--ink);font-weight:700">load</text><text x="684" y="229" text-anchor="middle" style="fill:var(--muted)">QueryNode 加载</text>
  <line x1="316" y1="214" x2="330" y2="214" style="stroke:var(--line);stroke-width:2"/><path d="M330,214 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="460" y1="214" x2="474" y2="214" style="stroke:var(--line);stroke-width:2"/><path d="M474,214 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="604" y1="214" x2="618" y2="214" style="stroke:var(--line);stroke-width:2"/><path d="M618,214 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <path d="M684,192 C684,158 686,148 687,116" style="fill:none;stroke:var(--teal);stroke-width:1.5;stroke-dasharray:5 3"/><path d="M687,116 l-5,11 l10,0 z" style="fill:var(--teal)"/><text x="704" y="166" text-anchor="start" style="fill:var(--teal);font-size:11px">接力</text>
  <text x="380" y="262" text-anchor="middle" style="fill:var(--faint);font-size:12px">后台（封段·落盘·建索引·加载）不阻塞「可见」：行在 growing 段里就已能被查到</text>
</svg><div class="figcap"><b>一条数据的一生</b>：<b>前台</b>很快——insert 写进 <b>WAL 即持久</b>（不丢），落进 <b>growing 段</b>，<b>tsafe 追上它的 ts 就能被搜到</b>；<b>后台</b>慢慢来——段满了<b>封段→flush 成 binlog→建索引→QueryNode 加载</b>，然后<b>接力</b>由 sealed+索引来服务。关键直觉：<b>"持久"和"可见"发生得早，落盘/索引是后台事</b>，并不挡查询。</div></div>
```

3. **`### 1 · 写入：从 insert 到「写进日志就算数」`** — SDK insert → Proxy (校验、必要时 RootCoord 分配 PK、TSO 盖时间戳、按 vchannel/partition 路由)、produce 到 WAL。强调"写进 WAL 并 ack = 持久、可恢复，insert 返回"。引用：`internal/proxy/task_insert.go`（insertTask 的 PreExecute/Execute）、RootCoord TSO/ID allocator（`internal/rootcoord`）、流式写入（`internal/streamingnode`, `pkg/streaming`）。交叉链接到<span class="inline">第 15 课</span>、<span class="inline">第 16 课</span>、<span class="inline">第 11 课</span>。
4. **`### 2 · 持久 vs 可见：两条时间线`** + **Fig 2** (a small diagram contrasting the *durability* clock (WAL ack) and the *visibility* clock (tsafe ≥ ts); show the row is durable first, then visible a moment later when tsafe catches up, and that the growing segment serves it). Spec: viewBox 0 0 760 300; two horizontal timelines (amber "持久" and teal "可见"), a row marker dropping onto each, and a gap labeled "growing 段先顶上". Cross-link <span class="inline">第 30 课</span>（一致性与 tsafe）、<span class="inline">第 26 课</span>（delegator/tsafe）。
5. **`### 3 · 后台落盘：seal → flush → binlog`** — growing 满/超时 → seal（只读）→ SyncTask 把列序列化成 insert/stats/delta binlog 落对象存储，DataCoord 记录 binlog 路径并推进 checkpoint。引用：`internal/flushcommon/writebuffer`、`internal/flushcommon/syncmgr`、`internal/storage`（binlog）、`internal/datacoord`。交叉链接 <span class="inline">第 17 课</span>、<span class="inline">第 18 课</span>。
6. **`### 4 · 建索引 + 加载：从"能查"到"查得快"`** — DataCoord 调度 index build，IndexNode 用 Knowhere 建 HNSW/IVF 写索引文件；QueryCoord 把 sealed+indexed 段分配给 QueryNode，segcore 加载（mmap+索引）；delegator 完成 **handoff**：服务从 growing 接力到 sealed+index，避免重复计数。引用：`internal/datacoord`（index scheduler）、`internal/indexnode`、`internal/querycoordv2`、`internal/querynodev2/delegator`、segcore。交叉链接 <span class="inline">第 21 课</span>、<span class="inline">第 23 课</span>、<span class="inline">第 26 课</span>、<span class="inline">第 27 课</span>。
7. **Fig 3 — "谁碰了这一行" 对照表** (a normal `<table class="t">`, NOT an SVG): 阶段 | 组件 | 源码包 | 详见课次 — one row per stage (8 rows). The 课次 cells use `<span class="inline">第 N 课</span>` (will be auto-linkified by the glossary feature only on L46; here keep as plain inline or manual `<a>` to the lesson — use the existing lesson cross-ref convention `<span class="inline">第 N 课</span>`).
8. **`### 5 · 三个边界，一句话记住`** — synthesis: ① 持久边界＝WAL ack；② 可见边界＝tsafe≥ts（早，不等落盘）；③ 服务接力＝flush+index+load 后从 growing 交棒给 sealed。再点回设计专题（<span class="inline">第 51 课</span>日志即数据、<span class="inline">第 52 课</span>边写边查、<span class="inline">第 53 课</span>存算分离）。
9. A closing `<details>` deep-dive (optional, matches house style) on a subtle point — e.g. why delete/upsert ride the same path via delta binlog (link <span class="inline">第 20 课</span>).

**Citations rule:** cite **file + symbol** (line numbers drift). Keep every claim checkable against `milvus-io/milvus`. If a doc/source claim is uncertain, verify against `/home/verden/course/milvus` before writing.

- [ ] **Step 1** Write sections 1 (lead) + Fig 1 into `part13.py` `"zh"`. Build + render-verify Fig 1 (Task 0 harness): `cd src && python3 build.py && cd .. && python3 /tmp/cover_render.py 57 /tmp/l57 && view /tmp/l57/L57_zh.png`. Fix any overflow/overlap.
- [ ] **Step 2** Write sections 3·1 (写入), 4 (持久 vs 可见 + Fig 2). Build + render-verify Fig 2.
- [ ] **Step 3** Write sections 5 (后台落盘), 6 (建索引+加载), 7 (Fig 3 table). Build.
- [ ] **Step 4** Write sections 8 (三个边界) + 9 (details). Build.
- [ ] **Step 5** Gate: `cd src && python3 build.py && python3 build_print.py && python3 check_html.py`. Expected: 0 errors AND no MIN_CJK warning for L57 (zh ≥ 3000 CJK). If WARN remains, expand prose.
- [ ] **Step 6** Commit:
```bash
git add src/part13.py && git commit -s -m "feat(part13): author capstone L57 Chinese content + figures

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 3: Author the L57 English content at parity

Mirror every zh section into the `"en"` value of `LESSON_57`. Same figures with English labels (keep identical viewBox/coords; only text changes — watch English width vs each `<rect>`, since Latin is wider; shorten labels if a render-verify shows overflow). Same cross-links (`<span class="inline">Lesson N</span>`). Same source citations.

**Files:** Modify `src/part13.py` (the `"en"` value).

- [ ] **Step 1** Mirror lead + Fig 1 (English labels: `SDK / insert · row`, `Proxy / stamp ts · PK`, `WAL/MQ / ordered · durable`, `growing seg / in memory`, `visible ✓ / tsafe ≥ ts`; boundary `durable ✓`; background lane `seal / read-only`, `flush / binlog → object store`, `index / Knowhere`, `load / QueryNode`; `full/timeout`, `handoff`; caption mirrors zh). Aria-label in English.
- [ ] **Step 2** Mirror sections 1–5 + Fig 2 + Fig 3 table (English headers: `Stage | Component | Source package | See lesson`).
- [ ] **Step 3** Build + render-verify **both** languages: `cd src && python3 build.py && cd .. && python3 /tmp/cover_render.py 57 /tmp/l57 && view /tmp/l57/L57_en.png && view /tmp/l57/L57_zh.png`. Confirm zh/en parity (same fig count, same layout) and no English overflow.
- [ ] **Step 4** Gate: `cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py`. Expected 0/0 and all links resolve.
- [ ] **Step 5** Commit:
```bash
git add src/part13.py && git commit -s -m "feat(part13): author capstone L57 English content at parity

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 4: L57 self-test + inbound cross-links + final L57 verification

Make L57 discoverable from the lessons it synthesizes, and add a self-test matching house style.

**Files:**
- Modify: `src/quizzes.py` (add `"57-capstone-life-of-a-row.html"` entry to `QUIZZES`)
- Modify: `src/part12.py` (one pointer from L56 to the capstone) — minimal, optional but recommended

- [ ] **Step 1: Add an L57 self-test** to `src/quizzes.py` `QUIZZES` dict — 2 MCQs grounded in the lesson, e.g.:
  - Q: "一行数据什么时候算'持久、不会丢'？" → answer: "写进 WAL 并被 ack 后（不必等 flush 落盘）"; distractors: "flush 成 binlog 后" / "建好索引后" / "QueryNode 加载后".
  - Q: "新写入的行通常先从哪里被搜到？" → answer: "growing 段（tsafe 追上其 ts 后）"; distractors: "sealed 段" / "索引文件" / "对象存储里的 binlog".
  Provide both `zh` and `en` for each question/option, following the exact shape of existing `QUIZZES` entries (copy the structure of any L5x entry).

- [ ] **Step 2: Add one inbound pointer** at the end of L56's content (`part12.py` `LESSON_56`), both languages, e.g. zh: `<p>想把这六个设计主题<strong>串成一条线</strong>？去<span class="inline">第 57 课</span>跟着一行数据走完全程。</p>` / en mirror with `Lesson 57`. (Keep it to one sentence; do not restructure L56.)

- [ ] **Step 3: Full gate + idempotency**

```bash
cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py
cd .. && git status --short   # note files
cd src && python3 build.py && python3 build_print.py && cd ..
git status --short            # MUST be identical (idempotent)
```
Expected: `0 error(s), 0 warning(s)`, all links resolve, identical status across the two builds.

- [ ] **Step 4: Render-verify** all L57 figures once more (both langs) — no overflow/clip/collision, zh/en parity.

- [ ] **Step 5: Commit**
```bash
git add -A && git commit -s -m "feat(part13): add L57 self-test and inbound link from L56

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 5: Add the glossary filter JS to `shell.py`

**Files:** Modify `src/shell.py` (add a `GLOSSARY_JS` constant next to `SEARCH_JS`).

- [ ] **Step 1: Add `GLOSSARY_JS`** immediately after the `SEARCH_JS = """ … """` block:

```python
GLOSSARY_JS = """
(function(){
  function wire(inputId, countId, emptyId, scope){
    var q=document.getElementById(inputId); if(!q) return;
    var root=document.querySelector(scope); if(!root) return;
    var empty=document.getElementById(emptyId), count=document.getElementById(countId);
    var rows=[].slice.call(root.querySelectorAll('table.t tr')).filter(function(tr){return tr.querySelector('td');});
    rows.forEach(function(tr){ tr.setAttribute('data-s',(tr.textContent||'').toLowerCase()); });
    function run(){
      var t=(q.value||'').toLowerCase().trim(), n=0;
      rows.forEach(function(tr){
        var hit=!t||tr.getAttribute('data-s').indexOf(t)>=0;
        tr.classList.toggle('hide',!hit); if(hit)n++;
      });
      if(empty) empty.classList.toggle('show', !!t && n===0);
      if(count) count.textContent = t ? String(n) : '';
    }
    q.addEventListener('input',run);
  }
  wire('qglzh','qglzhc','qglzhe','.lang-zh');
  wire('qglen','qglenc','qglene','.lang-en');
})();
"""
```

- [ ] **Step 2: Build to confirm no syntax error**

Run: `cd src && python3 build.py >/dev/null && echo OK`
Expected: `OK`

(No commit yet — committed with Task 6.)

---

## Task 6: Make L46 searchable + cross-linked

Add a search box + empty-state to both languages of `LESSON_46`, wire the filter script, and turn every "第 N 课 / Lesson N" reference into a link to that lesson.

**Files:** Modify `src/part10.py` (top-of-file imports + helpers; rebuild `LESSON_46` after its literal definition).

- [ ] **Step 1: Add imports + helpers near the top of `src/part10.py`** (after the module docstring / existing imports; if none, at the very top):

```python
import re as _re
import shell as _shell


def _linkify_lessons(html):
    """Wrap '第 N 课' / 'Lesson N' references in links to that lesson page.

    N must be a valid lesson number (1..len(PAGES)); out-of-range refs are left
    as plain text. Glossary content has no pre-existing <a>, so this is safe to
    run once at import time.
    """
    n = len(_shell.PAGES)

    def repl(m):
        k = int(m.group(1))
        if 1 <= k <= n:
            return f'<a href="{_shell.PAGES[k-1][0]}">{m.group(0)}</a>'
        return m.group(0)

    html = _re.sub(r'第\s*(\d+)\s*课', repl, html)
    html = _re.sub(r'Lesson\s+(\d+)', repl, html)
    return html


def _gl_search(lang):
    if lang == "zh":
        return ('<div class="toc-search"><input id="qglzh" type="search" '
                'placeholder="🔎 搜索术语（中英皆可）" autocomplete="off" aria-label="search terms">'
                '<span class="qcount" id="qglzhc"></span></div>'
                '<div class="toc-empty" id="qglzhe">没有匹配的术语，换个关键词试试。</div>')
    return ('<div class="toc-search"><input id="qglen" type="search" '
            'placeholder="🔎 Search terms (zh or en)" autocomplete="off" aria-label="search terms">'
            '<span class="qcount" id="qglenc"></span></div>'
            '<div class="toc-empty" id="qglene">No matching terms — try another keyword.</div>')
```

- [ ] **Step 2: Rebuild `LESSON_46`** by inserting, **immediately after** the existing `LESSON_46 = { … }` literal block, this re-binding:

```python
LESSON_46 = {
    "zh": _gl_search("zh") + _linkify_lessons(LESSON_46["zh"]),
    "en": _gl_search("en") + _linkify_lessons(LESSON_46["en"]) + f'<script>{_shell.GLOSSARY_JS}</script>',
}
```

- [ ] **Step 3: Build + gates**

Run: `cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py`
Expected: `0 error(s), 0 warning(s)`; **all internal links resolve** (the new glossary→lesson links must all resolve — if any fails, the linkify produced a bad filename; verify `_shell.PAGES[k-1][0]`).

- [ ] **Step 4: Verify the rendered glossary** has the search box and linkified refs:

```bash
cd .. && grep -c 'id="qglzh"\|id="qglen"' lessons/46-glossary.html   # expect 2
grep -oE '<a href="[0-9]{2}-[a-z-]+\.html">第 [0-9]+ 课</a>' lessons/46-glossary.html | head   # expect linkified zh refs
grep -c 'GLOSSARY_JS\|wire(' lessons/46-glossary.html   # expect the script present (>=1)
```

- [ ] **Step 5: Manual interactivity check (optional but recommended)** — open `lessons/46-glossary.html` in a browser, type a term (e.g. "tsafe" / "段"), confirm rows filter and the count updates; clear to restore. (Static screenshot can't capture JS; this is a human/manual check.)

- [ ] **Step 6: Commit**
```bash
git add src/shell.py src/part10.py && git commit -s -m "feat(glossary): add term search + cross-links to lessons in L46

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 7: Create the cover generator `src/build_covers.py`

A local-only tool that composes six 1200×630 branded cover cards from key lesson
figures (figure inlined with the **dark** palette on a dark card), renders PNGs via
chromium, and emits a gallery. Independent of `build.py`; outputs are committed.

**Files:** Create `src/build_covers.py`. Create dir `assets/covers/` (the script makes it).

- [ ] **Step 1: Create `src/build_covers.py`** with this complete content:

```python
#!/usr/bin/env python3
"""Compose shareable 1200x630 cover cards from key lesson figures.

Local-only (chromium for PNG). Outputs (committed):
  assets/covers/<slug>.svg   source of truth
  assets/covers/<slug>.png   rendered 2x
  assets/covers.html         gallery

Usage:
  python3 build_covers.py            build all covers + gallery
  python3 build_covers.py --list 03  list lesson 03's zh figures (pick index)
"""
import os, re, sys, glob, subprocess, tempfile, html as _html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
LESSONS = os.path.join(ROOT, "lessons")
OUT = os.path.join(ROOT, "assets", "covers")
sys.path.insert(0, HERE)
import shell  # noqa: E402  (palette + favicon + lang JS)

# (lesson, lang, fig_index_within_that_lang, slug, title_zh, title_en)
# fig_index defaults to 0 (the lesson's headline figure); verify with --list.
COVERS = [
    ("03", "zh", 0, "01-request-flow",      "一次请求的一生",   "Life of a request"),
    ("09", "zh", 0, "02-control-data-plane", "控制面 vs 数据面", "Control plane vs data plane"),
    ("51", "zh", 0, "03-log-as-data",        "日志即数据",       "Log as data"),
    ("12", "zh", 0, "04-segment-lifecycle",  "段的生命周期",     "Segment lifecycle"),
    ("26", "zh", 0, "05-two-layer-fanout",   "两层扇出查询",     "Two-layer fan-out query"),
    ("53", "zh", 0, "06-storage-compute",    "存算分离",         "Storage-compute separation"),
]


def parse_palette(css):
    """{var: value}; dark :root overlaid on the light :root defaults."""
    pal = {}
    m = re.search(r':root\s*\{(.*?)\}', css, re.S)
    if m:
        for k, v in re.findall(r'--([a-z0-9-]+)\s*:\s*([^;]+);', m.group(1)):
            pal[k] = v.strip()
    md = re.search(r'@media \(prefers-color-scheme: dark\)\s*\{(.*)\}', css, re.S)
    if md:
        dm = re.search(r':root\s*\{(.*?)\}', md.group(1), re.S)
        if dm:
            for k, v in re.findall(r'--([a-z0-9-]+)\s*:\s*([^;]+);', dm.group(1)):
                pal[k] = v.strip()
    return pal


def inline_palette(svg, pal):
    return re.sub(r'var\(--([a-z0-9-]+)(?:\s*,[^)]*)?\)',
                  lambda m: pal.get(m.group(1), "#888"), svg)


def figs_of(lesson, lang):
    f = glob.glob(os.path.join(LESSONS, f"{lesson}-*.html"))[0]
    h = open(f, encoding="utf-8").read()
    figs = re.findall(r'<div class="fig">.*?</div>\s*</div>', h, re.S)
    half = len(figs) // 2
    return figs[:half] if lang == "zh" else figs[half:]


def inner_svg(fig):
    m = re.search(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>', fig, re.S)
    if not m:
        raise SystemExit("build_covers: could not parse <svg> in figure")
    return m.group(1), m.group(2)


def build_svg(lesson, lang, idx, tz, te, pal):
    figs = figs_of(lesson, lang)
    if idx >= len(figs):
        raise SystemExit(f"build_covers: lesson {lesson} has {len(figs)} {lang} figs, need idx {idx}")
    vb, inner = inner_svg(figs[idx])
    inner = inline_palette(inner, pal)
    bg = pal.get("bg", "#0e1117"); ink = pal.get("ink", "#e6e6e6")
    muted = pal.get("muted", "#9aa0a6"); accent = pal.get("accent", "#1296db")
    panel = pal.get("panel", "#171a21"); line = pal.get("line", "#2a2f37")
    W, H, fw = 1200, 630, 1080
    fh = int(fw * 300 / 760); fx = (W - fw) // 2; fy = 156
    font = "-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>text{{font-family:{font}}}.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}</style>
<rect width="{W}" height="{H}" fill="{bg}"/>
<rect x="0" y="0" width="{W}" height="8" fill="{accent}"/>
<text x="60" y="66" font-size="30" font-weight="700" fill="{ink}">🐦 Milvus 图解教程 · Milvus Visual Guide</text>
<text x="60" y="112" font-size="36" font-weight="700" fill="{accent}">第 {int(lesson)} 课 · {_html.escape(tz)}</text>
<text x="60" y="142" font-size="22" fill="{muted}">{_html.escape(te)}</text>
<rect x="{fx-20}" y="{fy-16}" width="{fw+40}" height="{fh+32}" rx="16" fill="{panel}" stroke="{line}"/>
<svg x="{fx}" y="{fy}" width="{fw}" height="{fh}" viewBox="{vb}">{inner}</svg>
<text x="60" y="{H-32}" font-size="22" fill="{muted}">verdenmax.github.io/milvus-visual-guide</text>
<text x="{W-60}" y="{H-32}" text-anchor="end" font-size="22" fill="{muted}">57 课 · 中英双语 / bilingual</text>
</svg>'''


def render_png(svg_path, png_path):
    if not _which("chromium"):
        print("  (chromium not found; skipping PNG — commit SVG only)")
        return False
    udd = tempfile.mkdtemp(prefix="cov_")
    subprocess.run(["chromium", "--headless", "--no-sandbox", "--hide-scrollbars",
                    f"--user-data-dir={udd}", "--force-device-scale-factor=2",
                    "--window-size=1200,630", f"--screenshot={png_path}", svg_path],
                   capture_output=True)
    return os.path.exists(png_path)


def _which(b):
    for p in os.environ.get("PATH", "").split(os.pathsep):
        if os.path.exists(os.path.join(p, b)):
            return True
    return False


def gallery_html():
    cards = []
    for lesson, lang, idx, slug, tz, te in COVERS:
        cards.append(
            f'<figure class="cov"><a href="covers/{slug}.png"><img loading="lazy" '
            f'src="covers/{slug}.png" alt="{_html.escape(tz)} / {_html.escape(te)}"></a>'
            f'<figcaption><b>第 {int(lesson)} 课 · <span class="lang-zh">{_html.escape(tz)}</span>'
            f'<span class="lang-en">{_html.escape(te)}</span></b><br>'
            f'<a href="covers/{slug}.svg" download>SVG</a> · <a href="covers/{slug}.png" download>PNG</a> · '
            f'<a href="lessons/{lesson}-{_slug_lookup(lesson)}"><span class="lang-zh">看这一课</span><span class="lang-en">open lesson</span></a>'
            f'</figcaption></figure>')
    grid = "\n".join(cards)
    return f'''<!DOCTYPE html>
<html lang="zh-CN" data-lang="zh"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{shell.LANG_BOOT}
<title>封面图库 · Cover gallery - Milvus 图解教程</title>
{shell.head_meta("Cover gallery - Milvus 图解教程", "Shareable cover cards of the Milvus Visual Guide's key diagrams.")}
<style>{shell.CSS}
.covgrid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:1.4rem;margin:1.6rem 0}}
.cov img{{width:100%;border:1px solid var(--line);border-radius:12px;display:block}}
.cov figcaption{{color:var(--muted);font-size:.9rem;margin:.5rem 0 0}}
</style></head><body>
<div class="topbar"><div class="topbar-inner">
<a class="home" href="index.html">🐦 <b class="lang-zh">Milvus 图解教程</b><b class="lang-en">Milvus Visual Guide</b></a>
<span class="pill"><span class="lang-zh">封面图库</span><span class="lang-en">Cover gallery</span></span>
<button class="langtoggle" onclick="mvgToggleLang()" aria-label="switch language"><span class="lang-zh">EN</span><span class="lang-en">中</span></button>
</div><div class="progress"><span style="width:100%"></span></div></div>
<div class="wrap"><div class="hero">
<div class="part">{shell.bi("可分享封面", "Shareable covers")}</div>
<h1><span class="lang-zh">封面图库</span><span class="lang-en">Cover gallery</span></h1>
<p class="lead">{shell.bi("把本教程最具代表性的几张图做成 1200×630 的可分享封面（社交卡片尺寸）。点击可看大图，或下载 SVG / PNG。", "The guide's most iconic diagrams as 1200×630 shareable cards (social-card size). Click to enlarge, or download SVG / PNG.")}</p>
</div>
<div class="covgrid">{grid}</div>
</div>
<script>{shell.LANG_JS}</script>
</body></html>'''


def _slug_lookup(lesson):
    f = glob.glob(os.path.join(LESSONS, f"{lesson}-*.html"))[0]
    return os.path.basename(f).split("-", 1)[1]


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--list":
        for i, fig in enumerate(figs_of(sys.argv[2], "zh")):
            m = re.search(r'aria-label="([^"]*)"', fig)
            print(f"[{i}] {(m.group(1) if m else '(no aria)')[:90]}")
        return
    os.makedirs(OUT, exist_ok=True)
    pal = parse_palette(shell.CSS)
    for lesson, lang, idx, slug, tz, te in COVERS:
        svg = build_svg(lesson, lang, idx, tz, te, pal)
        sp = os.path.join(OUT, slug + ".svg")
        open(sp, "w", encoding="utf-8").write(svg)
        ok = render_png(sp, os.path.join(OUT, slug + ".png"))
        print(f"  {slug}.svg{' + .png' if ok else ''}")
    open(os.path.join(ROOT, "assets", "covers.html"), "w", encoding="utf-8").write(gallery_html())
    print(f"Wrote {len(COVERS)} covers + assets/covers.html")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Confirm target figures.** For each cover lesson, list its zh figures and confirm index 0 is the headline diagram; adjust the `fig_index` in `COVERS` if not.

```bash
cd src && for n in 03 09 51 12 26 53; do echo "== L$n =="; python3 build_covers.py --list $n; done
```
Expected: each lists the lesson's zh figures with aria-labels; pick the index whose aria-label matches the cover's intent (update `COVERS` if ≠ 0).

(No commit yet — committed with Task 8 after PNGs render.)

---

## Task 8: Generate covers, wire README, commit

**Files:** Run `src/build_covers.py`; create `assets/covers/*.svg|png` + `assets/covers.html`; modify `README.md`.

- [ ] **Step 1: Generate** all covers + gallery

```bash
cd src && python3 build_covers.py
```
Expected: `01-request-flow.svg + .png` … `06-storage-compute.svg + .png`, then `Wrote 6 covers + assets/covers.html`.

- [ ] **Step 2: Visually inspect all 6 PNGs** at 1200×630 — figure is centered, legible, not clipped by the panel; title/URL bands readable; dark palette looks right (no light-on-light). Use the view tool on each `assets/covers/*.png`. If a figure overflows its panel, lower `fw`/raise `fy` or pick a different `fig_index`; regenerate.

- [ ] **Step 3: Confirm idempotency** of the SVG (PNG bytes may differ across chromium runs; SVG must not)

```bash
cd src && python3 build_covers.py >/dev/null && cd .. && git status --short assets/covers/*.svg
```
Expected: no `.svg` shows as modified on the second run (re-run produced identical SVG).

- [ ] **Step 4: Add a README link.** In `README.md`, add a line in the links/sections area:

```markdown
- 🖼️ **[Cover gallery](https://verdenmax.github.io/milvus-visual-guide/covers.html)** — shareable 1200×630 cards of the guide's key diagrams (SVG + PNG).
```

- [ ] **Step 5: Verify gallery links resolve** (manual, since `check_links.py` only scans lessons + index):

```bash
grep -oE 'href="(covers/[^"]+|lessons/[^"]+|index\.html)"' assets/covers.html | sort -u | head
ls assets/covers/   # every referenced slug.svg/.png exists
```

- [ ] **Step 6: Commit**
```bash
git add assets/ README.md src/build_covers.py && git commit -s -m "feat(covers): add 6 shareable cover cards + gallery

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 9: Final integration — full gate, deploy, live verification, cleanup

**Files:** none new (verification + push). Optionally link the gallery from `index.html` footer (via `shell.index_page`) — judgment call; keep minimal.

- [ ] **Step 1: Whole-repo gate + idempotency**

```bash
cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py
cd .. && git status --short            # should be clean (all committed)
cd src && python3 build.py && python3 build_print.py && cd .. && git status --short   # MUST stay clean (idempotent)
```
Expected: `Checked 57 lessons + index - 0 error(s), 0 warning(s)`, `all <N> internal links resolve`, clean status both times.

- [ ] **Step 2: XML-validity of every NEW svg** (L57 figs + 6 covers)

```bash
python3 - <<'PY'
import glob, xml.dom.minidom as m
bad=0
for f in glob.glob("assets/covers/*.svg"):
    try: m.parse(f)
    except Exception as e: bad+=1; print("BAD", f, e)
print("covers:", len(glob.glob('assets/covers/*.svg')), "checked,", bad, "invalid")
PY
```
Expected: `0 invalid`. (L57 figs already validated by `check_html` + render-verify in Task 4.)

- [ ] **Step 3: Push**

```bash
git push origin master
```

- [ ] **Step 4: Verify CI + Deploy both green**

```bash
sleep 40; curl -s "https://api.github.com/repos/verdenmax/milvus-visual-guide/actions/runs?per_page=4" \
 | python3 -c "import sys,json;d=json.load(sys.stdin);[print(r['name'],'|',r['status'],'|',r['conclusion']) for r in d['workflow_runs'][:2]]"
```
Expected: `Deploy to GitHub Pages | completed | success` and `CI | completed | success` (poll again if still in_progress).

- [ ] **Step 5: Live checks**

```bash
curl -s -o /dev/null -w "L57 %{http_code}\n" https://verdenmax.github.io/milvus-visual-guide/lessons/57-capstone-life-of-a-row.html
curl -s -o /dev/null -w "gallery %{http_code}\n" https://verdenmax.github.io/milvus-visual-guide/covers.html
curl -s -o /dev/null -w "cover png %{http_code}\n" https://verdenmax.github.io/milvus-visual-guide/covers/01-request-flow.png
curl -s https://verdenmax.github.io/milvus-visual-guide/lessons/46-glossary.html | grep -c 'id="qglzh"'   # expect 1
```
Expected: all `200`; glossary search box present.

- [ ] **Step 6: Cleanup** throwaway artifacts

```bash
rm -rf /tmp/l57 /tmp/cover_render.py /tmp/chr_* /tmp/cov_* 2>/dev/null; echo cleaned
```

- [ ] **Step 7: Update plan + checkpoint** — mark all tasks done; note the three features live.

---

## Self-review notes (filled during writing)

- Task numbering: Capstone = Tasks 1–4, Glossary = Tasks 5–6, Covers = Tasks 7–8, Integration = Task 9 (the header file-map line said 5–7/8–11/12; this is the corrected mapping).
- Spec coverage: ① glossary search+linkify → Tasks 5–6; ② 6 covers + gallery + README → Tasks 7–8; ③ capstone L57 (part13, wiring, MAX_LESSON, figures, parity, quiz, inbound link) → Tasks 1–4. All spec sections covered.
- Type/name consistency: ids `qglzh/qglzhc/qglzhe`, `qglen/qglenc/qglene` match between `GLOSSARY_JS` (Task 5) and `_gl_search` (Task 6). `COVERS` tuple shape `(lesson,lang,idx,slug,tz,te)` consistent across `build_svg`/`gallery_html`/`main`. `MAX_LESSON=57` set in Task 1, relied on by linkify range + cross-ref gate.
