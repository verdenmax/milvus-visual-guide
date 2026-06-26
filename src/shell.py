"""Shared HTML shell (CSS design system + navigation) for the Milvus visual guide."""

import base64

# ---- favicon (inline SVG, base64) ----
_FAVICON_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<rect width='32' height='32' rx='7' fill='#1296db'/>"
    "<text x='16' y='22' font-family='system-ui,sans-serif' font-size='14'"
    " font-weight='800' fill='#fff' text-anchor='middle'>Mv</text></svg>"
)
FAVICON = "data:image/svg+xml;base64," + base64.b64encode(_FAVICON_SVG.encode()).decode()


def esc(s):
    """Escape plain text for an HTML text/attribute context.

    For chrome/meta strings that are NOT meant to carry inline markup (page
    titles, descriptions). Do NOT use on lesson body content or bi() inputs,
    which may legitimately contain inline tags.
    """
    return (
        str(s).replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )


def head_meta(title, description, og_type="website"):
    """SEO / social meta tags + favicon for a page <head>."""
    t = esc(title)
    d = esc(description)
    return (
        f'<meta name="description" content="{d}">\n'
        f'<meta name="theme-color" content="#1296db">\n'
        f'<link rel="icon" type="image/svg+xml" href="{FAVICON}">\n'
        f'<meta property="og:type" content="{og_type}">\n'
        f'<meta property="og:site_name" content="Milvus 图解教程">\n'
        f'<meta property="og:title" content="{t}">\n'
        f'<meta property="og:description" content="{d}">\n'
        f'<meta name="twitter:card" content="summary">\n'
        f'<meta name="twitter:title" content="{t}">\n'
        f'<meta name="twitter:description" content="{d}">'
    )


# Ordered list of all pages:
# (filename, title_zh, title_en, part_zh, part_en)
# Grows one Part per milestone; M0 ships only L01 to prove the pipeline.
PAGES = [
    ("01-what-is-milvus.html", "Milvus 是什么", "What is Milvus",
     "第一部分 · 宏观全景", "Part 1 · The Big Picture"),
    ("02-project-map.html", "项目全景地图", "The project map",
     "第一部分 · 宏观全景", "Part 1 · The Big Picture"),
    ("03-life-of-a-request.html", "一次请求的一生", "Life of a request",
     "第一部分 · 宏观全景", "Part 1 · The Big Picture"),
    ("04-embeddings-and-similarity.html", "向量与相似度", "Embeddings & similarity",
     "第二部分 · 前置基础", "Part 2 · Foundations"),
    ("05-ann-algorithms.html", "ANN 算法直觉", "ANN algorithms, intuitively",
     "第二部分 · 前置基础", "Part 2 · Foundations"),
    ("06-data-model.html", "数据模型", "The data model",
     "第二部分 · 前置基础", "Part 2 · Foundations"),
    ("07-segments.html", "Segment 与日志即数据", "Segments & log-as-data",
     "第二部分 · 前置基础", "Part 2 · Foundations"),
    ("08-dependencies-and-deployment.html", "依赖与部署形态", "Dependencies & deployment",
     "第二部分 · 前置基础", "Part 2 · Foundations"),
    ("09-control-vs-data-plane.html", "控制面 vs 数据面", "Control plane vs data plane",
     "第三部分 · 分布式架构", "Part 3 · Distributed architecture"),
    ("10-proxy.html", "Proxy 网关", "The Proxy gateway",
     "第三部分 · 分布式架构", "Part 3 · Distributed architecture"),
    ("11-rootcoord.html", "RootCoord", "RootCoord",
     "第三部分 · 分布式架构", "Part 3 · Distributed architecture"),
    ("12-datacoord.html", "DataCoord", "DataCoord",
     "第三部分 · 分布式架构", "Part 3 · Distributed architecture"),
    ("13-querycoord.html", "QueryCoordV2", "QueryCoordV2",
     "第三部分 · 分布式架构", "Part 3 · Distributed architecture"),
    ("14-metadata-and-coordination.html", "元数据与协调", "Metadata & coordination",
     "第三部分 · 分布式架构", "Part 3 · Distributed architecture"),
    ("15-insert-via-proxy.html", "经 Proxy 的插入", "Insert via Proxy",
     "第四部分 · 写入链路", "Part 4 · The write path"),
    ("16-streaming-and-wal.html", "流式系统与 WAL", "Streaming & WAL",
     "第四部分 · 写入链路", "Part 4 · The write path"),
    ("17-datanode-and-flush.html", "DataNode 与 flush", "DataNode & flush",
     "第四部分 · 写入链路", "Part 4 · The write path"),
    ("18-binlog-and-storage.html", "Binlog 与存储格式", "Binlog & storage format",
     "第四部分 · 写入链路", "Part 4 · The write path"),
    ("19-compaction-and-gc.html", "Compaction 与 GC", "Compaction & GC",
     "第四部分 · 写入链路", "Part 4 · The write path"),
    ("20-delete-and-upsert.html", "删除与 Upsert", "Delete & upsert",
     "第四部分 · 写入链路", "Part 4 · The write path"),
    ("21-index-service.html", "索引服务", "The index service",
     "第五部分 · 索引", "Part 5 · Indexing"),
    ("22-knowhere.html", "Knowhere 向量索引", "Knowhere vector indexes",
     "第五部分 · 索引", "Part 5 · Indexing"),
    ("23-index-build-and-load.html", "构建与加载索引", "Index build & load",
     "第五部分 · 索引", "Part 5 · Indexing"),
    ("24-scalar-and-fulltext.html", "标量与全文索引", "Scalar & full-text",
     "第五部分 · 索引", "Part 5 · Indexing"),
    ("25-search-via-proxy.html", "经 Proxy 的搜索", "Search via Proxy",
     "第六部分 · 查询链路", "Part 6 · The query path"),
    ("26-querynode-and-delegator.html", "QueryNode 与 delegator", "QueryNode & the delegator",
     "第六部分 · 查询链路", "Part 6 · The query path"),
    ("27-segcore.html", "Segcore（C++）", "Segcore (C++)",
     "第六部分 · 查询链路", "Part 6 · The query path"),
    ("28-execution-engine.html", "执行引擎", "The execution engine",
     "第六部分 · 查询链路", "Part 6 · The query path"),
    ("29-reduce.html", "Reduce 与结果归并", "Reduce & result assembly",
     "第六部分 · 查询链路", "Part 6 · The query path"),
    ("30-consistency-and-timestamps.html", "一致性与时间戳", "Consistency & timestamps",
     "第六部分 · 查询链路", "Part 6 · The query path"),
    ("31-wal-architecture.html", "WAL 架构", "WAL architecture",
     "第七部分 · 流式系统", "Part 7 · Streaming system"),
    ("32-ddl-dcl-via-log.html", "通过日志的 DDL/DCL", "DDL/DCL through the log",
     "第七部分 · 流式系统", "Part 7 · Streaming system"),
    ("33-replication-and-cdc.html", "复制与 CDC", "Replication & CDC",
     "第七部分 · 流式系统", "Part 7 · Streaming system"),
    ("34-core-layout.html", "core 布局", "The C++ core layout",
     "第八部分 · C++ 内核", "Part 8 · C++ core internals"),
    ("35-mmap-and-chunks.html", "mmap 与列式分块", "mmap & chunked columns",
     "第八部分 · C++ 内核", "Part 8 · C++ core internals"),
    ("36-expr-and-exec.html", "表达式与向量化执行", "Expressions & vectorized execution",
     "第八部分 · C++ 内核", "Part 8 · C++ core internals"),
    ("37-gpu-acceleration.html", "GPU 加速", "GPU acceleration",
     "第八部分 · C++ 内核", "Part 8 · C++ core internals"),
    ("38-api-and-sdks.html", "API 与多语言 SDK", "API & multi-language SDKs",
     "第九部分 · API、工具与运维", "Part 9 · API, tools & ops"),
    ("39-observability.html", "可观测性：日志/指标/追踪", "Observability: logs/metrics/traces",
     "第九部分 · API、工具与运维", "Part 9 · API, tools & ops"),
    ("40-configuration.html", "配置：paramtable 与 milvus.yaml", "Configuration: paramtable & milvus.yaml",
     "第九部分 · API、工具与运维", "Part 9 · API, tools & ops"),
    ("41-deployment.html", "部署与运维", "Deployment & operations",
     "第九部分 · API、工具与运维", "Part 9 · API, tools & ops"),
    ("42-build-and-run.html", "构建与运行", "Build & run",
     "第十部分 · 实践与贡献", "Part 10 · Practice & contributing"),
    ("43-testing.html", "测试", "Testing",
     "第十部分 · 实践与贡献", "Part 10 · Practice & contributing"),
    ("44-code-conventions.html", "代码约定", "Code conventions",
     "第十部分 · 实践与贡献", "Part 10 · Practice & contributing"),
    ("45-contributing-prs.html", "提交 PR 与贡献", "Submitting PRs & contributing",
     "第十部分 · 实践与贡献", "Part 10 · Practice & contributing"),
    ("46-glossary.html", "术语表", "Glossary",
     "第十部分 · 实践与贡献", "Part 10 · Practice & contributing"),
    ("47-bulk-import.html", "批量导入：第二条写入路径", "Bulk import: the second write path",
     "第十一部分 · 进阶专题（选读）", "Part 11 · Advanced topics (optional)"),
    ("48-hybrid-search-rerank.html", "混合检索与重排", "Hybrid search & reranking",
     "第十一部分 · 进阶专题（选读）", "Part 11 · Advanced topics (optional)"),
    ("49-quota-and-rate-limiting.html", "配额、限流与背压", "Quota, rate-limiting & backpressure",
     "第十一部分 · 进阶专题（选读）", "Part 11 · Advanced topics (optional)"),
    ("50-advanced-features-tour.html", "进阶特性巡礼", "Advanced features tour",
     "第十一部分 · 进阶专题（选读）", "Part 11 · Advanced topics (optional)"),
    ("51-design-log-as-data.html", "日志即数据：为什么整个系统都围着 WAL 转", "Log as data: why the whole system orbits the WAL",
     "第十二部分 · 设计专题（综合）", "Part 12 · Design themes (synthesis)"),
    ("52-design-query-while-write.html", "边写边查还保证正确：一致性是怎么炼成的", "Query-while-you-write, correctly: how consistency is forged",
     "第十二部分 · 设计专题（综合）", "Part 12 · Design themes (synthesis)"),
    ("53-design-storage-compute-separation.html", "存算分离：为什么节点可以是“无状态”的", "Storage–compute separation: why nodes can be stateless",
     "第十二部分 · 设计专题（综合）", "Part 12 · Design themes (synthesis)"),
    ("54-design-scale-to-billions.html", "扩展到十亿级：分而治之的艺术", "Scaling to billions: the art of divide-and-conquer",
     "第十二部分 · 设计专题（综合）", "Part 12 · Design themes (synthesis)"),
    ("55-design-two-languages.html", "两种语言，一套系统：C++ 内核与 Go 编排的分工", "Two languages, one system: the C++ kernel / Go orchestration split",
     "第十二部分 · 设计专题（综合）", "Part 12 · Design themes (synthesis)"),
    ("56-design-failure-as-default.html", "故障是常态：系统如何自愈", "Failure as the default: how the system heals itself",
     "第十二部分 · 设计专题（综合）", "Part 12 · Design themes (synthesis)"),
    ("57-capstone-life-of-a-row.html", "终章 · 一条数据的一生：从写入到被搜到", "Capstone · Life of a row: from write to searchable",
     "第十三部分 · 终章", "Part 13 · Capstone"),
]


def bi(zh, en):
    """Inline bilingual pair; only the active language is shown (CSS-controlled)."""
    return f'<span class="lang-zh">{zh}</span><span class="lang-en">{en}</span>'


INDEX_FILE = "index.html"

CSS = r"""
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #f6f7f9; --panel: #ffffff; --panel-2: #f0f2f5; --ink: #1d2129;
  --muted: #5b6470; --faint: #8a939f; --line: #e1e5ea;
  --accent: #1296db; --accent-soft: #e2f2fb; --accent-ink: #0b6699;
  --blue: #2563eb; --blue-soft: #e7efff; --amber: #b4690e; --amber-soft: #fdf1dd;
  --purple: #7c3aed; --purple-soft: #f0e9ff; --red: #d23f3f; --red-soft: #fbe6e6;
  --teal: #0d9488; --teal-soft: #d7f3ef;
  --code-bg: #0f172a; --code-ink: #e2e8f0; --code-line: #1e293b;
  --shadow: 0 1px 2px rgba(16,24,40,.06), 0 8px 24px rgba(16,24,40,.06);
  --radius: 14px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0e1116; --panel: #161b22; --panel-2: #1c232c; --ink: #e6edf3;
    --muted: #9aa6b2; --faint: #6e7a86; --line: #2a323c;
    --accent: #4cb8ec; --accent-soft: #0e2c3e; --accent-ink: #8fd3f4;
    --blue: #6ea8fe; --blue-soft: #16243f; --amber: #e0a44a; --amber-soft: #33270f;
    --purple: #b794f6; --purple-soft: #271a40; --red: #f08080; --red-soft: #3a1a1a;
    --teal: #5ed0c4; --teal-soft: #0d2e2a;
    --code-bg: #0a0f1a; --code-ink: #d8e2f0; --code-line: #14202f;
    --shadow: 0 1px 2px rgba(0,0,0,.4), 0 10px 30px rgba(0,0,0,.35);
  }
}
html { scroll-behavior: smooth; overflow-x: hidden; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC",
    "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  background: var(--bg); color: var(--ink); line-height: 1.7;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--accent); text-decoration: none; }
code, .mono { font-family: "SF Mono", "JetBrains Mono", "Fira Code", ui-monospace, Menlo, Consolas, monospace; overflow-wrap: break-word; }

/* ---- top progress bar ---- */
.topbar {
  position: sticky; top: 0; z-index: 50; background: var(--panel);
  border-bottom: 1px solid var(--line); backdrop-filter: blur(8px);
}
.topbar-inner {
  max-width: 960px; margin: 0 auto; padding: .7rem 1.25rem;
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
}
.topbar .home { font-size: .82rem; color: var(--muted); font-weight: 600; display:flex; gap:.5rem; align-items:center; }
.topbar .home b { color: var(--accent); }
.topbar .pill { font-size: .72rem; color: var(--muted); background: var(--panel-2);
  padding: .2rem .6rem; border-radius: 999px; border: 1px solid var(--line); white-space: nowrap; }
.progress { height: 3px; background: var(--panel-2); }
.progress > span { display: block; height: 100%; background: linear-gradient(90deg, var(--accent), var(--purple)); }

.wrap { max-width: 820px; margin: 0 auto; padding: 2.4rem 1.25rem 5rem; }

/* ---- hero ---- */
.hero { margin-bottom: 2rem; }
.hero .part { font-size: .76rem; letter-spacing: .08em; text-transform: uppercase;
  color: var(--accent); font-weight: 700; margin-bottom: .55rem; }
.hero h1 { font-size: 2.05rem; line-height: 1.2; letter-spacing: -.01em; font-weight: 750; }
.hero .lead { margin-top: .9rem; font-size: 1.06rem; color: var(--muted); }

h2 { font-size: 1.32rem; margin: 2.4rem 0 .9rem; letter-spacing: -.01em;
  display: flex; align-items: center; gap: .55rem; }
h2::before { content: ""; width: 4px; height: 1.05em; background: var(--accent); border-radius: 3px; display: inline-block; }
h3 { font-size: 1.05rem; margin: 1.4rem 0 .5rem; }
p { margin: .7rem 0; }
ul, ol { margin: .6rem 0 .6rem 1.3rem; }
li { margin: .3rem 0; }
strong { color: var(--ink); font-weight: 680; }
.inline { background: var(--panel-2); border: 1px solid var(--line); border-radius: 6px;
  padding: .08em .4em; font-size: .9em; color: var(--accent-ink); }

/* ---- callout cards ---- */
.card { border-radius: var(--radius); padding: 1.05rem 1.2rem; margin: 1.2rem 0;
  border: 1px solid var(--line); background: var(--panel); box-shadow: var(--shadow); }
.card .tag { font-size: .72rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase;
  display: inline-flex; align-items: center; gap: .4rem; margin-bottom: .5rem; }
.card.macro { border-left: 4px solid var(--blue); }
.card.macro .tag { color: var(--blue); }
.card.detail { border-left: 4px solid var(--purple); }
.card.detail .tag { color: var(--purple); }
.card.analogy { border-left: 4px solid var(--amber); background: var(--amber-soft); }
.card.analogy .tag { color: var(--amber); }
.card.key { border-left: 4px solid var(--accent); background: var(--accent-soft); }
.card.key .tag { color: var(--accent-ink); }
.card.warn { border-left: 4px solid var(--red); background: var(--red-soft); }
.card.warn .tag { color: var(--red); }
.card.spark { border-left: 4px solid #e0a000;
  background: linear-gradient(100deg, rgba(224,160,0,.12), transparent 70%); }
.card.spark .tag { color: #c98a00; }
@media (prefers-color-scheme: dark) { .card.spark .tag { color: #f0c050; } }

/* ---- code file callout ---- */
.codefile { margin: 1.2rem 0; border-radius: 12px; overflow: hidden; border: 1px solid var(--line);
  box-shadow: var(--shadow); }
.codefile .cf-head { display: flex; align-items: center; gap: .55rem; padding: .5rem .85rem;
  background: var(--panel-2); border-bottom: 1px solid var(--line); font-size: .8rem; }
.codefile .cf-head .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--accent); flex-shrink:0; }
.codefile .cf-head .path { font-family: ui-monospace, monospace; color: var(--ink); font-weight: 600; }
.codefile .cf-head .ln { margin-left: auto; color: var(--faint); font-size: .72rem; }
.codefile pre { background: var(--code-bg); color: var(--code-ink); padding: .9rem 1rem;
  overflow-x: auto; font-size: .82rem; line-height: 1.6; }
.codefile pre .cm { color: #7d8aa3; }
.codefile pre .kw { color: #c792ea; }
.codefile pre .fn { color: #82aaff; }
.codefile pre .st { color: #c3e88d; }
.codefile pre .nb { color: #f78c6c; }

pre.code { background: var(--code-bg); color: var(--code-ink); padding: .9rem 1rem; border-radius: 12px;
  overflow-x: auto; font-size: .83rem; line-height: 1.6; margin: 1.1rem 0; box-shadow: var(--shadow); }
pre.code .cm { color: #7d8aa3; } pre.code .kw { color: #c792ea; }
pre.code .fn { color: #82aaff; } pre.code .st { color: #c3e88d; } pre.code .nb { color: #f78c6c; }

/* ---- collapsible accordion (details/summary) ---- */
.accordion { border: 1px solid var(--line); border-radius: 12px; background: var(--panel);
  margin: .7rem 0; box-shadow: var(--shadow); overflow: hidden; }
.accordion > summary { cursor: pointer; padding: .85rem 1.1rem; font-weight: 650; font-size: .96rem;
  list-style: none; display: flex; align-items: center; gap: .6rem; user-select: none; }
.accordion > summary::-webkit-details-marker { display: none; }
.accordion > summary::after { content: "▶"; font-size: .68rem; color: var(--accent);
  margin-left: auto; transition: transform .15s ease; }
.accordion[open] > summary::after { transform: rotate(90deg); }
.accordion > summary:hover { background: var(--panel-2); }
.accordion[open] > summary { border-bottom: 1px solid var(--line); }
.accordion .badge-num { background: var(--accent-soft); color: var(--accent-ink);
  width: 1.6rem; height: 1.6rem; border-radius: 7px; display: inline-flex; align-items: center;
  justify-content: center; font-size: .82rem; font-weight: 700; flex-shrink: 0; }
.accordion .hint { font-size: .72rem; color: var(--faint); font-weight: 400; }
.acc-body { padding: .9rem 1.1rem 1.1rem; }
.acc-intro { color: var(--muted); font-size: .9rem; margin: .2rem 0 .4rem; }
.qa { margin: 1rem 0; }
.qa:first-child { margin-top: .3rem; }
.qa .q { font-weight: 680; font-size: .9rem; display: flex; gap: .45rem; align-items: center; margin-bottom: .3rem; }
.qa .a { color: var(--muted); font-size: .9rem; }
.qa .a strong { color: var(--ink); }
.qa pre.code { margin: .5rem 0 0; font-size: .78rem; }

/* ---- flow diagram ---- */
.flow { display: flex; align-items: stretch; gap: 0; flex-wrap: wrap; margin: 1.3rem 0;
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 1.2rem 1rem; box-shadow: var(--shadow); }
.flow .node { flex: 1 1 0; min-width: 110px; text-align: center; padding: .7rem .5rem;
  border-radius: 10px; background: var(--panel-2); border: 1px solid var(--line); }
.flow .node .nt { font-weight: 700; font-size: .92rem; }
.flow .node .nd { font-size: .76rem; color: var(--muted); margin-top: .2rem; }
.flow .node.hl { background: var(--accent-soft); border-color: var(--accent); }
.flow .arrow { align-self: center; color: var(--faint); font-size: 1.3rem; padding: 0 .35rem; }

/* vertical flow */
.vflow { margin: 1.3rem 0; }
.vflow .step { display: flex; gap: .9rem; position: relative; padding-bottom: 1.1rem; }
.vflow .step:not(:last-child)::before { content:""; position:absolute; left: 15px; top: 34px; bottom: -2px;
  width: 2px; background: var(--line); }
.vflow .num { width: 32px; height: 32px; border-radius: 50%; background: var(--accent); color: #fff;
  display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: .85rem; flex-shrink: 0; z-index:1; }
.vflow .sc h4 { margin: .25rem 0 .2rem; font-size: 1rem; }
.vflow .sc p { margin: .15rem 0; font-size: .92rem; color: var(--muted); }
.vflow .sc .mono { font-size: .8rem; color: var(--accent-ink); }

/* layered architecture */
.layers { margin: 1.3rem 0; display: flex; flex-direction: column; gap: .55rem; }
.layer { border-radius: 12px; padding: .85rem 1.1rem; border: 1px solid var(--line); background: var(--panel);
  box-shadow: var(--shadow); }
.layer .lh { display: flex; align-items: center; gap: .6rem; }
.layer .lh .badge { font-size: .7rem; font-weight: 700; padding: .12rem .5rem; border-radius: 999px; }
.layer .lh .name { font-weight: 700; font-family: ui-monospace, monospace; }
.layer .ld { font-size: .85rem; color: var(--muted); margin-top: .35rem; }
.layer.l-core { border-left: 4px solid var(--accent); } .layer.l-core .badge { background: var(--accent-soft); color: var(--accent-ink); }
.layer.l-main { border-left: 4px solid var(--blue); } .layer.l-main .badge { background: var(--blue-soft); color: var(--blue); }
.layer.l-part { border-left: 4px solid var(--purple); } .layer.l-part .badge { background: var(--purple-soft); color: var(--purple); }
.layer.l-app { border-left: 4px solid var(--amber); } .layer.l-app .badge { background: var(--amber-soft); color: var(--amber); }

/* two-column compare */
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1.2rem 0; }
@media (max-width: 640px) { .cols { grid-template-columns: 1fr; } }
.col { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 1rem 1.1rem; box-shadow: var(--shadow); min-width: 0; }
.col h4 { margin: 0 0 .4rem; font-size: .95rem; }

table.t { width: 100%; border-collapse: collapse; margin: 1.1rem 0; font-size: .9rem;
  background: var(--panel); border-radius: 12px; overflow: hidden; box-shadow: var(--shadow); }
table.t th, table.t td { padding: .6rem .8rem; text-align: left; border-bottom: 1px solid var(--line); }
table.t th { background: var(--panel-2); font-size: .8rem; letter-spacing: .02em; }
table.t tr:last-child td { border-bottom: none; }
table.t td.mono, table.t td .mono { font-family: ui-monospace, monospace; font-size: .82rem; color: var(--accent-ink); }
@media (max-width: 640px) {
  /* Wide multi-column tables: scroll within their own box instead of
     forcing page-level horizontal overflow (which clipped right columns). */
  table.t { display: block; overflow-x: auto; -webkit-overflow-scrolling: touch; }
  table.t th, table.t td { padding: .5rem .6rem; }
}
.selftest { margin: 2.2rem 0 0; border-top: 2px dashed var(--line); padding-top: 1.2rem; }
.selftest > h2 { margin-top: .2rem; }
.quiz { background: var(--panel); border: 1px solid var(--line); border-left: 4px solid var(--blue);
  border-radius: 12px; padding: .9rem 1.1rem; margin: 1rem 0; box-shadow: var(--shadow); }
.quiz .qn { font-weight: 650; }
.quiz ol.opts { list-style: upper-alpha; margin: .55rem 0 .6rem 1.5rem; padding: 0; }
.quiz ol.opts li { margin: .3rem 0; padding-left: .15rem; }
.quiz details.accordion { margin: .5rem 0 0; }
.selftest code { font-family: ui-monospace, monospace; font-size: .9em; color: var(--accent-ink);
  background: var(--accent-soft); padding: 0 .28em; border-radius: 4px; }

/* footer nav */
.footnav { display: flex; justify-content: space-between; gap: 1rem; margin-top: 3rem;
  padding-top: 1.4rem; border-top: 1px solid var(--line); }
.footnav a { flex: 1; padding: .85rem 1.1rem; border-radius: 12px; border: 1px solid var(--line);
  background: var(--panel); box-shadow: var(--shadow); transition: .15s; }
.footnav a:hover { border-color: var(--accent); transform: translateY(-1px); }
.footnav a.next { text-align: right; }
.footnav .dir { font-size: .72rem; color: var(--faint); text-transform: uppercase; letter-spacing: .05em; }
.footnav .ttl { font-weight: 700; color: var(--ink); margin-top: .15rem; }
.footnav a.disabled { opacity: .35; pointer-events: none; }

/* index page */
.toc { display: grid; gap: .7rem; margin-top: 1.6rem; }
.toc-part { font-size: .78rem; font-weight: 700; letter-spacing: .05em; text-transform: uppercase;
  color: var(--accent); margin: 1.4rem 0 .2rem; }
.toc a { display: flex; align-items: center; gap: .9rem; padding: .85rem 1.05rem; border-radius: 12px;
  background: var(--panel); border: 1px solid var(--line); box-shadow: var(--shadow); transition: .15s; }
.toc a:hover { border-color: var(--accent); transform: translateX(3px); }
.toc .n { width: 30px; height: 30px; border-radius: 8px; background: var(--accent-soft); color: var(--accent-ink);
  display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: .85rem; flex-shrink: 0; }
.toc .tt { font-weight: 650; color: var(--ink); }
.toc .ts { font-size: .8rem; color: var(--muted); margin-left: auto; text-align: right; }
.toc-search { position: relative; margin: 1.6rem 0 -.4rem; }
.toc-search input { width: 100%; box-sizing: border-box; padding: .75rem 2.8rem .75rem 1rem;
  border-radius: 12px; border: 1px solid var(--line); background: var(--panel); color: var(--ink);
  font-size: .98rem; box-shadow: var(--shadow); }
.toc-search input:focus { outline: none; border-color: var(--accent); }
.toc-search .qcount { position: absolute; right: 1rem; top: 50%; transform: translateY(-50%);
  color: var(--faint); font-size: .8rem; pointer-events: none; }
.toc a.hide, .toc .toc-part.hide { display: none; }
.t tr.hide { display: none; }
.toc-empty { display: none; color: var(--muted); padding: 1rem; text-align: center; }
.toc-empty.show { display: block; }
.hero.index h1 { font-size: 2.3rem; }
.legend { display:flex; gap:1.2rem; flex-wrap:wrap; margin-top:1rem; font-size:.8rem; color:var(--muted); }
.legend span { display:flex; align-items:center; gap:.4rem; }
.legend i { width:12px; height:12px; border-radius:3px; display:inline-block; }
.pdf-btn { display:inline-flex; align-items:center; gap:.4rem; padding:.55rem 1.1rem;
  background:var(--accent); color:#fff; border-radius:10px; font-size:.9rem; font-weight:650;
  box-shadow:var(--shadow); transition:.15s; }
.pdf-btn:hover { background:var(--accent-ink); transform:translateY(-1px); }

/* ---- bilingual language switch ----
   Contract: <html> must carry data-lang="zh" (default) or "en".
   page()/index_page() hard-code data-lang="zh"; LANG_BOOT may switch to "en". */
html[data-lang="en"] .lang-zh { display: none !important; }
html[data-lang="zh"] .lang-en { display: none !important; }
.langtoggle { font-size:.72rem; font-weight:700; color:var(--accent-ink);
  background:var(--accent-soft); border:1px solid var(--accent); border-radius:999px;
  padding:.22rem .7rem; cursor:pointer; line-height:1.4; white-space:nowrap; }
.langtoggle:hover { background:var(--accent); color:#fff; }

/* ---- schematic: cell strips (vector rows / quant blocks / KV columns) ---- */
.cellgroup { margin: 1.2rem 0; background: var(--panel); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 1rem 1.1rem; box-shadow: var(--shadow); }
.cellgroup .cg-cap { font-size: .82rem; color: var(--muted); margin-bottom: .55rem; }
.cellgroup .cg-cap b { color: var(--ink); }
.cells { display: flex; flex-wrap: wrap; gap: .35rem; align-items: center; }
.cells + .cells { margin-top: .5rem; }
.cell { min-width: 2.1rem; padding: .38rem .5rem; text-align: center; border-radius: 8px;
  background: var(--panel-2); border: 1px solid var(--line); font-size: .78rem;
  font-family: ui-monospace, monospace; white-space: nowrap; }
.cell.scale { background: var(--amber-soft); border-color: var(--amber); color: var(--amber); font-weight: 700; }
.cell.hl    { background: var(--accent-soft); border-color: var(--accent); color: var(--accent-ink); font-weight: 700; }
.cell.q     { background: var(--blue-soft); border-color: var(--blue); color: var(--blue); }
.cell.dim   { opacity: .45; }
.cells .lab { font-size: .76rem; color: var(--faint); padding: 0 .35rem; }
.cells .sep { color: var(--faint); padding: 0 .1rem; }

/* ---- schematic: timeline lanes (write vs read, step-by-step) ---- */
.timeline { margin: 1.2rem 0; display: flex; flex-direction: column; gap: .5rem;
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 1rem 1.1rem; box-shadow: var(--shadow); }
.timeline .lane { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
.timeline .lane-label { min-width: 6rem; font-size: .8rem; font-weight: 700; color: var(--muted); }
.timeline .tslot { padding: .4rem .6rem; border-radius: 8px; background: var(--panel-2);
  border: 1px solid var(--line); font-size: .78rem; text-align: center; font-family: ui-monospace, monospace; }
.timeline .tslot.span { flex: 1; min-width: 8rem; background: var(--blue-soft); border-color: var(--blue);
  color: var(--blue); font-weight: 700; }
.timeline .tslot.now { background: var(--accent-soft); border-color: var(--accent); color: var(--accent-ink); font-weight: 700; }
.timeline .tl-row { display: flex; align-items: flex-start; gap: .6rem; padding: .12rem 0; }
.timeline .tl-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--accent); flex-shrink: 0; margin-top: .45rem; }
.timeline .tl-t { font-family: ui-monospace, monospace; font-weight: 700; color: var(--accent-ink); min-width: 2.4rem; font-size: .82rem; flex-shrink: 0; margin-top: .18rem; }
.timeline .tl-c { font-size: .9rem; color: var(--muted); }

/* ---- worked-example trace: one concrete input, stepped through ---- */
.trace { margin: 1.3rem 0; background: var(--panel); border: 1px solid var(--line);
  border-left: 4px solid var(--accent); border-radius: var(--radius); padding: 1rem 1.1rem; box-shadow: var(--shadow); }
.trace .tcap { font-size: .82rem; color: var(--muted); margin-bottom: .7rem; }
.trace .tcap b { color: var(--accent-ink); }
.trace .stations { display: flex; align-items: stretch; gap: 0; flex-wrap: wrap; }
.trace .stn { flex: 1 1 0; min-width: 116px; border: 1px solid var(--line); border-radius: 10px;
  padding: .55rem; background: var(--bg); }
.trace .stn h5 { margin: 0 0 .45rem; font-size: .8rem; color: var(--ink); }
.trace .cellrow { display: flex; gap: .3rem; align-items: center; flex-wrap: wrap; }
.trace .vc { min-width: 2.1rem; padding: .32rem .45rem; text-align: center; border-radius: 7px;
  background: var(--panel-2); border: 1px solid var(--line); font: 600 .76rem ui-monospace, monospace; white-space: nowrap; }
.trace .vc.hot  { background: var(--accent-soft); border-color: var(--accent); color: var(--accent-ink); }
.trace .vc.blue { background: var(--blue-soft); border-color: var(--blue); color: var(--blue); }
.trace .vc.dim  { opacity: .42; }
.trace .tlab { font-size: .68rem; color: var(--faint); margin-top: .35rem; }
.trace .op { align-self: center; color: var(--accent); font: 700 .72rem ui-monospace, monospace;
  padding: 0 .5rem; text-align: center; white-space: nowrap; }
.trace svg { max-width: 100%; height: auto; display: block; margin: .3rem auto; }
@media (max-width: 640px) { .trace .stations { flex-direction: column; } .trace .op { padding: .3rem 0; } }
/* --- hand-drawn figure (inline SVG illustrations) --- */
.fig { margin: 1.3rem 0; background: var(--panel); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 1rem 1rem .85rem; box-shadow: var(--shadow); text-align: center; }
.fig svg { max-width: 100%; height: auto; display: block; margin: 0 auto;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", sans-serif; }
.fig svg text { fill: var(--ink); }
.fig .figcap { margin: .72rem auto 0; font-size: .8rem; color: var(--muted); line-height: 1.55; max-width: 46rem; }
.fig .figcap b { color: var(--accent-ink); font-weight: 700; }
"""

SEARCH_JS = """
(function(){
  var q=document.getElementById('q'); if(!q) return;
  var toc=document.querySelector('.toc');
  var empty=document.getElementById('tocempty');
  var count=document.getElementById('qcount');
  var links=[].slice.call(toc.querySelectorAll('a'));
  var heads=[].slice.call(toc.querySelectorAll('.toc-part'));
  links.forEach(function(a){ a.setAttribute('data-s',(a.textContent||'').toLowerCase()); });
  function run(){
    var t=(q.value||'').toLowerCase().trim(), n=0;
    links.forEach(function(a){
      var hit=!t||a.getAttribute('data-s').indexOf(t)>=0;
      a.classList.toggle('hide',!hit); if(hit)n++;
    });
    heads.forEach(function(h){
      var el=h.nextElementSibling, any=false;
      while(el && !el.classList.contains('toc-part')){
        if(el.tagName==='A' && !el.classList.contains('hide')){any=true;break;}
        el=el.nextElementSibling;
      }
      h.classList.toggle('hide',!any);
    });
    empty.classList.toggle('show', !!t && n===0);
    count.textContent = t ? String(n) : '';
  }
  q.addEventListener('input',run);
})();
"""

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

LANG_JS = """
function mvgSetLang(l){
  l=(l==='en')?'en':'zh';
  var d=document.documentElement;
  d.dataset.lang=l; d.lang=(l==='en'?'en':'zh-CN');
  try{localStorage.setItem('mvg-lang',l);}catch(e){}
}
function mvgToggleLang(){
  mvgSetLang(document.documentElement.dataset.lang==='en'?'zh':'en');
}
"""

# Runs in <head> before first paint to avoid a flash of the wrong language.
LANG_BOOT = (
    "<script>try{var l=localStorage.getItem('mvg-lang');"
    "if(l==='en'){document.documentElement.dataset.lang='en';"
    "document.documentElement.lang='en';}}catch(e){}</script>"
)


def page(filename, content, home_href="../index.html"):
    """Wrap one lesson's bilingual content in the full HTML shell.

    ``content`` is a dict ``{"zh": html, "en": html}``. Both are emitted; CSS
    shows only the active language. Navigation uses plain relative ``href``
    links so the site works via file:// and any static server (lessons share
    one directory; home defaults to ``../index.html``).
    """
    idx = next(i for i, p in enumerate(PAGES) if p[0] == filename)
    fname, title_zh, title_en, part_zh, part_en = PAGES[idx]
    total = len(PAGES)
    pct = int((idx + 1) / total * 100)
    home = home_href

    if idx > 0:
        p = PAGES[idx - 1]
        prev_link = (
            f'<a class="prev" href="{p[0]}"><div class="dir">{bi("← 上一课", "← Prev")}</div>'
            f'<div class="ttl">{bi(esc(p[1]), esc(p[2]))}</div></a>'
        )
    else:
        prev_link = (
            f'<a class="prev" href="{home}"><div class="dir">{bi("← 返回", "← Back")}</div>'
            f'<div class="ttl">{bi("目录", "Contents")}</div></a>'
        )
    if idx + 1 < total:
        p = PAGES[idx + 1]
        next_link = (
            f'<a class="next" href="{p[0]}"><div class="dir">{bi("下一课 →", "Next →")}</div>'
            f'<div class="ttl">{bi(esc(p[1]), esc(p[2]))}</div></a>'
        )
    else:
        next_link = (
            f'<a class="next" href="{home}"><div class="dir">{bi("完成 →", "Done →")}</div>'
            f'<div class="ttl">{bi("返回目录", "Back to index")}</div></a>'
        )

    title_tag = f"{idx+1:02d} · {title_zh} / {title_en} - Milvus 图解教程"
    desc = f"{part_zh}｜{title_zh} - Milvus 图解教程（中英双语，配真实源码对应、折叠深挖与设计亮点）"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN" data-lang="zh"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{LANG_BOOT}
<title>{esc(title_tag)}</title>
{head_meta(title_tag, desc, og_type="article")}
<style>{CSS}</style>
</head><body>
<div class="topbar">
  <div class="topbar-inner">
    <a class="home" href="{home}">🐦 <b class="lang-zh">Milvus 图解教程</b><b class="lang-en">Milvus Visual Guide</b></a>
    <span class="pill">{bi(esc(part_zh), esc(part_en))}</span>
    <span class="pill">{idx+1:02d} / {total:02d}</span>
    <button class="langtoggle" onclick="mvgToggleLang()" aria-label="switch language"><span class="lang-zh">EN</span><span class="lang-en">中</span></button>
  </div>
  <div class="progress"><span style="width:{pct}%"></span></div>
</div>
<div class="wrap">
  <div class="hero">
    <div class="part">{bi(esc(part_zh), esc(part_en))}</div>
    <h1><span class="lang-zh">{esc(title_zh)}</span><span class="lang-en">{esc(title_en)}</span></h1>
  </div>
  <div class="lang-zh">{content["zh"]}</div>
  <div class="lang-en">{content["en"]}</div>
  <div class="footnav">{prev_link}{next_link}</div>
</div>
<script>{LANG_JS}</script>
</body></html>"""
    return html


# Per-lesson TOC subtitle: filename -> (zh, en). Missing entries render blank.
# Grows one Part per milestone alongside PAGES.
SUBTITLES = {
    "01-what-is-milvus.html": ("向量数据库 · ANN 检索 · 为何要分布式",
                               "vector DB; ANN search; why distributed"),
    "02-project-map.html": ("三语言分工 · 运行时组件 · 仓库布局 · 四组导航",
                            "three languages; runtime components; repo layout; four-group nav"),
    "03-life-of-a-request.html": ("insert 与 search 全链路 · 时间戳的角色",
                                  "the insert & search paths; the role of timestamps"),
    "04-embeddings-and-similarity.html": ("向量 · L2/IP/COSINE · 归一化 · ANN 问题",
                                          "embeddings; L2/IP/COSINE; normalization; the ANN problem"),
    "05-ann-algorithms.html": ("FLAT/IVF/HNSW/PQ/DiskANN · 速度↔内存↔召回 · 关键参数",
                               "FLAT/IVF/HNSW/PQ/DiskANN; speed↔memory↔recall; key params"),
    "06-data-model.html": ("collection/schema/field · 主键/动态字段 · 分区键 · 数据类型",
                           "collection/schema/field; primary key/dynamic field; partition key; data types"),
    "07-segments.html": ("段的生命周期 · vchannel→pchannel · 日志即数据 · 列式布局",
                         "segment lifecycle; vchannel→pchannel; log-as-data; columnar layout"),
    "08-dependencies-and-deployment.html": ("etcd · 对象存储 · 消息队列 · Lite/Standalone/Cluster",
                                            "etcd; object storage; message queue; Lite/Standalone/Cluster"),
    "09-control-vs-data-plane.html": ("协调者 vs 节点 · types.go 接口 · MixCoord · 服务发现",
                                      "coordinators vs nodes; types.go interfaces; MixCoord; service discovery"),
    "10-proxy.html": ("唯一入口 · 校验/鉴权/限流 · ddQueue/dmQueue/dqQueue · 扇出归并",
                      "single entry; validate/auth/rate-limit; ddQueue/dmQueue/dqQueue; fan-out & reduce"),
    "11-rootcoord.html": ("DDL · 元数据表 · TSO 时间戳 · 全局 ID 分配",
                          "DDL; meta table; TSO timestamps; global ID allocation"),
    "12-datacoord.html": ("段分配 · flush/compaction · GC · 索引构建调度",
                          "segment allocation; flush/compaction; GC; index-build scheduling"),
    "13-querycoord.html": ("加载/释放 · 段与分片分配 · 均衡 · 副本 · distribution↔target",
                           "load/release; segment & shard assignment; balance; replicas; distribution↔target"),
    "14-metadata-and-coordination.html": ("etcd · session 服务发现 · Catalog · kv 层 · watch 派活",
                                          "etcd; session discovery; Catalog; kv layer; watch-driven assignment"),
    "15-insert-via-proxy.html": ("校验定主键 · 按主键哈希到 vchannel · 打包消息 · Append 进 WAL · 原子批",
                                 "validate & settle PK; hash by PK to vchannels; pack messages; Append to WAL; atomic batch"),
    "16-streaming-and-wal.html": ("WAL 单一事实来源 · 消息与 TimeTick · PChannel/VChannel/CChannel · StreamingClient · 日志即数据",
                                  "WAL single source of truth; message & TimeTick; PChannel/VChannel/CChannel; StreamingClient; log as data"),
    "17-datanode-and-flush.html": ("growing 段 · flush 触发 · binlog 落对象存储 · StreamingNode vs DataNode · growing/sealed 相变",
                                   "growing segment; flush triggers; binlogs to object storage; StreamingNode vs DataNode; growing/sealed transition"),
    "18-binlog-and-storage.html": ("insert/delete/stats binlog 与索引文件 · 列式布局 · 对象存储路径布局 · internal/storage 序列化 · storagev2",
                                   "insert/delete/stats binlogs & index files; columnar layout; object-storage path layout; internal/storage serialization; storagev2"),
    "19-compaction-and-gc.html": ("compaction 合并碎段·应用 L0 墓碑 · Mix/Merge/Clustering/Sort/Level0 类型 · DataCoord 调度·datanode 执行 · GC 按 TTL 清孤儿",
                                  "compaction merges fragments & applies L0 tombstones; Mix/Merge/Clustering/Sort/Level0 types; DataCoord schedules, datanode executes; GC reclaims orphans past TTL"),
    "20-delete-and-upsert.html": ("删除即墓碑·进 WAL·沉淀 L0 deltalog · 布隆过滤器路由删除 · upsert = 删除 + 插入 · 按时间戳的 MVCC 可见性",
                                  "delete as tombstone; into WAL; settle as L0 deltalog; bloom filters route deletes; upsert = delete + insert; timestamp-based MVCC visibility"),
    "21-index-service.html": ("DataCoord 调度索引构建·worker 执行（无 indexnode 进程） · CreateIndex → 每个 sealed 段一个构建任务 → 索引文件 → 可加载 · auto-index 自动选型",
                              "DataCoord schedules index build, a worker executes it (no indexnode process); CreateIndex → one build task per sealed segment → index files → loadable; auto-index picks the type"),
    "22-knowhere.html": ("向量索引由 Knowhere 提供：FLAT/IVF_FLAT/SQ8/PQ·HNSW·DiskANN·SCANN·GPU CAGRA·稀疏 · nlist/nprobe 与 M/ef 取舍 · metric 必须与字段匹配",
                         "vector indexes come from Knowhere: FLAT/IVF_FLAT/SQ8/PQ, HNSW, DiskANN, SCANN, GPU CAGRA, sparse; nlist/nprobe and M/ef tradeoffs; the metric must match the field"),
    "23-index-build-and-load.html": ("sealed 段 → 构建任务（worker 读 binlog·调 Knowhere）→ 索引文件落对象存储 → QueryNode 加载（mmap 或内存） · growing 段用暴力扫描 · 索引引擎版本协商",
                                     "sealed segment → build task (worker reads binlogs, calls Knowhere) → index files in object storage → QueryNode loads (mmap or memory); growing segments use brute force; index-engine version negotiation"),
    "24-scalar-and-fulltext.html": ("标量索引加速过滤：倒排/bitmap/排序/ngram/混合/JSON · 全文 BM25 由 Rust tantivy 落地 · 标量 bitset 下推给向量 ANN（先筛后搜）",
                                    "scalar indexes accelerate filtering: inverted/bitmap/sort/ngram/hybrid/JSON; full-text BM25 via Rust tantivy; scalar bitset pushed down into vector ANN (filter-then-search)"),
    "25-search-via-proxy.html": ("searchTask 三段式 · 解析→建 plan→guarantee ts · 一致性级别 · 扇出到分片 · 跨分片归并",
                                 "searchTask three stages; parse→plan→guarantee ts; consistency levels; scatter to shards; cross-shard reduce"),
    "26-querynode-and-delegator.html": ("delegator/shard leader · sealed+growing · 段分布到 worker · 扇出归并 · 消费 WAL 尾部 · tsafe",
                                        "delegator/shard leader; sealed+growing; segment distribution to workers; scatter & merge; consume WAL tail; tsafe"),
    "27-segcore.html": ("C++ 单段引擎 · cgo 边界 · SegmentInterface · sealed=索引/growing=暴力 · 段内 topK",
                        "C++ single-segment engine; cgo boundary; SegmentInterface; sealed=index/growing=brute-force; the segment's topK"),
    "28-execution-engine.html": ("表达式树(expr) · 向量化执行(exec) · 按块求 bitset · 先过滤再检索",
                                 "expression tree (expr); vectorized exec; per-chunk bitset; filter-then-search"),
    "29-reduce.html": ("三层归并：段内/节点/Proxy · 按主键去重 · 排序 · offset/limit · scatter-gather",
                       "three-level merge: segment/node/Proxy; dedup by PK; sort; offset/limit; scatter-gather"),
    "30-consistency-and-timestamps.html": ("TSO 全局时钟 · 保证时间戳 · 五种一致性级别 · MVCC · tsafe 等待",
                                           "TSO global clock; guarantee ts; five consistency levels; MVCC; tsafe wait"),
    "31-wal-architecture.html": ("StreamingCoord 调度 · StreamingNode 拦截器链 · WAL Backend · RecoveryStorage 检查点重放",
                                 "StreamingCoord scheduling; StreamingNode interceptor chain; WAL Backend; RecoveryStorage checkpoint-replay"),
    "32-ddl-dcl-via-log.html": ("DML=Append/单日志 · DDL/DCL=Broadcast/多日志 · Broadcaster 锁+ACK · 消息语义",
                                "DML=Append/one log; DDL/DCL=Broadcast/many logs; Broadcaster lock+ACK; message semantics"),
    "33-replication-and-cdc.html": ("复制日志而非状态 · 星型拓扑 · Primary→Replicator→Secondary · 容灾/跨域/迁移",
                                    "replicate the log not state; star topology; Primary→Replicator→Secondary; DR/cross-region/migration"),
    "34-core-layout.html": ("internal/core/src 子模块地图 · 控制面 Go / 计算面 C++ · cgo(*_c.h) 桥 · 查询与建索引两条路径",
                            "internal/core/src submodule map; Go control plane / C++ compute core; cgo(*_c.h) bridge; query & index-build paths"),
    "35-mmap-and-chunks.html": ("列式存储 · chunked column(ChunkedColumnInterface) · mmap 让数据大于内存 · MmapChunkManager 统一分配",
                                "columnar storage; chunked column (ChunkedColumnInterface); mmap for data larger than RAM; MmapChunkManager central allocation"),
    "36-expr-and-exec.html": ("逻辑 ITypeExpr → 物理 Expr::Eval(向量化) · Task/Driver/Operator 流水线 · FilterBitsNode/VectorSearchNode · 算子可组合",
                              "logical ITypeExpr → physical Expr::Eval (vectorized); Task/Driver/Operator pipeline; FilterBitsNode/VectorSearchNode; composable operators"),
    "37-gpu-acceleration.html": ("GPU 索引(GPU_CAGRA/IVF/BRUTE) 类型在 Milvus、算法在 Knowhere/RAFT · 编译期 milvus-gpu · 显存池 · IndexEngineVersionManager 取最小版本",
                                 "GPU indexes (GPU_CAGRA/IVF/BRUTE): types in Milvus, algorithms in Knowhere/RAFT; compile-time milvus-gpu; VRAM pool; IndexEngineVersionManager takes the MIN version"),
    "38-api-and-sdks.html": ("一份契约 milvus-proto(MilvusService→milvuspb) · 传输层 distributed/proxy vs 逻辑层 proxy/impl.go · 多语言 SDK · gRPC 与 REST 两道门",
                             "one contract milvus-proto (MilvusService→milvuspb); transport distributed/proxy vs logic proxy/impl.go; multi-language SDKs; gRPC & REST two doors"),
    "39-observability.html": ("三大支柱：日志 mlog(带 ctx/结构化/跨节点传播) · 指标 Prometheus(pkg/metrics) · 追踪 OpenTelemetry(pkg/tracer+otelgrpc) · 用 ctx 串起一个请求",
                              "three pillars: logs mlog (ctx/structured/cross-node propagation); metrics Prometheus (pkg/metrics); traces OpenTelemetry (pkg/tracer+otelgrpc); stitch one request via ctx"),
    "40-configuration.html": ("ParamItem(Key/Default/Doc + GetAsInt/Bool 类型安全) · 分层数据源 file<env<etcd 按优先级合并 · config.Manager · 热更新 vs Immutable",
                              "ParamItem (Key/Default/Doc + GetAsInt/Bool type-safe); layered sources file<env<etcd merged by priority; config.Manager; hot reload vs Immutable"),
    "41-deployment.html": ("部署阶梯：内嵌单机→compose→Helm/Operator · 集群按需独立伸缩 · MQ 即 WAL 后端(rocksmq/Pulsar/Kafka/Woodpecker) · 配置/可观测/滚动升级合流",
                           "deployment ladder: embedded→compose→Helm/Operator; cluster scales independently; MQ is the WAL backend (rocksmq/Pulsar/Kafka/Woodpecker); config/observability/rolling-upgrade converge"),
    "42-build-and-run.html": ("两段式构建 make milvus = build-cpp(cmake/conan)→build-go(CGO 链接) · 一个二进制多角色(cmd/main.go) · install_deps/start_*/stop_graceful 脚本",
                              "two-stage build: make milvus = build-cpp(cmake/conan)→build-go(CGO link); one binary, many roles (cmd/main.go); install_deps/start_*/stop_graceful scripts"),
    "43-testing.html": ("go 测试必带 -tags dynamic,test 与 -gcflags=all=-N -l(为 mockey 打补丁) · 两种 mock：mockery(生成接口)/mockey(运行时函数) · make test-go/test-proxy",
                        "go tests must carry -tags dynamic,test and -gcflags=all=-N -l (for mockey patching); two mocks: mockery (generated interfaces)/mockey (runtime functions); make test-go/test-proxy"),
    "44-code-conventions.html": ("merr 错误：Input(不可重试) vs System(可重试)、别用 fmt.Errorf · 日志只用 mlog · import gci 排序(milvus-io 最后) · 生成文件勿手改 · 多由 linter 把关",
                                 "merr errors: Input (not retriable) vs System (retriable), no fmt.Errorf; log only via mlog; gci import order (milvus-io last); don't hand-edit generated files; mostly linter-enforced"),
    "45-contributing-prs.html": ("fork-and-pull 流程 · DCO 签名 git commit -s · PR 标题 {type}: {描述} · 按类型关联 issue/设计文档 · 机器人(DCO/Mergify/CI)先把关",
                                 "fork-and-pull flow; DCO sign-off git commit -s; PR title {type}: {desc}; link issue/design-doc by type; bots (DCO/Mergify/CI) gate first"),
    "46-glossary.html": ("全书术语速查表：按主题(架构/写入/查询/索引/C++ 内核/流式/运维与贡献)归拢关键概念，每条一句话定义 + 课次",
                         "the guide's quick-reference glossary: key concepts by theme (architecture/write/query/indexing/C++ core/streaming/ops & contributing), each a one-line definition + lesson"),
    "47-bulk-import.html": ("绕过 WAL 的第二条写入路径 · ImportV2 → DataCoord 多阶段作业(PreImport/Import/Sort/Index/提交) · DataNode 读 json/csv/parquet 直接写段 · 与流式分工",
                            "the second write path bypassing WAL · ImportV2 → DataCoord multi-phase job (PreImport/Import/Sort/Index/commit) · DataNode reads json/csv/parquet straight into segments · divides labor with streaming"),
    "48-hybrid-search-rerank.html": ("多向量字段 · HybridSearch 带 N 个 SubReqs 并行子搜索 · 融合 ranker：RRF(按名次)/WeightedRanker(加权)/模型重排 · 主要在 Proxy 融合",
                                     "multiple vector fields · HybridSearch with N SubReqs run in parallel · fusion rankers: RRF (by rank)/WeightedRanker/model reranking · fused mainly at the Proxy"),
    "49-quota-and-rate-limiting.html": ("自我保护(背压) · QuotaCenter(RootCoord)收指标→算限速→下发 Proxy · 两档刹车：限速 vs forceDeny · RateLimitInterceptor 回可重试 ErrServiceRateLimit",
                                        "self-protection (backpressure) · QuotaCenter (RootCoord) collects metrics→computes limits→pushes to Proxies · two brakes: throttle vs forceDeny · RateLimitInterceptor returns retriable ErrServiceRateLimit"),
    "50-advanced-features-tour.html": ("巡礼六大生产特性：RBAC(权限) · 资源组(算力隔离) · 数据库(多租户) · 迭代器(翻页) · TTL(自动过期) · Function(服务端向量化)",
                                       "a tour of six production features: RBAC (permissions) · resource groups (compute isolation) · databases (multi-tenancy) · iterators (paging) · TTL (auto-expiry) · Function (server-side vectorization)"),
    "51-design-log-as-data.html": ("贯穿全书的第一条设计主线 · WAL 是唯一事实来源、段/索引/副本都是派生 · 写=追加(盖 TimeTick)、记上即成功 · 一份日志多方按需重放(落段/边写边查/复制/恢复)",
                                   "the first design throughline · the WAL is the one source of truth, segments/indexes/replicas are derived · write=append (stamp TimeTick), logged=success · one log replayed on demand by many (flush/query-while-write/replicate/recover)"),
    "52-design-query-while-write.html": ("一致性三步走 · TSO 发全局单调戳 → Proxy 按级别算保证时间戳 Tg → QueryNode 等 tsafe≥Tg、segcore 按 MVCC(墓碑)过滤 · 级别=新鲜度↔延迟的旋钮",
                                         "consistency in three steps · TSO issues a global monotonic stamp → Proxy derives guarantee ts Tg by level → QueryNode waits tsafe≥Tg, segcore filters by MVCC (tombstones) · the level is a freshness↔latency dial"),
    "53-design-storage-compute-separation.html": ("三层解耦：控制面(etcd 存状态)/计算层(无状态节点)/存储层(对象存储装字节) · 对象存储=建/载之间的中转仓库 · mmap 让大于内存也能加载 · 节点挂了重分配+从存储重载，秒级恢复",
                                                  "three-tier decoupling: control plane (etcd holds state) / compute (stateless nodes) / storage (object storage holds bytes) · object storage = transfer warehouse between build & load · mmap serves data larger than RAM · a dead node is reassigned + reloaded from storage, recovering in seconds"),
    "54-design-scale-to-billions.html": ("分而治之：分(切段摊到分片)→搜(各段并行算局部 topK)→并(三层归并出全局 topK) · 各局部 topK 的并集必含全局 topK，每层只搬 K 个 · 每段建索引+过滤下推让小块也快 · 召回由段内精度决定",
                                         "divide and conquer: split (segments over shards) → search (segments compute local topK in parallel) → combine (three-level merge into a global topK) · the union of local topKs contains the global topK, each layer moves only K · per-segment index + filter pushdown make small blocks fast · recall is set by in-segment precision"),
    "55-design-two-languages.html": ("两类活儿用两种语言：C++ 内核(segcore+Knowhere)承包过滤/检索/归并+SIMD/GPU，Go 编排做调度/RPC/容错 · cgo 桥要薄(粗粒度/零拷贝/带上下文) · 语言是工具不是信仰",
                                     "two kinds of work, two languages: the C++ kernel (segcore+Knowhere) does filter/search/merge + SIMD/GPU, Go orchestration does scheduling/RPC/fault-tolerance · the cgo bridge must be thin (coarse-grained/zero-copy/carries context) · a language is a tool, not a faith"),
    "56-design-failure-as-default.html": ("全书收尾 · 假定故障是常态、系统自愈三层：不丢(WAL+检查点+重放)、对账(协调者比对目标vs实际、可重入任务纠偏)、感知与接管(session/lease+Broadcaster 原子 DDL) · 六条主线，一种工程智慧",
                                          "the guide's finale · assume failure is the default; self-healing in three layers: don't lose (WAL+checkpoint+replay), reconcile (coordinators compare target vs actual, idempotent tasks), detect & take over (session/lease + Broadcaster atomic DDL) · six throughlines, one engineering wisdom"),
    "57-capstone-life-of-a-row.html": ("把写入·索引·查询三条链路串成一行数据的旅程",
                                       "thread the write / index / query paths into one row's journey"),
}


def index_page(lesson_prefix="lessons/"):
    """Build the bilingual index (table of contents). Always relative links."""
    order = []   # ordered list of (part_zh, part_en)
    groups = {}  # part_zh -> [(num, fname, title_zh, title_en), ...]
    for i, (fname, tz, te, pz, pe) in enumerate(PAGES):
        if pz not in groups:
            groups[pz] = []
            order.append((pz, pe))
        groups[pz].append((i + 1, fname, tz, te))

    blocks = []
    for pz, pe in order:
        blocks.append(f'<div class="toc-part">{bi(esc(pz), esc(pe))}</div>')
        for num, fname, tz, te in groups[pz]:
            sz, se = SUBTITLES.get(fname, ("", ""))
            blocks.append(
                f'<a href="{lesson_prefix}{fname}"><span class="n">{num:02d}</span>'
                f'<span class="tt"><span class="lang-zh">{esc(tz)}</span>'
                f'<span class="lang-en">{esc(te)}</span></span>'
                f'<span class="ts"><span class="lang-zh">{esc(sz)}</span>'
                f'<span class="lang-en">{esc(se)}</span></span></a>'
            )
    toc = "\n".join(blocks)
    total = len(PAGES)
    nparts = len(order)

    title_tag = "Milvus 图解教程 · 看懂分布式向量数据库内部 / Milvus Visual Guide"
    desc = ("从零理解整个 Milvus 向量数据库的中英双语图解教程：宏观结构、数据模型、写入链路、"
            "索引、查询链路、流式系统、C++ 内核，每课配真实源码对应、折叠深挖与设计亮点。")

    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-lang="zh"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{LANG_BOOT}
<title>{esc(title_tag)}</title>
{head_meta(title_tag, desc, og_type="website")}
<style>{CSS}</style>
</head><body>
<div class="topbar">
  <div class="topbar-inner">
    <span class="home">🐦 <b class="lang-zh">Milvus 图解教程</b><b class="lang-en">Milvus Visual Guide</b></span>
    <span class="pill"><span class="lang-zh">共 {total} 课 · {nparts} 个部分</span><span class="lang-en">{total} lesson{'' if total == 1 else 's'} · {nparts} part{'' if nparts == 1 else 's'}</span></span>
    <button class="langtoggle" onclick="mvgToggleLang()" aria-label="switch language"><span class="lang-zh">EN</span><span class="lang-en">中</span></button>
  </div>
  <div class="progress"><span style="width:100%"></span></div>
</div>
<div class="wrap">
  <div class="hero index">
    <div class="part">{bi("从零开始 · 面向完全新手", "From scratch · for complete beginners")}</div>
    <h1><span class="lang-zh">用图解读懂整个 Milvus</span><span class="lang-en">Understand all of Milvus, visually</span></h1>
    <p class="lead"><span class="lang-zh">这套教程带你<strong>层层深入</strong>：先建立<strong>宏观全景</strong>与<strong>向量检索基础</strong>，再看懂<strong>分布式架构</strong>，
    然后顺着数据走一遍<strong>写入</strong>·<strong>索引</strong>·<strong>查询</strong>三条链路，深入 <strong>C++ 内核</strong>与<strong>流式系统</strong>，最后学会<strong>本地构建与贡献</strong>。每课配真实源码对应、图解与设计亮点。</span>
    <span class="lang-en">A layered tour: build the <strong>big picture</strong> and <strong>vector-search foundations</strong> first, understand the <strong>distributed architecture</strong>,
    then follow the data through the <strong>write</strong>, <strong>index</strong> and <strong>query</strong> paths, dive into the <strong>C++ core</strong> and the <strong>streaming system</strong>, and finally learn to <strong>build and contribute</strong>. Every lesson maps to real source, with diagrams and design insights.</span></p>
    <div class="legend">
      <span><i style="background:var(--blue)"></i>{bi("宏观理解", "Big picture")}</span>
      <span><i style="background:var(--purple)"></i>{bi("细节 / 源码", "Details / source")}</span>
      <span><i style="background:var(--amber)"></i>{bi("生活类比", "Analogy")}</span>
      <span><i style="background:var(--accent)"></i>{bi("关键要点", "Key points")}</span>
    </div>
    <p style="margin:.8rem 0 0;color:var(--faint);font-size:.8rem">{bi("📌 对照 milvus-io/milvus 仓库真实源码核实 · 源码引用以“文件 + 符号名”为主（行号随上游更新而变）", "📌 Verified against the real milvus-io/milvus source; references cite file + symbol (line numbers drift upstream)")}</p>
  </div>
  <div class="toc-search">
    <input id="q" type="search" placeholder="🔎 搜索课程 / Search lessons" autocomplete="off" aria-label="search">
    <span class="qcount" id="qcount"></span>
  </div>
  <div class="toc">{toc}</div>
  <div class="toc-empty" id="tocempty">{bi("没有匹配的课程，换个关键词试试。", "No matching lessons, try another keyword.")}</div>
  <p style="margin:2.4rem 0 0;color:var(--faint);font-size:.78rem;text-align:center">{bi("本项目是第三方、非官方的学习材料，不含 Milvus 源码（仅引用少量标注来源的片段）；Milvus 由其作者以 Apache-2.0 许可发布。", "Third-party, unofficial learning material; contains no Milvus source code beyond small, cited snippets. Milvus is Apache-2.0-licensed by its authors.")}</p>
</div>
<script>{LANG_JS}</script>
<script>{SEARCH_JS}</script>
</body></html>"""
