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
                "en": "Using this lesson's four-group nav (Access Proxy / Coordination MixCoord / Worker nodes / Storage &amp; deps), assign each of these to a group and a rough code directory: (1) creating a collection, (2) the in-segment compute of one vector search, (3) flushing freshly written data into a binlog, (4) storing 'which shard is on which machine'.",
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
    "04-embeddings-and-similarity.html": {
        "mcq": [
            {
                "q": {
                    "zh": "当所有向量都已经归一化（模长为 1）时，用 IP（内积）和用 COSINE（余弦）排序 topK 的结果有什么关系？",
                    "en": "When all vectors are normalized (unit length), how do the topK rankings by IP (inner product) and by COSINE relate?",
                },
                "opts": [
                    {
                        "zh": "完全等价：归一化后内积就等于余弦，排序结果一致，所以很多系统直接归一化再用 IP",
                        "en": "Exactly equivalent: after normalization the inner product equals cosine, so the rankings match; many systems normalize and then use IP",
                    },
                    {"zh": "IP 永远把所有向量判为相同距离", "en": "IP always judges all vectors as equally distant"},
                    {"zh": "COSINE 此时会退化成 L2 欧氏距离", "en": "COSINE degenerates into L2 Euclidean distance here"},
                    {"zh": "两者结果总是恰好相反", "en": "The two always give exactly opposite results"},
                ],
                "answer": 0,
                "why": {
                    "zh": "余弦相似度 = 内积 /（两模长之积）。当模长都为 1 时分母为 1，于是余弦就等于内积，排序完全一致。这就是“先归一化再用 IP”这一常见做法的依据",
                    "en": "Cosine = inner product / (product of norms). When both norms are 1 the denominator is 1, so cosine equals inner product and the rankings are identical. That justifies the common 'normalize then use IP' trick",
                },
            },
            {
                "q": {
                    "zh": "对二值（binary）向量做相似度，下面哪一组度量是合适的？",
                    "en": "For binary vectors, which set of metrics is appropriate?",
                },
                "opts": [
                    {
                        "zh": "HAMMING / JACCARD —— 它们衡量比特位的差异或集合重叠，专为二值向量设计",
                        "en": "HAMMING / JACCARD - they measure bit differences or set overlap, designed for binary vectors",
                    },
                    {"zh": "只能用 L2，二值向量当成普通浮点处理", "en": "Only L2; treat binary vectors as ordinary floats"},
                    {"zh": "必须先转成稀疏向量再用 IP", "en": "Must convert to sparse vectors first and use IP"},
                    {"zh": "二值向量不支持任何相似度度量", "en": "Binary vectors support no similarity metric at all"},
                ],
                "answer": 0,
                "why": {
                    "zh": "metric_type.go 里为二值向量提供了 HAMMING（不同比特数）和 JACCARD（集合相似度）等度量；稀疏向量用 IP。度量名是大小写敏感的字符串常量，要按代码原样写",
                    "en": "metric_type.go provides HAMMING (differing bits) and JACCARD (set similarity) for binary vectors; sparse vectors use IP. Metric names are case-sensitive string constants, written exactly as in the code",
                },
            },
            {
                "q": {
                    "zh": "为什么在高维向量上需要 ANN（近似最近邻）而不是精确暴力搜索？",
                    "en": "Why do we need ANN (approximate nearest neighbor) on high-dim vectors rather than exact brute force?",
                },
                "opts": [
                    {
                        "zh": "海量高维向量下精确逐一比对太慢，ANN 用一点点精度（召回率）换取毫秒级速度",
                        "en": "Exact one-by-one comparison is too slow at scale; ANN trades a little accuracy (recall) for millisecond speed",
                    },
                    {"zh": "因为精确搜索会返回错误结果", "en": "Because exact search returns wrong results"},
                    {"zh": "因为高维向量无法计算距离", "en": "Because distances cannot be computed in high dimensions"},
                    {"zh": "因为 ANN 总是比暴力搜索更精确", "en": "Because ANN is always more accurate than brute force"},
                ],
                "answer": 0,
                "why": {
                    "zh": "暴力搜索要把查询和每条向量都算一遍距离，数据上亿时延迟无法接受。ANN 通过索引结构只看一小部分候选，用可控的召回率损失换来巨大的速度提升——这正是下一课要展开的主题",
                    "en": "Brute force computes the distance against every vector; at hundreds of millions the latency is unacceptable. ANN inspects only a small candidate set via an index, trading a controllable recall loss for huge speedups - exactly the next lesson's topic",
                },
            },
        ],
        "open": [
            {
                "zh": "假设你要做“以图搜图”，图片向量已用某模型生成。你会先归一化吗？会选 L2、IP 还是 COSINE？说说你的理由，并想想如果换成“稀疏关键词向量”度量该怎么变。",
                "en": "Suppose you build image-to-image search with vectors from some model. Would you normalize first? Would you pick L2, IP, or COSINE? Explain your reasoning, and consider how the metric should change for 'sparse keyword vectors'.",
            },
        ],
    },
    "05-ann-algorithms.html": {
        "mcq": [
            {
                "q": {
                    "zh": "ANN 索引选型常被描述为“速度↔内存↔召回”的三角权衡。这个三角的核心含义是什么？",
                    "en": "ANN index selection is often described as a 'speed↔memory↔recall' triangle. What does this triangle mean at its core?",
                },
                "opts": [
                    {
                        "zh": "三者很难同时拉满：提升一个常要牺牲另一个，选型就是按业务在三者间找平衡点",
                        "en": "You can rarely max all three: improving one often sacrifices another, so selection means balancing the three for your workload",
                    },
                    {"zh": "三者完全独立，可以各自任意最大化", "en": "The three are fully independent and each can be maximized freely"},
                    {"zh": "只要内存够大，速度和召回就一定都最优", "en": "With enough memory, speed and recall are both automatically optimal"},
                    {"zh": "三角说明 FLAT 在所有维度都最好", "en": "The triangle shows FLAT is best on every dimension"},
                ],
                "answer": 0,
                "why": {
                    "zh": "FLAT 召回 100% 但慢且占内存；IVF 用聚类剪枝换速度；HNSW 又快又准但更吃内存；PQ/DiskANN 用压缩或落盘省内存但牺牲一点召回或速度。没有银弹，选型是工程权衡",
                    "en": "FLAT gives 100% recall but is slow and memory-heavy; IVF trades pruning for speed; HNSW is fast and accurate but memory-hungry; PQ/DiskANN save memory via compression or disk at some recall/speed cost. No silver bullet - selection is a trade-off",
                },
            },
            {
                "q": {
                    "zh": "关于 IVF 的参数 nlist 和 nprobe，下面哪种理解是对的？",
                    "en": "Regarding IVF's nlist and nprobe parameters, which understanding is correct?",
                },
                "opts": [
                    {
                        "zh": "nlist 是聚类桶的数量；nprobe 是查询时实际扫描的桶数。nprobe 越大召回越高但越慢",
                        "en": "nlist is the number of cluster buckets; nprobe is how many buckets are actually scanned at query time. Larger nprobe means higher recall but slower",
                    },
                    {"zh": "nlist 控制查询速度，nprobe 决定向量维度", "en": "nlist controls query speed, nprobe sets the vector dimension"},
                    {"zh": "两者都只影响建索引、不影响查询", "en": "Both affect only index building, not querying"},
                    {"zh": "nprobe 越大一定越快", "en": "Larger nprobe is always faster"},
                ],
                "answer": 0,
                "why": {
                    "zh": "IVF 把向量聚成 nlist 个桶；查询时只在离查询最近的 nprobe 个桶里找。nprobe 小则扫得少、快但可能漏掉真正近邻（召回低），nprobe 大则更全但更慢——又是一个速度↔召回的旋钮",
                    "en": "IVF clusters vectors into nlist buckets; a query searches only the nprobe buckets nearest the query. Small nprobe scans less - fast but may miss true neighbors (low recall); large nprobe is more complete but slower - another speed↔recall knob",
                },
            },
            {
                "q": {
                    "zh": "DiskANN 与 HNSW 相比，最主要的取舍点在哪里？",
                    "en": "Compared with HNSW, what is DiskANN's main trade-off?",
                },
                "opts": [
                    {
                        "zh": "DiskANN 把大部分索引放在 SSD 上，用磁盘换内存，适合内存放不下的超大数据集",
                        "en": "DiskANN keeps most of the index on SSD, trading disk for memory, suited to huge datasets that don't fit in RAM",
                    },
                    {"zh": "DiskANN 完全不需要任何存储", "en": "DiskANN needs no storage at all"},
                    {"zh": "DiskANN 只能处理二值向量", "en": "DiskANN only handles binary vectors"},
                    {"zh": "DiskANN 总是比 HNSW 快且更省内存", "en": "DiskANN is always faster and more memory-efficient than HNSW"},
                ],
                "answer": 0,
                "why": {
                    "zh": "HNSW 是纯内存图索引，又快又准但内存开销大；DiskANN 专为“内存装不下”的超大规模设计，把索引主体放 SSD，用磁盘 I/O 换内存占用，代价是延迟通常高于纯内存索引",
                    "en": "HNSW is an in-memory graph index, fast and accurate but memory-heavy; DiskANN targets ultra-large scale that won't fit in RAM, putting the index body on SSD and trading disk I/O for memory, at the cost of latency higher than pure in-memory indexes",
                },
            },
        ],
        "open": [
            {
                "zh": "给定一个 1 亿条、512 维、要求 p99 延迟 < 50ms、召回 ≥ 0.95、且服务器内存有限的场景，你会从 FLAT/IVF/HNSW/PQ/DiskANN 里先试哪个？说说你权衡“速度↔内存↔召回”的思路。",
                "en": "For 100M items at 512-dim, requiring p99 < 50ms, recall ≥ 0.95, on a memory-limited server, which of FLAT/IVF/HNSW/PQ/DiskANN would you try first? Explain how you weigh the speed↔memory↔recall trade-off.",
            },
        ],
    },
    "06-data-model.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 的动态字段（dynamic field）解决了什么问题？",
                    "en": "What problem does Milvus's dynamic field solve?",
                },
                "opts": [
                    {
                        "zh": "允许写入 schema 里没显式声明的字段（存进 $meta），给固定 schema 留一个灵活的活口",
                        "en": "It lets you write fields not explicitly declared in the schema (stored in $meta), giving a fixed schema a flexible escape hatch",
                    },
                    {"zh": "它让主键可以重复", "en": "It allows duplicate primary keys"},
                    {"zh": "它把所有字段都变成向量", "en": "It turns every field into a vector"},
                    {"zh": "它取消了对数据类型的检查", "en": "It removes all data-type checking"},
                ],
                "answer": 0,
                "why": {
                    "zh": "开启 enable_dynamic_field 后，未声明的字段会被收进一个隐藏的 $meta（JSON）里，既保持了固定 schema 的结构与效率，又能容纳临时/稀疏的额外属性。代价是它不如固定字段高效",
                    "en": "With enable_dynamic_field on, undeclared fields go into a hidden $meta (JSON), keeping the fixed schema's structure and efficiency while accommodating temporary/sparse extra attributes. The trade-off is it's less efficient than fixed fields",
                },
            },
            {
                "q": {
                    "zh": "关于分区键（partition key），下面哪种说法最准确？",
                    "en": "Regarding the partition key, which statement is most accurate?",
                },
                "opts": [
                    {
                        "zh": "指定某个标量字段为分区键后，Milvus 按其值自动把数据路由到不同分区，查询带该条件时可只扫相关分区（分区剪枝）",
                        "en": "Designating a scalar field as partition key makes Milvus auto-route data into partitions by its value; queries with that condition can scan only relevant partitions (partition pruning)",
                    },
                    {"zh": "分区键必须是向量字段", "en": "The partition key must be a vector field"},
                    {"zh": "分区键会让查询必须扫描所有分区", "en": "The partition key forces every query to scan all partitions"},
                    {"zh": "分区键和主键必须是同一个字段", "en": "The partition key and primary key must be the same field"},
                ],
                "answer": 0,
                "why": {
                    "zh": "分区键是一种“按字段值自动分区”的机制：你不用手动管理分区，Milvus 依分区键的值把数据分散；查询带上该字段过滤时能做分区剪枝、只扫部分分区，是多租户（如按 user_id 隔离）的利器",
                    "en": "The partition key auto-partitions by a field's value: you don't manage partitions manually, Milvus spreads data by the key's value; a query filtering on that field enables partition pruning, scanning only some partitions - great for multi-tenancy (e.g. isolating by user_id)",
                },
            },
            {
                "q": {
                    "zh": "下面哪一组全部是当前 Milvus 支持的向量数据类型？",
                    "en": "Which group consists entirely of vector data types currently supported by Milvus?",
                },
                "opts": [
                    {
                        "zh": "FloatVector、BinaryVector、Float16Vector、BFloat16Vector、Int8Vector、SparseFloatVector",
                        "en": "FloatVector, BinaryVector, Float16Vector, BFloat16Vector, Int8Vector, SparseFloatVector",
                    },
                    {"zh": "只有 FloatVector 和 BinaryVector 两种", "en": "Only FloatVector and BinaryVector"},
                    {"zh": "VarChar、JSON、Array、Bool", "en": "VarChar, JSON, Array, Bool"},
                    {"zh": "Int64、Float、Double、Bool", "en": "Int64, Float, Double, Bool"},
                ],
                "answer": 0,
                "why": {
                    "zh": "以当前代码（client/entity/field.go）为准，向量类型有六种：FloatVector、BinaryVector、Float16Vector、BFloat16Vector、Int8Vector、SparseFloatVector。旧文档里“只有两种向量”的说法已过时——代码为准",
                    "en": "Per current code (client/entity/field.go) there are six vector types: FloatVector, BinaryVector, Float16Vector, BFloat16Vector, Int8Vector, SparseFloatVector. The old docs' 'only two vector types' is outdated - the code wins",
                },
            },
        ],
        "open": [
            {
                "zh": "为一个“电商商品”集合设计 schema：你会把哪个字段设为主键、是否开 auto_id？把哪个字段作分区键？要不要开动态字段？哪些标量字段会参与过滤？写出你的字段清单与理由。",
                "en": "Design a schema for an e-commerce 'product' collection: which field is the primary key, and do you enable auto_id? Which field is the partition key? Do you enable the dynamic field? Which scalar fields participate in filtering? Write your field list and reasoning.",
            },
        ],
    },
    "07-segments.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 中一个 segment 的生命周期状态链是下面哪一条？",
                    "en": "Which chain is the lifecycle of a segment in Milvus?",
                },
                "opts": [
                    {
                        "zh": "Growing → Sealed → Flushing → Flushed →（Dropped）",
                        "en": "Growing → Sealed → Flushing → Flushed → (Dropped)",
                    },
                    {"zh": "Sealed → Growing → Dropped → Flushed", "en": "Sealed → Growing → Dropped → Flushed"},
                    {"zh": "Flushed → Growing → Sealed → Flushing", "en": "Flushed → Growing → Sealed → Flushing"},
                    {"zh": "Dropped → Flushing → Growing → Sealed", "en": "Dropped → Flushing → Growing → Sealed"},
                ],
                "answer": 0,
                "why": {
                    "zh": "这些状态名直接来自代码里的 SegmentState 枚举：Growing（内存可变）→ Sealed（写满不可变）→ Flushing（落盘中）→ Flushed（已存对象存储、可建索引）→ Dropped（压缩/删除后等待 GC）",
                    "en": "These names come straight from the SegmentState enum: Growing (mutable in memory) → Sealed (full, immutable) → Flushing (landing) → Flushed (in object storage, indexable) → Dropped (after compaction/delete, awaiting GC)",
                },
            },
            {
                "q": {
                    "zh": "关于 vchannel 与 pchannel 的关系，下面哪种说法正确？",
                    "en": "Which statement about vchannel and pchannel is correct?",
                },
                "opts": [
                    {
                        "zh": "vchannel 是逻辑分片，pchannel 是物理 MQ topic；多个 vchannel 可共享一个 pchannel（vchannel 名截掉最后一段即得 pchannel）",
                        "en": "vchannel is a logical shard, pchannel is a physical MQ topic; many vchannels can share one pchannel (strip a vchannel name's last segment to get the pchannel)",
                    },
                    {"zh": "vchannel 和 pchannel 必须一一对应", "en": "vchannel and pchannel must map one-to-one"},
                    {"zh": "pchannel 是逻辑概念，vchannel 是物理 topic", "en": "pchannel is logical, vchannel is the physical topic"},
                    {"zh": "二者都只存在于查询路径，与写入无关", "en": "Both exist only on the query path, unrelated to writes"},
                ],
                "answer": 0,
                "why": {
                    "zh": "func.go 里 GetVirtualChannel 把 pchannel 名拼上 collectionID 和分片号得到 vchannel；ToPhysicalChannel 反过来截掉最后一段还原 pchannel。逻辑分片数与物理 topic 数解耦，让多个 vchannel 复用少量 pchannel",
                    "en": "In func.go, GetVirtualChannel appends collectionID and shard index to a pchannel name to form a vchannel; ToPhysicalChannel reverses it by stripping the last segment. Decoupling logical shards from physical topics lets many vchannels reuse few pchannels",
                },
            },
            {
                "q": {
                    "zh": "“日志即数据（log as data）”这一设计哲学的核心是什么？",
                    "en": "What is the core of the 'log as data' design philosophy?",
                },
                "opts": [
                    {
                        "zh": "append-only、带时间戳、可重放的日志才是唯一真相，其它数据形态（内存段、binlog、索引）都是它的物化视图",
                        "en": "The append-only, timestamped, replayable log is the only source of truth; other forms (memory segments, binlogs, indexes) are its materialized views",
                    },
                    {"zh": "日志只用于崩溃恢复，平时没有用", "en": "The log is only for crash recovery and otherwise useless"},
                    {"zh": "数据写进段后日志就可以立刻丢弃", "en": "The log can be discarded the moment data enters a segment"},
                    {"zh": "日志和数据是两份互不相关的副本", "en": "Log and data are two unrelated copies"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Milvus 把传统“表是真相、日志是辅助”反了过来：日志是权威源，写入只要进了日志就算落地；内存 Growing 段、对象存储 binlog、索引都靠消费/重放这条日志来追上状态。这支撑了边写边查和简单的崩溃恢复",
                    "en": "Milvus inverts the traditional 'table is truth, log is aid': the log is authoritative, and a write is 'landed' once in the log; the in-memory Growing segment, binlogs, and indexes all catch up by consuming/replaying it. This enables search-while-writing and simple crash recovery",
                },
            },
        ],
        "open": [
            {
                "zh": "“边写边查”要求刚 insert 的数据立刻能被搜到。结合本课的段生命周期，说说为什么 Growing 段是这件事的关键，以及查询时为什么要同时看 Growing 段和已加载的 Sealed 段。",
                "en": "'Search while writing' requires just-inserted data to be searchable immediately. Using this lesson's segment lifecycle, explain why the Growing segment is key, and why a query must look at both Growing and loaded Sealed segments.",
            },
        ],
    },
    "08-dependencies-and-deployment.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 的三大外部依赖各自承担什么角色？",
                    "en": "What role does each of Milvus's three external dependencies play?",
                },
                "opts": [
                    {
                        "zh": "etcd 存元数据与服务发现；对象存储（MinIO/S3）存 binlog 与索引；消息队列/WAL 承载写入日志",
                        "en": "etcd for metadata and service discovery; object storage (MinIO/S3) for binlogs and indexes; message queue/WAL carries the write log",
                    },
                    {"zh": "三者都用来存向量索引，互为备份", "en": "All three store the vector index as backups of each other"},
                    {"zh": "etcd 存向量、对象存储记日志、MQ 存元数据", "en": "etcd stores vectors, object storage records logs, MQ stores metadata"},
                    {"zh": "三者都只在 Cluster 模式下才需要", "en": "All three are needed only in Cluster mode"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Milvus 把三件难且通用的事外包：强一致的元数据/服务发现给 etcd，海量廉价持久的数据给对象存储，有序可重放的写入日志给消息队列/WAL。由此自身节点近乎无状态、可弹性伸缩",
                    "en": "Milvus outsources three hard, generic jobs: strongly-consistent metadata/service-discovery to etcd, cheap durable bulk data to object storage, ordered replayable write logs to the message queue/WAL. This makes its nodes nearly stateless and elastic",
                },
            },
            {
                "q": {
                    "zh": "根据 milvus.yaml 的注释，当 mq.type=default 时，Standalone 和 Cluster 模式分别默认用哪种消息队列？",
                    "en": "Per milvus.yaml comments, with mq.type=default, which MQ do Standalone and Cluster modes default to?",
                },
                "opts": [
                    {
                        "zh": "Standalone 默认 RocksMQ；Cluster 默认 Pulsar（且 Cluster 不支持 RocksMQ）",
                        "en": "Standalone defaults to RocksMQ; Cluster defaults to Pulsar (and Cluster doesn't support RocksMQ)",
                    },
                    {"zh": "两者都默认 Kafka", "en": "Both default to Kafka"},
                    {"zh": "Standalone 默认 Pulsar；Cluster 默认 RocksMQ", "en": "Standalone defaults to Pulsar; Cluster defaults to RocksMQ"},
                    {"zh": "两者都默认 Woodpecker", "en": "Both default to Woodpecker"},
                ],
                "answer": 0,
                "why": {
                    "zh": "yaml 注释给了精确优先级：standalone 为 rocksmq(默认)>Pulsar>Kafka>Woodpecker；cluster 为 Pulsar(默认)>Kafka>Woodpecker，rocksmq 在集群不支持。RocksMQ 内置于进程、无法跨节点共享，故只用于单机",
                    "en": "The yaml comments give the exact priority: standalone is rocksmq(default)>Pulsar>Kafka>Woodpecker; cluster is Pulsar(default)>Kafka>Woodpecker, with rocksmq unsupported. RocksMQ is in-process and can't be shared across nodes, so it's single-machine only",
                },
            },
            {
                "q": {
                    "zh": "对于一个全新的 Milvus 部署，官方在 milvus.yaml 注释里推荐显式使用哪种 MQ，为什么？",
                    "en": "For a brand-new Milvus deployment, which MQ do the milvus.yaml comments recommend explicitly using, and why?",
                },
                "opts": [
                    {
                        "zh": "Woodpecker —— 新一代内置 WAL，性能更好、运维更简单、成本更低；优先级靠后只是为了不改变老实例的行为",
                        "en": "Woodpecker - the next-gen built-in WAL with better performance, simpler ops, lower cost; it sits low in priority only to keep existing instances' behavior unchanged",
                    },
                    {"zh": "RocksMQ，因为它最古老最稳定", "en": "RocksMQ, because it's the oldest and most stable"},
                    {"zh": "Kafka，因为它是唯一支持集群的", "en": "Kafka, because it's the only one supporting clusters"},
                    {"zh": "随便哪个都行，注释没有推荐", "en": "Any will do; the comments make no recommendation"},
                ],
                "answer": 0,
                "why": {
                    "zh": "注释明确建议新实例显式用 Woodpecker，以获得更好性能、更简运维、更低成本。它在默认优先级里排最后，是为了兼容老实例（升级不改默认队列），但对新部署应主动选它",
                    "en": "The comments explicitly recommend new instances use Woodpecker for better performance, simpler ops, and lower cost. It ranks last in default priority to stay compatible with existing instances (no swapping their default on upgrade), but new deployments should pick it actively",
                },
            },
        ],
        "open": [
            {
                "zh": "你要把一个原型推上生产：数据将从百万级涨到十亿级、并发上升、需要高可用。说说你会从 Lite/Standalone/Cluster 中怎么演进，沿途哪些外部依赖（etcd、对象存储、MQ）需要从“内置/本地”换成“外部生产级集群”，以及为什么 API 几乎不用改。",
                "en": "You're taking a prototype to production: data grows from millions to billions, concurrency rises, HA is required. Describe how you'd evolve across Lite/Standalone/Cluster, which external dependencies (etcd, object storage, MQ) must move from 'built-in/local' to 'external production clusters' along the way, and why the API barely changes.",
            },
        ],
    },
    "09-control-vs-data-plane.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Proxy 既不存段也不存索引，为什么本课仍把它划进“数据面”而不是“控制面”？",
                    "en": "The Proxy stores neither segments nor indexes, so why does this lesson still place it in the 'data plane' rather than the 'control plane'?",
                },
                "opts": [
                    {
                        "zh": "因为控制面/数据面是按“是否承载用户吞吐”划分的，Proxy 站在每条请求的吞吐链路上；它能轻松扩缩是因为无状态，而非因为它属于控制面",
                        "en": "Because the split is by 'whether it carries user throughput'; the Proxy sits on every request's throughput path; it scales easily because it is stateless, not because it belongs to the control plane",
                    },
                    {"zh": "因为 Proxy 比协调者启动得更晚", "en": "Because the Proxy starts up later than the coordinators"},
                    {"zh": "因为只有控制面才允许存数据", "en": "Because only the control plane is allowed to store data"},
                    {"zh": "因为 Proxy 不实现任何 types.go 接口", "en": "Because the Proxy implements no interface in types.go"},
                ],
                "answer": 0,
                "why": {
                    "zh": "划分依据是“是否承载用户吞吐”，不是“是否存数据”。Proxy 站在吞吐链路上故属数据面；它无状态故可随意扩缩。把“承载吞吐”和“持有状态”分开看，才能准确理解每个组件的扩缩容策略",
                    "en": "The criterion is 'does it carry user throughput', not 'does it store data'. The Proxy is on the throughput path so it is data plane; it is stateless so it scales freely. Separating 'carries throughput' from 'holds state' is the key to each component's scaling story",
                },
            },
            {
                "q": {
                    "zh": "types.go 里所有组件共有的基座接口 Component 规定了哪四个方法？这反映了什么设计意图？",
                    "en": "What four methods does the shared base interface Component in types.go require, and what design intent does that reflect?",
                },
                "opts": [
                    {
                        "zh": "Init/Start/Stop/Register —— 一个分布式组件的“生命周期最小集”，其中 Register 是向 etcd 注册自己以支持服务发现",
                        "en": "Init/Start/Stop/Register - the minimal lifecycle of a distributed component, where Register registers itself in etcd for service discovery",
                    },
                    {"zh": "Read/Write/Flush/Compact，强调存储能力", "en": "Read/Write/Flush/Compact, emphasizing storage ability"},
                    {"zh": "Login/Logout/Auth/Rate，强调安全", "en": "Login/Logout/Auth/Rate, emphasizing security"},
                    {"zh": "Search/Insert/Delete/Query，强调数据操作", "en": "Search/Insert/Delete/Query, emphasizing data ops"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Component 抽出每个组件都需要的“生命周期最小集”：初始化、启动、停止、注册。用接口而非具体类型当契约，换来可替换（本地直连或 gRPC 代理）与可测试（mock）两大好处",
                    "en": "Component abstracts the minimal lifecycle every component needs: init, start, stop, register. Using an interface (not a concrete type) as the contract buys replaceability (direct or gRPC proxy) and testability (mocking)",
                },
            },
            {
                "q": {
                    "zh": "“MixCoord 把三个协调者打包进一个进程”——下面哪种描述最准确？",
                    "en": "'MixCoord packs the three coordinators into one process' - which description is most accurate?",
                },
                "opts": [
                    {
                        "zh": "RootCoord/DataCoord/QueryCoord 在逻辑上仍是三个角色，物理上是同一个可执行体；MixCoord 接口同时嵌入了三套 gRPC 服务",
                        "en": "RootCoord/DataCoord/QueryCoord remain three roles logically but are one executable physically; the MixCoord interface embeds all three gRPC services at once",
                    },
                    {"zh": "三个协调者被合并成一个新角色，原有职责消失", "en": "The three coordinators merge into a brand-new role and their old duties vanish"},
                    {"zh": "MixCoord 取代了所有数据面节点", "en": "MixCoord replaces all data-plane nodes"},
                    {"zh": "MixCoord 只是三个协调者的负载均衡器", "en": "MixCoord is merely a load balancer in front of the three coordinators"},
                ],
                "answer": 0,
                "why": {
                    "zh": "逻辑三角色、物理一进程：mixCoordImpl 同时持有三套协调者实现，MixCoord 接口嵌入三套 gRPC 服务。打包减少了部署与跨进程通信开销，但职责边界仍清晰",
                    "en": "Three roles logically, one process physically: mixCoordImpl holds all three coordinator impls and the MixCoord interface embeds all three gRPC services. Packaging cuts deployment and cross-process overhead while keeping duties distinct",
                },
            },
        ],
        "open": [
            {
                "zh": "假如把一条 search 的距离计算“顺手”放到协调者上执行，短期看似乎省了一次 RPC。请论证为什么这会破坏整个集群的稳定性，并用本课“三条边界纪律”解释正确做法。",
                "en": "Suppose you 'conveniently' ran a search's distance computation on a coordinator to save one RPC. Argue why this would wreck cluster stability, and use this lesson's 'three boundary disciplines' to explain the right approach.",
            },
        ],
    },
    "10-proxy.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Proxy 的任务调度器把请求分进 ddQueue / dmQueue / dqQueue 三个队列。这种物理隔离的主要目的是什么？",
                    "en": "The Proxy's task scheduler routes requests into three queues - ddQueue / dmQueue / dqQueue. What is the main purpose of this physical separation?",
                },
                "opts": [
                    {
                        "zh": "三类操作的排序约束与并发画像不同：DDL 需严格串行，DML/DQL 可高并发；分队列才能各按自己的约束调度，互不拖累",
                        "en": "The three kinds have different ordering constraints and concurrency profiles: DDL must be strictly serial, DML/DQL can be highly concurrent; separate queues let each schedule under its own rules without dragging the others",
                    },
                    {"zh": "为了让三类请求共享同一把全局锁", "en": "To make the three kinds share one global lock"},
                    {"zh": "为了把向量数据缓存在 Proxy 内存里", "en": "To cache vector data in the Proxy's memory"},
                    {"zh": "因为 gRPC 要求每种方法独占一个队列", "en": "Because gRPC requires each method to own a queue"},
                ],
                "answer": 0,
                "why": {
                    "zh": "DDL（建删表）必须串行以保证结构唯一；DML/DQL 追求高并发与低延迟。把不同排序与并发画像的任务物理隔离，各队列按自身约束调度，是稳定与性能的前提（另有 dcQueue 管 flush）",
                    "en": "DDL must be serial to keep structure single-versioned; DML/DQL want high concurrency and low latency. Isolating tasks of different ordering/concurrency profiles lets each queue schedule under its own constraint - essential for stability and speed (a dcQueue also handles flush)",
                },
            },
            {
                "q": {
                    "zh": "为什么说 Proxy 是 Milvus 里“最易扩展的一环”？",
                    "en": "Why is the Proxy called 'the most easily scaled' part of Milvus?",
                },
                "opts": [
                    {
                        "zh": "因为它无状态——不持有段或索引，只做校验/分派/归并；可像 Web 服务器一样随意加减实例，前面挂个负载均衡即可",
                        "en": "Because it is stateless - it holds no segments or indexes, only validates/dispatches/reduces; instances can be added or removed like web servers behind a load balancer",
                    },
                    {"zh": "因为它把所有数据都存在本地磁盘上", "en": "Because it stores all data on its local disk"},
                    {"zh": "因为它运行在协调者进程内部", "en": "Because it runs inside the coordinator process"},
                    {"zh": "因为它不需要鉴权与限流", "en": "Because it needs no auth or rate limiting"},
                ],
                "answer": 0,
                "why": {
                    "zh": "无状态是横向扩展的钥匙：Proxy 不持有用户数据，任何实例都能处理任何请求，于是可任意增减、负载均衡。这正呼应第 9 课“承载吞吐≠持有状态”的区分",
                    "en": "Statelessness is the key to horizontal scaling: holding no user data, any Proxy instance can serve any request, so instances scale freely behind a balancer. This echoes Lesson 9's 'carries throughput is not holds state'",
                },
            },
            {
                "q": {
                    "zh": "一条 search 请求在 Proxy 这里如何被处理成最终结果？",
                    "en": "How is a search request turned into a final result at the Proxy?",
                },
                "opts": [
                    {
                        "zh": "扇出（fan-out）到负责各分片的 QueryNode 各算局部 topK，再汇总回 Proxy 归并（reduce）成全局 topK",
                        "en": "Fan-out to the QueryNodes owning each shard, each computes a local topK, then results are gathered back at the Proxy and reduced into a global topK",
                    },
                    {"zh": "Proxy 自己在内存里扫描全部向量算出 topK", "en": "The Proxy scans all vectors in its own memory to compute topK"},
                    {"zh": "请求被转给 RootCoord 执行检索", "en": "The request is handed to RootCoord to run the search"},
                    {"zh": "只查询第一个分片，忽略其余", "en": "Only the first shard is queried and the rest ignored"},
                ],
                "answer": 0,
                "why": {
                    "zh": "分布式检索是“扇出—归并”：每个分片只看局部数据，算出局部 topK，Proxy 作为汇合点把它们正确合并成全局 topK，慢的那个分片决定整体延迟（reduce 细节见第 29 课）",
                    "en": "Distributed search is fan-out then reduce: each shard sees only local data and computes a local topK; the Proxy is the meeting point that merges them into a global topK, and the slowest shard sets the latency (reduce details in Lesson 29)",
                },
            },
        ],
        "open": [
            {
                "zh": "客户端要求“强一致”读（读到此刻为止的所有写入）。请说明 Proxy 如何用“保证时间戳（guarantee timestamp）”把这个要求传达给 QueryNode，以及它和一致性级别、延迟之间的取舍。",
                "en": "A client demands a 'strong' read (sees all writes up to now). Explain how the Proxy conveys this to QueryNodes via a 'guarantee timestamp', and the trade-off among consistency level, freshness, and latency.",
            },
        ],
    },
    "11-rootcoord.html": {
        "mcq": [
            {
                "q": {
                    "zh": "为什么 TSO 时间戳必须由 RootCoord 这“唯一一处”发放，而不能让各节点本地生成？",
                    "en": "Why must TSO timestamps be issued by RootCoord as 'the single point', rather than generated locally by each node?",
                },
                "opts": [
                    {
                        "zh": "唯一发放才能保证全局单调递增、互不冲突，给分布式事件一条统一时间线；本地各生成会乱序、撞号，破坏因果",
                        "en": "A single issuer guarantees globally monotonic, non-conflicting timestamps - one unified timeline for distributed events; local generation would reorder and collide, breaking causality",
                    },
                    {"zh": "因为本地时钟比 RootCoord 更快", "en": "Because local clocks are faster than RootCoord"},
                    {"zh": "因为时间戳必须等于墙上时钟的精确值", "en": "Because timestamps must equal the exact wall-clock value"},
                    {"zh": "因为节点没有访问 etcd 的权限", "en": "Because nodes have no permission to access etcd"},
                ],
                "answer": 0,
                "why": {
                    "zh": "全局唯一、单调递增的时间线是分布式排序与一致性的基础。集中发放才能保证这一点；TSO 概念上是“物理时间+逻辑计数”的 64 位混合值，单点发放并不成为瓶颈（靠批量）",
                    "en": "A globally unique, monotonic timeline underpins distributed ordering and consistency. Only a central issuer guarantees it; TSO is conceptually a 64-bit 'physical time + logical counter' hybrid, and a single issuer is no bottleneck thanks to batching",
                },
            },
            {
                "q": {
                    "zh": "RootCoord 发放 TSO/ID 时用“批量取一段 + 高水位持久化”，这种设计同时换来了什么？",
                    "en": "RootCoord issues TSO/ID with 'allocate a batch + persist a high watermark'. What does this design buy at once?",
                },
                "opts": [
                    {
                        "zh": "既快又防回退：内存内快速发放整段，只把高水位写 etcd；崩溃重启从高水位继续，绝不发出已用过的值",
                        "en": "Both fast and rollback-proof: hand out a whole batch from memory, persisting only the high watermark to etcd; after a crash it resumes from the watermark and never reissues a used value",
                    },
                    {"zh": "每发一个 ID 都同步写一次 etcd，保证绝对精确", "en": "Persist to etcd on every single ID for absolute precision"},
                    {"zh": "让 ID 可以回退以复用旧值", "en": "Lets IDs roll back to reuse old values"},
                    {"zh": "把发放工作下放给每个 DataNode", "en": "Delegates issuance to each DataNode"},
                ],
                "answer": 0,
                "why": {
                    "zh": "逐个持久化太慢，纯内存又会在重启后回退。批量分配让发放走内存极快，高水位持久化保证崩溃后不回退、不重复。这是“性能 vs 安全”的经典折中",
                    "en": "Per-value persistence is too slow; pure in-memory rolls back on restart. Batch allocation keeps issuance in-memory fast, while the persisted high watermark prevents rollback and duplication after a crash - a classic performance-vs-safety trade-off",
                },
            },
            {
                "q": {
                    "zh": "为什么所有 DDL（建/删集合、分区、别名、库）都要收口到 RootCoord 串行登记？",
                    "en": "Why must all DDL (create/drop collection, partition, alias, database) funnel through RootCoord for serial registration?",
                },
                "opts": [
                    {
                        "zh": "串行登记保证集合结构只有一个权威版本，避免并发改结构产生冲突；元数据落 IMetaTable，背靠 etcd 持久化、启动回放",
                        "en": "Serial registration guarantees one authoritative version of the structure, avoiding conflicts from concurrent schema changes; metadata lands in IMetaTable, persisted to etcd and replayed on startup",
                    },
                    {"zh": "因为 DDL 比 DML 更耗 CPU", "en": "Because DDL is more CPU-heavy than DML"},
                    {"zh": "因为只有 RootCoord 能访问对象存储", "en": "Because only RootCoord can access object storage"},
                    {"zh": "因为 DDL 必须绕过 etcd", "en": "Because DDL must bypass etcd"},
                ],
                "answer": 0,
                "why": {
                    "zh": "结构（schema）必须唯一权威，否则两个并发建表/改表会互相覆盖。单点串行登记是最简单可靠的保证；元数据持久化在 etcd，重启回放重建内存视图",
                    "en": "The schema must be singly authoritative, or two concurrent DDLs would clobber each other. A single serial registrar is the simplest reliable guarantee; metadata persisted in etcd is replayed to rebuild the in-memory view on restart",
                },
            },
        ],
        "open": [
            {
                "zh": "RootCoord 是“唯一、权威、串行”的点，听起来像单点瓶颈与单点故障。请结合“批量发放”“MixCoord 多副本/选主”“etcd 持久化”三点，论证为什么它在实践中既不慢也不脆。",
                "en": "RootCoord is a 'single, authoritative, serial' point, which sounds like a bottleneck and a single point of failure. Using 'batch issuance', 'MixCoord replicas/leader election', and 'etcd persistence', argue why it is in practice neither slow nor fragile.",
            },
        ],
    },
    "12-datacoord.html": {
        "mcq": [
            {
                "q": {
                    "zh": "DataCoord 维护的段状态机大致是怎样的？谁来执行真正的落盘与合并？",
                    "en": "What is DataCoord's segment state machine roughly, and who actually performs the flush and compaction?",
                },
                "opts": [
                    {
                        "zh": "Growing → Sealed → Flushing → Flushed →（Dropped）；DataCoord 只分配段、记账状态流转，落盘/合并/建索引交给 datanode worker 执行",
                        "en": "Growing → Sealed → Flushing → Flushed → (Dropped); DataCoord only allocates segments and bookkeeps transitions, while flush/compaction/index-build run on datanode workers",
                    },
                    {"zh": "段只有“存在”和“删除”两态，由 Proxy 执行落盘", "en": "Segments have only 'exists' and 'deleted', and the Proxy flushes them"},
                    {"zh": "DataCoord 自己执行所有落盘与合并", "en": "DataCoord itself performs all flush and compaction"},
                    {"zh": "段状态由每个 QueryNode 各自决定", "en": "Each QueryNode decides segment state on its own"},
                ],
                "answer": 0,
                "why": {
                    "zh": "决策与执行分离：DataCoord 是写入侧的总调度，维护 SegmentState_* 状态机并分配段，但真正的 IO（落盘、compaction、建索引）由 datanode worker 干。这正是控制面/数据面分工的体现",
                    "en": "Decide vs execute: DataCoord is the write-side scheduler maintaining the SegmentState_* machine and allocating segments, but the real IO (flush, compaction, index build) runs on datanode workers - the control/data plane split in action",
                },
            },
            {
                "q": {
                    "zh": "关于“索引构建”，下面哪条符合当前 Milvus 的真实架构？",
                    "en": "Regarding 'index building', which statement matches Milvus's actual current architecture?",
                },
                "opts": [
                    {
                        "zh": "没有独立的 indexnode；索引构建 worker 已并入 datanode（DataNodeClient 内嵌 IndexNodeClient），由 DataCoord 调度",
                        "en": "There is no standalone indexnode; the index-build worker is folded into the datanode (DataNodeClient embeds IndexNodeClient), scheduled by DataCoord",
                    },
                    {"zh": "有一个独立的 indexnode 进程专门建索引", "en": "A dedicated standalone indexnode process builds indexes"},
                    {"zh": "索引由 Proxy 在返回结果前临时构建", "en": "Indexes are built ad hoc by the Proxy before returning results"},
                    {"zh": "索引由 etcd 负责构建与存储", "en": "Indexes are built and stored by etcd"},
                ],
                "answer": 0,
                "why": {
                    "zh": "这是常见误解的纠正点：Milvus 已没有独立 indexnode，构建 worker 并入 datanode，DataCoord 负责调度。索引文件最终存对象存储，元数据记录其引用",
                    "en": "A common-misconception fix: Milvus has no standalone indexnode; the build worker is merged into the datanode and DataCoord schedules it. Index files end up in object storage, with metadata recording their reference",
                },
            },
            {
                "q": {
                    "zh": "“Flushed 即不可变”意味着删除和更新如何实现？",
                    "en": "'Flushed means immutable' - so how are deletes and updates implemented?",
                },
                "opts": [
                    {
                        "zh": "落盘后的段只读；删除/更新以新写入 + delta 形式追加，查询时再合并——只追加、不就地改",
                        "en": "A flushed segment is read-only; deletes/updates are appended as new writes + deltas and merged at query time - append-only, never in-place edits",
                    },
                    {"zh": "直接打开旧 binlog 就地覆盖对应行", "en": "Open the old binlog and overwrite the row in place"},
                    {"zh": "删除会立刻物理擦除整个段", "en": "A delete instantly physically erases the whole segment"},
                    {"zh": "更新要求先把段状态退回 Growing", "en": "An update requires reverting the segment back to Growing"},
                ],
                "answer": 0,
                "why": {
                    "zh": "不可变 + 只追加是第 7 课“日志即数据”的延续：删除记 delta、更新写新值，查询时合并生效；compaction 在后台把小段与 delete 整理掉，用后台整理换前台查询轻快",
                    "en": "Immutable + append-only continues Lesson 7's 'log-as-data': deletes record deltas, updates write new values, merged at query time; compaction tidies small segments and deletes in the background, trading background work for a lighter foreground query",
                },
            },
        ],
        "open": [
            {
                "zh": "段太小太多会拖慢查询，compaction 能合并它们却要消耗 IO 与 CPU。请设计你心中的 compaction 触发策略（按段数、按大小、按 delete 比例……），并说明它如何平衡“前台查询轻快”与“后台开销可控”。",
                "en": "Too many tiny segments slow queries; compaction merges them but burns IO and CPU. Design your own compaction trigger policy (by segment count, by size, by delete ratio...) and explain how it balances 'a light foreground query' against 'bounded background cost'.",
            },
        ],
    },
    "13-querycoord.html": {
        "mcq": [
            {
                "q": {
                    "zh": "QueryCoordV2 的世界从“load”开始。为什么“存了”不等于“能查”？",
                    "en": "QueryCoordV2's world starts at 'load'. Why does 'stored' not equal 'searchable'?",
                },
                "opts": [
                    {
                        "zh": "段与索引必须被加载进 QueryNode 内存才可检索；load 把数据搬进内存，release 再把内存还回去",
                        "en": "Segments and indexes must be loaded into QueryNode memory to be retrievable; load brings data into memory, release returns it",
                    },
                    {"zh": "因为对象存储默认禁止读取", "en": "Because object storage forbids reads by default"},
                    {"zh": "因为查询必须先经过 DataCoord 审批", "en": "Because queries must first be approved by DataCoord"},
                    {"zh": "因为存储后的段会自动加密，需解密才可查", "en": "Because stored segments are auto-encrypted and need decryption to query"},
                ],
                "answer": 0,
                "why": {
                    "zh": "检索发生在 QueryNode 内存里。落盘只是“持久化”，要可查必须把段与索引加载进内存。load/release 就是这层“可检索性”的开关，也是 QueryCoord 调度的起点",
                    "en": "Search happens in QueryNode memory. Flushing only persists; to be searchable, segments and indexes must be loaded into memory. load/release toggles this 'searchability' and is the starting point of QueryCoord's scheduling",
                },
            },
            {
                "q": {
                    "zh": "QueryCoordV2 健壮性的核心是“distribution 向 target 收敛”。这句话最准确的含义是？",
                    "en": "The core of QueryCoordV2's robustness is 'distribution converges to target'. What does this most precisely mean?",
                },
                "opts": [
                    {
                        "zh": "target=期望布局，distribution=实际已加载状态；observer 持续比对并纠偏，让实际不断逼近期望——声明终态、持续校正",
                        "en": "target = desired layout, distribution = actual loaded state; observers continually compare and correct so the actual keeps approaching the desired - declare the end state, keep correcting",
                    },
                    {"zh": "把所有段一次性加载到一个节点上", "en": "Load all segments onto one node at once"},
                    {"zh": "distribution 是配置文件，target 是运行日志", "en": "distribution is a config file, target is a runtime log"},
                    {"zh": "两者必须时刻完全相等，否则集群停机", "en": "The two must always be exactly equal or the cluster halts"},
                ],
                "answer": 0,
                "why": {
                    "zh": "这是声明式调度：你描述“想要的终态（target）”，系统观测“实际状态（distribution）”并持续纠偏。节点崩溃、负载倾斜都靠这套收敛自动修复，而非一次性命令式操作",
                    "en": "This is declarative scheduling: you describe the desired end state (target), and the system observes the actual state (distribution) and continually corrects. Node crashes and skew are auto-healed by convergence, not one-shot imperative commands",
                },
            },
            {
                "q": {
                    "zh": "QueryCoordV2 用“副本（replica）”买到了什么，代价是什么？",
                    "en": "What do 'replicas' buy QueryCoordV2, and at what cost?",
                },
                "opts": [
                    {
                        "zh": "同一集合在不同节点各加载一份，换来高可用（一份挂了还有别份）与吞吐（并行分担查询），代价是 N 倍内存",
                        "en": "The same collection loaded once each on different nodes, buying HA (one dies, others survive) and throughput (parallel query sharing), at the cost of N times the memory",
                    },
                    {"zh": "把数据压缩以省内存，但会降低召回", "en": "Compresses data to save memory but lowers recall"},
                    {"zh": "副本只用于备份，不参与查询", "en": "Replicas are backup-only and never serve queries"},
                    {"zh": "副本能减少总内存占用", "en": "Replicas reduce total memory usage"},
                ],
                "answer": 0,
                "why": {
                    "zh": "副本是“以内存换可用性与吞吐”：每份副本独立加载在不同节点，节点死了还有别的副本顶上，多副本还能并行分担查询；代价是内存随副本数线性增长",
                    "en": "Replicas trade memory for availability and throughput: each replica loads independently on different nodes, so a node death is survived and queries can be shared in parallel; the cost is memory growing linearly with replica count",
                },
            },
        ],
        "open": [
            {
                "zh": "你的集群里某个 QueryNode 反复成为查询热点（CPU 长期顶满），而其它节点很闲。请用“balancer + distribution/target”解释 QueryCoordV2 会如何自动缓解，并说说在什么情况下它仍可能无能为力（需要人为干预）。",
                "en": "In your cluster one QueryNode keeps becoming a query hotspot (CPU pinned) while others sit idle. Using 'balancer + distribution/target', explain how QueryCoordV2 auto-mitigates this, and when it might still be powerless (needing human intervention).",
            },
        ],
    },
    "14-metadata-and-coordination.html": {
        "mcq": [
            {
                "q": {
                    "zh": "一次 CreateCollection 从协调者落到 etcd，要穿过哪几层？每层的角色是什么？",
                    "en": "From coordinator down to etcd, which layers does a CreateCollection traverse, and what is each layer's role?",
                },
                "opts": [
                    {
                        "zh": "协调者（业务动词）→ metastore 的 Catalog 接口（翻译成键值语言）→ kv 原语（Save/MultiSave）→ etcd / 对象存储；每下一层更通用、更不懂业务",
                        "en": "coordinator (business verb) → metastore's Catalog interface (translate to key-value language) → kv primitives (Save/MultiSave) → etcd / object storage; each layer down is more generic, less business-aware",
                    },
                    {"zh": "Proxy 直接把 SQL 写进 etcd", "en": "The Proxy writes SQL straight into etcd"},
                    {"zh": "协调者直接拼 etcd 的 key 并写入，无中间层", "en": "The coordinator hand-assembles etcd keys and writes with no middle layer"},
                    {"zh": "先写对象存储，再由 etcd 异步同步", "en": "Write object storage first, then etcd syncs asynchronously"},
                ],
                "answer": 0,
                "why": {
                    "zh": "三层落地：协调者说业务语言，Catalog 翻译成键值语言并拆解对象，kv 提供 Save/MultiSave 等原语，最终写 etcd。每层抽象更通用，故换后端时上层不必改——分层解耦",
                    "en": "Three layers: coordinators speak business language, Catalog translates and decomposes objects, kv offers Save/MultiSave primitives, finally writing etcd. Each layer is more generic, so swapping the backend leaves upper layers untouched - layered decoupling",
                },
            },
            {
                "q": {
                    "zh": "为什么向量 binlog 与索引文件要放对象存储，而不能塞进 etcd？",
                    "en": "Why must vector binlogs and index files go to object storage rather than being stuffed into etcd?",
                },
                "opts": [
                    {
                        "zh": "etcd 是 Raft 强一致存储，对单值大小与总量有保守上限；塞大块数据会拖垮 watch 与选主。大块数据应下沉对象存储，etcd 只留路径引用",
                        "en": "etcd is a Raft strongly-consistent store with conservative caps on value size and total volume; stuffing bulk data drags down watch and leader election. Bulk data should sink to object storage, with etcd keeping only a path reference",
                    },
                    {"zh": "对象存储比 etcd 更强一致，所以放大数据", "en": "Object storage is more strongly consistent than etcd, so bulk goes there"},
                    {"zh": "etcd 不支持二进制，只能存文本", "en": "etcd cannot store binary, only text"},
                    {"zh": "因为索引文件必须可被 SQL 查询", "en": "Because index files must be SQL-queryable"},
                ],
                "answer": 0,
                "why": {
                    "zh": "分界依据体量与角色：小而关键、需强一致与 watch 的元数据进 etcd；大而笨重只需可靠存放的数据/索引进对象存储。把强一致用在最该用的地方，别让它为海量数据买单",
                    "en": "The divide is by size and role: small, critical metadata needing strong consistency and watch goes to etcd; bulky data/index needing only reliable storage goes to object storage. Spend strong consistency where it matters, don't make it pay for massive data",
                },
            },
            {
                "q": {
                    "zh": "组件用带租约的 session 注册到 etcd，而不是写一个 alive=true 标记。这种“租约+续约”设计的关键好处是？",
                    "en": "Components register a leased session in etcd instead of writing an alive=true flag. What is the key benefit of this 'lease + renewal' design?",
                },
                "opts": [
                    {
                        "zh": "它把“活着”变成需要持续续约才能维持的状态；进程被 kill-9 或断电时心跳一停，租约到期 etcd 自动清记录，无需任何人善后",
                        "en": "It makes 'alive' a state that must be continually renewed; on kill-9 or power loss the heartbeat stops, the lease expires, and etcd auto-purges the record with no cleanup by anyone",
                    },
                    {"zh": "它让 session 里直接存下查询数据以加速", "en": "It stores query data inside the session to speed things up"},
                    {"zh": "它要求每个节点退出前必须手动注销", "en": "It requires every node to manually deregister before exit"},
                    {"zh": "它使 search 流量改为经过 etcd 中转", "en": "It routes search traffic through etcd"},
                ],
                "answer": 0,
                "why": {
                    "zh": "“故障即默认”：系统假设节点随时可能突然失联，没人有机会改标记。租约让活着成为需要不断证明的例外，心跳停则记录自动消失。session 存的是地址不是数据，流量仍走直连",
                    "en": "'Failure is the default': the system assumes a node may vanish suddenly with no chance to flip a flag. A lease makes being alive an exception that must be continually proven; stop the heartbeat and the record auto-vanishes. A session stores an address, not data; traffic still goes direct",
                },
            },
        ],
        "open": [
            {
                "zh": "“watch 是通知，不是真相。”请解释这句话：当协调者的 watch 因网络抖动断开重连、中间漏掉若干事件时，Milvus 用什么手段（revision、先全量后增量）保证节点最终仍拿到正确的分配，而不会“漏接活”。",
                "en": "'Watch is a notification, not the truth.' Explain this: when a coordinator's watch drops and reconnects on a network jitter and misses some events, what mechanisms (revision; full-pull-then-incremental) keep nodes eventually getting the correct assignment without 'missing work'.",
            },
        ],
    },
    "15-insert-via-proxy.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Proxy 处理 insert 时为什么要先用 <code>checkPrimaryFieldData</code> 敲定主键，再做分片？",
                    "en": "Why does the Proxy settle the primary key with <code>checkPrimaryFieldData</code> first, before sharding the insert?",
                },
                "opts": [
                    {
                        "zh": "因为“把哪一行发到哪个 vchannel”靠的是对主键哈希（assignChannelsByPK），没有确定的主键就无法路由；autoID 时还要在此为每行分配全局唯一主键",
                        "en": "Because routing 'which row to which vchannel' hashes the primary key (assignChannelsByPK); without a settled key there is no routing, and with auto-ID this step also assigns a globally unique key per row",
                    },
                    {"zh": "因为主键决定向量用哪种距离度量", "en": "Because the primary key decides which distance metric the vectors use"},
                    {"zh": "因为不先定主键就无法压缩向量", "en": "Because vectors can't be compressed without a key first"},
                    {"zh": "因为段 ID 必须等于主键", "en": "Because the segment ID must equal the primary key"},
                ],
                "answer": 0,
                "why": {
                    "zh": "主键既是身份也是路由依据：分片用它哈希，删除/更新用它对齐同一行。所以必须在写入前敲定，autoID 时在此分配，之后整条流水线都默认主键齐全",
                    "en": "The key is both identity and routing basis: sharding hashes it, deletes/updates align the same row by it. So it must be settled before the write (auto-ID allocates here); the whole pipeline then trusts keys are complete",
                },
            },
            {
                "q": {
                    "zh": "Proxy 打包插入消息时把 segmentID 留空（填 0），把“分段”推迟到 StreamingNode。这样设计最主要的好处是？",
                    "en": "The Proxy leaves segmentID empty (0) when packing, deferring segmenting to the StreamingNode. What is the main benefit?",
                },
                "opts": [
                    {
                        "zh": "段是有状态的：能装多少、何时封口取决于该分片当前进度，只有独占该 pchannel 的 StreamingNode 最清楚。Proxy 无状态可多开，让它定段会导致并发冲突",
                        "en": "A segment is stateful: capacity and seal timing depend on the shard's current progress, known best by the StreamingNode that exclusively owns that pchannel. The Proxy is stateless and replicable, so letting it decide segments would cause concurrent clashes",
                    },
                    {"zh": "这样可以省掉时间戳", "en": "It lets the system skip timestamps"},
                    {"zh": "因为 Proxy 不知道集合有几个分片", "en": "Because the Proxy doesn't know how many shards a collection has"},
                    {"zh": "因为段 ID 由客户端 SDK 生成", "en": "Because segment IDs are generated by the client SDK"},
                ],
                "answer": 0,
                "why": {
                    "zh": "“无状态归无状态、有状态归有状态”：把段分配收归到单一、独占该通道的 StreamingNode，既保证一致性，又让可横向扩展的 Proxy 保持轻量",
                    "en": "'Stateless to the stateless, stateful to the stateful': centralizing segment assignment in the single StreamingNode that owns the channel keeps assignment consistent and the horizontally-scalable Proxy lightweight",
                },
            },
            {
                "q": {
                    "zh": "一次 insert 返回成功，准确含义是什么？",
                    "en": "When an insert returns success, what does it precisely mean?",
                },
                "opts": [
                    {
                        "zh": "这批消息已可靠追加进 WAL（单一事实来源）；即使 StreamingNode 立刻宕机，重启也能从 WAL 回放不丢数据。它不等于已落盘成段文件——那是后台异步做的",
                        "en": "The batch was reliably appended to the WAL (single source of truth); even if the StreamingNode crashes at once, it replays from the WAL on restart with no loss. It does NOT mean flushed into segment files — that is done asynchronously in the background",
                    },
                    {"zh": "数据已经写进对象存储的 binlog 文件", "en": "The data is already in binlog files in object storage"},
                    {"zh": "数据已经构建好索引可被检索", "en": "An index is already built and the data is searchable"},
                    {"zh": "数据已经在所有副本上落盘", "en": "The data is persisted on all replicas"},
                ],
                "answer": 0,
                "why": {
                    "zh": "WAL 是单一事实来源：进了日志就持久、可回放，所以“写成功 = 已记日志”而非“已落盘成段”。落盘、建索引都在后台沿 WAL 异步推进",
                    "en": "The WAL is the single source of truth: once logged, data is durable and replayable, so 'write success = logged' not 'flushed to a segment'. Persisting and indexing proceed asynchronously off the WAL",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说 insert 的“原子批”只保证“同一 vchannel 的消息作为一个事务一起写”，跨 vchannel 并不保证严格原子。请想一想：为什么 Milvus 在这里选择务实取舍而不是上两阶段提交？这种取舍在什么场景下可能让用户观察到“部分可见”，又为什么对绝大多数 insert 影响很小？",
                "en": "This lesson notes an insert's 'atomic batch' only guarantees 'messages of the same vchannel are written together as one transaction'; strict atomicity is not guaranteed across vchannels. Think: why does Milvus pick this pragmatic trade-off over a two-phase commit? In what scenario might a user observe 'partial visibility', and why is the impact tiny for the vast majority of inserts?",
            },
        ],
    },
    "16-streaming-and-wal.html": {
        "mcq": [
            {
                "q": {
                    "zh": "“WAL 是单一事实来源”这句话，最准确的含义是？",
                    "en": "What does 'the WAL is the single source of truth' most precisely mean?",
                },
                "opts": [
                    {
                        "zh": "所有变更先写进 WAL 才算数；段、索引、内存里可检索的数据都是回放 WAL 得到的派生形态，崩溃后从 WAL 重放即可重建",
                        "en": "Every mutation must enter the WAL first to count; segments, indexes, and in-memory searchable data are derivatives obtained by replaying the WAL, and can be rebuilt by replay after a crash",
                    },
                    {"zh": "WAL 只是崩溃恢复用的备份，平时不参与读写", "en": "The WAL is just a crash-recovery backup, idle during normal reads/writes"},
                    {"zh": "WAL 保存的是查询结果缓存", "en": "The WAL stores a cache of query results"},
                    {"zh": "WAL 等价于 etcd 里的元数据", "en": "The WAL is equivalent to the metadata in etcd"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Milvus 把传统库“表是主体、日志是保险”的关系倒了过来：日志升格为权威副本，段/索引都是它的物化视图。守住 WAL 就守住了数据",
                    "en": "Milvus inverts the traditional 'table is primary, log is insurance' relation: the log is promoted to the authoritative copy, and segments/indexes are its materialized views. Guard the WAL and you guard the data",
                },
            },
            {
                "q": {
                    "zh": "PChannel、VChannel、CChannel 三者的关系，下面哪个说法对？",
                    "en": "Which statement correctly describes the relation among PChannel, VChannel, and CChannel?",
                },
                "opts": [
                    {
                        "zh": "VChannel 是逻辑分片（多）、PChannel 是物理日志（少，一条=一个 topic），多个 VChannel 复用一条 PChannel；CChannel 是集群级单例控制通道，做跨 PChannel 全局排序",
                        "en": "VChannel is a logical shard (many), PChannel is a physical log (few, one = one topic), many VChannels multiplex one PChannel; CChannel is a cluster-wide singleton control channel for global ordering across PChannels",
                    },
                    {"zh": "每个 VChannel 独占一条物理 topic，一一对应", "en": "Each VChannel owns its own physical topic, one-to-one"},
                    {"zh": "PChannel 是逻辑的、VChannel 是物理的", "en": "PChannel is logical and VChannel is physical"},
                    {"zh": "CChannel 用于承载普通 insert 数据", "en": "CChannel carries ordinary insert data"},
                ],
                "answer": 0,
                "why": {
                    "zh": "topic 是稀缺资源，集合/分片可能成千上万，一对一会爆炸。复用 PChannel 用固定物理资源承载弹性逻辑分片；TimeTick 定义在 PChannel 上，故分片内有序天然保证，跨片全序交给 CChannel",
                    "en": "Topics are scarce and collections/shards can number in the thousands, so one-to-one would explode. Multiplexing carries elastic logical shards on fixed physical resources; TimeTick is defined per PChannel, so in-shard order is natural and cross-shard total order is delegated to the CChannel",
                },
            },
            {
                "q": {
                    "zh": "关于 StreamingNode 与 StreamingCoord 的分工，哪个描述正确？",
                    "en": "Which describes the StreamingNode vs StreamingCoord division correctly?",
                },
                "opts": [
                    {
                        "zh": "StreamingNode 独占管理一批 PChannel（TimeTick/事务、段分配、RecoveryStorage 等执行职责）；StreamingCoord 是单例、跑在 RootCoord 进程里，做通道分配与跨通道广播等决策",
                        "en": "The StreamingNode exclusively manages a subset of PChannels (execution duties: TimeTick/txn, segment assignment, RecoveryStorage); the StreamingCoord is a singleton running inside the RootCoord process, doing decisions like channel assignment and cross-channel broadcast",
                    },
                    {"zh": "StreamingCoord 是独立进程，StreamingNode 只读不写", "en": "The StreamingCoord is a standalone process and the StreamingNode is read-only"},
                    {"zh": "两者都跑在 Proxy 里", "en": "Both run inside the Proxy"},
                    {"zh": "StreamingNode 负责分配通道，StreamingCoord 负责搬运日志", "en": "The StreamingNode assigns channels and the StreamingCoord hauls logs"},
                ],
                "answer": 0,
                "why": {
                    "zh": "又一次“控制面决策、数据面干活”：Coord 决定谁负责哪条通道、协调全局原子操作，Node 真正承载并消费日志、分配段、做恢复。Coord 与 RootCoord 合署，省一次跨进程跳转",
                    "en": "Once more 'control plane decides, data plane does work': the Coord decides who owns which channel and coordinates global-atomic ops; the Node actually carries and consumes the log, assigns segments, recovers. Co-locating the Coord with RootCoord saves a cross-process hop",
                },
            },
        ],
        "open": [
            {
                "zh": "“日志即数据”带来的最大回报是解耦与弹性：新增一个消费者（如 QueryNode），只要从 WAL 某个位置开始消费、慢慢追上即可，不必停机搬数据。请结合 TimeTick 的“水位线”机制，解释一个落后的消费者是如何判断“我已经追上了”的，以及为什么即使某条通道暂时没有业务写入，消费端的可见性也不会被卡住。",
                "en": "The biggest payoff of 'log as data' is decoupling and elasticity: adding a consumer (e.g. a QueryNode) just needs it to start consuming from some WAL position and gradually catch up, with no downtime or data hauling. Using TimeTick's 'watermark' mechanism, explain how a lagging consumer decides 'I have caught up', and why consumer visibility does not stall even when a channel has no business writes for a while.",
            },
        ],
    },
    "17-datanode-and-flush.html": {
        "mcq": [
            {
                "q": {
                    "zh": "WAL 里的 insert 消息，为什么要先在内存里攒成 growing 段、而不是来一行就往对象存储写一行？",
                    "en": "Why do WAL insert messages first accumulate into an in-memory growing segment instead of writing one file per arriving row to object storage?",
                },
                "opts": [
                    {
                        "zh": "对象存储擅长少而大的文件、怕海量小文件；growing 段用内存缓冲把“碎写”聚合成“批写”，攒满再一次性落成大 binlog，既保护后端又摊薄每行成本",
                        "en": "Object storage loves few large files and hates many small ones; the growing segment uses an in-memory buffer to aggregate 'scattered writes' into 'batched writes', persisting one big binlog when full — protecting the backend and amortizing per-row cost",
                    },
                    {"zh": "因为内存比对象存储更持久可靠", "en": "Because memory is more durable and reliable than object storage"},
                    {"zh": "因为对象存储不支持向量数据", "en": "Because object storage cannot store vector data"},
                    {"zh": "因为 growing 段不需要主键", "en": "Because growing segments need no primary key"},
                ],
                "answer": 0,
                "why": {
                    "zh": "这是 LSM-Tree 类引擎的共有智慧：先在内存攒（memtable），再批量落盘（SSTable）。growing 段还吸收了写入与落盘之间的速率差，可靠性由背后的 WAL 兜底（丢了可重放）",
                    "en": "This is the wisdom of LSM-tree engines: accumulate in memory (memtable), then batch-persist (SSTable). The growing segment also absorbs the write-vs-persist rate mismatch, with reliability backstopped by the WAL (lost data is replayable)",
                },
            },
            {
                "q": {
                    "zh": "在当前流式架构下，“消费 WAL → 攒 growing 段 → flush 成 binlog”这条落盘流水线主要由谁驱动？",
                    "en": "Under the current streaming architecture, who mainly drives the 'consume WAL → grow segment → flush into binlogs' persistence pipeline?",
                },
                "opts": [
                    {
                        "zh": "StreamingNode 的 flusher：它消费自己负责的 PChannel 上的 WAL，复用 flushcommon 的 writebuffer/syncmgr 落盘，并用 RecoveryStorage 记检查点；DataNode 退居二线、专注后台 compaction",
                        "en": "The StreamingNode's flusher: it consumes the WAL on its own PChannels, reuses flushcommon's writebuffer/syncmgr to persist, and checkpoints via RecoveryStorage; the DataNode steps back to focus on background compaction",
                    },
                    {"zh": "DataNode 独立订阅消息队列、攒段落盘（旧模型）", "en": "The DataNode independently subscribes the MQ and persists segments (the old model)"},
                    {"zh": "Proxy 在返回客户端前同步落盘", "en": "The Proxy persists synchronously before returning to the client"},
                    {"zh": "DataCoord 亲自把数据写进对象存储", "en": "DataCoord writes data into object storage itself"},
                ],
                "answer": 0,
                "why": {
                    "zh": "新模型把“写 WAL”和“消费 WAL 落盘”收拢到同一侧：段分配（写入时）与落盘（消费时）同进程，状态一致、恢复干净。这是“把有状态职责收归独占该通道的单一节点”的体现",
                    "en": "The new model gathers 'write WAL' and 'consume WAL to persist' on the same side: segment assignment (at write) and persistence (at consume) share a process — consistent state, clean recovery. This embodies 'gather stateful duties into the single node that owns the channel'",
                },
            },
            {
                "q": {
                    "zh": "段的 flush 同时设置“按大小”和“按时间”两个触发条件，主要原因是？",
                    "en": "Why does segment flush set both a 'by size' and a 'by time' trigger?",
                },
                "opts": [
                    {
                        "zh": "两条件取先到者，分别堵住两种坏情况：只看大小会让慢分片的段迟迟攒不满、落不了盘；只看时间会让热分片的段瞬间膨胀到内存扛不住",
                        "en": "Whichever comes first triggers, each plugging a bad case: size-only lets a slow shard's segment never fill and never persist; time-only lets a hot shard's segment balloon beyond memory",
                    },
                    {"zh": "因为大小和时间必须同时满足才能 flush", "en": "Because both size and time must be satisfied to flush"},
                    {"zh": "为了让 binlog 文件大小完全相等", "en": "To make all binlog files exactly equal in size"},
                    {"zh": "因为对象存储要求固定的写入间隔", "en": "Because object storage requires a fixed write interval"},
                ],
                "answer": 0,
                "why": {
                    "zh": "“用两个维度的阈值夹出健康工作区间”：大小兜住快分片不撑爆内存，时间兜住慢分片不饿着不落盘，取先到者。此外还有显式 flush（建索引/释放前确保落盘）",
                    "en": "'Use thresholds on two dimensions to bracket a healthy range': size keeps the fast shard from blowing memory, time keeps the slow shard from starving unpersisted, take whichever is first. There is also explicit flush (ensure persistence before index build/release)",
                },
            },
        ],
        "open": [
            {
                "zh": "本课强调一个段在生命周期里可能多次 flush，于是对象存储里一个段往往对应“一组”而非“一个”binlog 文件——这正是后面需要 compaction 的根源。请顺着这个线索想一想：随着不断 flush，小 binlog 越积越多会给“检索”带来什么具体开销？compaction 把它们合并后，又分别改善了哪些方面？（可结合第 7 课段的列式布局与即将到来的第 19 课。）",
                "en": "This lesson stresses a segment may flush multiple times in its life, so a segment in object storage often maps to 'a set' of binlog files, not one — the very root of why compaction is later needed. Follow this thread: as flushes pile up small binlogs, what concrete cost does this impose on 'retrieval'? After compaction merges them, which aspects improve and how? (Tie in Lesson 7's columnar layout and the upcoming Lesson 19.)",
            },
        ],
    },
    "18-binlog-and-storage.html": {
        "mcq": [
            {
                "q": {
                    "zh": "一个 sealed 段在对象存储里通常对应哪几类产物，它们各装什么？",
                    "en": "What kinds of artifact does a sealed segment usually map to in object storage, and what does each hold?",
                },
                "opts": [
                    {
                        "zh": "insert binlog（每字段一个、列式数据）、delete binlog（作废主键+删除时间戳的墓碑）、stats binlog（主键 min/max + 布隆过滤器）、index file（ANN 索引）",
                        "en": "insert binlog (one per field, columnar data), delete binlog (tombstones of void PK + delete timestamp), stats binlog (PK min/max + bloom filter), index file (the ANN index)",
                    },
                    {"zh": "只有一个把所有字段按行打包的大文件", "en": "Just one big file packing all fields by row"},
                    {"zh": "一个段一个文件，删除时原地改写", "en": "One file per segment, rewritten in place on delete"},
                    {"zh": "只有向量数据，标量字段不落盘", "en": "Only vector data; scalar fields are not persisted"},
                ],
                "answer": 0,
                "why": {
                    "zh": "insert 是真身、delete 是叠加层（墓碑，不真删）、stats 是加速卡（让查询跳过无关段）、index 是另一种视角。序列化由 internal/storage 的 PayloadWriter/InsertCodec/DeleteCodec 完成",
                    "en": "Insert is the real body, delete an overlay (tombstone, no true erase), stats an acceleration card (lets queries skip irrelevant segments), index another viewpoint. Serialization is by internal/storage's PayloadWriter/InsertCodec/DeleteCodec",
                },
            },
            {
                "q": {
                    "zh": "为什么 insert binlog 采用列式（每字段一个文件），而不是按行存？",
                    "en": "Why is the insert binlog columnar (one file per field) rather than row-stored?",
                },
                "opts": [
                    {
                        "zh": "契合向量检索的访问模式（整列连续扫描、可送 SIMD/GPU）、同列同类型压缩率高、查询可列裁剪只读需要的列；加列也只是多一个列文件，schema 演进近乎零成本",
                        "en": "It fits vector retrieval's access pattern (scan a whole column contiguously, feed SIMD/GPU), compresses well for same-type columns, allows column pruning; adding a field is just one more column file — near-zero-cost schema evolution",
                    },
                    {"zh": "因为对象存储只支持列式文件", "en": "Because object storage only supports columnar files"},
                    {"zh": "因为按行存无法保存向量", "en": "Because row storage cannot hold vectors"},
                    {"zh": "因为列式可以原地修改数据", "en": "Because columnar allows in-place data modification"},
                ],
                "answer": 0,
                "why": {
                    "zh": "向量查询要的是所有行的向量列去算相似度，列式让向量连续躺在一个文件里、扫描顺序读且缓存友好；这呼应第 7 课段的列式存储伏笔",
                    "en": "A vector query wants the vector column of all rows for similarity; columnar keeps vectors contiguous in one file, sequential and cache-friendly — echoing Lesson 7's columnar hook",
                },
            },
            {
                "q": {
                    "zh": "stats binlog 里的布隆过滤器（Bloom filter）在查询中起什么作用？",
                    "en": "What role does the bloom filter in the stats binlog play in queries?",
                },
                "opts": [
                    {
                        "zh": "在打开一个段之前先判断“这个段里肯定没有某主键”，从而整段跳过；它绝不漏报，只允许极小概率误报，用于安全地排除不可能的段",
                        "en": "Before opening a segment, judge that 'this segment definitely lacks a given PK' and skip the whole segment; it never has false negatives, allows only a tiny false-positive rate, used to safely exclude impossible segments",
                    },
                    {"zh": "压缩向量数据以节省存储", "en": "Compress vector data to save storage"},
                    {"zh": "精确记录每一行的删除时间", "en": "Precisely record each row's delete time"},
                    {"zh": "替代主键索引做精确点查", "en": "Replace the PK index for exact point lookups"},
                ],
                "answer": 0,
                "why": {
                    "zh": "布隆过滤器是概率型集合，只回答“肯定不在/可能在”。Milvus 实现于 internal/util/bloomfilter，由 PrimaryKeyStats 持有；删除路由也靠它逐段筛查（第 20 课）",
                    "en": "A bloom filter is a probabilistic set answering only 'definitely not / maybe'. Milvus implements it in internal/util/bloomfilter, held by PrimaryKeyStats; delete routing also screens segments by it (Lesson 20)",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说 binlog 格式是 Milvus 各组件之间的“通用语言”：flusher 按它写、QueryNode 按它读、compaction 按它读改写、索引构建按它读。请思考：为什么一种“稳定、自描述、向后兼容”的磁盘格式，对一个能长期独立升级各组件的分布式系统如此关键？如果格式频繁不兼容地改动，会引发哪些连锁问题？（可结合第 18 课的 event header 与第 12 课 DataCoord 的段元数据。）",
                "en": "This lesson calls the binlog format the 'common language' among Milvus components: the flusher writes it, QueryNode reads it, compaction reads-and-rewrites it, index building reads it. Consider: why is a 'stable, self-describing, backward-compatible' on-disk format so critical for a distributed system that upgrades components independently over time? If the format changed incompatibly and often, what chain reactions would follow? (Tie in Lesson 18's event header and Lesson 12's DataCoord segment metadata.)",
            },
        ],
    },
    "19-compaction-and-gc.html": {
        "mcq": [
            {
                "q": {
                    "zh": "关于 compaction 的调度与执行，下面哪种说法符合 Milvus 当前架构？",
                    "en": "Regarding the scheduling and execution of compaction, which statement matches Milvus's current architecture?",
                },
                "opts": [
                    {
                        "zh": "DataCoord 扫描段元数据、按策略生成并分派 compaction 任务；真正读旧 binlog、合并、写新段的是 datanode 上的 compaction worker",
                        "en": "DataCoord scans segment metadata and, by policy, generates and dispatches compaction tasks; the one actually reading old binlogs, merging, and writing new segments is the compaction worker on a datanode",
                    },
                    {"zh": "compaction 由 Proxy 在写入路径上同步完成", "en": "Compaction is done synchronously by the Proxy on the write path"},
                    {"zh": "compaction 由 QueryNode 在查询时即时合并", "en": "Compaction is merged on the fly by QueryNode at query time"},
                    {"zh": "compaction 必须由独立的 indexnode 执行", "en": "Compaction must be executed by a dedicated indexnode"},
                ],
                "answer": 0,
                "why": {
                    "zh": "这正是“协调器管调度、节点管执行”的主旋律：DataCoord 调度，datanode worker 执行——也呼应第 17 课“DataNode 当下主要职责是 compaction”",
                    "en": "This is the refrain 'coordinators schedule, nodes execute': DataCoord schedules, a datanode worker executes — echoing Lesson 17's 'DataNode's main present role is compaction'",
                },
            },
            {
                "q": {
                    "zh": "Level0DeleteCompaction（datapb.CompactionType_Level0DeleteCompaction）在 compaction 里扮演什么角色？",
                    "en": "What role does Level0DeleteCompaction (datapb.CompactionType_Level0DeleteCompaction) play among compactions?",
                },
                "opts": [
                    {
                        "zh": "删除先被缓冲为第零层（L0）的墓碑（作废主键+时间戳），尚未落到具体 sealed 段；Level0DeleteCompaction 把这层 L0 墓碑物理应用进对应的段，让被删的行真正消失",
                        "en": "A delete is first buffered as a Level-0 (L0) tombstone (void PK + timestamp), not yet on a specific sealed segment; Level0DeleteCompaction physically applies this L0 tombstone layer into the matching segments, truly removing deleted rows",
                    },
                    {"zh": "它负责把多个小段按大小合并", "en": "It merges several small segments by size"},
                    {"zh": "它把段内数据按主键排序", "en": "It sorts a segment's data by primary key"},
                    {"zh": "它按聚类键重新分桶数据", "en": "It re-buckets data by a clustering key"},
                ],
                "answer": 0,
                "why": {
                    "zh": "这是上一课“删除不真删”的下半场。DataCoord 用 compaction_l0_view.go 的 LevelZeroCompactionView 追踪哪些 L0 墓碑该和哪些段合并；完整可见性见第 20 课",
                    "en": "This is the second half of last lesson's 'deletes don't truly delete'. DataCoord tracks which L0 tombstones merge with which segments via LevelZeroCompactionView in compaction_l0_view.go; full visibility in Lesson 20",
                },
            },
            {
                "q": {
                    "zh": "为什么 GC（garbage_collector.go）只删“孤儿超过 TTL（保留期）”的对象，而不是一变孤儿就删？",
                    "en": "Why does GC (garbage_collector.go) delete only objects 'orphaned beyond TTL (retention period)' rather than the instant they become orphans?",
                },
                "opts": [
                    {
                        "zh": "分布式系统存在时间差：某 QueryNode 可能仍在读刚被 compaction 替换的旧段，某操作可能要回滚；TTL 给在途引用留一个安全窗口，宁可垃圾多躺一会儿也绝不误删在用数据",
                        "en": "Distributed time skews exist: some QueryNode may still read an old segment just replaced by compaction, some operation may roll back; TTL leaves a safe window for in-flight references — better let garbage linger than ever mis-delete data in use",
                    },
                    {"zh": "因为对象存储不支持立即删除", "en": "Because object storage doesn't support immediate deletion"},
                    {"zh": "因为 TTL 能压缩 binlog 体积", "en": "Because TTL compresses binlog size"},
                    {"zh": "因为孤儿对象会自动过期失效", "en": "Because orphan objects auto-expire on their own"},
                ],
                "answer": 0,
                "why": {
                    "zh": "compaction 只在元数据上把旧段标记 dropped，物理文件仍在；GC 以元数据为准绳反向核对无引用对象，过 TTL 才删——这是“逻辑作废与物理回收分离”的设计",
                    "en": "Compaction only marks old segments dropped in metadata while physical files remain; GC takes metadata as the yardstick to reverse-check unreferenced objects and deletes only past TTL — the 'separate logical voiding from physical reclaim' design",
                },
            },
        ],
        "open": [
            {
                "zh": "本课把 compaction 与 GC 比作“一前一后的接力”：前者把碎、脏数据重写成整、净新段并把旧段逻辑作废，后者在 TTL 之后把旧段物理清走。请思考：为什么 Milvus 选择“写入只快速追加、整理留给后台批量做”（LSM 式）而不是“写入时就整理好”？这种解耦在写放大、写入延迟、读效率、存储成本之间各做了什么取舍？（可结合第 17 课 flush 与第 18 课列式 binlog。）",
                "en": "This lesson likens compaction and GC to 'a relay, one after the other': the former rewrites fragmented, dirty data into tidy, clean new segments and logically voids the old; the latter, past TTL, physically sweeps the old away. Consider: why does Milvus choose 'writes only append fast, tidying left to background batches' (LSM-style) rather than 'tidy at write time'? What tradeoffs does this decoupling make among write amplification, write latency, read efficiency, and storage cost? (Tie in Lesson 17's flush and Lesson 18's columnar binlogs.)",
            },
        ],
    },
    "20-delete-and-upsert.html": {
        "mcq": [
            {
                "q": {
                    "zh": "在只追加、不可变的存储底座上，Milvus 的一次 delete 实际做了什么？",
                    "en": "On an append-only, immutable storage substrate, what does a Milvus delete actually do?",
                },
                "opts": [
                    {
                        "zh": "生成一条带主键和删除时间戳的删除消息进 WAL，沉淀为第零层（L0）删除数据/deltalog（墓碑），并不回到 insert binlog 原地抹除；物理删除留给 Level0DeleteCompaction",
                        "en": "Generate a delete message (PK + delete timestamp) into the WAL, settling as Level-0 (L0) delete data/deltalog (a tombstone), without erasing in place in the insert binlog; physical removal is left to Level0DeleteCompaction",
                    },
                    {"zh": "立即在对象存储里找到该行并删除", "en": "Immediately find and delete that row in object storage"},
                    {"zh": "把整个段重写一遍以去掉该行", "en": "Rewrite the whole segment to drop that row"},
                    {"zh": "在内存里标记后从不落盘", "en": "Mark it in memory and never persist"},
                ],
                "answer": 0,
                "why": {
                    "zh": "binlog 不可变，删除只能表达成“追加一枚带时间戳的墓碑”。删除与插入共用同一条 WAL、排同一条全局时序，由 TSO 统一裁定先后",
                    "en": "Binlogs are immutable, so a delete can only be expressed as 'append a timestamped tombstone'. Deletes and inserts share the same WAL in one global order, with TSO adjudicating their ordering",
                },
            },
            {
                "q": {
                    "zh": "一条删除消息说“作废主键 X”，系统如何决定把这枚墓碑落到哪些段？",
                    "en": "A delete message says 'void PK X'; how does the system decide which segments to land this tombstone on?",
                },
                "opts": [
                    {
                        "zh": "拿主键 X 逐段问布隆过滤器（FieldStats.BF，internal/storage/field_stats.go）：回答“肯定没有”的段跳过，只把墓碑落到“可能含 X”的段；布隆绝不漏报，保证不会漏删",
                        "en": "Ask each segment's bloom filter with PK X (FieldStats.BF, internal/storage/field_stats.go): segments answering 'definitely not' are skipped, the tombstone lands only on those that 'might hold X'; the bloom never has false negatives, guaranteeing no missed delete",
                    },
                    {"zh": "把墓碑无差别地塞进每一个段", "en": "Stuff the tombstone indiscriminately into every segment"},
                    {"zh": "随机选几个段应用", "en": "Apply it to a few random segments"},
                    {"zh": "只落到最新创建的段", "en": "Only land it on the newest-created segment"},
                ],
                "answer": 0,
                "why": {
                    "zh": "布隆过滤器随 PK stats 序列化进 stats binlog（第 18 课）；“绝不漏报”是正确性命脉，误报只是多做无用功。这把广播压成精准投递，删除代价不随段数线性膨胀",
                    "en": "The bloom filter is serialized into the stats binlog alongside PK stats (Lesson 18); 'no false negatives' is the lifeline of correctness, a false positive only wastes a little work. This compresses broadcast into precise delivery, so delete cost doesn't balloon linearly with segment count",
                },
            },
            {
                "q": {
                    "zh": "在按时间戳的 MVCC 下，以保证时间戳 T 读取，一行在什么条件下可见？upsert 又如何融入这套规则？",
                    "en": "Under timestamp-based MVCC, reading at guarantee-ts T, when is a row visible? And how does upsert fit this rule?",
                },
                "opts": [
                    {
                        "zh": "可见 ⇔ 该行插入 ts ≤ T 且不存在 ts ≤ T 的墓碑作废它；upsert = 同主键先删后插，旧版本被墓碑作废、新版本以更晚 ts 写入，读取按 T 自然命中最新未作废版本",
                        "en": "Visible ⇔ the row's insert ts ≤ T and no tombstone with ts ≤ T voids it; upsert = for the same PK delete then insert, the old version voided by a tombstone and the new written with a later ts, so a read by T naturally hits the latest non-voided version",
                    },
                    {"zh": "可见 ⇔ 该行是最后写入的，无关时间戳", "en": "Visible ⇔ the row was written last, regardless of timestamp"},
                    {"zh": "upsert 会原地修改某个字段而不新增版本", "en": "Upsert modifies a field in place without adding a version"},
                    {"zh": "可见性由段是否建好索引决定", "en": "Visibility is decided by whether the segment has an index built"},
                ],
                "answer": 0,
                "why": {
                    "zh": "插入给行盖“生日”、删除盖“忌日”，读取拿 T 只认“生日 ≤ T 且无 ts ≤ T 的忌日”的行。同一数据换 T 即换快照，读写互不阻塞；T 怎么定由一致性级别决定（第 30 课）",
                    "en": "An insert stamps a 'birthday', a delete a 'deathday'; a read with T sees only rows whose 'birthday ≤ T and no deathday with ts ≤ T'. The same data with a different T is a different snapshot, reads and writes never block; how T is set is decided by the consistency level (Lesson 30)",
                },
            },
        ],
        "open": [
            {
                "zh": "本课把插入、删除、upsert 统一成“一堆带时间戳的不可变事件”，再用一条 MVCC 规则裁决可见性。请思考：这种“写只追加、读取快照、按时间戳裁决”的设计，相比传统数据库“原地更新 + 读写加锁”，在高并发向量检索场景下有什么优势与代价？它给“保证时间戳 T 怎么定”留下了什么问题，需要一致性级别（第 30 课）来回答？（可结合第 16 课 WAL 与 TSO、第 19 课 compaction 回收旧版本。）",
                "en": "This lesson unifies insert, delete, and upsert into 'a pile of timestamped immutable events,' then adjudicates visibility with one MVCC rule. Consider: compared with a traditional database's 'in-place update + read/write locking,' what are the advantages and costs of this 'writes only append, reads take a snapshot, judged by timestamp' design under high-concurrency vector retrieval? What question does it leave open about 'how guarantee-ts T is set,' to be answered by consistency levels (Lesson 30)? (Tie in Lesson 16's WAL and TSO, and Lesson 19's compaction reclaiming old versions.)",
            },
        ],
    },
    "21-index-service.html": {
        "mcq": [
            {
                "q": {
                    "zh": "在 Milvus 里，谁负责调度索引构建、谁真正执行构建？",
                    "en": "In Milvus, who schedules index build and who actually executes it?",
                },
                "opts": [
                    {
                        "zh": "DataCoord 拥有索引元数据与调度（internal/datacoord/index_service.go 的 CreateIndex、index_inspector.go），把每个 sealed 段的构建任务派给一个 worker；worker 实现 workerpb 的 IndexNodeClient 协议执行构建，并不存在独立的 indexnode 进程",
                        "en": "DataCoord owns index metadata and scheduling (CreateIndex in internal/datacoord/index_service.go, index_inspector.go), dispatching a per-sealed-segment build task to a worker; the worker executes via the workerpb IndexNodeClient protocol — there is no separate indexnode process",
                    },
                    {"zh": "QueryNode 在加载段时顺便构建索引", "en": "QueryNode builds the index incidentally while loading segments"},
                    {"zh": "Proxy 收到请求后直接在本地构建", "en": "The Proxy builds it locally right after receiving the request"},
                    {"zh": "RootCoord 负责构建所有索引", "en": "RootCoord builds all indexes"},
                ],
                "answer": 0,
                "why": {
                    "zh": "“IndexNodeClient”只是历史遗留的协议名；执行索引构建的是 datanode 上的 worker，没有单独的 indexnode 进程。调度（DataCoord）与执行（worker）分离，正是控制面/数据面分工的延续",
                    "en": "'IndexNodeClient' is only a legacy protocol name; the executor is a worker on a datanode, with no separate indexnode process. Splitting scheduling (DataCoord) from execution (worker) continues the control-plane/data-plane division of labor",
                },
            },
            {
                "q": {
                    "zh": "一次 CreateIndex 请求之后，索引是如何从“一条声明”变成“可加载的文件”的？",
                    "en": "After a CreateIndex request, how does an index go from 'a declaration' to 'loadable files'?",
                },
                "opts": [
                    {
                        "zh": "CreateIndex 把索引定义写进元数据；随后每个 sealed 段各派生一个构建任务，worker 读该段 binlog、调 Knowhere 建索引、把索引文件写回对象存储，QueryNode 之后即可加载",
                        "en": "CreateIndex records the index definition in metadata; then each sealed segment spawns a build task, the worker reads that segment's binlogs, calls Knowhere to build, writes index files back to object storage, and QueryNode can then load them",
                    },
                    {"zh": "整张表一次性构建成一个全局索引文件", "en": "The whole table is built in one shot into a single global index file"},
                    {"zh": "索引只存在内存里，从不落盘", "en": "The index lives only in memory and is never persisted"},
                    {"zh": "growing 段也会立刻被构建索引", "en": "Growing segments also get an index built immediately"},
                ],
                "answer": 0,
                "why": {
                    "zh": "索引以“段”为单位构建：只有 sealed（已封口、不可变）段才值得建索引，growing 段仍用暴力扫描（详见第 23 课）。声明—派任务—建文件—可加载，是一条异步流水线",
                    "en": "Indexes are built per segment: only sealed (closed, immutable) segments are worth indexing, growing ones still use brute force (see Lesson 23). Declare → dispatch task → build files → loadable is an asynchronous pipeline",
                },
            },
        ],
        "open": [
            {
                "zh": "本课强调“没有独立的 indexnode 进程，构建跑在实现 IndexNodeClient 协议的 worker 上”。请思考：为什么 Milvus 选择把索引构建做成“由 DataCoord 调度、按段派发给 worker”的异步任务，而不是在写入时同步建索引？这种设计对写入吞吐、资源弹性、以及 auto-index 自动选型分别带来什么好处？（可结合第 12 课 DataCoord、第 23 课构建与加载。）",
                "en": "This lesson stresses 'no separate indexnode process; the build runs on a worker implementing the IndexNodeClient protocol.' Consider: why does Milvus make index build an asynchronous task 'scheduled by DataCoord, dispatched per segment to a worker' instead of building synchronously at write time? What does this design buy for write throughput, resource elasticity, and auto-index type selection? (Tie in Lesson 12 DataCoord and Lesson 23 build-and-load.)",
            },
        ],
    },
    "22-knowhere.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 的向量索引（HNSW、IVF_PQ、SCANN、GPU CAGRA 等）究竟来自哪里？",
                    "en": "Where do Milvus's vector indexes (HNSW, IVF_PQ, SCANN, GPU CAGRA, etc.) actually come from?",
                },
                "opts": [
                    {
                        "zh": "它们大多是上游 Knowhere 库提供的 IndexEnum 索引类型，并非 milvus core 自己定义；core 仅引用少量常量（如 common/Utils.h 的 INDEX_DISKANN、index/Utils.cpp 的 INDEX_FAISS_IVFFLAT/INDEX_SPARSE_INVERTED_INDEX/INDEX_SPARSE_WAND 等 knowhere::IndexEnum::）",
                        "en": "Most are IndexEnum types provided by the upstream Knowhere library, not defined by milvus core itself; core only references a few constants (e.g. INDEX_DISKANN in common/Utils.h, INDEX_FAISS_IVFFLAT/INDEX_SPARSE_INVERTED_INDEX/INDEX_SPARSE_WAND etc. as knowhere::IndexEnum:: in index/Utils.cpp)",
                    },
                    {"zh": "全部由 milvus core 的 Go 代码实现", "en": "All implemented by milvus core's Go code"},
                    {"zh": "每种索引都是一个独立的微服务", "en": "Each index type is a standalone microservice"},
                    {"zh": "由 Proxy 在查询时临时算法生成", "en": "Generated on the fly by the Proxy at query time"},
                ],
                "answer": 0,
                "why": {
                    "zh": "向量索引算法属于 Knowhere（封装 Faiss/HNSWlib/DiskANN/cuVS 等）。引用 milvus 文件时只能引那些确实存在的 IndexEnum 常量，其余索引名应作为“Knowhere 索引名”呈现，不要硬塞进不含它们的 milvus 文件",
                    "en": "Vector index algorithms belong to Knowhere (wrapping Faiss/HNSWlib/DiskANN/cuVS, etc.). When citing a milvus file you may only cite IndexEnum constants that truly exist; the rest should be presented as 'Knowhere index names,' not forced into milvus files that lack them",
                },
            },
            {
                "q": {
                    "zh": "选择向量索引与参数时，下面哪一条描述是对的？",
                    "en": "When choosing a vector index and its params, which statement is correct?",
                },
                "opts": [
                    {
                        "zh": "IVF 系的 nlist/nprobe、HNSW 的 M/ef 都是“召回 vs 速度/内存”的旋钮；FLAT 暴力扫描召回 100% 但最慢，PQ/SQ8 用压缩省内存换精度，DiskANN 把图放磁盘换超大规模；且查询 metric 必须与建索引时一致",
                        "en": "IVF's nlist/nprobe and HNSW's M/ef are all 'recall vs speed/memory' knobs; FLAT brute force gives 100% recall but is slowest, PQ/SQ8 trade accuracy for memory via compression, DiskANN puts the graph on disk for huge scale; and the query metric must match the one used to build the index",
                    },
                    {"zh": "metric 可以查询时随意更换，不影响结果", "en": "The metric can be swapped freely at query time without affecting results"},
                    {"zh": "nprobe 越小召回越高", "en": "The smaller nprobe is, the higher the recall"},
                    {"zh": "HNSW 不需要任何参数", "en": "HNSW needs no parameters at all"},
                ],
                "answer": 0,
                "why": {
                    "zh": "所有 ANN 索引本质都在“召回—延迟—内存”三角里取舍；调大 nprobe/ef 提召回但更慢。metric（L2/IP/COSINE 等）必须与字段建索引时匹配，否则距离语义错乱、结果无意义",
                    "en": "Every ANN index trades within the 'recall–latency–memory' triangle; raising nprobe/ef lifts recall but is slower. The metric (L2/IP/COSINE, etc.) must match what the field was indexed with, otherwise distance semantics break and results are meaningless",
                },
            },
        ],
        "open": [
            {
                "zh": "本课刻意区分了“milvus core 真正定义/引用的 IndexEnum 常量”与“仅作为 Knowhere 索引名呈现的类型”。请思考：为什么把向量索引算法外包给 Knowhere 这样的专门库，对 Milvus 是合理的架构选择？这对“引用代码出处”的严谨性提出了什么要求（即不能把 HNSW/SCANN 等硬归到不含它们的 milvus 文件）？（可结合第 5 课 ANN 算法。）",
                "en": "This lesson deliberately separates 'IndexEnum constants milvus core truly defines/references' from 'types presented merely as Knowhere index names.' Consider: why is outsourcing vector index algorithms to a dedicated library like Knowhere a sound architectural choice for Milvus? What rigor does this demand about 'citing code provenance' (i.e. not attributing HNSW/SCANN to milvus files that lack them)? (Tie in Lesson 5 ANN algorithms.)",
            },
        ],
    },
    "23-index-build-and-load.html": {
        "mcq": [
            {
                "q": {
                    "zh": "一个 sealed 段的索引，从构建到能被查询，经过哪条路径？",
                    "en": "What path does a sealed segment's index take from build to queryable?",
                },
                "opts": [
                    {
                        "zh": "sealed 段 → 构建任务（worker 读该段 binlog、调 Knowhere 建索引）→ 索引文件写入对象存储 → QueryNode 加载（可 mmap 或全内存，loadSealedSegment）；growing 段尚未建索引，查询时用暴力扫描",
                        "en": "sealed segment → build task (worker reads the segment's binlogs, calls Knowhere to build) → index files written to object storage → QueryNode loads them (mmap or fully in-memory, loadSealedSegment); growing segments aren't indexed yet and use brute force at query time",
                    },
                    {"zh": "QueryNode 直接从内存共享 DataNode 的索引，无需对象存储", "en": "QueryNode shares the DataNode's index directly from memory, with no object storage"},
                    {"zh": "索引文件随 binlog 一起在写入时同步生成", "en": "Index files are generated synchronously with binlogs at write time"},
                    {"zh": "growing 段也用 HNSW 索引检索", "en": "Growing segments are also searched via an HNSW index"},
                ],
                "answer": 0,
                "why": {
                    "zh": "对象存储是构建侧（worker 写）与加载侧（QueryNode 读）之间的解耦点，二者无需直接通信。mmap 让超出内存的索引也能加载，是“内存 vs 延迟”的取舍",
                    "en": "Object storage is the decoupling point between the build side (worker writes) and the load side (QueryNode reads), so the two need no direct communication. mmap lets indexes larger than RAM still load, a 'memory vs latency' tradeoff",
                },
            },
            {
                "q": {
                    "zh": "索引引擎版本管理（index_engine_version_manager.go）在滚动升级时为何重要？",
                    "en": "Why does index-engine version management (index_engine_version_manager.go) matter during a rolling upgrade?",
                },
                "opts": [
                    {
                        "zh": "不同节点的 Knowhere 版本支持的索引格式可能不同；构建时按“以最弱节点为准”（GetCurrentIndexEngineVersion/GetMinimalIndexEngineVersion）选版本，确保新建的索引所有 QueryNode 都能加载，升级期间服务不中断",
                        "en": "Different nodes' Knowhere versions may support different index formats; the build picks a version 'deferring to the weakest node' (GetCurrentIndexEngineVersion/GetMinimalIndexEngineVersion) so every QueryNode can load the new index, keeping service uninterrupted during the upgrade",
                    },
                    {"zh": "它决定查询用哪个 metric", "en": "It decides which metric a query uses"},
                    {"zh": "它给每个段分配主键", "en": "It assigns primary keys to each segment"},
                    {"zh": "它只是日志里的版本号，无实际作用", "en": "It is just a version string in logs with no real effect"},
                ],
                "answer": 0,
                "why": {
                    "zh": "“以最弱节点为准”是兼容性优先于新特性的体现：用一点“暂不使用新格式”的代价，换升级期间全集群始终可加载、不丢服务。这是在线数据库升级的通用保守策略",
                    "en": "'Defer to the weakest node' embodies compatibility-over-new-features: trade 'not yet using the newest format' for a cluster that stays loadable and loses no service during the upgrade. It's the standard conservative strategy for online database upgrades",
                },
            },
        ],
        "open": [
            {
                "zh": "本课用“对象存储”把索引构建与加载彻底解耦，又用“以最弱节点为准”的版本协商保证滚动升级不中断。请思考：这两个设计分别体现了分布式系统的什么通用原则？为什么 growing 段宁可用暴力扫描也不立刻建索引，这与“段的生命周期”（第 7 课）如何呼应？（可结合第 18 课 binlog、第 22 课 Knowhere。）",
                "en": "This lesson fully decouples index build from load via 'object storage,' and guarantees uninterrupted rolling upgrades via 'defer to the weakest node' version negotiation. Consider: what general distributed-systems principles do these two designs embody? Why would a growing segment rather use brute force than build an index immediately, and how does that echo the 'segment lifecycle' (Lesson 7)? (Tie in Lesson 18 binlog and Lesson 22 Knowhere.)",
            },
        ],
    },
    "24-scalar-and-fulltext.html": {
        "mcq": [
            {
                "q": {
                    "zh": "在带条件的混合查询里，标量过滤与向量 ANN 是如何配合的？",
                    "en": "In a conditional hybrid query, how do scalar filtering and vector ANN cooperate?",
                },
                "opts": [
                    {
                        "zh": "标量索引算出一个 bitset 过滤掩码，下推给向量 ANN，让 ANN 只在合格子集上检索（先筛后搜）；这避免了“先搜后筛”在高选择性过滤下 topK 被筛光、召回骤降的问题",
                        "en": "The scalar index computes a bitset filter mask and pushes it down into vector ANN so ANN searches only the qualifying subset (filter-then-search); this avoids 'search-then-filter' where, under a selective filter, the topK gets filtered away and recall collapses",
                    },
                    {"zh": "先做完整 ANN，再事后丢掉不合格行，永远更优", "en": "Always run full ANN first then discard non-qualifying rows, which is always better"},
                    {"zh": "标量与向量索引各查各的，结果不交互", "en": "Scalar and vector indexes query independently and never interact"},
                    {"zh": "过滤必须逐行扫描，无法用索引加速", "en": "Filtering must scan row by row and can't be accelerated by an index"},
                ],
                "answer": 0,
                "why": {
                    "zh": "把过滤掩码下推进 ANN，本质是数据库的“谓词下推”：尽早、尽低剔除不合格数据。先筛后搜保证 topK 是在合格集合里选出来的，召回稳定",
                    "en": "Pushing the filter mask into ANN is essentially database 'predicate pushdown': eliminate non-qualifying data as early and low as possible. Filter-then-search guarantees the topK is chosen within the qualifying set, with stable recall",
                },
            },
            {
                "q": {
                    "zh": "下面关于 Milvus 标量与全文索引的描述，哪条是对的？",
                    "en": "Which statement about Milvus scalar and full-text indexes is correct?",
                },
                "opts": [
                    {
                        "zh": "标量索引在 C++（internal/core/src/index/）：倒排 InvertedIndexTantivy（等值/字符串）、BitmapIndex（低基数）、ScalarIndexSort（STL_SORT 范围）、ngram（子串）、HybridScalarIndex（自动选型）、JSON；全文 BM25 由 Rust 的 tantivy 引擎落地，经 thirdparty/tantivy 绑定接入",
                        "en": "Scalar indexes live in C++ (internal/core/src/index/): inverted InvertedIndexTantivy (equality/string), BitmapIndex (low-cardinality), ScalarIndexSort (STL_SORT range), ngram (substring), HybridScalarIndex (auto-pick), JSON; full-text BM25 is delivered by Rust's tantivy engine via the thirdparty/tantivy binding",
                    },
                    {"zh": "全文检索也由 Knowhere 提供", "en": "Full-text search is also provided by Knowhere"},
                    {"zh": "标量索引只有一种类型，适用于所有字段", "en": "There is only one scalar index type, used for all fields"},
                    {"zh": "bitmap 索引最适合高基数字段", "en": "Bitmap indexes are best for high-cardinality fields"},
                ],
                "answer": 0,
                "why": {
                    "zh": "不同标量索引各有适用场景：低基数用 bitmap、范围查询用排序、等值/全文用倒排（tantivy）。HybridScalarIndex 会按数据特征自动选型。全文 BM25 由 Rust tantivy 落地，不属于 Knowhere",
                    "en": "Different scalar indexes fit different cases: bitmap for low cardinality, sort for range queries, inverted (tantivy) for equality/full-text. HybridScalarIndex auto-picks by data characteristics. Full-text BM25 is delivered by Rust tantivy, not Knowhere",
                },
            },
        ],
        "open": [
            {
                "zh": "本课把“过滤”这半边交给标量索引、把“相似检索”那半边交给向量索引，再用 bitset 下推让二者协同（先筛后搜 = 谓词下推）。请思考：为什么 Milvus 需要这么多种标量索引（倒排/bitmap/排序/ngram/混合/JSON），而不是一种通吃？全文检索为何要专门引入 Rust 的 tantivy，而不复用向量那套？（可结合第 22 课 Knowhere、第 6 课数据模型。）",
                "en": "This lesson hands the 'filter' half to scalar indexes and the 'similarity search' half to vector indexes, then makes them cooperate via bitset pushdown (filter-then-search = predicate pushdown). Consider: why does Milvus need so many scalar index types (inverted/bitmap/sort/ngram/hybrid/JSON) rather than one-size-fits-all? Why introduce Rust's tantivy specifically for full-text instead of reusing the vector stack? (Tie in Lesson 22 Knowhere and Lesson 6 data model.)",
            },
        ],
    },
    "25-search-via-proxy.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Proxy 侧的 searchTask 在 PreExecute 阶段，从“一致性级别”推出 guarantee 时间戳。下面哪条最准确地描述了它的作用与取舍？",
                    "en": "On the Proxy side, searchTask in PreExecute derives a guarantee timestamp from the consistency level. Which best describes its role and tradeoff?",
                },
                "opts": [
                    {
                        "zh": "guarantee ts 是一条“至少读到此刻为止数据”的下界：越接近 tMax（如 Strong）看到的越新但可能要等，越小（如 Eventually）答得越快但可能越旧；它由 parseGuaranteeTsFromConsistency 算出并随请求下发，真正“等够新再答”发生在 QueryNode 侧",
                        "en": "The guarantee ts is a lower bound 'read at least the data up to this instant': closer to tMax (e.g. Strong) is fresher but may wait, smaller (e.g. Eventually) answers faster but may be staler; parseGuaranteeTsFromConsistency computes it and it travels with the request, while the actual 'wait until fresh enough' happens on the QueryNode",
                    },
                    {"zh": "guarantee ts 指定“只读这一个时刻的数据”，是一个精确的等值快照", "en": "The guarantee ts specifies 'read only the data at this one instant', an exact equality snapshot"},
                    {"zh": "guarantee ts 决定 topK 的大小", "en": "The guarantee ts decides the size of topK"},
                    {"zh": "guarantee ts 只在写入时使用，与搜索无关", "en": "The guarantee ts is used only on writes and is unrelated to search"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Strong→tMax、Bounded→tMax−gracefulTime、Eventually→1。它是“看得多新 ↔ 答得多快”的旋钮，是下界而非等值；Proxy 只算出并下发，等待在 QueryNode（第 30 课）。",
                    "en": "Strong→tMax, Bounded→tMax−gracefulTime, Eventually→1. It is the 'how fresh ↔ how fast' dial, a lower bound not an equality; the Proxy only computes and forwards it, the waiting is on the QueryNode (Lesson 30).",
                },
            },
            {
                "q": {
                    "zh": "关于 Proxy 在一次搜索里的职责，下面哪条是对的？",
                    "en": "Regarding the Proxy's responsibilities in one search, which is correct?",
                },
                "opts": [
                    {
                        "zh": "Proxy 把布尔过滤编译成 planpb.PlanNode（向量 ANN 节点+标量谓词子树）、扇出到各分片的 delegator、再跨分片归并 topK；它本身不持有向量数据、不算距离、不执行 plan",
                        "en": "The Proxy compiles the boolean filter into a planpb.PlanNode (vector ANN node + scalar predicate subtree), scatters to each shard's delegator, then reduces topK across shards; it holds no vector data, computes no distances, and does not execute the plan itself",
                    },
                    {"zh": "Proxy 在自己进程内加载索引并直接计算 ANN", "en": "The Proxy loads indexes in its own process and computes ANN directly"},
                    {"zh": "Proxy 决定每个段归哪个 QueryNode 持有", "en": "The Proxy decides which QueryNode holds each segment"},
                    {"zh": "Proxy 串行逐个查询分片以保证顺序", "en": "The Proxy queries shards serially one by one to preserve order"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Proxy 是无状态的“翻译+调度+归并”层：编 plan、定 guarantee ts、并发扇出、跨分片 reduce。算距离在 segcore，段分布由 QueryCoord（第 13 课）决定，plan 在 segcore 才执行（第 28 课）。",
                    "en": "The Proxy is a stateless 'translate+schedule+merge' layer: compile the plan, fix guarantee ts, fan out concurrently, reduce across shards. Distance compute is in segcore, segment distribution is QueryCoord's (Lesson 13), and the plan runs only in segcore (Lesson 28).",
                },
            },
            {
                "q": {
                    "zh": "一次 search 被描述为“两层扇出”。这两层分别是什么？",
                    "en": "A search is described as a 'two-level fan-out'. What are the two levels?",
                },
                "opts": [
                    {
                        "zh": "第一层 Proxy 扇到各分片（delegator），第二层每个 delegator 再扇到它管的多个段/worker；对应地归并也分层（段内→节点内→跨分片，即三级 reduce）",
                        "en": "Level one: Proxy fans out to shards (delegators); level two: each delegator fans out to the multiple segments/workers it manages; correspondingly the merge is layered too (per-segment → per-node → cross-shard, the three-level reduce)",
                    },
                    {"zh": "第一层扇到 etcd，第二层扇到对象存储", "en": "Level one fans out to etcd, level two to object storage"},
                    {"zh": "第一层是写、第二层是读", "en": "Level one is the write, level two is the read"},
                    {"zh": "两层都在 SDK 客户端完成", "en": "Both levels happen in the SDK client"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Proxy→分片 是第一层，delegator→段/worker 是第二层（第 26 课）。归并对称分三级：segcore 段内、delegator 节点内、Proxy 跨分片（第 29 课收束）。",
                    "en": "Proxy→shards is level one, delegator→segments/workers is level two (Lesson 26). The merge is symmetrically three-level: segcore per-segment, delegator per-node, Proxy cross-shard (tied up in Lesson 29).",
                },
            },
        ],
        "open": [
            {
                "zh": "本课把 Proxy 定位成“翻译+调度+归并”的无状态层，自己不碰向量数据。请思考：为什么把“算距离”推给 QueryNode、而让 Proxy 保持无状态，对系统的弹性扩容与容错有什么好处？如果让 Proxy 直接持有索引、就地计算，会带来哪些问题？（可结合第 10 课 Proxy、第 9 课控制面/数据面。）",
                "en": "This lesson frames the Proxy as a stateless 'translate+schedule+merge' layer that never touches vector data. Consider: why does pushing 'distance compute' to the QueryNode while keeping the Proxy stateless help elastic scaling and fault tolerance? What problems would arise if the Proxy held indexes and computed in place? (Tie in Lesson 10 Proxy and Lesson 9 control/data plane.)",
            },
        ],
    },
    "26-querynode-and-delegator.html": {
        "mcq": [
            {
                "q": {
                    "zh": "delegator（shard leader）为了给出一个“完整且新鲜”的答案，必须同时搜哪两类段？它们的检索方式有何不同？",
                    "en": "To give a 'complete and fresh' answer, which two kinds of segments must the delegator (shard leader) search, and how do their retrieval methods differ?",
                },
                "opts": [
                    {
                        "zh": "sealed 段（已封存、带 Knowhere 索引、由 QueryCoord 分布到多 worker、走索引检索）+ growing 段（在长、无索引、delegator 消费 WAL 尾部维护、暴力逐条算）；两边结果合并才完整",
                        "en": "sealed segments (settled, with a Knowhere index, distributed across workers by QueryCoord, searched via the index) + growing segments (growing, no index, maintained by the delegator consuming the WAL tail, brute-forced per row); merging both is what makes the answer complete",
                    },
                    {"zh": "只搜 sealed 段即可，growing 段不参与检索", "en": "Search only sealed segments; growing segments don't participate"},
                    {"zh": "sealed 和 growing 都走暴力扫描，没有区别", "en": "Both sealed and growing use brute force, no difference"},
                    {"zh": "growing 段也建好了索引，和 sealed 一样快", "en": "Growing segments are also indexed, as fast as sealed"},
                ],
                "answer": 0,
                "why": {
                    "zh": "“新鲜”和“高效”是一对矛盾：稳定大头交给索引（sealed，快），易变小尾巴交给暴力（growing，新）。delegator 消费 WAL 维护 growing，保证刚写就能搜到；两边合并兼得快与新。",
                    "en": "'Fresh' and 'efficient' conflict: give the stable bulk to the index (sealed, fast) and the volatile tail to brute force (growing, fresh). The delegator consumes the WAL to maintain growing so just-written data is searchable; merging both gets fast and fresh at once.",
                },
            },
            {
                "q": {
                    "zh": "delegator 维护一个 tsafe。收到一个带 guarantee ts 的 search 时，它如何用 tsafe？",
                    "en": "The delegator maintains a tsafe. When it receives a search carrying a guarantee ts, how does it use tsafe?",
                },
                "opts": [
                    {
                        "zh": "tsafe 表示“已把 WAL 消费到的时间戳”。若 tsafe ≥ guaranteeTs 则该看到的写入已到齐、立即检索；若 tsafe < guaranteeTs（还没追上）就等到 tsafe 追上再答——这把一致性级别真正兑现",
                        "en": "tsafe is 'up to which timestamp the WAL has been consumed'. If tsafe ≥ guaranteeTs, the writes it should see have arrived, so it searches immediately; if tsafe < guaranteeTs (not caught up), it waits until tsafe catches up before answering — this redeems the consistency level",
                    },
                    {"zh": "tsafe 用来决定 topK 的大小", "en": "tsafe decides the size of topK"},
                    {"zh": "tsafe 是对象存储的版本号，与等待无关", "en": "tsafe is an object-storage version number, unrelated to waiting"},
                    {"zh": "tsafe 总是等于 tMax，所以从不需要等待", "en": "tsafe always equals tMax, so no waiting is ever needed"},
                ],
                "answer": 0,
                "why": {
                    "zh": "tsafe 是 delegator 已消费 WAL 的进度。Strong 取 tMax 就得等到消费追平最新；Eventually 取极小值几乎不等——这正是“看得多新↔答得多快”在分片端的落地（第 30 课详解 MVCC）。",
                    "en": "tsafe is the delegator's WAL-consumption progress. Strong takes tMax so it must wait until consumption catches the latest; Eventually takes a tiny value so it barely waits — exactly the 'how fresh ↔ how fast' ruler at the shard end (MVCC detailed in Lesson 30).",
                },
            },
            {
                "q": {
                    "zh": "为什么 delegator 要先在“节点内”把各 worker 的结果归并一次，再交给 Proxy，而不是把所有原始结果直接上交？",
                    "en": "Why does the delegator first merge the workers' results 'within the node' before handing them to the Proxy, instead of forwarding all raw results?",
                },
                "opts": [
                    {
                        "zh": "为了尽量减少跨网络搬运的数据量：把 N 份 topK 压成一份再上交，Proxy 接收的数据降到 1/N；这是分布式里“局部归并/下推聚合”的通用做法，逐级收窄而非把海量候选背到最顶",
                        "en": "To minimize data moved across the network: compress N topK sets into one before forwarding, cutting what the Proxy receives to 1/N; this is the general 'partial merge / pushdown aggregation' practice in distributed systems, narrowing stage by stage rather than hauling masses of candidates to the top",
                    },
                    {"zh": "因为 Proxy 没有能力做归并", "en": "Because the Proxy is incapable of merging"},
                    {"zh": "因为 worker 之间必须互相通信", "en": "Because workers must communicate with each other"},
                    {"zh": "节点内归并是多余的，纯属浪费", "en": "Node-level merge is redundant and pure waste"},
                ],
                "answer": 0,
                "why": {
                    "zh": "三级 reduce 让每一层只把必要精华往上交。delegator 先压成一份 topK，大幅减少发往 Proxy 的数据——和数据库把过滤/聚合下推到存储层是同一智慧。",
                    "en": "The three-level reduce makes each layer pass up only the essence. The delegator compresses to one topK first, greatly reducing data sent to the Proxy — the same wisdom as databases pushing filtering/aggregation down to storage.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课区分了两个正交维度：分片（按数据切，让单次检索并行变快）与副本（按可用性复制，让吞吐叠加并容错）。请思考：如果某个 collection 读 QPS 很高但数据量不大，你会优先加分片还是加副本？如果数据量巨大、单机放不下呢？delegator 在这两种扩展里各扮演什么角色？（可结合第 13 课 QueryCoord。）",
                "en": "This lesson distinguished two orthogonal dimensions: shards (split by data, making a single search faster in parallel) and replicas (copied for availability, stacking throughput and tolerating faults). Consider: if a collection has very high read QPS but modest data size, would you add shards or replicas first? What if the data is huge and won't fit on one machine? What role does the delegator play in each kind of scaling? (Tie in Lesson 13 QueryCoord.)",
            },
        ],
    },
    "27-segcore.html": {
        "mcq": [
            {
                "q": {
                    "zh": "segcore 是用什么语言写的、负责什么？Go 侧的 QueryNode 如何调用它？",
                    "en": "What language is segcore written in and what does it do? How does the Go-side QueryNode call it?",
                },
                "opts": [
                    {
                        "zh": "segcore 是 C++ 写的“单段检索引擎”，只在一个 segment 内部执行检索/查询；Go 的 LocalSegment 经纯 C 的 segment_c.h（NewSegment/AsyncSearch/DeleteSegment）通过 cgo 调进 C++，段在 Go 侧只是个不透明句柄",
                        "en": "segcore is a C++ 'single-segment search engine' that executes search/query only inside one segment; Go's LocalSegment calls into C++ over cgo through pure-C segment_c.h (NewSegment/AsyncSearch/DeleteSegment), where a segment is just an opaque handle on the Go side",
                    },
                    {"zh": "segcore 是 Go 写的，直接在 QueryNode 进程里以 Go 代码运行", "en": "segcore is written in Go and runs as Go code directly in the QueryNode process"},
                    {"zh": "segcore 是 Rust 写的全文检索引擎", "en": "segcore is a Rust full-text search engine"},
                    {"zh": "segcore 由 Proxy 直接调用，不经过 QueryNode", "en": "segcore is called directly by the Proxy, bypassing the QueryNode"},
                ],
                "answer": 0,
                "why": {
                    "zh": "segcore 是 C++ 单段引擎（不懂分片/副本/WAL）。cgo 只认 C 的 ABI，所以要用纯 C 的 segment_c.h 把 C++ 能力包一层暴露给 Go；段在 Go 侧是 void* 不透明句柄。",
                    "en": "segcore is a C++ single-segment engine (ignorant of shards/replicas/WAL). cgo only recognizes C's ABI, so pure-C segment_c.h wraps C++ ability for Go; a segment is a void* opaque handle on the Go side.",
                },
            },
            {
                "q": {
                    "zh": "segcore 用同一套 SegmentInterface 抽象“一个段”，下有两种实现。sealed 与 growing 的检索路径分别是什么？",
                    "en": "segcore abstracts 'a segment' with one SegmentInterface, with two implementations. What are the retrieval paths of sealed vs growing?",
                },
                "opts": [
                    {
                        "zh": "SegmentSealed 走加载好的 Knowhere 索引（HNSW/IVF…，跳过大半向量，快）；SegmentGrowing 无索引、对每条向量暴力算距离（小、新）。上层只调同一个 Search，由多态自动选快路/慢路",
                        "en": "SegmentSealed goes through the loaded Knowhere index (HNSW/IVF…, skipping most vectors, fast); SegmentGrowing has no index and brute-forces distances over every vector (small, fresh). The upper layer just calls the same Search, and polymorphism picks the fast/slow path",
                    },
                    {"zh": "sealed 暴力扫、growing 走索引，正好相反", "en": "sealed brute-forces and growing uses the index, exactly reversed"},
                    {"zh": "两者都不计算距离，只返回行号", "en": "Neither computes distances; they only return row numbers"},
                    {"zh": "sealed 和 growing 必须由不同的 Proxy 分别调用", "en": "sealed and growing must be called by different Proxies separately"},
                ],
                "answer": 0,
                "why": {
                    "zh": "“同一接口、两种实现”是多态：上层不必关心段带不带索引，segcore 按段的实际类型自动选索引（sealed，快）或暴力（growing，新）。这也是 delegator 能云淡风轻合并两者的原因。",
                    "en": "'One interface, two implementations' is polymorphism: the upper layer needn't care whether a segment is indexed; segcore picks index (sealed, fast) or brute force (growing, fresh) by the segment's actual type. That is why the delegator can airily merge both.",
                },
            },
            {
                "q": {
                    "zh": "为什么 Milvus 要在 Go 与 C++ 之间隔一层纯 C 的 segment_c.h，而不让 Go 直接调 C++ 的类与方法？",
                    "en": "Why does Milvus interpose a layer of pure-C segment_c.h between Go and C++, instead of letting Go call C++ classes and methods directly?",
                },
                "opts": [
                    {
                        "zh": "因为 cgo 只认 C 的 ABI：C++ 的类/模板/虚表经 name mangling 后 Go 对不上号，而 C 函数符号简单稳定，是两种语言的最大公约数；所以要用纯 C 函数把 C++ 能力包一层暴露",
                        "en": "Because cgo only recognizes C's ABI: C++ classes/templates/vtables are name-mangled and unmatchable to Go, while C function symbols are simple and stable, the greatest common denominator of both languages; so pure-C functions wrap and expose the C++ ability",
                    },
                    {"zh": "因为 C 比 C++ 运行得更快", "en": "Because C runs faster than C++"},
                    {"zh": "因为 Go 不允许调用任何非 Go 代码", "en": "Because Go forbids calling any non-Go code"},
                    {"zh": "纯属历史包袱，没有技术原因", "en": "Purely historical baggage, no technical reason"},
                ],
                "answer": 0,
                "why": {
                    "zh": "cgo 跨的是 C 的 ABI。C++ 的 name mangling 让 Go 对不上符号，于是 Milvus core 里大量 *_c.h/*_c.cpp 都是“给 Go 看的 C 门面”，背后才是真正干活的 C++。边界还刻意粗粒度以摊薄 cgo 调用开销。",
                    "en": "cgo crosses C's ABI. C++ name mangling makes symbols unmatchable to Go, so the many *_c.h/*_c.cpp files in Milvus core are 'C facades for Go,' with the real working C++ behind. The boundary is also kept coarse to amortize cgo call overhead.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课强调 segcore 在段内还默默做 MVCC：结合删除位图与 guarantee ts 的时间过滤，只让“该看到”的那一版数据可见。请思考：为什么把这层可见性判定放在“最贴近数据的段内”执行，而不是在 Proxy 或 delegator 统一过滤？这对正确性和性能各有什么意义？（可结合第 20 课删除、第 30 课一致性。）",
                "en": "This lesson stressed that segcore silently does MVCC inside a segment: combining the delete bitmap and the guarantee-ts time filter so only the 'should-be-seen' version is visible. Consider: why perform this visibility judgment 'inside the segment, closest to the data' rather than filtering uniformly at the Proxy or delegator? What does this mean for correctness and for performance? (Tie in Lesson 20 deletes and Lesson 30 consistency.)",
            },
        ],
    },
    "28-execution-engine.html": {
        "mcq": [
            {
                "q": {
                    "zh": "在 Milvus 的混合查询里，执行引擎（exec）对标量过滤求值后，产出什么交给向量检索？",
                    "en": "In a Milvus hybrid query, after the execution engine (exec) evaluates the scalar filter, what does it hand to the vector search?",
                },
                "opts": [
                    {"zh": "一张 bitset：每行 1 bit，标记是否满足过滤条件，作为向量检索的剪枝掩码", "en": "A bitset: one bit per row marking pass/fail, used as the pruning mask for vector search"},
                    {"zh": "一份重新排序后的原始向量副本", "en": "A re-sorted copy of the raw vectors"},
                    {"zh": "一个 SQL 结果集", "en": "A SQL result set"},
                    {"zh": "一棵新的索引树", "en": "A freshly built index tree"},
                ],
                "answer": 0,
                "why": {
                    "zh": "exec 在列式分块上向量化地求值过滤，产出一张 bitset（合格行掩码）。向量检索只在置 1 的行里找最近邻——这就是用 bitset 剪枝。",
                    "en": "exec evaluates the filter in a vectorized way over columnar chunks, producing a bitset (qualifying-row mask). The vector search only looks at the 1-bits — that is bitset pruning.",
                },
            },
            {
                "q": {
                    "zh": "为什么 Milvus 默认“先过滤、再检索”，而不是“先检索、再过滤”？",
                    "en": "Why does Milvus default to 'filter-then-search' rather than 'search-then-filter'?",
                },
                "opts": [
                    {"zh": "先过滤能保证在合格集合里稳稳取够 topK；先检索再过滤可能把 topK 过滤掉、结果不足 K 条", "en": "Filtering first reliably yields a full topK within the qualifying set; searching first then filtering may drop most of topK, leaving fewer than K"},
                    {"zh": "因为过滤比向量检索更慢，要先做完", "en": "Because filtering is slower than vector search, so do it first"},
                    {"zh": "因为先检索会损坏索引", "en": "Because searching first corrupts the index"},
                    {"zh": "两者完全等价，只是习惯", "en": "They are equivalent; it's just convention"},
                ],
                "answer": 0,
                "why": {
                    "zh": "若先取 topK 再过滤，命中条件的可能不足 K 条，只能调大 topK 反复重搜，既慢又不稳。先过滤把检索约束在合格集合里，既保证结果数、又省下最贵的向量计算。",
                    "en": "Take topK first then filter and you may end up with fewer than K matches, forcing repeated retries with a larger topK — slow and unstable. Filtering first constrains the search to the qualifying set, guaranteeing the count and saving the most expensive vector compute.",
                },
            },
            {
                "q": {
                    "zh": "为什么要把过滤字符串编译成表达式树、再用向量化引擎按“块”求值，而不是逐行解释执行？",
                    "en": "Why compile the filter string into an expression tree and evaluate it 'by chunk' with a vectorized engine, instead of interpreting it row by row?",
                },
                "opts": [
                    {"zh": "解析只做一次、可复用与优化；按列分块批量求值能用 SIMD、对缓存友好、几乎无分支预测失败，远快于逐行", "en": "Parse once (reusable + optimizable); batched per-column/chunk evaluation uses SIMD, is cache-friendly with almost no branch mispredictions — far faster than row-by-row"},
                    {"zh": "为了让结果按字母排序", "en": "To sort results alphabetically"},
                    {"zh": "为了节省磁盘空间", "en": "To save disk space"},
                    {"zh": "树只是为了好看，对性能没影响", "en": "The tree is just cosmetic, no performance impact"},
                ],
                "answer": 0,
                "why": {
                    "zh": "树让同一过滤被多段多块复用，并能做常量折叠/短路/区间合并等优化；列式分块 + 向量化把零散的逐行计算变成批量的按列计算，充分利用 SIMD 与缓存，这是现代分析型执行引擎快的根本。",
                    "en": "A tree lets the same filter be reused across segments/chunks and enables constant-folding/short-circuit/range-merge optimizations; columnar chunks + vectorization turn scattered row-wise work into batched column-wise work that exploits SIMD and cache — the basis of a fast modern analytical engine.",
                },
            },
        ],
        "open": [
            {
                "zh": "设想一个过滤极强的查询（合格行只占 0.1%），又要在 HNSW 这类图索引上做相似检索。“先过滤”可能让可走的图节点变得很稀疏、跳不到下一跳，从而影响召回。请思考：引擎可以用哪些策略来兼顾“过滤约束”与“召回”？（提示：放宽搜索范围、对极小候选集直接暴力计算……）这说明过滤的强弱会如何反过来影响检索策略？",
                "en": "Imagine a very selective query (only 0.1% of rows qualify) that also needs similarity search on a graph index like HNSW. 'Filter first' can make the navigable graph too sparse to hop through, hurting recall. Consider: what strategies can the engine use to balance the filter constraint with recall? (Hints: widen the search scope, brute-force a tiny candidate set…) What does this reveal about how filter selectivity feeds back into search strategy?",
            },
        ],
    },
    "29-reduce.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 一次分布式搜索的结果归并（Reduce）发生在哪几层？",
                    "en": "At which levels does Milvus merge (Reduce) the results of one distributed search?",
                },
                "opts": [
                    {"zh": "三层：段内(segcore Reduce.cpp) → 节点内(delegator) → 跨分片(Proxy)，逐级向上", "en": "Three levels: in-segment (segcore Reduce.cpp) → in-node (delegator) → cross-shard (Proxy), bottom-up"},
                    {"zh": "只在 Proxy 一处一次性完成", "en": "Only once, entirely at the Proxy"},
                    {"zh": "只在每个段内完成，不需要再合并", "en": "Only inside each segment, no further merging"},
                    {"zh": "在客户端 SDK 里完成", "en": "In the client SDK"},
                ],
                "answer": 0,
                "why": {
                    "zh": "归并顺着数据的物理分布分三层：段内先 reduce 出本段 topK，节点(delegator)把本分片各段合并，Proxy 最后跨分片合并出全局 topK。每层只上交局部 topK。",
                    "en": "Merging follows the data's physical layout in three levels: each segment reduces to its topK, the node (delegator) merges a shard's segments, and the Proxy finally merges across shards into the global topK. Each level only sends up a local topK.",
                },
            },
            {
                "q": {
                    "zh": "为什么分层归并能扩展到十亿级，而“把所有候选发到一处统一排序”不行？",
                    "en": "Why does hierarchical merging scale to billions while 'send all candidates to one place and sort' does not?",
                },
                "opts": [
                    {"zh": "因为局部 topK 的并集必含全局 topK，每层只需上交 K 条，网络上始终只流动 K 量级数据", "en": "Because the union of local topKs contains the global topK, so each level sends only K items — only K-scale data ever crosses the network"},
                    {"zh": "因为分层用了 GPU", "en": "Because levels use the GPU"},
                    {"zh": "因为分层不需要排序", "en": "Because levels skip sorting"},
                    {"zh": "因为分层把数据压缩了", "en": "Because levels compress the data"},
                ],
                "answer": 0,
                "why": {
                    "zh": "最终只要 K 条，凡是进不了某层前 K 的都进不了全局前 K，所以每层只上交自己的前 K。于是 Proxy 只面对 S×K 条（与底层总量无关），而一次性汇总要搬运/排序随数据量爆炸的海量候选。",
                    "en": "Only K items are needed; anything outside a level's top K can't be in the global top K, so each level sends only its top K. The Proxy then faces just S×K (independent of total data), whereas one-shot gather must move/sort candidates that explode with data volume.",
                },
            },
            {
                "q": {
                    "zh": "归并时为什么必须“按主键去重”？",
                    "en": "Why must a merge 'dedup by primary key'?",
                },
                "opts": [
                    {"zh": "因为同一实体可能跨多个段出现(growing 新值/sealed 旧值/删除墓碑)，不去重会返回重复或过期版本", "en": "Because the same entity may appear across segments (growing new value / sealed old value / delete tombstone); without dedup you'd return duplicates or stale versions"},
                    {"zh": "因为主键能让结果按字母排序", "en": "Because the PK sorts results alphabetically"},
                    {"zh": "因为去重能减少网络流量", "en": "Because dedup reduces network traffic"},
                    {"zh": "因为不去重会损坏索引", "en": "Because not deduping corrupts the index"},
                ],
                "answer": 0,
                "why": {
                    "zh": "在“日志即数据、段不可变”的模型里，一条数据可能同时存在于多个段（旧值、新 upsert、墓碑并存）。归并必须按主键认人，并配合时间戳/删除位图只留“该看到”的那一版，否则结果会重复或过期。",
                    "en": "In a 'log-as-data, immutable-segment' model, one row may exist in several segments (old value, new upsert, tombstone). The merge must identify by PK and, with timestamp/delete bitmap, keep only the 'should-be-seen' version, or results would be duplicated or stale.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说“归并本身是精确的，近似发生在段内 ANN 检索”。请据此推理：如果一次搜索召回率不理想，你应该调哪些旋钮（提示：nprobe/ef、段内检索精度），而不是动归并？再想想：为什么深翻页(offset 很大)会让归并变贵？要支持“无限下滑”的场景，比用大 offset 更好的做法是什么？",
                "en": "This lesson says 'the merge is exact; approximation happens in the in-segment ANN search'. Reason from that: if a search's recall is poor, which knobs should you tune (hint: nprobe/ef, in-segment search precision) rather than the merge? Then consider: why does deep pagination (large offset) make the merge expensive, and what is a better approach than a large offset for an 'infinite scroll' scenario?",
            },
        ],
    },
    "30-consistency-and-timestamps.html": {
        "mcq": [
            {
                "q": {
                    "zh": "一次读请求带的“保证时间戳 Tg”，含义是什么？它由什么决定？",
                    "en": "What does the 'guarantee timestamp Tg' on a read mean, and what determines it?",
                },
                "opts": [
                    {"zh": "“至少让我看到截至 Tg 的所有写入”；由这次读选的一致性级别决定（parseGuaranteeTsFromConsistency）", "en": "'Let me see at least all writes up to Tg'; set by the read's consistency level (parseGuaranteeTsFromConsistency)"},
                    {"zh": "数据在磁盘上的物理地址", "en": "The data's physical address on disk"},
                    {"zh": "查询要返回多少条结果(topK)", "en": "How many results the query returns (topK)"},
                    {"zh": "向量的维度", "en": "The vector dimension"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Tg 表达“这次读要求看到截至哪一刻的写入”。一致性级别把它映射成具体值：Strong=最新 tMax、Bounded=tMax−gracefulTime、Eventually=1、Session=本会话上次写、Customized=用户指定。",
                    "en": "Tg expresses 'up to which moment this read must see writes'. The consistency level maps it: Strong=latest tMax, Bounded=tMax−gracefulTime, Eventually=1, Session=this session's last write, Customized=user-given.",
                },
            },
            {
                "q": {
                    "zh": "QueryNode 靠什么机制“保证”读到截至 Tg 的全部写入？",
                    "en": "By what mechanism does a QueryNode 'guarantee' it sees all writes up to Tg?",
                },
                "opts": [
                    {"zh": "维护 tsafe(已消费的 WAL TimeTick)；当 tsafe ≥ Tg 才回答，否则挂起等待(或超时)", "en": "It tracks tsafe (the consumed WAL TimeTick); it answers only when tsafe ≥ Tg, otherwise it waits (or times out)"},
                    {"zh": "锁住整个集合，禁止写入", "en": "It locks the whole collection, blocking writes"},
                    {"zh": "重启自己以加载最新数据", "en": "It restarts itself to load the latest data"},
                    {"zh": "直接相信本地时钟", "en": "It simply trusts its local clock"},
                ],
                "answer": 0,
                "why": {
                    "zh": "节点的 tsafe 表示它已把 WAL 消费/应用到哪个 TimeTick。读到来时若 tsafe ≥ Tg，说明截至 Tg 的写入都在，立即搜；否则挂起等待 tsafe 追上 Tg。这就是“保证”二字的来源(how-guarantee-ts-works)。",
                    "en": "A node's tsafe is how far it has consumed/applied the WAL (a TimeTick). On a read, if tsafe ≥ Tg all writes up to Tg are present, so search now; otherwise it waits until tsafe catches up. That is the source of the word 'guarantee'.",
                },
            },
            {
                "q": {
                    "zh": "关于 Milvus 的一致性级别，下面哪种说法正确？",
                    "en": "Which statement about Milvus consistency levels is correct?",
                },
                "opts": [
                    {"zh": "它只决定“这次读能看到多新的写”，不影响写入是否持久化；同一集合不同查询可用不同级别", "en": "It only decides 'how fresh a read sees writes', not whether writes persist; different queries on one collection can use different levels"},
                    {"zh": "它是整个库的全局开关，改一次影响所有读写", "en": "It is a global switch for the whole DB, changing it affects all reads and writes"},
                    {"zh": "选 Eventually 会导致数据丢失", "en": "Choosing Eventually causes data loss"},
                    {"zh": "Strong 一定比 Bounded 快", "en": "Strong is always faster than Bounded"},
                ],
                "answer": 0,
                "why": {
                    "zh": "一致性级别是“每次读自带的新鲜度要求”，不改变写入的持久化与最终可见性。所以后台对账可用 Strong、用户搜索用 Bounded、离线刷库用 Eventually，互不影响。Strong 最新但可能要等，未必更快。",
                    "en": "A level is a 'per-read freshness requirement'; it doesn't change write persistence or eventual visibility. So a reconciliation job can use Strong, user search Bounded, offline backfill Eventually — independently. Strong is freshest but may wait, not necessarily faster.",
                },
            },
        ],
        "open": [
            {
                "zh": "为你自己的一个场景选一个一致性级别并说明理由：比如“用户上传一张图后立刻以图搜图”“电商首页的相似商品推荐(高并发)”“离线批量去重”“审计回放某历史时刻的数据”。分别该选 Strong / Bounded / Session / Eventually / Customized 中的哪个？把“能容忍多旧”与“延迟要求”这两条线索用上。",
                "en": "Pick a consistency level for one of your own scenarios and justify it: e.g. 'a user uploads an image then immediately does image-to-image search', 'similar-product recommendation on a busy storefront (high concurrency)', 'offline batch dedup', 'audit replay of data as of a historical moment'. Which of Strong / Bounded / Session / Eventually / Customized fits each? Use the two clues: 'how stale can it tolerate' and 'latency requirement'.",
            },
        ],
    },
    "31-wal-architecture.html": {
        "mcq": [
            {
                "q": {
                    "zh": "在 Milvus 流式系统里，StreamingCoord 和 StreamingNode 的分工是什么？",
                    "en": "In Milvus's streaming system, how do StreamingCoord and StreamingNode divide the work?",
                },
                "opts": [
                    {"zh": "StreamingCoord(单例，在 RootCoord 内)调度——把 PChannel 分给 StreamingNode；StreamingNode 执行——真正写每条 PChannel 的 WAL", "en": "StreamingCoord (a singleton inside RootCoord) schedules — assigns PChannels to StreamingNodes; StreamingNode executes — actually writes each PChannel's WAL"},
                    {"zh": "两者都直接写日志，没有分工", "en": "Both write the log directly, with no division"},
                    {"zh": "StreamingNode 调度、StreamingCoord 写日志", "en": "StreamingNode schedules and StreamingCoord writes the log"},
                    {"zh": "它们只负责读，不负责写", "en": "They only read, never write"},
                ],
                "answer": 0,
                "why": {
                    "zh": "这又是“协调者调度、节点执行”的体现：StreamingCoord 做通道管理(把 PChannel 分给节点、健康监控、再均衡)但自己不写日志；StreamingNode 为分到的每条 PChannel 跑完整 WAL(拦截器链+scanner+RecoveryStorage)。",
                    "en": "Another 'coordinator schedules, node executes': StreamingCoord does channel management (assign PChannels, health monitoring, rebalancing) but writes no log; StreamingNode runs the full WAL (interceptor chain + scanner + RecoveryStorage) for each assigned PChannel.",
                },
            },
            {
                "q": {
                    "zh": "每次 Append 都要穿过一条“拦截器链”，下列哪组是它的主要环节？",
                    "en": "Every Append passes an 'interceptor chain'. Which set are its main stages?",
                },
                "opts": [
                    {"zh": "TimeTick(盖单调时间戳) / Txn(事务) / Shard(段分配) / Lock(独占或共享)", "en": "TimeTick (stamp a monotonic ts) / Txn (transaction) / Shard (segment assignment) / Lock (exclusive/shared)"},
                    {"zh": "压缩 / 加密 / 去重 / 排序", "en": "compress / encrypt / dedup / sort"},
                    {"zh": "解析 SQL / 优化 / 执行 / 返回", "en": "parse SQL / optimize / execute / return"},
                    {"zh": "建索引 / 查索引 / 删索引 / 重建", "en": "build index / query index / drop index / rebuild"},
                ],
                "answer": 0,
                "why": {
                    "zh": "拦截器把横切关注点拆开、按序串联：TimeTick 盖那把读路径要等的时钟、Txn 管事务原子性、Shard 决定段 ID(段在此刻才分配)、Lock 控制并发独占。要加新写语义，挂个新拦截器即可。",
                    "en": "The chain separates cross-cutting concerns in order: TimeTick stamps the clock the read path waits on, Txn handles transaction atomicity, Shard decides the segment ID (segments are assigned here), Lock controls concurrent exclusivity. A new write semantic is just a new interceptor.",
                },
            },
            {
                "q": {
                    "zh": "关于 WAL Backend 与崩溃恢复，下列哪种说法正确？",
                    "en": "Which statement about the WAL Backend and crash recovery is correct?",
                },
                "opts": [
                    {"zh": "Backend 可插拔(Kafka/Pulsar/Woodpecker/RocksMQ，一 PChannel 一 topic)；RecoveryStorage 靠检查点+重放 WAL 确定性地重建状态", "en": "The backend is pluggable (Kafka/Pulsar/Woodpecker/RocksMQ, one topic per PChannel); RecoveryStorage rebuilds state deterministically via checkpoint + WAL replay"},
                    {"zh": "Backend 写死为 Kafka，不可更换", "en": "The backend is hard-coded to Kafka and cannot change"},
                    {"zh": "崩溃后数据无法恢复，只能重灌", "en": "After a crash data can't recover, you must reload"},
                    {"zh": "恢复靠各节点的本地时钟对齐", "en": "Recovery relies on aligning nodes' local clocks"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Milvus 把“日志存储”抽象成可插拔接口(walimpls)，一个 PChannel 对应一个 topic；崩溃后 RecoveryStorage 从最近检查点重放其后的 WAL。因为 WAL 是单一事实来源且每条带单调 TimeTick，重放是确定性的，状态能一字不差重建。",
                    "en": "Milvus abstracts log storage into a pluggable interface (walimpls), one PChannel per topic; after a crash RecoveryStorage replays the WAL from the latest checkpoint. Because the WAL is the single source of truth with monotonic TimeTicks, replay is deterministic and state rebuilds exactly.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说 Milvus 把“WAL=主角、段/索引=可由日志重建的派生数据”，这与传统单机数据库(WAL 只是为崩溃恢复的副产物、表才是主角)正好主次相反。请思考：这个“主次反转”让 Milvus 获得了哪些能力(如让段留在内存、多种数据形态异步追日志、副本/CDC 靠复制日志同步)？它又带来什么代价或前提(对 WAL 的可靠性、有序性、可重放性的强依赖)？",
                "en": "This lesson says Milvus makes 'the WAL the protagonist, with segments/indexes as log-derivable derived data' — the opposite priority of a traditional single-node DB (where the WAL is just a crash-recovery byproduct and tables are the protagonist). Consider: what capabilities does this 'inversion' buy Milvus (segments in memory, multiple data forms tailing the log asynchronously, replicas/CDC syncing by copying the log)? And what cost or precondition does it impose (a strong dependence on the WAL's reliability, ordering and replayability)?",
            },
        ],
    },
    "32-ddl-dcl-via-log.html": {
        "mcq": [
            {
                "q": {
                    "zh": "为什么 DDL/DCL(建/删集合、RBAC 等)不能像普通 insert 那样只写进一条 PChannel？",
                    "en": "Why can't DDL/DCL (create/drop collection, RBAC, etc.) just write into one PChannel like an ordinary insert?",
                },
                "opts": [
                    {"zh": "因为它们改的是整个集合/集群的元信息，必须对所有相关 PChannel 原子生效，否则分片间会对“集合是否存在/schema/权限”产生分裂认知", "en": "Because they change whole-collection/cluster metadata and must take effect atomically across all relevant PChannels, or shards would split on 'does the collection exist / schema / permissions'"},
                    {"zh": "因为 DDL 数据量太大，一条日志放不下", "en": "Because DDL is too large to fit in one log"},
                    {"zh": "因为 DDL 必须比 DML 慢", "en": "Because DDL must be slower than DML"},
                    {"zh": "因为 PChannel 不支持写元数据", "en": "Because PChannels can't store metadata"},
                ],
                "answer": 0,
                "why": {
                    "zh": "DML 只影响某些行(进一条 PChannel)；DDL/DCL 改的是 schema/分区/权限等对整个集合所有分片都成立的元信息。若只广播到一半 PChannel，分片间就会对“集合是否存在”等持不同认知，造成元信息层面的不一致——这是正确性底线，故须原子。",
                    "en": "DML affects some rows (one PChannel); DDL/DCL change metadata (schema/partitions/permissions) true for all of a collection's shards. If broadcast to only half the PChannels, shards disagree on 'does the collection exist', causing metadata-level inconsistency — a correctness floor, hence atomicity.",
                },
            },
            {
                "q": {
                    "zh": "Broadcaster 如何保证一次 DDL/DCL 的“原子广播”？",
                    "en": "How does the Broadcaster ensure a DDL/DCL's 'atomic broadcast'?",
                },
                "opts": [
                    {"zh": "StreamingClient.Broadcast → 资源加锁 → 分发到所有相关 PChannel → 收齐每条 PChannel 的 ACK → 释放锁", "en": "StreamingClient.Broadcast → lock the resource → distribute to all relevant PChannels → collect each PChannel's ACK → release the lock"},
                    {"zh": "直接写 etcd，绕过所有 PChannel", "en": "Write etcd directly, bypassing all PChannels"},
                    {"zh": "随机选一条 PChannel 写入即可", "en": "Just write to one random PChannel"},
                    {"zh": "让客户端自己挨个通知每个分片", "en": "Have the client notify each shard one by one"},
                ],
                "answer": 0,
                "why": {
                    "zh": "DDL 走 Broadcast 而非 Append：Broadcaster 先锁住本次变更涉及的资源(防并发冲突)，把消息分发到所有相关 PChannel(各自写进 WAL)，追踪每条的 ACK，全部确认后才算成功并释放锁。锁+全员 ACK 共同实现“全有或全无”。",
                    "en": "DDL goes via Broadcast, not Append: the Broadcaster locks the affected resource (preventing concurrent conflict), distributes the message to all relevant PChannels (each writes its WAL), tracks each ACK, and succeeds only after all confirm, then releases the lock. Lock + all-acks give 'all-or-nothing'.",
                },
            },
            {
                "q": {
                    "zh": "为什么 Milvus 要把 DDL 也编进 WAL，而不是只写进 etcd？",
                    "en": "Why does Milvus also encode DDL into the WAL, rather than only writing it into etcd?",
                },
                "opts": [
                    {"zh": "为了让“改结构”和“改数据”共用同一条日志、同一套 TimeTick，从而天然有序(如“先建集合再写入”的因果)、可重放、对所有消费者一致", "en": "So 'changing structure' and 'changing data' share one log and one TimeTick — naturally ordered (e.g. 'create then write' causality), replayable, consistent for all consumers"},
                    {"zh": "因为 etcd 容量不够", "en": "Because etcd lacks capacity"},
                    {"zh": "为了让 DDL 更慢以便观察", "en": "To make DDL slower for observability"},
                    {"zh": "WAL 比 etcd 更省钱", "en": "The WAL is cheaper than etcd"},
                ],
                "answer": 0,
                "why": {
                    "zh": "若 DDL 走 etcd、DML 走 WAL，两条时间线难以保证“先建集合后写入”的因果。把 DDL 也编进同一条 WAL、用同一套 TimeTick 排序，结构变更与数据变更落在同一条时间线上，顺序对所有人一致；DDL 也因此获得可重放、可被多方消费等好处。元数据最终仍落 etcd，但“何时发生/如何排序”由 WAL 裁定。",
                    "en": "If DDL went via etcd and DML via the WAL, two timelines make 'create-then-write' causality hard. Encoding DDL into the same WAL with the same TimeTick puts structural and data changes on one timeline, consistent for all; DDL also gains replayability and multi-consumer benefits. Metadata still lands in etcd, but 'when/how-ordered' is adjudicated by the WAL.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课把“原子性”分成了两个维度：跨 PChannel 的原子(Broadcaster：锁+全员 ACK)与单 PChannel 内多条写入的原子(事务：Txn 拦截器)。请各想一个需要它们的具体例子(如：建集合要让所有分片同时认账；一次批量 upsert 要么都见要么都不见)。再思考：如果某条 PChannel 在广播中迟迟不 ACK(其节点宕机)，结合第 31 课的“节点失联→PChannel 重新分配→从检查点重放”，系统最终如何仍收敛到一致？",
                "en": "This lesson split 'atomicity' into two dimensions: cross-PChannel atomicity (Broadcaster: lock + all-acks) and within-PChannel multi-write atomicity (transactions: the Txn interceptor). Think of a concrete example needing each (e.g. create-collection must be acknowledged by all shards at once; a batch upsert must be all-or-nothing visible). Then consider: if one PChannel never ACKs during a broadcast (its node crashed), how — combined with Lesson 31's 'node lost → PChannel reassigned → replay from checkpoint' — does the system still converge to consistency?",
            },
        ],
    },
    "33-replication-and-cdc.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 跨集群同步数据，采用的核心思路是什么？",
                    "en": "What is the core idea behind Milvus's cross-cluster data sync?",
                },
                "opts": [
                    {"zh": "复制 WAL 并在对方重放(CDC：传“发生了什么”)，因 WAL 是单一事实来源、重放确定性，几乎不需特殊逻辑", "en": "Replicate the WAL and replay it on the other side (CDC: ship 'what happened'); since the WAL is the single source of truth and replay is deterministic, almost no special logic is needed"},
                    {"zh": "定期把表/段/索引整份拷贝过去(复制最终状态)", "en": "Periodically copy tables/segments/indexes wholesale (replicate final state)"},
                    {"zh": "让两个集群都能写并互相覆盖", "en": "Let both clusters write and overwrite each other"},
                    {"zh": "靠各集群本地时钟对齐数据", "en": "Align data by each cluster's local clock"},
                ],
                "answer": 0,
                "why": {
                    "zh": "复制状态又重又难(数据在变、要处理增量/冲突/版本)；Milvus 复制的是“变更日志”这条有序流，对方按同序重放即得同状态。因为本就有一条记录全部变更、全局有序、可重放的 WAL，复制只是给它多一个异地消费者。",
                    "en": "Replicating state is heavy and hard (data changes; handle increments/conflicts/versions); Milvus replicates the ordered stream of 'changes' and the other side replays in order to the same state. Because there's already a WAL recording all changes, globally ordered and replayable, replication is just one more remote consumer of it.",
                },
            },
            {
                "q": {
                    "zh": "在复制链路里，备集群 Proxy 上那个 Replicate 拦截器的关键职责是什么？",
                    "en": "In the replication chain, what is the key duty of the Replicate interceptor on the secondary's Proxy?",
                },
                "opts": [
                    {"zh": "识别“这是复制来的消息”，保留其原有 TimeTick、不重新盖戳，以保证主备两边重放顺序严格一致", "en": "Recognize 'this is a replicated message', keep its original TimeTick and not re-stamp it, so the replay order on primary and secondary stays strictly identical"},
                    {"zh": "把消息压缩后再写入", "en": "Compress the message before writing"},
                    {"zh": "给复制来的消息盖一个备集群的新时间戳", "en": "Stamp replicated messages with a fresh secondary timestamp"},
                    {"zh": "丢弃所有重复消息", "en": "Discard all duplicate messages"},
                ],
                "answer": 0,
                "why": {
                    "zh": "普通写入进 WAL 时 TimeTick 拦截器会盖本地新戳；但复制来的消息已带主集群的 TimeTick，若再盖一个，两边顺序就错位、状态不一致。Replicate 拦截器恰恰反过来：保留原序、不乱盖戳。整套复制里“特殊”的部分，少到只剩这一个拦截器。",
                    "en": "On a normal write the TimeTick interceptor stamps a fresh local ts; but a replicated message already carries the primary's TimeTick — stamping again would misalign order and break consistency. The Replicate interceptor does the opposite: keep the original order, don't re-stamp. The only 'special' part of replication is this one interceptor.",
                },
            },
            {
                "q": {
                    "zh": "为什么 Milvus 的跨集群复制用“星型(一主多备、单向)”而不是多主互相同步？",
                    "en": "Why does Milvus use a 'star (one primary, many secondaries, one-way)' topology rather than multi-primary mutual sync?",
                },
                "opts": [
                    {"zh": "保证“唯一真相源头”、避免多主冲突(同一数据被两边同时改成不同值)；复杂度收敛，切换由 controller 显式管理", "en": "To keep a single source of truth and avoid multi-primary conflicts (the same row changed to different values on both sides); complexity converges, and role switches are explicitly managed by the controller"},
                    {"zh": "因为星型比网状传得更快", "en": "Because a star transmits faster than a mesh"},
                    {"zh": "因为 Milvus 不支持多于两个集群", "en": "Because Milvus supports no more than two clusters"},
                    {"zh": "因为单向复制不需要网络", "en": "Because one-way replication needs no network"},
                ],
                "answer": 0,
                "why": {
                    "zh": "多主互写会遇到经典冲突：同一条数据被两边几乎同时改成不同值，难以仲裁。星型让变更从唯一源头单向流出、备只读，根本不给冲突留余地；需要切换时由 CDC controller 显式变更角色。这与 TSO 单源发号、Broadcaster 单源广播是同一种“收敛到权威源头”的审美。",
                    "en": "Multi-primary writes hit the classic conflict: the same row changed to different values on both sides, hard to arbitrate. A star makes change flow one-way from a single source with read-only secondaries, leaving no room for conflict; switches are made explicitly by the CDC controller. Same 'converge to one authority' aesthetic as the single-source TSO and Broadcaster.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说“状态 = 日志的重放结果”，于是崩溃恢复、边写边查、DDL 原子生效、跨集群复制都成了“对同一条日志的操作”。请挑其中两三个，分别说明它们各自是“谁在重放这条日志、为了得到什么状态”。再思考：复制延迟如何影响容灾的 RPO(能丢多少数据)？要把 RPO 压到极小、甚至不丢，需要付出什么代价(回忆第 30 课的一致性/新鲜度 vs 性能取舍)？",
                "en": "This lesson says 'state = the result of replaying the log', so crash recovery, query-while-write, atomic DDL, and cross-cluster replication all become 'operations on the same log'. Pick two or three and explain, for each, 'who replays the log, to obtain what state'. Then consider: how does replication lag affect DR's RPO (how much data can be lost)? What is the cost of pushing RPO to near-zero or zero (recall Lesson 30's consistency/freshness vs performance trade-off)?",
            },
        ],
    },
    "34-core-layout.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 把“控制面用 Go、计算内核用 C++”这样切分，主要的理由是什么？",
                    "en": "Why does Milvus split it as 'control plane in Go, compute core in C++'?",
                },
                "opts": [
                    {"zh": "两类活性质不同：控制面（调度/RPC/并发）要开发效率与并发力(Go 之长)，计算面(海量向量距离/过滤)要极致性能与贴硬件(C++ 之长)，各扬其长", "en": "The two kinds of work differ: the control plane (scheduling/RPC/concurrency) wants velocity and concurrency (Go's strength); the compute plane (massive vector distance/filtering) wants peak performance close to hardware (C++'s strength) — each to its strength"},
                    {"zh": "因为 Go 不能编译成机器码", "en": "Because Go cannot compile to machine code"},
                    {"zh": "因为 C++ 比 Go 更容易写并发与 RPC", "en": "Because C++ is easier than Go for concurrency and RPC"},
                    {"zh": "纯粹是历史包袱，没有设计理由", "en": "Purely legacy baggage, with no design reason"},
                ],
                "answer": 0,
                "why": {
                    "zh": "控制面要的是开发效率、并发表达力、丰富生态——Go 的 goroutine/GC 正合适；计算面是每秒上亿次浮点的热路径，要 SIMD、精细内存布局、可调 GPU——C++ 的主场，而 GC 在此会成负担。于是清晰切分、cgo 衔接，换来“既好开发、又跑得飞快”。",
                    "en": "The control plane wants developer velocity, concurrency expressiveness and a rich ecosystem — Go's goroutines/GC fit. The compute plane is a hundreds-of-millions-of-FLOPs hot path wanting SIMD, fine memory layout and GPU — C++'s turf, where GC is a burden. Hence the clean split bridged by cgo: 'easy to develop, and blazingly fast'.",
                },
            },
            {
                "q": {
                    "zh": "为什么 Go 调 C++ 内核要经过一层 C 风格接口(如 segment_c.h)，而不是直接调 C++ 类？",
                    "en": "Why does Go call the C++ core through a C-style interface (e.g. segment_c.h) instead of C++ classes directly?",
                },
                "opts": [
                    {"zh": "cgo 只能跨越 C ABI，C++ 的类/模板/异常无法直接跨语言，于是 C++ 内部照常用类/模板，对外只露一层扁平的 C 函数", "en": "cgo can only cross the C ABI; C++ classes/templates/exceptions can't cross languages directly, so C++ uses classes/templates internally but exposes only a flat layer of C functions"},
                    {"zh": "因为 C 函数比 C++ 方法跑得快", "en": "Because C functions run faster than C++ methods"},
                    {"zh": "因为 Milvus 内核其实是用 C 而非 C++ 写的", "en": "Because the core is actually written in C, not C++"},
                    {"zh": "为了让 Go 能继承 C++ 的类", "en": "So that Go can inherit from C++ classes"},
                ],
                "answer": 0,
                "why": {
                    "zh": "cgo 的桥只认 C ABI——C++ 的类、模板、异常这些高级特性没法直接跨语言传递。于是内核对外包一层以 _c.h/_c.cpp 结尾的扁平 C 函数(创建段/灌数据/搜索/释放)，Go 侧再用 LocalSegment 这类封装把脏活包好。这让两种语言各自保持地道，只在边界用最朴素的 C 函数对接。",
                    "en": "cgo's bridge only speaks the C ABI — C++ classes, templates and exceptions can't pass across languages directly. So the core wraps a flat layer of C functions (ending in _c.h/_c.cpp: create segment/load/search/release), and the Go side hides the dirty work behind wrappers like LocalSegment. Both languages stay idiomatic, meeting only at the boundary with plain C functions.",
                },
            },
            {
                "q": {
                    "zh": "关于 C++ 内核服务的“两条路径”，下面哪个说法正确？",
                    "en": "About the 'two paths' the C++ core serves, which statement is correct?",
                },
                "opts": [
                    {"zh": "查询路径(QueryNode 搜段)与索引构建路径(worker 把 sealed 段交给 Knowhere 建索引)共用同一套内核，关键数据结构/算法只实现一次", "en": "The query path (QueryNode searching a segment) and the index-build path (a worker handing a sealed segment to Knowhere) share the same core, so key data structures/algorithms are implemented once"},
                    {"zh": "查询和建索引各有一套完全独立、互不相干的 C++ 内核", "en": "Query and index build each have a fully independent, unrelated C++ core"},
                    {"zh": "内核只服务查询，建索引完全在 Go 里完成", "en": "The core only serves queries; index building is done entirely in Go"},
                    {"zh": "内核只服务建索引，查询完全在 Go 里完成", "en": "The core only serves index building; queries are done entirely in Go"},
                ],
                "answer": 0,
                "why": {
                    "zh": "无论“读”还是“建索引”，最重的计算都落在同一套 C++ 内核里：段的列式布局、距离计算、Knowhere 索引类型只实现一次，查询时用、建索引时也用，不必维护两套可能算得不一致的代码。可把内核想成一座“中央厨房”，前台点“搜索”、后厨下“建索引”单，同一套灶具按订单类型出餐。",
                    "en": "Whether 'reading' or 'index building', the heaviest computation lands in the same C++ core: the columnar layout, distance math and Knowhere index types are implemented once, used at both query and build time, with no second divergent copy. Think of the core as a 'central kitchen' — the front desk orders 'search', the back-of-house drops an 'index build' ticket, same stoves plating by order type.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课把 Milvus 看成“Go 控制面 + cgo 桥 + C++ 计算面”。请用自己的话说清：(1) 一次段内搜索是怎样从 Go 经 cgo 进入 segcore、再返回的(回忆那条 Go 封装→过 cgo→C++ 计算→结果回传的链)；(2) 为什么 cgo 调用要“粗粒度、零拷贝”——把一整次搜索打包成一次调用、数据尽量传指针，对性能意味着什么？再结合第 29 课，说说“批量搜(大 nq)”为何能摊薄过桥的固定开销。",
                "en": "This lesson frames Milvus as 'Go control plane + cgo bridge + C++ compute plane'. In your own words: (1) how does one in-segment search go from Go through cgo into segcore and back (recall the chain Go wrapper → cross cgo → C++ compute → result returned)? (2) Why must cgo calls be 'coarse-grained, zero-copy' — packing a whole search into one call and passing pointers — and what does that mean for performance? Tie it to Lesson 29: why does batching (large nq) amortize the fixed cost of crossing the bridge?",
            },
        ],
    },
    "35-mmap-and-chunks.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 把一个段按“列（字段）”而不是按“行”来组织内存，主要好处是什么？",
                    "en": "Milvus organizes a segment's memory by 'column (field)' rather than by 'row'. What's the main benefit?",
                },
                "opts": [
                    {"zh": "一次检索只读用到的几列、数据连续、可用 SIMD 并行；按行存则要跳读并把同行无关字段拽进缓存，浪费带宽", "en": "A search reads only the few columns it needs, contiguously, with SIMD parallelism; row storage forces stride-reads that drag unrelated same-row fields into cache, wasting bandwidth"},
                    {"zh": "列存能让磁盘占用更小", "en": "Column storage makes disk usage smaller"},
                    {"zh": "列存让每条记录的写入更快", "en": "Column storage makes writing each record faster"},
                    {"zh": "列存不需要任何索引", "en": "Column storage needs no index at all"},
                ],
                "answer": 0,
                "why": {
                    "zh": "向量检索的特点是“对少数列做大量同质运算”（算距离、比阈值）。列存把同一字段的值连续摆放，查询只碰需要的列、顺序扫、缓存命中高，还能一条 SIMD 指令同时算 8/16 个浮点。按行存则要在内存里跳着读，每步顺带把同行几十个用不上的字段拉进缓存，白白浪费带宽——这正是分析/检索类系统普遍选列存的原因。",
                    "en": "Vector search does 'heavy homogeneous ops on a few columns' (distance, thresholds). Column storage lays a field's values contiguously, so a query touches only needed columns, scans sequentially with high cache hits, and computes 8/16 floats per SIMD instruction. Row storage strides through memory, dragging dozens of unused same-row fields into cache each step — wasted bandwidth. That's why analytics/search systems converge on columnar.",
                },
            },
            {
                "q": {
                    "zh": "为什么 Milvus 把一列再切成多个定长“块（chunk）”，而不是用一整块连续内存装下整列？",
                    "en": "Why does Milvus cut a column into many fixed-size 'chunks' instead of one contiguous block for the whole column?",
                },
                "opts": [
                    {"zh": "大块连续内存难分配，且 growing 段不断追加；分块后写满一块再要一块、老块不动，内存也能按块分配/换入换出", "en": "Large contiguous allocations are hard, and growing segments keep appending; with chunks you fill one then request another, old blocks stay put, and memory is allocated/swapped per block"},
                    {"zh": "因为分块能让数据自动加密", "en": "Because chunking auto-encrypts the data"},
                    {"zh": "因为一列最多只能放一个 chunk", "en": "Because a column may hold at most one chunk"},
                    {"zh": "因为分块后就不再需要 mmap", "en": "Because chunking removes the need for mmap"},
                ],
                "answer": 0,
                "why": {
                    "zh": "一列可能有上百万行，硬塞进一整块连续内存有两难：大块连续内存在碎片下可能根本分不出来；growing 段还在不断追加，每来一批就整体重分配、搬移，代价极高。分块把列切成定长小块：追加只需再要一块、老块原地不动；内存分配、释放、换入换出都以块为单位，粒度刚好；遍历就是一块接一块扫，块内连续、SIMD 友好。由 ChunkedColumnInterface 抽象、ChunkedColumn 等实现。",
                    "en": "A column may have millions of rows. One contiguous block has two problems: under fragmentation such a slab may not exist; and a growing segment keeps appending, so reallocating/copying the whole thing per batch is hugely costly. Chunking cuts the column into fixed-size blocks: append just asks for another, old blocks stay put; alloc/free/swap happen per block at just-right granularity; scanning walks block by block, each contiguous and SIMD-friendly. Abstracted by ChunkedColumnInterface, implemented by ChunkedColumn etc.",
                },
            },
            {
                "q": {
                    "zh": "用 mmap 把 binlog 映射进内存，相比直接 read() 整份读进堆，关键优势是什么？",
                    "en": "mmap-ing binlog into memory vs read()-ing it wholesale into heap — what's the key advantage?",
                },
                "opts": [
                    {"zh": "数据按需缺页调入、冷页由 OS 换出，于是一个节点能加载总量超过物理内存的段；代价是冷访问的磁盘延迟", "en": "Data faults in on demand and cold pages are evicted by the OS, so a node can load segments totaling more than physical RAM; the cost is cold-access disk latency"},
                    {"zh": "mmap 能让数据永远不丢、无需磁盘", "en": "mmap makes data never lost and needs no disk"},
                    {"zh": "mmap 把所有数据一次性全压进物理内存，所以更快", "en": "mmap crams all data into physical RAM at once, so it's faster"},
                    {"zh": "mmap 让 Milvus 不再需要 binlog 文件", "en": "mmap removes the need for binlog files"},
                ],
                "answer": 0,
                "why": {
                    "zh": "read() 把文件整份拷进堆，能加载的数据被物理内存卡死。mmap 则把文件映射进虚拟地址空间：访问到某页才缺页、由 OS 读进页缓存，热页常驻、冷页在内存吃紧时被 OS 换出。于是冷数据躺在磁盘不占内存，节点能装下远超 RAM 的数据，且换页逻辑全由内核自动处理、Milvus 一行都不用写。代价是冷页首次访问要等一次磁盘 I/O。是否对某字段启用由 EnableMmap 配置。",
                    "en": "read() copies the file wholesale into heap, capping loadable data at physical RAM. mmap maps the file into virtual address space: a page faults in only when touched, the OS reads it into page cache, hot pages stay resident, cold pages get evicted under pressure. So cold data rests on disk taking no RAM, a node holds far more than RAM, and the kernel handles all paging — Milvus writes none. The cost: a cold page's first access waits one disk I/O. Per-field toggle via EnableMmap.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说 mmap 是“用一点点延迟换巨大容量”，并把“什么数据在内存、什么在磁盘”外包给了操作系统。请结合第 18 课（binlog 落盘）和第 34 课（中央厨房）谈谈：(1) 一个内存只有 64GB 的 QueryNode，为什么能服务总量上百 GB 的段？热/冷数据各落在哪里？(2) mmap 模式下为什么常有“预热”现象（首次查冷段偏慢、之后变快）？(3) 如果你的业务要求每一次查询都低延迟、无抖动，你会倾向 mmap 还是纯内存加载？为什么？这与第 30 课“新鲜度/一致性 vs 性能”的取舍有何相通之处？",
                "en": "This lesson calls mmap 'a little latency for huge capacity', outsourcing 'what's in RAM vs on disk' to the OS. Tie it to Lesson 18 (binlog on disk) and Lesson 34 (central kitchen): (1) Why can a QueryNode with only 64GB RAM serve segments totaling hundreds of GB? Where do hot/cold data live? (2) Why is there often a 'warm-up' effect under mmap (first query on a cold segment is slow, then fast)? (3) If your workload demands low, jitter-free latency on every query, would you prefer mmap or pure in-memory loading, and why? How does this echo Lesson 30's 'freshness/consistency vs performance' trade-off?",
            },
        ],
    },
    "36-expr-and-exec.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 执行引擎把表达式分成“逻辑（expr/ITypeExpr）”和“物理（exec/Expr::Eval）”两层，主要目的是什么？",
                    "en": "Milvus's engine splits expressions into 'logical (expr/ITypeExpr)' and 'physical (exec/Expr::Eval)' layers. Why?",
                },
                "opts": [
                    {"zh": "把“算什么(语义、可校验、可优化改写)”与“怎么算得快(向量化执行)”解耦：逻辑层便于校验/优化/借用索引，物理层专注高效执行", "en": "Decouple 'what to compute (semantics, checkable, rewritable)' from 'how to compute fast (vectorized execution)': the logical layer eases validation/optimization/index use, the physical layer focuses on fast execution"},
                    {"zh": "因为 C++ 不允许一个类同时表达逻辑和执行", "en": "Because C++ forbids one class from expressing both logic and execution"},
                    {"zh": "纯粹为了多写一些类、显得复杂", "en": "Purely to write more classes and look complex"},
                    {"zh": "逻辑层负责 GPU、物理层负责 CPU", "en": "The logical layer does GPU, the physical layer does CPU"},
                ],
                "answer": 0,
                "why": {
                    "zh": "逻辑表达式(ITypeExpr)是带类型、可校验的声明式树，只说“要算什么”，本身不执行；它便于做等价改写——常量折叠/短路(AlwaysTrueExpr)、把刷掉最多行的条件前置、发现范围条件可借标量索引等。物理表达式(Expr::Eval)才是真正会跑的向量化代码。先有干净语义树、再编译成贴硬件的执行码，是成熟查询引擎的通用套路。",
                    "en": "The logical expression (ITypeExpr) is a typed, checkable declarative tree that only says 'what to compute' and doesn't run; it eases equivalence rewrites — constant folding/short-circuit (AlwaysTrueExpr), putting the most-selective condition first, spotting range conditions that can use a scalar index. The physical expression (Expr::Eval) is the vectorized code that actually runs. A clean semantic tree first, then compile to hardware-hugging code, is standard for mature engines.",
                },
            },
            {
                "q": {
                    "zh": "exec 里 Task、Driver、Operator 三者的分工，下面哪个描述最准确？",
                    "en": "In exec, what's the most accurate division among Task, Driver, and Operator?",
                },
                "opts": [
                    {"zh": "Task=一次完整执行(含状态机)；Driver=像传送带把一批批数据推过算子链(并用 Blocking/StopReason 表达暂停恢复)；Operator=各司其职的物理算子(过滤/检索/分组…)", "en": "Task = one complete execution (with a state machine); Driver = a conveyor pushing batches through the operator chain (using Blocking/StopReason for pause/resume); Operator = single-purpose physical operators (filter/search/group…)"},
                    {"zh": "三者都是同一个类的别名", "en": "All three are aliases of the same class"},
                    {"zh": "Task 负责存储、Driver 负责网络、Operator 负责日志", "en": "Task does storage, Driver does networking, Operator does logging"},
                    {"zh": "Operator 驱动 Driver，Driver 驱动 Task", "en": "Operator drives Driver, Driver drives Task"},
                ],
                "answer": 0,
                "why": {
                    "zh": "这是一套向量化版的火山(Volcano)流水线。Task(Task.h)代表一次完整执行，有状态机 TaskState(kRunning/kFinished/…)；Driver(Driver.h)像传送带，把一批批数据推过它持有的一串 Operator，并用 BlockingReason/StopReason 表达“为何暂停/何时恢复”，从而让有限线程同时驱动多条流水线；Operator(operator/*)是物理算子基类，FilterBitsNode 产 bitset、VectorSearchNode 做检索等。一次查询=按需把算子拼成一条链。",
                    "en": "It's a vectorized Volcano pipeline. Task (Task.h) is one complete execution with state machine TaskState (kRunning/kFinished/…); Driver (Driver.h) is a conveyor pushing batches through its chain of Operators, using BlockingReason/StopReason for 'why pause/when resume' so limited threads drive many pipelines; Operator (operator/*) is the physical-operator base — FilterBitsNode produces a bitset, VectorSearchNode searches, etc. One query = assemble a chain on demand.",
                },
            },
            {
                "q": {
                    "zh": "为什么说这套引擎“向量化 + 算子可组合”既快又通用？",
                    "en": "Why is this engine 'vectorized + composable operators' both fast and general?",
                },
                "opts": [
                    {"zh": "向量化=一批批算，摊薄每行固定开销、喂饱 SIMD(快)；算子各封一种能力、遵守“吃一批吐一批”契约，可被 Driver 任意拼成流水线(通用)，新增能力常常只是再加一个算子", "en": "Vectorized = compute by the batch, amortizing per-row fixed cost and feeding SIMD (fast); each operator boxes one capability under a 'consume a batch, emit a batch' contract, so the Driver assembles any pipeline (general), and adding a capability is often just one more operator"},
                    {"zh": "因为它把所有查询都编译成同一段固定代码", "en": "Because it compiles every query into one fixed piece of code"},
                    {"zh": "因为它一行一行地解释执行，最灵活", "en": "Because it interprets row by row, which is most flexible"},
                    {"zh": "因为它不需要任何算子", "en": "Because it needs no operators at all"},
                ],
                "answer": 0,
                "why": {
                    "zh": "快来自两条腿：向量化(整批流动，把函数调用/虚分派/边界检查摊到一大批行、单行成本趋零，并喂饱 SIMD)与流水线(算子串行流动、各专一事)。通用来自算子可组合：过滤/检索/分组/聚合/迭代过滤各是一个独立 Operator，查询计划要什么就拼什么；机制(Task/Driver/Operator 骨架)与策略(拼哪些算子)分离，新增能力常常只是再加一个算子、老算子一行不改——这就是“对扩展开放、对修改封闭”。",
                    "en": "Fast rests on two legs: vectorization (flow by the batch, spreading function calls/virtual dispatch/bounds checks over many rows so per-row cost nears zero, feeding SIMD) and pipelining (operators in series, each one thing). General comes from composable operators: filter/search/group/aggregate/iterative-filter are each an independent Operator the plan assembles on demand; separating mechanism (the Task/Driver/Operator skeleton) from policy (which operators) means adding a capability is often just one more operator with no edits to old ones — 'open for extension, closed for modification'.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说这条 expr/exec 流水线，正是 segcore 在第 27 课那次 cgo 调用“里面”真正干的活。请把第 35、36 课串起来，完整描述一次“带标量过滤的向量搜索”在 C++ 内核里的旅程：(1) Go 怎么经 cgo 进来；(2) FilterBitsNode 如何在 mmap 的列式分块上向量化求值、产出 bitset；(3) VectorSearchNode 如何只在通过过滤的候选上检索；(4) 结果如何回到 Go。再思考：把“逐行执行”改成“逐批向量化”，为什么常带来数量级的加速？批的大小该如何权衡（联系第 35 课的 chunk 粒度）？",
                "en": "This lesson says the expr/exec pipeline is exactly what segcore does 'inside' the Lesson 27 cgo call. Stitching Lessons 35 and 36, fully describe one 'vector search with scalar filter' through the C++ core: (1) how Go enters via cgo; (2) how FilterBitsNode evaluates vectorized over mmap'd columnar chunks to produce a bitset; (3) how VectorSearchNode searches only over survivors; (4) how results return to Go. Then consider: why does swapping 'row-at-a-time' for 'batch vectorization' often yield order-of-magnitude speedups? How should batch size be traded off (relate to Lesson 35's chunk granularity)?",
            },
        ],
    },
    "37-gpu-acceleration.html": {
        "mcq": [
            {
                "q": {
                    "zh": "为什么向量检索特别适合用 GPU 加速？",
                    "en": "Why is vector search especially well-suited to GPU acceleration?",
                },
                "opts": [
                    {"zh": "检索=对海量向量重复同一个距离公式、彼此独立，是“大批量、同质、可并行”的负载，正中 GPU 上千核(SIMT)下怀", "en": "Search = the same distance formula repeated over masses of vectors, each independent — a 'bulk, homogeneous, parallel' load that perfectly fits the GPU's thousands of cores (SIMT)"},
                    {"zh": "因为 GPU 的单核比 CPU 单核聪明得多、分支预测更强", "en": "Because a GPU core is far smarter than a CPU core, with better branch prediction"},
                    {"zh": "因为 GPU 不需要把数据从内存搬进显存", "en": "Because GPUs don't need to move data from RAM into VRAM"},
                    {"zh": "因为向量检索逻辑分支极多、串行依赖很强", "en": "Because vector search has many branches and strong serial dependencies"},
                ],
                "answer": 0,
                "why": {
                    "zh": "CPU 少而精(几十个强核、擅长复杂串行)，GPU 多而简(上千个简单核、擅长同一运算套在海量数据上，即 SIMT)。一次搜索要把查询向量与成千上万候选逐一算距离——同一公式重复无数遍、互不依赖，正是 GPU 最饿的那口饭。规模/吞吐够大时常快出数量级。注意 GPU 单核并不更聪明，且需要主机↔显存搬运，所以小批量未必划算。",
                    "en": "CPU = few but powerful (dozens of strong cores, good at complex serial work); GPU = many but simple (thousands of simple cores good at one op over massive data, i.e. SIMT). One search computes the distance from the query to thousands of candidates — the same formula repeated, independent — the GPU's hungriest meal. At scale/throughput it's often orders of magnitude faster. Note a GPU core isn't smarter, and host↔VRAM transfer means small batches may not pay off.",
                },
            },
            {
                "q": {
                    "zh": "关于 Milvus 里 GPU 索引（如 GPU_CAGRA）的“算法实现住在哪”，哪个说法正确？",
                    "en": "About where GPU indexes (e.g. GPU_CAGRA) in Milvus are actually implemented, which is correct?",
                },
                "opts": [
                    {"zh": "Milvus 只暴露类型名并在 indexparamcheck 校验参数、负责路由；真正的 GPU 算法在 Knowhere（CAGRA 源自 NVIDIA RAFT/cuVS），Milvus 不在 core 手写 CUDA", "en": "Milvus only exposes the type names, validates params in indexparamcheck, and routes; the real GPU algorithms live in Knowhere (CAGRA from NVIDIA RAFT/cuVS) — Milvus doesn't hand-write CUDA in its core"},
                    {"zh": "GPU_CAGRA 的 CUDA 核函数就写在 Milvus 的 internal/core 里", "en": "GPU_CAGRA's CUDA kernels are written right in Milvus's internal/core"},
                    {"zh": "GPU 索引完全由 Go 层实现，不涉及 C++/CUDA", "en": "GPU indexes are implemented entirely in Go, with no C++/CUDA"},
                    {"zh": "Milvus 没有任何 GPU 索引类型", "en": "Milvus has no GPU index types at all"},
                ],
                "answer": 0,
                "why": {
                    "zh": "这是本课强调的边界纪律：Milvus 暴露 GPU_CAGRA/GPU_IVF_FLAT/GPU_IVF_PQ/GPU_BRUTE_FORCE 这些类型，参数校验器在 internal/util/indexparamcheck（cagra_checker、raft_ivf_*、raft_brute_force_checker），但算法本身在 Knowhere 及其依赖的 NVIDIA RAFT/cuVS 里——CAGRA 是面向 GPU 的图索引（可类比 GPU 版 HNSW）。Milvus 负责暴露、校验、调度、路由，把写 CUDA 的专业活交给专业的人。别把 CUDA 的功劳记到 milvus core 头上。",
                    "en": "This is the lesson's boundary discipline: Milvus exposes GPU_CAGRA/GPU_IVF_FLAT/GPU_IVF_PQ/GPU_BRUTE_FORCE, with param checkers in internal/util/indexparamcheck (cagra_checker, raft_ivf_*, raft_brute_force_checker), but the algorithms live in Knowhere and its NVIDIA RAFT/cuVS dependency — CAGRA is a GPU-oriented graph index (a GPU 'HNSW'). Milvus exposes, validates, schedules, routes, leaving the CUDA to the experts. Don't credit CUDA to the Milvus core.",
                },
            },
            {
                "q": {
                    "zh": "下面关于 Milvus GPU 支持的“工程现实”，哪个说法正确？",
                    "en": "Which statement about the 'engineering reality' of Milvus GPU support is correct?",
                },
                "opts": [
                    {"zh": "GPU 是编译期的独立构建(make milvus-gpu / MILVUS_GPU_VERSION)，要专门编译并部署到 GPU 机器；运行时用显存池(gpu.initMemSize/maxMemSize)复用稀缺显存", "en": "GPU is a compile-time separate build (make milvus-gpu / MILVUS_GPU_VERSION), specially built and deployed on GPU machines; at runtime a VRAM pool (gpu.initMemSize/maxMemSize) reuses scarce VRAM"},
                    {"zh": "任何 CPU 版 Milvus 装好后，改一个配置就能在运行时切到 GPU", "en": "Any CPU Milvus can switch to GPU at runtime by changing one config after install"},
                    {"zh": "GPU 版会让 Proxy、协调器、WAL 等也全部跑在显卡上", "en": "The GPU build also runs Proxy, coordinators, WAL, etc. all on the GPU"},
                    {"zh": "GPU 版不需要任何额外的 CUDA/RAFT 依赖", "en": "The GPU build needs no extra CUDA/RAFT dependencies"},
                ],
                "answer": 0,
                "why": {
                    "zh": "core_build.sh 里 GPU_VERSION 默认 OFF，靠 -DMILVUS_GPU_VERSION=ON 打开；Makefile 有独立的 make milvus-gpu/build-cpp-gpu。因为要链接庞大的 CUDA/RAFT 工具链，Milvus 把 GPU 做成独立构建变体：要的人专门编译部署，不要的人零负担——不是运行时按钮。GPU 只接管索引的构建与检索这段最重的计算，其余(Proxy/协调器/WAL/段管理)仍在 CPU。显存稀缺，故用显存池预占复用、避免频繁 alloc/free。",
                    "en": "In core_build.sh GPU_VERSION defaults OFF, enabled by -DMILVUS_GPU_VERSION=ON; the Makefile has separate make milvus-gpu/build-cpp-gpu. Because it links the heavy CUDA/RAFT toolchain, Milvus makes GPU a separate build variant: build/deploy it if you want it, zero burden otherwise — not a runtime button. The GPU only takes over the heavy index build/search; the rest (Proxy/coordinators/WAL/segment mgmt) stays on CPU. VRAM is scarce, so a pool reserves and reuses it, avoiding frequent alloc/free.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说“硬件能力会反过来改变算法选择”——CPU 上不敢用的暴力全算，在 GPU 上(GPU_BRUTE_FORCE)反而简单、召回 100%、还能当精度基准。请结合第 5 课(ANN 索引)与第 29 课(批量更划算)谈谈：(1) 为什么 CPU 时代“必须用近似索引”的直觉，到 GPU 时代未必成立？(2) 既然 GPU 常快出数量级，为什么 Milvus 还把它做成可选的独立构建、而非默认开启？请从主机↔显存搬运、显存上限、成本/运维、以及“小批量未必划算”几个角度，谈谈什么样的业务才真正值得上 GPU。",
                "en": "This lesson says 'hardware reshapes algorithm choice' — brute force, unthinkable on CPU, is simple on GPU (GPU_BRUTE_FORCE), with 100% recall and useful as a baseline. Tie to Lesson 5 (ANN indexes) and Lesson 29 (batching pays): (1) Why might the CPU-era intuition 'you must use an approximate index' not hold on the GPU? (2) Given the GPU is often orders of magnitude faster, why does Milvus still make it an optional separate build rather than on by default? Considering host↔VRAM transfer, VRAM ceilings, cost/ops, and 'small batches may not pay', discuss what kind of workload truly justifies going GPU.",
            },
        ],
    },
    "38-api-and-sdks.html": {
        "mcq": [
            {
                "q": {
                    "zh": "为什么 Milvus 把所有对外 API 集中定义在一份 milvus-proto（MilvusService）里，而不是各 SDK 各自约定？",
                    "en": "Why does Milvus define all external APIs centrally in one milvus-proto (MilvusService) rather than each SDK agreeing on its own?",
                },
                "opts": [
                    {"zh": "以 proto 为唯一事实来源：服务端与各语言 SDK 都从同一份 proto 生成/绑定，对请求与响应的理解完全一致，跨语言行为统一、演进可控", "en": "The proto as single source of truth: server and all SDKs generate/bind from the same proto, sharing an identical understanding of requests/responses — consistent cross-language behavior and controlled evolution"},
                    {"zh": "因为 gRPC 不允许多个客户端", "en": "Because gRPC forbids multiple clients"},
                    {"zh": "因为每种语言的功能本来就该不一样", "en": "Because each language's features should differ anyway"},
                    {"zh": "纯粹是为了多生成一些代码", "en": "Purely to generate more code"},
                ],
                "answer": 0,
                "why": {
                    "zh": "milvus-proto 用 Protocol Buffers 描述 MilvusService 及各接口的请求/响应消息(SearchRequest/SearchResults…)，编译生成各语言代码(Go 侧为 milvuspb)。服务端与所有 SDK 都以同一份 proto 为准，于是对“一次搜索长什么样、返回哪些字段”理解一致，不会鸡同鸭讲；加字段先改 proto 再各端重生成、向后兼容。契约独立成仓，多语言生态才能围着同一中心转。",
                    "en": "milvus-proto uses Protocol Buffers to describe MilvusService and each endpoint's request/response messages (SearchRequest/SearchResults…), compiled into per-language code (milvuspb in Go). Server and all SDKs follow the same proto, so they agree on 'what a search looks like, what fields return' — no mismatch; adding a field means editing the proto then regenerating, backward-compatibly. Pulling the contract into its own repo lets a multi-language ecosystem orbit one center.",
                },
            },
            {
                "q": {
                    "zh": "Milvus 里 internal/distributed/proxy 的 gRPC Server 与 internal/proxy/impl.go 的 Proxy 是什么关系？",
                    "en": "What's the relationship between the gRPC Server in internal/distributed/proxy and the Proxy in internal/proxy/impl.go?",
                },
                "opts": [
                    {"zh": "前者是“传输层”(收网络请求、鉴权、限流，方法体常只一行转交)，后者是“逻辑层”(真正的校验、入队、扇出、归并)；传输与逻辑解耦", "en": "The former is the 'transport layer' (receive, auth, rate-limit; methods often just one line forwarding), the latter the 'logic layer' (real validation, enqueue, fan-out, merge); transport decoupled from logic"},
                    {"zh": "两者是同一个类的两个名字", "en": "They are two names for the same class"},
                    {"zh": "Proxy(impl.go)负责网络收发，Server(distributed)负责业务逻辑", "en": "Proxy(impl.go) does networking, Server(distributed) does business logic"},
                    {"zh": "Server 负责 C++ 内核，Proxy 负责 GPU", "en": "Server handles the C++ core, Proxy handles the GPU"},
                ],
                "answer": 0,
                "why": {
                    "zh": "service.go 的 Server 把自己 RegisterMilvusServiceServer 成 MilvusService 实现，但它的 Search 几乎只有一行：return s.proxy.Search(ctx, request)。真正的业务逻辑在 impl.go 的 Proxy.Search(校验、入 dqQueue、扇出 QueryNode、归并)。这样切分是因为“传输”(gRPC/TLS/鉴权/限流/REST)与“逻辑”(搜索语义)会各自变化，解耦后可各自演进与测试，也让同一逻辑层被 gRPC 和 REST 两道门复用。",
                    "en": "service.go's Server RegisterMilvusServiceServer's itself as the MilvusService impl, but its Search is essentially one line: return s.proxy.Search(ctx, request). The real logic is impl.go's Proxy.Search (validate, enqueue dqQueue, fan out to QueryNodes, merge). The split exists because 'transport' (gRPC/TLS/auth/rate-limit/REST) and 'logic' (search semantics) change independently; decoupling lets each evolve and be tested, and lets one logic layer be reused by both the gRPC and REST doors.",
                },
            },
            {
                "q": {
                    "zh": "关于 gRPC 与 REST 两种入口，下面哪个说法正确？",
                    "en": "About the gRPC and REST entrances, which statement is correct?",
                },
                "opts": [
                    {"zh": "两道门通向同一个 Proxy、语义一致，仅“包装”不同：gRPC 二进制高效(生产首选)，REST(gin，/v2/vectordb)零门槛易调试；REST 处理器本质是把 JSON 转成同样的 proto 调用同一套 Proxy", "en": "Both doors lead to the same Proxy with identical semantics, differing only in 'wrapping': gRPC binary-efficient (production), REST (gin, /v2/vectordb) zero-friction; the REST handler essentially turns JSON into the same proto calls on the same Proxy"},
                    {"zh": "REST 和 gRPC 走完全独立的两套业务逻辑，结果可能不同", "en": "REST and gRPC run two fully separate business logics and may return different results"},
                    {"zh": "REST 比 gRPC 总是更快、更省带宽", "en": "REST is always faster and more bandwidth-efficient than gRPC"},
                    {"zh": "只有 gRPC 能用，REST 仅供文档展示", "en": "Only gRPC works; REST is just for documentation"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Proxy 在 service.go 里同时起 gRPC 和一个 gin HTTP 服务(registerHTTPServer，处理器在 httpserver/handler_v2.go，路径 /v2/vectordb)。两道门最终都汇到同一个 Proxy 逻辑层——REST 处理器把 JSON 转成对应 proto 请求、调用同一套 Proxy 方法，故语义完全一致。区别只在包装：gRPC(HTTP2 二进制、长连接、强类型)适合生产；REST(JSON、curl 即用)适合上手与跨语言/无 gRPC 环境。",
                    "en": "The Proxy starts both gRPC and a gin HTTP server in service.go (registerHTTPServer; handlers in httpserver/handler_v2.go, path /v2/vectordb). Both doors converge on the same Proxy logic — the REST handler turns JSON into the matching proto request and calls the same Proxy methods, so semantics are identical. The difference is only wrapping: gRPC (HTTP2 binary, long connections, strongly typed) for production; REST (JSON, curl-ready) for getting started and gRPC-less/cross-language environments.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说“一份契约 + 一个门面 + 两种包装”。请结合第 3 课(一次请求的旅程)与第 10 课(Proxy)谈谈：(1) 你在 pymilvus 里调用 client.search(...)，到返回结果，中间经过了哪些层(SDK→proto→哪道门→传输层 Server→逻辑层 Proxy→集群)？(2) 为什么把“传输层(distributed/proxy)”和“逻辑层(proxy/impl.go)”分开，对加新协议入口、做鉴权限流、写单测各有什么好处？(3) 假如你怀疑一个搜索结果不对，如何利用“gRPC 与 REST 落到同一个 Proxy”这一点来快速定位是服务端还是 SDK 的问题？",
                "en": "This lesson says 'one contract + one facade + two wrappings'. Tie to Lesson 3 (a request's journey) and Lesson 10 (Proxy): (1) From calling client.search(...) in pymilvus to getting results, which layers are crossed (SDK→proto→which door→transport Server→logic Proxy→cluster)? (2) Why does splitting 'transport (distributed/proxy)' from 'logic (proxy/impl.go)' help with adding new protocol entrances, doing auth/rate-limiting, and writing unit tests? (3) If you suspect a search result is wrong, how can you use 'gRPC and REST land on the same Proxy' to quickly tell whether it's a server-side or SDK-side problem?",
            },
        ],
    },
    "39-observability.html": {
        "mcq": [
            {
                "q": {
                    "zh": "可观测性的“三大支柱”各回答什么问题、如何配合？",
                    "en": "What does each of the 'three pillars' of observability answer, and how do they work together?",
                },
                "opts": [
                    {"zh": "日志=发生了什么(细节)、指标=整体趋势(告警)、追踪=一个请求走过哪些环节；配合：指标发现异常→追踪定位环节→日志还原细节", "en": "Logs = what happened (detail), metrics = overall trend (alert), traces = which stages a request crossed; together: metrics detect → traces locate → logs reconstruct"},
                    {"zh": "三者是同一种数据的三个名字，留一个即可", "en": "All three are names for the same data; keep just one"},
                    {"zh": "日志负责告警、指标负责存细节、追踪负责画仪表盘", "en": "Logs alert, metrics store details, traces draw dashboards"},
                    {"zh": "三者都只在单机内有用，分布式下无意义", "en": "All three only matter on a single machine, useless in distributed mode"},
                ],
                "answer": 0,
                "why": {
                    "zh": "三者各有盲区：只看指标知道“延迟涨了”却不知哪个请求/哪一步；只看日志，海量分散难以把同一请求的条目连起来；只看追踪知道卡在某段却缺细节。所以三管齐下：指标用来发现(告警)、追踪用来定位(哪个请求/哪一跳)、日志用来还原(那一段的细节)。Milvus 分别用 pkg/mlog、pkg/metrics(Prometheus)、pkg/tracer(OpenTelemetry)。",
                    "en": "Each has blind spots: metrics show 'latency rose' but not which request/step; logs are massive and scattered, hard to connect one request's entries; traces show 'stuck in a segment' but lack detail. So three-pronged: metrics detect (alert), traces locate (which request/hop), logs reconstruct (that segment's detail). Milvus uses pkg/mlog, pkg/metrics (Prometheus), pkg/tracer (OpenTelemetry) respectively.",
                },
            },
            {
                "q": {
                    "zh": "Milvus 规定日志必须用 pkg/mlog 且每条都带 ctx，最关键的好处是什么？",
                    "en": "Milvus mandates logging via pkg/mlog with ctx on every call. What's the key benefit?",
                },
                "opts": [
                    {"zh": "ctx 能携带可传播的结构化字段：经 WithFields+OptPropagated+gRPC 拦截器，请求的“身份”随 RPC 跨节点流动，一个 ID 就能把全集群相关日志归拢", "en": "ctx can carry propagatable structured fields: via WithFields+OptPropagated+gRPC interceptors, the request's 'identity' flows with RPCs across nodes, so one ID gathers related logs cluster-wide"},
                    {"zh": "ctx 能让日志自动变成中文", "en": "ctx automatically translates logs into Chinese"},
                    {"zh": "带 ctx 纯粹是为了让函数签名更长", "en": "Carrying ctx is purely to make signatures longer"},
                    {"zh": "mlog 会把日志直接写进向量索引", "en": "mlog writes logs straight into the vector index"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Milvus 是分布式的：一个请求的“故事”被拆散在多个进程/机器上书写。mlog 强制带 ctx，使日志能携带结构化字段(mlog.String/Int64)；用 WithFields 挂到 ctx、加 OptPropagated 并配 gRPC 拦截器(UnaryServer/ClientInterceptor)，这些字段就随 RPC 传到下游节点。于是 Proxy 给请求打的标记会出现在它触发的 QueryNode/DataNode 日志里，事后用一个 ID 就能把散落全集群的相关日志一网打尽——这是分布式排错的生死线。",
                    "en": "Milvus is distributed: one request's 'story' is written across many processes/machines. mlog mandates ctx so logs carry structured fields (mlog.String/Int64); attaching them via WithFields with OptPropagated plus gRPC interceptors (Unary Server/Client) propagates them downstream. So a marker stamped at the Proxy reappears in the QueryNode/DataNode logs it triggers, and one ID later nets all related logs cluster-wide — a lifeline for distributed debugging.",
                },
            },
            {
                "q": {
                    "zh": "本课说日志(mlog 可传播字段)与链路追踪(OpenTelemetry)“用的是同一招”。这一招是什么？",
                    "en": "This lesson says logs (mlog propagatable fields) and tracing (OpenTelemetry) 'use the same move'. What is it?",
                },
                "opts": [
                    {"zh": "把请求的“身份/上下文”塞进 ctx，再由 gRPC 拦截器随 RPC 带到下游节点，从而把散落多节点的碎片围绕“同一个请求”重新聚拢", "en": "Tuck the request's 'identity/context' into ctx and let gRPC interceptors carry it with the RPC to downstream nodes, re-gathering fragments scattered across nodes around 'the same request'"},
                    {"zh": "把所有数据压缩后写到一个文件里", "en": "Compress everything into one file"},
                    {"zh": "让每个节点用本地时钟各自编号", "en": "Have each node number things by its local clock"},
                    {"zh": "把日志和 span 都发给同一个 GPU 处理", "en": "Send both logs and spans to the same GPU"},
                ],
                "answer": 0,
                "why": {
                    "zh": "otelgrpc 拦截器在一次 RPC 里把“trace context”(本次追踪的唯一 ID 与当前 span)塞进 RPC 元数据带给下游，下游把自己这段作为子 span 挂到同一条 trace；mlog 的 OptPropagated 字段同理随 RPC 传播。两者本质都是“把标识塞进 ctx、再随 gRPC 传播”，这正是分布式可观测性的核心心法，也是“每条日志必带 ctx”铁律的深意——ctx 是串起整个分布式可观测性的那根线。",
                    "en": "The otelgrpc interceptor tucks the 'trace context' (the trace's unique ID and current span) into RPC metadata for downstream, which attaches its work as a child span on the same trace; mlog's OptPropagated fields propagate over RPC the same way. Both are 'tuck an identifier into ctx, propagate with gRPC' — the core method of distributed observability and the deeper point of 'every log carries ctx': ctx is the thread stitching it all together.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课用“医院监护病人”类比三大支柱，并强调它们靠“给请求一个能跨节点传播的身份”协作。请：(1) 用自己的话说清，当线上“搜索 P99 突然变慢”，你会如何依次用指标、追踪、日志把根因定位出来；(2) 解释为什么在分布式系统里，光有日志或光有指标都不够；(3) 结合第 38 课“每条日志必带 ctx”的铁律，谈谈“把身份塞进 ctx 再随 gRPC 传播”这一招，为什么同时支撑了日志聚合与链路追踪。",
                "en": "This lesson uses 'a hospital monitoring a patient' for the three pillars and stresses they cooperate by 'giving a request an identity that propagates across nodes'. Please: (1) in your own words, describe how you'd use metrics, then traces, then logs in turn to locate the root cause when 'search P99 suddenly slows' in production; (2) explain why, in a distributed system, logs alone or metrics alone are insufficient; (3) tying to Lesson 38's 'every log carries ctx' rule, discuss why 'tuck identity into ctx, propagate over gRPC' underpins both log aggregation and tracing.",
            },
        ],
    },
    "40-configuration.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 的配置为什么分成 paramtable 和 config 两层？",
                    "en": "Why is Milvus's config split into two layers, paramtable and config?",
                },
                "opts": [
                    {"zh": "分离“怎么用配置”(paramtable：类型安全/有文档/分组的读取面)与“配置从哪来”(config：多来源/优先级/热更新的取值面)，使配置行为可预测、可解释", "en": "Separate 'how to use config' (paramtable: a type-safe/documented/grouped read surface) from 'where config comes from' (config: a multi-source/priority/hot-reload value surface), making config behavior predictable and explainable"},
                    {"zh": "因为 Go 不允许在一个包里读文件", "en": "Because Go forbids reading files in one package"},
                    {"zh": "纯粹为了多写一层、显得复杂", "en": "Purely to add a layer and look complex"},
                    {"zh": "paramtable 管 CPU 配置，config 管 GPU 配置", "en": "paramtable handles CPU config, config handles GPU config"},
                ],
                "answer": 0,
                "why": {
                    "zh": "上层 paramtable 提供类型安全、有文档、可分组的“读取面”；下层 config 提供多来源、按优先级合并、可热更新的“取值面”。分离后，排查“某配置为什么是这个值/为什么改了不生效”时路径清晰：先在 paramtable 找 ParamItem 的 Key 与默认，再去 config 看它在 yaml/env/etcd 是否被更高优先级覆盖。一个旋钮当前值唯一、来源唯一，确定性正是大型系统配置管理的根本诉求。",
                    "en": "The upper paramtable offers a type-safe, documented, grouped 'read surface'; the lower config offers a multi-source, priority-merged, hot-reloadable 'value surface'. Decoupled, debugging 'why is this value / why didn't my change take effect' is clear: find the ParamItem's Key and default in paramtable, then check config for higher-priority overrides in yaml/env/etcd. A knob has one current value from one source — the determinism large-system config management fundamentally needs.",
                },
            },
            {
                "q": {
                    "zh": "代码读配置时写的是 Params.XxxCfg.Yyy.GetAsInt() 而不是自己解析字符串，好处是什么？",
                    "en": "Code reads config via Params.XxxCfg.Yyy.GetAsInt() instead of parsing strings itself. The benefit?",
                },
                "opts": [
                    {"zh": "把“字符串→类型”的转换收口到 ParamItem 内部，避免满地 strconv 与重复 bug，杜绝“忘转换/转错类型”；ParamItem 还登记 Key/Default/Doc 等元信息", "en": "It funnels 'string→type' conversion inside ParamItem, avoiding scattered strconv and duplicated bugs and eliminating 'forgot/wrong conversion'; ParamItem also registers metadata like Key/Default/Doc"},
                    {"zh": "GetAsInt 会自动把配置上传到 etcd", "en": "GetAsInt automatically uploads config to etcd"},
                    {"zh": "这样读出来的值总是 0", "en": "Values read this way are always 0"},
                    {"zh": "它能绕过优先级、直接读文件", "en": "It bypasses priority and reads the file directly"},
                ],
                "answer": 0,
                "why": {
                    "zh": "每个配置项是一个 ParamItem(param_item.go)，提供 GetValue/GetAsBool/GetAsInt/GetAsInt64 等类型化读取。消费方直接拿到类型正确的值，转换逻辑只在 ParamItem 内部一处，既无满地 strconv，也让“忘转换、转错类型”无处发生。ParamItem 还登记 Key、DefaultValue、Doc、FallbackKeys、PanicIfEmpty 等：默认值使开箱即用，Doc 可自动生成文档，FallbackKeys 兼容旧键名，PanicIfEmpty 在缺关键配置时启动即明确报错。",
                    "en": "Each config item is a ParamItem (param_item.go) offering typed reads: GetValue/GetAsBool/GetAsInt/GetAsInt64. Consumers get correctly-typed values; conversion lives in one place inside ParamItem — no scattered strconv, no 'forgot/wrong conversion'. ParamItem also registers Key, DefaultValue, Doc, FallbackKeys, PanicIfEmpty: defaults give out-of-the-box use, Doc auto-generates docs, FallbackKeys keep old key names working, PanicIfEmpty fails fast at startup when a critical config is missing.",
                },
            },
            {
                "q": {
                    "zh": "关于配置的多数据源、优先级与热更新，下面哪个说法正确？",
                    "en": "About config's multiple sources, priority, and hot reload, which is correct?",
                },
                "opts": [
                    {"zh": "来源 file(milvus.yaml) < env < etcd，由 config.Manager 按优先级合并(值越小越优先，越动态越贴身越优先)；可变项经 etcd+Dispatcher 回调热更新，Immutable/Forbidden 项锁死拒改", "en": "Sources file(milvus.yaml) < env < etcd, merged by config.Manager by priority (lesser value wins; more dynamic/personal wins); mutable items hot-reload via etcd+Dispatcher callbacks, Immutable/Forbidden items are locked"},
                    {"zh": "文件配置永远压过 etcd，因为文件更“正式”", "en": "File config always beats etcd because files are more 'official'"},
                    {"zh": "所有配置都能在运行时随意热更新，没有例外", "en": "Every config can be hot-reloaded freely at runtime, no exceptions"},
                    {"zh": "优先级是值越大越优先", "en": "Priority means a larger value wins"},
                ],
                "answer": 0,
                "why": {
                    "zh": "config 包定义 FileSource(milvus.yaml，默认/清单)、EnvSource(环境变量，临时覆盖)、EtcdSource(运行时下发)。source.go 里 HighPriority=1<NormalPriority=11<LowPriority=21，注明“值越小优先级越高”，即越动态越贴身的来源越优先(etcd>env>file)。config.Manager 合并各源；可变项写入 etcd 后经 Dispatcher 回调刷新 ParamItem 的 lastValue，立即生效不重启。但端口等不该运行时变的项用 Immutable/Forbidden 锁死，拒绝热更新以保安全。",
                    "en": "The config package defines FileSource (milvus.yaml, defaults/catalog), EnvSource (env vars, temporary override), EtcdSource (runtime distribution). In source.go HighPriority=1<NormalPriority=11<LowPriority=21, noting 'lesser value = higher priority' — the more dynamic/personal source wins (etcd>env>file). config.Manager merges sources; mutable items written to etcd refresh a ParamItem's lastValue via Dispatcher callbacks, effective without restart. But items like ports that shouldn't change at runtime are locked via Immutable/Forbidden, refusing hot reload for safety.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课把配置面板比作“印好标签、分好优先级、部分可热拧”的控制台。请：(1) 描述一个配置值从 milvus.yaml/环境变量/etcd 到代码 GetAsInt() 的完整旅程，并说明三者冲突时谁生效、为什么这样设计合理；(2) 你在生产改了 milvus.yaml 里的某个限流值却发现“不生效”，结合优先级链你会怎么排查？(3) 为什么 Milvus 不把所有配置都做成可热更新，而要用 Immutable/Forbidden 锁住一部分？这与第 37 课“GPU 默认 OFF”体现了怎样共同的工程价值观？",
                "en": "This lesson likens config to a control panel that's 'labeled, prioritized, partly hot-turnable'. Please: (1) describe a config value's full journey from milvus.yaml/env/etcd to the code's GetAsInt(), and say who wins on conflict and why that design is reasonable; (2) you changed a rate-limit in milvus.yaml in production but it 'doesn't take effect' — using the priority chain, how would you debug? (3) Why doesn't Milvus make every config hot-reloadable, instead locking some via Immutable/Forbidden? What shared engineering value does this share with Lesson 37's 'GPU off by default'?",
            },
        ],
    },
    "41-deployment.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 的部署方式从内嵌单机到 k8s Operator 排成一道阶梯，这样设计的意义是什么？",
                    "en": "Milvus's deployment options form a ladder from embedded single-node to the k8s Operator. What's the point of this design?",
                },
                "opts": [
                    {"zh": "上手零负担(standalone_embed 一条命令零依赖)、认真用有生产级方案(Helm/Operator)，可随需求逐级往上，不被复杂度劝退", "en": "Zero burden to start (standalone_embed: one command, zero deps) and production-grade when serious (Helm/Operator); climb rung by rung as needs grow, not scared off by complexity"},
                    {"zh": "因为 Milvus 只能在 k8s 上运行", "en": "Because Milvus only runs on k8s"},
                    {"zh": "几种方式功能完全不同、互不兼容", "en": "The options have totally different, incompatible features"},
                    {"zh": "内嵌单机用于生产，Operator 用于开发", "en": "Embedded single-node is for production, the Operator for development"},
                ],
                "answer": 0,
                "why": {
                    "zh": "阶梯由简到繁：内嵌单机(standalone_embed.sh，嵌入式 etcd+本地 rocksmq+本地盘，几乎零外部依赖)适合学习/开发；docker-compose 把 etcd/MinIO/Pulsar 拉成独立容器，在一台机器体验真实分工，适合集成测试；k8s 的 Helm Chart 模板化部署、Milvus Operator 声明式管理全生命周期(扩缩容/自愈/滚动升级)，是生产首选。你按需选择那一级，而非被迫一上来就扛全部复杂度。",
                    "en": "The ladder runs simple to elaborate: embedded single-node (standalone_embed.sh — embedded etcd + local rocksmq + local disk, near-zero external deps) for learning/dev; docker-compose brings etcd/MinIO/Pulsar up as separate containers for real division of labor on one machine, for integration tests; k8s Helm Chart templates the deploy and the Milvus Operator declaratively manages the full lifecycle (scaling/self-healing/rolling upgrade) for production. You pick the rung you need rather than shouldering all complexity up front.",
                },
            },
            {
                "q": {
                    "zh": "选择集群模式(而非单机)最核心的回报是什么？",
                    "en": "What's the core payoff of choosing cluster mode (over standalone)?",
                },
                "opts": [
                    {"zh": "兑现存算分离红利——可按需独立伸缩：读多就扩 QueryNode、写多就扩 streaming/DataNode、存储在对象存储独立扩，把算力精准投到瓶颈处", "en": "It cashes the compute/storage-separation dividend — scale independently on demand: add QueryNodes for reads, streaming/DataNodes for writes, storage scales independently in the object store — pouring compute precisely at the bottleneck"},
                    {"zh": "集群模式延迟一定比单机更低", "en": "Cluster mode always has lower latency than standalone"},
                    {"zh": "集群模式不需要任何外部依赖", "en": "Cluster mode needs no external dependencies"},
                    {"zh": "集群模式让所有组件挤进一个进程", "en": "Cluster mode crams all components into one process"},
                ],
                "answer": 0,
                "why": {
                    "zh": "集群模式兑现了第 3 部分“存算分离、组件解耦”的红利：哪一环是瓶颈就单独给哪一环加机器。读多写少就多加 QueryNode；批量灌数据就临时加强写入/流式与建索引；存储不够就扩对象存储(无状态、不牵动计算)。单机所有角色挤在一个进程，要扩只能整体复制、既浪费又不灵活。所以选集群的真正理由往往不是“装更多数据”，而是“把钱花在刀刃上”。但代价是要运维外部依赖与 k8s，复杂度更高——按真实需求选型。",
                    "en": "Cluster mode cashes Part 3's 'compute/storage separation, decoupled components' dividend: add machines to whichever link is the bottleneck. Read-heavy → more QueryNodes; bulk loading → temporarily beef up write/streaming and index building; out of storage → scale the object store (stateless, doesn't disturb compute). Standalone crowds all roles in one process, so scaling means replicating the whole — wasteful and inflexible. The real reason for cluster is usually not 'hold more data' but 'spend where it counts'. The cost is operating external deps and k8s — choose by real need.",
                },
            },
            {
                "q": {
                    "zh": "关于 Milvus 的消息队列(MQ)选择，下面哪个说法正确？",
                    "en": "About Milvus's message queue (MQ) choice, which is correct?",
                },
                "opts": [
                    {"zh": "MQ 就是 WAL 的后端：rocksmq 仅单机(默认)、Pulsar 集群默认、Kafka 集群可选、Woodpecker 新部署推荐；由 mq.type 选，地基的吞吐/可靠性决定写入能力", "en": "The MQ is the WAL backend: rocksmq standalone-only (default), Pulsar cluster default, Kafka cluster option, Woodpecker recommended for new; chosen via mq.type — the backend's throughput/reliability bounds write capacity"},
                    {"zh": "MQ 只是个可有可无的缓存，删掉不影响写入", "en": "The MQ is just an optional cache; removing it doesn't affect writes"},
                    {"zh": "rocksmq 在集群模式下是默认且推荐", "en": "rocksmq is the default and recommended in cluster mode"},
                    {"zh": "四种 MQ 完全等价，随便选都一样", "en": "All four MQs are equivalent; pick any, no difference"},
                ],
                "answer": 0,
                "why": {
                    "zh": "回忆第 16/31 课，Milvus 写入先落 WAL，而这条日志的后端就是 MQ。mq.type 支持 rocksmq(基于 RocksDB、本地嵌入，仅单机、单机默认)、Pulsar(集群默认；rocksmq 在集群不支持，因其本地无法多节点共享)、Kafka(集群可选)、Woodpecker(Milvus 自研、新部署推荐，主打更好性能/更简运维/更低成本)。把日志后端做成可插拔，体现“对接口编程、实现可替换”的思路——选 MQ 实质是为整条写入路径选地基。",
                    "en": "Recall Lessons 16/31: Milvus writes by logging to the WAL first, and that log's backend is the MQ. mq.type supports rocksmq (RocksDB-based, local embedded — standalone only, standalone default), Pulsar (cluster default; rocksmq isn't supported in cluster, being local and unshareable), Kafka (cluster option), Woodpecker (Milvus's own, recommended for new, for better performance/simpler ops/lower cost). Making the log backend pluggable reflects 'program to an interface, swap the implementation' — choosing the MQ is choosing the foundation for the whole write path.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课把部署比作“选住处”，并说集群模式兑现了存算分离的红利。请：(1) 给三个不同场景(本地学习 / 小团队稳定流量的生产 / 读流量暴涨的大规模检索服务)各推荐一种部署方式并说明理由；(2) 解释为什么“上集群”不总是更好——它带来弹性，但代价是什么？(3) 结合第 16/31 课，说明 MQ 为什么是“关键部署决策”：把日志后端做成可插拔(rocksmq/Pulsar/Woodpecker)，体现了本书反复出现的哪种设计哲学(可联系第 22 课 Knowhere、第 39 课 Prometheus/OTel)？",
                "en": "This lesson likens deployment to 'choosing a home' and says cluster mode cashes the compute/storage-separation dividend. Please: (1) recommend a deployment method for each of three scenarios (local learning / a small team's steady-traffic production / a large-scale search service with surging read traffic) and justify each; (2) explain why 'going cluster' isn't always better — it brings elasticity, but at what cost? (3) Tying to Lessons 16/31, explain why the MQ is a 'key deployment decision': making the log backend pluggable (rocksmq/Pulsar/Woodpecker) reflects which recurring design philosophy of this guide (relate to Lesson 22 Knowhere, Lesson 39 Prometheus/OTel)?",
            },
        ],
    },
    "42-build-and-run.html": {
        "mcq": [
            {
                "q": {
                    "zh": "为什么编译 Milvus 不能只敲 go build，而要用 make milvus？",
                    "en": "Why can't you build Milvus with just go build — why use make milvus?",
                },
                "opts": [
                    {"zh": "Milvus 是 Go+C++ 经 cgo 黏合，必须先 build-cpp(cmake/conan 编 C++ 内核)产出库，再 build-go(CGO_ENABLED=1)链接它们；go build 找不到还没编出的 C++ 库会失败", "en": "Milvus is Go+C++ glued by cgo: you must build-cpp first (cmake/conan compile the C++ core into libs), then build-go (CGO_ENABLED=1) links them; a lone go build can't find the not-yet-built C++ libs and fails"},
                    {"zh": "因为 go build 在 Linux 上不可用", "en": "Because go build is unavailable on Linux"},
                    {"zh": "因为 Milvus 是纯 C++ 项目，没有 Go", "en": "Because Milvus is pure C++ with no Go"},
                    {"zh": "make milvus 只是 go build 的别名，没区别", "en": "make milvus is just an alias of go build, no difference"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Milvus 的计算内核是 C++，Go 部分靠 cgo 链接这些 C++ 库才能跑。Makefile 里 milvus: build-cpp print-build-info build-go——次序写死、先 C++ 后 Go。build-cpp 用 cmake/conan 编 internal/core(还依赖 generated-proto)产出 C++ 库；build-go 开 CGO_ENABLED=1，用 CGO_LDFLAGS/CFLAGS 链接这些库编出 cmd/main.go。单独 go build 时这些库还不存在，必然失败。所以要装两套工具链(Go + C++ 的 cmake/conan)。",
                    "en": "Milvus's compute core is C++, and the Go part must cgo-link those C++ libs to run. The Makefile defines milvus: build-cpp print-build-info build-go — order hard-wired, C++ first, Go second. build-cpp uses cmake/conan to compile internal/core (also needing generated-proto) into C++ libs; build-go runs with CGO_ENABLED=1, linking them via CGO_LDFLAGS/CFLAGS to compile cmd/main.go. A lone go build fails because those libs don't exist yet. Hence two toolchains (Go + C++'s cmake/conan).",
                },
            },
            {
                "q": {
                    "zh": "make milvus 编出的产物是什么形态？",
                    "en": "What form does make milvus produce?",
                },
                "opts": [
                    {"zh": "一个 milvus 二进制(cmd/main.go)，靠启动参数决定扮演 Proxy/协调器/各节点等任意角色；构建简单、版本一致、部署灵活", "en": "One milvus binary (cmd/main.go) that plays any role — Proxy/coordinator/nodes — by launch arguments; simple builds, version consistency, flexible deployment"},
                    {"zh": "十几个二进制，每个角色一个，需各自同步版本", "en": "A dozen binaries, one per role, each needing version sync"},
                    {"zh": "一个只能当 Proxy 用的二进制", "en": "A binary that can only act as a Proxy"},
                    {"zh": "一组 Python 脚本", "en": "A set of Python scripts"},
                ],
                "answer": 0,
                "why": {
                    "zh": "尽管 Milvus 有 Proxy、各协调器、各类节点十几种角色，编出来却只有一个 milvus 二进制。秘密在入口 cmd/main.go：同一程序靠启动参数决定本次扮演哪个角色(proxy/querynode…)。好处：一次编译到处部署(构建简单)、所有角色同源同版本(杜绝错配)、单机一个进程拉起所有角色而集群同一二进制在不同机器以不同角色启动(部署灵活)。这就是“单二进制+角色分发”。",
                    "en": "Though Milvus has a dozen roles (Proxy, coordinators, nodes), it compiles to one milvus binary. The secret is cmd/main.go: the same program picks its role this run by launch args (proxy/querynode…). Benefits: compile once deploy everywhere (simple builds), all roles same-source/same-version (no mismatch), one process brings up all roles in standalone while the same binary launches in different roles across machines in cluster (flexible). That's 'one binary + role dispatch'.",
                },
            },
            {
                "q": {
                    "zh": "下面关于 Milvus 构建/运行命令的说法，哪个正确？",
                    "en": "Which statement about Milvus build/run commands is correct?",
                },
                "opts": [
                    {"zh": "install_deps.sh 装依赖；make generated-proto 生成 proto；make milvus(-gpu) 编二进制；standalone_embed.sh/start_*.sh 启动；stop_graceful.sh 优雅停止让写入/刷盘收尾", "en": "install_deps.sh installs deps; make generated-proto generates proto; make milvus(-gpu) builds the binary; standalone_embed.sh/start_*.sh launch; stop_graceful.sh stops gracefully, letting writes/flushes finish"},
                    {"zh": "应该用 kill 直接杀进程，比优雅停止更安全", "en": "You should kill the process directly — safer than a graceful stop"},
                    {"zh": "make generated-proto 必须在 make milvus 之后运行", "en": "make generated-proto must run after make milvus"},
                    {"zh": "GPU 版和 CPU 版用同一个 make 目标", "en": "GPU and CPU builds use the same make target"},
                ],
                "answer": 0,
                "why": {
                    "zh": "完整链路：install_deps.sh 一次装齐 cmake/conan/Go；make generated-proto 由 milvus-proto 生成代码(必须先于编译，因 C++/Go 都要 include/import 这些类型)；make milvus(CPU)/make milvus-gpu(GPU，链接 CUDA/RAFT)两段式编出二进制；用 standalone_embed.sh(零依赖)/start_standalone.sh/start_cluster.sh 启动；stop_graceful.sh 优雅停止，先刷盘、记检查点、了断在途请求再退出——草率 kill 可能丢失未刷盘状态、重启要靠重放恢复。",
                    "en": "Full chain: install_deps.sh installs cmake/conan/Go at once; make generated-proto generates code from milvus-proto (must precede compilation since C++/Go both include/import these types); make milvus (CPU)/make milvus-gpu (GPU, links CUDA/RAFT) two-stage build the binary; launch via standalone_embed.sh (zero-dep)/start_standalone.sh/start_cluster.sh; stop_graceful.sh stops gracefully — flush, checkpoint, settle in-flight requests, then exit. A careless kill may lose unflushed state, forcing replay recovery on restart.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说 Milvus 的构建“不只是 go build”，根子在它 Go+C++ 的双语本质。请：(1) 用自己的话解释 make milvus 的两段(build-cpp / build-go)各做什么、cgo 在哪里咬合、为什么次序不能反；(2) 为什么编 Milvus 要装 cmake/conan 这套 C++ 工具链，而纯 Go 项目不用？(3) “一个二进制扮演多角色(cmd/main.go)”对构建、版本管理、单机/集群部署各带来什么好处？再联系第 2、34 课，谈谈“Go+C++ 双语架构”在性能与构建复杂度之间是怎样取舍的。",
                "en": "This lesson says Milvus's build is 'not just go build', rooted in its Go+C++ bilingual nature. Please: (1) in your own words explain what make milvus's two stages (build-cpp / build-go) each do, where cgo meshes, and why the order can't reverse; (2) why does building Milvus need the cmake/conan C++ toolchain while a pure-Go project doesn't? (3) what does 'one binary, many roles (cmd/main.go)' buy for builds, version management, and standalone/cluster deployment? Tying to Lessons 2 and 34, discuss how the 'Go+C++ bilingual architecture' trades off performance against build complexity.",
            },
        ],
    },
    "43-testing.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 的 Go 单测为什么必须带 -tags dynamic,test 和 -gcflags=\"all=-N -l\"？",
                    "en": "Why must Milvus's Go unit tests carry -tags dynamic,test and -gcflags=\"all=-N -l\"?",
                },
                "opts": [
                    {"zh": "dynamic,test 让 Go 动态链接 C++ 内核并启用测试代码(cgo 项目所需)；-N -l 关优化/内联，使函数保留可替换入口，bytedance/mockey 才能在运行时打补丁", "en": "dynamic,test makes Go dynamically link the C++ core and enable test code (needed by this cgo project); -N -l disables optimization/inlining so functions keep a replaceable entry, letting bytedance/mockey patch at runtime"},
                    {"zh": "纯粹是历史遗留，没实际作用", "en": "Pure legacy with no real effect"},
                    {"zh": "为了让测试跑得更快", "en": "To make tests run faster"},
                    {"zh": "因为 Go 在 Linux 上必须加这些参数", "en": "Because Go requires these on Linux"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Milvus 是 Go+C++：dynamic 让 Go 动态链接 C++ 内核库(cgo)、test 启用测试专用代码，少了就编不过。-gcflags=\"all=-N -l\" 关优化(-N)与内联(-l)：mockey 是在机器码层面把函数跳转到假实现的“猴子补丁”，若函数被内联/优化，入口消失、补丁打不上，测试会编译失败或 panic。所以 -N -l 不是调优而是 mockey 工作的前提——这正是测试约定反复强调它的原因。",
                    "en": "Milvus is Go+C++: dynamic dynamically links the C++ core (cgo), test enables test-only code — miss them and it won't compile. -gcflags=\"all=-N -l\" disables optimization (-N) and inlining (-l): mockey is a machine-code 'monkey-patch' redirecting a function to a fake; if a function is inlined/optimized its entry vanishes, the patch can't land, and tests fail to compile or panic. So -N -l isn't tuning but a prerequisite for mockey — exactly why conventions keep stressing it.",
                },
            },
            {
                "q": {
                    "zh": "Milvus 测试里 mockery 与 mockey 的区别是什么？",
                    "en": "What's the difference between mockery and mockey in Milvus tests?",
                },
                "opts": [
                    {"zh": "mockery(vektra)编译期为接口生成假实现(internal/mocks，勿手改、make generate-mockery-* 重生成)；mockey(bytedance)运行时给具体函数打补丁——接口用前者、函数用后者", "en": "mockery (vektra) compile-time generates interface fakes (internal/mocks; don't hand-edit, regenerate via make generate-mockery-*); mockey (bytedance) patches concrete functions at runtime — interfaces use the former, functions the latter"},
                    {"zh": "两者是同一个工具的不同拼写", "en": "They're the same tool spelled differently"},
                    {"zh": "mockery 管运行时、mockey 管编译期", "en": "mockery is runtime, mockey is compile-time"},
                    {"zh": "都需要手动编辑生成的 mock 文件", "en": "Both require hand-editing the generated mock files"},
                ],
                "answer": 0,
                "why": {
                    "zh": "名字像但完全不同。mockery(vektra/mockery)是编译期：读接口、生成实现该接口的假对象(文件在 internal/mocks、mock_*.go)，是生成物——勿手改，改接口后用 make generate-mockery-{模块} 重生成(同 proto 的 .pb.go“别手编”)。mockey(bytedance/mockey)是运行时：不靠接口，直接替换具体函数实现(需 -N -l)。判断法则：面向接口的依赖用 mockery 注入；要换具体/包级函数用 mockey。",
                    "en": "Alike in name, opposite in nature. mockery (vektra/mockery) is compile-time: reads an interface and generates a fake implementing it (files in internal/mocks, mock_*.go) — a generated artifact; don't hand-edit, change the interface then regenerate via make generate-mockery-{module} (like proto .pb.go 'don't hand-edit'). mockey (bytedance/mockey) is runtime: not interface-based, it replaces a concrete function's implementation (needs -N -l). Rule: inject interface deps with mockery; replace concrete/package-level functions with mockey.",
                },
            },
            {
                "q": {
                    "zh": "下面关于跑 Milvus 测试的说法，哪个正确？",
                    "en": "Which statement about running Milvus tests is correct?",
                },
                "opts": [
                    {"zh": "用 make test-go(先 build-cpp-with-unittest 再带正确标志跑)或 make test-proxy/test-querycoord 等模块快捷方式；C++ 用 make test-cpp；单测某函数也要带全那串标志", "en": "Use make test-go (first build-cpp-with-unittest then run with the right flags) or module shortcuts like make test-proxy/test-querycoord; C++ via make test-cpp; even a single test function needs the full flag string"},
                    {"zh": "直接 go test ./... 即可，无需任何特殊参数", "en": "A plain go test ./... suffices, no special flags"},
                    {"zh": "Go 测试不需要先编 C++", "en": "Go tests don't need to build C++ first"},
                    {"zh": "make test-go 会跳过竞态检测", "en": "make test-go skips the race detector"},
                ],
                "answer": 0,
                "why": {
                    "zh": "make test-go 先 build-cpp-with-unittest(Go 测试要 cgo 链接 C++)，再调 run_go_unittest.sh 用 -tags dynamic,test -gcflags=\"all=-N -l\" -race -cover -failfast -count=1 -ldflags=\"-r RPATH\" 逐包跑。只想跑某模块有 make test-proxy/test-querycoord/test-datacoord/test-rootcoord/test-querynode/test-datanode；C++ 用 make test-cpp。直接 go test 因缺标志(找不到 C++ 库、mockey 失灵)会失败；开发跑单个函数也得带全标志加 -run TestXxx。",
                    "en": "make test-go first runs build-cpp-with-unittest (Go tests cgo-link C++), then run_go_unittest.sh runs per package with -tags dynamic,test -gcflags=\"all=-N -l\" -race -cover -failfast -count=1 -ldflags=\"-r RPATH\". Module shortcuts: make test-proxy/test-querycoord/test-datacoord/test-rootcoord/test-querynode/test-datanode; C++ via make test-cpp. A plain go test fails for missing flags (can't find C++ libs, mockey breaks); running one function still needs the full flags plus -run TestXxx.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课把那串测试标志比作“进实验室的装备”，并说测试的“特殊”浓缩了 Milvus 的两大基因(双语与并发)。请：(1) 把 -tags dynamic,test / -gcflags=\"all=-N -l\" / -race 三者分别对应到“为何需要”，尤其说清 -N -l 与 mockey 的因果；(2) 给两个测试场景各选 mockery 还是 mockey 并说明：A) 被测函数依赖一个 Coordinator 接口；B) 被测函数内部调用了一个包级工具函数且无法注入；(3) 为什么 mock 文件(internal/mocks)“勿手改”？这和第 8 部分 proto 生成文件的纪律是同一条吗？",
                "en": "This lesson likens the test flags to 'lab gear' and says testing's 'specialness' distills Milvus's two genes (bilingual and concurrent). Please: (1) map -tags dynamic,test / -gcflags=\"all=-N -l\" / -race each to 'why it's needed', especially the -N -l ↔ mockey causation; (2) for two scenarios choose mockery or mockey and justify: A) the function under test depends on a Coordinator interface; B) it internally calls a package-level helper that can't be injected; (3) why must mock files (internal/mocks) not be hand-edited? Is this the same discipline as Part 8's generated proto files?",
            },
        ],
    },
    "44-code-conventions.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 的 merr 把错误分成 Input 与 System 两类，核心判据和后果是什么？",
                    "en": "Milvus's merr splits errors into Input and System. What's the core criterion and consequence?",
                },
                "opts": [
                    {"zh": "判据是“归因测试”：请求内容本身逼出的=Input(不可重试、如实返回用户)；Milvus 自身/暂时性故障=System(保持可重试、该报警)。归类直接决定系统要不要重试", "en": "The criterion is the 'blame test': forced by the request content itself = Input (not retriable, return to user); Milvus's own/transient failure = System (stays retriable, should alarm). Classification directly decides whether the system retries"},
                    {"zh": "Input 是小错、System 是大错，按严重程度分", "en": "Input is minor, System is major — split by severity"},
                    {"zh": "两类完全等价，随便归哪类都行", "en": "The two are equivalent; classify either way"},
                    {"zh": "Input 用于 C++、System 用于 Go", "en": "Input is for C++, System for Go"},
                ],
                "answer": 0,
                "why": {
                    "zh": "判据不是“看起来像不像参数校验”，而是归因测试：是请求内容本身逼出这个分支(Input，怪用户、重试也没用)，还是内部/暂时性失败(System，不怪用户、过会儿可能就好)。后果很实际：Milvus 很多地方用 retry.Do 自动重试，把本可重试的 System 误标 Input 会让“等一下就成”的操作枉死；把注定失败的 Input 误标 System 会让系统空转重试。所以归类直接决定重试行为。",
                    "en": "The criterion isn't 'does it look like validation' but the blame test: did the request content force this branch (Input — user's fault, retry won't help) or an internal/transient failure (System — not the user's fault, may clear up). The consequence is concrete: many places use retry.Do; mislabeling a retriable System as Input kills an op that would've succeeded after a wait; mislabeling a doomed Input as System spins endless retries. So classification directly decides retry behavior.",
                },
            },
            {
                "q": {
                    "zh": "关于给错误加上下文与新增错误码，下面哪条做法符合 merr 约定？",
                    "en": "About adding context to errors and adding new error codes, which follows merr conventions?",
                },
                "opts": [
                    {"zh": "加上下文只用 merr.Wrap/Wrapf(不用 WrapErrXxxErr(err,…) 以免盖掉内层码)；新增错误要从 errors.go 现有家族区间里取码、按 Input/System 设可重试标志", "en": "Add context only via merr.Wrap/Wrapf (not WrapErrXxxErr(err,…) which masks the inner code); new errors pick a code from the existing family range in errors.go and set the retriable flag per Input/System"},
                    {"zh": "随手用 fmt.Errorf 包一下最省事", "en": "Just wrap with fmt.Errorf, simplest"},
                    {"zh": "新增错误码随便挑个没用过的数字即可，无所谓区间", "en": "Pick any unused number for a new code, ranges don't matter"},
                    {"zh": "把错误改成 Input 不用管别处有没有 retry.Do", "en": "Turning an error Input needn't consider any retry.Do elsewhere"},
                ],
                "answer": 0,
                "why": {
                    "zh": "加上下文用 merr.Wrap/Wrapf——它保留内层错误码；而 WrapErrXxxErr(err,…) 会用新错误盖掉内层码、丢失原始分类。错误码在 errors.go 里是分段的：相近职责的错码在相近区间，新增时必须从对应家族区间挑码、别和 C++ segcore 码撞车，并按 Input/System 设好可重试布尔。此外把某错改成 Input 前要先 grep retry.Do，确认没有重试链依赖它的可重试性——改错归类会悄悄破坏重试。",
                    "en": "Add context with merr.Wrap/Wrapf — it preserves the inner code; WrapErrXxxErr(err,…) masks it with a new error, losing the original classification. Codes in errors.go are partitioned: similar-duty errors sit in adjacent ranges, so a new error must pick from its family range (not collide with C++ segcore codes) and set the retriable bool per Input/System. Also, before turning an error Input, grep retry.Do to ensure no retry chain depends on its retriability — mislabeling silently breaks retries.",
                },
            },
            {
                "q": {
                    "zh": "下面关于 Milvus 其余硬约定(日志/import/生成文件)的说法，哪个正确？",
                    "en": "Which statement about Milvus's other hard conventions (logging/imports/generated files) is correct?",
                },
                "opts": [
                    {"zh": "日志只用 mlog(带 ctx；log/zap/fmt.Println 被 depguard 禁)；import 按 标准库→第三方→github.com/milvus-io(gci 强制)；mocks/.pb.go 改源头重生成、勿手改——多由 golangci-lint/gci 自动把关", "en": "Log only via mlog (with ctx; log/zap/fmt.Println forbidden by depguard); imports stdlib→third-party→github.com/milvus-io (gci-enforced); mocks/.pb.go regenerate from source, don't hand-edit — mostly auto-enforced by golangci-lint/gci"},
                    {"zh": "想用哪个日志库都行，linter 不管", "en": "Use any logging library; the linter doesn't care"},
                    {"zh": "import 顺序随意，gci 只是建议", "en": "Import order is free; gci is only a suggestion"},
                    {"zh": "生成的 mock 文件应该直接手改来通过测试", "en": "Generated mock files should be hand-edited to pass tests"},
                ],
                "answer": 0,
                "why": {
                    "zh": ".golangci.yml 用 depguard 明令禁止 pkg/v3/log、标准 log、裸 zap，强制只用 pkg/v3/mlog 且每条带 ctx(第 39 课)。gci 把 import 强制成 标准库→第三方→github.com/milvus-io 三段、本项目包排最后。mockery 生成的 mock 与 proto 的 .pb.go 是生成物，要改接口/proto 再 make 重生成、别手改(同第 43 课纪律)。这些约定大多由 golangci-lint/gci 与守护测试自动执行——提 PR 前本地先 lint+测试自查最省事。",
                    "en": ".golangci.yml uses depguard to forbid pkg/v3/log, standard log, raw zap, forcing pkg/v3/mlog with ctx on every call (Lesson 39). gci enforces imports into stdlib→third-party→github.com/milvus-io, this project's packages last. mockery-generated mocks and proto .pb.go are artifacts — change the interface/proto then regenerate via make, don't hand-edit (Lesson 43's discipline). These are mostly auto-enforced by golangci-lint/gci and guard tests — self-check with lint+tests locally before a PR.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说“一个错误还携带着该拿它怎么办的信息”，merr 让错误自带身份(码/可重试/Input vs System)。请：(1) 举一个具体例子(如 ErrCollectionNotFound)说明同一个错为何在内部默认 System(可重试)、到 proxy 边界才用 WrapErrAsInputErrorWhen 翻成 Input；(2) 解释为什么用 merr.Wrap 而非 WrapErrXxxErr 加上下文；(3) 这些约定大多由 linter 自动执行，谈谈“把约定固化成工具”对一个数百人协作的开源项目意味着什么——它和第 40 课“配置收口”、第 43 课“生成文件别手改”体现了怎样共同的工程审美？",
                "en": "This lesson says 'an error also carries information about what to do with it'; merr gives errors an identity (code/retriable/Input vs System). Please: (1) with a concrete example (e.g. ErrCollectionNotFound) explain why the same error defaults to System (retriable) internally but is flipped to Input via WrapErrAsInputErrorWhen only at the proxy boundary; (2) explain why add context with merr.Wrap rather than WrapErrXxxErr; (3) these conventions are mostly linter-enforced — discuss what 'solidifying conventions into tools' means for a hundreds-of-contributors open-source project, and what shared engineering aesthetic it shares with Lesson 40's 'config funneling' and Lesson 43's 'don't hand-edit generated files'.",
            },
        ],
    },
    "45-contributing-prs.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Milvus 采用 fork-and-pull 协作流程，下面哪个描述正确？",
                    "en": "Milvus uses the fork-and-pull workflow. Which description is correct?",
                },
                "opts": [
                    {"zh": "你没有官方仓库写权限：fork 到自己账号(origin)干活、加官方为 upstream 只拉不推；从 upstream/master 开分支改、push 到 origin、再向 master 发 PR，CI+评审后合入", "en": "You lack write access to the official repo: fork to your account (origin) to work, add the official as upstream (pull-only); branch from upstream/master, push to origin, file a PR to master, merged after CI+review"},
                    {"zh": "直接把改动 push 到 milvus-io/milvus 的 master", "en": "Push changes straight to milvus-io/milvus's master"},
                    {"zh": "fork 后就有了官方仓库的写权限", "en": "Forking grants write access to the official repo"},
                    {"zh": "不需要分支，直接在 master 上改", "en": "No branch needed, edit master directly"},
                ],
                "answer": 0,
                "why": {
                    "zh": "贡献者成千上万，不可能给每人开主仓库写权限。fork 机制：你对自己账号下的 fork(origin)有完全写权限，随便改；官方仓库作为 upstream 只能 fetch、不能 push。典型流动：从 upstream 拉最新→本地改→push 到 origin→从 origin 向 upstream 发 PR→CI+维护者评审→合入 master。配 upstream 还能开发前同步最新、减少冲突。这样既不挡参与自由，又守住主仓库质量。",
                    "en": "With thousands of contributors, you can't grant everyone write access to the main repo. The fork mechanism: you have full write access to your fork (origin) to change freely; the official repo as upstream is fetch-only, not push. Typical flow: pull latest from upstream→change locally→push to origin→file a PR from origin to upstream→CI+maintainer review→merge to master. Adding upstream also lets you sync before developing, reducing conflicts. This keeps participation open while protecting the main repo's quality.",
                },
            },
            {
                "q": {
                    "zh": "关于 DCO 签名(Signed-off-by)，下面哪条正确？",
                    "en": "About the DCO sign-off (Signed-off-by), which is correct?",
                },
                "opts": [
                    {"zh": "每个 commit 都需带 Signed-off-by，用 git commit -s 自动追加；它声明你有权按本项目许可证提交这段代码，缺了 DCO 检查会拦下 PR", "en": "Every commit needs a Signed-off-by, auto-appended by git commit -s; it declares you have the right to submit this code under the project's license, and a missing one blocks the PR via the DCO check"},
                    {"zh": "只需在第一个 commit 签一次即可", "en": "You only need to sign the first commit once"},
                    {"zh": "DCO 是可选的，CI 不检查", "en": "DCO is optional; CI doesn't check it"},
                    {"zh": "AI 工具的署名可以替代你的 DCO 签名", "en": "An AI tool's attribution can replace your DCO sign-off"},
                ],
                "answer": 0,
                "why": {
                    "zh": "DCO(开发者原创声明)要求每个 commit 信息含一行 Signed-off-by: 姓名 <邮箱>；git commit -s 用你的 git 身份自动追加。它是一份轻量声明：你确认这段代码是你写的、或你有权按本项目开源许可证提交，用于厘清来源、规避版权风险。缺了它 DCO 检查标红、拦下 PR——可用 git rebase 给历史提交补 -s 再强推。注意：用 AI 辅助时，最后一行的 sign-off 必须是你这位开发者，AI 署名只能另加、不能顶替。",
                    "en": "The DCO requires each commit message to contain a line Signed-off-by: Name <email>; git commit -s auto-appends it using your git identity. It's a lightweight statement: you confirm the code is yours or you have the right to submit it under the project's license, clarifying provenance and avoiding copyright risk. Without it the DCO check goes red and blocks the PR — you can git rebase to add -s to past commits then force-push. Note: with AI assistance, the final sign-off must be you the developer; the AI's attribution is additional, not a replacement.",
                },
            },
            {
                "q": {
                    "zh": "关于 PR 标题格式与按类型的关联要求，下面哪个正确？",
                    "en": "About the PR title format and per-type linking requirements, which is correct?",
                },
                "opts": [
                    {"zh": "标题为 {type}: {描述}(feat/fix/enhance/test/doc…)；fix 须关联 issue，feat 须关联 issue+设计文档(docs/design-docs，否则 Mergify 拦)，enhance 大改才需 issue，doc/test 不强制；body 非空", "en": "Title is {type}: {description} (feat/fix/enhance/test/doc…); fix must link an issue, feat must link issue+design doc (docs/design-docs, else Mergify blocks), enhance needs an issue only if large, doc/test don't; body non-empty"},
                    {"zh": "标题随便写，机器人不检查", "en": "Title is free-form; bots don't check"},
                    {"zh": "所有 PR 都不需要关联任何 issue", "en": "No PR needs to link any issue"},
                    {"zh": "feat 只要有 issue 就行，不需要设计文档", "en": "feat only needs an issue, no design doc"},
                ],
                "answer": 0,
                "why": {
                    "zh": "Milvus 要求 PR 标题写成 {type}: {描述}，type 固定为 feat(新功能)/fix(修 bug)/enhance(增强)/test/doc/auto/build(deps) 等，便于维护者识别并驱动自动化。按类型关联：fix 须 issue(issue: #123)；feat 须 issue+设计文档(放 docs/design-docs，缺了 Mergify 贴 do-not-merge/missing-design-doc 拦住)；enhance 仅大改(L/XL/XXL)需 issue；doc/test 不强制。此外 body 不能为空；改 2.x 分支还要关联对应 master PR(pr: #123)。",
                    "en": "Milvus requires PR titles as {type}: {description}, with type fixed to feat (new feature)/fix (bug)/enhance/test/doc/auto/build(deps), so maintainers can identify and drive automation. Linking by type: fix needs an issue (issue: #123); feat needs issue+design doc (under docs/design-docs; missing it, Mergify adds do-not-merge/missing-design-doc to block); enhance needs an issue only if large (L/XL/XXL); doc/test don't. Also the body can't be empty; a PR to a 2.x branch must link the matching master PR (pr: #123).",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说提 PR 的格式关卡(DCO/标题/关联)由机器人先把关，好让人类评审专注于“代码本身好不好”。请：(1) 把一次贡献从 fork 到合入的完整流程用自己的话讲一遍，说清 upstream/origin/本地三者间数据怎么流动；(2) 解释为什么 feat: 类 PR 要强制关联设计文档，这与第 44 课“用 linter 强制约定”体现了怎样共同的思路；(3) 作为一个刚读完这份指南的新人，你打算从什么样的第一个改动入手(如 good first issue / 文档修正 / 补测试)？为什么从小处起步是迈出第一步的好策略？",
                "en": "This lesson says a PR's format gates (DCO/title/links) are bot-checked first so human review focuses on 'is the code good'. Please: (1) narrate a full contribution from fork to merge in your own words, clarifying how data flows among upstream/origin/local; (2) explain why feat: PRs must link a design doc, and what shared idea this shares with Lesson 44's 'enforce conventions via linters'; (3) as a newcomer who just finished this guide, what first change would you start with (e.g. a good first issue / doc fix / adding a test), and why is starting small a good strategy for taking the first step?",
            },
        ],
    },
    "47-bulk-import.html": {
        "mcq": [
            {
                "q": {
                    "zh": "为什么 Milvus 在流式写入之外，还要单独做一条批量导入路径？",
                    "en": "Why does Milvus build a separate bulk-import path in addition to streaming writes?",
                },
                "opts": [
                    {"zh": "海量一次性灌库若仍逐行走 WAL 会又慢、又挤占在线写入、又浪费(这些数据本就一次写定)；批量导入绕过 WAL、读文件直接生成段，专为离线大批量优化", "en": "Routing a one-shot massive load through the WAL row by row is slow, crowds out online writes, and is wasteful (this data is write-once); bulk import bypasses the WAL and reads files straight into segments, optimized for large offline loads"},
                    {"zh": "因为流式写入无法保证数据安全", "en": "Because streaming writes can't keep data safe"},
                    {"zh": "因为批量导入产出的段格式和流式不同、必须分开", "en": "Because imported segments have a different format and must be separate"},
                    {"zh": "纯粹为了多一个 API", "en": "Purely to add one more API"},
                ],
                "answer": 0,
                "why": {
                    "zh": "流式写入(第15–17课)为在线持续写入而生：逐行经 Proxy→WAL→growing→flush，保证实时可见、崩溃可重放。但一次性灌入上亿历史行时，逐行走 WAL 会慢(每行序列化/Append/定序/消费)、会把 WAL 与 StreamingNode 堵死拖垮在线写入、且对“一次写定、不再改”的数据而言 WAL 的实时/可重放保险纯属浪费。所以批量导入绕过 WAL、直接读文件写段——批量场景用批量工具。注意“绕过 WAL≠不安全”：导入的事实来源是源文件本身，失败重来即可。",
                    "en": "Streaming writes (L15–17) are built for online continuous ingestion: row by row via Proxy→WAL→growing→flush, ensuring real-time visibility and crash replay. But loading hundreds of millions of historical rows at once via the WAL is slow (each row serialized/appended/ordered/consumed), jams the WAL and StreamingNode (hurting online writes), and wastes the WAL's real-time/replay insurance on write-once data. So bulk import bypasses the WAL, reading files straight into segments — batch tools for batch scenes. Note 'bypassing WAL ≠ unsafe': the source of truth is the source files themselves; on failure, just rerun.",
                },
            },
            {
                "q": {
                    "zh": "批量导入被 DataCoord 编排成一个多阶段作业，其阶段大致是什么、为什么分阶段？",
                    "en": "Bulk import is a DataCoord-orchestrated multi-phase job. What are the phases roughly, and why phase it?",
                },
                "opts": [
                    {"zh": "Pending→PreImport(扫描/校验/估算)→Import(读文件直接写段)→Sorting→IndexBuilding→提交；分阶段以便断点续作、进度可查、失败可重试", "en": "Pending→PreImport (scan/validate/estimate)→Import (read files straight into segments)→Sorting→IndexBuilding→commit; phased for resumability, queryable progress, retry on failure"},
                    {"zh": "只有一个阶段：把文件一把灌进去", "en": "Just one phase: dump the files in at once"},
                    {"zh": "先建索引、再读文件，顺序相反", "en": "Build indexes first, then read files — reverse order"},
                    {"zh": "由 Proxy 而非 DataCoord 全程执行", "en": "Executed entirely by Proxy, not DataCoord"},
                ],
                "answer": 0,
                "why": {
                    "zh": "客户端调 ImportV2，Proxy 的 importTask 转交 DataCoord(本就管段/落盘/建索引的协调者)。DataCoord 把导入当成有状态作业：Pending→PreImporting→Importing→Sorting→IndexBuilding→Uncommitted→Committing(失败进 Failed)。导入海量数据是长时间、易失败的过程，拆成阶段才能断点续作、进度可查、失败可重试——与第21课“按段建索引”同一种“拆成可调度可恢复小步”的智慧。DataNode 执行实际的读文件写段，importutilv2 支持 json/csv/numpy/parquet。",
                    "en": "The client calls ImportV2; Proxy's importTask hands it to DataCoord (already the coordinator of segments/flushing/indexing). DataCoord treats import as a stateful job: Pending→PreImporting→Importing→Sorting→IndexBuilding→Uncommitted→Committing (Failed on error). Importing massive data is long-running and failure-prone, so phasing enables resume, queryable progress, and retry — the same 'schedulable, recoverable steps' wisdom as Lesson 21's per-segment indexing. DataNodes do the actual read-files-into-segments; importutilv2 supports json/csv/numpy/parquet.",
                },
            },
            {
                "q": {
                    "zh": "为什么把 PreImport 和 Import 拆成两段，PreImport 在做什么？",
                    "en": "Why split PreImport from Import, and what does PreImport do?",
                },
                "opts": [
                    {"zh": "PreImport 先空跑勘探：校验 schema、估算行数与分布(autoID 时尤其要预知行数以预留主键 ID)，不写数据；提前排雷、规划切段，让正式 Import 能放心并行", "en": "PreImport does a dry-run survey first: validate schema, estimate row count and distribution (esp. under autoID, to pre-allocate PK IDs), writing no data; it clears mines and plans segment slicing so the real Import can run in parallel with confidence"},
                    {"zh": "PreImport 就是把数据先写一遍、Import 再写一遍", "en": "PreImport writes the data once and Import writes it again"},
                    {"zh": "两者完全相同，只是名字不同", "en": "They're identical, just named differently"},
                    {"zh": "PreImport 负责删除旧数据", "en": "PreImport deletes old data"},
                ],
                "answer": 0,
                "why": {
                    "zh": "“先勘探、再施工”：PreImport 只扫描/校验/估算、不落数据。它提前确认文件可读、schema 对得上(不匹配就早报错，免得写到一半留下半成品段)；并估算行数与分布——在 autoID 下，系统须预知行数才能一次性预留连续的主键 ID 区间分给并行的 DataNode，否则主键会撞号或留空洞。用一次廉价预扫描换取正式执行的确定性与高效；与第44课 merr“输入错误尽早在边界发现”一脉相承。",
                    "en": "'Survey first, then build': PreImport only scans/validates/estimates, writing no data. It confirms files are readable and the schema matches (erroring early instead of leaving half-built segments), and estimates row count/distribution — under autoID, the system must know the count to pre-allocate a contiguous PK-ID range for parallel DataNodes, else PKs collide or leave gaps. A cheap pre-scan buys certainty and efficiency at execution time; akin to Lesson 44's merr 'catch input errors early at the boundary'.",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说批量导入与流式写入是“同一个段抽象、两条生产路径”。请：(1) 给三个场景各选一条写入路径并说明：A) 线上应用用户持续插入数据；B) 从旧系统迁移 5 亿条历史向量；C) 每天凌晨批量回填昨日数据。(2) 解释“绕过 WAL”为何在导入场景里是安全的——导入的“事实来源”是什么？(3) 为什么让两条路径都产出“同格式的段”很重要？这与第 22 课(Knowhere 统一接口)、第 36 课(算子统一吃一批吐一批)体现了怎样共同的设计审美？",
                "en": "This lesson says bulk import and streaming writes are 'one segment abstraction, two production paths'. Please: (1) pick a write path for each scenario and justify: A) an online app continuously inserting user data; B) migrating 500M historical vectors from a legacy system; C) a nightly batch backfill of yesterday's data. (2) Explain why 'bypassing the WAL' is safe in the import scenario — what is the import's 'source of truth'? (3) Why does it matter that both paths produce 'same-format segments'? What shared design aesthetic does this share with Lesson 22 (Knowhere's unified interface) and Lesson 36 (operators uniformly consuming/emitting a batch)?",
            },
        ],
    },
    "48-hybrid-search-rerank.html": {
        "mcq": [
            {
                "q": {
                    "zh": "为什么需要混合检索(HybridSearch)，而不是只用一个向量字段搜？",
                    "en": "Why hybrid search instead of searching just one vector field?",
                },
                "opts": [
                    {"zh": "单一 embedding 有盲区：稠密向量擅语义却不抓精确关键词，稀疏(BM25)擅关键词却不懂近义；混合检索用多个向量字段综合多种相关性信号(也用于多模态)", "en": "A single embedding has blind spots: dense excels at semantics but misses exact keywords, sparse (BM25) hits keywords but ignores synonyms; hybrid search combines multiple vector fields and relevance signals (also for multimodal)"},
                    {"zh": "因为单向量检索结果总是错的", "en": "Because single-vector search is always wrong"},
                    {"zh": "因为混合检索更省内存", "en": "Because hybrid search uses less memory"},
                    {"zh": "纯粹为了让查询更慢", "en": "Purely to make queries slower"},
                ],
                "answer": 0,
                "why": {
                    "zh": "稠密向量(第4课)擅长语义——沙发≈长椅，但对“XJ-200”这种精确关键词不敏感；稀疏向量/BM25(第24课)擅长关键词精确命中，却不懂近义。两者盲区互补。一个集合可定义多个向量字段(第6课)，混合检索同时打到多个字段、综合多种信号，也覆盖多模态(图+文)、多视角。这是把检索从玩具推向真实业务(尤其 RAG：提问既含语义又含关键术语)的关键一步。",
                    "en": "Dense vectors (L4) excel at semantics — sofa≈couch — but miss exact keywords like 'XJ-200'; sparse/BM25 (L24) nails keyword hits but ignores synonyms. Their blind spots complement. A collection can define multiple vector fields (L6); hybrid search hits several at once, combining signals, also covering multimodal (image+text) and multi-view. It's a key step from toy to real workload (especially RAG, where questions carry both semantics and key terms).",
                },
            },
            {
                "q": {
                    "zh": "一次 HybridSearch 在系统里是怎么执行的？",
                    "en": "How is a HybridSearch executed in the system?",
                },
                "opts": [
                    {"zh": "它带 N 个 SubReqs，每个就是一次完整的普通向量检索；Proxy 把它们并行扇出(复用第25–29课查询链路)、各得一份 ranked 列表，再用 ranker 融合成最终 topK", "en": "It carries N SubReqs, each a complete plain vector search; the Proxy fans them out in parallel (reusing the Lesson 25–29 path), gets a ranked list each, then fuses into the final topK with a ranker"},
                    {"zh": "它是一个全新的、独立于普通检索的引擎", "en": "It's a brand-new engine independent of plain search"},
                    {"zh": "它把所有向量字段拼成一个大向量再搜一次", "en": "It concatenates all vector fields into one big vector and searches once"},
                    {"zh": "它只在一个段里搜、不扇出", "en": "It searches in one segment only, no fan-out"},
                ],
                "answer": 0,
                "why": {
                    "zh": "HybridSearchRequest 带一组 SubReqs，每个指定搜哪个向量字段、用什么查询向量、topK、过滤。Proxy(task_search.go)见 len(SubReqs)>0 即知是 advanced 混合检索，把每路当独立搜索扇出，复用 delegator 扇段、filter-then-search、三层 reduce(第29课)，各自归并出一份 topK。所以它不另造引擎，而是“N 次普通检索并起来跑 + 一道融合”。子搜索数有上限(defaultMaxSearchRequest)；且每路通常要多取候选(比最终 topK 大)，因为融合会打乱名次。",
                    "en": "A HybridSearchRequest carries a set of SubReqs, each specifying the vector field, query vector, topK, filter. The Proxy (task_search.go), seeing len(SubReqs)>0, treats each as an independent search, reusing delegator fan-out, filter-then-search, and the three-level reduce (L29), each merging its own topK. So it builds no new engine — 'N plain searches run together + one fusion'. Sub-searches are capped (defaultMaxSearchRequest); each path usually fetches more candidates than the final topK, since fusion reshuffles ranks.",
                },
            },
            {
                "q": {
                    "zh": "融合(rerank)的三类 ranker——RRF、WeightedRanker、模型重排——各自怎么工作、何时用？",
                    "en": "The three rankers — RRF, WeightedRanker, model reranking — how does each work and when to use it?",
                },
                "opts": [
                    {"zh": "RRF 只按名次(1/(k+r)，k默认60，抹平量纲，稳健默认)；WeightedRanker 归一化分数后加权(想给某路更高权重)；模型重排用 cross-encoder 精排(质量最高、成本最高，常只精排少量候选)", "en": "RRF uses rank only (1/(k+r), k default 60, erases units, robust default); WeightedRanker normalizes then weights (to weight a path higher); model reranking uses a cross-encoder (highest quality, highest cost, often only the top few)"},
                    {"zh": "三者都直接把各路原始分数相加", "en": "All three just add the raw scores from each path"},
                    {"zh": "RRF 需要调用外部模型", "en": "RRF requires calling an external model"},
                    {"zh": "模型重排不看查询、只看候选", "en": "Model reranking ignores the query, looking only at candidates"},
                ],
                "answer": 0,
                "why": {
                    "zh": "难点是不同路分数不可比(稠密相似度 0.92 vs BM25 14.7 不是一个量纲)。RRF 干脆只看名次：某榜第 r 名得 1/(k+r)，跨榜相加，天然抹平量纲，不确定怎么权衡时的稳健默认。WeightedRanker 在你明确想偏向某路时，对归一化分数加权求和。模型重排把候选交 cross-encoder(Cohere/TEI 等)成对精看、重新打分，质量最高但要为每个候选跑模型、延迟成本高，故常只对前融合出的少量候选(如 top-50)精排。常见“先粗后精”：RRF 快融出候选 → 模型精排——把贵算力花在刀刃上(同第5/28课分层收敛)。",
                    "en": "The hard part: scores across paths are incomparable (dense 0.92 vs BM25 14.7, different units). RRF looks only at rank: r-th in a list earns 1/(k+r), summed across lists, naturally erasing units — a robust default when unsure. WeightedRanker, when you want to favor a path, weights the normalized scores. Model reranking hands candidates to a cross-encoder (Cohere/TEI) for pairwise re-scoring — highest quality but a model run per candidate, high latency/cost, so often only the top few (e.g. top-50). A common 'coarse then fine': RRF fuses fast → model refines — spend costly compute where it counts (like the layered convergence of L5/L28).",
                },
            },
        ],
        "open": [
            {
                "zh": "本课说混合检索是“多路打分 → 融合成一榜”，且主要在 Proxy 这一层融合。请：(1) 为一个 RAG 问答场景(用户问“2023 年 XJ-200 的退货政策”)设计一个混合检索：用哪些向量字段、为什么纯语义或纯关键词都不够？(2) 解释 RRF 为什么能融合“不可比的分数”，并说明为何每路子搜索常要多取候选(比最终 topK 大)。(3) 为什么融合放在 Proxy 而不是某个 QueryNode？这与第 29 课“三层 reduce 的最顶层是 Proxy”有何呼应？",
                "en": "This lesson says hybrid search is 'score several ways → fuse into one list', fused mainly at the Proxy. Please: (1) design a hybrid search for a RAG scenario (user asks 'the 2023 return policy for XJ-200'): which vector fields, and why is pure-semantic or pure-keyword insufficient? (2) explain why RRF can fuse 'incomparable scores', and why each sub-search often fetches more candidates than the final topK. (3) why is fusion done at the Proxy rather than a QueryNode? How does this echo Lesson 29's 'the top tier of the three-level reduce is the Proxy'?",
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
