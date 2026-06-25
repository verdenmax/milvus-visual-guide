"""Content for Part 8 (C++ core internals). Lessons 34-37.

Bilingual {"zh","en"} dicts mirroring part1-7. Facts verified against
internal/core/src (segcore/index/query/exec/expr/mmap/storage/common) and the
cgo *_c.h bridge.
"""

LESSON_34 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前面我们已经多次撞见"<strong>segcore（C++）</strong>""<strong>exec 引擎</strong>""<strong>mmap 列式分块</strong>"这些名字——它们都住在同一个地方：Milvus 的 <strong>C++ 内核</strong>，源码在 <span class="inline">internal/core/src</span>。
这一部分（第八部分）我们正式推开这扇门，先看一张<strong>布局地图</strong>：内核由哪些子模块组成、各管什么、彼此怎么协作，又是怎么通过 <strong>cgo</strong> 和上层的 Go 衔接起来的。
读懂这张地图，后面三课（mmap、表达式与执行、GPU）你就知道每块拼图嵌在哪儿。
</p>

<p>说句心里话：很多人读到“C++ 内核”就发怵，觉得这一定是“高深劝退”的部分。其实恰恰相反——<strong>你不需要会写一行 C++，也能读懂这一部分</strong>。我们的目标不是教你 C++ 语法，而是带你看清<strong>“这块代码在整个 Milvus 里扮演什么角色、为什么这样设计”</strong>。
就像你不必是汽车工程师，也能理解“发动机负责出力、变速箱负责传动”一样。所以这一课不会贴一大段晦涩的 C++ 源码，而是用<strong>地图、分层图、流程图</strong>把内核的“骨架”画给你看；偶尔提到的文件名（如 <span class="mono">segment_c.h</span>），也只是帮你<strong>按图索骥</strong>，知道“想深究的话该去哪儿翻”。
带着这种“看角色、看设计、不抠语法”的心态往下读，你会发现 Milvus 的 C++ 内核并不神秘，它只是把“算得快”这件事，认认真真地拆成了几块、各司其职。</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把 Milvus 想成一台精密仪器：<strong>Go</strong> 是外壳与操作面板——按钮、网络接口、调度逻辑，负责"<strong>指挥</strong>"；<strong>C++ 内核</strong>是面板下真正干重活的<strong>精密机芯</strong>——
  段内检索、索引构建、距离计算，负责"<strong>玩命算</strong>"。两者之间，<strong>cgo</strong> 就是连接面板与机芯的那组<strong>传动轴</strong>：你在面板上按一下"搜索"，传动轴把指令传进机芯，机芯算完再把结果送回面板。
  各司其职：面板要灵活好用，机芯要快到极致。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：<strong>internal/core/src 按职责切成若干子模块——segcore(段内引擎)、index(索引)、query(查询计划)、exec(向量化执行)、expr(表达式)、mmap(列式分块)、storage(binlog I/O)、common(公共类型)等；Go 通过 cgo(*_c.h)调进来</strong>。
  这套内核服务于两条路径：<strong>查询</strong>（QueryNode 在段内检索）与<strong>索引构建</strong>（worker 把段建成索引）。计算密集的活都在这里，性能也在这里见真章。
</div>

<h2>为什么 Milvus 要有一个 C++ 内核</h2>
<p>第 2 课说过 Milvus 是"Go + C++（+少量 Rust）"。为什么不全用 Go？因为<strong>这两类活的性质截然不同</strong>。<strong>控制面</strong>——协调、调度、RPC、并发管理、状态机——要的是<strong>开发效率与并发表达力</strong>，Go 的 goroutine、垃圾回收、丰富生态正合适。
而<strong>计算面</strong>——在一个段里对几十万条向量算距离、跑过滤、压缩解压——要的是<strong>极致性能与对硬件的精确掌控</strong>：手写 SIMD、精细管理内存布局与缓存、必要时调度 GPU。这些恰是 C++ 的主场，而 Go 的 GC 和运行时在这种<strong>每秒上亿次浮点运算</strong>的热路径上会成为负担。
所以 Milvus 做了一个清晰的切分：<strong>Go 写控制面、C++ 写计算内核</strong>，各扬其长。代价是要跨越 Go↔C++ 的语言边界（这就是 cgo 的活），但换来的是"<strong>既好开发、又跑得飞快</strong>"。</p>

<p>你可能会问：要极致性能，为什么不用 Rust？这其实是个很合理的问题，答案是<strong>历史与生态</strong>。Milvus 起步时，向量检索这个领域的成熟内核库（尤其是 <strong>Knowhere/FAISS</strong> 这一脉）、以及各家 GPU 计算工具链，几乎都是 <strong>C++</strong> 生态——
用 C++ 写内核，能<strong>直接复用</strong>这些现成的高性能积木，而不必从头造轮子。后来 Milvus 也确实引入了<strong>少量 Rust</strong>（第 24 课的 tantivy 全文索引就是 Rust 写的、再用 C++ 封装调用），说明它并不排斥更现代的语言，只是<strong>在哪块用什么，取决于哪块的生态最成熟、迁移成本最低</strong>。
这是一种很务实的工程态度：<strong>语言是工具，不是信仰</strong>。理解了这一点，你就不会纠结"为什么是 C++"，而会去欣赏 Milvus"在每一层用最合适的工具"的选择。</p>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">控制面</span><span class="name">Go（internal/*）</span></div><div class="ld">Proxy/协调器/节点：调度、RPC、并发、状态——要开发效率与并发力</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">桥</span><span class="name">cgo（*_c.h / *_c.cpp）</span></div><div class="ld">Go 与 C++ 之间的 C-ABI 传动轴：指令传进去、结果送回来</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">计算面</span><span class="name">C++ 内核（internal/core/src）</span></div><div class="ld">段内检索、索引、距离计算：要极致性能、贴硬件、可调 GPU</div></div>
</div>

<h2>内核的子模块地图</h2>
<p><span class="inline">internal/core/src</span> 不是一团乱码，而是按<strong>职责</strong>切得很清楚的若干目录。把它们摆成一张表，你就有了通览全局的"<strong>导航图</strong>"——后面无论钻到哪一课，都能在这张图上找到位置：</p>

<p>看这张表时有个小窍门：把子模块按“<strong>从下往上</strong>”的顺序读，理解会更顺。最底层是 <strong>common</strong>（大家都要用的公共类型，像是“通用零件库”）和 <strong>storage</strong>（负责把数据在磁盘 binlog 与内存之间搬进搬出，是“仓库管理员”）；
往上一层是 <strong>mmap</strong>，它把 storage 取来的列数据组织成<strong>可被高效计算的内存布局</strong>（列式分块）；再往上，<strong>expr/exec</strong> 在这些分块上跑过滤与算子、<strong>index</strong> 在候选集上做向量检索；最顶上的 <strong>segcore</strong> 则像“<strong>车间主任</strong>”，把上述这些能力<strong>编排</strong>成一次完整的“段内搜索”，并通过 cgo 对 Go 暴露入口。
也就是说，这张表不只是“有哪些模块”的清单，它还隐含了一条<strong>自底向上的协作链</strong>：公共类型 → 存储搬运 → 内存布局 → 过滤/检索 → 编排出餐。心里装着这条链，你再看后面任何一课，都能立刻定位“它在链条的哪一环、上游给它喂什么、它又把结果交给谁”。</p>

<table class="t">
  <tr><th>子模块</th><th>管什么</th><th>关联课</th></tr>
  <tr><td class="mono"><strong>segcore</strong></td><td>段内搜索引擎、cgo 入口（一个段怎么被搜）</td><td>第 27 课</td></tr>
  <tr><td class="mono"><strong>index</strong></td><td>Knowhere 向量索引的封装 + 标量/全文索引</td><td>第 22、24 课</td></tr>
  <tr><td class="mono"><strong>query</strong></td><td>搜索/检索的查询计划结构</td><td>第 28 课</td></tr>
  <tr><td class="mono"><strong>exec</strong></td><td>向量化执行引擎（物理算子在分块上跑）</td><td>第 28 课</td></tr>
  <tr><td class="mono"><strong>expr</strong></td><td>逻辑表达式树（过滤条件）</td><td>第 28 课</td></tr>
  <tr><td class="mono"><strong>mmap</strong></td><td>列式分块存储、内存映射</td><td>第 35 课</td></tr>
  <tr><td class="mono"><strong>storage</strong></td><td>binlog/payload 的读写序列化</td><td>第 18 课</td></tr>
  <tr><td class="mono"><strong>common</strong></td><td>公共类型与工具（schema、类型定义等）</td><td>贯穿</td></tr>
</table>

<p>除了上面这几个主力，还有 <span class="mono">plan</span>（计划解析）、<span class="mono">bitset</span>（过滤掩码的位运算）、<span class="mono">clustering</span>（聚类压缩相关）等更细的模块。
不必死记，记住一个<strong>分层直觉</strong>就够：<strong>common 是地基</strong>（大家都依赖的类型），<strong>storage/mmap 管"数据怎么放"</strong>，<strong>index 管"怎么建检索结构"</strong>，<strong>expr/exec/query 管"一次查询怎么算"</strong>，
而 <strong>segcore 是把它们缝在一起、对外（对 Go）提供"在一个段里搜/查"的总入口</strong>。一张图在手，纷繁的目录就有了主心骨。</p>

<p>这张地图还藏着一条<strong>依赖的方向</strong>：越往"地基"走的模块（common、storage、mmap）越<strong>不依赖别人、被别人依赖</strong>；越往"上层"走（segcore、query/exec）越<strong>组合调用下层</strong>。
比如一次段内搜索：segcore 拿到请求，先让 expr/exec 在 mmap 提供的列式分块上算出过滤 bitset，再让 index 在候选上做向量检索，期间用到的类型来自 common、原始数据来自 storage 落盘的 binlog——
<strong>一层调一层，方向清晰，几乎不回头</strong>。这种"<strong>单向依赖、分层清楚</strong>"的结构，不是为了好看，而是为了<strong>可维护</strong>：你改 mmap 的内部实现，只要接口不变，上面的 segcore/exec 就不用动；你想给 exec 加一个新算子，也不必担心惊动底层存储。
读一个大型 C++ 工程，<strong>先摸清它的分层与依赖方向</strong>，往往比一头扎进某个文件更高效——这张地图，正是给你这把"先看骨架、再看血肉"的钥匙。</p>

<h2>cgo 桥：Go 与 C++ 怎么握手</h2>
<p>Go 调 C++ 不能直接调，得经过 <strong>cgo</strong> 这道桥。具体做法是：C++ 内核把要暴露给 Go 的能力，包装成一组 <strong>C 风格的接口</strong>——文件名常以 <span class="mono">_c.h</span> / <span class="mono">_c.cpp</span> 结尾（比如第 27 课见过的 <span class="mono">segment_c.h</span>）。
为什么是 C 接口而不是 C++？因为 cgo 只能跨越 <strong>C ABI</strong>（C++ 的类、模板、异常这些没法直接跨语言）。于是 C++ 内部该用类用类、该用模板用模板，但<strong>对外只露出一层薄薄的、扁平的 C 函数</strong>：创建段、灌数据、搜索、释放……
Go 这边则有对应的封装（如第 2、27 课的 <span class="mono">LocalSegment</span>），把"调用 C 函数 + 传指针 + 收结果"这些脏活包好，让上层 Go 代码用起来像调一个普通 Go 对象。这层"<strong>C 接口 + Go 封装</strong>"的设计，让两种语言<strong>各自保持地道</strong>，只在边界处用最朴素的 C 函数对接。</p>

<p>跨语言这道桥<strong>不是免费的</strong>，理解它的代价能帮你看懂很多性能设计。每次 cgo 调用都有<strong>固定开销</strong>（切换栈、参数封送等），而且 Go 的内存和 C++ 的内存<strong>互不认识</strong>——不能让 C++ 长期持有一个 Go 指针，反之亦然。
所以 Milvus 的做法是<strong>"粗粒度调用、数据零拷贝"</strong>：不要一行一个 cgo 调用，而是<strong>把一整次"段内搜索"打包成一次调用</strong>，让 C++ 在里面把成千上万条向量算完再一次性返回；数据则尽量用<strong>共享内存/直接传指针</strong>的方式避免来回拷贝（比如 mmap 的数据，C++ 直接读那块映射内存）。
把"过桥"的次数压到最少、每次过桥搬运的"货"尽量大，是用好 cgo 的关键。这也解释了第 29 课为什么强调"批量搜（大 nq）"更划算——批量越大，单次过桥的固定开销就被摊得越薄。<strong>边界处的设计，往往是性能的隐形战场。</strong></p>

<p>还有一点容易被忽略：cgo 这道桥不仅传<strong>数据</strong>，也传<strong>上下文</strong>。比如一次搜索的 trace 信息（第 27 课提过的链路追踪）、超时控制、以及出错时的错误码，都要顺着这道桥来回带——Go 侧发起调用时把 trace 上下文塞进去，C++ 算完把耗时、命中数等指标带回来，这样一次跨语言的搜索在<strong>可观测性</strong>上才不会“断片”。理解了这点，你就明白为什么内核的 C 接口里，除了“查询”“结果”这些主角，往往还夹着一堆看似不起眼的句柄、缓冲区、状态码——它们正是让两套运行时<strong>协同得既快又可控</strong>的黏合剂。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Go 侧封装</h4><p>如 <span class="mono">LocalSegment.Search</span>：准备好查询、缓冲区、trace。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>过 cgo 调 C 函数</h4><p>调 <span class="mono">segment_c.h</span> 暴露的 C 接口，把指针/参数传进 C++。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>C++ 内核计算</h4><p>segcore 里真正做段内检索（sealed=索引/growing=暴力）。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>结果回传 Go</h4><p>把结果写回缓冲区，Go 侧解析成段的 topK。</p></div></div>
</div>

<h2>两条路径：内核同时服务"查询"和"建索引"</h2>
<p>最后看这套内核被谁用。它主要服务<strong>两条路径</strong>。<strong>查询路径</strong>：QueryNode（Go）加载段后，每次搜索都经 cgo 调进 segcore，由 expr/exec 过滤、index 检索、reduce 收敛出段内 topK（第 27、28、29 课全在这一层发生）。
<strong>索引构建路径</strong>：建索引的 worker（第 21、23 课）也调用 core 里 index 模块的能力，把一个 sealed 段的原始向量交给 Knowhere 建成索引文件。换句话说，<strong>无论"读"还是"建索引"，最重的那部分计算，都落在这同一套 C++ 内核里</strong>。

<p>这两条路径“共用一套内核”，是个很值得玩味的设计。它意味着<strong>关键的数据结构与算法只实现一次</strong>：段的列式布局、距离计算、Knowhere 的索引类型……查询时用它、建索引时也用它，不必维护两套各自为政、还可能算得不一致的代码。
你可以把 C++ 内核想成一座<strong>“中央厨房”</strong>：前台（QueryNode）来点“搜索”这道菜，它按“查询路径”出餐；后厨排程（DataCoord 安排的建索引任务）来下“把这批向量做成索引”的单，它按“索引路径”出餐——<strong>同一套灶具、同一批厨师，只是订单类型不同</strong>。
正因如此，第 8 部分接下来的每一课，其实都在介绍这座厨房里的某件“灶具”：第 35 课的 mmap 是<strong>食材怎么摆放</strong>（数据布局），第 36 课的 expr/exec 是<strong>怎么按菜谱快速烹饪</strong>（向量化执行），第 37 课的 GPU 则是<strong>再加一口猛火灶</strong>（硬件加速）。把它们连起来，你就看懂了 Milvus“快”的底层来源——不是某一个魔法开关，而是<strong>数据布局、执行引擎、硬件加速三者协同</strong>的结果。</p>
这也解释了为什么把它做扎实如此重要：它是 Milvus 性能的"<strong>发动机舱</strong>"——上层 Go 把请求调度过来，真正决定快不快的，是这舱里的活儿。下一课，我们就钻进其中一块——<strong>mmap 与列式分块</strong>，看段的数据在内存里到底长什么样。</p>

<p>把这一课放进全书的脉络：前面七部分，我们大多站在 <strong>Go 控制面</strong>的视角看 Milvus——谁调度谁、数据怎么流、日志怎么写。从这一部分起，我们<strong>换一副眼镜</strong>，钻到 <strong>C++ 计算面</strong>里，看那些"被调度"的重活到底是怎么被高效完成的。
两副眼镜缺一不可：只懂控制面，你会觉得"检索"是个黑盒；只懂计算面，你又不知道这些计算是被谁、在何时、为何触发的。把两者接起来——<strong>Go 决定"做什么、何时做"，C++ 决定"怎么做得最快"，cgo 在中间传话</strong>——你对 Milvus 的理解才真正立体。
所以这一部分虽然偏底层、偏硬核，却是把"宏观架构"和"微观性能"缝合起来的关键一针。带着第 34 课这张地图，接下来我们逐块深入：先看数据怎么放（mmap），再看一次查询怎么算（expr/exec），最后看 GPU 如何再加一档速度。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>Go + C++ 分工</strong>：Go 写控制面(调度/RPC/并发，要开发效率)，C++ 写计算内核(检索/索引/距离，要极致性能贴硬件)；cgo 是两者的桥。</li>
    <li><strong>子模块地图</strong>：<span class="mono">internal/core/src</span> = segcore(段内引擎/cgo 入口) + index + query + exec + expr + mmap + storage + common(+plan/bitset/clustering)。</li>
    <li><strong>cgo 桥</strong>：C++ 对外只露一层 C 接口(<span class="mono">*_c.h</span>，如 segment_c.h，受限于 C ABI)，Go 侧用 <span class="mono">LocalSegment</span> 等封装它。</li>
    <li><strong>两条路径</strong>：内核同时服务"查询"(QueryNode 段内检索)与"索引构建"(worker 建索引)——最重的计算都在这里。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
We've bumped into the names <strong>segcore (C++)</strong>, the <strong>exec engine</strong>, <strong>mmap chunked columns</strong> several times — they all live in
one place: Milvus's <strong>C++ core</strong>, with source under <span class="inline">internal/core/src</span>. This part (Part 8) formally opens that door, starting with a
<strong>layout map</strong>: which submodules the core has, what each owns, how they cooperate, and how it connects to the upper Go via <strong>cgo</strong>. Read this map and the
next three lessons (mmap, expr/exec, GPU) will each have a clear place to slot into.
</p>

<p>A reassuring word up front: many readers tense up at the words "C++ core", expecting something forbiddingly advanced. The opposite is true — <strong>you don't need to write a
single line of C++ to follow this part</strong>. Our goal isn't to teach C++ syntax; it's to make clear <strong>what role this code plays inside Milvus and why it's designed this
way</strong>. Just as you needn't be an automotive engineer to grasp "the engine makes power, the transmission delivers it", this lesson won't dump dense C++ source on you. Instead it
draws the core's <strong>skeleton</strong> with maps, layer diagrams and flows; the occasional filename (like <span class="mono">segment_c.h</span>) is only a <strong>signpost</strong> for
"where to dig if you want more". Read with that "see the role and the design, skip the syntax" mindset and the C++ core stops being mysterious — it's just the job of "computing fast",
carefully split into a few pieces that each do one thing well.</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Picture Milvus as a precision instrument: <strong>Go</strong> is the shell and control panel — buttons, network ports, scheduling logic, doing the "<strong>directing</strong>"; the
  <strong>C++ core</strong> is the <strong>precision movement</strong> beneath that does the heavy lifting — in-segment search, index building, distance math, doing the "<strong>frantic
  computing</strong>". Between them, <strong>cgo</strong> is the <strong>drive shaft</strong> connecting panel and movement: you press "search" on the panel, the shaft carries the command
  into the movement, and the movement returns the result. Each plays to its strength: the panel must be flexible, the movement blazingly fast.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>internal/core/src is cut by responsibility into submodules — segcore (in-segment engine), index, query (query plan), exec (vectorized execution), expr (expression
  tree), mmap (chunked columns), storage (binlog I/O), common (shared types), etc.; Go calls in via cgo (*_c.h)</strong>. The core serves two paths: <strong>query</strong> (QueryNode
  searching in a segment) and <strong>index build</strong> (a worker turning a segment into an index). The compute-heavy work all lives here, and so does the performance.
</div>

<h2>Why Milvus needs a C++ core</h2>
<p>Lesson 2 said Milvus is "Go + C++ (+ a little Rust)". Why not all Go? Because the two kinds of work are fundamentally different. The <strong>control plane</strong> — coordination,
scheduling, RPC, concurrency, state machines — wants <strong>developer velocity and concurrency expressiveness</strong>, where Go's goroutines, GC and rich ecosystem fit. The
<strong>compute plane</strong> — computing distances over hundreds of thousands of vectors in a segment, running filters, (de)compressing — wants <strong>peak performance and precise
control of the hardware</strong>: hand-written SIMD, fine-grained memory layout and cache management, GPU scheduling when needed. These are C++'s home turf, while Go's GC and runtime become
a burden on such <strong>hundreds-of-millions-of-FLOPs-per-second</strong> hot paths. So Milvus made a clean split: <strong>Go writes the control plane, C++ writes the compute core</strong>,
each to its strength. The cost is crossing the Go↔C++ language boundary (that's cgo's job), but the payoff is "<strong>easy to develop, and blazingly fast</strong>".</p>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">control plane</span><span class="name">Go (internal/*)</span></div><div class="ld">Proxy/coordinators/nodes: scheduling, RPC, concurrency, state — wants velocity and concurrency</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">bridge</span><span class="name">cgo (*_c.h / *_c.cpp)</span></div><div class="ld">the C-ABI drive shaft between Go and C++: commands in, results out</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">compute plane</span><span class="name">C++ core (internal/core/src)</span></div><div class="ld">in-segment search, indexing, distance math: wants peak perf, close to hardware, GPU-capable</div></div>
</div>

<h2>The core's submodule map</h2>
<p><span class="inline">internal/core/src</span> isn't a blob but several directories cut clearly by <strong>responsibility</strong>. Laying them out as a table gives you a "<strong>navigation
map</strong>" — wherever you drill in later, you can locate it here:</p>

<table class="t">
  <tr><th>Submodule</th><th>What it owns</th><th>Related lesson</th></tr>
  <tr><td class="mono"><strong>segcore</strong></td><td>in-segment search engine, the cgo entry (how a segment is searched)</td><td>Lesson 27</td></tr>
  <tr><td class="mono"><strong>index</strong></td><td>Knowhere vector-index wrappers + scalar/full-text indexes</td><td>Lessons 22, 24</td></tr>
  <tr><td class="mono"><strong>query</strong></td><td>search/retrieve query-plan structures</td><td>Lesson 28</td></tr>
  <tr><td class="mono"><strong>exec</strong></td><td>vectorized execution engine (physical operators over chunks)</td><td>Lesson 28</td></tr>
  <tr><td class="mono"><strong>expr</strong></td><td>the logical expression tree (filters)</td><td>Lesson 28</td></tr>
  <tr><td class="mono"><strong>mmap</strong></td><td>chunked columnar storage, memory mapping</td><td>Lesson 35</td></tr>
  <tr><td class="mono"><strong>storage</strong></td><td>binlog/payload read-write serialization</td><td>Lesson 18</td></tr>
  <tr><td class="mono"><strong>common</strong></td><td>shared types and utilities (schema, type defs, etc.)</td><td>throughout</td></tr>
</table>

<p>Besides these main ones, there are finer modules like <span class="mono">plan</span> (plan parsing), <span class="mono">bitset</span> (bit ops on filter masks), <span class="mono">clustering</span>
(clustering-compaction related). Don't memorize them; one <strong>layering intuition</strong> is enough: <strong>common is the foundation</strong> (types everyone depends on),
<strong>storage/mmap own "how data is laid out"</strong>, <strong>index owns "how to build retrieval structures"</strong>, <strong>expr/exec/query own "how one query computes"</strong>, and
<strong>segcore stitches them together and exposes (to Go) the single entry for "search/query within a segment"</strong>. Map in hand, the many directories gain a backbone.</p>

<h2>The cgo bridge: how Go and C++ shake hands</h2>
<p>Go can't call C++ directly; it goes through the <strong>cgo</strong> bridge. The way: the C++ core wraps the capabilities it exposes to Go into a set of <strong>C-style interfaces</strong> —
files often ending in <span class="mono">_c.h</span> / <span class="mono">_c.cpp</span> (like the <span class="mono">segment_c.h</span> from Lesson 27). Why C, not C++? Because cgo can only cross the
<strong>C ABI</strong> (C++ classes, templates, exceptions can't cross languages directly). So C++ internally uses classes and templates as it likes, but <strong>exposes only a thin, flat layer of C
functions</strong>: create a segment, load data, search, release… On the Go side there are matching wrappers (like <span class="mono">LocalSegment</span> from Lessons 2, 27) that hide the dirty work of
"call the C function + pass pointers + collect results", so upper Go code uses it like an ordinary Go object. This "<strong>C interface + Go wrapper</strong>" design keeps both languages
<strong>idiomatic</strong>, meeting only at the boundary with plain C functions.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Go-side wrapper</h4><p>e.g. <span class="mono">LocalSegment.Search</span>: prepare the query, buffers, trace.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Call the C function via cgo</h4><p>call the C interface exposed by <span class="mono">segment_c.h</span>, passing pointers/args into C++.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>C++ core computes</h4><p>segcore does the in-segment search (sealed=index / growing=brute force).</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Result back to Go</h4><p>write results into the buffer; the Go side parses them into the segment's topK.</p></div></div>
</div>

<h2>Two paths: the core serves both "query" and "index build"</h2>
<p>Finally, who uses this core. It mainly serves <strong>two paths</strong>. The <strong>query path</strong>: after QueryNode (Go) loads a segment, each search crosses cgo into segcore, where
expr/exec filter, index searches, and reduce converges the segment's topK (Lessons 27, 28, 29 all happen at this layer). The <strong>index-build path</strong>: the index-building worker (Lessons
21, 23) also calls the core's index module to hand a sealed segment's raw vectors to Knowhere to build index files. In other words, <strong>whether "reading" or "index building", the heaviest
computation lands in this same C++ core</strong>. That's why building it solidly matters so much: it is Milvus's "<strong>engine bay</strong>" — the upper Go schedules requests in, but what really
decides speed is the work in this bay. Next lesson, we drill into one block — <strong>mmap and chunked columns</strong> — to see what a segment's data actually looks like in memory.</p>

<p>That the two paths "share one core" is a design worth savoring. It means the <strong>key data structures and algorithms are implemented once</strong>: the segment's columnar layout,
distance math, Knowhere's index types… used at query time and at build time alike, with no second, divergent copy that might compute things inconsistently. Think of the C++ core as a
<strong>central kitchen</strong>: the front desk (QueryNode) orders the "search" dish and it plates via the "query path"; the back-of-house scheduler (an index task from DataCoord) drops a
"turn these vectors into an index" ticket and it plates via the "index path" — <strong>same stoves, same cooks, only the order type differs</strong>. That's why every following lesson in
Part 8 really introduces one "appliance" in this kitchen: Lesson 35's mmap is <strong>how the ingredients are arranged</strong> (data layout), Lesson 36's expr/exec is <strong>how to cook
fast by the recipe</strong> (vectorized execution), and Lesson 37's GPU is <strong>adding a roaring extra burner</strong> (hardware acceleration). Connect them and you see where Milvus's
"fast" really comes from — not one magic switch, but <strong>data layout, execution engine and hardware acceleration working in concert</strong>.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Go + C++ split</strong>: Go writes the control plane (scheduling/RPC/concurrency, wants velocity), C++ writes the compute core (search/index/distance, wants peak perf close to hardware); cgo is the bridge.</li>
    <li><strong>Submodule map</strong>: <span class="mono">internal/core/src</span> = segcore (in-segment engine / cgo entry) + index + query + exec + expr + mmap + storage + common (+plan/bitset/clustering).</li>
    <li><strong>cgo bridge</strong>: C++ exposes only a thin C interface (<span class="mono">*_c.h</span>, e.g. segment_c.h, limited by the C ABI), wrapped on the Go side by <span class="mono">LocalSegment</span> and the like.</li>
    <li><strong>Two paths</strong>: the core serves both "query" (QueryNode in-segment search) and "index build" (worker building indexes) — the heaviest computation is here.</li>
  </ul>
</div>
""",
}

LESSON_35 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课我们拿到了 C++ 内核的整张地图。这一课把镜头推近，钻进其中一块地基——<strong>mmap 子模块</strong>（<span class="inline">internal/core/src/mmap</span>）。它回答一个最朴素却最关键的问题：一个 sealed 段的数据，<strong>在内存里到底长什么样</strong>？答案藏在两个词里——<strong>列式</strong>（按字段组织）与<strong>分块</strong>（chunked）；再加上一招 <strong>mmap</strong>，让一台机器能装下比物理内存还大的数据。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  把一个段想成一座<strong>图书馆</strong>。<strong>按行存</strong>像把每位读者的借阅记录订成一本厚册子——想统计"所有人借过的某一类书"，你得翻遍每本册子里那一栏。<strong>按列存</strong>则像按"书名""作者""日期"分别建卡片柜：要查作者，直接拉开"作者"那一柜，<strong>一抽到底、不碰别的</strong>。
  而 <strong>mmap</strong> 就像图书馆的规矩：书<strong>平时都待在书架上</strong>（磁盘），你只把<strong>正在读的那几页</strong>搬到书桌（内存）；管理员（操作系统）随时按需取书、桌子满了就把久不看的放回架上。于是<strong>书架能放的书，远多于书桌能摊开的书</strong>——这正是"数据大于内存"的秘密。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong>Milvus 把一个段按字段切成"列"，每列再切成若干"块"(chunk)，由 <span class="mono">ChunkedColumn</span> 家族表示；数据可选择用 <span class="mono">mmap</span> 映射进虚拟内存，靠操作系统的页缓存按需调入，从而支撑超过物理内存的数据量</strong>。列式让检索只碰需要的字段，分块让内存可逐块管理，mmap 让冷数据留在磁盘、热数据留在缓存。
</div>

<h2>为什么按列存，而不是按行存</h2>
<p>要理解段的内存布局，先得想清楚一件事：一次向量搜索，<strong>到底要读哪些数据</strong>？答案是——<strong>一个向量字段</strong>（拿来算距离）加上<strong>少数几个标量字段</strong>（拿来做过滤，比如 <span class="mono">age &gt; 30</span>）。一个段可能有几十个字段，但单次查询往往只关心其中两三个。这就决定了"<strong>按列存</strong>"的天然优势：把同一字段的所有值<strong>连续地</strong>摆在一起，查询时只把用到的那几列读进来，<strong>其余字段一个字节都不碰</strong>。</p>
<p>反过来看"<strong>按行存</strong>"：一条记录的所有字段挨在一起，一行接一行。这对"读整条记录"很友好，却对向量检索很不友好——为了取出某一列的全部取值，你得在内存里<strong>跳着读</strong>，每跳一步还顺带把同行里用不上的几十个字段也拽进了 CPU 缓存，白白浪费带宽。而向量检索恰恰是"<strong>对某一列做成千上万次同样的运算</strong>"的典型场景：算距离、比阈值、压缩解压……</p>
<p>列式布局把这件事做到了极致：同一列的数据类型相同、紧挨排列，于是可以<strong>一次加载一大片、用 SIMD 指令并行算</strong>（一条指令同时处理 8 个、16 个浮点数），CPU 缓存命中率也高得多。这就是为什么几乎所有面向分析与检索的系统——从列式数据库到向量库——都不约而同地选择列存。Milvus 的段，正是把每个字段独立成一"列"，交给 <span class="inline">internal/core/src/mmap</span> 下的 <span class="mono">ChunkedColumn</span> 家族来承载。下面这张表把两种布局摆在一起看，差别一目了然。</p>

<p>不妨用一个具体数字感受差距。设想一个段有 100 万行、每行 50 个字段，而一次过滤只需读 1 个标量列。按行存时，为了扫这一列，CPU 要在内存里以"每行一大步"的方式跳 100 万次，每步还把同行另外 49 个字段的数据一并拉进缓存行——真正有用的不到 <strong>1/50</strong>，其余全是被白白搬运又立刻丢弃的"过路数据"。按列存时，这一列的 100 万个值<strong>紧挨成一条</strong>，CPU 顺序扫过、缓存行里装的<strong>全是有用数据</strong>，还能让向量化指令一次吞下一大把。两种布局读的是同样的逻辑数据，物理上的代价却可能差出<strong>一个数量级</strong>。这也是为什么"列式"不是锦上添花的小优化，而是向量检索系统的<strong>地基性选择</strong>——它从根上决定了热路径能跑多快。</p>

<table class="t">
  <tr><th>维度</th><th>按行存（row-oriented）</th><th>按列存（column-oriented，Milvus 段）</th></tr>
  <tr><td>组织方式</td><td>一条记录的所有字段挨在一起，逐行排列</td><td>同一字段的所有取值挨在一起，逐列排列</td></tr>
  <tr><td>取某一列全部值</td><td>跳着读，顺带拽进无关字段（污染缓存）</td><td>连续读一整片，只碰这一列</td></tr>
  <tr><td>向量检索/过滤</td><td>不友好：同一运算要在分散内存上重复</td><td>友好：一大片连续数据 + SIMD 并行</td></tr>
  <tr><td>适合的场景</td><td>OLTP：读写整条记录</td><td>OLAP/向量检索：对少数列做大量同质运算</td></tr>
  <tr><td>Milvus 中的体现</td><td>—</td><td>每个字段一列，由 <span class="mono">ChunkedColumnInterface</span> 表示</td></tr>
</table>

<h2>一列是怎么切成块的：chunked column</h2>
<p>列存解决了"按字段组织"，但还有个现实问题：一个段可能有几十万、上百万行，<strong>一列的数据会很大</strong>。如果硬要把一整列塞进<strong>一块连续内存</strong>，会带来两个麻烦：一是大块连续内存难分配（内存碎片下可能根本找不到这么大一片）；二是 growing 段还在<strong>不断追加</strong>新数据，每来一批就重新分配、整体搬移，代价高得离谱。Milvus 的解法是<strong>分块（chunk）</strong>：把一列切成若干<strong>定长的小块</strong>，一列 = 一串 chunk。</p>
<p>这套抽象的顶层是 <span class="inline">internal/core/src/mmap/ChunkedColumnInterface.h</span> 里的 <span class="mono">ChunkedColumnInterface</span>——一个抽象基类，定义了"一列该提供哪些能力"：<span class="mono">NumChunks()</span>（我有几块）、<span class="mono">NumRows()</span>（一共几行）、按块取数据、按行号定位到"第几块的第几个"等等。具体实现是 <span class="inline">ChunkedColumn.h</span> 里的一个<strong>类族</strong>，按字段类型分工：定长数据（如 int64、float 向量）用 <span class="mono">ChunkedColumn</span>；变长数据（如 varchar、JSON）用 <span class="mono">ChunkedVariableColumn</span>；数组、向量数组则有 <span class="mono">ChunkedArrayColumn</span>、<span class="mono">ChunkedVectorArrayColumn</span>。它们都继承自 <span class="mono">ChunkedColumnBase</span>，共享"分块"的骨架，只在"一个值怎么编码"上各有不同。</p>
<p>每个块里装的就是 <span class="inline">ChunkData.h</span> 定义的 <span class="mono">FixedLengthChunk</span>（定长）或 <span class="mono">VariableLengthChunk</span>（变长）。分块带来的好处很实在：<strong>growing 段追加</strong>时，写满一块就再要一块，老块原地不动、无需搬移；<strong>内存管理</strong>按块进行，分配、释放、甚至换入换出都以块为单位，粒度刚刚好；上层算子遍历一列时，就是"<strong>一块接一块地扫</strong>"，每块内部又是连续内存、对 SIMD 友好。所以你可以把一列想成一列<strong>抽屉柜</strong>：柜子（列）逻辑上是一个整体，但物理上由一格格抽屉（chunk）拼成，要哪行就算出它在第几格、第几个位置。下面这张分层图把"列 → 块 → 块内数据"的关系画出来。</p>

<p>这里还有一个常被忽略却很关键的细节：<strong>定长与变长的处理方式完全不同</strong>。对于定长字段（比如一个 128 维的 float 向量，每行恒占 512 字节），定位第 k 行简单到只是一次乘法——块内偏移 = k × 单行字节数，<strong>直接算出地址、一步取到</strong>。但对于变长字段（比如长短不一的 varchar），就没法"乘一下"得到地址，因为每行长度都不一样。<span class="mono">ChunkedVariableColumn</span> 的做法是<strong>另存一张偏移表</strong>：先记下每个值在数据区里的起止位置，取第 k 个值时<strong>先查偏移表、再按偏移去数据区取那一段</strong>。这就是为什么变长列要单独一个类——它多了"<strong>偏移索引</strong>"这层间接。理解了这点，你就明白 <span class="mono">ChunkedColumn</span> 家族为什么按字段类型分了这么多子类：<strong>不是为了好看，而是因为"一个值怎么编码、怎么定位"这件事，定长和变长、标量和数组本就该用不同策略</strong>。把这层差异交给类族各自处理，上层算子就能用统一的 <span class="mono">ChunkedColumnInterface</span> 接口、不必关心底下究竟是哪种编码——这正是抽象基类的价值所在。</p>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">列</span><span class="name">ChunkedColumnInterface（一个字段在段内的全部取值）</span></div><div class="ld">提供 NumChunks()/NumRows()/按行定位；按类型分 ChunkedColumn(定长) / ChunkedVariableColumn(变长) 等</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">块</span><span class="name">chunk × N（定长小块，一列切成一串）</span></div><div class="ld">growing 追加=写满一块再要一块；内存按块分配/换入换出；块内连续、SIMD 友好</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">块内数据</span><span class="name">FixedLengthChunk / VariableLengthChunk（ChunkData.h）</span></div><div class="ld">定长直接定址；变长另存偏移表，先查偏移再取值</div></div>
</div>

<h2>mmap：让数据大于内存</h2>
<p>现在到了最精彩的一招。段的原始数据，最终是以 <strong>binlog 文件</strong>的形式落在磁盘上的（第 18 课）。当 QueryNode 加载一个段时，有两种把这些列数据放进内存的方式。第一种是老老实实 <span class="mono">read()</span>：把文件内容<strong>整份拷进堆内存</strong>。简单直接，但有个硬上限——<strong>一台机器能加载的数据，被物理内存卡死了</strong>。内存 64GB，就装不下 100GB 的段。</p>
<p>第二种就是 <strong>mmap</strong>：不拷贝，而是把 binlog 文件<strong>映射</strong>进进程的<strong>虚拟地址空间</strong>。映射完成后，这段数据看起来就像一片普通内存，C++ 代码照常按地址访问；但<strong>真正的数据并不立刻进物理内存</strong>。只有当代码第一次访问到某一页时，CPU 触发一次<strong>缺页中断</strong>，操作系统才把那一页从磁盘读进<strong>页缓存</strong>（page cache）。访问过的热页留在缓存里，下次直接命中；久不访问的冷页，在内存吃紧时被操作系统<strong>悄悄换出</strong>。</p>
<p>这一下就打破了"数据必须 ≤ 内存"的枷锁：一个节点可以加载<strong>总量远超物理内存</strong>的段——冷数据安静地躺在磁盘上不占内存，只有真正被查到的热数据才占用页缓存，换入换出全由操作系统这位"老管家"自动打理，Milvus 自己<strong>一行换页逻辑都不用写</strong>。代价当然有：访问冷页要等一次磁盘 I/O（缺页的延迟），所以 mmap 适合<strong>冷热分明、内存放不下全部</strong>的场景，是一种"用一点点延迟换巨大容量"的划算交易。要不要对某个字段启用 mmap，是<strong>可配置</strong>的——cgo 入口 <span class="inline">internal/core/src/segcore/load_field_data_c.h</span> 的 <span class="mono">EnableMmap(...)</span> 就是 Go 侧在加载字段数据时拨动的那个开关。下面用一条流程把"带 mmap 加载并访问一列"走一遍。</p>

<p>值得停下来体会一下这套设计的"<strong>四两拨千斤</strong>"：mmap 之所以优雅，是因为它把"<strong>什么数据该在内存、什么该在磁盘</strong>"这个极难的决策，整个<strong>外包给了操作系统</strong>。操作系统几十年来在页缓存、预读、换出算法上的积累，比任何应用自己写一套缓存都更成熟、更省心。Milvus 只需说一句"把这个文件映射进来"，剩下的冷热判断、换入换出、内存压力下的取舍，全由内核按全局视角自动完成。这也解释了一个实践要点：mmap 模式下，<strong>第一次查询某个冷段往往偏慢</strong>（要把页从磁盘缺页调进来），而<strong>反复查询的热段则几乎和纯内存一样快</strong>（页都在缓存里）——这就是所谓的"<strong>预热</strong>"现象。对运维而言，这意味着可以用<strong>较小的内存</strong>扛住<strong>大得多的数据集</strong>，代价是接受冷数据首次访问的延迟抖动；要不要这笔交易，取决于数据的冷热分布与延迟要求。回到第 34 课说的"中央厨房"：mmap 就像厨房不必把所有食材都堆在操作台上，而是大部分放冷库（磁盘）、要用时才取到台面（页缓存）——台面虽小，能做的菜却不受台面大小的限制。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>加载字段（EnableMmap）</h4><p>Go 经 cgo 调 <span class="mono">load_field_data_c.h</span>，对该字段开启 mmap，而非整份读进堆。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>映射 binlog 文件</h4><p>把磁盘上的列数据 <span class="mono">mmap</span> 进虚拟地址空间——此刻并不占物理内存。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>按需缺页调入</h4><p>算子访问到某 chunk 的某一页时触发缺页，OS 把该页读入<strong>页缓存</strong>。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>冷页自动换出</h4><p>内存吃紧时，久未访问的冷页被 OS 换出；热页常驻。数据总量可远超内存。</p></div></div>
</div>

<h2>谁来分配这些内存：MmapChunkManager</h2>
<p>最后补一块拼图：这些 mmap 出来的内存块，<strong>谁在统一调度</strong>？答案是 <span class="inline">internal/core/src/storage/MmapChunkManager.h</span> 里的 <span class="mono">MmapChunkManager</span>。它像一位"<strong>仓库总管</strong>"，向上层提供 <span class="mono">Allocate(...)</span> 申请一块 mmap 背书的内存来安放 chunk；底下由 <span class="mono">MmapBlocksHandler</span> 按需切出<strong>定长小块</strong>（<span class="mono">AllocateFixSizeBlock()</span>）或<strong>大块</strong>（<span class="mono">AllocateLargeBlock(size)</span>），并用一个 <span class="mono">BlockType</span> 区分两类用途。</p>
<p>把它独立成一个"总管"，好处是<strong>集中管控</strong>：所有走 mmap 的内存都从这一个口子出，方便统一限额、统计用量、按块回收，避免到处各自 mmap 导致难以追踪。再往上一点还有一层<strong>缓存层</strong>（cachinglayer）与 <span class="mono">PinWrapper</span> 的设计：当某个 chunk 正被一次计算使用时，会被"<strong>钉住</strong>"（pin）在缓存里，保证它不会在算到一半时被换出；算完再松开，让它重新成为可被换出的普通冷页。这一钉一松，正是"<strong>既要省内存、又要保证正在用的数据不丢</strong>"的精细平衡。把这些串起来，你就看清了一个段的数据在内存里的全貌：<strong>按列组织、逐块切分、可选 mmap、由 MmapChunkManager 统一分配、用缓存与 pin 守护热数据</strong>。下一课（第 36 课）我们就让 expr/exec 引擎在这些列式分块上真正跑起来——看一次查询是怎么"算"出来的。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>列式</strong>：段按字段切成列，检索只碰需要的几列、连续读、SIMD 友好；对照按行存的"跳读 + 缓存污染"。</li>
    <li><strong>分块</strong>：一列 = 一串定长 chunk，由 <span class="mono">ChunkedColumnInterface</span> 抽象、<span class="mono">ChunkedColumn</span>/<span class="mono">ChunkedVariableColumn</span> 等实现；利于 growing 追加与按块内存管理。</li>
    <li><strong>mmap</strong>：把 binlog 映射进虚拟内存、按需缺页、冷页换出，让一个节点装下<strong>大于物理内存</strong>的数据；代价是冷访问的磁盘延迟，按字段经 <span class="mono">EnableMmap</span> 配置。</li>
    <li><strong>统一分配</strong>：<span class="mono">MmapChunkManager</span> 集中分配 mmap 内存块；cachinglayer 的 <span class="mono">PinWrapper</span> 在计算期间钉住热 chunk 防止被换出。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson handed us the whole map of the C++ core. Now we zoom into one piece of the foundation — the <strong>mmap submodule</strong> (<span class="inline">internal/core/src/mmap</span>). It answers a plain but crucial question: what does a sealed segment's data <strong>actually look like in memory</strong>? The answer lives in two words — <strong>columnar</strong> (organized by field) and <strong>chunked</strong> — plus one trick, <strong>mmap</strong>, that lets one machine hold more data than physical RAM.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Picture a segment as a <strong>library</strong>. <strong>Row storage</strong> is like binding each reader's borrowing record into a thick booklet — to tally "everyone who borrowed a certain genre" you must flip through every booklet's one column. <strong>Column storage</strong> instead files cards by "title", "author", "date": to query authors you pull open the "author" drawer and <strong>scan it end to end, touching nothing else</strong>.
  And <strong>mmap</strong> is the library's rule: books <strong>stay on the shelves</strong> (disk); you only carry <strong>the few pages you're reading</strong> to your desk (RAM); the librarian (the OS) fetches on demand and reshelves what's long unused when the desk fills up. So <strong>the shelves hold far more than the desk can spread out</strong> — exactly the secret of "data larger than memory".
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>Milvus cuts a segment by field into "columns", cuts each column into fixed-size "chunks", represented by the <span class="mono">ChunkedColumn</span> family; data can be <span class="mono">mmap</span>'d into virtual memory and paged in on demand by the OS page cache, supporting more data than physical RAM</strong>. Columnar means a search touches only the fields it needs; chunking means memory is managed block by block; mmap keeps cold data on disk and hot data in cache.
</div>

<h2>Why columnar, not row-oriented</h2>
<p>To understand a segment's memory layout, first ask: what does one vector search actually read? The answer — <strong>one vector field</strong> (to compute distance) plus <strong>a few scalar fields</strong> (to filter, e.g. <span class="mono">age &gt; 30</span>). A segment may have dozens of fields, but a single query usually cares about two or three. That dictates the natural advantage of <strong>column storage</strong>: lay all values of one field <strong>contiguously</strong> together, read only the columns you use, and <strong>never touch a byte of the rest</strong>.</p>
<p>Contrast <strong>row storage</strong>: a record's fields sit together, row after row. Great for "read a whole record", but bad for vector search — to pull out one column's values you must <strong>stride through memory</strong>, and each step drags dozens of unused same-row fields into the CPU cache, wasting bandwidth. Yet vector search is the textbook case of "<strong>do the same operation thousands of times over one column</strong>": compute distance, compare thresholds, (de)compress…</p>
<p>Columnar layout takes this to the limit: a column's values share one type and sit adjacent, so you can <strong>load a big slab at once and compute with SIMD</strong> (one instruction over 8 or 16 floats), with far better cache hit rates. That's why nearly every analytics- and search-oriented system — from columnar databases to vector stores — converges on column storage. A Milvus segment makes each field its own "column", carried by the <span class="mono">ChunkedColumn</span> family under <span class="inline">internal/core/src/mmap</span>. The table below puts the two layouts side by side.</p>

<table class="t">
  <tr><th>Dimension</th><th>Row-oriented</th><th>Column-oriented (Milvus segment)</th></tr>
  <tr><td>Organization</td><td>all fields of one record together, row by row</td><td>all values of one field together, column by column</td></tr>
  <tr><td>Read one column</td><td>stride-read, dragging in unrelated fields (cache pollution)</td><td>read one contiguous slab, touch only this column</td></tr>
  <tr><td>Vector search/filter</td><td>unfriendly: same op repeated over scattered memory</td><td>friendly: one big slab + SIMD parallelism</td></tr>
  <tr><td>Best fit</td><td>OLTP: read/write whole records</td><td>OLAP/vector search: heavy homogeneous ops on few columns</td></tr>
  <tr><td>In Milvus</td><td>—</td><td>each field a column via <span class="mono">ChunkedColumnInterface</span></td></tr>
</table>

<h2>How a column is cut into chunks</h2>
<p>Columnar solves "organize by field", but a practical problem remains: a segment may have hundreds of thousands or millions of rows, so <strong>one column's data is large</strong>. Forcing a whole column into <strong>one contiguous block</strong> brings two troubles: large contiguous allocations are hard (fragmentation may mean no such slab exists); and a growing segment keeps <strong>appending</strong>, so reallocating and copying the whole thing per batch is absurdly costly. Milvus's fix is <strong>chunking</strong>: cut a column into several <strong>fixed-size small blocks</strong>; a column = a list of chunks.</p>
<p>The top of this abstraction is <span class="mono">ChunkedColumnInterface</span> in <span class="inline">internal/core/src/mmap/ChunkedColumnInterface.h</span> — an abstract base defining "what a column must offer": <span class="mono">NumChunks()</span> (how many blocks), <span class="mono">NumRows()</span> (how many rows), fetch-by-chunk, locate a row to "which chunk, which offset", and so on. The concrete implementations form a <strong>class family</strong> in <span class="inline">ChunkedColumn.h</span>, split by field type: fixed-width data (int64, float vectors) use <span class="mono">ChunkedColumn</span>; variable-length data (varchar, JSON) use <span class="mono">ChunkedVariableColumn</span>; arrays and vector-arrays have <span class="mono">ChunkedArrayColumn</span> and <span class="mono">ChunkedVectorArrayColumn</span>. All inherit <span class="mono">ChunkedColumnBase</span>, sharing the "chunking" skeleton and differing only in "how one value is encoded".</p>
<p>Each block holds a <span class="mono">FixedLengthChunk</span> (fixed) or <span class="mono">VariableLengthChunk</span> (variable) defined in <span class="inline">ChunkData.h</span>. The payoff is concrete: on <strong>growing-segment append</strong>, fill one block then ask for another — old blocks stay put, no copying; <strong>memory management</strong> is per block, so allocation, freeing, even swap-in/out happen at just-right granularity; and an operator scanning a column simply "<strong>walks block after block</strong>", each block being contiguous and SIMD-friendly. Think of a column as a <strong>chest of drawers</strong>: logically one unit (the column), physically assembled from drawers (chunks); for any row you compute which drawer and which slot. The layered diagram shows "column → chunk → in-chunk data".</p>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">column</span><span class="name">ChunkedColumnInterface (all values of one field in the segment)</span></div><div class="ld">offers NumChunks()/NumRows()/locate-by-row; by type: ChunkedColumn(fixed) / ChunkedVariableColumn(variable)</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">chunk</span><span class="name">chunk × N (fixed-size blocks; a column cut into a list)</span></div><div class="ld">growing append = fill one, ask another; memory per-block alloc/swap; in-block contiguous, SIMD-friendly</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">in-chunk</span><span class="name">FixedLengthChunk / VariableLengthChunk (ChunkData.h)</span></div><div class="ld">fixed = direct addressing; variable = an offset table, look up offset then fetch</div></div>
</div>

<h2>mmap: data larger than memory</h2>
<p>Now the best trick. A segment's raw data ultimately lands on disk as <strong>binlog files</strong> (Lesson 18). When a QueryNode loads a segment, there are two ways to bring these columns into memory. The first is a plain <span class="mono">read()</span>: copy the file contents <strong>wholesale into heap</strong>. Simple and direct, but with a hard ceiling — <strong>the data a machine can load is capped by physical RAM</strong>. With 64GB you can't hold a 100GB segment.</p>
<p>The second is <strong>mmap</strong>: don't copy; <strong>map</strong> the binlog file into the process's <strong>virtual address space</strong>. Once mapped, the data looks like ordinary memory and C++ accesses it by address as usual — but <strong>the real data isn't in physical RAM yet</strong>. Only when code first touches a page does the CPU raise a <strong>page fault</strong>, and the OS reads that page from disk into the <strong>page cache</strong>. Hot pages already touched stay cached and hit next time; cold pages long untouched get <strong>quietly evicted</strong> when memory is tight.</p>
<p>This breaks the "data must be ≤ RAM" shackle: a node can load segments whose <strong>total far exceeds physical RAM</strong> — cold data rests on disk taking no memory, only the hot data actually queried occupies page cache, and all swap-in/out is handled automatically by the OS, that seasoned housekeeper, with Milvus writing <strong>not one line of paging logic</strong>. The cost, of course: touching a cold page waits one disk I/O (page-fault latency), so mmap suits <strong>clearly hot/cold, doesn't-fit-in-RAM</strong> workloads — a shrewd trade of "a little latency for huge capacity". Whether to mmap a given field is <strong>configurable</strong> — the cgo entry <span class="mono">EnableMmap(...)</span> in <span class="inline">internal/core/src/segcore/load_field_data_c.h</span> is the switch the Go side flips when loading field data. The flow below walks "load a column with mmap and access it".</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Load field (EnableMmap)</h4><p>Go calls <span class="mono">load_field_data_c.h</span> via cgo, enabling mmap for the field rather than reading it wholesale into heap.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Map the binlog file</h4><p><span class="mono">mmap</span> the on-disk column data into virtual address space — occupying no physical RAM yet.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Fault in on demand</h4><p>When an operator touches a page of some chunk, a page fault makes the OS read that page into the <strong>page cache</strong>.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Evict cold pages</h4><p>Under memory pressure the OS evicts long-unused cold pages; hot pages stay resident. Total data can far exceed RAM.</p></div></div>
</div>

<h2>Who allocates this memory: MmapChunkManager</h2>
<p>One last piece: who centrally schedules these mmap'd blocks? It's <span class="mono">MmapChunkManager</span> in <span class="inline">internal/core/src/storage/MmapChunkManager.h</span>. Like a <strong>warehouse master</strong>, it offers <span class="mono">Allocate(...)</span> to request an mmap-backed block to place a chunk; underneath, <span class="mono">MmapBlocksHandler</span> carves out <strong>fixed-size blocks</strong> (<span class="mono">AllocateFixSizeBlock()</span>) or <strong>large blocks</strong> (<span class="mono">AllocateLargeBlock(size)</span>), distinguishing the two via a <span class="mono">BlockType</span>.</p>
<p>Making it a single "master" buys <strong>central control</strong>: all mmap memory exits through one door, easing global quotas, usage accounting, and per-block reclamation, avoiding scattered mmaps that are hard to track. One layer up sits a <strong>caching layer</strong> (cachinglayer) with a <span class="mono">PinWrapper</span> design: while a chunk is in use by a computation it is <strong>pinned</strong> in cache so it can't be evicted mid-calculation; once done it's released back to being an ordinary, evictable cold page. This pin-and-release is the fine balance of "<strong>save memory, yet never lose the data being used</strong>". Tie it together and you see a segment's full memory picture: <strong>organized by column, sliced into chunks, optionally mmap'd, allocated centrally by MmapChunkManager, with hot data guarded by the cache and pinning</strong>. Next (Lesson 36) we let the expr/exec engine actually run over these columnar chunks — seeing how a query is "computed".</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Columnar</strong>: a segment is cut by field into columns; search touches only the needed columns, reads contiguously, SIMD-friendly — versus row storage's "stride-read + cache pollution".</li>
    <li><strong>Chunked</strong>: a column = a list of fixed-size chunks, abstracted by <span class="mono">ChunkedColumnInterface</span> and implemented by <span class="mono">ChunkedColumn</span>/<span class="mono">ChunkedVariableColumn</span> etc.; eases growing append and per-block memory management.</li>
    <li><strong>mmap</strong>: map binlog into virtual memory, fault in on demand, evict cold pages — letting a node hold data <strong>larger than physical RAM</strong>; the cost is cold-access disk latency, configured per field via <span class="mono">EnableMmap</span>.</li>
    <li><strong>Central allocation</strong>: <span class="mono">MmapChunkManager</span> allocates mmap blocks centrally; the cachinglayer's <span class="mono">PinWrapper</span> pins hot chunks during computation to prevent eviction.</li>
  </ul>
</div>
""",
}
