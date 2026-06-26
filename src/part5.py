"""Part 5 · Indexing (L21–L24).

Bilingual lesson content for the index subsystem: the index service (DataCoord
schedules, a datanode worker builds — no indexnode), the Knowhere vector-index
families, the build-and-load data path, and scalar/full-text (tantivy) indexes.

Citations are grep-verified against /home/verden/course/milvus. Most vector
index names are Knowhere library `IndexEnum` constants, NOT milvus-core symbols;
only milvus-side enums that genuinely exist are attributed to milvus files.
"""

LESSON_21 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前四部分我们把"写入"讲透了：一行数据从 Proxy 进门、Append 进 WAL、攒成 growing 段、flush 成 binlog、再被 compaction 合并整洁。可到此为止，这些 sealed 段里的向量还只是一堆<strong>原始数据</strong>——要查"最像谁"，只能把查询向量和每一条库内向量<strong>逐个算距离</strong>（brute force，暴力扫描）。段一多、向量一多，这种扫法就慢得不可接受。
这一课起进入第五部分<strong>索引</strong>：先讲<strong>索引服务</strong>——谁来决定给哪些段建索引、谁真正动手建、建出来的东西又如何变成"可被查询加载"的资产。
关键结论先摆出来：<strong>建索引由 DataCoord 调度、由一个 worker（datanode）执行——没有独立的 indexnode 进程</strong>（回忆第 9、12 课的"协调器调度、节点执行"）。
</p>

<div class="card analogy">
  <div class="tag">📚 生活类比</div>
  还记得那座"一架书 = 一族册子"的图书馆吗？书都上架了，可读者想找"讲向量检索的书"，难道要一架一架翻过去？那太慢了。真正高效的图书馆，会为每个书架做一套<strong>目录卡片</strong>（索引）：按主题、按作者排好，查的人翻一翻卡片就能直奔目标。
  但目录不会自己长出来。<strong>馆长</strong>（DataCoord）盯着全馆的账本，决定"<strong>哪些书架还没目录、该建什么样的目录</strong>"，然后把任务派下去；真正<strong>埋头读书架、一张张写卡片</strong>的，是<strong>馆员助手</strong>（worker）。馆长只管<strong>调度与登记</strong>，不亲自抄卡片；助手只管<strong>干活</strong>，干完把卡片交回、登记进总目录。
  注意：这里<strong>没有第三个"专职抄卡片的部门"</strong>——抄卡片的活就由平时管书库的助手顺手兼着干。记住这一点，你就抓住了 Milvus 索引服务的骨架。
</div>

<h2>为什么需要索引服务：从暴力扫描到可加载的索引</h2>
<p>第 5 课讲 ANN 时我们就埋过伏笔：在高维向量上做<strong>精确</strong>的最近邻，注定要和每条数据比一遍，代价随数据量<strong>线性</strong>增长。一个集合可能有上亿条向量、成百上千个 sealed 段，逐条算距离的<strong>暴力扫描</strong>在线上根本扛不住。
索引就是为这件事而生：用一次<strong>离线的预处理</strong>（建图、聚类、量化……），把数据组织成一种"<strong>查的时候能跳过大半</strong>"的结构，从而把检索从"扫全部"压成"只看一小撮候选"。代价是这次预处理本身<strong>很重</strong>——要读出整段数据、跑复杂算法、再把结果写回存储。换句话说，索引是一笔<strong>"先苦后甜"</strong>的买卖：建的时候多花一次力气，之后每一次查询都<strong>反复受益</strong>，把这笔预处理成本摊薄到无数次检索头上。</p>

<p>正因为建索引<strong>又重又慢</strong>，它不能塞进写入主链路（那会拖垮写入延迟），必须作为一项<strong>后台任务</strong>，在数据<strong>已经 sealed（不可变）</strong>之后异步地做——这和上一课 compaction 的哲学一脉相承：<strong>把"快速记账"和"慢慢整理"解耦</strong>。
于是就需要一套"<strong>索引服务</strong>"来回答三个问题：<strong>给哪些段建</strong>（调度）、<strong>谁来建</strong>（执行）、<strong>建完怎么用</strong>（让 QueryNode 能加载）。这三问，正是这一课的主线。</p>

<p>这里值得把"建索引到底有多重"想具体些。以最常见的图索引 HNSW 为例：要给一个段里几十万、上百万条向量建图，算法得为<strong>每个点反复搜索它的近邻、连边、再分层组织</strong>，是个计算量随数据量超线性增长的活；IVF 系要先对全段向量<strong>聚类</strong>（跑 k-means）、再把每条向量分配到桶里；带量化的 IVF_PQ 还要额外训练<strong>码本</strong>。这些都意味着：建索引会<strong>吃掉大量 CPU/内存、读出整段数据、产出不小的索引文件</strong>。
把这样一桩重活放进写入链路，等于让每次写入都去等一次"全段重算"，写入延迟会瞬间崩坏。所以 Milvus 的选择毫无悬念——<strong>写入只管把数据快速落成段，建索引留到后台、在不可变的 sealed 段上慢慢做</strong>。这就是"索引必须是后台服务"背后那条朴素却硬核的工程理由。</p>

<div class="cols">
  <div class="col"><h4>没有索引（暴力扫描）</h4><p>查询向量要和段里<strong>每一条</strong>库内向量算距离，代价 <span class="mono">O(N)</span> 随数据量线性增长。段越多、向量越多，越慢。growing 段（还没建索引）就是这么查的——能用，但只适合<strong>小数据量</strong>。</p></div>
  <div class="col"><h4>有索引（ANN）</h4><p>预先把向量组织成图 / 倒排桶 / 量化码，查询时<strong>只探一小撮候选</strong>，代价接近 <span class="mono">O(log N)</span> 或亚线性。代价是建索引这次预处理很重，所以放到后台、在 sealed 段上做。</p></div>
</div>

<h2>谁拥有、谁构建：DataCoord 调度 + worker 执行</h2>
<p>这是本课<strong>最容易记错</strong>的一点，请务必坐实：建索引<strong>不存在</strong>一个叫 "indexnode" 的独立进程。它的分工，和第 12 课讲 DataCoord、第 17 课讲 DataNode 的主旋律完全一致——<strong>协调器管调度、节点管执行</strong>。</p>

<p><strong>DataCoord 是大脑</strong>：它拥有<strong>索引的元数据</strong>（哪个集合的哪个字段建了什么索引、每个段的索引到了哪个状态），代码在 <span class="mono">internal/datacoord/index_service.go</span>（对外 RPC，如 <span class="inline">CreateIndex</span>）、<span class="mono">index_meta.go</span>（元数据）、<span class="mono">index_inspector.go</span>（巡检：发现"还没建索引的 sealed 段"并生成构建任务）。它<strong>不</strong>亲自读向量、跑算法。</p>

<p><strong>worker 是手脚</strong>：真正读出段的 binlog、调 Knowhere 跑建索引算法、把索引文件写回对象存储的，是一个 <strong>worker</strong>——在当下的架构里，这个 worker 跑在 <strong>datanode</strong> 上（代码在 <span class="mono">internal/datanode/index/task_index.go</span> 的 <span class="inline">indexBuildTask</span>）。
它实现了 <span class="inline">workerpb.IndexNodeClient</span> 这个 gRPC 接口——<strong>注意：接口名里虽有 "IndexNode" 字样，但那只是历史遗留的协议名，并不代表存在一个独立的 indexnode 进程</strong>。这一点和第 17 课"流式写入交给 StreamingNode、DataNode 退居后台做 compaction 与建索引"完全吻合。</p>

<p>在 worker 内部，一个构建任务大致是三个动作：<strong>读</strong>——把段的向量 binlog 从对象存储拉出来、拼装成内存里的数据集；<strong>建</strong>——把这份数据集连同索引类型与参数交给 <strong>Knowhere</strong>，让它跑真正的算法（建图 / 聚类 / 训练码本）；<strong>写</strong>——把 Knowhere 的产物序列化成索引文件、写回对象存储，再把路径上报 DataCoord。
worker 是"<strong>纯手脚</strong>"：它完全<strong>不关心</strong>哪个段"<strong>该不该</strong>"建——那个决策完全归 DataCoord 的巡检器。这种"<strong>协调器决策、worker 计算</strong>"的干净切分，正是整套机制能横向扩展的根本：多加几个 worker，就能并行建更多段，而 DataCoord 始终是那个唯一记账的大脑。</p>

<div class="flow">
  <div class="node hl"><div class="nt">DataCoord</div><div class="nd">拥有索引元数据 · 巡检 sealed 段 · 生成构建任务</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">构建任务队列</div><div class="nd">每个 sealed 段一个任务 · 分派给 worker</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">datanode worker</div><div class="nd">实现 IndexNodeClient · 读 binlog · 调 Knowhere · 写索引文件</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">回写元数据</div><div class="nd">索引文件路径登记 · 段标记"已建索引"</div></div>
</div>

<h2>索引的生命周期：CreateIndex → 段级构建任务 → 索引文件 → 可加载</h2>
<p>把一次建索引<strong>从头到尾</strong>串起来，是理解索引服务的最好方式。它分四步，每一步都对应上面图里的一段：</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>CreateIndex（声明意图）</h4><p class="mono">index_service.go · CreateIndex</p><p>用户对某<strong>字段</strong>声明"我要建索引"（指定索引类型与参数）。DataCoord 把这条<strong>索引定义</strong>记进元数据——这是<strong>集合级</strong>的声明，<strong>还没</strong>真正去算任何一个段。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>段级构建任务</h4><p class="mono">index_inspector.go · createIndexForSegment</p><p>巡检器周期性扫描：凡是<strong>已 sealed、却还没建这套索引</strong>的段，就为它生成<strong>一个构建任务</strong>。一个集合有多少 sealed 段，就会派出多少个任务（每段一个）。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>worker 构建索引文件</h4><p class="mono">datanode/index · indexBuildTask</p><p>worker 领到任务：<strong>读出该段的向量 binlog</strong> → 调 <strong>Knowhere</strong> 跑建索引（建图 / 聚类 / 量化）→ 把产物<strong>索引文件</strong>写进对象存储（回忆第 18 课的 <span class="mono">index_files</span> 前缀）。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>登记 → 可加载</h4><p>worker 把索引文件路径<strong>回写 DataCoord 元数据</strong>，该段被标记为"<strong>已建索引</strong>"。至此索引成为一份<strong>持久资产</strong>；当集合被加载时，QueryNode 就能<strong>加载</strong>它来做 ANN（下一课、第 23 课展开）。</p></div></div>
</div>

<p>这条生命周期里有个常被忽略的关键：<strong>CreateIndex 是"声明"，不是"立即建好"</strong>。你调用 CreateIndex 之后，已存在的 sealed 段会被<strong>逐段异步</strong>地建；而<strong>之后新产生</strong>的 sealed 段（来自持续写入与 flush），也会被巡检器<strong>自动补建</strong>同一套索引。
所以"建索引"不是一次性动作，而是一个<strong>持续生效的策略</strong>：只要这套索引定义还在，DataCoord 就会确保"<strong>每一个 sealed 段最终都建上它</strong>"。这也解释了为什么 <span class="inline">GetIndexState</span> / <span class="inline">DescribeIndex</span> 这类接口要返回"已建/在建/总数"的进度——因为建索引天然是一个<strong>渐进收敛</strong>的过程。</p>

<h2>为什么"按段"建索引：粒度、失败与重试</h2>
<p>请特别留意上面反复出现的一个词：<strong>"每个 sealed 段一个构建任务"</strong>。索引服务的调度粒度，<strong>不是集合、不是分区，而是段</strong>。这个选择不是随意的，它直接来自前面几部分的设计：段是 Milvus 里<strong>不可变、可独立处理</strong>的最小数据单元——只有 sealed 段（数据已冻结）才适合建索引，因为建索引算法需要<strong>看到一份固定不变的数据</strong>；growing 段还在不断接收新行，建了也会立刻过时，所以 growing 段干脆<strong>不建索引</strong>，查询时对它用暴力扫描（下一课、第 23 课会再强调这一点）。</p>

<p>按段建索引带来三个实打实的好处。其一是<strong>可并行</strong>：成百上千个段的构建任务互不依赖，可以<strong>同时分派</strong>给多个 worker 并行跑，把一个大集合的"建索引"摊成许多小任务并发完成。其二是<strong>可增量</strong>：写入持续产生新段，巡检器只需为<strong>新出现的、还没建的段</strong>派任务，已经建好的段<strong>无需重做</strong>——索引随数据"自然生长"。其三是<strong>失败隔离</strong>：某个段的构建任务失败（worker 崩了、读 binlog 出错），影响的只是<strong>那一个段</strong>，DataCoord 重新派一次即可，不牵连其它已建好的段。</p>

<div class="cellgroup">
  <div class="cg-cap">同一集合的若干 sealed 段，各自独立成一个构建任务，可并行、可增量、失败可单独重试</div>
  <div class="cells">
    <div class="cell dim"><span class="lab">段 #1</span><span class="q">已建索引 ✓</span></div>
    <div class="cell dim"><span class="lab">段 #2</span><span class="q">已建索引 ✓</span></div>
    <div class="cell hl"><span class="lab">段 #3</span><span class="q">构建中…</span></div>
    <div class="cell sep"><span class="lab">段 #4</span><span class="q">失败→重试</span></div>
    <div class="cell"><span class="lab">段 #5（growing）</span><span class="q">不建·暴力扫描</span></div>
  </div>
</div>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="按段建索引：每个 sealed 段成为一个独立构建任务，可并行、可增量、失败只重试该段；growing 段不建、查询走暴力扫描">
    <text x="40" y="40" style="fill:var(--muted)">同一集合的若干段 —— 调度粒度 = 段（不是集合 / 分区）</text>
    <rect x="40" y="48" width="690" height="44" rx="9" style="fill:none;stroke:var(--accent);stroke-width:1.5"/>
    <rect x="52" y="56" width="126" height="28" rx="6" style="fill:var(--panel);stroke:var(--line)"/><text x="115" y="75" text-anchor="middle" style="fill:var(--ink)">seg #1</text>
    <rect x="186" y="56" width="126" height="28" rx="6" style="fill:var(--panel);stroke:var(--line)"/><text x="249" y="75" text-anchor="middle" style="fill:var(--ink)">seg #2</text>
    <rect x="320" y="56" width="126" height="28" rx="6" style="fill:var(--panel);stroke:var(--line)"/><text x="383" y="75" text-anchor="middle" style="fill:var(--ink)">seg #3</text>
    <rect x="454" y="56" width="126" height="28" rx="6" style="fill:var(--panel);stroke:var(--line)"/><text x="517" y="75" text-anchor="middle" style="fill:var(--ink)">seg #4</text>
    <rect x="588" y="56" width="130" height="28" rx="6" style="fill:var(--panel-2);stroke:var(--line)"/><text x="653" y="75" text-anchor="middle" style="fill:var(--muted)">growing</text>
    <line x1="115" y1="92" x2="115" y2="156" style="stroke:var(--line);stroke-width:1.5"/><path d="M115,156 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="249" y1="92" x2="249" y2="156" style="stroke:var(--line);stroke-width:1.5"/><path d="M249,156 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="383" y1="92" x2="383" y2="156" style="stroke:var(--line);stroke-width:1.5"/><path d="M383,156 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="517" y1="92" x2="517" y2="156" style="stroke:var(--line);stroke-width:1.5"/><path d="M517,156 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="653" y1="92" x2="653" y2="156" style="stroke:var(--line);stroke-width:1.5;stroke-dasharray:4 3"/><path d="M653,156 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <rect x="52" y="160" width="126" height="56" rx="8" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="115" y="184" text-anchor="middle" style="fill:var(--teal);font-weight:700">✓ 已建索引</text><text x="115" y="204" text-anchor="middle" style="fill:var(--muted)">无需重做</text>
    <rect x="186" y="160" width="126" height="56" rx="8" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="249" y="184" text-anchor="middle" style="fill:var(--teal);font-weight:700">✓ 已建索引</text><text x="249" y="204" text-anchor="middle" style="fill:var(--muted)">无需重做</text>
    <rect x="320" y="160" width="126" height="56" rx="8" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="383" y="184" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">⚙ 构建中</text><text x="383" y="204" text-anchor="middle" style="fill:var(--muted)">worker 并行跑</text>
    <rect x="454" y="160" width="126" height="56" rx="8" style="fill:var(--panel);stroke:var(--red);stroke-width:1.5"/><text x="517" y="184" text-anchor="middle" style="fill:var(--red);font-weight:700">✗ 失败</text><text x="517" y="204" text-anchor="middle" style="fill:var(--red)">→ 重试这一个</text>
    <rect x="588" y="160" width="130" height="56" rx="8" style="fill:var(--panel-2);stroke:var(--line)"/><text x="653" y="184" text-anchor="middle" style="fill:var(--muted);font-weight:700">不建</text><text x="653" y="204" text-anchor="middle" style="fill:var(--muted)">查询走暴力扫描</text>
    <path d="M580,188 C616,188 612,120 524,98" style="fill:none;stroke:var(--red);stroke-width:1.5;stroke-dasharray:5 4"/><path d="M524,98 l11,-1 l-5,-9 z" style="fill:var(--red)"/>
    <text x="384" y="246" text-anchor="middle" style="fill:var(--muted)">段级任务：可并行 · 可增量 · 失败只影响这一段</text>
  </svg>
  <div class="figcap"><b>调度粒度是"段"，不是集合</b>：每个不可变的 <b>sealed 段</b>独立成一个构建任务——成百上千个任务<b>互不依赖、可并行</b>；新段来了只派新任务（<b>可增量</b>）；某个任务失败只<b>重试那一个段</b>，不牵连别人。<b>growing 段不建索引</b>，查询时对它走暴力扫描。</div>
</div>

<p>正因为有这套"<strong>段级任务 + 状态机 + 重试</strong>"的机制，索引服务才能在一个<strong>持续写入、节点会崩、网络会抖</strong>的分布式环境里，稳稳地把"每个段最终都建上索引"这件事推进到底。
这也是 DataCoord 要<strong>拥有索引元数据</strong>的根本原因：它必须为每个段<strong>记账</strong>——这个段建到了哪一步、用的哪份索引定义、索引文件落在哪里、失败了几次。没有这本账，分布式下的"渐进收敛"就无从谈起。你可以把 <span class="mono">index_meta.go</span> 理解成这本"<strong>索引总账</strong>"，把 <span class="mono">index_inspector.go</span> 理解成那位<strong>不断对账、发现缺口就补派任务</strong>的巡检员。</p>

<table class="t">
  <tr><th>阶段</th><th>谁负责</th><th>产出 / 状态</th></tr>
  <tr><td><strong>CreateIndex</strong></td><td>Proxy→DataCoord</td><td>把索引定义写进元数据（集合级声明）</td></tr>
  <tr><td><strong>巡检 &amp; 派任务</strong></td><td>DataCoord（inspector）</td><td>每个未建索引的 sealed 段 → 一个构建任务</td></tr>
  <tr><td><strong>构建</strong></td><td>datanode worker</td><td>读 binlog · 调 Knowhere · 写索引文件到对象存储</td></tr>
  <tr><td><strong>登记</strong></td><td>worker→DataCoord</td><td>索引文件路径入元数据 · 段标记"已建索引"</td></tr>
  <tr><td><strong>加载</strong></td><td>QueryNode</td><td>集合加载时把索引读入内存 / mmap，供 ANN 检索</td></tr>
</table>

<p>关于<strong>auto-index（自动索引）</strong>：很多用户并不想纠结"该选 HNSW 还是 IVF、参数怎么调"。Milvus 提供 <strong>AUTOINDEX</strong>——你只声明"给这个字段建索引"，由系统<strong>按字段类型与数据规模自动挑选</strong>一套合理的索引类型与参数。
它的本质仍然走上面这条完全相同的链路：CreateIndex 声明 → 巡检派任务 → worker 用 Knowhere 构建 → 登记可加载；只是"选哪种索引、参数填多少"这步从<strong>用户手填</strong>变成了<strong>系统代选</strong>。对初学者，AUTOINDEX 是最省心的默认；想精调时再换成具体类型（下一课逐一拆解各家索引）。</p>

<p>这里还要把"索引服务"和后面两课的关系<strong>提前接上</strong>，免得你把它们割裂着记。本课讲的是"<strong>建索引这件事如何被调度与执行</strong>"，是<strong>控制流</strong>的视角；下一课（第 22 课）会钻进 worker 调用的那个 <strong>Knowhere</strong> 库内部，看它到底有哪些<strong>向量索引家族</strong>（FLAT/IVF/HNSW/DiskANN……）、各自的取舍与参数；再下一课（第 23 课）则顺着<strong>数据流</strong>，把"sealed 段的原始向量 → worker 构建 → 索引文件落对象存储 → QueryNode 加载进内存或 mmap"这条物理路径走一遍。
三课是同一件事的三个切面：<strong>谁调度（本课）、用什么算法（第 22 课）、数据怎么流动（第 23 课）</strong>。把它们叠在一起，你才算真正看懂了 Milvus 的索引。</p>

<p>最后留一个值得回味的设计观感：索引服务几乎<strong>完整复刻</strong>了 compaction 的那套范式——都由 <strong>DataCoord 调度</strong>、都在 <strong>datanode worker</strong> 上执行、都只作用于<strong>不可变的 sealed 段</strong>、都把结果<strong>写回对象存储</strong>再<strong>原子地登记进元数据</strong>、都是"<strong>不打扰写入主链路</strong>"的后台任务。
这不是巧合，而是 Milvus 反复使用的同一套<strong>后台维护任务骨架</strong>：把"慢而重、但能让读更快"的活，从前台剥离，交给协调器在系统空闲时摊销地做。理解了 compaction，你几乎<strong>不费力</strong>就能理解索引服务；而理解了这套通用骨架，你也就握住了 Milvus 整个"写完之后"世界的钥匙。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/datacoord/index_service.go</span><span class="ln">CreateIndex：声明索引定义，由 DataCoord 受理（节选）</span></div>
  <pre><span class="cm">// DataCoord 对外 RPC：受理"给某字段建索引"的声明，写进索引元数据。</span>
<span class="cm">// 注意：这里只"登记意图"，真正的逐段构建由 inspector 异步派发给 worker。</span>
<span class="kw">func</span> (s *Server) <span class="fn">CreateIndex</span>(ctx context.Context, req *indexpb.CreateIndexRequest) (*commonpb.Status, error) {
    <span class="cm">// 健康检查、参数校验、分配 indexID……</span>
    <span class="cm">// 把 index 定义写入 meta；之后 index_inspector 巡检 sealed 段、逐段派构建任务。</span>
}</pre>
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：sealed 段里的向量若不建索引，就只能<strong>暴力逐条扫</strong>（慢）。索引服务把"建索引"做成一项<strong>后台任务</strong>——<strong>DataCoord 调度</strong>（<span class="mono">index_service.go</span>/<span class="mono">index_meta.go</span>/<span class="mono">index_inspector.go</span>：拥有元数据、巡检 sealed 段、<strong>每段派一个构建任务</strong>），<strong>datanode worker 执行</strong>（<span class="inline">indexBuildTask</span>，实现 <span class="inline">workerpb.IndexNodeClient</span>，<strong>没有独立 indexnode 进程</strong>：读 binlog、调 Knowhere、写索引文件、回写元数据）。CreateIndex 是<strong>声明</strong>而非立即建好，新段会被<strong>自动补建</strong>；AUTOINDEX 让系统代选类型与参数。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>为何要索引</strong>：不建索引只能暴力 <span class="mono">O(N)</span> 逐条算距离；索引用一次重的离线预处理换查询时的"只看一小撮候选"。</li>
    <li><strong>调度 vs 执行</strong>：DataCoord 拥有索引元数据并调度（<span class="mono">index_service.go</span> 的 <span class="inline">CreateIndex</span>、<span class="mono">index_inspector.go</span>）；datanode worker 执行（<span class="inline">indexBuildTask</span>）。</li>
    <li><strong>没有 indexnode</strong>：worker 实现 <span class="inline">workerpb.IndexNodeClient</span>，但那只是协议名——构建跑在 datanode 上，<strong>不存在</strong>独立 indexnode 进程（呼应第 9、17 课）。</li>
    <li><strong>生命周期</strong>：CreateIndex（声明）→ 每个 sealed 段一个构建任务 → worker 读 binlog·调 Knowhere·写索引文件 → 登记后可被 QueryNode 加载。</li>
    <li><strong>声明而非即建</strong>：已存在的段逐段异步建，新 sealed 段自动补建；进度可经 <span class="inline">GetIndexState</span>/<span class="inline">DescribeIndex</span> 查询。</li>
    <li><strong>AUTOINDEX</strong>：系统按字段类型与规模自动挑选索引类型与参数，链路不变，只是把"选型"自动化。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The first four parts nailed the write path: a row enters through the Proxy, is Appended to the WAL, accumulates into a growing segment, is flushed to binlogs, and is later merged tidy by compaction. But up to here, the vectors in those sealed segments are still just <strong>raw data</strong> — to ask "most like which?", you can only compute the distance from the query vector to <strong>every single</strong> stored vector (brute force). With many segments and many vectors, that scan becomes unacceptably slow.
From here we enter Part 5, <strong>Indexing</strong>: first the <strong>index service</strong> — who decides which segments get an index, who actually builds it, and how the result becomes a "loadable" asset.
The headline conclusion up front: <strong>index build is scheduled by DataCoord and executed by a worker (a datanode) — there is NO separate indexnode process</strong> (recall the "coordinators schedule, nodes execute" theme from Lessons 9 and 12).
</p>

<div class="card analogy">
  <div class="tag">📮 Analogy</div>
  Remember that library, "one bookshelf = a family of volumes"? The books are all shelved, but if a reader wants "books on vector search," must they walk the shelves one by one? Too slow. An efficient library builds a set of <strong>catalog cards</strong> (an index) for every shelf: sorted by topic and author, so a searcher flips a few cards and goes straight to the target.
  But the catalog doesn't grow itself. The <strong>head librarian</strong> (DataCoord) watches the whole library's ledger and decides "<strong>which shelves still lack a catalog, and what kind to build</strong>," then hands out tasks; the one who actually <strong>buries themselves in the shelf and writes cards</strong> is an <strong>assistant</strong> (a worker). The head librarian only <strong>schedules and registers</strong>, never copies cards; the assistant only <strong>does the work</strong>, then hands the cards back and registers them in the master catalog.
  Note: there is <strong>no third "dedicated card-copying department"</strong> — the card-copying is done on the side by the same assistant who usually tends the stacks. Grasp this and you have the skeleton of Milvus's index service.
</div>

<h2>Why an index service: from brute force to a loadable index</h2>
<p>Lesson 5 (on ANN) planted the seed: an <strong>exact</strong> nearest-neighbor over high-dimensional vectors must compare against every datum, with cost growing <strong>linearly</strong> with size. A collection may hold hundreds of millions of vectors across hundreds or thousands of sealed segments; a per-row <strong>brute-force</strong> scan simply can't hold up in production.
An index exists for exactly this: one <strong>offline preprocessing</strong> pass (build a graph, cluster, quantize…) organizes the data into a structure that lets a query <strong>skip most of it</strong>, compressing retrieval from "scan everything" to "look at a small candidate set." The price is that this preprocessing is itself <strong>heavy</strong> — read out a whole segment, run a complex algorithm, write the result back to storage. In other words, an index is a <strong>"pain now, gain later"</strong> bargain: spend extra effort once at build time, and <strong>every subsequent query reaps the benefit</strong>, amortizing that preprocessing cost across countless retrievals.</p>

<p>Precisely because building an index is <strong>heavy and slow</strong>, it can't sit in the write hot path (it would wreck write latency); it must be a <strong>background task</strong>, done asynchronously after data is <strong>sealed (immutable)</strong> — the very same philosophy as last lesson's compaction: <strong>decouple "fast bookkeeping" from "slow tidying."</strong>
So we need an "<strong>index service</strong>" to answer three questions: <strong>which segments to build for</strong> (schedule), <strong>who builds</strong> (execute), and <strong>how the result is used</strong> (let QueryNode load it). Those three questions are this lesson's through-line.</p>

<p>It's worth making "just how heavy is an index build" concrete. Take the most common graph index, HNSW: to build a graph over hundreds of thousands or millions of vectors in a segment, the algorithm must <strong>repeatedly search each point's neighbors, link edges, and organize layers</strong> — work whose cost grows super-linearly with size. The IVF family must first <strong>cluster</strong> the whole segment's vectors (run k-means) and assign each vector to a bucket; quantized IVF_PQ additionally trains a <strong>codebook</strong>. All of this means a build <strong>eats lots of CPU/memory, reads out the whole segment, and produces sizeable index files</strong>.
Putting such a heavy job in the write path would make every write wait for a "full-segment recompute," instantly destroying write latency. So Milvus's choice is a foregone conclusion — <strong>writes only land data into segments fast, and index building is left to the background, done slowly on immutable sealed segments</strong>. That is the plain yet hard engineering reason behind "an index must be a background service."</p>

<div class="cols">
  <div class="col"><h4>No index (brute force)</h4><p>The query vector computes a distance against <strong>every single</strong> stored vector in a segment, cost <span class="mono">O(N)</span> growing linearly with size. More segments, more vectors, slower. Growing segments (not yet indexed) are queried exactly this way — it works, but only for <strong>small data</strong>.</p></div>
  <div class="col"><h4>With an index (ANN)</h4><p>Vectors are pre-organized into a graph / inverted buckets / quantized codes; a query <strong>probes only a small candidate set</strong>, cost approaching <span class="mono">O(log N)</span> or sublinear. The cost is the heavy one-time build, so it runs in the background on sealed segments.</p></div>
</div>

<h2>Who owns, who builds: DataCoord schedules + a worker executes</h2>
<p>This is the point <strong>most easily misremembered</strong>, so nail it down: index build has <strong>no</strong> separate process called "indexnode." Its division of labor matches the main theme of Lesson 12 (DataCoord) and Lesson 17 (DataNode) exactly — <strong>coordinators schedule, nodes execute</strong>.</p>

<p><strong>DataCoord is the brain</strong>: it owns the <strong>index metadata</strong> (which field of which collection has what index, and the state of each segment's index), with code in <span class="mono">internal/datacoord/index_service.go</span> (the outward RPCs such as <span class="inline">CreateIndex</span>), <span class="mono">index_meta.go</span> (metadata), and <span class="mono">index_inspector.go</span> (inspection: find "sealed segments not yet indexed" and emit build tasks). It does <strong>not</strong> read vectors or run algorithms itself.</p>

<p><strong>The worker is the hands</strong>: the one that actually reads a segment's binlogs, calls Knowhere to run the build algorithm, and writes index files back to object storage is a <strong>worker</strong> — in today's architecture, that worker runs on a <strong>datanode</strong> (code in <span class="mono">internal/datanode/index/task_index.go</span>, the <span class="inline">indexBuildTask</span>).
It implements the gRPC interface <span class="inline">workerpb.IndexNodeClient</span> — <strong>note: despite the "IndexNode" in the interface name, that is only a legacy protocol name and does NOT imply a separate indexnode process</strong>. This dovetails with Lesson 17: streaming writes went to StreamingNode, and the DataNode stepped back to do compaction and index builds.</p>

<p>Inside the worker, one build task is roughly three moves: <strong>read</strong> — pull the segment's vector binlogs out of object storage and assemble them into an in-memory dataset; <strong>build</strong> — hand that dataset to <strong>Knowhere</strong> with the index type and params and let it run the actual algorithm (build a graph / cluster / train a codebook); <strong>write</strong> — serialize Knowhere's output into index files and write them back to object storage, then report the paths to DataCoord. The worker is "just hands": it knows nothing about which segment "should" be built — that decision belongs entirely to DataCoord's inspector. This clean split of "the coordinator decides, the worker computes" is exactly what makes the whole thing scalable: add more workers and more segments build in parallel, with DataCoord still the single brain keeping the books.</p>

<div class="flow">
  <div class="node hl"><div class="nt">DataCoord</div><div class="nd">owns index meta · inspects sealed segments · emits build tasks</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">build task queue</div><div class="nd">one task per sealed segment · dispatched to a worker</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">datanode worker</div><div class="nd">implements IndexNodeClient · reads binlogs · calls Knowhere · writes index files</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">write back meta</div><div class="nd">register index-file paths · mark segment "indexed"</div></div>
</div>

<h2>The index lifecycle: CreateIndex → per-segment build task → index files → loadable</h2>
<p>Stringing one build <strong>end to end</strong> is the best way to understand the index service. It is four steps, each mapping to a stage in the diagram above:</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>CreateIndex (declare intent)</h4><p class="mono">index_service.go · CreateIndex</p><p>A user declares "build an index" on a <strong>field</strong> (with an index type and params). DataCoord records this <strong>index definition</strong> into metadata — a <strong>collection-level</strong> declaration that has <strong>not</strong> yet computed any segment.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Per-segment build task</h4><p class="mono">index_inspector.go · createIndexForSegment</p><p>The inspector periodically scans: any segment that is <strong>sealed yet not built for this index</strong> gets <strong>one build task</strong>. As many sealed segments as a collection has, that many tasks go out (one per segment).</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Worker builds index files</h4><p class="mono">datanode/index · indexBuildTask</p><p>The worker takes a task: <strong>read the segment's vector binlogs</strong> → call <strong>Knowhere</strong> to build (graph / cluster / quantize) → write the resulting <strong>index files</strong> to object storage (recall Lesson 18's <span class="mono">index_files</span> prefix).</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Register → loadable</h4><p>The worker <strong>writes the index-file paths back to DataCoord's metadata</strong> and the segment is marked "<strong>indexed</strong>." The index is now a <strong>durable asset</strong>; when the collection is loaded, QueryNode can <strong>load</strong> it for ANN (next lesson, and Lesson 23).</p></div></div>
</div>

<p>One often-missed key in this lifecycle: <strong>CreateIndex is a "declaration," not "built instantly."</strong> After you call CreateIndex, the already-existing sealed segments are built <strong>segment by segment, asynchronously</strong>; and segments produced <strong>later</strong> (from continued writes and flushes) are <strong>auto-built</strong> with the same index by the inspector.
So "building an index" is not a one-shot action but a <strong>continuously-in-effect policy</strong>: as long as the index definition exists, DataCoord ensures "<strong>every sealed segment eventually gets it</strong>." This also explains why interfaces like <span class="inline">GetIndexState</span> / <span class="inline">DescribeIndex</span> report progress ("built/building/total") — building an index is inherently a <strong>gradually-converging</strong> process.</p>

<h2>Why build "per segment": granularity, failure, and retry</h2>
<p>Notice a phrase that keeps recurring above: <strong>"one build task per sealed segment."</strong> The index service's scheduling granularity is <strong>not the collection, not the partition, but the segment</strong>. This is no arbitrary choice; it falls straight out of earlier parts: a segment is Milvus's smallest <strong>immutable, independently-processable</strong> unit of data — only a sealed segment (data frozen) is fit for indexing, because the build algorithm needs to see <strong>a fixed, unchanging dataset</strong>; a growing segment is still receiving new rows, so an index built on it would instantly go stale. Hence growing segments are simply <strong>not indexed</strong> and are queried by brute force (a point the next lesson and Lesson 23 re-emphasize).</p>

<p>Per-segment indexing brings three concrete benefits. First, <strong>parallelism</strong>: the build tasks for hundreds or thousands of segments are mutually independent and can be <strong>dispatched at once</strong> across many workers, spreading a large collection's "build" into many small concurrent tasks. Second, <strong>incrementality</strong>: writes keep producing new segments, and the inspector only needs to emit tasks for the <strong>newly-appeared, not-yet-built</strong> segments; already-built ones <strong>need no redo</strong> — the index "grows naturally" with the data. Third, <strong>failure isolation</strong>: if one segment's build task fails (a worker crashed, a binlog read errored), only <strong>that one segment</strong> is affected; DataCoord simply re-dispatches it, without touching other already-built segments.</p>

<div class="cellgroup">
  <div class="cg-cap">Several sealed segments of one collection, each an independent build task: parallel, incremental, individually retriable on failure</div>
  <div class="cells">
    <div class="cell dim"><span class="lab">seg #1</span><span class="q">indexed ✓</span></div>
    <div class="cell dim"><span class="lab">seg #2</span><span class="q">indexed ✓</span></div>
    <div class="cell hl"><span class="lab">seg #3</span><span class="q">building…</span></div>
    <div class="cell sep"><span class="lab">seg #4</span><span class="q">failed→retry</span></div>
    <div class="cell"><span class="lab">seg #5 (growing)</span><span class="q">no index · brute force</span></div>
  </div>
</div>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="Per-segment index build: each sealed segment becomes an independent build task — parallel, incremental, and a failure only retries that one segment; growing segments are not built and are brute-force scanned at query time">
    <text x="40" y="40" style="fill:var(--muted)">segments of one collection —— scheduling granularity = segment (not collection / partition)</text>
    <rect x="40" y="48" width="690" height="44" rx="9" style="fill:none;stroke:var(--accent);stroke-width:1.5"/>
    <rect x="52" y="56" width="126" height="28" rx="6" style="fill:var(--panel);stroke:var(--line)"/><text x="115" y="75" text-anchor="middle" style="fill:var(--ink)">seg #1</text>
    <rect x="186" y="56" width="126" height="28" rx="6" style="fill:var(--panel);stroke:var(--line)"/><text x="249" y="75" text-anchor="middle" style="fill:var(--ink)">seg #2</text>
    <rect x="320" y="56" width="126" height="28" rx="6" style="fill:var(--panel);stroke:var(--line)"/><text x="383" y="75" text-anchor="middle" style="fill:var(--ink)">seg #3</text>
    <rect x="454" y="56" width="126" height="28" rx="6" style="fill:var(--panel);stroke:var(--line)"/><text x="517" y="75" text-anchor="middle" style="fill:var(--ink)">seg #4</text>
    <rect x="588" y="56" width="130" height="28" rx="6" style="fill:var(--panel-2);stroke:var(--line)"/><text x="653" y="75" text-anchor="middle" style="fill:var(--muted)">growing</text>
    <line x1="115" y1="92" x2="115" y2="156" style="stroke:var(--line);stroke-width:1.5"/><path d="M115,156 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="249" y1="92" x2="249" y2="156" style="stroke:var(--line);stroke-width:1.5"/><path d="M249,156 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="383" y1="92" x2="383" y2="156" style="stroke:var(--line);stroke-width:1.5"/><path d="M383,156 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="517" y1="92" x2="517" y2="156" style="stroke:var(--line);stroke-width:1.5"/><path d="M517,156 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="653" y1="92" x2="653" y2="156" style="stroke:var(--line);stroke-width:1.5;stroke-dasharray:4 3"/><path d="M653,156 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <rect x="52" y="160" width="126" height="56" rx="8" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="115" y="184" text-anchor="middle" style="fill:var(--teal);font-weight:700">✓ indexed</text><text x="115" y="204" text-anchor="middle" style="fill:var(--muted)">no rebuild</text>
    <rect x="186" y="160" width="126" height="56" rx="8" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="249" y="184" text-anchor="middle" style="fill:var(--teal);font-weight:700">✓ indexed</text><text x="249" y="204" text-anchor="middle" style="fill:var(--muted)">no rebuild</text>
    <rect x="320" y="160" width="126" height="56" rx="8" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="383" y="184" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">⚙ building</text><text x="383" y="204" text-anchor="middle" style="fill:var(--muted)">workers in parallel</text>
    <rect x="454" y="160" width="126" height="56" rx="8" style="fill:var(--panel);stroke:var(--red);stroke-width:1.5"/><text x="517" y="184" text-anchor="middle" style="fill:var(--red);font-weight:700">✗ failed</text><text x="517" y="204" text-anchor="middle" style="fill:var(--red)">→ retry this one</text>
    <rect x="588" y="160" width="130" height="56" rx="8" style="fill:var(--panel-2);stroke:var(--line)"/><text x="653" y="184" text-anchor="middle" style="fill:var(--muted);font-weight:700">no index</text><text x="653" y="204" text-anchor="middle" style="fill:var(--muted)">brute-force scan</text>
    <path d="M580,188 C616,188 612,120 524,98" style="fill:none;stroke:var(--red);stroke-width:1.5;stroke-dasharray:5 4"/><path d="M524,98 l11,-1 l-5,-9 z" style="fill:var(--red)"/>
    <text x="384" y="246" text-anchor="middle" style="fill:var(--muted)">per-segment tasks: parallel · incremental · failure-isolated</text>
  </svg>
  <div class="figcap"><b>The granularity is the "segment", not the collection</b>: each immutable <b>sealed segment</b> becomes one independent build task — hundreds are <b>independent and run in parallel</b>; a new segment just gets a new task (<b>incremental</b>); a failed task <b>retries only that segment</b>, not the others. <b>Growing segments aren't indexed</b> — a query brute-force scans them.</div>
</div>

<p>It is exactly this "<strong>per-segment task + state machine + retry</strong>" mechanism that lets the index service, in a distributed environment of <strong>continuous writes, crashing nodes, and flaky networks</strong>, steadily drive "every segment eventually gets indexed" to completion.
This is also the root reason DataCoord must <strong>own the index metadata</strong>: it has to <strong>keep books</strong> for every segment — which step this segment reached, which index definition it uses, where its index files live, how many times it failed. Without this ledger, "gradual convergence" under distribution is impossible. Think of <span class="mono">index_meta.go</span> as that "<strong>index ledger</strong>," and <span class="mono">index_inspector.go</span> as the inspector who <strong>keeps reconciling and re-dispatches a task wherever a gap appears</strong>.</p>

<table class="t">
  <tr><th>Stage</th><th>Who</th><th>Output / state</th></tr>
  <tr><td><strong>CreateIndex</strong></td><td>Proxy→DataCoord</td><td>write the index definition to metadata (collection-level)</td></tr>
  <tr><td><strong>Inspect &amp; emit tasks</strong></td><td>DataCoord (inspector)</td><td>each not-yet-built sealed segment → one build task</td></tr>
  <tr><td><strong>Build</strong></td><td>datanode worker</td><td>read binlogs · call Knowhere · write index files to object storage</td></tr>
  <tr><td><strong>Register</strong></td><td>worker→DataCoord</td><td>index-file paths into metadata · mark segment "indexed"</td></tr>
  <tr><td><strong>Load</strong></td><td>QueryNode</td><td>on collection load, read the index into memory / mmap for ANN</td></tr>
</table>

<p>On <strong>auto-index</strong>: many users don't want to agonize over "HNSW or IVF, and how to tune the params." Milvus offers <strong>AUTOINDEX</strong> — you merely declare "build an index on this field," and the system <strong>auto-picks</strong> a reasonable index type and params by field type and data scale.
Its essence still runs the exact same chain: CreateIndex declares → inspector emits tasks → worker builds with Knowhere → register as loadable; only the "which index, what params" step shifts from <strong>user-specified</strong> to <strong>system-chosen</strong>. For beginners, AUTOINDEX is the most worry-free default; switch to a concrete type when you want to fine-tune (next lesson dissects each index family).</p>

<p>Let's also <strong>connect ahead</strong> how this "index service" relates to the next two lessons, so you don't memorize them in isolation. This lesson is about "<strong>how the act of building an index is scheduled and executed</strong>" — a <strong>control-flow</strong> view. The next lesson (22) drills into the <strong>Knowhere</strong> library that the worker calls, seeing exactly which <strong>vector-index families</strong> exist (FLAT/IVF/HNSW/DiskANN…), their tradeoffs and params. The lesson after (23) follows the <strong>data flow</strong>, walking the physical path "sealed segment's raw vectors → worker builds → index files to object storage → QueryNode loads into memory or mmap."
The three are three facets of one thing: <strong>who schedules (this lesson), with what algorithm (Lesson 22), how data flows (Lesson 23)</strong>. Stack them together and you truly understand Milvus indexing.</p>

<p>Finally, a design observation worth savoring: the index service almost <strong>exactly mirrors</strong> compaction's paradigm — both are <strong>scheduled by DataCoord</strong>, both <strong>execute on a datanode worker</strong>, both act only on <strong>immutable sealed segments</strong>, both <strong>write results to object storage</strong> and then <strong>atomically register them into metadata</strong>, and both are <strong>background tasks that don't disturb the write hot path</strong>.
This is no coincidence but the same <strong>background-maintenance skeleton</strong> Milvus reuses: peel the "slow and heavy, but makes reads faster" work off the foreground and let the coordinator amortize it when the system is idle. Once you understand compaction, you understand the index service <strong>almost for free</strong>; and once you understand this generic skeleton, you hold the key to Milvus's entire "after the write" world.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/datacoord/index_service.go</span><span class="ln">CreateIndex: declare the index definition, accepted by DataCoord (excerpt)</span></div>
  <pre><span class="cm">// DataCoord's outward RPC: accept the "build an index on a field" declaration, write it to index meta.</span>
<span class="cm">// Note: this only "registers intent"; the per-segment build is dispatched asynchronously by the inspector to a worker.</span>
<span class="kw">func</span> (s *Server) <span class="fn">CreateIndex</span>(ctx context.Context, req *indexpb.CreateIndexRequest) (*commonpb.Status, error) {
    <span class="cm">// health check, param validation, allocate indexID...</span>
    <span class="cm">// write the index definition to meta; later index_inspector inspects sealed segments and emits per-segment build tasks.</span>
}</pre>
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: vectors in a sealed segment, if unindexed, can only be <strong>brute-force scanned row by row</strong> (slow). The index service makes "building an index" a <strong>background task</strong> — <strong>DataCoord schedules</strong> (<span class="mono">index_service.go</span>/<span class="mono">index_meta.go</span>/<span class="mono">index_inspector.go</span>: owns metadata, inspects sealed segments, emits <strong>one build task per segment</strong>), and a <strong>datanode worker executes</strong> (<span class="inline">indexBuildTask</span>, implementing <span class="inline">workerpb.IndexNodeClient</span>, with <strong>no separate indexnode process</strong>: read binlogs, call Knowhere, write index files, write back meta). CreateIndex is a <strong>declaration</strong>, not an instant build; new segments are <strong>auto-built</strong>; AUTOINDEX lets the system pick the type and params.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Why index</strong>: without one, you can only brute-force <span class="mono">O(N)</span> per-row distances; an index trades a heavy offline preprocess for "look at a small candidate set" at query time.</li>
    <li><strong>Schedule vs execute</strong>: DataCoord owns index metadata and schedules (<span class="inline">CreateIndex</span> in <span class="mono">index_service.go</span>, <span class="mono">index_inspector.go</span>); a datanode worker executes (<span class="inline">indexBuildTask</span>).</li>
    <li><strong>No indexnode</strong>: the worker implements <span class="inline">workerpb.IndexNodeClient</span>, but that's just a protocol name — the build runs on a datanode; there is <strong>no</strong> separate indexnode process (echoing Lessons 9 and 17).</li>
    <li><strong>Lifecycle</strong>: CreateIndex (declare) → one build task per sealed segment → worker reads binlogs · calls Knowhere · writes index files → registered, then loadable by QueryNode.</li>
    <li><strong>Declare, not instant</strong>: existing segments build asynchronously one by one, new sealed segments auto-build; progress is queryable via <span class="inline">GetIndexState</span>/<span class="inline">DescribeIndex</span>.</li>
    <li><strong>AUTOINDEX</strong>: the system auto-picks index type and params by field type and scale; the chain is unchanged, only the type-selection is automated.</li>
  </ul>
</div>
""",
}

LESSON_22 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课我们看清了"谁来建索引"：DataCoord 调度、datanode worker 执行。但 worker 在那一步只是<strong>调了一个库</strong>——真正懂"如何把向量组织成可快速检索的结构"的，是 Milvus 依赖的上游向量检索内核 <strong>Knowhere</strong>。
这一课就钻进 Knowhere，看它提供了哪几大<strong>向量索引家族</strong>（FLAT、IVF 系、HNSW、DiskANN、SCANN、GPU、稀疏），各自是<strong>什么思路</strong>、有<strong>哪些关键参数</strong>、<strong>何时该选谁</strong>。
一句重要的提醒先放这儿：下面绝大多数索引名（HNSW、IVF_SQ8、SCANN、CAGRA……）是 <strong>Knowhere 库里的 <span class="inline">IndexEnum</span> 常量</strong>，<strong>并不</strong>定义在 Milvus 自己的代码里；只有少数枚举在 Milvus core 中被引用，本课会精确区分。
</p>

<div class="card analogy">
  <div class="tag">📚 生活类比</div>
  想象你管着一个堆满货物的大仓库，任务是"<strong>来一个样品，找出最像它的几件货</strong>"。你有好几种组织货架的办法：
  <strong>最笨但最准</strong>的，是把<strong>每一件货都和样品比一遍</strong>（这就是 FLAT，暴力扫描，召回 100% 但慢）；
  <strong>聪明一点</strong>，先把货<strong>按相似度分区</strong>（聚类），样品先定位到最近的几个区、只翻这几个区（这是 IVF：先粗分桶，再桶内细找）；
  <strong>更聪明</strong>，给货物之间<strong>架一张"近邻跳板"的网</strong>，从任意一件货出发，顺着跳板几步就能跳到最像样品的那片（这是 HNSW：可导航的小世界图）；
  <strong>省空间</strong>的办法是把每件货<strong>压成一张缩略图</strong>再比（这是 PQ 量化：用近似换内存）；
  <strong>放不下内存</strong>时，就把货架<strong>摊到磁盘上</strong>、只把索引骨架留在内存（这是 DiskANN）。
  没有"最好"的办法，只有"<strong>在速度、内存、召回、成本之间，你愿意怎么取舍</strong>"。Knowhere 就是把这些办法<strong>都备齐</strong>的工具箱。
</div>

<h2>Knowhere 是什么：Milvus 的向量检索内核</h2>
<p><strong>Knowhere</strong> 是 Milvus 项目维护的一个<strong>独立的、上游的</strong>向量检索库（C++ 为主，对接 FAISS、HNSWlib、DiskANN、cuVS 等多种底层实现，并统一封装）。Milvus 的 C++ core 在<strong>建索引</strong>和<strong>做向量检索</strong>这两件最核心的算法活上，都是<strong>调用 Knowhere</strong> 来完成的——你可以把它理解成 Milvus 的"<strong>向量计算引擎</strong>"。
回忆第 2 课讲的"三语言分工"：Go 管分布式与调度、C++ 管单机的存储与计算、Rust 管全文索引；而 C++ 这一层里，<strong>向量索引与检索的具体算法</strong>就外包给了 Knowhere 这个专门的库。</p>

<p>为什么要把算法<strong>单独抽成一个库</strong>，而不是和 Milvus core 混写在一起？因为向量检索是一个<strong>飞速演进、又高度专业</strong>的领域：今天 HNSW 当红、明天 DiskANN、后天 GPU 上的 CAGRA，底层还要对接 FAISS、cuVS 等一堆各有所长的实现。把这些<strong>算法细节封装进 Knowhere</strong>，让它专注"如何又快又准地建索引、搜向量"，Milvus core 则只需通过<strong>统一的接口</strong>说"给我用 X 索引、Y 度量、建/搜"，两边<strong>各自独立演进</strong>。
这正是良好分层的价值：Milvus 不必为了引入一种新索引就改动分布式调度，Knowhere 也不必关心段、WAL、副本这些分布式概念。本课接下来讲的所有索引家族，都是 Knowhere 这一侧暴露给 Milvus 的"<strong>能力清单</strong>"。</p>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">Milvus core</span><span class="name">建索引 / 向量检索的调用方</span></div><div class="ld">只通过统一接口说"用 X 索引、Y 度量、建/搜"，不碰算法细节</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">Knowhere</span><span class="name">统一的向量计算引擎（独立上游库）</span></div><div class="ld">封装各种索引算法，对上暴露"能力清单"、对下对接多种实现</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">底层实现</span><span class="name">FAISS · HNSWlib · DiskANN · cuVS …</span></div><div class="ld">各有所长的具体算法库，由 Knowhere 统一对接与封装</div></div>
</div>

<p>这带来一个对<strong>读代码很重要</strong>的事实，也是本课<strong>反复强调</strong>的引用纪律：因为索引算法住在 Knowhere（上游库）里，绝大多数<strong>索引类型名是 Knowhere 的 <span class="inline">IndexEnum</span> 常量，而不是 Milvus core 里的符号</strong>。
在 Milvus 仓库里，你能看到的是 core 代码<strong>引用</strong>这些 Knowhere 枚举的地方——例如 <span class="mono">internal/core/src/index/Utils.cpp</span> 里引用了 <span class="inline">knowhere::IndexEnum::INDEX_FAISS_IVFFLAT</span>、<span class="inline">INDEX_SPARSE_INVERTED_INDEX</span>、<span class="inline">INDEX_SPARSE_WAND</span> 等，<span class="mono">internal/core/src/common/Utils.h</span> 里引用了 <span class="inline">INDEX_DISKANN</span>。
但像 HNSW、IVF_SQ8、IVF_PQ、SCANN、GPU_CAGRA 这些名字，<strong>不要</strong>去 Milvus core 里找它们的"定义"——它们的定义在 Knowhere 上游库里。<strong>本课提到这些名字时，一律按"Knowhere 索引名"来讲，绝不硬安到某个不含它的 Milvus 文件上。</strong></p>

<h2>向量索引家族：思路、参数、何时用</h2>
<p>下面这张表是本课的"地图"。把它读懂，你就掌握了"面对一个字段，该怎么选索引"的主干判断：</p>

<table class="t">
  <tr><th>家族（Knowhere 名）</th><th>核心思路</th><th>关键参数</th><th>何时选它</th></tr>
  <tr><td><strong>FLAT</strong></td><td>暴力穷举，逐条算距离</td><td>无</td><td>数据小、要 100% 召回、做基准对照</td></tr>
  <tr><td><strong>IVF_FLAT</strong></td><td>先聚类分桶，查询只探最近的几桶</td><td>nlist（桶数）/ nprobe（探几桶）</td><td>中等规模、想要召回与速度平衡、不愿损精度</td></tr>
  <tr><td><strong>IVF_SQ8</strong></td><td>IVF + 标量量化（每维压成 1 字节）</td><td>nlist / nprobe</td><td>内存吃紧、可接受轻微精度损失</td></tr>
  <tr><td><strong>IVF_PQ</strong></td><td>IVF + 乘积量化（向量压成短码）</td><td>nlist / nprobe / m / nbits</td><td>超大规模、内存极紧、能容忍更多精度损失</td></tr>
  <tr><td><strong>HNSW</strong></td><td>可导航小世界图，顺近邻边跳转</td><td>M（每点边数）/ efConstruction / ef（查询）</td><td>追求<strong>高召回 + 低延迟</strong>、内存够用（最常用）</td></tr>
  <tr><td><strong>DiskANN</strong></td><td>磁盘上的图索引，内存只放骨架</td><td>search_list / beamwidth 等</td><td>数据量远超内存、用 SSD 换容量</td></tr>
  <tr><td><strong>SCANN</strong></td><td>各向异性量化 + 重排，谷歌系</td><td>nlist / nprobe / reorder_k</td><td>想在量化索引上拿更高召回</td></tr>
  <tr><td><strong>GPU（CAGRA / GPU_IVF_*）</strong></td><td>GPU 上建图 / IVF，海量并行</td><td>对应 CPU 版 + GPU 资源</td><td>有 GPU、要极高吞吐</td></tr>
  <tr><td><strong>稀疏（SPARSE_INVERTED_INDEX / SPARSE_WAND）</strong></td><td>为稀疏向量设计的倒排 + WAND 剪枝</td><td>drop_ratio 等</td><td>稀疏向量（如 BM25/SPLADE 学习稀疏）</td></tr>
</table>

<p>读这张表，抓两条主线就够了。<strong>第一条线是"分桶 vs 建图"</strong>：IVF 系走的是"<strong>先聚类、查询只看最近几桶</strong>"的路子，参数核心是 <span class="inline">nlist</span>（分多少桶）与 <span class="inline">nprobe</span>（查时探几桶）——nprobe 越大，看的桶越多，召回越高但越慢；
HNSW 走的是"<strong>建一张近邻跳板网、顺边跳到目标区</strong>"的路子，参数核心是 <span class="inline">M</span>（每个点连几条边，图越密越准也越占内存）与 <span class="inline">ef</span>（查询时维护的候选集大小，越大召回越高也越慢）。
<strong>第二条线是"原始 vs 量化"</strong>：FLAT/IVF_FLAT/HNSW 存的是<strong>原始向量</strong>（准但占内存），SQ8/PQ 则把向量<strong>压缩</strong>了（省内存但损精度）。把这两条线一交叉，你就能理解为什么有 IVF_FLAT、IVF_SQ8、IVF_PQ 这一串变体——它们都是"IVF 这套分桶骨架"配上"不同的压缩强度"。</p>

<p>给每个家族安一句"人设"会更好记。<strong>FLAT</strong> 是老实的笨小孩：它从不近似，召回永远 100%——当你想<strong>量一量别的索引到底损了多少召回</strong>时，它就是那把"<strong>真值标尺</strong>"，但规模一大就力不从心。<strong>IVF</strong> 是分区规划师：聚一次类，查询时只走最近的几个区；简单、可预测，精度几乎全靠 nprobe 调。<strong>HNSW</strong> 是人脉广的领路人：靠一张多层跳板图，几跳就到对的邻域，给出大多数业务最想要的"低延迟 + 高召回"组合——代价是要把整张图（连同原始向量）<strong>都放进内存</strong>。
<strong>DiskANN</strong> 是磁盘上的大仓库：当连量化都塞不进内存时，它把图放上 SSD、内存只留一副导航骨架，用一点延迟换"<strong>服务远超内存的数据量</strong>"的能力。<strong>量化版 IVF（SQ8/PQ）</strong>是省空间的能手：SQ8 把每一维压成一个字节，PQ 把向量切成若干子向量、各用码本里的一个码字替代，体积大幅缩水，代价是接受一点召回损失（可用重排步骤部分找回）。</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="乘积量化 PQ：把向量切成若干子向量，每段在自己的码本里找最近码字，用码字编号替代，整条向量压成一串短码">
    <text x="40" y="40" style="fill:var(--muted)">原始向量 v（8 维 · 32 字节）→ 切成 4 段子向量</text>
    <rect x="48" y="50" width="156" height="40" rx="8" style="fill:var(--blue-soft);stroke:var(--blue)"/><text x="126" y="75" text-anchor="middle" class="mono" style="fill:var(--blue)">[0.2, 0.9]</text>
    <rect x="212" y="50" width="156" height="40" rx="8" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="290" y="75" text-anchor="middle" class="mono" style="fill:var(--accent-ink)">[0.1, 0.3]</text>
    <rect x="376" y="50" width="156" height="40" rx="8" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="454" y="75" text-anchor="middle" class="mono" style="fill:var(--teal)">[0.8, 0.7]</text>
    <rect x="540" y="50" width="156" height="40" rx="8" style="fill:var(--amber-soft);stroke:var(--amber)"/><text x="618" y="75" text-anchor="middle" class="mono" style="fill:var(--amber)">[0.5, 0.4]</text>
    <line x1="126" y1="90" x2="126" y2="122" style="stroke:var(--line);stroke-width:1.5"/><path d="M126,122 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="290" y1="90" x2="290" y2="122" style="stroke:var(--line);stroke-width:1.5"/><path d="M290,122 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="454" y1="90" x2="454" y2="122" style="stroke:var(--line);stroke-width:1.5"/><path d="M454,122 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="618" y1="90" x2="618" y2="122" style="stroke:var(--line);stroke-width:1.5"/><path d="M618,122 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <rect x="48" y="124" width="156" height="44" rx="8" style="fill:var(--panel);stroke:var(--blue)"/><text x="126" y="151" text-anchor="middle" style="fill:var(--ink)">码本① · 最近码字</text>
    <rect x="212" y="124" width="156" height="44" rx="8" style="fill:var(--panel);stroke:var(--accent)"/><text x="290" y="151" text-anchor="middle" style="fill:var(--ink)">码本② · 最近码字</text>
    <rect x="376" y="124" width="156" height="44" rx="8" style="fill:var(--panel);stroke:var(--teal)"/><text x="454" y="151" text-anchor="middle" style="fill:var(--ink)">码本③ · 最近码字</text>
    <rect x="540" y="124" width="156" height="44" rx="8" style="fill:var(--panel);stroke:var(--amber)"/><text x="618" y="151" text-anchor="middle" style="fill:var(--ink)">码本④ · 最近码字</text>
    <line x1="126" y1="168" x2="126" y2="194" style="stroke:var(--line);stroke-width:1.5"/><path d="M126,194 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="290" y1="168" x2="290" y2="194" style="stroke:var(--line);stroke-width:1.5"/><path d="M290,194 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="454" y1="168" x2="454" y2="194" style="stroke:var(--line);stroke-width:1.5"/><path d="M454,194 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="618" y1="168" x2="618" y2="194" style="stroke:var(--line);stroke-width:1.5"/><path d="M618,194 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <rect x="86" y="196" width="80" height="34" rx="7" style="fill:var(--blue-soft);stroke:var(--blue)"/><text x="126" y="219" text-anchor="middle" class="mono" style="fill:var(--blue)">12</text>
    <rect x="250" y="196" width="80" height="34" rx="7" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="290" y="219" text-anchor="middle" class="mono" style="fill:var(--accent-ink)">7</text>
    <rect x="414" y="196" width="80" height="34" rx="7" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="454" y="219" text-anchor="middle" class="mono" style="fill:var(--teal)">30</text>
    <rect x="578" y="196" width="80" height="34" rx="7" style="fill:var(--amber-soft);stroke:var(--amber)"/><text x="618" y="219" text-anchor="middle" class="mono" style="fill:var(--amber)">3</text>
    <text x="380" y="266" text-anchor="middle" style="fill:var(--ink)"><tspan style="font-weight:700">PQ code = [12, 7, 30, 3]</tspan> · 32 字节 → 4 字节（缩到 1/8，近似换内存）</text>
  </svg>
  <div class="figcap"><b>把向量"压成一串短码"</b>：PQ 把向量切成 M 段<b>子向量</b>，每段在自己的<b>小码本</b>里找<b>最近的码字</b>，用那个<b>码字编号</b>替代整段。一条原本 32 字节的向量就变成 4 个字节的码——<b>体积大幅缩水</b>，代价是一点召回（可用重排部分找回）。</div>
</div>

<div class="cols">
  <div class="col"><h4>"要召回高、延迟低，内存够"</h4><p>直接上 <strong>HNSW</strong>。图索引几跳就拿到接近穷举的召回；召回还要更高就把 <span class="inline">ef</span> 调大。这是大多数线上向量检索的默认甜点区。</p></div>
  <div class="col"><h4>"我的数据放不进内存"</h4><p>用 <strong>IVF_PQ/SQ8</strong> 量化压缩，或上 <strong>DiskANN</strong> 把主体落 SSD。用一点召回（量化）或一点延迟（磁盘），换"<strong>每节点能服务多得多的向量</strong>"的容量。</p></div>
</div>

<p>再单独说一句<strong>稀疏</strong>向量，因为它和上面这些长得很不一样。稠密 embedding 是几百个<strong>恒有值</strong>的维度；<strong>稀疏向量</strong>（来自 BM25 或 SPLADE 这类学习稀疏模型）维度极高、但每条向量只有<strong>寥寥几个非零项</strong>——本质是一张"词 → 权重"的映射。它没法像稠密向量那样分桶或建图，于是 Knowhere 用<strong>倒排索引</strong>（<span class="inline">SPARSE_INVERTED_INDEX</span>）来服务它：对每个维度，维护一条"哪些向量含它、权重多少"的倒排链。
<strong>WAND</strong> 变体（<span class="inline">SPARSE_WAND</span>）再加上动态剪枝——算出上界分数、把不可能进 topK 的候选直接跳过，和文本检索引擎的做法如出一辙。这两个稀疏枚举，正是真实出现在 Milvus core <span class="mono">index/Utils.cpp</span> 里的那一对。</p>

<h2>放在哪里算：内存、磁盘、GPU</h2>
<p>不同索引家族对<strong>存储介质</strong>的假设也不同，这直接决定了它的容量上限与成本。把它们按"算力/存储层次"摆开看：</p>

<div class="layers">
  <div class="layer l-core"><span class="badge">GPU 显存</span><span class="name">GPU 索引（CAGRA / GPU_IVF_*）</span><span class="ld">海量并行、极高吞吐；受显存容量限制、需要 GPU 卡</span></div>
  <div class="layer l-main"><span class="badge">内存</span><span class="name">HNSW / IVF_FLAT / IVF_SQ8 / IVF_PQ / FLAT</span><span class="ld">索引常驻内存或 mmap；最常见，延迟低；容量受内存限制（量化可压）</span></div>
  <div class="layer l-part"><span class="badge">磁盘(SSD)</span><span class="name">DiskANN</span><span class="ld">图主体落 SSD，内存只放骨架；用磁盘容量换"放得下超大数据"，延迟略升</span></div>
  <div class="layer l-app"><span class="badge">稀疏</span><span class="name">SPARSE_INVERTED_INDEX / SPARSE_WAND</span><span class="ld">面向稀疏向量的倒排结构，配 WAND 动态剪枝跳过低分候选</span></div>
</div>

<p>这一层次图想说的核心是一个<strong>三角取舍</strong>：<strong>速度、内存（成本）、召回</strong>，三者通常只能优先保两个。
HNSW 把"速度 + 召回"拉满，代价是<strong>吃内存</strong>；IVF_PQ/SQ8 用<strong>量化省内存</strong>，代价是<strong>损召回</strong>；DiskANN 用<strong>磁盘换容量</strong>，代价是<strong>延迟略升</strong>；GPU 用<strong>硬件换吞吐</strong>，代价是<strong>需要 GPU 成本</strong>。
没有一个索引能在三个角上同时夺冠——选型的本质，就是<strong>根据你的数据规模、延迟要求、内存预算、召回底线，在这个三角里挑一个落点</strong>。这也呼应了第 5 课讲 ANN 时反复出现的那句话：<strong>近似检索，是在"够快、够省、够准"之间做工程权衡。</strong></p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="向量索引的三角取舍：速度、省内存、召回通常只能优先保两个；HNSW 保速度与召回、IVF_PQ 保速度与省内存、DiskANN 保召回与容量">
    <polygon points="380,58 124,256 636,256" style="fill:var(--accent-soft);opacity:.16"/>
    <polygon points="380,58 124,256 636,256" style="fill:none;stroke:var(--accent);stroke-width:1.5"/>
    <circle cx="380" cy="58" r="5" style="fill:var(--accent)"/><text x="380" y="44" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">召回 recall</text>
    <circle cx="124" cy="256" r="5" style="fill:var(--accent)"/><text x="96" y="276" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">速度 speed</text>
    <circle cx="636" cy="256" r="5" style="fill:var(--accent)"/><text x="664" y="276" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">省内存 low-mem</text>
    <text x="380" y="166" text-anchor="middle" style="fill:var(--muted)">通常只能优先保两角</text>
    <rect x="158" y="138" width="118" height="34" rx="7" style="fill:var(--panel);stroke:var(--blue);stroke-width:1.5"/><text x="217" y="160" text-anchor="middle" style="fill:var(--blue);font-weight:700">HNSW</text>
    <text x="217" y="186" text-anchor="middle" style="fill:var(--muted)">舍：吃内存</text>
    <rect x="320" y="216" width="120" height="34" rx="7" style="fill:var(--panel);stroke:var(--amber);stroke-width:1.5"/><text x="380" y="238" text-anchor="middle" style="fill:var(--amber);font-weight:700">IVF_PQ / SQ8</text>
    <text x="380" y="206" text-anchor="middle" style="fill:var(--muted)">舍：损召回</text>
    <rect x="484" y="138" width="118" height="34" rx="7" style="fill:var(--panel);stroke:var(--teal);stroke-width:1.5"/><text x="543" y="160" text-anchor="middle" style="fill:var(--teal);font-weight:700">DiskANN</text>
    <text x="543" y="186" text-anchor="middle" style="fill:var(--muted)">舍：延迟略升</text>
  </svg>
  <div class="figcap"><b>三角取舍：速度 · 省内存 · 召回，通常只能保两角</b>。<b>HNSW</b> 保<b>速度+召回</b>（代价是吃内存）；<b>IVF_PQ/SQ8</b> 保<b>速度+省内存</b>（代价是损召回）；<b>DiskANN</b> 保<b>召回+容量</b>（代价是延迟略升）；GPU 用硬件换吞吐、FLAT 用慢换 100% 召回。选型，就是按数据规模/延迟/内存/召回底线在三角里挑一个落点。</div>
</div>

<h2>一次 IVF 检索是怎么跳过大半数据的</h2>
<p>把"分桶剪枝"这件事看具体，最能体会索引为什么快。以 IVF 为例，假设建索引时把全段向量聚成了 4 个桶（<span class="inline">nlist=4</span>），查询设 <span class="inline">nprobe=2</span>：</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>定位最近的桶</h4><p>查询向量 q 先和 4 个桶的<strong>中心点</strong>算距离，挑出最近的 <span class="inline">nprobe=2</span> 个桶。其余 2 个桶<strong>整桶跳过</strong>，连看都不看。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>桶内精算</h4><p>只在选中的 2 个桶里，对桶内向量<strong>逐条算距离</strong>（若是 IVF_FLAT 用原始向量精算；若是 SQ8/PQ 则用压缩码近似算）。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>归并取 topK</h4><p>把这 2 个桶里算出的候选<strong>归并、排序</strong>，取最近的 topK 返回。扫描量从"全段"降到了"大约一半"——nprobe 越小降得越多、越快，但漏桶的风险也越大（召回越低）。</p></div></div>
</div>

<p>这条流程把 <span class="inline">nprobe</span> 的取舍演示得很直白：<strong>nprobe 调大</strong>，看的桶多、漏掉真近邻的概率小、<strong>召回升</strong>，但要精算的向量也多、<strong>变慢</strong>；<strong>nprobe 调小</strong>则反之。
HNSW 里的 <span class="inline">ef</span> 是同一个旋钮的"图版本"：ef 越大，查询时维护的候选集越大、搜得越充分、召回越高也越慢。<strong>记住这条通则</strong>：几乎所有 ANN 索引都有这么一个"<strong>查得多一点 ↔ 召回高一点、但更慢</strong>"的运行时旋钮，调它就是在<strong>速度与召回之间滑动</strong>。建索引期的参数（nlist、M）决定"结构的骨架与上限"，查询期的参数（nprobe、ef）则在这个骨架上做"当次检索的松紧调节"。顺带一提：HNSW 的检索其实是同一思路的"图版本"——它从图的顶层入口出发，每一步都<strong>贪心地跳向离 q 更近的邻居</strong>，先在稀疏的高层快速逼近大致区域，再逐层下沉到稠密的底层做精细搜索，最终把候选收敛到目标邻域。无论分桶还是建图，本质都是<strong>"只精算一小撮、整体跳过大半"</strong>。</p>

<h2>一条铁律：度量必须和字段匹配</h2>
<p>最后强调一个<strong>极易踩坑、却后果严重</strong>的点：索引用的<strong>度量（metric）必须和字段建表时声明的度量一致</strong>。回忆第 4 课——向量的"相似"是由度量定义的：<strong>L2</strong>（欧氏距离，越小越像）、<strong>IP</strong>（内积，越大越像）、<strong>COSINE</strong>（余弦，方向越一致越像）。
如果字段是按 COSINE 语义训练出来的 embedding，却给它建了个 L2 的索引，那么索引"<strong>认为的近</strong>"和你"<strong>真正想要的近</strong>"就对不上，检索结果会<strong>系统性地错</strong>——而且不会报错，只是召回莫名其妙地差。所以 Knowhere 建索引时，<strong>度量是和索引绑在一起的一等参数</strong>，必须和字段、和你训练 embedding 时用的度量三者对齐。这是向量检索里最隐蔽的一类 bug，务必从一开始就把它定对。Milvus 会在建索引时校验度量与字段的一致性，但语义层面的"用对度量"仍要靠你自己把关。</p>

<p>把"参数"再收一收，分成<strong>两个时刻</strong>记最清楚。<strong>建索引期参数</strong>（如 IVF 的 <span class="inline">nlist</span>、HNSW 的 <span class="inline">M</span> 与 <span class="inline">efConstruction</span>、PQ 的 <span class="inline">m</span>/<span class="inline">nbits</span>）决定的是<strong>索引结构本身</strong>——分多少桶、图多密、码本多大；它们一旦建好就<strong>固化进索引文件</strong>，要改只能重建。
<strong>查询期参数</strong>（如 <span class="inline">nprobe</span>、<span class="inline">ef</span>）则是每次检索都能<strong>临时调</strong>的旋钮，不必重建索引，调大调小就在当次的"速度 ↔ 召回"之间滑动。理解这层"<strong>建期定骨架、查期调松紧</strong>"的分工，你在调优时就不会把两类参数混为一谈：召回长期不够，先想是不是 nlist/M 这类<strong>结构参数</strong>选小了（要重建）；只是某次想多换点召回，调大 nprobe/ef 即可（无需重建）。</p>

<p>最后把这一课接回主线。本课讲的是 Knowhere 这个<strong>算法内核"有什么、怎么选"</strong>；但这些索引<strong>建在哪段数据上、建完的文件去哪了、QueryNode 又怎么把它用起来</strong>，是<strong>数据流</strong>的事——那正是下一课（第 23 课）要走的"sealed 段 → 构建 → 索引文件落对象存储 → QueryNode 加载"全程。把"选什么索引"（本课）和"索引怎么流动"（下一课）合起来，你才算真正掌握了 Milvus 的向量索引。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/index/Utils.cpp</span><span class="ln">Milvus core 引用 Knowhere 的索引枚举（节选示意）</span></div>
  <pre><span class="cm">// 这些是 Knowhere 上游库的 IndexEnum 常量，Milvus core 在此处引用它们：</span>
knowhere::IndexEnum::<span class="nb">INDEX_FAISS_IVFFLAT</span>      <span class="cm">// IVF_FLAT</span>
knowhere::IndexEnum::<span class="nb">INDEX_FAISS_BIN_IVFFLAT</span>  <span class="cm">// 二值向量 IVF</span>
knowhere::IndexEnum::<span class="nb">INDEX_SPARSE_INVERTED_INDEX</span> <span class="cm">// 稀疏倒排</span>
knowhere::IndexEnum::<span class="nb">INDEX_SPARSE_WAND</span>        <span class="cm">// 稀疏 WAND 剪枝</span>
<span class="cm">// 另见 common/Utils.h 引用 knowhere::IndexEnum::INDEX_DISKANN（DiskANN）。</span>
<span class="cm">// 而 HNSW / IVF_SQ8 / IVF_PQ / SCANN / GPU_CAGRA 等名字定义在 Knowhere 库内，core 不含其定义。</span></pre>
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：worker 建索引/检索时调的算法内核是上游库 <strong>Knowhere</strong>。它备齐了多大<strong>向量索引家族</strong>——<strong>FLAT</strong>（暴力·满召回）、<strong>IVF_FLAT/SQ8/PQ</strong>（聚类分桶 + 可选量化，旋钮 nlist/nprobe）、<strong>HNSW</strong>（近邻图，旋钮 M/ef）、<strong>DiskANN</strong>（磁盘图换容量）、<strong>SCANN</strong>、<strong>GPU/CAGRA</strong>（硬件换吞吐）、<strong>稀疏</strong>（SPARSE_INVERTED_INDEX/SPARSE_WAND）。选型是<strong>速度↔内存↔召回</strong>三角取舍；度量必须和字段一致。引用纪律：多数索引名是 <strong>Knowhere IndexEnum</strong>，Milvus core 仅<strong>引用</strong>少数（<span class="mono">index/Utils.cpp</span> 的 IVF/稀疏、<span class="mono">common/Utils.h</span> 的 INDEX_DISKANN）。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>Knowhere = 向量内核</strong>：Milvus C++ core 的建索引与向量检索都调上游库 Knowhere（封装 FAISS/HNSWlib/DiskANN/cuVS）。</li>
    <li><strong>索引家族</strong>：FLAT（满召回慢）/ IVF_FLAT·SQ8·PQ（分桶±量化）/ HNSW（近邻图，最常用）/ DiskANN（磁盘）/ SCANN / GPU·CAGRA / 稀疏。</li>
    <li><strong>两条主线</strong>：分桶（IVF：nlist/nprobe）vs 建图（HNSW：M/ef）；原始（准·占内存）vs 量化（省内存·损精度）。</li>
    <li><strong>三角取舍</strong>：速度↔内存（成本）↔召回，通常只能优先两个；选型即在三角里挑落点。</li>
    <li><strong>运行时旋钮</strong>：nprobe/ef 越大→召回高但更慢；建索引期参数（nlist/M）定骨架，查询期参数（nprobe/ef）定松紧。</li>
    <li><strong>度量必须匹配</strong>：L2/IP/COSINE 要和字段、和 embedding 训练时一致，否则结果系统性错且不报错。</li>
    <li><strong>引用纪律</strong>：多数索引名是 Knowhere 的 IndexEnum；core 仅引用少数（<span class="mono">index/Utils.cpp</span>、<span class="mono">common/Utils.h</span> 的 INDEX_DISKANN）。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson nailed "who builds the index": DataCoord schedules, a datanode worker executes. But in that step the worker merely <strong>called a library</strong> — the one that truly knows "how to organize vectors into a fast-searchable structure" is Milvus's upstream vector-search kernel, <strong>Knowhere</strong>.
This lesson drills into Knowhere to see which <strong>vector-index families</strong> it offers (FLAT, the IVF line, HNSW, DiskANN, SCANN, GPU, sparse), what each is <strong>about</strong>, its <strong>key params</strong>, and <strong>when to pick which</strong>.
One important caveat up front: most index names below (HNSW, IVF_SQ8, SCANN, CAGRA…) are <strong><span class="inline">IndexEnum</span> constants in the Knowhere library</strong>, <strong>not</strong> defined in Milvus's own code; only a few enums are referenced in Milvus core, and this lesson distinguishes them precisely.
</p>

<div class="card analogy">
  <div class="tag">📮 Analogy</div>
  Picture running a warehouse packed with goods, your job being "<strong>given a sample, find the few items most like it</strong>." You have several ways to organize the shelves:
  <strong>The dumbest but most accurate</strong> is to <strong>compare every item against the sample</strong> (that's FLAT, brute force, 100% recall but slow);
  <strong>a bit smarter</strong>, first <strong>zone the goods by similarity</strong> (cluster), locate the sample to the nearest few zones and only browse those (that's IVF: coarse buckets first, fine search within);
  <strong>smarter still</strong>, <strong>string a net of "neighbor shortcuts"</strong> between items so that from any item you hop a few shortcuts to the patch most like the sample (that's HNSW: a navigable small-world graph);
  <strong>to save space</strong>, <strong>compress each item into a thumbnail</strong> before comparing (that's PQ quantization: approximation for memory);
  <strong>when it won't fit in memory</strong>, <strong>spread the shelves onto disk</strong> and keep only the index skeleton in memory (that's DiskANN).
  There is no "best" method, only "<strong>how you choose to trade off among speed, memory, recall, and cost</strong>." Knowhere is the toolbox that stocks <strong>all</strong> of these methods.
</div>

<h2>What is Knowhere: Milvus's vector-search kernel</h2>
<p><strong>Knowhere</strong> is a <strong>standalone, upstream</strong> vector-search library maintained by the Milvus project (primarily C++, wrapping FAISS, HNSWlib, DiskANN, cuVS, etc. behind a unified API). Milvus's C++ core does its two most core algorithmic jobs — <strong>building indexes</strong> and <strong>vector search</strong> — by <strong>calling Knowhere</strong>; think of it as Milvus's "<strong>vector compute engine</strong>."
Recall Lesson 2's "three-language split": Go handles distribution and scheduling, C++ handles single-machine storage and compute, Rust handles full-text indexing; and within that C++ layer, the <strong>concrete algorithms of vector indexing and search</strong> are outsourced to this dedicated library, Knowhere.</p>

<p>Why factor the algorithms into a <strong>separate library</strong> instead of intermixing them with Milvus core? Because vector search is a <strong>fast-evolving yet highly specialized</strong> field: HNSW is hot today, DiskANN tomorrow, GPU CAGRA the day after, with FAISS, cuVS and a dozen other implementations underneath, each with its own strengths. <strong>Encapsulating those algorithm details inside Knowhere</strong> lets it focus on "how to build and search vectors fast and accurately," while Milvus core only says, through a <strong>unified interface</strong>, "use index X with metric Y, build/search"; the two <strong>evolve independently</strong>.
That is the value of clean layering: Milvus need not touch distributed scheduling to add a new index, and Knowhere need not know about segments, the WAL, or replicas. Every index family this lesson covers is part of the "<strong>capability menu</strong>" Knowhere exposes to Milvus.</p>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">Milvus core</span><span class="name">caller of index-build / vector-search</span></div><div class="ld">just says "use index X, metric Y, build/search" via a unified interface, untouched by algorithm details</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">Knowhere</span><span class="name">the unified vector-compute engine (separate upstream lib)</span></div><div class="ld">wraps various index algorithms, exposing a "capability menu" up and adapting many impls below</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">implementations</span><span class="name">FAISS · HNSWlib · DiskANN · cuVS …</span></div><div class="ld">concrete algorithm libraries, each with its strengths, unified and wrapped by Knowhere</div></div>
</div>

<p>This yields a fact <strong>important for reading code</strong>, and the citation discipline this lesson <strong>keeps stressing</strong>: because the index algorithms live in Knowhere (the upstream library), most <strong>index-type names are Knowhere <span class="inline">IndexEnum</span> constants, not symbols in Milvus core</strong>.
In the Milvus repo, what you can see are the spots where core code <strong>references</strong> these Knowhere enums — e.g. <span class="mono">internal/core/src/index/Utils.cpp</span> references <span class="inline">knowhere::IndexEnum::INDEX_FAISS_IVFFLAT</span>, <span class="inline">INDEX_SPARSE_INVERTED_INDEX</span>, <span class="inline">INDEX_SPARSE_WAND</span>, and <span class="mono">internal/core/src/common/Utils.h</span> references <span class="inline">INDEX_DISKANN</span>.
But names like HNSW, IVF_SQ8, IVF_PQ, SCANN, GPU_CAGRA — <strong>do not</strong> hunt for their "definition" in Milvus core; they are defined in the Knowhere upstream library. <strong>When this lesson mentions these names, it treats them strictly as "Knowhere index names," never forcing them onto some Milvus file that lacks them.</strong></p>

<h2>The vector-index families: idea, params, when to use</h2>
<p>The table below is this lesson's "map." Read it well and you grasp the backbone of "facing a field, how to choose an index":</p>

<table class="t">
  <tr><th>Family (Knowhere name)</th><th>Core idea</th><th>Key params</th><th>When to pick it</th></tr>
  <tr><td><strong>FLAT</strong></td><td>brute force, per-row distance</td><td>none</td><td>small data, want 100% recall, baseline comparison</td></tr>
  <tr><td><strong>IVF_FLAT</strong></td><td>cluster into buckets, query probes only the nearest few</td><td>nlist (buckets) / nprobe (probed)</td><td>medium scale, want recall-speed balance, no precision loss</td></tr>
  <tr><td><strong>IVF_SQ8</strong></td><td>IVF + scalar quantization (1 byte per dim)</td><td>nlist / nprobe</td><td>memory-tight, can accept slight precision loss</td></tr>
  <tr><td><strong>IVF_PQ</strong></td><td>IVF + product quantization (short codes)</td><td>nlist / nprobe / m / nbits</td><td>huge scale, very tight memory, tolerate more precision loss</td></tr>
  <tr><td><strong>HNSW</strong></td><td>navigable small-world graph, hop along neighbor edges</td><td>M (edges/node) / efConstruction / ef (query)</td><td>want <strong>high recall + low latency</strong>, memory sufficient (most common)</td></tr>
  <tr><td><strong>DiskANN</strong></td><td>on-disk graph index, only skeleton in memory</td><td>search_list / beamwidth, etc.</td><td>data far exceeds memory, trade SSD for capacity</td></tr>
  <tr><td><strong>SCANN</strong></td><td>anisotropic quantization + reorder, Google-derived</td><td>nlist / nprobe / reorder_k</td><td>want higher recall on a quantized index</td></tr>
  <tr><td><strong>GPU (CAGRA / GPU_IVF_*)</strong></td><td>graph / IVF on GPU, massive parallelism</td><td>CPU-equivalents + GPU resources</td><td>have a GPU, need very high throughput</td></tr>
  <tr><td><strong>Sparse (SPARSE_INVERTED_INDEX / SPARSE_WAND)</strong></td><td>inverted index for sparse vectors + WAND pruning</td><td>drop_ratio, etc.</td><td>sparse vectors (e.g. BM25 / SPLADE learned-sparse)</td></tr>
</table>

<p>Reading the table, two through-lines suffice. <strong>Line one is "bucketing vs graph"</strong>: the IVF line takes the "<strong>cluster first, query looks at only the nearest few buckets</strong>" route, its core params being <span class="inline">nlist</span> (how many buckets) and <span class="inline">nprobe</span> (how many to probe) — bigger nprobe means more buckets seen, higher recall but slower;
HNSW takes the "<strong>build a net of neighbor shortcuts and hop edge-by-edge to the target patch</strong>" route, its core params being <span class="inline">M</span> (edges per point — denser graph, more accurate but more memory) and <span class="inline">ef</span> (candidate-set size at query time — larger means higher recall but slower).
<strong>Line two is "raw vs quantized"</strong>: FLAT/IVF_FLAT/HNSW store <strong>raw vectors</strong> (accurate but memory-hungry), while SQ8/PQ <strong>compress</strong> them (memory-saving but precision-losing). Cross these two lines and you understand why the IVF_FLAT, IVF_SQ8, IVF_PQ series exists — all "the IVF bucketing skeleton" plus "different compression strengths."</p>

<p>It helps to give each family a one-line "personality." <strong>FLAT</strong> is the honest plodder: it never approximates, so its recall is always 100% — invaluable as a <strong>ground-truth baseline</strong> when you want to measure how much recall another index actually loses, but hopeless at scale. <strong>IVF</strong> is the zoning planner: cluster once, then at query time visit only the nearest zones; simple, predictable, and its accuracy is tuned almost entirely by nprobe. <strong>HNSW</strong> is the well-connected navigator: by building a multi-layer shortcut graph it reaches the right neighborhood in just a few hops, delivering the best latency-recall combo most workloads want — at the price of holding the whole graph (and raw vectors) in memory.
<strong>DiskANN</strong> is the warehouse-on-disk: when even quantization can't squeeze the data into RAM, it puts the graph on SSD and keeps only a navigating skeleton in memory, trading a bit of latency for the ability to serve datasets far larger than memory. <strong>The quantized IVFs (SQ8/PQ)</strong> are the space-savers: SQ8 squashes each dimension to a byte, PQ chops a vector into sub-vectors and replaces each with a codebook entry, shrinking footprint dramatically while accepting some recall loss that a re-rank step can partly recover.</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="Product quantization PQ: chop a vector into sub-vectors, find the nearest codeword in each sub-codebook, and replace each with that codeword id, compressing the whole vector into a short code">
    <text x="40" y="40" style="fill:var(--muted)">original vector v (8 dims · 32 bytes) → chopped into 4 sub-vectors</text>
    <rect x="48" y="50" width="156" height="40" rx="8" style="fill:var(--blue-soft);stroke:var(--blue)"/><text x="126" y="75" text-anchor="middle" class="mono" style="fill:var(--blue)">[0.2, 0.9]</text>
    <rect x="212" y="50" width="156" height="40" rx="8" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="290" y="75" text-anchor="middle" class="mono" style="fill:var(--accent-ink)">[0.1, 0.3]</text>
    <rect x="376" y="50" width="156" height="40" rx="8" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="454" y="75" text-anchor="middle" class="mono" style="fill:var(--teal)">[0.8, 0.7]</text>
    <rect x="540" y="50" width="156" height="40" rx="8" style="fill:var(--amber-soft);stroke:var(--amber)"/><text x="618" y="75" text-anchor="middle" class="mono" style="fill:var(--amber)">[0.5, 0.4]</text>
    <line x1="126" y1="90" x2="126" y2="122" style="stroke:var(--line);stroke-width:1.5"/><path d="M126,122 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="290" y1="90" x2="290" y2="122" style="stroke:var(--line);stroke-width:1.5"/><path d="M290,122 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="454" y1="90" x2="454" y2="122" style="stroke:var(--line);stroke-width:1.5"/><path d="M454,122 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="618" y1="90" x2="618" y2="122" style="stroke:var(--line);stroke-width:1.5"/><path d="M618,122 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <rect x="48" y="124" width="156" height="44" rx="8" style="fill:var(--panel);stroke:var(--blue)"/><text x="126" y="151" text-anchor="middle" style="fill:var(--ink)">codebook① · nearest</text>
    <rect x="212" y="124" width="156" height="44" rx="8" style="fill:var(--panel);stroke:var(--accent)"/><text x="290" y="151" text-anchor="middle" style="fill:var(--ink)">codebook② · nearest</text>
    <rect x="376" y="124" width="156" height="44" rx="8" style="fill:var(--panel);stroke:var(--teal)"/><text x="454" y="151" text-anchor="middle" style="fill:var(--ink)">codebook③ · nearest</text>
    <rect x="540" y="124" width="156" height="44" rx="8" style="fill:var(--panel);stroke:var(--amber)"/><text x="618" y="151" text-anchor="middle" style="fill:var(--ink)">codebook④ · nearest</text>
    <line x1="126" y1="168" x2="126" y2="194" style="stroke:var(--line);stroke-width:1.5"/><path d="M126,194 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="290" y1="168" x2="290" y2="194" style="stroke:var(--line);stroke-width:1.5"/><path d="M290,194 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="454" y1="168" x2="454" y2="194" style="stroke:var(--line);stroke-width:1.5"/><path d="M454,194 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <line x1="618" y1="168" x2="618" y2="194" style="stroke:var(--line);stroke-width:1.5"/><path d="M618,194 l-4,-10 l8,0 z" style="fill:var(--line)"/>
    <rect x="86" y="196" width="80" height="34" rx="7" style="fill:var(--blue-soft);stroke:var(--blue)"/><text x="126" y="219" text-anchor="middle" class="mono" style="fill:var(--blue)">12</text>
    <rect x="250" y="196" width="80" height="34" rx="7" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="290" y="219" text-anchor="middle" class="mono" style="fill:var(--accent-ink)">7</text>
    <rect x="414" y="196" width="80" height="34" rx="7" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="454" y="219" text-anchor="middle" class="mono" style="fill:var(--teal)">30</text>
    <rect x="578" y="196" width="80" height="34" rx="7" style="fill:var(--amber-soft);stroke:var(--amber)"/><text x="618" y="219" text-anchor="middle" class="mono" style="fill:var(--amber)">3</text>
    <text x="380" y="266" text-anchor="middle" style="fill:var(--ink)"><tspan style="font-weight:700">PQ code = [12, 7, 30, 3]</tspan> · 32 bytes → 4 bytes (8× smaller, approx. for memory)</text>
  </svg>
  <div class="figcap"><b>Compress a vector into a short code</b>: PQ chops a vector into M <b>sub-vectors</b>; each finds the <b>nearest codeword</b> in its own <b>small codebook</b> and is replaced by that <b>codeword id</b>. A 32-byte vector becomes a 4-byte code — <b>dramatically smaller</b>, at the cost of a little recall (a re-rank can partly recover it).</div>
</div>

<div class="cols">
  <div class="col"><h4>"I want max recall &amp; low latency, RAM is fine"</h4><p>Reach for <strong>HNSW</strong>. The graph gives near-exhaustive recall at a few-hop cost; tune <span class="inline">ef</span> up if recall must be higher. This is the default sweet spot for most production vector search.</p></div>
  <div class="col"><h4>"My data won't fit in RAM"</h4><p>Quantize with <strong>IVF_PQ/SQ8</strong> to shrink it, or go <strong>DiskANN</strong> to put the bulk on SSD. You trade a little recall (quantization) or a little latency (disk) for the capacity to serve far more vectors per node.</p></div>
</div>

<p>A quick word on <strong>sparse</strong> vectors, since they look different from everything above. Dense embeddings have a few hundred always-present dimensions; <strong>sparse vectors</strong> (from BM25 or learned-sparse models like SPLADE) have a huge dimensionality but only a handful of non-zero entries per vector — essentially "term → weight" maps. They can't be bucketed or graphed the same way, so Knowhere serves them with an <strong>inverted index</strong> (<span class="inline">SPARSE_INVERTED_INDEX</span>): for each dimension, a posting list of "which vectors have it and with what weight." The <strong>WAND</strong> variant (<span class="inline">SPARSE_WAND</span>) adds dynamic pruning — it computes upper-bound scores and skips candidates that cannot possibly enter the topK, much like text search engines do. These are the two sparse-vector enums that genuinely appear in Milvus core's <span class="mono">index/Utils.cpp</span>.</p>

<h2>Where it computes: memory, disk, GPU</h2>
<p>Different families also assume different <strong>storage media</strong>, which directly sets capacity ceilings and cost. Lay them out by the "compute/storage hierarchy":</p>

<div class="layers">
  <div class="layer l-core"><span class="badge">GPU VRAM</span><span class="name">GPU indexes (CAGRA / GPU_IVF_*)</span><span class="ld">massive parallelism, very high throughput; bounded by VRAM, needs a GPU card</span></div>
  <div class="layer l-main"><span class="badge">memory</span><span class="name">HNSW / IVF_FLAT / IVF_SQ8 / IVF_PQ / FLAT</span><span class="ld">index resident in memory or mmap; most common, low latency; capacity bounded by RAM (quantization compresses)</span></div>
  <div class="layer l-part"><span class="badge">disk(SSD)</span><span class="name">DiskANN</span><span class="ld">graph body on SSD, only skeleton in memory; trade disk capacity to "fit huge data," latency slightly up</span></div>
  <div class="layer l-app"><span class="badge">sparse</span><span class="name">SPARSE_INVERTED_INDEX / SPARSE_WAND</span><span class="ld">inverted structures for sparse vectors, with WAND dynamic pruning to skip low-score candidates</span></div>
</div>

<p>The core message of this hierarchy is a <strong>triangle tradeoff</strong>: <strong>speed, memory (cost), recall</strong> — you can usually prioritize only two.
HNSW maxes out "speed + recall" at the cost of <strong>memory</strong>; IVF_PQ/SQ8 <strong>save memory via quantization</strong> at the cost of <strong>recall</strong>; DiskANN <strong>trades disk for capacity</strong> at the cost of <strong>slightly higher latency</strong>; GPU <strong>trades hardware for throughput</strong> at the cost of <strong>GPU expense</strong>.
No index wins all three corners at once — choosing an index is, in essence, <strong>picking a landing point in this triangle per your data scale, latency target, memory budget, and recall floor</strong>. This echoes the refrain from Lesson 5 on ANN: <strong>approximate search is an engineering tradeoff among "fast enough, cheap enough, accurate enough."</strong></p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="The triangle tradeoff of vector indexes: speed, low memory, and recall — usually you can keep only two; HNSW keeps speed and recall, IVF_PQ keeps speed and low memory, DiskANN keeps recall and capacity">
    <polygon points="380,58 124,256 636,256" style="fill:var(--accent-soft);opacity:.16"/>
    <polygon points="380,58 124,256 636,256" style="fill:none;stroke:var(--accent);stroke-width:1.5"/>
    <circle cx="380" cy="58" r="5" style="fill:var(--accent)"/><text x="380" y="44" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">recall</text>
    <circle cx="124" cy="256" r="5" style="fill:var(--accent)"/><text x="100" y="276" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">speed</text>
    <circle cx="636" cy="256" r="5" style="fill:var(--accent)"/><text x="660" y="276" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">low-memory</text>
    <text x="380" y="166" text-anchor="middle" style="fill:var(--muted)">usually keep only two corners</text>
    <rect x="158" y="138" width="118" height="34" rx="7" style="fill:var(--panel);stroke:var(--blue);stroke-width:1.5"/><text x="217" y="160" text-anchor="middle" style="fill:var(--blue);font-weight:700">HNSW</text>
    <text x="217" y="186" text-anchor="middle" style="fill:var(--muted)">gives up: memory</text>
    <rect x="320" y="216" width="120" height="34" rx="7" style="fill:var(--panel);stroke:var(--amber);stroke-width:1.5"/><text x="380" y="238" text-anchor="middle" style="fill:var(--amber);font-weight:700">IVF_PQ / SQ8</text>
    <text x="380" y="206" text-anchor="middle" style="fill:var(--muted)">gives up: recall</text>
    <rect x="484" y="138" width="118" height="34" rx="7" style="fill:var(--panel);stroke:var(--teal);stroke-width:1.5"/><text x="543" y="160" text-anchor="middle" style="fill:var(--teal);font-weight:700">DiskANN</text>
    <text x="543" y="186" text-anchor="middle" style="fill:var(--muted)">gives up: latency</text>
  </svg>
  <div class="figcap"><b>Triangle tradeoff: speed · low-memory · recall — usually keep only two</b>. <b>HNSW</b> keeps <b>speed+recall</b> (costs memory); <b>IVF_PQ/SQ8</b> keeps <b>speed+low-memory</b> (costs recall); <b>DiskANN</b> keeps <b>recall+capacity</b> (costs a little latency); GPU trades hardware for throughput, FLAT trades speed for 100% recall. Choosing an index = picking a landing point by your scale / latency / memory / recall floor.</div>
</div>

<h2>How one IVF search skips most of the data</h2>
<p>Making "bucket pruning" concrete best conveys why an index is fast. Take IVF: suppose the build clustered the segment's vectors into 4 buckets (<span class="inline">nlist=4</span>) and the query sets <span class="inline">nprobe=2</span>:</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Locate nearest buckets</h4><p>The query vector q first computes distance to the 4 buckets' <strong>centroids</strong> and picks the nearest <span class="inline">nprobe=2</span>. The other 2 buckets are <strong>skipped entirely</strong>, never looked at.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>In-bucket exact compute</h4><p>Only within the 2 chosen buckets, compute distance <strong>per vector</strong> (IVF_FLAT computes exactly on raw vectors; SQ8/PQ approximate via compressed codes).</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Merge for topK</h4><p><strong>Merge and sort</strong> the candidates from those 2 buckets and take the nearest topK. Scanned volume drops from "the whole segment" to "about half" — smaller nprobe drops it more and runs faster, but risks missing a bucket (lower recall).</p></div></div>
</div>

<p>This flow demonstrates the <span class="inline">nprobe</span> tradeoff plainly: <strong>raise nprobe</strong> → more buckets seen, lower chance of missing a true neighbor, <strong>recall up</strong>, but more vectors to compute, <strong>slower</strong>; <strong>lower nprobe</strong> is the reverse.
HNSW's <span class="inline">ef</span> is the "graph version" of the same dial: bigger ef → larger candidate set maintained at query time → more thorough search → higher recall but slower. <strong>Remember this general rule</strong>: nearly every ANN index has such a "<strong>search a bit more ↔ a bit higher recall, but slower</strong>" runtime dial; turning it <strong>slides between speed and recall</strong>. Build-time params (nlist, M) set "the skeleton and its ceiling"; query-time params (nprobe, ef) adjust "the tightness of this particular search" on that skeleton. As an aside: HNSW search is really the "graph version" of the same idea — starting from the graph's top entry, each step <strong>greedily hops toward a neighbor closer to q</strong>, rapidly approaching the rough region on the sparse upper layers, then descending layer by layer into the dense bottom for a fine search, finally converging candidates onto the target neighborhood. Whether bucketing or graph, the essence is the same: <strong>"exact-compute a tiny subset, skip most overall."</strong></p>

<h2>An iron rule: the metric must match the field</h2>
<p>Finally, stress a point that is <strong>easy to trip on yet severe</strong>: the index's <strong>metric must match the metric declared for the field at schema time</strong>. Recall Lesson 4 — a vector's "similarity" is defined by a metric: <strong>L2</strong> (Euclidean, smaller is closer), <strong>IP</strong> (inner product, larger is closer), <strong>COSINE</strong> (cosine, more aligned direction is closer).
If a field's embeddings were trained under COSINE semantics but you build an L2 index on them, then what the index "<strong>thinks is near</strong>" and what you "<strong>actually want as near</strong>" disagree, and results are <strong>systematically wrong</strong> — with no error raised, just inexplicably poor recall. So when Knowhere builds an index, the <strong>metric is a first-class parameter bound to the index</strong> and must align across the field, the index, and the metric you used to train the embeddings. This is one of the most insidious bug classes in vector search; get it right from the very start. Milvus does validate metric-vs-field consistency at build time, but using the semantically right metric is ultimately yours to guard.</p>

<p>To tidy up "params," the clearest way is to split them by <strong>two moments</strong>. <strong>Build-time params</strong> (IVF's <span class="inline">nlist</span>, HNSW's <span class="inline">M</span> and <span class="inline">efConstruction</span>, PQ's <span class="inline">m</span>/<span class="inline">nbits</span>) decide the <strong>index structure itself</strong> — how many buckets, how dense the graph, how big the codebook; once built they are <strong>frozen into the index files</strong> and changing them means a rebuild.
<strong>Query-time params</strong> (<span class="inline">nprobe</span>, <span class="inline">ef</span>) are dials you can <strong>adjust per search</strong> without rebuilding, sliding the current query along "speed ↔ recall." Grasping this "<strong>build sets the skeleton, query tunes the tightness</strong>" split keeps the two kinds apart when tuning: if recall is chronically too low, first suspect a too-small <strong>structural param</strong> like nlist/M (needs a rebuild); if you just want more recall on a particular query, bump nprobe/ef (no rebuild).</p>

<p>Finally, connect this lesson back to the main line. Here we covered <strong>what the Knowhere algorithm kernel offers and how to choose</strong>; but <strong>which segment's data these indexes are built on, where the built files go, and how QueryNode puts them to use</strong> are matters of <strong>data flow</strong> — exactly the "sealed segment → build → index files to object storage → QueryNode loads" journey of the next lesson (23). Combine "which index to choose" (this lesson) with "how the index flows" (next lesson) and you truly command Milvus's vector indexing.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/index/Utils.cpp</span><span class="ln">Milvus core references Knowhere's index enums (illustrative excerpt)</span></div>
  <pre><span class="cm">// These are IndexEnum constants from the upstream Knowhere library; Milvus core references them here:</span>
knowhere::IndexEnum::<span class="nb">INDEX_FAISS_IVFFLAT</span>      <span class="cm">// IVF_FLAT</span>
knowhere::IndexEnum::<span class="nb">INDEX_FAISS_BIN_IVFFLAT</span>  <span class="cm">// binary-vector IVF</span>
knowhere::IndexEnum::<span class="nb">INDEX_SPARSE_INVERTED_INDEX</span> <span class="cm">// sparse inverted</span>
knowhere::IndexEnum::<span class="nb">INDEX_SPARSE_WAND</span>        <span class="cm">// sparse WAND pruning</span>
<span class="cm">// See also common/Utils.h referencing knowhere::IndexEnum::INDEX_DISKANN (DiskANN).</span>
<span class="cm">// Whereas HNSW / IVF_SQ8 / IVF_PQ / SCANN / GPU_CAGRA are defined inside Knowhere; core has no definition of them.</span></pre>
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: the algorithm kernel the worker calls to build/search is the upstream library <strong>Knowhere</strong>. It stocks a range of <strong>vector-index families</strong> — <strong>FLAT</strong> (brute force · full recall), <strong>IVF_FLAT/SQ8/PQ</strong> (cluster-bucket + optional quantization, dials nlist/nprobe), <strong>HNSW</strong> (neighbor graph, dials M/ef), <strong>DiskANN</strong> (on-disk graph for capacity), <strong>SCANN</strong>, <strong>GPU/CAGRA</strong> (hardware for throughput), <strong>sparse</strong> (SPARSE_INVERTED_INDEX/SPARSE_WAND). Selection is a <strong>speed↔memory↔recall</strong> triangle; the metric must match the field. Citation discipline: most index names are <strong>Knowhere IndexEnum</strong>, and Milvus core only <strong>references</strong> a few (the IVF/sparse ones in <span class="mono">index/Utils.cpp</span>, INDEX_DISKANN in <span class="mono">common/Utils.h</span>).
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Knowhere = vector kernel</strong>: Milvus C++ core does index build and vector search by calling the upstream Knowhere library (wraps FAISS/HNSWlib/DiskANN/cuVS).</li>
    <li><strong>Index families</strong>: FLAT (full recall, slow) / IVF_FLAT·SQ8·PQ (bucketing ± quantization) / HNSW (neighbor graph, most common) / DiskANN (disk) / SCANN / GPU·CAGRA / sparse.</li>
    <li><strong>Two through-lines</strong>: bucketing (IVF: nlist/nprobe) vs graph (HNSW: M/ef); raw (accurate · memory) vs quantized (memory-saving · precision loss).</li>
    <li><strong>Triangle tradeoff</strong>: speed ↔ memory (cost) ↔ recall, usually only two prioritized; selection is picking a point in the triangle.</li>
    <li><strong>Runtime dial</strong>: larger nprobe/ef → higher recall but slower; build-time params (nlist/M) set the skeleton, query-time params (nprobe/ef) set the tightness.</li>
    <li><strong>Metric must match</strong>: L2/IP/COSINE must align with the field and with embedding training, else results are systematically wrong with no error.</li>
    <li><strong>Citation discipline</strong>: most index names are Knowhere IndexEnum; core only references a few (<span class="mono">index/Utils.cpp</span>, INDEX_DISKANN in <span class="mono">common/Utils.h</span>).</li>
  </ul>
</div>
""",
}

LESSON_23 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前两课分别讲了"<strong>谁来建索引</strong>"（DataCoord 调度、worker 执行）和"<strong>建什么索引</strong>"（Knowhere 的各家向量索引）。这一课把镜头切到<strong>数据流</strong>：一段数据从"原始向量"到"可被检索的索引"，物理上到底<strong>流经哪些地方</strong>。
完整链路是：<strong>sealed 段的原始向量 → 构建任务（worker 读 binlog、调 Knowhere 建索引）→ 索引文件写进对象存储 → QueryNode 在加载集合时把索引读进内存或 mmap → 段变得可被 ANN 检索</strong>。
途中还有两个关键问题：<strong>还没建好索引的段（尤其 growing 段）怎么查</strong>？以及<strong>索引格式升级了、老索引还能不能用</strong>（索引版本管理）？这一课一并讲清。
</p>

<div class="card analogy">
  <div class="tag">📚 生活类比</div>
  又回到图书馆。上一课馆员助手已经把书架读了一遍、写好了一沓<strong>目录卡片</strong>（索引）。但卡片不能就摊在书架旁——它得<strong>装箱、送进中央档案库</strong>（对象存储）统一保管，登记在册，谁要都能调。
  等到某家<strong>分馆</strong>（QueryNode）要对外提供"快速查书"服务时，它会去中央档案库<strong>把这套卡片借出一份副本</strong>：要么<strong>整副本搬到前台抽屉里</strong>（加载进内存，查得最快），要么<strong>放在身边的架子上、用到哪页翻哪页</strong>（mmap，省内存、按需读盘）。
  还有两件事：<strong>刚到、还没来得及编目的新书</strong>（growing 段），读者要找也得照顾——只能<strong>一本本翻过去</strong>（暴力扫描），慢但不漏。以及，档案库的<strong>卡片格式偶尔会升级</strong>（新版排版更高效），分馆得能认出"这批卡片是哪个版本的、我这台设备认不认得"——这就是索引版本管理。
</div>

<h2>数据流总览：从 sealed 段到可检索</h2>
<p>先把整条路一眼看全。它串起了前面好几课的角色：第 17 课的 flush 产出 sealed 段、第 18 课的对象存储与 binlog、第 13 课 QueryCoord 的加载/释放、第 21 课的构建任务：</p>

<div class="timeline">
  <div class="lane"><span class="lane-label">① sealed</span><span class="tslot">段已 flush 成 binlog（原始向量，不可变）</span></div>
  <div class="lane"><span class="lane-label">② 构建</span><span class="tslot now">worker 读 binlog → 调 Knowhere 建索引</span></div>
  <div class="lane"><span class="lane-label">③ 落盘</span><span class="tslot">索引文件写进对象存储（index_files 前缀）</span></div>
  <div class="lane"><span class="lane-label">④ 加载</span><span class="tslot now">QueryNode 读索引进内存 / mmap</span></div>
  <div class="lane"><span class="lane-label">⑤ 可查</span><span class="tslot">该段以 ANN 方式参与检索</span></div>
</div>

<p>这条流水线最值得记住的特征是：<strong>每一步都把"重活"留在后台、把"产物"沉淀成持久文件</strong>。原始向量是持久的（binlog 在对象存储）、索引也是持久的（索引文件在对象存储）——所以即便 worker 或 QueryNode 中途崩了，<strong>已落盘的产物都不会丢</strong>，重启后从对象存储重新取即可。
这正是 Milvus 反复出现的"<strong>计算与存储分离</strong>"：构建索引的算力（worker）、服务检索的算力（QueryNode）都是<strong>无状态、可替换</strong>的，真正的<strong>状态</strong>（原始数据、索引）都躺在对象存储这块共享底座上。理解这一点，你就明白为什么 Milvus 的节点能随意扩缩容、崩了能快速恢复——因为"数据"和"算它的人"被干净地解耦了。</p>

<h2>构建侧：worker 读 binlog、调 Knowhere、写索引文件</h2>
<p>把第 21 课的"构建"这一步放大。worker（datanode 上的 <span class="inline">indexBuildTask</span>）领到一个段的构建任务后，它的 <span class="inline">Execute</span> 大致做三件事：</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>读出原始向量</h4><p>按任务里的段信息，从对象存储<strong>拉取该段的向量 binlog</strong>，反序列化、拼装成 Knowhere 能吃的内存数据集（回忆第 18 课的列式 binlog）。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>调 Knowhere 建索引</h4><p>按索引类型与参数（第 22 课），把数据集交给 Knowhere 跑建索引——建图 / 聚类 / 训练码本。这是整条链路里<strong>最吃 CPU/内存</strong>的一步。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>写索引文件 + 登记</h4><p>把 Knowhere 产出的索引<strong>序列化成索引文件</strong>、写回对象存储（<span class="mono">index_files</span> 前缀），再把文件路径<strong>上报 DataCoord</strong>，段标记"已建索引"。</p></div></div>
</div>

<p>这里有个常被忽视、却很重要的细节：worker 建索引读的是 binlog（原始向量），写的是索引文件——两者是<strong>并存</strong>的，索引<strong>不会替换</strong>原始数据。
为什么要留着原始向量？因为很多索引（如量化的 IVF_PQ）是<strong>有损</strong>的，检索时可能需要原始向量做<strong>精确重排（rerank）</strong>；而且未来若要<strong>重建索引</strong>（换索引类型、换参数、或索引格式升级），也必须从原始向量重新来过。所以对象存储里，同一个段会同时存着<strong>原始 binlog</strong> 和<strong>索引文件</strong>两份产物，各司其职：原始 binlog 是"<strong>真相</strong>"（可重建一切），索引文件是"<strong>加速副本</strong>"（坏了、过时了都能从原始数据重造）。这也呼应了第 18 课列出的对象存储产物清单：insert_log / delta_log / stats_log / <strong>index_files</strong> 并列共存。</p>

<p>顺带把"构建为什么必须在不可变数据上做"再钉死一遍。worker 读 binlog 建索引时，<strong>必须确信这份数据在构建期间不会变</strong>——否则建到一半数据被改写，建出的索引就和数据对不上了。sealed 段恰好提供了这个保证：它是<strong>只读、不可变</strong>的快照，worker 可以放心地读它、慢慢算，期间不必担心有人在背后改数据。
这正是前面几部分反复铺垫的"<strong>不可变性</strong>"在索引场景下的再次兑现：binlog 不可变让 compaction 能安全地后台合并（第 19 课）、让删除只能追加墓碑（第 20 课），现在又让建索引能安全地后台进行。<strong>不可变是这一切后台异步任务的共同地基</strong>——没有它，"一边服务查询、一边后台重写/建索引"这种并发就会处处是数据竞争。</p>

<h2>加载侧：QueryNode 把索引读进内存或 mmap</h2>
<p>索引文件躺在对象存储里只是"<strong>可被加载的资产</strong>"，本身不能直接对外服务。真正让它"<strong>活起来、能查</strong>"的，是 <strong>QueryNode 在加载集合时的加载动作</strong>（回忆第 13 课：QueryCoord 决定把哪些段加载到哪些 QueryNode）。
加载逻辑在 <span class="mono">internal/querynodev2/segments/segment_loader.go</span>（如 <span class="inline">loadSealedSegment</span>），它把该段的索引文件从对象存储取下、交给 C++ 侧（经 Knowhere）<strong>反序列化、装载</strong>成一个可检索的索引对象。装载方式有两种，是一个重要的<strong>内存 vs 磁盘</strong>取舍，直接关系到"一个节点能服务多大数据、查得多快"：</p>

<div class="cols">
  <div class="col"><h4>加载进内存（memory）</h4><p>把索引<strong>整个读进内存</strong>。检索时所有访问都命中内存，<strong>延迟最低、最稳定</strong>；代价是<strong>吃内存</strong>，单节点能装下的数据量受内存上限约束。对延迟敏感、内存充裕的场景首选。</p></div>
  <div class="col"><h4>内存映射（mmap）</h4><p>把索引文件 <strong>mmap</strong> 进地址空间，<strong>用到哪页才从磁盘换入哪页</strong>。<strong>省内存</strong>、能在同样内存下装下<strong>多得多</strong>的数据；代价是冷数据访问会触发<strong>缺页读盘</strong>，延迟略升、有抖动。容量优先时选它。</p></div>
</div>

<p>memory 与 mmap 的取舍，本质又是那个老三角的一条边：<strong>用延迟换容量</strong>。它和上一课 DiskANN"把图放磁盘"是同一种思路在<strong>不同层次</strong>的体现——DiskANN 是<strong>索引算法本身</strong>为磁盘而设计，mmap 则是<strong>加载方式</strong>层面让任意内存索引"按需读盘"。
Milvus 允许按字段、按场景<strong>精细配置</strong>哪些数据走 mmap，于是你能把"热的小字段放内存、冷的大向量走 mmap"，在<strong>成本与延迟</strong>之间找到适合自己的平衡点。这层灵活性，正是"计算存储分离 + 文件化索引"带来的红利：索引既然只是对象存储里的文件，加载侧就能自由决定"怎么把它搬进来用"。</p>

<p>还要把"加载"和第 13 课的<strong>QueryCoord</strong> 接起来，免得你以为 QueryNode 会自作主张地加载。真正决定"<strong>哪些段、哪些索引、加载到哪台 QueryNode</strong>"的是 QueryCoord——它掌握全局的副本、均衡与 distribution↔target 视图，把加载任务<strong>派</strong>给具体的 QueryNode；QueryNode 只是<strong>执行</strong>这条加载指令（从对象存储取索引文件、装载、汇报已就绪）。
这又一次是"<strong>协调器调度、节点执行</strong>"的同一主旋律：建索引是 DataCoord 调度 + worker 执行，加载索引则是 QueryCoord 调度 + QueryNode 执行。两条后台链路结构惊人地对称——都把"重活"交给可替换的节点，把"全局账本"留在协调器手里。把这种对称性看透，你对 Milvus 整套分布式骨架的理解就成型了。</p>

<h2>还没建索引的段：growing 段用暴力扫描</h2>
<p>一个绕不开的问题：<strong>刚写入、还在 growing、或刚 sealed 但索引还没建好</strong>的段，查询要不要照顾？答案是必须照顾——否则刚写进去的数据就查不到，违背了"<strong>写完即可见</strong>"。
处理办法很直接：<strong>这些还没有索引的段，检索时退化为暴力扫描（brute force / FLAT 式逐条算距离）</strong>。慢，但<strong>正确、不漏</strong>。这也解释了为什么第 21 课强调"<strong>索引只建在不可变的 sealed 段上</strong>"——growing 段还在变，建了也白建，索性等它 sealed 后再建，建好之前就用暴力扫描兜底。</p>

<div class="flow">
  <div class="node hl"><div class="nt">growing 段</div><div class="nd">还在接收新行 · 无索引</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">暴力扫描</div><div class="nd">逐条算距离 · 慢但不漏</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">flush → sealed</div><div class="nd">冻结成不可变 binlog</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">建索引 → ANN</div><div class="nd">该段转为索引检索 · 快</div></div>
</div>

<p>于是一次检索在 QueryNode 上常常是<strong>"混合"</strong>的：少数 growing 段走暴力扫描、大量 sealed 段走 ANN 索引，各段算出局部 topK，再<strong>归并</strong>成全局结果（这与第 10 课 Proxy 的扇出归并是同一种"分而治之"，只是层次不同）。
对用户而言，这一切是<strong>透明</strong>的——你只管查，至于"哪些段有索引、哪些没有、各用什么方式算"，由 QueryNode 内部自动决定。理解这层混合，你就不会再困惑"为什么刚写的数据也能立刻搜到，但好像比老数据慢一点点"——因为新数据所在的 growing 段还在用暴力扫描，等它 sealed、建好索引，就和老数据一样快了。这也是为什么一个集合刚导入大量数据时，查询会先慢后快：随着后台把一个个 sealed 段的索引陆续建好，走暴力扫描的段越来越少、走 ANN 的段越来越多，整体延迟便<strong>逐步下降、趋于稳定</strong>。</p>

<h2>索引版本管理：格式升级了，老索引怎么办</h2>
<p>最后一个常被忽略、却很现实的问题：索引文件是有<strong>格式版本</strong>的。Knowhere 在演进，索引的<strong>引擎版本（index engine version）</strong>会升级——新版可能有更高效的布局、新的能力。那么集群里<strong>新老 QueryNode 混部</strong>、或<strong>老索引遇上新引擎</strong>时，怎么保证"建出来的索引，加载它的节点认得"？
这就是 <span class="mono">internal/datacoord/index_engine_version_manager.go</span> 的职责：DataCoord 维护一个 <span class="inline">IndexEngineVersionManager</span>，跟踪集群里各 QueryNode 上报的索引引擎版本，给出<strong>当前可用的版本</strong>（<span class="inline">GetCurrentIndexEngineVersion</span>）与<strong>最低兼容版本</strong>（<span class="inline">GetMinimalIndexEngineVersion</span>）。建索引时按这个<strong>协商出的版本</strong>来建，就能保证产出的索引<strong>不会高于集群里最弱节点认得的版本</strong>，避免"建了个新格式索引、却没有节点能加载"的尴尬。</p>

<p>这套版本协商，背后是一个分布式系统都会遇到的现实约束：<strong>升级不是一瞬间、而是滚动进行的</strong>。你不可能让全集群几十上百个节点同时换成新版 Knowhere；现实里总有一段时间<strong>新老节点并存</strong>。如果建索引的 worker 已经升级、却按最新格式建了索引，而某些还没升级的老 QueryNode <strong>读不懂</strong>这个新格式，那个段就在这些节点上<strong>加载失败、无法服务</strong>。
版本管理器的"<strong>取最低兼容版本</strong>"策略，本质就是一条朴素的兼容性铁律：<strong>产出物的格式，要向集群里最保守的消费者看齐</strong>。等所有节点都升级完、最低版本水位整体抬高了，新格式才会自然启用。这种"<strong>以最弱节点为准</strong>"的保守协商，在数据库的在线升级里随处可见——它用一点"暂时用不上新特性"的代价，换来了<strong>升级期间服务不中断</strong>。这也是分布式系统"<strong>兼容性优先于新特性</strong>"原则的一个缩影：能不能用上最新最快的格式是其次，<strong>整个集群在升级过程中始终可用、不丢服务</strong>才是第一位的。</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="索引引擎版本协商：建索引版本取各节点支持版本的最小值，即所有节点都能加载的最高格式，最老的节点也能加载">
    <rect x="30" y="58" width="196" height="92" rx="11" style="fill:var(--panel);stroke:var(--accent);stroke-width:1.5"/>
    <text x="128" y="84" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">DataCoord 版本管理器</text>
    <text x="128" y="108" text-anchor="middle" style="fill:var(--muted)">各节点支持: v3·v3·v2</text>
    <text x="128" y="132" text-anchor="middle" style="fill:var(--teal);font-weight:700">建索引 = 取最小 = v2</text>
    <line x1="226" y1="104" x2="260" y2="104" style="stroke:var(--accent);stroke-width:2"/><path d="M260,104 l-11,-5 l0,10 z" style="fill:var(--accent)"/>
    <rect x="262" y="82" width="150" height="46" rx="9" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="337" y="102" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">worker 建索引</text><text x="337" y="120" text-anchor="middle" style="fill:var(--muted)">按 v2 产出</text>
    <line x1="412" y1="104" x2="446" y2="104" style="stroke:var(--teal);stroke-width:2"/><path d="M446,104 l-11,-5 l0,10 z" style="fill:var(--teal)"/>
    <rect x="448" y="84" width="96" height="42" rx="8" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="496" y="110" text-anchor="middle" class="mono" style="fill:var(--teal);font-weight:700">index v2</text>
    <line x1="544" y1="98" x2="586" y2="66" style="stroke:var(--teal);stroke-width:1.5"/><path d="M586,66 l-11,1 l4,8 z" style="fill:var(--teal)"/>
    <line x1="544" y1="105" x2="586" y2="109" style="stroke:var(--teal);stroke-width:1.5"/><path d="M586,109 l-11,-2 l1,8 z" style="fill:var(--teal)"/>
    <line x1="544" y1="112" x2="586" y2="152" style="stroke:var(--teal);stroke-width:1.5"/><path d="M586,152 l-10,-4 l-1,9 z" style="fill:var(--teal)"/>
    <rect x="588" y="48" width="152" height="38" rx="7" style="fill:var(--panel);stroke:var(--teal)"/><text x="664" y="72" text-anchor="middle" style="fill:var(--ink)">QueryNode v3 ✓</text>
    <rect x="588" y="92" width="152" height="38" rx="7" style="fill:var(--panel);stroke:var(--teal)"/><text x="664" y="116" text-anchor="middle" style="fill:var(--ink)">QueryNode v3 ✓</text>
    <rect x="588" y="136" width="152" height="38" rx="7" style="fill:var(--panel);stroke:var(--teal);stroke-width:1.5"/><text x="664" y="160" text-anchor="middle" style="fill:var(--ink)">QueryNode v2 ✓</text>
    <text x="385" y="212" text-anchor="middle" style="fill:var(--red);font-weight:700">✗ 若按 v3 建 → 只支持 v2 的老节点加载失败</text>
    <text x="385" y="244" text-anchor="middle" style="fill:var(--muted)">∴ 建索引版本 = 各节点支持版本的最小值 = 所有节点都能加载的最高格式</text>
  </svg>
  <div class="figcap"><b>建索引，向最弱的消费者看齐</b>：升级是<b>滚动</b>的，新老 QueryNode 总会并存。DataCoord 把建索引版本取成<b>各节点支持版本的最小值</b>（源码 <span class="mono">GetCurrentIndexEngineVersion</span>，即<b>所有节点都能加载的最高格式</b>）：本例 <span class="mono">min(v3,v3,v2)=v2</span>，连最老的 v2 节点也能加载；若按更高的 v3 建，v2 老节点就读不懂。这正是"<b>兼容性优先于新特性</b>"。</div>
</div>

<p>把这一课收束一下：我们沿着<strong>数据流</strong>，走完了索引"从原始向量到可被检索"的物理全程——构建侧 worker 把 sealed 段读成索引文件落对象存储，加载侧 QueryNode 把索引文件搬进内存或 mmap，中间用暴力扫描兜住还没建好索引的段，外加版本管理保证新老索引互认。
至此，<strong>向量索引</strong>这条线就讲透了：第 21 课"谁建"、第 22 课"建什么"、第 23 课"怎么流动与加载"。但别忘了，真实的查询往往不只是"找最像的向量"，还常常带着<strong>标量过滤条件</strong>（"价格 &lt; 100 且类别 = 数码"）和<strong>全文检索</strong>（"包含关键词 X"）。这些<strong>非向量</strong>的检索要快，同样得靠索引——那就是下一课<strong>标量与全文索引</strong>的主题。</p>

<table class="t">
  <tr><th>产物 / 状态</th><th>在哪里</th><th>谁负责</th></tr>
  <tr><td>原始向量 binlog</td><td>对象存储（insert_log 前缀）</td><td>flush（第 17 课）产出，构建时被读</td></tr>
  <tr><td>索引文件</td><td>对象存储（index_files 前缀）</td><td>worker 构建后写入</td></tr>
  <tr><td>索引元数据（路径/状态）</td><td>etcd（经 DataCoord）</td><td>worker 回写、DataCoord 记账</td></tr>
  <tr><td>加载后的索引对象</td><td>QueryNode 内存 / mmap</td><td>QueryNode 加载集合时装载</td></tr>
  <tr><td>索引引擎版本</td><td>DataCoord（版本管理器）</td><td><span class="mono">index_engine_version_manager.go</span></td></tr>
</table>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/datacoord/index_engine_version_manager.go</span><span class="ln">IndexEngineVersionManager：协商索引引擎版本（节选）</span></div>
  <pre><span class="cm">// DataCoord 跟踪各 QueryNode 上报的索引引擎版本，给出可用/最低兼容版本，</span>
<span class="cm">// 让构建出的索引不会高于集群里最弱节点能加载的版本。</span>
<span class="kw">type</span> IndexEngineVersionManager <span class="kw">interface</span> {
    <span class="fn">GetCurrentIndexEngineVersion</span>() int32 <span class="cm">// 当前可用版本</span>
    <span class="fn">GetMinimalIndexEngineVersion</span>() int32 <span class="cm">// 最低兼容版本</span>
    <span class="cm">// AddNode/RemoveNode/Update：随 QueryNode 上下线刷新版本视图</span>
}</pre>
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：索引的<strong>数据流</strong>是——<strong>sealed 段原始向量</strong>（对象存储 binlog）→ <strong>worker 构建</strong>（<span class="inline">indexBuildTask.Execute</span>：读 binlog、调 Knowhere）→ <strong>索引文件落对象存储</strong>（index_files）→ <strong>QueryNode 加载</strong>（<span class="mono">segment_loader.go</span>：读进内存或 mmap）→ 段以 <strong>ANN</strong> 可查。<strong>原始向量与索引并存</strong>（重排/重建要用原始数据）；<strong>growing 段无索引、用暴力扫描兜底</strong>，sealed 并建好索引后转 ANN；一次检索常是"暴力 + ANN"混合再归并。<strong>计算存储分离</strong>让节点无状态可恢复。<strong>索引版本</strong>由 <span class="mono">index_engine_version_manager.go</span> 协商，保证产出的索引被集群节点认得。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>完整数据流</strong>：sealed 段原始向量 → worker 读 binlog·调 Knowhere 构建 → 索引文件落对象存储 → QueryNode 加载 → 段可 ANN 检索。</li>
    <li><strong>原始与索引并存</strong>：索引文件（<span class="mono">index_files</span>）不替换原始 binlog；量化索引重排、未来重建都要回到原始向量。</li>
    <li><strong>加载两方式</strong>：内存（延迟最低·吃内存）vs mmap（省内存·按需读盘·略抖）；可按字段/场景配置，是延迟↔容量取舍。</li>
    <li><strong>growing 用暴力扫描</strong>：无索引的段退化为逐条算距离，慢但不漏；sealed 建好索引后转 ANN。一次检索常是暴力+ANN 混合归并。</li>
    <li><strong>计算存储分离</strong>：原始数据与索引都在对象存储，worker/QueryNode 无状态、崩了从对象存储恢复。</li>
    <li><strong>索引版本管理</strong>：<span class="mono">index_engine_version_manager.go</span> 的 <span class="inline">IndexEngineVersionManager</span>（<span class="inline">GetCurrentIndexEngineVersion</span>/<span class="inline">GetMinimalIndexEngineVersion</span>）协商版本，避免建出无人能加载的索引。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The last two lessons covered "<strong>who builds the index</strong>" (DataCoord schedules, a worker executes) and "<strong>what index to build</strong>" (Knowhere's vector-index families). This lesson cuts to the <strong>data flow</strong>: physically, where does a segment's data travel as it goes from "raw vectors" to "a searchable index"?
The full chain: <strong>a sealed segment's raw vectors → a build task (the worker reads binlogs and calls Knowhere) → index files written to object storage → QueryNode reads the index into memory or mmaps it when the collection is loaded → the segment becomes ANN-searchable</strong>.
Two key questions arise along the way: <strong>how do you query a segment that isn't indexed yet (especially a growing one)</strong>, and <strong>if the index format is upgraded, can old indexes still be used</strong> (index versioning)? This lesson settles both.
</p>

<div class="card analogy">
  <div class="tag">📮 Analogy</div>
  Back to the library. Last lesson the assistant read the shelf and wrote a stack of <strong>catalog cards</strong> (the index). But the cards can't just sit by the shelf — they must be <strong>boxed and sent to the central archive</strong> (object storage) for safekeeping, logged, and available on request.
  When a <strong>branch library</strong> (QueryNode) wants to offer "fast lookups," it <strong>checks out a copy</strong> of those cards from the central archive: either <strong>moves the whole copy into the front desk drawer</strong> (load into memory, fastest to query) or <strong>keeps it on a nearby shelf and flips to a page when needed</strong> (mmap, memory-saving, read on demand).
  Two more things: <strong>brand-new books not yet cataloged</strong> (growing segments) must still serve readers — only by <strong>flipping through them one by one</strong> (brute force), slow but complete. And the archive's <strong>card format occasionally upgrades</strong> (a more efficient new layout), so a branch must recognize "which version these cards are and whether my equipment reads it" — that is index versioning.
</div>

<h2>Data-flow overview: from sealed segment to searchable</h2>
<p>First see the whole path at a glance. It threads together roles from several earlier lessons: Lesson 17's flush producing sealed segments, Lesson 18's object storage and binlogs, Lesson 13's QueryCoord load/release, Lesson 21's build task:</p>

<div class="timeline">
  <div class="lane"><span class="lane-label">① sealed</span><span class="tslot">segment flushed to binlogs (raw vectors, immutable)</span></div>
  <div class="lane"><span class="lane-label">② build</span><span class="tslot now">worker reads binlogs → calls Knowhere to build</span></div>
  <div class="lane"><span class="lane-label">③ persist</span><span class="tslot">index files written to object storage (index_files prefix)</span></div>
  <div class="lane"><span class="lane-label">④ load</span><span class="tslot now">QueryNode reads the index into memory / mmap</span></div>
  <div class="lane"><span class="lane-label">⑤ queryable</span><span class="tslot">the segment participates in search via ANN</span></div>
</div>

<p>The most memorable trait of this pipeline: <strong>every step leaves the "heavy work" in the background and settles the "product" into durable files</strong>. Raw vectors are durable (binlogs in object storage), and so is the index (index files in object storage) — so even if a worker or QueryNode crashes midway, <strong>the already-persisted products are never lost</strong>; just refetch from object storage on restart.
This is Milvus's recurring "<strong>compute-storage separation</strong>": the compute for building indexes (workers) and for serving search (QueryNodes) is <strong>stateless and replaceable</strong>, while the real <strong>state</strong> (raw data, indexes) lives on the shared object-storage substrate. Grasp this and you see why Milvus nodes scale freely and recover fast after a crash — because "the data" and "who computes on it" are cleanly decoupled.</p>

<h2>Build side: worker reads binlogs, calls Knowhere, writes index files</h2>
<p>Zoom into Lesson 21's "build" step. After the worker (the <span class="inline">indexBuildTask</span> on a datanode) picks up a segment's build task, its <span class="inline">Execute</span> roughly does three things:</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Read raw vectors</h4><p>By the segment info in the task, <strong>pull the segment's vector binlogs</strong> from object storage, deserialize, and assemble into an in-memory dataset Knowhere can consume (recall Lesson 18's columnar binlogs).</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Call Knowhere to build</h4><p>Per the index type and params (Lesson 22), hand the dataset to Knowhere to build — graph / cluster / train codebook. This is the <strong>most CPU/memory-hungry</strong> step of the chain.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Write index files + register</h4><p><strong>Serialize Knowhere's output into index files</strong>, write them back to object storage (<span class="mono">index_files</span> prefix), then <strong>report the paths to DataCoord</strong> and mark the segment "indexed."</p></div></div>
</div>

<p>One often-overlooked but important detail: the worker <strong>reads binlogs (raw vectors) and writes index files — the two coexist; the index does NOT replace the raw data</strong>.
Why keep the raw vectors? Because many indexes (e.g. quantized IVF_PQ) are <strong>lossy</strong>, and search may need raw vectors for <strong>exact re-ranking</strong>; and any future <strong>rebuild</strong> (change index type, change params, or an index-format upgrade) must start over from the raw vectors. So in object storage, one segment holds both the <strong>raw binlogs</strong> and the <strong>index files</strong>, each with its job: the raw binlogs are the "<strong>truth</strong>" (everything can be rebuilt from them), the index files an "<strong>acceleration copy</strong>" (if corrupted or stale, they can be rebuilt from the raw data). This echoes Lesson 18's object-storage product list: insert_log / delta_log / stats_log / <strong>index_files</strong> coexisting side by side.</p>

<p>Let's also nail down once more "why the build must run on immutable data." When the worker reads binlogs to build an index, it <strong>must be sure the data won't change during the build</strong> — otherwise, if the data were rewritten halfway, the produced index wouldn't match the data. A sealed segment provides exactly this guarantee: it is a <strong>read-only, immutable</strong> snapshot, so the worker can read it freely and compute slowly without worrying about anyone changing the data behind its back.
This is the recurring "<strong>immutability</strong>" theme from earlier parts cashing in again, now in the indexing context: immutable binlogs let compaction merge safely in the background (Lesson 19), let deletes only append tombstones (Lesson 20), and now let index builds proceed safely in the background. <strong>Immutability is the shared foundation of all these background async tasks</strong> — without it, the concurrency of "serving queries while rewriting/indexing in the background" would be riddled with data races.</p>

<h2>Load side: QueryNode reads the index into memory or mmap</h2>
<p>An index file sitting in object storage is only a "<strong>loadable asset</strong>" — it cannot serve directly. What makes it "<strong>come alive and queryable</strong>" is <strong>QueryNode's load action when the collection is loaded</strong> (recall Lesson 13: QueryCoord decides which segments load onto which QueryNodes).
The load logic is in <span class="mono">internal/querynodev2/segments/segment_loader.go</span> (e.g. <span class="inline">loadSealedSegment</span>); it fetches the segment's index files from object storage and hands them to the C++ side (via Knowhere) to <strong>deserialize and load</strong> into a searchable index object. Loading comes in two ways — an important <strong>memory vs disk</strong> tradeoff that directly governs "how much data a node can serve and how fast it queries":</p>

<div class="cols">
  <div class="col"><h4>Load into memory</h4><p>Read the <strong>entire index into RAM</strong>. All access at query time hits memory, giving the <strong>lowest, most stable latency</strong>; the cost is <strong>memory consumption</strong>, with per-node capacity bounded by RAM. First choice for latency-sensitive, memory-rich scenarios.</p></div>
  <div class="col"><h4>Memory-map (mmap)</h4><p><strong>mmap</strong> the index files into the address space, <strong>paging in from disk only what's touched</strong>. <strong>Memory-saving</strong>, fitting <strong>far more</strong> data under the same RAM; the cost is that cold access triggers <strong>page faults to disk</strong>, with slightly higher, jittery latency. Pick it when capacity comes first.</p></div>
</div>

<p>The memory-vs-mmap tradeoff is, again, one edge of that old triangle: <strong>trade latency for capacity</strong>. It is the same idea as last lesson's DiskANN ("put the graph on disk") expressed at a <strong>different level</strong> — DiskANN designs the <strong>index algorithm itself</strong> for disk, while mmap makes <strong>any in-memory index</strong> "page in on demand" at the <strong>load</strong> level.
Milvus lets you <strong>finely configure</strong> which data goes through mmap by field and scenario, so you can keep "hot small fields in memory, cold large vectors on mmap," finding your own balance between <strong>cost and latency</strong>. This flexibility is the dividend of "compute-storage separation + file-based indexes": since an index is just a file in object storage, the load side is free to decide "how to bring it in and use it."</p>

<p>Let's also connect "load" to Lesson 13's <strong>QueryCoord</strong>, lest you think QueryNode loads on its own whim. The one that decides "<strong>which segments, which indexes, onto which QueryNode</strong>" is QueryCoord — it holds the global view of replicas, balancing, and distribution↔target, and <strong>dispatches</strong> load tasks to specific QueryNodes; a QueryNode merely <strong>executes</strong> that load command (fetch index files from object storage, load, report ready).
This is, once more, the same "<strong>coordinator schedules, node executes</strong>" theme: index build is DataCoord-scheduled + worker-executed, index load is QueryCoord-scheduled + QueryNode-executed. The two background chains are strikingly symmetric — both hand the "heavy work" to replaceable nodes and keep the "global ledger" with the coordinator. See this symmetry clearly and your grasp of Milvus's whole distributed skeleton takes shape.</p>

<h2>Segments not yet indexed: growing segments use brute force</h2>
<p>An unavoidable question: should queries serve segments that are <strong>just written, still growing, or sealed-but-not-yet-indexed</strong>? They must — otherwise freshly written data couldn't be found, violating "<strong>visible once written</strong>."
The handling is direct: <strong>these unindexed segments fall back to brute force at query time (FLAT-style per-row distance)</strong>. Slow, but <strong>correct and complete</strong>. This also explains why Lesson 21 stressed "<strong>indexes are built only on immutable sealed segments</strong>" — a growing segment is still changing, so building on it is wasted; better to wait until it's sealed, with brute force covering the gap until then.</p>

<div class="flow">
  <div class="node hl"><div class="nt">growing segment</div><div class="nd">still receiving rows · no index</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">brute force</div><div class="nd">per-row distance · slow but complete</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">flush → sealed</div><div class="nd">frozen into immutable binlogs</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">build → ANN</div><div class="nd">segment switches to index search · fast</div></div>
</div>

<p>So a single search on a QueryNode is often <strong>"hybrid"</strong>: a few growing segments use brute force, many sealed segments use ANN indexes, each computes a local topK, then they <strong>merge</strong> into a global result (the same "divide and conquer" as Lesson 10's Proxy fan-out-and-reduce, just at a different level).
To the user this is all <strong>transparent</strong> — you just query, and "which segments have an index, which don't, and how each computes" is decided automatically inside QueryNode. Grasp this hybrid and you'll no longer wonder "why can freshly written data be searched instantly, yet seems a touch slower than old data" — because the growing segment holding new data is still on brute force; once it's sealed and indexed, it's as fast as the old data. This is also why, just after bulk-importing a lot of data, queries start slow and speed up: as the background builds the indexes of sealed segments one by one, fewer segments use brute force and more use ANN, so overall latency <strong>steadily drops and stabilizes</strong>.</p>

<h2>Index versioning: the format upgraded — what about old indexes?</h2>
<p>A last, often-ignored yet very real issue: index files have a <strong>format version</strong>. Knowhere evolves, and the index's <strong>engine version</strong> upgrades — newer versions may have more efficient layouts or new capabilities. So when the cluster runs <strong>mixed old/new QueryNodes</strong>, or an <strong>old index meets a new engine</strong>, how do you guarantee "the index that's built is recognized by the node that loads it"?
That is the job of <span class="mono">internal/datacoord/index_engine_version_manager.go</span>: DataCoord maintains an <span class="inline">IndexEngineVersionManager</span> that tracks the index-engine versions reported by each QueryNode and yields the <strong>currently available version</strong> (<span class="inline">GetCurrentIndexEngineVersion</span>) and the <strong>minimal compatible version</strong> (<span class="inline">GetMinimalIndexEngineVersion</span>). Building per this <strong>negotiated version</strong> ensures the produced index is <strong>never higher than the weakest node in the cluster can recognize</strong>, avoiding the embarrassment of "built a new-format index that no node can load."</p>

<p>Behind this version negotiation is a real constraint every distributed system faces: <strong>upgrades aren't instantaneous — they roll out gradually</strong>. You can't switch dozens or hundreds of nodes to a new Knowhere version all at once; in practice there's always a window of <strong>mixed old/new nodes</strong>. If a worker that already upgraded builds an index in the latest format, while some not-yet-upgraded old QueryNodes <strong>can't read</strong> that new format, that segment <strong>fails to load and can't serve</strong> on those nodes.
The version manager's "<strong>take the minimal compatible version</strong>" policy is, in essence, a plain compatibility rule: <strong>the format of a product must align with the most conservative consumer in the cluster</strong>. Only once all nodes have upgraded and the minimal-version watermark rises overall does the new format naturally take effect. This "<strong>defer to the weakest node</strong>" conservative negotiation is everywhere in online database upgrades — it trades "temporarily not using a new feature" for <strong>uninterrupted service during the upgrade</strong>. It is a microcosm of the distributed-systems principle "<strong>compatibility over new features</strong>": whether you get the newest, fastest format is secondary; what comes first is that <strong>the whole cluster stays available throughout the upgrade, losing no service</strong>.</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="Index engine version negotiation: the build version is the minimum of all nodes' supported versions, i.e. the highest format every node can load, so even the oldest node can load it">
    <rect x="30" y="58" width="196" height="92" rx="11" style="fill:var(--panel);stroke:var(--accent);stroke-width:1.5"/>
    <text x="128" y="84" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">DataCoord version mgr</text>
    <text x="128" y="108" text-anchor="middle" style="fill:var(--muted)">nodes support: v3·v3·v2</text>
    <text x="128" y="132" text-anchor="middle" style="fill:var(--teal);font-weight:700">build = take the min = v2</text>
    <line x1="226" y1="104" x2="260" y2="104" style="stroke:var(--accent);stroke-width:2"/><path d="M260,104 l-11,-5 l0,10 z" style="fill:var(--accent)"/>
    <rect x="262" y="82" width="150" height="46" rx="9" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="337" y="102" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">worker builds</text><text x="337" y="120" text-anchor="middle" style="fill:var(--muted)">at v2</text>
    <line x1="412" y1="104" x2="446" y2="104" style="stroke:var(--teal);stroke-width:2"/><path d="M446,104 l-11,-5 l0,10 z" style="fill:var(--teal)"/>
    <rect x="448" y="84" width="96" height="42" rx="8" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="496" y="110" text-anchor="middle" class="mono" style="fill:var(--teal);font-weight:700">index v2</text>
    <line x1="544" y1="98" x2="586" y2="66" style="stroke:var(--teal);stroke-width:1.5"/><path d="M586,66 l-11,1 l4,8 z" style="fill:var(--teal)"/>
    <line x1="544" y1="105" x2="586" y2="109" style="stroke:var(--teal);stroke-width:1.5"/><path d="M586,109 l-11,-2 l1,8 z" style="fill:var(--teal)"/>
    <line x1="544" y1="112" x2="586" y2="152" style="stroke:var(--teal);stroke-width:1.5"/><path d="M586,152 l-10,-4 l-1,9 z" style="fill:var(--teal)"/>
    <rect x="588" y="48" width="152" height="38" rx="7" style="fill:var(--panel);stroke:var(--teal)"/><text x="664" y="72" text-anchor="middle" style="fill:var(--ink)">QueryNode v3 ✓</text>
    <rect x="588" y="92" width="152" height="38" rx="7" style="fill:var(--panel);stroke:var(--teal)"/><text x="664" y="116" text-anchor="middle" style="fill:var(--ink)">QueryNode v3 ✓</text>
    <rect x="588" y="136" width="152" height="38" rx="7" style="fill:var(--panel);stroke:var(--teal);stroke-width:1.5"/><text x="664" y="160" text-anchor="middle" style="fill:var(--ink)">QueryNode v2 ✓</text>
    <text x="385" y="212" text-anchor="middle" style="fill:var(--red);font-weight:700">✗ if built at v3 → the node that only supports v2 fails to load</text>
    <text x="385" y="244" text-anchor="middle" style="fill:var(--muted)">∴ build version = the minimum of nodes' versions = the highest format all can load</text>
  </svg>
  <div class="figcap"><b>Build to the weakest consumer</b>: upgrades are <b>rolling</b>, so old and new QueryNodes coexist. DataCoord sets the build version to the <b>minimum of all nodes' supported versions</b> (source <span class="mono">GetCurrentIndexEngineVersion</span> — the <b>highest format every node can load</b>): here <span class="mono">min(v3,v3,v2)=v2</span>, so even the oldest v2 node can load it; built at the higher v3, the v2 node couldn't. That is "<b>compatibility over new features</b>".</div>
</div>

<p>To wrap up: along the <strong>data flow</strong>, we walked the index's full physical journey "from raw vectors to searchable" — the build side's worker turns a sealed segment into index files in object storage, the load side's QueryNode brings those files into memory or mmap, brute force covers segments not yet indexed in between, plus versioning ensures old and new indexes recognize each other.
With that, the <strong>vector-index</strong> thread is complete: Lesson 21 "who builds," Lesson 22 "what to build," Lesson 23 "how it flows and loads." But remember, real queries are often not just "find the most similar vector" — they frequently carry <strong>scalar filters</strong> ("price &lt; 100 and category = electronics") and <strong>full-text search</strong> ("contains keyword X"). For these <strong>non-vector</strong> lookups to be fast, they too need indexes — the subject of the next lesson, <strong>scalar and full-text indexes</strong>.</p>

<table class="t">
  <tr><th>Product / state</th><th>Where</th><th>Who</th></tr>
  <tr><td>raw-vector binlogs</td><td>object storage (insert_log prefix)</td><td>produced by flush (Lesson 17), read at build</td></tr>
  <tr><td>index files</td><td>object storage (index_files prefix)</td><td>written by worker after build</td></tr>
  <tr><td>index metadata (paths/state)</td><td>etcd (via DataCoord)</td><td>written back by worker, booked by DataCoord</td></tr>
  <tr><td>loaded index object</td><td>QueryNode memory / mmap</td><td>loaded by QueryNode on collection load</td></tr>
  <tr><td>index engine version</td><td>DataCoord (version manager)</td><td><span class="mono">index_engine_version_manager.go</span></td></tr>
</table>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/datacoord/index_engine_version_manager.go</span><span class="ln">IndexEngineVersionManager: negotiate the index engine version (excerpt)</span></div>
  <pre><span class="cm">// DataCoord tracks the index-engine versions reported by each QueryNode and yields available/minimal-compatible versions,</span>
<span class="cm">// so a built index is never higher than the weakest node in the cluster can load.</span>
<span class="kw">type</span> IndexEngineVersionManager <span class="kw">interface</span> {
    <span class="fn">GetCurrentIndexEngineVersion</span>() int32 <span class="cm">// currently available version</span>
    <span class="fn">GetMinimalIndexEngineVersion</span>() int32 <span class="cm">// minimal compatible version</span>
    <span class="cm">// AddNode/RemoveNode/Update: refresh the version view as QueryNodes come and go</span>
}</pre>
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: the index <strong>data flow</strong> is — <strong>sealed segment raw vectors</strong> (object-storage binlogs) → <strong>worker builds</strong> (<span class="inline">indexBuildTask.Execute</span>: read binlogs, call Knowhere) → <strong>index files to object storage</strong> (index_files) → <strong>QueryNode loads</strong> (<span class="mono">segment_loader.go</span>: into memory or mmap) → the segment is queryable via <strong>ANN</strong>. <strong>Raw vectors and index coexist</strong> (re-rank/rebuild need the raw data); <strong>growing segments have no index and fall back to brute force</strong>, switching to ANN once sealed and built; a single search is often "brute force + ANN" merged. <strong>Compute-storage separation</strong> makes nodes stateless and recoverable. <strong>Index versions</strong> are negotiated by <span class="mono">index_engine_version_manager.go</span>, ensuring built indexes are recognized by cluster nodes.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Full data flow</strong>: sealed-segment raw vectors → worker reads binlogs · calls Knowhere to build → index files to object storage → QueryNode loads → segment ANN-searchable.</li>
    <li><strong>Raw and index coexist</strong>: index files (<span class="mono">index_files</span>) don't replace raw binlogs; quantized-index re-ranking and any future rebuild go back to raw vectors.</li>
    <li><strong>Two load modes</strong>: memory (lowest latency · RAM-hungry) vs mmap (memory-saving · page-in on demand · slight jitter); configurable per field/scenario, a latency↔capacity tradeoff.</li>
    <li><strong>Growing uses brute force</strong>: unindexed segments fall back to per-row distance, slow but complete; switch to ANN after sealed and built. A search is often brute-force + ANN merged.</li>
    <li><strong>Compute-storage separation</strong>: both raw data and indexes live in object storage; workers/QueryNodes are stateless and recover from object storage after a crash.</li>
    <li><strong>Index versioning</strong>: <span class="mono">index_engine_version_manager.go</span>'s <span class="inline">IndexEngineVersionManager</span> (<span class="inline">GetCurrentIndexEngineVersion</span>/<span class="inline">GetMinimalIndexEngineVersion</span>) negotiates versions, avoiding building an index no node can load.</li>
  </ul>
</div>
""",
}

LESSON_24 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前三课讲的索引，全是为<strong>向量检索</strong>服务的。但真实查询很少是"纯向量"——它常常带着<strong>标量过滤</strong>（"价格 &lt; 100、类别 = 数码、上架时间在本周"）和<strong>全文检索</strong>（"商品描述里含'防水'"）。
这一课讲<strong>非向量</strong>那一半的加速：<strong>标量索引</strong>（倒排、bitmap、排序、ngram、混合、JSON）让过滤又快又省；<strong>全文检索（BM25）</strong>借助 Rust 的 <strong>tantivy</strong> 引擎落地。最后看<strong>标量过滤 + 向量 ANN</strong> 如何在一次"混合查询"里协同。
有了这一课，你对 Milvus"<strong>既能按相似度找、又能按条件筛、还能按关键词搜</strong>"的全貌才算补齐。
</p>

<div class="card analogy">
  <div class="tag">📚 生活类比</div>
  最后一次回到图书馆。前几课的"目录卡片"是为"<strong>找内容相近的书</strong>"（向量检索）做的。但读者还有别的问法：
  "<strong>2024 年以后出版的</strong>"（按字段范围筛）——你需要一份<strong>按出版年排好序</strong>的清单（排序索引）；
  "<strong>精装 / 平装</strong>"这种就两三种取值的（低基数）——做一张<strong>"精装→哪些书、平装→哪些书"的对照位图</strong>最省（bitmap）；
  "<strong>书名里带'量子'二字的</strong>"——你需要一份<strong>"词 → 出现在哪些书"的倒排词表</strong>（倒排索引）；
  "<strong>正文里讲到'防水'的</strong>"——那就要给全文做一套<strong>专业的检索引擎</strong>，还要会断词、算相关性打分（全文 / BM25）。
  这些都<strong>不是</strong>"找相似向量"，而是"<strong>按条件精确地筛、按关键词相关地搜</strong>"。一次复杂查询往往<strong>两种都要</strong>：先用标量索引快速筛掉绝大多数书，再在剩下的小堆里做向量相似检索——这就是<strong>混合查询</strong>。
</div>

<h2>标量索引：给过滤那一半提速</h2>
<p>向量检索回答"<strong>最像谁</strong>"，标量过滤回答"<strong>满不满足条件</strong>"。如果过滤字段没有索引，那么"价格 &lt; 100"就只能<strong>逐行扫</strong>一遍所有数据去判断——和没索引的向量检索一样慢。<strong>标量索引</strong>就是为加速这种"按字段值筛"而生的。
这件事的重要性常被低估：在很多真实业务里，<strong>过滤条件才是把候选从"全库"压到"一小撮"的主力</strong>。想象一个有十亿商品的库，一句"类别=数码 且 价格&lt;100"也许就把候选从十亿砍到几十万——如果这一刀砍得慢（逐行扫十亿），那后面再快的向量检索也被拖累了。所以标量索引不是"锦上添花"，而是混合查询里<strong>和向量索引同等重要</strong>的另一半。
Milvus 的标量索引实现住在 C++ core 的 <span class="mono">internal/core/src/index/</span> 下，针对不同<strong>数据特征</strong>提供了好几种，每种擅长一类过滤：</p>

<table class="t">
  <tr><th>标量索引（头文件）</th><th>适合的数据 / 查询</th><th>核心思路</th></tr>
  <tr><td><strong>倒排（<span class="mono">InvertedIndexTantivy.h</span>）</strong></td><td>等值 / 集合判断（=、IN）、字符串</td><td>"值 → 含此值的行"倒排表，tantivy 支撑</td></tr>
  <tr><td><strong>bitmap（<span class="mono">BitmapIndex.h</span>）</strong></td><td><strong>低基数</strong>字段（性别、状态、枚举）</td><td>每个取值一张位图，过滤 = 位运算，极快</td></tr>
  <tr><td><strong>排序（<span class="mono">ScalarIndexSort.h</span> / <span class="mono">StringIndexSort.h</span>）</strong></td><td><strong>范围</strong>查询（&lt;、&gt;、BETWEEN）</td><td>STL_SORT：按值排序后二分定位区间</td></tr>
  <tr><td><strong>ngram（<span class="mono">NgramInvertedIndex.h</span>）</strong></td><td>子串 / 模糊匹配（LIKE '%x%'）</td><td>按 n-gram 切片建倒排，加速含子串查询</td></tr>
  <tr><td><strong>混合（<span class="mono">HybridScalarIndex.h</span>）</strong></td><td>不确定该用哪种时</td><td>按数据特征<strong>自动挑</strong>合适的标量索引</td></tr>
  <tr><td><strong>JSON（<span class="mono">JsonHybridScalarIndex.h</span>）</strong></td><td>JSON / 动态字段里的子键</td><td>为 JSON 路径建标量索引，加速嵌套字段过滤</td></tr>
</table>

<p>读这张表，关键是<strong>"按数据特征选索引"</strong>这条直觉。<strong>低基数</strong>字段（只有寥寥几种取值，如"已上架/已下架"）最适合 <strong>bitmap</strong>：每个取值一张位图，"筛出所有已上架"就是<strong>取出对应位图</strong>，多个条件的 AND/OR 直接做<strong>位运算</strong>，快到极致、还省空间。
<strong>范围</strong>查询（价格区间、时间区间）最适合 <strong>排序索引（STL_SORT）</strong>：把值排好序，二分一下就能定位区间的两端，区间内整段命中。<strong>等值与字符串</strong>查询适合<strong>倒排</strong>：直接查"这个值出现在哪些行"。
当你拿不准时，<strong>HybridScalarIndex</strong> 会<strong>替你自动挑</strong>——这和第 21 课向量的 AUTOINDEX 是同一种"省心"哲学，只是用在标量侧。理解了"<strong>数据长什么样，就配什么索引</strong>"，你就掌握了标量索引选型的主干。</p>

<p>再把几种索引的"性格"各点一句，帮你形成长期记忆。<strong>bitmap</strong> 是低基数之王：当一个字段只有"是/否""红/黄/蓝"这种<strong>屈指可数</strong>的取值时，给每个取值存一张"哪些行是它"的位图，过滤就退化成<strong>位与/位或</strong>，又快又省；但若字段取值成千上万（高基数，如用户 ID），位图会爆炸，就不该用它。
<strong>排序索引（STL_SORT）</strong>是范围查询的利器：把值排好序后，"价格在 50~100 之间"只需<strong>二分</strong>找到区间两端，中间整段命中，避免逐行比较。<strong>倒排</strong>则面向<strong>等值与字符串</strong>：天生回答"<strong>哪些行的这个字段等于 X</strong>"，因为它存的就是"值 → 行"的映射。
<strong>ngram</strong> 解决的是倒排搞不定的<strong>子串模糊匹配</strong>（<span class="inline">LIKE '%关键词%'</span>）：把字符串切成连续的 n 个字符的小片、对这些小片建倒排，于是"含某子串"就能靠命中相应的 n-gram 片段来加速。把这四种性格记住，遇到一个过滤字段，你几乎能<strong>条件反射</strong>地选对索引。</p>

<p>还要专门提一句 <strong>JSON / 动态字段</strong>的索引。回忆第 6 课：Milvus 支持动态字段和 JSON 类型，让你往一行里塞进结构灵活的<strong>嵌套数据</strong>。但灵活是有代价的——如果对 JSON 里的某个子键（如 <span class="inline">meta["brand"]</span>）做过滤，默认也得把每行的 JSON <strong>解析一遍</strong>再判断，很慢。
<strong>JsonHybridScalarIndex</strong>（<span class="mono">JsonHybridScalarIndex.h</span>）就是为此而生：它能为 JSON 里的<strong>特定路径</strong>建标量索引，把"嵌套字段过滤"也加速到和普通标量字段一个量级。这让"动态/JSON 字段"既保留了<strong>schema 灵活性</strong>，又不至于在过滤性能上吃大亏——又一次体现了 Milvus"<strong>灵活与性能兼得</strong>"的工程取向。</p>

<div class="cols">
  <div class="col"><h4>向量索引（前三课）</h4><p>回答"<strong>最像谁</strong>"。Knowhere 的 HNSW/IVF/DiskANN 等，按<strong>语义相似度</strong>排序，近似检索（ANN）。</p></div>
  <div class="col"><h4>标量索引（本课）</h4><p>回答"<strong>满不满足条件</strong>"。bitmap/排序/倒排等，按<strong>字段值精确</strong>筛选，产出一个 bitset。</p></div>
  <div class="col"><h4>全文索引（本课）</h4><p>回答"<strong>哪些文档最相关</strong>"。tantivy 倒排 + BM25，按<strong>词项相关性</strong>打分排序。</p></div>
</div>

<p>这三类索引各司其职，却又能在一次查询里<strong>叠加</strong>使用，这正是 Milvus 强于"纯向量库"的地方：它不是只会做"找相似向量"这一件事，而是把<strong>相似检索、条件过滤、关键词检索</strong>三种能力<strong>统一</strong>进了同一个引擎、同一份数据、同一次查询里。这背后是一个朴素但重要的判断：真实业务里的检索，几乎<strong>从不是</strong>"只按向量"或"只按条件"，而总是<strong>二者乃至三者的组合</strong>——"在符合某些条件、且文本相关的候选里，找语义最像的"。把三种索引都备齐并能协同，Milvus 才配称为一个能扛真实业务的<strong>向量数据库</strong>，而非一个孤立的"向量检索算法库"。</p>

<h2>倒排索引与全文检索：Rust 的 tantivy 引擎</h2>
<p>上表里反复出现的<strong>倒排</strong>，以及"全文检索"，背后是同一个引擎：<strong>tantivy</strong>——一个用 <strong>Rust</strong> 写的全文搜索库（类比 Java 世界的 Lucene）。这正是第 2 课说的"三语言分工"里 <strong>Rust 负责全文索引</strong>那一块的落地。
Milvus 的 C++ core 通过 <span class="mono">internal/core/src/index/InvertedIndexTantivy.h</span>（<span class="inline">InvertedIndexTantivy</span> 类）<strong>封装并调用</strong> tantivy；C++ 与 Rust 之间通过 <span class="mono">internal/core/thirdparty/tantivy</span> 下的绑定层（FFI）打通。也就是说，倒排索引的"脏活累活"——分词、建词表、布尔检索、相关性打分——都<strong>外包给 tantivy</strong> 这个专业引擎，C++ 这侧只负责把它接进 Milvus 的段与查询体系。</p>

<div class="layers">
  <div class="layer l-app"><span class="badge">Milvus core (C++)</span><span class="name">InvertedIndexTantivy</span><span class="ld">internal/core/src/index/InvertedIndexTantivy.{h,cpp}：把倒排/全文接入段与查询</span></div>
  <div class="layer l-main"><span class="badge">绑定层 (FFI)</span><span class="name">thirdparty/tantivy</span><span class="ld">C++ ↔ Rust 的桥：rust-binding / tantivy-wrapper</span></div>
  <div class="layer l-core"><span class="badge">引擎 (Rust)</span><span class="name">tantivy</span><span class="ld">分词、倒排词表、布尔检索、BM25 相关性打分</span></div>
</div>

<p><strong>全文检索（full-text search）</strong>就是建立在这套倒排之上的。当你对一段文本做"包含关键词"的搜索时，tantivy 会先<strong>分词</strong>（把句子切成词项）、对每个词项维护"<strong>它出现在哪些文档、出现几次</strong>"的倒排表，查询时再用 <strong>BM25</strong> 这类相关性模型给文档<strong>打分排序</strong>——分数高（既包含查询词、又不是因为该词烂大街）的文档排在前面。
这和向量检索的"按相似度排序"形成了有趣的对照：<strong>向量检索按"语义相近"排，全文检索按"词项相关"排</strong>。Milvus 把两者都纳入麾下，于是它既能做"<strong>语义搜索</strong>"（找意思相近的），又能做"<strong>关键词搜索</strong>"（找字面命中的），还能把两者<strong>融合</strong>成更强的检索（混合检索，后续课程展开）。BM25 这类全文打分，正是借由 tantivy 倒排实现的。</p>

<p>这里值得把<strong>稀疏向量</strong>和<strong>全文检索</strong>的关系点破，因为它们容易混。第 22 课讲过 Knowhere 的稀疏向量索引（SPARSE_INVERTED_INDEX/WAND），而本课讲 tantivy 的全文倒排——两者<strong>思路相通</strong>（都是倒排 + 打分剪枝），却处在<strong>不同层次</strong>：全文检索面向<strong>原始文本</strong>，自己负责分词、建词表、按 BM25 打分；稀疏向量检索面向<strong>已经向量化</strong>的"词→权重"映射（往往正是某个 BM25/SPLADE 模型的输出），在向量层面做检索。
换句话说，你既可以让 Milvus <strong>直接对文本</strong>做全文检索（走 tantivy），也可以先把文本<strong>编码成稀疏向量</strong>再做稀疏向量检索（走 Knowhere）。两条路殊途同归，都能实现"按词项命中"的关键词式检索，只是落在了引擎栈的不同位置。理解这层区分，你读 Milvus 文档时就不会被"全文检索""稀疏向量""BM25"这几个词绕晕。</p>

<h2>标量过滤 + 向量 ANN：一次混合查询怎么协同</h2>
<p>把标量索引和向量索引<strong>合到一次查询里</strong>，才是它们真正的用武之地。考虑一个典型请求："在<strong>类别=数码 且 价格&lt;100</strong> 的商品里，找和这张图<strong>最像</strong>的 10 件"。这里既有<strong>标量过滤</strong>（类别、价格），又有<strong>向量 ANN</strong>（最像）。Milvus 的执行思路是<strong>先筛后搜</strong>：</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>标量过滤（缩小候选）</h4><p>用<strong>标量索引</strong>（bitmap/排序/倒排）快速算出"<strong>满足 类别=数码 且 价格&lt;100</strong>"的行集合——一个<strong>位图（bitset）</strong>。绝大多数不合格的数据在这一步就被<strong>整片排除</strong>。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>向量 ANN（带过滤检索）</h4><p>把这个 bitset 作为<strong>过滤掩码</strong>交给向量检索：在 ANN 搜索（HNSW/IVF）时，<strong>只在通过过滤的行里</strong>找最近邻，不浪费算力在已被排除的数据上。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>归并取 topK</h4><p>各段算出局部结果，归并出全局<strong>最像的 10 件</strong>——它们<strong>既满足标量条件、又向量最相近</strong>。</p></div></div>
</div>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="混合查询先筛后搜：标量索引算出 bitset 过滤掩码，下推给向量 ANN，让 ANN 只在通过过滤的行里找最近邻，召回稳定">
    <rect x="170" y="34" width="420" height="40" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="380" y="59" text-anchor="middle" style="fill:var(--ink)">查询：类别=数码 ∧ 价格&lt;100 → 找最像 top10</text>
    <rect x="36" y="100" width="170" height="50" rx="10" style="fill:var(--panel);stroke:var(--accent);stroke-width:1.5"/><text x="121" y="122" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">标量索引</text><text x="121" y="140" text-anchor="middle" style="fill:var(--muted)">bitmap / 排序 / 倒排</text>
    <text x="36" y="174" style="fill:var(--muted)">bitset 掩码（通过=1）</text>
    <rect x="40" y="182" width="24" height="26" rx="4" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="52" y="200" text-anchor="middle" class="mono" style="fill:var(--accent-ink)">1</text>
    <rect x="66" y="182" width="24" height="26" rx="4" style="fill:var(--panel-2);stroke:var(--line)"/><text x="78" y="200" text-anchor="middle" class="mono" style="fill:var(--faint)">0</text>
    <rect x="92" y="182" width="24" height="26" rx="4" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="104" y="200" text-anchor="middle" class="mono" style="fill:var(--accent-ink)">1</text>
    <rect x="118" y="182" width="24" height="26" rx="4" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="130" y="200" text-anchor="middle" class="mono" style="fill:var(--accent-ink)">1</text>
    <rect x="144" y="182" width="24" height="26" rx="4" style="fill:var(--panel-2);stroke:var(--line)"/><text x="156" y="200" text-anchor="middle" class="mono" style="fill:var(--faint)">0</text>
    <rect x="170" y="182" width="24" height="26" rx="4" style="fill:var(--panel-2);stroke:var(--line)"/><text x="182" y="200" text-anchor="middle" class="mono" style="fill:var(--faint)">0</text>
    <rect x="196" y="182" width="24" height="26" rx="4" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="208" y="200" text-anchor="middle" class="mono" style="fill:var(--accent-ink)">1</text>
    <rect x="222" y="182" width="24" height="26" rx="4" style="fill:var(--panel-2);stroke:var(--line)"/><text x="234" y="200" text-anchor="middle" class="mono" style="fill:var(--faint)">0</text>
    <line x1="258" y1="125" x2="354" y2="125" style="stroke:var(--accent);stroke-width:2;stroke-dasharray:5 4"/><path d="M354,125 l-11,-5 l0,10 z" style="fill:var(--accent)"/>
    <text x="306" y="115" text-anchor="middle" style="fill:var(--accent-ink)">掩码下推</text>
    <rect x="356" y="100" width="210" height="66" rx="10" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/><text x="461" y="128" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">向量 ANN（HNSW/IVF）</text><text x="461" y="150" text-anchor="middle" style="fill:var(--muted)">只在"通过"的行里找最近邻</text>
    <line x1="566" y1="133" x2="600" y2="133" style="stroke:var(--teal);stroke-width:2"/><path d="M600,133 l-11,-5 l0,10 z" style="fill:var(--teal)"/>
    <rect x="602" y="108" width="150" height="52" rx="10" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="677" y="130" text-anchor="middle" style="fill:var(--teal);font-weight:700">top10</text><text x="677" y="150" text-anchor="middle" style="fill:var(--muted)">合格 + 最像</text>
    <text x="380" y="246" text-anchor="middle" style="fill:var(--muted)"><tspan style="fill:var(--teal);font-weight:700">先筛后搜（谓词下推）→ 召回稳定 ✓</tspan>　｜　先搜后筛 → 严过滤时 topK 可能全被筛光 ✗</text>
  </svg>
  <div class="figcap"><b>先筛后搜：把过滤掩码下推给 ANN</b>：标量索引先算出一张 <span class="mono">bitset</span>（哪些行通过 <span class="mono">类别=数码 ∧ 价格&lt;100</span>），再把它<b>下推</b>给向量 ANN——ANN <b>只在通过过滤的行里</b>找最近邻。这就是<b>谓词下推</b>：比"先搜完整 ANN、再事后筛掉"召回稳得多（严过滤时后者可能把 topK 全筛光）。</div>
</div>

<p>这里的关键设计是：<strong>标量过滤的结果（bitset）会"喂进"向量检索，让 ANN 在过滤后的子集上跑</strong>，而不是"先做完整 ANN、再事后筛掉不合格的"。后者（先搜后筛）有个致命问题：如果过滤条件很严（比如只有 1% 数据合格），先搜出来的 topK 可能<strong>全被筛光</strong>，导致召回骤降甚至空结果。<strong>先筛后搜</strong>（把过滤掩码下推进 ANN）则保证 topK 是<strong>在合格集合里</strong>选出来的，召回稳定。顺带说一句：这种"<strong>把过滤条件尽量往底层推</strong>"的思路，在数据库里有个通用名字叫<strong>谓词下推（predicate pushdown）</strong>——能在更早、更底层把不合格数据剔除，就别让它流到更贵的后续算子里。Milvus 把标量过滤的 bitset 下推进向量 ANN，正是谓词下推在"向量检索"语境下的体现。
这正是标量索引<strong>不可或缺</strong>的原因：它让"过滤"这一步<strong>足够快、且能把结果以 bitset 形式精确地交给向量检索</strong>。没有标量索引，过滤要逐行扫；有了它，过滤变成位运算，再把掩码下推给 ANN——标量与向量两套索引，就这样在一次查询里<strong>分工协同</strong>，共同把"带条件的相似检索"做快、做准。</p>

<p>到这里，<strong>第五部分·索引</strong>就讲完了，把四课串成一条线收个尾：第 21 课讲<strong>索引服务</strong>（DataCoord 调度、worker 执行，无 indexnode）；第 22 课讲 <strong>Knowhere 向量索引</strong>（FLAT/IVF/HNSW/DiskANN…的取舍与参数）；第 23 课讲<strong>构建与加载</strong>（sealed 段 → 构建 → 索引文件 → QueryNode 加载，growing 用暴力扫描）；本课讲<strong>标量与全文索引</strong>（倒排/bitmap/排序/ngram/JSON + tantivy 全文，与向量混合检索）。
四课合起来回答了一个完整的问题：<strong>Milvus 如何把"原始数据"变成"能被各种方式快速检索的资产"</strong>。索引是连接"<strong>写入</strong>"（前四部分）与"<strong>读取</strong>"（后续部分）的<strong>枢纽</strong>——写入把数据落成段，索引把段变得可检索，读取才能在毫秒级里既按相似度找、又按条件筛、还按关键词搜。下一部分，我们就正式进入<strong>查询链路</strong>，看一次 search 请求如何穿过 Proxy、QueryNode、各段索引，最终归并出你要的结果。回头看这四课，你会发现一个反复出现的母题：<strong>用空间换时间</strong>——无论是向量的 HNSW 图、IVF 倒排桶，还是标量的位图、排序数组、tantivy 倒排表，本质都是<strong>预先多存一份"为检索优化过的结构"</strong>，把查询时本来要做的全量扫描，换成查询时的少量跳转。理解了这一点，你就握住了所有索引设计的总钥匙。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/index/InvertedIndexTantivy.h</span><span class="ln">InvertedIndexTantivy：倒排/全文标量索引，封装 Rust tantivy（节选）</span></div>
  <pre><span class="cm">// C++ 侧的标量索引实现，内部调用 Rust 的 tantivy 引擎（经 thirdparty/tantivy 绑定）。</span>
<span class="cm">// 倒排（等值/字符串）、全文（BM25）都由它接入 Milvus 的段与查询体系。</span>
<span class="kw">template</span> &lt;<span class="kw">typename</span> T&gt;
<span class="kw">class</span> InvertedIndexTantivy : <span class="kw">public</span> ScalarIndex&lt;T&gt; {
    <span class="cm">// Build：读字段数据 → 交给 tantivy 建倒排</span>
    <span class="cm">// 检索：等值/范围/子串/全文 → 转成 tantivy 查询，返回命中行的 bitset</span>
};
<span class="cm">// 另见 BitmapIndex.h（低基数位图）、ScalarIndexSort.h（STL_SORT 范围）、HybridScalarIndex.h（自动选型）。</span></pre>
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：除了向量索引，Milvus 还为<strong>非向量</strong>检索建<strong>标量索引</strong>（C++ <span class="mono">internal/core/src/index/</span>）——<strong>倒排</strong>（<span class="inline">InvertedIndexTantivy</span>，等值/字符串）、<strong>bitmap</strong>（<span class="inline">BitmapIndex</span>，低基数）、<strong>排序</strong>（<span class="inline">ScalarIndexSort</span> STL_SORT，范围）、<strong>ngram</strong>（子串）、<strong>混合</strong>（<span class="inline">HybridScalarIndex</span> 自动选型）、<strong>JSON</strong>；<strong>全文检索（BM25）</strong>由 Rust 的 <strong>tantivy</strong> 引擎落地（<span class="mono">InvertedIndexTantivy.{cpp,h}</span> + <span class="mono">thirdparty/tantivy</span> 绑定）。混合查询<strong>先筛后搜</strong>：标量索引算出 <strong>bitset</strong> 过滤掩码，下推给向量 ANN，让 ANN 只在合格子集上跑，召回稳定——标量与向量两套索引在一次查询里分工协同。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>标量索引加速过滤</strong>：倒排（<span class="mono">InvertedIndexTantivy.h</span>）、bitmap（<span class="mono">BitmapIndex.h</span> 低基数）、排序（<span class="mono">ScalarIndexSort.h</span> STL_SORT 范围）、ngram、混合（<span class="mono">HybridScalarIndex.h</span> 自动选型）、JSON。</li>
    <li><strong>按数据特征选</strong>：低基数→bitmap、范围→排序、等值/字符串→倒排、子串→ngram、拿不准→Hybrid 自动挑。</li>
    <li><strong>tantivy = Rust 全文引擎</strong>：倒排与全文经 <span class="inline">InvertedIndexTantivy</span> 封装、由 <span class="mono">thirdparty/tantivy</span> 绑定调用，对应第 2 课"Rust 管全文"。</li>
    <li><strong>全文检索 BM25</strong>：tantivy 分词、建倒排、按 BM25 相关性打分；与向量"按语义排"形成"按词项排"的互补。</li>
    <li><strong>混合查询先筛后搜</strong>：标量索引产出 bitset 掩码下推进 ANN，只在合格子集找最近邻；优于"先搜后筛"（严过滤会把 topK 筛空、召回崩）。</li>
    <li><strong>协同</strong>：标量索引让过滤变位运算、向量索引让相似检索变 ANN，两者在一次"带条件的相似检索"里分工。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The indexes of the last three lessons all served <strong>vector search</strong>. But real queries are rarely "pure vector" — they often carry <strong>scalar filters</strong> ("price &lt; 100, category = electronics, listed this week") and <strong>full-text search</strong> ("the product description contains 'waterproof'").
This lesson covers the acceleration of that <strong>non-vector</strong> half: <strong>scalar indexes</strong> (inverted, bitmap, sort, ngram, hybrid, JSON) make filtering fast and cheap; <strong>full-text search (BM25)</strong> is realized via Rust's <strong>tantivy</strong> engine. Finally we see how <strong>scalar filter + vector ANN</strong> cooperate in a single "hybrid query."
With this lesson, your full picture of Milvus — "<strong>find by similarity, filter by condition, and search by keyword</strong>" — is complete.
</p>

<div class="card analogy">
  <div class="tag">📮 Analogy</div>
  One last trip to the library. The "catalog cards" of earlier lessons were for "<strong>finding books with similar content</strong>" (vector search). But readers ask other things too:
  "<strong>published after 2024</strong>" (filter by field range) — you need a list <strong>sorted by publication year</strong> (a sort index);
  "<strong>hardcover / paperback</strong>," with only a few possible values (low cardinality) — a <strong>"hardcover→which books, paperback→which books" bitmap</strong> is cheapest (bitmap);
  "<strong>title contains the word 'quantum'</strong>" — you need an <strong>inverted word list of "term → which books"</strong> (inverted index);
  "<strong>the body text discusses 'waterproof'</strong>" — that demands a proper <strong>search engine</strong> over full text, which also tokenizes and scores relevance (full-text / BM25).
  None of these is "find a similar vector"; they are "<strong>filter precisely by condition, search relevantly by keyword</strong>." A complex query often needs <strong>both</strong>: first use scalar indexes to quickly drop the vast majority of books, then run vector similarity over the small remaining pile — that's a <strong>hybrid query</strong>.
</div>

<h2>Scalar indexes: speeding up the filter half</h2>
<p>Vector search answers "<strong>most like which</strong>"; scalar filtering answers "<strong>does it meet the condition</strong>." If the filter field has no index, then "price &lt; 100" can only be judged by <strong>scanning every row</strong> — as slow as unindexed vector search. <strong>Scalar indexes</strong> exist to speed up exactly this "filter by field value."
The importance of this is often underrated: in many real workloads, <strong>the filter condition is the main force compressing candidates from "the whole collection" to "a small handful."</strong> Imagine a billion-product collection where "category=electronics and price&lt;100" might cut candidates from a billion to a few hundred thousand — if that cut is slow (scanning a billion rows), even the fastest vector search afterward is dragged down. So scalar indexes are not "icing on the cake" but the other half, <strong>as important as the vector index</strong>, in a hybrid query.
Milvus's scalar-index implementations live under the C++ core's <span class="mono">internal/core/src/index/</span>, offering several kinds for different <strong>data characteristics</strong>, each good at a class of filters:</p>

<table class="t">
  <tr><th>Scalar index (header)</th><th>Fit data / query</th><th>Core idea</th></tr>
  <tr><td><strong>Inverted (<span class="mono">InvertedIndexTantivy.h</span>)</strong></td><td>equality / set (=, IN), strings</td><td>"value → rows holding it" inverted list, backed by tantivy</td></tr>
  <tr><td><strong>Bitmap (<span class="mono">BitmapIndex.h</span>)</strong></td><td><strong>low-cardinality</strong> fields (gender, status, enums)</td><td>one bitmap per value; filter = bit ops, very fast</td></tr>
  <tr><td><strong>Sort (<span class="mono">ScalarIndexSort.h</span> / <span class="mono">StringIndexSort.h</span>)</strong></td><td><strong>range</strong> queries (&lt;, &gt;, BETWEEN)</td><td>STL_SORT: sort by value, binary-search the interval</td></tr>
  <tr><td><strong>Ngram (<span class="mono">NgramInvertedIndex.h</span>)</strong></td><td>substring / fuzzy match (LIKE '%x%')</td><td>build inverted lists over n-gram slices to speed substring queries</td></tr>
  <tr><td><strong>Hybrid (<span class="mono">HybridScalarIndex.h</span>)</strong></td><td>when unsure which to use</td><td><strong>auto-pick</strong> a suitable scalar index by data characteristics</td></tr>
  <tr><td><strong>JSON (<span class="mono">JsonHybridScalarIndex.h</span>)</strong></td><td>sub-keys inside JSON / dynamic fields</td><td>build scalar indexes for JSON paths to speed nested-field filtering</td></tr>
</table>

<p>Reading the table, the key intuition is <strong>"pick the index by data characteristics."</strong> <strong>Low-cardinality</strong> fields (only a few values, e.g. "listed/unlisted") suit <strong>bitmap</strong> best: one bitmap per value, "filter all listed" is just <strong>pulling out the matching bitmap</strong>, and multi-condition AND/OR is direct <strong>bit operations</strong> — extremely fast and space-thrifty.
<strong>Range</strong> queries (price interval, time interval) suit a <strong>sort index (STL_SORT)</strong>: sort the values, binary-search to pin the interval's ends, everything inside hits as a block. <strong>Equality and string</strong> queries suit <strong>inverted</strong>: directly look up "which rows hold this value."
When unsure, <strong>HybridScalarIndex</strong> <strong>auto-picks for you</strong> — the same "worry-free" philosophy as Lesson 21's vector AUTOINDEX, applied on the scalar side. Grasp "<strong>match the index to what the data looks like</strong>" and you hold the backbone of scalar-index selection.</p>

<p>Let's give each index a one-line "personality" for long-term memory. <strong>Bitmap</strong> is the king of low cardinality: when a field has only a <strong>handful</strong> of values like "yes/no" or "red/yellow/blue," storing one "which rows have it" bitmap per value reduces filtering to <strong>bit-AND/bit-OR</strong>, fast and thrifty; but if a field has thousands of distinct values (high cardinality, e.g. user IDs), the bitmaps explode and you shouldn't use it.
The <strong>sort index (STL_SORT)</strong> is the tool for range queries: with values sorted, "price between 50 and 100" only needs a <strong>binary search</strong> for the interval's ends, with everything inside hitting as a block, avoiding row-by-row comparison. <strong>Inverted</strong> targets <strong>equality and strings</strong>: it natively answers "<strong>which rows have this field equal to X</strong>" because it stores exactly the "value → rows" mapping.
<strong>Ngram</strong> solves the <strong>substring fuzzy match</strong> that inverted can't (<span class="inline">LIKE '%keyword%'</span>): slice a string into small pieces of n consecutive characters and build inverted lists over those pieces, so "contains a substring" is accelerated by hitting the corresponding n-gram slices. Memorize these four personalities and, facing a filter field, you'll <strong>reflexively</strong> pick the right index.</p>

<p>A special word on <strong>JSON / dynamic field</strong> indexes. Recall Lesson 6: Milvus supports dynamic fields and the JSON type, letting you stuff flexibly-structured <strong>nested data</strong> into a row. But flexibility has a cost — filtering on a sub-key inside JSON (e.g. <span class="inline">meta["brand"]</span>) would by default require <strong>parsing each row's JSON</strong> before judging, which is slow.
<strong>JsonHybridScalarIndex</strong> (<span class="mono">JsonHybridScalarIndex.h</span>) exists for this: it can build scalar indexes for <strong>specific paths</strong> inside JSON, accelerating "nested-field filtering" to the same order as ordinary scalar fields. This lets "dynamic/JSON fields" keep their <strong>schema flexibility</strong> without paying a heavy filter-performance penalty — once more reflecting Milvus's engineering bent toward "<strong>flexibility and performance together</strong>."</p>

<div class="cols">
  <div class="col"><h4>Vector indexes (last 3 lessons)</h4><p>Answer "<strong>most like which</strong>." Knowhere's HNSW/IVF/DiskANN etc., rank by <strong>semantic similarity</strong>, approximate search (ANN).</p></div>
  <div class="col"><h4>Scalar indexes (this lesson)</h4><p>Answer "<strong>does it meet the condition</strong>." bitmap/sort/inverted etc., filter precisely by <strong>field value</strong>, producing a bitset.</p></div>
  <div class="col"><h4>Full-text index (this lesson)</h4><p>Answer "<strong>which documents are most relevant</strong>." tantivy inverted + BM25, score and rank by <strong>term relevance</strong>.</p></div>
</div>

<p>These three index classes each do their job, yet can be <strong>stacked</strong> in one query — exactly where Milvus beats a "pure vector store": it doesn't only do "find a similar vector," but <strong>unifies</strong> three capabilities — <strong>similarity search, conditional filtering, keyword retrieval</strong> — into one engine, one dataset, one query. Behind this is a plain but important judgment: real-world retrieval is almost <strong>never</strong> "by vector only" or "by condition only," but always a <strong>combination of two or even three</strong> — "among candidates meeting some conditions and textually relevant, find the semantically most alike." Stocking all three index families and making them cooperate is what earns Milvus the name of a real-workload <strong>vector database</strong>, not an isolated "vector-search algorithm library."</p>

<h2>Inverted index and full-text search: Rust's tantivy engine</h2>
<p>The <strong>inverted</strong> index that keeps recurring above, and "full-text search," share one engine behind them: <strong>tantivy</strong> — a full-text search library written in <strong>Rust</strong> (analogous to Lucene in the Java world). This is the realization of "Rust handles full-text indexing" from Lesson 2's "three-language split."
Milvus's C++ core <strong>wraps and calls</strong> tantivy through <span class="mono">internal/core/src/index/InvertedIndexTantivy.h</span> (the <span class="inline">InvertedIndexTantivy</span> class); the C++↔Rust bridge is the binding layer (FFI) under <span class="mono">internal/core/thirdparty/tantivy</span>. That is, the "dirty heavy work" of an inverted index — tokenization, building the term table, boolean retrieval, relevance scoring — is all <strong>outsourced to tantivy</strong>, the professional engine, while the C++ side only wires it into Milvus's segment and query system.</p>

<div class="layers">
  <div class="layer l-app"><span class="badge">Milvus core (C++)</span><span class="name">InvertedIndexTantivy</span><span class="ld">internal/core/src/index/InvertedIndexTantivy.{h,cpp}: wires inverted/full-text into segments &amp; queries</span></div>
  <div class="layer l-main"><span class="badge">binding (FFI)</span><span class="name">thirdparty/tantivy</span><span class="ld">the C++ ↔ Rust bridge: rust-binding / tantivy-wrapper</span></div>
  <div class="layer l-core"><span class="badge">engine (Rust)</span><span class="name">tantivy</span><span class="ld">tokenization, inverted term table, boolean retrieval, BM25 relevance scoring</span></div>
</div>

<p><strong>Full-text search</strong> is built on top of this inverted index. When you search "contains keyword" over a text, tantivy first <strong>tokenizes</strong> (splits the sentence into terms), maintains for each term an inverted list of "<strong>which documents it appears in, and how often</strong>," and at query time uses a relevance model like <strong>BM25</strong> to <strong>score and rank</strong> documents — those scoring high (containing the query terms, and not because the term is ubiquitous) rank first.
This forms an interesting contrast with vector search's "rank by similarity": <strong>vector search ranks by "semantic closeness," full-text search ranks by "term relevance."</strong> Milvus embraces both, so it can do "<strong>semantic search</strong>" (find similar meaning) and "<strong>keyword search</strong>" (find literal hits), and even <strong>fuse</strong> the two into stronger retrieval (hybrid retrieval, covered later). BM25-style full-text scoring is realized precisely via tantivy's inverted index.</p>

<p>It's worth clarifying the relationship between <strong>sparse vectors</strong> and <strong>full-text search</strong>, since they're easy to confuse. Lesson 22 covered Knowhere's sparse-vector indexes (SPARSE_INVERTED_INDEX/WAND), while this lesson covers tantivy's full-text inverted index — the two share <strong>the same idea</strong> (inverted + scored pruning) yet sit at <strong>different levels</strong>: full-text search targets <strong>raw text</strong>, handling tokenization, term-table building, and BM25 scoring itself; sparse-vector search targets an <strong>already-vectorized</strong> "term→weight" map (often the very output of a BM25/SPLADE model), doing retrieval at the vector level.
In other words, you can have Milvus do full-text search <strong>directly on text</strong> (via tantivy), or first <strong>encode text into a sparse vector</strong> and do sparse-vector search (via Knowhere). The two paths converge — both achieve "term-hit" keyword-style retrieval — they just land at different spots in the engine stack. Grasp this distinction and you won't get tangled by the words "full-text search," "sparse vector," and "BM25" when reading Milvus docs.</p>

<h2>Scalar filter + vector ANN: how a hybrid query cooperates</h2>
<p>Putting scalar and vector indexes <strong>into one query</strong> is where they truly shine. Consider a typical request: "among products with <strong>category=electronics and price&lt;100</strong>, find the 10 <strong>most like</strong> this image." Here there is both a <strong>scalar filter</strong> (category, price) and a <strong>vector ANN</strong> (most like). Milvus's approach is <strong>filter first, then search</strong>:</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Scalar filter (shrink candidates)</h4><p>Use <strong>scalar indexes</strong> (bitmap/sort/inverted) to quickly compute the row set "<strong>satisfying category=electronics and price&lt;100</strong>" — a <strong>bitmap (bitset)</strong>. The vast majority of non-qualifying data is <strong>excluded wholesale</strong> at this step.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Vector ANN (filtered search)</h4><p>Hand this bitset as a <strong>filter mask</strong> to vector search: during ANN (HNSW/IVF), find nearest neighbors <strong>only among rows that pass the filter</strong>, wasting no compute on already-excluded data.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Merge for topK</h4><p>Each segment computes local results, merged into the global <strong>10 most alike</strong> — they <strong>both satisfy the scalar condition and are vector-nearest</strong>.</p></div></div>
</div>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="A hybrid query is filter-then-search: the scalar index computes a bitset mask, pushed down into vector ANN so ANN searches only the rows that pass the filter, keeping recall stable">
    <rect x="150" y="34" width="460" height="40" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="380" y="59" text-anchor="middle" style="fill:var(--ink)">query: category=electronics ∧ price&lt;100 → find top10 most alike</text>
    <rect x="36" y="100" width="170" height="50" rx="10" style="fill:var(--panel);stroke:var(--accent);stroke-width:1.5"/><text x="121" y="122" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">scalar index</text><text x="121" y="140" text-anchor="middle" style="fill:var(--muted)">bitmap / sort / inverted</text>
    <text x="36" y="174" style="fill:var(--muted)">bitset mask (pass=1)</text>
    <rect x="40" y="182" width="24" height="26" rx="4" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="52" y="200" text-anchor="middle" class="mono" style="fill:var(--accent-ink)">1</text>
    <rect x="66" y="182" width="24" height="26" rx="4" style="fill:var(--panel-2);stroke:var(--line)"/><text x="78" y="200" text-anchor="middle" class="mono" style="fill:var(--faint)">0</text>
    <rect x="92" y="182" width="24" height="26" rx="4" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="104" y="200" text-anchor="middle" class="mono" style="fill:var(--accent-ink)">1</text>
    <rect x="118" y="182" width="24" height="26" rx="4" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="130" y="200" text-anchor="middle" class="mono" style="fill:var(--accent-ink)">1</text>
    <rect x="144" y="182" width="24" height="26" rx="4" style="fill:var(--panel-2);stroke:var(--line)"/><text x="156" y="200" text-anchor="middle" class="mono" style="fill:var(--faint)">0</text>
    <rect x="170" y="182" width="24" height="26" rx="4" style="fill:var(--panel-2);stroke:var(--line)"/><text x="182" y="200" text-anchor="middle" class="mono" style="fill:var(--faint)">0</text>
    <rect x="196" y="182" width="24" height="26" rx="4" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="208" y="200" text-anchor="middle" class="mono" style="fill:var(--accent-ink)">1</text>
    <rect x="222" y="182" width="24" height="26" rx="4" style="fill:var(--panel-2);stroke:var(--line)"/><text x="234" y="200" text-anchor="middle" class="mono" style="fill:var(--faint)">0</text>
    <line x1="258" y1="125" x2="354" y2="125" style="stroke:var(--accent);stroke-width:2;stroke-dasharray:5 4"/><path d="M354,125 l-11,-5 l0,10 z" style="fill:var(--accent)"/>
    <text x="306" y="115" text-anchor="middle" style="fill:var(--accent-ink)">push down</text>
    <rect x="356" y="100" width="210" height="66" rx="10" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/><text x="461" y="128" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">vector ANN (HNSW/IVF)</text><text x="461" y="150" text-anchor="middle" style="fill:var(--muted)">only among "pass" rows</text>
    <line x1="566" y1="133" x2="600" y2="133" style="stroke:var(--teal);stroke-width:2"/><path d="M600,133 l-11,-5 l0,10 z" style="fill:var(--teal)"/>
    <rect x="602" y="108" width="150" height="52" rx="10" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="677" y="130" text-anchor="middle" style="fill:var(--teal);font-weight:700">top10</text><text x="677" y="150" text-anchor="middle" style="fill:var(--muted)">qualified + nearest</text>
    <text x="380" y="246" text-anchor="middle" style="fill:var(--muted)"><tspan style="fill:var(--teal);font-weight:700">filter-then-search (pushdown) → stable recall ✓</tspan> | search-then-filter → may filter the whole topK away ✗</text>
  </svg>
  <div class="figcap"><b>Filter-then-search: push the mask down into ANN</b>: the scalar index first computes a <span class="mono">bitset</span> (which rows pass <span class="mono">category=electronics ∧ price&lt;100</span>), then <b>pushes it down</b> into vector ANN — which searches nearest neighbors <b>only among passing rows</b>. That is <b>predicate pushdown</b>: far more stable recall than "run full ANN then discard" (which, under a selective filter, can wipe out the whole topK).</div>
</div>

<p>The key design here: <strong>the scalar filter's result (a bitset) is "fed into" vector search so ANN runs over the filtered subset</strong>, rather than "run full ANN first, then discard non-qualifying afterward." The latter (search-then-filter) has a fatal flaw: if the filter is selective (say only 1% of data qualifies), the topK first searched out may be <strong>entirely filtered away</strong>, collapsing recall or even returning nothing. <strong>Filter-then-search</strong> (pushing the filter mask down into ANN) guarantees the topK is chosen <strong>within the qualifying set</strong>, with stable recall. As an aside: this "<strong>push the filter condition as low as possible</strong>" idea has a general name in databases — <strong>predicate pushdown</strong> — eliminate non-qualifying data as early and as low as you can, rather than letting it flow into more expensive downstream operators. Milvus pushing the scalar-filter bitset down into vector ANN is precisely predicate pushdown in the "vector search" context.
This is exactly why scalar indexes are <strong>indispensable</strong>: they make "filtering" <strong>fast enough, and able to hand the result to vector search precisely as a bitset</strong>. Without scalar indexes, filtering scans row by row; with them, filtering becomes bit operations, then the mask is pushed down to ANN — the two index families thus <strong>divide labor and cooperate</strong> in one query, jointly making "conditional similarity search" both fast and accurate.</p>

<p>That completes <strong>Part 5 · Indexing</strong>; let's tie the four lessons into one line. Lesson 21 covered the <strong>index service</strong> (DataCoord schedules, a worker executes, no indexnode); Lesson 22, <strong>Knowhere vector indexes</strong> (the tradeoffs and params of FLAT/IVF/HNSW/DiskANN…); Lesson 23, <strong>build and load</strong> (sealed segment → build → index files → QueryNode loads, growing uses brute force); this lesson, <strong>scalar and full-text indexes</strong> (inverted/bitmap/sort/ngram/JSON + tantivy full-text, hybrid with vectors).
Together the four answer one complete question: <strong>how does Milvus turn "raw data" into "an asset searchable fast in every way"</strong>. Indexing is the <strong>hub</strong> connecting "<strong>writes</strong>" (the first four parts) and "<strong>reads</strong>" (later parts) — writes land data into segments, indexes make segments searchable, and only then can reads, in milliseconds, find by similarity, filter by condition, and search by keyword. The next part formally enters the <strong>query path</strong>, watching how a search request traverses the Proxy, QueryNodes, and per-segment indexes to finally merge into the result you asked for. Looking back over these four lessons, you will spot a recurring motif: <strong>trading space for time</strong> — whether it is the vector HNSW graph, IVF inverted buckets, or the scalar bitmap, sorted array, and tantivy inverted list, each is essentially <strong>storing an extra "search-optimized structure" up front</strong>, converting the full scan you would otherwise do at query time into a few cheap jumps. Grasp this and you hold the master key to every index design.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/index/InvertedIndexTantivy.h</span><span class="ln">InvertedIndexTantivy: inverted/full-text scalar index wrapping Rust tantivy (excerpt)</span></div>
  <pre><span class="cm">// The C++-side scalar-index implementation, internally calling Rust's tantivy engine (via the thirdparty/tantivy binding).</span>
<span class="cm">// Inverted (equality/string) and full-text (BM25) are both wired into Milvus's segment &amp; query system through it.</span>
<span class="kw">template</span> &lt;<span class="kw">typename</span> T&gt;
<span class="kw">class</span> InvertedIndexTantivy : <span class="kw">public</span> ScalarIndex&lt;T&gt; {
    <span class="cm">// Build: read field data -> hand to tantivy to build the inverted index</span>
    <span class="cm">// Query: equality/range/substring/full-text -> translate to a tantivy query, return a bitset of matching rows</span>
};
<span class="cm">// See also BitmapIndex.h (low-cardinality bitmap), ScalarIndexSort.h (STL_SORT range), HybridScalarIndex.h (auto-pick).</span></pre>
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: beyond vector indexes, Milvus builds <strong>scalar indexes</strong> for <strong>non-vector</strong> lookups (C++ <span class="mono">internal/core/src/index/</span>) — <strong>inverted</strong> (<span class="inline">InvertedIndexTantivy</span>, equality/string), <strong>bitmap</strong> (<span class="inline">BitmapIndex</span>, low-cardinality), <strong>sort</strong> (<span class="inline">ScalarIndexSort</span> STL_SORT, range), <strong>ngram</strong> (substring), <strong>hybrid</strong> (<span class="inline">HybridScalarIndex</span>, auto-pick), <strong>JSON</strong>; <strong>full-text search (BM25)</strong> is realized by Rust's <strong>tantivy</strong> engine (<span class="mono">InvertedIndexTantivy.{cpp,h}</span> + the <span class="mono">thirdparty/tantivy</span> binding). A hybrid query <strong>filters first, then searches</strong>: scalar indexes compute a <strong>bitset</strong> filter mask, pushed down to vector ANN so it runs over the qualifying subset, keeping recall stable — scalar and vector index families cooperate in a single query.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Scalar indexes speed filtering</strong>: inverted (<span class="mono">InvertedIndexTantivy.h</span>), bitmap (<span class="mono">BitmapIndex.h</span>, low-cardinality), sort (<span class="mono">ScalarIndexSort.h</span> STL_SORT, range), ngram, hybrid (<span class="mono">HybridScalarIndex.h</span>, auto-pick), JSON.</li>
    <li><strong>Pick by data characteristics</strong>: low-cardinality→bitmap, range→sort, equality/string→inverted, substring→ngram, unsure→Hybrid auto-picks.</li>
    <li><strong>tantivy = Rust full-text engine</strong>: inverted and full-text are wrapped by <span class="inline">InvertedIndexTantivy</span> and called via the <span class="mono">thirdparty/tantivy</span> binding, matching Lesson 2's "Rust handles full-text."</li>
    <li><strong>Full-text BM25</strong>: tantivy tokenizes, builds inverted lists, and scores by BM25 relevance; complements vector's "rank by semantics" with "rank by term relevance."</li>
    <li><strong>Hybrid query filters first</strong>: scalar indexes produce a bitset mask pushed down into ANN to find neighbors only in the qualifying subset; better than "search-then-filter" (selective filters empty the topK and crash recall).</li>
    <li><strong>Cooperation</strong>: scalar indexes turn filtering into bit ops, vector indexes turn similarity search into ANN; the two divide labor in one "conditional similarity search."</li>
  </ul>
</div>
""",
}
