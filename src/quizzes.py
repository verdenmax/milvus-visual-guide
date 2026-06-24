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
