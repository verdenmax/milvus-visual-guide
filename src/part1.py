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
