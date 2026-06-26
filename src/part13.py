"""Part 13 - Capstone (synthesis): the life of one row, end to end."""

LESSON_57 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
这是全课的<strong>收束</strong>。前面我们把 Milvus 拆成了写入、索引、查询三条链路分别讲透；这一课不再拆，而是反过来——只<strong>跟着一行数据</strong>，
从你按下 <span class="mono">insert</span> 的那一刻，一路看它<strong>变得持久</strong>、<strong>能被搜到</strong>，最后被<strong>高效地长期服务</strong>。
把散落各课的零件，串成一条你能一眼看完的<strong>旅程</strong>。</p>

<div class="card analogy"><div class="tag">⚡ 打个比方</div>
<p>想象后厨的<strong>挂单系统</strong>：你在收银台敲下一单，单子一旦<strong>打印进"订单流水"</strong>，这单就<strong>绝不会丢</strong>了——哪怕屏幕黑了、机器重启，照着流水重念一遍就全回来了（这就是"<strong>持久</strong>"）。
几乎同一瞬间，墙上的菜品屏就能<strong>看到这单</strong>（这就是"<strong>可见</strong>"）。至于把它<strong>归档进台账、把常点的菜备料上架</strong>，是后厨<strong>慢慢在后台做</strong>的事，并不挡着这单先被看见、先开做。
一行数据进 Milvus，正是这个节奏：<strong>先持久、很快可见，落盘建索引都是后台慢工</strong>。</p></div>

<h2>目标：把三条链路，串成一行数据的旅程</h2>
<p>学到这里你已经分别认识了写入、索引、查询的每个零件，但真正容易卡住新手的，是它们<strong>合起来</strong>时的两个问题：
"我刚 <span class="mono">insert</span> 完，<strong>到底什么时候不会丢</strong>？"和"为什么<strong>有时候马上能搜到、有时候要等一下</strong>？"
这两个问题的答案，恰好是本课要立起来的两根支柱——<strong>持久边界</strong>与<strong>可见边界</strong>。把它们看清了，整套系统在你脑子里就从"一堆组件"变成"一条有节奏的流水线"。</p>

<div class="card macro"><div class="tag">🗺️ 大图景</div>
<p>一行数据有<strong>两条路同时在走</strong>：① <strong>前台路（快）</strong>——insert → Proxy 盖时间戳 → 写进 WAL <strong>即持久</strong> → 落进内存里的 growing 段 → tsafe 追上它的时间戳就<strong>可见</strong>；
② <strong>后台路（慢）</strong>——段满了就封段 → flush 成 binlog 落对象存储 → 建索引 → QueryNode 加载，然后<strong>接力</strong>由"封存段 + 索引"来服务这行。
关键直觉：<strong>"持久"和"可见"发生在前台、很早；落盘与建索引是后台慢工，并不挡查询</strong>。</p></div>

<div class="fig"><svg viewBox="0 0 760 300" role="img" aria-label="一条数据的一生：前台路 SDK 插入到 Proxy 盖时间戳与主键、写进 WAL 即持久、进入 growing 段、tsafe 追上即可见；后台路 封段到 flush 成 binlog、建索引、QueryNode 加载、再接力服务，后台不阻塞可见">
  <text x="380" y="22" text-anchor="middle" style="fill:var(--ink);font-weight:700">一条数据的一生：前台「写入→持久→可见」，后台「落盘→索引→加载」</text>
  <rect x="16" y="70" width="110" height="44" rx="9" style="fill:var(--blue-soft);stroke:var(--blue)"/><text x="71" y="90" text-anchor="middle" style="fill:var(--blue);font-weight:700">SDK</text><text x="71" y="107" text-anchor="middle" style="fill:var(--muted)">insert · 行</text>
  <rect x="170" y="70" width="110" height="44" rx="9" style="fill:var(--blue-soft);stroke:var(--blue)"/><text x="225" y="90" text-anchor="middle" style="fill:var(--blue);font-weight:700">Proxy</text><text x="225" y="107" text-anchor="middle" style="fill:var(--muted)">盖 ts · PK</text>
  <rect x="324" y="70" width="110" height="44" rx="9" style="fill:var(--amber-soft);stroke:var(--amber)"/><text x="379" y="90" text-anchor="middle" style="fill:var(--amber);font-weight:700">WAL / MQ</text><text x="379" y="107" text-anchor="middle" style="fill:var(--muted)">顺序 · 持久</text>
  <rect x="478" y="70" width="110" height="44" rx="9" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="533" y="90" text-anchor="middle" style="fill:var(--teal);font-weight:700">growing 段</text><text x="533" y="107" text-anchor="middle" style="fill:var(--muted)">驻内存</text>
  <rect x="632" y="70" width="110" height="44" rx="9" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="687" y="90" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">可见 ✓</text><text x="687" y="107" text-anchor="middle" style="fill:var(--muted)">tsafe ≥ ts</text>
  <line x1="126" y1="92" x2="168" y2="92" style="stroke:var(--line);stroke-width:2"/><path d="M168,92 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="280" y1="92" x2="322" y2="92" style="stroke:var(--line);stroke-width:2"/><path d="M322,92 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="434" y1="92" x2="476" y2="92" style="stroke:var(--line);stroke-width:2"/><path d="M476,92 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="588" y1="92" x2="630" y2="92" style="stroke:var(--line);stroke-width:2"/><path d="M630,92 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="456" y1="58" x2="456" y2="124" style="stroke:var(--accent);stroke-width:1.5;stroke-dasharray:4 3"/><text x="456" y="50" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700;font-size:11px">持久✓ 不丢</text>
  <path d="M533,114 C533,150 360,156 268,190" style="fill:none;stroke:var(--muted);stroke-width:1.5;stroke-dasharray:5 3"/><path d="M268,190 l9,-3 l-2,10 z" style="fill:var(--muted)"/><text x="470" y="132" text-anchor="middle" style="fill:var(--muted);font-size:11px">满/超时</text>
  <rect x="188" y="192" width="128" height="44" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="252" y="212" text-anchor="middle" style="fill:var(--ink);font-weight:700">seal 封段</text><text x="252" y="229" text-anchor="middle" style="fill:var(--muted)">只读</text>
  <rect x="332" y="192" width="128" height="44" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="396" y="212" text-anchor="middle" style="fill:var(--ink);font-weight:700">flush</text><text x="396" y="229" text-anchor="middle" style="fill:var(--muted)">binlog → 对象存储</text>
  <rect x="476" y="192" width="128" height="44" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="540" y="212" text-anchor="middle" style="fill:var(--ink);font-weight:700">index</text><text x="540" y="229" text-anchor="middle" style="fill:var(--muted)">建索引 · Knowhere</text>
  <rect x="620" y="192" width="128" height="44" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="684" y="212" text-anchor="middle" style="fill:var(--ink);font-weight:700">load</text><text x="684" y="229" text-anchor="middle" style="fill:var(--muted)">QueryNode 加载</text>
  <line x1="316" y1="214" x2="330" y2="214" style="stroke:var(--line);stroke-width:2"/><path d="M330,214 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="460" y1="214" x2="474" y2="214" style="stroke:var(--line);stroke-width:2"/><path d="M474,214 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="604" y1="214" x2="618" y2="214" style="stroke:var(--line);stroke-width:2"/><path d="M618,214 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <path d="M684,192 C684,158 686,148 687,116" style="fill:none;stroke:var(--teal);stroke-width:1.5;stroke-dasharray:5 3"/><path d="M687,116 l-5,11 l10,0 z" style="fill:var(--teal)"/><text x="706" y="166" text-anchor="start" style="fill:var(--teal);font-size:11px">接力</text>
  <text x="380" y="262" text-anchor="middle" style="fill:var(--faint);font-size:12px">后台（封段·落盘·建索引·加载）不阻塞「可见」：行在 growing 段里就已能被查到</text>
</svg><div class="figcap"><b>一条数据的一生</b>：<b>前台</b>很快——insert 写进 <b>WAL 即持久</b>（不丢），落进 <b>growing 段</b>，<b>tsafe 追上它的 ts 就能被搜到</b>；<b>后台</b>慢慢来——段满了<b>封段 → flush 成 binlog → 建索引 → QueryNode 加载</b>，然后<b>接力</b>由"封存段 + 索引"来服务。一句话：<b>"持久"和"可见"很早，落盘与索引是后台事，不挡查询。</b></div></div>

<h2>第 1 站 · 写入：进了日志就算数</h2>
<p>你调用 <span class="mono">insert</span>，请求先到 <strong>Proxy</strong>。Proxy 不存数据，它是<strong>门卫加调度</strong>：校验 schema、必要时向 RootCoord 申请一段<strong>全局唯一主键</strong>（autoID 时，由 RootCoord 的 ID allocator 批量发号）、
向 RootCoord 要一个<strong>时间戳 ts</strong>（TSO，全局单调递增——见<span class="inline">第 11 课</span>），再按主键哈希把每一行<strong>路由到某个 vchannel（分片）</strong>，最后把这批行打包成 <span class="mono">InsertMsg</span> <strong>写进该分片的 WAL</strong>。
源码可循：<span class="inline">internal/proxy/task_insert.go</span>（insertTask 的 PreExecute/Execute）、<span class="inline">internal/rootcoord</span>（TSO 与 ID allocator）、流式写入在 <span class="inline">internal/streamingnode</span> 与 <span class="inline">pkg/streaming</span>。</p>

<p>关键的一刻在这里：<strong>一旦 InsertMsg 追加进 WAL 并被确认（ack），这次写入就"算数"了</strong>——insert 返回成功。为什么这么早就敢返回？因为 WAL 是<strong>顺序、可靠、可重放</strong>的（<span class="inline">第 7 课</span>、<span class="inline">第 16 课</span>）：
哪怕下一秒整个进程崩了，这条记录还在日志里，重启后照着重放就回来了。<strong>"持久"不等于"落盘成了 binlog"，而是"进了 WAL"</strong>——这是理解后面一切的地基。</p>

<div class="flow">
  <div class="node"><div class="nt">SDK</div><div class="nd">insert 一批行</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">Proxy</div><div class="nd">校验 · 发 PK · 盖 ts · 按分片路由</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">WAL / MQ</div><div class="nd">追加 InsertMsg · ack＝持久</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">growing 段</div><div class="nd">消费日志 · 驻内存累积</div></div>
</div>

<p>这里还藏着一个常被忽略的好处：<strong>Proxy 自己不存任何数据，只盖戳、转发</strong>，所以它是<strong>无状态</strong>的——可以随意多开、横向扩展，任何一台 Proxy 都能处理任何一行的写入，挂一台换一台也毫无影响。这正是<span class="inline">第 53 课</span>"存算分离"在写入侧最直接的体现：<strong>把状态推给 WAL 和对象存储，节点本身轻得可以随时替换</strong>。</p>

<h2>第 2 站 · 持久 ≠ 可见：两条时间线</h2>
<p>写进 WAL，这行就<strong>持久</strong>了；但它<strong>什么时候能被搜到</strong>，是另一条时间线。负责某分片读的 <strong>delegator</strong>（在 QueryNode 里）也在<strong>消费同一条 WAL</strong>，把新行喂进它本地的 growing 段，
同时维护一个水位 <strong>tsafe</strong>＝"我已经消费到的时间戳"。一次查询会带一个<strong>保证时间戳（guarantee ts）</strong>，delegator <strong>只在 tsafe ≥ guarantee ts 时才返回</strong>——这样你绝不会读到一个"还没追上"的残缺快照（<span class="inline">第 26 课</span>、<span class="inline">第 30 课</span>）。</p>

<p>于是出现一个<strong>窗口</strong>：行已经持久（进了 WAL）、也已经躺在 growing 段里，但 delegator 的 tsafe 可能<strong>还差一点</strong>没追上它的 ts。
这就是为什么"<strong>强一致</strong>"读有时要<strong>等一下</strong>（它把 guarantee ts 设成"最新"，必须等 tsafe 追上）；而"<strong>最终一致 / 有界一致</strong>"读<strong>不等</strong>，直接读当前可见的快照、用一点新鲜度换低延迟。<strong>可见性，本质上只是一次时间戳比较。</strong></p>

<p>举个具体例子你立刻就懂：你刚 <span class="mono">insert</span> 一行，紧接着用 <strong>Strong（强一致）</strong>去搜它。若此刻 delegator 的 tsafe 还没追上这行的 ts，这次搜索会<strong>短暂阻塞、等水位涨上来再返回</strong>——于是你"写完马上就能搜到"。换成 <strong>Eventually（最终一致）</strong>，它<strong>不等</strong>，可能这一瞬还搜不到、过几毫秒就有了。<strong>延迟和新鲜度之间怎么取舍，就攥在你选的一致性级别里</strong>——而底层机制自始至终只是同一个 tsafe 比较，并没有为某个级别另起炉灶。</p>

<div class="fig"><svg viewBox="0 0 760 300" role="img" aria-label="持久与可见是两条时间线：行写进 WAL 被确认后立刻持久，但要等 delegator 的 tsafe 追上这行的时间戳才对强一致读可见；两者之间的窗口里行已在 growing 段，强一致读在此等待，最终一致读不等">
  <rect x="250" y="86" width="220" height="128" rx="10" style="fill:var(--amber-soft);stroke:var(--amber);stroke-dasharray:4 3"/>
  <text x="380" y="26" text-anchor="middle" style="fill:var(--ink);font-weight:700">「持久」和「可见」是两条时间线</text>
  <text x="74" y="106" text-anchor="end" style="fill:var(--amber);font-weight:700">持久</text>
  <line x1="90" y1="100" x2="704" y2="100" style="stroke:var(--line);stroke-width:2"/><path d="M704,100 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <circle cx="250" cy="100" r="7" style="fill:var(--amber)"/><text x="250" y="74" text-anchor="middle" style="fill:var(--amber);font-weight:700">WAL ack → 持久 ✓</text>
  <text x="74" y="206" text-anchor="end" style="fill:var(--teal);font-weight:700">可见</text>
  <line x1="90" y1="200" x2="704" y2="200" style="stroke:var(--line);stroke-width:2"/><path d="M704,200 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <circle cx="470" cy="200" r="7" style="fill:var(--teal)"/><text x="470" y="226" text-anchor="middle" style="fill:var(--teal);font-weight:700">tsafe ≥ ts → 可见 ✓</text>
  <text x="360" y="132" text-anchor="middle" style="fill:var(--muted);font-size:12px">这段窗口：已持久不丢</text>
  <text x="360" y="152" text-anchor="middle" style="fill:var(--muted);font-size:12px">growing 段已持有该行</text>
  <text x="360" y="172" text-anchor="middle" style="fill:var(--muted);font-size:12px">强一致读在此等 tsafe</text>
  <text x="380" y="264" text-anchor="middle" style="fill:var(--faint);font-size:12px">最终 / 有界一致读不等：直接读当前可见快照，用一点新鲜度换低延迟</text>
</svg><div class="figcap"><b>两条时间线</b>：行写进 WAL 被 ack 的瞬间就<b>持久</b>（左侧 amber 点）；但要等 delegator 的 <b>tsafe 追上这行的 ts</b> 才对强一致读<b>可见</b>（右侧 teal 点）。中间那段窗口里行已在 growing 段——<b>强一致读在此等待，最终一致读不等</b>。可见性＝一次时间戳比较。</div></div>

<h2>第 3 站 · 后台落盘：seal → flush → binlog</h2>
<p>前台已经"持久 + 可见"，后台才不紧不慢地开工。growing 段在内存里越攒越大，到了<strong>大小或时间阈值</strong>就被<strong>封段（seal）</strong>变只读；随后一个 <strong>SyncTask</strong> 把这段的列数据<strong>序列化成 binlog</strong>——
insert binlog（真数据）、stats binlog（统计/主键索引）、delta binlog（删除）——<strong>写进对象存储</strong>，DataCoord 记下这些 binlog 路径并<strong>推进 checkpoint</strong>。
到这一步，数据<strong>第二次变得更耐久</strong>：它现在独立于 WAL 存在于对象存储，就算 WAL 被截断也不怕（<span class="inline">第 17 课</span>、<span class="inline">第 18 课</span>）。源码在 <span class="inline">internal/flushcommon/writebuffer</span>、<span class="inline">internal/flushcommon/syncmgr</span> 与 <span class="inline">internal/storage</span>。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>封段 seal</h4><p>growing 段满/超时，转为只读，不再接收新行。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>flush 成 binlog</h4><p>SyncTask 把列序列化为 insert/stats/delta binlog，写进对象存储。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>记账 + 推进 checkpoint</h4><p>DataCoord 记下 binlog 路径；WAL 的消费位点前移，旧日志可回收。</p></div></div>
</div>

<p>为什么非要把这些活儿甩到后台？因为它们<strong>又重又慢</strong>：序列化几十万行、建一棵 HNSW 图，都是秒级甚至更久的重活。如果让 <span class="mono">insert</span> 一直<strong>傻等</strong>到落盘、建索引全做完才返回，写入吞吐立刻就被拖垮了。Milvus 的选择是把它们<strong>异步挪到后台</strong>，前台只留"写一条日志"这一件极快的事——<strong>这正是写入能扛住高并发的关键</strong>，也再次印证了那条主线：<strong>先持久、快返回，慢工放后台</strong>。</p>

<h2>第 4 站 · 建索引 + 加载：从"能查"到"查得快"</h2>
<p>封存的段还只能<strong>暴力扫</strong>，要"查得快"得有索引。DataCoord 的 index 调度发现这个 sealed 段<strong>还缺索引</strong>，就派一个构建任务给 <strong>IndexNode</strong>；IndexNode 读 binlog、用 <strong>Knowhere</strong> 建出 HNSW/IVF 之类的向量索引，写成<strong>索引文件</strong>落对象存储（<span class="inline">第 21 课</span>、<span class="inline">第 23 课</span>）。
接着 <strong>QueryCoord</strong> 把这个"已封存 + 已建索引"的段<strong>分配给某个 QueryNode</strong>，QueryNode 用 <strong>segcore</strong> 把列与索引<strong>加载</strong>进来（常用 mmap，见<span class="inline">第 27 课</span>、<span class="inline">第 35 课</span>）。</p>

<p>最后是漂亮的一手——<strong>接力（handoff）</strong>：在 sealed 段加载好之前，这行一直由 growing 段服务；加载完成后，delegator 把它从"growing 还在顶"切换成"<strong>由 sealed + 索引来服务</strong>"，并<strong>把 growing 里这部分排除掉</strong>，确保<strong>不重不漏</strong>（<span class="inline">第 26 课</span>）。
对查询者完全无感：可见性一刻没断，只是背后从"内存暴力"换成了"索引快搜"。</p>

<div class="cols">
  <div class="col"><h4>🌱 growing 段先顶（能查）</h4><p>新行驻内存、<strong>暴力扫</strong>，胜在<strong>最新、零等待</strong>。tsafe 追上即可见，不必等落盘建索引。</p></div>
  <div class="col"><h4>🧊 sealed + 索引接力（查得快）</h4><p>封存段加载索引后，由它<strong>高效服务</strong>；delegator 排除 growing 的重叠部分，<strong>不重不漏</strong>，可见性无缝衔接。</p></div>
</div>

<p>你可能会问：既然这行最终都要由索引来服务，为什么不<strong>干脆等索引建好再让它可见</strong>？因为建索引动辄数秒，真这么等，"刚写的数据搜不到"会长达好几秒——对很多在线场景完全无法接受。让 growing 段<strong>先用暴力扫顶上这几秒</strong>、再悄悄接力给索引，正是 Milvus 在"<strong>新鲜度</strong>"和"<strong>效率</strong>"之间拿捏出的那个恰到好处的平衡点。</p>

<p>把整段旅程里"谁碰了这一行"汇成一张表，方便你随时回查到对应的课：</p>

<table class="t">
  <tr><th>阶段</th><th>谁在做</th><th>源码包（文件 / 符号）</th><th>详见</th></tr>
  <tr><td>盖时间戳 / 发主键</td><td>Proxy + RootCoord</td><td class="mono">internal/proxy/task_insert.go · internal/rootcoord（TSO/IDAllocator）</td><td>第 10、11、15 课</td></tr>
  <tr><td>写日志（持久）</td><td>WAL / 流式系统</td><td class="mono">internal/streamingnode · pkg/streaming</td><td>第 16、31 课</td></tr>
  <tr><td>进 growing 段（可查）</td><td>delegator（QueryNode）</td><td class="mono">internal/querynodev2/delegator（tsafe）</td><td>第 26、30 课</td></tr>
  <tr><td>封段 + flush</td><td>writebuffer / SyncTask</td><td class="mono">internal/flushcommon/writebuffer · syncmgr</td><td>第 17、18 课</td></tr>
  <tr><td>记账 binlog</td><td>DataCoord</td><td class="mono">internal/datacoord · internal/storage</td><td>第 12、18 课</td></tr>
  <tr><td>建索引</td><td>IndexNode + Knowhere</td><td class="mono">internal/indexnode · internal/datacoord（index 调度）</td><td>第 21、22、23 课</td></tr>
  <tr><td>分配 + 加载</td><td>QueryCoord + segcore</td><td class="mono">internal/querycoordv2 · internal/core（segcore）</td><td>第 13、27 课</td></tr>
  <tr><td>接力服务</td><td>delegator</td><td class="mono">internal/querynodev2/delegator（handoff）</td><td>第 26 课</td></tr>
</table>

<h2>收尾 · 三个边界，一句话记住</h2>
<div class="card spark"><div class="tag">💡 一句话洞见</div>
<p><strong>持久很早、可见也很早，落盘与索引是后台的事。</strong> 新手最大的误会，是以为"要等数据 flush 成 binlog、建好索引、被加载，才算写成功、才能被搜到"。
其实恰恰相反：<strong>进了 WAL 就持久（不丢）、tsafe 追上就可见（能查）</strong>，这两件事都在前台、很快发生；封段、落盘、建索引、加载是<strong>后台慢工</strong>，只为"<strong>查得更快、留得更久</strong>"，从不挡着前台。</p></div>

<p>所以记住三个边界就够了：① <strong>持久边界 = WAL ack</strong>（进了日志就不丢，不必等落盘）；② <strong>可见边界 = tsafe ≥ ts</strong>（早，强一致才需等待）；③ <strong>服务接力 = flush + 建索引 + 加载之后</strong>，由 sealed + 索引从 growing 手里接棒。
这三个边界，正好把<span class="inline">第 51 课</span>的"日志即数据"、<span class="inline">第 52 课</span>的"边写边查"、<span class="inline">第 53 课</span>的"存算分离"收在了一行数据上。</p>

<div class="card key"><div class="tag">📌 本课要点</div>
<ul>
<li>一行数据有<strong>两条路同时走</strong>：前台「写入→持久→可见」快，后台「封段→落盘→建索引→加载」慢。</li>
<li><strong>持久 = 进 WAL 被 ack</strong>，insert 即可返回；不必等 flush 成 binlog。</li>
<li><strong>可见 = delegator 的 tsafe ≥ 这行的 ts</strong>；强一致读会等，最终/有界一致读不等。</li>
<li>新行先由 <strong>growing 段</strong>服务（最新、暴力）；建好索引加载后，delegator <strong>接力</strong>给 sealed + 索引，<strong>不重不漏</strong>。</li>
<li>后台落盘 / 建索引只为<strong>查得快、留得久</strong>，<strong>从不阻塞可见性</strong>。</li>
</ul></div>

<details><summary>深挖：删除和 upsert 也走同一条路吗？</summary>
<p>是的，而且复用得很优雅。删除不会去"擦掉"已有数据，而是写一条<strong>带时间戳的墓碑（delete record）</strong>进同一条 WAL，最终落成 <strong>delta binlog</strong>；查询时在段内用<strong>删除位图</strong>把"在你的 guarantee ts 之前已被删"的行<strong>过滤掉</strong>——
所以"可见性"同样只是一次时间戳比较（<span class="inline">第 20 课</span>、<span class="inline">第 30 课</span>）。<strong>upsert</strong> 则≈"删旧 + 插新"：同主键写入新版本并让旧版本对新读不可见。换句话说，<strong>插入、删除、更新，走的是同一条"日志 → 段 → 时间戳可见"的路</strong>，只是携带的消息类型不同——这正是"日志即数据"的威力：一套机制，统一了所有写。</p></details>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
This is the course's <strong>finale</strong>. We spent the whole guide taking Milvus apart into three paths — write, index, query. This lesson does the opposite: it <strong>follows one single row</strong>,
from the instant you press <span class="mono">insert</span>, watching it become <strong>durable</strong>, then <strong>searchable</strong>, and finally <strong>served efficiently</strong> for the long run.
The parts scattered across the course, threaded into one <strong>journey</strong> you can read at a glance.</p>

<div class="card analogy"><div class="tag">⚡ An analogy</div>
<p>Picture a kitchen's <strong>order-ticket system</strong>: you punch in an order at the register, and the moment it's <strong>printed into the "order log"</strong> that order <strong>can never be lost</strong> — even if the screen goes dark or the machine reboots, replaying the log brings it all back (that's <strong>durable</strong>).
Almost the same instant, the kitchen display <strong>shows the order</strong> (that's <strong>visible</strong>). Filing it into the ledger and pre-stocking the popular dishes are things the kitchen does <strong>slowly, in the background</strong> — they don't block this order from being seen and started first.
A row entering Milvus follows exactly this rhythm: <strong>durable first, visible soon after, flushing and indexing are slow background work</strong>.</p></div>

<h2>The goal: thread three paths into one row's journey</h2>
<p>By now you know each part of write, index and query separately. What actually trips up newcomers is the two questions that arise when they <strong>come together</strong>:
"I just finished <span class="mono">insert</span> — <strong>when exactly is it safe from loss</strong>?" and "why is it <strong>sometimes searchable instantly, sometimes only after a brief wait</strong>?"
The answers are the two pillars this lesson erects — the <strong>durability boundary</strong> and the <strong>visibility boundary</strong>. See them clearly and the whole system turns, in your head, from "a pile of components" into "one pipeline with a rhythm."</p>

<div class="card macro"><div class="tag">🗺️ The big picture</div>
<p>One row travels <strong>two paths at once</strong>: ① the <strong>foreground (fast)</strong> — insert → Proxy stamps a timestamp → written to the WAL is <strong>durable</strong> → lands in an in-memory growing segment → it's <strong>visible</strong> once tsafe catches up to its timestamp;
② the <strong>background (slow)</strong> — the segment fills and seals → flush into binlogs in object storage → build the index → QueryNode loads it, then a <strong>handoff</strong> lets "sealed segment + index" serve this row.
The key intuition: <strong>"durable" and "visible" happen in the foreground, early; flushing and indexing are slow background work that never blocks queries</strong>.</p></div>

<div class="fig"><svg viewBox="0 0 760 300" role="img" aria-label="The life of a row: foreground path SDK insert to Proxy stamps timestamp and PK, written to WAL is durable, enters the growing segment, visible once tsafe catches up; background path seal to flush into binlog, build index, QueryNode load, then handoff serving, background never blocking visibility">
  <text x="380" y="22" text-anchor="middle" style="fill:var(--ink);font-weight:700">The life of a row: foreground "write→durable→visible", background "flush→index→load"</text>
  <rect x="16" y="70" width="110" height="44" rx="9" style="fill:var(--blue-soft);stroke:var(--blue)"/><text x="71" y="90" text-anchor="middle" style="fill:var(--blue);font-weight:700">SDK</text><text x="71" y="107" text-anchor="middle" style="fill:var(--muted)">insert · row</text>
  <rect x="170" y="70" width="110" height="44" rx="9" style="fill:var(--blue-soft);stroke:var(--blue)"/><text x="225" y="90" text-anchor="middle" style="fill:var(--blue);font-weight:700">Proxy</text><text x="225" y="107" text-anchor="middle" style="fill:var(--muted)">stamp ts · PK</text>
  <rect x="324" y="70" width="110" height="44" rx="9" style="fill:var(--amber-soft);stroke:var(--amber)"/><text x="379" y="90" text-anchor="middle" style="fill:var(--amber);font-weight:700">WAL / MQ</text><text x="379" y="107" text-anchor="middle" style="fill:var(--muted)">ordered · durable</text>
  <rect x="478" y="70" width="110" height="44" rx="9" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="533" y="90" text-anchor="middle" style="fill:var(--teal);font-weight:700">growing seg</text><text x="533" y="107" text-anchor="middle" style="fill:var(--muted)">in memory</text>
  <rect x="632" y="70" width="110" height="44" rx="9" style="fill:var(--accent-soft);stroke:var(--accent)"/><text x="687" y="90" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">visible ✓</text><text x="687" y="107" text-anchor="middle" style="fill:var(--muted)">tsafe ≥ ts</text>
  <line x1="126" y1="92" x2="168" y2="92" style="stroke:var(--line);stroke-width:2"/><path d="M168,92 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="280" y1="92" x2="322" y2="92" style="stroke:var(--line);stroke-width:2"/><path d="M322,92 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="434" y1="92" x2="476" y2="92" style="stroke:var(--line);stroke-width:2"/><path d="M476,92 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="588" y1="92" x2="630" y2="92" style="stroke:var(--line);stroke-width:2"/><path d="M630,92 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="456" y1="58" x2="456" y2="124" style="stroke:var(--accent);stroke-width:1.5;stroke-dasharray:4 3"/><text x="456" y="50" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700;font-size:11px">durable ✓</text>
  <path d="M533,114 C533,150 360,156 268,190" style="fill:none;stroke:var(--muted);stroke-width:1.5;stroke-dasharray:5 3"/><path d="M268,190 l9,-3 l-2,10 z" style="fill:var(--muted)"/><text x="470" y="132" text-anchor="middle" style="fill:var(--muted);font-size:11px">full/timeout</text>
  <rect x="188" y="192" width="128" height="44" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="252" y="212" text-anchor="middle" style="fill:var(--ink);font-weight:700">seal</text><text x="252" y="229" text-anchor="middle" style="fill:var(--muted)">read-only</text>
  <rect x="332" y="192" width="128" height="44" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="396" y="212" text-anchor="middle" style="fill:var(--ink);font-weight:700">flush</text><text x="396" y="229" text-anchor="middle" style="fill:var(--muted)">binlog → store</text>
  <rect x="476" y="192" width="128" height="44" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="540" y="212" text-anchor="middle" style="fill:var(--ink);font-weight:700">index</text><text x="540" y="229" text-anchor="middle" style="fill:var(--muted)">Knowhere</text>
  <rect x="620" y="192" width="128" height="44" rx="9" style="fill:var(--panel-2);stroke:var(--line)"/><text x="684" y="212" text-anchor="middle" style="fill:var(--ink);font-weight:700">load</text><text x="684" y="229" text-anchor="middle" style="fill:var(--muted)">QueryNode</text>
  <line x1="316" y1="214" x2="330" y2="214" style="stroke:var(--line);stroke-width:2"/><path d="M330,214 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="460" y1="214" x2="474" y2="214" style="stroke:var(--line);stroke-width:2"/><path d="M474,214 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <line x1="604" y1="214" x2="618" y2="214" style="stroke:var(--line);stroke-width:2"/><path d="M618,214 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <path d="M684,192 C684,158 686,148 687,116" style="fill:none;stroke:var(--teal);stroke-width:1.5;stroke-dasharray:5 3"/><path d="M687,116 l-5,11 l10,0 z" style="fill:var(--teal)"/><text x="706" y="166" text-anchor="start" style="fill:var(--teal);font-size:11px">handoff</text>
  <text x="380" y="262" text-anchor="middle" style="fill:var(--faint);font-size:12px">background (seal·flush·index·load) doesn't block "visible": the row is searchable while still in the growing segment</text>
</svg><div class="figcap"><b>The life of a row</b>: the <b>foreground</b> is fast — insert is written to the <b>WAL = durable</b> (no loss), lands in a <b>growing segment</b>, and is <b>searchable once tsafe reaches its ts</b>; the <b>background</b> takes its time — a full segment <b>seals → flushes to binlog → is indexed → loaded by a QueryNode</b>, then a <b>handoff</b> lets "sealed + index" serve it. In a sentence: <b>"durable" and "visible" are early; flush and index are background work that never blocks queries.</b></div></div>

<h2>Stop 1 · Write: it counts once it's in the log</h2>
<p>You call <span class="mono">insert</span>, and the request hits the <strong>Proxy</strong> first. The Proxy stores nothing; it is <strong>gatekeeper plus dispatcher</strong>: it validates the schema, requests a batch of <strong>globally-unique primary keys</strong> when autoID is on (handed out in bulk by RootCoord's ID allocator), asks RootCoord for a <strong>timestamp ts</strong> (TSO, globally monotonic — see <span class="inline">Lesson 11</span>), hashes each row to a <strong>vchannel (shard)</strong>, and finally packs the batch into an <span class="mono">InsertMsg</span> <strong>written to that shard's WAL</strong>.
Trace it in source: <span class="inline">internal/proxy/task_insert.go</span> (insertTask's PreExecute/Execute), <span class="inline">internal/rootcoord</span> (TSO and ID allocator), with streaming writes in <span class="inline">internal/streamingnode</span> and <span class="inline">pkg/streaming</span>.</p>

<p>Here is the pivotal moment: <strong>once the InsertMsg is appended to the WAL and acknowledged, the write "counts"</strong> — insert returns success. Why dare return so early? Because the WAL is <strong>ordered, reliable and replayable</strong> (<span class="inline">Lesson 7</span>, <span class="inline">Lesson 16</span>): even if the whole process crashes a second later, the record is still in the log, and a replay after restart brings it back. <strong>"Durable" does not mean "flushed into a binlog" — it means "in the WAL"</strong>, and that is the bedrock of everything that follows.</p>

<div class="flow">
  <div class="node"><div class="nt">SDK</div><div class="nd">insert a batch of rows</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">Proxy</div><div class="nd">validate · assign PK · stamp ts · route by shard</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">WAL / MQ</div><div class="nd">append InsertMsg · ack = durable</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">growing seg</div><div class="nd">consume log · accrue in memory</div></div>
</div>

<p>There's an easily-missed bonus here: <strong>the Proxy stores no data, it only stamps and forwards</strong>, so it is <strong>stateless</strong> — you can run many of them, scale them out, any Proxy can handle any row's write, and losing one and swapping in another changes nothing. This is the most direct expression of <span class="inline">Lesson 53</span>'s storage–compute separation on the write side: <strong>push state out to the WAL and object storage, and the node itself stays light enough to replace at any time</strong>.</p>

<h2>Stop 2 · Durable ≠ visible: two timelines</h2>
<p>Written to the WAL, the row is <strong>durable</strong>; but <strong>when it can be searched</strong> is a different timeline. The <strong>delegator</strong> that serves reads for a shard (inside a QueryNode) is <strong>consuming the very same WAL</strong>, feeding new rows into its own growing segment, while maintaining a watermark <strong>tsafe</strong> = "the timestamp I've consumed up to." A query carries a <strong>guarantee timestamp</strong>, and the delegator <strong>only returns once tsafe ≥ guarantee ts</strong> — so you never read a "not-caught-up", partial snapshot (<span class="inline">Lesson 26</span>, <span class="inline">Lesson 30</span>).</p>

<p>Hence a <strong>window</strong> appears: the row is already durable (in the WAL) and already sitting in the growing segment, yet the delegator's tsafe may still be <strong>a hair behind</strong> its ts. That's why a <strong>Strong-consistency</strong> read sometimes <strong>waits</strong> (it sets the guarantee ts to "latest" and must wait for tsafe to catch up), while an <strong>Eventually / Bounded</strong> read <strong>doesn't wait</strong>, reading the currently-visible snapshot and trading a little freshness for low latency. <strong>Visibility is, at heart, a single timestamp comparison.</strong></p>

<p>A concrete example makes it click: you just <span class="mono">insert</span> a row, then immediately search for it with <strong>Strong</strong> consistency. If the delegator's tsafe hasn't yet reached the row's ts, the search <strong>briefly blocks and returns once the watermark rises</strong> — so you "can search it the moment you finish writing." Switch to <strong>Eventually</strong> and it <strong>doesn't wait</strong>: maybe it's not there this instant, but it is a few milliseconds later. <strong>How you trade latency against freshness is held entirely in the consistency level you choose</strong> — while underneath it's always the same tsafe comparison, with no separate machinery for any one level.</p>

<div class="fig"><svg viewBox="0 0 760 300" role="img" aria-label="Durable and visible are two timelines: the row is durable the instant its WAL write is acked, but it is only visible to a Strong read once the delegator's tsafe reaches the row's timestamp; in the window between, the row is already in the growing segment, a Strong read waits here while an Eventually read does not">
  <rect x="248" y="86" width="248" height="128" rx="10" style="fill:var(--amber-soft);stroke:var(--amber);stroke-dasharray:4 3"/>
  <text x="380" y="26" text-anchor="middle" style="fill:var(--ink);font-weight:700">"Durable" and "visible" are two timelines</text>
  <text x="74" y="106" text-anchor="end" style="fill:var(--amber);font-weight:700">durable</text>
  <line x1="90" y1="100" x2="704" y2="100" style="stroke:var(--line);stroke-width:2"/><path d="M704,100 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <circle cx="248" cy="100" r="7" style="fill:var(--amber)"/><text x="248" y="74" text-anchor="middle" style="fill:var(--amber);font-weight:700">WAL ack → durable ✓</text>
  <text x="74" y="206" text-anchor="end" style="fill:var(--teal);font-weight:700">visible</text>
  <line x1="90" y1="200" x2="704" y2="200" style="stroke:var(--line);stroke-width:2"/><path d="M704,200 l-10,-5 l0,10 z" style="fill:var(--line)"/>
  <circle cx="496" cy="200" r="7" style="fill:var(--teal)"/><text x="496" y="226" text-anchor="middle" style="fill:var(--teal);font-weight:700">tsafe ≥ ts → visible ✓</text>
  <text x="372" y="132" text-anchor="middle" style="fill:var(--muted);font-size:12px">this window: already durable</text>
  <text x="372" y="152" text-anchor="middle" style="fill:var(--muted);font-size:12px">growing seg already holds the row</text>
  <text x="372" y="172" text-anchor="middle" style="fill:var(--muted);font-size:12px">a Strong read waits for tsafe here</text>
  <text x="380" y="264" text-anchor="middle" style="fill:var(--faint);font-size:12px">Eventually / Bounded reads don't wait: they read the currently-visible snapshot, trading freshness for latency</text>
</svg><div class="figcap"><b>Two timelines</b>: the row is <b>durable</b> the instant its WAL write is acked (left amber dot); but only <b>visible</b> to a Strong read once the delegator's <b>tsafe reaches the row's ts</b> (right teal dot). In the window between, the row is already in the growing segment — <b>a Strong read waits here, an Eventually read does not</b>. Visibility = one timestamp comparison.</div></div>

<h2>Stop 3 · Background flush: seal → flush → binlog</h2>
<p>The foreground already has "durable + visible"; only now does the background get to work, unhurried. The growing segment swells in memory until it hits a <strong>size or time threshold</strong> and is <strong>sealed</strong> (made read-only); then a <strong>SyncTask</strong> <strong>serializes its columns into binlogs</strong> — insert binlog (the real data), stats binlog (statistics / primary-key index), delta binlog (deletes) — <strong>written into object storage</strong>, with DataCoord recording those binlog paths and <strong>advancing the checkpoint</strong>.
At this step the data becomes <strong>durable a second time, more solidly</strong>: it now exists in object storage independent of the WAL, so even WAL truncation is fine (<span class="inline">Lesson 17</span>, <span class="inline">Lesson 18</span>). Source lives in <span class="inline">internal/flushcommon/writebuffer</span>, <span class="inline">internal/flushcommon/syncmgr</span> and <span class="inline">internal/storage</span>.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>seal</h4><p>The growing segment is full / timed out; it turns read-only and accepts no new rows.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>flush to binlog</h4><p>A SyncTask serializes columns into insert/stats/delta binlogs, written to object storage.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>record + advance checkpoint</h4><p>DataCoord records the binlog paths; the WAL consume offset moves forward, old log reclaimable.</p></div></div>
</div>

<p>Why insist on pushing this work to the background? Because it is <strong>heavy and slow</strong>: serializing hundreds of thousands of rows, building an HNSW graph — these take seconds or more. If <span class="mono">insert</span> had to <strong>sit and wait</strong> for flush and indexing to finish before returning, write throughput would collapse. Milvus's choice is to <strong>do them asynchronously in the background</strong>, leaving the foreground with just "write one log entry," the one fast thing — <strong>which is exactly why writes sustain high concurrency</strong>, and proves the throughline again: <strong>durable first, return fast, slow work goes to the background</strong>.</p>

<h2>Stop 4 · Index + load: from "searchable" to "searchable fast"</h2>
<p>A sealed segment can still only be <strong>brute-force scanned</strong>; to be "fast" it needs an index. DataCoord's index scheduling notices this sealed segment <strong>still lacks an index</strong> and dispatches a build task to an <strong>IndexNode</strong>; the IndexNode reads the binlog, uses <strong>Knowhere</strong> to build an HNSW/IVF-style vector index, and writes <strong>index files</strong> into object storage (<span class="inline">Lesson 21</span>, <span class="inline">Lesson 23</span>).
Then <strong>QueryCoord</strong> <strong>assigns</strong> this "sealed + indexed" segment to some <strong>QueryNode</strong>, which uses <strong>segcore</strong> to <strong>load</strong> the columns and index in (often mmap — see <span class="inline">Lesson 27</span>, <span class="inline">Lesson 35</span>).</p>

<p>Last comes the elegant move — the <strong>handoff</strong>: until the sealed segment is loaded, the row is served by the growing segment; once loading completes, the delegator switches it from "growing still covers it" to "<strong>served by sealed + index</strong>", and <strong>excludes that portion from growing</strong>, guaranteeing <strong>no double-count, no gap</strong> (<span class="inline">Lesson 26</span>). To the querier it's entirely seamless: visibility never lapses for an instant, the engine behind it merely swaps "in-memory brute force" for "fast indexed search."</p>

<div class="cols">
  <div class="col"><h4>🌱 growing serves first (searchable)</h4><p>New rows in memory, <strong>brute-force scanned</strong>, winning on <strong>freshness and zero wait</strong>. Visible once tsafe catches up — no need to wait for flush or index.</p></div>
  <div class="col"><h4>🧊 sealed + index takes over (fast)</h4><p>Once the sealed segment loads its index, it <strong>serves efficiently</strong>; the delegator excludes the overlapping part of growing, <strong>no double-count, no gap</strong>, visibility seamless.</p></div>
</div>

<p>You might ask: since the row will ultimately be served by the index anyway, why not <strong>just wait for the index before making it visible</strong>? Because building an index takes seconds, and waiting like that would mean "just-written data isn't searchable" for several seconds — unacceptable for many online scenarios. Letting the growing segment <strong>cover those seconds with brute force</strong>, then quietly handing off to the index, is exactly the well-judged balance Milvus strikes between <strong>freshness</strong> and <strong>efficiency</strong>.</p>

<p>Here's "who touched this row" across the whole journey, as a table you can use to jump back to the relevant lesson:</p>

<table class="t">
  <tr><th>Stage</th><th>Who does it</th><th>Source package (file / symbol)</th><th>See</th></tr>
  <tr><td>stamp ts / assign PK</td><td>Proxy + RootCoord</td><td class="mono">internal/proxy/task_insert.go · internal/rootcoord (TSO/IDAllocator)</td><td>Lessons 10, 11, 15</td></tr>
  <tr><td>write log (durable)</td><td>WAL / streaming</td><td class="mono">internal/streamingnode · pkg/streaming</td><td>Lessons 16, 31</td></tr>
  <tr><td>enter growing seg (searchable)</td><td>delegator (QueryNode)</td><td class="mono">internal/querynodev2/delegator (tsafe)</td><td>Lessons 26, 30</td></tr>
  <tr><td>seal + flush</td><td>writebuffer / SyncTask</td><td class="mono">internal/flushcommon/writebuffer · syncmgr</td><td>Lessons 17, 18</td></tr>
  <tr><td>record binlog</td><td>DataCoord</td><td class="mono">internal/datacoord · internal/storage</td><td>Lessons 12, 18</td></tr>
  <tr><td>build index</td><td>IndexNode + Knowhere</td><td class="mono">internal/indexnode · internal/datacoord (index scheduling)</td><td>Lessons 21, 22, 23</td></tr>
  <tr><td>assign + load</td><td>QueryCoord + segcore</td><td class="mono">internal/querycoordv2 · internal/core (segcore)</td><td>Lessons 13, 27</td></tr>
  <tr><td>handoff serving</td><td>delegator</td><td class="mono">internal/querynodev2/delegator (handoff)</td><td>Lesson 26</td></tr>
</table>

<h2>Wrap-up · Three boundaries, in one breath</h2>
<div class="card spark"><div class="tag">💡 The one insight</div>
<p><strong>Durable is early, visible is early too; flush and index are the background's job.</strong> The newcomer's biggest misconception is thinking "the write only succeeds, and the data only becomes searchable, after it's flushed into a binlog, indexed and loaded."
The truth is the opposite: <strong>in the WAL means durable (no loss), tsafe catching up means visible (searchable)</strong> — both happen in the foreground, fast; sealing, flushing, indexing and loading are <strong>slow background work</strong>, only to "<strong>search faster, keep longer</strong>", never blocking the foreground.</p></div>

<p>So three boundaries are all you need to remember: ① the <strong>durability boundary = WAL ack</strong> (in the log means no loss, no need to wait for flush); ② the <strong>visibility boundary = tsafe ≥ ts</strong> (early; only Strong reads wait); ③ the <strong>serving handoff = after flush + index + load</strong>, when sealed + index takes over from growing.
These three boundaries gather <span class="inline">Lesson 51</span>'s "log as data", <span class="inline">Lesson 52</span>'s "query while you write" and <span class="inline">Lesson 53</span>'s "storage–compute separation" onto a single row.</p>

<div class="card key"><div class="tag">📌 Key points</div>
<ul>
<li>A row travels <strong>two paths at once</strong>: the foreground "write→durable→visible" is fast, the background "seal→flush→index→load" is slow.</li>
<li><strong>Durable = appended to the WAL and acked</strong>; insert can return immediately, without waiting for a binlog flush.</li>
<li><strong>Visible = the delegator's tsafe ≥ the row's ts</strong>; Strong reads wait, Eventually/Bounded reads don't.</li>
<li>New rows are served first by the <strong>growing segment</strong> (freshest, brute force); after the index loads, the delegator <strong>hands off</strong> to sealed + index, with <strong>no double-count, no gap</strong>.</li>
<li>Background flush / index exist only to <strong>search faster, keep longer</strong>, and <strong>never block visibility</strong>.</li>
</ul></div>

<details><summary>Going deeper: do delete and upsert take the same path?</summary>
<p>Yes — and the reuse is elegant. A delete doesn't "erase" existing data; it writes a <strong>timestamped tombstone (delete record)</strong> into the same WAL, eventually landing as a <strong>delta binlog</strong>; at query time a <strong>delete bitmap</strong> within the segment <strong>filters out</strong> rows "already deleted before your guarantee ts" — so "visibility" is again just a timestamp comparison (<span class="inline">Lesson 20</span>, <span class="inline">Lesson 30</span>). <strong>Upsert</strong> ≈ "delete old + insert new": it writes a new version under the same primary key and makes the old version invisible to new reads. In other words, <strong>insert, delete and update all travel the same "log → segment → timestamped visibility" path</strong>, differing only in the message type they carry — which is the power of "log as data": one mechanism, unifying every write.</p></details>
""",
}
