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
