"""Part 6 - The query path (查询链路). Lessons 25-30.

Read-path counterpart to Part 4: trace a search from the SDK through the Proxy,
into the QueryNode/delegator, down to the C++ segcore, and back through reduce.

M6a = L25-L27 (this batch). M6b = L28-L30 (later dispatch).
"""

LESSON_25 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
第四部分我们把<strong>写入</strong>的一生走完了：数据从 SDK 经 Proxy、写进 WAL、落成段、建好索引。从这一课起，我们走<strong>另一条路</strong>——<strong>查询链路</strong>：一次 <span class="inline">search</span> 是怎么从 SDK 出发、被 Proxy 翻译与调度、扇出到各个分片、最后归并出 topK 返回的。
这一部分是写入链路的"<strong>镜像</strong>"，并且会一路下钻到 C++ 的 <strong>segcore</strong>（第 27 课）。本课先站在<strong>入口</strong>看：<strong>Proxy 这一侧</strong>到底为一次搜索做了哪些事。把入口这一层吃透，你就有了一张"<strong>读路径全景的目录</strong>"——后面每一课（delegator、segcore、执行引擎、reduce、一致性）都是在补全本课提到的某一个环节。
</p>

<div class="card analogy">
  <div class="tag">📚 生活类比</div>
  你走进一家<strong>连锁图书馆的总服务台</strong>，说："帮我找几本和这本书最像的。"总台职员（<strong>Proxy</strong>）要依次做五件事：
  <strong>① 听懂需求</strong>——按什么标准"像"（度量）、要几本（topK）、有没有附加条件（"只要 2020 年后出版的"=标量过滤）；
  <strong>② 写成标准检索单</strong>——把口头需求翻译成一张分馆都看得懂的表格（search plan）；
  <strong>③ 定一个时间快照</strong>——你要"<strong>绝对最新</strong>"（连刚还回、还没上架的也得算）还是"<strong>稍旧但更快</strong>"？这就是一致性级别决定的 <strong>guarantee 时间戳</strong>；
  <strong>④ 把检索单分发给各分馆</strong>（shard / delegator），各分馆各自找出自己最像的几本（scatter）；
  <strong>⑤ 汇总排序</strong>——把所有分馆交回的候选合在一起、排序、取最像的前几本给你（reduce）。
  总台自己<strong>不翻书架</strong>，它只负责"<strong>听懂、翻译、定快照、分发、归并</strong>"。这正是 Proxy 在一次搜索里的角色。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一次 <span class="inline">search</span> 在 Proxy 侧被封装成一个 <strong>searchTask</strong>（<span class="mono">internal/proxy/task_search.go</span>），走 <strong>PreExecute → Execute → PostExecute</strong> 三段式：<strong>PreExecute</strong> 校验并解析请求、把布尔过滤表达式编译成<strong>检索计划</strong>（plan：向量字段 + 度量 + topK + 标量过滤）、并由<strong>一致性级别</strong>推出 <strong>guarantee 时间戳</strong>（<span class="inline">parseGuaranteeTsFromConsistency</span>，<span class="mono">internal/proxy/util.go</span>）；<strong>Execute</strong> 把请求<strong>扇出（scatter）</strong>到该 collection 的各个分片（vchannel 的 <strong>delegator</strong>）；<strong>PostExecute</strong> 把各分片回来的结果<strong>跨分片归并（reduce）</strong>成最终 topK。Proxy 只做"<strong>翻译 + 调度 + 归并</strong>"，真正搜段的活在 QueryNode（第 26 课）和 segcore（第 27 课）。
</div>

<p>开讲之前，先把和写路径的"<strong>镜像</strong>"关系看具体。<strong>写</strong>的时候，Proxy 把一批行按 vchannel 切开、追加进 WAL——这是一次"<strong>会写入的扇出</strong>"；<strong>读</strong>的时候，Proxy 把同一个查询发往每个分片、再把回来的结果归并——这是一次"<strong>会收集的扇出</strong>"。两者都绕着第 3 课就埋下的同一对概念转：<strong>按 vchannel 分片</strong>（决定打哪些分片）与<strong>时间戳</strong>（写入给数据盖戳、读取携带 guarantee ts）。如果你还记得第四部分的写路径，其实已经掌握了读路径的<strong>骨架形状</strong>——这一部分只是往里填读路径特有的几个"器官"：plan、delegator、segcore、reduce、一致性。</p>

<h2>一次搜索在 Proxy 侧的五步</h2>
<p>把总台职员那五件事落到代码上，就是 <span class="mono">searchTask</span> 的主干流程。下面这条竖流把它一步步摆开：</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>解析请求（parse）</h4><p>从 <span class="inline">SearchRequest</span> 取出：要搜的 collection / 分区、向量字段、<strong>topK</strong>、<strong>度量类型</strong>（L2/IP/COSINE）、查询向量（placeholder group）、布尔<strong>过滤表达式</strong>（如 <span class="mono">year &gt; 2020</span>）、以及<strong>一致性级别</strong>。在 <span class="inline">PreExecute</span> 里完成校验与字段解析。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>构建检索计划（plan）</h4><p>把过滤表达式<strong>编译成 <span class="inline">planpb.PlanNode</span></strong>：一棵带<strong>向量 ANN 节点</strong>（字段 + 度量 + topK）和<strong>标量谓词子树</strong>的计划树。这张"检索单"会随请求一起发给分片，下钻到 segcore 时被执行（第 28 课详述执行引擎）。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>定 guarantee 时间戳</h4><p>按<strong>一致性级别</strong>调用 <span class="inline">parseGuaranteeTsFromConsistency</span> 算出本次读要求的"<strong>时间快照</strong>"：Strong→看到最新、Eventually→只要够快、Bounded→容忍一点延迟。这个 ts 决定 QueryNode 要"<strong>等数据追到多新</strong>"才回答（第 30 课 MVCC 详解）。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>扇出到分片（scatter）</h4><p>一个 collection 的数据按 <strong>vchannel</strong> 分成多个<strong>分片</strong>，每个分片由一个 <strong>delegator（shard leader）</strong>负责。<span class="inline">Execute</span> 通过负载均衡策略，把"检索单 + guarantee ts"并发发往各分片的 delegator（<span class="inline">searchShard</span>）。</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>跨分片归并（reduce）</h4><p>各分片各自返回"<strong>自己最像的 topK</strong>"。<span class="inline">PostExecute</span> 把这些<strong>局部 topK</strong> 汇总、<strong>按距离重排、按主键去重</strong>，取出<strong>全局 topK</strong> 返回 SDK。这层跨分片归并的细节留到第 29 课。</p></div></div>
</div>

<p>这五步里，第 1 步的"<strong>度量</strong>"值得回头多看一眼。回忆第 4、22 课：向量的"像"由度量定义（<strong>L2</strong> 越小越像、<strong>IP/COSINE</strong> 越大/越一致越像），而且<strong>检索用的度量必须和建索引、和字段声明时一致</strong>。Proxy 在解析请求时会拿到本次检索指定的度量，并校验它和字段/索引是否对得上——这道关卡看似不起眼，却挡掉了向量检索里最隐蔽的一类错误（度量用错会让结果"<strong>系统性地不对、却不报错</strong>"）。所以你可以把 Proxy 的"解析"理解成不只是"<strong>读出参数</strong>"，还包含一层"<strong>合法性与一致性的守门</strong>"：字段存不存在、向量维度对不对、度量配不配、topK 是否超限、表达式能不能编译——任一不合法，请求会在<strong>还没扇出之前</strong>就被挡回 SDK，而不是浪费一整轮分布式检索。</p>

<p>把这五步连起来看，Proxy 的角色就非常清楚了：它是一个"<strong>翻译官 + 调度员 + 收银台</strong>"。翻译（把人话的过滤条件编成计划树）、调度（决定打哪些分片、带什么时间快照）、收银（把零散结果汇成一份答案）——<strong>三件事都不碰真正的向量数据</strong>。这与第 10 课讲 Proxy "无状态网关、扇出归并"的定位完全一致；search 只是把那张"扇出—归并"的图，落到了<strong>读路径</strong>上。</p>

<p>再多说一句第 2 步的<strong>检索计划</strong>，因为它是写路径里完全没有、读路径独有的一环。SDK 发来的过滤条件是一串<strong>字符串表达式</strong>（如 <span class="mono">color == "red" &amp;&amp; year &gt; 2020</span>），人能读、机器不能直接执行。Proxy 把它<strong>解析成一棵表达式树</strong>，再和"向量 ANN 检索"这件主任务拼成一个完整的 <span class="inline">planpb.PlanNode</span>：顶层是一个<strong>向量检索节点</strong>（指明在哪个向量字段上、用什么度量、取多少 topK），它下面挂着<strong>标量谓词子树</strong>（把 <span class="mono">color/year</span> 这些条件编成可被高效执行的判断）。这张计划随请求<strong>原样下发</strong>到每个分片、每个段，最终在 C++ 的执行引擎里被跑起来——"<strong>先按谓词把候选行筛小，再在筛后的子集上做 ANN</strong>"（这套"先筛后搜"的执行细节是第 28 课的主题）。Proxy 这一步只负责<strong>把计划编出来</strong>，不负责执行它。</p>

<p>还有一个值得点名的细节：一次 search 请求里<strong>可以同时带多个查询向量</strong>——这叫 <strong>nq</strong>（number of queries，查询向量个数），它们装在一个 <span class="inline">placeholder group</span> 里。<span class="mono">searchTask</span> 在 <span class="inline">checkNq</span> 这一步校验它的大小。nq 的意义是"<strong>一次往返、批量问 N 个相似检索</strong>"：每个查询向量各自要它自己的 topK，扇出到分片后由 segcore 对每个查询向量分别算、分别取 topK，归并时也按查询向量<strong>分组</strong>各归各的。理解 nq 你才不会把"topK=10"和"nq=5"混为一谈——前者是"每个问题要几个答案"，后者是"一次问几个问题"，最终结果是 <strong>nq × topK</strong> 这么一张表。</p>

<h2>Proxy 在搜索里"做什么"与"不做什么"</h2>
<p>初学最容易把 Proxy 想成"搜索引擎本体"。恰恰相反——它是一个<strong>无状态的协调层</strong>，手里既没有向量数据、也没有索引。把它的"<strong>职责边界</strong>"摆清楚，整条查询链路就不会在脑子里错位：</p>

<div class="cols">
  <div class="col"><h4>✅ Proxy 负责</h4><p>校验与鉴权、把过滤表达式<strong>编译成 plan</strong>、按一致性级别<strong>算 guarantee ts</strong>、做<strong>负载均衡</strong>挑 QueryNode、把请求<strong>扇出</strong>到各分片、把各分片结果<strong>跨分片归并</strong>成最终 topK、按 offset/limit 截断后返回 SDK。一句话：<strong>翻译、调度、归并</strong>。</p></div>
  <div class="col"><h4>❌ Proxy 不负责</h4><p>不持有向量数据、不持有索引、<strong>不在自己进程里算距离</strong>；不决定"某段数据归哪个 QueryNode"（那是 QueryCoord 的事，第 13 课）；不执行 plan（plan 下钻到 segcore 才执行，第 28 课）；不等数据追新（"等到 guarantee ts"发生在 QueryNode，第 30 课）。</p></div>
</div>

<p>这条边界为什么重要？因为它正是 Milvus "<strong>计算与协调分离</strong>"的体现：Proxy 可以<strong>无状态地水平扩容</strong>（多开几个都行、挂一个也不丢数据），因为它<strong>什么都不存</strong>；真正昂贵的"<strong>持有索引、在内存里算向量距离</strong>"的活，被推给了能<strong>按段水平扩展</strong>的 QueryNode。把"<strong>谁存数据、谁算距离、谁只协调</strong>"这三件事分开，是读懂后面第 26、27 课的前提——也是几乎所有分布式检索系统共有的设计取向：让协调层轻、让计算层重，各自独立伸缩。</p>

<h2>数据怎么流：从 SDK 到结果</h2>
<p>换一个角度，用一条横向的数据流把"谁把请求交给谁"画清楚。注意中间高亮的那一格，就是本课的主角 <span class="inline">searchTask</span>：</p>

<div class="flow">
  <div class="node"><div class="nt">SDK</div><div class="nd">Search RPC<br>向量+topK+expr</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">Proxy · searchTask</div><div class="nd">解析→plan→guarantee-ts</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">delegator A</div><div class="nd">分片 1 局部 topK</div></div>
  <div class="arrow">＋</div>
  <div class="node"><div class="nt">delegator B</div><div class="nd">分片 2 局部 topK</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">reduce</div><div class="nd">归并出全局 topK</div></div>
</div>

<p>这条流里有两个"<strong>一对多</strong>"的扩散点，是理解分布式检索的关键。第一个在 <strong>Proxy → delegator</strong>：一个 collection 被切成多个分片，请求要<strong>同时</strong>打到每个分片（scatter）。第二个在每个 delegator 内部：它还要把搜索继续扇到自己管的多个段与多个 worker QueryNode 上（这是第 26 课的内容）。
所以一次 search 是<strong>两层扇出</strong>：Proxy 扇到分片、分片再扇到段。对应地，归并也是<strong>分层</strong>的：段内取 topK、节点内合并、Proxy 跨分片再合并——这"<strong>三级 reduce</strong>"留到第 29 课系统讲。本课你只要记住<strong>最外层</strong>这一对：Proxy 扇出、Proxy 归并。</p>

<p>为什么扇出要<strong>并发</strong>、而不是一个分片一个分片地问？因为一次搜索的延迟，取决于<strong>最慢的那个分片</strong>，而不是所有分片之和。若串行去问 N 个分片，总延迟≈N×单分片延迟；并发扇出后，总延迟≈单分片延迟＋一点点归并开销。这正是分布式检索"<strong>用并行换低延迟</strong>"的根本手法：把一个大问题<strong>切成互不依赖的小问题</strong>同时算，再把答案拼起来。也正因为各分片<strong>互不依赖</strong>（每个分片只看自己那部分数据），扇出才能放心地并发——这种"<strong>数据分片 + 无共享并行</strong>"的结构，是 Milvus 能横向扩展读吞吐的根本原因：分片越多、每片越小，单片越快，加机器就能线性提升整体能力。</p>

<h2>一致性级别 → guarantee 时间戳</h2>
<p>第三步那个"<strong>定时间快照</strong>"特别值得单独说，因为它是 Milvus 在<strong>"看得多新" vs "答得多快"</strong>之间给用户的旋钮。回忆第 11 课的 <strong>TSO 全局时钟</strong>：每条写入都带一个全局单调递增的时间戳。一次读则携带一个 <strong>guarantee 时间戳</strong>，含义是"<strong>我至少要看到 ts ≤ guarantee 的所有写入</strong>"。<span class="inline">parseGuaranteeTsFromConsistency</span> 就是把抽象的<strong>一致性级别</strong>翻译成这个具体 ts：</p>

<table class="t">
  <tr><th>一致性级别</th><th>guarantee ts 取值</th><th>含义 / 取舍</th></tr>
  <tr><td><strong>Strong</strong></td><td><span class="inline">tMax</span>（当前最新）</td><td>必须看到此刻为止的<strong>所有</strong>写入；最强一致，但可能要<strong>等数据追上</strong>，延迟最高</td></tr>
  <tr><td><strong>Bounded</strong></td><td><span class="inline">tMax − gracefulTime</span></td><td>容忍一个<strong>有界的</strong>陈旧窗口（默认几秒），换更稳的低延迟（常用默认）</td></tr>
  <tr><td><strong>Eventually</strong></td><td><span class="inline">1</span>（极小值）</td><td>不等任何数据，<strong>能多快多快</strong>；可能读到略旧的快照，最终一致</td></tr>
  <tr><td><strong>Session</strong> / <strong>Customized</strong></td><td>由会话 / 用户指定的 ts</td><td>Session：保证读到<strong>自己刚写</strong>的；Customized：调用方<strong>自带</strong> guarantee ts</td></tr>
</table>

<p>看这张表只需抓住一条主轴：<strong>guarantee ts 越大（越接近 tMax），看到的数据越新、但越可能要等；越小，答得越快、但可能越旧</strong>。
<span class="inline">parseGuaranteeTsFromConsistency</span> 的实现也正是这个意思——<strong>Strong</strong> 直接把 ts 设成 <span class="inline">tMax</span>，<strong>Bounded</strong> 用 <span class="inline">tMax</span> 减去一个配置的 <span class="inline">gracefulTime</span>，<strong>Eventually</strong> 干脆设成 <span class="inline">1</span>（几乎不等）。Proxy 在这一步只是<strong>算出</strong>这个 ts 并塞进发往分片的请求里；真正"<strong>等数据追到 guarantee ts 才回答</strong>"的动作发生在 QueryNode 侧（第 30 课讲它如何用已消费的 WAL 进度 / TimeTick 与 guarantee ts 比较、不够新就<strong>等</strong>）。这条"<strong>一致性级别 → guarantee ts → 等待</strong>"的链路，是 Part 6 反复要回看的主线。</p>

<p>顺带厘清一个容易混的点：guarantee ts <strong>不是</strong>"只读这一个时刻的数据"，而是"<strong>至少</strong>读到这个时刻为止的数据"——它是一条<strong>下界</strong>。配合第 30 课要讲的 <strong>MVCC</strong>（多版本：一次读看到的是 ts ≤ guarantee 的写入、且未被同样 ts 之前的删除抹掉），你就能理解为什么同一份数据、不同一致性级别下，<strong>看到的"版本"会不一样</strong>。本课先把"Proxy 在入口处算出这个 ts"这件事记牢即可。</p>

<p>再补两句 <strong>Session</strong> 与 <strong>Customized</strong>，它们不在上面那段 <span class="inline">switch</span> 的三个分支里、而是走另一条路给出 ts。<strong>Session（会话一致）</strong>解决的是"<strong>读到我自己刚写的</strong>"这个最常见诉求：客户端会<strong>记住自己最近一次写入的时间戳</strong>，把它作为 guarantee ts 带进读请求，于是"写完立刻搜"一定能搜到自己那条——但不保证看到<strong>别人</strong>此刻的写入。<strong>Customized（自定义）</strong>则把这个旋钮<strong>完全交给调用方</strong>：你自己算一个 ts 传进来，系统照此等待。理解了这四到五个级别，你就握住了 Milvus 给应用层的那个核心权衡——<strong>读得多新、和答得多快，是同一条标尺上的两端，由你按业务来滑</strong>。这也是为什么默认级别是 <strong>Bounded</strong>：它把"陈旧窗口"限制在几秒内、绝大多数场景都够新，却换来了远比 Strong 稳定的低延迟。</p>

<h2>把代码主干认出来</h2>
<p>不必读懂 <span class="mono">task_search.go</span> 的每一行，但要能<strong>认出它的三段式骨架</strong>。下面是高度简化的示意——把上面五步对到方法名上：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/proxy/task_search.go</span><span class="ln">searchTask 的三段式骨架（高度简化示意）</span></div>
  <pre><span class="kw">type</span> <span class="nb">searchTask</span> <span class="kw">struct</span> { <span class="cm">/* request、plan、guarantee ts、结果 … */</span> }

<span class="cm">// ① 解析 + 建 plan + 定 guarantee ts</span>
<span class="kw">func</span> (t *searchTask) <span class="fn">PreExecute</span>(ctx) error {
    <span class="cm">// 校验请求、解析向量字段 / topK / 度量 / 过滤表达式</span>
    <span class="cm">// 把布尔过滤编译成 planpb.PlanNode（ANN 节点 + 标量谓词）</span>
    t.GuaranteeTs = <span class="fn">parseGuaranteeTsFromConsistency</span>(ts, tMax, consistencyLevel)
}
<span class="cm">// ② 扇出到各分片的 delegator</span>
<span class="kw">func</span> (t *searchTask) <span class="fn">Execute</span>(ctx) error {
    <span class="cm">// 按负载均衡把 plan + guaranteeTs 并发发往每个分片</span>
    <span class="cm">//   → t.searchShard(ctx, nodeID, queryNode, channel)</span>
}
<span class="cm">// ③ 跨分片归并出全局 topK（细节见第 29 课）</span>
<span class="kw">func</span> (t *searchTask) <span class="fn">PostExecute</span>(ctx) error { <span class="cm">/* reduce */</span> }</pre>
</div>

<p>这套 <strong>PreExecute / Execute / PostExecute</strong> 三段式不是 search 独有的——它是 Proxy 里<strong>所有 task</strong>（insert、query、DDL……）的统一形状（回忆第 10 课的三条任务队列）。把 search 套进这个模板，你只需要记住每段<strong>填了什么</strong>：Pre 段填"plan 与 guarantee ts"，Execute 段填"扇出"，Post 段填"归并"。认出这个骨架，你读任何一个 Proxy task 都会快很多。</p>

<p>顺便对照一下 search 和 <strong>query</strong>（标量查询 / <span class="mono">queryTask</span>）的区别：两者都走三段式、都要扇出到分片、都要 guarantee ts，但 <strong>search 是"按向量相似度取 topK"</strong>（核心是 ANN 检索 + 距离排序），<strong>query 是"按标量条件取出满足的行"</strong>（核心是谓词过滤，没有向量 ANN、没有 topK 距离排序）。理解了 search 这条最复杂的读路径，query 不过是把"向量 ANN 节点"从 plan 里拿掉的简化版。</p>

<p>最后把本课接回主线。我们已经看清 Proxy 把一次搜索<strong>翻译成 plan、定好 guarantee ts、扇出到各分片</strong>——但请求<strong>到了分片之后会发生什么</strong>？那个接住请求的 <strong>delegator（shard leader）</strong>，要同时搜<strong>已封存的 sealed 段</strong>（带索引）和<strong>还在长的 growing 段</strong>（WAL 活跃尾部），还要把活儿继续扇到持有段的 worker QueryNode 上再合并。这正是<strong>下一课（第 26 课）</strong>要走进的世界：QueryNode 与 delegator。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>查询链路开篇</strong>：search 是写入链路的镜像，本课站在 Proxy 入口看，一路会下钻到 C++ segcore（第 27 课）。</li>
    <li><strong>searchTask 三段式</strong>（<span class="mono">internal/proxy/task_search.go</span>）：PreExecute 解析+建 plan+定 guarantee ts；Execute 扇出；PostExecute 归并。</li>
    <li><strong>检索计划（plan）</strong>：把布尔过滤编译成 <span class="inline">planpb.PlanNode</span>＝向量 ANN 节点（字段+度量+topK）＋标量谓词子树。</li>
    <li><strong>guarantee ts</strong>：由一致性级别经 <span class="inline">parseGuaranteeTsFromConsistency</span>（<span class="mono">util.go</span>）算出——Strong→tMax，Bounded→tMax−gracefulTime，Eventually→1。</li>
    <li><strong>两层扇出</strong>：Proxy 扇到分片（delegator），分片再扇到段（第 26 课）；归并也分层（三级 reduce，第 29 课）。</li>
    <li><strong>Proxy 不碰向量数据</strong>：只做翻译 + 调度 + 归并，真正搜段在 QueryNode / segcore。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Part 4 walked the whole life of a <strong>write</strong>: data flows from the SDK through the Proxy, into the WAL, settles into segments, gets indexed. From this lesson we walk the <strong>other road</strong> — the <strong>query path</strong>: how a <span class="inline">search</span> leaves the SDK, gets translated and scheduled by the Proxy, fans out across shards, and is reduced into a topK to return.
This part is the <strong>mirror</strong> of the write path, and it descends all the way into the C++ <strong>segcore</strong> (Lesson 27). This lesson stands at the <strong>entrance</strong>: what exactly does the <strong>Proxy side</strong> do for one search. Master this entry layer and you hold a "<strong>table of contents for the whole read path</strong>" — every later lesson (delegator, segcore, execution engine, reduce, consistency) fills in one stage this lesson names.
</p>

<div class="card analogy">
  <div class="tag">📮 Analogy</div>
  You walk up to the <strong>front desk of a chain library</strong> and say, "find me a few books most like this one." The desk clerk (the <strong>Proxy</strong>) does five things in order:
  <strong>① understand the request</strong> — by what measure is "alike" (the metric), how many (topK), any extra condition ("only published after 2020" = a scalar filter);
  <strong>② write a standard search slip</strong> — translate the spoken request into a form every branch understands (the search plan);
  <strong>③ fix a point-in-time snapshot</strong> — do you want "<strong>absolutely latest</strong>" (counting books just returned, not yet shelved) or "<strong>slightly older but faster</strong>"? That is the <strong>guarantee timestamp</strong> set by the consistency level;
  <strong>④ hand the slip to each branch</strong> (shard / delegator), each finds its own most-alike few (scatter);
  <strong>⑤ collate and rank</strong> — merge what all branches return, sort, take the most-alike few for you (reduce).
  The desk itself <strong>never touches a shelf</strong>; it only "<strong>understands, translates, snapshots, dispatches, merges</strong>." That is exactly the Proxy's role in a search.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  On the Proxy side a <span class="inline">search</span> is wrapped into a <strong>searchTask</strong> (<span class="mono">internal/proxy/task_search.go</span>) following a <strong>PreExecute → Execute → PostExecute</strong> three-stage shape: <strong>PreExecute</strong> validates and parses the request, compiles the boolean filter into a <strong>search plan</strong> (vector field + metric + topK + scalar filter), and derives the <strong>guarantee timestamp</strong> from the <strong>consistency level</strong> (<span class="inline">parseGuaranteeTsFromConsistency</span>, <span class="mono">internal/proxy/util.go</span>); <strong>Execute</strong> <strong>scatters</strong> the request across the collection's shards (each vchannel's <strong>delegator</strong>); <strong>PostExecute</strong> <strong>reduces</strong> across shards into the final topK. The Proxy only does "<strong>translate + schedule + merge</strong>"; the actual segment search lives in the QueryNode (Lesson 26) and segcore (Lesson 27).
</div>

<p>Before diving in, it helps to see the <strong>mirror</strong> against the write path concretely. On a <strong>write</strong>, the Proxy splits a batch of rows by vchannel and appends them to the WAL — a <strong>scatter that writes</strong>. On a <strong>read</strong>, the Proxy sends one query to every shard and merges what comes back — a <strong>scatter that gathers</strong>. Both pivot on the same two ideas introduced back in Lesson 3: <strong>sharding by vchannel</strong> (which shards to touch) and <strong>timestamps</strong> (a write stamps its data; a read carries a guarantee ts). If you remember Part 4's write path, you already know the <strong>shape</strong> of the read path — this part just fills in the read-specific organs: the plan, the delegator, segcore, reduce, and consistency.</p>

<h2>Five steps on the Proxy side of a search</h2>
<p>Map those five desk-clerk chores onto code and you get the backbone of <span class="mono">searchTask</span>. This vertical flow lays it out step by step:</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Parse the request</h4><p>From the <span class="inline">SearchRequest</span> pull out: target collection / partitions, the vector field, <strong>topK</strong>, <strong>metric type</strong> (L2/IP/COSINE), the query vectors (placeholder group), the boolean <strong>filter expression</strong> (e.g. <span class="mono">year &gt; 2020</span>), and the <strong>consistency level</strong>. Validation and field parsing happen in <span class="inline">PreExecute</span>.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Build the search plan</h4><p>Compile the filter into a <strong><span class="inline">planpb.PlanNode</span></strong>: a plan tree with a <strong>vector ANN node</strong> (field + metric + topK) and a <strong>scalar predicate subtree</strong>. This "search slip" travels with the request to the shards and is executed once it reaches segcore (the execution engine is detailed in Lesson 28).</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Fix the guarantee timestamp</h4><p>By <strong>consistency level</strong>, call <span class="inline">parseGuaranteeTsFromConsistency</span> to compute the "<strong>snapshot</strong>" this read requires: Strong→see the latest, Eventually→just be fast, Bounded→tolerate a little staleness. This ts decides how <strong>up-to-date</strong> the QueryNode must be before it answers (MVCC in Lesson 30).</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Scatter to shards</h4><p>A collection's data is split by <strong>vchannel</strong> into <strong>shards</strong>, each owned by a <strong>delegator (shard leader)</strong>. <span class="inline">Execute</span>, via a load-balancing policy, sends "plan + guarantee ts" concurrently to each shard's delegator (<span class="inline">searchShard</span>).</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>Reduce across shards</h4><p>Each shard returns "<strong>its own topK</strong>." <span class="inline">PostExecute</span> merges these <strong>local topKs</strong>, <strong>re-sorts by distance, dedups by primary key</strong>, and takes the <strong>global topK</strong> back to the SDK. The cross-shard reduce details are saved for Lesson 29.</p></div></div>
</div>

<p>Among these five steps, step 1's "<strong>metric</strong>" deserves a second look. Recall Lessons 4 and 22: a vector's "alikeness" is defined by a metric (<strong>L2</strong> smaller is closer; <strong>IP/COSINE</strong> larger/more-aligned is closer), and <strong>the metric used for search must match the one used at index build and field declaration</strong>. While parsing, the Proxy reads the metric specified for this search and checks it against the field/index — an unglamorous gate that nonetheless blocks the most insidious class of vector-search bugs (a wrong metric makes results "<strong>systematically off, yet raises no error</strong>"). So think of the Proxy's "parse" as not merely "<strong>reading out parameters</strong>" but also a layer of "<strong>legality and consistency gatekeeping</strong>": does the field exist, is the vector dimension right, does the metric fit, is topK within limits, can the expression compile — if any is invalid, the request is bounced back to the SDK <strong>before any fan-out</strong>, rather than wasting a whole round of distributed search.</p>

<p>Chained together, the Proxy's role is crystal clear: it is a "<strong>translator + dispatcher + cashier</strong>." Translate (compile a human filter into a plan tree), dispatch (decide which shards to hit with which snapshot), cash up (collate scattered results into one answer) — and <strong>none of the three touches the actual vector data</strong>. This matches Lesson 10's framing of the Proxy as a "stateless gateway that fans out and reduces"; search merely lands that fan-out/reduce picture on the <strong>read path</strong>.</p>

<p>A bit more on step 2's <strong>search plan</strong>, since it is something the write path entirely lacks and the read path uniquely needs. The filter the SDK sends is a <strong>string expression</strong> (e.g. <span class="mono">color == "red" &amp;&amp; year &gt; 2020</span>) — human-readable, but not directly executable by a machine. The Proxy <strong>parses it into an expression tree</strong> and combines it with the main "vector ANN search" task into a complete <span class="inline">planpb.PlanNode</span>: at the top a <strong>vector-search node</strong> (which vector field, which metric, how large a topK) under which hangs a <strong>scalar predicate subtree</strong> (the <span class="mono">color/year</span> conditions compiled into efficiently-executable checks). This plan is <strong>passed down verbatim</strong> with the request to every shard and segment, finally run inside the C++ execution engine — "<strong>narrow the candidate rows by the predicate first, then do ANN over the filtered subset</strong>" (this filter-then-search execution detail is the subject of Lesson 28). At this step the Proxy only <strong>compiles the plan</strong>; it does not execute it.</p>

<p>One more detail worth naming: a single search request <strong>may carry multiple query vectors</strong> — this is <strong>nq</strong> (number of queries), packed into one <span class="inline">placeholder group</span>. <span class="mono">searchTask</span> validates its size at the <span class="inline">checkNq</span> step. The meaning of nq is "<strong>batch N similarity searches in one round trip</strong>": each query vector wants its own topK, and after fan-out segcore computes and takes a topK for each query vector separately, with the merge also <strong>grouped</strong> per query vector. Grasping nq keeps you from conflating "topK=10" with "nq=5" — the former is "how many answers per question," the latter is "how many questions at once," and the final result is a table of <strong>nq × topK</strong>.</p>

<h2>What the Proxy "does" and "does not do" in a search</h2>
<p>Beginners most easily imagine the Proxy as "the search engine itself." Quite the opposite — it is a <strong>stateless coordination layer</strong> holding neither vector data nor indexes. Drawing its "<strong>responsibility boundary</strong>" clearly keeps the whole query path from getting muddled in your head:</p>

<div class="cols">
  <div class="col"><h4>✅ The Proxy does</h4><p>Validate and authenticate, <strong>compile the filter into a plan</strong>, <strong>compute guarantee ts</strong> from the consistency level, <strong>load-balance</strong> to pick QueryNodes, <strong>scatter</strong> the request to shards, <strong>reduce across shards</strong> into the final topK, truncate by offset/limit and return to the SDK. In one line: <strong>translate, schedule, merge</strong>.</p></div>
  <div class="col"><h4>❌ The Proxy does not</h4><p>Hold vector data, hold indexes, or <strong>compute distances in its own process</strong>; decide "which QueryNode owns a segment" (that is QueryCoord's job, Lesson 13); execute the plan (the plan runs only once it reaches segcore, Lesson 28); wait for data to catch up ("wait until guarantee ts" happens on the QueryNode, Lesson 30).</p></div>
</div>

<p>Why does this boundary matter? Because it embodies Milvus's "<strong>separation of compute and coordination</strong>": the Proxy can <strong>scale out statelessly</strong> (run as many as you like, lose no data if one dies) precisely because it <strong>stores nothing</strong>; the genuinely expensive work — "<strong>holding indexes and computing vector distances in memory</strong>" — is pushed onto QueryNodes that <strong>scale horizontally by segment</strong>. Separating "<strong>who stores data, who computes distances, who only coordinates</strong>" is the prerequisite for understanding Lessons 26 and 27 — and a design choice shared by nearly every distributed search system: keep the coordination layer light, the compute layer heavy, each scaling independently.</p>

<h2>How data flows: from SDK to result</h2>
<p>From another angle, draw "who hands the request to whom" as a horizontal data flow. Note the highlighted cell in the middle — the star of this lesson, <span class="inline">searchTask</span>:</p>

<div class="flow">
  <div class="node"><div class="nt">SDK</div><div class="nd">Search RPC<br>vectors+topK+expr</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">Proxy · searchTask</div><div class="nd">parse→plan→guarantee-ts</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">delegator A</div><div class="nd">shard 1 local topK</div></div>
  <div class="arrow">＋</div>
  <div class="node"><div class="nt">delegator B</div><div class="nd">shard 2 local topK</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">reduce</div><div class="nd">merge into global topK</div></div>
</div>

<p>This flow has two "<strong>one-to-many</strong>" spread points, the key to understanding distributed search. The first is at <strong>Proxy → delegator</strong>: a collection is cut into several shards and the request must hit each shard <strong>simultaneously</strong> (scatter). The second is inside each delegator: it further fans the search out to the several segments and worker QueryNodes it manages (that is Lesson 26's content).
So a search is a <strong>two-level fan-out</strong>: Proxy to shards, shard to segments. Correspondingly the merge is also <strong>layered</strong>: topK within a segment, merge within a node, then a cross-shard merge on the Proxy — this "<strong>three-level reduce</strong>" is covered systematically in Lesson 29. For this lesson, just remember the <strong>outermost</strong> pair: Proxy fans out, Proxy reduces.</p>

<p>Why must the fan-out be <strong>concurrent</strong> rather than asking one shard at a time? Because a search's latency is set by the <strong>slowest shard</strong>, not the sum of all shards. Querying N shards serially makes total latency ≈ N × per-shard latency; with concurrent fan-out, total latency ≈ per-shard latency + a little merge overhead. This is the fundamental trick of distributed search — "<strong>parallelism for low latency</strong>": cut one big problem into <strong>mutually-independent small problems</strong>, solve them at once, then stitch the answers. And precisely because shards are <strong>independent</strong> (each looks only at its own slice of data), the fan-out can safely go concurrent — this "<strong>data sharding + shared-nothing parallelism</strong>" structure is the root reason Milvus scales read throughput horizontally: more shards, each smaller and faster, so adding machines linearly lifts overall capacity.</p>

<h2>Consistency level → guarantee timestamp</h2>
<p>Step three, "<strong>fix the snapshot</strong>," deserves its own section, because it is the dial Milvus gives users between <strong>"how fresh you see" vs "how fast you answer."</strong> Recall Lesson 11's <strong>TSO global clock</strong>: every write carries a globally monotonic timestamp. A read carries a <strong>guarantee timestamp</strong> meaning "<strong>I must at least see every write with ts ≤ guarantee</strong>." <span class="inline">parseGuaranteeTsFromConsistency</span> translates the abstract <strong>consistency level</strong> into that concrete ts:</p>

<table class="t">
  <tr><th>Consistency level</th><th>guarantee ts value</th><th>Meaning / tradeoff</th></tr>
  <tr><td><strong>Strong</strong></td><td><span class="inline">tMax</span> (the latest)</td><td>must see <strong>all</strong> writes up to now; strongest consistency, but may have to <strong>wait for data to catch up</strong>, highest latency</td></tr>
  <tr><td><strong>Bounded</strong></td><td><span class="inline">tMax − gracefulTime</span></td><td>tolerate a <strong>bounded</strong> staleness window (a few seconds by default) for steadier low latency (the common default)</td></tr>
  <tr><td><strong>Eventually</strong></td><td><span class="inline">1</span> (a tiny value)</td><td>wait for nothing, <strong>as fast as possible</strong>; may read a slightly stale snapshot, eventually consistent</td></tr>
  <tr><td><strong>Session</strong> / <strong>Customized</strong></td><td>session- / user-supplied ts</td><td>Session: guarantees you read <strong>your own just-written</strong> data; Customized: the caller <strong>brings its own</strong> guarantee ts</td></tr>
</table>

<p>Reading the table needs only one axis: <strong>the larger the guarantee ts (closer to tMax), the fresher the data you see but the more likely you wait; the smaller, the faster you answer but the staler it may be.</strong>
The implementation of <span class="inline">parseGuaranteeTsFromConsistency</span> says exactly this — <strong>Strong</strong> sets ts to <span class="inline">tMax</span>, <strong>Bounded</strong> subtracts a configured <span class="inline">gracefulTime</span> from <span class="inline">tMax</span>, and <strong>Eventually</strong> sets it to <span class="inline">1</span> (waits for almost nothing). At this step the Proxy merely <strong>computes</strong> the ts and stuffs it into the request sent to shards; the actual act of "<strong>wait until data catches up to guarantee ts before answering</strong>" happens on the QueryNode side (Lesson 30 shows how it compares its consumed WAL progress / TimeTick against guarantee ts and <strong>waits</strong> if not fresh enough). This "<strong>consistency level → guarantee ts → wait</strong>" chain is the through-line Part 6 keeps returning to.</p>

<p>One easily-confused point to clear up: the guarantee ts is <strong>not</strong> "read only the data at this one instant" but "read <strong>at least</strong> the data up to this instant" — it is a <strong>lower bound</strong>. Together with Lesson 30's <strong>MVCC</strong> (multi-version: a read sees writes with ts ≤ guarantee, not erased by deletes with ts before it), you can see why the same data, under different consistency levels, shows a <strong>different "version."</strong> For now just nail down that the Proxy computes this ts at the entrance.</p>

<p>Two more words on <strong>Session</strong> and <strong>Customized</strong>, which are not among the three branches of the <span class="inline">switch</span> above but get their ts by another route. <strong>Session</strong> solves the most common need, "<strong>read my own just-written data</strong>": the client <strong>remembers the timestamp of its most recent write</strong> and carries it as the guarantee ts on a read, so "search right after writing" is guaranteed to find your own row — though it does not promise to see <strong>others'</strong> writes at this moment. <strong>Customized</strong> hands the dial <strong>entirely to the caller</strong>: you compute a ts yourself and pass it in, and the system waits accordingly. Understanding these four-to-five levels gives you the core tradeoff Milvus exposes to the application layer — <strong>how fresh you read and how fast you answer are two ends of one ruler, and you slide it by your business needs</strong>. That is also why the default level is <strong>Bounded</strong>: it caps the staleness window to a few seconds — fresh enough for the vast majority of cases — while buying far steadier low latency than Strong.</p>

<h2>Recognize the code backbone</h2>
<p>You needn't read every line of <span class="mono">task_search.go</span>, but you should <strong>recognize its three-stage skeleton</strong>. Here is a heavily simplified sketch — mapping the five steps above onto method names:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/proxy/task_search.go</span><span class="ln">searchTask three-stage skeleton (heavily simplified)</span></div>
  <pre><span class="kw">type</span> <span class="nb">searchTask</span> <span class="kw">struct</span> { <span class="cm">/* request, plan, guarantee ts, results … */</span> }

<span class="cm">// (1) parse + build plan + fix guarantee ts</span>
<span class="kw">func</span> (t *searchTask) <span class="fn">PreExecute</span>(ctx) error {
    <span class="cm">// validate request; parse vector field / topK / metric / filter expr</span>
    <span class="cm">// compile the boolean filter into a planpb.PlanNode (ANN node + scalar predicate)</span>
    t.GuaranteeTs = <span class="fn">parseGuaranteeTsFromConsistency</span>(ts, tMax, consistencyLevel)
}
<span class="cm">// (2) scatter to each shard's delegator</span>
<span class="kw">func</span> (t *searchTask) <span class="fn">Execute</span>(ctx) error {
    <span class="cm">// load-balance the plan + guaranteeTs concurrently to every shard</span>
    <span class="cm">//   → t.searchShard(ctx, nodeID, queryNode, channel)</span>
}
<span class="cm">// (3) reduce across shards into the global topK (details in Lesson 29)</span>
<span class="kw">func</span> (t *searchTask) <span class="fn">PostExecute</span>(ctx) error { <span class="cm">/* reduce */</span> }</pre>
</div>

<p>This <strong>PreExecute / Execute / PostExecute</strong> three-stage shape is not unique to search — it is the uniform shape of <strong>every</strong> Proxy task (insert, query, DDL…) (recall Lesson 10's three task queues). Fit search into the template and you only need to remember <strong>what each stage fills in</strong>: Pre fills "plan and guarantee ts," Execute fills "scatter," Post fills "reduce." Recognize this skeleton and you'll read any Proxy task far faster.</p>

<p>For contrast, compare search with <strong>query</strong> (scalar query / <span class="mono">queryTask</span>): both follow the three stages, both scatter to shards, both carry a guarantee ts — but <strong>search "takes a topK by vector similarity"</strong> (its core is ANN search + distance sorting), whereas <strong>query "fetches rows satisfying a scalar condition"</strong> (its core is predicate filtering, with no vector ANN and no topK distance sort). Once you understand search, the most complex read path, query is just the simplified version with the "vector ANN node" removed from the plan.</p>

<p>Finally, tie this lesson back to the through-line. We have seen the Proxy <strong>translate a search into a plan, fix the guarantee ts, and scatter to shards</strong> — but <strong>what happens once the request reaches a shard</strong>? The <strong>delegator (shard leader)</strong> that catches the request must search both the <strong>sealed segments</strong> (with their indexes) and the <strong>growing segments</strong> (the live tail of the WAL), and further fan the work out to worker QueryNodes holding segments before merging. That is exactly the world the <strong>next lesson (Lesson 26)</strong> steps into: the QueryNode and the delegator.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Query path begins</strong>: search mirrors the write path; this lesson stands at the Proxy entrance and will descend into C++ segcore (Lesson 27).</li>
    <li><strong>searchTask three stages</strong> (<span class="mono">internal/proxy/task_search.go</span>): PreExecute parses + builds plan + fixes guarantee ts; Execute scatters; PostExecute reduces.</li>
    <li><strong>Search plan</strong>: compile the boolean filter into a <span class="inline">planpb.PlanNode</span> = vector ANN node (field+metric+topK) + scalar predicate subtree.</li>
    <li><strong>guarantee ts</strong>: derived from the consistency level via <span class="inline">parseGuaranteeTsFromConsistency</span> (<span class="mono">util.go</span>) — Strong→tMax, Bounded→tMax−gracefulTime, Eventually→1.</li>
    <li><strong>Two-level fan-out</strong>: Proxy to shards (delegators), shard to segments (Lesson 26); the merge is layered too (three-level reduce, Lesson 29).</li>
    <li><strong>Proxy never touches vectors</strong>: only translate + schedule + merge; the real segment search is in the QueryNode / segcore.</li>
  </ul>
</div>
""",
}

LESSON_26 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课，Proxy 把一次搜索<strong>翻译成 plan、定好 guarantee ts、扇出到各个分片</strong>。可"分片"接住请求的那一刻，故事才真正进入<strong>检索引擎</strong>的地界。每个分片的<strong>接收者</strong>，是一个跑在 QueryNode 上的特殊角色——<strong>delegator（shard leader，分片首领）</strong>。
这一课就走进 delegator：它如何同时照顾<strong>两类段</strong>（封存好的 sealed 段、还在长的 growing 段），如何把搜索<strong>再扇出</strong>到持有段的 worker QueryNode、再把结果合并，以及它怎么靠<strong>消费 WAL 尾部</strong>让"刚写进来的数据"也能被搜到。
如果说第 25 课的 Proxy 是"<strong>把请求送到门口的快递</strong>"，那么 delegator 就是"<strong>分拣中心的现场主管</strong>"：它不亲自把每件货搬来搬去，而是清楚每件货在哪、该派谁去取、取回来怎么并成一份，并且时刻盯着"<strong>最新到的货有没有都算进来</strong>"。把这一层看懂，你就握住了 Milvus 读路径里<strong>最核心的协调者</strong>。
</p>

<div class="card analogy">
  <div class="tag">📚 生活类比</div>
  把一个分片想成一个<strong>城市片区的图书调度台</strong>，delegator 就是这个片区的<strong>调度主管</strong>。片区里的书分两种存法：
  <strong>① 已编目入库的旧书</strong>——它们整整齐齐躺在片区里<strong>好几座分馆</strong>（worker QueryNode）的书架上，每本都进了<strong>检索目录</strong>（索引），查起来又快又准（这是 <strong>sealed 段</strong>）；
  <strong>② 今天刚到、还没编目的新书</strong>——它们堆在调度台<strong>自己手边的"新到推车"</strong>上，还没进目录，但因为就在手边、数量也少，<strong>一本本翻一遍</strong>也快（这是 <strong>growing 段</strong>，靠每天的<strong>送货车</strong>＝WAL 尾部不断补货）。
  来了一个"找最像的几本"的请求，调度主管要做三件事：<strong>把请求分发给各分馆</strong>各自在目录里查（扇出到 worker），<strong>自己顺手翻一遍新到推车</strong>（本地搜 growing），最后<strong>把分馆和推车的结果合在一起</strong>排个序交上去（节点内归并）。少看任何一边，答案都不完整——<strong>旧书新书都得查</strong>，这正是 delegator 存在的全部理由。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一个 vchannel（分片）在副本内由一个 QueryNode 担任 <strong>shard leader</strong>，其上运行 <strong>delegator</strong>（<span class="mono">internal/querynodev2/delegator/delegator.go</span> 的 <span class="inline">ShardDelegator</span> 接口 / <span class="inline">shardDelegator</span>）。它是该分片所有读的入口，必须给出一个<strong>完整且新鲜</strong>的答案，因此要同时覆盖：<strong>sealed 段</strong>（已封存、带 Knowhere 索引，由 QueryCoord 安排加载、<strong>分布</strong>到副本内多个 worker QueryNode 上）与 <strong>growing 段</strong>（delegator 自己<strong>消费 WAL 尾部</strong>维护的、尚未封存的最新数据）。一次 <span class="inline">Search</span> 里，delegator 取一份段快照（<span class="inline">GetSegmentInfo</span> → sealed + growing），把 sealed 检索<strong>扇出</strong>到各 worker、growing 在本地搜，再把两边的部分结果<strong>节点内归并</strong>后返回 Proxy。它还维护一个 <strong>tsafe</strong>（已消费到的 WAL 进度），不够 guarantee ts 新就<strong>等</strong>（第 30 课）。
</div>

<h2>delegator 是谁：一个分片的读协调者</h2>
<p>先把"分片"和"段"的关系理顺。回忆第 7 课：一个 collection 的数据按 <strong>vchannel</strong> 切成若干<strong>分片</strong>，每个分片里又装着许多<strong>段（segment）</strong>。再回忆第 13 课：<strong>QueryCoord</strong> 负责"<strong>把哪些段、加载到哪些 QueryNode</strong>"，并为每个 vchannel 在副本内指定一个 QueryNode 当 <strong>shard leader</strong>。这个 leader 上跑的就是 <strong>delegator</strong>——它是该分片<strong>对外的唯一读入口</strong>，Proxy 扇出过来的请求就落在它身上。</p>

<p>关键在于：delegator <strong>本身不一定持有该分片所有段的数据</strong>。为了弹性与负载均衡，QueryCoord 会把这个分片的 sealed 段<strong>分散加载</strong>到副本内的<strong>多个 QueryNode（worker）</strong>上——可能有些段在 leader 自己身上，更多段在别的 worker 上。delegator 维护一张<strong>分布表（distribution）</strong>，记着"<strong>哪个段此刻在哪个 worker</strong>"。于是 delegator 的角色更像一个"<strong>知道货在谁手里的调度员</strong>"：它不亲自扛下所有段，而是<strong>把检索请求路由到持有对应段的 worker</strong>，再收集合并。这正是 Milvus 读路径能<strong>水平扩展</strong>的地方——段越多，摊到的 worker 越多，单 worker 的负担越轻，加机器就能提升整体检索吞吐。</p>

<p>这里要补一个第 13 课埋下的概念：<strong>副本（replica）</strong>。为了高可用与更高吞吐，一个 collection 可以被加载<strong>多份</strong>，每一份叫一个副本；每个副本都是一套"<strong>能独立答全量数据</strong>"的 QueryNode 班子。delegator 说的"把段分布到多个 worker"，指的就是<strong>在同一个副本内部</strong>把段摊开。于是同一个分片，在不同副本里各有一个自己的 leader 与一套 worker。好处有二：其一，<strong>多副本分担读流量</strong>，请求可以被负载均衡到不同副本，吞吐随副本数增长；其二，<strong>容错</strong>——某个 worker 甚至某个副本出问题，别的副本仍能答得上来。把"<strong>分片（按数据切）</strong>"和"<strong>副本（按可用性复制）</strong>"这两个正交维度分清楚，你就理解了 Milvus 读侧扩展性的两条腿：分片让单次检索<strong>并行变快</strong>，副本让整体吞吐<strong>叠加变高</strong>、并带来冗余。delegator 始终是"<strong>某副本里某分片</strong>"这个交点上的那个协调者。</p>

<h2>两类段：sealed（带索引）与 growing（WAL 尾部）</h2>
<p>delegator 要给一个<strong>完整</strong>的答案，就必须同时搜两类段。它们一冷一热、一稳一新，差别正好成一对：</p>

<div class="cols">
  <div class="col"><h4>🧊 sealed 段（封存 · 带索引）</h4><p>已经<strong>封存、不再变化</strong>的段，建好了 <strong>Knowhere 向量索引</strong>（第 22 课），由 QueryCoord 安排从对象存储<strong>加载</strong>进内存、并<strong>分布</strong>到副本内多个 worker（第 23 课）。检索时走<strong>索引</strong>（HNSW/IVF…），<strong>又快又准</strong>。它们是数据的"<strong>主体</strong>"——大、稳、可被索引加速、可被水平摊开。</p></div>
  <div class="col"><h4>🔥 growing 段（在长 · 无索引）</h4><p>还在<strong>持续接收新插入</strong>、尚未封存的段，<strong>没有索引</strong>。delegator <strong>自己消费该 vchannel 的 WAL 尾部</strong>（<span class="inline">ProcessInsert</span> / <span class="inline">ProcessDelete</span>），把刚写入的行维护成 growing 段。检索时只能<strong>暴力逐条算</strong>（第 27 课详述），但因为它小、就在本地，开销可控——它保证了"<strong>刚写完就能搜到</strong>"的新鲜度。</p></div>
</div>

<p>为什么非要<strong>分成两类</strong>、而不能统一处理？因为<strong>"新鲜"和"高效"是一对天然矛盾</strong>。索引（尤其图索引）<strong>建起来很贵</strong>、且建好后不便频繁改动，所以它只适合给"<strong>已经定型、不再变</strong>"的 sealed 段用；而刚写进来的数据<strong>每时每刻都在变</strong>，根本来不及建索引。Milvus 的解法就是"<strong>分而治之</strong>"：把<strong>稳定的大头</strong>交给索引（sealed，快），把<strong>易变的小尾巴</strong>交给暴力扫描（growing，新），两边结果一合并，就同时拿到了"<strong>快</strong>"和"<strong>新</strong>"。这其实是第 7 课"<strong>日志即数据 / LSM 思路</strong>"在读路径上的回响——新数据先在内存里以可变形态服务，攒够了再<strong>封存 + 建索引</strong>沉淀为高效的不可变主体。随着 growing 段不断被 flush、compaction（第 17、19 课）转成 sealed，"新尾巴"会持续变成"旧主体"，而 delegator 始终把<strong>两边的当前快照</strong>拼成一个完整视图。</p>

<p>这里有个微妙却关键的问题：当一个 growing 段被封存、又作为 sealed 段被加载进来时，会不会<strong>被数到两次</strong>（一次当 growing、一次当 sealed），让结果重复？delegator 必须处理这种"<strong>交接（handoff）</strong>"。它的办法是维护一份"<strong>排除名单</strong>"——一个段一旦以 sealed 形态就绪、可被检索，它对应的 growing 形态就要<strong>从可读快照里排除掉</strong>，反之亦然，确保<strong>同一份数据在某一时刻只被一类段代表</strong>。再加上归并阶段<strong>按主键去重</strong>这道保险，delegator 才能在"数据形态不断从 growing 流向 sealed"的过程中，始终给出<strong>不重不漏</strong>的结果。理解这一点，你就明白 delegator 不只是个"分发+合并"的简单路由器，它还在<strong>维护一个随时间推移、段不断换形态的一致视图</strong>——这是它作为 shard leader 最不显眼、却最不能出错的职责。</p>

<h2>一次分片内检索：扇出到 worker，再归并</h2>
<p>把 delegator 处理一次 <span class="inline">Search</span> 的内部动作摆开，就是"<strong>取快照 → 分组扇出 → 本地搜 growing → 节点内归并</strong>"这一串：</p>

<div class="flow">
  <div class="node hl"><div class="nt">delegator</div><div class="nd">取段快照<br>sealed+growing</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">worker QN-1</div><div class="nd">搜它持有的<br>sealed 段(索引)</div></div>
  <div class="arrow">＋</div>
  <div class="node"><div class="nt">worker QN-2</div><div class="nd">搜它持有的<br>sealed 段(索引)</div></div>
  <div class="arrow">＋</div>
  <div class="node"><div class="nt">本地 growing</div><div class="nd">暴力搜<br>WAL 尾部</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">节点内归并</div><div class="nd">合成本分片<br>局部 topK</div></div>
</div>

<p>逐步看：delegator 先调 <span class="inline">GetSegmentInfo(readable)</span> 拿到一份<strong>当前可读段的快照</strong>——返回 <span class="inline">sealed</span>（按 worker 分好组）与 <span class="inline">growing</span> 两份清单。然后它<strong>按"段在谁手上"把检索子任务分组</strong>（<span class="inline">organizeSubTask</span>）：在 worker A 上的那批段，打包成一个子请求发给 A；在 worker B 上的发给 B；growing 段就在 delegator <strong>本地</strong>搜。各 worker 各自在自己内存里的段上跑 segcore 检索（下一课），把<strong>各自的局部 topK</strong> 回传。delegator 收齐后，把"<strong>各 worker 的结果 + 本地 growing 的结果</strong>"做一次<strong>节点内归并</strong>（按距离排序、按主键去重、取 topK），得到<strong>这一个分片的局部 topK</strong>，交回给 Proxy。</p>

<p>看出"<strong>扇出—归并</strong>"又出现了吗？第 25 课说一次 search 是<strong>两层扇出</strong>：Proxy 扇到分片、分片再扇到段。这一课正是<strong>第二层</strong>——delegator 把搜索扇到持有段的各 worker，再做<strong>节点内</strong>归并。于是整条读路径的归并是<strong>三级</strong>的：worker 上<strong>段内</strong>取 topK（segcore，第 27 课）、delegator 做<strong>节点内/分片内</strong>合并（本课）、Proxy 做<strong>跨分片</strong>合并（第 25 课）——这"<strong>三级 reduce</strong>"第 29 课会系统收束。本课你抓住中间这一级即可：<strong>delegator 把一个分片的零散段结果，合成该分片的一份局部 topK</strong>。</p>

<p>为什么要在 delegator 这一层<strong>先合并一次</strong>，而不是把所有 worker 的原始结果一股脑全发回 Proxy？这背后是一个朴素却重要的工程考量：<strong>尽量减少跨网络搬运的数据量</strong>。设想一个分片摊在 5 个 worker 上、每个 worker 各返回 topK 条候选，如果不在节点内先归并，Proxy 就要接收 <strong>5 份</strong>候选再去重排序；而 delegator 先把这 5 份压成<strong>一份</strong> topK，发给 Proxy 的数据量就降到原来的五分之一。把"<strong>能在靠近数据的地方先聚合的，就别留到上游再聚合</strong>"——这正是分布式系统里"<strong>下推聚合 / 局部归并</strong>"的通用智慧，和数据库把过滤、聚合尽量下推到存储层是同一个道理。三级 reduce 的存在，本质就是让每一层都<strong>只把必要的精华往上交</strong>，逐级收窄，而不是把海量原始候选一路背到最顶。</p>

<h2>谁是谁：一张角色对照表</h2>
<p>delegator 这一层名词较多（leader、worker、副本、sealed、growing、tsafe），用一张表把"<strong>角色 → 是谁 / 在哪 / 干什么</strong>"钉牢：</p>

<table class="t">
  <tr><th>角色 / 概念</th><th>是谁 / 在哪</th><th>干什么</th></tr>
  <tr><td><strong>delegator（shard leader）</strong></td><td>某 vchannel 在副本内被指定的那个 QueryNode 上</td><td>该分片读的<strong>唯一入口</strong>：取快照、扇出、归并、维护 tsafe</td></tr>
  <tr><td><strong>worker QueryNode</strong></td><td>副本内持有 sealed 段的若干 QueryNode</td><td>在<strong>自己内存里的段</strong>上跑 segcore 检索，回传局部结果</td></tr>
  <tr><td><strong>sealed 段</strong></td><td>分布在各 worker 内存（由 QueryCoord 加载）</td><td>带索引、走索引检索；数据主体，可水平摊开</td></tr>
  <tr><td><strong>growing 段</strong></td><td>delegator 本地（消费 WAL 尾部得到）</td><td>无索引、暴力搜；保证最新写入可见</td></tr>
  <tr><td><strong>tsafe</strong></td><td>delegator 维护的一个时间戳</td><td>已消费 WAL 到的进度；&lt; guarantee ts 就等（第 30 课）</td></tr>
</table>

<p>这张表里藏着 delegator 设计的两条主线。<strong>第一条是"协调 vs 计算"的再次分离</strong>：delegator 只<strong>协调</strong>（路由、归并、维护分布与 tsafe），真正在段上<strong>算距离</strong>的是 worker 上的 segcore——这和第 25 课"Proxy 只协调、不算"是同一种分层思想，只是下沉了一层。<strong>第二条是"新鲜度的责任在 leader"</strong>：sealed 段是别人加载的、稳定的；唯独 growing 这条"<strong>保鲜</strong>"的活，是 delegator 亲自消费 WAL 完成的。这也解释了 leader 为什么特殊——它不只是个调度员，还<strong>背着这个分片"看到最新写入"的责任</strong>。换个角度说：sealed 这一侧的"加载与分布"是 QueryCoord 在<strong>控制面</strong>统筹的（第 13 课），delegator 只是被动地<strong>知道</strong>结果；而 growing 这一侧的"消费与保鲜"则完全是 delegator 在<strong>数据面</strong>主动完成的。一个分片的"全貌"，正是这两股力量——上面控制面安排的稳定主体、与本地数据面追上来的最新尾巴——在 delegator 这个点上<strong>汇合</strong>而成。</p>

<h2>新鲜从哪来：消费 WAL 尾部 + tsafe</h2>
<p>最后把"<strong>为什么读能看到刚写的</strong>"这件事说透，它正是 Part 6 的主线之一。回忆第 16 课：所有写入都先 Append 进 <strong>WAL</strong>（流式日志）。delegator 作为 shard leader，会<strong>订阅并持续消费</strong>本 vchannel 的 WAL 尾部：每来一条新的 Insert/Delete 消息，它就 <span class="inline">ProcessInsert</span> / <span class="inline">ProcessDelete</span> 把对应改动<strong>反映进 growing 段</strong>。于是"写入落 WAL"和"读能看到"之间，只隔着 delegator 消费 WAL 的这一点点延迟——这就是数据<strong>保鲜</strong>的来源。这也正好呼应第 16 课的主题：WAL 不只是写入的"持久化保险"，它同时是读路径的"<strong>新鲜数据来源</strong>"——同一条流，写的人往里 Append，读这一侧的 delegator 在尾部 Tail，一前一后咬合得很紧。</p>

<p>但"<strong>看得到</strong>"还不够，还要"<strong>看得够新</strong>"。delegator 维护一个 <strong>tsafe</strong>：它表示"<strong>我已经把 WAL 消费到了哪个时间戳</strong>"——意味着 ts ≤ tsafe 的所有写入，我都已反映进可读数据了。第 25 课算出的 <strong>guarantee ts</strong> 这时就派上用场：delegator 收到带 guarantee ts 的 search 后，会比较 <span class="inline">tsafe</span> 与 guarantee ts——若 <span class="inline">tsafe ≥ guaranteeTs</span>，说明该看到的写入都到齐了，立刻检索；若 <span class="inline">tsafe &lt; guaranteeTs</span>（自己还没追上），就<strong>等</strong>，等到 tsafe 追上再答。这一"<strong>等够新再答</strong>"的机制，把第 25 课的一致性级别真正<strong>兑现</strong>了：Strong 取 tMax，delegator 就得等到消费追平最新；Eventually 取极小值，几乎不用等——这正是"读得多新 ↔ 答得多快"那把标尺在<strong>分片这一端</strong>的落地。完整的 MVCC 与等待细节，留到第 30 课收口。</p>

<div class="timeline">
  <div class="lane"><span class="lane-label">写入流 (WAL)</span><span class="tslot">ts=10 批A</span><span class="tslot">ts=20 批B</span><span class="tslot">ts=30 批C</span><span class="tslot span">…持续追加…</span></div>
  <div class="lane"><span class="lane-label">delegator 消费</span><span class="tslot">已消费到 ts=20</span><span class="tslot now">tsafe = 20（A·B 可读）</span></div>
  <div class="lane"><span class="lane-label">读 (Strong, Tg=30)</span><span class="tslot">tsafe&lt;30</span><span class="tslot now">等 → 待 tsafe 追到 30 才答</span></div>
  <div class="lane"><span class="lane-label">读 (Eventually)</span><span class="tslot">Tg≈很小</span><span class="tslot now">tsafe≥Tg → 立即答</span></div>
</div>

<p>把 delegator 的三重身份收一收，你就抓住了它的全貌：它是<strong>路由器</strong>（知道每个段在哪个 worker、把子任务分发过去）、是<strong>归并器</strong>（把零散结果合成一份局部 topK 再上交）、还是<strong>保鲜员与守门人</strong>（消费 WAL 维护 growing、用 tsafe 兑现一致性）。这三件事缺一不可：少了路由，它就得自己扛下全部段、失去水平扩展；少了归并，上游就被海量原始结果淹没；少了保鲜与守门，读要么看不到新数据、要么读到不该读的旧快照。正因为把这三件事都压在<strong>shard leader 这一个点</strong>上，Milvus 才能让"一个分片的读"既<strong>可扩展</strong>、又<strong>新鲜</strong>、还<strong>一致</strong>——这也是为什么 delegator 是整条查询链路里承上启下的枢纽。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/querynodev2/delegator/delegator.go</span><span class="ln">ShardDelegator 接口（节选：读 + 段快照 + 数据 + tsafe）</span></div>
  <pre><span class="kw">type</span> <span class="nb">ShardDelegator</span> <span class="kw">interface</span> {
    <span class="cm">// 读：一次分片内检索（扇出到 worker + 本地 growing，再归并）</span>
    <span class="fn">Search</span>(ctx, req *querypb.SearchRequest) ([]*internalpb.SearchResults, error)
    <span class="cm">// 取当前可读段的快照：sealed（按 worker 分布）+ growing（本地）</span>
    <span class="fn">GetSegmentInfo</span>(readable bool) (sealed []SnapshotItem, growing []SegmentEntry)
    <span class="cm">// 数据：消费 WAL 尾部，把新写入反映进 growing 段</span>
    <span class="fn">ProcessInsert</span>(insertRecords map[int64]*InsertData)
    <span class="fn">ProcessDelete</span>(deleteData []*DeleteData, ts uint64)
    <span class="cm">// tsafe：已消费 WAL 的进度；&lt; guarantee ts 则等待（第 30 课）</span>
    <span class="fn">GetTSafe</span>() uint64
    <span class="fn">UpdateTSafe</span>(ts uint64)
    <span class="cm">// … Query / LoadSegments / SyncDistribution 等省略 …</span>
}</pre>
</div>

<p>把本课接回主线：delegator 把一个分片的搜索<strong>扇到各 worker、再合成一份局部 topK</strong>——但 worker 拿到子请求后，到底是<strong>怎么在一个段里把最像的几条找出来</strong>的？sealed 段说"走索引"、growing 段说"暴力扫"，这两句话背后，是 Go 通过 <strong>cgo</strong> 调进 <strong>C++ 的 segcore</strong> 引擎。<strong>下一课（第 27 课）</strong>就跨过这道 Go↔C++ 的边界，走进单个段内部的检索。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>delegator = 分片读入口</strong>：某 vchannel 在副本内被指定的 shard leader（<span class="mono">delegator.go</span> 的 <span class="inline">ShardDelegator</span>），承接 Proxy 扇出过来的读。</li>
    <li><strong>两类段都要搜</strong>：sealed（封存·带 Knowhere 索引·分布在多 worker·走索引）＋ growing（在长·无索引·本地·暴力），合并才完整。</li>
    <li><strong>分布与扇出</strong>：QueryCoord 把 sealed 段分散加载到副本内多 worker；delegator 维护分布表，按"段在谁手上"扇出子任务（<span class="inline">organizeSubTask</span>）再归并。</li>
    <li><strong>三级 reduce 的中间一级</strong>：段内 topK（segcore）→ <strong>delegator 节点内合并</strong> → Proxy 跨分片合并（第 29 课收束）。</li>
    <li><strong>新鲜度来自 WAL</strong>：delegator 消费 vchannel 的 WAL 尾部（<span class="inline">ProcessInsert/Delete</span>）维护 growing，所以刚写就能搜到。</li>
    <li><strong>tsafe 兑现一致性</strong>：维护已消费进度 tsafe，<span class="inline">tsafe &lt; guaranteeTs</span> 就等到追上再答（第 30 课详解）。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson, the Proxy <strong>translated a search into a plan, fixed the guarantee ts, and scattered it across shards</strong>. But the moment a "shard" catches the request, the story truly enters the <strong>search engine's</strong> turf. Each shard's <strong>receiver</strong> is a special role running on a QueryNode — the <strong>delegator (shard leader)</strong>.
This lesson steps into the delegator: how it tends <strong>two kinds of segments</strong> at once (the sealed segments, settled and indexed; the growing segments, still growing), how it <strong>fans the search out again</strong> to worker QueryNodes holding segments and merges the results, and how it keeps "just-written data" searchable by <strong>consuming the tail of the WAL</strong>.
If Lesson 25's Proxy is "<strong>the courier that brings the request to the door</strong>," the delegator is "<strong>the floor supervisor of a sorting center</strong>": it doesn't haul each item itself but knows where every item is, who to send to fetch it, how to combine what comes back into one batch, and keeps an eye on "<strong>whether the newest arrivals are all counted in</strong>." Understand this layer and you hold the <strong>most central coordinator</strong> on Milvus's read path.
</p>

<div class="card analogy">
  <div class="tag">📮 Analogy</div>
  Picture a shard as a <strong>district library dispatch desk</strong>, and the delegator as that district's <strong>dispatch supervisor</strong>. Books in the district are stored two ways:
  <strong>① catalogued, archived books</strong> — neatly shelved across <strong>several branch libraries</strong> (worker QueryNodes), each entered into a <strong>search catalog</strong> (an index), fast and accurate to look up (these are <strong>sealed segments</strong>);
  <strong>② books that arrived today, not yet catalogued</strong> — piled on the <strong>"new-arrivals cart" right beside the desk</strong>, not yet in the catalog, but since they're at hand and few, <strong>flipping through them one by one</strong> is still quick (these are <strong>growing segments</strong>, restocked by the daily <strong>delivery truck</strong> = the WAL tail).
  When a "find the few most-alike" request arrives, the supervisor does three things: <strong>dispatch the request to each branch</strong> to look it up in their catalogs (fan out to workers), <strong>flip through the new-arrivals cart itself</strong> (search growing locally), and finally <strong>merge the branch and cart results</strong>, sort, and hand them up (node-level merge). Skip either side and the answer is incomplete — <strong>old and new books both must be searched</strong>, which is the entire reason the delegator exists.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  Within a replica, a vchannel (shard) is served by one QueryNode acting as <strong>shard leader</strong>, running a <strong>delegator</strong> (the <span class="inline">ShardDelegator</span> interface / <span class="inline">shardDelegator</span> in <span class="mono">internal/querynodev2/delegator/delegator.go</span>). It is the entry for all reads on that shard and must produce a <strong>complete and fresh</strong> answer, so it covers both: <strong>sealed segments</strong> (settled, with a Knowhere index, loaded and <strong>distributed</strong> by QueryCoord across multiple worker QueryNodes in the replica) and <strong>growing segments</strong> (the latest, not-yet-sealed data the delegator maintains by <strong>consuming the WAL tail</strong>). In one <span class="inline">Search</span>, the delegator takes a segment snapshot (<span class="inline">GetSegmentInfo</span> → sealed + growing), <strong>fans</strong> the sealed search out to workers, searches growing locally, then <strong>merges within the node</strong> and returns to the Proxy. It also maintains a <strong>tsafe</strong> (how far it has consumed the WAL) and <strong>waits</strong> if that is not as fresh as the guarantee ts (Lesson 30).
</div>

<h2>Who the delegator is: a shard's read coordinator</h2>
<p>First, straighten out "shard" vs "segment." Recall Lesson 7: a collection's data is cut by <strong>vchannel</strong> into several <strong>shards</strong>, and each shard holds many <strong>segments</strong>. Recall Lesson 13: <strong>QueryCoord</strong> decides "<strong>which segments load onto which QueryNodes</strong>" and designates, for each vchannel within a replica, one QueryNode as the <strong>shard leader</strong>. What runs on that leader is the <strong>delegator</strong> — the shard's <strong>single outward read entry</strong>, the landing point for requests the Proxy fans out.</p>

<p>The crucial point: the delegator <strong>does not necessarily hold all of the shard's segment data itself</strong>. For elasticity and load balancing, QueryCoord <strong>spreads</strong> the shard's sealed segments across <strong>multiple QueryNodes (workers)</strong> in the replica — some segments may sit on the leader, more on other workers. The delegator keeps a <strong>distribution table</strong> recording "<strong>which segment is on which worker right now</strong>." So the delegator is more like a "<strong>dispatcher who knows who holds the goods</strong>": rather than carrying all segments itself, it <strong>routes the search to the worker holding each segment</strong> and then collects and merges. This is exactly where Milvus's read path <strong>scales horizontally</strong> — more segments spread over more workers, lighter load per worker, so adding machines lifts overall search throughput.</p>

<p>Here we should fill in a concept Lesson 13 planted: the <strong>replica</strong>. For high availability and higher throughput, a collection can be loaded in <strong>several copies</strong>, each called a replica; every replica is a full crew of QueryNodes able to "<strong>answer the entire dataset independently</strong>." When the delegator "distributes segments across multiple workers," it means spreading them out <strong>within one replica</strong>. So the same shard has, in each replica, its own leader and its own set of workers. Two benefits follow: first, <strong>multiple replicas share read traffic</strong> — requests can be load-balanced across replicas and throughput grows with replica count; second, <strong>fault tolerance</strong> — if a worker or even a whole replica has trouble, other replicas can still answer. Tell apart the two orthogonal dimensions — "<strong>shards (split by data)</strong>" and "<strong>replicas (copied for availability)</strong>" — and you understand the two legs of Milvus read-side scalability: shards make a single search <strong>faster in parallel</strong>, replicas make overall throughput <strong>stack higher</strong> and add redundancy. The delegator is always the coordinator sitting at the intersection "<strong>this shard in this replica.</strong>"</p>

<h2>Two kinds of segments: sealed (indexed) and growing (WAL tail)</h2>
<p>To give a <strong>complete</strong> answer, the delegator must search both kinds. One cold, one hot; one stable, one fresh — their differences form a neat pair:</p>

<div class="cols">
  <div class="col"><h4>🧊 sealed segment (settled · indexed)</h4><p>A segment that is <strong>settled and immutable</strong>, with a built <strong>Knowhere vector index</strong> (Lesson 22), <strong>loaded</strong> from object storage into memory and <strong>distributed</strong> across workers in the replica by QueryCoord (Lesson 23). Search goes through the <strong>index</strong> (HNSW/IVF…), <strong>fast and accurate</strong>. These are the data's "<strong>bulk</strong>" — large, stable, index-accelerated, horizontally spread.</p></div>
  <div class="col"><h4>🔥 growing segment (growing · no index)</h4><p>A segment still <strong>receiving new inserts</strong>, not yet sealed, with <strong>no index</strong>. The delegator <strong>consumes the vchannel's WAL tail itself</strong> (<span class="inline">ProcessInsert</span> / <span class="inline">ProcessDelete</span>), maintaining just-written rows as growing segments. Search can only go <strong>brute force, row by row</strong> (detailed in Lesson 27), but since it's small and local, the cost is bounded — it guarantees the freshness of "<strong>searchable right after writing</strong>."</p></div>
</div>

<p>Why insist on <strong>two kinds</strong> rather than handle them uniformly? Because <strong>"fresh" and "efficient" are a natural conflict</strong>. An index (a graph index especially) is <strong>expensive to build</strong> and awkward to mutate frequently, so it only suits "<strong>finalized, no-longer-changing</strong>" sealed segments; freshly written data <strong>changes constantly</strong> and there's no time to index it. Milvus's answer is "<strong>divide and conquer</strong>": give the <strong>stable bulk</strong> to the index (sealed, fast) and the <strong>volatile little tail</strong> to brute force (growing, fresh), then merge — getting both "<strong>fast</strong>" and "<strong>fresh</strong>" at once. This is really Lesson 7's "<strong>log-as-data / LSM idea</strong>" echoing on the read path — new data serves in memory in a mutable form first, then once enough accumulates it is <strong>sealed + indexed</strong> into an efficient immutable bulk. As growing segments are continually flushed and compacted (Lessons 17, 19) into sealed ones, the "fresh tail" keeps becoming "old bulk," and the delegator always stitches the <strong>current snapshot of both</strong> into one complete view.</p>

<p>Here is a subtle yet crucial problem: when a growing segment gets sealed and is then loaded back in as a sealed segment, could it be <strong>counted twice</strong> (once as growing, once as sealed), duplicating results? The delegator must handle this "<strong>handoff</strong>." Its method is to maintain an "<strong>exclude list</strong>" — once a segment is ready and searchable in its sealed form, its growing form must be <strong>excluded from the readable snapshot</strong>, and vice versa, ensuring that <strong>the same data is represented by only one kind of segment at any instant</strong>. Plus the safety net of <strong>dedup by primary key</strong> during merge, the delegator can keep giving <strong>no-duplicate, no-miss</strong> results even as data forms keep flowing from growing to sealed. Grasp this and you see the delegator is not just a simple "dispatch + merge" router — it <strong>maintains a consistent view as segments keep changing form over time</strong>, its least conspicuous yet most error-intolerant duty as shard leader.</p>

<h2>One in-shard search: fan out to workers, then merge</h2>
<p>Lay out the delegator's internal moves for one <span class="inline">Search</span> and you get the chain "<strong>take a snapshot → group and fan out → search growing locally → merge within the node</strong>":</p>

<div class="flow">
  <div class="node hl"><div class="nt">delegator</div><div class="nd">take segment snapshot<br>sealed+growing</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">worker QN-1</div><div class="nd">search its<br>sealed segs (index)</div></div>
  <div class="arrow">＋</div>
  <div class="node"><div class="nt">worker QN-2</div><div class="nd">search its<br>sealed segs (index)</div></div>
  <div class="arrow">＋</div>
  <div class="node"><div class="nt">local growing</div><div class="nd">brute-force<br>the WAL tail</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">merge in node</div><div class="nd">this shard's<br>local topK</div></div>
</div>

<p>Step by step: the delegator first calls <span class="inline">GetSegmentInfo(readable)</span> for a <strong>snapshot of currently-readable segments</strong> — returning <span class="inline">sealed</span> (already grouped by worker) and <span class="inline">growing</span>. Then it <strong>groups the search sub-tasks by "who holds the segment"</strong> (<span class="inline">organizeSubTask</span>): the batch on worker A is packed into one sub-request to A, the batch on B goes to B, and growing segments are searched <strong>locally</strong> on the delegator. Each worker runs segcore search on the segments in its own memory (next lesson) and returns <strong>its own local topK</strong>. Once collected, the delegator <strong>merges within the node</strong> "<strong>the workers' results + the local growing results</strong>" (sort by distance, dedup by primary key, take topK) into <strong>this shard's local topK</strong> and hands it back to the Proxy.</p>

<p>See "<strong>fan-out / merge</strong>" appear again? Lesson 25 said a search is a <strong>two-level fan-out</strong>: Proxy to shards, shard to segments. This lesson is the <strong>second level</strong> — the delegator fans the search out to the workers holding segments, then merges <strong>within the node</strong>. So the read path's merge is <strong>three-level</strong>: <strong>within a segment</strong> topK on a worker (segcore, Lesson 27), <strong>within the node/shard</strong> on the delegator (this lesson), and <strong>across shards</strong> on the Proxy (Lesson 25) — this "<strong>three-level reduce</strong>" is tied up systematically in Lesson 29. For this lesson, just grasp the middle level: <strong>the delegator combines a shard's scattered per-segment results into one local topK for that shard</strong>.</p>

<p>Why <strong>merge once</strong> at the delegator layer rather than ship all workers' raw results straight to the Proxy? Behind this is a plain but important engineering consideration: <strong>minimize the data moved across the network</strong>. Imagine a shard spread over 5 workers, each returning topK candidates; without a node-level merge, the Proxy would receive <strong>5 sets</strong> to re-sort and dedup, whereas the delegator first compresses those 5 into <strong>one</strong> topK, cutting the data sent to the Proxy to a fifth. "<strong>Whatever can be aggregated near the data, don't defer to upstream</strong>" — this is the general wisdom of "<strong>pushdown aggregation / partial merge</strong>" in distributed systems, the same reason databases push filtering and aggregation down to the storage layer. The three-level reduce exists precisely so each layer <strong>passes up only the necessary essence</strong>, narrowing stage by stage, rather than hauling a flood of raw candidates all the way to the top.</p>

<h2>Who is who: a role cheat-sheet</h2>
<p>This layer has many nouns (leader, worker, replica, sealed, growing, tsafe). A table nails "<strong>role → who / where / does what</strong>":</p>

<table class="t">
  <tr><th>Role / concept</th><th>Who / where</th><th>Does what</th></tr>
  <tr><td><strong>delegator (shard leader)</strong></td><td>on the QueryNode designated for a vchannel within a replica</td><td>the shard's <strong>sole read entry</strong>: take snapshot, fan out, merge, maintain tsafe</td></tr>
  <tr><td><strong>worker QueryNode</strong></td><td>the several QueryNodes holding sealed segments in the replica</td><td>run segcore search on <strong>segments in its own memory</strong>, return partial results</td></tr>
  <tr><td><strong>sealed segment</strong></td><td>distributed across workers' memory (loaded by QueryCoord)</td><td>indexed, searched via the index; the data bulk, horizontally spread</td></tr>
  <tr><td><strong>growing segment</strong></td><td>local to the delegator (from consuming the WAL tail)</td><td>no index, brute-force search; guarantees latest writes are visible</td></tr>
  <tr><td><strong>tsafe</strong></td><td>a timestamp the delegator maintains</td><td>how far the WAL is consumed; &lt; guarantee ts → wait (Lesson 30)</td></tr>
</table>

<p>This table hides two through-lines of the delegator's design. <strong>One is the re-separation of "coordinate vs compute"</strong>: the delegator only <strong>coordinates</strong> (route, merge, maintain distribution and tsafe); what actually <strong>computes distances</strong> on segments is segcore on the workers — the same layering as Lesson 25's "Proxy only coordinates, never computes," just one level lower. <strong>The other is "freshness is the leader's responsibility"</strong>: sealed segments are loaded by others and stable; only the growing "<strong>keep-fresh</strong>" job is done by the delegator itself consuming the WAL. That explains why the leader is special — it is not just a dispatcher, it also <strong>bears this shard's responsibility for "seeing the latest writes."</strong> Put another way: the "load and distribute" of the sealed side is orchestrated by QueryCoord on the <strong>control plane</strong> (Lesson 13), and the delegator merely passively <strong>knows</strong> the result; whereas the "consume and keep fresh" of the growing side is done entirely by the delegator on the <strong>data plane</strong>. A shard's "whole picture" is precisely these two forces — the stable bulk arranged by the control plane above, and the latest tail caught up by the local data plane — <strong>converging</strong> at the single point of the delegator.</p>

<h2>Where freshness comes from: consuming the WAL tail + tsafe</h2>
<p>Finally, fully explain "<strong>why a read can see what was just written</strong>," a key through-line of Part 6. Recall Lesson 16: every write is first appended to the <strong>WAL</strong> (the streaming log). As shard leader, the delegator <strong>subscribes to and continuously consumes</strong> this vchannel's WAL tail: for each new Insert/Delete message, it <span class="inline">ProcessInsert</span> / <span class="inline">ProcessDelete</span> to <strong>reflect the change into growing segments</strong>. So between "the write hits the WAL" and "a read can see it" lies only the small delay of the delegator consuming the WAL — that is the source of data <strong>freshness</strong>. This neatly echoes Lesson 16's theme: the WAL is not only the write path's "durability insurance," it is at the same time the read path's "<strong>source of fresh data</strong>" — one stream, the writer appending to it and the reader-side delegator tailing it, the two meshing tightly back to back.</p>

<p>But "<strong>can see</strong>" is not enough; it must also be "<strong>fresh enough</strong>." The delegator maintains a <strong>tsafe</strong>: it means "<strong>up to which timestamp I have consumed the WAL</strong>" — i.e. all writes with ts ≤ tsafe are already reflected into readable data. Now Lesson 25's <strong>guarantee ts</strong> pays off: receiving a search carrying a guarantee ts, the delegator compares <span class="inline">tsafe</span> against guarantee ts — if <span class="inline">tsafe ≥ guaranteeTs</span>, all the writes it should see have arrived, so it searches immediately; if <span class="inline">tsafe &lt; guaranteeTs</span> (it hasn't caught up), it <strong>waits</strong> until tsafe catches up before answering. This "<strong>wait until fresh enough, then answer</strong>" mechanism truly <strong>redeems</strong> Lesson 25's consistency levels: Strong takes tMax, so the delegator must wait until its consumption catches the latest; Eventually takes a tiny value, so it barely waits — exactly how the "how-fresh-you-read ↔ how-fast-you-answer" ruler lands at the <strong>shard end</strong>. The full MVCC and waiting details are tied up in Lesson 30.</p>

<div class="timeline">
  <div class="lane"><span class="lane-label">write stream (WAL)</span><span class="tslot">ts=10 A</span><span class="tslot">ts=20 B</span><span class="tslot">ts=30 C</span><span class="tslot span">…keeps appending…</span></div>
  <div class="lane"><span class="lane-label">delegator consumes</span><span class="tslot">consumed up to ts=20</span><span class="tslot now">tsafe = 20 (A·B readable)</span></div>
  <div class="lane"><span class="lane-label">read (Strong, Tg=30)</span><span class="tslot">tsafe&lt;30</span><span class="tslot now">wait → answer when tsafe reaches 30</span></div>
  <div class="lane"><span class="lane-label">read (Eventually)</span><span class="tslot">Tg≈tiny</span><span class="tslot now">tsafe≥Tg → answer at once</span></div>
</div>

<p>Sum up the delegator's three identities and you have the whole picture: it is a <strong>router</strong> (knows which worker holds each segment, dispatches sub-tasks there), a <strong>merger</strong> (combines scattered results into one local topK before handing up), and a <strong>freshness-keeper and gatekeeper</strong> (consumes the WAL to maintain growing, redeems consistency via tsafe). None of the three is dispensable: without routing, it would carry all segments itself and lose horizontal scaling; without merging, upstream drowns in a flood of raw results; without keeping-fresh and gatekeeping, reads either miss new data or read a stale snapshot they shouldn't. Precisely by pressing all three onto <strong>the single point of the shard leader</strong>, Milvus makes "a shard's read" at once <strong>scalable</strong>, <strong>fresh</strong>, and <strong>consistent</strong> — which is why the delegator is the linchpin connecting both ends of the whole query path.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/querynodev2/delegator/delegator.go</span><span class="ln">ShardDelegator interface (excerpt: read + snapshot + data + tsafe)</span></div>
  <pre><span class="kw">type</span> <span class="nb">ShardDelegator</span> <span class="kw">interface</span> {
    <span class="cm">// read: one in-shard search (fan out to workers + local growing, then merge)</span>
    <span class="fn">Search</span>(ctx, req *querypb.SearchRequest) ([]*internalpb.SearchResults, error)
    <span class="cm">// snapshot of currently-readable segments: sealed (by worker) + growing (local)</span>
    <span class="fn">GetSegmentInfo</span>(readable bool) (sealed []SnapshotItem, growing []SegmentEntry)
    <span class="cm">// data: consume the WAL tail, reflect new writes into growing segments</span>
    <span class="fn">ProcessInsert</span>(insertRecords map[int64]*InsertData)
    <span class="fn">ProcessDelete</span>(deleteData []*DeleteData, ts uint64)
    <span class="cm">// tsafe: how far the WAL is consumed; &lt; guarantee ts → wait (Lesson 30)</span>
    <span class="fn">GetTSafe</span>() uint64
    <span class="fn">UpdateTSafe</span>(ts uint64)
    <span class="cm">// … Query / LoadSegments / SyncDistribution etc. omitted …</span>
}</pre>
</div>

<p>Tie this lesson back to the line: the delegator <strong>fans a shard's search out to workers, then combines a local topK</strong> — but once a worker gets a sub-request, how exactly does it <strong>find the few most-alike rows inside a segment</strong>? "Sealed says go through the index, growing says brute-force scan" — behind those two phrases, Go calls into the <strong>C++ segcore</strong> engine over <strong>cgo</strong>. The <strong>next lesson (Lesson 27)</strong> crosses that Go↔C++ boundary and steps inside the search within a single segment.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>delegator = a shard's read entry</strong>: the shard leader designated for a vchannel within a replica (<span class="inline">ShardDelegator</span> in <span class="mono">delegator.go</span>), catching reads the Proxy fans out.</li>
    <li><strong>both kinds of segments searched</strong>: sealed (settled · Knowhere-indexed · spread over workers · via index) + growing (growing · no index · local · brute force), merged for completeness.</li>
    <li><strong>distribution &amp; fan-out</strong>: QueryCoord spreads sealed segments over workers; the delegator keeps a distribution table, fans sub-tasks by "who holds the segment" (<span class="inline">organizeSubTask</span>), then merges.</li>
    <li><strong>the middle of the three-level reduce</strong>: per-segment topK (segcore) → <strong>delegator node-level merge</strong> → Proxy cross-shard merge (tied up in Lesson 29).</li>
    <li><strong>freshness from the WAL</strong>: the delegator consumes the vchannel's WAL tail (<span class="inline">ProcessInsert/Delete</span>) to maintain growing, so just-written data is searchable.</li>
    <li><strong>tsafe redeems consistency</strong>: it tracks consumed progress; if <span class="inline">tsafe &lt; guaranteeTs</span> it waits until caught up before answering (detailed in Lesson 30).</li>
  </ul>
</div>
""",
}

LESSON_27 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前两课，请求从 Proxy 扇到分片、再由 delegator 扇到一个个段、路由给持有段的 worker。现在我们站在<strong>最里层</strong>：worker 拿到一个段、一张检索计划，到底<strong>怎么在这一个段内部把最像的几条找出来</strong>？
答案要跨过一道语言边界——因为真正干这件算力活的，不是 Go，而是 C++ 写的检索内核 <strong>segcore</strong>。这一课就走进 segcore：它是什么、Go 如何通过 <strong>cgo</strong> 调到它、它内部如何用一套统一接口（<span class="inline">SegmentInterface</span>）同时服务<strong>带索引的 sealed</strong> 段与<strong>靠暴力的 growing</strong> 段。
这是整条查询链路<strong>最深的一层</strong>，也是第六部分上半段（第 25–27 课）的<strong>收尾</strong>：到了这里，那张从 Proxy 一路下发的检索计划，终于"<strong>触底</strong>"、在真实的向量数据上被执行。
</p>

<div class="card analogy">
  <div class="tag">📚 生活类比</div>
  想象一座研究档案馆里，有一位只会说<strong>"C++ 语"</strong>的<strong>资深检索专家</strong>（segcore），他动作极快、只管"在<strong>一个档案室</strong>里找出最像样品的几份卷宗"。而楼上发指令的<strong>调度经理</strong>只会说<strong>"Go 语"</strong>（QueryNode）。两人语言不通，怎么协作？
  靠的是档案馆门口那个<strong>固定的翻译窗口</strong>（<strong>cgo / C API</strong>）：经理把需求写成一张<strong>标准工单</strong>递进窗口，窗口把它翻成 C++ 语交给专家；专家查完，再把结果经窗口翻回来。<strong>所有往来都必须走这个窗口</strong>，不能直接喊话——这就是 Go 与 C++ 之间的边界。
  而专家手上的档案室也分两种：一种是<strong>早已整理好、配了卡片目录</strong>的库房（<strong>sealed + 索引</strong>），凭目录一翻就跳到对的架子，极快；另一种是<strong>今天刚收、还堆在收件筐里</strong>的散件（<strong>growing</strong>），没目录，只能<strong>一份一份过目</strong>（暴力扫描），好在量少。专家对外是<strong>同一套找卷宗的手法</strong>，对内却按"<strong>有没有目录</strong>"自动选快路或慢路——这正是 segcore 的 <span class="inline">SegmentInterface</span> 同时罩住 sealed 与 growing 的样子。无论哪种档案室，专家对外交付的都是同一句话："<strong>这是本室里最像样品的几份</strong>"——内部的快慢之别，外人不必知道。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  <strong>segcore</strong> 是 Milvus 用 <strong>C++</strong> 写的"<strong>单段检索引擎</strong>"：它只负责"<strong>在一个 segment 内部执行检索/查询</strong>"，不懂分片、副本、WAL 这些分布式概念。Go 侧的 QueryNode 通过 <strong>cgo</strong> 跨语言调用它：Go 的 <span class="inline">LocalSegment</span>（<span class="mono">internal/querynodev2/segments/segment.go</span>，第 2 课见过）持有一个指向 C++ 段对象的<strong>不透明句柄</strong>，经 <strong>C API</strong>（<span class="mono">internal/core/src/segcore/segment_c.h</span>，如 <span class="inline">NewSegment</span> / <span class="inline">AsyncSearch</span> / <span class="inline">DeleteSegment</span>）调进去。C++ 内部用一套统一接口 <strong><span class="inline">SegmentInterface</span></strong>（<span class="mono">SegmentInterface.h:81</span>）抽象"一个段"，其下有两种实现：<strong>SegmentSealed</strong>（封存段，走加载好的 <strong>Knowhere 索引</strong>检索）与 <strong>SegmentGrowing</strong>（在长段，无索引，<strong>暴力</strong>逐条算）。列式/分块存储与 mmap 的细节是第八部分的专题。
</div>

<h2>segcore 是什么：单段检索的 C++ 内核</h2>
<p>先把 segcore 在整张地图上的位置钉死。回忆第 2 课的"三语言分工"：<strong>Go</strong> 管分布式与调度，<strong>C++</strong> 管单机的存储与计算，<strong>Rust</strong> 管全文索引。前面两课讲的 Proxy、delegator、QueryNode 调度，全在 <strong>Go</strong> 这一侧；而"<strong>在一个段里真刀真枪算向量距离、跑过滤</strong>"这件<strong>计算密集</strong>的活，落在 <strong>C++</strong> 的 segcore 上。它是 worker QueryNode "<strong>身体里</strong>"那台真正的检索发动机——上层千辛万苦地分片、路由、合并，最终都是为了把一个"在某段上检索"的请求，交到 segcore 手里执行。</p>

<p>补一句 segcore 的"业务面"：它不只服务<strong>向量搜索（Search）</strong>，也服务<strong>标量查询（Query / Retrieve）</strong>——即第 25 课提过的、"按条件取出满足的行"那条路。两者在 segcore 里共用同一套段抽象与过滤机制，区别只在最后一步是"<strong>做 ANN 取最像的 topK</strong>"还是"<strong>把命中行的字段取出来</strong>"。所以你可以把 segcore 理解成一台<strong>通用的单段执行器</strong>：上层给它一份计划，它在一个段的数据上把计划<strong>跑完</strong>，至于是搜还是查，只是计划里的算子不同。这也解释了为什么 <span class="inline">SegmentInterface</span> 上既有 <span class="inline">Search</span> 又有取字段、填主键之类的方法——它要同时撑起读路径上"<strong>搜</strong>"与"<strong>查</strong>"两类需求。</p>

<p>为什么这一层非要用 <strong>C++</strong>，不能像别的部分那样用 Go？因为这是<strong>性能最敏感的内循环</strong>：一次检索要在成千上万条向量上做距离计算、要紧贴 SIMD 指令与缓存、要精细管理大块内存与 mmap——这些都是 C++（以及它对接的 Knowhere、FAISS 等）的主场，而 Go 的运行时（GC、调度）在这种<strong>极致数值计算</strong>场景反而是负担。所以 Milvus 的取舍很清晰：<strong>分布式协调用 Go（开发快、并发友好），单机数值计算用 C++（榨干硬件）</strong>，两者各取所长。代价就是要在 Go 与 C++ 之间架一座桥——这座桥就是 <strong>cgo</strong>。</p>

<p>顺带把 segcore 和第 22 课的 <strong>Knowhere</strong> 摆到一起，免得混淆两者的边界。segcore 是"<strong>段的引擎</strong>"：它管一个段内的<strong>全套</strong>检索流程——接计划、过滤、调度、套用删除位图与时间过滤、组织结果。而当流程走到"<strong>纯粹的向量 ANN 计算</strong>"那一步（在 sealed 段上用 HNSW/IVF 找近邻），segcore 自己<strong>并不重写算法</strong>，而是<strong>调用 Knowhere</strong> 这个上游向量内核去算。换句话说：<strong>segcore 负责"段内的编排与正确性"，Knowhere 负责"索引结构与近邻计算"</strong>，前者调后者。再加上 growing 段那条不走索引的暴力路径，你就拼出了 segcore 段内检索的全貌：<strong>过滤 → （sealed 调 Knowhere 索引 / growing 暴力）→ 取 topK</strong>。把"谁编排、谁算 ANN"分清，第 22 与本课就不会打架。</p>

<p>多说一句这座桥的"<strong>窄</strong>"。Go 调 C++ 之所以要绕道一层<strong>纯 C 接口</strong>，根因是 cgo 只认 <strong>C 的 ABI</strong>（应用二进制接口）：C++ 的类、模板、命名空间、虚函数表这些，编译后名字会被"<strong>name mangling</strong>"打乱，Go 根本对不上号；而 C 函数的符号简单、稳定，是两种语言都能握手的<strong>最大公约数</strong>。所以 segcore 的对外门面 <span class="mono">segment_c.h</span> 里全是<strong>朴素的 C 函数</strong>，参数也尽量用基础类型与不透明指针——它像一道特意收窄的"<strong>闸口</strong>"，把复杂的 C++ 世界藏在身后，只留几个干净的把手给 Go 抓。理解这一点，你看 Milvus core 里大量 <span class="mono">*_c.h / *_c.cpp</span> 文件就不会困惑了：它们都是"<strong>给 Go 看的 C 门面</strong>"，背后才是真正干活的 C++ 实现。</p>

<h2>那道边界：Go 如何通过 cgo 调到 segcore</h2>
<p>把"Go 调 C++"这件事拆开看，它分四层，像剥洋葱一样从 Go 一直钻到 C++ 的段实现：</p>

<div class="layers">
  <div class="layer l-app"><span class="badge">Go</span><span class="name">LocalSegment（querynodev2/segments/segment.go）</span><span class="ld">Go 侧对"一个段"的封装；持有 C++ 段对象的不透明句柄；第 2 课见过它的 Search</span></div>
  <div class="layer l-part"><span class="badge">cgo / C API</span><span class="name">segment_c.h（NewSegment / AsyncSearch / DeleteSegment …）</span><span class="ld">纯 C 函数签名的"翻译窗口"；所有 Go↔C++ 往来必经此处；句柄类型 CSegmentInterface = void*</span></div>
  <div class="layer l-main"><span class="badge">C++ 接口</span><span class="name">SegmentInterface（SegmentInterface.h:81）</span><span class="ld">C API 背后真正的对象；用统一虚接口抽象"一个段"的检索/查询能力</span></div>
  <div class="layer l-core"><span class="badge">C++ 实现</span><span class="name">SegmentSealed（走索引） / SegmentGrowing（暴力）</span><span class="ld">两种段实现；sealed 用 Knowhere 索引、growing 逐条暴力算</span></div>
</div>

<p>逐层看这趟"下钻"：最上面，Go 的 <span class="inline">LocalSegment</span>（第 2 课就出现过的那个类型）是 worker 对"一个段"的本地代表，它的 <span class="inline">Search</span> 方法<strong>并不亲自算距离</strong>，而是把检索计划、查询向量、guarantee ts 等打包，<strong>通过 cgo 调一个 C 函数</strong>。中间一层 <span class="mono">segment_c.h</span> 就是那个"<strong>翻译窗口</strong>"：它声明了一组<strong>纯 C 函数</strong>（<span class="inline">NewSegment</span> 建段、<span class="inline">AsyncSearch</span> 检索、<span class="inline">DeleteSegment</span> 释放……），因为 cgo 只能跨"<strong>C 的 ABI</strong>"，C++ 的类与模板没法直接被 Go 看见，于是必须用一层 C 函数把 C++ 能力<strong>包一层</strong>暴露出来。这些 C 函数里，Go 看到的段只是一个 <span class="inline">CSegmentInterface</span>（本质是个 <span class="inline">void*</span> 不透明句柄）——Go 不知道、也不需要知道它背后是什么 C++ 对象。</p>

<p>再往里，C 函数把这个句柄<strong>转回真正的 C++ 对象</strong>——一个 <span class="inline">SegmentInterface</span>（<span class="mono">SegmentInterface.h:81</span> 那个虚接口），然后调它的 <span class="inline">Search</span> 等虚方法。到这里，控制权才真正进入 segcore 的算法世界。这趟跨语言调用的代价不可忽视：每次 cgo 调用都有固定开销，数据要在 Go 与 C++ 的内存表示间小心传递（不能让 Go 的 GC 动了 C++ 还在用的内存）。所以 Milvus 的设计有意让 cgo 边界<strong>粗粒度</strong>——一次调用就交给 C++ 一整段的检索，而不是在热循环里频繁来回穿越边界。<strong>记住这条边界的形状</strong>：Go 负责"<strong>调度与拼装</strong>"，C++ 负责"<strong>段内的真正计算</strong>"，中间隔着一道窄窄的、纯 C 的 <span class="mono">segment_c.h</span> 窗口。</p>

<h2>统一接口下的两副面孔：sealed vs growing</h2>
<p>跨过边界进了 C++，segcore 用<strong>同一套接口</strong>（<span class="inline">SegmentInterface</span>，及其内部接口）抽象"一个段"，但底下有<strong>两种实现</strong>，对应第 26 课那对老朋友——sealed 与 growing。它们检索的<strong>路子完全不同</strong>：</p>

<div class="cols">
  <div class="col"><h4>🧊 SegmentSealed → 走索引</h4><p>封存段已建好 <strong>Knowhere 向量索引</strong>（第 22 课，如 HNSW/IVF），并加载进内存。检索时<strong>不逐条扫</strong>，而是让索引带路——图索引几跳、或 IVF 只探最近几桶，<strong>跳过绝大多数向量</strong>，直接逼近最像的那一小撮。这是"<strong>快</strong>"的来源，也是数据主体的常态路径。</p></div>
  <div class="col"><h4>🔥 SegmentGrowing → 暴力扫</h4><p>在长段还<strong>没有索引</strong>（数据每刻在变，来不及建）。检索时只能<strong>暴力（brute force）</strong>：把查询向量和段内<strong>每一条</strong>向量都算一遍距离，再排序取 topK。因为 growing 段<strong>小</strong>、就在本地，这点暴力开销可以接受——它换来的是"<strong>刚写就能搜到</strong>"的新鲜。</p></div>
</div>

<p>这"<strong>同一接口、两种实现</strong>"的设计妙在哪？它让<strong>上层（delegator、worker 的调度代码）完全不必关心一个段到底带不带索引</strong>——它只管对每个段调同一个 <span class="inline">Search</span>，segcore 内部会按段的实际类型<strong>自动选择快路（索引）或慢路（暴力）</strong>。这是面向对象"<strong>多态</strong>"在系统设计里的经典用法：把"<strong>变化的部分</strong>"（怎么搜）封在实现里，对外只暴露"<strong>不变的契约</strong>"（给我一个段一张计划、还我段内 topK）。也正因如此，第 26 课 delegator 才能云淡风轻地说"把 sealed 和 growing 的结果合并"——在它眼里两者长得一样，差异被 segcore 这层<strong>悄悄吸收</strong>了。</p>

<p>还有一件 segcore 在段内默默替你做的事，常被忽略却很关键：<strong>剔除"不该看到的行"</strong>。一个段里的数据不是只有"插入"——还有<strong>删除</strong>（第 20 课）和<strong>时间戳</strong>（第 11 课）。segcore 检索时会<strong>结合两层过滤</strong>：一是<strong>删除位图</strong>，把已被删除的行标掉、不计入候选；二是 <strong>guarantee ts</strong> 带来的<strong>时间过滤</strong>，只让 ts ≤ guarantee 的那一版数据可见。换句话说，<strong>MVCC（多版本可见性）最终落地的执行点，就在 segcore 这一层</strong>：上层把 guarantee ts 一路传下来，真正"按这个时间快照决定每一行可不可见"的判定，是在段内、贴着数据完成的。所以你不会搜到"刚被删的"或"晚于你时间快照才写入的"行——这层正确性，正是 sealed/growing 之外，segcore 段内逻辑的另一半职责（完整的一致性与 MVCC 第 30 课收口）。</p>

<h2>一次段内检索：从计划到段内 topK</h2>
<p>把 segcore 在<strong>一个段里</strong>处理一次检索的动作摆开（以带过滤的 sealed 段为例），就是下面这条短链。注意它正是第 25 课那张 plan 在最底层被<strong>真正执行</strong>的地方：</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>接收计划与查询向量</h4><p>经 C API 进来一份 <strong>检索计划</strong>（plan：向量字段 + 度量 + topK + 标量谓词）、<strong>查询向量</strong>（placeholder）、以及 <strong>guarantee ts</strong>。segcore 在这一个段的范围内执行它。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>标量过滤 → bitset</h4><p>先按计划里的<strong>标量谓词</strong>（如 <span class="mono">year &gt; 2020</span>）在段内算出一张<strong>位掩码（bitset）</strong>：标出"哪些行合格"。这一步把候选范围<strong>先缩小</strong>（第 24 课的"先筛后搜"、第 28 课详述执行引擎）。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>向量检索（索引 / 暴力）</h4><p>在合格子集上做 ANN：<strong>sealed</strong> 让 <strong>Knowhere 索引</strong>带路、跳过大半；<strong>growing</strong> 则对合格行<strong>逐条暴力</strong>算距离。按度量（L2/IP/COSINE）算出相似度。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>段内取 topK 回传</h4><p>把本段算出的候选<strong>排序、取最像的 topK</strong>，作为<strong>段内局部结果</strong>经 C API 交回 Go 侧。它将参与 delegator 的节点内归并（第 26 课）——这就是"<strong>三级 reduce</strong>"最底下那一级。</p></div></div>
</div>

<p>这条链把整条查询链路<strong>收口</strong>了：第 25 课 Proxy 编出的那张 plan，一路下发、穿过 delegator、跨过 cgo 边界，<strong>终于在 segcore 这里被真正跑起来</strong>。而 segcore 吐出的"段内 topK"，又会反向<strong>逐级归并</strong>上去——段内 topK（这里）→ delegator 节点内合并（第 26 课）→ Proxy 跨分片合并（第 25 课）。你现在应该能把一次 search 的"<strong>下行扇出</strong>"和"<strong>上行归并</strong>"完整地在脑子里画一遍了。其中第 2、3 步"<strong>先用谓词筛出 bitset、再在子集上做 ANN</strong>"的执行细节（计划树、表达式、向量化算子），是第 28 课"执行引擎"的主题；而段内数据为什么是<strong>列式、分块、可 mmap</strong> 的，则留到第八部分深挖。本课你只要牢牢记住这一层的边界与分工。</p>

<p>最后留一个"<strong>往下看</strong>"的钩子。本课刻意没展开两件事，它们各有专属篇章。其一是"<strong>计划到底怎么在段内执行</strong>"：那张 plan 进了 segcore 后，标量谓词会被编成一棵<strong>表达式树</strong>、由一套<strong>向量化执行引擎</strong>逐算子跑出来（先过滤、再向量检索），这是第 28 课的主题。其二是"<strong>段内的数据长什么样</strong>"：为什么向量与标量在段里是<strong>列式、分块</strong>存放的，为什么可以 <strong>mmap</strong>（把磁盘文件映射成内存、按需换入）从而服务远超内存的数据——这套存储细节是第八部分的专题。本课把"<strong>谁在算、隔着哪道边界、两类段各走什么路</strong>"立住，后面两处深挖才有地基。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/segcore/SegmentInterface.h</span><span class="ln">第 81 行起：C API 背后统一的段接口（节选示意）</span></div>
  <pre><span class="cm">// 被 C API 使用的、SegmentSealed 与 SegmentGrowing 的公共接口</span>
<span class="kw">class</span> <span class="nb">SegmentInterface</span> {
 <span class="kw">public</span>:
    <span class="kw">virtual</span> ~SegmentInterface() = <span class="kw">default</span>;
    <span class="cm">// 在“这一个段”内执行检索：吃一份 plan + 查询向量，吐段内结果</span>
    <span class="kw">virtual</span> std::unique_ptr&lt;SearchResult&gt;
    <span class="fn">Search</span>(<span class="kw">const</span> query::Plan* plan,
           <span class="kw">const</span> query::PlaceholderGroup* placeholder, ...) <span class="kw">const</span> = <span class="nb">0</span>;
    <span class="cm">// … FillPrimaryKeys / FillTargetEntry 等省略 …</span>
};
<span class="cm">// 两种实现：SegmentSealed（走 Knowhere 索引）/ SegmentGrowing（暴力逐条）</span>
<span class="cm">// Go 经 cgo 调入：segment_c.h 的 NewSegment / AsyncSearch / DeleteSegment</span>
<span class="cm">//                 ←→ Go 侧 LocalSegment（querynodev2/segments/segment.go）</span></pre>
</div>

<p>把整个第六部分上半段串起来：第 25 课，Proxy 把搜索<strong>翻译成 plan、定好 guarantee ts、扇到各分片</strong>；第 26 课，delegator 在分片内<strong>覆盖 sealed+growing、扇到 worker、节点内归并</strong>；这一课，worker 通过 <strong>cgo</strong> 把"段内检索"交给 C++ 的 <strong>segcore</strong>，由它用<strong>统一接口</strong>对 sealed 走索引、对 growing 走暴力，算出<strong>段内 topK</strong>。下半段（第 28–30 课，后续派发）会接着深挖：plan 在 segcore 里<strong>具体怎么执行</strong>（执行引擎）、三级 reduce <strong>怎么归并</strong>、以及 guarantee ts 与 MVCC <strong>如何兑现一致性</strong>。把这上半段连成一句话记牢：<strong>一次搜索，就是一张计划从 Proxy 出发、经 delegator 扇到段、跨 cgo 进 segcore 被执行，再把段内 topK 逐级归并回来的旅程</strong>——而 segcore，就是这趟旅程<strong>最深处那台真正干活的发动机</strong>。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>segcore = C++ 单段检索引擎</strong>：只在"一个 segment 内部"执行检索/查询，不懂分片/副本/WAL；是 worker 体内真正算向量的发动机。</li>
    <li><strong>cgo 边界</strong>：Go 的 <span class="inline">LocalSegment</span>（<span class="mono">segments/segment.go</span>）经纯 C 的 <span class="mono">segment_c.h</span>（<span class="inline">NewSegment/AsyncSearch/DeleteSegment</span>）调进 C++；段在 Go 侧只是个不透明句柄。</li>
    <li><strong>统一接口</strong>：<span class="inline">SegmentInterface</span>（<span class="mono">SegmentInterface.h:81</span>）抽象"一个段"，下有 <strong>SegmentSealed</strong> 与 <strong>SegmentGrowing</strong> 两种实现（多态）。</li>
    <li><strong>sealed = 索引、growing = 暴力</strong>：封存段走加载好的 Knowhere 索引（快）；在长段无索引、逐条暴力算（保新鲜）。</li>
    <li><strong>段内一次检索</strong>：收 plan → 标量过滤出 bitset → 子集上做 ANN（索引/暴力）→ 取段内 topK 回传，是三级 reduce 最底层。</li>
    <li><strong>为什么用 C++</strong>：性能敏感的内循环（SIMD/缓存/mmap）是 C++ 主场；Go 管调度、C++ 管计算，cgo 边界刻意粗粒度。列式/分块/mmap 见第八部分。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The last two lessons sent the request from the Proxy out to shards, then from the delegator out to individual segments, routed to the worker holding each. Now we stand at the <strong>innermost layer</strong>: a worker has one segment and one search plan — how exactly does it <strong>find the few most-alike rows inside this one segment</strong>?
The answer crosses a language boundary, because the engine that actually does this compute-heavy work is not Go but a C++ search kernel, <strong>segcore</strong>. This lesson steps into segcore: what it is, how Go calls it over <strong>cgo</strong>, and how it uses one unified interface (<span class="inline">SegmentInterface</span>) to serve both the <strong>indexed sealed</strong> segments and the <strong>brute-force growing</strong> segments.
This is the <strong>deepest layer</strong> of the whole query path and the <strong>finale</strong> of Part 6's first half (Lessons 25-27): here, the search plan handed down all the way from the Proxy finally "<strong>hits bottom</strong>" and is executed on real vector data.
</p>

<div class="card analogy">
  <div class="tag">📮 Analogy</div>
  Picture a research archive with a <strong>senior retrieval specialist</strong> who only speaks <strong>"C++"</strong> (segcore), extremely fast, whose sole job is "find the few files most like a sample <strong>within one archive room</strong>." But the <strong>dispatch manager</strong> upstairs who issues orders only speaks <strong>"Go"</strong> (the QueryNode). They don't share a language — how do they cooperate?
  Through a <strong>fixed translation window</strong> at the archive's entrance (<strong>cgo / the C API</strong>): the manager writes the request as a <strong>standard work order</strong> and slips it through the window, which translates it into C++ for the specialist; the specialist searches and the result comes back out through the window. <strong>All exchange must go through this window</strong>, never by shouting directly — that is the Go↔C++ boundary.
  And the specialist's rooms come in two kinds: one is a stockroom <strong>long since organized with a card catalog</strong> (<strong>sealed + index</strong>), where the catalog jumps you straight to the right shelf, blazing fast; the other is loose material <strong>that arrived today, still piled in the inbox</strong> (<strong>growing</strong>), with no catalog, so you must <strong>read each sheet one by one</strong> (brute-force scan), though luckily it's small. Outwardly the specialist offers <strong>one and the same retrieval method</strong>, but internally picks the fast or slow path by "<strong>is there a catalog</strong>" — exactly how segcore's <span class="inline">SegmentInterface</span> covers both sealed and growing. Whichever room, the specialist delivers the same sentence: "<strong>here are the few in this room most like your sample</strong>" — the inner fast/slow difference need not concern the outsider.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  <strong>segcore</strong> is Milvus's "<strong>single-segment search engine</strong>" written in <strong>C++</strong>: it only "<strong>executes search/query inside one segment</strong>," knowing nothing of shards, replicas, or the WAL. The Go-side QueryNode calls it across languages via <strong>cgo</strong>: Go's <span class="inline">LocalSegment</span> (<span class="mono">internal/querynodev2/segments/segment.go</span>, seen in Lesson 2) holds an <strong>opaque handle</strong> to a C++ segment object and calls in through a <strong>C API</strong> (<span class="mono">internal/core/src/segcore/segment_c.h</span>, e.g. <span class="inline">NewSegment</span> / <span class="inline">AsyncSearch</span> / <span class="inline">DeleteSegment</span>). Inside C++, a unified interface <strong><span class="inline">SegmentInterface</span></strong> (<span class="mono">SegmentInterface.h:81</span>) abstracts "a segment," with two implementations: <strong>SegmentSealed</strong> (sealed, searches via the loaded <strong>Knowhere index</strong>) and <strong>SegmentGrowing</strong> (growing, no index, <strong>brute-force</strong> per row). Columnar/chunked storage and mmap are a Part 8 topic.
</div>

<h2>What segcore is: the C++ kernel of single-segment search</h2>
<p>First, pin segcore's place on the map. Recall Lesson 2's "three-language split": <strong>Go</strong> handles distribution and scheduling, <strong>C++</strong> handles single-machine storage and compute, <strong>Rust</strong> handles full-text indexing. The Proxy, delegator, and QueryNode scheduling of the past two lessons all live on the <strong>Go</strong> side; the <strong>compute-intensive</strong> work of "<strong>actually computing vector distances and running filters within a segment</strong>" lands on C++'s segcore. It is the real search engine "<strong>inside the body</strong>" of a worker QueryNode — all the painstaking sharding, routing, and merging upstream ultimately exists to hand a "search on some segment" request to segcore to execute.</p>

<p>One more "business face" of segcore: it serves not only <strong>vector search (Search)</strong> but also <strong>scalar query (Query / Retrieve)</strong> — the "fetch rows satisfying a condition" path mentioned in Lesson 25. Both share the same segment abstraction and filtering machinery in segcore; they differ only in the last step: "<strong>do ANN and take the most-alike topK</strong>" versus "<strong>pull out the fields of the matched rows</strong>." So you can think of segcore as a <strong>general single-segment executor</strong>: upstream hands it a plan and it <strong>runs the plan to completion</strong> on one segment's data; whether it searches or queries is just a different operator in the plan. That is also why <span class="inline">SegmentInterface</span> has both <span class="inline">Search</span> and methods to fetch fields and fill primary keys — it must hold up both "<strong>search</strong>" and "<strong>query</strong>" needs on the read path.</p>

<p>Why must this layer be <strong>C++</strong> rather than Go like the rest? Because this is the <strong>most performance-sensitive inner loop</strong>: a search computes distances over thousands upon thousands of vectors, hugs SIMD instructions and the cache, and finely manages large memory blocks and mmap — all home turf for C++ (and the Knowhere/FAISS it wraps), whereas Go's runtime (GC, scheduling) is a burden in such <strong>extreme numerical computing</strong>. So Milvus's tradeoff is clear: <strong>distributed coordination in Go (fast to develop, concurrency-friendly), single-machine numerical compute in C++ (squeeze the hardware)</strong>, each playing to its strength. The price is a bridge between Go and C++ — that bridge is <strong>cgo</strong>.</p>

<p>While we're here, set segcore beside Lesson 22's <strong>Knowhere</strong> so their boundary isn't blurred. segcore is the "<strong>segment engine</strong>": it runs the <strong>whole</strong> in-segment retrieval flow — take the plan, filter, schedule, apply the delete bitmap and time filter, organize results. But when the flow reaches "<strong>the pure vector ANN compute</strong>" step (finding neighbors with HNSW/IVF on a sealed segment), segcore does <strong>not</strong> reimplement the algorithm; it <strong>calls Knowhere</strong>, the upstream vector kernel, to compute. In other words: <strong>segcore owns "in-segment orchestration and correctness," Knowhere owns "index structures and neighbor computation,"</strong> the former calling the latter. Add the no-index brute-force path of growing segments and you have the full picture of segcore's in-segment search: <strong>filter → (sealed calls the Knowhere index / growing brute-forces) → take topK</strong>. Tell apart "who orchestrates, who computes ANN" and Lessons 22 and 27 won't clash.</p>

<h2>That boundary: how Go calls segcore over cgo</h2>
<p>Unpack "Go calls C++" and it has four layers, peeling like an onion from Go all the way down to the C++ segment implementation:</p>

<div class="layers">
  <div class="layer l-app"><span class="badge">Go</span><span class="name">LocalSegment (querynodev2/segments/segment.go)</span><span class="ld">Go's wrapper for "a segment"; holds an opaque handle to the C++ segment object; its Search appeared in Lesson 2</span></div>
  <div class="layer l-part"><span class="badge">cgo / C API</span><span class="name">segment_c.h (NewSegment / AsyncSearch / DeleteSegment …)</span><span class="ld">a "translation window" of pure-C signatures; all Go↔C++ exchange passes here; handle type CSegmentInterface = void*</span></div>
  <div class="layer l-main"><span class="badge">C++ interface</span><span class="name">SegmentInterface (SegmentInterface.h:81)</span><span class="ld">the real object behind the C API; a unified virtual interface abstracting a segment's search/query ability</span></div>
  <div class="layer l-core"><span class="badge">C++ impls</span><span class="name">SegmentSealed (via index) / SegmentGrowing (brute force)</span><span class="ld">two segment impls; sealed uses the Knowhere index, growing computes per row</span></div>
</div>

<p>Layer by layer down this "descent": at the top, Go's <span class="inline">LocalSegment</span> (the type that appeared back in Lesson 2) is the worker's local stand-in for "a segment," and its <span class="inline">Search</span> method <strong>does not compute distances itself</strong> — it packs the plan, query vectors, guarantee ts, etc. and <strong>calls a C function over cgo</strong>. The middle layer <span class="mono">segment_c.h</span> is that "<strong>translation window</strong>": it declares a set of <strong>pure-C functions</strong> (<span class="inline">NewSegment</span> to build, <span class="inline">AsyncSearch</span> to search, <span class="inline">DeleteSegment</span> to release…), because cgo can only cross "<strong>C's ABI</strong>" — C++ classes and templates are invisible to Go, so C++ ability must be <strong>wrapped</strong> in a layer of C functions. In these C functions, the segment Go sees is merely a <span class="inline">CSegmentInterface</span> (essentially a <span class="inline">void*</span> opaque handle) — Go neither knows nor needs to know what C++ object backs it.</p>

<p>One more word on how <strong>narrow</strong> this bridge is. Go calls C++ by detouring through a <strong>pure-C interface</strong> fundamentally because cgo only recognizes <strong>C's ABI</strong> (application binary interface): C++ classes, templates, namespaces, and vtables get their names scrambled by <strong>name mangling</strong> after compilation, which Go cannot match; whereas C function symbols are simple and stable, the <strong>greatest common denominator</strong> both languages can shake hands on. So segcore's outward facade <span class="mono">segment_c.h</span> is all <strong>plain C functions</strong>, with parameters kept to basic types and opaque pointers — like a deliberately narrowed "<strong>sluice gate</strong>" that hides the complex C++ world behind it and leaves Go only a few clean handles to grab. Grasp this and the many <span class="mono">*_c.h / *_c.cpp</span> files in Milvus core stop being confusing: they are all "<strong>C facades for Go to see</strong>," with the real working C++ implementation behind them.</p>

<p>Deeper still, the C function <strong>casts the handle back into the real C++ object</strong> — a <span class="inline">SegmentInterface</span> (that virtual interface at <span class="mono">SegmentInterface.h:81</span>) — and calls its <span class="inline">Search</span> and other virtual methods. Only here does control truly enter segcore's algorithmic world. The cost of this cross-language call is not negligible: every cgo call has a fixed overhead, and data must be passed carefully between Go's and C++'s memory representations (Go's GC must not move memory C++ is still using). So Milvus deliberately keeps the cgo boundary <strong>coarse-grained</strong> — one call hands C++ a whole segment's search, rather than crossing the boundary repeatedly in a hot loop. <strong>Remember the shape of this boundary</strong>: Go handles "<strong>scheduling and assembly</strong>," C++ handles "<strong>the real in-segment compute</strong>," with a narrow, pure-C <span class="mono">segment_c.h</span> window between them.</p>

<h2>Two faces under one interface: sealed vs growing</h2>
<p>Across the boundary and into C++, segcore abstracts "a segment" with <strong>one interface</strong> (<span class="inline">SegmentInterface</span> and its internal interface), but underneath there are <strong>two implementations</strong>, matching the old friends from Lesson 26 — sealed and growing. Their retrieval <strong>routes differ completely</strong>:</p>

<div class="cols">
  <div class="col"><h4>🧊 SegmentSealed → via index</h4><p>A sealed segment has a built <strong>Knowhere vector index</strong> (Lesson 22, e.g. HNSW/IVF) loaded into memory. Search does <strong>not scan row by row</strong> but lets the index lead — a few graph hops, or IVF probing only the nearest buckets, <strong>skipping the vast majority</strong> of vectors to home in on the most-alike few. This is the source of "<strong>fast</strong>," the normal path for the data bulk.</p></div>
  <div class="col"><h4>🔥 SegmentGrowing → brute force</h4><p>A growing segment has <strong>no index yet</strong> (data changes every moment, no time to index). Search can only go <strong>brute force</strong>: compute distance between the query vector and <strong>every</strong> vector in the segment, then sort and take topK. Since growing segments are <strong>small</strong> and local, this brute-force cost is acceptable — in return for the freshness of "<strong>searchable right after writing</strong>."</p></div>
</div>

<p>What makes this "<strong>one interface, two implementations</strong>" design clever? It lets <strong>the upper layers (the delegator's and worker's scheduling code) be wholly unconcerned with whether a segment has an index</strong> — they just call the same <span class="inline">Search</span> on each segment, and segcore internally <strong>picks the fast path (index) or slow path (brute force) by the segment's actual type</strong>. This is the classic use of object-oriented "<strong>polymorphism</strong>" in systems design: seal "<strong>what varies</strong>" (how to search) inside the implementations and expose only "<strong>the unchanging contract</strong>" (give me a segment and a plan, get back the segment's topK). Precisely because of this, Lesson 26's delegator could airily say "merge the sealed and growing results" — in its eyes the two look alike, the difference <strong>quietly absorbed</strong> by the segcore layer.</p>

<p>There's one more thing segcore silently does for you inside a segment, often overlooked yet crucial: <strong>excluding "rows you shouldn't see."</strong> A segment's data isn't only "inserts" — there are also <strong>deletes</strong> (Lesson 20) and <strong>timestamps</strong> (Lesson 11). When searching, segcore <strong>applies two filters</strong>: one, a <strong>delete bitmap</strong> marking out already-deleted rows so they don't count as candidates; two, the <strong>time filter</strong> brought by the <strong>guarantee ts</strong>, making visible only the version with ts ≤ guarantee. In other words, <strong>the execution point where MVCC (multi-version visibility) finally lands is this segcore layer</strong>: upper layers pass the guarantee ts all the way down, and the actual judgment of "per this snapshot, is each row visible" happens in the segment, hugging the data. So you won't search up "just-deleted" rows or rows "written later than your snapshot" — this correctness is, beyond sealed/growing, the other half of segcore's in-segment logic (full consistency and MVCC are tied up in Lesson 30).</p>

<h2>One in-segment search: from plan to a segment's topK</h2>
<p>Lay out segcore's moves for one search <strong>inside a segment</strong> (take a filtered sealed segment) and you get this short chain. Note it is exactly where Lesson 25's plan is <strong>actually executed</strong> at the bottom:</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Receive plan and query vectors</h4><p>In through the C API come a <strong>search plan</strong> (plan: vector field + metric + topK + scalar predicate), the <strong>query vectors</strong> (placeholder), and the <strong>guarantee ts</strong>. segcore executes it within the scope of this one segment.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Scalar filter → bitset</h4><p>First, by the plan's <strong>scalar predicate</strong> (e.g. <span class="mono">year &gt; 2020</span>), compute a <strong>bitset</strong> within the segment marking "which rows qualify." This <strong>narrows</strong> the candidate set first (Lesson 24's filter-then-search; the execution engine is detailed in Lesson 28).</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Vector search (index / brute force)</h4><p>Do ANN over the qualifying subset: <strong>sealed</strong> lets the <strong>Knowhere index</strong> lead and skip most; <strong>growing</strong> <strong>brute-forces</strong> distances over the qualifying rows. Compute similarity by the metric (L2/IP/COSINE).</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Take the segment's topK, return</h4><p><strong>Sort the candidates computed in this segment and take the most-alike topK</strong>, returning it as the <strong>segment's local result</strong> through the C API to Go. It joins the delegator's node-level merge (Lesson 26) — the bottom level of the "<strong>three-level reduce</strong>."</p></div></div>
</div>

<p>This chain <strong>ties off</strong> the whole query path: the plan the Proxy compiled in Lesson 25, handed down, through the delegator, across the cgo boundary, is <strong>finally run for real here in segcore</strong>. And the "segment topK" segcore emits is then <strong>merged level by level</strong> back up — segment topK (here) → delegator node-level merge (Lesson 26) → Proxy cross-shard merge (Lesson 25). You should now be able to picture a search's "<strong>downward fan-out</strong>" and "<strong>upward merge</strong>" end to end in your head. The execution detail of steps 2-3 "<strong>filter into a bitset, then do ANN over the subset</strong>" (the plan tree, expressions, vectorized operators) is the subject of Lesson 28's "execution engine"; why in-segment data is <strong>columnar, chunked, and mmap-able</strong> is dug into in Part 8. For this lesson, just firmly remember this layer's boundary and division of labor.</p>

<p>Finally, leave a hook to "<strong>look further down.</strong>" This lesson deliberately left two things unexpanded, each with its own chapter. One is "<strong>how the plan actually executes in a segment</strong>": once the plan enters segcore, the scalar predicate is compiled into an <strong>expression tree</strong> and run operator by operator by a <strong>vectorized execution engine</strong> (filter first, then vector search) — the subject of Lesson 28. The other is "<strong>what in-segment data looks like</strong>": why vectors and scalars are stored <strong>columnar and chunked</strong> in a segment, and why they can be <strong>mmap</strong>-ed (mapping disk files as memory, paged in on demand) to serve data far larger than RAM — these storage details are a Part 8 topic. This lesson establishes "<strong>who computes, across which boundary, and what path each kind of segment takes</strong>"; only then do those two deep dives have a foundation.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/segcore/SegmentInterface.h</span><span class="ln">from line 81: the unified segment interface behind the C API (sketch)</span></div>
  <pre><span class="cm">// common interface of SegmentSealed and SegmentGrowing used by the C API</span>
<span class="kw">class</span> <span class="nb">SegmentInterface</span> {
 <span class="kw">public</span>:
    <span class="kw">virtual</span> ~SegmentInterface() = <span class="kw">default</span>;
    <span class="cm">// run a search within "this one segment": eat a plan + query vectors, emit the segment's result</span>
    <span class="kw">virtual</span> std::unique_ptr&lt;SearchResult&gt;
    <span class="fn">Search</span>(<span class="kw">const</span> query::Plan* plan,
           <span class="kw">const</span> query::PlaceholderGroup* placeholder, ...) <span class="kw">const</span> = <span class="nb">0</span>;
    <span class="cm">// … FillPrimaryKeys / FillTargetEntry etc. omitted …</span>
};
<span class="cm">// two impls: SegmentSealed (via Knowhere index) / SegmentGrowing (brute force per row)</span>
<span class="cm">// Go calls in over cgo: segment_c.h's NewSegment / AsyncSearch / DeleteSegment</span>
<span class="cm">//                 ←→ Go-side LocalSegment (querynodev2/segments/segment.go)</span></pre>
</div>

<p>Stitch the whole first half of Part 6 together: in Lesson 25, the Proxy <strong>translated the search into a plan, fixed the guarantee ts, and fanned it to shards</strong>; in Lesson 26, the delegator, within a shard, <strong>covered sealed+growing, fanned to workers, and merged within the node</strong>; in this lesson, the worker, over <strong>cgo</strong>, handed "in-segment search" to C++'s <strong>segcore</strong>, which uses a <strong>unified interface</strong> to take the index route for sealed and the brute-force route for growing, computing a <strong>segment topK</strong>. The second half (Lessons 28-30, dispatched later) digs deeper: how the plan <strong>actually executes</strong> inside segcore (the execution engine), how the three-level reduce <strong>merges</strong>, and how guarantee ts and MVCC <strong>redeem consistency</strong>. Remember this first half as one sentence: <strong>a search is the journey of one plan setting out from the Proxy, fanned through the delegator to segments, crossing cgo into segcore to be executed, then merged level by level back as segment topKs</strong> — and segcore is <strong>the real working engine at the deepest point of that journey.</strong></p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>segcore = the C++ single-segment search engine</strong>: executes search/query only "inside one segment," knowing nothing of shards/replicas/WAL; the real vector-computing engine inside a worker.</li>
    <li><strong>the cgo boundary</strong>: Go's <span class="inline">LocalSegment</span> (<span class="mono">segments/segment.go</span>) calls into C++ through pure-C <span class="mono">segment_c.h</span> (<span class="inline">NewSegment/AsyncSearch/DeleteSegment</span>); a segment is just an opaque handle on the Go side.</li>
    <li><strong>unified interface</strong>: <span class="inline">SegmentInterface</span> (<span class="mono">SegmentInterface.h:81</span>) abstracts "a segment," with <strong>SegmentSealed</strong> and <strong>SegmentGrowing</strong> implementations (polymorphism).</li>
    <li><strong>sealed = index, growing = brute force</strong>: sealed searches via the loaded Knowhere index (fast); growing has no index and computes per row (keeps fresh).</li>
    <li><strong>one in-segment search</strong>: receive plan → scalar-filter into a bitset → ANN over the subset (index/brute force) → take the segment's topK and return; the bottom of the three-level reduce.</li>
    <li><strong>why C++</strong>: the performance-sensitive inner loop (SIMD/cache/mmap) is C++'s turf; Go schedules, C++ computes, the cgo boundary kept deliberately coarse. Columnar/chunked/mmap in Part 8.</li>
  </ul>
</div>
""",
}


LESSON_28 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课我们钻进 segcore，看清一个段内部怎么搜。但真实查询往往是<strong>"带条件的搜索"</strong>——既要<strong>向量相似</strong>，
又要<strong>满足标量过滤</strong>（比如 <span class="inline">price &lt; 500 &amp;&amp; category == "shoes"</span>）。这一课看 Milvus 的
C++ 内核怎么把过滤<strong>高效地</strong>跑起来：先把过滤条件编译成一棵<strong>表达式树</strong>，再用<strong>向量化执行引擎</strong>在
列式分块上<strong>批量</strong>求值，先筛出合格行、剪掉其余，最后只在合格集合里做向量检索。这一步看不见、却决定了"<strong>带条件的相似检索</strong>"到底快不快、准不准。
它由 C++ 内核里的两个目录撑起：<span class="mono">expr</span>（表达式）与 <span class="mono">exec</span>（执行），是 Milvus 把"数据库执行引擎"
缝进"向量检索"的关键一环。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把它想成工厂的<strong>"质检 + 精装"</strong>流水线：先让质检员按规格（过滤条件）在传送带（列式分块）上飞快地挑出合格件，
  做个<strong>合格清单</strong>（bitset）；只有清单上的件才送去最贵的<strong>精装工序</strong>（向量检索）。不合格的早早剔除，
  就不必为它们付出后面最贵的成本——这正是"<strong>先过滤、再检索</strong>"省时的道理。质检员还有个聪明做法：如果货架上贴了<strong>标签目录</strong>（标量索引），
他不用把每件都翻一遍，直接照目录就能挑出合格件；没有目录时，才老老实实一件件过。Milvus 的过滤也是如此——有索引走索引，没索引才全扫。
而"质检"用的不是肉眼一件件看，而是<strong>一整批一起量</strong>（向量化）：把同一规格的尺子按在一排零件上一次量完，比逐个量快上几十倍。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：<strong>过滤字符串 → 逻辑表达式树（expr）→ 向量化执行引擎（exec）在分块上求值出一个 bitset → 用 bitset 剪枝向量检索</strong>。
  "<strong>先过滤、再检索</strong>"（filter-then-search）是混合查询又快又准的关键；表达式与执行分属 <span class="mono">expr</span> 与
  <span class="mono">exec</span> 两层，前者描述"算什么"，后者负责"怎么快速算"。这套机制让 Milvus 既能<strong>按相似度找</strong>，又能<strong>按条件筛</strong>，
  而不必在二者之间二选一——这正是"向量数据库"区别于"纯向量检索库"的又一处底气。
</div>

<h2>从过滤字符串到表达式树</h2>
<p>用户写下的布尔过滤（一个字符串）不会被原样执行。它先经语法解析，变成一棵<strong>逻辑表达式树</strong>——在 C++ 内核里就是
<span class="inline">expr</span> 里的 <span class="mono">ITypeExpr</span> 体系。树的<strong>叶子</strong>是字段引用（列）与常量，<strong>内部节点</strong>
是比较（<span class="mono">&lt;</span>/<span class="mono">==</span>）、逻辑（<span class="mono">AND</span>/<span class="mono">OR</span>/<span class="mono">NOT</span>）
与算术运算。把条件变成树，引擎才能逐节点、按类型地高效求值，也方便做常量折叠、短路等优化。</p>

<p>为什么非要先建一棵树，而不是"边读字符串边算"？因为<strong>解析只做一次、执行要做千万次</strong>。把过滤编译成结构化的树后，
引擎可以对<strong>每一段、每一块数据反复复用同一棵树</strong>，省去重复解析的开销；还能在编译期做优化——比如把恒为真的子条件
（<span class="inline">AlwaysTrueExpr</span>）直接短路、把常量提前算好、把范围比较合并。更重要的是，<strong>树的结构天然适配"按列、按块"的向量化执行</strong>：
每个节点都知道自己要在哪一列上、用什么运算去批量求值。这是把"一句话过滤"变成"能在十亿行上飞快跑"的第一步。</p>

<p>具体看一棵树怎么"走"：<span class="inline">price &lt; 500 &amp;&amp; category == "shoes"</span> 的根是一个 <strong>AND</strong> 逻辑节点，
它有两个孩子——左边是 <strong>Compare(LT)</strong>（小于），其下挂着列引用 <span class="mono">price</span> 与常量 <span class="mono">500</span>；
右边是 <strong>Compare(EQ)</strong>（等于），挂着 <span class="mono">category</span> 与 <span class="mono">"shoes"</span>。求值时引擎自底向上：
先各自算出两个比较的结果（每个都是一列 bool），再让 AND 把两列<strong>按位与</strong>合并成最终掩码。<strong>类型在这里很关键</strong>——
每个节点都带着自己的结果类型（数值、布尔、字符串…），引擎据此选对应的向量化算法；类型不匹配会在编译期就报错，而不是等到跑了一半才崩。
正因为结构和类型都明确，同一棵树才能被安全地<strong>编译成机器友好的物理算子</strong>。</p>

<p>把过滤建成树还有一层好处：<strong>优化都能在树上做</strong>。引擎可以把恒为真的子树（<span class="inline">AlwaysTrueExpr</span>）整段省掉、
把常量表达式提前折叠成一个值、把"<span class="inline">a &gt; 3 AND a &lt; 8</span>"这种对同一列的两个比较合并成一次区间判断
（这正是 <span class="inline">BinaryArithOpEvalRangeExpr</span> 这类算子的用武之地）。短路也在树上发生：AND 的左孩子若整块都为假，右孩子那一块就不必再算。
这些优化看似琐碎，但当它们作用在<strong>每个段、每一块、每一次查询</strong>上时，省下的就是实打实的延迟与 CPU。</p>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">字符串</span><span class="name">price &lt; 500 &amp;&amp; category == "shoes"</span></div><div class="ld">用户写的过滤表达式（DSL）</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">解析</span><span class="name">parse</span></div><div class="ld">语法解析 + 绑定字段 / 类型检查</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">逻辑树</span><span class="name">ITypeExpr</span></div><div class="ld">AND( price&lt;500 , category=="shoes" )——叶子是列/常量，内部是运算</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">物理算子</span><span class="name">exec/expression</span></div><div class="ld">编译成可在分块上批量求值的物理算子</div></div>
</div>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/expr/ITypeExpr.h</span><span class="ln">逻辑表达式树的基类（节选示意）</span></div>
  <pre><span class="kw">class</span> ITypeExpr {                 <span class="cm">// 逻辑表达式节点的基类</span>
    <span class="cm">// 一棵树：内部节点持有子表达式，叶子是列引用/常量</span>
    <span class="kw">const</span> std::vector&lt;std::shared_ptr&lt;ITypeExpr&gt;&gt;&amp; inputs() <span class="kw">const</span>;
    <span class="kw">virtual</span> DataType type() <span class="kw">const</span>;     <span class="cm">// 结果类型（bool / 数值…）</span>
};
<span class="cm">// 过滤 price &lt; 500 &amp;&amp; category == "shoes" 会被建成：</span>
<span class="cm">//   LogicalBinary(AND, Compare(LT, col(price), 500),</span>
<span class="cm">//                      Compare(EQ, col(category), "shoes"))</span></pre>
</div>

<h2>向量化执行引擎：一块一块地算</h2>
<p>有了逻辑树，<strong>执行引擎</strong>（<span class="inline">exec</span>，含 <span class="mono">Task</span> / <span class="mono">Driver</span> /
<span class="mono">QueryContext</span>）把它编译成<strong>物理算子</strong>（<span class="mono">exec/expression</span> 下的各种 Expr），
然后在<strong>列式分块（chunk）</strong>上<strong>批量、向量化</strong>地求值——不是一行一行地算，而是<strong>一块一块</strong>地算，
充分利用 CPU 的 SIMD。求值的产物是一个 <strong>bitset</strong>：每行对应 1 个 bit，标记它<strong>满足 / 不满足</strong>整个过滤条件。</p>

<p><strong>"向量化 + 分块"为什么快？</strong>关键在于<strong>把按行的零散计算，变成按列的批量计算</strong>。传统的逐行求值，每处理一行都要走一遍
表达式树、做一次虚函数调用、跳一次分支，CPU 的流水线和缓存全被打断；而向量化执行<strong>对一整块（chunk）里成百上千个同列的值
做同一种运算</strong>，既能用上 <span class="mono">SIMD</span>（一条指令算多个数）、又对缓存友好（数据在内存里连续）、还几乎没有分支预测失败。
<strong>分块（chunk）</strong>还顺带解决了内存问题：数据被切成固定大小的块，引擎一次只处理一块，内存占用可控，也方便对 mmap 的冷数据按需加载
（第 35 课会专门讲列式分块与 mmap）。这套"列式 + 分块 + 向量化"的组合，正是现代分析型数据库执行引擎的标配。</p>

<p>执行引擎内部是一套"<strong>拉取式</strong>"的算子流水线：<span class="mono">Driver</span> 不停地向最上层算子要"下一批结果"，
这个请求层层向下传，最底层的扫描算子从 <span class="mono">QueryContext</span> 持有的列数据里取出一块，逐层向上求值、过滤，最后吐出一批结果——
<strong>整条链路一次处理一块、按需流动</strong>，内存占用小、还能并行。当过滤是多个条件的组合时，引擎对每个条件各算一列 bool 掩码，
再用 <strong>AND / OR</strong> 把它们合并：<span class="inline">A &amp;&amp; B</span> 是两张掩码按位与，<span class="inline">A || B</span> 是按位或。
有了这套机制，<strong>任意复杂的布尔过滤</strong>都能被拆成"一堆按列的批量运算 + 几次位运算合并"，最终落到一张 bitset 上——
既统一又高效。理解了这一点，你就明白为什么 Milvus 能在带着复杂过滤的同时，还把延迟压在毫秒级。</p>

<p>顺带说一个常被忽略的点：<strong>bitset 不只是"过滤结果"，它还是整段计算的"省力开关"</strong>。一旦某一块（chunk）的 bitset 全为 0，
说明这块里没有任何合格行，向量检索就能<strong>整块跳过</strong>，连距离都不用算；反之全为 1 时，引擎知道这块"无过滤"，可以走更快的全量路径。
正是这种"<strong>按块的早停与特判</strong>"，让"先过滤"在过滤很强或很弱的两个极端都不吃亏。位运算本身极廉价（一条指令处理 64 行），
所以即便过滤条件很复杂、要算很多列，合并掩码这步几乎不占时间——真正的大头永远是后面的向量距离计算，而那一步已经被 bitset 牢牢约束住了。</p>

<p>把这一课放回整条查询链路：第 25 课 Proxy 收到搜索、定好保证时间戳并分发；第 26 课 delegator 把请求扇到段；第 27 课 segcore 在一个段里搜——
而<strong>本课的 expr/exec，就是"在一个段里搜"时负责"过滤"的那一半</strong>：它先用表达式 + 向量化执行算出 bitset，再把 bitset 交给向量索引去找最近邻。
下一课（第 29 课）我们看每个段、每个节点各自搜出的 topK，是怎么一层层<strong>归并</strong>成最终一份答案的。一句话承接：<strong>过滤缩小候选、检索找最近邻、归并合成结果</strong>，
三步合起来才是一次完整的查询。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>编译</h4><p>逻辑树 → 物理算子（每个比较/逻辑节点对应一个可向量化求值的 Expr）。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>按块求值</h4><p>对每个 <span class="mono">chunk</span>（列的一段）批量算谓词，SIMD 友好；不满足的行直接置 0。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>产出 bitset</h4><p>合并所有块的结果，得到整段的"合格行掩码"——一行 1 bit。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>交给检索</h4><p>这张 bitset 作为<strong>过滤掩码</strong>送进向量检索，只在置 1 的行里找最近邻。</p></div></div>
</div>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/exec/Task.h</span><span class="ln">向量化执行引擎的执行单元（节选示意）</span></div>
  <pre><span class="kw">class</span> Task {                       <span class="cm">// 一次执行：驱动算子在分块上跑</span>
    <span class="cm">// Driver 拉动算子，QueryContext 持有列数据 / 上下文</span>
    RowVectorPtr Next();               <span class="cm">// 取下一批结果（向量化、按块）</span>
};
<span class="cm">// 物理算子在 exec/expression/ 下，例如：</span>
<span class="cm">//   BinaryArithOpEvalRangeExpr（区间/算术比较）、AlwaysTrueExpr…</span></pre>
</div>

<h2>先过滤、再检索（filter-then-search）</h2>
<p>拿到 bitset 后，向量检索<strong>只在"满足条件"的行里</strong>找最近邻。这就是 Milvus 的<strong>"先过滤、再检索"</strong>。
为什么不反过来"先检索、再过滤"？因为若先取 topK、再用条件过滤，很可能<strong>topK 大部分被过滤掉、结果不足 K 条</strong>；
而先过滤、把检索约束在合格集合里，就能<strong>稳稳取够 topK</strong>。代价是过滤本身要算，但靠向量化 + bitset，这一步极快。</p>

<p>举个具体的数：一个段里有 100 万行商品，过滤 <span class="inline">price &lt; 500</span> 命中其中约 20%。先过滤，bitset 里只有约
20 万个 1，向量检索就<strong>只在这 20 万行里</strong>找最近的 K 条——又快、又一定够 K 条。若反过来先做 ANN 取 100 条、再用价格过滤，
很可能这 100 条里满足价格的不到 K 条，只能把 topK 调大重搜，来回试、还不保证。<strong>过滤越严（命中越少），"先过滤"的优势越大</strong>：
检索的候选集越小，省下的最贵的向量计算就越多。这就是为什么混合查询里，Milvus 默认"先过滤、再检索"。</p>

<p>当然也有更精细的玩法：当过滤极强（合格行很少）、又要在图索引（如 HNSW）上搜时，"先过滤"可能让图变得"<strong>太稀疏而走不通</strong>"——
邻居大多被过滤掉、跳不到下一跳。这时引擎会用一些策略（如放宽搜索范围、或对极小候选集直接暴力算）来保证召回。
但无论哪种策略，<strong>过滤约束检索</strong>这条主线不变：bitset 始终是那张"哪些行可以被返回"的通行证，区别只在"<strong>怎么在它的约束下把最近邻找全</strong>"。
这也提醒我们：过滤的强弱会实打实影响检索策略与召回，<strong>建好标量索引、写好过滤条件</strong>，和选对向量索引一样重要。</p>

<h2>标量索引：让"过滤"这一步更快</h2>
<p>上面说的是<strong>没有标量索引</strong>时的通用路径——exec 引擎<strong>全列扫描</strong>地算 bitset。但还记得第 24 课的<strong>标量索引</strong>吗？
当过滤字段建了倒排 / bitmap / 排序索引，引擎就不必逐块扫全列：它可以<strong>直接查索引</strong>，快速拿到"满足条件的行号集合"，再转成 bitset。
于是 <span class="inline">category == "shoes"</span> 这种等值过滤、或 <span class="inline">price 在某区间</span> 这种范围过滤，命中行可以
"<strong>查出来</strong>"而不是"<strong>扫出来</strong>"。<strong>有索引走索引、没索引走 exec 全扫</strong>——这正是 expr/exec 与标量索引协作的地方：
表达式层决定"算什么条件"，执行层决定"用索引查还是全扫算"，最后都汇成同一张喂给向量检索的 bitset。</p>

<p>很多人会问：这套引擎和传统 SQL 数据库的执行器像不像？<strong>骨架很像、目标不同</strong>。SQL 的执行器最终要返回"满足条件的行（投影出若干列）"，
而 Milvus 这套 expr/exec 的<strong>主产物是一张给向量检索用的 bitset</strong>——过滤是<strong>为向量检索服务的前置剪枝</strong>，而不是查询的终点。
所以你会看到熟悉的概念（表达式树、向量化、列式分块、谓词下推），但它们都被组织成"<strong>先把候选集缩小，再交给最贵的向量计算</strong>"这条主线。
另一个差别是数据形态：Milvus 的"表"是<strong>一段段不可变的 segment</strong>，每段列式存储、可被 mmap，执行引擎就在这些段上并行地跑过滤与检索。
把"经典数据库执行引擎"和"向量检索"缝在一起，正是 Milvus C++ 内核的精髓，也是它能做<strong>带复杂条件的相似检索</strong>的底气。</p>

<div class="cols">
  <div class="col"><h4>✅ 先过滤、再检索（Milvus）</h4><p>先用 expr/exec 算出 bitset，向量检索只看合格行。<strong>结果数有保证</strong>、避免无效计算。混合查询的默认姿势。</p></div>
  <div class="col"><h4>⚠️ 先检索、再过滤</h4><p>先取 topK 再套条件，<strong>可能凑不够 K 条</strong>，要反复加大 topK 重试，既慢又不稳。仅在过滤极弱时才偶尔划算。</p></div>
</div>

<h2>分工一览：expr / exec / bitset</h2>
<p>把这一课的三个主角并排放在一起，它们的边界就清晰了——一个描述条件、一个高效执行、一个承上启下连接过滤与检索：</p>
<table class="t">
  <tr><th>角色</th><th>是什么</th><th>负责</th><th>所在</th></tr>
  <tr><td><strong>expr</strong></td><td class="mono">逻辑表达式树（ITypeExpr）</td><td>描述"过滤条件算什么"</td><td class="mono">core/src/expr</td></tr>
  <tr><td><strong>exec</strong></td><td class="mono">向量化执行引擎 + 物理算子</td><td>在分块上"怎么快速算"</td><td class="mono">core/src/exec</td></tr>
  <tr><td><strong>bitset</strong></td><td class="mono">每行 1 bit 的合格掩码</td><td>连接过滤与检索的"通行证"</td><td class="mono">求值产物</td></tr>
</table>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>表达式树（expr）</strong>：过滤字符串先编译成 <span class="mono">ITypeExpr</span> 逻辑树，叶子是列/常量、内部是比较/逻辑/算术节点。</li>
    <li><strong>向量化执行（exec）</strong>：<span class="mono">Task/Driver/QueryContext</span> 把逻辑树变成物理算子，在<strong>列式分块</strong>上批量、SIMD 友好地求值，产出一个 <strong>bitset</strong>。</li>
    <li><strong>filter-then-search</strong>：用 bitset 剪枝，向量检索只看合格行；先过滤能<strong>保证取够 topK</strong>，比"先检索再过滤"又快又稳。</li>
    <li><strong>分层</strong>：expr 说"算什么"、exec 说"怎么快速算"——这正是数据库执行引擎的经典分工。</li>
    <li><strong>承上启下</strong>：过滤（本课）缩小候选、检索（第 27 课）找最近邻、归并（第 29 课）合成结果，三步合起来才是一次完整查询；有标量索引时过滤还能"查"而非"扫"，更快。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson we went inside segcore to see how a single segment is searched. But real queries are usually
<strong>"filtered search"</strong> — both <strong>vector similarity</strong> AND a <strong>scalar filter</strong>
(e.g. <span class="inline">price &lt; 500 &amp;&amp; category == "shoes"</span>). This lesson shows how Milvus's C++
core runs that filter <strong>efficiently</strong>: it compiles the filter into an <strong>expression tree</strong>, then a
<strong>vectorized execution engine</strong> evaluates it over columnar <strong>chunks</strong> to pick the qualifying rows,
and only then does the vector search run over that qualifying set.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of a factory's <strong>"QC + finishing"</strong> line: an inspector quickly checks items on the conveyor
  (columnar chunks) against the spec (the filter) and produces a <strong>pass-list</strong> (a bitset); only the listed items
  go on to the expensive <strong>finishing step</strong> (vector search). Rejecting early means you never pay the most expensive
  cost for items that don't qualify — that is exactly why "<strong>filter first, then search</strong>" saves time.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>filter string → logical expression tree (expr) → the vectorized execution engine (exec) evaluates it over
  chunks into a bitset → the bitset prunes the vector search</strong>. "<strong>Filter-then-search</strong>" is what makes hybrid
  queries fast and correct; expression and execution live in two layers — <span class="mono">expr</span> ("what to compute") and
  <span class="mono">exec</span> ("how to compute it fast").
</div>

<h2>From a filter string to an expression tree</h2>
<p>The boolean filter you write (a string) is not executed verbatim. It is parsed into a <strong>logical expression tree</strong> —
in the C++ core, the <span class="mono">ITypeExpr</span> hierarchy under <span class="inline">expr</span>. The <strong>leaves</strong>
are column references and constants; the <strong>internal nodes</strong> are comparisons (<span class="mono">&lt;</span>/<span class="mono">==</span>),
logic (<span class="mono">AND</span>/<span class="mono">OR</span>/<span class="mono">NOT</span>) and arithmetic. Turning the condition into a
tree lets the engine evaluate it node-by-node by type, and enables optimizations like constant folding and short-circuiting.</p>

<p>Why turn a perfectly readable string into a tree at all? Because a <strong>tree is something a machine can reason about</strong>, whereas a string is just characters. Once the condition is a typed tree, the engine can <strong>type-check</strong> it (is <span class="mono">price</span> really numeric? does <span class="mono">==</span> make sense for these operands?), <strong>rewrite</strong> it for speed (drop an always-true branch, evaluate the most selective condition first), and <strong>compile</strong> each node into a concrete executable operator. It's the same reason compilers parse source into an abstract syntax tree rather than executing text directly: structure unlocks analysis. So this first step — string → typed tree — is not bureaucratic ceremony; it's the move that turns "what the user wants" into "something the engine can optimize and run fast". Keep that in mind as you watch the tree become physical operators in the next step.</p>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">string</span><span class="name">price &lt; 500 &amp;&amp; category == "shoes"</span></div><div class="ld">the user's filter expression (DSL)</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">parse</span><span class="name">parse</span></div><div class="ld">parse + bind fields / type-check</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">logical tree</span><span class="name">ITypeExpr</span></div><div class="ld">AND( price&lt;500 , category=="shoes" ) — leaves are cols/consts, internal nodes are ops</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">physical ops</span><span class="name">exec/expression</span></div><div class="ld">compiled to physical operators that evaluate over chunks</div></div>
</div>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/expr/ITypeExpr.h</span><span class="ln">base class of the logical expression tree (illustrative)</span></div>
  <pre><span class="kw">class</span> ITypeExpr {                 <span class="cm">// base class of a logical expression node</span>
    <span class="cm">// a tree: internal nodes hold child expressions, leaves are col refs/consts</span>
    <span class="kw">const</span> std::vector&lt;std::shared_ptr&lt;ITypeExpr&gt;&gt;&amp; inputs() <span class="kw">const</span>;
    <span class="kw">virtual</span> DataType type() <span class="kw">const</span>;     <span class="cm">// result type (bool / numeric…)</span>
};
<span class="cm">// the filter price &lt; 500 &amp;&amp; category == "shoes" becomes:</span>
<span class="cm">//   LogicalBinary(AND, Compare(LT, col(price), 500),</span>
<span class="cm">//                      Compare(EQ, col(category), "shoes"))</span></pre>
</div>

<h2>The vectorized execution engine: compute chunk by chunk</h2>
<p>Given the logical tree, the <strong>execution engine</strong> (<span class="inline">exec</span>, with <span class="mono">Task</span> /
<span class="mono">Driver</span> / <span class="mono">QueryContext</span>) compiles it into <strong>physical operators</strong> (the various Expr
under <span class="mono">exec/expression</span>), then evaluates them over columnar <strong>chunks</strong> in a <strong>batched, vectorized</strong>
way — not row by row but <strong>chunk by chunk</strong>, SIMD-friendly. The output is a <strong>bitset</strong>: one bit per row marking whether
it <strong>passes / fails</strong> the whole filter.</p>

<p>It's worth pausing on why "<strong>chunk by chunk</strong>" matters so much. A naive engine evaluates a predicate <strong>one row at a time</strong>: fetch a row, run the comparison, branch, store the result, repeat — and every one of those steps carries fixed overhead (a function call, a bounds check, a possibly-mispredicted branch). Over a segment of hundreds of thousands of rows, that overhead dominates. A vectorized engine flips it: it grabs a <strong>whole chunk of a column at once</strong> — say tens of thousands of contiguous values of the same type — and runs the comparison over the entire slab in a tight loop the CPU can accelerate with <strong>SIMD</strong> (one instruction comparing 8 or 16 values at a time). The per-row overhead is <strong>amortized to near zero</strong>, and contiguous same-typed data is exactly what the CPU's cache and prefetcher love. This is the same "batch, don't drip" philosophy you'll meet again in the C++ core (Lesson 36): the engine you see here is, in fact, the very same expr/exec machinery that lesson dissects — only viewed from the query path rather than from inside the kernel.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Compile</h4><p>logical tree → physical operators (each comparison/logic node becomes a vectorizable Expr).</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Evaluate by chunk</h4><p>for each <span class="mono">chunk</span> (a slice of a column), batch-evaluate the predicate, SIMD-friendly; failing rows set to 0.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Produce a bitset</h4><p>merge all chunks' results into the segment's "qualifying-row mask" — one bit per row.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Hand to search</h4><p>that bitset becomes the <strong>filter mask</strong> for the vector search, which only looks at the 1-bits.</p></div></div>
</div>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/exec/Task.h</span><span class="ln">the vectorized execution unit (illustrative)</span></div>
  <pre><span class="kw">class</span> Task {                       <span class="cm">// one execution: drive operators over chunks</span>
    <span class="cm">// Driver pulls operators; QueryContext holds column data / context</span>
    RowVectorPtr Next();               <span class="cm">// pull the next batch of results (vectorized, by chunk)</span>
};
<span class="cm">// physical operators live under exec/expression/, e.g.:</span>
<span class="cm">//   BinaryArithOpEvalRangeExpr (range/arith compare), AlwaysTrueExpr…</span></pre>
</div>

<h2>Filter-then-search</h2>
<p>With the bitset in hand, the vector search looks <strong>only at the qualifying rows</strong> for nearest neighbors. That is Milvus's
<strong>"filter-then-search"</strong>. Why not the reverse, "search-then-filter"? Because if you take topK first and then apply the
condition, <strong>most of the topK may be filtered out, leaving fewer than K results</strong>; filtering first, and constraining the
search to the qualifying set, <strong>reliably yields a full topK</strong>. The cost is the filter computation itself — but with
vectorization + a bitset, that step is very fast.</p>

<p>Think of the bitset as a <strong>cheap, compact "guest list"</strong> the filter hands to the search. It's just one bit per row — a few kilobytes for a whole segment — yet it encodes exactly "<strong>who is allowed in</strong>". Producing it first, then letting the vector search consult it, has a subtle but decisive advantage over the reverse order: it makes the <strong>result count predictable</strong>. With filter-then-search, you ask for topK <strong>among the qualifying rows</strong>, so you reliably get K results (assuming at least K qualify). With search-then-filter, you ask for topK <strong>overall</strong> and then throw away the ones that don't match — and if your filter is selective (say it keeps 1% of rows), almost all of your topK evaporates, forcing you to re-search with an ever-larger K and hope. That instability is why "filter-first" is the sane default. The one case where the reverse can win is a <strong>very weak filter</strong> (it keeps almost everything): then the filter barely shrinks the candidate set, and paying for it up front buys little. Knowing which regime you're in is part of understanding why Milvus chose the default it did.</p>

<div class="cols">
  <div class="col"><h4>✅ Filter-then-search (Milvus)</h4><p>compute a bitset via expr/exec first; the vector search only sees qualifying rows. <strong>Result count is guaranteed</strong>, no wasted compute. The default for hybrid queries.</p></div>
  <div class="col"><h4>⚠️ Search-then-filter</h4><p>take topK then apply the condition — <strong>may fall short of K</strong>, forcing repeated retries with a larger topK; slow and unstable. Only occasionally worth it when the filter is very weak.</p></div>
</div>

<h2>Division of labor: expr / exec / bitset</h2>
<table class="t">
  <tr><th>Role</th><th>What</th><th>Responsible for</th><th>Where</th></tr>
  <tr><td><strong>expr</strong></td><td class="mono">logical expression tree (ITypeExpr)</td><td>describes "what the filter computes"</td><td class="mono">core/src/expr</td></tr>
  <tr><td><strong>exec</strong></td><td class="mono">vectorized engine + physical ops</td><td>"how to compute it fast" over chunks</td><td class="mono">core/src/exec</td></tr>
  <tr><td><strong>bitset</strong></td><td class="mono">one-bit-per-row qualifying mask</td><td>the "pass" linking filter to search</td><td class="mono">the evaluation output</td></tr>
</table>

<p>This three-way split — <strong>expr / exec / bitset</strong> — is worth internalizing because it recurs throughout database engineering. <strong>expr</strong> is the "<strong>what</strong>": a declarative, type-checked description of the predicate, easy to validate and rewrite but deliberately ignorant of how it runs. <strong>exec</strong> is the "<strong>how</strong>": the machinery that turns that description into fast, vectorized work over real data. And the <strong>bitset</strong> is the <strong>clean interface between filtering and searching</strong> — a tiny, uniform artifact ("these rows qualify") that lets two very different subsystems cooperate without knowing each other's internals. Separating "what" from "how", and connecting stages through a minimal shared artifact, is exactly how complex engines stay maintainable and fast at once. You'll see the very same expr/exec design again, in far more depth, when we open the C++ core in Part 8 — proof that this isn't a query-path quirk but a core architectural choice.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Expression tree (expr)</strong>: the filter string compiles to an <span class="mono">ITypeExpr</span> logical tree — leaves are cols/consts, internal nodes are comparison/logic/arithmetic.</li>
    <li><strong>Vectorized execution (exec)</strong>: <span class="mono">Task/Driver/QueryContext</span> turn the logical tree into physical operators, evaluated batched + SIMD-friendly over <strong>columnar chunks</strong>, producing a <strong>bitset</strong>.</li>
    <li><strong>Filter-then-search</strong>: the bitset prunes the search; filtering first <strong>guarantees a full topK</strong> and is faster/steadier than "search-then-filter".</li>
    <li><strong>Layering</strong>: expr says "what to compute", exec says "how to compute it fast" — the classic database execution-engine split.</li>
  </ul>
</div>
""",
}


LESSON_29 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前几课里，一次搜索被<strong>扇出（scatter）</strong>到很多地方：Proxy 分发给多个分片（shard），每个分片的 delegator 又把它发给持有不同段的 QueryNode，
每个段在 segcore 里各自搜出自己的一小份结果。问题来了：这么多份"局部 topK"，怎么合成<strong>唯一一份、正确排序、不重不漏</strong>的最终答案？
这就是 <strong>Reduce（归并）</strong>要做的事。它不是一步，而是<strong>分三层</strong>层层向上合并——段内、节点内、跨分片——每一层都只把自己的 topK 往上交，
数据越往上越少。读懂 Reduce，你就读懂了"分布式 topK"这件看似简单、实则讲究的事。它也是把"一次相似检索"从"一个段里的事"放大成"整个集群协同完成的事"的关键缝合点。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  像一场<strong>分赛区选拔</strong>：先在每个<strong>班级</strong>里选出前 3 名（段内 topK），再把各班前 3 名拿到<strong>年级</strong>里 PK、选出年级前 3（节点内归并），
  最后各年级的前 3 汇到<strong>校级</strong>决赛，排出全校前 3（跨分片归并）。没必要让全校几千人一起比——<strong>每一层只上交自己的前几名</strong>，
  既公平、又省力。Reduce 就是这套"逐层选拔"，最后那份"全校前 3"就是你要的 topK。如果硬要把全校几千人拉到一个操场上一起比，光是把人聚齐、排队、记录就乱成一团——
这恰好对应"把所有候选一次性汇总排序"的灾难。<strong>逐层选拔之所以高效，正是因为每一层都把规模摁在"前几名"，让上一层永远只面对很少的人。</strong>把这套朴素的智慧记牢，下面的所有细节都只是它在不同尺度上的展开而已。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：<strong>段内 topK（segcore）→ 节点内归并（delegator）→ 跨分片归并（Proxy）</strong>，三层逐级合并。每层只上交局部 topK，
  所以网络上流动的数据始终很小；归并时还要<strong>按主键去重、按距离排序、再按 offset/limit 分页</strong>。这套<strong>scatter-gather（扇出-归并）</strong>
  正是几乎所有分布式检索/查询引擎的通用骨架。
</div>

<h2>三层归并：从段到节点到 Proxy</h2>
<p>把扇出反过来走一遍，就是归并的三层。<strong>第一层在段内</strong>：segcore 在一个段里算完所有候选的距离后，并不会把全部结果都返回——那太多了——
而是就地做一次 <strong>reduce</strong>（<span class="mono">internal/core/src/segcore/reduce/Reduce.cpp</span>），只留下这个段里最好的 topK。<strong>第二层在节点</strong>：
一个 QueryNode（delegator/shard leader）手里有这个分片的很多段（sealed + growing），它把各段交上来的 topK <strong>再归并一次</strong>，得到"<strong>这个分片</strong>的 topK"。
<strong>第三层在 Proxy</strong>：Proxy 收到所有分片各自的 topK，做<strong>最后一次跨分片归并</strong>（参见 <span class="mono">docs/developer_guides/proxy-reduce.md</span>），
排出全局 topK，连同需要的标量字段一起返回给客户端。</p>

<div class="flow">
  <div class="node"><div class="nt">段内 topK</div><div class="nd">segcore Reduce.cpp（每段只留 K）</div></div>
  <div class="arrow">归并</div>
  <div class="node"><div class="nt">分片 topK</div><div class="nd">delegator 合并本节点各段（sealed+growing）</div></div>
  <div class="arrow">归并</div>
  <div class="node hl"><div class="nt">全局 topK</div><div class="nd">Proxy 跨分片最终归并 → 返回客户端</div></div>
</div>

<p>这三层不是随意切的，而是<strong>顺着数据的物理分布自然分出来的</strong>：数据天然按段存放、段按分片归属、分片散在不同节点，所以"先在最小单位（段）里收敛、再逐级向上"是最省力的路径。
还有一个容易忽略的细节：在节点这一层，delegator 要把 <strong>sealed 段</strong>（已建索引、不可变）和 <strong>growing 段</strong>（还在消费 WAL、可变）的结果<strong>一起归并</strong>——
前者来自索引检索、后者来自暴力检索（第 27 课），但它们产出的都是"距离 + 主键"的有序小份，归并时一视同仁。正因为如此，<strong>刚写入还没建索引的新数据，也能立刻参与搜索并出现在结果里</strong>——
这正是第 1 课说的"边写边查"在查询侧的落地。<strong>段内收敛得越狠，往上要归并的就越少</strong>，这也是为什么 segcore 要在最底层就先做一次 reduce，而不是把成千上万条候选一股脑往上抛。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>段内 reduce（segcore）</h4><p>每个段算完候选距离，就地选出本段 topK，只上交这一小份。<span class="mono">Reduce.cpp</span></p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>节点内归并（delegator）</h4><p>一个分片的多段（sealed+growing）topK 再合并，得到"本分片 topK"。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>跨分片归并（Proxy）</h4><p>各分片 topK 汇到 Proxy，做最后一次合并，排出<strong>全局 topK</strong>。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>回填与返回</h4><p>按主键取回 <span class="mono">output_fields</span> 等标量字段，组装成结果返回客户端。</p></div></div>
</div>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/segcore/reduce/Reduce.cpp</span><span class="ln">段内归并：把候选收敛成本段 topK（节选示意）</span></div>
  <pre><span class="cm">// 段内：对每个查询向量(nq 个)，从候选里取距离最优的 topK</span>
<span class="cm">// 关键动作：按距离排序 + 按主键去重 + 截断到 topK</span>
ReduceHelper::Reduce();          <span class="cm">// 收敛每个段的搜索结果</span>
ReduceHelper::Marshal();         <span class="cm">// 打包成可跨进程传输的结果</span></pre>
</div>

<h2>为什么非要分层？一次性合并不行吗？</h2>
<p>设想最朴素的做法：让所有段、所有节点把<strong>全部候选</strong>都发到 Proxy，由 Proxy 一次性排序取 topK。这在小规模也许还行，但到了十亿级就<strong>彻底崩溃</strong>——
网络要搬运海量数据、Proxy 要排序天文数字条记录，既慢又占内存。<strong>分层归并的精髓在于"早收敛"</strong>：既然最终只要 K 条，那么每一层都<strong>只需上交自己的前 K 条</strong>就够了
（再多的也进不了全局前 K）。于是每个段只传 K 条、每个分片只传 K 条，<strong>网络上流动的数据量被死死摁在很小的规模</strong>。这是一个朴素却极有力的观察：
<strong>topK 的归并可以分治</strong>——局部 topK 的并集，一定包含全局 topK。</p>

<p>用一点点数学就更清楚了：设有 <span class="mono">S</span> 个分片、每个分片 <span class="mono">G</span> 个段。一次性全量汇总，Proxy 要面对的是"<strong>所有段里所有命中的候选</strong>"，
量级随数据规模线性膨胀，可能是上亿条。而分层归并里，每个段只上交 <span class="mono">K</span> 条，节点把 <span class="mono">G×K</span> 条收敛成 <span class="mono">K</span> 条，
Proxy 最后只面对 <span class="mono">S×K</span> 条——<strong>与底层总数据量完全无关，只和 K、分片数、段数有关</strong>。当 K=10、分片=8、每分片 16 段时，
最坏也不过是"每节点归并 160 条、Proxy 归并 80 条"这种<strong>极小的规模</strong>。这就是为什么 Milvus 能在十亿向量上做毫秒级 topK：<strong>真正昂贵的是底层的距离计算（被索引和过滤摁住了），
而归并这一步永远很轻</strong>。把"重计算下沉到数据所在处、只让轻量的 topK 往上汇聚"，是分布式系统里反复出现的智慧。</p>

<p>这里也藏着一个常见误区：以为"分片越多，归并越慢"。其实恰恰相反——分片多，意味着每个分片管的数据更少、底层检索更快，而归并端只多了"几条 K"而已（<span class="mono">S×K</span> 仍然很小）。
真正拖慢归并的从来不是分片数，而是<strong>过大的 K 或过深的 offset</strong>。所以扩容时大胆加分片/加节点去分担底层计算，归并这一层几乎不会成为瓶颈——这也是"存算分离 + 水平扩展"在查询侧能成立的微观原因之一。</p>

<div class="cols">
  <div class="col"><h4>✅ 分层归并（Milvus）</h4><p>每层只上交局部 topK，数据越往上越少；Proxy 只需合并"K × 分片数"条。<strong>可扩展到十亿级</strong>，延迟稳定。</p></div>
  <div class="col"><h4>⚠️ 一次性全量汇总</h4><p>所有候选发给一处统一排序：网络与内存随数据量爆炸，<strong>根本扛不住规模</strong>。只在玩具规模成立。</p></div>
</div>

<h2>归并到底做哪几件事</h2>
<p>每一层的归并，核心都是同样三件事，只是作用范围不同。<strong>① 按距离/相似度排序</strong>：把多份有序结果合并成一份仍然有序的结果（多路归并）。
<strong>② 按主键去重</strong>：同一个实体可能同时出现在多个段里——比如它在某个 growing 段里刚被写入、又在某个 sealed 段里有旧版本，或者删除与插入并存；
归并必须<strong>按主键认人</strong>，只保留"该看到"的那一条，避免同一条数据在结果里出现两次。<strong>③ 按 offset/limit 分页</strong>：在全局有序、去重之后，
跳过前 <span class="mono">offset</span> 条、取 <span class="mono">limit</span> 条，支撑"翻页"。注意：分页是在<strong>归并完成后</strong>做的——
要先有正确的全局排序，分页才有意义，这也是为什么深翻页（offset 很大）在分布式检索里天然更贵。</p>

<p>这里的<strong>去重</strong>值得多说一句，因为它直接关系到结果的正确性。在一个"日志即数据、段不可变"的系统里，同一个主键的数据可能<strong>同时存在于多个段</strong>：
它可能在某个 sealed 段里有一份旧值，又在某个 growing 段里有刚 upsert 进来的新值；也可能它已经被删除，却仍以"墓碑"的形式散落在某些段里（回忆第 20 课）。
如果归并时不按主键认人，结果里就会出现<strong>同一条数据的两份、甚至本该被删掉的旧版本</strong>。所以归并必须做两件事：一是<strong>按主键去重</strong>，二是配合<strong>时间戳与删除位图</strong>
只保留"在本次查询的可见时刻里、该被看到"的那一版。前者是"认人"，后者是"认时刻"——而"认时刻"正是下一课一致性要展开的主题。可以说，<strong>归并不仅是把结果排好序，更是把"分布在各处、带着不同版本"的数据，
收敛成一份逻辑上自洽的答案</strong>。</p>

<p>把它和你熟悉的 SQL <span class="inline">ORDER BY ... LIMIT</span> 对照一下会很有帮助：单机数据库里排序分页是一次完成的；而在 Milvus 这种分布式向量库里，
"排序键"是<strong>向量距离/相似度</strong>，数据又散在大量段与节点上，于是同样的"排序 + 截断"被拆成了<strong>三层逐级归并</strong>。本质没变——都是"取按某个键排序后的前若干条"——
但实现上要把它<strong>分治化、并行化</strong>，才扛得住规模。理解了这层对应关系，你就能把单机数据库的直觉，平滑迁移到分布式向量检索上：<strong>scatter 对应"并行扫描"，gather/reduce 对应"归并排序"，
offset/limit 对应"分页"</strong>，只是每一步都被放大到了集群尺度。</p>

<table class="t">
  <tr><th>动作</th><th>做什么</th><th>为什么</th></tr>
  <tr><td><strong>排序</strong></td><td class="mono">多路有序合并，按距离/分数</td><td>把多份局部 topK 合成一份全局有序</td></tr>
  <tr><td><strong>去重</strong></td><td class="mono">按主键认人，留"该看到"的版本</td><td>同一实体可能跨段出现，避免重复/旧版本</td></tr>
  <tr><td><strong>分页</strong></td><td class="mono">跳过 offset、取 limit</td><td>支撑翻页；深翻页天然更贵</td></tr>
</table>

<p>这三件事里，<strong>排序为什么用"多路归并"而不是"全部倒进一个数组再排"</strong>？因为各层交上来的每一份本身<strong>已经是有序的</strong>（段内 reduce 时就排好了）——
合并多份有序序列，用一个小顶堆（按距离）每次弹出最优的一条，复杂度只与"总条数 × log(份数)"有关，远比把所有候选打散重排划算。这其实就是经典的"<strong>归并排序的 merge 步</strong>"，
只不过被搬到了分布式场景：每个段、每个分片都是一条预先排好的"流"，归并器像拉链一样把它们咬合成一条全局有序的流，再截断出 topK。理解了这一点，你就明白为什么"<strong>每层都先排好再上交</strong>"如此重要——
它让上层的合并始终是廉价的多路归并，而不是昂贵的全量重排。</p>

<h2>一个具体例子：走一遍</h2>
<p>设 topK=3、有 2 个分片，每个分片各有 3 个段。最底层：6 个段各自搜出自己的前 3，得到 6 份"段 topK"。第二层：分片 A 的 3 个段（共 9 条候选）归并去重后留下分片 A 的前 3，
分片 B 同理留下前 3。第三层：Proxy 拿到 A、B 各自的前 3（共 6 条），最后归并、去重、排序，取出<strong>全局前 3</strong>。整个过程里，跨网络传输的最多就是
"每段 3 条""每分片 3 条""最后 6 条"——<strong>始终是 K 的量级，与底层总数据量无关</strong>。这正是分布式 topK 既能正确、又能扩展的根本原因。</p>

<p>顺着这个例子，再看两个现实里很关键的"变贵点"。其一是<strong>深翻页</strong>：要取第 1000 页、每页 10 条，意味着全局前 10010 条都得先被正确排出来——
每个分片就不能只交 10 条，而要交够"足以覆盖到第 10010 名"的量，<strong>归并的输入随 offset 线性变大</strong>，又慢又耗内存。所以向量检索里通常建议用"<strong>按上一页最后一条游标续取</strong>"
这类方式替代深翻页。其二是 <strong>nq（一次搜多少个查询向量）</strong>：批量搜 100 个向量，相当于把上面这套三层归并<strong>并行做 100 份</strong>，每份各自归出自己的 topK——
归并天然按 nq 并行，这也是 Milvus 鼓励"批量搜"以摊薄固定开销的原因。把这两点记住，你在调 <span class="mono">limit</span>/<span class="mono">offset</span>/批量大小时，
就知道每个旋钮背后动的是归并的哪根弦。</p>

<p>最后给"归并"一个准确的定位：它<strong>本身很轻</strong>，却处在"<strong>正确性的咽喉</strong>"上。轻，是因为它只搬运和合并 K 量级的数据；咽喉，是因为<strong>去重认人、版本认时刻、排序认距离</strong>
任何一处出错，用户拿到的就是重复、过期或乱序的结果。所以 Milvus 把段内 reduce 放在最贴近数据的 C++ segcore 里、把跨分片 reduce 放在 Proxy 里，每一层职责单一、边界清晰，
既能并行加速，又能把"正确性"逐层守住。</p>

<p>还有一点值得澄清：<strong>归并本身是"精确"的</strong>，它对收到的那些局部 topK 一定能合出正确的全局排序；真正"近似"的是<strong>每个段内的 ANN 检索</strong>（第 5 课）——
段内可能因为图/桶的近似而漏掉个别真正的近邻。所以一次搜索的召回率，<strong>取决于段内检索的近似程度（nprobe/ef 等），而不是归并</strong>。这提醒我们：
要想结果更准，旋钮在"段内检索的精度"上，而不是在"归并"上；归并只忠实地把各段交来的结果合好。把"近似在哪、精确在哪"分清楚，你对一次相似检索的质量来源就有了准确的判断。</p>

<p>回到全链路：第 28 课的过滤缩小了候选、第 27 课在段内搜出 topK，<strong>本课把分散的 topK 归并成最终答案</strong>；下一课（第 30 课）我们补上最后一块拼图——
这些段、这些节点搜到的，到底是<strong>哪个时刻</strong>的数据，即一致性与时间戳。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>三层归并</strong>：段内（segcore <span class="mono">Reduce.cpp</span>）→ 节点内（delegator）→ 跨分片（Proxy，见 <span class="mono">proxy-reduce.md</span>）。</li>
    <li><strong>分治的本质</strong>：每层只上交局部 topK，局部 topK 的并集必含全局 topK；网络上始终只流动 K 量级的数据，因而可扩展到十亿级。</li>
    <li><strong>归并三件事</strong>：按距离<strong>排序</strong>（多路归并）、按主键<strong>去重</strong>（同一实体可能跨段出现）、按 offset/limit <strong>分页</strong>（深翻页天然更贵）。</li>
    <li><strong>scatter-gather</strong>：扇出到分片/段、各搜局部 topK、再逐层 gather 归并——分布式检索/查询引擎的通用骨架。</li>
    <li><strong>近似在段内、精确在归并</strong>：召回率由段内 ANN 的精度（nprobe/ef）决定，归并只忠实合并；要更准就调段内检索，而非归并。深翻页与过大 K 才是归并变贵的主因。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
In the last few lessons, a search is <strong>scattered</strong> far and wide: the Proxy fans it out to multiple shards, each shard's
delegator sends it to the QueryNodes holding different segments, and each segment searches its own little slice in segcore. So the
question is: how do all these "local topKs" merge into <strong>one final answer that is correctly ordered, deduplicated and complete</strong>?
That is what <strong>Reduce</strong> does. It is not one step but <strong>three levels</strong> of bottom-up merging — within a segment,
within a node, across shards — and each level only passes its own topK upward, so the data shrinks as it climbs. Understand Reduce and you
understand "distributed topK", which looks simple but has real subtlety.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Like a <strong>tiered selection</strong>: first each <strong>class</strong> picks its top 3 (segment topK), then the classes' top-3s
  compete at the <strong>grade</strong> level for the grade's top 3 (node merge), and finally the grades' top-3s meet in the
  <strong>school</strong> final for the school's top 3 (cross-shard merge). No need to make all thousands compete at once — <strong>each
  level only sends up its own top few</strong>: fair and cheap. Reduce is that tiered selection, and the final "school top 3" is your topK.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>segment topK (segcore) → node merge (delegator) → cross-shard merge (Proxy)</strong>, merged level by level. Each
  level only sends up a local topK, so the data crossing the network stays small; merging also <strong>dedups by primary key, sorts by
  distance, then paginates by offset/limit</strong>. This <strong>scatter-gather</strong> shape is the universal skeleton of almost every
  distributed retrieval/query engine.
</div>

<h2>Three levels: from segment to node to Proxy</h2>
<p>Walk the scatter backwards and you get the three merge levels. <strong>Level one, in the segment</strong>: after segcore computes all
candidate distances in a segment it does NOT return them all — too many — but does a local <strong>reduce</strong>
(<span class="mono">internal/core/src/segcore/reduce/Reduce.cpp</span>), keeping only that segment's topK. <strong>Level two, in the node</strong>:
a QueryNode (delegator/shard leader) holds many segments of this shard (sealed + growing); it <strong>merges</strong> their topKs into "this
<strong>shard's</strong> topK". <strong>Level three, at the Proxy</strong>: the Proxy receives every shard's topK and does the <strong>final
cross-shard merge</strong> (see <span class="mono">docs/developer_guides/proxy-reduce.md</span>), producing the global topK, and returns it —
with the requested scalar fields — to the client.</p>

<div class="flow">
  <div class="node"><div class="nt">segment topK</div><div class="nd">segcore Reduce.cpp (keep K per segment)</div></div>
  <div class="arrow">merge</div>
  <div class="node"><div class="nt">shard topK</div><div class="nd">delegator merges this node's segments (sealed+growing)</div></div>
  <div class="arrow">merge</div>
  <div class="node hl"><div class="nt">global topK</div><div class="nd">Proxy's final cross-shard merge → return to client</div></div>
</div>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Segment reduce (segcore)</h4><p>each segment computes candidate distances and locally selects its topK, sending up only that slice. <span class="mono">Reduce.cpp</span></p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Node merge (delegator)</h4><p>a shard's many segments (sealed+growing) topKs are merged into "this shard's topK".</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Cross-shard merge (Proxy)</h4><p>shards' topKs gather at the Proxy for a final merge into the <strong>global topK</strong>.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Fill &amp; return</h4><p>fetch <span class="mono">output_fields</span> by PK, assemble the result, return to the client.</p></div></div>
</div>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/core/src/segcore/reduce/Reduce.cpp</span><span class="ln">segment-level reduce: converge candidates into the segment's topK (illustrative)</span></div>
  <pre><span class="cm">// in a segment: for each query vector (nq of them), take the best topK by distance</span>
<span class="cm">// key actions: sort by distance + dedup by primary key + truncate to topK</span>
ReduceHelper::Reduce();          <span class="cm">// converge each segment's search results</span>
ReduceHelper::Marshal();         <span class="cm">// pack into a cross-process transmittable result</span></pre>
</div>

<h2>Why levels? Can't we merge all at once?</h2>
<p>Picture the naive approach: every segment and node ships <strong>all candidates</strong> to the Proxy, which sorts once and takes the topK.
That might be fine at small scale, but at billions it <strong>collapses</strong> — the network hauls enormous data and the Proxy sorts an
astronomical number of records: slow and memory-hungry. <strong>The essence of hierarchical merging is "converge early"</strong>: since the
final answer is only K items, each level <strong>only needs to send up its own top K</strong> (anything beyond can't make the global top K).
So each segment sends K, each shard sends K, and <strong>the data crossing the network is pinned to a tiny size</strong>. It is a humble but
powerful observation: <strong>topK merging is divide-and-conquer</strong> — the union of local topKs is guaranteed to contain the global topK.</p>

<p>Let that guarantee sink in, because it's the mathematical heart of the whole design. Why is it <strong>safe</strong> for a segment to send up only its own top K and discard the rest? Because the global #1 result must, by definition, also be #1 in <strong>whatever segment it lives in</strong> — it can't be the best overall while being only, say, the 50th-best in its own segment. So no globally-relevant candidate is ever hiding below a segment's local top K; throwing away each segment's "also-rans" is <strong>provably lossless</strong>. This is what licenses the aggressive early convergence: each level can shrink its output to K with <strong>zero risk</strong> of dropping a true winner. Contrast that with computing an <strong>average</strong> or a <strong>median</strong> across shards — those you genuinely cannot compute from per-shard top-Ks, because the answer depends on data each shard discarded. topK is special: it's <strong>decomposable</strong>, and Milvus's three-level reduce is simply that decomposability cashed in for scale.</p>

<div class="cols">
  <div class="col"><h4>✅ Hierarchical merge (Milvus)</h4><p>each level sends only a local topK; data shrinks upward; the Proxy merges just "K × number-of-shards". <strong>Scales to billions</strong>, stable latency.</p></div>
  <div class="col"><h4>⚠️ One-shot full gather</h4><p>all candidates to one place for a single sort: network and memory explode with data volume, <strong>can't withstand scale</strong>. Only holds at toy size.</p></div>
</div>

<h2>What does a merge actually do</h2>
<p>At every level a merge is the same three things, just over a different scope. <strong>(1) Sort by distance/score</strong>: merge several
sorted results into one still-sorted result (k-way merge). <strong>(2) Dedup by primary key</strong>: the same entity can appear in multiple
segments — e.g. it was just written into a growing segment and also has an old version in a sealed one, or a delete and insert coexist;
the merge must <strong>identify by primary key</strong> and keep only the "should-be-seen" row, so no entity appears twice. <strong>(3)
Paginate by offset/limit</strong>: after the global sort and dedup, skip the first <span class="mono">offset</span> and take
<span class="mono">limit</span>, supporting pagination. Note: pagination happens <strong>after</strong> the merge — you need a correct global
order first, which is also why deep pagination (large offset) is inherently more expensive in distributed retrieval.</p>

<table class="t">
  <tr><th>Action</th><th>What</th><th>Why</th></tr>
  <tr><td><strong>Sort</strong></td><td class="mono">k-way sorted merge, by distance/score</td><td>fuse several local topKs into one global order</td></tr>
  <tr><td><strong>Dedup</strong></td><td class="mono">identify by PK, keep the "should-see" version</td><td>same entity may appear across segments; avoid dup/stale</td></tr>
  <tr><td><strong>Paginate</strong></td><td class="mono">skip offset, take limit</td><td>support paging; deep paging is inherently pricier</td></tr>
</table>

<h2>A concrete walk-through</h2>
<p>Let topK=3, with 2 shards, each holding 3 segments. Bottom level: the 6 segments each search their own top 3, giving 6 "segment topKs".
Second level: shard A's 3 segments (9 candidates total) merge+dedup down to shard A's top 3, and shard B likewise to its top 3. Third level:
the Proxy takes A's and B's top 3 (6 total) and finally merges, dedups, sorts, and takes the <strong>global top 3</strong>. Throughout, the most
that ever crosses the network is "3 per segment", "3 per shard", "6 at the end" — <strong>always on the order of K, independent of the total
underlying data</strong>. That is exactly why distributed topK can be both correct and scalable. Back to the full chain: Lesson 28's filter
narrowed the candidates, Lesson 27 found the topK inside a segment, and <strong>this lesson merges the scattered topKs into the final answer</strong>;
the next lesson (30) supplies the last piece — exactly <strong>which moment's</strong> data these segments and nodes searched, i.e. consistency and timestamps.</p>

<p>Step back and notice the <strong>shape</strong> of this pattern, because you'll meet it far beyond Milvus. "<strong>Compute locally, send up a small summary, merge upward</strong>" is the same skeleton as MapReduce, as a SQL <span class="mono">GROUP BY</span> executed across shards, as aggregating metrics from a fleet of servers. The three-level reduce here — segment → node → Proxy — is just that skeleton fitted to topK: each tier does as much work as it can <strong>where the data already is</strong> (avoiding moving raw data), and passes upward only a result that is <strong>tiny and already half-merged</strong>. The payoff is twofold: the <strong>network</strong> never carries more than O(K) per source, and the <strong>final merger</strong> (the Proxy) never faces more than "K × number of children", no matter how many billions of vectors sit underneath. Whenever you design a distributed query of your own, ask the same question Milvus answered here: <strong>can I push work down to the data and only float a small summary up?</strong> If yes, you've found your reduce.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Three merge levels</strong>: segment (segcore <span class="mono">Reduce.cpp</span>) → node (delegator) → cross-shard (Proxy, see <span class="mono">proxy-reduce.md</span>).</li>
    <li><strong>Divide-and-conquer</strong>: each level sends only a local topK; the union of local topKs contains the global topK; only K-scale data crosses the network, so it scales to billions.</li>
    <li><strong>A merge does three things</strong>: <strong>sort</strong> by distance (k-way), <strong>dedup</strong> by PK (an entity may appear across segments), <strong>paginate</strong> by offset/limit (deep paging is pricier).</li>
    <li><strong>Scatter-gather</strong>: fan out to shards/segments, search local topKs, gather and merge upward — the universal skeleton of distributed retrieval/query engines.</li>
  </ul>
</div>
""",
}


LESSON_30 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
从第 25 课到第 29 课，我们把一次搜索完整走通了：Proxy 分发、delegator 扇出、segcore 段内搜、exec 过滤、reduce 归并。但有一个问题一直被我们<strong>悄悄推迟</strong>到现在——
这些段、这些节点搜到的，到底是<strong>哪一个时刻</strong>的数据？刚 insert 进去的新数据，这次搜索看不看得到？这就是<strong>一致性与时间戳</strong>要回答的。
答案的核心只有三个词：<strong>TSO（全局时钟）、保证时间戳（guarantee ts）、MVCC（按时间戳决定可见性）</strong>。它们一起，让 Milvus 既能"边写边查"，又能让你<strong>按需选择</strong>"要多新鲜"。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  像看一份<strong>带版本时间的在线文档</strong>。每次编辑都盖一个<strong>时间戳</strong>；你打开文档时，其实是说"<strong>给我看截至某时刻 T 的版本</strong>"。
  要"绝对最新"，系统就得<strong>等所有在途编辑都落定</strong>再给你看（稍慢但最全）；要"快点出来"，就给你<strong>稍早一点的快照</strong>（可能差几条最新编辑，但秒开）。
  Milvus 的一致性级别，就是让你<strong>挑这条"要多新"的标尺</strong>——而时间戳，是让这一切可计算的统一刻度。说到底，"看哪一刻的版本"在分布式系统里不是个哲学问题，而是个<strong>能用一个整数（时间戳）精确表达和比较</strong>的工程问题。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：<strong>RootCoord 的 TSO 发全局单调时间戳，每次写和读都盖戳；读带一个"保证时间戳 Tg"（由一致性级别决定）；QueryNode 等到自己消费的数据(tsafe)追上 Tg，再按 MVCC 只返回"ts ≤ Tg 且未被删除"的那一版</strong>。
  新鲜度与延迟之间的取舍，就压缩在"<strong>Tg 取多新、要不要等</strong>"这一个旋钮上。可以说，<strong>时间戳是 Milvus 把"分布式"和"正确"同时握住的那只手</strong>。
</div>

<h2>TSO：一把全局唯一、只增不减的时钟</h2>
<p>分布式系统最头疼的事之一，是"<strong>谁先谁后</strong>"。多个 Proxy 同时收到写、多个节点各有各的本地时钟，怎么判断两条操作的先后？Milvus 的答案是<strong>TSO（Timestamp Oracle，时间戳预言机）</strong>：
由 <strong>RootCoord</strong>（即今天的 MixCoord 里那部分）维护<strong>一个</strong>全局的、<strong>单调递增</strong>的时间戳源。无论哪个 Proxy 来要，拿到的 ts 都<strong>绝不重复、绝不回退</strong>，且严格反映"谁先要、谁的 ts 小"。
于是整个集群有了<strong>统一的时间刻度</strong>：每条写入消息进 WAL 时盖一个 ts、每次读请求也领一个 ts。有了这把"全局钟"，"先后"就从模糊的物理时间，变成了可比较的整数。后面的一致性、MVCC，全都建立在它之上。</p>

<p>为什么不能各节点用各自的本地时钟？因为分布式系统里<strong>没有"绝对同步"的物理时钟</strong>——每台机器的时钟都会有毫秒级甚至更大的偏差（时钟漂移），
靠它们排先后，必然出现"A 机器以为自己晚、B 机器以为自己早"的矛盾，进而导致数据可见性错乱。TSO 用"<strong>单一来源发号</strong>"的办法绕开了这个难题：
既然只有一个 RootCoord 在发 ts，那么"谁的 ts 小谁就在前"就是<strong>全局一致、无可争议</strong>的。这其实是分布式系统里很经典的一招——<strong>把"排序"这件难事，收敛到一个权威节点上集中决定</strong>。
为避免这个节点成为瓶颈，TSO 还做了批量预分配等优化（一次取一段 ts 缓存着发），所以它既权威又不慢。记住这把全局钟的两个性质：<strong>单调（只增不减）</strong>与<strong>唯一（不重复）</strong>，
后面所有"先后""可见性"的讨论，都只是在这两个性质上推演。</p>

<div class="layers">
  <div class="layer l-core"><div class="lh"><span class="badge">TSO</span><span class="name">RootCoord</span></div><div class="ld">全局唯一、单调递增的时间戳源——集群的统一时钟</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">写</span><span class="name">insert/delete ts</span></div><div class="ld">每条写入进 WAL 时盖一个 ts（顺序即先后）</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">读</span><span class="name">guarantee ts (Tg)</span></div><div class="ld">每次读领一个 Tg：要看到"截至 Tg 的所有写入"</div></div>
  <div class="layer l-app"><div class="lh"><span class="badge">可见性</span><span class="name">MVCC</span></div><div class="ld">一行可见 ⇔ 它的 ts ≤ Tg 且未被 ts ≤ Tg 的墓碑删除</div></div>
</div>

<h2>保证时间戳与五种一致性级别</h2>
<p>读请求带的那个 <strong>Tg（guarantee timestamp，保证时间戳）</strong>，含义是"<strong>请让我至少看到截至 Tg 的所有写入</strong>"。Tg 取多大，由你选的<strong>一致性级别</strong>决定——这正是
<span class="mono">internal/proxy/util.go</span> 里 <span class="mono">parseGuaranteeTsFromConsistency</span> 做的事。Milvus 提供<strong>五种</strong>一致性级别（<span class="mono">commonpb.ConsistencyLevel_*</span>），
本质是"Tg 取多新"的不同档位：</p>

<p>这里要厘清一个常见误解：<strong>一致性级别管的是"读能看到多新的写"，不是"写得多快"或"数据存得对不对"</strong>。无论你选哪一档，写入都照样进 WAL、照样持久化、照样最终对所有人可见——级别只决定<strong>这一次读愿不愿意等、要看到截至哪一刻</strong>。
也正因如此，<strong>同一个集合，不同查询可以用不同级别</strong>：后台对账用 Strong、面向用户的搜索用 Bounded、离线刷库用 Eventually，互不影响。把"一致性"理解成"<strong>每次读自带的一个新鲜度要求</strong>"，
而不是"整个库的某种全局开关"，你就抓住了它的精髓。这也呼应了向量数据库的定位：它不像传统事务数据库那样追求"任何时刻全局强一致"，而是把"<strong>新鲜度</strong>"做成一个<strong>可按查询调节的旋钮</strong>，
在海量、高并发的相似检索场景里，换取吞吐与延迟的巨大收益。</p>

<table class="t">
  <tr><th>一致性级别</th><th>Tg 取值</th><th>含义 / 取舍</th></tr>
  <tr><td><strong>Strong</strong></td><td class="mono">最新的 tMax</td><td>看到此刻已提交的全部写入；最新鲜，可能要等</td></tr>
  <tr><td><strong>Bounded</strong></td><td class="mono">tMax − gracefulTime</td><td>容忍一小段陈旧（如几秒），换更低延迟；默认常用</td></tr>
  <tr><td><strong>Session</strong></td><td class="mono">本客户端上次写入的 ts</td><td>读到"自己刚写的"（read-your-writes）</td></tr>
  <tr><td><strong>Eventually</strong></td><td class="mono">1（极小）</td><td>不等待、立刻返回，可能较陈旧；最快</td></tr>
  <tr><td><strong>Customized</strong></td><td class="mono">用户指定的 ts</td><td>精确控制"读到哪一刻"，做时间旅行式查询</td></tr>
</table>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/proxy/util.go</span><span class="ln">由一致性级别推导保证时间戳 Tg（示意，已简化）</span></div>
  <pre><span class="cm">// parseGuaranteeTsFromConsistency: 一致性级别 → Tg</span>
<span class="kw">switch</span> level {
<span class="kw">case</span> Strong:      Tg = tMax                 <span class="cm">// 最新</span>
<span class="kw">case</span> Bounded:     Tg = tMax - gracefulTime  <span class="cm">// 容忍一点陈旧</span>
<span class="kw">case</span> Eventually:  Tg = 1                    <span class="cm">// 不等待</span>
<span class="cm">// Session: 取本会话上次写入 ts；Customized: 用户给定 ts</span>
}</pre>
</div>

<h2>MVCC：用时间戳决定"谁该被看到"</h2>
<p>有了 Tg，"可见性"就有了精确定义。Milvus 用 <strong>MVCC（多版本并发控制）</strong>：每条数据都带着它的写入 ts，<strong>一行对本次读可见，当且仅当：它的插入 ts ≤ Tg，并且没有一个 ts ≤ Tg 的删除墓碑作废它</strong>（回忆第 20 课——删除是盖墓碑、upsert 是删+插）。
换句话说，读不是"看当前最终状态"，而是"<strong>看截至 Tg 那一刻的快照</strong>"。这带来两个好处：其一，<strong>读写互不阻塞</strong>——写一直在更高的 ts 上追加，读只认自己 Tg 那一刻，谁也不挡谁；
其二，<strong>结果天然自洽</strong>——同一次查询里，所有段、所有节点都用同一个 Tg 过滤，看到的是同一个时间切片，绝不会"东边看到新的、西边看到旧的"。MVCC 把"并发"这件难事，化解成了"<strong>各看各的时间快照</strong>"。</p>

<p>把这套规则套在一个具体场景里：你先 <span class="inline">insert</span> 了商品 A（ts=95），紧接着把它 <span class="inline">delete</span> 了（墓碑 ts=98），又重新 <span class="inline">insert</span> 了改价后的 A（ts=110）。
现在三个读同时来：Tg=96 的读，只看得到第一版 A（95≤96，且 98 的墓碑还"不在它的时间里"）；Tg=100 的读，看到的是"A 已被删除"（墓碑 98≤100，而新版 110 还看不到）；Tg=120 的读，看到的是改价后的新 A（110≤120）。
<strong>同一份底层数据，三个不同 Tg 的读看到三种不同却各自正确的状态</strong>——这正是 MVCC 的威力：它不强行规定"现在到底是什么"，而是让每个读各自拿到"<strong>它那一刻该看到的真相</strong>"。
也正因为读永远只认自己的 Tg、写永远在更高的 ts 上追加，<strong>读和写就彻底解耦了</strong>：高并发写入的同时，查询照样跑，互不加锁、互不等待，这是 Milvus 能"边写边查"且吞吐很高的根本机制之一。</p>

<div class="cellgroup">
  <div class="cg-cap"><b>同一主键 k 的多个版本</b>：以 Tg=100 读，应看到哪一版？（绿✓=可见）</div>
  <div class="cells"><span class="lab">v1</span><span class="cell">insert k @ts=80</span><span class="sep">→</span><span class="cell dim">被后续覆盖</span></div>
  <div class="cells"><span class="lab">v2</span><span class="cell">delete k @ts=90</span><span class="sep">→</span><span class="cell dim">墓碑 ts=90 ≤ 100</span></div>
  <div class="cells"><span class="lab">v3</span><span class="cell hl">insert k @ts=95</span><span class="sep">→</span><span class="cell q">ts=95 ≤ 100 且其后无墓碑 ✓</span></div>
  <div class="cells"><span class="lab">v4</span><span class="cell">insert k @ts=120</span><span class="sep">→</span><span class="cell dim">ts=120 &gt; 100，不可见</span></div>
</div>

<h2>等待机制：tsafe 追上 Tg，才敢回答</h2>
<p>最关键的一环来了：<strong>怎么保证"截至 Tg 的写入，真的都到了 QueryNode 手里"？</strong>毕竟写是异步流过 WAL 的，节点可能还没消费到最新。Milvus 的办法是给每个 QueryNode 维护一个<strong>tsafe（服务时间水位）</strong>——
它表示"我已经把 WAL 消费并应用到了哪个 TimeTick"。TimeTick 是 WAL 里单调推进的时钟（第 16 课），节点每消费一段日志，tsafe 就往前推一点。<strong>当一个读请求带着 Tg 进来，节点先比较：如果 tsafe ≥ Tg，说明截至 Tg 的写入我都有了，立刻搜；
如果 tsafe &lt; Tg，就<strong>挂起等待</strong>，直到 tsafe 追上 Tg（或超时）</strong>。这套"<strong>等到数据足够新再回答</strong>"的机制，正是 <span class="mono">docs/developer_guides/how-guarantee-ts-works.md</span> 的核心，也是"保证时间戳"四个字里"<strong>保证</strong>"二字的由来。</p>

<p>等待当然不能无限。如果某个节点迟迟追不上（比如它落后太多、或上游写入洪峰），读会在超时后<strong>返回错误或退化</strong>，而不是永远挂着——这把"正确性"和"可用性"的边界交还给调用方掌控。
这也解释了为什么<strong>Strong 在写入压力很大时延迟会上升</strong>：Tg 被设成最新 tMax，而节点要消费完积压的 WAL 才能让 tsafe 追上去。反过来，<strong>Bounded 把 Tg 往回挪一点，就极大概率"一来就满足 tsafe ≥ Tg"，几乎不用等</strong>——
这就是它成为默认级别的原因。还要注意：tsafe 是<strong>按 vchannel（分片）维度</strong>推进的，一次查询要等的是它涉及的所有分片都各自 tsafe ≥ Tg；任何一个分片的消费卡住，都会拖慢这次强一致读。理解了这套等待，
你就能把线上"偶发的查询变慢"和"写入积压 / 某节点消费滞后"对应起来——它们往往是同一件事的两面。</p>

<p>那么实践中怎么选级别？给一个朴素的决策指南：<strong>要"写完立刻能查到自己写的"</strong>（比如刚上传一张图就想搜它），用 <strong>Session</strong> 或 Strong；<strong>对一致性极敏感、宁可慢一点也要最新</strong>（如某些金融、审计场景），用 <strong>Strong</strong>；
<strong>绝大多数高并发检索/推荐/RAG</strong>，差几条最新数据无伤大雅、但要低延迟高吞吐，用 <strong>Bounded</strong>（默认）；<strong>只要"大概新"、极致追求快</strong>（如离线分析、海量召回），用 <strong>Eventually</strong>；
<strong>要做"看某历史时刻快照"的时间旅行查询</strong>，用 <strong>Customized</strong> 指定 ts。一句话：<strong>先想清楚"这次查询能容忍多旧"，再倒推该选哪一档</strong>——这比无脑用 Strong"求稳"要明智得多，
因为不必要的强一致，换来的往往是不必要的延迟。</p>

<div class="timeline">
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t1</span><span class="tl-c">写入不断进 WAL，TimeTick 一路推进；QueryNode 消费并应用，tsafe 随之上涨</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t2</span><span class="tl-c">读请求到达，带 Tg=100；此刻节点 tsafe=98 &lt; 100</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t3</span><span class="tl-c">节点<strong>挂起等待</strong>：继续消费 WAL，直到 tsafe ≥ 100</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t4</span><span class="tl-c">tsafe=100，<strong>截至 Tg 的写入已齐</strong>，按 MVCC 过滤并返回结果</span></div>
</div>

<h2>取舍：要多新鲜，就要等多久</h2>
<p>把上面这套"等到 tsafe ≥ Tg 再答"放在心里，就能理解：<strong>"新鲜"从来不是免费的</strong>——要看到更新的数据，要么数据本就到了（运气好），要么就得等它到。Milvus 没有替你做这个取舍，而是把旋钮交到你手里。</p>
<p>现在五种一致性级别的设计意图就一目了然了：<strong>它们本质是在"新鲜度"和"延迟"之间给你一个旋钮</strong>。Strong 把 Tg 设成最新的 tMax，看得最全，但若节点还没追上，就得<strong>等</strong>——延迟可能略高。
Bounded 把 Tg 往回挪一点点（<span class="mono">tMax − gracefulTime</span>），用"容忍几秒陈旧"换"几乎不用等"，所以它是很多场景的<strong>默认之选</strong>。Eventually 干脆把 Tg 设到极小，<strong>从不等待、秒回</strong>，代价是可能看不到最新几条。
Session 保证你<strong>至少能读到自己刚写的</strong>，对"写完马上查"的交互很友好。Customized 则把"读哪一刻"完全交给你。回忆第 1 课说的"<strong>边写边查</strong>"：能做到这一点，正是因为 growing 段 + tsafe 机制让"新写的数据立刻可被某个 Tg 看见"——
而看不看得见、要不要等，由你选的级别决定。<strong>没有放之四海皆准的答案，只有适配场景的取舍</strong>：要强一致就接受可能的等待，要低延迟就接受可能的陈旧。</p>

<div class="cols">
  <div class="col"><h4>偏新鲜（Strong）</h4><p>看到此刻全部已提交写入；适合对正确性极敏感的场景。代价：节点未追上时要等，延迟可能更高。</p></div>
  <div class="col"><h4>偏低延迟（Bounded / Eventually）</h4><p>容忍一点点陈旧，几乎不等待、响应快；适合推荐、检索增强等"差几条无伤大雅"的高并发场景。</p></div>
</div>

<h2>全书的一次收束</h2>
<p>这一课也是<strong>查询链路（第六部分）的收尾</strong>。把六部分串起来看：你写下的数据先变成<strong>向量</strong>（第二部分），经 Proxy <strong>沿日志写入</strong>、落成段与 binlog（第四部分），被<strong>建成索引</strong>（第五部分）；
查询时，Proxy <strong>定好 Tg、分发</strong>，delegator <strong>扇出</strong>到段，segcore <strong>过滤 + 检索</strong>，reduce <strong>归并</strong>，最后由 tsafe + MVCC 保证你看到的是<strong>一个自洽、且新鲜度可选的时间快照</strong>。
至此，"一次相似检索如何在分布式系统里被正确、高效、可控地完成"这条主线，就完整闭环了。后面的部分（C++ 内核、流式系统、运维与贡献）会再向下钻、向外扩，但它们都挂在这条主线上。</p>

<p>回头看这一课为什么压轴：<strong>时间戳，是把前面所有零散机制缝在一起的那根线</strong>。写入的顺序靠它定（第 16 课 TimeTick），删除与 upsert 的版本靠它分（第 20 课墓碑），
段的可见性靠它判（第 7 课 growing/sealed），归并的去重靠它选对版本（第 29 课），而这一课把它们统一成一句话：<strong>一次读，就是"取一个 Tg、等数据追上、按 Tg 看快照"</strong>。
当你下次在 SDK 里写下 <span class="inline">consistency_level="Bounded"</span> 时，希望你眼前能浮现出这一整条链路：TSO 发戳、Proxy 定 Tg、QueryNode 等 tsafe、segcore 按 MVCC 过滤——
一个看似简单的参数背后，是一整套让"分布式、边写边查、还要正确"同时成立的精巧设计。<strong>读懂了时间戳，你就读懂了 Milvus 查询正确性的根</strong>。如果说前五课讲的是"<strong>怎么把结果搜出来、合出来</strong>"，这一课讲的就是"<strong>这些结果凭什么是对的、是哪一刻的</strong>"——前者关乎性能，后者关乎正确，二者合起来，才算真正讲完了"一次查询"。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>TSO</strong>：RootCoord 维护的全局、单调递增时间戳源；写与读都盖戳，给集群一把统一的钟。</li>
    <li><strong>保证时间戳 Tg + 五种一致性级别</strong>：Strong=最新 tMax、Bounded=tMax−gracefulTime、Session=本会话上次写、Eventually=1、Customized=用户指定（<span class="mono">parseGuaranteeTsFromConsistency</span>）。</li>
    <li><strong>MVCC</strong>：一行可见 ⇔ 插入 ts ≤ Tg 且无 ts ≤ Tg 的墓碑；读看的是"截至 Tg 的快照"，读写互不阻塞、结果自洽。</li>
    <li><strong>等待机制</strong>：QueryNode 的 <span class="mono">tsafe</span>（已消费的 WAL TimeTick）≥ Tg 才回答；这是"保证"二字的由来。</li>
    <li><strong>取舍</strong>：新鲜度 ↔ 延迟一个旋钮；强一致可能要等，低延迟可能略陈旧——按场景选级别，不必无脑求强一致。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
From Lesson 25 to 29 we walked a search end to end: the Proxy dispatches, the delegator fans out, segcore searches a segment, exec
filters, reduce merges. But one question we kept <strong>quietly deferring</strong> until now: which <strong>moment's</strong> data did
those segments and nodes actually search? Can a search see data you just inserted? That is what <strong>consistency and timestamps</strong>
answer. The core is just three words: <strong>TSO (a global clock), the guarantee timestamp, and MVCC (visibility by timestamp)</strong>.
Together they let Milvus both "query while you write" and <strong>let you choose</strong> "how fresh" you need.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Like reading a <strong>versioned online document</strong>. Every edit is stamped with a <strong>timestamp</strong>; opening the doc really
  means "<strong>show me the version as of moment T</strong>". For "absolutely latest", the system must <strong>wait for all in-flight edits
  to land</strong> (a bit slower but complete); for "just give it to me fast", it hands you a <strong>slightly earlier snapshot</strong>
  (maybe missing the last few edits, but instant). Milvus's consistency levels let you <strong>pick that "how fresh" dial</strong> — and the
  timestamp is the unified ruler that makes it all computable.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>RootCoord's TSO issues a global monotonic timestamp; every write and read is stamped; a read carries a "guarantee
  timestamp Tg" (set by its consistency level); a QueryNode waits until the data it has consumed (tsafe) catches up to Tg, then by MVCC
  returns only the version with "ts ≤ Tg and not deleted"</strong>. The freshness-vs-latency trade-off compresses into one knob: "how new is
  Tg, and do we wait."
</div>

<h2>TSO: one global, ever-increasing clock</h2>
<p>One of the hardest things in a distributed system is "<strong>who came first</strong>". Multiple Proxies take writes at once, each node has
its own local clock — how do you order two operations? Milvus's answer is the <strong>TSO (Timestamp Oracle)</strong>: <strong>RootCoord</strong>
(today, that part inside MixCoord) maintains <strong>one</strong> global, <strong>monotonically increasing</strong> timestamp source. Whichever
Proxy asks, the ts it gets <strong>never repeats and never goes backward</strong>, and strictly reflects "who asked first gets the smaller ts".
So the whole cluster shares a <strong>single time ruler</strong>: every write message is stamped as it enters the WAL, and every read gets a ts
too. With this global clock, "ordering" turns from fuzzy physical time into comparable integers. Consistency and MVCC are all built on it.</p>

<div class="layers">
  <div class="layer l-core"><div class="lh"><span class="badge">TSO</span><span class="name">RootCoord</span></div><div class="ld">a global, monotonic timestamp source — the cluster's single clock</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">write</span><span class="name">insert/delete ts</span></div><div class="ld">each write is stamped as it enters the WAL (order = precedence)</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">read</span><span class="name">guarantee ts (Tg)</span></div><div class="ld">each read gets a Tg: see all writes up to Tg</div></div>
  <div class="layer l-app"><div class="lh"><span class="badge">visibility</span><span class="name">MVCC</span></div><div class="ld">a row is visible iff its ts ≤ Tg and no tombstone with ts ≤ Tg deletes it</div></div>
</div>

<h2>The guarantee timestamp and five consistency levels</h2>
<p>The <strong>Tg (guarantee timestamp)</strong> a read carries means "<strong>please let me see at least all writes up to Tg</strong>". How large
Tg is depends on the <strong>consistency level</strong> you pick — exactly what <span class="mono">parseGuaranteeTsFromConsistency</span> in
<span class="mono">internal/proxy/util.go</span> does. Milvus offers <strong>five</strong> levels (<span class="mono">commonpb.ConsistencyLevel_*</span>),
essentially different settings of "how new is Tg":</p>

<table class="t">
  <tr><th>Level</th><th>Tg value</th><th>Meaning / trade-off</th></tr>
  <tr><td><strong>Strong</strong></td><td class="mono">latest tMax</td><td>see all committed writes so far; freshest, may wait</td></tr>
  <tr><td><strong>Bounded</strong></td><td class="mono">tMax − gracefulTime</td><td>tolerate a little staleness (e.g. seconds) for lower latency; a common default</td></tr>
  <tr><td><strong>Session</strong></td><td class="mono">this client's last-write ts</td><td>read-your-own-writes</td></tr>
  <tr><td><strong>Eventually</strong></td><td class="mono">1 (tiny)</td><td>no waiting, returns immediately, may be stale; fastest</td></tr>
  <tr><td><strong>Customized</strong></td><td class="mono">a user-supplied ts</td><td>precisely control "as of which moment" — time-travel queries</td></tr>
</table>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/proxy/util.go</span><span class="ln">derive guarantee ts Tg from the consistency level (illustrative, simplified)</span></div>
  <pre><span class="cm">// parseGuaranteeTsFromConsistency: consistency level → Tg</span>
<span class="kw">switch</span> level {
<span class="kw">case</span> Strong:      Tg = tMax                 <span class="cm">// latest</span>
<span class="kw">case</span> Bounded:     Tg = tMax - gracefulTime  <span class="cm">// tolerate some staleness</span>
<span class="kw">case</span> Eventually:  Tg = 1                    <span class="cm">// no waiting</span>
<span class="cm">// Session: this session's last-write ts; Customized: user-given ts</span>
}</pre>
</div>

<h2>MVCC: deciding "who should be seen" by timestamp</h2>
<p>With Tg, "visibility" has a precise definition. Milvus uses <strong>MVCC (multi-version concurrency control)</strong>: every row carries its
write ts, and <strong>a row is visible to this read iff its insert ts ≤ Tg AND no delete tombstone with ts ≤ Tg voids it</strong> (recall Lesson 20 —
a delete stamps a tombstone, an upsert is delete+insert). In other words, a read is not "the current final state" but "<strong>the snapshot as of
Tg</strong>". Two benefits: first, <strong>reads and writes don't block each other</strong> — writes keep appending at higher ts, reads only care about
their own Tg; second, <strong>results are inherently self-consistent</strong> — within one query, every segment and node filters by the same Tg, seeing
the same time-slice, never "new on one side, old on the other". MVCC turns the hard problem of concurrency into "<strong>everyone reads their own time
snapshot</strong>".</p>

<div class="cellgroup">
  <div class="cg-cap"><b>Multiple versions of one PK k</b>: reading at Tg=100, which version should be seen? (green ✓ = visible)</div>
  <div class="cells"><span class="lab">v1</span><span class="cell">insert k @ts=80</span><span class="sep">→</span><span class="cell dim">overwritten later</span></div>
  <div class="cells"><span class="lab">v2</span><span class="cell">delete k @ts=90</span><span class="sep">→</span><span class="cell dim">tombstone ts=90 ≤ 100</span></div>
  <div class="cells"><span class="lab">v3</span><span class="cell hl">insert k @ts=95</span><span class="sep">→</span><span class="cell q">ts=95 ≤ 100, no later tombstone ✓</span></div>
  <div class="cells"><span class="lab">v4</span><span class="cell">insert k @ts=120</span><span class="sep">→</span><span class="cell dim">ts=120 &gt; 100, invisible</span></div>
</div>

<h2>The wait mechanism: answer only once tsafe ≥ Tg</h2>
<p>Here is the crucial piece: <strong>how do we guarantee that the writes up to Tg have actually reached the QueryNode?</strong> After all, writes flow
asynchronously through the WAL; a node may not have consumed the latest yet. Milvus's trick is to give each QueryNode a <strong>tsafe (served watermark)</strong> —
how far it has consumed and applied the WAL, expressed as a TimeTick. TimeTick is the WAL's monotonically advancing clock (Lesson 16); each chunk of log a node
consumes pushes tsafe forward. <strong>When a read arrives with Tg, the node compares: if tsafe ≥ Tg, it has everything up to Tg, so search now; if tsafe &lt; Tg,
it <strong>suspends and waits</strong> until tsafe catches up to Tg (or times out)</strong>. This "<strong>wait until the data is fresh enough, then answer</strong>"
mechanism is the heart of <span class="mono">docs/developer_guides/how-guarantee-ts-works.md</span> — and the very reason the word "<strong>guarantee</strong>" is in
"guarantee timestamp".</p>

<div class="timeline">
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t1</span><span class="tl-c">writes keep entering the WAL, TimeTick advances; the QueryNode consumes and applies, tsafe rises</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t2</span><span class="tl-c">a read arrives with Tg=100; right now the node's tsafe=98 &lt; 100</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t3</span><span class="tl-c">the node <strong>suspends</strong>: keep consuming the WAL until tsafe ≥ 100</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t4</span><span class="tl-c">tsafe=100, <strong>all writes up to Tg are present</strong>; filter by MVCC and return</span></div>
</div>

<h2>The trade-off: the fresher you want it, the longer you may wait</h2>
<p>Now the design intent of the five levels is clear: <strong>they are a knob between "freshness" and "latency"</strong>. Strong sets Tg to the latest tMax —
sees the most, but if the node hasn't caught up it must <strong>wait</strong>, so latency may be higher. Bounded nudges Tg back a touch
(<span class="mono">tMax − gracefulTime</span>), trading "tolerate a few seconds of staleness" for "almost never wait", which is why it is a common
<strong>default</strong>. Eventually sets Tg tiny, <strong>never waits, returns instantly</strong>, at the cost of maybe missing the last few writes. Session
guarantees you <strong>at least read your own writes</strong>, friendly to "write then immediately query" interactions. Customized hands "as of when" entirely to
you. Recall Lesson 1's "<strong>query while you write</strong>": that works precisely because growing segments + the tsafe mechanism make "freshly written data
immediately visible to some Tg" — whether you see it, and whether you wait, is set by the level you choose. <strong>There is no one-size-fits-all answer, only a
trade-off matched to the scenario</strong>: want strong consistency, accept a possible wait; want low latency, accept possible staleness.</p>

<div class="cols">
  <div class="col"><h4>Toward freshness (Strong)</h4><p>see all committed writes so far; for correctness-critical scenarios. Cost: must wait when the node hasn't caught up; latency may rise.</p></div>
  <div class="col"><h4>Toward low latency (Bounded / Eventually)</h4><p>tolerate a little staleness, barely wait, respond fast; for high-concurrency cases (recommendation, RAG) where a few missing rows are harmless.</p></div>
</div>

<h2>A closing of the whole guide so far</h2>
<p>This lesson also <strong>closes the query path (Part 6)</strong>. Stringing the six parts together: data you write first becomes <strong>vectors</strong> (Part 2),
is <strong>written along the log</strong> via the Proxy into segments and binlogs (Part 4), and is <strong>built into indexes</strong> (Part 5); at query time the Proxy
<strong>sets Tg and dispatches</strong>, the delegator <strong>fans out</strong> to segments, segcore <strong>filters + searches</strong>, reduce <strong>merges</strong>, and
finally tsafe + MVCC guarantee you see <strong>a self-consistent snapshot with a freshness you can choose</strong>. With that, the main thread — "how one similarity
search is completed correctly, efficiently and controllably in a distributed system" — closes the loop. The remaining parts (the C++ core, the streaming system,
operations and contributing) drill further down and reach further out, but they all hang on this thread.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>TSO</strong>: a global, monotonic timestamp source in RootCoord; both writes and reads are stamped, giving the cluster one clock.</li>
    <li><strong>Guarantee ts Tg + five levels</strong>: Strong=latest tMax, Bounded=tMax−gracefulTime, Session=this session's last write, Eventually=1, Customized=user-given (<span class="mono">parseGuaranteeTsFromConsistency</span>).</li>
    <li><strong>MVCC</strong>: a row is visible iff insert ts ≤ Tg and no tombstone with ts ≤ Tg; a read sees "the snapshot as of Tg" — reads/writes don't block, results are self-consistent.</li>
    <li><strong>Wait mechanism</strong>: a QueryNode answers only once its <span class="mono">tsafe</span> (consumed WAL TimeTick) ≥ Tg — the source of the word "guarantee".</li>
    <li><strong>Trade-off</strong>: freshness ↔ latency on one knob; strong consistency may wait, low latency may be slightly stale — pick a level by scenario.</li>
  </ul>
</div>
""",
}
