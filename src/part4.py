"""Part 4 · The write path (lessons 15-20). One Part module per milestone.

M4a covers L15-L17: insert via Proxy, the streaming WAL backbone, and how WAL
entries become flushed binlogs. Each value is ``{"zh": html, "en": html}`` and is
wired into registry.CONTENT / shell.PAGES / shell.SUBTITLES / quizzes.QUIZZES.

Authoring model mirrors part1-3: lead -> analogy card -> macro card -> >=3 visual
diagrams per language -> cited code file+symbol -> key-points card. Symbols are
verified against /home/verden/course/milvus.
"""

LESSON_15 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前三部分我们把整座集群、每个协调者都看了一遍。从这一课起，我们沿着<strong>一行数据</strong>走一趟——它如何从客户端的 <span class="mono">insert</span> 调用，
一路变成对象存储里可被检索的段。第一站仍是老朋友 <strong>Proxy</strong>：但这次我们不看它怎么把关、怎么调度，而是聚焦它在<strong>写入</strong>这条路上到底做了哪些"加工"。
读完你会发现，Proxy 在写入路上的角色，更像一个<strong>把原料预处理成半成品</strong>的车间：进来的是杂乱的一批行，出去的是分好片、贴好时间戳、可直接投入 WAL 的有序消息。
</p>

<div class="card analogy">
  <div class="tag">📮 生活类比</div>
  把一次 insert 想象成往全国寄一批包裹。你把成箱的包裹（一批行）交到<strong>邮局柜台</strong>（Proxy）：柜员先<strong>核对面单</strong>（schema 校验：字段对不对、类型符不符）、
  给没贴单号的包裹<strong>补一个单号</strong>（主键自动填充），再按收件地址的<strong>邮编把包裹分到不同的分拣道</strong>（按主键哈希到 vchannel）。
  分好后盖上<strong>统一的收寄时间戳</strong>，整批一起投入传送带（写进 WAL）。柜台自己<strong>不送货、不入库</strong>，但这一批要么全部受理、要么整批退回——这就是写入的"原子批"。
  这一整套"核单—贴号—分拣—盖戳—上传送带"，就是 Proxy 在写入路上的全部活计；它快、轻、可多开，真正的"送货入库"留给后面的角色。
</div>

<h2>第一关：schema 校验与主键</h2>
<p>insert 请求进入 Proxy 后，被包装成 <span class="mono">insertTask</span>，先在 <span class="mono">PreExecute</span> 阶段做<strong>数据正确性</strong>检查。最核心的一步是
<span class="inline">checkPrimaryFieldData</span>：它要确认这批数据里的<strong>主键列</strong>是否合法、是否与 schema 声明一致。如果集合开了<strong>主键自增（autoID）</strong>，
客户端根本不会传主键，这一步就负责<strong>为每一行分配一个全局唯一的主键</strong>并回填；如果是用户自带主键，则校验其非空、不重复、类型匹配。校验完成后，这批行的主键 <span class="mono">IDs</span> 才算确定下来。</p>

<p>为什么主键要在<strong>这么靠前</strong>的位置敲定？因为接下来"把哪一行发到哪个分片"完全依赖主键。主键不仅是身份证，更是<strong>路由依据</strong>——
没有确定的主键，后面一步都没法走。所以你可以把这一步理解成"先给每个包裹贴好唯一单号，才能按单号分拣"。它同时也是 Proxy 对客户端数据做的<strong>最后一道语义校验</strong>：
一旦放行进入写入流水线，后端就默认这批数据"格式正确、主键齐全"，不再重复校验，把宝贵的算力留给真正的落盘。</p>

<p>这里还藏着一个值得展开的设计取舍：<strong>主键到底由谁来生成</strong>。开了 autoID 的集合，主键由 Milvus 在 Proxy 这一层统一分配——它向协调者要一段全局唯一的 ID 区间，
再切给这一批行。好处是客户端完全不用操心唯一性，坏处是你无法用业务含义（比如订单号）当主键。反过来，自带主键把生成权交给业务方，灵活但要你自己保证不重复。
无论哪种，<strong>校验都必须在写入之前完成</strong>：一旦数据进了 WAL，主键就成了这条记录"洗不掉的身份"，后续的更新、删除、去重全靠它对齐。
正因如此，Milvus 宁可在最前端多花一点校验成本，也绝不把一个"主键可能非法"的批次放进日志——这是用<strong>前置校验换取后端简单</strong>的典型分层思路。</p>

<p>还要留意一个常被忽略的细节：这一步顺带把<strong>客户端传来的字段</strong>与 schema 做了对齐。客户端可能少传了某个有默认值的字段、可能把列的顺序写反、
也可能携带了 schema 里没有的动态字段（第 6 课）。<span class="mono">checkPrimaryFieldData</span> 及其周边校验会把这些情况一一规整：补默认值、按 schema 顺序对齐、
合法的动态字段并入 <span class="mono">$meta</span>。等这一关走完，进入写入流水线的就是一批"<strong>干净、规整、主键齐全</strong>"的数据，后端再也不必为格式问题分心。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/proxy/task_insert.go</span><span class="ln">PreExecute 里敲定主键</span></div>
  <pre><span class="cm">// 校验/补全主键，返回这批行的 IDs；autoID 时在此分配</span>
it.result.IDs, err = checkPrimaryFieldData(ctx, allFields, it.schema, it.insertMsg)
<span class="kw">if</span> err != <span class="kw">nil</span> {
    mlog.Warn(ctx, <span class="st">"check primary field data error"</span>, mlog.Err(err))
    <span class="kw">return</span> err
}</pre>
</div>

<h2>第二关：按主键哈希到 vchannel</h2>
<p>校验过关后进入 <span class="mono">Execute</span>。Proxy 先向缓存要这个集合的<strong>虚拟通道列表</strong>（<span class="inline">chMgr.getVChannels(collID)</span>）——
回忆第 7 课：一个集合被切成若干<strong>分片（shard）</strong>，每个分片对应一个 <strong>vchannel</strong>。现在的关键动作是 <span class="inline">assignChannelsByPK</span>：
它<strong>逐行</strong>取出主键，做一次哈希，按哈希值把行号分到对应的 vchannel 上，得到一张"<span class="mono">channel → 行偏移列表</span>"的映射。</p>

<p>这一步决定了<strong>数据的物理分布</strong>。同一个主键永远哈希到同一个 vchannel，于是同一行的所有版本（包括后续的更新、删除）都落在同一个分片里——
这对后面"按主键删除""判断某行属于哪个段"至关重要（第 17、20 课会用到）。哈希分片还带来<strong>负载均衡</strong>：海量行被均匀摊到各个 vchannel，
没有哪个分片会成为热点。理解这一点，你就明白了 Milvus "<strong>水平扩展靠分片、分片靠主键哈希</strong>"的底层逻辑。</p>

<p>这里要分清两个容易混淆的概念：<strong>vchannel（虚拟通道）</strong>与<strong>pchannel（物理通道）</strong>。Proxy 哈希得到的是 vchannel——它是"集合的某个分片"这一<strong>逻辑</strong>概念，
随集合创建而生、随集合删除而灭。而真正承载 WAL 的是 pchannel——它是一条<strong>物理</strong>的日志分区，数量固定、由集群预先开好（对应一个消息队列 topic）。
多个集合的多个 vchannel 会<strong>复用</strong>同一条 pchannel。这层映射（vchannel → pchannel）下一课会细讲，这里你只需记住：Proxy 关心的是逻辑分片 vchannel，
而 vchannel 名字里就编码了它属于哪条 pchannel，写入时据此找到对应的 WAL。</p>

<p>还有一个微妙之处：如果集合设了<strong>分区键（partition key，第 6 课）</strong>，分片逻辑会走另一条分支
<span class="inline">repackInsertDataWithPartitionKeyForStreamingService</span>——它在哈希分片之外，还要按分区键把行归入正确的逻辑分区。
但骨架不变：<strong>仍然是"按某个键算出归属、再分组打包"</strong>。无论有没有分区键，Proxy 这一层的使命都一样：把一批无序的行，<strong>确定性地</strong>切成"每个 vchannel 一组"。
确定性很关键——同样的输入永远得到同样的分片结果，这样重试、回放才不会把数据弄乱。</p>

<div class="flow">
  <div class="node"><div class="nt">一批行</div><div class="nd">含主键列 IDs</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">assignChannelsByPK</div><div class="nd">逐行哈希主键</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">vchannel A</div><div class="nd">行 0,3,7…</div></div>
  <div class="arrow">＋</div>
  <div class="node"><div class="nt">vchannel B</div><div class="nd">行 1,2,5…</div></div>
</div>

<h2>第三关：打包成消息、Append 进 WAL</h2>
<p>段好片，Proxy 把每个 vchannel 上的那些行<strong>重新打包</strong>成一条条<strong>插入消息（InsertMessage）</strong>（见 <span class="inline">repackInsertDataForStreamingService</span>），
每条消息带上它的 vchannel、集合 ID、分区信息与 schema 版本。<strong>注意一个关键变化</strong>：段 ID（segmentID）在这里<strong>留空（填 0）</strong>——
"这批行该进哪个段"不再由 Proxy 决定，而是<strong>推迟到 StreamingNode</strong>在写 WAL 时分配（第 17 课详述）。Proxy 只负责"分片 + 打包"，不再操心"分段"。</p>

<p>这里出现的 <span class="mono">streaming.WAL()</span> 拿到的是一个 <strong>StreamingClient</strong>（WAL 访问器）。它是一个<strong>进程内</strong>的客户端，封装了 Append / Read / Broadcast 三类能力，
还内置了<strong>服务发现与自动重连</strong>：Proxy 不需要知道"负责某条 pchannel 的 StreamingNode 此刻在哪台机器上"，StreamingClient 会替它找路、断了会重连。
于是 Proxy 这一侧的代码出奇地简单——一句 <span class="mono">AppendMessages</span>，背后的寻址、网络、重试全被这层客户端吞掉了。这正是好接口的样子：<strong>把复杂留给自己，把简单交给调用方</strong>。</p>

<p>最后一步，也是这条路的核心：Proxy 调用 <span class="inline">streaming.WAL().AppendMessages(ctx, msgs...)</span>，把这批消息<strong>追加写入 WAL</strong>。
这正是新写入路径的精髓——<strong>客户端 → Proxy → StreamingClient.Append → StreamingNode → WAL 后端</strong>，而不是旧的"Proxy 直接发消息队列、DataNode 来消费"那套模型。
写成功后，Proxy 把返回的 <span class="mono">MaxTimeTick</span> 作为本次写入的时间戳回填给客户端，用于会话级一致性（你刚写的，下一刻一定读得到）。</p>

<p>为什么"分段"这件事要从 Proxy 手里拿走、推迟到 StreamingNode？因为段是<strong>有状态</strong>的：一个 growing 段能装多少行、何时该封口，取决于这个分片<strong>当前</strong>的写入进度，
而这份进度只有<strong>独占</strong>该 pchannel 的 StreamingNode 才掌握得最准。Proxy 是无状态、可多开的（第 10 课），如果让每个 Proxy 各自决定段 ID，
多个 Proxy 并发写同一分片就会打架。把分段权<strong>收归到单一的 StreamingNode</strong>，既保证了段分配的一致性，也让 Proxy 保持轻量。这正是"<strong>无状态的归无状态、有状态的归有状态</strong>"这条分层原则在写入路上的又一次体现。</p>

<table class="t">
  <tr><th>Proxy 这一步</th><th>它在做什么</th><th>关键符号</th></tr>
  <tr><td><strong>校验主键</strong></td><td>校验/补全主键，autoID 时分配</td><td class="mono">checkPrimaryFieldData</td></tr>
  <tr><td><strong>取分片</strong></td><td>拿到集合的 vchannel 列表</td><td class="mono">chMgr.getVChannels</td></tr>
  <tr><td><strong>哈希分片</strong></td><td>按主键把行分到各 vchannel</td><td class="mono">assignChannelsByPK</td></tr>
  <tr><td><strong>打包消息</strong></td><td>每 vchannel 一组 InsertMessage，段 ID 留空</td><td class="mono">repackInsertData…</td></tr>
  <tr><td><strong>写 WAL</strong></td><td>整批原子追加，拿回 TimeTick</td><td class="mono">WAL().AppendMessages</td></tr>
</table>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/proxy/task_insert_streaming.go</span><span class="ln">insertTask.Execute：分片→打包→Append</span></div>
  <pre><span class="cm">// 1) 取集合的 vchannel 列表</span>
channelNames, err := it.chMgr.getVChannels(collID)
<span class="cm">// 2) 按主键哈希分片，再打包成插入消息（segmentID 此处留 0）</span>
msgs, err := repackInsertDataForStreamingService(
    it.TraceCtx(), channelNames, it.insertMsg, it.result, ez, it.schemaVersion)
<span class="cm">// 3) 整批追加写入 WAL</span>
resp := streaming.WAL().AppendMessages(ctx, msgs...)
<span class="cm">// 4) 用返回的最大 TimeTick 作为本次写入时间戳</span>
it.result.Timestamp = resp.MaxTimeTick()</pre>
</div>

<h2>把流水线连起来</h2>
<p>把 Proxy 在写入路上的动作串成一条线，你会看到一个清晰的"加工"链条：校验 → 定主键 → 哈希分片 → 打包 → 追加 WAL。每一步都在为下一步铺路，
最终把"一批杂乱的行"变成"分好片、贴好时间戳、躺在 WAL 里等着被消费的有序消息"。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>接收 insert</h4><p>包装成 <span class="mono">insertTask</span> 进 dmQueue（第 10 课）。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>校验 + 定主键</h4><p class="mono">checkPrimaryFieldData</p><p>autoID 时为每行分配全局唯一主键。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>哈希到 vchannel</h4><p class="mono">assignChannelsByPK</p><p>同一主键恒定落同一分片。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>打包成消息</h4><p>每个 vchannel 一组 InsertMessage，segmentID 留空。</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>Append 进 WAL</h4><p class="mono">WAL().AppendMessages</p><p>整批原子追加，拿回 TimeTick。</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>返回客户端</h4><p>写成功即返回，落盘在后台异步进行。</p></div></div>
</div>

<h2>时间戳：写入如何在全局定序</h2>
<p>贯穿这一课、却一直没正面讲的，是<strong>时间戳</strong>。还记得第 3 课、第 10 课反复强调的"每个写入都要一个时间戳"吗？在写入路上，它的作用比读取时更隐蔽却更关键。
每条 insert 消息进 WAL 时，都会被打上一个<strong>单调递增</strong>的时间戳（TimeTick）。它不是墙上时钟，而是 WAL 这条日志的<strong>逻辑序号</strong>：谁先进日志，谁的时间戳就小。
正是这把"逻辑尺子"，让分散在多个分片、来自多个客户端的写入，能被排进<strong>一条全局有序</strong>的时间线。</p>

<p>这件事的回报，要到读取时才完全兑现。回忆第 10 课讲的<strong>保证时间戳（guarantee timestamp）</strong>：一次 search 会带上"请至少消费到这个时间点"的要求，
而判断"消费到没到"，靠的正是写入时打的这些 TimeTick。换句话说，<strong>写入侧老老实实地给每条记录定序，读取侧才能精确地控制可见性</strong>——
强一致就读到最新时间戳，有界过期就容忍一点点旧。写与读，被同一把时间戳的尺子悄悄缝在了一起。这也是为什么 Proxy 要把 <span class="mono">AppendMessages</span> 返回的
<span class="mono">MaxTimeTick</span> 回填给客户端：它是这次写入在全局时间线上的"坐标"，客户端拿着它，下一次查询就能要求"读到至少这个坐标"，从而读到自己刚写的数据。</p>

<div class="trace">
  <div class="tcap">WAL 日志：按 TimeTick 单调递增排好序</div>
  <div class="stations">
    <div class="stn">t₁<div class="op">insert A</div></div>
    <div class="stn">t₂<div class="op">insert B</div></div>
    <div class="stn blue">t₃<div class="op">insert C</div></div>
    <div class="stn hot">t₄<div class="op">本次写入</div></div>
    <div class="stn dim">t₅<div class="op">…后续</div></div>
  </div>
  <div class="tlab">读取带 guarantee ts = t₄：消费到 t₄ 即可回答，保证读到 A/B/C 与本次写入</div>
</div>

<p>把这条时间线记在脑子里，你就握住了整条写入路的<strong>骨架</strong>：Proxy 校验、分片、打包，最终把消息<strong>按时间戳顺序</strong>追加进 WAL；
后端按这个顺序消费、分段、落盘；读取再按时间戳控制能看到哪些。一行数据的旅程，本质上就是它在这条全局时间线上<strong>找到自己位置</strong>的过程。</p>

<h2>原子批与"写成功"的含义</h2>
<p>最后厘清一个常被误解的点：insert 返回成功，<strong>到底意味着什么</strong>？它<strong>不</strong>意味着数据已经落进对象存储的段文件——那是后台异步做的（第 17 课）。
它意味着这批消息已经<strong>可靠地追加进了 WAL</strong>，而 WAL 是 Milvus 的<strong>单一事实来源</strong>。只要进了 WAL，就算 StreamingNode 立刻宕机，
重启后也能从 WAL 回放、不丢数据。所以"写成功"= "已持久化进日志"，而非"已落盘成段"。</p>

<p>这也是"<strong>原子批</strong>"的由来：同一批 insert 要么整批进 WAL、整批可见，要么整批失败。Proxy 用 <span class="mono">AppendMessages</span> 的返回值统一判定——
<span class="mono">UnwrapFirstError()</span> 只要有一条失败就整批报错。这种"全有或全无"的语义，让客户端永远看不到"一半行进了、一半没进"的中间状态。
把这一课记牢：<strong>Proxy 是写入的加工车间，WAL 是写入的终点线</strong>。下一课，我们就走进 WAL 本身。</p>

<p>不过这里要诚实地补一句边界：当一批行被分到<strong>多个 vchannel</strong> 时，<span class="mono">AppendMessages</span> 是按 vchannel 分别追加的，跨 vchannel 之间并不保证严格的原子性——
它的承诺是"属于同一 vchannel 的消息作为一个事务一起写"。真正需要跨多个物理通道<strong>原子生效</strong>的场景（比如某些 DDL/DCL），走的是另一条 <span class="mono">Broadcast</span> 路径（下一课会提到）。
对绝大多数 insert 而言，一批行常常落在同一个或少数几个 vchannel，配合主键哈希的确定性，已经足以给客户端"这批写入整体成功"的体感。理解这条边界，
你才不会把"insert 的原子批"误读成"任意跨分片的分布式事务"——Milvus 在这里做的是<strong>务实的取舍</strong>，而非昂贵的两阶段提交。</p>

<p>最后再把镜头拉回主线。这一课你看到的，是 Proxy 如何把一次 insert <strong>翻译成 WAL 能理解的语言</strong>：校验定主键、哈希定分片、打包定格式、追加定时序。
它做完这一切，数据就安全地躺进了日志，等待被消费、被分段、被落盘——而这正是接下来两课的主题。记住这条流水线的形状，后面每一步都会与它严丝合缝地对上。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话串起来：<strong>insert 进 Proxy → 校验并敲定主键（checkPrimaryFieldData，autoID 时分配）→ 按主键哈希到各 vchannel（assignChannelsByPK）→ 打包成 InsertMessage（segmentID 留给 StreamingNode）→ streaming.WAL().AppendMessages 整批追加进 WAL → 用 MaxTimeTick 回填时间戳返回</strong>。
  写成功 = 已进 WAL（单一事实来源），不等于已落盘成段。把这条流水线的形状刻在脑子里，后面"消费、分段、落盘、压实"每一步都会与它对上。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>主键先行</strong>：<span class="mono">checkPrimaryFieldData</span> 校验/补全主键；autoID 时为每行分配全局唯一 ID，主键是后续路由的依据。</li>
    <li><strong>哈希分片</strong>：<span class="mono">assignChannelsByPK</span> 按主键把行分到各 vchannel，同一主键恒定落同一分片。</li>
    <li><strong>段 ID 后移</strong>：Proxy 打包时 segmentID 留空，分段交给 StreamingNode（第 17 课）。</li>
    <li><strong>写入路径</strong>：<span class="mono">streaming.WAL().AppendMessages</span> 把整批追加进 WAL，即"客户端 → Proxy → StreamingClient.Append → StreamingNode → WAL 后端"。</li>
    <li><strong>原子批</strong>：整批要么全进 WAL、全可见，要么整批失败；写成功 = 已持久化进日志，而非已落盘成段。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The first three parts toured the whole cluster and every coordinator. From here we follow <strong>one row of data</strong> on its journey — from a client's
<span class="mono">insert</span> call all the way to a searchable segment in object storage. The first stop is our old friend the <strong>Proxy</strong>, but this time we don't
watch it gate or schedule; we focus on what "processing" it does on the <strong>write</strong> path. By the end you'll see the Proxy's write-path role is more like a <strong>workshop turning raw material into a semi-finished part</strong>: in comes a messy batch of rows, out go sharded, timestamped, ordered messages ready to drop straight into the WAL.
</p>

<div class="card analogy">
  <div class="tag">📮 Analogy</div>
  Picture an insert as mailing a batch of parcels nationwide. You hand boxes of parcels (a batch of rows) to the <strong>post-office counter</strong> (the Proxy): the clerk first
  <strong>checks the labels</strong> (schema validation: right fields, right types), <strong>assigns a tracking number</strong> to any parcel missing one (primary-key auto-fill), then
  <strong>sorts parcels into chutes by postcode</strong> (hashing rows by primary key to vchannels). Once sorted, the whole batch gets <strong>one common postmark timestamp</strong> and rides
  the conveyor together (appended to the WAL). The counter <strong>delivers nothing and warehouses nothing</strong>, yet the batch is all-or-nothing — that is the write's "atomic batch."
  This whole routine — check label, assign number, sort, postmark, onto the conveyor — is the Proxy's entire job on the write path; it is fast, light, and replicable, leaving the real "delivery and warehousing" to later roles.
</div>

<h2>Gate one: schema validation and the primary key</h2>
<p>Once an insert reaches the Proxy it is wrapped as an <span class="mono">insertTask</span> and first runs <strong>data-correctness</strong> checks in <span class="mono">PreExecute</span>. The core step is
<span class="inline">checkPrimaryFieldData</span>: it confirms the batch's <strong>primary-key column</strong> is valid and consistent with the schema. If the collection uses <strong>auto-ID</strong>,
the client never sends a primary key, so this step <strong>assigns a globally unique key to every row</strong> and fills it in; with a user-supplied key it checks non-null, uniqueness, and type. Only
after this does the batch's primary-key <span class="mono">IDs</span> become settled.</p>

<p>Why settle the primary key <strong>so early</strong>? Because the next step — "which row goes to which shard" — depends entirely on it. The key is not just an identity card, it is the
<strong>routing basis</strong>; without a settled key, no later step can proceed. Think of it as "stamp a unique tracking number on every parcel before you can sort by it." It is also the
Proxy's <strong>last semantic validation</strong> of client data: once a batch is admitted into the write pipeline, the backend trusts it is "well-formed with complete keys" and never re-validates,
saving precious compute for the actual persistence.</p>

<p>A design trade-off worth unpacking hides here: <strong>who generates the primary key</strong>. With auto-ID, Milvus assigns the key uniformly at the Proxy layer — it asks the coordinator for a range of
globally unique IDs and slices it across this batch. The upside: clients never worry about uniqueness; the downside: you cannot use a business-meaningful value (say, an order number) as the key. Conversely,
a user-supplied key hands generation to the application — flexible, but you must guarantee no duplicates. Either way, <strong>validation must finish before the write</strong>: once data enters the WAL, the key becomes
that record's "indelible identity," and all later updates, deletes, and dedup align by it. That is why Milvus would rather spend a little extra validation up front than let a batch with a "possibly-illegal key" into the log —
a textbook case of <strong>front-loading validation to keep the backend simple</strong>.</p>

<p>Note one easily-missed detail too: this step also aligns the <strong>client-supplied fields</strong> with the schema. The client may have omitted a field with a default, written columns out of order,
or carried a dynamic field not in the schema (Lesson 6). <span class="mono">checkPrimaryFieldData</span> and its surrounding checks normalize all of this: fill defaults, reorder by schema, fold legal dynamic fields into
<span class="mono">$meta</span>. Once this gate is passed, what flows into the write pipeline is a "<strong>clean, normalized, fully-keyed</strong>" batch, and the backend never has to fuss over format again.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/proxy/task_insert.go</span><span class="ln">settling the primary key in PreExecute</span></div>
  <pre><span class="cm">// validate/fill primary key, return the batch IDs; auto-ID allocates here</span>
it.result.IDs, err = checkPrimaryFieldData(ctx, allFields, it.schema, it.insertMsg)
<span class="kw">if</span> err != <span class="kw">nil</span> {
    mlog.Warn(ctx, <span class="st">"check primary field data error"</span>, mlog.Err(err))
    <span class="kw">return</span> err
}</pre>
</div>

<h2>Gate two: hash rows by primary key to vchannels</h2>
<p>After validation comes <span class="mono">Execute</span>. The Proxy first asks its cache for the collection's <strong>virtual-channel list</strong> (<span class="inline">chMgr.getVChannels(collID)</span>) —
recall Lesson 7: a collection is cut into several <strong>shards</strong>, each backed by a <strong>vchannel</strong>. The key action now is <span class="inline">assignChannelsByPK</span>:
it takes each row's primary key, hashes it, and routes the row index to a vchannel by hash value, producing a "<span class="mono">channel → row-offset list</span>" map.</p>

<p>This step decides the <strong>physical distribution</strong> of data. The same primary key always hashes to the same vchannel, so every version of a row (including later updates and deletes)
lands in the same shard — crucial for "delete by primary key" and "which segment does this row belong to" later (Lessons 17 and 20). Hash sharding also gives <strong>load balance</strong>:
huge batches spread evenly across vchannels with no hot shard. Grasp this and you understand Milvus's bedrock logic: <strong>scale out by sharding, shard by primary-key hash</strong>.</p>

<p>Distinguish two easily-confused concepts here: <strong>vchannel (virtual channel)</strong> versus <strong>pchannel (physical channel)</strong>. What the Proxy hashes to is a vchannel — a <strong>logical</strong> notion of "a shard of a collection,"
born when the collection is created and gone when it is dropped. What actually carries the WAL is a pchannel — a <strong>physical</strong> log partition, fixed in number, pre-opened by the cluster (one per message-queue topic).
Many vchannels from many collections <strong>multiplex</strong> the same pchannel. That mapping (vchannel → pchannel) is detailed next lesson; here just remember: the Proxy cares about the logical shard, the vchannel,
and the vchannel name itself encodes which pchannel it belongs to, so the write finds the right WAL.</p>

<p>One subtlety more: if the collection sets a <strong>partition key (Lesson 6)</strong>, the sharding logic takes another branch,
<span class="inline">repackInsertDataWithPartitionKeyForStreamingService</span> — beyond hash sharding it also routes rows into the correct logical partition by partition key.
But the skeleton is unchanged: <strong>still "compute membership by some key, then group and pack."</strong> With or without a partition key, the Proxy's mission at this layer is the same: deterministically cut an unordered
batch of rows into "one group per vchannel." Determinism matters — the same input always yields the same sharding, so retries and replays never scramble the data.</p>

<div class="flow">
  <div class="node"><div class="nt">a batch of rows</div><div class="nd">with primary-key IDs</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">assignChannelsByPK</div><div class="nd">hash each PK</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">vchannel A</div><div class="nd">rows 0,3,7…</div></div>
  <div class="arrow">＋</div>
  <div class="node"><div class="nt">vchannel B</div><div class="nd">rows 1,2,5…</div></div>
</div>

<h2>Gate three: pack into messages, Append to the WAL</h2>
<p>With rows sharded, the Proxy <strong>repacks</strong> the rows on each vchannel into individual <strong>insert messages</strong> (see <span class="inline">repackInsertDataForStreamingService</span>),
each carrying its vchannel, collection ID, partition info, and schema version. <strong>Note one key change</strong>: the segment ID is <strong>left empty (set to 0)</strong> here —
"which segment these rows go to" is no longer decided by the Proxy but <strong>deferred to the StreamingNode</strong> when it writes the WAL (detailed in Lesson 17). The Proxy only "shards + packs," never "segments."</p>

<p>The <span class="mono">streaming.WAL()</span> here returns a <strong>StreamingClient</strong> (WAL accessor). It is an <strong>in-process</strong> client wrapping three capabilities — Append / Read / Broadcast —
with built-in <strong>service discovery and auto-reconnect</strong>: the Proxy need not know "which machine the StreamingNode responsible for a given pchannel is on right now"; the StreamingClient finds the route and reconnects on drops.
So the Proxy-side code is strikingly simple — one <span class="mono">AppendMessages</span>, with all the addressing, networking, and retries swallowed by this client layer. That is what a good interface looks like: <strong>keep complexity to yourself, hand simplicity to the caller</strong>.</p>

<p>The final, central step: the Proxy calls <span class="inline">streaming.WAL().AppendMessages(ctx, msgs...)</span> to <strong>append</strong> the batch to the WAL.
This is the essence of the new write path — <strong>Client → Proxy → StreamingClient.Append → StreamingNode → WAL backend</strong> — not the old "Proxy publishes to a message queue, DataNode consumes" model.
<p>On success the Proxy fills the returned <span class="mono">MaxTimeTick</span> back as this write's timestamp, used for session consistency (what you just wrote is readable next moment).</p>

<p>Why take "segmenting" out of the Proxy's hands and defer it to the StreamingNode? Because a segment is <strong>stateful</strong>: how many rows a growing segment can hold and when to seal it depend on this shard's
<strong>current</strong> write progress, and only the StreamingNode that <strong>exclusively owns</strong> that pchannel knows it most accurately. The Proxy is stateless and replicable (Lesson 10); if each Proxy decided segment IDs
on its own, several Proxies writing the same shard concurrently would clash. <strong>Centralizing segmenting in the single StreamingNode</strong> guarantees consistent assignment and keeps the Proxy lightweight. This is the
"<strong>stateless to the stateless, stateful to the stateful</strong>" layering principle showing up once more on the write path.</p>

<table class="t">
  <tr><th>Proxy step</th><th>what it does</th><th>key symbol</th></tr>
  <tr><td><strong>validate PK</strong></td><td>validate/fill the key, allocate on auto-ID</td><td class="mono">checkPrimaryFieldData</td></tr>
  <tr><td><strong>get shards</strong></td><td>fetch the collection's vchannel list</td><td class="mono">chMgr.getVChannels</td></tr>
  <tr><td><strong>hash-shard</strong></td><td>route rows to vchannels by PK</td><td class="mono">assignChannelsByPK</td></tr>
  <tr><td><strong>pack</strong></td><td>one group of InsertMessages per vchannel, segmentID empty</td><td class="mono">repackInsertData…</td></tr>
  <tr><td><strong>append WAL</strong></td><td>atomic batch append, get back a TimeTick</td><td class="mono">WAL().AppendMessages</td></tr>
</table>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/proxy/task_insert_streaming.go</span><span class="ln">insertTask.Execute: shard → pack → Append</span></div>
  <pre><span class="cm">// 1) get the collection's vchannel list</span>
channelNames, err := it.chMgr.getVChannels(collID)
<span class="cm">// 2) hash-shard by PK, repack into insert messages (segmentID left 0)</span>
msgs, err := repackInsertDataForStreamingService(
    it.TraceCtx(), channelNames, it.insertMsg, it.result, ez, it.schemaVersion)
<span class="cm">// 3) append the whole batch to the WAL</span>
resp := streaming.WAL().AppendMessages(ctx, msgs...)
<span class="cm">// 4) use the returned max TimeTick as this write's timestamp</span>
it.result.Timestamp = resp.MaxTimeTick()</pre>
</div>

<h2>Wiring the pipeline together</h2>
<p>String the Proxy's write-path actions into one line and a clean "processing" chain appears: validate → settle PK → hash-shard → pack → append to WAL. Each step paves the way for the next,
turning "a messy batch of rows" into "sharded, timestamped, ordered messages sitting in the WAL waiting to be consumed."</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>receive insert</h4><p>wrapped as <span class="mono">insertTask</span> into dmQueue (Lesson 10).</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>validate + settle PK</h4><p class="mono">checkPrimaryFieldData</p><p>auto-ID assigns a globally unique key per row.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>hash to vchannel</h4><p class="mono">assignChannelsByPK</p><p>same PK always lands on the same shard.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>pack into messages</h4><p>one group of InsertMessages per vchannel; segmentID left empty.</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>Append to WAL</h4><p class="mono">WAL().AppendMessages</p><p>whole batch appended atomically; get back a TimeTick.</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>return to client</h4><p>success returns at once; persistence happens asynchronously in the background.</p></div></div>
</div>

<h2>Timestamps: how a write is ordered globally</h2>
<p>Running through this whole lesson, yet never addressed head-on, is the <strong>timestamp</strong>. Remember Lessons 3 and 10 stressing "every write needs a timestamp"? On the write path its role is subtler
but more crucial than on reads. As each insert message enters the WAL it is stamped with a <strong>monotonically increasing</strong> timestamp (TimeTick). It is not a wall clock but the WAL's <strong>logical sequence number</strong>:
whoever enters the log first gets the smaller timestamp. This "logical ruler" is exactly what lets writes scattered across shards and arriving from many clients be ordered into <strong>one globally ordered</strong> timeline.</p>

<p>The payoff only fully materializes on reads. Recall the <strong>guarantee timestamp</strong> from Lesson 10: a search carries "please consume at least up to this point," and judging "have we reached it?" relies precisely on these
write-time TimeTicks. In other words, <strong>the write side faithfully orders every record so the read side can precisely control visibility</strong> — strong consistency reads the latest timestamp, bounded staleness tolerates a slightly older one.
Write and read are quietly stitched together by the same timestamp ruler. That is why the Proxy fills the <span class="mono">MaxTimeTick</span> from <span class="mono">AppendMessages</span> back to the client: it is this write's "coordinate" on the global timeline;
holding it, the client's next query can demand "read at least up to this coordinate" and thus read its own just-written data.</p>

<div class="trace">
  <div class="tcap">WAL log: ordered by monotonically increasing TimeTick</div>
  <div class="stations">
    <div class="stn">t₁<div class="op">insert A</div></div>
    <div class="stn">t₂<div class="op">insert B</div></div>
    <div class="stn blue">t₃<div class="op">insert C</div></div>
    <div class="stn hot">t₄<div class="op">this write</div></div>
    <div class="stn dim">t₅<div class="op">…later</div></div>
  </div>
  <div class="tlab">read with guarantee ts = t₄: consuming up to t₄ suffices to answer, guaranteeing A/B/C and this write are seen</div>
</div>

<p>Keep this timeline in mind and you hold the <strong>skeleton</strong> of the whole write path: the Proxy validates, shards, packs, and finally appends messages <strong>in timestamp order</strong> to the WAL;
the backend consumes, segments, and persists in that order; reads then use timestamps to control what is visible. A row's journey is essentially the process of it <strong>finding its place</strong> on this global timeline.</p>

<h2>Atomic batches and what "write succeeded" means</h2>
<p>One last commonly-misread point: what does an insert returning success <strong>actually mean</strong>? It does <strong>not</strong> mean the data has landed in segment files in object storage — that is done
asynchronously in the background (Lesson 17). It means the batch of messages was <strong>reliably appended to the WAL</strong>, and the WAL is Milvus's <strong>single source of truth</strong>. Once in the WAL,
even if the StreamingNode crashes immediately, it can replay from the WAL on restart and lose nothing. So "write succeeded" = "durably logged," not "flushed to a segment."</p>

<p>That is also the origin of the <strong>atomic batch</strong>: a batch of inserts either all enter the WAL and become visible together, or the whole batch fails. The Proxy decides this uniformly from
<span class="mono">AppendMessages</span>'s return — <span class="mono">UnwrapFirstError()</span> fails the whole batch if any one message failed. This all-or-nothing semantics means the client never sees a
half-applied state. Remember this lesson: <strong>the Proxy is the write's processing workshop; the WAL is the write's finish line</strong>. Next lesson we step into the WAL itself.</p>

<p>Honesty about a boundary, though: when a batch is split across <strong>multiple vchannels</strong>, <span class="mono">AppendMessages</span> appends per vchannel, and strict atomicity is not guaranteed across vchannels —
its promise is "messages belonging to the same vchannel are written together as one transaction." Scenarios that truly need <strong>atomic effect across multiple physical channels</strong> (certain DDL/DCL) take another path,
<span class="mono">Broadcast</span> (mentioned next lesson). For the vast majority of inserts a batch often lands on one or a few vchannels, and combined with the determinism of PK hashing that is already enough to give the client the
sense that "this write succeeded as a whole." Understand this boundary and you won't misread "an insert's atomic batch" as "an arbitrary cross-shard distributed transaction" — what Milvus does here is a <strong>pragmatic trade-off</strong>,
not an expensive two-phase commit.</p>

<p>Finally, pull the camera back to the throughline. What you saw this lesson is how the Proxy <strong>translates an insert into a language the WAL understands</strong>: validate-and-settle the key, hash-and-settle the shard,
pack-and-settle the format, append-and-settle the order. Having done all this, the data rests safely in the log, waiting to be consumed, segmented, and persisted — which is exactly the subject of the next two lessons.
Remember the shape of this pipeline; every later step will line up against it precisely.</p>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>insert enters the Proxy → validate and settle the primary key (checkPrimaryFieldData, auto-ID allocates) → hash by PK to vchannels (assignChannelsByPK) → pack into InsertMessages (segmentID left for the StreamingNode) → streaming.WAL().AppendMessages appends the whole batch to the WAL → fill MaxTimeTick back as the timestamp and return</strong>.
  Write success = in the WAL (single source of truth), which is not the same as flushed to a segment. Carve the shape of this pipeline into memory; every later step — consume, segment, persist, compact — will line up against it.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Primary key first</strong>: <span class="mono">checkPrimaryFieldData</span> validates/fills the key; auto-ID assigns a globally unique ID per row, and the key is the basis for later routing.</li>
    <li><strong>Hash sharding</strong>: <span class="mono">assignChannelsByPK</span> routes rows to vchannels by PK; the same key always lands on the same shard.</li>
    <li><strong>Segment ID deferred</strong>: the Proxy leaves segmentID empty when packing; segmenting is the StreamingNode's job (Lesson 17).</li>
    <li><strong>Write path</strong>: <span class="mono">streaming.WAL().AppendMessages</span> appends the batch to the WAL — i.e. "Client → Proxy → StreamingClient.Append → StreamingNode → WAL backend."</li>
    <li><strong>Atomic batch</strong>: the whole batch enters the WAL and becomes visible, or fails together; write success = durably logged, not flushed to a segment.</li>
  </ul>
</div>
""",
}

LESSON_16 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课，Proxy 把一批 insert 校验、分片、打包，最后<strong>追加进了 WAL</strong>。这一课我们就走进 WAL 本身——Milvus 写入链路的<strong>主心骨</strong>。
这是一次"轻量导览"：把 WAL 的几个核心概念（单一事实来源、消息与 TimeTick、三种通道、StreamingClient、StreamingNode/StreamingCoord）讲透，建立直觉；
真正逐行拆解 WAL 内部实现，我们留到第七部分深挖。读完这一课，你会明白为什么说"<strong>在 Milvus 里，日志不是辅助，而是数据本身</strong>"。
</p>

<div class="card analogy">
  <div class="tag">📒 生活类比</div>
  把 WAL 想成一家银行的<strong>流水账本</strong>：每一笔存取都<strong>先记进账本</strong>（append），再谈余额怎么变。账本只能<strong>往后追加、不能涂改</strong>，每条记录有一个严格递增的<strong>流水号</strong>（TimeTick）。
  哪怕账本系统某一刻崩了，重启后只要把账本<strong>从头念一遍</strong>，余额、报表、对账单全都能重新算出来——因为<strong>账本才是真相，其余都是它的派生</strong>。
  Milvus 的 WAL 正是这本账：所有写入先进 WAL，段、索引、删除标记都是从这本账"念出来"的结果。这一课，我们就来认识这本"账本"的几条核心规矩。
</div>

<h2>WAL 是单一事实来源</h2>
<p>先把这句话钉死：<strong>WAL（Write-Ahead Log，预写日志）是 Milvus 所有变更的单一事实来源（single source of truth）</strong>。任何 insert、delete、DDL，
都要<strong>先写进 WAL</strong> 才算数。段文件、索引、内存里的数据结构……它们统统是 WAL 的<strong>派生物</strong>——是把日志"重放（replay）"出来的不同形态。
这就是第 7 课"日志即数据"在系统层面的兑现：日志不是为了崩溃恢复而存在的<strong>附属品</strong>，它<strong>本身就是数据的权威副本</strong>。</p>

<p>为了体会这个定位有多反直觉，不妨对照一下传统数据库。传统库里，<strong>表才是主体</strong>，预写日志（WAL）只是为了"万一崩了能恢复"的<strong>保险</strong>——平时谁也不直接读它。
Milvus 把这个关系<strong>彻底倒过来</strong>了：日志升格为主角，表（段）反而成了日志的一种<strong>物化视图</strong>。为什么敢这么设计？因为向量数据库的负载有个鲜明特点：
写入是<strong>持续灌入的流</strong>，读取是<strong>对快照的检索</strong>，两者节奏天差地别。把写入收敛成一条<strong>纯追加的日志</strong>，就能让写入路径短到极致（只管 append），
再让各种"读取形态"在后台<strong>异步地、各取所需地</strong>从日志里长出来。这是一种"<strong>先记账、后算账</strong>"的架构哲学，写得越简单，整个系统越容易做正确、做快。</p>

<p>这个定位带来一个极其干净的心智模型：<strong>只要 WAL 在，数据就在</strong>。某台节点崩了、某个段文件坏了、某份索引丢了，都不致命——
从 WAL 重放即可重建。反过来，只有当数据<strong>成功进了 WAL</strong>，才算"写入成功"（正是上一课的结论）。于是整个系统的可靠性边界，被收敛到一个清晰的点上：<strong>守住 WAL</strong>。
也正因如此，WAL 后端用的都是 Kafka / Pulsar / Woodpecker / RMQ 这类<strong>自身高可靠、可持久化</strong>的消息系统——把"不丢日志"这件最关键的事，交给最擅长它的组件。</p>

<p>顺带说一句这些后端的取舍：Kafka、Pulsar 是业界成熟的分布式消息系统，适合大规模生产集群；RMQ（RocksMQ）是 Milvus 内嵌的轻量实现，单机/Standalone 形态下零外部依赖即可跑（回忆第 8 课）；
Woodpecker 则是 Milvus 自研、面向对象存储的 WAL 方案。无论选哪个，它们对上都<strong>统一成"一条 PChannel = 一个 topic"的抽象</strong>——这正是上一节 StreamingClient 那层封装的意义：
让"日志存在哪种系统里"成为一个<strong>可替换的部署选择</strong>，而不是写死在代码里的假设。你在小机器上用 RMQ 学习、在生产集群上换 Pulsar 扩容，<strong>写入路径的代码完全不变</strong>。</p>

<h2>消息与 TimeTick：日志的两块积木</h2>
<p>WAL 里流动的基本单位是<strong>消息（Message）</strong>：一条 InsertMessage、一条 DeleteMessage、一条 DDL 消息……每条都带有<strong>头（header）</strong>（类型、vchannel、集合 ID 等）和<strong>体（body）</strong>（真正的数据）。
Proxy 上一课打包出来的，正是这些消息。消息是<strong>自描述</strong>的：消费端只看消息本身，就能知道"这是什么操作、作用在哪个分片、该怎么应用"。</p>

<p>而把这些消息<strong>串成有序一条线</strong>的，是 <strong>TimeTick</strong>。TimeTick 是<strong>每条 pchannel 上单调递增的日志序号</strong>——可以把它理解成这条日志的"时钟"。
它不是墙上的物理时间，而是一把<strong>逻辑尺子</strong>：谁先 append，谁的 TimeTick 就小。正是这把尺子，让分散写入的消息有了<strong>确定的先后</strong>，
也让读取端能精确判断"我消费到哪个时间点了"。上一课 Proxy 回填给客户端的 <span class="mono">MaxTimeTick</span>，正是这把尺子上的一个刻度。<strong>消息是内容，TimeTick 是顺序</strong>——两块积木一搭，就拼出了"有序的、可重放的"日志。</p>

<p>这里要澄清一个常见困惑：TimeTick 既然单调递增，那系统岂不是要为每条消息都<strong>精确编号</strong>、严格无缝？其实没那么死板。TimeTick 更像是日志上<strong>不断推进的"水位线"</strong>：
StreamingNode 会周期性地往 WAL 里插入特殊的 <strong>TimeTick 消息</strong>，宣告"截至此刻，这条通道上小于该时间戳的写入都已就绪"。消费端看到这个水位线，就知道"我可以安全地把到此为止的数据对外可见了"。
这套机制解决了一个棘手问题：写入是断断续续的，消费端怎么判断"是真的没有新数据，还是数据在路上还没到"？答案就是水位线——<strong>TimeTick 把"时间在流逝"这件事本身也写进了日志</strong>，
于是即便某条通道暂时没有业务写入，它的"时钟"也在持续向前推进，消费端的可见性才不会被一条安静的通道卡住。理解了这一点，你就理解了 Milvus 一致性读的底层心跳。</p>

<div class="cellgroup">
  <div class="cg-cap">一条 pchannel 上的 WAL：消息按 TimeTick 严格递增排列</div>
  <div class="cells">
    <div class="cell"><span class="lab">t₁</span><span class="q">insert</span></div>
    <div class="cell"><span class="lab">t₂</span><span class="q">insert</span></div>
    <div class="cell hl"><span class="lab">t₃</span><span class="q">delete</span></div>
    <div class="cell"><span class="lab">t₄</span><span class="q">insert</span></div>
    <div class="cell dim"><span class="lab">t₅</span><span class="q">ddl</span></div>
    <div class="cell dim"><span class="lab">t₆</span><span class="q">…</span></div>
  </div>
</div>

<h2>三种通道：PChannel、VChannel、CChannel</h2>
<p>"通道（channel）"是 WAL 的分区概念，分三种，各司其职，很容易搞混，这里一次性讲清：</p>

<ul>
  <li><strong>PChannel（物理通道）</strong>：真正承载 WAL 的<strong>物理日志分区</strong>，一条 PChannel 对应 WAL 后端的<strong>一个 topic</strong>。数量固定、集群预先开好，是日志的"物理跑道"。TimeTick 就定义在每条 PChannel 上。</li>
  <li><strong>VChannel（虚拟通道）</strong>：<strong>逻辑</strong>概念，对应"某个集合的某个分片"。随集合创建/删除而生灭。多个 VChannel <strong>复用</strong>同一条 PChannel——上一课 Proxy 哈希出来的就是 VChannel。</li>
  <li><strong>CChannel（控制通道）</strong>：一条<strong>集群级别、单例</strong>的控制通道，用于需要<strong>跨 PChannel 全局排序</strong>的控制信息。它保证某些控制操作在整个集群有一致的先后。</li>
</ul>

<p>记住它们的关系最简单的方式：<strong>VChannel 是逻辑分片（多），PChannel 是物理日志（少），多个逻辑分片复用一条物理日志；CChannel 是头顶上那条唯一的"控制广播线"</strong>。
为什么不让每个 VChannel 都独占一条物理 topic？因为集合可能成千上万、分片更多，topic 是稀缺资源，一对一会爆炸。复用 PChannel，就是用<strong>固定的物理资源</strong>承载<strong>弹性的逻辑分片</strong>——
这正是分布式系统里"逻辑与物理解耦"的经典手法。</p>

<p>这里还藏着一个<strong>顺序粒度</strong>的微妙点，值得点破。TimeTick 的单调递增是定义在 <strong>PChannel</strong> 这条物理日志上的，也就是说：<strong>同一条 PChannel 上的所有消息有全局序，但跨 PChannel 之间没有天然的全序</strong>。
这正好够用——因为同一个 VChannel（同一分片）的消息一定落在同一条 PChannel 上，所以"<strong>分片内有序</strong>"是天然保证的，而分片之间本就互相独立、无需比较先后。
那么"需要跨 PChannel 全局一致"的少数操作（典型是 DDL，比如建/删集合要让所有分片同时知晓）怎么办？这就是 <strong>CChannel</strong> 与 Broadcast 存在的理由：它们专门负责把"必须全局一致"的那一小撮控制信息，
用一条单例通道串成全序。<strong>把"分片内强序"和"跨片全序"分开承载</strong>，是 Milvus 既要高吞吐、又要正确性的关键取舍——绝大多数数据走廉价的分片内序，极少数控制走昂贵的全局序。</p>

<table class="t">
  <tr><th>通道</th><th>层次</th><th>范围</th><th>用途</th></tr>
  <tr><td class="mono">PChannel</td><td>物理</td><td>一个 MQ topic</td><td>真正承载 WAL，TimeTick 定义于此</td></tr>
  <tr><td class="mono">VChannel</td><td>逻辑</td><td>集合的一个分片</td><td>写入路由单位，复用 PChannel</td></tr>
  <tr><td class="mono">CChannel</td><td>控制</td><td>整个集群（单例）</td><td>跨 PChannel 的全局控制排序</td></tr>
</table>

<h2>StreamingClient：Append / Broadcast / Read</h2>
<p>上一课那句 <span class="mono">streaming.WAL()</span>，拿到的就是 <strong>StreamingClient</strong>（代码里是 <span class="inline">WALAccesser</span> 接口）。它是一个<strong>进程内</strong>的 WAL 访问层，
把面对 WAL 后端的复杂度——寻址、连接、重试——全部封装起来，对上只暴露三类干净的能力：</p>

<ul>
  <li><strong>Append（追加写）</strong>：把消息写进 WAL。普通写入走 <span class="mono">RawAppend / AppendMessages</span>，按 VChannel 把消息（事务地）追加进对应 PChannel。这是写入路的主干。</li>
  <li><strong>Broadcast（广播写）</strong>：跨多个 VChannel <strong>原子地</strong>写一条消息，用于 DDL/DCL 这类"必须在多个分片同时生效"的场景。它配合 CChannel 实现全局一致的先后。</li>
  <li><strong>Read（读 / 扫描）</strong>：从 WAL 按位置读取消息，供消费端（StreamingNode 的 flusher、QueryNode 的 delegator 等）重放日志、追上最新状态。</li>
</ul>

<p>这层封装为什么重要？因为它把"<strong>WAL 后端是 Kafka 还是 Pulsar 还是别的</strong>"这件事，对上层彻底<strong>藏了起来</strong>。Proxy、StreamingNode 里的消费者，都只跟 <span class="mono">WALAccesser</span> 这套接口打交道，
完全不需要知道底下连的是哪种消息系统、它的客户端 API 长什么样、断线怎么重连。换后端时，只要换掉这层下面的实现，上层<strong>一行都不用改</strong>——这正是第 8、14 课反复出现的"用接口隔离可替换的后端"。
还有一点容易被忽略：StreamingClient 是<strong>进程内</strong>的（in-process），意味着调用 <span class="mono">Append</span> 不是一次裸的网络 RPC，而是先经过这层本地客户端，由它来做批量、寻址、重试。
这让写入侧的代码既简单又健壮：业务只表达"我要写这批消息"，至于"写到哪台机器、失败了重试几次"，都被这层悄悄兜住了。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/distributed/streaming/streaming.go</span><span class="ln">WALAccesser 接口（节选）</span></div>
  <pre><span class="kw">type</span> WALAccesser <span class="kw">interface</span> {
    <span class="cm">// 追加写：把单条/多条消息写进 WAL</span>
    RawAppend(ctx context.Context, msg message.MutableMessage, opts ...AppendOption) (*types.AppendResult, <span class="kw">error</span>)
    AppendMessages(ctx context.Context, msgs ...message.MutableMessage) AppendResponses

    <span class="cm">// 广播写：跨 vchannel 原子写，配合控制通道</span>
    Broadcast() Broadcast
    <span class="cm">// 控制通道名</span>
    ControlChannel() <span class="kw">string</span>

    <span class="cm">// 读：按位置扫描 WAL，供消费端重放</span>
    Read(ctx context.Context, opts ReadOption) Scanner
}</pre>
</div>

<h2>StreamingNode 与 StreamingCoord</h2>
<p>WAL 这套体系，由两个角色撑起来。一个是 <strong>StreamingNode（流式节点）</strong>：每个 StreamingNode <strong>独占管理一批 PChannel</strong>，负责这些 PChannel 上的写入与消费。
它身上挂着好几项关键职责：<strong>TimeTick 与事务</strong>（给消息定序、保证同一 VChannel 的批次事务性）、<strong>锁</strong>、<strong>分片管理（段分配）</strong>——
还记得上一课"段 ID 留空"吗？正是 StreamingNode 在写 WAL 时为消息分配段 ID——以及 <strong>RecoveryStorage（恢复存储）</strong>：维护检查点、元数据、并在崩溃后从 WAL 重放恢复。</p>

<p>另一个角色是 <strong>StreamingCoord（流式协调者）</strong>，它是<strong>单例</strong>，而且——这是个容易被忽略的关键点——<strong>跑在 RootCoord 进程里面</strong>。
它管两件事：<strong>通道管理</strong>（决定每条 PChannel 分配给哪个 StreamingNode，并在节点增减时再平衡）和 <strong>Broadcaster（广播器）</strong>（实现跨 PChannel 的原子 DDL/DCL）。
你可以把 StreamingCoord 理解成"WAL 这套子系统的大脑"：它不亲自搬运日志，但决定<strong>谁负责哪条物理通道</strong>、以及<strong>那些必须全局原子的控制操作怎么协调</strong>。</p>

<p>为什么 StreamingCoord 要<strong>塞进 RootCoord 进程里</strong>，而不是单独起一个组件？因为它的活儿天然和 RootCoord 紧挨着：RootCoord 本就掌管 DDL 与全局元数据（第 11 课），
而通道分配、跨通道广播，恰恰都是"集群级的元数据决策"。把它们<strong>合署办公</strong>，就省掉了一次跨进程跳转、也少了一个要部署、要做故障转移的组件。
这和第 9 课 MixCoord"把单例协调职责合并"是同一种直觉——不是每个概念上的"协调者"都得独占一个进程。要记住的分工很干净：<strong>StreamingCoord 做决策（分配、协调），StreamingNode 做执行（承载日志、分配段、恢复）</strong>，
这又是一次"控制面决策、数据面干活"的体现。</p>

<div class="layers">
  <div class="layer l-app"><span class="badge">写入侧</span><span class="name">Proxy</span><span class="ld">校验/分片/打包，调 StreamingClient.Append</span></div>
  <div class="layer l-main"><span class="badge">客户端</span><span class="name">StreamingClient（WALAccesser）</span><span class="ld">进程内 Append/Broadcast/Read + 服务发现/重连</span></div>
  <div class="layer l-core"><span class="badge">节点</span><span class="name">StreamingNode</span><span class="ld">独占一批 PChannel：TimeTick/事务、段分配、RecoveryStorage</span></div>
  <div class="layer l-part"><span class="badge">后端</span><span class="name">WAL 后端（Kafka/Pulsar/Woodpecker/RMQ）</span><span class="ld">一条 PChannel = 一个 topic，持久化日志</span></div>
</div>

<h2>日志即数据：其他形态靠回放追上</h2>
<p>把上面拼起来，就得到 Milvus 写入架构最核心的一句话：<strong>WAL 是真相，其他一切都是它的"投影"</strong>。段是把 WAL 里的 insert 消息攒起来、落盘成的列式文件；
索引是在段上再建的加速结构；QueryNode 内存里的可检索数据，是它<strong>消费 WAL、回放消息</strong>得到的。它们形态各异，但都在做同一件事：<strong>沿着 WAL 往前追，把日志"翻译"成自己需要的样子</strong>。</p>

<p>这个"<strong>log as data（日志即数据）</strong>"的设计，回报是巨大的<strong>解耦与弹性</strong>。新增一个 QueryNode？让它从 WAL 的某个位置开始消费，慢慢追上即可，不必停机搬数据。
某个消费者落后了？它自己沿 WAL 加速重放追上来，不影响别人。写入侧只管把消息<strong>可靠地按序追加</strong>，读取侧、落盘侧、索引侧各自<strong>独立地消费</strong>——
它们之间不直接耦合，只通过 WAL 这条<strong>有序日志</strong>间接协作。这就是为什么 Milvus 能把"写得快"和"读得稳"分开优化：因为它们被一条日志干净地隔开了。
下一课，我们就跟着其中一个消费者——把 WAL 里的 insert 攒成段、再 flush 成 binlog——看看"日志变成数据"的第一步具体怎么走。</p>

<p>临别再送你一句可以反复回味的话：<strong>在 Milvus 里，"写入"和"落盘"是两件被刻意分开的事</strong>。写入只对 WAL 负责，快而轻；落盘是后台消费者沿着 WAL 慢慢做的，稳而省。
正是这条 WAL，把"必须立刻完成的"和"可以从容完成的"干净地切开——理解了它，你就握住了整个写入链路的总纲。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话串起来：<strong>WAL 是单一事实来源；它由消息（内容）+ TimeTick（每条 PChannel 单调递增的顺序）构成；通道分 PChannel（物理 topic）/VChannel（逻辑分片，复用 PChannel）/CChannel（集群级控制）；StreamingClient 提供 Append/Broadcast/Read；StreamingNode 独占管理 PChannel（TimeTick、段分配、RecoveryStorage），StreamingCoord 单例跑在 RootCoord 里做通道分配与广播</strong>。
  段、索引、内存数据都是回放 WAL 得到的派生形态——日志即数据。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>单一事实来源</strong>：所有变更先进 WAL 才算数；段/索引/内存数据都是 WAL 的派生，崩溃后从 WAL 重放重建。</li>
    <li><strong>消息 + TimeTick</strong>：消息是自描述的内容；<span class="mono">TimeTick</span> 是每条 PChannel 上单调递增的逻辑序号，给消息定序。</li>
    <li><strong>三种通道</strong>：<span class="mono">PChannel</span>（物理 topic）← <span class="mono">VChannel</span>（逻辑分片，复用 PChannel）＋ <span class="mono">CChannel</span>（集群级控制排序）。</li>
    <li><strong>StreamingClient</strong>：<span class="mono">WALAccesser</span> 接口，进程内 <span class="mono">Append / Broadcast / Read</span>，封装寻址与重连。</li>
    <li><strong>两个角色</strong>：<span class="mono">StreamingNode</span> 独占管理 PChannel（TimeTick/事务、段分配、RecoveryStorage）；<span class="mono">StreamingCoord</span> 单例、跑在 RootCoord 里，做通道分配与跨通道广播。</li>
    <li><strong>日志即数据</strong>：消费者沿 WAL 回放追上最新状态，写读落盘各自解耦——这是 Milvus 弹性的根。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson the Proxy validated, sharded, and packed a batch of inserts, finally <strong>appending them to the WAL</strong>. This lesson we step into the WAL itself — the <strong>backbone</strong> of Milvus's write path.
This is a "light tour": we make the WAL's core concepts (single source of truth, message and TimeTick, the three channels, StreamingClient, StreamingNode/StreamingCoord) intuitive;
a line-by-line dissection of the WAL internals waits for Part 7. By the end you'll understand why "<strong>in Milvus, the log is not an aid but the data itself</strong>."
</p>

<div class="card analogy">
  <div class="tag">📒 Analogy</div>
  Think of the WAL as a bank's <strong>running ledger</strong>: every deposit or withdrawal is <strong>recorded in the ledger first</strong> (append), before any balance changes. The ledger is <strong>append-only, never edited</strong>, and each entry has a strictly increasing <strong>sequence number</strong> (TimeTick).
  Even if the ledger system crashes for a moment, on restart you just <strong>read the ledger from the top</strong> to recompute balances, reports, and statements — because <strong>the ledger is the truth and everything else is derived from it</strong>.
  Milvus's WAL is exactly that ledger: all writes go to the WAL first, and segments, indexes, and delete markers are all "read out" of it. This lesson, let's get to know a few core rules of this "ledger."
</div>

<h2>The WAL is the single source of truth</h2>
<p>Nail this down first: <strong>the WAL (Write-Ahead Log) is the single source of truth for all mutations in Milvus</strong>. Any insert, delete, or DDL must be <strong>written to the WAL first</strong> to count.
Segment files, indexes, in-memory data structures — they are all <strong>derivatives</strong> of the WAL, different shapes obtained by <strong>replaying</strong> the log.
This is Lesson 7's "log as data" realized at the system level: the log is not a crash-recovery <strong>side-product</strong>; it <strong>is the authoritative copy of the data</strong>.</p>

<p>To feel how counter-intuitive this positioning is, contrast it with a traditional database. There, <strong>the table is the protagonist</strong> and the write-ahead log is merely <strong>insurance</strong> for "recover if we ever crash" — nobody reads it directly in normal operation.
Milvus <strong>flips this entirely</strong>: the log is promoted to lead actor, and the table (segment) becomes a <strong>materialized view</strong> of the log. Why dare to design this way? Because a vector DB's workload has a distinctive shape:
writes are a <strong>continuous incoming stream</strong>, reads are <strong>retrieval over a snapshot</strong>, and the two cadences differ wildly. Collapsing writes into a single <strong>append-only log</strong> makes the write path as short as possible (just append),
then lets the various "read shapes" grow out of the log in the background, <strong>asynchronously and each taking what it needs</strong>. It is a "<strong>record first, reconcile later</strong>" architectural philosophy — the simpler the write, the easier the whole system is to make correct and fast.</p>

<p>This positioning yields an extremely clean mental model: <strong>as long as the WAL exists, the data exists</strong>. A crashed node, a corrupted segment file, a lost index — none is fatal; replay the WAL to rebuild.
Conversely, only when data has <strong>successfully entered the WAL</strong> is the write "successful" (exactly last lesson's conclusion). So the whole system's reliability boundary collapses to one clear point: <strong>guard the WAL</strong>.
That is also why WAL backends use highly-reliable, durable messaging systems like Kafka / Pulsar / Woodpecker / RMQ — handing the most critical job, "don't lose the log," to the component best at it.</p>

<p>A note on these backends' trade-offs: Kafka and Pulsar are mature industry distributed messaging systems, suited to large production clusters; RMQ (RocksMQ) is Milvus's embedded lightweight implementation, running with zero external dependencies in single-node/Standalone form (recall Lesson 8);
Woodpecker is Milvus's own object-storage-oriented WAL solution. Whichever you pick, they all <strong>unify upward into the abstraction "one PChannel = one topic"</strong> — exactly the point of the StreamingClient wrapping above:
making "which system the log lives in" a <strong>replaceable deployment choice</strong> rather than an assumption hard-wired into the code. You learn with RMQ on a small machine and switch to Pulsar to scale a production cluster, and <strong>the write-path code does not change at all</strong>.</p>

<h2>Message and TimeTick: the log's two building blocks</h2>
<p>The basic unit flowing in the WAL is a <strong>Message</strong>: an InsertMessage, a DeleteMessage, a DDL message... each with a <strong>header</strong> (type, vchannel, collection ID, etc.) and a <strong>body</strong> (the actual data).
What the Proxy packed last lesson are exactly these messages. A message is <strong>self-describing</strong>: the consumer, looking only at the message itself, knows "what operation this is, which shard it acts on, and how to apply it."</p>

<p>What <strong>strings these messages into one ordered line</strong> is <strong>TimeTick</strong>. TimeTick is a <strong>monotonically increasing log sequence number on each pchannel</strong> — think of it as the log's "clock."
It is not physical wall-clock time but a <strong>logical ruler</strong>: whoever appends first gets the smaller TimeTick. This ruler gives scattered writes a <strong>definite order</strong>,
and lets the read side judge precisely "up to which point have I consumed." The <span class="mono">MaxTimeTick</span> the Proxy filled back to the client last lesson is one tick on this ruler. <strong>The message is content; TimeTick is order</strong> — put the two blocks together and you get an "ordered, replayable" log.</p>

<p>One common confusion to clear up: if TimeTick increases monotonically, must the system <strong>precisely number</strong> every message with no gaps? It is not that rigid. TimeTick is more like a continually advancing <strong>"watermark"</strong> on the log:
the StreamingNode periodically inserts special <strong>TimeTick messages</strong> into the WAL, declaring "as of now, all writes on this channel below this timestamp are ready." Seeing this watermark, a consumer knows "I can safely make data up to here visible."
This mechanism solves a thorny problem: writes are intermittent, so how does a consumer tell "there really is no new data" from "data is in flight and hasn't arrived"? The answer is the watermark — <strong>TimeTick writes the very fact that "time is passing" into the log itself</strong>,
so even a channel with no business writes for a while keeps its "clock" advancing, and consumer visibility never stalls on a quiet channel. Grasp this and you grasp the heartbeat underlying Milvus's consistent reads.</p>

<div class="cellgroup">
  <div class="cg-cap">WAL on one pchannel: messages laid out by strictly increasing TimeTick</div>
  <div class="cells">
    <div class="cell"><span class="lab">t₁</span><span class="q">insert</span></div>
    <div class="cell"><span class="lab">t₂</span><span class="q">insert</span></div>
    <div class="cell hl"><span class="lab">t₃</span><span class="q">delete</span></div>
    <div class="cell"><span class="lab">t₄</span><span class="q">insert</span></div>
    <div class="cell dim"><span class="lab">t₅</span><span class="q">ddl</span></div>
    <div class="cell dim"><span class="lab">t₆</span><span class="q">…</span></div>
  </div>
</div>

<h2>Three channels: PChannel, VChannel, CChannel</h2>
<p>"Channel" is the WAL's partitioning concept, of three kinds, each with its own role, and easily confused — let's settle them once:</p>

<ul>
  <li><strong>PChannel (physical channel)</strong>: the <strong>physical log partition</strong> that actually carries the WAL; one PChannel maps to <strong>one topic</strong> on the WAL backend. Fixed in number, pre-opened by the cluster, the log's "physical track." TimeTick is defined on each PChannel.</li>
  <li><strong>VChannel (virtual channel)</strong>: a <strong>logical</strong> notion, "a shard of a collection." Born and dies with the collection. Many VChannels <strong>multiplex</strong> one PChannel — what the Proxy hashed to last lesson is a VChannel.</li>
  <li><strong>CChannel (control channel)</strong>: a <strong>cluster-wide, singleton</strong> control channel for control information needing <strong>global ordering across PChannels</strong>. It guarantees certain control operations have a consistent order cluster-wide.</li>
</ul>

<p>The simplest way to remember their relation: <strong>VChannels are logical shards (many), PChannels are physical logs (few), many logical shards multiplex one physical log; the CChannel is the single "control broadcast line" overhead</strong>.
Why not give each VChannel its own physical topic? Because collections can number in the thousands and shards even more; topics are a scarce resource and a one-to-one mapping would explode. Multiplexing PChannels carries <strong>elastic logical shards</strong> on <strong>fixed physical resources</strong> —
the classic "decouple logical from physical" move in distributed systems.</p>

<p>A subtle <strong>ordering granularity</strong> point hides here, worth spelling out. TimeTick's monotonic increase is defined on the <strong>PChannel</strong> physical log, meaning: <strong>all messages on one PChannel have a global order, but there is no natural total order across PChannels</strong>.
That is exactly enough — because messages of the same VChannel (same shard) always land on the same PChannel, "<strong>order within a shard</strong>" is naturally guaranteed, while shards are inherently independent and need no cross-comparison.
So how about the few operations that "need cross-PChannel global consistency" (typically DDL, e.g. creating/dropping a collection must reach all shards at once)? That is the reason <strong>CChannel</strong> and Broadcast exist: they specialize in stringing the small set of "must-be-globally-consistent" control information
into a total order over one singleton channel. <strong>Carrying "strong order within a shard" and "total order across shards" separately</strong> is Milvus's key trade-off for both high throughput and correctness — the vast majority of data takes the cheap in-shard order, the rare control takes the expensive global order.</p>

<table class="t">
  <tr><th>channel</th><th>layer</th><th>scope</th><th>purpose</th></tr>
  <tr><td class="mono">PChannel</td><td>physical</td><td>one MQ topic</td><td>actually carries the WAL; TimeTick defined here</td></tr>
  <tr><td class="mono">VChannel</td><td>logical</td><td>one shard of a collection</td><td>write-routing unit; multiplexes a PChannel</td></tr>
  <tr><td class="mono">CChannel</td><td>control</td><td>whole cluster (singleton)</td><td>global control ordering across PChannels</td></tr>
</table>

<h2>StreamingClient: Append / Broadcast / Read</h2>
<p>That <span class="mono">streaming.WAL()</span> from last lesson returns the <strong>StreamingClient</strong> (the <span class="inline">WALAccesser</span> interface in code). It is an <strong>in-process</strong> WAL access layer
that wraps all the complexity of facing the WAL backend — addressing, connecting, retrying — and exposes only three clean capabilities upward:</p>

<ul>
  <li><strong>Append (write)</strong>: write messages to the WAL. Normal writes go through <span class="mono">RawAppend / AppendMessages</span>, appending messages (transactionally) per VChannel to the corresponding PChannel. The spine of the write path.</li>
  <li><strong>Broadcast</strong>: <strong>atomically</strong> write one message across multiple VChannels, for DDL/DCL that "must take effect on several shards at once." It works with the CChannel for globally consistent ordering.</li>
  <li><strong>Read (scan)</strong>: read messages from the WAL by position, for consumers (the StreamingNode's flusher, the QueryNode's delegator, etc.) to replay the log and catch up to the latest state.</li>
</ul>

<p>Why does this wrapping layer matter? Because it completely <strong>hides</strong> "<strong>is the WAL backend Kafka, Pulsar, or something else</strong>" from the layers above. The Proxy and the consumers inside StreamingNode all talk only to the <span class="mono">WALAccesser</span> interface,
never needing to know which messaging system is underneath, what its client API looks like, or how to reconnect on a drop. To swap backends you just replace the implementation under this layer, and the upper layers <strong>change not a single line</strong> — exactly the "isolate replaceable backends behind an interface" recurring in Lessons 8 and 14.
One more easily-missed point: the StreamingClient is <strong>in-process</strong>, meaning a call to <span class="mono">Append</span> is not a raw network RPC but goes through this local client first, which handles batching, addressing, and retries.
That keeps the write-side code both simple and robust: the business only expresses "I want to write this batch of messages," while "which machine to write to, how many times to retry on failure" is quietly absorbed by this layer.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/distributed/streaming/streaming.go</span><span class="ln">the WALAccesser interface (excerpt)</span></div>
  <pre><span class="kw">type</span> WALAccesser <span class="kw">interface</span> {
    <span class="cm">// write: append one/many messages to the WAL</span>
    RawAppend(ctx context.Context, msg message.MutableMessage, opts ...AppendOption) (*types.AppendResult, <span class="kw">error</span>)
    AppendMessages(ctx context.Context, msgs ...message.MutableMessage) AppendResponses

    <span class="cm">// broadcast: atomic cross-vchannel write, paired with the control channel</span>
    Broadcast() Broadcast
    <span class="cm">// control channel name</span>
    ControlChannel() <span class="kw">string</span>

    <span class="cm">// read: scan the WAL by position for consumers to replay</span>
    Read(ctx context.Context, opts ReadOption) Scanner
}</pre>
</div>

<h2>StreamingNode and StreamingCoord</h2>
<p>The WAL system is held up by two roles. One is the <strong>StreamingNode</strong>: each StreamingNode <strong>exclusively manages a subset of PChannels</strong>, responsible for writes and consumption on them.
It carries several key duties: <strong>TimeTick &amp; transactions</strong> (ordering messages, ensuring a same-VChannel batch is transactional), <strong>locking</strong>, <strong>shard management (segment assignment)</strong> —
remember "segment ID left empty" last lesson? It is the StreamingNode that assigns the segment ID as it writes the WAL — and <strong>RecoveryStorage</strong>: maintaining checkpoints, metadata, and recovering by replaying the WAL after a crash.</p>

<p>The other role is the <strong>StreamingCoord</strong>, which is a <strong>singleton</strong> and — an easily-missed key point — <strong>runs inside the RootCoord process</strong>.
It manages two things: <strong>channel management</strong> (deciding which StreamingNode each PChannel is assigned to, and rebalancing as nodes come and go) and the <strong>Broadcaster</strong> (implementing atomic cross-PChannel DDL/DCL).
Think of the StreamingCoord as "the brain of the WAL subsystem": it does not haul logs itself, but decides <strong>who owns which physical channel</strong> and <strong>how those must-be-global-atomic control operations are coordinated</strong>.</p>

<p>Why is the StreamingCoord placed <strong>inside the RootCoord process</strong> rather than as a standalone component? Because its job is naturally close to RootCoord's: RootCoord already owns DDL and the global meta (Lesson 11), and channel assignment plus cross-channel broadcast are precisely "cluster-level metadata decisions."
Co-locating them avoids one more cross-process hop and one more thing to deploy and fail over. This is the same "<strong>fold singleton coordination duties together</strong>" instinct as the MixCoord idea from Lesson 9 — not everything that is conceptually a "coordinator" needs its own process.
The division to remember is clean: <strong>StreamingCoord decides (assignment, coordination), StreamingNode executes (carries the log, assigns segments, recovers)</strong> — yet another instance of "control plane decides, data plane does work."</p>

<div class="layers">
  <div class="layer l-app"><span class="badge">write side</span><span class="name">Proxy</span><span class="ld">validate/shard/pack, calls StreamingClient.Append</span></div>
  <div class="layer l-main"><span class="badge">client</span><span class="name">StreamingClient (WALAccesser)</span><span class="ld">in-process Append/Broadcast/Read + discovery/reconnect</span></div>
  <div class="layer l-core"><span class="badge">node</span><span class="name">StreamingNode</span><span class="ld">owns a subset of PChannels: TimeTick/txn, segment assignment, RecoveryStorage</span></div>
  <div class="layer l-part"><span class="badge">backend</span><span class="name">WAL backend (Kafka/Pulsar/Woodpecker/RMQ)</span><span class="ld">one PChannel = one topic, durable log</span></div>
</div>

<h2>Log as data: other shapes catch up by replaying</h2>
<p>Put it together and you get the most central sentence of Milvus's write architecture: <strong>the WAL is the truth; everything else is its "projection"</strong>. A segment is the columnar file produced by accumulating insert messages from the WAL and persisting them;
an index is an acceleration structure built atop a segment; the searchable data in a QueryNode's memory is what it got by <strong>consuming the WAL and replaying messages</strong>. Different shapes, but all doing one thing: <strong>following the WAL forward, "translating" the log into the form each needs</strong>.</p>

<p>This "<strong>log as data</strong>" design pays off in enormous <strong>decoupling and elasticity</strong>. Add a QueryNode? Let it start consuming from some WAL position and gradually catch up — no downtime, no data hauling.
A consumer fell behind? It accelerates its own replay along the WAL to catch up, affecting no one else. The write side just <strong>reliably appends messages in order</strong>; the read, persist, and index sides each <strong>consume independently</strong> —
not directly coupled to each other, only collaborating indirectly through this one <strong>ordered log</strong>. That is why Milvus can optimize "write fast" and "read steady" separately: a single log cleanly separates them.
Next lesson we follow one of those consumers — the one that accumulates WAL inserts into a segment and flushes it into a binlog — to see the first concrete step of "log becoming data."</p>

<p>A parting line worth savoring: <strong>in Milvus, "writing" and "persisting" are two deliberately separated things</strong>. Writing answers only to the WAL — fast and light; persisting is what background consumers do slowly along the WAL — steady and frugal.
It is this WAL that cleanly cuts apart "what must be done at once" from "what can be done at leisure" — understand it and you hold the master outline of the whole write path.</p>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>the WAL is the single source of truth; it is made of messages (content) + TimeTick (a per-PChannel monotonically increasing order); channels split into PChannel (physical topic) / VChannel (logical shard, multiplexing a PChannel) / CChannel (cluster-wide control); StreamingClient offers Append/Broadcast/Read; the StreamingNode exclusively manages PChannels (TimeTick, segment assignment, RecoveryStorage) and the StreamingCoord is a singleton running inside RootCoord doing channel assignment and broadcast</strong>.
  Segments, indexes, and in-memory data are all shapes derived by replaying the WAL — log as data.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Single source of truth</strong>: every mutation enters the WAL first; segments/indexes/in-memory data are WAL derivatives, rebuilt by replay after a crash.</li>
    <li><strong>Message + TimeTick</strong>: a message is self-describing content; <span class="mono">TimeTick</span> is a per-PChannel monotonically increasing logical sequence number ordering messages.</li>
    <li><strong>Three channels</strong>: <span class="mono">PChannel</span> (physical topic) ← <span class="mono">VChannel</span> (logical shard, multiplexes a PChannel) + <span class="mono">CChannel</span> (cluster-wide control ordering).</li>
    <li><strong>StreamingClient</strong>: the <span class="mono">WALAccesser</span> interface, in-process <span class="mono">Append / Broadcast / Read</span>, wrapping addressing and reconnection.</li>
    <li><strong>Two roles</strong>: the <span class="mono">StreamingNode</span> exclusively manages PChannels (TimeTick/txn, segment assignment, RecoveryStorage); the <span class="mono">StreamingCoord</span> is a singleton running inside RootCoord doing channel assignment and cross-channel broadcast.</li>
    <li><strong>Log as data</strong>: consumers replay along the WAL to catch up; write/read/persist are decoupled — the root of Milvus's elasticity.</li>
  </ul>
</div>
""",
}

LESSON_17 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课我们认清了 WAL 是单一事实来源，也埋了个钩子：段、索引这些"可检索的数据"，都是<strong>消费 WAL、回放日志</strong>得到的派生形态。
这一课就来看"<strong>日志变成数据</strong>"的第一步——WAL 里的 insert 消息，如何先在内存里攒成一个 <strong>growing 段（增长中的段）</strong>，
再在合适的时机 <strong>flush（封口落盘）</strong>成对象存储里的 <strong>binlog</strong> 文件。顺带，我们把一个常被搞混的问题讲清楚：<strong>这件事到底是谁干的——StreamingNode 还是 DataNode？</strong>
答案会颠覆一些旧教程给你的印象——所以这一课的另一条暗线，就是<strong>纠正"DataNode 负责落盘"这个过时的认知</strong>。
</p>

<div class="card analogy">
  <div class="tag">🏭 生活类比</div>
  把这条路想成一个<strong>装箱发货</strong>的流水线。WAL 是源源不断送来零件的传送带；工位上摆着一个<strong>正在装的箱子</strong>（growing 段），零件（insert 行）来一个就往里码一个。
  箱子不会无限装下去——<strong>装满了</strong>（达到大小阈值）、或者<strong>等得太久了</strong>（达到时间阈值），就该<strong>封箱</strong>（seal）。封好的箱子贴上清单、送进<strong>仓库</strong>（对象存储），从此<strong>只读不再改</strong>，这就是一个 binlog。
  注意分工：<strong>"零件该进哪个箱子"由调度台统一指派</strong>（段分配，StreamingNode 来做），而<strong>"把箱子封好、搬进仓库"是打包工的活</strong>（flush，落盘机制来做）。
  整条线最妙的一点是：传送带（WAL）上的零件清单<strong>永远留底</strong>——就算某个还没封的箱子被碰翻了，照着传送带的记录重新码一遍就行，一个零件都不会少。
</div>

<h2>growing 段：从 WAL 攒出来的内存缓冲</h2>
<p>回忆第 7 课：一个段（segment）是 Milvus 数据组织的基本单位。段有两种状态——<strong>growing（增长中）</strong>和 <strong>sealed（已封口）</strong>。一行数据落盘的旅程，正是从 growing 开始的。
当消费者沿着 WAL 往前读，遇到一条 InsertMessage，就把它的行<strong>追加进内存里对应的 growing 段</strong>。这个内存缓冲，在代码里由 <span class="inline">writebuffer</span> 维护（<span class="mono">internal/flushcommon/writebuffer</span>），
它按 vchannel 把消费到的行攒起来，等着够多了再一次性落盘。</p>

<p>"growing（增长中）"这个名字起得很传神：它<strong>正在长大</strong>，行数在涨、占的内存在涨，但还没定型。和它相对的 sealed 段则像一块"<strong>已经定型的化石</strong>"——内容固定、再不改动。
一个集合在某一时刻，往往同时存在<strong>少量 growing 段</strong>（每个活跃分片一个，正在接新数据）和<strong>大量 sealed 段</strong>（历史数据，已落盘）。
这个比例本身就揭示了向量数据库的负载形态：<strong>绝大多数数据是"写过就稳定下来"的历史，只有最前沿的一小撮还在变动</strong>。把"在变的"和"不变的"分成两类段、给两种待遇，正是 Milvus 高效的起点。</p>

<p>这里要回收上一课、上上一课埋的两个钩子。第一：<strong>段 ID 是谁分配的？</strong>上一课讲过，Proxy 打包时把段 ID 留空（填 0），真正的分配推迟到了 <strong>StreamingNode</strong>。
具体说，StreamingNode 的 WAL 写入链路里有一个<strong>分片管理（Shard Management）拦截器</strong>（<span class="mono">internal/streamingnode/server/wal/interceptors/shard</span>），
它在消息写进 WAL 时，决定"这批行该归属哪个段"——段满了就开一个新的。所以<strong>段分配是写入侧、在 StreamingNode 上完成的</strong>，这保证了同一分片的段编号有唯一、一致的来源。
第二：为什么要先在内存里攒、而不是来一行写一行？因为对象存储<strong>擅长大文件、怕小文件</strong>——把成千上万行攒成一个大 binlog 再落盘，远比一行一个小文件高效。这就是 growing 段存在的根本理由：<strong>用内存缓冲把"碎写"聚合成"批写"</strong>。</p>

<p>再往深想一层，growing 段其实是一个精妙的"<strong>缓冲带</strong>"，它吸收了写入侧与落盘侧之间的<strong>速率差</strong>。WAL 的写入可以很快、很突发——一秒钟灌进几十万行毫不稀奇；
而对象存储的落盘有固定的开销，喜欢"少而大"的文件。如果没有 growing 段这层缓冲，每来一行就落一个文件，对象存储会被海量小文件活活拖垮（元数据爆炸、吞吐崩塌）。
growing 段把这股<strong>湍急的写入流</strong>蓄成一个个"水池"，蓄满了再一次性泄洪到对象存储——既保护了后端，又摊薄了每行的落盘成本。这是几乎所有 LSM-Tree 类存储引擎共有的智慧：
<strong>先在内存里攒（memtable），再批量落盘（SSTable）</strong>。Milvus 的 growing→sealed，本质上就是这套思路在向量数据上的实现。</p>

<h2>flush：何时封口、落成 binlog</h2>
<p>growing 段不会无限长大。当它满足某个<strong>触发条件</strong>，就会被<strong>封口（seal）</strong>，随后<strong>flush</strong> 到对象存储。常见的触发条件有两类：</p>

<ul>
  <li><strong>按大小</strong>：段攒到了配置的容量上限（行数或字节数），说明"箱子装满了"，该封。</li>
  <li><strong>按时间</strong>：段虽然没满，但已经存在了足够久（或收到了显式的 flush 请求），为了让数据尽快可持久、可被后续处理，也会封。</li>
</ul>

<p>为什么要同时有这两个触发条件，而不是只看大小？因为它们各自堵住了一种"<strong>坏情况</strong>"。只看大小，会出现这样的尴尬：某个冷门分片写得很慢，一个 growing 段半天攒不满，
那这批数据就迟迟落不了盘——既占着内存，又迟迟不能被建索引、不能被高效检索。<strong>按时间封口</strong>正是为了兜住这种慢分片：哪怕没满，攒够一段时间也强制落盘，保证数据"可见性"和"持久性"的延迟有上界。
反过来，只看时间也不行：一个热门分片瞬间灌进海量行，要是非等到固定时间才封，单个段会膨胀到内存扛不住。<strong>按大小封口</strong>正是为了兜住这种快分片。两个条件<strong>取先到者</strong>——
谁先满足就按谁封——既不让快的撑爆内存，也不让慢的饿着不落盘。这是一种典型的"<strong>用两个维度的阈值，夹出一个健康的工作区间</strong>"的工程手法，你在限流、批处理、缓存刷新里会反复见到它。
此外还有一类<strong>显式 flush</strong>：用户主动调用 flush、或系统在某些操作（如建索引、释放集合）前需要确保数据已落盘，会直接请求封口——这给了上层一个"<strong>把当前写入强制定格</strong>"的手段。</p>

<p>封口之后的落盘动作，由<strong>同步管理器（SyncManager）</strong>负责（<span class="mono">internal/flushcommon/syncmgr</span>）。它把这个段在内存里攒的数据，序列化成一个个 <strong>binlog 文件</strong>写进对象存储。
一次落盘被封装成一个 <span class="inline">SyncTask</span>，里面清清楚楚记着：这是哪个集合、哪个分区、哪个段，时间戳范围是多少，以及生成了哪些 binlog——
<strong>插入数据的 insertBinlogs、统计信息的 statsBinlogs、删除标记的 deltaBinlog</strong>（下一课第 18 课会专门拆解这些 binlog 的格式）。SyncTask 跑完，这个段就从"内存里的 growing"变成了"对象存储里的 sealed"，数据第一次真正<strong>落到了磁盘</strong>。</p>

<p>这里有个值得点破的细节：flush <strong>不是</strong>"把整个 growing 段一次性原子替换掉"，而更像"<strong>把当前攒的这一批数据切下来、打包成 binlog 写出去</strong>"。
一个逻辑段在它的生命周期里，可能经历<strong>多次 flush</strong>——每次把新攒的增量写成一批新的 binlog，所以一个段在对象存储里往往对应<strong>一组（而非一个）binlog 文件</strong>。
这也解释了为什么后面需要 <strong>compaction</strong>（第 19 课）：随着不断 flush，小 binlog 会越积越多，必须定期合并，否则检索时要打开的文件碎片就太多了。
另外，flush 完成后还有关键一步——<strong>回写元数据</strong>：通过 metaWriter 把"这个段新增了哪些 binlog、路径在哪、行数多少"登记到元数据里（最终落到 DataCoord 管理的段元信息中，回忆第 12 课）。
只有元数据登记成功，这批 binlog 才算"被系统认可、可被后续查询和 compaction 看见"。<strong>数据落对象存储 + 元数据登记，两件事都成了，一次 flush 才算真正完成。</strong></p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/flushcommon/syncmgr/task.go</span><span class="ln">SyncTask：一次 flush 的全部账目（节选）</span></div>
  <pre><span class="kw">type</span> SyncTask <span class="kw">struct</span> {
    collectionID int64
    partitionID  int64
    segmentID    int64        <span class="cm">// 由 StreamingNode 分配的段 ID</span>
    channelName  string
    tsFrom, tsTo typeutil.Timestamp  <span class="cm">// 这批数据的时间戳范围</span>

    <span class="cm">// 落盘生成的三类 binlog（字段 ID -&gt; binlog）</span>
    insertBinlogs map[int64]*datapb.FieldBinlog  <span class="cm">// 插入数据</span>
    statsBinlogs  map[int64]*datapb.FieldBinlog  <span class="cm">// 统计信息</span>
    deltaBinlog   *datapb.FieldBinlog            <span class="cm">// 删除标记</span>
    <span class="cm">// ... chunkManager（对象存储）/ metaWriter（回写元数据） 等</span>
}</pre>
</div>

<h2>谁干哪一摊：StreamingNode 与 DataNode</h2>
<p>现在回答开头那个最容易搞混的问题。在<strong>流式架构</strong>下，这条"消费 WAL → growing 段 → flush → binlog"的流水线，到底跑在哪？答案是：<strong>主要由 StreamingNode 驱动</strong>。
StreamingNode 内部有一个 <strong>flusher（落盘器）</strong>（<span class="mono">internal/streamingnode/server/flusher</span>），它<strong>消费自己负责的那些 PChannel 上的 WAL</strong>，
复用上面讲的 <span class="mono">writebuffer</span> 与 <span class="mono">syncmgr</span> 这套通用落盘机制，把日志攒成段、flush 成 binlog。同时 StreamingNode 还维护 <strong>RecoveryStorage（恢复存储）</strong>——
记录"消费到哪了"的检查点，崩溃重启后能从 WAL 正确位置接着消费，不重不漏。换句话说，<strong>段分配、消费 WAL、攒段、落盘、检查点，这一整套都收拢在了 StreamingNode 这一侧</strong>。</p>

<p>那 <strong>DataNode</strong> 还做什么？在流式架构里，DataNode 的角色已经<strong>收窄</strong>：它不再是"消费消息队列、攒段落盘"的主力，而是主要承担<strong>后台的重活——compaction（段合并/压实）</strong>，
由 DataCoord 调度、DataNode 执行（第 19 课详述）。简单记：<strong>StreamingNode 负责"把日志变成段、把段落成 binlog"（写入路的落盘）；DataNode/DataCoord 负责"把已有的 binlog 整理得更高效"（后台的合并与回收）。</strong>
这条边界不必死记每个包名，但要抓住骨架：<strong>落盘在 StreamingNode（沿 WAL），整理在 DataNode（离线）。</strong>它们共享 <span class="mono">flushcommon</span> 这套通用代码，但触发的时机和目的截然不同。</p>

<p>为什么 Milvus 要把"落盘"从 DataNode 挪到 StreamingNode？这背后是流式架构的一次重要演进。在<strong>旧模型</strong>里，Proxy 把消息发进消息队列，DataNode 作为独立消费者去订阅、攒段、落盘——
写入路径上隔着一层"队列 + 独立消费进程"，链路长、协调点多。<strong>新模型</strong>把"写 WAL"和"消费 WAL 落盘"<strong>收拢到同一侧</strong>：StreamingNode 既是某批 PChannel 的写入负责人，又是它们的消费者。
好处很直接：段分配（写入时做）与段落盘（消费时做）发生在<strong>同一个进程</strong>里，对"这个段现在攒到哪了"有最一手、最一致的认知，不必跨进程同步状态；
崩溃恢复也更干净——RecoveryStorage 就在本地，记着检查点，重启即可沿 WAL 续上。这正是上一课"<strong>把有状态的职责收归到独占该通道的单一节点</strong>"那条原则，在落盘这件事上的兑现。</p>

<p>所以如果你脑子里还残留着"DataNode 消费 MQ、攒段、flush"的旧图景，这一课请把它<strong>更新掉</strong>：在当前流式架构下，<strong>落盘的主力是 StreamingNode 的 flusher</strong>，DataNode 退居二线、专注后台 compaction。
这也是为什么我们这一部分（写入链路）的核心是 WAL 与 StreamingNode，而把 compaction、GC 单独留到后面讲——<strong>"写进来"和"整理好"是两条节奏完全不同的线</strong>，分开理解才不会乱。</p>

<table class="t">
  <tr><th>职责</th><th>谁来做</th><th>关键包</th></tr>
  <tr><td><strong>段分配</strong>（决定行进哪个段）</td><td>StreamingNode（写入时）</td><td class="mono">streamingnode/.../interceptors/shard</td></tr>
  <tr><td><strong>消费 WAL、攒 growing 段</strong></td><td>StreamingNode 的 flusher</td><td class="mono">streamingnode/server/flusher · flushcommon/writebuffer</td></tr>
  <tr><td><strong>flush 落盘成 binlog</strong></td><td>SyncManager（被 flusher 调用）</td><td class="mono">flushcommon/syncmgr</td></tr>
  <tr><td><strong>检查点/崩溃恢复</strong></td><td>StreamingNode 的 RecoveryStorage</td><td class="mono">streamingnode/server/wal/recovery</td></tr>
  <tr><td><strong>compaction / GC</strong></td><td>DataCoord 调度、DataNode 执行</td><td class="mono">datacoord · datanode（第 19 课）</td></tr>
</table>

<h2>一行数据落盘的全程</h2>
<p>把这条路连成一条线，你就看完了"日志变成数据"的第一步，也看清了写入链路最后一个环节的全貌：</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>消费 WAL</h4><p>StreamingNode 的 flusher 沿自己负责的 PChannel 读 InsertMessage。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>攒进 growing 段</h4><p class="mono">writebuffer</p><p>按 vchannel 把行追加进内存里的 growing 段（段 ID 已由 StreamingNode 分配）。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>触发封口</h4><p>段满（大小）或够久（时间），seal。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>flush 落盘</h4><p class="mono">syncmgr · SyncTask</p><p>序列化成 insert/stats/delta binlog 写进对象存储。</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>回写元数据 + 检查点</h4><p>登记段为 sealed、记录 binlog 路径；推进 RecoveryStorage 检查点。</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>后续：compaction</h4><p>DataCoord 择机调度 DataNode 合并小段（第 19 课）。</p></div></div>
</div>

<h2>growing 与 sealed：两种段、两种待遇</h2>
<p>最后把 growing 与 sealed 这对概念并排放，你会更清楚这条路的"相变（phase transition）"到底发生了什么：</p>

<div class="cols">
  <div class="col"><h4>growing 段</h4><p>活在<strong>内存</strong>里，正在从 WAL 不断接收新行，<strong>可写可读但易失</strong>。它的可靠性其实来自<strong>背后的 WAL</strong>——即使 growing 段还没落盘就丢了，从 WAL 重放即可重建。
  查询要读到最新数据，就必须同时查 growing 段（这部分由 QueryNode 的 delegator 处理，留到读取链路细讲）。</p></div>
  <div class="col"><h4>sealed 段</h4><p>已 flush 成<strong>对象存储里的 binlog</strong>，<strong>只读、不可变、持久</strong>。它是后续<strong>建索引</strong>（在不可变数据上才好建）、<strong>compaction</strong>（合并、应用删除）的对象。
  一旦 sealed，这段数据就脱离了 WAL 的"待消费"队列，正式成为冷静、稳定的"已落盘资产"，也才有资格在它之上建索引、与其他段合并。</p></div>
</div>

<p>这个从 growing 到 sealed 的相变，是 Milvus 把"高速写入"与"高效检索"<strong>缝合</strong>的关键接缝：写入侧只管把行往 growing 段里灌、灌满就封；
检索侧则在一个个不可变的 sealed 段上建索引、做查询。两侧由这条 flush 流水线连接，又被 WAL 这条单一事实来源兜底。理解了这一步，你就理解了一行数据"从日志到磁盘"的完整一跃——下一课，我们打开那个 binlog 文件，看看里面的列式格式到底长什么样，以及它为什么对向量检索如此关键。</p>

<p>临走前再把这一部分（写入链路）的脉络收一收。从第 15 课到这里，我们完整走了一遍"<strong>一行数据从进门到落盘</strong>"：Proxy 校验、定主键、哈希分片、打包，把消息 Append 进 WAL（第 15 课）；
WAL 作为单一事实来源，用消息 + TimeTick 把写入串成有序、可重放的日志，由 StreamingNode/StreamingCoord 撑起（第 16 课）；StreamingNode 的 flusher 再沿 WAL 把日志攒成 growing 段、flush 成 binlog（这一课）。
三课连起来，恰好就是开篇那张图——<strong>客户端 → Proxy → StreamingClient.Append → StreamingNode → WAL 后端 →（落盘）对象存储</strong>——的逐段展开。
至于落盘之后的事：binlog 内部长什么样、小段怎么合并、删除与 upsert 怎么处理，是本部分后面几课的内容。<strong>写入的主干你已经握住了，剩下的都是在这条主干上长出的枝叶。</strong></p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话串起来：<strong>StreamingNode 的 flusher 消费自己 PChannel 上的 WAL → 按 vchannel 把行攒进内存里的 growing 段（段 ID 在写入时已由 StreamingNode 的 shard 拦截器分配）→ 段满或够久则 seal → SyncManager 把数据序列化成 insert/stats/delta binlog flush 进对象存储，并回写元数据、推进 RecoveryStorage 检查点</strong>。
  落盘在 StreamingNode（沿 WAL），而 compaction/GC 这类后台整理由 DataCoord 调度、DataNode 执行。记住骨架：<strong>落盘在线（StreamingNode）、整理离线（DataNode）</strong>。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>growing 段</strong>：从 WAL 消费的行先攒进内存缓冲（<span class="mono">flushcommon/writebuffer</span>），可写可读但易失，可靠性靠背后的 WAL 兜底。</li>
    <li><strong>段分配在写入侧</strong>：段 ID 由 StreamingNode 的分片管理拦截器分配（<span class="mono">interceptors/shard</span>），不是 Proxy、也不是 flush 时才定。</li>
    <li><strong>flush 触发</strong>：段满（大小）或够久（时间/显式请求）则 seal，由 <span class="mono">SyncManager</span> 的 <span class="mono">SyncTask</span> 序列化成 binlog 落对象存储。</li>
    <li><strong>三类 binlog</strong>：insert（数据）、stats（统计）、delta（删除标记），细节见第 18 课。</li>
    <li><strong>分工</strong>：StreamingNode 负责消费 WAL、攒段、flush、检查点（落盘）；DataCoord/DataNode 负责 compaction/GC（后台整理，第 19 课）；二者共享 <span class="mono">flushcommon</span>。</li>
    <li><strong>相变</strong>：growing（内存、可变、易失）→ sealed（对象存储、只读、持久），是写入与检索的接缝。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson we saw the WAL is the single source of truth, and planted a hook: segments, indexes — the "searchable data" — are all shapes derived by <strong>consuming the WAL and replaying the log</strong>.
This lesson covers the first step of "<strong>log becoming data</strong>" — how insert messages in the WAL first accumulate in memory into a <strong>growing segment</strong>,
then at the right moment <strong>flush</strong> (seal and persist) into <strong>binlog</strong> files in object storage. Along the way we settle a commonly-confused question: <strong>who actually does this — the StreamingNode or the DataNode?</strong>
The answer overturns what some older tutorials taught — so another undercurrent of this lesson is <strong>correcting the outdated belief that "the DataNode handles persistence."</strong>
</p>

<div class="card analogy">
  <div class="tag">🏭 Analogy</div>
  Picture this path as a <strong>packing-and-shipping</strong> line. The WAL is a conveyor steadily delivering parts; at the station sits <strong>a box being filled</strong> (the growing segment), and each arriving part (insert row) is stacked into it.
  The box won't fill forever — once it is <strong>full</strong> (size threshold) or has <strong>waited too long</strong> (time threshold), it gets <strong>sealed</strong>. The sealed box, with its manifest, ships to the <strong>warehouse</strong> (object storage) and becomes <strong>read-only, never changed</strong> — that is a binlog.
  Note the division of labor: <strong>"which box a part goes into" is assigned by the dispatch desk</strong> (segment assignment, done by the StreamingNode), while <strong>"seal the box and haul it to the warehouse" is the packer's job</strong> (flush, done by the persistence machinery).
  The neatest part of the whole line: the parts manifest on the conveyor (the WAL) <strong>is always kept</strong> — even if an unsealed box is knocked over, just re-stack it from the conveyor's record and not a single part is lost.
</div>

<h2>The growing segment: an in-memory buffer accumulated from the WAL</h2>
<p>Recall Lesson 7: a segment is Milvus's basic unit of data organization. A segment has two states — <strong>growing</strong> and <strong>sealed</strong>. A row's journey to disk begins in growing.
As a consumer reads forward along the WAL and meets an InsertMessage, it <strong>appends its rows into the corresponding in-memory growing segment</strong>. This in-memory buffer is maintained in code by <span class="inline">writebuffer</span> (<span class="mono">internal/flushcommon/writebuffer</span>),
which accumulates consumed rows per vchannel, waiting until there is enough to persist in one shot.</p>

<p>The name "growing" is wonderfully apt: it <strong>is getting bigger</strong> — row count rising, memory rising — but not yet set. Its opposite, the sealed segment, is like a "<strong>fossil already set in shape</strong>" — fixed content, never changed again.
At any moment a collection often holds <strong>a few growing segments</strong> (one per active shard, receiving new data) alongside <strong>many sealed segments</strong> (historical data, persisted).
That ratio itself reveals a vector DB's workload shape: <strong>the vast majority of data is history that "stabilizes once written," and only the small leading edge is still changing</strong>. Splitting "changing" from "unchanging" into two segment kinds with two treatments is the very starting point of Milvus's efficiency.</p>

<p>Here we reclaim two hooks planted in the last two lessons. First: <strong>who assigns the segment ID?</strong> Last lesson, the Proxy left the segment ID empty (0) when packing, deferring the real assignment to the <strong>StreamingNode</strong>.
Concretely, the StreamingNode's WAL write path has a <strong>Shard Management interceptor</strong> (<span class="mono">internal/streamingnode/server/wal/interceptors/shard</span>),
which, as a message is written to the WAL, decides "which segment these rows belong to" — opening a new one when a segment is full. So <strong>segment assignment happens on the write side, on the StreamingNode</strong>, giving each shard's segment numbering a unique, consistent source.
Second: why accumulate in memory rather than write row-by-row? Because object storage <strong>loves big files and hates small ones</strong> — accumulating thousands of rows into one big binlog before persisting is far more efficient than one small file per row. That is the fundamental reason growing segments exist: <strong>use an in-memory buffer to aggregate "scattered writes" into "batched writes."</strong></p>

<p>One layer deeper, the growing segment is really a clever <strong>buffer zone</strong> absorbing the <strong>rate mismatch</strong> between the write side and the persist side. WAL writes can be fast and bursty — hundreds of thousands of rows a second is nothing unusual;
object-storage persistence has fixed overhead and prefers "few, large" files. Without the growing segment as a buffer, persisting one file per arriving row would crush object storage under a sea of tiny files (metadata explosion, throughput collapse).
The growing segment pools this <strong>torrential write stream</strong> into "reservoirs," releasing a flood to object storage only once a pool is full — protecting the backend and amortizing the per-row persist cost. This is the wisdom shared by nearly all LSM-tree storage engines:
<strong>accumulate in memory first (memtable), then batch-persist (SSTable)</strong>. Milvus's growing→sealed is essentially that idea realized over vector data.</p>

<h2>flush: when to seal and persist into a binlog</h2>
<p>A growing segment doesn't grow forever. When it meets a <strong>trigger condition</strong> it is <strong>sealed</strong> and then <strong>flushed</strong> to object storage. Two common trigger kinds:</p>

<ul>
  <li><strong>By size</strong>: the segment reached the configured capacity cap (row count or bytes) — "the box is full," so seal it.</li>
  <li><strong>By time</strong>: the segment isn't full but has existed long enough (or an explicit flush request arrived); to make data durable and processable sooner, it is sealed too.</li>
</ul>

<p>Why have both triggers rather than only size? Because each plugs a different "<strong>bad case</strong>." Size-only leads to an awkward situation: a cold, slow-writing shard takes ages to fill one growing segment,
so that batch of data lingers unpersisted — occupying memory yet unable to be indexed or efficiently searched. <strong>Time-based sealing</strong> backstops exactly this slow shard: even when not full, after enough time it is force-persisted, bounding the latency of data "visibility" and "durability."
Conversely, time-only fails too: a hot shard flooded with rows in an instant would, if forced to wait for a fixed time, balloon a single segment beyond what memory can hold. <strong>Size-based sealing</strong> backstops this fast shard. The two conditions take <strong>whichever comes first</strong> —
seal by whoever is satisfied earlier — so the fast don't blow up memory and the slow don't starve unpersisted. This is a classic engineering move: "<strong>use thresholds on two dimensions to bracket a healthy operating range</strong>," which you'll meet again in rate limiting, batching, and cache flushing.
There is also an <strong>explicit flush</strong>: a user actively calling flush, or the system needing data persisted before certain operations (like index building or releasing a collection), requests sealing directly — giving upper layers a way to "<strong>freeze the current writes</strong>."</p>

<p>The persisting action after sealing is handled by the <strong>SyncManager</strong> (<span class="mono">internal/flushcommon/syncmgr</span>). It serializes the data accumulated in this segment into individual <strong>binlog files</strong> written to object storage.
One persist is wrapped as a <span class="inline">SyncTask</span>, which records clearly: which collection, partition, and segment this is, its timestamp range, and which binlogs were produced —
<strong>insertBinlogs for the inserted data, statsBinlogs for statistics, and deltaBinlog for delete markers</strong> (Lesson 18 dissects these binlog formats). Once the SyncTask completes, the segment turns from "an in-memory growing" into "a sealed one in object storage," and the data <strong>truly lands on disk</strong> for the first time.</p>

<p>A detail worth spelling out: flush is <strong>not</strong> "atomically swapping out the entire growing segment," but more like "<strong>slicing off the batch currently accumulated, packaging it into binlogs, and writing it out</strong>."
A logical segment may undergo <strong>multiple flushes</strong> over its lifetime — each writing the newly accumulated increment as a fresh batch of binlogs, so a segment in object storage often corresponds to <strong>a set of (not one) binlog files</strong>.
This also explains why <strong>compaction</strong> (Lesson 19) is later needed: as flushes continue, small binlogs pile up and must be periodically merged, or a query would have to open too many file fragments.
Also, after flush completes comes a key step — <strong>writing back metadata</strong>: via the metaWriter, "which binlogs this segment gained, their paths, the row counts" are registered into the metadata (ultimately into the segment meta managed by DataCoord, recall Lesson 12).
Only when the metadata registration succeeds is this batch of binlogs "recognized by the system, visible to later queries and compaction." <strong>Data to object storage + metadata registered, both done, and only then is one flush truly complete.</strong></p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/flushcommon/syncmgr/task.go</span><span class="ln">SyncTask: all the bookkeeping of one flush (excerpt)</span></div>
  <pre><span class="kw">type</span> SyncTask <span class="kw">struct</span> {
    collectionID int64
    partitionID  int64
    segmentID    int64        <span class="cm">// segment ID assigned by the StreamingNode</span>
    channelName  string
    tsFrom, tsTo typeutil.Timestamp  <span class="cm">// timestamp range of this batch</span>

    <span class="cm">// the three binlog kinds produced on persist (field ID -&gt; binlog)</span>
    insertBinlogs map[int64]*datapb.FieldBinlog  <span class="cm">// inserted data</span>
    statsBinlogs  map[int64]*datapb.FieldBinlog  <span class="cm">// statistics</span>
    deltaBinlog   *datapb.FieldBinlog            <span class="cm">// delete markers</span>
    <span class="cm">// ... chunkManager (object storage) / metaWriter (write back meta), etc.</span>
}</pre>
</div>

<h2>Who does what: StreamingNode vs DataNode</h2>
<p>Now answer the easily-confused question from the start. In the <strong>streaming architecture</strong>, where does this "consume WAL → growing segment → flush → binlog" pipeline actually run? The answer: <strong>mainly driven by the StreamingNode</strong>.
The StreamingNode contains a <strong>flusher</strong> (<span class="mono">internal/streamingnode/server/flusher</span>) that <strong>consumes the WAL on the PChannels it owns</strong>,
reusing the same general persistence machinery — <span class="mono">writebuffer</span> and <span class="mono">syncmgr</span> — to accumulate the log into segments and flush them into binlogs. The StreamingNode also maintains <strong>RecoveryStorage</strong> —
a checkpoint of "how far I have consumed," so that on crash-restart it resumes consuming from the correct WAL position with no loss or duplication. In other words, <strong>segment assignment, WAL consumption, segment accumulation, persistence, and checkpointing are all gathered on the StreamingNode side</strong>.</p>

<p>So what does the <strong>DataNode</strong> still do? In the streaming architecture the DataNode's role has <strong>narrowed</strong>: it is no longer the main force "consuming a message queue and persisting segments," but mainly takes on the <strong>heavy background work — compaction</strong>,
scheduled by DataCoord and executed by the DataNode (detailed in Lesson 19). Remember it simply: <strong>the StreamingNode "turns the log into segments and segments into binlogs" (write-path persistence); the DataNode/DataCoord "tidy existing binlogs to be more efficient" (background merge and reclaim).</strong>
Don't memorize every package name on this boundary, but grasp the skeleton: <strong>persistence on the StreamingNode (along the WAL), tidying on the DataNode (offline).</strong> They share the common <span class="mono">flushcommon</span> code, but their triggers and purposes are entirely different.</p>

<p>Why does Milvus move "persistence" from the DataNode to the StreamingNode? Behind this is an important evolution of the streaming architecture. In the <strong>old model</strong>, the Proxy published messages to a message queue, and the DataNode, as an independent consumer, subscribed, accumulated segments, and persisted —
the write path had a layer of "queue + independent consumer process" in the way, with a long chain and many coordination points. The <strong>new model</strong> <strong>gathers "write the WAL" and "consume the WAL to persist" onto the same side</strong>: the StreamingNode is both the write owner of a subset of PChannels and their consumer.
The benefit is direct: segment assignment (done at write time) and segment persistence (done at consume time) happen in the <strong>same process</strong>, with first-hand, consistent knowledge of "how far this segment has accumulated," needing no cross-process state sync;
crash recovery is cleaner too — RecoveryStorage is local, holding the checkpoint, so a restart just resumes along the WAL. This is exactly last lesson's principle of "<strong>gather stateful duties into the single node that owns the channel</strong>," realized for persistence.</p>

<p>So if your mind still carries the old picture of "DataNode consumes the MQ, accumulates segments, flushes," this lesson please <strong>update it</strong>: under the current streaming architecture, <strong>the main force of persistence is the StreamingNode's flusher</strong>, while the DataNode steps back to focus on background compaction.
That is also why this part (the write path) centers on the WAL and the StreamingNode, leaving compaction and GC for later — <strong>"writing in" and "tidying up" are two lines of entirely different cadence</strong>, and understanding them separately keeps things clear.</p>

<table class="t">
  <tr><th>duty</th><th>who does it</th><th>key package</th></tr>
  <tr><td><strong>segment assignment</strong> (which segment a row enters)</td><td>StreamingNode (at write time)</td><td class="mono">streamingnode/.../interceptors/shard</td></tr>
  <tr><td><strong>consume WAL, accumulate growing segment</strong></td><td>StreamingNode's flusher</td><td class="mono">streamingnode/server/flusher · flushcommon/writebuffer</td></tr>
  <tr><td><strong>flush into binlogs</strong></td><td>SyncManager (called by the flusher)</td><td class="mono">flushcommon/syncmgr</td></tr>
  <tr><td><strong>checkpoint / crash recovery</strong></td><td>StreamingNode's RecoveryStorage</td><td class="mono">streamingnode/server/wal/recovery</td></tr>
  <tr><td><strong>compaction / GC</strong></td><td>DataCoord schedules, DataNode executes</td><td class="mono">datacoord · datanode (Lesson 19)</td></tr>
</table>

<h2>The full journey of a row to disk</h2>
<p>String the path into one line and you've seen the first step of "log becoming data":</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>consume WAL</h4><p>the StreamingNode's flusher reads InsertMessages along the PChannels it owns.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>accumulate into a growing segment</h4><p class="mono">writebuffer</p><p>append rows per vchannel into the in-memory growing segment (segment ID already assigned by the StreamingNode).</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>trigger seal</h4><p>segment full (size) or old enough (time), seal.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>flush to disk</h4><p class="mono">syncmgr · SyncTask</p><p>serialize into insert/stats/delta binlogs written to object storage.</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>write back meta + checkpoint</h4><p>register the segment as sealed, record binlog paths; advance the RecoveryStorage checkpoint.</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>later: compaction</h4><p>DataCoord schedules the DataNode to merge small segments when apt (Lesson 19).</p></div></div>
</div>

<h2>Growing vs sealed: two states, two treatments</h2>
<p>Finally, place growing and sealed side by side and the "phase transition" of this path becomes clearer:</p>

<div class="cols">
  <div class="col"><h4>growing segment</h4><p>lives in <strong>memory</strong>, continuously receiving new rows from the WAL, <strong>readable and writable but volatile</strong>. Its reliability actually comes from the <strong>WAL behind it</strong> — even if a growing segment is lost before persisting, it can be rebuilt by replaying the WAL.
  To read the latest data, a query must also read growing segments (handled by the QueryNode's delegator, left for the read path).</p></div>
  <div class="col"><h4>sealed segment</h4><p>already flushed into <strong>binlogs in object storage</strong>, <strong>read-only, immutable, durable</strong>. It is the target of later <strong>index building</strong> (best done on immutable data) and <strong>compaction</strong> (merge, apply deletes).
  Once sealed, this data leaves the WAL's "to-be-consumed" queue and formally becomes a calm, stable "persisted asset," and only then is it eligible to have indexes built on it and to be merged with other segments.</p></div>
</div>

<p>This phase transition from growing to sealed is the key seam where Milvus <strong>stitches</strong> "high-speed writes" to "efficient retrieval": the write side just pours rows into the growing segment and seals when full;
the retrieval side builds indexes and runs queries over individual immutable sealed segments. The two sides are joined by this flush pipeline and backstopped by the WAL, the single source of truth. Understand this step and
you understand a row's complete leap "from log to disk" — next lesson we open that binlog file to see what its columnar format actually looks like, and why it matters so much for vector search.</p>

<p>Before leaving, let's gather the throughline of this part (the write path). From Lesson 15 to here we walked the full arc of "<strong>a row from entering the door to landing on disk</strong>": the Proxy validates, settles the primary key, hash-shards, packs, and Appends messages to the WAL (Lesson 15);
the WAL, as the single source of truth, strings writes into an ordered, replayable log of messages + TimeTick, held up by the StreamingNode/StreamingCoord (Lesson 16); the StreamingNode's flusher then accumulates the log into growing segments along the WAL and flushes them into binlogs (this lesson).
The three lessons together are exactly the per-segment unfolding of that opening diagram — <strong>Client → Proxy → StreamingClient.Append → StreamingNode → WAL backend → (persist) object storage</strong>.
As for what happens after persistence: what a binlog looks like inside, how small segments merge, how deletes and upserts are handled — those are the later lessons of this part. <strong>You now hold the trunk of the write path; the rest are branches growing off it.</strong></p>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>the StreamingNode's flusher consumes the WAL on its PChannels → accumulates rows per vchannel into an in-memory growing segment (segment ID already assigned at write time by the StreamingNode's shard interceptor) → seals when full or old enough → the SyncManager serializes the data into insert/stats/delta binlogs flushed to object storage, writes back metadata, and advances the RecoveryStorage checkpoint</strong>.
  Persistence is on the StreamingNode (along the WAL), while background tidying like compaction/GC is scheduled by DataCoord and executed by the DataNode. Remember the skeleton: <strong>persistence online (StreamingNode), tidying offline (DataNode)</strong>.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Growing segment</strong>: rows consumed from the WAL first accumulate in an in-memory buffer (<span class="mono">flushcommon/writebuffer</span>) — readable/writable but volatile, with reliability backstopped by the WAL.</li>
    <li><strong>Assignment on the write side</strong>: segment IDs are assigned by the StreamingNode's shard-management interceptor (<span class="mono">interceptors/shard</span>), not the Proxy and not at flush time.</li>
    <li><strong>Flush triggers</strong>: full (size) or old enough (time/explicit request) seals the segment; <span class="mono">SyncManager</span>'s <span class="mono">SyncTask</span> serializes it into binlogs in object storage.</li>
    <li><strong>Three binlog kinds</strong>: insert (data), stats (statistics), delta (delete markers); details in Lesson 18.</li>
    <li><strong>Division of labor</strong>: the StreamingNode consumes the WAL, accumulates, flushes, checkpoints (persistence); DataCoord/DataNode do compaction/GC (background tidying, Lesson 19); both share <span class="mono">flushcommon</span>.</li>
    <li><strong>Phase transition</strong>: growing (memory, mutable, volatile) → sealed (object storage, read-only, durable) — the seam between writing and retrieval.</li>
  </ul>
</div>
""",
}
