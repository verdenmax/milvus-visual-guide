"""Per-lesson bilingual self-test (自测题): design-insight multiple-choice + open prompts.

Schema per lesson::

    "NN-file.html": {
        "mcq": [
            {
                "q":   {"zh": "...", "en": "..."},
                "opts": [{"zh": "...", "en": "..."}, ...],
                "answer": 1,                      # 0-based index into opts (as written)
                "why": {"zh": "...", "en": "..."},
            },
        ],
        "open": [{"zh": "...", "en": "..."}],
    }

``render(fname, lang)`` turns it into HTML that build.py appends to the bottom of
each language's lesson body. Options are deterministically shuffled per question
(same permutation for zh and en, so the correct letter matches across languages).

Quiz text (q/opts/why) is raw HTML in a text context (like the lesson body):
write literal ``<``/``&`` as ``&lt;``/``&amp;`` (or wrap code in ``<code>``).
"""
import hashlib

_HEAD = {"zh": "🧪 自测 · 想一想为什么这么设计", "en": "🧪 Self-test - think about the design"}
_SEE = {"zh": "看答案与解析", "en": "Show answer &amp; explanation"}
_CLICK = {"zh": "点击展开", "en": "click to expand"}
_ANS = {"zh": "答案：", "en": "Answer: "}
_SEP = {"zh": "。", "en": ". "}
_OPEN = {
    "zh": "💭 发散思考（没有标准答案，动手或动脑想想）",
    "en": "💭 Open questions (no single right answer - just think or try)",
}


def _shuffle(opts, answer, seed):
    """Deterministically permute opts (stable across builds); return
    (new_opts, new_answer_index) so the correct option lands in a varied slot."""
    order = sorted(
        range(len(opts)),
        key=lambda i: hashlib.md5(f"{seed}:{i}".encode("utf-8")).hexdigest(),
    )
    return [opts[i] for i in order], order.index(answer)


QUIZZES = {
    "01-what-is-milvus.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 把“相似检索（ANN）”当作一等查询。和传统数据库的“精确匹配”相比，这个定位最主要带来什么不同？",
                    "en": "Milvus treats similarity search (ANN) as a first-class query. Compared with a traditional DB's exact match, what is the main difference this brings?",
                },
                "opts": [
                    {
                        "zh": "查询从“等于谁”变成“最像谁”，数据是高维向量、索引是 HNSW/IVF 等 ANN 结构，靠近似换毫秒级速度",
                        "en": "The query shifts from 'equal to which' to 'most like which'; data is high-dim vectors, indexes are ANN structures (HNSW/IVF), trading approximation for millisecond speed",
                    },
                    {"zh": "它让 SQL 的 JOIN 变得更快", "en": "It makes SQL JOINs faster"},
                    {"zh": "它把所有数据都压缩成整数以省空间", "en": "It compresses all data into integers to save space"},
                    {"zh": "它取消了索引，靠全表扫描保证精确", "en": "It drops indexes and relies on full scans for exactness"},
                ],
                "answer": 0,
                "why": {
                    "zh": "向量数据库的本质就是把“找相似”变成“在向量空间找最近邻”。海量高维向量下精确比对太慢，于是用 ANN 索引牺牲一点点精度换来毫秒级检索。这是它与按 ID/关键词精确命中的标量数据库的根本分野",
                    "en": "A vector DB fundamentally turns 'find similar' into 'find nearest neighbors in vector space'. Exact comparison is too slow at scale, so ANN indexes trade a little accuracy for millisecond retrieval. That is the core split from scalar DBs that hit exactly by id/keyword",
                },
            },
            {
                "q": {
                    "zh": "既然 FAISS 这类算法库就能算 ANN，为什么还需要 Milvus 这样一个“数据库”？",
                    "en": "If an algorithm library like FAISS can already compute ANN, why do we still need a 'database' like Milvus?",
                },
                "opts": [
                    {
                        "zh": "因为真实业务还需要持久化、边写边查的实时更新、标量+向量混合过滤、横向扩展、高可用与一致性——把检索变成一项服务",
                        "en": "Because real workloads also need persistence, real-time updates while querying, scalar+vector hybrid filtering, horizontal scaling, HA and consistency - turning search into a service",
                    },
                    {"zh": "因为 FAISS 算得不准，Milvus 永远返回精确最近邻", "en": "Because FAISS is inaccurate and Milvus always returns exact nearest neighbors"},
                    {"zh": "因为 Milvus 不需要任何索引就更快", "en": "Because Milvus is faster without any index"},
                    {"zh": "因为 FAISS 只能跑在 GPU 上", "en": "Because FAISS only runs on GPUs"},
                ],
                "answer": 0,
                "why": {
                    "zh": "算法库解决“怎么算得快”，数据库解决“怎么在真实世界里长期、可靠、规模化地用起来”。Milvus 内部确实用到了向量检索内核（Knowhere），但在其上补齐了持久化、实时写入、混合过滤、扩展与高可用等数据库该有的一切",
                    "en": "A library solves 'how to compute fast'; a database solves 'how to use it durably, reliably and at scale in the real world'. Milvus does use a vector-search kernel (Knowhere) internally, but adds persistence, streaming writes, hybrid filtering, scaling and HA on top",
                },
            },
            {
                "q": {
                    "zh": "Milvus 提供 Lite、Standalone、Cluster 三种形态。从“用户写的代码”角度看，三者最重要的共同点是什么？",
                    "en": "Milvus offers Lite, Standalone and Cluster. From the user's code perspective, what is the most important thing they share?",
                },
                "opts": [
                    {
                        "zh": "对外的 API 与核心概念一致：同样的 create_collection / insert / search，底层从一个进程长成一个集群而代码不变",
                        "en": "The external API and core concepts are the same: identical create_collection / insert / search, while the underside grows from one process into a cluster without code changes",
                    },
                    {"zh": "三者都必须部署在 Kubernetes 上", "en": "All three must be deployed on Kubernetes"},
                    {"zh": "三者都把数据只存在内存里，不持久化", "en": "All three keep data only in memory, never persisted"},
                    {"zh": "三者都只能存百万级以内的数据", "en": "All three are limited to a few million items"},
                ],
                "answer": 0,
                "why": {
                    "zh": "这正是分层架构的价值：用户面对统一的 API 与概念，规模通过更换部署形态来满足，而业务代码几乎不动。Lite 适合原型、Standalone 适合中小规模、Cluster 面向十亿级生产",
                    "en": "That is the value of the layered architecture: users face one API and concept set, scale is met by swapping the deployment shape, and business code barely changes. Lite suits prototypes, Standalone small/medium, Cluster billion-scale production",
                },
            },
        ],
        "open": [
            {
                "zh": "想一个你会用相似检索做的应用（比如“以图搜图”“RAG 文档问答”“商品推荐”）。如果只有纯 ANN（给向量返回 topK），还缺哪些能力？试着把它们对应到本课说的“库 vs 数据库”——你需要的是过滤、实时更新，还是高可用？",
                "en": "Think of an app you'd build with similarity search (image-to-image, RAG document QA, product recommendation). With pure ANN (give a vector, get topK), what is still missing? Map those to this lesson's 'library vs database' split - do you need filtering, real-time updates, or high availability?",
            },
        ],
    },
}


def render(fname, lang):
    """Return the self-test HTML block for ``fname`` in ``lang`` ('' if none)."""
    data = QUIZZES.get(fname)
    if not data or not (data.get("mcq") or data.get("open")):
        return ""
    out = ['<div class="selftest">', f'<h2>{_HEAD[lang]}</h2>']
    for i, item in enumerate(data.get("mcq", []), 1):
        shuffled, ans = _shuffle(item["opts"], item["answer"], f"{fname}:{i}")
        opts = "\n".join(f"    <li>{o[lang]}</li>" for o in shuffled)
        letter = chr(65 + ans)
        out.append(
            f'<div class="quiz">\n'
            f'  <div class="qn">{i}. {item["q"][lang]}</div>\n'
            f'  <ol class="opts">\n{opts}\n  </ol>\n'
            f'  <details class="accordion">\n'
            f'    <summary>{_SEE[lang]} <span class="hint">{_CLICK[lang]}</span></summary>\n'
            f'    <div class="acc-body"><div class="qa"><div class="a">'
            f'<strong>{_ANS[lang]}{letter}</strong>{_SEP[lang]}{item["why"][lang]}'
            f"</div></div></div>\n"
            f"  </details>\n"
            f"</div>"
        )
    opens = data.get("open", [])
    if opens:
        lis = "\n".join(f"    <li>{o[lang]}</li>" for o in opens)
        out.append(
            '<div class="card spark">\n'
            f'  <div class="tag">{_OPEN[lang]}</div>\n'
            f"  <ul>\n{lis}\n  </ul>\n"
            "</div>"
        )
    out.append("</div>")
    return "\n".join(out)


def _validate():
    """Fail fast on authoring mistakes in QUIZZES (clear message names the lesson)."""
    for fname, data in QUIZZES.items():
        for qi, item in enumerate(data.get("mcq", []), 1):
            opts = item["opts"]
            if not (0 <= item["answer"] < len(opts)):
                raise ValueError(
                    f"quizzes[{fname!r}] Q{qi}: answer {item['answer']} out of range 0..{len(opts) - 1}"
                )
            for o in opts:
                if not ({"zh", "en"} <= o.keys()):
                    raise ValueError(f"quizzes[{fname!r}] Q{qi}: an option is missing zh/en")
            if not ({"zh", "en"} <= item["q"].keys() and {"zh", "en"} <= item["why"].keys()):
                raise ValueError(f"quizzes[{fname!r}] Q{qi}: q/why missing zh/en")
        for oi, o in enumerate(data.get("open", []), 1):
            if not ({"zh", "en"} <= o.keys()):
                raise ValueError(f"quizzes[{fname!r}] open{oi}: missing zh/en")


_validate()
