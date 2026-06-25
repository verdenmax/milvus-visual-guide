"""Content for Part 2 (foundations). M2 ships lessons 04-08.

Each lesson is a bilingual dict {"zh": html, "en": html}, mirroring the
authoring model established in part1.py: lead -> analogy card -> macro card ->
>=3 visual diagrams per language -> cited code (file+symbol) -> key-points card.
Milvus facts are verified against the repo at /home/verden/course/milvus.
"""

LESSON_04 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
第一部分我们说过，Milvus 把"找相似"变成"在向量空间里找最近邻"。这一课把这句话<strong>拆开揉碎</strong>：
<strong>embedding（嵌入）</strong>到底是什么、向量空间长什么样、衡量"像不像"的<strong>度量（metric）</strong>有哪几种、
什么时候该用哪一种，以及为什么<strong>精确最近邻太慢</strong>、不得不转向 ANN。把这些基础打牢，后面所有关于索引与查询的课才有地基。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把每条数据想成<strong>地图上的一个点</strong>：经度纬度只有两个数，就能定位一座城市；而 embedding 是用<strong>几百上千个数</strong>给一段文字、一张图定位。
  "两座城市远不远"用直线距离量；"两段话像不像"也一样——只不过尺子从二维换成了几百维。<strong>度量</strong>就是你手里那把尺子：
  有人按"直线距离"量（L2），有人按"方向是否一致"量（余弦），选错尺子，"远近"的含义就全乱了。
</div>

<h2>embedding：把万物编码成空间里的一个点</h2>
<p>embedding 是一个训练好的<strong>神经网络模型</strong>的输出：喂进一段文字、一张图、一段音频，它吐出一串<strong>固定长度的浮点数</strong>——这就是向量。
关键性质只有一条，但极其重要：<strong>语义相近的输入，产出的向量在空间里也彼此靠近</strong>。"猫"和"小猫"几乎重叠，"猫"和"利率"则隔得很远。
于是"语义相似"这件以前说不清、道不明的事，第一次有了一把<strong>可计算的尺子</strong>。</p>

<p>两条铁律请记牢：①<strong>维度由模型决定</strong>（常见 384 / 768 / 1024 / 1536 维），同一个集合里的向量必须<strong>同维</strong>，否则没法比较；
②<strong>灌库与查询必须用同一个模型</strong>，否则两边向量根本"不在同一个空间"，比距离毫无意义——好比一个人用米、一个人用英尺报身高，数字再接近也不能直接比。</p>

<p>再补一句关于 embedding "好不好"的直觉：一个<strong>好的</strong>嵌入模型，是在海量数据上训练出来的，它学会的不是"记住每条数据"，而是<strong>把"语义"提炼成方向</strong>——
相关的概念指向相近的方向，无关的概念彼此正交（垂直）。所以"用对模型"几乎和"建对索引"一样重要：再快的检索，建立在错位的向量空间上，找回来的也是一堆<strong>看似相似、实则无关</strong>的结果。
这也是本教程反复强调"灌库与查询同模型"的原因——它是一切相似检索<strong>正确性</strong>的前提，而非性能问题。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>原始数据</h4><p>一段文字、一张图、一段音频……计算机无法直接判断它们"像不像"。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>embedding 模型</h4><p class="mono">bge / BERT / CLIP …</p><p>训练好的网络，把每条数据映射成固定维度的向量。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>向量（如 768 维）</h4><p>空间里的一个点：语义相近 ⇒ 点相近；语义无关 ⇒ 点相距很远。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>用度量衡量"距离"</h4><p>给两点一把尺子（L2 / IP / COSINE…），算出"远近"，就得到"像不像"。</p></div></div>
</div>

<h2>度量：衡量"像不像"的几把尺子</h2>
<p>向量是空间里的点，"两条数据像不像"就翻译成"两个点的<strong>距离</strong>或<strong>相似度</strong>有多少"。在动手之前，先补一句关于<strong>维度</strong>的直觉：
维度不是越高越好。维度越高，模型能塞进去的"语义细节"越多，但存储和计算成本也线性上涨，且过高的维度还会带来后面要讲的"维度灾难"。
工程上常见的取舍是：检索质量要求高就用 768 / 1024 维，要省内存、追求吞吐就用 384 维甚至更低，或者对向量做<strong>量化压缩</strong>（第 5 课展开）。
同一个集合内维度必须一致，这个数字一旦定下来，就跟着这个集合走到底。Milvus 支持的度量名字是<strong>固定且大小写敏感</strong>的字符串常量，
最常用的三把尺子是 <span class="inline">L2</span>、<span class="inline">IP</span>、<span class="inline">COSINE</span>：</p>

<ul>
  <li><strong>L2（欧氏距离）</strong>：两点之间的直线距离，<strong>越小越像</strong>。它关心"绝对位置差多少"，对向量的长度（模长）敏感。</li>
  <li><strong>IP（内积，Inner Product）</strong>：对应元素相乘再相加，<strong>越大越像</strong>。它同时受"方向是否一致"和"模长大小"影响。</li>
  <li><strong>COSINE（余弦相似度）</strong>：只看两个向量的<strong>夹角</strong>，完全忽略模长，<strong>越大（越接近 1）越像</strong>。本质是"先归一化再算内积"。</li>
</ul>

<div class="cellgroup">
  <div class="cg-cap"><b>一次距离计算</b>：查询向量 <span class="mono">q</span> 与库内向量 <span class="mono">v</span> 逐维相乘再相加，得到内积（IP）；L2 则是逐维相减、平方、求和</div>
  <div class="cells"><span class="lab">q</span><span class="cell hl">0.90</span><span class="cell hl">0.10</span><span class="cell hl">0.80</span></div>
  <div class="cells"><span class="lab">v</span><span class="cell">0.88</span><span class="cell">0.12</span><span class="cell">0.79</span></div>
  <div class="cells"><span class="lab">IP</span><span class="cell q">0.90·0.88</span><span class="sep">+</span><span class="cell q">0.10·0.12</span><span class="sep">+</span><span class="cell q">0.80·0.79</span><span class="sep">=</span><span class="cell scale">1.42 越大越像</span></div>
  <div class="cells"><span class="lab">L2²</span><span class="cell q">0.02²</span><span class="sep">+</span><span class="cell q">0.02²</span><span class="sep">+</span><span class="cell q">0.01²</span><span class="sep">=</span><span class="cell scale">0.0009 越小越像</span></div>
</div>

<p>这里藏着一个常见困惑：<strong>"距离"和"相似度"方向相反</strong>。L2 是距离，<strong>越小越好</strong>；IP / COSINE 是相似度，<strong>越大越好</strong>。
Milvus 在内部会统一处理这种排序方向，但你在选度量、看返回分数时要心里有数：看到 L2 别误以为"分数越高越像"。</p>

<h2>归一化：为什么 IP 和 COSINE 常常画等号</h2>
<p>"归一化（normalize）"指把向量<strong>缩放成长度为 1</strong>（除以它的模长），只保留方向、丢掉长度。这件小事会带来一个漂亮的结论：
<strong>对归一化后的向量，内积（IP）就等于余弦相似度（COSINE）</strong>。因为余弦本来就是"先归一化再算内积"，当向量已经是单位长度时，这一步归一化就免了。</p>

<div class="cols">
  <div class="col"><h4>未归一化</h4><p>向量长度各不相同。用 <span class="inline">IP</span> 时，<strong>长向量天然占便宜</strong>（内积偏大）；
  这时若你真正想比的是"方向/语义"，更应该用 <span class="inline">COSINE</span> 或 <span class="inline">L2</span>。</p></div>
  <div class="col"><h4>已归一化（长度=1）</h4><p>长度信息被抹平，只剩方向。此时 <span class="inline">IP == COSINE</span>，
  且 <span class="inline">L2</span> 与 <span class="inline">COSINE</span> 单调对应——用谁结果排序都一样。很多 embedding 模型默认输出就已归一化。</p></div>
</div>

<p>实战经验：如果你的模型文档说"输出已归一化"，那 <span class="inline">IP</span> 与 <span class="inline">COSINE</span> 等价、且最省事；
如果没归一化、又只关心语义方向，用 <span class="inline">COSINE</span> 最稳妥；如果连绝对位置都有意义（比如某些数值特征），才考虑 <span class="inline">L2</span>。
最重要的纪律是：<strong>建索引和搜索必须用同一种度量</strong>，否则"远近"的定义对不上，召回会一塌糊涂。</p>

<h2>二值与稀疏向量：另外几把专用尺子</h2>
<p>除了常见的浮点稠密向量，还有两类特殊向量，它们配专用的度量：</p>
<ul>
  <li><strong>二值向量（BinaryVector）</strong>：每一位非 0 即 1（比如指纹、分子结构哈希）。度量用 <strong>HAMMING</strong>（有多少位不同）或 <strong>JACCARD</strong>（两个集合的重叠程度）。</li>
  <li><strong>稀疏向量（SparseFloatVector）</strong>：维度极高但绝大多数是 0（比如 BM25、SPLADE 这类词项权重）。这类向量天然适合用 <strong>IP（内积）</strong> 来打分。</li>
</ul>

<table class="t">
  <tr><th>度量</th><th>含义</th><th>方向</th><th>典型用途 / 向量类型</th></tr>
  <tr><td><strong>L2</strong></td><td class="mono">欧氏直线距离</td><td>越小越像</td><td>稠密浮点；关心绝对位置</td></tr>
  <tr><td><strong>IP</strong></td><td class="mono">内积</td><td>越大越像</td><td>已归一化稠密向量；<strong>稀疏向量</strong></td></tr>
  <tr><td><strong>COSINE</strong></td><td class="mono">夹角余弦</td><td>越大越像</td><td>稠密向量，只比方向/语义</td></tr>
  <tr><td><strong>HAMMING</strong></td><td class="mono">不同位的个数</td><td>越小越像</td><td>二值向量</td></tr>
  <tr><td><strong>JACCARD</strong></td><td class="mono">集合重叠度</td><td>越小越像</td><td>二值向量</td></tr>
</table>

<p>这些名字不是教程随手起的，而是 Milvus 源码里<strong>逐字定义的常量</strong>。下面这段就是它们的"出生地"——记住这些字符串是<strong>大小写敏感</strong>的，
你在建索引、搜索时填的 <span class="inline">metric_type</span> 必须和它们一模一样。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">pkg/util/metric/metric_type.go</span><span class="ln">MetricType 常量</span></div>
  <pre><span class="kw">type</span> MetricType = <span class="kw">string</span>

<span class="kw">const</span> (
    L2      MetricType = <span class="st">"L2"</span>       <span class="cm">// 欧氏距离，越小越像</span>
    IP      MetricType = <span class="st">"IP"</span>       <span class="cm">// 内积，越大越像</span>
    COSINE  MetricType = <span class="st">"COSINE"</span>   <span class="cm">// 余弦相似度（归一化后 == IP）</span>
    HAMMING MetricType = <span class="st">"HAMMING"</span>  <span class="cm">// 二值向量：不同位的个数</span>
    JACCARD MetricType = <span class="st">"JACCARD"</span>  <span class="cm">// 二值向量：集合重叠度</span>
    <span class="cm">// 还有 BM25、MHJACCARD、SUBSTRUCTURE 等更专门的度量</span>
)</pre>
</div>

<h2>实战：到底该选哪一种度量</h2>
<p>把上面的知识收成一份可操作的决策清单。选度量这件事，归根到底取决于<strong>你的向量从哪来、要比什么</strong>，三句话就能定：</p>

<div class="cols">
  <div class="col"><h4>看模型文档</h4><p>若写明"输出已归一化（normalized / unit length）"，直接用 <span class="inline">IP</span>——它和 <span class="inline">COSINE</span> 等价又最省算力。
  绝大多数主流文本 embedding（如 bge 系列）都属于这一类。</p></div>
  <div class="col"><h4>只比方向/语义</h4><p>向量没归一化、你又只在乎"语义方向像不像"，用 <span class="inline">COSINE</span> 最稳：它自动忽略模长，不会被"长向量"带偏。</p></div>
</div>

<p>剩下两种情况：当<strong>绝对位置/数值大小本身有意义</strong>（某些工程特征、坐标类数据）时，才用 <span class="inline">L2</span>；当向量是<strong>二值或稀疏</strong>时，
按前面的表走 HAMMING / JACCARD / IP。一个最容易踩的坑再强调一次：<strong>同一个集合，建索引用什么度量，搜索就必须用什么度量</strong>，两者必须严格一致——
这不是"建议"，而是"规则"，违反它不会报一个友好的错误，而是<strong>悄悄返回一堆错的结果</strong>，排查起来非常费劲。</p>

<p>最后给一个收尾的直觉：度量决定"什么叫近"，模型决定"向量好不好"，而索引（下一课）决定"找得快不快"。三者是<strong>正交</strong>的三件事，
但在一次真实检索里缺一不可。把这三层在脑子里分开，你以后看任何向量检索的配置、调参、排障，都能立刻定位到"问题出在哪一层"。</p>

<h2>一个算到底的例子：同两条向量，三把尺子各得什么</h2>
<p>把前面的度量真正"算一遍"，直觉会牢固很多。取两条二维向量（维度取小只为方便手算，几百维同理）：
<span class="mono">a = [3, 4]</span>、<span class="mono">b = [4, 3]</span>，它们的模长都是 5（因为 3²+4²=25）。三把尺子分别给出：</p>

<table class="t">
  <tr><th>度量</th><th>怎么算</th><th>结果</th><th>读法</th></tr>
  <tr><td><strong>L2²</strong></td><td class="mono">(3−4)² + (4−3)² = 1 + 1</td><td class="mono">2（L2 = √2 ≈ 1.41）</td><td>距离，越小越像</td></tr>
  <tr><td><strong>IP</strong></td><td class="mono">3·4 + 4·3 = 12 + 12</td><td class="mono">24</td><td>相似度，越大越像</td></tr>
  <tr><td><strong>COSINE</strong></td><td class="mono">IP ÷ (|a|·|b|) = 24 ÷ 25</td><td class="mono">0.96</td><td>相似度，越接近 1 越像</td></tr>
</table>

<p>现在把两条向量都<strong>归一化</strong>（各自除以模长 5）：<span class="mono">a' = [0.6, 0.8]</span>、<span class="mono">b' = [0.8, 0.6]</span>，
再算它们的内积：<span class="mono">0.6·0.8 + 0.8·0.6 = 0.96</span>——<strong>正好等于上面的 COSINE</strong>。这就用具体数字印证了前面那句话：
<strong>对归一化后的向量，IP 就等于 COSINE</strong>。你也能直观看到 L2 与 COSINE"方向相反"：a、b 在位置上隔了一段（L2=√2），但方向相当接近（COSINE=0.96）。
选错尺子，"像不像"的结论可能就完全拧了——这正是"建索引和搜索必须同度量"之所以是<strong>规则而非建议</strong>的原因。</p>

<h2>topK 与分数阈值：一次搜索返回什么</h2>
<p>把"度量"用起来，一次<strong>搜索</strong>就是：给定一个<strong>查询向量</strong>，在集合里按度量算出每条的"远近"，取最接近的 <strong>K</strong> 条返回，这就是 <strong>topK</strong>。
返回结果是<strong>按相似度排好序</strong>的——第 1 名最像，依次往下。业务里还常配一个<strong>分数阈值</strong>：把"虽然排在最前、但其实不够像"的结果挡在门外，
避免给用户返回一堆勉强凑数的近邻。注意阈值的方向要跟着度量走：L2 是"小于某个距离才算像"，COSINE / IP 则是"大于某个分数才算像"。</p>

<div class="trace">
  <div class="tcap"><b>一次 topK=2 检索</b>：查询 <span class="mono">q</span> 对 4 条库内向量算距离（L2，越小越像），排序后取最近 2 条</div>
  <div class="stations">
    <div class="stn"><h5>① 算距离</h5>
      <div class="cellrow"><span class="vc">v1</span><span class="vc hot">0.03</span></div>
      <div class="cellrow"><span class="vc">v2</span><span class="vc">1.42</span></div>
      <div class="cellrow"><span class="vc">v3</span><span class="vc hot">0.07</span></div>
      <div class="cellrow"><span class="vc">v4</span><span class="vc">0.96</span></div>
      <div class="tlab">逐条与 q 比对</div>
    </div>
    <div class="op">排序→</div>
    <div class="stn"><h5>② 升序排</h5>
      <div class="cellrow"><span class="vc hot">v1 0.03</span></div>
      <div class="cellrow"><span class="vc hot">v3 0.07</span></div>
      <div class="cellrow"><span class="vc dim">v4 0.96</span></div>
      <div class="cellrow"><span class="vc dim">v2 1.42</span></div>
      <div class="tlab">距离从小到大</div>
    </div>
    <div class="op">取前2→</div>
    <div class="stn"><h5>③ topK=2</h5>
      <div class="cellrow"><span class="vc blue">v1 ✓</span></div>
      <div class="cellrow"><span class="vc blue">v3 ✓</span></div>
      <div class="tlab">最相似的 2 条返回</div>
    </div>
  </div>
</div>

<p>这张图也顺手揭示了暴力检索的成本：第 ① 步要和<strong>每一条</strong>都算一次距离。库里 4 条没问题，4 亿条就是灾难。这正是下文 ANN 要解决的痛点。</p>

<h2>高维空间为什么反直觉</h2>
<p>我们对"距离"的直觉来自二维、三维世界，但 embedding 动辄几百上千维，那里的几何<strong>和日常经验大不相同</strong>。一个著名现象叫<strong>"维度灾难"</strong>：
维度一高，<strong>几乎所有点之间的距离都趋于接近</strong>，"最近"和"次近"的差距被抹平，精确比较的区分度下降；同时，要在高维空间里"靠分块覆盖"做精确检索，
所需的格子数随维度<strong>指数级爆炸</strong>。这两点合起来意味着：在高维下既<strong>没法</strong>靠简单切分加速精确检索，逐个暴力又太慢——只能退而求其次用<strong>近似</strong>。</p>

<p>换个角度看，这恰恰解释了为什么 ANN 不是"偷懒"，而是高维世界里<strong>唯一可行的工程路线</strong>：既然精确的代价是指数或线性爆炸，那么用一点点召回损失，
换来可控的、毫秒级的检索，就成了必然选择。这也是后面所有索引（IVF、HNSW、PQ、DiskANN）共同的出发点——它们只是<strong>用不同的招式逼近同一个目标</strong>。</p>

<h2>ANN 问题：为什么不能"挨个精确算"</h2>
<p>有了向量和度量，最朴素的搜索就是<strong>暴力检索（brute-force / FLAT）</strong>：把查询向量和库里<strong>每一条</strong>都算一次距离，再排序取最近的 K 条（topK）。
结果<strong>绝对精确</strong>，逻辑也最简单。问题只有一个字：<strong>慢</strong>。</p>

<p>算一笔账：1 亿条 768 维向量，一次查询要做约 <strong>1 亿 × 768 ≈ 768 亿次</strong>乘加运算。单条查询就如此沉重，再叠加成百上千的并发，
任何单机都扛不住。这就是<strong>精确最近邻（exact kNN）</strong>在大规模下的死穴——复杂度 O(N·D) 随数据量<strong>线性增长</strong>，数据涨十倍，延迟也涨十倍。</p>

<table class="t">
  <tr><th>做法</th><th>怎么找</th><th>速度</th><th>结果</th></tr>
  <tr><td><strong>精确 kNN（FLAT）</strong></td><td class="mono">和每条都算距离</td><td>慢 O(N·D)</td><td>100% 精确</td></tr>
  <tr><td><strong>ANN 索引</strong></td><td class="mono">只看一小撮候选</td><td>快（毫秒级）</td><td>近似（召回常 95%+）</td></tr>
</table>

<p>解法是<strong>近似最近邻（ANN, Approximate Nearest Neighbor）</strong>：预先把向量组织成专门的<strong>索引结构</strong>（分桶、建图、压缩……），
查询时<strong>只检查一小撮最可能的候选</strong>，而不是全库扫描。代价是偶尔会漏掉个别真正的最近邻——但实践中<strong>召回率常在 95%~99% 以上</strong>，
而速度能快上<strong>几百倍</strong>。对绝大多数应用，这是一笔极其划算的买卖："用一点点精度，换巨大的速度"。</p>

<p>这一课只把<strong>问题</strong>讲清楚：为什么需要 ANN、它在用什么换什么。至于 ANN <strong>具体怎么实现</strong>——分桶的 IVF、建图的 HNSW、压缩的 PQ、面向磁盘的 DiskANN——
是下一课（第 5 课）的主角。把这一课的"度量"和"为什么近似"装进脑子，你就握住了理解所有向量索引的两把钥匙。
顺带说一句：FLAT（暴力检索）在 Milvus 里也是一个<strong>真实可选的"索引"</strong>——当数据量不大、又要 100% 精确召回时，它反而是最合适的选择。
所以"精确 vs 近似"不是非此即彼，而是 Milvus 留给你的一个<strong>按场景权衡</strong>的旋钮，这正是下一课要展开的主题。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话串起来：<strong>embedding 把数据变成空间里的点 → 度量给出"两点多像"的尺子 → 精确最近邻太慢 → 用 ANN 索引做近似检索</strong>。
  这四步是 Milvus 一切检索能力的地基。度量名字（L2 / IP / COSINE / HAMMING / JACCARD）和"近似换速度"的取舍，会在后面每一节反复出现。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>embedding</strong>：模型把非结构化数据编码成定长向量；语义相近 ⇒ 向量相近。维度由模型定，灌库与查询必须同模型、同维。</li>
    <li><strong>度量</strong>：L2（距离，越小越像）、IP（内积，越大越像）、COSINE（夹角，越大越像）；建索引与搜索<strong>必须用同一种</strong>。</li>
    <li><strong>归一化</strong>：缩放成长度 1 后，<strong>IP == COSINE</strong>；许多 embedding 默认已归一化。</li>
    <li><strong>专用度量</strong>：二值向量用 HAMMING / JACCARD；稀疏向量用 IP。名字大小写敏感（见 <span class="mono">metric_type.go</span>）。</li>
    <li><strong>ANN 问题</strong>：精确 kNN 是 O(N·D)，规模一大就崩；ANN 用一点点召回损失换几百倍提速。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Part 1 said Milvus turns "find similar" into "find nearest neighbors in vector space". This lesson
<strong>takes that sentence apart</strong>: what an <strong>embedding</strong> actually is, what the vector space looks like,
which <strong>metrics</strong> measure "how alike", when to use each, and why <strong>exact nearest-neighbor is too slow</strong>
so we must turn to ANN. Nail these foundations and every later lesson on indexing and querying has solid ground.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of each item as <strong>a point on a map</strong>: just two numbers (lat/long) locate a city; an embedding uses
  <strong>hundreds or thousands of numbers</strong> to locate a sentence or an image. "How far apart are two cities" is
  measured by straight-line distance; "how alike are two sentences" works the same way — only the ruler now lives in
  hundreds of dimensions. A <strong>metric</strong> is the ruler in your hand: some measure straight-line distance (L2),
  some measure whether directions align (cosine). Pick the wrong ruler and "near vs far" loses all meaning.
</div>

<h2>Embeddings: encoding everything into a point in space</h2>
<p>An embedding is the output of a trained <strong>neural network</strong>: feed in text, an image, or audio and it emits a
<strong>fixed-length list of floats</strong> — the vector. There is one property, but it is everything:
<strong>semantically similar inputs land close together</strong> in that space. "cat" and "kitten" nearly overlap;
"cat" and "interest rate" sit far apart. So "semantic similarity", once vague and unmeasurable, finally gets a
<strong>computable ruler</strong>.</p>

<p>Two iron rules: (1) <strong>the model decides the dimension</strong> (commonly 384 / 768 / 1024 / 1536), and all vectors in
one collection must be the <strong>same dimension</strong>, else they can't be compared; (2) <strong>you must use the same model
for ingest and for query</strong>, otherwise the two sides aren't "in the same space" and comparing distances is meaningless —
like one person quoting height in meters and another in feet.</p>

<p>One more intuition about whether an embedding is "good": a <strong>good</strong> embedding model is trained on huge data and learns not
to "memorize each item" but to <strong>distill meaning into direction</strong> — related concepts point in nearby directions, unrelated
ones become orthogonal (perpendicular). So "using the right model" matters almost as much as "building the right index": however
fast your retrieval, built on a misaligned vector space it returns results that <strong>look similar but are actually unrelated</strong>.
That's why this guide keeps stressing "same model for ingest and query" — it's a precondition for the <strong>correctness</strong> of all
similarity search, not a performance knob.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Raw data</h4><p>Text, an image, audio… a computer can't directly tell whether they "look alike".</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Embedding model</h4><p class="mono">bge / BERT / CLIP …</p><p>A trained network mapping each item to a fixed-dimension vector.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Vector (e.g. 768-d)</h4><p>A point in space: similar meaning ⇒ near points; unrelated ⇒ far apart.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Measure "distance"</h4><p>Give the two points a ruler (L2 / IP / COSINE…) to get "near/far" = "alike or not".</p></div></div>
</div>

<h2>Metrics: the rulers that measure "how alike"</h2>
<p>Vectors are points, so "are two items alike" becomes "how big is the <strong>distance</strong> or <strong>similarity</strong> between two
points". Before diving in, one intuition about <strong>dimension</strong>: higher isn't always better. More dimensions let the model pack
in more semantic detail, but storage and compute cost rise linearly, and overly high dimensions invite the "curse of
dimensionality" discussed later. A common trade: use 768 / 1024 dims when retrieval quality matters, drop to 384 or lower to save
memory and chase throughput, or <strong>quantize/compress</strong> the vectors (Lesson 5). All vectors in a collection share one dimension,
and once chosen that number stays with the collection for life. Milvus's metric names are <strong>fixed, case-sensitive</strong> string
constants; the three everyday rulers are <span class="inline">L2</span>, <span class="inline">IP</span>, and <span class="inline">COSINE</span>:</p>

<ul>
  <li><strong>L2 (Euclidean)</strong>: straight-line distance between two points, <strong>smaller is more alike</strong>. It cares about
  "how far apart in absolute position" and is sensitive to vector length (magnitude).</li>
  <li><strong>IP (Inner Product)</strong>: multiply matching elements and sum, <strong>larger is more alike</strong>. It is affected by both
  direction alignment and magnitude.</li>
  <li><strong>COSINE (cosine similarity)</strong>: looks only at the <strong>angle</strong> between two vectors, ignoring magnitude;
  <strong>larger (closer to 1) is more alike</strong>. It is essentially "normalize first, then take the inner product".</li>
</ul>

<div class="cellgroup">
  <div class="cg-cap"><b>One distance computation</b>: query <span class="mono">q</span> times in-store vector <span class="mono">v</span> element-by-element, summed = inner product (IP); L2 instead subtracts, squares, sums</div>
  <div class="cells"><span class="lab">q</span><span class="cell hl">0.90</span><span class="cell hl">0.10</span><span class="cell hl">0.80</span></div>
  <div class="cells"><span class="lab">v</span><span class="cell">0.88</span><span class="cell">0.12</span><span class="cell">0.79</span></div>
  <div class="cells"><span class="lab">IP</span><span class="cell q">0.90·0.88</span><span class="sep">+</span><span class="cell q">0.10·0.12</span><span class="sep">+</span><span class="cell q">0.80·0.79</span><span class="sep">=</span><span class="cell scale">1.42 bigger = closer</span></div>
  <div class="cells"><span class="lab">L2²</span><span class="cell q">0.02²</span><span class="sep">+</span><span class="cell q">0.02²</span><span class="sep">+</span><span class="cell q">0.01²</span><span class="sep">=</span><span class="cell scale">0.0009 smaller = closer</span></div>
</div>

<p>A common confusion hides here: <strong>"distance" and "similarity" point opposite ways</strong>. L2 is a distance, so
<strong>smaller is better</strong>; IP / COSINE are similarities, so <strong>larger is better</strong>. Milvus normalizes the sort order
internally, but when choosing a metric and reading scores, keep it straight: with L2, do not assume "higher score = more alike".</p>

<h2>Normalization: why IP and COSINE often become equal</h2>
<p>"Normalizing" a vector means <strong>scaling it to length 1</strong> (dividing by its magnitude), keeping direction and discarding
length. This small act yields a neat result: <strong>for normalized vectors, the inner product (IP) equals cosine similarity
(COSINE)</strong>. Cosine is already "normalize then inner-product"; if the vectors are already unit-length, that normalize step
is free.</p>

<div class="cols">
  <div class="col"><h4>Not normalized</h4><p>Vectors have different lengths. With <span class="inline">IP</span>, <strong>longer vectors get an unfair edge</strong>
  (bigger inner product); if what you really want to compare is direction/meaning, prefer <span class="inline">COSINE</span> or
  <span class="inline">L2</span>.</p></div>
  <div class="col"><h4>Normalized (length = 1)</h4><p>Length information is flattened away; only direction remains. Now
  <span class="inline">IP == COSINE</span>, and <span class="inline">L2</span> maps monotonically to <span class="inline">COSINE</span> — any of
  them ranks the same. Many embedding models already output normalized vectors.</p></div>
</div>

<p>Rule of thumb: if your model's docs say "outputs are normalized", then <span class="inline">IP</span> and
<span class="inline">COSINE</span> are equivalent and IP is cheapest; if not normalized and you only care about semantic direction,
<span class="inline">COSINE</span> is safest; only when absolute position matters (some numeric features) consider
<span class="inline">L2</span>. The cardinal discipline: <strong>build the index and search with the same metric</strong>, or the
definition of "near/far" won't line up and recall collapses.</p>

<h2>Binary and sparse vectors: a few more specialized rulers</h2>
<p>Beyond the everyday dense float vectors, two special kinds come with their own metrics:</p>
<ul>
  <li><strong>Binary vectors (BinaryVector)</strong>: every bit is 0 or 1 (e.g. fingerprints, molecular hashes). Use
  <strong>HAMMING</strong> (how many bits differ) or <strong>JACCARD</strong> (set overlap).</li>
  <li><strong>Sparse vectors (SparseFloatVector)</strong>: huge dimension but mostly zeros (e.g. BM25, SPLADE term weights). These are
  naturally scored with <strong>IP (inner product)</strong>.</li>
</ul>

<table class="t">
  <tr><th>Metric</th><th>Meaning</th><th>Direction</th><th>Typical use / vector type</th></tr>
  <tr><td><strong>L2</strong></td><td class="mono">Euclidean distance</td><td>smaller = closer</td><td>dense floats; absolute position matters</td></tr>
  <tr><td><strong>IP</strong></td><td class="mono">inner product</td><td>larger = closer</td><td>normalized dense; <strong>sparse vectors</strong></td></tr>
  <tr><td><strong>COSINE</strong></td><td class="mono">angle cosine</td><td>larger = closer</td><td>dense, compare direction/meaning only</td></tr>
  <tr><td><strong>HAMMING</strong></td><td class="mono">differing bits</td><td>smaller = closer</td><td>binary vectors</td></tr>
  <tr><td><strong>JACCARD</strong></td><td class="mono">set overlap</td><td>smaller = closer</td><td>binary vectors</td></tr>
</table>

<p>These names aren't invented by the tutorial — they are <strong>literally defined constants</strong> in Milvus source. Below is their
"birthplace"; remember the strings are <strong>case-sensitive</strong>, and the <span class="inline">metric_type</span> you pass when
building an index or searching must match them exactly.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">pkg/util/metric/metric_type.go</span><span class="ln">MetricType constants</span></div>
  <pre><span class="kw">type</span> MetricType = <span class="kw">string</span>

<span class="kw">const</span> (
    L2      MetricType = <span class="st">"L2"</span>       <span class="cm">// Euclidean distance, smaller = closer</span>
    IP      MetricType = <span class="st">"IP"</span>       <span class="cm">// inner product, larger = closer</span>
    COSINE  MetricType = <span class="st">"COSINE"</span>   <span class="cm">// cosine similarity (== IP once normalized)</span>
    HAMMING MetricType = <span class="st">"HAMMING"</span>  <span class="cm">// binary vectors: number of differing bits</span>
    JACCARD MetricType = <span class="st">"JACCARD"</span>  <span class="cm">// binary vectors: set overlap</span>
    <span class="cm">// plus more specialized metrics: BM25, MHJACCARD, SUBSTRUCTURE, …</span>
)</pre>
</div>

<h2>In practice: which metric should you actually pick</h2>
<p>Let's distill the above into an actionable checklist. Choosing a metric ultimately depends on <strong>where your vectors come from
and what you're comparing</strong>; three sentences settle it:</p>

<div class="cols">
  <div class="col"><h4>Read the model docs</h4><p>If it says "outputs are normalized / unit length", just use <span class="inline">IP</span> — equivalent to
  <span class="inline">COSINE</span> but cheapest. Most mainstream text embeddings (e.g. the bge family) fall here.</p></div>
  <div class="col"><h4>Compare direction/meaning only</h4><p>If vectors aren't normalized and you only care about "semantic direction", <span class="inline">COSINE</span>
  is safest: it ignores magnitude automatically and won't be skewed by "long vectors".</p></div>
</div>

<p>The remaining cases: use <span class="inline">L2</span> only when <strong>absolute position / magnitude itself is meaningful</strong> (some
engineering features, coordinate-like data); for <strong>binary or sparse</strong> vectors, follow the earlier table — HAMMING / JACCARD / IP.
One trap, stated once more: <strong>within a collection, whatever metric you build the index with, you must search with</strong> — the two
must match exactly. This isn't "advice", it's a "rule"; breaking it won't raise a friendly error, it <strong>silently returns wrong
results</strong> that are painful to debug.</p>

<p>A closing intuition: the metric decides "what counts as near", the model decides "how good the vectors are", and the index
(next lesson) decides "how fast you find them". The three are <strong>orthogonal</strong>, yet all indispensable in one real search. Keep
these three layers separate in your head and you'll instantly locate "which layer the problem is in" when reading any vector-search
config, tuning, or incident.</p>

<h2>A worked example: same two vectors, what each of the three rulers gives</h2>
<p>Actually "computing" the metrics once makes the intuition stick. Take two 2-D vectors (small dimensions just for hand-calculation; the
same holds in hundreds of dimensions): <span class="mono">a = [3, 4]</span> and <span class="mono">b = [4, 3]</span>, both with magnitude 5
(since 3²+4²=25). The three rulers give:</p>

<table class="t">
  <tr><th>Metric</th><th>How to compute</th><th>Result</th><th>How to read</th></tr>
  <tr><td><strong>L2²</strong></td><td class="mono">(3−4)² + (4−3)² = 1 + 1</td><td class="mono">2 (L2 = √2 ≈ 1.41)</td><td>distance, smaller = more alike</td></tr>
  <tr><td><strong>IP</strong></td><td class="mono">3·4 + 4·3 = 12 + 12</td><td class="mono">24</td><td>similarity, larger = more alike</td></tr>
  <tr><td><strong>COSINE</strong></td><td class="mono">IP ÷ (|a|·|b|) = 24 ÷ 25</td><td class="mono">0.96</td><td>similarity, closer to 1 = more alike</td></tr>
</table>

<p>Now <strong>normalize</strong> both vectors (divide each by its magnitude 5): <span class="mono">a' = [0.6, 0.8]</span> and
<span class="mono">b' = [0.8, 0.6]</span>, then take their inner product: <span class="mono">0.6·0.8 + 0.8·0.6 = 0.96</span> — <strong>exactly the
COSINE above</strong>. That confirms with concrete numbers the earlier claim: <strong>for normalized vectors, IP equals COSINE</strong>. You can also
see L2 and COSINE point "opposite ways": a and b sit some distance apart (L2=√2) yet point in quite similar directions (COSINE=0.96). Pick
the wrong ruler and the "alike or not" verdict can flip entirely — which is exactly why "index and search must use the same metric" is a
<strong>rule, not a suggestion</strong>.</p>

<h2>topK and score thresholds: what one search returns</h2>
<p>Putting metrics to work, one <strong>search</strong> is: given a <strong>query vector</strong>, compute "near/far" for each item by the metric,
and return the nearest <strong>K</strong> — that is <strong>topK</strong>. Results are <strong>sorted by similarity</strong> — rank 1 most alike, then down.
Apps often add a <strong>score threshold</strong> to keep out "ranked first but not actually close enough" results, avoiding a list of
barely-qualifying neighbors. Mind the direction: with L2 it's "closer than some distance counts as alike"; with COSINE / IP it's
"above some score counts as alike".</p>

<div class="trace">
  <div class="tcap"><b>One topK=2 search</b>: query <span class="mono">q</span> vs 4 stored vectors by distance (L2, smaller = closer), sort, keep nearest 2</div>
  <div class="stations">
    <div class="stn"><h5>① Distances</h5>
      <div class="cellrow"><span class="vc">v1</span><span class="vc hot">0.03</span></div>
      <div class="cellrow"><span class="vc">v2</span><span class="vc">1.42</span></div>
      <div class="cellrow"><span class="vc">v3</span><span class="vc hot">0.07</span></div>
      <div class="cellrow"><span class="vc">v4</span><span class="vc">0.96</span></div>
      <div class="tlab">compare each to q</div>
    </div>
    <div class="op">sort→</div>
    <div class="stn"><h5>② Ascending</h5>
      <div class="cellrow"><span class="vc hot">v1 0.03</span></div>
      <div class="cellrow"><span class="vc hot">v3 0.07</span></div>
      <div class="cellrow"><span class="vc dim">v4 0.96</span></div>
      <div class="cellrow"><span class="vc dim">v2 1.42</span></div>
      <div class="tlab">distance small→large</div>
    </div>
    <div class="op">top2→</div>
    <div class="stn"><h5>③ topK=2</h5>
      <div class="cellrow"><span class="vc blue">v1 ✓</span></div>
      <div class="cellrow"><span class="vc blue">v3 ✓</span></div>
      <div class="tlab">return 2 most similar</div>
    </div>
  </div>
</div>

<p>This figure also reveals brute force's cost: step ① computes a distance against <strong>every</strong> item. Four items is fine; four
hundred million is a disaster. That is exactly the pain ANN solves below.</p>

<h2>Why high-dimensional space is counter-intuitive</h2>
<p>Our intuition for "distance" comes from 2D and 3D, but embeddings have hundreds or thousands of dimensions where geometry
<strong>differs sharply from everyday experience</strong>. A famous phenomenon is the <strong>"curse of dimensionality"</strong>: as dimension
grows, <strong>almost all pairwise distances tend to converge</strong>, the gap between "nearest" and "second nearest" flattens, and exact
comparison loses discriminating power; meanwhile, covering the space with grid cells to speed up exact search needs a number of
cells that <strong>explodes exponentially</strong> with dimension. Together these mean: in high dimensions you <strong>cannot</strong> speed up
exact search by simple partitioning, and brute force is too slow — so you settle for <strong>approximation</strong>.</p>

<p>Seen this way, ANN isn't "cutting corners" — it is the <strong>only viable engineering path</strong> in a high-dimensional world. Since the
cost of being exact explodes exponentially or linearly, trading a little recall for controllable, millisecond retrieval becomes
inevitable. This is the shared starting point of every index ahead (IVF, HNSW, PQ, DiskANN) — they merely <strong>approach the same goal
with different tricks</strong>.</p>

<h2>The ANN problem: why we can't "compute exactly, one by one"</h2>
<p>With vectors and a metric in hand, the most naive search is <strong>brute force (FLAT)</strong>: compute the distance from the
query to <strong>every</strong> stored vector, then sort and keep the nearest K (topK). The result is <strong>perfectly exact</strong> and the
logic is trivial. There is exactly one problem: it is <strong>slow</strong>.</p>

<p>Do the math: 100M vectors of 768-d means one query does roughly <strong>100M × 768 ≈ 77 billion</strong> multiply-adds. A single
query is already heavy; multiply by hundreds or thousands of concurrent queries and no single machine survives. That is the
fatal flaw of <strong>exact kNN</strong> at scale — its O(N·D) cost grows <strong>linearly</strong> with data: 10× the data, 10× the latency.</p>

<table class="t">
  <tr><th>Approach</th><th>How it searches</th><th>Speed</th><th>Result</th></tr>
  <tr><td><strong>Exact kNN (FLAT)</strong></td><td class="mono">distance to every item</td><td>slow O(N·D)</td><td>100% exact</td></tr>
  <tr><td><strong>ANN index</strong></td><td class="mono">only a small candidate set</td><td>fast (milliseconds)</td><td>approximate (recall often 95%+)</td></tr>
</table>

<p>The fix is <strong>ANN (Approximate Nearest Neighbor)</strong>: organize the vectors ahead of time into a specialized
<strong>index structure</strong> (buckets, graphs, compression…), and at query time <strong>inspect only a small set of most-likely
candidates</strong> instead of scanning everything. The price is occasionally missing a true nearest neighbor — but in practice
<strong>recall is usually 95%–99%+</strong> while speed jumps <strong>hundreds of times</strong>. For most applications it's an excellent
trade: "spend a little accuracy to buy enormous speed".</p>

<p>This lesson only frames the <strong>problem</strong>: why ANN is needed and what it trades for what. <strong>How</strong> ANN is actually
implemented — bucketed IVF, graph-based HNSW, compressing PQ, disk-resident DiskANN — is the star of the next lesson (Lesson 5).
Pack "metrics" and "why approximate" into your head and you hold the two keys to understanding every vector index ahead.
A side note: FLAT (brute force) is also a <strong>real, selectable "index"</strong> in Milvus — when data is small and you want 100%
exact recall, it's actually the best choice. So "exact vs approximate" isn't either/or; it's a <strong>scenario-driven knob</strong> Milvus
leaves you, which is exactly what the next lesson unfolds.</p>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  Strung together in one line: <strong>embeddings turn data into points in space → a metric gives the ruler for "how alike two
  points are" → exact nearest-neighbor is too slow → use an ANN index for approximate search</strong>. These four steps are the
  bedrock of all of Milvus's retrieval. The metric names (L2 / IP / COSINE / HAMMING / JACCARD) and the "approximate-for-speed"
  trade reappear in every later section.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Embedding</strong>: a model encodes unstructured data into a fixed-length vector; similar meaning ⇒ near vectors.
    The model fixes the dimension; ingest and query must use the same model and dimension.</li>
    <li><strong>Metrics</strong>: L2 (distance, smaller = closer), IP (inner product, larger = closer), COSINE (angle, larger = closer);
    index and search <strong>must use the same one</strong>.</li>
    <li><strong>Normalization</strong>: after scaling to length 1, <strong>IP == COSINE</strong>; many embeddings are normalized by default.</li>
    <li><strong>Specialized metrics</strong>: binary vectors use HAMMING / JACCARD; sparse vectors use IP. Names are case-sensitive
    (see <span class="mono">metric_type.go</span>).</li>
    <li><strong>The ANN problem</strong>: exact kNN is O(N·D) and collapses at scale; ANN trades a little recall for hundreds-fold speed.</li>
  </ul>
</div>
""",
}


LESSON_05 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课我们论证了：大规模下精确最近邻太慢，必须用 <strong>ANN（近似最近邻）</strong>。这一课就来建立对主流 ANN <strong>索引家族</strong>的直觉——
<strong>FLAT、IVF、HNSW、PQ、DiskANN</strong>各用什么招式逼近"最近邻"，它们在<strong>速度、内存、召回</strong>这个三角里各站什么位置，
以及最关键的几个调参旋钮（<span class="inline">nlist/nprobe</span>、<span class="inline">M/ef</span>）到底在调什么。看完你就能给"该选哪个索引"一个有依据的答案。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  在一座大图书馆里找"内容最像这本"的几本书。<strong>FLAT</strong> 是把每一本都翻一遍——最准，但累死人。
  <strong>IVF</strong> 是先按主题分区，只钻进最相关的几个书架找（漏掉别架的风险换来速度）。
  <strong>HNSW</strong> 是顺着"这本像那本"的引用链一路跳过去，几跳就到目标附近。
  <strong>PQ</strong> 是把每本书压成一张"摘要卡"，省地方、翻得快，但摘要丢了细节。
  <strong>DiskANN</strong> 则是把书架搬进仓库（磁盘），只在手边留索引，用得起海量、但每次要去仓库取一趟。
</div>

<h2>先认清三角：速度 ↔ 内存 ↔ 召回</h2>
<p>所有 ANN 索引都在同一个<strong>三角</strong>里做取舍：<strong>查询速度</strong>（多快返回）、<strong>内存占用</strong>（吃多少 RAM）、<strong>召回率</strong>（找回的 topK 有多接近真正的最近邻）。
这三者<strong>不可能同时拉满</strong>——你几乎总是在"用一个换另两个"。理解任何一个索引、调任何一个参数，本质都是在这张三角里<strong>挪动你的位置</strong>。</p>

<div class="cols">
  <div class="col"><h4>想更快 / 更省内存</h4><p>就得接受<strong>召回下降</strong>：少看候选（IVF 调小 nprobe）、压缩向量（PQ）、把数据放磁盘（DiskANN）。
  代价是偶尔漏掉真正的最近邻。</p></div>
  <div class="col"><h4>想更高召回</h4><p>就得付出<strong>更多时间或内存</strong>：多看候选（调大 nprobe / ef）、保留原始精度（不量化）、把索引全放内存（HNSW）。
  极端就是退回 FLAT，100% 召回但最慢。</p></div>
</div>

<p>记住这张三角，下面每个索引家族就都能"对号入座"：它把旋钮拧向了三角的哪个角，又为此放弃了什么。
再强调一点：三角里还藏着一个常被忽略的第四维——<strong>建索引的时间与成本</strong>。FLAT 几乎不用建（直接存），HNSW 建图很慢、很吃 CPU，
IVF 要先跑一遍聚类。线上系统不仅要考虑"查得快不快"，也要考虑"<strong>建得起、重建得起</strong>"——数据持续写入时，索引是要不断增量或重建的。
这条线我们在第五部分（索引构建与调度）会专门展开，这里先在心里留个位置。</p>

<h2>五大索引家族：各自的招式</h2>
<p>Milvus 通过内核库 <strong>Knowhere</strong> 提供一整套索引类型，按"思路"可以归成五大家族。先用一张表建立全局印象，再逐个展开：</p>

<table class="t">
  <tr><th>索引</th><th>核心思路</th><th>关键参数</th><th>适合场景</th></tr>
  <tr><td><strong>FLAT</strong></td><td class="mono">暴力，逐条精确比对</td><td>无</td><td>小数据、要 100% 精确召回</td></tr>
  <tr><td><strong>IVF</strong></td><td class="mono">聚类分桶，只探几个桶</td><td>nlist / nprobe</td><td>中大规模、要可调的速度/召回</td></tr>
  <tr><td><strong>HNSW</strong></td><td class="mono">多层小世界图，沿边跳</td><td>M / efConstruction / ef</td><td>低延迟、高召回（内存换性能）</td></tr>
  <tr><td><strong>PQ / 量化</strong></td><td class="mono">压缩向量，省内存</td><td>m（子段数）/ nbits</td><td>内存紧张、可容忍精度损失</td></tr>
  <tr><td><strong>DiskANN</strong></td><td class="mono">磁盘驻留的图索引</td><td>search_list 等</td><td>超大数据、内存放不下</td></tr>
</table>

<h3>FLAT：不近似的"基准线"</h3>
<p><strong>FLAT</strong> 不做任何近似，就是上一课说的暴力检索：和每条都算距离、排序取 topK。它的意义有二：①小数据量（几万、几十万）时，它<strong>又准又够快</strong>，没必要上复杂索引；
②它是衡量其他索引<strong>召回率的"标准答案"</strong>——其他索引找回的结果有多接近 FLAT，就是它们的召回率。换句话说，FLAT 既是一个能用的索引，也是一把<strong>评估别的索引好坏的尺子</strong>。
很多人忽略了它的第二个身份，但在调优时它极其有用：没有"标准答案"，你根本无法量化"近似索引到底漏了多少"。</p>

<h3>IVF：先分区，再只钻几个区</h3>
<p><strong>IVF（倒排文件，Inverted File）</strong>先用聚类（k-means）把全库向量分成 <span class="inline">nlist</span> 个<strong>桶</strong>（每个桶一个中心点）。
查询时不再扫全库，而是先找出离查询<strong>最近的 <span class="inline">nprobe</span> 个桶</strong>，只在这几个桶里精确比对。两个旋钮含义很直白：
<span class="inline">nlist</span> 是"分多少个桶"（建索引时定），<span class="inline">nprobe</span> 是"查询时探几个桶"——<strong>nprobe 越大，看的候选越多，召回越高但越慢</strong>。
打个比方：nlist 像是把仓库分成多少个货区（一次定好），nprobe 像是这次取货你愿意跑几个货区——跑得多自然更不容易漏，但也更费腿。
这两个旋钮一个管"结构"、一个管"每次查询的力度"，配合起来就能把 IVF 精确地摆在三角里你想要的位置。</p>

<div class="trace">
  <div class="tcap"><b>IVF 搜索</b>：全库分成 6 个桶，查询只探最近的 2 个（nprobe=2），其余 4 桶直接跳过</div>
  <div class="stations">
    <div class="stn"><h5>① 全部桶</h5>
      <div class="cellrow"><span class="vc">桶1</span><span class="vc">桶2</span><span class="vc">桶3</span></div>
      <div class="cellrow"><span class="vc">桶4</span><span class="vc">桶5</span><span class="vc">桶6</span></div>
      <div class="tlab">nlist=6 个中心</div>
    </div>
    <div class="op">选最近2→</div>
    <div class="stn"><h5>② 命中桶</h5>
      <div class="cellrow"><span class="vc hot">桶2</span><span class="vc hot">桶5</span></div>
      <div class="cellrow"><span class="vc dim">其余跳过</span></div>
      <div class="tlab">nprobe=2</div>
    </div>
    <div class="op">桶内精算→</div>
    <div class="stn"><h5>③ topK</h5>
      <div class="cellrow"><span class="vc blue">最近邻 ✓</span></div>
      <div class="tlab">只在 2 桶里比对</div>
    </div>
  </div>
</div>

<p>IVF 还有几个常见变体，区别在"桶里怎么存向量"：<strong>IVF_FLAT</strong> 桶内仍存原始向量（准）；<strong>IVF_SQ8</strong> 把每维压成 1 字节（省内存）；
<strong>IVF_PQ</strong> 用乘积量化进一步压缩（更省，但精度更低）。它们共享同一套 <span class="inline">nlist/nprobe</span> 直觉，只是在三角里把"内存"这个角拧得松紧不同。</p>

<p>IVF 的一个固有弱点值得知道：它依赖<strong>聚类边界</strong>。如果某个真正的最近邻不巧落在了"没被探到的桶"里，就会被漏掉——这正是 nprobe 调大能提升召回的原因（探更多桶、漏得更少）。
所以 IVF 的召回对数据分布比较敏感：数据分得均匀时表现好，聚成几个超大簇时就需要更大的 nprobe 才能保证召回。理解了这一点，你调 nprobe 时就不是盲调，而是<strong>在"探桶数"和"延迟"之间找平衡</strong>。</p>

<h3>HNSW：在一张"可导航小世界图"上跳</h3>
<p><strong>HNSW（Hierarchical Navigable Small World）</strong>不分桶，而是把所有向量连成一张<strong>多层图</strong>：每个向量是一个节点，和它"邻近"的若干节点连边。
查询时从<strong>顶层稀疏图</strong>的一个入口出发，每一步都跳到"离查询更近"的邻居，像高速公路换到省道再换到小路，<strong>几跳就逼近目标</strong>。
三个旋钮：<span class="inline">M</span> 是每个节点的连边数（图多密，影响内存与召回），<span class="inline">efConstruction</span> 是建图时的候选宽度（建得多细），
<span class="inline">ef</span> 是查询时的候选宽度——<strong>ef 越大，搜得越广，召回越高但越慢</strong>。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>顶层入口</h4><p>从最稀疏的一层选一个入口节点，先做"大跨步"逼近。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>逐层下沉</h4><p>每到一层，沿边贪心跳向更近的邻居，再下沉到更密的下一层。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>底层精修</h4><p>在最密的底层用 <span class="mono">ef</span> 宽度的候选集做精细搜索，收敛到最近邻。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>返回 topK</h4><p>整条路径只访问了全库极小一部分节点，却很可能命中真正的最近邻。</p></div></div>
</div>

<p>HNSW 是当下<strong>最受欢迎</strong>的内存索引：召回高、延迟低、对参数不太敏感。代价是<strong>内存占用大</strong>（图结构 + 原始向量都在 RAM），
所以它站在三角里"速度高、召回高、但内存贵"的那个角。一个直觉：<span class="inline">M</span> 越大，图越密，召回越好但内存和建图时间也越高；
<span class="inline">ef</span> 是<strong>查询时才生效</strong>的旋钮，可以在线调——想临时提高召回，把 ef 调大即可，无需重建索引。这种"建图时定结构、查询时调宽度"的设计，
让 HNSW 既能预先建好，又保留了运行时的灵活度。当数据规模大到内存装不下时，就轮到下面两位出场。</p>

<h3>PQ 与 DiskANN：当内存装不下</h3>
<p><strong>PQ（Product Quantization，乘积量化）</strong>是一种<strong>压缩</strong>手段而非独立索引：它把一个高维向量切成若干<strong>子段</strong>，每段用一个小码本里的"代表向量"近似，
于是一条向量从几千字节压成几十字节。好处是内存骤降、距离也能在压缩域快速估算；代价是<strong>精度损失</strong>（用代表向量替代了真实值）。PQ 常和 IVF 组合成 <strong>IVF_PQ</strong>。</p>

<p><strong>DiskANN</strong>则换了个维度省内存：把图索引和向量<strong>主要放在 SSD 磁盘</strong>上，内存里只留必要的导航信息。它专为<strong>单机装不下的超大数据集</strong>设计，
用"磁盘的容量"换"内存的紧张"，代价是每次查询要<strong>读几次磁盘</strong>（靠 SSD 的随机读性能撑住延迟）。一句话：<strong>PQ 压数据、DiskANN 挪到磁盘</strong>，都是为了在内存有限时仍能服务海量向量。
要注意 DiskANN 强依赖 <strong>SSD（固态盘）</strong>而非机械盘——它的延迟预算建立在"随机读够快"的前提上，放在机械盘上会慢到不可用。
这也提醒我们：<strong>索引选型不只是软件问题，也和硬件（内存大小、盘的类型）深度绑定</strong>，这正是把它放进"速度↔内存↔召回"三角去理解的意义。</p>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">最准</span><span class="name">FLAT</span></div><div class="ld">不近似，100% 召回；小数据基准线。内存=全部原始向量，速度最慢。</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">可调</span><span class="name">IVF 家族</span></div><div class="ld">聚类分桶，nprobe 调速度/召回；IVF_SQ8 / IVF_PQ 进一步省内存。</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">低延迟</span><span class="name">HNSW</span></div><div class="ld">图索引，高召回低延迟；内存最贵。当下最流行的内存索引。</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">省内存</span><span class="name">PQ / DiskANN</span></div><div class="ld">压缩（PQ）或下沉磁盘（DiskANN），换取在内存受限时服务超大规模。</div></div>
</div>

<h2>怎么选：从场景倒推索引</h2>
<p>知道了五大家族，真正的问题是"<strong>我的场景该选哪个</strong>"。别背规则，按三个问题倒推即可：<strong>数据量多大？内存够不够？对召回有多苛刻？</strong>
顺着这三问，绝大多数选型就有了答案。</p>

<div class="cols">
  <div class="col"><h4>数据小、要绝对精确</h4><p>几万到几十万条，或调试阶段要"标准答案"：直接 <strong>FLAT</strong>。它够快、且 100% 召回，省去一切调参烦恼。</p></div>
  <div class="col"><h4>内存充足、追求低延迟</h4><p>百万到千万级、且机器内存放得下：<strong>HNSW</strong> 几乎是默认首选。高召回、低延迟、对参数宽容，代价是吃内存。</p></div>
  <div class="col"><h4>规模大、要可控权衡</h4><p>需要在速度和召回间灵活拨动：<strong>IVF</strong> 系列。靠 <span class="inline">nprobe</span> 一个旋钮，就能在线调出你要的平衡点。</p></div>
  <div class="col"><h4>超大、内存装不下</h4><p>上亿乃至更多、单机内存放不下：<strong>DiskANN</strong> 或 <strong>IVF_PQ</strong>。用磁盘容量或压缩，换"仍能服务"的能力。</p></div>
</div>

<p>这里要破除一个常见误解：<strong>没有"最好的索引"，只有"最适合当前三角约束的索引"</strong>。同一份数据，在内存富裕的机器上 HNSW 是最优解，
搬到内存吃紧的环境就可能要换成 IVF_PQ 或 DiskANN。所以"选索引"不是一次性决定，而是<strong>随你的数据规模、硬件预算、业务对召回的容忍度一起演化</strong>的。
Milvus 的价值之一，正是让你<strong>换索引而不换业务代码</strong>——同一套 create / insert / search，底层索引可以重建替换。</p>

<p>还有一个实战经验：很多团队会先用 <strong>FLAT 或 HNSW 跑出一个"召回基准"</strong>，再换到更省资源的索引，<strong>对照召回率</strong>看损失了多少。
因为 FLAT 给的就是"标准答案"，这套"先建基准、再压成本"的方法论，能让你在三角里<strong>有据可依地移动</strong>，而不是凭感觉调参。
说到底，索引选型是一门<strong>工程权衡</strong>而非"找最优解"的艺术：先想清楚业务能接受多少召回损失、机器有多少内存预算、查询延迟的红线在哪，
再回到这张三角上对号入座，答案往往就自然浮现了。</p>

<h2>这些名字从哪来：Knowhere 索引类型</h2>
<p>这些索引并非 Milvus 自研，而是来自它的向量检索<strong>内核库 Knowhere</strong>（一个上游/第三方库）。索引名字都是 Knowhere 的
<span class="mono">IndexEnum</span> 常量字符串，Milvus 在 C++ 侧<strong>引用</strong>它们、并按集合配置挑选对应的索引。
有个细节很容易被忽略：<strong>这些枚举常量散落在不同文件里，并非集中在某一个文件中定义</strong>。下面这段
<span class="mono">index/Utils.cpp</span> 列出的，是该文件里<strong>确实出现</strong>的几个枚举（IVF 与稀疏向量族）——
请特别注意：<strong>本课的两个主角 HNSW 与 DiskANN 并不在这个文件里</strong>，它们各自真正的引用位置列在下方表格，
教程<strong>不杜撰任何符号的所在文件</strong>：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/index/Utils.cpp</span><span class="ln">本文件确有的 knowhere::IndexEnum 引用</span></div>
  <pre><span class="cm">// NM_List() / BIN_List() / unsupported_index_combinations() 中引用</span>
knowhere::IndexEnum::INDEX_FAISS_IVFFLAT          <span class="cm">// IVF_FLAT（稠密浮点）</span>
knowhere::IndexEnum::INDEX_FAISS_BIN_IDMAP        <span class="cm">// 二值向量 FLAT</span>
knowhere::IndexEnum::INDEX_FAISS_BIN_IVFFLAT      <span class="cm">// 二值向量的 IVF</span>
knowhere::IndexEnum::INDEX_SPARSE_INVERTED_INDEX  <span class="cm">// 稀疏向量倒排</span>
knowhere::IndexEnum::INDEX_SPARSE_WAND            <span class="cm">// 稀疏向量 WAND</span></pre>
</div>

<p>那么 <strong>HNSW 与 DiskANN</strong> 到底"住"在哪里？把每个索引族对应到它在 Milvus 源码里被引用的真实位置，就一目了然了
（HNSW 是 Knowhere 库自己的枚举，core 仅引用、并不在上述 milvus 文件里定义）：</p>

<table class="t">
  <tr><th>索引族</th><th>Knowhere 枚举常量</th><th>Milvus 侧引用位置</th></tr>
  <tr><td><strong>IVF_FLAT</strong></td><td class="mono">INDEX_FAISS_IVFFLAT</td><td class="mono">index/Utils.cpp</td></tr>
  <tr><td><strong>稀疏倒排 / WAND</strong></td><td class="mono">INDEX_SPARSE_INVERTED_INDEX / _WAND</td><td class="mono">index/Utils.cpp</td></tr>
  <tr><td><strong>DiskANN</strong></td><td class="mono">INDEX_DISKANN</td><td class="mono">common/Utils.h（DISK_INDEX_LIST）、index/VectorDiskIndex.cpp</td></tr>
  <tr><td><strong>HNSW</strong></td><td class="mono">INDEX_HNSW</td><td>Knowhere 库枚举，被 core 引用（不在上述 milvus 文件中定义）</td></tr>
</table>

<p>所以正确的心智模型是：<strong>索引名字是 Knowhere 的 <span class="mono">IndexEnum</span> 常量，Milvus 按集合配置选用它们</strong>；
而"某个常量写在哪个文件"取决于它被使用的场景（IVF/稀疏出现在 <span class="mono">index/Utils.cpp</span> 的支持列表里，
DiskANN 因为要走"磁盘驻留"专门逻辑而出现在 <span class="mono">VectorDiskIndex.cpp</span> 与 <span class="mono">common/Utils.h</span>，
HNSW 则是 Knowhere 库里的枚举）。读源码时按这张表对号入座，就不会"在错的文件里找错的符号"。</p>

<p>这些索引的<strong>具体构建过程、参数细节、以及调度它们建索引的工程链路</strong>，是<strong>第五部分</strong>的主题，那时我们会真正钻进 C++ 内核去看。
这一课你只需要建立<strong>选型直觉</strong>：知道有这几类、各自在三角里的位置、关键旋钮调什么。这就够你在实践中做出第一个合理的选择了。
最后用一句话把五家串起来：<strong>FLAT 不取巧</strong>（基准与小数据），<strong>IVF 靠分桶</strong>（可调的速度/召回），<strong>HNSW 靠建图</strong>（低延迟、费内存），
<strong>PQ 靠压缩、DiskANN 靠下盘</strong>（内存受限时的两条出路）。它们不是互相替代的"谁更好"，而是覆盖了从"几万条"到"几十亿条"、从"内存富裕"到"内存吃紧"的<strong>不同生态位</strong>。
你越往后学，越会发现 Milvus 的很多设计——分段、增量索引、存算分离——都是为了让"换一个更合适的索引"这件事，在一个持续写入的生产系统里<strong>真正可行</strong>。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：<strong>所有 ANN 索引都在"速度 ↔ 内存 ↔ 召回"三角里取舍</strong>。FLAT 不近似（基准线）；IVF 分桶、用 nprobe 调速度/召回；
  HNSW 建图、低延迟高召回但费内存；PQ 压数据、DiskANN 挪磁盘，都是为内存受限时服务超大规模。它们是 Milvus 通过 Knowhere 提供、<strong>你按集合挑选</strong>的索引类型。
  本课只讲"怎么选"的直觉，"怎么建、怎么调度"留到第五部分深入。</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>三角取舍</strong>：速度、内存、召回不可兼得；选索引、调参数都是在三角里挪位置。</li>
    <li><strong>FLAT</strong>：不近似、100% 召回、最慢；小数据基准线，也是别的索引召回率的"标准答案"。</li>
    <li><strong>IVF</strong>：聚类分桶，<span class="mono">nlist</span> 定桶数、<span class="mono">nprobe</span> 定探几个桶（越大越准越慢）。变体 SQ8/PQ 省内存。</li>
    <li><strong>HNSW</strong>：多层小世界图，<span class="mono">M / efConstruction / ef</span>；高召回低延迟，但内存最贵，最流行。</li>
    <li><strong>PQ / DiskANN</strong>：压缩 / 下沉磁盘，为内存装不下的超大规模服务。</li>
    <li>这些是 <strong>Knowhere</strong> 索引枚举（Milvus 引用）：IVF/稀疏见 <span class="mono">index/Utils.cpp</span>，DiskANN 见 <span class="mono">VectorDiskIndex.cpp</span>，HNSW 为 Knowhere 库枚举；构建细节留到第五部分。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson argued that exact nearest-neighbor is too slow at scale, so we need <strong>ANN (Approximate Nearest Neighbor)</strong>.
This lesson builds intuition for the mainstream ANN <strong>index families</strong> — <strong>FLAT, IVF, HNSW, PQ, DiskANN</strong> — what trick
each uses to approach "the nearest neighbor", where each sits in the <strong>speed ↔ memory ↔ recall</strong> triangle, and what the key
knobs (<span class="inline">nlist/nprobe</span>, <span class="inline">M/ef</span>) actually tune. By the end you can give a grounded answer to
"which index should I pick".
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Finding the few books "most like this one" in a huge library. <strong>FLAT</strong> reads every book — most accurate, exhausting.
  <strong>IVF</strong> partitions by topic and only digs into the few most relevant shelves (speed for the risk of missing other shelves).
  <strong>HNSW</strong> hops along a "this book is like that book" reference chain, reaching the target's vicinity in a few jumps.
  <strong>PQ</strong> compresses each book into a "summary card" — compact and fast, but the summary drops detail.
  <strong>DiskANN</strong> moves the shelves into a warehouse (disk), keeping only an index at hand — affordable at huge scale, but each
  lookup makes a trip to the warehouse.
</div>

<h2>First, the triangle: speed ↔ memory ↔ recall</h2>
<p>Every ANN index trades off within one <strong>triangle</strong>: <strong>query speed</strong> (how fast it returns), <strong>memory footprint</strong>
(how much RAM it eats), and <strong>recall</strong> (how close the returned topK is to the true nearest neighbors). The three
<strong>cannot all be maxed</strong> — you almost always "spend one to buy the other two". Understanding any index, or tuning any
parameter, is essentially <strong>moving your position within this triangle</strong>.</p>

<div class="cols">
  <div class="col"><h4>Want faster / less memory</h4><p>Accept <strong>lower recall</strong>: inspect fewer candidates (smaller IVF nprobe), compress
  vectors (PQ), put data on disk (DiskANN). The price is occasionally missing a true nearest neighbor.</p></div>
  <div class="col"><h4>Want higher recall</h4><p>Pay <strong>more time or memory</strong>: inspect more candidates (larger nprobe / ef), keep full
  precision (no quantization), keep the whole index in RAM (HNSW). The extreme is falling back to FLAT — 100% recall, slowest.</p></div>
</div>

<p>Hold this triangle in mind and every index family below "snaps into place": which corner it turns the knob toward, and what it
gives up for it. One more emphasis: the triangle hides an often-ignored fourth axis — <strong>index build time and cost</strong>. FLAT needs
almost no building (just store); HNSW builds its graph slowly and CPU-heavily; IVF must first run clustering. A production system
weighs not only "how fast it queries" but also "<strong>can we afford to build and rebuild it</strong>" — as data keeps arriving, the index
must be incrementally updated or rebuilt. We'll unfold this in Part 5 (index building and scheduling); for now just reserve a slot
for it.</p>

<h2>Five index families: each one's trick</h2>
<p>Milvus offers a full set of index types via its kernel library <strong>Knowhere</strong>; grouped by "idea" they fall into five families.
First a table for the global picture, then one by one:</p>

<table class="t">
  <tr><th>Index</th><th>Core idea</th><th>Key params</th><th>Good for</th></tr>
  <tr><td><strong>FLAT</strong></td><td class="mono">brute force, exact per item</td><td>none</td><td>small data, 100% exact recall</td></tr>
  <tr><td><strong>IVF</strong></td><td class="mono">cluster into buckets, probe a few</td><td>nlist / nprobe</td><td>mid-large scale, tunable speed/recall</td></tr>
  <tr><td><strong>HNSW</strong></td><td class="mono">multi-layer small-world graph, hop edges</td><td>M / efConstruction / ef</td><td>low latency, high recall (memory for speed)</td></tr>
  <tr><td><strong>PQ / quantization</strong></td><td class="mono">compress vectors, save memory</td><td>m (subquantizers) / nbits</td><td>memory-tight, tolerate precision loss</td></tr>
  <tr><td><strong>DiskANN</strong></td><td class="mono">disk-resident graph index</td><td>search_list, …</td><td>huge data that won't fit in RAM</td></tr>
</table>

<h3>FLAT: the non-approximate "baseline"</h3>
<p><strong>FLAT</strong> does no approximation — it's last lesson's brute force: distance to every item, sort, take topK. Its value is
twofold: (1) at small scale (tens to hundreds of thousands) it is <strong>accurate and fast enough</strong>, no need for a complex index;
(2) it is the <strong>"ground truth" for recall</strong> — how close another index's results come to FLAT's is that index's recall. In other
words, FLAT is both a usable index and a <strong>yardstick for grading other indexes</strong>. Many overlook its second identity, but it's
invaluable when tuning: without "ground truth" you simply can't quantify "how much the approximate index actually missed".</p>

<h3>IVF: partition first, then probe only a few partitions</h3>
<p><strong>IVF (Inverted File)</strong> first uses clustering (k-means) to split all vectors into <span class="inline">nlist</span>
<strong>buckets</strong> (each with a centroid). At query time it doesn't scan everything; it finds the <strong>nearest
<span class="inline">nprobe</span> buckets</strong> to the query and compares exactly only within those. Two knobs, very direct:
<span class="inline">nlist</span> is "how many buckets" (set at build time), <span class="inline">nprobe</span> is "how many buckets to probe at
query" — <strong>larger nprobe means more candidates, higher recall but slower</strong>. An analogy: nlist is how many zones you split a
warehouse into (decided once), nprobe is how many zones you're willing to walk this trip — walking more naturally misses less but
costs more legwork. One knob governs "structure", the other "the effort per query"; together they place IVF precisely where you want
it in the triangle.</p>

<div class="trace">
  <div class="tcap"><b>IVF search</b>: all vectors split into 6 buckets, the query probes only the nearest 2 (nprobe=2), skipping the other 4</div>
  <div class="stations">
    <div class="stn"><h5>① All buckets</h5>
      <div class="cellrow"><span class="vc">b1</span><span class="vc">b2</span><span class="vc">b3</span></div>
      <div class="cellrow"><span class="vc">b4</span><span class="vc">b5</span><span class="vc">b6</span></div>
      <div class="tlab">nlist=6 centroids</div>
    </div>
    <div class="op">nearest 2→</div>
    <div class="stn"><h5>② Hit buckets</h5>
      <div class="cellrow"><span class="vc hot">b2</span><span class="vc hot">b5</span></div>
      <div class="cellrow"><span class="vc dim">rest skipped</span></div>
      <div class="tlab">nprobe=2</div>
    </div>
    <div class="op">exact in-bucket→</div>
    <div class="stn"><h5>③ topK</h5>
      <div class="cellrow"><span class="vc blue">neighbors ✓</span></div>
      <div class="tlab">compare in 2 buckets only</div>
    </div>
  </div>
</div>

<p>IVF has common variants differing in "how vectors are stored in a bucket": <strong>IVF_FLAT</strong> keeps raw vectors (accurate);
<strong>IVF_SQ8</strong> squeezes each dimension into 1 byte (saves memory); <strong>IVF_PQ</strong> compresses further via product quantization
(smaller, but lower precision). They share the same <span class="inline">nlist/nprobe</span> intuition, only turning the "memory" corner of
the triangle tighter or looser.</p>

<p>An inherent IVF weakness worth knowing: it relies on <strong>cluster boundaries</strong>. If a true nearest neighbor happens to fall in
"a bucket that wasn't probed", it's missed — which is exactly why raising nprobe lifts recall (probe more buckets, miss fewer). So
IVF's recall is somewhat sensitive to data distribution: it does well when data spreads evenly, but needs a larger nprobe to
guarantee recall when data clumps into a few huge clusters. Grasp this and tuning nprobe becomes deliberate — <strong>balancing "buckets
probed" against "latency"</strong> — rather than blind.</p>

<h3>HNSW: hopping on a "navigable small-world graph"</h3>
<p><strong>HNSW (Hierarchical Navigable Small World)</strong> doesn't bucket; it connects all vectors into a <strong>multi-layer graph</strong>:
each vector is a node linked to several "nearby" nodes. A query starts from an entry in the <strong>sparse top layer</strong> and, each step,
hops to the neighbor "closer to the query" — like going from highway to arterial to side street, <strong>approaching the target in a few
hops</strong>. Three knobs: <span class="inline">M</span> is edges per node (graph density, affects memory and recall),
<span class="inline">efConstruction</span> is the candidate width at build time (how finely it's built), and <span class="inline">ef</span> is the
candidate width at query time — <strong>larger ef searches wider, higher recall but slower</strong>.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Top-layer entry</h4><p>Pick an entry node on the sparsest layer and take big strides toward the query.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Descend layers</h4><p>At each layer, greedily hop along edges to closer neighbors, then descend to the denser next layer.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Refine at bottom</h4><p>On the densest bottom layer, search finely with a candidate set of width <span class="mono">ef</span>, converging to the nearest neighbors.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Return topK</h4><p>The whole path visits a tiny fraction of all nodes yet very likely hits the true nearest neighbors.</p></div></div>
</div>

<p>HNSW is today's <strong>most popular</strong> in-memory index: high recall, low latency, not too parameter-sensitive. The cost is
<strong>large memory</strong> (graph structure + raw vectors all in RAM), so it stands in the "fast, high-recall, but memory-expensive"
corner of the triangle. An intuition: larger <span class="inline">M</span> makes the graph denser, lifting recall but also memory and build
time; <span class="inline">ef</span> is a knob that <strong>only takes effect at query time</strong> and can be tuned online — to temporarily raise
recall, just increase ef, no rebuild needed. This "fix the structure at build, tune the width at query" design lets HNSW be
prebuilt yet stay flexible at runtime. When data grows beyond what RAM holds, the next two take over.</p>

<h3>PQ and DiskANN: when memory won't fit</h3>
<p><strong>PQ (Product Quantization)</strong> is a <strong>compression</strong> technique rather than a standalone index: it cuts a high-dim
vector into <strong>subvectors</strong>, approximating each by a "representative" from a small codebook, so one vector shrinks from
kilobytes to tens of bytes. The upside is a steep drop in memory and fast distance estimation in the compressed domain; the cost is
<strong>precision loss</strong> (representatives replace true values). PQ is often combined with IVF into <strong>IVF_PQ</strong>.</p>

<p><strong>DiskANN</strong> saves memory along a different axis: it keeps the graph index and vectors <strong>mostly on SSD</strong>, retaining only
essential navigation info in RAM. It's designed for <strong>datasets too large for one machine's memory</strong>, trading "disk capacity"
for "memory pressure", at the cost of a <strong>few disk reads per query</strong> (relying on SSD random-read performance to keep latency
acceptable). In one line: <strong>PQ compresses data, DiskANN moves it to disk</strong> — both to keep serving huge vector sets under limited
memory. Note DiskANN strongly depends on <strong>SSDs</strong>, not spinning disks — its latency budget assumes "random reads are fast enough";
on a HDD it would be unusably slow. This is a reminder that <strong>index choice isn't only a software question, it's deeply tied to
hardware</strong> (RAM size, disk type) — exactly why we frame it inside the "speed ↔ memory ↔ recall" triangle.</p>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">most exact</span><span class="name">FLAT</span></div><div class="ld">no approximation, 100% recall; small-data baseline. Memory = all raw vectors, slowest.</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">tunable</span><span class="name">IVF family</span></div><div class="ld">cluster into buckets, nprobe tunes speed/recall; IVF_SQ8 / IVF_PQ save more memory.</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">low latency</span><span class="name">HNSW</span></div><div class="ld">graph index, high recall and low latency; memory the most expensive. Most popular in-memory index.</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">memory-saving</span><span class="name">PQ / DiskANN</span></div><div class="ld">compress (PQ) or sink to disk (DiskANN), to serve huge scale under limited memory.</div></div>
</div>

<h2>How to choose: reason backward from your scenario</h2>
<p>Knowing the five families, the real question is "<strong>which one for my scenario</strong>". Don't memorize rules; reason backward from
three questions: <strong>how big is the data? is memory enough? how strict is the recall requirement?</strong> Follow those three and most
choices resolve themselves.</p>

<div class="cols">
  <div class="col"><h4>Small data, must be exact</h4><p>Tens to hundreds of thousands, or a debugging phase that needs "ground truth": just <strong>FLAT</strong>.
  Fast enough, 100% recall, zero tuning hassle.</p></div>
  <div class="col"><h4>Ample memory, want low latency</h4><p>Millions to tens of millions that fit in RAM: <strong>HNSW</strong> is almost the default. High recall,
  low latency, forgiving params, at the cost of memory.</p></div>
  <div class="col"><h4>Large scale, want a tunable trade</h4><p>Need to slide flexibly between speed and recall: the <strong>IVF</strong> family. With one knob,
  <span class="inline">nprobe</span>, you can dial the balance point online.</p></div>
  <div class="col"><h4>Huge, won't fit in memory</h4><p>Hundreds of millions or more, beyond a single machine's RAM: <strong>DiskANN</strong> or <strong>IVF_PQ</strong>.
  Trade disk capacity or compression for "still being able to serve".</p></div>
</div>

<p>Dispel a common misconception: <strong>there is no "best index", only "the index best fit to the current triangle constraints"</strong>. The
same data: on a memory-rich machine HNSW is optimal; moved to a memory-tight environment it may need to become IVF_PQ or DiskANN.
So "choosing an index" isn't a one-time decision; it <strong>evolves with your data scale, hardware budget, and the business's recall
tolerance</strong>. One of Milvus's values is letting you <strong>swap indexes without changing business code</strong> — the same create / insert /
search, with the underlying index rebuilt and replaced.</p>

<p>Another practical tip: many teams first run a <strong>"recall baseline" with FLAT or HNSW</strong>, then switch to a leaner index and
<strong>compare recall</strong> to see how much was lost. Because FLAT gives the "ground truth", this "build a baseline first, then squeeze
cost" methodology lets you <strong>move within the triangle with evidence</strong> instead of tuning by feel. Ultimately, index selection is
an art of <strong>engineering trade-offs</strong>, not "finding the optimum": first decide how much recall loss the business tolerates, how
much memory the machines have, and where the latency red line sits, then map back onto this triangle — and the answer usually
surfaces on its own.</p>

<h2>Where these names come from: Knowhere index types</h2>
<p>These indexes aren't built in-house by Milvus; they come from its vector-search <strong>kernel library Knowhere</strong> (an upstream/third-party lib).
The index names are all Knowhere <span class="mono">IndexEnum</span> string constants; the Milvus C++ side <strong>references</strong> them and picks one per
collection config. An easily-missed detail: <strong>these enum constants are scattered across different files, not defined together in a single file</strong>.
The snippet below lists only the enums that <strong>actually appear in</strong> <span class="mono">index/Utils.cpp</span> (the IVF and sparse-vector families) —
note carefully that <strong>this lesson's two flagship indexes, HNSW and DiskANN, are NOT in this file</strong>. Their real reference sites are in the
table that follows; this guide <strong>does not fabricate which file any symbol lives in</strong>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/index/Utils.cpp</span><span class="ln">knowhere::IndexEnum refs actually in this file</span></div>
  <pre><span class="cm">// referenced in NM_List() / BIN_List() / unsupported_index_combinations()</span>
knowhere::IndexEnum::INDEX_FAISS_IVFFLAT          <span class="cm">// IVF_FLAT (dense float)</span>
knowhere::IndexEnum::INDEX_FAISS_BIN_IDMAP        <span class="cm">// binary-vector FLAT</span>
knowhere::IndexEnum::INDEX_FAISS_BIN_IVFFLAT      <span class="cm">// IVF for binary vectors</span>
knowhere::IndexEnum::INDEX_SPARSE_INVERTED_INDEX  <span class="cm">// sparse-vector inverted index</span>
knowhere::IndexEnum::INDEX_SPARSE_WAND            <span class="cm">// sparse-vector WAND</span></pre>
</div>

<p>So where do <strong>HNSW and DiskANN</strong> actually "live"? Mapping each index family to where it is referenced in the Milvus source makes it
clear (HNSW is Knowhere's own enum — core only references it; it is not defined in the milvus files above):</p>

<table class="t">
  <tr><th>Index family</th><th>Knowhere enum constant</th><th>Milvus-side reference site</th></tr>
  <tr><td><strong>IVF_FLAT</strong></td><td class="mono">INDEX_FAISS_IVFFLAT</td><td class="mono">index/Utils.cpp</td></tr>
  <tr><td><strong>Sparse inverted / WAND</strong></td><td class="mono">INDEX_SPARSE_INVERTED_INDEX / _WAND</td><td class="mono">index/Utils.cpp</td></tr>
  <tr><td><strong>DiskANN</strong></td><td class="mono">INDEX_DISKANN</td><td class="mono">common/Utils.h (DISK_INDEX_LIST), index/VectorDiskIndex.cpp</td></tr>
  <tr><td><strong>HNSW</strong></td><td class="mono">INDEX_HNSW</td><td>Knowhere library enum, referenced by core (not defined in the milvus files above)</td></tr>
</table>

<p>So the correct mental model is: <strong>index names are Knowhere <span class="mono">IndexEnum</span> constants that Milvus selects per collection</strong>;
and "which file a constant is written in" depends on where it's used — IVF/sparse appear in the support lists in <span class="mono">index/Utils.cpp</span>,
DiskANN appears in <span class="mono">VectorDiskIndex.cpp</span> and <span class="mono">common/Utils.h</span> because it needs dedicated "disk-resident"
logic, and HNSW is an enum from the Knowhere library. Read the source against this table and you won't go "looking for the wrong symbol in the
wrong file".</p>

<p>The <strong>actual build process, parameter details, and the engineering pipeline that schedules index building</strong> are the subject of
<strong>Part 5</strong>, where we'll really dive into the C++ kernel. For this lesson you only need <strong>selection intuition</strong>: know these
families exist, where each sits in the triangle, and what the key knobs tune. That's enough to make your first reasonable choice in
practice. One sentence to tie the five together: <strong>FLAT plays it straight</strong> (baseline and small data), <strong>IVF buckets</strong>
(tunable speed/recall), <strong>HNSW builds a graph</strong> (low latency, memory-hungry), <strong>PQ compresses and DiskANN sinks to disk</strong>
(two ways out under memory limits). They aren't "which is better" substitutes; they cover <strong>different niches</strong> from "tens of
thousands" to "billions", from "memory-rich" to "memory-tight". The further you go, the more you'll see that much of Milvus's
design — segments, incremental indexing, storage-compute separation — exists to make "swap in a more suitable index" <strong>actually
feasible</strong> in a continuously-writing production system.</p>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  In one line: <strong>every ANN index trades off within the "speed ↔ memory ↔ recall" triangle</strong>. FLAT is exact (the baseline);
  IVF buckets and tunes speed/recall via nprobe; HNSW builds a graph for low latency and high recall but is memory-hungry; PQ
  compresses data, DiskANN sinks to disk — both to serve huge scale under limited memory. They are index types Milvus offers via
  Knowhere and <strong>you pick per collection</strong>.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>The triangle</strong>: speed, memory, recall can't all be maxed; picking an index and tuning params both move within it.</li>
    <li><strong>FLAT</strong>: exact, 100% recall, slowest; small-data baseline and the "ground truth" for others' recall.</li>
    <li><strong>IVF</strong>: cluster into buckets; <span class="mono">nlist</span> sets bucket count, <span class="mono">nprobe</span> sets buckets probed
    (larger = more accurate, slower). Variants SQ8/PQ save memory.</li>
    <li><strong>HNSW</strong>: multi-layer small-world graph, <span class="mono">M / efConstruction / ef</span>; high recall, low latency, but the most
    memory-hungry and most popular.</li>
    <li><strong>PQ / DiskANN</strong>: compress / sink to disk, to serve huge scale that won't fit in memory.</li>
    <li>These are <strong>Knowhere</strong> index enums (referenced by Milvus): IVF/sparse in <span class="mono">index/Utils.cpp</span>, DiskANN in <span class="mono">VectorDiskIndex.cpp</span>, HNSW a Knowhere library enum; build details are saved for Part 5.</li>
  </ul>
</div>
""",
}


LESSON_06 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前几课都在讲"向量怎么比、怎么搜"。这一课换个角度：<strong>数据在 Milvus 里到底是怎么组织的</strong>？
从 <strong>collection（集合）</strong> 到 <strong>schema（模式）</strong> 到 <strong>field（字段）</strong>，再到<strong>主键、自增、动态字段、分区、分区键</strong>，
以及 Milvus 现在支持的全部<strong>数据类型</strong>——尤其是六种向量类型。把这套"数据模型"理清，你才知道 insert 进去的东西被装进了什么样的结构里。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把 <strong>collection</strong> 想成一张<strong>Excel 表</strong>：<strong>schema</strong> 是表头的设计（有哪些列、每列什么类型），<strong>field</strong> 是一列，<strong>一行</strong>就是一条实体（entity）。
  <strong>主键</strong>是那一列"工号"，全表唯一、用来精确定位某一行。<strong>分区</strong>像是把这张大表按"部门"拆成几个 sheet，查某部门时只翻对应 sheet。
  只不过 Milvus 的表里，除了普通的数字、文本列，还能有一种特殊的列——<strong>向量列</strong>，专门用来做相似检索。
</div>

<h2>从 collection 到 field：三层结构</h2>
<p>Milvus 里数据组织的最外层是 <strong>collection</strong>，约等于关系数据库里的<strong>表（table）</strong>。一个 collection 由一份 <strong>schema</strong> 定义，
schema 里列出若干 <strong>field（字段）</strong>，每个 field 规定了名字、数据类型、以及一些类型参数。往 collection 里写入的每一条数据叫一个 <strong>entity（实体）</strong>，
对应关系库里的一<strong>行</strong>。这套对应关系记牢，后面所有概念都挂在它上面。和关系库相比，最大的不同只有一处：Milvus 的"行"里可以有一种特殊的"列"——<strong>向量列</strong>，
它就是做相似检索的那一列。其余的标量列（数字、文本、布尔），作用和关系库一模一样，主要用来做<strong>过滤</strong>（"价格小于 500""地区等于华东"）。
也就是说，一条 entity 通常长这样：<strong>一个主键 + 一个（或多个）向量 + 若干标量字段</strong>。检索时既按向量找相似，又能用标量字段加条件，这正是"向量数据库"区别于"纯算法库"的地方。</p>

<div class="cellgroup">
  <div class="cg-cap"><b>一条 entity 的解剖</b>：主键唯一定位 + 向量字段做相似检索 + 若干标量字段做过滤，三类字段拼成"一行"</div>
  <div class="cells"><span class="lab">字段</span><span class="cell hl">item_id</span><span class="cell q">image_vec</span><span class="cell">price</span><span class="cell">category</span><span class="cell">$meta</span></div>
  <div class="cells"><span class="lab">取值</span><span class="cell hl">10086</span><span class="cell q">[0.90, 0.10, …]</span><span class="cell">499.0</span><span class="cell">鞋</span><span class="cell">{"促销":true}</span></div>
  <div class="cells"><span class="lab">角色</span><span class="cell hl">主键·唯一</span><span class="cell q">向量·相似检索</span><span class="cell">标量·过滤</span><span class="cell">标量·分区键</span><span class="cell">动态字段</span></div>
</div>

<p>这张"解剖图"几乎就是 Milvus 数据模型的全部精华：<strong>一行里同时住着"用来精确定位的主键"、"用来模糊找相似的向量"、"用来精确过滤的标量"</strong>。
三者各司其职，缺一不可——没有主键就无法删改去重，没有向量就退化成普通数据库，没有标量过滤就只能做"纯相似"而无法表达业务条件。
把这三类字段在脑子里分清楚，后面读写入与查询链路时，你就能一眼看出每个字段在每一步里扮演什么角色。</p>

<p>这里有一个和关系库的关键差异要先点明：<strong>schema 在建集合时定下来后，结构基本是稳定的</strong>。维度、主键、度量这些核心元信息一旦确定，
就不能随意更改——这和关系库里随手 <span class="mono">ALTER TABLE</span> 加列删列的灵活度不同。原因在于 Milvus 为了极致的检索性能，会围绕 schema 预先规划好底层的<strong>列式存储和索引布局</strong>，
schema 是这套布局的"地基"。所以设计 schema 时要<strong>多想一步</strong>：哪些字段要参与过滤、哪个字段适合做分区键、向量维度选多少——这些决定会跟着集合走很久。
当然，Milvus 也留了"活口"（下文的动态字段），但核心结构的稳定性，是它换取高性能的必要代价。</p>

<p>顺带一提，<strong>collection 之上还有 database（数据库）</strong>这一层：一个 Milvus 实例里可以有多个 database，
每个 database 下再放多个 collection，用来做更粗粒度的隔离（不同业务线、不同环境）。本课聚焦 collection 及其内部结构，database 这一层知道它存在即可。</p>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">最外层</span><span class="name">database 数据库</span></div><div class="ld">一个实例可有多个 database，做最粗粒度的隔离（业务线 / 环境）。</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">≈ 表</span><span class="name">collection 集合</span></div><div class="ld">数据组织主体，由一份 schema 定义；本课主角。</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">逻辑切分</span><span class="name">partition 分区</span></div><div class="ld">collection 内按规则（或分区键）切成若干逻辑块，查询时只搜相关分区。</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">物理存储</span><span class="name">segment 段</span></div><div class="ld">每个分区内部再被切成多个 segment——真正落盘、建索引的物理单元（下一课详解）。</div></div>
</div>

<p>这条"<strong>database → collection → partition → segment</strong>"的四层包含关系，是理解 Milvus 数据组织的骨架：
越往外越是<strong>逻辑/管理</strong>概念（隔离、命名、切分），越往里越是<strong>物理/存储</strong>概念（真正占内存、落对象存储、建索引）。
注意 partition 与 segment 跨了"逻辑↔物理"这道分界线：分区是你能看见、能指定的逻辑抽屉，而 segment 是 Milvus 内部自动管理、你通常感知不到的物理盒子。
本课把镜头停在 collection 与 partition 这两层，segment 留给下一课专门拆解。</p>

<table class="t">
  <tr><th>Milvus 概念</th><th>≈ 关系数据库</th><th>说明</th></tr>
  <tr><td><strong>collection</strong></td><td>表 table</td><td>数据组织的最外层，有自己的 schema</td></tr>
  <tr><td><strong>schema</strong></td><td>表结构定义</td><td>规定有哪些 field、各自类型与约束</td></tr>
  <tr><td><strong>field</strong></td><td>列 column</td><td>一个字段：名字 + 数据类型 + 参数</td></tr>
  <tr><td><strong>entity</strong></td><td>行 row</td><td>写入的一条数据（一行）</td></tr>
  <tr><td><strong>partition</strong></td><td>分区</td><td>collection 内部的逻辑切分</td></tr>
</table>

<p>每个 field 由一份 <strong>FieldSchema</strong> 描述。在 Milvus 的开发者文档里，FieldSchema 与 CollectionSchema 的结构大致如下（这是<strong>简化的概念结构</strong>，
真实定义在 proto 里、字段更多，比如还有 nullable、default_value、is_partition_key 等）。注意 FieldSchema 里的 <span class="inline">IsPrimaryKey</span> 和 <span class="inline">AutoID</span> 两个布尔位，
它们正是下面要讲的"主键"和"自增"的开关：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">docs/developer_guides/chap02_schema.md</span><span class="ln">CollectionSchema / FieldSchema</span></div>
  <pre><span class="kw">type</span> CollectionSchema <span class="kw">struct</span> {
    Name        <span class="kw">string</span>
    Description <span class="kw">string</span>
    AutoId      <span class="kw">bool</span>
    Fields      []*FieldSchema    <span class="cm">// 一组字段</span>
}

<span class="kw">type</span> FieldSchema <span class="kw">struct</span> {
    Name         <span class="kw">string</span>
    IsPrimaryKey <span class="kw">bool</span>          <span class="cm">// 是不是主键</span>
    DataType     DataType         <span class="cm">// 字段类型（见下表）</span>
    TypeParams   []*KeyValuePair  <span class="cm">// 类型参数：如 dim / max_length</span>
    AutoID       <span class="kw">bool</span>          <span class="cm">// 主键是否自增</span>
}</pre>
</div>

<h2>主键、自增与 type_params</h2>
<p>每个 collection 必须有<strong>一个主键字段（primary key）</strong>，类型只能是 <span class="inline">Int64</span> 或 <span class="inline">VarChar</span>。主键<strong>全集合唯一</strong>，
用来精确定位、删除、去重一条 entity——这一点和关系库的主键完全一致。Milvus 内部很多机制（删除标记、去重、按主键路由分片）都依赖主键，
所以它不是可有可无的装饰，而是整个数据模型的<strong>支点</strong>：没有唯一主键，"删掉那一条""更新那一条"就无从谈起。</p>

<p>主键可以<strong>自增（auto_id）</strong>：开启后，你 insert 时<strong>不用</strong>自己提供主键值，Milvus 会自动分配一个全局唯一的 Int64。
这对"我只关心向量和内容、不在乎 id 是几"的场景很方便；反之，若你的数据本身带业务 id（比如商品编号、文档 UUID），就关掉 auto_id、自己提供主键，
这样你才能用业务侧已知的 id 去精确删改某一条。两种模式各有适用：<strong>auto_id 省心，自带 id 可控</strong>，按你是否需要"用外部 id 反查"来决定。</p>

<p><strong>type_params（类型参数）</strong>是字段类型的补充约束，最常见的两个：向量字段必须给 <span class="inline">dim</span>（维度），
VarChar 字段必须给 <span class="inline">max_length</span>（最大长度）。它们是建集合时就定死、跟着字段走的元信息——比如"这是一个 768 维的 FloatVector 列"。
为什么非给不可？因为 Milvus 要据此<strong>预先规划存储与索引的内存布局</strong>：知道每条向量占多少字节、每条字符串最长多少，才能高效地按列存放、批量计算。
这也解释了为什么<strong>维度一旦定下就不能改</strong>——它早已渗进底层存储的每一个角落。换句话说，<span class="inline">dim</span> 和 <span class="inline">max_length</span> 不是"软约束"，
而是 Milvus 据以分配内存、组织列存、构建索引的<strong>硬性前提</strong>；填错了不会"凑合能用"，而是从一开始就建不出正确的存储结构。</p>

<h2>动态字段：给 schema 留一道活口</h2>
<p>传统关系库的表是<strong>强 schema</strong>：没在表头声明的列，根本写不进去。但真实业务里，常常有一些<strong>临时的、不固定的</strong>附加属性，事先没法都列全——
比如不同来源的商品带着各不相同的标签字段，今天加一个"促销标记"，明天加一个"产地"。如果每加一个属性都要改 schema、重建集合，迭代就太重了。
Milvus 的 <strong>动态字段（dynamic field）</strong>就是为此设计的：开启 <span class="inline">enable_dynamic_field</span> 后，你 insert 时可以<strong>夹带 schema 里没声明的键值对</strong>，
它们会被统一收进一个名为 <span class="inline">$meta</span> 的隐藏 JSON 字段里，事后还能在过滤表达式里使用。这相当于在强 schema 的严谨之外，额外开了一个"什么都能塞"的口袋。</p>

<div class="cols">
  <div class="col"><h4>固定字段（声明过的）</h4><p>schema 里明确定义的 field：类型严格、可建索引、过滤高效。比如 <span class="mono">id / vector / price</span>。</p></div>
  <div class="col"><h4>动态字段（没声明的）</h4><p>开启 <span class="mono">enable_dynamic_field</span> 后随手夹带的键值，落进 <span class="mono">$meta</span> JSON。灵活，但不如固定字段高效。适合放<strong>临时、稀疏</strong>的属性。</p></div>
</div>

<p>一句话权衡：<strong>固定字段图的是"严谨与高效"，动态字段图的是"灵活与免改表"</strong>。把高频、要过滤的属性放进固定字段；把零散、临时的属性丢给动态字段，是常见的实践。
要提醒的是，动态字段虽然方便，但它的值存在 JSON 里，<strong>过滤时要解析 JSON</strong>，效率不如直接对固定字段建立的结构化存储。所以它适合"偶尔用一下"的属性，
而不是"每次查询都要过滤"的核心字段——后者还是老老实实声明成固定 field 更划算。动态字段的真正价值，是让 schema <strong>不必在第一天就想全所有字段</strong>，
给快速迭代的业务留了一道喘息的活口。</p>

<h2>分区与分区键：把大集合切小</h2>
<p>当一个 collection 很大时，把它整体当一坨来查既慢又浪费。<strong>分区（partition）</strong>是 collection 内部的<strong>逻辑切分</strong>：你可以按某种规则把数据分到不同分区，
查询时<strong>只在相关分区里找</strong>，从而剪掉大量无关数据。最典型的用法是按"租户、地区、时间"分区——查某个租户的数据，就只扫它那个分区。
要注意分区是<strong>逻辑</strong>概念，它和后面要讲的 segment（物理存储单元）是两个层次：一个分区内部，数据仍然会被切成很多个 segment 来存储和索引。
你可以把分区理解成"逻辑上的抽屉"，segment 是"抽屉里实际装东西的盒子"——下一课会专门讲 segment。</p>

<p>手动管理分区很繁琐，于是有了<strong>分区键（partition key）</strong>：你把某个<strong>标量字段</strong>（比如 <span class="inline">user_id</span>）指定为分区键，
Milvus 就会<strong>自动</strong>根据这个字段的值把 entity 散列到不同分区里。查询时只要在过滤条件里带上这个字段，Milvus 就能<strong>自动只搜对应分区</strong>，
你完全不用手动建分区、选分区。这在多租户场景里极其好用：一个 collection 装很多用户的数据，靠分区键天然隔离、又互不打扰。</p>

<p>分区和上一课的"索引选型"其实是同一种思想的两次应用：<strong>都在想办法"少看一点数据"</strong>。索引是在向量层面剪枝（只看近的候选），分区是在数据层面剪枝（只看相关的那一块）。
两者叠加，效果是乘法级的：先用分区键把"几亿条全集合"缩到"几百万条某租户的数据"，再让 ANN 索引在这几百万条里快速找最近邻。理解了这一点，你设计 collection 时就会有意识地问自己：
<strong>"我的查询几乎总会带哪个过滤条件？"</strong>——那个字段，往往就是最好的分区键候选。一个小提醒：分区键一旦在建集合时指定就固定下来，
所以这又是一个需要在 schema 设计阶段就想清楚的决定，和前面说的"维度、主键"一样，属于"开局定终身"的那类选择。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>定义 schema</h4><p>声明字段：主键、向量字段（带 dim）、若干标量字段；可选开启动态字段、指定分区键。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>创建 collection</h4><p>schema 落定，collection 诞生；维度、主键、度量等元信息从此固定。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>insert 实体</h4><p>每行带上各字段的值（主键自增则可省）；分区键决定它落进哪个分区。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>建索引 + 检索</h4><p>给向量字段建 ANN 索引，之后即可按相似度 + 标量过滤检索。</p></div></div>
</div>

<h2>数据类型：标量与六种向量</h2>
<p>schema 里每个字段的类型，来自 Milvus 的 <strong>DataType</strong> 枚举。<strong>标量字段</strong>负责承载结构化信息、支撑过滤；<strong>向量字段</strong>承载 embedding、支撑相似检索。
这里有一个<strong>极其重要的纠错点</strong>：早年的开发者文档里只列了 BinaryVector / FloatVector 两种向量，那份清单<strong>早已过时</strong>。
以当前代码为准（<span class="mono">client/entity/field.go</span> 的 FieldType），Milvus 现在支持的类型如下——标量一大类，向量<strong>足足六种</strong>：</p>

<table class="t">
  <tr><th>类别</th><th>数据类型</th><th>说明</th></tr>
  <tr><td rowspan="4"><strong>标量</strong></td><td class="mono">Bool</td><td>布尔</td></tr>
  <tr><td class="mono">Int8 / Int16 / Int32 / Int64</td><td>不同宽度的整数；Int64 常作主键</td></tr>
  <tr><td class="mono">Float / Double</td><td>单精度 / 双精度浮点</td></tr>
  <tr><td class="mono">VarChar / JSON / Array</td><td>变长字符串（需 max_length）/ JSON / 数组</td></tr>
  <tr><td rowspan="6"><strong>向量</strong></td><td class="mono">FloatVector</td><td>最常见：32 位浮点稠密向量</td></tr>
  <tr><td class="mono">BinaryVector</td><td>二值向量（每位 0/1），配 HAMMING/JACCARD</td></tr>
  <tr><td class="mono">Float16Vector</td><td>半精度（16 位）稠密向量，省内存</td></tr>
  <tr><td class="mono">BFloat16Vector</td><td>bfloat16 稠密向量，省内存、动态范围大</td></tr>
  <tr><td class="mono">Int8Vector</td><td>8 位整数稠密向量，进一步省内存</td></tr>
  <tr><td class="mono">SparseFloatVector</td><td>稀疏浮点向量（高维多零），配 IP</td></tr>
</table>

<p>这六种向量类型不是凭空列举，而是当前代码里<strong>逐个定义的常量</strong>。下面这段就是它们的出处——注意 BinaryVector=100 起跳，向量类型和标量类型在编号上是<strong>分段</strong>的：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">client/entity/field.go</span><span class="ln">FieldType 常量（当前 DataType 集）</span></div>
  <pre><span class="kw">const</span> (
    FieldTypeBool   FieldType = <span class="nb">1</span>
    FieldTypeInt64  FieldType = <span class="nb">5</span>    <span class="cm">// 常作主键</span>
    FieldTypeVarChar FieldType = <span class="nb">21</span>
    FieldTypeJSON   FieldType = <span class="nb">23</span>
    FieldTypeArray  FieldType = <span class="nb">22</span>

    FieldTypeBinaryVector    FieldType = <span class="nb">100</span>  <span class="cm">// 向量类型从 100 起</span>
    FieldTypeFloatVector     FieldType = <span class="nb">101</span>
    FieldTypeFloat16Vector   FieldType = <span class="nb">102</span>
    FieldTypeBFloat16Vector  FieldType = <span class="nb">103</span>
    FieldTypeSparseVector    FieldType = <span class="nb">104</span>  <span class="cm">// SparseFloatVector</span>
    FieldTypeInt8Vector      FieldType = <span class="nb">105</span>
)</pre>
</div>

<p>标量类型里有几个值得单独点一句：<span class="inline">VarChar</span> 是变长字符串，必须给 <span class="inline">max_length</span>，常用来存原文、标题、URL；
<span class="inline">JSON</span> 能存一整块嵌套结构，适合放半结构化的元信息；<span class="inline">Array</span> 是同类型元素的数组（如多个标签）。
这些标量字段不只是"附带存着"，它们能直接参与<strong>过滤表达式</strong>——这正是 Milvus 把"向量检索 + 标量过滤"揉在一次查询里的基础。
有了它们，你才能写出"向量最像、且 price &lt; 500、且 tags 包含'新品'"这种混合查询。</p>

<p>这么多向量类型，本质都在三角里做<strong>精度 vs 内存</strong>的取舍：FloatVector 最精确也最占空间；Float16 / BFloat16 / Int8 是用更少的位数<strong>换内存</strong>（每条向量占用减半甚至更多）；
SparseFloatVector 则专为"高维但绝大多数是 0"的场景（如关键词权重）服务，只存非零项，省得多。还有 <span class="inline">BinaryVector</span>，每一维只用 1 个比特表示，配合上一课的 HAMMING/JACCARD 距离，特别适合指纹、去重这类二值特征。<strong>选哪种向量类型，和上一课选哪种索引一样，是一道工程权衡题。</strong></p>

<p>把这一课串成一个具体例子收尾：假设要做一个"商品图片检索"的集合，schema 大概是——主键 <span class="mono">item_id</span>（Int64，开 auto_id）、
向量字段 <span class="mono">image_vec</span>（FloatVector，dim=512）、标量字段 <span class="mono">price</span>（Float）、<span class="mono">category</span>（VarChar，作分区键）、
再开 <span class="inline">enable_dynamic_field</span> 以备临时打标签。建好后，一条"找和这张鞋子图最像、价格小于 500、且属于鞋类"的查询，
就是<strong>向量检索（image_vec）+ 标量过滤（price &lt; 500）+ 分区剪枝（category=鞋）</strong>三件事一次做完。
你看，这一课讲的每个概念——主键、向量字段、标量字段、分区键、动态字段——都在这一条真实查询里各就各位。把数据模型理清，后面看写入与查询链路时，你才知道数据被装进了什么形状的容器里。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：<strong>collection（表）由 schema 定义，schema 列出 field（列），每条数据是 entity（行）</strong>。
  主键唯一定位、可自增；动态字段给 schema 留活口；分区/分区键把大集合切小、加速查询，是多租户场景的利器。
  字段类型来自 DataType——标量一大类、向量<strong>六种</strong>（务必以当前代码为准，别用过时的两种向量清单）。
  把数据模型想成"带向量列的表"，你就抓住了它的精髓。</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>三层结构</strong>：collection ≈ 表，schema = 表结构，field = 列，entity = 行；collection 之上还有 database。</li>
    <li><strong>主键</strong>：每集合一个，Int64 或 VarChar，全局唯一；可开 <span class="mono">auto_id</span> 自增。<span class="mono">type_params</span> 给 dim / max_length。</li>
    <li><strong>动态字段</strong>：开 <span class="mono">enable_dynamic_field</span> 后，未声明的键值进 <span class="mono">$meta</span> JSON，灵活但不如固定字段高效。</li>
    <li><strong>分区 / 分区键</strong>：分区是集合内逻辑切分；把标量字段设为分区键后，Milvus 自动散列与剪枝，多租户神器。</li>
    <li><strong>数据类型</strong>：标量（Bool、Int8~64、Float、Double、VarChar、JSON、Array）+ <strong>六种向量</strong>（Float / Binary / Float16 / BFloat16 / Int8 / SparseFloat）。见 <span class="mono">client/entity/field.go</span>。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The last few lessons were about "how vectors are compared and searched". This one shifts angle: <strong>how is data actually
organized inside Milvus</strong>? From <strong>collection</strong> to <strong>schema</strong> to <strong>field</strong>, then <strong>primary key, auto_id, dynamic
field, partition, partition key</strong>, and all the <strong>data types</strong> Milvus supports today — especially the six vector types. Clear
up this "data model" and you'll know what kind of structure your inserted data lands in.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of a <strong>collection</strong> as an <strong>Excel sheet</strong>: the <strong>schema</strong> is the header design (which columns, what type each),
  a <strong>field</strong> is one column, and a <strong>row</strong> is one entity. The <strong>primary key</strong> is the "employee ID" column — unique across
  the whole sheet, used to pinpoint a row. A <strong>partition</strong> is like splitting the big sheet into a few sheets by "department",
  so querying one department only flips to the matching sheet. Only, a Milvus table can also have a special column — a
  <strong>vector column</strong> — dedicated to similarity search.
</div>

<h2>From collection to field: a three-layer structure</h2>
<p>The outermost layer of data organization in Milvus is the <strong>collection</strong>, roughly a <strong>table</strong> in a relational database. A
collection is defined by a <strong>schema</strong>, which lists several <strong>fields</strong>, each specifying a name, data type, and some type
parameters. Each item written into a collection is an <strong>entity</strong>, corresponding to a <strong>row</strong>. Memorize this mapping; every
concept later hangs off it. Versus a relational DB there is one big difference: a Milvus "row" can hold a special "column" — the
<strong>vector column</strong> — the one used for similarity search. The other scalar columns (numbers, text, boolean) behave exactly like a
relational DB's, mainly used for <strong>filtering</strong> ("price below 500", "region equals East"). So an entity typically looks like:
<strong>one primary key + one (or more) vectors + several scalar fields</strong>. A search finds similar by vector while also constraining by
scalar fields — exactly what separates a "vector database" from a "pure algorithm library".</p>

<div class="cellgroup">
  <div class="cg-cap"><b>Anatomy of one entity</b>: a primary key to pinpoint + a vector field for similarity + several scalar fields for filtering — three kinds of field make up "a row"</div>
  <div class="cells"><span class="lab">field</span><span class="cell hl">item_id</span><span class="cell q">image_vec</span><span class="cell">price</span><span class="cell">category</span><span class="cell">$meta</span></div>
  <div class="cells"><span class="lab">value</span><span class="cell hl">10086</span><span class="cell q">[0.90, 0.10, …]</span><span class="cell">499.0</span><span class="cell">shoes</span><span class="cell">{"sale":true}</span></div>
  <div class="cells"><span class="lab">role</span><span class="cell hl">PK · unique</span><span class="cell q">vector · search</span><span class="cell">scalar · filter</span><span class="cell">scalar · part. key</span><span class="cell">dynamic field</span></div>
</div>

<p>This "anatomy" is basically the whole essence of the Milvus data model: <strong>a single row simultaneously houses "a primary key to
pinpoint exactly", "a vector to fuzzily find similar", and "scalars to filter precisely"</strong>. Each plays its role and none is optional —
without a primary key you can't delete/update/dedup, without a vector it degrades to an ordinary database, without scalar filtering you
can only do "pure similarity" with no way to express business conditions. Keep these three kinds of field straight in your head, and when
you later read the write and query paths you'll instantly see what role each field plays at each step.</p>

<p>One key difference from a relational DB to flag first: <strong>once the schema is set at collection creation, the structure is largely
stable</strong>. Core metadata like dimension, primary key, and metric can't be changed at will — unlike the freewheeling
<span class="mono">ALTER TABLE</span> add/drop column of a relational DB. The reason is that for top retrieval performance, Milvus plans the
underlying <strong>columnar storage and index layout</strong> around the schema; the schema is the "foundation" of that layout. So designing a
schema means <strong>thinking one step ahead</strong>: which fields will filter, which field suits the partition key, what vector dimension —
these decisions live with the collection for a long time. Milvus does leave a "release valve" (the dynamic field below), but the
stability of the core structure is the necessary price it pays for high performance.</p>

<p>By the way, <strong>above the collection there is also a database layer</strong>: a Milvus instance can hold several databases, each holding
several collections, for coarser-grained isolation (different business lines, different environments). This lesson focuses on the
collection and its internals; just know the database layer exists.</p>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">outermost</span><span class="name">database</span></div><div class="ld">an instance can hold several databases — the coarsest isolation (business line / environment).</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">≈ table</span><span class="name">collection</span></div><div class="ld">the main data organization, defined by one schema; this lesson's focus.</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">logical split</span><span class="name">partition</span></div><div class="ld">a collection is split into logical blocks by rule (or partition key); a query only searches relevant partitions.</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">physical storage</span><span class="name">segment</span></div><div class="ld">each partition is further split into many segments — the physical units that actually persist and get indexed (next lesson).</div></div>
</div>

<p>This four-level containment "<strong>database → collection → partition → segment</strong>" is the skeleton for understanding Milvus data
organization: the further out, the more it is a <strong>logical/management</strong> concept (isolation, naming, splitting); the further in, the
more it is a <strong>physical/storage</strong> concept (actually consuming memory, landing in object storage, getting indexed). Note that partition
and segment straddle the "logical ↔ physical" line: a partition is a logical drawer you can see and specify, while a segment is a physical
box Milvus manages internally that you usually never notice. This lesson keeps the lens on the collection and partition levels; segments
are dissected next lesson.</p>

<table class="t">
  <tr><th>Milvus concept</th><th>≈ relational DB</th><th>Note</th></tr>
  <tr><td><strong>collection</strong></td><td>table</td><td>outermost layer of data, has its own schema</td></tr>
  <tr><td><strong>schema</strong></td><td>table definition</td><td>declares the fields, their types and constraints</td></tr>
  <tr><td><strong>field</strong></td><td>column</td><td>one field: name + data type + params</td></tr>
  <tr><td><strong>entity</strong></td><td>row</td><td>one written item (a row)</td></tr>
  <tr><td><strong>partition</strong></td><td>partition</td><td>a logical split inside a collection</td></tr>
</table>

<p>Each field is described by a <strong>FieldSchema</strong>. In Milvus's developer docs, FieldSchema and CollectionSchema look roughly like
this (a <strong>simplified conceptual structure</strong>; the real definition lives in proto and has more fields, e.g. nullable, default_value,
is_partition_key). Note the <span class="inline">IsPrimaryKey</span> and <span class="inline">AutoID</span> booleans in FieldSchema — they are exactly
the "primary key" and "auto increment" switches discussed next:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">docs/developer_guides/chap02_schema.md</span><span class="ln">CollectionSchema / FieldSchema</span></div>
  <pre><span class="kw">type</span> CollectionSchema <span class="kw">struct</span> {
    Name        <span class="kw">string</span>
    Description <span class="kw">string</span>
    AutoId      <span class="kw">bool</span>
    Fields      []*FieldSchema    <span class="cm">// a set of fields</span>
}

<span class="kw">type</span> FieldSchema <span class="kw">struct</span> {
    Name         <span class="kw">string</span>
    IsPrimaryKey <span class="kw">bool</span>          <span class="cm">// is it the primary key</span>
    DataType     DataType         <span class="cm">// field type (see table below)</span>
    TypeParams   []*KeyValuePair  <span class="cm">// type params: e.g. dim / max_length</span>
    AutoID       <span class="kw">bool</span>          <span class="cm">// is the primary key auto-incrementing</span>
}</pre>
</div>

<h2>Primary key, auto_id, and type_params</h2>
<p>Every collection must have <strong>one primary key field</strong>, of type only <span class="inline">Int64</span> or <span class="inline">VarChar</span>. The
primary key is <strong>unique across the collection</strong>, used to pinpoint, delete, and deduplicate an entity — exactly like a relational
PK. Many Milvus internals (delete markers, dedup, sharding by PK) depend on the primary key, so it isn't optional decoration but
the <strong>pivot</strong> of the whole data model: without a unique PK, "delete that one" / "update that one" make no sense.</p>

<p>The primary key can <strong>auto-increment (auto_id)</strong>: with it on, you <strong>don't</strong> supply a PK value at insert; Milvus assigns a
globally unique Int64. Handy for "I only care about the vector and content, not what the id is"; conversely, if your data carries a
business id (a product code, a document UUID), turn auto_id off and supply your own PK, so you can delete/update a specific row by
the externally-known id. Each mode has its place: <strong>auto_id is carefree, your-own-id is controllable</strong> — decide by whether you
need to "look up by external id".</p>

<p><strong>type_params</strong> are supplementary constraints on a field's type; the two most common: a vector field must give
<span class="inline">dim</span> (dimension), a VarChar field must give <span class="inline">max_length</span>. They are metadata fixed at collection
creation and bound to the field — e.g. "this is a 768-d FloatVector column". Why mandatory? Because Milvus uses them to
<strong>pre-plan the memory layout of storage and index</strong>: knowing how many bytes each vector takes and how long each string can be
lets it store columnarly and compute in batches efficiently. This also explains why <strong>dimension can't change once set</strong> — it has
seeped into every corner of the underlying storage. In other words, <span class="inline">dim</span> and <span class="inline">max_length</span> aren't
"soft constraints" but <strong>hard prerequisites</strong> Milvus uses to allocate memory, organize columnar storage, and build indexes; get
them wrong and it won't "make do", it simply can't build the correct storage structure from the start.</p>

<h2>Dynamic field: a release valve for the schema</h2>
<p>A traditional relational table is <strong>strict-schema</strong>: columns not declared in the header simply can't be written. But real
workloads often have <strong>temporary, irregular</strong> extra attributes that can't all be listed in advance — items from different sources
carry different tag fields; today you add a "promo flag", tomorrow a "place of origin". If every new attribute required altering the
schema and rebuilding the collection, iteration would be too heavy. Milvus's <strong>dynamic field</strong> is built for this: with
<span class="inline">enable_dynamic_field</span> on, at insert you can <strong>carry key-value pairs not declared in the schema</strong>, which get
collected into a hidden JSON field named <span class="inline">$meta</span> and can still be used in filter expressions later. It's like adding
a "stuff-anything" pocket alongside the rigor of a strict schema.</p>

<div class="cols">
  <div class="col"><h4>Fixed fields (declared)</h4><p>Fields explicitly defined in the schema: strict type, indexable, efficient filtering. E.g.
  <span class="mono">id / vector / price</span>.</p></div>
  <div class="col"><h4>Dynamic fields (undeclared)</h4><p>Key-values carried ad hoc once <span class="mono">enable_dynamic_field</span> is on, landing in the
  <span class="mono">$meta</span> JSON. Flexible, but less efficient than fixed fields. Good for <strong>temporary, sparse</strong> attributes.</p></div>
</div>

<p>The trade-off in one line: <strong>fixed fields buy "rigor and efficiency", dynamic fields buy "flexibility and no schema change"</strong>.
Common practice: put high-frequency, filter-worthy attributes in fixed fields; toss scattered, temporary ones into dynamic fields.
A caveat: convenient as it is, a dynamic field's value lives in JSON, so <strong>filtering parses JSON</strong> — less efficient than the
structured storage of a fixed field. So it suits "occasionally used" attributes, not "filtered on every query" core fields — those
are still better declared as fixed fields. The real value of dynamic fields is letting the schema <strong>not have to foresee every field
on day one</strong>, leaving a breathing valve for fast-iterating workloads.</p>

<h2>Partition and partition key: slicing a big collection small</h2>
<p>When a collection is huge, querying it as one lump is slow and wasteful. A <strong>partition</strong> is a <strong>logical split</strong> inside a
collection: you can route data into different partitions by some rule, and a query <strong>searches only the relevant partitions</strong>,
pruning lots of irrelevant data. The classic use is partitioning by "tenant, region, time" — query one tenant and only scan its
partition. Note a partition is a <strong>logical</strong> concept, on a different layer from the segment (physical storage unit) covered next:
within one partition, data is still cut into many segments for storage and indexing. Think of a partition as a "logical drawer" and
a segment as "the boxes that actually hold things inside the drawer" — the next lesson is all about segments.</p>

<p>Managing partitions manually is tedious, so there's the <strong>partition key</strong>: designate a <strong>scalar field</strong> (e.g.
<span class="inline">user_id</span>) as the partition key and Milvus <strong>automatically</strong> hashes entities into partitions by that field's value.
At query time, just include that field in the filter and Milvus <strong>automatically searches only the matching partition</strong> — no manual
partition creation or selection. This is superb for multi-tenancy: one collection holds many users' data, naturally isolated by the
partition key without interfering with each other.</p>

<p>Partitioning and last lesson's "index selection" are really the same idea applied twice: <strong>both find ways to "look at less
data"</strong>. The index prunes at the vector level (only nearby candidates), the partition prunes at the data level (only the relevant
chunk). Stacked, the effect is multiplicative: the partition key shrinks "hundreds of millions in the whole collection" down to "a
few million for one tenant", then the ANN index quickly finds nearest neighbors among those few million. Grasp this and when
designing a collection you'll consciously ask: <strong>"which filter will almost every query carry?"</strong> — that field is often the best
partition-key candidate. A small reminder: the partition key, once specified at collection creation, is fixed — so this is another
decision to settle at schema-design time, in the same "set once for life" category as dimension and primary key.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Define the schema</h4><p>Declare fields: primary key, vector field (with dim), some scalar fields; optionally enable dynamic field and set a partition key.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Create the collection</h4><p>The schema is fixed and the collection is born; dimension, primary key, metric and other metadata become fixed.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Insert entities</h4><p>Each row carries field values (PK can be omitted if auto); the partition key decides which partition it lands in.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Build index + search</h4><p>Build an ANN index on the vector field, then retrieve by similarity + scalar filtering.</p></div></div>
</div>

<h2>Data types: scalar and the six vectors</h2>
<p>Each field's type in the schema comes from Milvus's <strong>DataType</strong> enum. <strong>Scalar fields</strong> carry structured info and power
filtering; <strong>vector fields</strong> carry embeddings and power similarity search. Here is an <strong>extremely important correction</strong>: older
developer docs listed only BinaryVector / FloatVector, and that list is <strong>long outdated</strong>. Going by current code
(<span class="mono">client/entity/field.go</span>'s FieldType), Milvus today supports the following — one big scalar group, and a full
<strong>six</strong> vector types:</p>

<table class="t">
  <tr><th>Category</th><th>Data type</th><th>Note</th></tr>
  <tr><td rowspan="4"><strong>Scalar</strong></td><td class="mono">Bool</td><td>boolean</td></tr>
  <tr><td class="mono">Int8 / Int16 / Int32 / Int64</td><td>integers of different widths; Int64 often the PK</td></tr>
  <tr><td class="mono">Float / Double</td><td>single / double precision float</td></tr>
  <tr><td class="mono">VarChar / JSON / Array</td><td>variable string (needs max_length) / JSON / array</td></tr>
  <tr><td rowspan="6"><strong>Vector</strong></td><td class="mono">FloatVector</td><td>most common: 32-bit float dense vector</td></tr>
  <tr><td class="mono">BinaryVector</td><td>binary (each bit 0/1), with HAMMING/JACCARD</td></tr>
  <tr><td class="mono">Float16Vector</td><td>half-precision (16-bit) dense vector, memory-saving</td></tr>
  <tr><td class="mono">BFloat16Vector</td><td>bfloat16 dense vector, memory-saving, large dynamic range</td></tr>
  <tr><td class="mono">Int8Vector</td><td>8-bit integer dense vector, further memory-saving</td></tr>
  <tr><td class="mono">SparseFloatVector</td><td>sparse float vector (high-dim, mostly zero), with IP</td></tr>
</table>

<p>A few scalar types deserve a sentence: <span class="inline">VarChar</span> is a variable string requiring <span class="inline">max_length</span>, often
storing raw text, titles, URLs; <span class="inline">JSON</span> stores a whole nested structure, good for semi-structured metadata;
<span class="inline">Array</span> is an array of same-type elements (e.g. multiple tags). These scalar fields aren't just "stored along"; they
directly join <strong>filter expressions</strong> — exactly the basis for Milvus fusing "vector search + scalar filtering" into one query. With
them you can write hybrid queries like "most similar by vector, and price &lt; 500, and tags contain 'new'".</p>

<p>These six vector types aren't listed out of thin air; they are <strong>constants defined one by one</strong> in current code. Below is their
source — note BinaryVector starts at 100, so vector types and scalar types are <strong>partitioned</strong> by number:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">client/entity/field.go</span><span class="ln">FieldType constants (current DataType set)</span></div>
  <pre><span class="kw">const</span> (
    FieldTypeBool   FieldType = <span class="nb">1</span>
    FieldTypeInt64  FieldType = <span class="nb">5</span>    <span class="cm">// often the PK</span>
    FieldTypeVarChar FieldType = <span class="nb">21</span>
    FieldTypeJSON   FieldType = <span class="nb">23</span>
    FieldTypeArray  FieldType = <span class="nb">22</span>

    FieldTypeBinaryVector    FieldType = <span class="nb">100</span>  <span class="cm">// vector types start at 100</span>
    FieldTypeFloatVector     FieldType = <span class="nb">101</span>
    FieldTypeFloat16Vector   FieldType = <span class="nb">102</span>
    FieldTypeBFloat16Vector  FieldType = <span class="nb">103</span>
    FieldTypeSparseVector    FieldType = <span class="nb">104</span>  <span class="cm">// SparseFloatVector</span>
    FieldTypeInt8Vector      FieldType = <span class="nb">105</span>
)</pre>
</div>

<p>All these vector types essentially make a <strong>precision-vs-memory</strong> trade in the triangle: FloatVector is most precise and most
space-hungry; Float16 / BFloat16 / Int8 use fewer bits to <strong>trade for memory</strong> (halving per-vector footprint or more);
SparseFloatVector serves "high-dim but mostly zero" cases (keyword weights), storing only non-zeros and saving a lot.
There's also <span class="inline">BinaryVector</span>, using just 1 bit per dimension, which pairs with last lesson's HAMMING/JACCARD distances and suits binary features like fingerprints and dedup.
<strong>Choosing a vector type, like choosing an index last lesson, is an engineering trade-off.</strong></p>

<p>To close, a concrete example tying it together: suppose a "product image search" collection; the schema is roughly — primary key
<span class="mono">item_id</span> (Int64, auto_id on), vector field <span class="mono">image_vec</span> (FloatVector, dim=512), scalar fields
<span class="mono">price</span> (Float) and <span class="mono">category</span> (VarChar, as partition key), plus <span class="inline">enable_dynamic_field</span> for
ad-hoc tags. Once built, a query "find most like this shoe image, price under 500, and in the shoes category" is
<strong>vector search (image_vec) + scalar filter (price &lt; 500) + partition pruning (category=shoes)</strong> done in one shot. See — every
concept here (primary key, vector field, scalar field, partition key, dynamic field) takes its place in one real query. Clear up
the data model and, when reading the write and query paths later, you'll know the shape of the container your data lives in.</p>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  In one line: <strong>a collection (table) is defined by a schema, the schema lists fields (columns), each item is an entity (row)</strong>.
  The primary key pinpoints uniquely and can auto-increment; the dynamic field is a release valve for the schema; partitions /
  partition keys slice a big collection small and speed up queries — a boon for multi-tenancy. Field types come from DataType — one
  big scalar group, and <strong>six</strong> vectors (always go by current code; don't use the outdated two-vector list). Picture the data model
  as "a table with a vector column" and you've caught its essence.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Three-layer structure</strong>: collection ≈ table, schema = table definition, field = column, entity = row; above collection there's also a database.</li>
    <li><strong>Primary key</strong>: one per collection, Int64 or VarChar, globally unique; can enable <span class="mono">auto_id</span>. <span class="mono">type_params</span> give dim / max_length.</li>
    <li><strong>Dynamic field</strong>: with <span class="mono">enable_dynamic_field</span> on, undeclared key-values go into the <span class="mono">$meta</span> JSON — flexible but less efficient than fixed fields.</li>
    <li><strong>Partition / partition key</strong>: a partition is a logical split inside a collection; set a scalar field as the partition key and Milvus auto-hashes and prunes — a multi-tenancy gem.</li>
    <li><strong>Data types</strong>: scalar (Bool, Int8~64, Float, Double, VarChar, JSON, Array) + <strong>six vectors</strong> (Float / Binary / Float16 / BFloat16 / Int8 / SparseFloat). See <span class="mono">client/entity/field.go</span>.</li>
  </ul>
</div>
""",
}


LESSON_07 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课我们说，一个分区里的数据"仍会被切成很多 segment 来存"。这一课就把 <strong>segment（段）</strong>——Milvus 里<strong>数据与索引的基本单位</strong>——讲透：
它的<strong>生命周期</strong>（Growing → Sealed → Flushing → Flushed →（Dropped）），向量数据怎么从一条<strong>vchannel</strong> 流进来、又怎么映射到底层的 <strong>pchannel</strong>，
以及 Milvus 最核心的一条设计哲学——<strong>"日志即数据（log as data）"</strong>。理解了 segment，你才真正看懂"边写边查"是怎么实现的。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把写入想成一家工厂的流水线。新来的货先堆在<strong>正在装的集装箱</strong>里（Growing 段，还能继续往里塞）；
  装满了就<strong>封箱</strong>（Sealed，不再接收新货）；封好的箱子被<strong>送进仓库归档</strong>（Flushing → Flushed，落到对象存储）；
  哪天这批货过期了，整箱<strong>报废处理</strong>（Dropped）。而真正的"账本"不是集装箱本身，而是流水线入口那条<strong>不断记录"谁、什么时候、来了什么货"的传送带日志</strong>——
  只要日志在，任何时候都能照着它把货重新堆一遍。这条日志，就是 Milvus 的灵魂。
</div>

<h2>segment：数据与索引的基本单位</h2>
<p>在正式拆解之前先建立一个直觉：你在第一部分见过的"边写边查""分布式扩展""崩溃不丢数据"这些能力，<strong>追根溯源全都落在 segment 和它背后的日志上</strong>。
所以这一课虽然在"前置基础"部分，却是后面所有写入链路、查询链路、压缩与索引章节的<strong>共同地基</strong>——值得多花点时间彻底吃透。</p>
<p>一个 collection 可能有几亿条数据，Milvus 不会把它当成"一个巨大的整体"来管理，而是切成许多<strong>segment（段）</strong>。
每个 segment 是一<strong>批 entity</strong> 的集合（通常几十万到上百万条），它是 Milvus 里<strong>存储、刷盘、建索引、加载、检索</strong>的基本单位——
几乎所有数据操作都以 segment 为颗粒度。为什么要切段？因为只有把"大数据"拆成"许多小块"，才能<strong>并行处理、独立索引、按需加载、增量更新</strong>——
这正是分布式系统横向扩展的前提。打个比方，与其管理一座没有隔间的巨型仓库，不如把货物装进许多<strong>标准集装箱</strong>：每个箱子可以单独搬运、单独上架、单独盘点，
整体的弹性和并行度都来自这种"切块"。Milvus 的 segment 就是这样的标准集装箱。每个段还带着自己的元信息（段 ID、所属 collection/partition、行数、状态等），由 DataCoord 统一登记和调度。</p>


<p>segment 分两大类，对应"正在写"和"已写完"两种状态：<strong>增长段（Growing）</strong>在内存里，正通过流式日志持续接收新写入；
<strong>封存段（Sealed）</strong>已经写满、变成<strong>不可变（immutable）</strong>，会被刷到对象存储、并在其上构建索引。
这个"可变的增长段 + 不可变的封存段"的二分，是后面理解"边写边查"和"索引构建"的关键。</p>

<p>为什么要强调"不可变"？因为<strong>不可变是分布式系统的好朋友</strong>：一个段一旦封存就永不更改，那么它就可以被<strong>安全地缓存、复制、并行加载到多个 QueryNode</strong>，
不用担心一边读一边被改的并发问题。删除和更新怎么办？Milvus 不在原段上改，而是<strong>另写一份"删除标记（delete log）"</strong>，检索时把被删的主键过滤掉；
真正的物理清理留给后台的<strong>压缩（compaction）</strong>。所以"不可变段 + 删除日志 + 压缩"这套组合，是 Milvus 在保证高并发读取的同时，又能支持增删改的巧妙设计。</p>


<div class="cols">
  <div class="col"><h4>增长段 Growing</h4><p>在内存里，<strong>可变</strong>，正在通过 vchannel 持续吸收新数据。它<strong>立即可查</strong>（保证新数据的新鲜度），但还没建正式索引，靠暴力或临时结构检索。</p></div>
  <div class="col"><h4>封存段 Sealed</h4><p>已写满、<strong>不可变</strong>，刷盘成 binlog 存进对象存储，并在其上构建 ANN 索引。检索高效，是大部分历史数据的归宿。</p></div>
</div>

<h2>生命周期：从 Growing 到 Dropped</h2>
<p>一个 segment 会沿着一条<strong>固定的状态链</strong>演化。这些状态名不是教程瞎编的，而是 Milvus 代码里 <span class="inline">SegmentState</span> 枚举里<strong>逐字定义</strong>的：
<strong>Growing（增长）→ Sealed（封存）→ Flushing（刷盘中）→ Flushed（已刷盘）→（Dropped 丢弃）</strong>。每一步都有明确的触发条件：</p>

<div class="timeline">
  <div class="lane"><span class="lane-label">Growing</span><span class="tslot">内存中 · 可变</span><span class="tslot span">持续吸收 vchannel 来的新数据，立即可查</span></div>
  <div class="lane"><span class="lane-label">Sealed</span><span class="tslot now">写满 / 超时触发封存</span><span class="tslot">不再接收新写入，变不可变</span></div>
  <div class="lane"><span class="lane-label">Flushing</span><span class="tslot">正在落盘</span><span class="tslot">把内存数据写成 binlog 文件</span></div>
  <div class="lane"><span class="lane-label">Flushed</span><span class="tslot now">已存入对象存储</span><span class="tslot">可在其上建索引</span></div>
  <div class="lane"><span class="lane-label">Dropped</span><span class="tslot">被压缩/删除替代</span><span class="tslot">逻辑丢弃，等待 GC 回收</span></div>
</div>

<p>解释几个关键转换：<strong>Growing → Sealed（封存）</strong>由"段写满了（达到大小上限）"或"攒够时间了（超时）"触发——一旦封存，这个段就<strong>不再接收任何新写入</strong>，变成只读快照。
<strong>Sealed → Flushing → Flushed（刷盘）</strong>是把内存里的数据<strong>持久化</strong>成 <span class="inline">binlog</span> 文件、写进对象存储的过程；Flushed 之后数据就<strong>不怕进程崩溃</strong>了，
而且可以在它上面安心建 ANN 索引。<strong>Dropped（丢弃）</strong>通常发生在<strong>压缩（compaction）</strong>之后：多个小段被合并成一个大段，或带删除标记的数据被清理，旧段就被标记 Dropped、等待垃圾回收。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>触发封存</h4><p>段写满（达到大小上限）<strong>或</strong>超时——DataCoord 下令把 Growing 段转 Sealed，从此只读。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>刷盘成 binlog</h4><p>把内存里按列组织的数据<strong>序列化成 binlog 文件</strong>，逐字段写入对象存储；写完即 Flushed，数据持久化、不怕崩溃。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>异步建索引</h4><p>IndexNode 读取 binlog，在其上<strong>构建 ANN 索引</strong>（IVF/HNSW…），索引文件也存进对象存储。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>加载检索</h4><p>QueryNode <strong>加载</strong>封存段及其索引到内存，对外提供高效 ANN 检索；同时 Growing 段补上最新数据。</p></div></div>
</div>

<p>注意第 3、4 步是<strong>异步</strong>发生的：刷盘和建索引在后台进行，不阻塞写入，也不阻塞对 Growing 段的查询。这种"<strong>写入、刷盘、建索引、加载</strong>各自独立、互不阻塞"的流水线，
正是 Milvus 把吞吐做高、把延迟做低的关键。每一环都能独立扩展——写得快了就加 DataNode，建索引慢了就加 IndexNode，查得多了就加 QueryNode。</p>

<p>另外还有几个相关状态值得一提：枚举里还有 <span class="inline">Importing</span>（批量导入时的临时段）和 <span class="inline">NotExist</span> 等。
但对理解主流程，记住 <strong>Growing → Sealed → Flushing → Flushed →（Dropped）</strong>这条主线就够了——它贯穿了一条数据"从内存可变、到落盘不可变、到最终被回收"的一生。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">commonpb.SegmentState</span><span class="ln">milvus-proto go-api/v3 生成枚举（common.proto）</span></div>
  <pre><span class="cm">// 段的生命周期状态（由 common.proto 生成，datacoord 大量引用）</span>
SegmentState_Growing    <span class="cm">// 增长：内存中、可变、持续写入</span>
SegmentState_Sealed     <span class="cm">// 封存：写满、不可变、只读</span>
SegmentState_Flushing   <span class="cm">// 刷盘中：正写成 binlog</span>
SegmentState_Flushed    <span class="cm">// 已刷盘：落到对象存储，可建索引</span>
SegmentState_Dropped    <span class="cm">// 丢弃：被压缩/删除替代，等待 GC</span>
SegmentState_Importing  <span class="cm">// 导入：批量导入时的临时段</span></pre>
</div>

<div class="card warn">
  <div class="tag">⚠️ 数值顺序 ≠ 时间顺序</div>
  本课讲的是<strong>时间顺序</strong>（Growing→Sealed→Flushing→Flushed→Dropped），
  但 proto 里枚举的<strong>数值</strong>并不按这个顺序排：<span class="mono">NotExist=1, Growing=2, Sealed=3, Flushed=4, Flushing=5, Dropped=6</span>——
  注意 <strong>Flushed 的数字（4）反而排在 Flushing（5）前面</strong>。这只是历史上枚举值追加的先后所致，与状态流转的真实顺序无关，<strong>属正常现象</strong>，别拿数值大小去推断流程方向。
</div>

<h2>vchannel → pchannel：数据从哪条管子流进来</h2>
<p>新写入的数据不是直接"塞进" segment 的，而是先经过一条<strong>流式日志的管道</strong>。这里有两个概念：<strong>vchannel（虚拟通道）</strong>和 <strong>pchannel（物理通道）</strong>。
一个 collection 在创建时会被<strong>分成 N 个 vchannel（虚拟分片，shard）</strong>——这就是"分片数"。每条写入按主键哈希落到某个 vchannel 上，
同一个 vchannel 的数据由一个 DataNode/StreamingNode 负责消费、攒成 Growing 段。<strong>vchannel 是逻辑上的"分片"概念</strong>。</p>

<p>为什么要分片？因为一个 collection 的写入量可能很大，单条管道扛不住。把它拆成 N 条 vchannel，每条独立消费、独立攒段，就能<strong>并行吃下写入</strong>——
这是写入侧横向扩展的关键。分片数在建表时定下，决定了写入的最大并行度，所以是个需要提前规划的容量参数。</p>


<p>而 <strong>pchannel 是物理通道</strong>——它对应消息队列（WAL）里一个真实的 <strong>topic</strong>。多个 vchannel 可以<strong>共享</strong>同一个 pchannel：
vchannel 的名字其实就是在 pchannel 名字后面拼上 collection ID 和分片序号。下面这段代码就揭示了二者的映射关系——从一个 vchannel 名字里<strong>截掉最后一段</strong>，就还原出它所在的 pchannel：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">pkg/util/funcutil/func.go</span><span class="ln">ToPhysicalChannel / GetVirtualChannel</span></div>
  <pre><span class="cm">// vchannel 名 = pchannel 名 + "_" + collectionID + "v" + 分片号</span>
<span class="kw">func</span> GetVirtualChannel(pchannel <span class="kw">string</span>, collectionID <span class="kw">int64</span>, idx <span class="kw">int</span>) <span class="kw">string</span> {
    <span class="kw">return</span> fmt.Sprintf(<span class="st">"%s_%dv%d"</span>, pchannel, collectionID, idx)
}

<span class="cm">// 反过来：从 vchannel 名截掉最后一段，就得到 pchannel</span>
<span class="kw">func</span> ToPhysicalChannel(vchannel <span class="kw">string</span>) <span class="kw">string</span> {
    index := strings.LastIndex(vchannel, <span class="st">"_"</span>)
    <span class="kw">return</span> vchannel[:index]   <span class="cm">// 多个 vchannel 可共享一个 pchannel</span>
}</pre>
</div>

<p>为什么要分这两层？因为<strong>逻辑分片数（vchannel）</strong>和<strong>物理资源数（pchannel/topic）</strong>需要<strong>解耦</strong>：你可以有很多逻辑分片来并行处理，
但底层物理 topic 的数量受 MQ 资源限制，于是让多个 vchannel 复用少量 pchannel。这是"逻辑与物理解耦"的经典设计——和上一课"分区是逻辑、segment 是物理"异曲同工。</p>

<h2>日志即数据：Milvus 的核心哲学</h2>
<p>现在来讲 Milvus 最重要的一条设计思想——<strong>"日志即数据（log as data）"</strong>，也叫"log as a source of truth"。它的意思是：
<strong>写入这件事的"真相"，不是某个表、某个段里的数据，而是那条按时间戳排好序、只追加（append-only）、可重放（replayable）的日志</strong>。</p>

<p>传统数据库里，"日志"（WAL）只是为了崩溃恢复的辅助，真正的数据在表里。Milvus 把这个关系<strong>倒了过来</strong>：日志本身就是权威数据源，
其他一切数据形态——内存里的 Growing 段、对象存储里的 binlog、QueryNode 加载的索引——都是<strong>对这条日志的"物化（materialized）视图"</strong>，
它们靠<strong>不断消费、重放这条日志</strong>来追上最新状态。一条写入只要<strong>成功写进了日志</strong>，就算"落地"了，哪怕此刻还没刷盘、还没建索引。</p>

<p>这里还藏着一个细节：日志里的每条记录都带一个<strong>时间戳（timestamp）</strong>。Milvus 用一套全局时间戳机制给所有写入和查询<strong>排序</strong>，
于是"在某个时间点之前的数据是什么样"这件事是<strong>确定可重现</strong>的。这就是后面 MVCC、一致性级别、时间旅行查询的根基——而它们全都源自"日志即数据"这一条。</p>


<div class="flow">
  <div class="node hl"><div class="nt">insert</div><div class="nd">客户端写入</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">写入日志(WAL)</div><div class="nd">按 ts 追加 · pchannel</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Growing 段</div><div class="nd">消费日志 · 内存可查</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Sealed + Flush</div><div class="nd">落盘 binlog</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">建索引</div><div class="nd">ANN 索引就绪</div></div>
</div>

<p>这条哲学带来三个巨大好处：①<strong>边写边查</strong>——数据一进日志就被 Growing 段消费、立即可查，不必等刷盘和建索引；
②<strong>崩溃恢复简单</strong>——进程挂了，重放日志即可重建内存状态，不丢数据；③<strong>解耦与扩展</strong>——读、写、索引各自独立地消费同一条日志，
谁慢了不拖累别人，也能各自独立扩展。这正是第一部分埋下的那句"日志即数据"的真正含义，也是 Milvus 流式架构（第十五课起的写入链路）的地基。</p>

<h2>列式布局：段内部怎么存</h2>
<p>最后看一眼 segment <strong>内部</strong>是怎么存数据的。Milvus 用<strong>列式（columnar）布局</strong>：同一个字段的所有值<strong>连续存在一起</strong>，
而不是像关系库那样一行行存。比如一个段里有 id、vector、price 三个字段，它会把所有 id 存一块、所有 vector 存一块、所有 price 存一块。
落盘后，每个字段对应一份 <span class="inline">binlog</span> 文件。</p>

<p>为什么用列式？因为向量检索的访问模式是"<strong>把某一列（向量列）整批拿出来算距离</strong>"，列式布局让这种<strong>批量、连续</strong>的访问极其高效（缓存友好、可向量化计算）；
标量过滤也类似——只需扫描相关的那几列，不必把整行读出来。<strong>列式 + 按段切分 + 日志驱动</strong>，这三件事合起来，就构成了 Milvus 存储层的骨架。</p>

<p>这也解释了为什么上一课讲的那些<strong>数据类型</strong>会按字段分开存：每个字段（无论是 Int64 主键、FloatVector、还是 JSON）在段里都是<strong>独立的一列、独立的一份 binlog</strong>。
向量字段那一列交给 ANN 索引去加速，标量字段那几列交给标量索引或暴力过滤——两者在检索时配合完成"先按标量过滤、再在候选里做向量召回"的混合查询。
段、列、日志、索引这几个概念到这里就彻底闭环了。</p>


<h2>把几件事串起来：一条数据的一生</h2>
<p>到这里，我们可以把前面所有概念拼成一张完整的图，看一条数据从写入到被检索经历了什么。下面这张表把<strong>各个阶段</strong>、它所在的<strong>段状态</strong>、
<strong>存放位置</strong>和<strong>能否被查到</strong>对照起来——这正是"边写边查"和"日志即数据"在现实中的样子：</p>

<table class="t">
  <thead><tr><th>阶段</th><th>段状态</th><th>数据在哪</th><th>是否可查</th><th>说明</th></tr></thead>
  <tbody>
    <tr><td>刚写入</td><td>—</td><td>WAL 日志（pchannel）</td><td>—</td><td>写进日志即"落地"，这是唯一真相</td></tr>
    <tr><td>被消费</td><td>Growing</td><td>内存（增长段）</td><td>✅ 立即可查</td><td>保证新数据新鲜度，暴力/临时检索</td></tr>
    <tr><td>写满封存</td><td>Sealed</td><td>内存 → 准备刷盘</td><td>✅</td><td>不可变只读快照</td></tr>
    <tr><td>持久化</td><td>Flushing→Flushed</td><td>对象存储（binlog）</td><td>✅</td><td>不怕崩溃，可建索引</td></tr>
    <tr><td>建好索引</td><td>Flushed</td><td>对象存储 + 索引文件</td><td>✅ 高效</td><td>QueryNode 加载后高效 ANN 检索</td></tr>
    <tr><td>压缩回收</td><td>Dropped</td><td>等待 GC</td><td>❌</td><td>被合并/删除替代后逻辑丢弃</td></tr>
  </tbody>
</table>

<p>读这张表时请特别注意一件事：<strong>无论数据处在哪个阶段，只要它已经进了日志，就是"已落地"的</strong>——查询时 Milvus 会<strong>同时</strong>看 QueryNode 上加载的封存段（历史数据）
和正在增长的 Growing 段（最新数据），把两边的结果合并返回。这就是为什么 Milvus 能做到"刚写进去的数据立刻就能搜到"，而不像传统离线索引那样要等一轮批处理。
理解了这张表，你就理解了 Milvus 存储与查询协同的核心机制。</p>

<h2>查询时：Growing 与 Sealed 都会被搜到</h2>
<p>很多人有个误解，以为"只有落了盘、建了索引的段才会被搜索"。其实恰恰相反：<strong>一次查询会同时扇出到两类段</strong>——
QueryNode 上加载的 <strong>Sealed 段</strong>（历史数据、带 ANN 索引，走高效检索）和仍在内存里的 <strong>Growing 段</strong>（最新数据、还没建正式索引，走暴力/临时检索），
最后把两边的 topK 候选<strong>归并</strong>成一个全局结果返回。少了任何一边结果都不完整：只搜 Sealed 会漏掉刚写入的最新数据，只搜 Growing 则看不到海量历史。</p>

<div class="cols">
  <div class="col"><h4>Growing 段（最新）</h4><p>内存中、可变、还没正式索引。负责<strong>新鲜度</strong>：刚写进来的数据就在这里，被暴力或临时结构检索。数据量小，暴力也够快。</p></div>
  <div class="col"><h4>Sealed 段（历史）</h4><p>已落盘、带 ANN 索引、被 QueryNode 加载。负责<strong>规模与效率</strong>：海量历史数据的高效近邻检索都在这里完成。</p></div>
</div>

<p>这套"两类段一起搜、再归并"的设计，正是 Milvus 能兼顾<strong>"查得到最新"和"查得快历史"</strong>的关键。它也解释了"刚 insert 完马上就能搜到"的原理——
那条数据此刻就躺在某个 Growing 段里，根本不必等刷盘与建索引。后面查询链路的课会展开"结果怎么归并、一致性级别怎么影响可见性"，这里先记住一句话：<strong>Growing 与 Sealed 是查询的两条腿，缺一不可。</strong></p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：<strong>segment 是数据与索引的基本单位，沿 Growing → Sealed → Flushing → Flushed →（Dropped）演化</strong>。
  数据经 vchannel（逻辑分片）流入、映射到 pchannel（物理 MQ topic）；Milvus 奉行<strong>"日志即数据"</strong>——日志是唯一真相，其余形态都是它的物化视图，
  这才有了"边写边查"和简单的崩溃恢复。段内用列式布局，对向量批量计算友好。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>segment</strong>：数据/索引的基本单位；Growing（内存、可变、可查）vs Sealed（不可变、刷盘、建索引）。</li>
    <li><strong>生命周期</strong>：Growing → Sealed → Flushing → Flushed →（Dropped），状态名见 <span class="mono">SegmentState_*</span>。</li>
    <li><strong>vchannel → pchannel</strong>：collection 分成 N 个 vchannel（逻辑分片），多个 vchannel 共享一个 pchannel（物理 MQ topic）。</li>
    <li><strong>日志即数据</strong>：append-only、带时间戳、可重放的日志是唯一真相；其他数据形态是它的物化视图——支撑边写边查与崩溃恢复。</li>
    <li><strong>列式布局</strong>：段内按字段连续存（每字段一份 binlog），对向量批量计算和标量过滤都高效。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson we said the data in a partition "is still chopped into many segments to store." This lesson explains the <strong>segment</strong>—Milvus's
<strong>basic unit of data and index</strong>—in full: its <strong>lifecycle</strong> (Growing → Sealed → Flushing → Flushed → (Dropped)), how vector data flows in
through a <strong>vchannel</strong> and maps to an underlying <strong>pchannel</strong>, and Milvus's most important design philosophy—<strong>"log as data."</strong>
Understand segments and you finally understand how "search while writing" actually works.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of writes as a factory line. New goods first pile into the <strong>container currently being loaded</strong> (a Growing segment—you can still stuff more in);
  once full it gets <strong>sealed</strong> (Sealed—no new goods); the sealed container is <strong>archived into the warehouse</strong> (Flushing → Flushed, landing in object storage);
  someday when that batch expires, the whole container is <strong>scrapped</strong> (Dropped). But the real "ledger" isn't the containers—it's the
  <strong>conveyor-belt log at the line's entrance that keeps recording "who, when, what goods arrived."</strong> As long as the log survives, you can rebuild everything by replaying it.
  That log is Milvus's soul.
</div>

<h2>Segment: the basic unit of data and index</h2>
<p>A collection may hold hundreds of millions of rows, and Milvus never manages it as "one giant blob"—it chops it into many <strong>segments</strong>.
Each segment is a <strong>batch of entities</strong> (typically hundreds of thousands to a few million), and it is Milvus's basic unit of
<strong>storage, flushing, indexing, loading, and search</strong>—nearly every data operation is segment-grained. Why chop? Because only by splitting "big data" into "many small blocks"
can you <strong>process in parallel, index independently, load on demand, and update incrementally</strong>—the prerequisite for horizontal scaling.
By analogy, rather than managing one cavernous warehouse, pack goods into many <strong>standard containers</strong>: each can be moved, shelved, and inventoried independently;
all elasticity and parallelism comes from this "chunking." A Milvus segment is exactly such a standard container. Each segment also carries its own metadata (segment ID, owning collection/partition, row count, state…), registered and scheduled by DataCoord.</p>

<p>Segments come in two kinds, matching "being written" and "already written": a <strong>Growing segment</strong> lives in memory and keeps receiving new writes via the streaming log;
a <strong>Sealed segment</strong> is already full and has become <strong>immutable</strong>, flushed to object storage with an index built on top.
This split of "mutable Growing + immutable Sealed" is the key to understanding "search while writing" and index construction later.</p>

<p>Why stress "immutable"? Because <strong>immutability is a distributed system's best friend</strong>: once a segment is sealed it never changes, so it can be
<strong>safely cached, replicated, and loaded in parallel onto many QueryNodes</strong> without worrying about read-while-write races. What about deletes and updates?
Milvus doesn't modify the original segment—it <strong>writes a separate "delete log"</strong> and filters deleted primary keys at search time; the actual physical cleanup is left to background <strong>compaction</strong>.
So "immutable segments + delete logs + compaction" is the clever design that lets Milvus support inserts/updates/deletes while keeping reads highly concurrent.</p>

<div class="cols">
  <div class="col"><h4>Growing</h4><p>In memory, <strong>mutable</strong>, continuously absorbing new data via vchannel. It is <strong>immediately searchable</strong> (freshness), but has no formal index yet—brute-force or temporary structures.</p></div>
  <div class="col"><h4>Sealed</h4><p>Full and <strong>immutable</strong>, flushed to binlogs in object storage, with an ANN index built on top. Efficient to search—the home of most historical data.</p></div>
</div>

<h2>Lifecycle: from Growing to Dropped</h2>
<p>A segment evolves along a <strong>fixed state chain</strong>. These names aren't invented by the tutorial—they are <strong>literally defined</strong> in Milvus's
<span class="inline">SegmentState</span> enum: <strong>Growing → Sealed → Flushing → Flushed → (Dropped)</strong>. Each step has a clear trigger:</p>

<div class="timeline">
  <div class="lane"><span class="lane-label">Growing</span><span class="tslot">in memory · mutable</span><span class="tslot span">keeps absorbing new data from vchannel, searchable immediately</span></div>
  <div class="lane"><span class="lane-label">Sealed</span><span class="tslot now">full / timeout triggers seal</span><span class="tslot">no more writes, becomes immutable</span></div>
  <div class="lane"><span class="lane-label">Flushing</span><span class="tslot">landing to disk</span><span class="tslot">data written as binlog files</span></div>
  <div class="lane"><span class="lane-label">Flushed</span><span class="tslot now">stored in object storage</span><span class="tslot">index can be built on top</span></div>
  <div class="lane"><span class="lane-label">Dropped</span><span class="tslot">replaced by compaction/delete</span><span class="tslot">logically dropped, awaiting GC</span></div>
</div>

<p>Key transitions: <strong>Growing → Sealed</strong> is triggered when "the segment is full (size cap)" or "enough time has passed (timeout)"—once sealed it
<strong>accepts no new writes</strong> and becomes a read-only snapshot. <strong>Sealed → Flushing → Flushed</strong> <strong>persists</strong> the in-memory data into
<span class="inline">binlog</span> files in object storage; after Flushed the data <strong>survives process crashes</strong> and an ANN index can be built on it safely.
<strong>Dropped</strong> usually follows <strong>compaction</strong>: several small segments merge into a big one, or deleted-marked data is cleaned up, and the old segment is marked Dropped awaiting GC.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Trigger seal</h4><p>Segment full (size cap) <strong>or</strong> timeout—DataCoord turns the Growing segment Sealed; read-only from now on.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Flush to binlog</h4><p><strong>Serialize column-organized in-memory data into binlog files</strong>, written field by field to object storage; once done it is Flushed—persisted, crash-proof.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Build index async</h4><p>IndexNode reads binlogs and <strong>builds the ANN index</strong> (IVF/HNSW…); index files also go to object storage.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Load &amp; search</h4><p>QueryNode <strong>loads</strong> the sealed segment and its index into memory for efficient ANN search; Growing segments fill in the freshest data.</p></div></div>
</div>

<p>Note steps 3 and 4 happen <strong>asynchronously</strong>: flushing and indexing run in the background, blocking neither writes nor queries on Growing segments. This pipeline where
<strong>writing, flushing, indexing, and loading</strong> are independent and non-blocking is exactly how Milvus achieves high throughput and low latency. Each stage scales independently—add DataNodes to write faster, IndexNodes to index faster, QueryNodes to serve more queries.</p>

<p>A few related states are worth mentioning: the enum also has <span class="inline">Importing</span> (a temporary segment during bulk import) and <span class="inline">NotExist</span>, etc.
But for the main flow, remembering <strong>Growing → Sealed → Flushing → Flushed → (Dropped)</strong> is enough—it traces a row of data's whole life "from mutable in memory, to immutable on disk, to finally reclaimed."</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">commonpb.SegmentState</span><span class="ln">generated enum in milvus-proto go-api/v3 (common.proto)</span></div>
  <pre><span class="cm">// Segment lifecycle states (generated from common.proto, heavily used by datacoord)</span>
SegmentState_Growing    <span class="cm">// in memory, mutable, continuous writes</span>
SegmentState_Sealed     <span class="cm">// full, immutable, read-only</span>
SegmentState_Flushing   <span class="cm">// landing to disk as binlog</span>
SegmentState_Flushed    <span class="cm">// flushed to object storage, indexable</span>
SegmentState_Dropped    <span class="cm">// replaced by compaction/delete, awaiting GC</span>
SegmentState_Importing  <span class="cm">// temporary segment during bulk import</span></pre>
</div>

<div class="card warn">
  <div class="tag">⚠️ Numeric order ≠ temporal order</div>
  This lesson teaches the <strong>temporal order</strong> (Growing→Sealed→Flushing→Flushed→Dropped), but the enum's <strong>numeric values</strong>
  in the proto do <strong>not</strong> follow that order: <span class="mono">NotExist=1, Growing=2, Sealed=3, Flushed=4, Flushing=5, Dropped=6</span>—
  note that <strong>Flushed's number (4) actually precedes Flushing's (5)</strong>. That is just the historical order in which enum values were
  appended; it has nothing to do with the real state-transition order. This is <strong>expected</strong>—don't infer flow direction from the numbers.
</div>

<h2>vchannel → pchannel: which pipe data flows in through</h2>
<p>Newly written data isn't "stuffed" directly into a segment—it first passes through a <strong>streaming-log pipeline</strong>. Two concepts here: <strong>vchannel (virtual channel)</strong> and <strong>pchannel (physical channel)</strong>.
At creation a collection is <strong>split into N vchannels (virtual shards)</strong>—the "shard count." Each write hashes by primary key onto some vchannel;
data on the same vchannel is consumed by one DataNode/StreamingNode and accumulated into Growing segments. <strong>A vchannel is the logical "shard" concept.</strong></p>

<p>Why shard? Because a collection's write volume can be huge and a single pipe can't keep up. Splitting it into N vchannels, each consumed and accumulated independently, lets you
<strong>ingest writes in parallel</strong>—the key to write-side horizontal scaling. The shard count is fixed at table creation and bounds the maximum write parallelism, so it's a capacity parameter to plan ahead.</p>

<p>A <strong>pchannel is the physical channel</strong>—it maps to a real <strong>topic</strong> in the message queue (WAL). Multiple vchannels can <strong>share</strong> one pchannel:
a vchannel's name is simply the pchannel name with the collection ID and shard index appended. The code below reveals the mapping—strip the last segment off a vchannel name to recover its pchannel:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">pkg/util/funcutil/func.go</span><span class="ln">ToPhysicalChannel / GetVirtualChannel</span></div>
  <pre><span class="cm">// vchannel name = pchannel name + "_" + collectionID + "v" + shardIdx</span>
<span class="kw">func</span> GetVirtualChannel(pchannel <span class="kw">string</span>, collectionID <span class="kw">int64</span>, idx <span class="kw">int</span>) <span class="kw">string</span> {
    <span class="kw">return</span> fmt.Sprintf(<span class="st">"%s_%dv%d"</span>, pchannel, collectionID, idx)
}

<span class="cm">// reverse: strip the last segment off a vchannel name to get pchannel</span>
<span class="kw">func</span> ToPhysicalChannel(vchannel <span class="kw">string</span>) <span class="kw">string</span> {
    index := strings.LastIndex(vchannel, <span class="st">"_"</span>)
    <span class="kw">return</span> vchannel[:index]   <span class="cm">// many vchannels can share one pchannel</span>
}</pre>
</div>

<p>Why two layers? Because the <strong>logical shard count (vchannel)</strong> and the <strong>physical resource count (pchannel/topic)</strong> need to be <strong>decoupled</strong>: you can have many logical shards for parallelism,
but the number of physical topics is bounded by MQ resources, so many vchannels reuse a few pchannels. This is the classic "decouple logical from physical" design—echoing last lesson's "partition is logical, segment is physical."</p>

<h2>Log as data: Milvus's core philosophy</h2>
<p>Now for Milvus's most important design idea—<strong>"log as data,"</strong> a.k.a. "log as the source of truth." It means:
<strong>the "truth" of a write isn't the data in some table or segment, but that timestamp-ordered, append-only, replayable log.</strong></p>

<p>In a traditional database the "log" (WAL) is just an aid for crash recovery, with the real data in tables. Milvus <strong>inverts</strong> this: the log itself is the authoritative source,
and every other data form—the in-memory Growing segment, the binlogs in object storage, the index loaded by QueryNode—is a <strong>"materialized view"</strong> of that log,
catching up by <strong>continuously consuming and replaying it</strong>. A write counts as "landed" the moment it is <strong>successfully written to the log</strong>, even if not yet flushed or indexed.</p>

<p>There's a hidden detail: each log record carries a <strong>timestamp</strong>. Milvus uses a global timestamp mechanism to <strong>order</strong> all writes and queries, so "what the data looked like before a given point in time" is
<strong>deterministically reproducible</strong>. This is the foundation for MVCC, consistency levels, and time-travel queries later—all stemming from "log as data."</p>

<div class="flow">
  <div class="node hl"><div class="nt">insert</div><div class="nd">client write</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">write log (WAL)</div><div class="nd">append by ts · pchannel</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Growing seg</div><div class="nd">consume log · searchable</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Sealed + Flush</div><div class="nd">land binlog</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">build index</div><div class="nd">ANN index ready</div></div>
</div>

<p>This philosophy brings three huge benefits: ① <strong>search while writing</strong>—data is consumed by Growing segments the instant it hits the log and is immediately searchable, no waiting for flush/index;
② <strong>simple crash recovery</strong>—if a process dies, replay the log to rebuild in-memory state, no data loss; ③ <strong>decoupling and scaling</strong>—reads, writes, and indexing each consume the same log independently,
so a slow one doesn't drag the others and each scales on its own. This is what "log as data" from Part 1 truly meant, and the bedrock of Milvus's streaming architecture (the write path from Lesson 15 on).</p>

<h2>Columnar layout: how a segment stores data inside</h2>
<p>Finally, a glance at how a segment stores data <strong>internally</strong>. Milvus uses a <strong>columnar layout</strong>: all values of one field are <strong>stored contiguously together</strong>,
rather than row by row as in relational databases. E.g., a segment with id, vector, and price fields stores all ids together, all vectors together, all prices together.
After flushing, each field corresponds to one <span class="inline">binlog</span> file.</p>

<p>Why columnar? Because vector search's access pattern is "<strong>pull a whole column (the vector column) out in bulk and compute distances</strong>," and columnar layout makes such <strong>bulk, contiguous</strong> access extremely efficient (cache-friendly, vectorizable);
scalar filtering is similar—scan only the relevant columns, no need to read whole rows. <strong>Columnar + per-segment chunking + log-driven</strong>—these three together form the skeleton of Milvus's storage layer.</p>

<p>This also explains why last lesson's <strong>data types</strong> are stored field by field: each field (be it an Int64 primary key, a FloatVector, or JSON) is an <strong>independent column with its own binlog</strong> in the segment.
The vector field's column is accelerated by the ANN index; scalar columns get scalar indexes or brute-force filtering—together completing hybrid queries that "filter by scalar first, then recall vectors among candidates."
Segment, column, log, and index now close the loop.</p>

<h2>Tying it together: the life of one row</h2>
<p>Now we can assemble everything into one complete picture of what a row goes through from write to search. The table below maps each <strong>stage</strong> to its <strong>segment state</strong>,
<strong>where the data lives</strong>, and <strong>whether it's searchable</strong>—this is "search while writing" and "log as data" in real life:</p>

<table class="t">
  <thead><tr><th>Stage</th><th>Segment state</th><th>Where data lives</th><th>Searchable?</th><th>Note</th></tr></thead>
  <tbody>
    <tr><td>Just written</td><td>—</td><td>WAL log (pchannel)</td><td>—</td><td>Written to log = "landed", the only truth</td></tr>
    <tr><td>Consumed</td><td>Growing</td><td>memory (growing seg)</td><td>✅ immediately</td><td>Freshness; brute/temporary search</td></tr>
    <tr><td>Full, sealed</td><td>Sealed</td><td>memory → ready to flush</td><td>✅</td><td>Immutable read-only snapshot</td></tr>
    <tr><td>Persisted</td><td>Flushing→Flushed</td><td>object storage (binlog)</td><td>✅</td><td>Crash-proof, indexable</td></tr>
    <tr><td>Indexed</td><td>Flushed</td><td>object storage + index files</td><td>✅ efficient</td><td>Efficient ANN after QueryNode load</td></tr>
    <tr><td>Compacted/GC</td><td>Dropped</td><td>awaiting GC</td><td>❌</td><td>Logically dropped after merge/delete</td></tr>
  </tbody>
</table>

<p>Reading this table, note one thing in particular: <strong>no matter which stage the data is in, once it's in the log it is "landed"</strong>—at query time Milvus looks at <strong>both</strong> the sealed segments loaded on QueryNodes (historical data)
and the still-growing Growing segments (newest data), merging both results. That's why Milvus can "search data the instant it's written," unlike traditional offline indexes that wait for a batch round.
Understand this table and you understand the core mechanism of Milvus's storage-query collaboration.</p>

<h2>At query time: both Growing and Sealed are searched</h2>
<p>A common misconception is that "only flushed, indexed segments get searched." The opposite is true: <strong>a single query fans out to both
kinds of segment</strong>—the <strong>Sealed segments</strong> loaded on QueryNodes (historical data, with an ANN index, efficient search) and the
<strong>Growing segments</strong> still in memory (newest data, no formal index yet, brute-force/temporary search)—then <strong>merges</strong> the topK
candidates from both sides into one global result. Drop either side and the result is incomplete: searching only Sealed misses the freshest
just-written data, while searching only Growing can't see the vast history.</p>

<div class="cols">
  <div class="col"><h4>Growing segments (newest)</h4><p>In memory, mutable, not formally indexed yet. They provide <strong>freshness</strong>: just-written data lives here, searched by brute force or temporary structures. Small in size, so brute force is fast enough.</p></div>
  <div class="col"><h4>Sealed segments (history)</h4><p>Flushed, ANN-indexed, loaded by QueryNodes. They provide <strong>scale and efficiency</strong>: efficient nearest-neighbor search over vast historical data happens here.</p></div>
</div>

<p>This "search both kinds, then merge" design is exactly how Milvus reconciles <strong>"finds the newest" and "finds history fast"</strong>. It also
explains why "you can search right after an insert"—that row is sitting in some Growing segment right now, with no need to wait for flush and
indexing. Later query-path lessons unpack "how results are merged and how the consistency level affects visibility"; for now, remember one
line: <strong>Growing and Sealed are the two legs a query stands on—neither is dispensable.</strong></p>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>a segment is the basic unit of data and index, evolving Growing → Sealed → Flushing → Flushed → (Dropped)</strong>.
  Data flows in via vchannels (logical shards), mapped to pchannels (physical MQ topics); Milvus follows <strong>"log as data"</strong>—the log is the only truth and every other form is its materialized view,
  which is what enables "search while writing" and simple crash recovery. Inside a segment, the columnar layout is friendly to bulk vector computation.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Segment</strong>: the basic unit of data/index; Growing (in memory, mutable, searchable) vs Sealed (immutable, flushed, indexed).</li>
    <li><strong>Lifecycle</strong>: Growing → Sealed → Flushing → Flushed → (Dropped); state names per <span class="mono">SegmentState_*</span>.</li>
    <li><strong>vchannel → pchannel</strong>: a collection splits into N vchannels (logical shards); many vchannels share one pchannel (physical MQ topic).</li>
    <li><strong>Log as data</strong>: an append-only, timestamped, replayable log is the only truth; other forms are its materialized views—enabling search-while-writing and crash recovery.</li>
    <li><strong>Columnar layout</strong>: stored field by field within a segment (one binlog per field), efficient for bulk vector computation and scalar filtering.</li>
  </ul>
</div>
""",
}


LESSON_08 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前面几课讲的都是 Milvus "内部"怎么组织数据；这一课收个尾，看看 Milvus <strong>"外部"</strong>依赖什么、又能以哪些<strong>形态部署</strong>。
Milvus 把"存元数据""存大块数据""记写入日志"这三件事<strong>分别外包给三类外部组件</strong>：<strong>etcd</strong>（元数据 + 服务发现）、
<strong>对象存储</strong>（MinIO/S3，存 binlog 与索引）、<strong>消息队列 / WAL</strong>（rocksmq / Pulsar / Kafka / Woodpecker）。
再配合三种部署形态——<strong>Milvus Lite / Standalone / Cluster</strong>——你就能从"能跑起来"一路理解到"能扛生产"。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把 Milvus 想成一家<strong>大型连锁餐厅</strong>。它不自己造发电机、不自己挖水井，而是接入城市的<strong>基础设施</strong>：
  <strong>etcd</strong> 像是<strong>工商登记与门店通讯录</strong>（谁在营业、各店地址、统一调度）；<strong>对象存储</strong>像是<strong>城郊的中央仓库</strong>（海量食材长期囤放，便宜耐放）；
  <strong>消息队列</strong>像是<strong>后厨的点单传送带</strong>（每一单按顺序记下、依次处理，断电也能照单复原）。
  而"开一家路边小摊（Lite）""开一家单店（Standalone）""开一片连锁（Cluster）"，则是同一套手艺的三种规模。把这三样基础设施和三种规模想清楚，你就掌握了 Milvus 在真实世界里"长什么样、怎么落地"。
</div>

<h2>为什么要有外部依赖</h2>
<p>一个看似简单的问题：Milvus 为什么不把元数据、数据、日志全自己存，非要依赖外部组件？答案是<strong>"专业的事交给专业的系统"</strong>。
存元数据需要<strong>强一致、可监听变更</strong>——这正是 etcd 的看家本领；存海量向量和索引需要<strong>便宜、近乎无限、高可用</strong>的容量——这正是对象存储（S3 类）的强项；
记写入日志需要<strong>有序、持久、可重放</strong>——这正是消息队列的本职。Milvus 把这三类"难且通用"的能力<strong>外包</strong>出去，自己专注做"向量检索"这件最核心的事。
如果什么都自己造，不仅要重复造许多成熟的轮子，还要为每一个轮子的可靠性、扩展性单独操心——这显然不划算。更何况 etcd、S3、Kafka 这些系统都已被业界千锤百炼、生态成熟，直接复用它们，既省力又稳妥。</p>

<p>这种"<strong>存储与计算分离</strong>"的架构还带来一个巨大好处：Milvus 自己的各个节点都变成了<strong>无状态（stateless）</strong>或近乎无状态的——
真正的"状态"都沉淀在这三个外部系统里。于是计算节点可以<strong>随意增删、崩了重启、弹性伸缩</strong>，数据却安然无恙。这是云原生时代数据库的标准做法，也是 Milvus 能横向扩展的根基。
换句话说，当查询压力上来时，你只要多加几个无状态的 QueryNode，它们各自从对象存储拉数据、从 etcd 读拓扑、从 MQ 消费日志，就能立刻分担负载；
某个节点挂了，它身上没有独占的状态，重启或换一台机器重新加载即可，<strong>不会丢任何数据</strong>。这正是"存算分离 + 外部依赖"换来的弹性与可靠。</p>

<h2>三大外部依赖</h2>
<p>下面这张分层图把三类依赖、它们的角色和典型实现一次性摆清楚。注意：上层是 Milvus 自己的组件（协调者 + 节点），下层这三块才是它<strong>赖以生存的外部基础设施</strong>：</p>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">应用</span><span class="name">Milvus 组件</span></div><div class="ld">协调者（rootcoord/datacoord/querycoord）+ 节点（proxy/querynode/datanode/streamingnode）——大多无状态</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">依赖①</span><span class="name">etcd · 元数据 + 服务发现</span></div><div class="ld">collection/schema/segment 元信息、节点注册与健康、全局配置。强一致、可 watch。</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">依赖②</span><span class="name">对象存储 · MinIO / S3</span></div><div class="ld">binlog（列式数据）、索引文件、delta 日志。便宜、近乎无限、持久。</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">依赖③</span><span class="name">消息队列 / WAL</span></div><div class="ld">rocksmq / Pulsar / Kafka / Woodpecker。有序、持久、可重放的写入日志——"日志即数据"的载体。</div></div>
</div>

<table class="t">
  <thead><tr><th>外部依赖</th><th>角色（外包了什么能力）</th><th>典型实现 / 例子</th></tr></thead>
  <tbody>
    <tr><td><strong>etcd</strong></td><td>元数据 + 服务发现：强一致、可 watch 变更</td><td class="mono">etcd（K8s 同款）</td></tr>
    <tr><td><strong>对象存储</strong></td><td>持久化海量不可变数据：binlog、索引文件、delta 日志</td><td class="mono">MinIO / AWS S3 / GCS / 阿里云 OSS</td></tr>
    <tr><td><strong>消息队列 / WAL</strong></td><td>有序、持久、可重放的写入日志（"日志即数据"）</td><td class="mono">RocksMQ / Pulsar / Kafka / Woodpecker</td></tr>
  </tbody>
</table>

<p>记住这张表的一个规律：<strong>三类依赖恰好对应"小而关键""大而廉价""有序可重放"三种截然不同的存储需求</strong>——元数据少但要强一致，
向量数据多但写少读多，写入日志则要严格有序、可回放。把三者交给最擅长各自需求的成熟系统，正是 Milvus 这套外部依赖设计的核心思路。下面逐一展开。</p>

<h3>① etcd —— 元数据与服务发现</h3>
<p><strong>etcd</strong> 是一个<strong>强一致的分布式键值存储</strong>。Milvus 用它存放所有<strong>元数据</strong>：有哪些 collection、它们的 schema、每个 segment 的状态和位置、索引的元信息等；
同时用它做<strong>服务发现</strong>——各个节点启动后在 etcd 里注册自己，协调者通过 etcd 知道"现在有哪些节点活着、在哪"。元数据量不大但<strong>极其关键</strong>，必须强一致、不能丢，一旦元数据出错或丢失，整个集群就会"找不着北"，
这正是 etcd（Kubernetes 也用它）擅长的。它体量虽小，却是整个集群的"户口本"与"通讯录"。配置见 <span class="inline">configs/milvus.yaml</span> 的 <span class="inline">etcd</span> 段。</p>

<p>为什么元数据要单独拎出来、还非得强一致？设想两个协调者同时改同一个 segment 的状态、或者两个节点都以为自己是某个角色的主——如果元数据存储允许"读到旧值"，
整个集群就会陷入<strong>脑裂、状态错乱</strong>。etcd 用 Raft 协议保证"任何时刻所有人读到的都是同一份最新值"，并且支持 <strong>watch（监听变更）</strong>：
某个 key 一变，关心它的组件立刻收到通知。这种"强一致 + 可监听"的组合，正是协调者调度全局、节点感知拓扑变化的底座。所以 etcd 虽然存的数据不多，却是<strong>整个集群的大脑中枢</strong>，一旦它不可用，集群就无法做任何元数据变更。</p>

<h3>② 对象存储 —— 海量数据的归宿</h3>
<p>上一课的 binlog、索引文件，最终都存进<strong>对象存储</strong>：本地开发用 <strong>MinIO</strong>，云上用 <strong>S3 / GCS / 阿里云 OSS</strong> 等任何兼容 S3 API 的服务。
对象存储的特点是<strong>容量近乎无限、单位成本极低、持久可靠</strong>，特别适合存放向量这种"量大、写少读多、要长期留存"的数据。
Milvus 把"重数据"全压到这里，自己只在内存/本地盘缓存热数据。配置见 <span class="inline">milvus.yaml</span> 的 <span class="inline">minio</span> 段（地址、bucket、AK/SK 等）。</p>

<p>具体来说，对象存储里躺着三类东西：<strong>binlog</strong>（封存段刷下来的列式数据，每个字段一份）、<strong>索引文件</strong>（IVF/HNSW 等在 binlog 上建好的 ANN 索引）、
以及 <strong>delta 日志</strong>（记录删除标记的增量文件）。它们都是<strong>不可变</strong>的——写一次、读多次、永不原地改，这与对象存储"适合一次写入多次读取"的特性完美契合。
QueryNode 检索时把需要的 binlog 和索引从对象存储<strong>按需拉到本地缓存</strong>（就是 milvus.yaml 里的 <span class="inline">localStorage.path</span>），避免每次都远程读取。
这样一来，对象存储负责"廉价地存全量"，本地盘和内存负责"快速地读热点"，冷热分层、各司其职。值得强调的是，正因为这些文件都不可变，它们可以被<strong>任意多个节点同时安全读取</strong>、
可以被<strong>放心缓存</strong>而不必担心失效，这又一次印证了第七课"不可变是分布式系统好朋友"的论断——存储层的简单与可靠，很大程度上就来自这份不可变性。</p>

<h3>③ 消息队列 / WAL —— 写入日志的载体</h3>
<p>第七课的"日志即数据"那条<strong>append-only、可重放的日志</strong>，物理上就承载在<strong>消息队列（MQ）</strong>里——也就是 WAL（预写日志）。
Milvus 支持四种 MQ：<strong>rocksmq</strong>（基于 RocksDB 的内置轻量队列）、<strong>Pulsar</strong>、<strong>Kafka</strong>，以及新一代内置 WAL <strong>Woodpecker</strong>。
它们都提供"有序、持久、可被多消费者重放"的能力，正是 Growing 段消费、崩溃恢复、读写解耦的物理基础。换个角度看，MQ 在这里扮演的不是"传统消息中间件"的角色，而是 Milvus 的<strong>写入主干道</strong>——所有写入先进 MQ、再被各路消费者（攒段的、建索引的、做副本的）按需取用，谁快谁慢互不干扰。这正是为什么 MQ 的选择如此重要。</p>

<p>关于"默认用哪个"，<span class="inline">milvus.yaml</span> 的注释给了<strong>精确</strong>的规则（不要凭印象记）：当 <span class="inline">mq.type</span> 设为 <span class="inline">default</span> 时，
按当前部署模式、依下面的优先级自动挑选——</p>

<table class="t">
  <thead><tr><th>部署模式</th><th>默认 MQ</th><th>优先级顺序</th><th>说明</th></tr></thead>
  <tbody>
    <tr><td><strong>Standalone（单机/本地）</strong></td><td><strong>RocksMQ</strong></td><td>rocksmq（默认）&gt; Pulsar &gt; Kafka &gt; Woodpecker</td><td>内置、零外部依赖，开箱即用</td></tr>
    <tr><td><strong>Cluster（集群）</strong></td><td><strong>Pulsar</strong></td><td>Pulsar（默认）&gt; Kafka &gt; Woodpecker</td><td>RocksMQ 在集群模式<strong>不支持</strong></td></tr>
  </tbody>
</table>

<p>两条<strong>必须记牢</strong>的事实：① <strong>Standalone 默认是 RocksMQ</strong>，因为它内置在进程里、不需要额外部署，最适合单机；② <strong>Cluster 默认是 Pulsar</strong>，
且 <strong>RocksMQ 在集群模式下不被支持</strong>（它是单机内置的，无法跨节点共享）。另外，注释还特别建议：<strong>新实例推荐显式使用 Woodpecker</strong>，
以获得更好的性能、更简单的运维和更低的成本——它是 Milvus 主推的下一代内置 WAL。<span class="inline">mq.type</span> 的合法取值为 <span class="inline">[default, pulsar, kafka, rocksmq, woodpecker]</span>。</p>

<p>为什么这套优先级要设计得这么细？因为它要同时照顾<strong>"开箱即用"和"向后兼容"</strong>两件事：对单机用户，内置的 RocksMQ 不需要你额外部署任何东西，装上就能跑；
对集群用户，RocksMQ 这种单机内置队列根本无法跨节点共享，所以必须退而求其次用 Pulsar/Kafka 这类真正的分布式 MQ。而之所以把 Woodpecker 排在优先级末尾却又"强烈推荐新实例使用"，
是因为优先级要保证<strong>老实例升级后行为不变</strong>（不能突然把别人的默认队列换掉），但对全新部署，官方希望你主动选 Woodpecker——它作为新一代内置 WAL，在性能、运维成本上都更优。
看懂这套规则背后的"既要兼容老的、又要引导用新的"取舍，你就理解了一个成熟系统是怎么演进默认值的。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">configs/milvus.yaml</span><span class="ln">mq 段的优先级注释</span></div>
  <pre><span class="cm"># Milvus 支持四种消息队列(MQ)：rocksmq(基于 RocksDB)、Pulsar、Kafka、Woodpecker。</span>
<span class="cm"># 通过 mq.type 切换；未设置时按以下优先级（多种 MQ 同时配置时）：</span>
<span class="cm"># 1. standalone(本地)模式: rocksmq(默认) &gt; Pulsar &gt; Kafka &gt; Woodpecker</span>
<span class="cm"># 2. cluster 模式: Pulsar(默认) &gt; Kafka (集群不支持 rocksmq) &gt; Woodpecker</span>
<span class="cm"># 新实例建议显式使用 Woodpecker，以获得更好性能、更简运维、更低成本。</span>
mq:
  <span class="cm"># 合法取值: [default, pulsar, kafka, rocksmq, woodpecker]</span>
  type: default</pre>
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  Milvus 把三件最难、最通用的事<strong>外包</strong>：元数据/服务发现给 <strong>etcd</strong>，海量数据持久化给<strong>对象存储</strong>，写入日志给<strong>消息队列/WAL</strong>。
  由此自身节点近乎<strong>无状态</strong>、可弹性伸缩。部署上分 <strong>Lite / Standalone / Cluster</strong> 三档：从一行 pip 装的进程内库，到单进程一体机，再到 K8s 上各组件独立伸缩的集群。
  MQ 默认值要记准：Standalone→RocksMQ，Cluster→Pulsar，新实例推荐 Woodpecker。
</div>

<h2>三种部署形态</h2>
<p>同一套 Milvus，能以三种<strong>规模</strong>落地，对应不同的使用场景。理解它们的差异，就知道什么时候该用哪一个：</p>

<div class="cols">
  <div class="col"><h4>Milvus Lite</h4><p><strong>一个 pip 就装好</strong>的进程内（in-process）版本，数据存在<strong>本地文件</strong>，无需任何外部依赖。适合<strong>学习、原型、笔记本上的小实验</strong>、单元测试。能跑通完整 API，但不为大规模/高并发设计。</p></div>
  <div class="col"><h4>Standalone</h4><p><strong>单进程</strong>把所有组件打包在一起运行，MQ 默认用内置 <strong>RocksMQ</strong>，元数据用内嵌或本地 etcd，数据用本地 MinIO。适合<strong>中小规模生产、单机部署</strong>，运维简单。</p></div>
  <div class="col"><h4>Cluster</h4><p>各组件（协调者 + 各类节点）在 <strong>Kubernetes</strong> 上<strong>独立部署、独立伸缩</strong>，MQ 默认用 <strong>Pulsar</strong>，依赖外部 etcd / S3 / Pulsar 集群。适合<strong>大规模、高并发、高可用</strong>生产。</p></div>
</div>

<table class="t">
  <thead><tr><th>形态</th><th>怎么跑</th><th>用到的依赖</th><th>规模</th><th>何时用</th></tr></thead>
  <tbody>
    <tr><td><strong>Milvus Lite</strong></td><td>pip 装的<strong>进程内</strong>库，嵌在你的 Python 进程里</td><td><strong>零外部依赖</strong>，数据落本地文件</td><td>百万级以内 · 单机</td><td>学习、原型、笔记本实验、单元测试</td></tr>
    <tr><td><strong>Standalone</strong></td><td><strong>单进程</strong>把所有组件打包一起跑</td><td>内置 RocksMQ + 本地 MinIO + 内嵌/本地 etcd</td><td>千万级 · 单机</td><td>中小规模生产，要运维简单</td></tr>
    <tr><td><strong>Cluster</strong></td><td>各组件在 <strong>K8s</strong> 上独立部署、独立伸缩</td><td>外部 etcd / S3 / Pulsar 等生产级集群</td><td>上亿乃至更大 · 高并发高可用</td><td>大规模生产，需按组件独立扩容</td></tr>
  </tbody>
</table>

<p>这张表把三种形态的差异一次摆清：从左到右，<strong>组件越拆越散、依赖越来越外置、能扛的规模越来越大、运维也越来越重</strong>。
Lite 适合"今天就想跑通第一个向量检索"，Standalone 适合"一台机器扛住一条业务线"，Cluster 适合"几亿向量、多团队共用、不能停机"。
关键是它们共享同一套 API 与数据模型，所以选型不必一步到位——<strong>先用 Lite/Standalone 起步，规模涨上来再迁到 Cluster</strong>，业务代码几乎不动。</p>

<p>三者的核心区别其实就是<strong>"组件聚合度"和"依赖外置程度"</strong>的连续谱：Lite 把一切塞进一个进程、零外部依赖；Standalone 仍是单进程但开始用上对象存储这类依赖；
Cluster 则把每个组件拆开、把每个依赖都外置成独立集群，换来无上限的横向扩展。它们共享<strong>同一套 API 和数据模型</strong>，所以你可以<strong>从 Lite 起步、平滑迁移到 Cluster</strong>，业务代码几乎不用改。</p>

<p>怎么选？给个简单的决策直觉：<strong>在笔记本上学习、跑 demo、写单元测试</strong>，用 <strong>Lite</strong>——一个 pip 装好，数据落在本地文件，几分钟就能跑通第一个向量检索；
<strong>数据量在千万级以内、单机内存/磁盘扛得住、不需要高可用</strong>，用 <strong>Standalone</strong>——一个进程搞定，运维成本最低；
<strong>数据上亿、并发高、要求高可用、需要按组件独立扩容</strong>，上 <strong>Cluster</strong>——在 K8s 上把 proxy、querynode、datanode 等按各自负载独立伸缩，把 etcd/对象存储/Pulsar 都用生产级集群。
记住这条主线：<strong>规模越大，越要把组件拆开、把依赖外置</strong>；而无论哪一档，API 和数据模型都不变，这正是 Milvus 让你"小处起步、大处不愁"的底气。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Lite：学习与原型</h4><p>pip 安装、进程内、本地文件。<strong>零外部依赖</strong>，几分钟跑通第一个向量检索。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Standalone：中小生产</h4><p>单进程一体机，RocksMQ + 本地 MinIO/etcd。运维最简单，适合单机就够用的场景。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Cluster：大规模生产</h4><p>K8s 上组件各自伸缩，Pulsar + 外部 etcd/S3。为高并发、高可用、海量数据而生。</p></div></div>
</div>

<p>最后把这一整个"前置基础"部分串起来：第四课讲了<strong>向量与相似度</strong>（数据长什么样、怎么比），第五课讲了<strong>ANN 算法</strong>（怎么快速地比），
第六课讲了<strong>数据模型</strong>（怎么组织字段与表），第七课讲了<strong>segment 与日志即数据</strong>（数据在内部怎么存与流动），这一课讲了<strong>外部依赖与部署</strong>（整套系统靠什么支撑、以什么形态运行）。
有了这五块地基，你就具备了读懂后面 Milvus 各个子系统（写入链路、查询链路、索引、压缩……）所需的全部前置知识。</p>

<p>回头看，这五课其实回答了五个层层递进的问题：<strong>"向量是什么、怎么比较"→"海量向量怎么比得快"→"业务数据怎么建模"→"数据在引擎内部怎么存与流"→"整个引擎靠什么外部设施、以什么规模运行"</strong>。
从一个数字向量出发，一路走到一套能在 K8s 上弹性伸缩的分布式系统——这条主线，就是理解 Milvus 的<strong>地图</strong>。接下来的部分会沿着这张地图，逐一深入每个子系统的内部细节。
读到这里，恭喜你已经打好了所有前置基础。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>三大依赖</strong>：etcd（元数据 + 服务发现）、对象存储（MinIO/S3，存 binlog 与索引）、消息队列/WAL（写入日志）。</li>
    <li><strong>存算分离</strong>：状态沉淀到外部系统，Milvus 节点近乎无状态、可弹性伸缩。</li>
    <li><strong>MQ 四选项</strong>：rocksmq / Pulsar / Kafka / Woodpecker；Woodpecker 是主推的新一代内置 WAL。</li>
    <li><strong>MQ 默认值</strong>：Standalone → RocksMQ（rocksmq&gt;Pulsar&gt;Kafka&gt;Woodpecker）；Cluster → Pulsar（Pulsar&gt;Kafka&gt;Woodpecker，集群不支持 RocksMQ）。</li>
    <li><strong>三种部署</strong>：Lite（pip、进程内、本地文件）、Standalone（单进程、RocksMQ）、Cluster（K8s、Pulsar、各组件独立伸缩）；同一套 API，可平滑升级。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The previous lessons covered how Milvus organizes data "inside"; this one wraps up by looking at what Milvus depends on <strong>"outside"</strong> and the <strong>shapes it deploys in</strong>.
Milvus <strong>outsources three jobs</strong>—"store metadata," "store bulk data," "record the write log"—to three kinds of external components: <strong>etcd</strong> (metadata + service discovery),
<strong>object storage</strong> (MinIO/S3, holding binlogs and indexes), and a <strong>message queue / WAL</strong> (rocksmq / Pulsar / Kafka / Woodpecker).
Combine these with three deployment shapes—<strong>Milvus Lite / Standalone / Cluster</strong>—and you understand the whole way from "it runs" to "it carries production."
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of Milvus as a <strong>large restaurant chain</strong>. It doesn't build its own generator or dig its own well—it taps into city <strong>infrastructure</strong>:
  <strong>etcd</strong> is like the <strong>business registry and store directory</strong> (who's open, each branch's address, unified scheduling); <strong>object storage</strong> is like a <strong>central warehouse on the outskirts</strong> (vast ingredients stored long-term, cheap and durable);
  the <strong>message queue</strong> is like the <strong>order conveyor in the kitchen</strong> (every order recorded in sequence, processed one by one, replayable even after a power cut).
  And "a street stall (Lite)," "a single store (Standalone)," "a chain (Cluster)" are three scales of the same craft. Get these three infrastructures and three scales straight, and you grasp how Milvus actually "looks and lands" in the real world.
</div>

<h2>Why external dependencies</h2>
<p>A seemingly simple question: why doesn't Milvus store metadata, data, and logs all by itself instead of depending on external components? The answer is <strong>"leave the professional jobs to the professional systems."</strong>
Storing metadata needs <strong>strong consistency and change-watching</strong>—exactly etcd's forte; storing massive vectors and indexes needs <strong>cheap, near-infinite, highly available</strong> capacity—exactly object storage's (S3-class) strength;
recording the write log needs <strong>ordered, durable, replayable</strong>—exactly a message queue's job. Milvus <strong>outsources</strong> these three "hard and generic" capabilities and focuses on its core: vector search.
Building everything itself would mean reinventing many mature wheels and worrying about each wheel's reliability and scalability separately—clearly not worth it. Besides, systems like etcd, S3, and Kafka are battle-tested with mature ecosystems; reusing them directly is both easier and safer.</p>

<p>This <strong>storage-compute separation</strong> architecture brings a huge benefit: Milvus's own nodes become <strong>stateless</strong> or nearly so—the real "state" all settles into these three external systems.
So compute nodes can be <strong>added/removed at will, restarted after crashes, scaled elastically</strong> while the data stays intact. This is the standard cloud-native database practice and the foundation of Milvus's horizontal scaling.
In other words, when query pressure rises, just add a few stateless QueryNodes—each pulls data from object storage, reads topology from etcd, consumes the log from MQ, and immediately shares the load;
if a node dies, it holds no exclusive state, so just restart or reload on another machine, <strong>losing no data</strong>. This is the elasticity and reliability bought by "storage-compute separation + external dependencies."</p>

<h2>The three external dependencies</h2>
<p>The layered diagram below lays out the three dependencies, their roles, and typical implementations at once. Note: the upper layer is Milvus's own components (coordinators + nodes); the three blocks below are the <strong>external infrastructure it lives on</strong>:</p>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">App</span><span class="name">Milvus components</span></div><div class="ld">Coordinators (rootcoord/datacoord/querycoord) + nodes (proxy/querynode/datanode/streamingnode)—mostly stateless</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">Dep ①</span><span class="name">etcd · metadata + service discovery</span></div><div class="ld">collection/schema/segment metadata, node registration &amp; health, global config. Strong consistency, watchable.</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">Dep ②</span><span class="name">object storage · MinIO / S3</span></div><div class="ld">binlogs (columnar data), index files, delta logs. Cheap, near-infinite, durable.</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">Dep ③</span><span class="name">message queue / WAL</span></div><div class="ld">rocksmq / Pulsar / Kafka / Woodpecker. An ordered, durable, replayable write log—the carrier of "log as data."</div></div>
</div>

<table class="t">
  <thead><tr><th>External dependency</th><th>Role (capability outsourced)</th><th>Typical implementations / examples</th></tr></thead>
  <tbody>
    <tr><td><strong>etcd</strong></td><td>metadata + service discovery: strongly consistent, watchable</td><td class="mono">etcd (same as K8s)</td></tr>
    <tr><td><strong>object storage</strong></td><td>persist massive immutable data: binlogs, index files, delta logs</td><td class="mono">MinIO / AWS S3 / GCS / Aliyun OSS</td></tr>
    <tr><td><strong>message queue / WAL</strong></td><td>ordered, durable, replayable write log ("log as data")</td><td class="mono">RocksMQ / Pulsar / Kafka / Woodpecker</td></tr>
  </tbody>
</table>

<p>Note one pattern in this table: <strong>the three dependencies map onto three very different storage needs—"small but critical", "large but
cheap", and "ordered and replayable"</strong>—metadata is small yet must be strongly consistent, vector data is large yet write-rarely read-often,
and the write log must be strictly ordered and replayable. Handing each to the mature system best suited to it is the core idea of this
external-dependency design. We unpack them one by one below.</p>

<h3>① etcd — metadata and service discovery</h3>
<p><strong>etcd</strong> is a <strong>strongly consistent distributed key-value store</strong>. Milvus uses it to hold all <strong>metadata</strong>: which collections exist, their schemas, each segment's state and location, index metadata, etc.;
and for <strong>service discovery</strong>—nodes register themselves in etcd on startup, and coordinators learn "which nodes are alive and where" through etcd. Metadata is small but <strong>critically important</strong>, must be strongly consistent and never lost; if metadata is corrupted or lost, the whole cluster "loses its bearings,"
which is exactly etcd's forte (Kubernetes uses it too). Small in size, it is the cluster's "household registry" and "address book." See the <span class="inline">etcd</span> section in <span class="inline">configs/milvus.yaml</span>.</p>

<p>Why pull metadata out separately and insist on strong consistency? Imagine two coordinators changing the same segment's state at once, or two nodes each thinking they're the primary for some role—if the metadata store allowed "reading a stale value,"
the whole cluster would fall into <strong>split-brain and state chaos</strong>. etcd uses the Raft protocol to guarantee "everyone reads the same latest value at any moment," and supports <strong>watch (change notifications)</strong>:
the moment a key changes, components that care are notified instantly. This "strong consistency + watchable" combo is the bedrock for coordinators to schedule globally and nodes to sense topology changes. So although etcd stores little data, it is the <strong>brain of the whole cluster</strong>—once it's unavailable, the cluster can make no metadata changes.</p>

<h3>② Object storage — the home of massive data</h3>
<p>Last lesson's binlogs and index files all end up in <strong>object storage</strong>: <strong>MinIO</strong> for local dev, <strong>S3 / GCS / Aliyun OSS</strong> or any S3-API-compatible service in the cloud.
Object storage is <strong>near-infinite in capacity, extremely low in unit cost, durable and reliable</strong>—perfect for vectors, which are "large in volume, write-few read-many, long-retention" data.
Milvus pushes all "heavy data" here, caching only hot data in memory/local disk. See the <span class="inline">minio</span> section in <span class="inline">milvus.yaml</span> (address, bucket, AK/SK, etc.).</p>

<p>Concretely, three kinds of things live in object storage: <strong>binlogs</strong> (columnar data flushed from sealed segments, one per field), <strong>index files</strong> (ANN indexes like IVF/HNSW built on binlogs),
and <strong>delta logs</strong> (incremental files recording delete marks). All are <strong>immutable</strong>—written once, read many, never modified in place—matching object storage's "write-once read-many" nature perfectly.
At search time QueryNode pulls the needed binlogs and indexes from object storage <strong>on demand into a local cache</strong> (that's <span class="inline">localStorage.path</span> in milvus.yaml), avoiding remote reads every time.
So object storage "stores the full set cheaply" while local disk and memory "read hot spots fast"—a hot/cold tiering with clear division of labor. Worth stressing: precisely because these files are immutable, they can be <strong>safely read by arbitrarily many nodes at once</strong>
and <strong>cached without worrying about invalidation</strong>—again confirming Lesson 7's point that "immutability is a distributed system's best friend." The storage layer's simplicity and reliability largely come from this immutability.</p>

<h3>③ Message queue / WAL — the carrier of the write log</h3>
<p>Lesson 7's "log as data"—that <strong>append-only, replayable log</strong>—is physically carried in a <strong>message queue (MQ)</strong>, i.e., the WAL (write-ahead log).
Milvus supports four MQs: <strong>rocksmq</strong> (a built-in lightweight queue based on RocksDB), <strong>Pulsar</strong>, <strong>Kafka</strong>, and the next-gen built-in WAL <strong>Woodpecker</strong>.
They all provide "ordered, durable, multi-consumer replayable" capability—the physical basis for Growing-segment consumption, crash recovery, and read-write decoupling. From another angle, MQ here isn't a "traditional message middleware" role but Milvus's <strong>write trunk road</strong>—
every write enters MQ first, then is taken on demand by various consumers (segment accumulators, index builders, replica makers), each unaffected by the others' pace. This is exactly why the MQ choice matters so much.</p>

<p>On "which is the default," the comments in <span class="inline">milvus.yaml</span> give the <strong>exact</strong> rules (don't rely on memory): when <span class="inline">mq.type</span> is set to <span class="inline">default</span>,
it auto-selects by the current deployment mode, following the priority below—</p>

<table class="t">
  <thead><tr><th>Deployment mode</th><th>Default MQ</th><th>Priority order</th><th>Note</th></tr></thead>
  <tbody>
    <tr><td><strong>Standalone (single/local)</strong></td><td><strong>RocksMQ</strong></td><td>rocksmq (default) &gt; Pulsar &gt; Kafka &gt; Woodpecker</td><td>Built-in, zero external deps, works out of the box</td></tr>
    <tr><td><strong>Cluster</strong></td><td><strong>Pulsar</strong></td><td>Pulsar (default) &gt; Kafka &gt; Woodpecker</td><td>RocksMQ is <strong>unsupported</strong> in cluster mode</td></tr>
  </tbody>
</table>

<p>Two facts you <strong>must remember</strong>: ① <strong>Standalone defaults to RocksMQ</strong>, because it's built into the process and needs no extra deployment—ideal for single-machine; ② <strong>Cluster defaults to Pulsar</strong>,
and <strong>RocksMQ is unsupported in cluster mode</strong> (it's single-machine built-in and can't be shared across nodes). Also, the comments specifically recommend: <strong>new instances should explicitly use Woodpecker</strong>
for better performance, operational simplicity, and cost efficiency—it's Milvus's flagship next-gen built-in WAL. Valid values for <span class="inline">mq.type</span> are <span class="inline">[default, pulsar, kafka, rocksmq, woodpecker]</span>.</p>

<p>Why design this priority so carefully? Because it has to serve both <strong>"out-of-the-box" and "backward compatibility"</strong>: for single-machine users, the built-in RocksMQ requires deploying nothing extra—install and run;
for cluster users, a single-machine built-in queue like RocksMQ simply can't be shared across nodes, so it must fall back to a true distributed MQ like Pulsar/Kafka. And the reason Woodpecker sits last in priority yet is "strongly recommended for new instances"
is that the priority must keep <strong>existing instances' behavior unchanged on upgrade</strong> (you can't suddenly swap out someone's default queue), but for brand-new deployments the project wants you to actively pick Woodpecker—as the next-gen built-in WAL, it's superior in performance and operating cost.
Understand the "stay compatible with the old, while steering toward the new" trade-off behind this rule, and you understand how a mature system evolves its defaults.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">configs/milvus.yaml</span><span class="ln">priority comments in the mq section</span></div>
  <pre><span class="cm"># Milvus supports four MQs: rocksmq (RocksDB-based), Pulsar, Kafka, Woodpecker.</span>
<span class="cm"># Switch via mq.type; if unset, the following priority applies (multiple MQs configured):</span>
<span class="cm"># 1. standalone (local) mode: rocksmq (default) &gt; Pulsar &gt; Kafka &gt; Woodpecker</span>
<span class="cm"># 2. cluster mode: Pulsar (default) &gt; Kafka (rocksmq unsupported in cluster) &gt; Woodpecker</span>
<span class="cm"># For new instances, explicitly using Woodpecker is recommended for better perf/ops/cost.</span>
mq:
  <span class="cm"># Valid values: [default, pulsar, kafka, rocksmq, woodpecker]</span>
  type: default</pre>
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  Milvus <strong>outsources</strong> the three hardest, most generic jobs: metadata/service-discovery to <strong>etcd</strong>, bulk-data persistence to <strong>object storage</strong>, the write log to a <strong>message queue/WAL</strong>.
  This makes its own nodes nearly <strong>stateless</strong> and elastically scalable. Deployment comes in three tiers—<strong>Lite / Standalone / Cluster</strong>: from a one-line pip in-process library, to a single-process all-in-one, to a K8s cluster where each component scales independently.
  Memorize the MQ defaults: Standalone → RocksMQ, Cluster → Pulsar, new instances → Woodpecker recommended.
</div>

<h2>Three deployment shapes</h2>
<p>The same Milvus can land at three <strong>scales</strong>, matching different use cases. Understand their differences and you'll know when to use which:</p>

<div class="cols">
  <div class="col"><h4>Milvus Lite</h4><p>An <strong>in-process</strong> build installed with <strong>a single pip</strong>, data stored in <strong>local files</strong>, no external deps. Great for <strong>learning, prototyping, laptop experiments</strong>, unit tests. Runs the full API but not designed for large scale/high concurrency.</p></div>
  <div class="col"><h4>Standalone</h4><p>A <strong>single process</strong> packing all components together, MQ defaults to built-in <strong>RocksMQ</strong>, metadata via embedded or local etcd, data via local MinIO. Suited for <strong>small-to-mid production, single-machine</strong>, simple to operate.</p></div>
  <div class="col"><h4>Cluster</h4><p>Components (coordinators + various nodes) <strong>deployed and scaled independently</strong> on <strong>Kubernetes</strong>, MQ defaults to <strong>Pulsar</strong>, relying on external etcd / S3 / Pulsar clusters. For <strong>large-scale, high-concurrency, high-availability</strong> production.</p></div>
</div>

<table class="t">
  <thead><tr><th>Shape</th><th>How it runs</th><th>Dependencies used</th><th>Scale</th><th>When</th></tr></thead>
  <tbody>
    <tr><td><strong>Milvus Lite</strong></td><td>pip-installed <strong>in-process</strong> library, embedded in your Python process</td><td><strong>zero external deps</strong>, data in local files</td><td>up to ~millions · single machine</td><td>learning, prototyping, laptop experiments, unit tests</td></tr>
    <tr><td><strong>Standalone</strong></td><td><strong>single process</strong> packing all components together</td><td>built-in RocksMQ + local MinIO + embedded/local etcd</td><td>tens of millions · single machine</td><td>small-to-mid production, wants simple ops</td></tr>
    <tr><td><strong>Cluster</strong></td><td>each component deployed and scaled independently on <strong>K8s</strong></td><td>external production-grade etcd / S3 / Pulsar</td><td>hundreds of millions+ · high concurrency &amp; HA</td><td>large-scale production, per-component scaling</td></tr>
  </tbody>
</table>

<p>This table lays out the differences at a glance: left to right, <strong>components split further apart, dependencies move more external, the
scale it carries grows, and ops gets heavier</strong>. Lite suits "I want my first vector search running today," Standalone suits "one machine
carries one business line," Cluster suits "hundreds of millions of vectors, shared across teams, no downtime." Crucially they share the same
API and data model, so you needn't pick the final shape up front—<strong>start on Lite/Standalone and migrate to Cluster as scale grows</strong>,
with business code barely changing.</p>

<p>The core difference among the three is a continuum of <strong>"component aggregation" and "dependency externalization"</strong>: Lite crams everything into one process with zero external deps; Standalone is still one process but starts using dependencies like object storage;
Cluster splits every component apart and externalizes every dependency into an independent cluster, buying unbounded horizontal scaling. They share <strong>the same API and data model</strong>, so you can <strong>start with Lite and migrate smoothly to Cluster</strong> with almost no business-code changes.</p>

<p>How to choose? A simple decision intuition: for <strong>learning on a laptop, running demos, writing unit tests</strong>, use <strong>Lite</strong>—one pip, data in local files, your first vector search in minutes;
for <strong>data within tens of millions, single-machine memory/disk that can handle it, no HA needed</strong>, use <strong>Standalone</strong>—one process, lowest operating cost;
for <strong>billions of rows, high concurrency, HA, per-component scaling</strong>, go <strong>Cluster</strong>—on K8s scale proxy, querynode, datanode etc. independently by their own load, with production-grade etcd/object-storage/Pulsar.
Remember this through-line: <strong>the bigger the scale, the more you split components apart and externalize dependencies</strong>; yet at every tier the API and data model stay unchanged—this is what lets Milvus "start small, never sweat big."</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Lite: learning &amp; prototyping</h4><p>pip install, in-process, local files. <strong>Zero external deps</strong>, your first vector search in minutes.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Standalone: small-mid production</h4><p>Single-process all-in-one, RocksMQ + local MinIO/etcd. Simplest ops, for single-machine-is-enough scenarios.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Cluster: large-scale production</h4><p>Components scale on their own on K8s, Pulsar + external etcd/S3. Built for high concurrency, HA, and massive data.</p></div></div>
</div>

<p>Finally, let's tie this whole "Foundations" part together: Lesson 4 covered <strong>embeddings &amp; similarity</strong> (what the data looks like, how to compare), Lesson 5 covered <strong>ANN algorithms</strong> (how to compare fast),
Lesson 6 covered the <strong>data model</strong> (how to organize fields and tables), Lesson 7 covered <strong>segments &amp; log-as-data</strong> (how data is stored and flows internally), and this lesson covered <strong>external dependencies &amp; deployment</strong> (what supports the whole system and in what shape it runs).
With these five foundations, you have all the prerequisites to understand the upcoming Milvus subsystems (write path, query path, indexing, compaction…).</p>

<p>Looking back, these five lessons answer five progressively deeper questions: <strong>"what is a vector and how to compare it" → "how to compare massive vectors fast" → "how to model business data" → "how data is stored and flows inside the engine" → "what external infrastructure the whole engine relies on and at what scale it runs."</strong>
Starting from a numeric vector, all the way to a distributed system that scales elastically on K8s—this through-line is the <strong>map</strong> for understanding Milvus. The parts that follow will dive into each subsystem's internals along this map.
If you've read this far, congratulations—you've laid all the foundations.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Three dependencies</strong>: etcd (metadata + service discovery), object storage (MinIO/S3, holds binlogs and indexes), message queue/WAL (the write log).</li>
    <li><strong>Storage-compute separation</strong>: state settles into external systems; Milvus nodes are nearly stateless and elastically scalable.</li>
    <li><strong>Four MQ options</strong>: rocksmq / Pulsar / Kafka / Woodpecker; Woodpecker is the flagship next-gen built-in WAL.</li>
    <li><strong>MQ defaults</strong>: Standalone → RocksMQ (rocksmq&gt;Pulsar&gt;Kafka&gt;Woodpecker); Cluster → Pulsar (Pulsar&gt;Kafka&gt;Woodpecker; RocksMQ unsupported in cluster).</li>
    <li><strong>Three deployments</strong>: Lite (pip, in-process, local files), Standalone (single process, RocksMQ), Cluster (K8s, Pulsar, components scale independently); same API, upgradeable smoothly.</li>
  </ul>
</div>
""",
}
