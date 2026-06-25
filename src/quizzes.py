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
