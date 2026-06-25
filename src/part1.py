"""Content for Part 1 (macro overview). M0 ships lesson 01 as the baseline."""

LESSON_01 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Milvus 是一个<strong>开源的分布式向量数据库</strong>：它把图片、文本、音频这类<strong>非结构化数据</strong>
先交给 AI 模型编码成<strong>向量</strong>，再在海量（十亿级）向量里<strong>按"相似度"飞快地找出最接近的若干条</strong>。
传统数据库擅长"精确匹配"（按 ID、按关键词），Milvus 擅长的是另一种问题——<strong>"哪些东西在语义上最像它"</strong>。
一个数据库专门把这件事做到又快、又准、又能横向扩展，这就是 Milvus 存在的理由。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把传统数据库想成<strong>按书号查书的目录</strong>：你得先知道确切的编号或书名，才能精确命中一本。
  Milvus 更像一位<strong>懂内容的图书管理员</strong>：你递给他一本书说"<strong>给我找几本读起来'感觉'最像这本的</strong>"，
  他不靠书名，而是凭<strong>内容的相似</strong>把最接近的几本递回来。把"感觉像不像"变成可计算的"距离远不远"，正是向量数据库的看家本领。
</div>

<h2>它到底解决什么问题</h2>
<p>我们身边绝大多数数据都是<strong>非结构化</strong>的——文本、图片、音频、视频。计算机没法直接判断"这两段话意思像不像""这两张图长得像不像"。
现代 AI 的做法是：用一个 <strong>embedding（嵌入）模型</strong>把每条数据编码成一串浮点数，也就是<strong>向量</strong>。
关键性质是：<strong>语义相近的东西，向量在空间里也彼此靠近</strong>。于是"找相似内容"就被翻译成了一个干净的数学问题——
<strong>在向量空间里找最近邻（nearest neighbor）</strong>。</p>

<p>难点在<strong>规模</strong>：当数据有上亿条、每条又是几百上千维时，挨个精确算距离慢得无法接受。
工程上改用<strong>近似最近邻（ANN, Approximate Nearest Neighbor）</strong>：用专门的索引结构，牺牲一点点精度，把检索从"逐个比对"加速成"毫秒级"。
把 ANN 检索作为<strong>一等公民查询</strong>、并围绕它把存储、更新、扩展、高可用都补齐——这就是向量数据库，Milvus 是其中的代表。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：<strong>Milvus 是一个把"ANN 相似检索"当作一等查询的数据库</strong>。它为<strong>十亿级</strong>向量而设计，
  采用<strong>存算分离、云原生（K8s）</strong>的分布式架构，既能横向扩展吞吐，又能靠<strong>实时流式写入</strong>让新数据"边写边可查"。
  它用 <strong>Go + C++</strong>（少量 Rust）实现，对 CPU/GPU 做了加速。
</div>

<div class="cols">
  <div class="col"><h4>传统（标量）数据库</h4><p>查询是<strong>精确匹配</strong>：<span class="inline">WHERE id = 42</span>、按关键词命中。
  数据是结构化的行与列，索引是 B-Tree / 哈希。问"<strong>等于谁</strong>"。</p></div>
  <div class="col"><h4>向量数据库 Milvus</h4><p>查询是<strong>相似检索</strong>：给一个向量，返回<strong>距离最近的 topK</strong>。
  数据是高维向量（+ 标量字段），索引是 HNSW / IVF / DiskANN 等 ANN 结构。问"<strong>最像谁</strong>"。</p></div>
</div>

<h2>向量从哪来：用 embedding 把万物编码成点</h2>
<p>向量不是凭空冒出来的，而是由 <strong>embedding（嵌入）模型</strong>算出来的。可以把它想成一台"<strong>理解机</strong>"：
喂进一段文字或一张图，它吐出一串固定长度的浮点数，把这条数据的"含义"压进这串数字里。模型在海量数据上训练过，
<strong>学会了让"意思相近"的输入产出"位置相近"的向量</strong>——"猫"和"小猫"几乎挨在一起，"猫"和"利率"则隔得很远。
于是"语义相似"这件以前说不清的事，第一次有了可计算的尺子。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>原始数据</h4><p>一段文字、一张图片、一段音频……计算机眼里它们无法直接比较"像不像"。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>embedding 模型</h4><p class="mono">BERT / CLIP / bge…</p><p>训练好的神经网络，把每条数据映射成固定维度的向量。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>向量（如 768 维）</h4><p>语义相近 ⇒ 点相近；语义无关 ⇒ 点相距很远。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>存入 Milvus</h4><p>向量 + 标量字段（id、原文、价格、标签…）一起入库，建好索引等待检索。</p></div></div>
</div>

<p>两条要点请记牢：①<strong>维度由模型决定</strong>（常见 384 / 768 / 1536 维），同一个集合里的向量必须<strong>同维</strong>；
②<strong>灌库与查询要用同一个模型</strong>，否则两边向量"不在同一个空间"，比距离毫无意义。一句话概括分工：
<strong>"把数据变成向量"是模型的事，"把海量向量存好、索引好、搜得快"才是 Milvus 的事</strong>——本教程讲的正是后者。</p>

<h2>ANN：用一点点精度，换巨大的速度</h2>
<p>有了向量，最朴素的搜索是<strong>暴力检索</strong>：把查询向量和库里<strong>每一条</strong>都算一遍距离，再排序取前 K。
结果精确，但太慢——1 亿条 768 维向量，一次查询要做上百亿次乘加，扛不住高并发。<strong>ANN（近似最近邻）</strong>换了个思路：
预先把向量组织成<strong>索引结构</strong>（分桶的 IVF、可导航小世界图 HNSW、面向磁盘的 DiskANN…），查询时<strong>只看一小部分候选</strong>，
用"<strong>极小的召回损失</strong>"换来"<strong>成百上千倍的提速</strong>"。</p>

<table class="t">
  <tr><th>做法</th><th>怎么找</th><th>速度</th><th>结果</th></tr>
  <tr><td><strong>暴力检索</strong></td><td class="mono">和每条都算距离</td><td>慢（O(N·D)）</td><td>精确</td></tr>
  <tr><td><strong>ANN 索引</strong></td><td class="mono">只看少量候选</td><td>快（毫秒级）</td><td>近似（召回极高）</td></tr>
</table>

<p>"近似"听起来吓人，实际里<strong>召回率常在 95%~99% 以上</strong>，而速度是暴力检索的几百倍——对绝大多数应用，这是笔极划算的买卖。
Milvus 内置多种索引，让你在<strong>速度、内存、精度</strong>之间按需权衡（第 5 课会专门展开）。</p>

<h2>把"相似"变成"距离"：一次搜索长什么样</h2>
<p>向量就是<strong>高维空间里的一个点</strong>。两条数据像不像，用它们向量之间的<strong>距离/相似度</strong>来衡量。Milvus 支持几种常见度量：
<span class="inline">L2</span>（欧氏距离，越小越像）、<span class="inline">IP</span>（内积，越大越像）、<span class="inline">COSINE</span>（余弦相似度）。
一次<strong>搜索</strong>就是：给定一个<strong>查询向量</strong>，在集合里找出距离最近的 <strong>K</strong> 条（称为 <strong>topK</strong>）。</p>

<div class="cellgroup">
  <div class="cg-cap"><b>一次相似检索</b>：查询向量 <span class="mono">q</span> 在 4 条库内向量里找最近的 2 条（topK=2，距离越小越像）</div>
  <div class="cells"><span class="lab">q</span><span class="cell hl">0.90</span><span class="cell hl">0.10</span><span class="cell hl">0.80</span></div>
  <div class="cells"><span class="lab">v1</span><span class="cell">0.88</span><span class="cell">0.12</span><span class="cell">0.79</span><span class="sep">→</span><span class="cell q">距离 0.03 ✓</span></div>
  <div class="cells"><span class="lab">v2</span><span class="cell">0.20</span><span class="cell">0.95</span><span class="cell">0.15</span><span class="sep">→</span><span class="cell dim">距离 1.42</span></div>
  <div class="cells"><span class="lab">v3</span><span class="cell">0.85</span><span class="cell">0.05</span><span class="cell">0.83</span><span class="sep">→</span><span class="cell q">距离 0.07 ✓</span></div>
  <div class="cells"><span class="lab">v4</span><span class="cell">0.10</span><span class="cell">0.30</span><span class="cell">0.90</span><span class="sep">→</span><span class="cell dim">距离 0.96</span></div>
</div>

<p>选哪种度量，取决于你的向量怎么来：<strong>归一化</strong>过的 embedding 常用 <span class="inline">COSINE</span> 或 <span class="inline">IP</span>（方向越一致越相似），
关注绝对位置时用 <span class="inline">L2</span>。同一个集合里，<strong>建索引与搜索必须用同一种度量</strong>，否则"远近"的定义对不上。
返回的 <strong>topK</strong> 是按距离排好序的——第 1 名最像，依次往下；业务里还常配一个"分数阈值"，把"虽然最靠前、但其实不够像"的结果挡掉。</p>

<p>把上面这件事用 Python SDK（pymilvus）写出来，就是"建集合 → 灌数据 → 搜"三步。注意：这里展示的是<strong>用法</strong>，
后面的课会一层层钻进 Milvus 内部，看这三步在引擎里到底发生了什么。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">pymilvus 快速上手</span><span class="ln">create → insert → search</span></div>
  <pre><span class="kw">from</span> pymilvus <span class="kw">import</span> MilvusClient

client = MilvusClient(<span class="st">"demo.db"</span>)               <span class="cm"># Milvus Lite：本地就是一个文件</span>
client.create_collection(collection_name=<span class="st">"docs"</span>, dimension=<span class="nb">768</span>)

client.insert(collection_name=<span class="st">"docs"</span>, data=rows)      <span class="cm"># rows：768 维向量 + 文本等标量字段</span>

hits = client.search(
    collection_name=<span class="st">"docs"</span>,
    data=[query_vector],                          <span class="cm"># 一个查询向量</span>
    limit=<span class="nb">3</span>,                                      <span class="cm"># topK=3：返回最相似的 3 条</span>
    output_fields=[<span class="st">"text"</span>],                        <span class="cm"># 顺便把原文带回来</span>
)</pre>
</div>

<h2>为什么需要"数据库"，而不只是一个检索库</h2>
<p>也许你听过 FAISS、HNSWlib 这类<strong>算法库</strong>：给它一堆固定向量，它能算 ANN。那为什么还要 Milvus？因为真实业务远不止"算一次最近邻"。
一个能上生产的系统，需要把下面这些<strong>一并解决</strong>，而这恰恰是"库"与"数据库"的分界线：</p>

<div class="cols">
  <div class="col"><h4>算法库（如 FAISS）</h4><p>在<strong>内存里</strong>对一批<strong>相对静态</strong>的向量做 ANN。
  自己负责持久化、增删改、扩容、容错、并发、过滤——这些它都<strong>不管</strong>。</p></div>
  <div class="col"><h4>数据库（Milvus）</h4><p>持久化与崩溃恢复、<strong>边写边查</strong>的实时更新、<strong>标量+向量混合过滤</strong>、
  横向扩展到十亿级、高可用与一致性、多租户与权限——把检索<strong>变成一项服务</strong>。</p></div>
</div>

<p>把"数据库才有、而库没有"的能力摊开看，至少包括这些：</p>
<ul>
  <li><strong>持久化与崩溃恢复</strong>：进程挂了、机器宕了，数据不丢、能恢复。</li>
  <li><strong>实时增删改</strong>：一边持续写入/删除，一边还能查到新结果，而不是"重建一次索引才生效"。</li>
  <li><strong>混合过滤</strong>：向量相似 + 标量条件（价格、时间、标签、分区）一起约束。</li>
  <li><strong>横向扩展与高可用</strong>：加机器即可扩容，副本与故障转移保证不停服。</li>
  <li><strong>多租户与权限</strong>：一套集群服务很多业务，彼此隔离、各管各的权限。</li>
</ul>

<p>一个最能说明问题的例子：在 1 亿条商品里，要找"<strong>和这张鞋子图最像、且 价格 &lt; 500、且 当前有货</strong>"的 10 件。
纯算法库只会"按向量找最像"，没法附带"价格、库存"这些条件；Milvus 则能把<strong>标量过滤</strong>（一个布尔表达式）与<strong>向量检索</strong>
揉在一起一次做完。这类"<strong>向量 + 条件</strong>"的混合查询，恰恰是把相似检索真正落进业务的关键一步。</p>

<p>换句话说：<strong>算法库解决"怎么算得快"，数据库解决"怎么在真实世界里长期、可靠、规模化地用起来"</strong>。
Milvus 内部确实也用到了向量检索的内核库（Knowhere），但在它之上补齐了数据库该有的一切。</p>

<h2>Milvus 都用在哪：典型场景</h2>
<p>把"按相似度找"这一种能力用起来，能解决一大批看似不同、本质相通的问题：</p>
<div class="cols">
  <div class="col"><h4>检索增强生成（RAG）</h4><p>把文档切块、向量化入库；提问时检索最相关的几段喂给大模型作答，相当于<strong>给 LLM 装上"长期记忆"与"资料库"</strong>。这是当下最火的用法。</p></div>
  <div class="col"><h4>推荐与多模态搜索</h4><p>以图搜图、以文搜图、相似商品/内容推荐——把"用户喜欢的东西"向量化，再找它的邻居。</p></div>
  <div class="col"><h4>语义去重 / 聚类</h4><p>近似重复检测、海量内容聚类：靠"向量靠得够近"来判断"内容够像"。</p></div>
  <div class="col"><h4>异常检测</h4><p>正常样本在空间里聚成一团，<strong>离群点</strong>（向量远离簇）往往就是可疑对象。</p></div>
</div>

<h2>Milvus 长什么样：分布式的整体形态</h2>
<p>从最高处看，Milvus 把系统拆成三类角色，外加三个外部依赖。这里只建立<strong>轮廓</strong>，第 2 课画"全景地图"、第 3 课走"一次请求的一生"，会逐步放大每一块：</p>

<div class="flow">
  <div class="node hl"><div class="nt">SDK / 客户端</div><div class="nd">pymilvus 等</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Proxy</div><div class="nd">接入 · 校验 · 路由</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">协调器</div><div class="nd">root / data / query coord</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">工作节点</div><div class="nd">data / query / streaming node</div></div>
</div>

<p>这三类角色各司其职：<strong>Proxy</strong> 是统一入口，负责接收请求、做参数校验与鉴权，再把请求路由到该去的节点；
<strong>协调器</strong>（RootCoord / DataCoord / QueryCoord）是"大脑"，管元数据、分配任务、调度负载，但<strong>自己不亲手搬数据</strong>；
真正干活的是<strong>工作节点</strong>——DataNode 处理写入与落盘，QueryNode 加载段并执行检索，StreamingNode 承载流式日志。
"<strong>协调器管调度、节点管执行</strong>"是 Milvus 架构里反复出现的主旋律。</p>

<p>底下还垫着三块<strong>外部依赖</strong>，分别承担"记账、存货、写日志"：<strong>etcd</strong> 存元数据（有哪些集合、分片在哪台机器）；
<strong>对象存储</strong>（MinIO / S3）存真正的数据与索引文件；<strong>消息队列 / WAL</strong>（Pulsar / Kafka / 内置 woodpecker）承载写入日志，
让"写"先落到一条可重放的日志上。Milvus 的一个核心设计就是<strong>"日志即数据（log as data）"</strong>——这条线我们会在写入链路（第 15 课起）反复用到。</p>

<p><strong>为什么是 Go + C++？</strong>这是一种"<strong>各取所长</strong>"的分工：<strong>Go</strong> 写分布式<strong>控制面</strong>——协调、调度、RPC、并发管理，
开发效率高、并发模型顺手；<strong>C++</strong> 写<strong>计算密集的内核</strong>——段内检索（segcore）、索引、距离计算，追求极致性能、贴近硬件（也能调度 GPU）；
再加<strong>少量 Rust</strong>（tantivy）做全文倒排索引。配合<strong>存算分离</strong>，计算节点与存储能各自独立扩展——这正是它敢说"<strong>弹性伸缩到十亿级</strong>"的底气。</p>

<h2>三种部署形态：按规模选一种</h2>
<p>同一套理念，Milvus 提供从"一个文件"到"一个集群"的三档形态，按数据量和场景选择即可：</p>

<table class="t">
  <tr><th>形态</th><th>怎么跑</th><th>适合</th><th>规模感</th></tr>
  <tr><td><strong>Milvus Lite</strong></td><td class="mono">pip install，本地一个文件</td><td>入门、原型、笔记本上做实验</td><td>百万级以内</td></tr>
  <tr><td><strong>Standalone</strong></td><td class="mono">单机，所有组件在一个进程</td><td>中小规模、单机部署</td><td>千万级</td></tr>
  <tr><td><strong>Cluster</strong></td><td class="mono">K8s 上分布式多副本</td><td>生产、高可用、弹性伸缩</td><td>十亿级及以上</td></tr>
</table>

<p>无论哪种形态，<strong>对外的 API 与核心概念是一致的</strong>：你写的 <span class="inline">create_collection / insert / search</span> 代码不用改，
只是底层从"一个进程"长成了"一个集群"。一个常被低估的特性是<strong>"边写边查"</strong>：刚 <span class="inline">insert</span> 进去的新数据，
不必等"建好索引"就能被搜到——Milvus 靠流式日志 + 可查询的"增长段"做到数据<strong>实时新鲜</strong>，这一点我们在写入链路与查询链路会反复看到。
这正是本教程的视角——我们不教你怎么用（官方文档已经很好），而是带你<strong>钻进引擎，看它内部是怎么实现这一切的</strong>。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>向量 / embedding</strong>：AI 模型把非结构化数据编码成的一串数字；语义相近 ⇒ 向量相近。</li>
    <li><strong>ANN 相似检索</strong>：在向量空间找最近邻；用专门索引把检索从"逐个比对"加速到毫秒级。Milvus 把它当<strong>一等查询</strong>。</li>
    <li><strong>库 vs 数据库</strong>：算法库（FAISS）只算 ANN；Milvus 还补齐持久化、实时更新、混合过滤、扩展、高可用——把检索变成服务。</li>
    <li><strong>整体形态</strong>：Proxy（接入）+ 协调器 + 工作节点，外加 etcd / 对象存储 / 消息队列三大依赖；核心思想"日志即数据"。</li>
    <li><strong>三种部署</strong>：Lite（一个文件）→ Standalone（单机）→ Cluster（K8s 集群），API 与概念一致。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Milvus is an <strong>open-source, distributed vector database</strong>: it takes <strong>unstructured data</strong>
(images, text, audio), lets an AI model encode each item into a <strong>vector</strong>, and then, across huge
(billion-scale) collections of vectors, <strong>finds the most similar items, fast</strong>.
Traditional databases are great at <strong>exact matching</strong> (by id, by keyword); what Milvus is great at is a
different question — <strong>"which things are most alike in meaning?"</strong>. A database built specifically to answer
that quickly, accurately, and at scale: that is why Milvus exists.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of a traditional database as a <strong>catalog you search by call number</strong>: you need the exact id or title to
  land on one book. Milvus is more like a <strong>librarian who knows the content</strong>: you hand over one book and say
  "<strong>find me a few that <em>feel</em> most like this</strong>", and they hand back the closest ones — not by title, but by
  <strong>similarity of content</strong>. Turning "does it feel alike?" into a computable "how far apart are they?" is the
  core trick of a vector database.
</div>

<h2>What problem does it actually solve</h2>
<p>Most data around us is <strong>unstructured</strong> — text, images, audio, video. A computer can't directly tell whether
"these two sentences mean the same thing" or "these two images look alike". Modern AI's answer: use an
<strong>embedding model</strong> to encode each item into a list of floats — a <strong>vector</strong>. The key property is that
<strong>semantically similar items land close together</strong> in that space. So "find similar content" becomes a clean
mathematical problem: <strong>find the nearest neighbors in vector space</strong>.</p>

<p>The hard part is <strong>scale</strong>: with hundreds of millions of items, each hundreds or thousands of dimensions,
computing exact distances one by one is hopelessly slow. In practice we use
<strong>ANN (Approximate Nearest Neighbor)</strong> search: special index structures trade a tiny bit of accuracy to turn
retrieval from "compare against everything" into "milliseconds". Treat ANN as a <strong>first-class query</strong> and build
storage, updates, scaling and availability around it — that is a vector database, and Milvus is a leading one.</p>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>Milvus is a database whose first-class query is ANN similarity search</strong>. It is designed for
  <strong>billions</strong> of vectors, uses a <strong>storage-compute-separated, cloud-native (K8s)</strong> distributed
  architecture, scales throughput horizontally, and keeps new data queryable via <strong>real-time streaming writes</strong>.
  It is written in <strong>Go + C++</strong> (with a little Rust) and accelerated on CPU/GPU.
</div>

<div class="cols">
  <div class="col"><h4>Traditional (scalar) DB</h4><p>Queries are <strong>exact matches</strong>: <span class="inline">WHERE id = 42</span>, keyword hits.
  Data is structured rows/columns; indexes are B-Tree / hash. It asks "<strong>equal to which?</strong>"</p></div>
  <div class="col"><h4>Vector DB (Milvus)</h4><p>Queries are <strong>similarity search</strong>: given a vector, return the <strong>nearest topK</strong>.
  Data is high-dimensional vectors (+ scalar fields); indexes are ANN structures like HNSW / IVF / DiskANN. It asks "<strong>most like which?</strong>"</p></div>
</div>

<h2>Where vectors come from: embeddings turn anything into a point</h2>
<p>Vectors don't appear out of thin air — an <strong>embedding model</strong> computes them. Think of it as an
"<strong>understanding machine</strong>": feed in a piece of text or an image and it emits a fixed-length list of floats that
packs the item's "meaning" into those numbers. Trained on huge datasets, it <strong>learns to give semantically close inputs
nearby vectors</strong> — "cat" and "kitten" sit almost on top of each other, "cat" and "interest rate" land far apart. For the
first time, "semantic similarity" has a computable ruler.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Raw data</h4><p>A sentence, an image, a clip of audio… a computer can't compare "alike or not" directly.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Embedding model</h4><p class="mono">BERT / CLIP / bge…</p><p>A trained neural net that maps each item to a fixed-dimension vector.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Vector (e.g. 768-d)</h4><p>Semantically close ⇒ points close; unrelated ⇒ points far apart.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Into Milvus</h4><p>The vector + scalar fields (id, text, price, tags…) are stored and indexed, ready to be searched.</p></div></div>
</div>

<p>Two things to remember: (1) <strong>the model decides the dimension</strong> (commonly 384 / 768 / 1536), and all vectors in one
collection must share the <strong>same dimension</strong>; (2) <strong>use the same model for ingest and query</strong>, otherwise the two
sides' vectors are "not in the same space" and comparing distances is meaningless. In one line: <strong>"turn data into vectors" is the
model's job; "store, index and search huge piles of vectors fast" is Milvus's job</strong> — and this guide is about the latter.</p>

<h2>ANN: trade a little accuracy for a lot of speed</h2>
<p>With vectors in hand, the most naive search is <strong>brute force</strong>: compute the distance from the query to <strong>every</strong>
item, then sort and take the top K. Exact, but far too slow — 100M vectors of 768-d means tens of billions of multiply-adds per query,
which can't sustain high concurrency. <strong>ANN (Approximate Nearest Neighbor)</strong> flips the approach: organize vectors into an
<strong>index structure</strong> ahead of time (bucketed IVF, the navigable small-world graph HNSW, disk-oriented DiskANN…), and at query
time <strong>look at only a small set of candidates</strong>, trading a <strong>tiny recall loss</strong> for a <strong>100-1000x speedup</strong>.</p>

<table class="t">
  <tr><th>Approach</th><th>How it searches</th><th>Speed</th><th>Result</th></tr>
  <tr><td><strong>Brute force</strong></td><td class="mono">distance to every item</td><td>slow (O(N·D))</td><td>exact</td></tr>
  <tr><td><strong>ANN index</strong></td><td class="mono">only a few candidates</td><td>fast (milliseconds)</td><td>approximate (very high recall)</td></tr>
</table>

<p>"Approximate" sounds scary, but in practice <strong>recall is often 95-99%+</strong> while speed is hundreds of times faster than brute
force — for almost all applications, a great trade. Milvus ships several index types so you can balance <strong>speed, memory and
accuracy</strong> (Lesson 5 dives in).</p>

<h2>Turning "similar" into "distance": what a search looks like</h2>
<p>A vector is just <strong>a point in high-dimensional space</strong>. How alike two items are is measured by the
<strong>distance / similarity</strong> between their vectors. Milvus supports several common metrics:
<span class="inline">L2</span> (Euclidean, smaller = closer), <span class="inline">IP</span> (inner product, larger = closer),
<span class="inline">COSINE</span> (cosine similarity). One <strong>search</strong> is: given a <strong>query vector</strong>, return
the <strong>K</strong> nearest items in the collection (the <strong>topK</strong>).</p>

<div class="cellgroup">
  <div class="cg-cap"><b>One similarity search</b>: query vector <span class="mono">q</span> finds the nearest 2 of 4 stored vectors (topK=2; smaller distance = closer)</div>
  <div class="cells"><span class="lab">q</span><span class="cell hl">0.90</span><span class="cell hl">0.10</span><span class="cell hl">0.80</span></div>
  <div class="cells"><span class="lab">v1</span><span class="cell">0.88</span><span class="cell">0.12</span><span class="cell">0.79</span><span class="sep">→</span><span class="cell q">dist 0.03 ✓</span></div>
  <div class="cells"><span class="lab">v2</span><span class="cell">0.20</span><span class="cell">0.95</span><span class="cell">0.15</span><span class="sep">→</span><span class="cell dim">dist 1.42</span></div>
  <div class="cells"><span class="lab">v3</span><span class="cell">0.85</span><span class="cell">0.05</span><span class="cell">0.83</span><span class="sep">→</span><span class="cell q">dist 0.07 ✓</span></div>
  <div class="cells"><span class="lab">v4</span><span class="cell">0.10</span><span class="cell">0.30</span><span class="cell">0.90</span><span class="sep">→</span><span class="cell dim">dist 0.96</span></div>
</div>

<p>Which metric to pick depends on how your vectors are made: <strong>normalized</strong> embeddings usually use
<span class="inline">COSINE</span> or <span class="inline">IP</span> (the more aligned the direction, the more similar), while
<span class="inline">L2</span> is used when absolute position matters. Within one collection, <strong>index and search must use the same
metric</strong>, or the definition of "near" won't line up. The returned <strong>topK</strong> is sorted by distance — rank 1 is the most
similar, and so on; apps often add a "score threshold" to drop results that "rank highest but aren't actually close enough".</p>

<p>Written with the Python SDK (pymilvus), the whole thing is three steps — "create a collection → load data → search".
Note this shows <strong>usage</strong>; later lessons drill into Milvus internals to see what these three steps actually do inside the engine.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">pymilvus quickstart</span><span class="ln">create → insert → search</span></div>
  <pre><span class="kw">from</span> pymilvus <span class="kw">import</span> MilvusClient

client = MilvusClient(<span class="st">"demo.db"</span>)               <span class="cm"># Milvus Lite: just a local file</span>
client.create_collection(collection_name=<span class="st">"docs"</span>, dimension=<span class="nb">768</span>)

client.insert(collection_name=<span class="st">"docs"</span>, data=rows)      <span class="cm"># rows: 768-d vectors + scalar fields</span>

hits = client.search(
    collection_name=<span class="st">"docs"</span>,
    data=[query_vector],                          <span class="cm"># one query vector</span>
    limit=<span class="nb">3</span>,                                      <span class="cm"># topK=3: the 3 most similar</span>
    output_fields=[<span class="st">"text"</span>],                        <span class="cm"># bring the original text back too</span>
)</pre>
</div>

<h2>Why a "database", not just a search library</h2>
<p>You may have heard of <strong>algorithm libraries</strong> like FAISS or HNSWlib: hand them a pile of fixed vectors and they
compute ANN. So why Milvus? Because real workloads need far more than "compute nearest neighbors once". A production-ready
system must handle all of the following <strong>together</strong> — and that is exactly the line between a "library" and a "database":</p>

<div class="cols">
  <div class="col"><h4>Algorithm library (e.g. FAISS)</h4><p>Does ANN over a batch of <strong>relatively static</strong> vectors,
  <strong>in memory</strong>. Persistence, inserts/deletes, scaling, fault tolerance, concurrency, filtering — all <strong>your problem</strong>.</p></div>
  <div class="col"><h4>Database (Milvus)</h4><p>Persistence and crash recovery, <strong>real-time updates while querying</strong>,
  <strong>scalar + vector hybrid filtering</strong>, horizontal scale to billions, high availability and consistency, multi-tenancy
  and access control — it turns search <strong>into a service</strong>.</p></div>
</div>

<p>Laying out "what a database has and a library doesn't", at minimum:</p>
<ul>
  <li><strong>Persistence &amp; crash recovery</strong>: a process dies, a machine goes down — data isn't lost and can recover.</li>
  <li><strong>Real-time mutations</strong>: keep writing/deleting while still querying fresh results, instead of "rebuild the index to take effect".</li>
  <li><strong>Hybrid filtering</strong>: vector similarity + scalar conditions (price, time, tags, partitions) constrained together.</li>
  <li><strong>Horizontal scale &amp; HA</strong>: add machines to grow; replicas and failover keep the service up.</li>
  <li><strong>Multi-tenancy &amp; access control</strong>: one cluster serves many workloads, isolated, each with its own permissions.</li>
</ul>

<p>One example that nails it: across 100M products, find the 10 that are "<strong>most like this shoe image, AND price &lt; 500, AND
in stock</strong>". A pure algorithm library only "finds the most similar by vector" — it can't attach "price, stock" conditions; Milvus
fuses <strong>scalar filtering</strong> (a boolean expression) with <strong>vector search</strong> in one shot. This kind of "<strong>vector +
condition</strong>" hybrid query is exactly the step that takes similarity search from a demo into real business.</p>

<p>Put differently: <strong>an algorithm library solves "how to compute it fast"; a database solves "how to use it reliably,
durably and at scale in the real world"</strong>. Milvus does use a vector-search kernel library internally (Knowhere), but adds
everything a database is supposed to provide on top.</p>

<h2>Where Milvus is used: typical scenarios</h2>
<p>Put "find by similarity" to work and it solves a whole class of problems that look different but are alike underneath:</p>
<div class="cols">
  <div class="col"><h4>Retrieval-augmented generation (RAG)</h4><p>Chunk and embed documents into the DB; at question time retrieve the most relevant passages and feed them to an LLM — effectively giving the LLM <strong>long-term memory and a knowledge base</strong>. The hottest use today.</p></div>
  <div class="col"><h4>Recommendation &amp; multimodal search</h4><p>Image-to-image, text-to-image, similar-product/content recommendation — embed "what the user likes" and find its neighbors.</p></div>
  <div class="col"><h4>Semantic dedup / clustering</h4><p>Near-duplicate detection and large-scale clustering: "vectors close enough" means "content alike enough".</p></div>
  <div class="col"><h4>Anomaly detection</h4><p>Normal samples cluster together; <strong>outliers</strong> (vectors far from clusters) are often the suspicious ones.</p></div>
</div>

<h2>What Milvus looks like: the distributed shape</h2>
<p>From the very top, Milvus splits the system into three kinds of roles plus three external dependencies. Here we only sketch the
<strong>outline</strong>; Lesson 2 draws the "project map" and Lesson 3 walks "the life of a request", zooming into each block:</p>

<div class="flow">
  <div class="node hl"><div class="nt">SDK / client</div><div class="nd">pymilvus, etc.</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Proxy</div><div class="nd">entry · validate · route</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Coordinators</div><div class="nd">root / data / query coord</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Worker nodes</div><div class="nd">data / query / streaming node</div></div>
</div>

<p>The three roles divide the labor: <strong>Proxy</strong> is the single entry point — it receives requests, validates and authenticates
them, and routes each to the right node; the <strong>coordinators</strong> (RootCoord / DataCoord / QueryCoord) are the "brain" that manages
metadata, assigns tasks and schedules load, but <strong>don't move data themselves</strong>; the actual work is done by <strong>worker
nodes</strong> — DataNode handles writes and flushing, QueryNode loads segments and runs search, StreamingNode carries the streaming log.
"<strong>Coordinators schedule, nodes execute</strong>" is a recurring motif of the Milvus architecture.</p>

<p>Underneath sit three <strong>external dependencies</strong> doing "bookkeeping, storage, logging": <strong>etcd</strong> holds metadata
(which collections exist, which shard is on which machine); <strong>object storage</strong> (MinIO / S3) holds the actual data and
index files; a <strong>message queue / WAL</strong> (Pulsar / Kafka / the built-in woodpecker) carries the write log, so a "write" first
lands on a replayable log. A core Milvus design is <strong>"log as data"</strong> — a thread we'll pull on repeatedly in the write path
(from Lesson 15).</p>

<p><strong>Why Go + C++?</strong> It's a "<strong>best tool for each job</strong>" split: <strong>Go</strong> writes the distributed
<strong>control plane</strong> — coordination, scheduling, RPC, concurrency — where developer velocity and a friendly concurrency model
matter; <strong>C++</strong> writes the <strong>compute-heavy kernels</strong> — in-segment search (segcore), indexing, distance math — chasing
peak performance close to the hardware (and able to drive GPUs); plus <strong>a little Rust</strong> (tantivy) for the full-text inverted
index. Combined with <strong>storage-compute separation</strong>, compute nodes and storage scale independently — which is what lets Milvus
claim "<strong>elastic scaling to billions</strong>".</p>

<h2>Three deployment shapes: pick one by scale</h2>
<p>Same ideas, three sizes — from "one file" to "one cluster" — chosen by data volume and scenario:</p>

<table class="t">
  <tr><th>Shape</th><th>How it runs</th><th>Good for</th><th>Scale</th></tr>
  <tr><td><strong>Milvus Lite</strong></td><td class="mono">pip install, one local file</td><td>learning, prototypes, laptop experiments</td><td>up to ~millions</td></tr>
  <tr><td><strong>Standalone</strong></td><td class="mono">single machine, all components in one process</td><td>small/medium, single-host deploy</td><td>tens of millions</td></tr>
  <tr><td><strong>Cluster</strong></td><td class="mono">distributed, replicated, on K8s</td><td>production, HA, elastic scaling</td><td>billions and beyond</td></tr>
</table>

<p>Whichever shape you pick, the <strong>external API and core concepts are the same</strong>: your
<span class="inline">create_collection / insert / search</span> code doesn't change — the underside just grows from "one process"
into "one cluster". An often-underrated feature is <strong>"query while you write"</strong>: data you just <span class="inline">insert</span>
becomes searchable without waiting for an index to be built — Milvus keeps data <strong>fresh in real time</strong> via a streaming log plus
queryable "growing segments", something we'll see again in the write and query paths. That is the lens of this guide: we don't teach
<em>how to use</em> Milvus (the official docs do that well), we take you <strong>inside the engine to see how it implements all of this</strong>.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Vector / embedding</strong>: the list of numbers an AI model encodes data into; semantically close ⇒ vectors close.</li>
    <li><strong>ANN similarity search</strong>: find nearest neighbors in vector space; special indexes make it milliseconds instead of brute force. Milvus treats it as a <strong>first-class query</strong>.</li>
    <li><strong>Library vs database</strong>: a library (FAISS) just computes ANN; Milvus adds persistence, real-time updates, hybrid filtering, scaling, HA — search as a service.</li>
    <li><strong>Overall shape</strong>: Proxy (entry) + coordinators + worker nodes, plus etcd / object storage / message queue; the core idea is "log as data".</li>
    <li><strong>Three deployments</strong>: Lite (one file) → Standalone (single host) → Cluster (K8s), with the same API and concepts.</li>
  </ul>
</div>
""",
}


LESSON_02 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课我们站在山顶看清了"Milvus 是什么"。这一课要做的是一张<strong>全景地图</strong>：把代码仓库里几十个目录、三种编程语言、五六个运行时组件、三类外部依赖，
一次性<strong>放到同一张图上</strong>。地图的价值不在记住每条街，而在于——之后无论我们钻进哪一课（写入、查询、索引、一致性……），
你都能立刻指着这张图说"<strong>哦，它在这里</strong>"。
</p>

<div class="card analogy">
  <div class="tag">🗺️ 生活类比</div>
  把 Milvus 想成一座<strong>分工明确的城市</strong>：<strong>市民服务大厅（Proxy）</strong>是唯一的对外窗口，所有请求先到这里登记、核验、分流；
  <strong>市政府（MixCoord）</strong>不亲自搬砖，只管规划与调度——谁建在哪、谁负责哪一片；<strong>各施工队与仓库管理员（工作节点）</strong>才真正动手干活；
  地底下还铺着<strong>水电管网（etcd / 对象存储 / 消息队列）</strong>。你不必记住每个人的名字，只要知道"<strong>办事去大厅、决策找市府、干活找工程队</strong>"，就永远不会迷路。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  Milvus 是一套<strong>三语言分工、存算分离</strong>的分布式向量库：逻辑上有 Root/Data/Query 多种角色，物理上协调器三合一为 <strong>MixCoord</strong>；记住"<strong>协调器管调度、节点管执行</strong>"，你就拿到了这套系统的全局地图。
</div>

<h2>三种语言，三种活</h2>
<p>Milvus 的源码乍看庞杂，但有一条最省力的切入线索：<strong>它用三种语言，各干一种最擅长的活</strong>。看懂这条分工，半张地图就已经在脑子里了：</p>

<div class="cols">
  <div class="col"><h4>Go · 分布式控制面</h4><p>占 <span class="inline">internal/</span> 的绝大多数。负责<strong>协调、调度、RPC、元数据、并发管理</strong>——也就是"<strong>把一群机器组织起来</strong>"这件事。Go 的并发模型与开发效率，正好适合写控制面。</p></div>
  <div class="col"><h4>C++ · 计算内核</h4><p>集中在 <span class="inline">internal/core/</span>。负责<strong>段内检索、索引、距离计算、表达式求值</strong>这些<strong>计算密集</strong>的脏活累活，贴近硬件、追求极致性能（也能驱动 GPU）。</p></div>
</div>

<p>第三种语言是<strong>少量 Rust</strong>：它只负责一块很专的领域——<strong>全文倒排索引</strong>，藏在 <span class="inline">internal/core/thirdparty/tantivy</span> 里（tantivy 是一个 Rust 写的全文检索库）。
所以一句话记牢分工：<strong>Go 管"把机器们协调好"，C++ 管"把一段数据搜得飞快"，Rust 管"全文检索那一小块"</strong>。
C++ 内核里又细分成几个子模块——<span class="mono">segcore</span>（段内检索引擎）、<span class="mono">index</span>（索引构建与加载）、<span class="mono">query</span>（查询执行）、<span class="mono">exec</span>（执行算子）、<span class="mono">expr</span>（标量表达式）——
这些名字会在后面的课里反复出现，现在混个脸熟即可。</p>

<p>举个最直观的例子感受这套分工：当你发起<strong>一次 search</strong>，请求会<strong>同时穿过这三种语言</strong>——先由 <strong>Go</strong> 写的 Proxy 接住、校验、把请求路由到对的 QueryNode；
QueryNode（也是 Go）找出该搜哪些段后，把"段内的相似度计算"这一步<strong>下沉给 C++ 的 segcore</strong> 去飞快地算；如果你的查询里还带了<strong>全文检索</strong>条件，
那一小段就轮到 <strong>Rust 的 tantivy</strong> 出场。三种语言像接力赛一样把一次请求跑完——<strong>Go 负责"组织流程"，C++ 负责"算得快"，Rust 负责"全文那一棒"</strong>。
看懂这一点，你就明白了为什么 Milvus 要"混血"：不是炫技，而是让每段代码都跑在它最擅长的语言上。</p>

<h2>把镜头拉近：search 在 Go 与 C++ 之间怎么交接</h2>
<p>上一段说三种语言像接力，但那根"棒"<strong>到底在哪一行代码交接</strong>？以 search 为例，把镜头再拉近一档：当 QueryNode 走到"要在某个段里<strong>真正算距离</strong>"这一步时，调用的是 Go 侧 <span class="mono">internal/querynodev2/segments/segment.go</span> 里的 <span class="mono">LocalSegment.Search</span>。这个方法<strong>自己并不算距离</strong>——它做的是把请求<strong>通过 cgo（Go 调 C 的桥）递进 C++</strong>。代码里那个名叫 <span class="mono">cgoSearch</span> 的计时器，量的就是"<strong>这趟在 C++ 里待了多久</strong>"，它的存在本身就标出了语言边界的位置。</p>

<div class="flow">
  <div class="node hl"><div class="nt">QueryNode（Go）</div><div class="nd">LocalSegment.Search · 圈定段</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">cgo 边界</div><div class="nd">cgoSearch 计时器</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">segcore（C++）</div><div class="nd">AsyncSearch · 段内算 topK</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">回到 Go</div><div class="nd">QueryNode 归并各段 topK</div></div>
</div>

<p>越过 cgo 这道门，就进了 C++ 的地盘：<span class="mono">internal/core/src/segcore/segment_c.cpp</span> 里的 <span class="mono">AsyncSearch</span> 接住请求，把它丢进一个专门的搜索线程池（<span class="mono">getSearchCPUExecutor</span>）<strong>异步</strong>执行，并开一个名为 <span class="mono">SegCoreSearch</span> 的链路追踪 span。真正的近邻计算就发生在这里；算完，<strong>每段的 topK 再沿原路回传给 Go</strong>，由 QueryNode 归并。这趟来回让你看清一件事：<strong>Go 与 C++ 的边界不是抽象口号，而是一行具体的 cgo 调用</strong>——Go 端负责"决定搜哪些段、收集与归并结果"，C++ 端负责"把一段数据搜到极致快"，cgo 就是它们之间那根结实的接力棒。后面查询链路的课会沿着这根棒一路钻进 segcore，这里你只要记住"<strong>棒在 <span class="mono">LocalSegment.Search</span> 这一行交出去</strong>"即可。</p>

<p>顺带点一个工程上的讲究：跨 cgo 这道门<strong>本身是有成本的</strong>——要在 Go 的协程调度与 C++ 的线程之间来回切换。所以 Milvus 不会"一行一调"，而是<strong>以"一个段、一次搜索"为粒度成批跨越</strong>，把尽量多的计算攒在 C++ 一侧一次做完。这也解释了 segcore 为什么要把搜索丢进自己的<strong>线程池异步执行</strong>：让 C++ 安心吃满 CPU 做密集计算，而 Go 这边的协程不必干等、可以腾出手去伺候别的请求。<strong>边界划在哪、怎么跨</strong>，往往决定一套"混血"系统跑得顺不顺——这正是 Milvus 宁愿把"算得重的那一整段"成块下沉给 C++ 的深层原因。</p>

<h2>运行时有哪些组件：先纠正一个常见误解</h2>
<p>很多旧资料会画出"<strong>三个独立的协调器</strong>"——RootCoord、DataCoord、QueryCoord 各是一个进程。<strong>这在今天的 Milvus 里已经不准确了。</strong>
当前版本把这三个协调角色<strong>合并进了同一个进程 <span class="mono">MixCoord</span></strong>。也就是说：三个协调"角色"在代码里仍然存在（分别是 <span class="inline">internal/rootcoord</span>、
<span class="inline">internal/datacoord</span>、<span class="inline">internal/querycoordv2</span> 三个模块），但它们<strong>被打包成一个 MixCoord 一起部署</strong>，不再是三个独立进程。</p>

<p>这是一个<strong>"逻辑 vs 物理"</strong>的经典区分，务必分清：在<strong>逻辑上</strong>，元数据管理（Root）、写入与段管理（Data）、查询负载调度（Query）仍是三件不同的事；
但在<strong>物理上</strong>，它们如今住在同一个进程里。证据就在代码里——<span class="inline">internal/types/types.go</span> 中的 <span class="mono">MixCoord</span> 接口，
直接把 <span class="mono">RootCoordServer</span>、<span class="mono">QueryCoordServer</span>、<span class="mono">DataCoordServer</span> 三个服务接口<strong>嵌在了一起</strong>（本课末尾会贴出这段代码）。
所以今天 Milvus 的<strong>运行时组件</strong>是这六个：</p>

<table class="t">
  <tr><th>组件</th><th>语言</th><th>职责（一句话）</th><th>internal 包</th></tr>
  <tr><td><strong>Proxy</strong></td><td>Go</td><td>对外唯一入口：校验、鉴权、分配时间戳、路由、跨分片归并</td><td class="mono">proxy</td></tr>
  <tr><td><strong>MixCoord</strong></td><td>Go</td><td>三合一协调器：元数据 + 段管理 + 查询调度（含 streamingcoord）</td><td class="mono">coordinator · rootcoord · datacoord · querycoordv2</td></tr>
  <tr><td><strong>QueryNode</strong></td><td>Go + C++</td><td>加载段、执行检索；段内搜索下沉到 C++ segcore</td><td class="mono">querynodev2 · core</td></tr>
  <tr><td><strong>DataNode</strong></td><td>Go</td><td>消费日志、攒"增长段"、刷盘成 binlog；也承担索引构建的执行</td><td class="mono">datanode · flushcommon</td></tr>
  <tr><td><strong>StreamingNode</strong></td><td>Go</td><td>承载流式 WAL：写入先落到这条可重放的日志上</td><td class="mono">streamingnode · streamingcoord</td></tr>
  <tr><td><strong>CDC</strong></td><td>Go</td><td>变更数据捕获：把写入变更复制到下游 / 做跨集群同步</td><td class="mono">cdc</td></tr>
</table>

<p>两个容易踩的坑顺便点破：①<strong>没有单独的 indexnode</strong>——索引构建是由 DataCoord 调度、交给一个 datanode 工作进程去跑的，并不存在一个叫"索引节点"的独立组件；
②<strong>Standalone 与 Cluster 跑的是同一套组件</strong>，区别只在"住在几个进程里"。</p>

<h2>逻辑一张图，物理两种形态</h2>
<p>同样这六个组件，<strong>Standalone</strong>（单机）把它们<strong>塞进一个进程</strong>，省心、适合中小规模；<strong>Cluster</strong>（集群）则把每个组件<strong>拆成独立的 K8s Pod</strong>，
各自按需扩缩容、互不拖累。注意：<strong>对你写的代码而言，两者毫无区别</strong>——同样的 <span class="inline">create_collection / insert / search</span>，底层从"一个进程"长成"一个集群"，API 与概念完全一致。</p>

<div class="cols">
  <div class="col"><h4>Standalone（单机）</h4><p>MixCoord + Proxy + 三种 Node + CDC <strong>全在一个进程</strong>里；依赖（etcd / 对象存储 / MQ）可内嵌或外接。<strong>部署简单</strong>，适合中小规模与单机生产。</p></div>
  <div class="col"><h4>Cluster（集群）</h4><p>每个组件是<strong>独立的 Pod</strong>，QueryNode / DataNode 可各自扩到多副本。<strong>弹性、高可用</strong>，面向十亿级生产。逻辑角色不变，只是"分家"了。</p></div>
</div>

<h2>一条贯穿全书的主线：控制面 vs 数据面</h2>
<p>如果说"三种语言"是横向的切法，那么<strong>"控制面 vs 数据面"</strong>就是纵向的切法——这是理解 Milvus 最重要的一根线，几乎每一课都会回到它。
所谓<strong>控制面（control plane）</strong>，管的是"<strong>谁该做什么</strong>"：集合的结构、分片落在哪台机器、段该不该刷盘、查询该路由到哪个副本——
这些<strong>决策与元数据</strong>都归 MixCoord 这个大脑。而<strong>数据面（data plane）</strong>管的是"<strong>真正把数据搬动、计算出来</strong>"：
写入的字节、刷盘的 binlog、检索时一条条算出来的距离——这些<strong>重活</strong>全在工作节点和 C++ 内核里发生。</p>

<div class="cols">
  <div class="col"><h4>控制面（control plane）</h4><p>管"<strong>谁该做什么</strong>"：结构、分片分配、刷盘决策、查询路由——决策与元数据归 <strong>MixCoord/协调器</strong>。要的是<strong>正确、一致</strong>，走 etcd 强一致，宁可慢一点。</p></div>
  <div class="col"><h4>数据面（data plane）</h4><p>管"<strong>真正搬动与计算</strong>"：写字节、刷 binlog、逐条算距离——重活在 <strong>DataNode/QueryNode + C++ 内核</strong>。要的是<strong>快、可并行、能水平扩展</strong>，机器不够就加。</p></div>
</div>

<p>为什么要这么分？因为<strong>这两件事的脾气完全不同</strong>。控制面要的是"<strong>正确、一致、别出错</strong>"——元数据错一点，整个集群就乱套，所以它宁可慢一点、走 etcd 做强一致；
数据面要的是"<strong>快、能并行、能水平扩展</strong>"——它可以容忍"近似"、可以多副本并发，机器不够就加机器。<strong>把这两种诉求拆开</strong>，
各自用最合适的技术去满足，正是分布式系统反复验证过的智慧。所以你会看到一句反复出现的口诀：<strong>"协调器管调度、节点管执行"</strong>——
MixCoord 只发号施令、绝不亲手搬一个字节；DataNode / QueryNode 闷头干活、不操心全局怎么编排。</p>

<p>这根主线还顺手解释了"<strong>为什么要存算分离</strong>"：当数据面的节点<strong>不自己保存长期状态</strong>（状态都托管给 etcd 和对象存储）时，它们就变成了"<strong>用完即弃</strong>"的算力——
查询忙了就多拉几个 QueryNode、写入忙了就多拉几个 DataNode，闲了再缩回去，<strong>而数据一个字节都不会丢</strong>。计算与存储能各自独立伸缩，
这正是 Milvus 敢承诺"<strong>弹性扩展到十亿级</strong>"的工程根基。记住这根线，后面的写入链路、查询链路、一致性，都只是它在不同场景下的展开。</p>

<h2>仓库长什么样：顶层目录速记</h2>
<p>把 git 仓库的顶层目录走一遍，你就有了"<strong>去哪找代码</strong>"的索引。它们大致按"<strong>入口 → 核心逻辑 → 共享库 → 周边</strong>"排列：</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4><span class="mono">cmd/</span> · 程序入口</h4><p>每个组件怎么启动都在这里：<span class="mono">cmd/components/</span>（mix_coord、proxy、query_node…）与 <span class="mono">cmd/roles/roles.go</span>（决定本进程跑哪些角色）。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4><span class="mono">internal/</span> · 核心逻辑</h4><p>系统的"<strong>主干</strong>"：proxy、rootcoord、datacoord、querycoordv2、querynodev2、datanode、streamingnode、coordinator(mixcoord)、core(C++)、storage、metastore、kv、distributed(gRPC 服务)、types(接口)、tso…</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4><span class="mono">pkg/</span> · 共享库</h4><p>跨组件复用的工具：日志、配置(paramtable)、proto、工具函数。注意它<strong>自带独立的 go.mod</strong>（模块名 <span class="mono">github.com/milvus-io/milvus/pkg/v3</span>）。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4><span class="mono">client/</span> · Go SDK</h4><p>官方 Go 客户端 <span class="mono">milvusclient</span>（也有独立 go.mod）。Python 的 pymilvus 在另一个仓库。</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>周边目录</h4><p><span class="mono">configs/</span>（<span class="mono">milvus.yaml</span> 配置）、<span class="mono">deployments/</span>（部署）、<span class="mono">scripts/</span>（脚本）、<span class="mono">tests/</span>（测试）、<span class="mono">docs/</span>（文档）。</p></div></div>
</div>

<h2>三块外部依赖：记账、存货、写日志</h2>
<p>Milvus 自己不重复造轮子，而是把三件"基础设施级"的脏活外包给成熟系统。这也是<strong>存算分离</strong>能成立的前提：</p>
<ul>
  <li><strong>etcd · 记账</strong>：存<strong>元数据</strong>——有哪些集合、分片在哪台机器、谁是谁的副本。小而关键，是集群的"户口本"。</li>
  <li><strong>对象存储（MinIO / S3）· 存货</strong>：存<strong>真正的数据与索引文件</strong>——刷盘后的 binlog、建好的索引。便宜、海量、持久。</li>
  <li><strong>消息队列 / WAL（Pulsar / Kafka / 内置 woodpecker）· 写日志</strong>：承载<strong>写入日志</strong>，让"写"先落到一条<strong>可重放</strong>的日志上。这正是 Milvus "<strong>日志即数据（log as data）</strong>"的根基（第 15 课起细讲）。</li>
</ul>

<p>把这三块垫在底下，计算节点就变得"<strong>无状态</strong>"了——挂了重启、按需扩容都不丢数据，因为真正的状态都在 etcd 与对象存储里。<strong>这就是存算分离能弹性伸缩到十亿级的底气。</strong></p>

<p>这里也顺手说清一个常被问到的点：<strong>这三块依赖不是"可有可无的配角"，而是 Milvus 架构的一部分</strong>。它们的选择是<strong>可插拔</strong>的——消息队列既可以用 Pulsar / Kafka 这类成熟中间件，
也可以用 Milvus <strong>内置的 woodpecker</strong>（省去额外部署一套 MQ 的麻烦）；对象存储既可以是云上的 S3，也可以是本地自建的 MinIO。Milvus 通过一层抽象把这些差异挡在外面，
让上层逻辑无需关心"日志到底落在哪、文件到底存在哪"。<strong>这种"把基础设施抽象掉"的设计，正是它能在云上、私有化、单机之间无缝切换的原因。</strong></p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/types/types.go</span><span class="ln">type MixCoord interface</span></div>
  <pre><span class="cm">// MixCoord 把三个协调角色的服务接口"嵌"在一起 —— 这就是"三合一"的代码铁证</span>
<span class="kw">type</span> MixCoord <span class="kw">interface</span> {
    Component
    rootcoordpb.RootCoordServer   <span class="cm">// 元数据 / DDL（Root）</span>
    querypb.QueryCoordServer      <span class="cm">// 查询负载调度（Query）</span>
    datapb.DataCoordServer        <span class="cm">// 段管理 / 写入协调（Data）</span>
    <span class="cm">// …三者如今同住一个进程，对外仍是三套逻辑接口</span>
}</pre>
</div>

<h2>四组导航模型：把任何一课都钉到地图上</h2>
<p>最后，给你一张<strong>分四组</strong>的"导航坐标"。今后每学一课，先问自己"它属于哪一组"，再去对应的代码目录里找——这张分组图会一直陪着你：</p>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">顶层</span><span class="name">SDK / API</span></div><div class="ld">pymilvus / Go <span class="mono">milvusclient</span> —— 你写的 create / insert / search 从这里出发。</div></div>
  <div class="layer l-app"><div class="lh"><span class="badge">① 接入层</span><span class="name">Proxy</span></div><div class="ld">唯一对外窗口：校验、鉴权、分配时间戳、路由、跨分片归并结果。</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">② 协调层</span><span class="name">MixCoord</span></div><div class="ld">三合一大脑：管元数据、管段、调度查询负载——只决策、不搬数据。</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">③ 工作节点</span><span class="name">Query / Data / Streaming Node</span></div><div class="ld">真正干活：QueryNode 搜、DataNode 写与刷盘、StreamingNode 承载 WAL。</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">内核</span><span class="name">C++ core (segcore / index / query)</span></div><div class="ld">垫在工作节点之下的计算内核：段内检索与索引的极速实现。</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">④ 存储与依赖</span><span class="name">etcd · 对象存储 · MQ/WAL</span></div><div class="ld">记账（元数据）、存货（数据与索引）、写日志（可重放的写入流）。</div></div>
</div>

<p>带着这张地图，下一课我们就<strong>让它动起来</strong>：跟着一条 insert 和一条 search，走一遍"<strong>一次请求的一生</strong>"，看请求是怎么在这四组之间流动的。</p>

<h2>怎么用这张地图：给你的学习路线</h2>
<p>地图画好了，最后教你<strong>怎么用</strong>它。本教程后面的每一部分，其实都是在<strong>放大地图上的某一块</strong>——你完全可以把它当作"导览路线"：</p>
<ul>
  <li><strong>遇到"写入"相关的话题</strong>（insert、WAL、刷盘、段、压缩）→ 看的是 ② 协调层的 <strong>DataCoord 角色</strong> + ③ 工作节点里的 <strong>DataNode / StreamingNode</strong>，对应 <span class="mono">internal/datanode</span>、<span class="mono">internal/streamingnode</span>、<span class="mono">internal/flushcommon</span>。这条线在<strong>第 15 课</strong>起的写入链路里展开。</li>
  <li><strong>遇到"查询"相关的话题</strong>（search、过滤、归并、一致性）→ 看的是 ① 接入层 <strong>Proxy</strong> + ③ 工作节点里的 <strong>QueryNode</strong> + 内核 <strong>C++ segcore</strong>，对应 <span class="mono">internal/proxy</span>、<span class="mono">internal/querynodev2</span>、<span class="mono">internal/core/src/segcore</span>。这条线在<strong>第 25 课</strong>起展开。</li>
  <li><strong>遇到"索引"相关的话题</strong>（HNSW、IVF、DiskANN、量化）→ 看的是内核 <strong>C++ index</strong> + ② 协调层 <strong>DataCoord 的索引调度</strong>，对应 <span class="mono">internal/core/src/index</span> 与 <span class="mono">internal/datacoord</span> 里的 index 相关文件。</li>
  <li><strong>遇到"元数据 / 集合 / 权限"相关的话题</strong> → 看的是 ② 协调层的 <strong>RootCoord 角色</strong> 与 etcd，对应 <span class="mono">internal/rootcoord</span>、<span class="mono">internal/metastore</span>。</li>
</ul>

<p>换句话说：<strong>每当你不知道"这件事归谁管"，就回到这四组上对号入座</strong>。组件名、目录名、语言、职责，这四样信息你只要建立起对应关系，
就拿到了在这套庞大代码库里<strong>自由导航</strong>的能力——而这，正是"全景地图"这一课最想留给你的东西。一张地图记不住每条街没关系，
重要的是<strong>你永远知道自己站在哪、下一步该往哪走</strong>。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>三语言分工</strong>：Go（控制面，<span class="mono">internal/</span>）+ C++（计算内核，<span class="mono">internal/core/</span>：segcore/index/query/exec/expr）+ 少量 Rust（全文 tantivy）。</li>
    <li><strong>MixCoord 是关键纠错点</strong>：Root/Data/Query 三个协调<strong>角色</strong>仍在，但已合并为<strong>一个 MixCoord 进程</strong>部署——逻辑三件事、物理一个进程。</li>
    <li><strong>六个运行时组件</strong>：MixCoord、Proxy、QueryNode、DataNode、StreamingNode、CDC；<strong>没有单独 indexnode</strong>（索引由 DataCoord 调度、datanode 执行）。</li>
    <li><strong>两种形态</strong>：Standalone 一个进程、Cluster 多个 Pod，<strong>同套组件、同套 API</strong>。</li>
    <li><strong>仓库索引</strong>：<span class="mono">cmd/</span> 入口 · <span class="mono">internal/</span> 核心 · <span class="mono">pkg/</span> 共享库 · <span class="mono">client/</span> SDK；外部依赖 etcd / 对象存储 / MQ 支撑存算分离。</li>
    <li><strong>四组导航</strong>：① 接入 Proxy ② 协调 MixCoord ③ 工作节点 ④ 存储与依赖，外加底层 C++ 内核与顶层 SDK。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson we stood on the summit and saw "what Milvus is". This lesson draws a <strong>map of the whole project</strong>:
the dozens of directories, three programming languages, half a dozen runtime components, and three external dependencies —
all placed on <strong>one picture</strong>. A map's value isn't memorizing every street; it's that whenever we later dive into a
lesson (writes, queries, indexing, consistency…), you can point at this map and say "<strong>ah, it lives here</strong>".
</p>

<div class="card analogy">
  <div class="tag">🗺️ Analogy</div>
  Think of Milvus as a <strong>city with a clear division of labor</strong>: the <strong>citizen service hall (Proxy)</strong> is the one public
  window — every request first checks in, gets validated, and is routed there; the <strong>city government (MixCoord)</strong> doesn't lay bricks,
  it only plans and schedules — who is built where, who owns which district; the <strong>crews and warehouse keepers (worker nodes)</strong> do
  the actual work; and underground run the <strong>utilities (etcd / object storage / message queue)</strong>. You needn't memorize every name —
  just "<strong>errands go to the hall, decisions to the government, work to the crews</strong>" and you'll never get lost.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  Milvus is a distributed vector store built on <strong>three-language division of labor and storage-compute separation</strong>: logically there are Root/Data/Query roles, physically the coordinators fuse into one <strong>MixCoord</strong>; remember "<strong>coordinators schedule, nodes execute</strong>" and you hold the system's global map.
</div>

<h2>Three languages, three jobs</h2>
<p>The source looks sprawling, but there's one effortless way in: <strong>Milvus uses three languages, each doing what it's best at</strong>.
Grasp that split and half the map is already in your head:</p>

<div class="cols">
  <div class="col"><h4>Go · distributed control plane</h4><p>Most of <span class="inline">internal/</span>. Handles <strong>coordination, scheduling, RPC, metadata, concurrency</strong> — i.e. "<strong>organizing a fleet of machines</strong>". Go's concurrency model and developer velocity fit a control plane.</p></div>
  <div class="col"><h4>C++ · compute kernels</h4><p>Concentrated in <span class="inline">internal/core/</span>. Handles the <strong>compute-heavy</strong> grunt work — in-segment search, indexing, distance math, expression eval — close to the hardware, chasing peak speed (and able to drive GPUs).</p></div>
</div>

<p>The third language is <strong>a little Rust</strong>: it owns one very specialized area — the <strong>full-text inverted index</strong> — tucked in
<span class="inline">internal/core/thirdparty/tantivy</span> (tantivy is a Rust full-text search library). So, in one line: <strong>Go "coordinates the
machines", C++ "searches one piece of data blazingly fast", Rust "owns the small full-text slice"</strong>. The C++ kernel further splits into a few
submodules — <span class="mono">segcore</span> (in-segment search), <span class="mono">index</span> (build/load indexes), <span class="mono">query</span>
(query execution), <span class="mono">exec</span> (execution operators), <span class="mono">expr</span> (scalar expressions) — names that recur in later
lessons; just get acquainted for now.</p>

<p>A vivid example of this division: when you issue <strong>one search</strong>, the request <strong>passes through all three languages at once</strong> — first the
<strong>Go</strong>-written Proxy catches it, validates it, and routes it to the right QueryNode; the QueryNode (also Go), after figuring out which segments to hit,
<strong>sinks the "in-segment similarity computation" down to C++ segcore</strong> to crunch blazingly fast; and if your query carries a <strong>full-text</strong> condition,
that small slice goes to <strong>Rust's tantivy</strong>. The three languages run a request like a relay — <strong>Go "organizes the flow", C++ "computes fast", Rust "runs the
full-text leg"</strong>. Grasp this and you see why Milvus is "multilingual": not for show, but so each piece of code runs in the language it's best at.</p>

<h2>Zooming in: how a search hands off between Go and C++</h2>
<p>We said the three languages run a relay, but <strong>which line of code actually passes the baton</strong>? Take search and zoom in one more notch: when a QueryNode reaches the step "<strong>actually compute distances inside a segment</strong>", it calls <span class="mono">LocalSegment.Search</span> in <span class="mono">internal/querynodev2/segments/segment.go</span> on the Go side. That method <strong>doesn't compute distances itself</strong> — it hands the request <strong>across cgo (Go's bridge to C) into C++</strong>. The timer named <span class="mono">cgoSearch</span> in the code measures "<strong>how long this trip spent inside C++</strong>", and its very existence marks where the language boundary sits.</p>

<div class="flow">
  <div class="node hl"><div class="nt">QueryNode (Go)</div><div class="nd">LocalSegment.Search · pick segments</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">cgo boundary</div><div class="nd">cgoSearch timer</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">segcore (C++)</div><div class="nd">AsyncSearch · per-segment topK</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">back to Go</div><div class="nd">QueryNode reduces per-segment topK</div></div>
</div>

<p>Cross the cgo door and you're on C++ turf: <span class="mono">AsyncSearch</span> in <span class="mono">internal/core/src/segcore/segment_c.cpp</span> catches the request, drops it onto a dedicated search thread pool (<span class="mono">getSearchCPUExecutor</span>) to run <strong>asynchronously</strong>, and opens a trace span named <span class="mono">SegCoreSearch</span>. The real neighbor computation happens here; once done, <strong>each segment's topK travels back to Go the same way</strong> and the QueryNode reduces it. This round trip makes one thing clear: <strong>the Go/C++ boundary is not an abstract slogan but a concrete cgo call</strong> — Go decides "which segments to search and how to collect/reduce results", C++ "searches one piece of data blazingly fast", and cgo is the sturdy baton between them. Later query-path lessons follow that baton deep into segcore; for now just remember "<strong>the baton is handed off at <span class="mono">LocalSegment.Search</span></strong>".</p>

<p>A worthwhile engineering note: crossing the cgo door <strong>has a cost of its own</strong> — it switches back and forth between Go's goroutine scheduler and C++'s threads. So Milvus doesn't "call once per row"; it <strong>crosses in batches at the granularity of "one segment, one search"</strong>, piling as much computation as possible onto the C++ side to do in one go. That also explains why segcore runs the search <strong>asynchronously on its own thread pool</strong>: let C++ saturate the CPU on dense computation while Go's goroutines don't idle and can go serve other requests. <strong>Where the boundary is drawn and how it's crossed</strong> often decides whether a "multilingual" system runs smoothly — the deep reason Milvus would rather sink "the whole heavy-compute slice" into C++ in chunks.</p>

<h2>The runtime components: first, fix a common misconception</h2>
<p>Lots of older material draws "<strong>three separate coordinators</strong>" — RootCoord, DataCoord, QueryCoord each a process. <strong>That is no longer
accurate in today's Milvus.</strong> The current version <strong>merges these three coordinator roles into one process, <span class="mono">MixCoord</span></strong>.
The three coordinator "roles" still exist in code (modules <span class="inline">internal/rootcoord</span>, <span class="inline">internal/datacoord</span>,
<span class="inline">internal/querycoordv2</span>), but they are <strong>packaged into a single MixCoord and deployed together</strong> — no longer three
independent processes.</p>

<p>This is a classic <strong>"logical vs physical"</strong> distinction — keep them straight: <strong>logically</strong>, metadata management (Root), writes
&amp; segment management (Data), and query-load scheduling (Query) are still three different things; but <strong>physically</strong> they now live in one
process. The proof is in the code — the <span class="mono">MixCoord</span> interface in <span class="inline">internal/types/types.go</span> <strong>embeds</strong>
the three service interfaces <span class="mono">RootCoordServer</span>, <span class="mono">QueryCoordServer</span>, <span class="mono">DataCoordServer</span> together
(snippet at the end of this lesson). So today's <strong>runtime components</strong> are these six:</p>

<table class="t">
  <tr><th>Component</th><th>Language</th><th>Responsibility (one line)</th><th>internal package</th></tr>
  <tr><td><strong>Proxy</strong></td><td>Go</td><td>The one public entry: validate, auth, assign timestamp, route, reduce across shards</td><td class="mono">proxy</td></tr>
  <tr><td><strong>MixCoord</strong></td><td>Go</td><td>Three-in-one coordinator: metadata + segment mgmt + query scheduling (incl. streamingcoord)</td><td class="mono">coordinator · rootcoord · datacoord · querycoordv2</td></tr>
  <tr><td><strong>QueryNode</strong></td><td>Go + C++</td><td>Loads segments, runs search; in-segment search sinks into C++ segcore</td><td class="mono">querynodev2 · core</td></tr>
  <tr><td><strong>DataNode</strong></td><td>Go</td><td>Consumes the log, builds "growing segments", flushes to binlogs; also runs index builds</td><td class="mono">datanode · flushcommon</td></tr>
  <tr><td><strong>StreamingNode</strong></td><td>Go</td><td>Carries the streaming WAL: a write first lands on this replayable log</td><td class="mono">streamingnode · streamingcoord</td></tr>
  <tr><td><strong>CDC</strong></td><td>Go</td><td>Change Data Capture: replicate write changes downstream / cross-cluster sync</td><td class="mono">cdc</td></tr>
</table>

<p>Two easy traps, dispelled: (1) <strong>there is no separate indexnode</strong> — index building is scheduled by DataCoord and run by a datanode worker;
no component called "index node" exists; (2) <strong>Standalone and Cluster run the same set of components</strong> — the only difference is "how many
processes they live in".</p>

<h2>One logical picture, two physical shapes</h2>
<p>Those same six components: <strong>Standalone</strong> (single host) <strong>packs them into one process</strong> — simple, good for small/medium scale;
<strong>Cluster</strong> <strong>splits each into its own K8s Pod</strong> that scales independently. Note: <strong>to your code, the two are identical</strong> — the same
<span class="inline">create_collection / insert / search</span>; the underside just grows from "one process" to "one cluster", with the same API and concepts.</p>

<div class="cols">
  <div class="col"><h4>Standalone (single host)</h4><p>MixCoord + Proxy + the three Nodes + CDC <strong>all in one process</strong>; dependencies (etcd / object storage / MQ) can be embedded or external. <strong>Simple to deploy</strong>, fits small/medium and single-host production.</p></div>
  <div class="col"><h4>Cluster</h4><p>Each component is an <strong>independent Pod</strong>; QueryNode / DataNode scale to many replicas. <strong>Elastic, highly available</strong>, for billion-scale production. The logical roles are unchanged — they've just "moved into separate houses".</p></div>
</div>

<h2>One thread that runs through the whole guide: control plane vs data plane</h2>
<p>If "three languages" is a horizontal cut, then <strong>"control plane vs data plane"</strong> is the vertical one — the single most important thread for
understanding Milvus, and nearly every lesson returns to it. The <strong>control plane</strong> governs "<strong>who should do what</strong>": a collection's schema,
which shard sits on which machine, whether a segment should flush, which replica a query routes to — these <strong>decisions and metadata</strong> belong to the
MixCoord brain. The <strong>data plane</strong> governs "<strong>actually moving and computing the data</strong>": the written bytes, the flushed binlogs, the distances
computed one by one at search time — that <strong>heavy lifting</strong> all happens in the worker nodes and the C++ kernel.</p>

<div class="cols">
  <div class="col"><h4>Control plane</h4><p>governs "<strong>who should do what</strong>": structure, shard assignment, flush decisions, query routing — decisions and metadata belong to <strong>MixCoord/coordinators</strong>. Wants <strong>correct, consistent</strong>; uses etcd's strong consistency, slower is fine.</p></div>
  <div class="col"><h4>Data plane</h4><p>governs "<strong>actually moving and computing</strong>": writing bytes, flushing binlogs, computing distances one by one — heavy lifting in <strong>DataNode/QueryNode + the C++ core</strong>. Wants <strong>fast, parallel, horizontally scalable</strong>; add machines if short.</p></div>
</div>

<p>Why split this way? Because <strong>the two have completely different temperaments</strong>. The control plane wants "<strong>correct, consistent, never wrong</strong>" —
one bad metadata write and the whole cluster goes haywire, so it would rather be a bit slow and go through etcd for strong consistency; the data plane wants
"<strong>fast, parallel, horizontally scalable</strong>" — it can tolerate "approximate", run many replicas concurrently, and add machines when short. <strong>Separating these
two demands</strong> and satisfying each with the most fitting technology is wisdom distributed systems have proven again and again. Hence the recurring motto:
<strong>"coordinators schedule, nodes execute"</strong> — MixCoord only gives orders and never moves a byte itself; DataNode / QueryNode just do the work and don't fret
about global orchestration.</p>

<p>This thread also neatly explains "<strong>why storage-compute separation</strong>": when data-plane nodes <strong>don't keep long-term state themselves</strong> (state is
entrusted to etcd and object storage), they become "<strong>disposable</strong>" compute — busy on queries? spin up more QueryNodes; busy on writes? spin up more DataNodes;
scale back when idle — <strong>and not one byte of data is lost</strong>. Compute and storage scale independently, which is the engineering foundation behind Milvus's promise
of "<strong>elastic scaling to billions</strong>". Hold onto this thread and the later write path, query path, and consistency are all just its unfolding in different settings.</p>

<h2>What the repo looks like: top-level directories at a glance</h2>
<p>Walk the git repo's top level once and you have an index of "<strong>where to find code</strong>". They roughly follow "<strong>entry → core logic → shared libs → periphery</strong>":</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4><span class="mono">cmd/</span> · entrypoints</h4><p>How each component starts: <span class="mono">cmd/components/</span> (mix_coord, proxy, query_node…) and <span class="mono">cmd/roles/roles.go</span> (which roles this process runs).</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4><span class="mono">internal/</span> · core logic</h4><p>The system's <strong>trunk</strong>: proxy, rootcoord, datacoord, querycoordv2, querynodev2, datanode, streamingnode, coordinator(mixcoord), core(C++), storage, metastore, kv, distributed(gRPC servers), types(interfaces), tso…</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4><span class="mono">pkg/</span> · shared libs</h4><p>Cross-component utilities: logging, config (paramtable), proto, helpers. Note it has its <strong>own go.mod</strong> (module <span class="mono">github.com/milvus-io/milvus/pkg/v3</span>).</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4><span class="mono">client/</span> · Go SDK</h4><p>The official Go client <span class="mono">milvusclient</span> (also its own go.mod). Python's pymilvus lives in a separate repo.</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>Periphery</h4><p><span class="mono">configs/</span> (<span class="mono">milvus.yaml</span>), <span class="mono">deployments/</span>, <span class="mono">scripts/</span>, <span class="mono">tests/</span>, <span class="mono">docs/</span>.</p></div></div>
</div>

<h2>Three external dependencies: bookkeeping, storage, logging</h2>
<p>Milvus doesn't reinvent wheels — it outsources three "infrastructure-grade" chores to mature systems. This is also the prerequisite for <strong>storage-compute separation</strong>:</p>
<ul>
  <li><strong>etcd · bookkeeping</strong>: holds <strong>metadata</strong> — which collections exist, which shard sits on which machine, who replicates whom. Small but critical, the cluster's "registry".</li>
  <li><strong>Object storage (MinIO / S3) · the warehouse</strong>: holds the <strong>actual data and index files</strong> — flushed binlogs, built indexes. Cheap, vast, durable.</li>
  <li><strong>Message queue / WAL (Pulsar / Kafka / built-in woodpecker) · the log</strong>: carries the <strong>write log</strong>, so a "write" first lands on a <strong>replayable</strong> log. This is the root of Milvus's "<strong>log as data</strong>" (detailed from Lesson 15).</li>
</ul>

<p>With those three underneath, compute nodes become "<strong>stateless</strong>" — crash-restart or scale-on-demand without losing data, because the real state
lives in etcd and object storage. <strong>That is why storage-compute separation can scale elastically to billions.</strong></p>

<p>One frequently asked point, settled here: <strong>these three dependencies aren't optional bit players — they're part of the Milvus architecture</strong>. Their choice is
<strong>pluggable</strong> — the message queue can be a mature middleware like Pulsar / Kafka, or Milvus's <strong>built-in woodpecker</strong> (sparing you from deploying a separate MQ);
object storage can be cloud S3 or self-hosted MinIO. Milvus hides these differences behind an abstraction layer, so upper logic needn't care "where exactly the log lands, where
exactly the file is stored". <strong>This "abstract the infrastructure away" design is precisely why it can switch seamlessly among cloud, on-prem, and single-host.</strong></p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/types/types.go</span><span class="ln">type MixCoord interface</span></div>
  <pre><span class="cm">// MixCoord embeds the three coordinator service interfaces — the code proof of "three-in-one"</span>
<span class="kw">type</span> MixCoord <span class="kw">interface</span> {
    Component
    rootcoordpb.RootCoordServer   <span class="cm">// metadata / DDL (Root)</span>
    querypb.QueryCoordServer      <span class="cm">// query-load scheduling (Query)</span>
    datapb.DataCoordServer        <span class="cm">// segment mgmt / write coordination (Data)</span>
    <span class="cm">// …all three now share one process, still three logical interfaces outward</span>
}</pre>
</div>

<h2>The four-group navigation model: pin any lesson to the map</h2>
<p>Finally, a set of <strong>four-group</strong> "navigation coordinates". For every lesson ahead, first ask "which group does it belong to?", then go to the
matching code directory — this grouping will stay with you:</p>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">Top</span><span class="name">SDK / API</span></div><div class="ld">pymilvus / Go <span class="mono">milvusclient</span> — your create / insert / search start here.</div></div>
  <div class="layer l-app"><div class="lh"><span class="badge">① Access</span><span class="name">Proxy</span></div><div class="ld">The one public window: validate, auth, assign timestamp, route, reduce across shards.</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">② Coordination</span><span class="name">MixCoord</span></div><div class="ld">The three-in-one brain: metadata, segments, query-load scheduling — decides, never moves data.</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">③ Worker nodes</span><span class="name">Query / Data / Streaming Node</span></div><div class="ld">The real work: QueryNode searches, DataNode writes &amp; flushes, StreamingNode carries the WAL.</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">Kernel</span><span class="name">C++ core (segcore / index / query)</span></div><div class="ld">The compute kernel beneath the worker nodes: blazing in-segment search and indexing.</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">④ Storage &amp; deps</span><span class="name">etcd · object storage · MQ/WAL</span></div><div class="ld">Bookkeeping (metadata), warehouse (data &amp; indexes), the log (a replayable write stream).</div></div>
</div>

<p>With this map in hand, the next lesson <strong>sets it in motion</strong>: we follow one insert and one search through "<strong>the life of a request</strong>"
and watch how a request flows among these four groups.</p>

<h2>How to use this map: your learning route</h2>
<p>The map is drawn — finally, how to <strong>use</strong> it. Every later part of this guide essentially <strong>zooms into one block of the map</strong> — treat it as a tour route:</p>
<ul>
  <li><strong>A "write" topic</strong> (insert, WAL, flush, segments, compaction) → look at the ② <strong>DataCoord role</strong> + ③ <strong>DataNode / StreamingNode</strong>, i.e. <span class="mono">internal/datanode</span>, <span class="mono">internal/streamingnode</span>, <span class="mono">internal/flushcommon</span>. This thread unfolds in the write path from <strong>Lesson 15</strong>.</li>
  <li><strong>A "query" topic</strong> (search, filtering, reduce, consistency) → look at the ① <strong>Proxy</strong> + ③ <strong>QueryNode</strong> + kernel <strong>C++ segcore</strong>, i.e. <span class="mono">internal/proxy</span>, <span class="mono">internal/querynodev2</span>, <span class="mono">internal/core/src/segcore</span>. Unfolds from <strong>Lesson 25</strong>.</li>
  <li><strong>An "index" topic</strong> (HNSW, IVF, DiskANN, quantization) → look at the kernel <strong>C++ index</strong> + ② <strong>DataCoord's index scheduling</strong>, i.e. <span class="mono">internal/core/src/index</span> and the index-related files in <span class="mono">internal/datacoord</span>.</li>
  <li><strong>A "metadata / collection / access-control" topic</strong> → look at the ② <strong>RootCoord role</strong> and etcd, i.e. <span class="mono">internal/rootcoord</span>, <span class="mono">internal/metastore</span>.</li>
</ul>

<p>In other words: <strong>whenever you don't know "who owns this thing", come back to these four groups and place it</strong>. Component name, directory name, language,
responsibility — once you build the mapping among those four facts, you've gained the ability to <strong>navigate freely</strong> in this huge codebase — which is exactly what the
"project map" lesson most wants to leave you with. It's fine not to memorize every street; what matters is that <strong>you always know where you stand and where to go next</strong>.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Three-language split</strong>: Go (control plane, <span class="mono">internal/</span>) + C++ (compute kernels, <span class="mono">internal/core/</span>: segcore/index/query/exec/expr) + a little Rust (full-text tantivy).</li>
    <li><strong>MixCoord is the key correction</strong>: the Root/Data/Query coordinator <strong>roles</strong> still exist, but are merged into <strong>one MixCoord process</strong> — three things logically, one process physically.</li>
    <li><strong>Six runtime components</strong>: MixCoord, Proxy, QueryNode, DataNode, StreamingNode, CDC; <strong>no separate indexnode</strong> (index is scheduled by DataCoord, run by a datanode).</li>
    <li><strong>Two shapes</strong>: Standalone = one process, Cluster = many Pods — <strong>same components, same API</strong>.</li>
    <li><strong>Repo index</strong>: <span class="mono">cmd/</span> entry · <span class="mono">internal/</span> core · <span class="mono">pkg/</span> shared libs · <span class="mono">client/</span> SDK; external deps etcd / object storage / MQ enable storage-compute separation.</li>
    <li><strong>Four-group nav</strong>: ① Access Proxy ② Coordination MixCoord ③ Worker nodes ④ Storage &amp; deps, plus the C++ kernel below and the SDK above.</li>
  </ul>
</div>
""",
}


LESSON_03 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
有了上一课的全景地图，这一课我们<strong>让它动起来</strong>：跟着<strong>一条 insert</strong> 和<strong>一条 search</strong>，从客户端出发，
走遍 Proxy、协调器、工作节点、C++ 内核，看一次请求<strong>到底经过哪些手、在每一站发生了什么</strong>。这是一条"<strong>万米高空的航线图</strong>"——
只点出每个站点的名字与职责，细节留给后面的写入链路（<strong>第 15 课</strong>起）、查询链路（<strong>第 25 课</strong>起）、一致性（<strong>第 30 课</strong>）逐站放大。
</p>

<div class="card analogy">
  <div class="tag">📮 生活类比</div>
  把<strong>写入</strong>想成<strong>往邮局寄信</strong>：你不会把信直接塞进收件人家门，而是先交到<strong>邮局柜台（Proxy）</strong>，柜台<strong>盖一个时间戳（收件时间）</strong>、
  按地址分拣，再把信<strong>登记进一本流水账（WAL 日志）</strong>。只要账记上了，这封信就"<strong>算寄出了</strong>"，哪怕后续的投递慢一点也丢不了。
  而<strong>查询</strong>更像<strong>查档案</strong>：你说"<strong>给我看截至某个时刻为止的全部记录</strong>"，档案管理员据此圈定一个<strong>时间快照</strong>，
  保证你看到的是一份<strong>前后一致</strong>的状态，而不是边查边变的半成品。<strong>时间戳，就是这两件事共同的钥匙。</strong>这一课，我们就握着这把钥匙，把读写两条链路彻底走通一遍。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一次请求的主线只有两条：<strong>写</strong>沿着日志走（Proxy→WAL→growing 段→flush），<strong>读</strong>靠扇出归约（Proxy→QueryNode 分片→segcore→reduce）；贯穿这两条线的钥匙，是<strong>时间戳</strong>。
</div>

<h2>写入的一生：insert 走过的七站</h2>
<p>先看写。一条 <span class="inline">insert</span> 从 SDK 出发，要走过下面这条链路。请特别留意<strong>两个关键动作</strong>：在 Proxy <strong>盖时间戳</strong>、
以及"<strong>先写日志</strong>"——这两点是后面理解一致性与崩溃恢复的地基：</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>客户端 / SDK</h4><p>pymilvus / Go <span class="mono">milvusclient</span> 把若干行（向量 + 标量字段）打包，发往 Proxy。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Proxy · 校验 + 补主键 + 盖时间戳</h4><p>校验 schema；若主键是 auto-id 就<strong>自动补上</strong>；向 <strong>TSO</strong> 申请一个全局<strong>时间戳 ts</strong>，盖在这批数据上。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Proxy · 按主键哈希分片</h4><p>用主键把每行<strong>哈希到不同的 vchannel（虚拟分片）</strong>，决定它该进哪条写入流——这样数据天然被打散到多个分片并行处理。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>追加到 WAL / 流式日志</h4><p>Proxy 把这批数据<strong>追加进 WAL</strong>（一条可重放的写入日志）。<strong>账一记上，这次写入就算成功返回了。</strong></p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>StreamingNode / DataNode · 消费日志</h4><p>工作节点<strong>顺着日志往下读</strong>，把刚写入的行<strong>放进一个"增长段（growing segment）"</strong>——一块还在内存里、可以被立即查询的数据。</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>刷盘成 binlog</h4><p>当增长段攒到一定<strong>大小 / 时间</strong>阈值，就<strong>刷盘（flush）</strong>成<strong>binlog</strong>，持久化到对象存储，段从此"封存（sealed）"。</p></div></div>
  <div class="step"><div class="num">7</div><div class="sc"><h4>DataCoord · 记账段元数据</h4><p><strong>DataCoord</strong>（MixCoord 里的 Data 角色）记录"<strong>哪些段、在哪、多大、刷没刷</strong>"，作为后续查询与压缩的依据。</p></div></div>
</div>

<p>这里有三个观念值得现在就刻进脑子。其一，"<strong>日志即数据（log as data）</strong>"：Milvus 把"写"先变成"<strong>往日志里追加一条记录</strong>"，
日志才是<strong>唯一的真相来源</strong>，段、索引都只是日志的"物化视图"。这让崩溃恢复变得简单——重放日志即可。其二，"<strong>边写边查</strong>"：
新数据进了<strong>增长段</strong>就能被搜到，<strong>不必等刷盘、更不必等建索引</strong>，这正是 Milvus 数据"实时新鲜"的来源。其三，"<strong>一批原子可见</strong>"：
同一批 insert 共享<strong>同一个时间戳</strong>，要么一起可见、要么都不可见，不会让你查到"半批"数据。</p>

<p>有一个地方值得停下来多想一层：<strong>为什么写入要"先过日志"，而不是直接写进段、写进对象存储？</strong>这看似绕了远路，实则是分布式存储的核心智慧。
直接写段有三个麻烦：一是<strong>慢</strong>——对象存储适合"大块、批量"写，逐行写又慢又贵；二是<strong>难恢复</strong>——写到一半进程挂了，段处于"残缺"状态，很难判断哪些行成功了；
三是<strong>难并发</strong>——多个写入者同时改同一个段，要费很大力气做锁。而"<strong>先写一条只追加（append-only）的日志</strong>"把这三件事一次解决：
追加是<strong>顺序写</strong>，飞快；日志<strong>天然有序</strong>，重放到哪一条一清二楚，崩溃后接着重放即可；多个写入只是<strong>往同一条日志尾部排队</strong>，无需互相加锁。
段和索引则在"<strong>事后</strong>"由消费者从日志慢慢物化出来——这就是把"<strong>写得快</strong>"和"<strong>查得快</strong>"这对矛盾<strong>解耦</strong>的关键招式。</p>

<h2>崩溃与重放：日志即数据的实战红利</h2>
<p>前面说"日志即数据"听起来像口号，它最实在的红利要等到<strong>崩溃恢复</strong>时才兑现。设想消费日志、攒增长段的那个工作节点<strong>突然宕机</strong>：内存里还没刷盘的增长段一瞬间全没了。换作"直接写段"的系统，这往往意味着<strong>数据丢失</strong>；但在 Milvus 里，丢掉的只是"<strong>从日志物化出来的中间结果</strong>"，而<strong>唯一真相</strong>——那条 WAL 日志——好端端地躺在消息队列／对象存储里，<strong>一个字节都没少</strong>。</p>

<p>于是恢复就变成一件机械的事：节点重启后，<strong>不必从头重放整条日志</strong>，而是从它上次记下的<strong>检查点（checkpoint，即消费位点 / seek position）</strong>开始，把"<strong>检查点之后</strong>"的那段日志<strong>重新消费一遍（replay）</strong>，增长段就被<strong>原样重建</strong>出来，仿佛什么都没发生过。检查点的作用就像看书夹的书签：你不必每次从第一页读起，翻到书签那页接着读即可。正因为日志<strong>天然有序、可重放</strong>，"读到哪了"永远是一个明确的位置，崩溃后接着读就行——这就是把"写"设计成"<strong>带时间戳的、只追加的日志</strong>"换来的最大底气。</p>

<p>再往上看一层，这也解释了为什么 Milvus 的工作节点能做到"<strong>无状态、用完即弃</strong>"：既然任何节点的内存状态都能靠重放日志重建，那么节点挂了就换一个、负载高了就多拉几个，<strong>数据安全完全不依赖某一台机器还活着</strong>。"日志即数据"与上一课的"存算分离"，本质上是<strong>同一个设计哲学的一体两面</strong>——把唯一真相托管给可重放的日志与对象存储，计算节点便获得了随意伸缩、随时重建的自由。</p>

<p>还有一个常被忽略的细节值得点一句：<strong>检查点不是凭空前进的，而是跟着"刷盘"走</strong>。当增长段刷成 binlog、稳稳落进对象存储后，"这段日志已被安全物化"才算坐实，消费位点便可以<strong>安全地往前挪</strong>——这样崩溃后要重放的日志就越来越短，恢复也越来越快。换句话说，<strong>flush 既是为了让历史数据落盘，也是为了给日志"减负"</strong>。这条"<strong>写日志 → 消费 → 刷盘 → 推进检查点</strong>"的循环，正是写入链路在背后悄悄转动的飞轮，第 15 课起我们会逐圈拆解它。值得一提的是，检查点也不必"每条都记"——记得太频繁本身是种开销，记得太稀疏又会拉长崩溃后的重放窗口，<strong>多久推进一次</strong>是吞吐与恢复速度之间的又一处工程权衡。你会发现，这种"快与稳之间拿捏分寸"的取舍，几乎是贯穿整个 Milvus 设计的母题。</p>

<h2>查询的一生：search 走过的六站</h2>
<p>再看读。一条 <span class="inline">search</span> 的链路和写不同——它要<strong>同时问很多个分片</strong>，再把结果<strong>层层归并</strong>成最终的 topK。
关键动作同样有两个：在 Proxy <strong>定一个"保证时间戳"</strong>（决定你能看到多新的数据），以及把"<strong>段内的相似度计算</strong>"下沉给 <strong>C++ 内核</strong>：</p>

<div class="flow">
  <div class="node hl"><div class="nt">SDK / 客户端</div><div class="nd">发起 search(向量, topK)</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Proxy</div><div class="nd">定保证时间戳 · 建查询计划 · 按分片路由</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">QueryNode · delegator</div><div class="nd">圈定 封存段 + 增长段</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">segcore (C++)</div><div class="nd">段内检索 · 每段 topK</div></div>
</div>

<p>把这条链路一站站说清楚：</p>
<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Proxy · 定"保证时间戳"</h4><p>根据你选的<strong>一致性级别</strong>推导一个 <strong>guarantee timestamp</strong>：要"看见最新"（Strong）就取最大时间，要"够快、容忍少量延迟"（Bounded）就取稍早一点的时间。这个 ts 决定了你这次能看到多新的数据。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Proxy · 建计划 + 路由</h4><p>把查询解析成一个<strong>搜索计划</strong>（向量字段、度量、topK、标量过滤条件），再按<strong>分片</strong>把请求<strong>分发到相关的 QueryNode</strong>。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>delegator · 圈定要搜的段</h4><p>每个分片有一个<strong>代理者 / 分片领导（delegator / shard leader）</strong>，它清楚本分片有哪些<strong>封存段 + 增长段</strong>，并据保证时间戳<strong>等数据"够新"了</strong>再放行搜索。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>segcore (C++) · 段内检索</h4><p>真正"算距离"的脏活下沉到 <strong>C++ 的 segcore</strong>：在每个段内沿索引找近邻，吐出<strong>这一段的 topK</strong>。</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>节点内归并</h4><p>一个 QueryNode 上可能有很多段，它先把<strong>各段的 topK 归并</strong>成"本节点的 topK"，减少要往上传的数据。</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>Proxy · 跨分片归并 → 客户端</h4><p>Proxy 收齐<strong>各分片的 topK</strong>，再做<strong>一次全局归并</strong>，排出最终的 topK 返回客户端。<strong>"分头搜、层层并"</strong>是检索的标准套路。</p></div></div>
</div>

<p>注意搜索的"<strong>扇出—归约（scatter-gather）</strong>"形状：Proxy 把一个请求<strong>扇出</strong>给多个分片、每个分片再扇给多个段并行算，
然后结果<strong>反向归约</strong>——段 topK → 节点 topK → 全局 topK。每一层都只往上传"前 K 个"，所以即便底下有上亿条向量，
网络上流动的也只是<strong>很少量的候选</strong>。这就是分布式检索既<strong>快</strong>又<strong>省</strong>的关键。</p>

<p>顺便回答一个常见疑问：<strong>为什么读和写要走两条不同的路？</strong>因为它们的目标根本不同。<strong>写</strong>追求"<strong>尽快落定、绝不丢失</strong>"，所以它走"日志"这条<strong>顺序、单向</strong>的快车道，
一路向前、不回头；<strong>读</strong>追求"<strong>在海量数据里挑出最像的几条</strong>"，所以它必须<strong>扇出</strong>到所有相关分片和段、并行去算，再把结果<strong>归约</strong>回来。
一个是"<strong>把水灌进管道</strong>"，一个是"<strong>从万千水库里舀出最甜的那几瓢</strong>"——形状自然不同。但请注意，<strong>读其实要同时看两种段</strong>：
已经刷盘的<strong>封存段</strong>（历史数据）和还在内存里的<strong>增长段</strong>（刚写入、尚未落盘的新数据）。正因为 delegator 把这两者<strong>都纳入检索范围</strong>，
Milvus 才能做到"<strong>边写边查</strong>"——你上一秒 insert 的数据，下一秒就能在增长段里被搜到。这也是为什么"写入的增长段"和"查询的段选择"是同一枚硬币的两面。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/proxy/util.go · 读请求按一致性级别推导保证时间戳</span><span class="ln">parseGuaranteeTsFromConsistency · 示意，已简化</span></div>
  <pre><span class="cm">// 一致性级别 → guarantee timestamp（决定这次 search 能看到多新的数据）</span>
<span class="kw">switch</span> consistencyLevel {
<span class="kw">case</span> Strong:      guaranteeTs = tMax                 <span class="cm">// 强一致：看见此刻最新</span>
<span class="kw">case</span> Bounded:     guaranteeTs = tMax - gracefulTime  <span class="cm">// 有界：容忍少量延迟，换更低时延</span>
<span class="kw">case</span> Eventually:  guaranteeTs = <span class="nb">1</span>                   <span class="cm">// 最终：最快，可能读到较旧快照</span>
}
<span class="cm">// delegator 会"等到本分片数据追上 guaranteeTs"再开始搜，从而给出一致快照</span>
<span class="cm">// 示意，已简化：真实代码用 commonpb.ConsistencyLevel_Strong / tsoutil.AddPhysicalDurationOnTs</span></pre>
</div>

<h2>时间戳：读写共用的那把钥匙</h2>
<p>把上面两条链路并排一看，你会发现<strong>时间戳（timestamp）</strong>是贯穿读写的<strong>同一根轴</strong>：<strong>写</strong>给每批数据盖一个 ts（决定它"何时发生"）；
<strong>读</strong>用一个保证 ts 圈定一个<strong>快照</strong>（决定它"看见到何时为止")。两者用的是<strong>同一套全局时钟（TSO）</strong>，于是"先后顺序"在整个集群里有了统一的定义：</p>

<div class="timeline">
  <div class="lane"><span class="lane-label">写入流</span><span class="tslot">ts=10 批A</span><span class="tslot">ts=20 批B</span><span class="tslot">ts=30 批C</span><span class="tslot span">…持续追加…</span></div>
  <div class="lane"><span class="lane-label">读 (Strong)</span><span class="tslot">取 ts=最新</span><span class="tslot now">看见 A·B·C 全部</span></div>
  <div class="lane"><span class="lane-label">读 (Bounded)</span><span class="tslot">取 ts=稍早</span><span class="tslot now">看见 A·B（容忍 C 略迟）</span></div>
</div>

<p>这里只需建立<strong>直觉</strong>：保证时间戳越"新"，看到的数据越全，但可能要<strong>多等一会儿</strong>（等分片追上这个 ts）；越"旧"则越快、但可能漏掉最新写入。
这正是<strong>一致性级别</strong>在背后做的权衡。它的完整机制——TSO 怎么发号、delegator 怎么等、快照怎么保证——留到<strong>第 30 课</strong>专门展开，这里点到为止。</p>

<p>再补一句关于 <strong>TSO（Timestamp Oracle，时间戳分配器）</strong>的直觉：它是整个集群的"<strong>统一发号机</strong>"，保证发出去的时间戳<strong>全局单调递增</strong>——
后申请的一定比先申请的大。有了这台"<strong>全局时钟</strong>"，分布在不同机器上的写入才有了公认的<strong>先后次序</strong>，读取也才能用一个 ts 干净地切出"<strong>截至此刻</strong>"的快照。
你可以把它想成银行叫号机：每个人来都撕一张号，号码只增不减，于是"谁先谁后"再无争议。TSO 住在 MixCoord 里（Root 角色），Proxy 每次处理读写都先向它<strong>要一个号</strong>。
正是这台朴素的发号机，撑起了 Milvus 在分布式环境下的<strong>时序一致性</strong>——一个看似简单、却无处不在的基础设施。</p>

<h2>一张表收尾：每个组件在一次请求里扮演什么角色</h2>
<p>最后用一张表把"<strong>谁在一次请求里干什么</strong>"对齐，方便你随时回查：</p>

<table class="t">
  <tr><th>组件</th><th>在写入里</th><th>在查询里</th></tr>
  <tr><td><strong>SDK / 客户端</strong></td><td>打包行、发起 insert</td><td>发起 search(向量, topK)、收最终结果</td></tr>
  <tr><td><strong>Proxy</strong></td><td>校验、补主键、盖时间戳、按 PK 哈希分片、写 WAL</td><td>定保证时间戳、建计划、路由、<strong>跨分片归并</strong></td></tr>
  <tr><td><strong>TSO</strong>（在 MixCoord）</td><td>发放写入时间戳</td><td>作为保证时间戳的参照时钟</td></tr>
  <tr><td><strong>StreamingNode / DataNode</strong></td><td>消费日志、攒增长段、刷盘成 binlog</td><td>（写侧为主）</td></tr>
  <tr><td><strong>DataCoord</strong>（在 MixCoord）</td><td>记账段元数据、触发刷盘/压缩</td><td>提供"有哪些段"的信息</td></tr>
  <tr><td><strong>QueryNode · delegator</strong></td><td>（读侧为主）</td><td>圈定封存段+增长段、等数据够新、汇总本节点 topK</td></tr>
  <tr><td><strong>segcore (C++)</strong></td><td>—</td><td>段内检索、算每段 topK</td></tr>
</table>

<p>这就是"一次请求的一生"的全貌：<strong>写</strong>是"盖时间戳 → 先写日志 → 异步落盘 → 协调器记账"，<strong>读</strong>是"定快照 → 扇出到分片与段 → C++ 算 topK → 层层归并"。
两条链路看似不同，却共享同一套<strong>时间戳</strong>与同一张<strong>全景地图</strong>。带着这副"骨架"，后面每一部分都会回到这两条链路上的某一站，把它<strong>放大成一整课</strong>。</p>

<p>最后留一个<strong>承前启后</strong>的提醒：本课所有名词——时间戳、vchannel、WAL、增长段、封存段、binlog、delegator、segcore、归并——你现在<strong>不必记牢每个细节</strong>，
只要在脑子里建立起"它在哪条链路的哪一站"的<strong>位置感</strong>即可。把它们想象成地铁线路图上的站点：你暂时不知道每站附近有什么，但你知道<strong>坐这条线能到那里</strong>。
后面的课，就是带你<strong>在每一站下车，逛透它周围的街区</strong>。下一部分起，我们正式钻进引擎内部——从"数据是怎么被组织成集合、分区、段"开始。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>写入链路</strong>：SDK → Proxy（校验、补主键、<strong>盖时间戳</strong>、按 PK 哈希分片）→ 追加 <strong>WAL</strong> → StreamingNode/DataNode 消费 → <strong>增长段</strong> → 刷盘成 <strong>binlog</strong> → DataCoord 记账。</li>
    <li><strong>日志即数据</strong>：先写可重放的日志，写入即返回；段与索引是日志的物化视图，崩溃后重放即可恢复。</li>
    <li><strong>查询链路</strong>：SDK → Proxy（<strong>定保证时间戳</strong>、建计划、路由）→ QueryNode <strong>delegator</strong> 圈定封存段+增长段 → <strong>segcore(C++)</strong> 段内 topK → 节点归并 → Proxy <strong>跨分片归并</strong> → 客户端。</li>
    <li><strong>扇出—归约</strong>：每一层只上传"前 K 个"，所以海量向量下网络上只流动极少候选。</li>
    <li><strong>时间戳是读写共用的钥匙</strong>：写盖 ts、读用保证 ts 取一致快照；一致性级别就是在"看得多新 vs 等得多久"之间权衡（细节见<strong>第 30 课</strong>）。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
With last lesson's project map in hand, this lesson <strong>sets it in motion</strong>: we follow <strong>one insert</strong> and <strong>one search</strong>
from the client out, through Proxy, the coordinator, the worker nodes, and the C++ kernel, watching <strong>which hands a request passes through and what
happens at each stop</strong>. This is a "<strong>30,000-foot flight map</strong>" — naming each station and its job, leaving the details to the write path
(<strong>Lesson 15</strong>+), the query path (<strong>Lesson 25</strong>+), and consistency (<strong>Lesson 30</strong>) to zoom into station by station.
</p>

<div class="card analogy">
  <div class="tag">📮 Analogy</div>
  Think of a <strong>write</strong> as <strong>mailing a letter at the post office</strong>: you don't stuff the letter directly into the recipient's door — you hand it to
  the <strong>counter (Proxy)</strong>, which <strong>stamps a timestamp (received-at time)</strong>, sorts it by address, and <strong>logs it into a ledger (the WAL)</strong>.
  Once it's in the ledger, the letter "<strong>counts as sent</strong>" — even if delivery is a bit slow, it won't be lost. A <strong>query</strong> is more like <strong>reading
  the archive</strong>: you say "<strong>show me all records up to a certain moment</strong>", and the archivist fixes a <strong>time snapshot</strong> accordingly, guaranteeing you
  see a <strong>self-consistent</strong> state rather than a half-finished one changing as you read. <strong>The timestamp is the shared key to both.</strong> In this lesson, holding that key, we'll walk both the read and write chains end to end.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  A request has just two main lines: a <strong>write</strong> follows the log (Proxy→WAL→growing segment→flush), a <strong>read</strong> relies on scatter-gather (Proxy→QueryNode shards→segcore→reduce); the key threading both lines is the <strong>timestamp</strong>.
</div>

<h2>The life of a write: the seven stops of an insert</h2>
<p>Writes first. An <span class="inline">insert</span> leaves the SDK and travels this chain. Note <strong>two key actions</strong> in particular: <strong>stamping a timestamp</strong>
at the Proxy, and "<strong>log first</strong>" — these two are the bedrock for later understanding consistency and crash recovery:</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Client / SDK</h4><p>pymilvus / Go <span class="mono">milvusclient</span> packs some rows (vectors + scalar fields) and sends them to the Proxy.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Proxy · validate + fill PK + stamp timestamp</h4><p>Validate the schema; if the primary key is auto-id, <strong>fill it in</strong>; request a global <strong>timestamp ts</strong> from the <strong>TSO</strong> and stamp it on this batch.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Proxy · hash by primary key into shards</h4><p>Use the PK to <strong>hash each row into a vchannel (virtual shard)</strong>, deciding which write stream it enters — so data is naturally spread across shards for parallelism.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Append to the WAL / streaming log</h4><p>The Proxy <strong>appends the batch to the WAL</strong> (a replayable write log). <strong>Once it's in the ledger, the write returns as a success.</strong></p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>StreamingNode / DataNode · consume the log</h4><p>Worker nodes <strong>read down the log</strong> and put the just-written rows into a "<strong>growing segment</strong>" — data still in memory and immediately queryable.</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>Flush to binlog</h4><p>When a growing segment hits a <strong>size / time</strong> threshold, it <strong>flushes</strong> into a <strong>binlog</strong>, persisted to object storage; the segment becomes "<strong>sealed</strong>".</p></div></div>
  <div class="step"><div class="num">7</div><div class="sc"><h4>DataCoord · track segment metadata</h4><p><strong>DataCoord</strong> (the Data role inside MixCoord) records "<strong>which segments, where, how big, flushed or not</strong>" as the basis for later queries and compaction.</p></div></div>
</div>

<p>Three ideas worth carving into your mind now. First, "<strong>log as data</strong>": Milvus turns a "write" into "<strong>append a record to the log</strong>" first; the log is
the <strong>single source of truth</strong>, and segments and indexes are just its "materialized views". This makes crash recovery simple — replay the log. Second, "<strong>query while
writing</strong>": new data enters a <strong>growing segment</strong> and is searchable <strong>without waiting for a flush, let alone an index build</strong> — the source of Milvus's
"real-time freshness". Third, "<strong>a batch is atomically visible</strong>": one insert batch shares <strong>one timestamp</strong> — either all visible or none, never letting you read
"half a batch".</p>

<p>One spot worth pausing to think a layer deeper: <strong>why must a write "go through the log first" instead of writing straight into segments and object storage?</strong> It looks like a
detour, but it's the core wisdom of distributed storage. Writing segments directly has three problems: it's <strong>slow</strong> — object storage favors "large, batched" writes, and row-by-row
is slow and costly; it's <strong>hard to recover</strong> — if the process dies mid-write, the segment is "partial" and it's hard to tell which rows succeeded; and it's <strong>hard to
concurrent</strong> — many writers mutating the same segment require heavy locking. "<strong>Write an append-only log first</strong>" solves all three at once: appends are <strong>sequential
writes</strong>, blazing fast; the log is <strong>naturally ordered</strong>, so you know exactly where replay stopped and just resume after a crash; concurrent writers merely <strong>queue at the
log's tail</strong>, needing no mutual locks. Segments and indexes are then materialized "<strong>after the fact</strong>" by consumers reading the log — the key move that <strong>decouples</strong>
the tension between "<strong>writing fast</strong>" and "<strong>querying fast</strong>".</p>

<h2>Crash &amp; replay: the practical payoff of "log as data"</h2>
<p>"Log as data" sounds like a slogan, but its most concrete payoff only cashes out at <strong>crash recovery</strong>. Picture the worker node that consumes the log and builds growing segments <strong>suddenly dying</strong>: the not-yet-flushed growing segments in memory vanish in an instant. In a system that "writes segments directly", that often means <strong>data loss</strong>; but in Milvus, what's lost is merely the "<strong>intermediate result materialized from the log</strong>", while the <strong>single source of truth</strong> — the WAL — sits safely in the message queue / object storage, <strong>not a byte missing</strong>.</p>

<p>So recovery becomes mechanical: after the node restarts, it <strong>need not replay the whole log from the start</strong>; it resumes from the <strong>checkpoint (its consume position / seek position)</strong> it last recorded, <strong>replays</strong> the slice of log "<strong>after that checkpoint</strong>", and the growing segment is <strong>rebuilt exactly as before</strong>, as if nothing happened. A checkpoint is like a bookmark: you don't reread from page one, you flip to the bookmark and continue. Precisely because the log is <strong>naturally ordered and replayable</strong>, "where did I get to" is always a definite position, and after a crash you just keep reading — that is the biggest assurance bought by designing a "write" as a "<strong>timestamped, append-only log</strong>".</p>

<p>One layer up, this also explains why Milvus's worker nodes can be "<strong>stateless, disposable</strong>": since any node's in-memory state can be rebuilt by replaying the log, a dead node is simply replaced and a busy load simply gets more nodes — <strong>data safety never depends on one machine staying alive</strong>. "Log as data" and last lesson's "storage-compute separation" are, in essence, <strong>two sides of one design philosophy</strong>: entrust the single source of truth to a replayable log and object storage, and compute nodes gain the freedom to scale and rebuild at will.</p>

<p>One often-overlooked detail worth a line: <strong>a checkpoint doesn't advance out of thin air — it follows the flush</strong>. Only once a growing segment is flushed into a binlog and safely landed in object storage is "this slice of log has been safely materialized" confirmed, and only then may the consume position <strong>safely move forward</strong> — so the log to replay after a crash keeps shrinking and recovery keeps getting faster. In other words, <strong>flush exists both to persist historical data and to "lighten" the log</strong>. This loop — "<strong>write log → consume → flush → advance checkpoint</strong>" — is the flywheel quietly turning behind the write path, which we'll dismantle turn by turn from Lesson 15 on. Worth noting: a checkpoint needn't be recorded "for every record" — recording too often is itself overhead, recording too sparsely lengthens the post-crash replay window, so <strong>how often to advance it</strong> is yet another engineering trade-off between throughput and recovery speed. You'll find this "calibrating between fast and steady" tension is almost a recurring motif across Milvus's whole design.</p>

<h2>The life of a query: the six stops of a search</h2>
<p>Now reads. A <span class="inline">search</span> differs from a write — it must <strong>ask many shards at once</strong>, then <strong>reduce layer by layer</strong> into the final topK.
Again two key actions: fixing a "<strong>guarantee timestamp</strong>" at the Proxy (deciding how fresh the data you see is), and sinking the "<strong>in-segment similarity
computation</strong>" down to the <strong>C++ kernel</strong>:</p>

<div class="flow">
  <div class="node hl"><div class="nt">SDK / client</div><div class="nd">issue search(vector, topK)</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Proxy</div><div class="nd">fix guarantee ts · build plan · route by shard</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">QueryNode · delegator</div><div class="nd">pick sealed + growing segments</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">segcore (C++)</div><div class="nd">in-segment search · per-segment topK</div></div>
</div>

<p>The same chain, stop by stop:</p>
<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Proxy · fix the "guarantee timestamp"</h4><p>Derive a <strong>guarantee timestamp</strong> from your chosen <strong>consistency level</strong>: to "see the latest" (Strong) take the max time; to be "fast, tolerating a little lag" (Bounded) take a slightly earlier time. This ts decides how fresh the data you can see is.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Proxy · build plan + route</h4><p>Parse the query into a <strong>search plan</strong> (vector field, metric, topK, scalar filter), then <strong>dispatch to the relevant QueryNodes</strong> by <strong>shard</strong>.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>delegator · pick the segments to search</h4><p>Each shard has a <strong>delegator / shard leader</strong> that knows the shard's <strong>sealed + growing segments</strong>, and waits until data is "<strong>fresh enough</strong>" per the guarantee ts before letting the search proceed.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>segcore (C++) · in-segment search</h4><p>The real "distance-crunching" grunt work sinks into <strong>C++ segcore</strong>: walk the index within each segment to find neighbors and emit <strong>that segment's topK</strong>.</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>Reduce within the node</h4><p>A QueryNode may hold many segments; it first <strong>reduces each segment's topK</strong> into "this node's topK", cutting the data to send upward.</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>Proxy · reduce across shards → client</h4><p>The Proxy collects <strong>each shard's topK</strong>, does <strong>one global reduce</strong>, and returns the final topK to the client. "<strong>Search in parallel, reduce in layers</strong>" is the standard pattern.</p></div></div>
</div>

<p>Note search's "<strong>scatter-gather</strong>" shape: the Proxy <strong>scatters</strong> a request to many shards, each shard fans out to many segments computed in parallel, then results
are <strong>gathered back</strong> — segment topK → node topK → global topK. Each layer only passes up "the top K", so even with hundreds of millions of vectors underneath, only a
<strong>tiny set of candidates</strong> flows over the network. That is the key to distributed search being both <strong>fast</strong> and <strong>cheap</strong>.</p>

<p>While we're here, a common question: <strong>why do reads and writes take two different paths?</strong> Because their goals fundamentally differ. A <strong>write</strong> pursues "<strong>settle
fast, never lose</strong>", so it takes the "log" — a <strong>sequential, one-way</strong> express lane, ever forward, never looking back; a <strong>read</strong> pursues "<strong>pick the few most
similar out of a huge pile</strong>", so it must <strong>scatter</strong> to all relevant shards and segments, compute in parallel, then <strong>gather</strong> the results back. One is "<strong>pouring
water into a pipe</strong>", the other is "<strong>scooping the sweetest few ladles from thousands of reservoirs</strong>" — the shapes naturally differ. But note that <strong>a read actually looks at two
kinds of segments</strong>: the flushed <strong>sealed segments</strong> (historical data) and the in-memory <strong>growing segments</strong> (freshly written, not yet flushed). Precisely because the
delegator <strong>includes both</strong> in the search scope, Milvus achieves "<strong>query while writing</strong>" — data you inserted a second ago is searchable in the growing segment the next.
That's why "the growing segment of writes" and "the segment selection of queries" are two sides of one coin.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/proxy/util.go · derive guarantee ts from the consistency level</span><span class="ln">parseGuaranteeTsFromConsistency · illustrative, simplified</span></div>
  <pre><span class="cm">// consistency level → guarantee timestamp (decides how fresh this search sees)</span>
<span class="kw">switch</span> consistencyLevel {
<span class="kw">case</span> Strong:      guaranteeTs = tMax                 <span class="cm">// strong: see the very latest</span>
<span class="kw">case</span> Bounded:     guaranteeTs = tMax - gracefulTime  <span class="cm">// bounded: tolerate a little lag for lower latency</span>
<span class="kw">case</span> Eventually:  guaranteeTs = <span class="nb">1</span>                   <span class="cm">// eventual: fastest, may read an older snapshot</span>
}
<span class="cm">// the delegator waits until the shard's data catches up to guaranteeTs, giving a consistent snapshot</span>
<span class="cm">// illustrative, simplified: real code uses commonpb.ConsistencyLevel_Strong / tsoutil.AddPhysicalDurationOnTs</span></pre>
</div>

<h2>Timestamps: the key shared by reads and writes</h2>
<p>Lay the two chains side by side and you'll see <strong>the timestamp</strong> is the <strong>same axis</strong> running through both: a <strong>write</strong> stamps each batch with a ts
(deciding "when it happened"); a <strong>read</strong> uses a guarantee ts to fix a <strong>snapshot</strong> (deciding "up to when it sees"). Both use the <strong>same global clock (TSO)</strong>, so
"order" has one unified definition across the whole cluster:</p>

<div class="timeline">
  <div class="lane"><span class="lane-label">Write stream</span><span class="tslot">ts=10 batch A</span><span class="tslot">ts=20 batch B</span><span class="tslot">ts=30 batch C</span><span class="tslot span">…keeps appending…</span></div>
  <div class="lane"><span class="lane-label">Read (Strong)</span><span class="tslot">take ts=latest</span><span class="tslot now">sees A·B·C all</span></div>
  <div class="lane"><span class="lane-label">Read (Bounded)</span><span class="tslot">take ts=earlier</span><span class="tslot now">sees A·B (tolerates C lag)</span></div>
</div>

<p>Here you only need the <strong>intuition</strong>: the "fresher" the guarantee ts, the more complete the data you see, but you may <strong>wait a bit longer</strong> (for the shard to catch up
to that ts); the "older" it is, the faster, but you may miss the latest writes. That is exactly the trade-off <strong>consistency levels</strong> make behind the scenes. The full mechanism — how the
TSO issues, how the delegator waits, how the snapshot is guaranteed — is saved for <strong>Lesson 30</strong>; we only touch it here.</p>

<p>One more intuition about the <strong>TSO (Timestamp Oracle)</strong>: it is the cluster's "<strong>unified ticket dispenser</strong>", guaranteeing the timestamps it hands out are
<strong>globally monotonically increasing</strong> — a later request always gets a larger number than an earlier one. With this "<strong>global clock</strong>", writes scattered across different
machines gain an agreed-upon <strong>order</strong>, and reads can cleanly carve out an "<strong>up to this moment</strong>" snapshot with a single ts. Think of it as a bank's number dispenser: everyone
tears off a ticket, the numbers only go up, so "who came first" is never in dispute. The TSO lives in MixCoord (the Root role), and the Proxy <strong>takes a number</strong> from it on every read or
write. This humble dispenser is what underpins Milvus's <strong>temporal consistency</strong> in a distributed setting — a piece of infrastructure that looks simple yet is everywhere.</p>

<h2>Closing with a table: each component's role in one request</h2>
<p>Finally, a table aligning "<strong>who does what in one request</strong>", handy to revisit anytime:</p>

<table class="t">
  <tr><th>Component</th><th>In a write</th><th>In a query</th></tr>
  <tr><td><strong>SDK / client</strong></td><td>pack rows, issue insert</td><td>issue search(vector, topK), receive final results</td></tr>
  <tr><td><strong>Proxy</strong></td><td>validate, fill PK, stamp timestamp, hash by PK into shards, write WAL</td><td>fix guarantee ts, build plan, route, <strong>reduce across shards</strong></td></tr>
  <tr><td><strong>TSO</strong> (in MixCoord)</td><td>issue the write timestamp</td><td>the reference clock for the guarantee ts</td></tr>
  <tr><td><strong>StreamingNode / DataNode</strong></td><td>consume the log, build growing segments, flush to binlog</td><td>(mainly write-side)</td></tr>
  <tr><td><strong>DataCoord</strong> (in MixCoord)</td><td>track segment metadata, trigger flush/compaction</td><td>provide "which segments exist"</td></tr>
  <tr><td><strong>QueryNode · delegator</strong></td><td>(mainly read-side)</td><td>pick sealed+growing segments, wait for freshness, reduce node topK</td></tr>
  <tr><td><strong>segcore (C++)</strong></td><td>—</td><td>in-segment search, compute per-segment topK</td></tr>
</table>

<p>That is the full picture of "the life of a request": a <strong>write</strong> is "stamp a timestamp → log first → flush asynchronously → coordinator bookkeeps"; a <strong>read</strong> is "fix a
snapshot → scatter to shards and segments → C++ computes topK → reduce in layers". The two chains look different, yet share one set of <strong>timestamps</strong> and one <strong>project map</strong>. With
this "skeleton", every later part returns to some stop on these two chains and <strong>zooms it into a whole lesson</strong>.</p>

<p>One closing reminder that <strong>bridges past and future</strong>: every term in this lesson — timestamp, vchannel, WAL, growing segment, sealed segment, binlog, delegator, segcore, reduce — you
<strong>need not memorize every detail</strong> now; just build a <strong>sense of place</strong> for "which stop on which chain it sits at". Picture them as stations on a metro map: you don't yet know
what's around each station, but you know <strong>this line gets you there</strong>. The later lessons take you to <strong>get off at each station and explore its neighborhood</strong>. From the next part on,
we formally dive into the engine — starting with "how data is organized into collections, partitions, and segments".</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Write path</strong>: SDK → Proxy (validate, fill PK, <strong>stamp timestamp</strong>, hash by PK into shards) → append <strong>WAL</strong> → StreamingNode/DataNode consume → <strong>growing segment</strong> → flush to <strong>binlog</strong> → DataCoord bookkeeps.</li>
    <li><strong>Log as data</strong>: write a replayable log first, return on append; segments and indexes are materialized views of the log, recoverable by replay after a crash.</li>
    <li><strong>Query path</strong>: SDK → Proxy (<strong>fix guarantee ts</strong>, build plan, route) → QueryNode <strong>delegator</strong> picks sealed+growing → <strong>segcore (C++)</strong> per-segment topK → node reduce → Proxy <strong>reduce across shards</strong> → client.</li>
    <li><strong>Scatter-gather</strong>: each layer passes up only "the top K", so under huge data only a tiny candidate set flows over the network.</li>
    <li><strong>Timestamp is the shared key</strong>: writes stamp a ts, reads use a guarantee ts for a consistent snapshot; the consistency level trades "how fresh you see vs how long you wait" (details in <strong>Lesson 30</strong>).</li>
  </ul>
</div>
""",
}
