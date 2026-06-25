# Milvus Visual Guide / Milvus 图解学习指南

<p align="center">
  <a href="https://verdenmax.github.io/milvus-visual-guide/"><b>📖&nbsp; Read the guide online&nbsp; →&nbsp; verdenmax.github.io/milvus-visual-guide</b></a>
  <br>
  <sub>The complete bilingual (English&nbsp;+&nbsp;中文) visual guide to Milvus internals — 50 lessons, runs in your browser, zero install.<br>点开即读这份 Milvus 内部原理图解指南 · 中英双语 · 50 课 · 无需安装</sub>
</p>

[![Read online](https://img.shields.io/badge/Read_online-Live_Demo-1296db?logo=githubpages&logoColor=white)](https://verdenmax.github.io/milvus-visual-guide/)
[![CI](https://github.com/verdenmax/milvus-visual-guide/actions/workflows/ci.yml/badge.svg)](https://github.com/verdenmax/milvus-visual-guide/actions/workflows/ci.yml)
[![Deploy](https://github.com/verdenmax/milvus-visual-guide/actions/workflows/deploy.yml/badge.svg)](https://github.com/verdenmax/milvus-visual-guide/actions/workflows/deploy.yml)
[![Parts](https://img.shields.io/badge/parts-11-7048e8)](https://verdenmax.github.io/milvus-visual-guide/)
[![Lessons](https://img.shields.io/badge/lessons-50-7048e8)](https://verdenmax.github.io/milvus-visual-guide/)
[![Explains Milvus](https://img.shields.io/badge/explains-milvus-1296db?logo=github&logoColor=white)](https://github.com/milvus-io/milvus)
[![Dependencies](https://img.shields.io/badge/dependencies-0-2b8a3e)](#build--validate)
[![Code: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Content: CC BY 4.0](https://img.shields.io/badge/content-CC_BY_4.0-blue.svg)](LICENSE-CONTENT)

A visual, bilingual (English + 中文) guide to the internals of
[Milvus](https://github.com/milvus-io/milvus) - the distributed vector database - that takes you
from *"what is a vector database"* all the way to *"how the write/query paths work in the code"*
and *"how to build, test and contribute a PR"*.

> **Disclaimer:** This is **third-party, unofficial** educational material *about* Milvus. It
> contains **no Milvus source code** beyond small, cited snippets; it explains Milvus by quoting
> short, attributed excerpts. Milvus itself is **Apache-2.0**-licensed by its own authors.

> **Status:** **complete** - all **11 parts / 50 lessons** are built and validated. The guide was
> built milestone-driven; see `docs/superpowers/plans/` for the roadmap.

Every lesson is self-contained, embeds both languages (toggle in the page), and uses hand-drawn
diagrams, worked-example traces, real (cited) code, and a short self-test quiz.

---

## What it covers

The guide is organized into eleven parts that build up along the data lifecycle:

| Part | Topic | Lessons |
| --- | --- | --- |
| 1 | Overview - what Milvus is, the project map, the life of a request | L01-03 |
| 2 | Foundations - embeddings, ANN, the data model, segments, dependencies | L04-08 |
| 3 | Distributed architecture - proxy, rootcoord, datacoord, querycoord, metadata | L09-14 |
| 4 | The write path - insert, streaming/WAL, datanode/flush, binlog, compaction | L15-20 |
| 5 | Indexing - the index service, Knowhere, scalar & full-text (tantivy) | L21-24 |
| 6 | The query path - search, querynode, segcore, exec, reduce, consistency | L25-30 |
| 7 | Streaming system (deep) - WAL architecture, DDL/DCL via log, replication & CDC | L31-33 |
| 8 | C++ core internals - segcore, mmap, expr/exec, GPU | L34-37 |
| 9 | API, tools & ops - gRPC/SDK, observability, config, deployment | L38-41 |
| 10 | Practice & contributing - build/run, testing, conventions, PRs, glossary | L42-46 |
| 11 | Advanced topics (optional) - bulk import, hybrid search & rerank, quota/rate-limit, advanced features tour | L47-50 |

## How to view

**Online:** published via GitHub Pages at **https://verdenmax.github.io/milvus-visual-guide/**.

**Locally** (zero dependencies, just Python 3):

```bash
cd src
python3 build.py
# then open ../index.html in a browser
```

## How to print / export a PDF

```bash
cd src
python3 build_print.py
# open ../print_zh.html (Chinese) or ../print_en.html (English) in a browser,
# then File -> Print -> Save as PDF (Ctrl/Cmd+P). Each lesson starts on a new page.
```

## Project structure

```
src/            generators + tooling (pure Python 3, no dependencies)
  part1.py .. part11.py   lesson content (bilingual), one module per part
  quizzes.py              per-lesson self-test questions
  shell.py                page shell + the shared CSS
  registry.py             ordered filename -> content map
  build.py                builds index.html + lessons/*.html
  build_print.py          builds print_zh.html + print_en.html
  check_html.py           structural HTML validation
  check_links.py          internal link validation
lessons/        generated lesson pages (committed, kept in sync)
index.html      generated table of contents (committed)
print_*.html    generated print editions (committed)
docs/superpowers/   design specs and implementation plans
```

## Build & validate

```bash
cd src
python3 build.py          # regenerate index.html + lessons/*.html
python3 build_print.py    # regenerate print_zh.html + print_en.html
python3 check_html.py     # structural checks (0 error / 0 warning expected)
python3 check_links.py    # all internal links must resolve
```

The generated HTML is committed and kept in sync with the sources; a re-run of `build.py` should
produce no diff.

## License

Dual-licensed:

- **Code** (the Python generators and validation scripts under `src/`) - MIT, see [LICENSE](LICENSE).
- **Content** (the lesson text and diagrams rendered into `index.html`, `lessons/*.html`,
  `print_*.html`) - CC BY 4.0, see [LICENSE-CONTENT](LICENSE-CONTENT).

---

## 中文说明

这是一份 [Milvus](https://github.com/milvus-io/milvus) 内部原理的**图解、双语**学习指南，从
"Milvus 是什么"一路讲到"写入/查询链路在代码里怎么走"以及"怎么本地构建、测试、提一个 PR"。

> **声明：** 本项目是**第三方、非官方**的学习材料，**不包含 Milvus 源码**（仅引用少量、标注来源的
> 代码片段来讲解）。Milvus 本身由其作者以 **Apache-2.0** 许可发布。

> **进度：** **已完成** —— 全部 **11 个部分 / 50 课**均已构建并通过校验。本指南按里程碑分部分构建，
> 路线图见 `docs/superpowers/plans/`。

每一课都自成一体、内嵌中英双语（页内可切换），用手绘图、worked-example 追踪图、真实（标注来源的）
代码和一段自测题来讲清一个概念。

**十一个部分**（沿数据生命周期层层递进）：① 宏观全景（L01-03）② 前置基础（L04-08）
③ 分布式架构（L09-14）④ 写入链路（L15-20）⑤ 索引（L21-24）⑥ 查询链路（L25-30）
⑦ 流式系统（L31-33）⑧ C++ 内核（L34-37）⑨ API·工具·运维（L38-41）⑩ 实战与贡献（L42-46）
⑪ 进阶专题·选读（L47-50）。

**怎么看：** 在线版见 **https://verdenmax.github.io/milvus-visual-guide/**；本地零依赖，
`cd src && python3 build.py` 后用浏览器打开 `index.html`。

**怎么打印：** `cd src && python3 build_print.py`，再打开 `print_zh.html`（中文）或
`print_en.html`（英文），用 `Ctrl/Cmd+P` 导出 PDF，每课自动分页。

**许可：** 双许可 —— 代码（`src/` 下的 Python 生成器与校验脚本）用 MIT（见 LICENSE），
教学内容（课程文字与图）用 CC BY 4.0（见 LICENSE-CONTENT）。
