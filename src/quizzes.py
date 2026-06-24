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
    "02-project-map.html": {
        "mcq": [
            {
                "q": {
                    "zh": "关于当前 Milvus 的协调器（coordinator），下面哪种说法最准确？",
                    "en": "Regarding the coordinators in current Milvus, which statement is most accurate?",
                },
                "opts": [
                    {
                        "zh": "Root/Data/Query 三个协调角色在代码里仍存在，但已合并进同一个 MixCoord 进程一起部署——逻辑三件事、物理一个进程",
                        "en": "The Root/Data/Query coordinator roles still exist in code but are merged into one MixCoord process deployed together - three things logically, one process physically",
                    },
                    {"zh": "RootCoord、DataCoord、QueryCoord 必须各自作为独立进程部署", "en": "RootCoord, DataCoord and QueryCoord must each be deployed as a separate process"},
                    {"zh": "三个协调器已被彻底删除，功能移到了 Proxy 里", "en": "The three coordinators were removed entirely and their work moved into the Proxy"},
                    {"zh": "MixCoord 只是 RootCoord 的新名字，另两个仍独立", "en": "MixCoord is just a new name for RootCoord; the other two remain independent"},
                ],
                "answer": 0,
                "why": {
                    "zh": "代码铁证在 internal/types/types.go 的 MixCoord 接口：它把 RootCoordServer、QueryCoordServer、DataCoordServer 三个服务接口嵌在一起。三个“角色”仍在（internal/rootcoord、datacoord、querycoordv2），但作为一个 MixCoord 进程部署。这是“逻辑 vs 物理”的经典区分",
                    "en": "The proof is the MixCoord interface in internal/types/types.go: it embeds RootCoordServer, QueryCoordServer and DataCoordServer. The three roles still exist (internal/rootcoord, datacoord, querycoordv2) but deploy as one MixCoord process - the classic logical-vs-physical split",
                },
            },
            {
                "q": {
                    "zh": "Milvus 用三种语言分工。下面哪一组“语言 → 职责”的对应是对的？",
                    "en": "Milvus splits work across three languages. Which 'language → responsibility' mapping is correct?",
                },
                "opts": [
                    {
                        "zh": "Go = 分布式控制面（internal/）；C++ = 计算内核（internal/core/：segcore/index/query）；Rust = 全文倒排索引（tantivy）",
                        "en": "Go = distributed control plane (internal/); C++ = compute kernels (internal/core/: segcore/index/query); Rust = full-text inverted index (tantivy)",
                    },
                    {"zh": "Go 写索引内核，C++ 写 RPC，Rust 写调度", "en": "Go writes the index kernel, C++ writes RPC, Rust writes scheduling"},
                    {"zh": "三种语言各写一份完全相同的实现以容错", "en": "The three languages each write an identical implementation for fault tolerance"},
                    {"zh": "Rust 负责绝大多数控制面逻辑", "en": "Rust handles most of the control-plane logic"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Go 擅长并发与开发效率，适合写协调/调度/RPC 的控制面；C++ 贴近硬件、追求极致性能，适合段内检索与索引这类计算内核；Rust 只负责很专的全文倒排索引（tantivy）。一次 search 会依次穿过这三种语言",
                    "en": "Go suits concurrency and velocity for the coordination/scheduling/RPC control plane; C++ is close to the hardware for compute kernels like in-segment search and indexing; Rust owns only the specialized full-text inverted index (tantivy). One search passes through all three",
                },
            },
            {
                "q": {
                    "zh": "关于“索引构建”由谁负责，下面哪种说法正确？",
                    "en": "Who is responsible for 'index building'? Which statement is correct?",
                },
                "opts": [
                    {
                        "zh": "没有单独的 indexnode；索引构建由 DataCoord 调度、交给一个 datanode 工作进程执行",
                        "en": "There is no separate indexnode; index building is scheduled by DataCoord and run by a datanode worker",
                    },
                    {"zh": "由一个名为 indexnode 的独立组件专门负责", "en": "A dedicated standalone component called indexnode handles it"},
                    {"zh": "由 Proxy 在写入时同步构建索引", "en": "The Proxy builds the index synchronously at write time"},
                    {"zh": "由客户端 SDK 在本地构建后上传", "en": "The client SDK builds it locally and uploads it"},
                ],
                "answer": 0,
                "why": {
                    "zh": "当前架构没有独立的 indexnode 组件。索引构建是异步的：DataCoord 负责调度，实际执行落在 datanode 工作进程上。把它记进“四组导航”里：索引话题属于“工作节点 + 协调层 DataCoord + C++ 内核 index”",
                    "en": "The current architecture has no standalone indexnode. Index building is asynchronous: DataCoord schedules it and a datanode worker runs it. In the four-group nav, an index topic maps to 'worker nodes + DataCoord + C++ kernel index'",
                },
            },
        ],
        "open": [
            {
                "zh": "用本课的“四组导航”（接入 Proxy / 协调 MixCoord / 工作节点 / 存储与依赖）给下面几件事各找一个“归属组”和大致的代码目录：①新建一个集合 ②一次向量检索的段内计算 ③把刚写入的数据刷盘成 binlog ④保存“某个分片在哪台机器”。",
                "en": "Using this lesson's four-group nav (Access Proxy / Coordination MixCoord / Worker nodes / Storage & deps), assign each of these to a group and a rough code directory: (1) creating a collection, (2) the in-segment compute of one vector search, (3) flushing freshly written data into a binlog, (4) storing 'which shard is on which machine'.",
            },
        ],
    },
    "03-life-of-a-request.html": {
        "mcq": [
            {
                "q": {
                    "zh": "一条 insert 在 Proxy 处会发生哪些关键动作？",
                    "en": "What key actions happen to an insert at the Proxy?",
                },
                "opts": [
                    {
                        "zh": "校验 schema、必要时自动补主键、向 TSO 申请一个时间戳盖在这批数据上、按主键哈希到 vchannel/分片，再追加到 WAL",
                        "en": "Validate the schema, auto-fill the primary key if needed, request a timestamp from the TSO and stamp the batch, hash by PK into vchannels/shards, then append to the WAL",
                    },
                    {"zh": "直接把每一行逐条写入对象存储，并同步建好索引", "en": "Write each row directly into object storage one by one and build the index synchronously"},
                    {"zh": "把数据发给 QueryNode 立即检索一遍再返回", "en": "Send the data to a QueryNode to search it once and return"},
                    {"zh": "只负责转发，不做任何校验或时间戳分配", "en": "Only forward the request, doing no validation or timestamp assignment"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Proxy 是统一入口：校验、补主键、盖时间戳（来自 TSO）、按 PK 哈希分片，最后把这批数据追加到可重放的 WAL。一旦日志记上，写入即算成功返回；落盘成 binlog 是后续由工作节点异步完成的",
                    "en": "The Proxy is the single entry: validate, fill PK, stamp a timestamp (from the TSO), hash by PK into shards, and finally append the batch to a replayable WAL. Once logged, the write returns as success; flushing to binlogs is done asynchronously by worker nodes later",
                },
            },
            {
                "q": {
                    "zh": "为什么 Milvus 的写入要“先写一条只追加的日志（WAL）”，而不是直接写进段/对象存储？",
                    "en": "Why does a Milvus write 'append to a log (WAL) first' instead of writing straight into segments/object storage?",
                },
                "opts": [
                    {
                        "zh": "顺序追加飞快、日志天然有序便于崩溃后重放恢复、并发写只需在日志尾排队无需加锁——把“写得快”和“查得快”解耦",
                        "en": "Sequential appends are fast, the ordered log makes crash recovery a simple replay, and concurrent writers just queue at the tail without locks - decoupling 'write fast' from 'query fast'",
                    },
                    {"zh": "因为对象存储不支持持久化，只能先放日志", "en": "Because object storage can't persist data, so it must go to a log first"},
                    {"zh": "为了让客户端能直接读取原始日志格式", "en": "So that clients can read the raw log format directly"},
                    {"zh": "日志只是调试用途，生产环境会关闭", "en": "The log is only for debugging and is disabled in production"},
                ],
                "answer": 0,
                "why": {
                    "zh": "这是“日志即数据（log as data）”的核心收益：append-only 是顺序写，极快；日志有序，重放到哪条一清二楚，崩溃后接着重放即可；多写者只在尾部排队，免去段级锁。段与索引是日志事后物化出来的视图",
                    "en": "This is the core payoff of 'log as data': append-only is sequential and very fast; the ordered log makes it clear where replay stopped, so recovery is just resuming replay; concurrent writers only queue at the tail, avoiding segment-level locks. Segments and indexes are views materialized from the log afterward",
                },
            },
            {
                "q": {
                    "zh": "一次 search 的“扇出—归约（scatter-gather）”形状，下面哪种描述对？",
                    "en": "Which describes the 'scatter-gather' shape of one search correctly?",
                },
                "opts": [
                    {
                        "zh": "Proxy 扇出到多个分片、每分片再到多个段并行算，结果反向归约：段 topK → 节点 topK → Proxy 跨分片全局 topK，每层只上传前 K 个",
                        "en": "The Proxy scatters to many shards, each fans out to many segments computed in parallel; results gather back: segment topK → node topK → Proxy global topK, each layer passing up only the top K",
                    },
                    {"zh": "Proxy 把全部原始向量拉回本地，自己暴力算一遍 topK", "en": "The Proxy pulls all raw vectors back and brute-forces the topK itself"},
                    {"zh": "只查一个分片的一个段就直接返回", "en": "It searches only one segment of one shard and returns directly"},
                    {"zh": "由客户端 SDK 负责跨分片归并", "en": "The client SDK does the cross-shard reduce"},
                ],
                "answer": 0,
                "why": {
                    "zh": "段内检索在 C++ segcore 算出每段 topK，QueryNode 先归并出本节点 topK，Proxy 再跨分片做全局归并。每层只往上传“前 K 个候选”，所以即便底下有上亿向量，网络上也只流动很少量数据——这是分布式检索又快又省的关键",
                    "en": "In-segment search computes per-segment topK in C++ segcore, the QueryNode reduces to a node topK, and the Proxy reduces globally across shards. Each layer passes up only 'the top K', so even with hundreds of millions of vectors, only a tiny amount flows over the network - the key to fast, cheap distributed search",
                },
            },
            {
                "q": {
                    "zh": "读请求的“保证时间戳（guarantee timestamp）”和一致性级别是什么关系？",
                    "en": "How does a read's 'guarantee timestamp' relate to the consistency level?",
                },
                "opts": [
                    {
                        "zh": "由一致性级别推导：Strong 取最新时间（看见最全、可能多等）、Bounded 取稍早时间（容忍少量延迟换更低时延）、Eventually 最快但可能读到较旧快照",
                        "en": "It's derived from the level: Strong takes the latest time (most complete, may wait longer), Bounded takes a slightly earlier time (tolerate a little lag for lower latency), Eventually is fastest but may read an older snapshot",
                    },
                    {"zh": "保证时间戳是固定常量，和一致性级别无关", "en": "The guarantee timestamp is a fixed constant, unrelated to the consistency level"},
                    {"zh": "一致性级别只影响写入，不影响读取", "en": "The consistency level only affects writes, not reads"},
                    {"zh": "它由客户端随机生成", "en": "It is randomly generated by the client"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Proxy 按一致性级别推导 guarantee ts，delegator 会“等到本分片数据追上这个 ts”再开始搜，从而给出一致快照。ts 越新看得越全但可能多等，越旧越快但可能漏掉最新写入——这就是“看得多新 vs 等得多久”的权衡（细节见第 30 课）",
                    "en": "The Proxy derives the guarantee ts from the level, and the delegator waits until the shard's data catches up to that ts before searching, giving a consistent snapshot. A fresher ts sees more but may wait longer; an older one is faster but may miss the latest writes - the 'how fresh vs how long you wait' trade-off (details in Lesson 30)",
                },
            },
        ],
        "open": [
            {
                "zh": "“边写边查”是 Milvus 的一个关键特性：你上一秒 insert 的数据，下一秒就能被搜到。结合本课的写入链路与查询链路，说说这是靠哪两个机制配合实现的？（提示：增长段、delegator 的段选择）",
                "en": "'Query while writing' is a key Milvus feature: data you inserted a second ago is searchable the next. Combining this lesson's write and query paths, which two mechanisms cooperate to make this possible? (Hint: the growing segment, and the delegator's segment selection.)",
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
