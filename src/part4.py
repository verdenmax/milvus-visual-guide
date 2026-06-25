"""Part 4 · The write path (lessons 15-20). One Part module per milestone.

Part 4 covers L15-L20: L15 insert via Proxy, L16 streaming &amp; WAL, L17 datanode &
flush, L18 binlog &amp; storage format, L19 compaction &amp; GC, and L20 delete &amp; upsert
(MVCC). Each value is ``{"zh": html, "en": html}`` and is
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

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>包装成 insertTask</h4><p>insert 请求进 Proxy，在 <span class="mono">PreExecute</span> 阶段做数据正确性检查。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>校验主键列</h4><p><span class="mono">checkPrimaryFieldData</span>：主键是否合法、是否与 schema 一致。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>autoID? 分配 : 校验</h4><p>自增→为每行<strong>分配全局唯一主键</strong>并回填；自带→校验非空/不重/类型匹配。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>主键 IDs 敲定</h4><p>主键确定，才能据它<strong>路由到分片</strong>（下一关）。</p></div></div>
</div>

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
    mlog.Warn(ctx, <span class="st">"check primary field data and hash primary key failed"</span>, mlog.Err(err))
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

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Wrap into an insertTask</h4><p>the insert enters the Proxy; <span class="mono">PreExecute</span> runs data-correctness checks.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Validate the PK column</h4><p><span class="mono">checkPrimaryFieldData</span>: is the primary key valid and consistent with the schema?</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>autoID? allocate : validate</h4><p>auto → <strong>allocate a globally unique PK</strong> per row and fill it in; user-supplied → check non-null/unique/type.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>PK IDs settled</h4><p>with PKs fixed, they can <strong>route to a shard</strong> (the next gate).</p></div></div>
</div>

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
    mlog.Warn(ctx, <span class="st">"check primary field data and hash primary key failed"</span>, mlog.Err(err))
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
On success the Proxy fills the returned <span class="mono">MaxTimeTick</span> back as this write's timestamp, used for session consistency (what you just wrote is readable next moment).</p>

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

<div class="flow">
  <div class="node"><div class="nt">Proxy 写入</div><div class="nd">RawAppend / AppendMessages</div></div>
  <div class="arrow">按 VChannel</div>
  <div class="node hl"><div class="nt">WAL（PChannel）</div><div class="nd">事务地追加进日志（单一事实源）</div></div>
  <div class="arrow">Read 消费</div>
  <div class="node"><div class="nt">StreamingNode flusher</div><div class="nd">Tail 日志 → growing 段 → 落盘</div></div>
</div>

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

<div class="flow">
  <div class="node hl"><div class="nt">WAL（真相）</div><div class="nd">按序追加的 insert/delete 日志</div></div>
  <div class="arrow">回放</div>
  <div class="node"><div class="nt">growing/sealed 段</div><div class="nd">攒消息、落盘成列式 binlog</div></div>
  <div class="node"><div class="nt">索引</div><div class="nd">在段上再建的加速结构</div></div>
  <div class="node"><div class="nt">QueryNode 内存</div><div class="nd">消费 WAL 得到的可检索数据</div></div>
</div>

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

<div class="flow">
  <div class="node"><div class="nt">Proxy write</div><div class="nd">RawAppend / AppendMessages</div></div>
  <div class="arrow">by VChannel</div>
  <div class="node hl"><div class="nt">WAL (PChannel)</div><div class="nd">transactionally appended to the log (single source of truth)</div></div>
  <div class="arrow">Read consume</div>
  <div class="node"><div class="nt">StreamingNode flusher</div><div class="nd">tail the log → growing segment → flush</div></div>
</div>

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

<div class="flow">
  <div class="node hl"><div class="nt">WAL (the truth)</div><div class="nd">ordered append-only insert/delete log</div></div>
  <div class="arrow">replay</div>
  <div class="node"><div class="nt">growing/sealed segments</div><div class="nd">accumulate messages, flush to columnar binlog</div></div>
  <div class="node"><div class="nt">indexes</div><div class="nd">acceleration structures built atop segments</div></div>
  <div class="node"><div class="nt">QueryNode memory</div><div class="nd">searchable data from consuming the WAL</div></div>
</div>

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

<div class="flow">
  <div class="node"><div class="nt">WAL</div><div class="nd">写入日志(单一事实源)</div></div>
  <div class="arrow">消费攒入</div>
  <div class="node hl"><div class="nt">growing 段</div><div class="nd">内存缓冲：把碎写聚成批写</div></div>
  <div class="arrow">触发→seal</div>
  <div class="node"><div class="nt">sealed 段</div><div class="nd">定型、不再改</div></div>
  <div class="arrow">flush</div>
  <div class="node"><div class="nt">binlog</div><div class="nd">大文件落对象存储</div></div>
</div>

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

<div class="flow">
  <div class="node"><div class="nt">WAL</div><div class="nd">write log (single source of truth)</div></div>
  <div class="arrow">consume &amp; buffer</div>
  <div class="node hl"><div class="nt">growing segment</div><div class="nd">memory buffer: coalesce small writes into batches</div></div>
  <div class="arrow">trigger→seal</div>
  <div class="node"><div class="nt">sealed segment</div><div class="nd">fixed, never changes</div></div>
  <div class="arrow">flush</div>
  <div class="node"><div class="nt">binlog</div><div class="nd">big files to object storage</div></div>
</div>

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

LESSON_18 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课，一个段被 flush 成了对象存储里的 binlog——但 binlog 文件<strong>里面到底长什么样</strong>？这一课我们把它<strong>掰开</strong>看：一个段在对象存储里其实不是一个文件，而是<strong>一族文件</strong>——
插入数据的 <strong>insert binlog</strong>、删除标记的 <strong>delete binlog</strong>、统计信息的 <strong>stats binlog</strong>，外加建好的<strong>索引文件</strong>。
我们会看清它们各自<strong>装什么</strong>、为什么 insert binlog 要按<strong>列</strong>而不是按<strong>行</strong>存、它们在对象存储里按怎样的<strong>路径</strong>摆放，以及这一切的序列化代码住在 <span class="mono">internal/storage</span> 的哪里。
</p>

<div class="card analogy">
  <div class="tag">📚 生活类比</div>
  把一个段想成图书馆里<strong>一个书架的藏书</strong>，binlog 就是把这批书归档进仓库的<strong>不同册子</strong>。<strong>insert binlog</strong> 是<strong>正文卷</strong>——但它不是一本本完整的书堆在一起，而是<strong>把所有书的"书名页"装订成一册、所有"作者页"装订成另一册</strong>（这就是<strong>列式</strong>：同一字段的值聚在一起）。
  <strong>delete binlog</strong> 是一张<strong>注销清单</strong>，记着"哪些书在什么时刻被划掉了"，但并不真把正文卷里的书撕掉。<strong>stats binlog</strong> 是<strong>索引卡片</strong>——记着这架书的编号范围（最小/最大主键），还夹了一张<strong>布隆过滤器</strong>做的"快速查无此书"小卡，让你不必翻遍整架就能判断"某本书<strong>大概</strong>在不在这"。
  而<strong>索引文件</strong>则是另建的<strong>检索目录</strong>，专为快速查找而生。所有这些册子，都按<strong>馆/区/架/类</strong>这样固定的编号挂在仓库的货架上——这就是对象存储里的路径布局。
</div>

<h2>一个段，一族文件：四类产物</h2>
<p>回忆上一课的 <span class="inline">SyncTask</span>：一次 flush 会生成 insertBinlogs、statsBinlogs、deltaBinlog 三类。把索引也算上，一个段在对象存储里最终对应<strong>四类产物</strong>，各装各的内容：</p>

<table class="t">
  <tr><th>产物</th><th>装什么</th><th>路径前缀</th></tr>
  <tr><td><strong>insert binlog</strong>（插入）</td><td>段里每个字段的<strong>列式</strong>数据：主键列、向量列、标量列，各自一个文件</td><td class="mono">insert_log/</td></tr>
  <tr><td><strong>delete binlog</strong>（删除）</td><td>被删除的<strong>主键 + 删除时间戳</strong>，是"注销清单"而非真正抹除</td><td class="mono">delta_log/</td></tr>
  <tr><td><strong>stats binlog</strong>（统计）</td><td>主键的 <strong>min/max</strong> 与<strong>布隆过滤器</strong>，用于快速排除"这段没有某主键"</td><td class="mono">stats_log/</td></tr>
  <tr><td><strong>index file</strong>（索引）</td><td>在 sealed 段上建的 ANN 索引结构（如 HNSW/IVF），单独建、单独存</td><td class="mono">index_files/</td></tr>
</table>

<p>这四类里，最值得先讲清的是它们的<strong>分工哲学</strong>：<strong>insert binlog 是"真身"</strong>——数据本体只此一份；<strong>delete binlog 是"叠加层"</strong>——它不修改 insert binlog，只在其上<strong>追加一层"这些主键作废了"的标记</strong>；
<strong>stats binlog 是"加速卡"</strong>——它不含原始数据，只是从数据里提炼的摘要，让查询能<strong>跳过</strong>不相关的段；<strong>index file 是"另一种视角"</strong>——同一份向量数据，换一种为快速近邻查找优化的组织方式。
这种"<strong>真身 + 叠加层 + 加速卡 + 另一种视角</strong>"的分层，正是 Milvus 把"写得快"和"读得快"解耦的微观体现：写入只管把真身和注销清单<strong>追加</strong>落盘（快），而把"整理真身、应用注销、建加速结构"留给后台慢慢做。</p>

<p>这里要特别点破 delete binlog 的"<strong>不真删</strong>"哲学。删除一行，<strong>并不会</strong>回头去 insert binlog 里把那行抹掉——对象存储里的 binlog 是<strong>只读不可变</strong>的，根本改不了。
取而代之，删除被记成 delta_log 里的一条"<strong>主键 X 在时刻 t 作废</strong>"的<strong>墓碑（tombstone）</strong>。查询时把 insert binlog 和 delete binlog <strong>叠加</strong>起来看：一行只有在"它存在且没被更晚的墓碑划掉"时才可见。
真正把墓碑<strong>物理应用</strong>、把作废的行从数据里删干净，是后台 <strong>compaction</strong> 的活（第 19 课）。删除与可见性的完整机制，留到第 20 课专门拆。</p>

<h2>stats binlog 与布隆过滤器：让查询学会"跳过"</h2>
<p>四类产物里，stats binlog 最不起眼，却是<strong>查询提速的隐形功臣</strong>。它<strong>不存原始数据</strong>，只存从这个段的主键列里提炼出的两样东西：一是主键的 <strong>min/max 区间</strong>，二是一张 <strong>布隆过滤器（Bloom filter）</strong>。
这两样东西干的是同一件事——让查询在<strong>真正打开一个段之前</strong>，就先判断"<strong>这个段里压根没有我要的主键</strong>"，从而<strong>整段跳过</strong>，省下打开 binlog、解码列、逐行比对的全部开销。在动辄成百上千个段的集合里，这种"先排除、再细查"的剪枝，是把"全表扫描"压成"只看相关几段"的关键。</p>

<p>布隆过滤器是一种<strong>概率型集合</strong>：问它"主键 X 在不在这个段里"，它只会回答两种之一——"<strong>肯定不在</strong>"或"<strong>可能在</strong>"。它<strong>绝不漏报</strong>（说不在就一定不在），但<strong>允许极小概率误报</strong>（说可能在，结果细查发现没有）。
这种"<strong>宁可多查、绝不漏查</strong>"的非对称特性，恰好契合数据库的需求：它只用来<strong>安全地排除</strong>不可能的段，绝不会因为它而漏掉真实存在的行。Milvus 的布隆过滤器实现在 <span class="mono">internal/util/bloomfilter</span>，由 <span class="inline">PrimaryKeyStats</span>（<span class="mono">internal/storage/stats.go</span>）持有，随段一起序列化进 stats binlog。
下一课讲删除路由、第 20 课讲删除与 upsert 时，你会再次见到它——一条删除消息要找到"该作废的主键到底落在哪个段"，靠的正是各段的布隆过滤器逐一筛查。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/storage/stats.go</span><span class="ln">PrimaryKeyStats：段级主键摘要（节选）</span></div>
  <pre><span class="kw">type</span> PrimaryKeyStats <span class="kw">struct</span> {
    FieldID int64                            <span class="cm">// 主键字段</span>
    MaxPk, MinPk PrimaryKey                  <span class="cm">// 主键上下界（真实 PK 边界）</span>
    BF       bloomfilter.BloomFilterInterface <span class="cm">// 布隆过滤器：快速"查无此主键"</span>
}</pre>
</div>

<p>至于 <strong>index file</strong>，它和前三者有个本质区别：前三者是 flush 时<strong>顺带</strong>产出的（写入路上就有），而索引是事后<strong>专门一步</strong>在 sealed 段上构建的（由 DataCoord 调度，回忆第 12 课）。
原因很直白：<strong>索引只能在不可变数据上建</strong>——数据还在变，建好的图/倒排就会失效。所以索引天然是"<strong>段封口之后</strong>"的产物，单独建、单独存、单独加载。一个 sealed 段因此可能有"数据 binlog + 索引文件"两套东西，查询时按需取用：有索引走索引、没索引就暴力扫 binlog。这也是为什么"新写入的数据查得稍慢、过一会儿就快了"——因为索引是落盘之后才异步建起来的，建好之前只能扫原始 binlog。</p>

<h2>为什么 insert binlog 要按列存</h2>
<p>insert binlog 最关键的设计是<strong>列式（columnar）</strong>：同一个段里，<strong>每个字段单独存成一个 binlog 文件</strong>，而不是把一整行的所有字段挨在一起存。一个段如果有"主键、向量、年龄、城市"四个字段，落盘后就是<strong>四个 insert binlog 文件</strong>，每个文件里只装那一列的连续值。</p>

<div class="cellgroup">
  <div class="cg-cap">列式布局：同一字段的值聚成一个连续的 binlog 文件（一段 = 多个列文件）</div>
  <div class="cells">
    <div class="cell hl"><span class="lab">pk</span><span class="q">101,102,103,…</span></div>
    <div class="cell"><span class="lab">vector</span><span class="q">[…],[…],[…]</span></div>
    <div class="cell"><span class="lab">age</span><span class="q">23,31,27,…</span></div>
    <div class="cell dim"><span class="lab">city</span><span class="q">"BJ","SH",…</span></div>
  </div>
</div>

<p>为什么向量数据库尤其偏爱列式？三个理由层层递进。第一，<strong>检索的访问模式是"列式"的</strong>：一次向量查询，要的是<strong>所有行的向量列</strong>去算相似度，几乎用不到同一行的其他字段。
列式布局下，向量列<strong>连续地</strong>躺在一个文件里，扫描时顺序读、缓存友好、还能<strong>整列一次性</strong>送进 SIMD/GPU 批量算距离；要是按行存，向量被其他字段<strong>切碎</strong>地夹在中间，每读一个向量都要跳着读，性能惨不忍睹。</p>

<p>第二，<strong>同列同类型，压缩率极高</strong>。一列"年龄"全是小整数、一列"城市"反复出现那几个字符串，放在一起天然有规律，用字典编码、游程编码、位压缩能压得很狠；按行存则把不同类型的值混在一起，压缩器无从下手。
第三，<strong>按需读取（列裁剪）</strong>：查询只关心某几列时，列式让你<strong>只打开需要的列文件</strong>，完全跳过其余列的 I/O。这三条加起来，决定了向量库的 binlog<strong>必然是列式</strong>——这也呼应了第 7 课讲段时埋下的"列式存储"伏笔。</p>

<p>这里还要厘清一个常见困惑：<strong>为什么同一个段、同一个字段，对象存储里往往不止一个 binlog 文件？</strong>答案藏在上一课——一个段在生命周期里会<strong>多次 flush</strong>，每次只把"<strong>这一批新攒的增量</strong>"切下来落盘。
于是同一字段会随着一次次 flush 产出一串 binlog，路径末段那个 <span class="mono">{logID}</span> 就是用来区分它们的<strong>序号</strong>。换句话说，"一个段的某一列"在物理上是<strong>一组按 logID 排开的 binlog 文件</strong>，逻辑上拼起来才是这一列的完整数据。
这正是 compaction 要登场的根本动机：随着写入持续，小 binlog 越积越多，查询要打开的文件碎片就越来越碎——必须定期把它们<strong>合并</strong>成更大、更整的文件（第 19 课）。</p>

<p>列式还带来一个容易被忽视、但对工程极其重要的好处：<strong>schema 演进友好</strong>。给集合<strong>加一个字段</strong>，在列式布局下只是"<strong>多一个列文件</strong>"，老的列文件原封不动、无需重写；要是按行存，加一列意味着每一行的物理布局都变了，历史数据几乎要全部重排。
向量库的字段动辄是几百上千维的大向量，按行重排的代价是天文数字。列式让"加列"变成一个<strong>近乎零成本</strong>的增量动作——这也是几乎所有现代分析型存储都选列式的深层原因之一。</p>

<p>底层把"一列值"序列化进文件的，是 <span class="mono">internal/storage</span> 里的 <strong>PayloadWriter</strong>（<span class="mono">NewPayloadWriter</span> 返回 <span class="inline">PayloadWriterInterface</span>）。它按字段的数据类型，把一列的值写成 Milvus 选用的列存底座（基于 <strong>Apache Arrow / Parquet</strong> 系的列式编码）。
再往上，<strong>InsertCodec</strong>（<span class="mono">data_codec.go</span>）负责把一个 <span class="inline">InsertData</span>（一段内存里的若干列）整体序列化成一批 <span class="inline">Blob</span>，每个 Blob 对应一个字段的 insert binlog；<strong>DeleteCodec</strong> 则把 <span class="inline">DeleteData</span>（主键 + 时间戳）序列化成 delta binlog。它们就是"内存数据 → binlog 文件"这一步的总入口。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/storage/data_codec.go</span><span class="ln">InsertCodec：一个段的若干列 → 一批 binlog（节选）</span></div>
  <pre><span class="cm">// Blob key 形如：</span>
<span class="cm">// ${tenant}/insert_log/${collection_id}/${partition_id}/${segment_id}/${field_id}/${log_idx}</span>
<span class="kw">type</span> InsertCodec <span class="kw">struct</span> {
    Schema *etcdpb.CollectionMeta
}

<span class="cm">// 把一段内存数据按字段序列化成多个 Blob（每个字段一个 binlog）</span>
<span class="kw">func</span> (c *InsertCodec) <span class="fn">Serialize</span>(
    partitionID, segmentID UniqueID, data ...*InsertData,
) ([]*Blob, <span class="nb">error</span>) { <span class="cm">/* 逐字段调用 PayloadWriter */</span> }</pre>
</div>

<h2>对象存储里的路径布局</h2>
<p>这些 binlog 不是平铺乱放的，而是按一条<strong>固定的层级路径</strong>挂在对象存储上，自带"我是谁的"信息。以 insert binlog 为例，它的 key 形如：</p>

<div class="layers">
  <div class="layer l-app"><span class="badge">类别</span><span class="name">insert_log</span><span class="ld">产物类型前缀：insert_log / delta_log / stats_log / index_files</span></div>
  <div class="layer l-main"><span class="badge">集合</span><span class="name">{collectionID}</span><span class="ld">属于哪个集合</span></div>
  <div class="layer l-part"><span class="badge">分区</span><span class="name">{partitionID}</span><span class="ld">属于哪个分区</span></div>
  <div class="layer l-core"><span class="badge">段</span><span class="name">{segmentID}</span><span class="ld">属于哪个段</span></div>
  <div class="layer l-core"><span class="badge">字段</span><span class="name">{fieldID}/{logID}</span><span class="ld">哪个字段的第几个 binlog（同段同字段可多个）</span></div>
</div>

<p>把这条路径读一遍，你就懂了对象存储的"<strong>自描述</strong>"之美：<span class="mono">insert_log/{collectionID}/{partitionID}/{segmentID}/{fieldID}/{logID}</span>——
光看 key 就知道"这是哪个集合、哪个分区、哪个段、哪个字段的第几个插入 binlog"，<strong>不必查元数据就能定位与归类</strong>。
这些前缀常量定义在 <span class="mono">pkg/common</span>：<span class="inline">SegmentInsertLogPath="insert_log"</span>、<span class="inline">SegmentDeltaLogPath="delta_log"</span>、<span class="inline">SegmentStatslogPath="stats_log"</span>。
delete 与 stats binlog 走相同的层级，只是把首段前缀换成 <span class="mono">delta_log</span> / <span class="mono">stats_log</span>。</p>

<p>这套路径布局还藏着一个运维上的大好处：<strong>按前缀就能批量操作</strong>。要删一个段的所有数据？删 <span class="mono">.../{segmentID}/</span> 前缀下的对象即可；要清一个集合？删 <span class="mono">.../{collectionID}/</span> 前缀即可。
后台 GC（第 19 课）正是靠这种<strong>前缀化、可枚举</strong>的布局，去识别和清理"没人认领的"孤儿对象。<strong>路径即归属</strong>——对象存储没有目录树，但这套带层级语义的 key 前缀，让它<strong>用得像一棵目录树</strong>。</p>

<p>顺带说清一个底层事实：S3、MinIO、OSS 这类对象存储，<strong>本质上是一张扁平的"键→值"大表</strong>，并<strong>没有真正的文件夹</strong>——你看到的"目录"只是按 <span class="mono">/</span> 分隔符对 key 做的<strong>前缀分组</strong>。Milvus 这套 <span class="mono">类别/集合/分区/段/字段/logID</span> 的 key 设计，正是<strong>顺着对象存储的天性</strong>来的：用结构化的 key 前缀，在扁平命名空间上"虚拟"出一棵层级树。
这也解释了为什么 Milvus 选对象存储而非传统文件系统做底座——对象存储<strong>近乎无限的容量、按需付费、天然多副本高可用</strong>，正好匹配向量库"数据大、只追加、要持久"的特点；而它"怕小文件、不能原地改"的短板，又恰好被前面讲的"<strong>批量攒成大 binlog、删除用墓碑叠加</strong>"这两招化解掉了。落盘格式与底层存储，是一对<strong>互相成就</strong>的设计。</p>

<h2>从行到 binlog：序列化的一跳</h2>
<p>把这一步连成线，你就看清了上一课 SyncTask 内部"序列化"那一格里到底发生了什么：</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>内存里的列</h4><p class="mono">InsertData</p><p>一个段攒下的若干行，已按字段组织成多列。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>逐列序列化</h4><p class="mono">PayloadWriter</p><p>每个字段一列值，写成列式编码（Arrow/Parquet 系）。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>打包成 Blob</h4><p class="mono">InsertCodec.Serialize</p><p>每字段一个 Blob = 一个 insert binlog；附 stats（含布隆）。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>按路径写对象存储</h4><p>挂到 insert_log/集合/分区/段/字段/logID。</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>回写元数据</h4><p>把 binlog 路径登记进 DataCoord 的段元信息（第 12 课）。</p></div></div>
</div>

<p>把视角拉高一层，你会发现 binlog 格式其实是 Milvus 各组件之间的<strong>通用语言</strong>。StreamingNode 的 flusher 按这个格式<strong>写</strong>，QueryNode 加载段时按这个格式<strong>读</strong>，DataNode 做 compaction 时按这个格式<strong>读改写</strong>，索引构建按这个格式<strong>读</strong>——四方互不直接通信，全靠"<strong>对同一种落盘格式的共同约定</strong>"协作。
正因如此，binlog 格式必须是<strong>自描述、可演进、向后兼容</strong>的：每个 binlog 文件头部带有事件头（event header，记录类型、时间戳范围、版本等元信息），读取方据此正确解码。这种"<strong>以稳定的磁盘格式作为组件间契约</strong>"的设计，让 Milvus 能独立升级各个组件，而不必担心新写的数据老组件读不了、或反之——这是大型存储系统能长期演进的基石。</p>

<p>最后提一句<strong>存储格式 v2</strong>。上面讲的是经典 binlog 路径（<span class="mono">internal/storage</span>，一字段一文件）。Milvus 还在演进一套更紧凑的<strong>打包列式格式</strong>——
<span class="mono">internal/storagev2</span>（packed 格式），把多列打包进更少的文件、更贴近 Parquet 的现代列存，目标是减少小文件数量、提升大列扫描效率。
你只需知道它<strong>存在且与经典 binlog 并存</strong>即可；本课的"列式 + 路径布局 + 序列化入口"这套心智模型，对两者都适用。理解了 binlog 是什么、为什么列式、怎样摆放，你就握住了 Milvus 落盘格式的总纲——下一课，我们看这些 binlog 越积越多之后，compaction 与 GC 怎样把它们整理干净。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话串起来：<strong>一个段在对象存储里对应一族文件——insert binlog（每字段一个、列式数据）、delete binlog（作废主键+时间戳的墓碑）、stats binlog（主键 min/max + 布隆过滤器）、index file（ANN 索引）</strong>。
  insert 是真身、delete 是叠加层、stats 是加速卡、index 是另一种视角。序列化由 <span class="mono">internal/storage</span> 的 <span class="inline">PayloadWriter</span> / <span class="inline">InsertCodec</span> / <span class="inline">DeleteCodec</span> 完成；路径按 <span class="mono">类别/集合/分区/段/字段/logID</span> 自描述地挂在对象存储上。更紧凑的 <span class="mono">storagev2</span> 打包格式与之并存。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>四类产物</strong>：insert binlog（列式数据）、delete binlog（墓碑：作废主键+ts）、stats binlog（min/max + 布隆）、index file（ANN 索引）。</li>
    <li><strong>列式存储</strong>：insert binlog 一字段一文件，连续存同列值——契合向量扫描、压缩率高、可列裁剪（呼应第 7 课）。</li>
    <li><strong>删除不真删</strong>：delete 记成 delta_log 墓碑，查询时叠加，物理删除留到 compaction（第 19 课）/可见性见第 20 课。</li>
    <li><strong>序列化入口</strong>：<span class="mono">internal/storage</span> 的 <span class="inline">PayloadWriter</span>（写一列）、<span class="inline">InsertCodec</span>/<span class="inline">DeleteCodec</span>（打包成 Blob）。</li>
    <li><strong>路径自描述</strong>：<span class="mono">insert_log/{collectionID}/{partitionID}/{segmentID}/{fieldID}/{logID}</span>，前缀常量在 <span class="mono">pkg/common</span>。</li>
    <li><strong>storagev2</strong>：更紧凑的打包列式格式，与经典 binlog 并存。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson a segment was flushed into binlogs in object storage — but what does a binlog file <strong>actually look like inside</strong>? This lesson <strong>cracks it open</strong>: a segment in object storage isn't one file but <strong>a family of files</strong> —
the <strong>insert binlog</strong> for the inserted data, the <strong>delete binlog</strong> for delete markers, the <strong>stats binlog</strong> for statistics, plus the built <strong>index files</strong>.
We'll see what each <strong>holds</strong>, why insert binlogs store by <strong>column</strong> rather than by <strong>row</strong>, how they are laid out by <strong>path</strong> in object storage, and where the serialization code lives in <span class="mono">internal/storage</span>.
</p>

<div class="card analogy">
  <div class="tag">📚 Analogy</div>
  Picture a segment as <strong>the holdings of one bookshelf</strong> in a library, and binlogs as the <strong>different volumes</strong> that archive this batch into the warehouse. The <strong>insert binlog</strong> is the <strong>main text</strong> — but not whole books stacked together; rather, <strong>all the "title pages" bound into one volume, all the "author pages" into another</strong> (that is <strong>columnar</strong>: values of the same field gathered together).
  The <strong>delete binlog</strong> is a <strong>cancellation list</strong> recording "which books were struck off at what moment," without actually tearing pages from the main text. The <strong>stats binlog</strong> is an <strong>index card</strong> — noting this shelf's number range (min/max primary key) and tucking in a <strong>bloom-filter</strong> "quick not-here" card, so you can judge "is a certain book <strong>probably</strong> here" without scanning the whole shelf.
  The <strong>index files</strong> are a separately-built <strong>lookup catalogue</strong>, made for fast search. All these volumes hang on the warehouse shelves by a fixed <strong>library/zone/shelf/category</strong> numbering — that is the path layout in object storage.
</div>

<h2>One segment, a family of files: four kinds of artifact</h2>
<p>Recall last lesson's <span class="inline">SyncTask</span>: one flush produces three kinds — insertBinlogs, statsBinlogs, deltaBinlog. Counting indexes too, a segment in object storage ultimately maps to <strong>four kinds of artifact</strong>, each holding its own content:</p>

<table class="t">
  <tr><th>artifact</th><th>holds</th><th>path prefix</th></tr>
  <tr><td><strong>insert binlog</strong></td><td>each field's <strong>columnar</strong> data: the PK column, vector column, scalar columns — one file each</td><td class="mono">insert_log/</td></tr>
  <tr><td><strong>delete binlog</strong></td><td>deleted <strong>primary keys + delete timestamps</strong> — a "cancellation list," not a real erase</td><td class="mono">delta_log/</td></tr>
  <tr><td><strong>stats binlog</strong></td><td>the PK <strong>min/max</strong> and a <strong>bloom filter</strong>, to quickly rule out "this segment lacks a given PK"</td><td class="mono">stats_log/</td></tr>
  <tr><td><strong>index file</strong></td><td>the ANN index built on the sealed segment (e.g. HNSW/IVF), built and stored separately</td><td class="mono">index_files/</td></tr>
</table>

<p>Among these four, the first thing to make clear is their <strong>division-of-labor philosophy</strong>: <strong>the insert binlog is the "real body"</strong> — the data itself, only one copy; <strong>the delete binlog is an "overlay"</strong> — it does not modify the insert binlog, only <strong>appends a layer of "these PKs are void" markers</strong> on top;
<strong>the stats binlog is an "acceleration card"</strong> — it holds no raw data, just a summary distilled from the data so queries can <strong>skip</strong> irrelevant segments; <strong>the index file is "another viewpoint"</strong> — the same vector data, reorganized to optimize fast nearest-neighbor search.
This layering of "<strong>real body + overlay + acceleration card + another viewpoint</strong>" is the micro-level embodiment of how Milvus decouples "writing fast" from "reading fast": writing only <strong>appends</strong> the real body and the cancellation list to disk (fast), leaving "tidying the body, applying cancellations, building accelerators" for the background to do slowly.</p>

<p>It's worth spelling out the delete binlog's "<strong>doesn't truly delete</strong>" philosophy. Deleting a row does <strong>not</strong> go back into the insert binlog to erase that row — binlogs in object storage are <strong>read-only and immutable</strong>, unchangeable by nature.
Instead, a delete is recorded as a <strong>tombstone</strong> in delta_log: "<strong>primary key X voided at time t</strong>." At query time the insert binlog and delete binlog are <strong>overlaid</strong>: a row is visible only if "it exists and isn't struck off by a later tombstone."
Actually <strong>physically applying</strong> tombstones — purging void rows from the data — is the job of background <strong>compaction</strong> (Lesson 19). The full mechanism of delete and visibility is dissected in Lesson 20.</p>

<h2>The stats binlog and bloom filter: teaching queries to "skip"</h2>
<p>Of the four artifacts, the stats binlog is the most inconspicuous, yet it's the <strong>invisible hero of query speed</strong>. It <strong>stores no raw data</strong>, only two things distilled from this segment's primary-key column: the PK's <strong>min/max range</strong>, and a <strong>bloom filter</strong>.
Both do the same job — let a query judge, <strong>before actually opening a segment</strong>, that "<strong>this segment has none of the PK I want</strong>," and thus <strong>skip the whole segment</strong>, saving all the cost of opening binlogs, decoding columns, and row-by-row comparison. In a collection with hundreds or thousands of segments, this "rule out first, examine later" pruning is the key to compressing a "full scan" down to "look at only the relevant few segments."</p>

<p>A bloom filter is a <strong>probabilistic set</strong>: ask it "is PK X in this segment," and it answers only one of two things — "<strong>definitely not</strong>" or "<strong>maybe</strong>." It <strong>never misses</strong> (if it says not present, it truly isn't), but <strong>allows a tiny chance of false positive</strong> (says maybe, then a closer look finds nothing).
This asymmetry of "<strong>rather over-check than ever miss</strong>" fits a database's need perfectly: it is used only to <strong>safely exclude</strong> impossible segments, never causing a truly-existing row to be missed. Milvus's bloom filter lives in <span class="mono">internal/util/bloomfilter</span>, held by <span class="inline">PrimaryKeyStats</span> (<span class="mono">internal/storage/stats.go</span>) and serialized into the stats binlog alongside the segment.
When the next lessons cover delete routing and Lesson 20 covers delete and upsert, you'll meet it again — a delete message finding "which segment the to-be-voided PK actually lands in" relies precisely on screening each segment's bloom filter one by one.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/storage/stats.go</span><span class="ln">PrimaryKeyStats: a segment-level PK summary (excerpt)</span></div>
  <pre><span class="kw">type</span> PrimaryKeyStats <span class="kw">struct</span> {
    FieldID int64                            <span class="cm">// the PK field</span>
    MaxPk, MinPk PrimaryKey                  <span class="cm">// real PK bounds</span>
    BF       bloomfilter.BloomFilterInterface <span class="cm">// bloom filter: quick "no such PK"</span>
}</pre>
</div>

<p>As for the <strong>index file</strong>, it differs essentially from the other three: the first three are produced <strong>incidentally</strong> at flush time (they exist on the write path), whereas the index is built later in a <strong>dedicated step</strong> on the sealed segment (scheduled by DataCoord, recall Lesson 12).
The reason is plain: <strong>an index can only be built on immutable data</strong> — if the data still changes, the built graph/inverted-list would go stale. So an index is naturally a "<strong>post-seal</strong>" product, built, stored, and loaded separately. A sealed segment may therefore have two sets of things — "data binlogs + index files" — used on demand at query time: take the index if present, brute-force scan the binlogs if not. This is also why "freshly-written data queries a bit slower, then speeds up after a while" — the index is built asynchronously only after persistence, and until it's ready the raw binlogs must be scanned.</p>

<h2>Why insert binlogs store by column</h2>
<p>The key design of insert binlogs is <strong>columnar</strong>: within one segment, <strong>each field is stored as its own binlog file</strong>, rather than packing all fields of a whole row together. If a segment has four fields "pk, vector, age, city," after persisting it becomes <strong>four insert binlog files</strong>, each holding only that one column's contiguous values.</p>

<div class="cellgroup">
  <div class="cg-cap">Columnar layout: values of one field gather into one contiguous binlog file (a segment = many column files)</div>
  <div class="cells">
    <div class="cell hl"><span class="lab">pk</span><span class="q">101,102,103,…</span></div>
    <div class="cell"><span class="lab">vector</span><span class="q">[…],[…],[…]</span></div>
    <div class="cell"><span class="lab">age</span><span class="q">23,31,27,…</span></div>
    <div class="cell dim"><span class="lab">city</span><span class="q">"BJ","SH",…</span></div>
  </div>
</div>

<p>Why do vector databases especially favor columnar? Three reasons, escalating. First, <strong>the retrieval access pattern is "columnar"</strong>: a vector query wants <strong>the vector column of all rows</strong> to compute similarity, and barely touches a row's other fields.
Under columnar layout the vector column lies <strong>contiguously</strong> in one file — sequential reads when scanning, cache-friendly, and a <strong>whole column at once</strong> can be fed into SIMD/GPU to batch-compute distances; row storage would <strong>shred</strong> vectors between other fields, forcing a jumpy read per vector — dreadful performance.</p>

<p>Second, <strong>same column, same type, excellent compression</strong>. A column of "age" all small integers, a column of "city" repeating a few strings — gathered together they have natural regularity, compressing hard with dictionary, run-length, and bit packing; row storage mixes different types together, leaving the compressor nowhere to start.
Third, <strong>read-on-demand (column pruning)</strong>: when a query cares about only a few columns, columnar lets you <strong>open just the needed column files</strong>, skipping all I/O for the rest. These three together dictate that a vector DB's binlogs <strong>must be columnar</strong> — echoing the "columnar storage" hook planted back in Lesson 7 on segments.</p>

<p>Let's also clear up a common confusion: <strong>why does the same segment and same field often have more than one binlog file in object storage?</strong> The answer hides in the last lesson — a segment <strong>flushes multiple times</strong> over its life, each time slicing off only "<strong>the new increment just accumulated</strong>" to disk.
So the same field produces a series of binlogs across successive flushes, and that <span class="mono">{logID}</span> at the path's tail is the <strong>sequence number</strong> distinguishing them. In other words, "a column of a segment" is physically <strong>a set of binlog files laid out by logID</strong>; only stitched together logically do they form this column's complete data.
That is the root motivation for compaction: as writes continue, small binlogs pile up and a query's file fragments grow ever more fragmented — they must be periodically <strong>merged</strong> into larger, tidier files (Lesson 19).</p>

<p>Columnar brings another easily-overlooked but engineering-critical benefit: <strong>schema-evolution friendliness</strong>. <strong>Adding a field</strong> to a collection is, under columnar layout, just "<strong>one more column file</strong>," leaving old column files untouched and needing no rewrite; under row storage, adding a column changes every row's physical layout, forcing nearly all historical data to be reshuffled.
A vector DB's fields are often big vectors of hundreds or thousands of dimensions, so the cost of a row-wise reshuffle is astronomical. Columnar turns "add a column" into an <strong>almost zero-cost</strong> incremental act — one of the deep reasons nearly all modern analytical stores choose columnar.</p>

<p>What serializes "a column of values" into a file underneath is the <strong>PayloadWriter</strong> in <span class="mono">internal/storage</span> (<span class="mono">NewPayloadWriter</span> returns a <span class="inline">PayloadWriterInterface</span>). By the field's data type it writes a column's values into Milvus's chosen columnar substrate (an <strong>Apache Arrow / Parquet</strong>-family columnar encoding).
Above it, the <strong>InsertCodec</strong> (<span class="mono">data_codec.go</span>) serializes a whole <span class="inline">InsertData</span> (several in-memory columns of a segment) into a batch of <span class="inline">Blob</span>s, each Blob one field's insert binlog; the <strong>DeleteCodec</strong> serializes <span class="inline">DeleteData</span> (PKs + timestamps) into a delta binlog. They are the entry point of the "in-memory data → binlog file" step.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/storage/data_codec.go</span><span class="ln">InsertCodec: a segment's columns → a batch of binlogs (excerpt)</span></div>
  <pre><span class="cm">// Blob key looks like:</span>
<span class="cm">// ${tenant}/insert_log/${collection_id}/${partition_id}/${segment_id}/${field_id}/${log_idx}</span>
<span class="kw">type</span> InsertCodec <span class="kw">struct</span> {
    Schema *etcdpb.CollectionMeta
}

<span class="cm">// serialize a segment's in-memory data into multiple Blobs (one binlog per field)</span>
<span class="kw">func</span> (c *InsertCodec) <span class="fn">Serialize</span>(
    partitionID, segmentID UniqueID, data ...*InsertData,
) ([]*Blob, <span class="nb">error</span>) { <span class="cm">/* call PayloadWriter per field */</span> }</pre>
</div>

<h2>The path layout in object storage</h2>
<p>These binlogs aren't dumped flat; they hang in object storage by a <strong>fixed hierarchical path</strong> that carries "whose I am" info. Take an insert binlog: its key looks like:</p>

<div class="layers">
  <div class="layer l-app"><span class="badge">kind</span><span class="name">insert_log</span><span class="ld">artifact-type prefix: insert_log / delta_log / stats_log / index_files</span></div>
  <div class="layer l-main"><span class="badge">collection</span><span class="name">{collectionID}</span><span class="ld">which collection</span></div>
  <div class="layer l-part"><span class="badge">partition</span><span class="name">{partitionID}</span><span class="ld">which partition</span></div>
  <div class="layer l-core"><span class="badge">segment</span><span class="name">{segmentID}</span><span class="ld">which segment</span></div>
  <div class="layer l-core"><span class="badge">field</span><span class="name">{fieldID}/{logID}</span><span class="ld">which field's which binlog (same segment+field may have several)</span></div>
</div>

<p>Read this path and you grasp the "<strong>self-describing</strong>" beauty of object storage: <span class="mono">insert_log/{collectionID}/{partitionID}/{segmentID}/{fieldID}/{logID}</span> —
the key alone tells you "which collection, partition, segment, and field, and which insert binlog of that field," so you can <strong>locate and classify it without consulting metadata</strong>.
These prefix constants are defined in <span class="mono">pkg/common</span>: <span class="inline">SegmentInsertLogPath="insert_log"</span>, <span class="inline">SegmentDeltaLogPath="delta_log"</span>, <span class="inline">SegmentStatslogPath="stats_log"</span>.
Delete and stats binlogs follow the same hierarchy, only swapping the leading prefix to <span class="mono">delta_log</span> / <span class="mono">stats_log</span>.</p>

<p>This path layout hides a big operational benefit too: <strong>batch operations by prefix</strong>. Delete all of a segment's data? Delete objects under the <span class="mono">.../{segmentID}/</span> prefix. Clear a collection? Delete the <span class="mono">.../{collectionID}/</span> prefix.
Background GC (Lesson 19) relies on exactly this <strong>prefixed, enumerable</strong> layout to identify and clean "unclaimed" orphan objects. <strong>Path is ownership</strong> — object storage has no directory tree, but these hierarchy-bearing key prefixes let it <strong>be used like one</strong>.</p>

<p>Let's spell out an underlying fact: object stores like S3, MinIO, and OSS are <strong>essentially one flat "key→value" big table</strong>, with <strong>no real folders</strong> — the "directories" you see are just <strong>prefix grouping</strong> of keys by the <span class="mono">/</span> separator. Milvus's <span class="mono">kind/collection/partition/segment/field/logID</span> key design goes precisely <strong>with the grain of object storage</strong>: structured key prefixes "virtualize" a hierarchy tree over a flat namespace.
This also explains why Milvus chose object storage rather than a traditional filesystem as its substrate — object storage's <strong>near-infinite capacity, pay-as-you-go, and built-in multi-replica high availability</strong> match a vector DB's traits of "big data, append-only, must persist"; and its weaknesses of "fears small files, can't update in place" are dissolved exactly by the two moves above — "<strong>batch-accumulate into big binlogs, and overlay deletes as tombstones</strong>." The persistence format and the underlying storage are a pair of designs that <strong>make each other work</strong>.</p>

<h2>From rows to binlog: the serialization hop</h2>
<p>String this step into a line and you see what really happens inside last lesson's "serialize" cell of the SyncTask:</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>columns in memory</h4><p class="mono">InsertData</p><p>the rows a segment accumulated, organized into columns by field.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>serialize per column</h4><p class="mono">PayloadWriter</p><p>each field's column of values written in columnar encoding (Arrow/Parquet-family).</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>pack into Blobs</h4><p class="mono">InsertCodec.Serialize</p><p>one Blob per field = one insert binlog; plus stats (with bloom).</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>write to object storage by path</h4><p>hang at insert_log/collection/partition/segment/field/logID.</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>write back metadata</h4><p>register binlog paths into DataCoord's segment meta (Lesson 12).</p></div></div>
</div>

<p>Zoom out a level and you see the binlog format is really the <strong>common language</strong> among Milvus's components. The StreamingNode's flusher <strong>writes</strong> in this format, the QueryNode <strong>reads</strong> it when loading a segment, the DataNode <strong>reads-and-rewrites</strong> it during compaction, index building <strong>reads</strong> it — the four never talk directly, cooperating entirely through "<strong>a shared agreement on one persistence format</strong>."
For exactly this reason the binlog format must be <strong>self-describing, evolvable, and backward-compatible</strong>: each binlog file carries an event header (recording type, timestamp range, version and other metadata) by which the reader decodes correctly. This design of "<strong>a stable on-disk format as the contract between components</strong>" lets Milvus upgrade each component independently, without fearing that newly-written data can't be read by old components or vice versa — the bedrock on which a large storage system evolves over time.</p>

<p>Finally, a word on <strong>storage format v2</strong>. The above is the classic binlog layout (<span class="mono">internal/storage</span>, one file per field). Milvus is also evolving a more compact <strong>packed columnar format</strong> —
<span class="mono">internal/storagev2</span> (the packed format), bundling multiple columns into fewer files, closer to modern Parquet columnar storage, aiming to cut the number of small files and improve large-column scan efficiency.
You only need to know it <strong>exists and coexists with classic binlogs</strong>; this lesson's mental model of "columnar + path layout + serialization entry" applies to both. Understand what a binlog is, why columnar, and how it's laid out, and you hold the master outline of Milvus's persistence format — next lesson, we see how compaction and GC tidy these binlogs once they pile up.</p>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>a segment in object storage maps to a family of files — insert binlogs (one per field, columnar data), a delete binlog (tombstones of void PK + timestamp), a stats binlog (PK min/max + bloom filter), and index files (the ANN index)</strong>.
  Insert is the real body, delete an overlay, stats an acceleration card, index another viewpoint. Serialization is done by <span class="mono">internal/storage</span>'s <span class="inline">PayloadWriter</span> / <span class="inline">InsertCodec</span> / <span class="inline">DeleteCodec</span>; paths hang self-describingly as <span class="mono">kind/collection/partition/segment/field/logID</span>. The more compact <span class="mono">storagev2</span> packed format coexists with it.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Four artifacts</strong>: insert binlog (columnar data), delete binlog (tombstone: void PK + ts), stats binlog (min/max + bloom), index file (ANN index).</li>
    <li><strong>Columnar storage</strong>: insert binlog is one file per field, contiguous values of one column — fits vector scans, compresses well, allows column pruning (echoes Lesson 7).</li>
    <li><strong>Deletes don't truly delete</strong>: a delete is a delta_log tombstone, overlaid at query time; physical removal waits for compaction (Lesson 19) / visibility in Lesson 20.</li>
    <li><strong>Serialization entry</strong>: <span class="mono">internal/storage</span>'s <span class="inline">PayloadWriter</span> (writes a column), <span class="inline">InsertCodec</span>/<span class="inline">DeleteCodec</span> (pack into Blobs).</li>
    <li><strong>Self-describing paths</strong>: <span class="mono">insert_log/{collectionID}/{partitionID}/{segmentID}/{fieldID}/{logID}</span>, prefix constants in <span class="mono">pkg/common</span>.</li>
    <li><strong>storagev2</strong>: a more compact packed columnar format, coexisting with classic binlogs.</li>
  </ul>
</div>
""",
}

LESSON_19 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课我们看清了 binlog 的样子，也埋下了两颗"麻烦的种子"：一是写入<strong>越攒越多的小 binlog</strong>（每次 flush 切一刀，碎片越积越碎），二是删除<strong>只记墓碑、从不真删</strong>（delta_log 里的作废标记越堆越厚）。
这一课讲 Milvus 的两位"<strong>后台清洁工</strong>"：<strong>compaction（合并整理）</strong>把碎小的段合并成更大更干净的段、并把墓碑<strong>物理应用</strong>掉；<strong>GC（垃圾回收）</strong>则把没人认领的<strong>孤儿对象</strong>从对象存储里清走。
我们会看清它们各自<strong>解决什么问题</strong>、有哪几种 compaction 类型、谁<strong>调度</strong>谁<strong>执行</strong>，以及代码住在 <span class="mono">internal/datacoord</span> 的哪里。
</p>

<div class="card analogy">
  <div class="tag">📚 生活类比</div>
  还记得上一课那个"一架书 = 一族册子"的图书馆吗？写入久了，仓库里会出现两种乱象：<strong>一是同一架书被拆成几十本薄薄的小册子</strong>（每次只归档一点新书），翻一架要开几十本；<strong>二是注销清单越积越长</strong>，可被划掉的书还原封不动占着架位。
  <strong>compaction</strong> 就是定期来的<strong>整理员</strong>：他把同一架的薄册子<strong>合订成几本厚书</strong>、顺手<strong>按注销清单把作废的书真正抽走</strong>、还能<strong>按主题重新归类</strong>让相近的书挨在一起——整理完，找书的人开的册子更少、读到的全是有效的书。
  <strong>GC</strong> 则是仓库的<strong>清运工</strong>：整理员合订完，旧的薄册子就没人认领了；清运工<strong>等过了规定时限</strong>，确认真没人再用，才把这些孤儿箱子拉去销毁，腾出货架。两人分工：整理员让<strong>读得快</strong>，清运工让<strong>存得省</strong>。
</div>

<h2>为什么需要 compaction：从碎片到整洁</h2>
<p>compaction 的动机，正是上一课结尾埋下的两个伏笔。第一，<strong>小文件碎片化</strong>：一个段会多次 flush，同一字段产出一串按 logID 排开的小 binlog；一个集合里又有成百上千个段。查询要打开的文件越碎，<strong>元数据开销、随机 I/O、解码次数</strong>就越多——这对"怕小文件"的对象存储尤其致命。
第二，<strong>墓碑累积</strong>：删除只在 delta_log 里追加"主键 X 在 t 作废"，被删的行仍躺在 insert binlog 里。墓碑越堆越多，查询每读一行都要<strong>叠加比对一遍删除集</strong>，又慢又占内存。compaction 把这两件事一并解决：<strong>合并碎片 + 应用墓碑</strong>。</p>

<div class="timeline">
  <div class="lane"><span class="lane-label">整理前</span><span class="tslot">段A（小）</span><span class="tslot">段B（小）</span><span class="tslot">段C（小）</span><span class="tslot span">+ 一堆 delta 墓碑</span></div>
  <div class="lane"><span class="lane-label">compaction</span><span class="tslot now">合并 + 物理删除作废行</span></div>
  <div class="lane"><span class="lane-label">整理后</span><span class="tslot now">段D（大·干净·无墓碑）</span></div>
</div>

<p>整理之后的收益是<strong>实打实的读效率</strong>：要打开的段更少、每段更大更连续（顺序 I/O 更友好）、墓碑已被清掉（不必再叠加比对）、数据更适合建索引。
换句话说，compaction 是 Milvus"<strong>写得快、读得快</strong>"这对矛盾的<strong>调和器</strong>——写入只管<strong>追加</strong>（快但碎、带墓碑），把"整理成利于读的样子"这件慢活，留给后台在系统空闲时慢慢做。这也是典型的 <strong>LSM 式</strong>思路：先快速追加写，再后台归并整理。</p>

<p>这里值得把一个权衡想透：既然 compaction 终归要把数据<strong>重写一遍</strong>，为什么不在写入那一刻就直接写成大段、一步到位？答案藏在"<strong>写放大</strong>"与"<strong>写入延迟</strong>"的取舍里。
如果要求写入时就把数据整理得井井有条，那么每来一小批数据，都得读出已有的大段、和新数据归并、再整段重写——一次小写入会触发一次大重写，<strong>写放大</strong>会爆炸，写入延迟也会被拖到不可接受。
Milvus 的选择是把这两件事<strong>解耦</strong>：写入路径只做"追加小段"这一件极快的事，<strong>保证写入低延迟、高吞吐</strong>；而"整理成大段"则攒够一批后，在后台<strong>批量地、摊销地</strong>做一次。同样一份重写代价，摊到成千上万次写入头上，<strong>单次写入几乎不受影响</strong>。这正是 LSM 类系统的精髓：<strong>用后台的批量整理，换前台的写入速度</strong>。</p>

<p>还要补一句 compaction 的<strong>节流哲学</strong>：它是一项"<strong>能省则省、可缓则缓</strong>"的后台任务。DataCoord 不会为一点点碎片就立刻触发，而是按段的大小、小文件数量、墓碑比例等设阈值，<strong>攒到划算了才合</strong>；执行时也受<strong>并发度</strong>限制，避免后台整理抢占了前台读写的资源。
这种"<strong>不打扰主链路</strong>"的克制，是后台维护任务的通用准则——它服务于读写，却绝不能反过来拖垮读写。理解了这层取舍，你就明白为什么 compaction 总是"<strong>慢半拍</strong>"地在背后默默进行，而不是争分夺秒地追着每一次写入跑。</p>

<h2>几种 compaction：各自整理什么</h2>
<p>compaction 不是只有一种。DataCoord 会根据不同的<strong>触发条件</strong>，调度不同<strong>类型</strong>的 compaction，每种干一类活。它们的类型枚举定义在 proto 的 <span class="inline">datapb.CompactionType</span> 里：</p>

<table class="t">
  <tr><th>类型</th><th>触发动机</th><th>整理效果</th></tr>
  <tr><td><strong>MixCompaction</strong></td><td>同一段攒了太多小 binlog / 碎片</td><td>把碎小 binlog <strong>合并</strong>成更大更整的段（最常见）</td></tr>
  <tr><td><strong>MergeCompaction</strong></td><td>多个未满的小段需要拼合</td><td>把若干小段<strong>合并</strong>成一个更大的段</td></tr>
  <tr><td><strong>Level0DeleteCompaction</strong></td><td>L0 删除数据（墓碑）累积</td><td>把 L0 墓碑<strong>物理应用</strong>进对应的 sealed 段</td></tr>
  <tr><td><strong>ClusteringCompaction</strong></td><td>按<strong>聚类键</strong>重组以提升检索局部性</td><td>把数据<strong>按聚类键重新分桶</strong>，相近数据聚在一起</td></tr>
  <tr><td><strong>SortCompaction</strong></td><td>需要按主键有序以加速查找</td><td>把段内数据<strong>按主键排序</strong>后重写</td></tr>
</table>

<p>把这张表读一遍，你会发现这几种 compaction 大致分成两阵营：<strong>Mix 与 Merge 是"合并派"</strong>——核心目标是把<strong>碎、散、小</strong>的段拼成<strong>大而整</strong>的段，顺带应用普通墓碑，是日常最频繁触发的一类；
<strong>Clustering 与 Sort 是"重排派"</strong>——它们在合并之外，还<strong>主动调整数据的物理顺序</strong>以提升读效率（详见下一节）；<strong>Level0DeleteCompaction 则自成一类</strong>，专司"把悬空的删除真正落到段上"。
理解它们的分野，关键不在记住每个名字，而在抓住一条主线：<strong>所有 compaction 都是在为"读"服务</strong>——要么让段更少更整、要么让墓碑清干净、要么让数据排得更利于剪枝。</p>

<p>这里最值得单独点破的是 <strong>Level0DeleteCompaction</strong>，它是上一课"删除不真删"那句话的<strong>下半场</strong>。删除消息先被缓冲成<strong>第零层（Level-0）</strong>的删除数据——一批只含"作废主键 + 时间戳"的 deltalog，<strong>尚未落到具体的 sealed 段上</strong>，像一层悬在所有段之上的"待应用删除"。
Level0DeleteCompaction 干的就是把这层 L0 墓碑<strong>真正下沉、应用</strong>到它们各自该作用的 sealed 段里，让被删的行在物理上消失。DataCoord 维护着一个 <strong>L0 删除视图</strong>（<span class="mono">internal/datacoord/compaction_l0_view.go</span> 的 <span class="inline">LevelZeroCompactionView</span>）来追踪"哪些 L0 墓碑该和哪些段做这桩合并"。删除的完整可见性机制，下一课专门拆。</p>

<div class="cellgroup">
  <div class="cg-cap">Level0DeleteCompaction：把悬在上方的 L0 墓碑下沉、应用进 sealed 段</div>
  <div class="cells">
    <div class="cell hl"><span class="lab">L0 墓碑</span><span class="q">pk=102@t9 · pk=205@t9</span></div>
    <div class="cell sep"><span class="lab">↓ 应用</span><span class="q">路由到含此 pk 的段</span></div>
    <div class="cell dim"><span class="lab">段（整理后）</span><span class="q">102/205 行已物理删除</span></div>
  </div>
</div>

<h2>谁调度、谁执行</h2>
<p>在进入分工之前，先把 <strong>ClusteringCompaction</strong> 与 <strong>SortCompaction</strong> 这两类"<strong>不只是合并、还要重排</strong>"的 compaction 说透，因为它们直接服务于<strong>读得更快</strong>。普通的 Mix/Merge 只把碎片拼大、把墓碑应用掉，<strong>不改变数据的排列顺序</strong>；而 Clustering 与 Sort 则会<strong>主动重组段内数据的物理顺序</strong>，让后续查询能跳过更多无关数据。</p>

<p><strong>ClusteringCompaction（按聚类键重组）</strong>的思路是：给集合指定一个<strong>聚类键</strong>（比如"地区""类别"），compaction 时把数据<strong>按这个键重新分桶</strong>，让"同一类"的数据聚到相邻的段里。
这样一来，带过滤条件的查询（如"只查华东地区")就能凭段级的 <strong>min/max 统计</strong>（回忆上一课的 stats binlog）<strong>整段跳过</strong>不相关的桶，只扫真正命中的几段——这正是数据库里"<strong>数据局部性</strong>"的威力：把经常一起被查的数据在物理上摆到一起，查询的剪枝率就越高。
<strong>SortCompaction（按主键排序）</strong>则把段内数据<strong>按主键有序</strong>地重写，让按主键的点查、范围查与去重都更高效；有序的数据还能让 min/max 区间更紧致、布隆判定更省力。两者的共同点是：它们用一次后台重写的代价，<strong>预先把数据摆成利于读的形状</strong>，把代价从"每次查询"提前摊销到了"一次整理"。</p>

<p>compaction 的分工，又一次印证了"<strong>协调器管调度、节点管执行</strong>"的主旋律（第 9 课）。<strong>DataCoord</strong> 是大脑：它扫描段的元数据、按各种 compaction 策略（<span class="mono">compaction_policy_*</span>）判断"哪些段该合、该做哪种 compaction"，生成 compaction 任务并入队、分派。
真正干重活——读旧 binlog、合并、应用墓碑、写出新 binlog——的，是 <strong>datanode 上的 compaction worker</strong>。这也正是<strong>第 17 课</strong>说的"DataNode 当下的主要职责就是 compaction"：流式写入已交给 StreamingNode，DataNode 退居幕后，专注做这桩后台整理。</p>

<div class="flow">
  <div class="node hl"><div class="nt">DataCoord</div><div class="nd">扫元数据 · 选策略 · 生成任务</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">compaction 队列</div><div class="nd">按优先级排队 · 分派</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">datanode worker</div><div class="nd">读旧 binlog · 合并 · 应用墓碑 · 写新 binlog</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">回写元数据</div><div class="nd">新段上线 · 旧段标记 dropped</div></div>
</div>

<p>完成后有一个关键动作：worker 写出新段，DataCoord <strong>原子地</strong>把元数据从"旧的若干小段"切换到"新的大段"，新段上线供查询，旧段被<strong>标记为 dropped</strong>。
这一步必须是<strong>原子</strong>的，意义重大：它保证任何查询在任意时刻看到的，要么是<strong>整批旧段</strong>、要么是<strong>那个新段</strong>，绝不会出现"新旧段同时可见、同一行被数到两遍"或"旧段已撤、新段未上、数据凭空消失"的中间态。正是这条"<strong>元数据切换原子化</strong>"的保证，让 compaction 这桩"在后台悄悄换掉数据"的大手术，对前台查询<strong>完全透明、毫无感知</strong>。
注意——此刻旧段的 binlog <strong>还躺在对象存储里没被删</strong>，只是元数据上不再被引用了。把这些"已 dropped、没人引用"的物理文件真正清走，是另一位清洁工 GC 的活。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">pkg/proto/datapb/data_coord.pb.go</span><span class="ln">CompactionType：compaction 类型枚举（节选）</span></div>
  <pre><span class="cm">// milvus-proto/go-api 生成；datacoord 据此调度对应类型</span>
<span class="kw">const</span> (
    CompactionType_MergeCompaction         CompactionType = <span class="nb">2</span>
    CompactionType_MixCompaction           CompactionType = <span class="nb">3</span>
    CompactionType_Level0DeleteCompaction  CompactionType = <span class="nb">7</span> <span class="cm">// 应用 L0 墓碑</span>
    CompactionType_ClusteringCompaction    CompactionType = <span class="nb">8</span> <span class="cm">// 按聚类键重组</span>
    CompactionType_SortCompaction          CompactionType = <span class="nb">9</span> <span class="cm">// 按主键排序</span>
)</pre>
</div>

<h2>GC：清走无主的孤儿对象</h2>
<p>compaction 制造了一批"逻辑上已废弃、物理上还在"的旧 binlog；删表、删分区、删段也会留下大量不再被引用的对象。<strong>GC（garbage collector）</strong>就是负责回收这些<strong>孤儿对象</strong>的后台循环，代码在 <span class="mono">internal/datacoord/garbage_collector.go</span>。
它周期性地扫描对象存储里的 binlog，对照元数据判断"<strong>这个对象还有没有被任何活段引用</strong>"；对那些<strong>已 dropped 的段</strong>或<strong>谁都不认领的孤儿文件</strong>，把它们从对象存储里删掉。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>扫描与比对</h4><p class="mono">recycleUnusedBinlogFiles</p><p>枚举对象存储里的 binlog，对照元数据找出"没有活段引用"的孤儿。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>处理 dropped 段</h4><p class="mono">recycleDroppedSegments</p><p>对已标记 dropped 的段，回收其全部 binlog（insert/delta/stats）。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>过 TTL 才删</h4><p>只删<strong>超过保留期（TTL）</strong>的对象，给在途读取与回滚留出安全窗口。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>物理删除</h4><p>按对象存储的前缀批量删，真正释放空间。</p></div></div>
</div>

<p>GC 设计里最关键的一个安全阀是 <strong>TTL（保留期）</strong>：它<strong>绝不</strong>在对象一变成孤儿的瞬间就删。原因是分布式系统里存在各种"<strong>时间差</strong>"——某个 QueryNode 可能还在读刚被 compaction 替换掉的旧段、某个操作可能需要回滚。
只删"<strong>已经孤儿超过 TTL</strong>"的对象，等于给所有在途的引用留出一个<strong>安全窗口</strong>，宁可让垃圾多躺一会儿，也绝不误删还在被用的数据。这正呼应上一课讲的：对象存储的<strong>前缀化、可枚举</strong>布局，让 GC 能高效地按段、按集合前缀去枚举和清理。</p>

<p>值得停下来想清楚：对象存储里的"<strong>孤儿</strong>"到底从哪来？它们的来源比想象中多。<strong>compaction</strong> 替换掉的旧段是最大一类——一次合并就批量制造一堆"已 dropped、待回收"的旧 binlog；
<strong>删除集合 / 分区 / 段</strong>的 DDL 会让大片对象瞬间失去引用；<strong>失败或超时的 flush、compaction、建索引任务</strong>可能写了一半就中断，留下"写了文件、却没登记进元数据"的<strong>半成品孤儿</strong>；
甚至<strong>元数据回滚</strong>也会让某些已落盘的对象变成无人认领。GC 的判定逻辑因此不能只看"文件在不在"，而要<strong>以元数据为准绳</strong>反向核对：凡是对象存储里有、但<strong>活段元数据里查不到引用</strong>的，就是孤儿候选。这是一种典型的"<strong>以权威元数据为真，物理存储向其对齐</strong>"的回收思路——元数据说不再需要，物理文件才可以被清。</p>

<p>这里也藏着一个常见的<strong>认知误区</strong>需要澄清：删除（delete）<strong>不会</strong>立刻让数据从对象存储消失，DDL 级的"删段"也只是先把段<strong>标记为 dropped</strong>。真正的物理空间释放，<strong>永远是 GC 在 TTL 之后异步完成的</strong>。
所以你删了一批数据、却发现对象存储占用没有立刻下降，这并不是 bug，而是这套"<strong>逻辑作废与物理回收分离</strong>"设计的<strong>正常表现</strong>——它用一点点存储上的延迟，换来了删除操作的<strong>低延迟、可回滚、对在途读取友好</strong>。理解了这一点，你也就理解了 Milvus 整条写入链路反复出现的同一种智慧：<strong>把"快速记账"和"慢慢清算"解耦开</strong>。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/datacoord/garbage_collector.go</span><span class="ln">garbageCollector：回收孤儿与 dropped 段（节选）</span></div>
  <pre><span class="kw">type</span> garbageCollector <span class="kw">struct</span> {
    meta    *meta
    handler Handler
    option  GcOption <span class="cm">// 含 TTL 等保留策略</span>
}

<span class="cm">// 后台循环：清理无引用的 binlog 与 dropped 段</span>
<span class="kw">func</span> (gc *garbageCollector) <span class="fn">recycleUnusedBinlogFiles</span>(ctx context.Context) { <span class="cm">/* 枚举·比对·过 TTL·删 */</span> }
<span class="kw">func</span> (gc *garbageCollector) <span class="fn">recycleDroppedSegments</span>(ctx context.Context, signal &lt;-<span class="kw">chan</span> gcCmd) { <span class="cm">/* 回收 dropped 段全部 binlog */</span> }</pre>
</div>

<p>把 compaction 与 GC 连起来看，它们是一前一后的<strong>接力</strong>：compaction 把"碎、脏"的数据重写成"整、净"的新段，并把旧段<strong>逻辑上</strong>作废；GC 在 TTL 之后把这些旧段<strong>物理上</strong>清走。
前者优化<strong>读</strong>（更少更干净的段）、后者优化<strong>存</strong>（不为废弃数据持续付费）。两者都由 <strong>DataCoord 调度</strong>，是 Milvus 写入链路"<strong>写完之后</strong>"那段静默却至关重要的自我维护——没有它们，系统会被小文件和墓碑慢慢拖垮，查询会越来越慢、存储会越用越胀。可以说，这两位后台清洁工虽不在写入与查询的主舞台上，却是让 Milvus 能<strong>长期稳定运行</strong>的幕后基石。下一课，我们正式拆开"删除与 upsert"，看墓碑、布隆过滤器与 MVCC 时间戳如何共同决定"一行到底可不可见"。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：写入只管<strong>快速追加</strong>，留下<strong>小文件碎片</strong>与<strong>删除墓碑</strong>两笔"技术债"，由两位后台清洁工偿还——<strong>compaction</strong>（DataCoord 调度、datanode worker 执行）把碎段<strong>合并</strong>、把 L0 墓碑<strong>物理应用</strong>（<span class="inline">datapb.CompactionType_Level0DeleteCompaction</span>），还可按聚类键重组（Clustering）、按主键排序（Sort）；<strong>GC</strong>（<span class="mono">garbage_collector.go</span>）在 <strong>TTL</strong> 之后清走<strong>孤儿与 dropped 段</strong>的对象。前者让读更快，后者让存更省。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>两笔技术债</strong>：多次 flush 留下的小文件碎片 + 删除只记的墓碑，由 compaction 与 GC 偿还。</li>
    <li><strong>compaction 类型</strong>：MixCompaction/MergeCompaction（合并碎段）、Level0DeleteCompaction（物理应用 L0 墓碑）、ClusteringCompaction（按聚类键重组）、SortCompaction（按主键排序）。</li>
    <li><strong>调度 vs 执行</strong>：DataCoord 选策略、生成任务；datanode worker 读旧 binlog、合并、写新段（呼应第 17 课）。</li>
    <li><strong>Level-0 删除</strong>：删除先缓冲为 L0 墓碑，<span class="mono">compaction_l0_view.go</span> 追踪，Level0DeleteCompaction 才把它物理应用进段（第 20 课展开）。</li>
    <li><strong>GC 与 TTL</strong>：<span class="mono">garbage_collector.go</span> 回收孤儿/ dropped 段对象，只删超过 TTL 者，给在途引用留安全窗口。</li>
    <li><strong>分工</strong>：compaction 优化读、GC 优化存，二者都由 DataCoord 调度。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson we saw what a binlog looks like, and planted two "troublesome seeds": one, writes accumulate <strong>ever more small binlogs</strong> (each flush slices off a fragment, piling up shards); two, deletes <strong>only record tombstones, never truly erase</strong> (the void markers in delta_log keep stacking up).
This lesson covers Milvus's two <strong>background janitors</strong>: <strong>compaction</strong> merges fragmented segments into larger, cleaner ones and <strong>physically applies</strong> tombstones; <strong>GC</strong> sweeps unclaimed <strong>orphan objects</strong> out of object storage.
We'll see what each <strong>solves</strong>, the kinds of compaction, who <strong>schedules</strong> and who <strong>executes</strong>, and where the code lives in <span class="mono">internal/datacoord</span>.
</p>

<div class="card analogy">
  <div class="tag">📚 Analogy</div>
  Remember last lesson's library, "one bookshelf = a family of volumes"? After a while, two messes appear in the warehouse: <strong>one, a single shelf gets split into dozens of thin pamphlets</strong> (each archives just a little new stock), so reading one shelf means opening dozens; <strong>two, the cancellation list keeps growing</strong>, yet the struck-off books still sit on the shelf untouched.
  <strong>Compaction</strong> is the <strong>tidying clerk</strong> who comes periodically: he <strong>binds the thin pamphlets of one shelf into a few thick volumes</strong>, <strong>actually pulls out the void books per the cancellation list</strong>, and can even <strong>re-shelve by topic</strong> so similar books sit together — afterward, a reader opens fewer volumes and reads only valid books.
  <strong>GC</strong> is the warehouse's <strong>hauler</strong>: once the clerk finishes binding, the old thin pamphlets are unclaimed; the hauler <strong>waits past a set deadline</strong>, confirms no one uses them, then carts these orphan boxes off for destruction, freeing shelf space. Division of labor: the clerk makes <strong>reads fast</strong>, the hauler makes <strong>storage cheap</strong>.
</div>

<h2>Why compaction is needed: from fragments to tidiness</h2>
<p>Compaction's motivation is exactly the two hooks planted at last lesson's end. First, <strong>small-file fragmentation</strong>: a segment flushes many times, producing a string of small binlogs by logID per field; and a collection has hundreds or thousands of segments. The more fragmented the files a query must open, the more <strong>metadata overhead, random I/O, and decode passes</strong> — especially fatal for object storage, which "fears small files."
Second, <strong>tombstone buildup</strong>: a delete only appends "PK X voided at t" into delta_log, while the deleted row still sits in the insert binlog. As tombstones stack up, every row read must <strong>overlay-compare against the delete set</strong> — slow and memory-hungry. Compaction solves both at once: <strong>merge fragments + apply tombstones</strong>.</p>

<div class="timeline">
  <div class="lane"><span class="lane-label">before</span><span class="tslot">seg A (small)</span><span class="tslot">seg B (small)</span><span class="tslot">seg C (small)</span><span class="tslot span">+ a pile of delta tombstones</span></div>
  <div class="lane"><span class="lane-label">compaction</span><span class="tslot now">merge + physically delete void rows</span></div>
  <div class="lane"><span class="lane-label">after</span><span class="tslot now">seg D (large · clean · no tombstones)</span></div>
</div>

<p>The payoff after tidying is <strong>real read efficiency</strong>: fewer segments to open, each larger and more contiguous (friendlier sequential I/O), tombstones already cleared (no more overlay-compare), and data better-suited to indexing.
In other words, compaction is the <strong>reconciler</strong> of Milvus's "write fast vs read fast" tension — writing only <strong>appends</strong> (fast but fragmented, with tombstones), leaving the slow work of "reshaping into a read-friendly form" for the background to do when the system is idle. This is the classic <strong>LSM-style</strong> idea: append fast, merge-and-tidy in the background.</p>

<p>It's worth thinking through one tradeoff: since compaction will eventually <strong>rewrite</strong> the data anyway, why not write large, tidy segments directly at write time, in one shot? The answer hides in the tradeoff between "<strong>write amplification</strong>" and "<strong>write latency</strong>."
If writes had to keep data perfectly tidy, then every small batch arriving would have to read the existing big segment, merge with the new data, and rewrite the whole segment — one small write triggering one big rewrite, making <strong>write amplification</strong> explode and write latency unacceptable.
Milvus's choice is to <strong>decouple</strong> the two: the write path does only the very fast thing of "appending small segments," <strong>guaranteeing low-latency, high-throughput writes</strong>; while "reshaping into big segments" is done once in the background, <strong>in batches, amortized</strong>, after enough has accumulated. The same rewrite cost, spread across thousands of writes, leaves <strong>each individual write almost unaffected</strong>. This is the essence of LSM-class systems: <strong>trade background batch-tidying for foreground write speed</strong>.</p>

<p>One more note on compaction's <strong>throttling philosophy</strong>: it is a background task that "<strong>saves where it can, defers where it may</strong>." DataCoord won't trigger immediately for a little fragmentation, but sets thresholds by segment size, small-file count, tombstone ratio, and so on, <strong>merging only when it's worthwhile</strong>; execution is also bounded by <strong>concurrency</strong>, lest background tidying steal resources from foreground reads and writes.
This restraint of "<strong>don't disturb the main path</strong>" is a general rule for background maintenance — it serves reads and writes, but must never drag them down in return. Grasp this tradeoff and you understand why compaction always proceeds quietly "<strong>a beat behind</strong>" in the background, rather than racing to chase every single write.</p>

<h2>Kinds of compaction: what each tidies</h2>
<p>Compaction isn't a single thing. DataCoord, by different <strong>triggers</strong>, schedules different <strong>types</strong> of compaction, each doing one class of work. Their type enum is defined in proto's <span class="inline">datapb.CompactionType</span>:</p>

<table class="t">
  <tr><th>type</th><th>trigger</th><th>tidying effect</th></tr>
  <tr><td><strong>MixCompaction</strong></td><td>one segment amassed too many small binlogs / fragments</td><td><strong>merges</strong> fragmented binlogs into a larger, tidier segment (most common)</td></tr>
  <tr><td><strong>MergeCompaction</strong></td><td>several under-full small segments need joining</td><td><strong>merges</strong> several small segments into one bigger segment</td></tr>
  <tr><td><strong>Level0DeleteCompaction</strong></td><td>Level-0 delete data (tombstones) accumulated</td><td><strong>physically applies</strong> L0 tombstones into the matching sealed segments</td></tr>
  <tr><td><strong>ClusteringCompaction</strong></td><td>re-organize by a <strong>clustering key</strong> for retrieval locality</td><td><strong>re-buckets data by clustering key</strong>, gathering similar data together</td></tr>
  <tr><td><strong>SortCompaction</strong></td><td>need PK order to speed lookups</td><td><strong>sorts a segment's data by PK</strong> and rewrites it</td></tr>
</table>

<p>Read this table and you'll see these compactions fall roughly into two camps: <strong>Mix and Merge are the "merge camp"</strong> — their core goal is stitching <strong>fragmented, scattered, small</strong> segments into <strong>large, tidy</strong> ones, applying ordinary tombstones along the way; this is the most frequently triggered class day to day.
<strong>Clustering and Sort are the "reorder camp"</strong> — beyond merging, they <strong>actively adjust the physical order of data</strong> to boost read efficiency (see the next section); and <strong>Level0DeleteCompaction is a class of its own</strong>, dedicated to "actually landing hovering deletes onto segments."
The key to understanding their distinctions isn't memorizing each name, but grasping one through-line: <strong>all compaction serves "reads"</strong> — by making segments fewer and tidier, clearing tombstones, or arranging data for better pruning.</p>

<p>The one worth spelling out is <strong>Level0DeleteCompaction</strong>, the <strong>second half</strong> of last lesson's "deletes don't truly delete." A delete message is first buffered as <strong>Level-0</strong> delete data — a batch of deltalogs holding only "void PK + timestamp," <strong>not yet landed on any specific sealed segment</strong>, like a layer of "pending deletes" hovering above all segments.
Level0DeleteCompaction is exactly what <strong>sinks and applies</strong> this L0 tombstone layer into the sealed segments they should act on, making the deleted rows physically vanish. DataCoord keeps an <strong>L0 delete view</strong> (<span class="inline">LevelZeroCompactionView</span> in <span class="mono">internal/datacoord/compaction_l0_view.go</span>) to track "which L0 tombstones should merge with which segments." The full visibility mechanism of deletes is dissected next lesson.</p>

<div class="cellgroup">
  <div class="cg-cap">Level0DeleteCompaction: sink the hovering L0 tombstones, apply them into sealed segments</div>
  <div class="cells">
    <div class="cell hl"><span class="lab">L0 tombstones</span><span class="q">pk=102@t9 · pk=205@t9</span></div>
    <div class="cell sep"><span class="lab">↓ apply</span><span class="q">route to segments holding the pk</span></div>
    <div class="cell dim"><span class="lab">segment (after)</span><span class="q">rows 102/205 physically deleted</span></div>
  </div>
</div>

<h2>Who schedules, who executes</h2>
<p>Before getting to the division of labor, let's fully explain <strong>ClusteringCompaction</strong> and <strong>SortCompaction</strong> — the two kinds that "<strong>don't just merge but also reorder</strong>" — because they directly serve <strong>faster reads</strong>. Ordinary Mix/Merge only stitch fragments larger and apply tombstones, <strong>without changing the data's arrangement</strong>; whereas Clustering and Sort <strong>actively reorganize the physical order of data within segments</strong>, letting later queries skip more irrelevant data.</p>

<p><strong>ClusteringCompaction (reorganize by clustering key)</strong> works like this: give the collection a <strong>clustering key</strong> (say "region" or "category"), and at compaction time <strong>re-bucket data by that key</strong>, gathering "same-class" data into neighboring segments.
Then a filtered query (e.g. "only East China") can, by each segment's <strong>min/max stats</strong> (recall last lesson's stats binlog), <strong>skip whole segments</strong> of irrelevant buckets and scan only the few that truly match — this is the power of "<strong>data locality</strong>" in databases: place data frequently queried together physically together, and the query's pruning rate rises.
<strong>SortCompaction (sort by primary key)</strong> rewrites a segment's data <strong>ordered by PK</strong>, making PK point lookups, range scans, and dedup more efficient; sorted data also tightens min/max ranges and eases bloom checks. Both share a trait: at the cost of one background rewrite, they <strong>pre-shape data into a read-friendly form</strong>, amortizing the cost from "every query" forward into "one tidying pass."</p>

<p>Compaction's division of labor again proves the refrain "<strong>coordinators schedule, nodes execute</strong>" (Lesson 9). <strong>DataCoord</strong> is the brain: it scans segment metadata, by various compaction policies (<span class="mono">compaction_policy_*</span>) decides "which segments to merge and which compaction to run," generates compaction tasks, enqueues and dispatches them.
The one doing the heavy lifting — reading old binlogs, merging, applying tombstones, writing new binlogs — is the <strong>compaction worker on a datanode</strong>. This is precisely <strong>Lesson 17</strong>'s point that "DataNode's main present role is compaction": streaming writes went to StreamingNode, and DataNode steps back to focus on this background tidying.</p>

<div class="flow">
  <div class="node hl"><div class="nt">DataCoord</div><div class="nd">scan meta · pick policy · generate tasks</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">compaction queue</div><div class="nd">prioritize · dispatch</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">datanode worker</div><div class="nd">read old binlogs · merge · apply tombstones · write new binlogs</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">write back meta</div><div class="nd">new segment online · old segments marked dropped</div></div>
</div>

<p>On completion comes a key act: the worker writes new segments, and DataCoord <strong>atomically</strong> switches metadata from "the old small segments" to "the new big segment," bringing the new one online for queries and <strong>marking the old ones dropped</strong>.
This step must be <strong>atomic</strong>, and that matters greatly: it guarantees any query, at any instant, sees either <strong>the whole batch of old segments</strong> or <strong>the one new segment</strong> — never an intermediate state where "old and new are both visible and a row gets counted twice" or "the old is withdrawn, the new not yet online, and data vanishes into thin air." It is precisely this "<strong>atomic metadata switch</strong>" guarantee that lets compaction — a major operation that "quietly swaps out data in the background" — be <strong>completely transparent and imperceptible</strong> to foreground queries.
Note — at this moment the old segments' binlogs <strong>still sit in object storage, undeleted</strong>; they are merely no longer referenced by metadata. Truly sweeping away these "dropped, unreferenced" physical files is the job of the other janitor, GC.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">pkg/proto/datapb/data_coord.pb.go</span><span class="ln">CompactionType: the compaction-type enum (excerpt)</span></div>
  <pre><span class="cm">// generated from milvus-proto/go-api; datacoord schedules by these</span>
<span class="kw">const</span> (
    CompactionType_MergeCompaction         CompactionType = <span class="nb">2</span>
    CompactionType_MixCompaction           CompactionType = <span class="nb">3</span>
    CompactionType_Level0DeleteCompaction  CompactionType = <span class="nb">7</span> <span class="cm">// apply L0 tombstones</span>
    CompactionType_ClusteringCompaction    CompactionType = <span class="nb">8</span> <span class="cm">// reorganize by clustering key</span>
    CompactionType_SortCompaction          CompactionType = <span class="nb">9</span> <span class="cm">// sort by primary key</span>
)</pre>
</div>

<h2>GC: sweeping away ownerless orphan objects</h2>
<p>Compaction produces a batch of old binlogs that are "logically discarded, physically still present"; dropping a collection, partition, or segment also leaves many no-longer-referenced objects. <strong>GC (garbage collector)</strong> is the background loop responsible for reclaiming these <strong>orphan objects</strong>, with code in <span class="mono">internal/datacoord/garbage_collector.go</span>.
It periodically scans the binlogs in object storage, checks against metadata "<strong>is this object still referenced by any live segment</strong>," and for those of <strong>dropped segments</strong> or <strong>orphan files no one claims</strong>, deletes them from object storage.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>scan and compare</h4><p class="mono">recycleUnusedBinlogFiles</p><p>enumerate binlogs in object storage, find orphans "referenced by no live segment" against metadata.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>handle dropped segments</h4><p class="mono">recycleDroppedSegments</p><p>for segments marked dropped, reclaim all their binlogs (insert/delta/stats).</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>delete only past TTL</h4><p>delete only objects <strong>past the retention period (TTL)</strong>, leaving a safe window for in-flight reads and rollback.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>physical delete</h4><p>batch-delete by object-storage prefix, truly freeing space.</p></div></div>
</div>

<p>The most crucial safety valve in GC's design is the <strong>TTL (retention period)</strong>: it <strong>never</strong> deletes an object the instant it becomes an orphan. The reason is the many "<strong>time skews</strong>" in a distributed system — some QueryNode may still be reading an old segment just replaced by compaction, some operation may need to roll back.
Deleting only objects "<strong>orphaned beyond TTL</strong>" gives every in-flight reference a <strong>safe window</strong>: better to let garbage linger a while than to ever mis-delete data still in use. This echoes last lesson's point: object storage's <strong>prefixed, enumerable</strong> layout lets GC efficiently enumerate and clean by segment or collection prefix.</p>

<p>It's worth pausing to ask: where do "<strong>orphans</strong>" in object storage actually come from? Their sources are more numerous than you'd think. Old segments replaced by <strong>compaction</strong> are the biggest class — one merge batch-creates a pile of "dropped, awaiting reclaim" old binlogs;
DDL that <strong>drops a collection / partition / segment</strong> makes swaths of objects instantly lose their references; <strong>failed or timed-out flush, compaction, or index-build tasks</strong> may break off mid-write, leaving <strong>half-finished orphans</strong> that "wrote files but never registered into metadata";
even a <strong>metadata rollback</strong> can turn some already-persisted objects ownerless. GC's decision logic therefore can't just look at "does the file exist," but must <strong>take metadata as the yardstick</strong> and check in reverse: anything present in object storage but with <strong>no reference found in live-segment metadata</strong> is an orphan candidate. This is the classic reclaim mindset of "<strong>authoritative metadata is truth, physical storage aligns to it</strong>" — only when metadata says it's no longer needed may the physical file be cleaned.</p>

<p>A common <strong>misconception</strong> needs clearing up here too: a delete does <strong>not</strong> immediately make data vanish from object storage, and even a DDL "drop segment" only first <strong>marks the segment dropped</strong>. The real release of physical space is <strong>always done asynchronously by GC, past TTL</strong>.
So if you delete a batch of data and notice object-storage usage doesn't drop right away, that's not a bug but the <strong>normal behavior</strong> of this "<strong>separate logical voiding from physical reclaim</strong>" design — it trades a little storage delay for deletes that are <strong>low-latency, rollback-able, and friendly to in-flight reads</strong>. Grasp this, and you grasp the same wisdom recurring across Milvus's whole write path: <strong>decouple "fast bookkeeping" from "slow settling."</strong></p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/datacoord/garbage_collector.go</span><span class="ln">garbageCollector: reclaim orphans and dropped segments (excerpt)</span></div>
  <pre><span class="kw">type</span> garbageCollector <span class="kw">struct</span> {
    meta    *meta
    handler Handler
    option  GcOption <span class="cm">// holds TTL and retention policy</span>
}

<span class="cm">// background loop: clean unreferenced binlogs and dropped segments</span>
<span class="kw">func</span> (gc *garbageCollector) <span class="fn">recycleUnusedBinlogFiles</span>(ctx context.Context) { <span class="cm">/* enumerate · compare · past-TTL · delete */</span> }
<span class="kw">func</span> (gc *garbageCollector) <span class="fn">recycleDroppedSegments</span>(ctx context.Context, signal &lt;-<span class="kw">chan</span> gcCmd) { <span class="cm">/* reclaim all binlogs of dropped segments */</span> }</pre>
</div>

<p>Seen together, compaction and GC are a <strong>relay</strong>, one after the other: compaction rewrites "fragmented, dirty" data into "tidy, clean" new segments and voids the old ones <strong>logically</strong>; GC, past TTL, sweeps these old segments away <strong>physically</strong>.
The former optimizes <strong>reads</strong> (fewer, cleaner segments), the latter optimizes <strong>storage</strong> (don't keep paying for discarded data). Both are <strong>scheduled by DataCoord</strong> — the silent yet vital self-maintenance of Milvus's write path "<strong>after the write</strong>"; without them, the system slowly chokes on small files and tombstones, queries grow ever slower and storage ever more bloated. These two background janitors, though never on the main stage of writes and queries, are the behind-the-scenes bedrock that lets Milvus <strong>run stably over the long haul</strong>. Next lesson, we formally crack open "delete and upsert," seeing how tombstones, bloom filters, and the MVCC timestamp together decide "whether a row is visible at all."</p>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: writing only <strong>appends fast</strong>, leaving two "tech debts" — <strong>small-file fragments</strong> and <strong>delete tombstones</strong> — repaid by two background janitors. <strong>Compaction</strong> (scheduled by DataCoord, executed by a datanode worker) <strong>merges</strong> fragments and <strong>physically applies</strong> L0 tombstones (<span class="inline">datapb.CompactionType_Level0DeleteCompaction</span>), and can reorganize by clustering key (Clustering) or sort by PK (Sort); <strong>GC</strong> (<span class="mono">garbage_collector.go</span>), past <strong>TTL</strong>, sweeps away objects of <strong>orphans and dropped segments</strong>. The former speeds reads, the latter saves storage.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Two tech debts</strong>: small-file fragments from repeated flushes + tombstone-only deletes, repaid by compaction and GC.</li>
    <li><strong>Compaction types</strong>: MixCompaction/MergeCompaction (merge fragments), Level0DeleteCompaction (physically apply L0 tombstones), ClusteringCompaction (reorganize by clustering key), SortCompaction (sort by PK).</li>
    <li><strong>Schedule vs execute</strong>: DataCoord picks policy and generates tasks; a datanode worker reads old binlogs, merges, writes new segments (echoes Lesson 17).</li>
    <li><strong>Level-0 deletes</strong>: a delete is first buffered as an L0 tombstone, tracked by <span class="mono">compaction_l0_view.go</span>, and only Level0DeleteCompaction applies it physically into segments (expanded in Lesson 20).</li>
    <li><strong>GC and TTL</strong>: <span class="mono">garbage_collector.go</span> reclaims orphan / dropped-segment objects, deleting only those past TTL, leaving a safe window for in-flight references.</li>
    <li><strong>Division of labor</strong>: compaction optimizes reads, GC optimizes storage; both scheduled by DataCoord.</li>
  </ul>
</div>
""",
}

LESSON_20 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
"删一行"听起来是数据库里最朴素的操作，但在一个<strong>只追加、不可变</strong>的存储底座上，它其实暗藏玄机：binlog 写下去就改不了，那"删除"到底删的是什么？这一课把<strong>删除（delete）</strong>与 <strong>upsert</strong> 彻底拆开——
删除如何变成 WAL 里的一条<strong>删除消息</strong>、再沉淀为<strong>第零层（L0）删除数据 / deltalog</strong>；<strong>布隆过滤器</strong>如何把一条删除<strong>路由</strong>到可能含此主键的段；<strong>upsert 为什么就是"删除 + 插入"</strong>；以及把这一切统一起来的那把钥匙——<strong>基于时间戳的 MVCC（多版本并发控制）</strong>：一行到底"可不可见"，由读取的保证时间戳与各版本的时间戳共同裁决。
</p>

<div class="card analogy">
  <div class="tag">📚 生活类比</div>
  把一个集合想成一家旅馆的<strong>住客登记簿</strong>——而且是一本<strong>只能往后写、不能涂改</strong>的簿子。客人退房时，前台<strong>不会</strong>翻回去把那一行划掉（簿子改不了），而是在新的一页盖一个章："<strong>X 房客在 t 时刻退房</strong>"——这就是<strong>删除墓碑（tombstone）</strong>。
  想知道"某位客人住在哪一页"，前台不必翻遍整本簿子，而是查一张<strong>快速索引卡</strong>（布隆过滤器）：它只会告诉你"<strong>这本簿子里<em>肯定没有</em>这位客人</strong>"或"<strong>可能有，去翻翻看</strong>"——用来快速排除不可能的簿子。
  客人要<strong>换房</strong>（改信息）？做法是"<strong>给旧房盖退房章 + 给新房写一条入住</strong>"——这正是 <strong>upsert = 删除 + 插入</strong>。而"<strong>现在到底谁在住</strong>"这个问题，答案取决于你<strong>以哪一刻为准</strong>去读这本簿子：读"截至此刻"的快照，才能干净地数出当下的住客——这就是<strong>按时间戳的 MVCC</strong>。
</div>

<h2>一条删除的旅程：消息 → WAL → L0 deltalog</h2>
<p>回忆<strong>第 15、16 课</strong>：写入并不直接落库，而是先变成一条消息 <strong>Append 进 WAL</strong>，WAL 才是单一事实来源。删除走的是<strong>同一条路</strong>——它不是去对象存储里"找到那行抹掉"，而是生成一条 <strong>删除消息（delete message）</strong>，携带<strong>要作废的主键</strong>与一个<strong>删除时间戳</strong>，Append 进 WAL，排进与插入<strong>同一条全局时序</strong>里。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>客户端发起 delete</h4><p>按主键或表达式指定"删谁"。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Proxy 盖时间戳</h4><p>向 TSO 要一个删除 ts，定下这次删除在全局时序里的位置。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Append 进 WAL</h4><p>删除消息（主键+ts）写入 WAL，和插入消息排同一条流。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>沉淀为 L0 deltalog</h4><p>消费方把删除缓冲成第零层删除数据（deltalog），暂不落到具体 sealed 段。</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>Level0DeleteCompaction 物理应用</h4><p>后台把 L0 墓碑下沉、应用进对应段（第 19 课）。</p></div></div>
</div>

<p>这里的关键洞察是：删除被建模成一条<strong>带时间戳的、不可变的事件</strong>，而不是一次"原地修改"。它先以<strong>第零层（Level-0）删除数据</strong>的形态存在——一批只含"<strong>作废主键 + 删除时间戳</strong>"的 deltalog，<strong>悬在所有 sealed 段之上、尚未应用到任何具体段</strong>。
为什么要先悬着？因为"这条删除到底该作用到哪些段"需要逐段判断（下一节讲），而真正把行从数据里抹掉的重写代价很大——于是和插入一样，删除也遵循"<strong>先快速记账、再后台清算</strong>"：先把墓碑快速记进 L0，把"物理应用"这桩慢活交给第 19 课的 <strong>Level0DeleteCompaction</strong>。这正是上一课"删除不真删"那句话在<strong>写入侧</strong>的完整落地。</p>

<p>这里还藏着一个容易被忽略、却至关重要的设计：<strong>删除和插入共用同一条 WAL、排在同一条全局时序里</strong>。为什么这点如此关键？因为只有当"插入某行"和"删除某行"被放进<strong>同一条单调递增的时间轴</strong>，系统才能毫不含糊地判定它们的<strong>先后</strong>——到底是"先插入、后删除"（那这行该消失），还是"先删除、后又插入了同主键的新行"（那新行该留下）。
设想若删除走另一条独立通道，两条流的时序就需要额外的协调才能对齐，稍有差池就会出现"删了又活、或活了又被误删"的诡异结果。把删除<strong>收编进与插入同一条 WAL</strong>，等于让 TSO 这台"全局发号机"（第 16 课）<strong>一并裁定</strong>所有写事件的先后，删除与插入的时序冲突在源头上就被消解了。这也是 Milvus"<strong>日志即数据、WAL 单一事实来源</strong>"这一信条在删除语义上的自然延伸。</p>

<h2>用布隆过滤器路由一条删除</h2>
<p>一条删除消息说"<strong>把主键 X 作废</strong>"，但 X 这一行可能落在成百上千个段里的<strong>某一个</strong>——总不能把这条墓碑无脑塞进每一个段。这里就轮到<strong>布隆过滤器</strong>登场了（回忆第 18 课：它随 PK stats 一起序列化进 stats binlog）。
系统拿主键 X 去<strong>逐段问布隆</strong>："这个段<strong>可能</strong>含 X 吗？"——布隆只会回答"<strong>肯定不在</strong>"或"<strong>可能在</strong>"。所有回答"肯定不在"的段被<strong>安全跳过</strong>，只有回答"可能在"的少数段，才需要把这条墓碑应用上去。</p>

<div class="cellgroup">
  <div class="cg-cap">布隆路由：拿待删主键 X 逐段筛，只把墓碑落到"可能含 X"的段</div>
  <div class="cells">
    <div class="cell dim"><span class="lab">段1</span><span class="q">布隆：肯定没有 → 跳过</span></div>
    <div class="cell hl"><span class="lab">段2</span><span class="q">布隆：可能有 → 应用墓碑</span></div>
    <div class="cell dim"><span class="lab">段3</span><span class="q">布隆：肯定没有 → 跳过</span></div>
    <div class="cell"><span class="lab">段4</span><span class="q">布隆：可能有 → 应用墓碑</span></div>
  </div>
</div>

<p>布隆过滤器"<strong>绝不漏报</strong>"的特性在这里是<strong>正确性的命脉</strong>：它说"肯定没有"就<strong>一定没有</strong>，所以被跳过的段绝不会冤枉地漏掉一个本该删的行；而它偶尔"误报"（说可能有、细查却没有）顶多<strong>多做一点无用功</strong>，绝不会错删。
这种"<strong>宁可多查、绝不漏查</strong>"的非对称保证，恰恰是删除路由能放心剪枝的根基。Milvus 里这张布隆过滤器由 <span class="inline">PrimaryKeyStats</span>（<span class="mono">internal/storage/stats.go</span>）持有——它装着主键的上下界（<span class="inline">MaxPk</span>/<span class="inline">MinPk</span>）与那张 <span class="inline">BF</span>（<span class="inline">bloomfilter.BloomFilterInterface</span>），经 <span class="inline">BloomFilterSet</span>/<span class="inline">pkoracle</span> 暴露，是"删除该落到哪些段"这个问题的<strong>判定依据</strong>。</p>

<p>值得体会布隆路由在<strong>规模</strong>上的意义：一个大集合可能有上千个段，若每条删除都把墓碑无差别地塞进每一个段，那么删除的代价会随段数<strong>线性膨胀</strong>，且绝大多数墓碑都落在"根本不含此主键"的段上，纯属浪费。
布隆过滤器把这件事从"<strong>广播给所有段</strong>"压成"<strong>精准投递给少数候选段</strong>"——它用每段一张小小的概率位图，换来删除写入量的<strong>大幅收缩</strong>，也让后续 Level0DeleteCompaction 要处理的墓碑量小得多。这是典型的"<strong>用一点点摘要空间，省下大量盲目 I/O</strong>"的工程权衡，与第 18 课讲查询时布隆帮忙"<strong>整段跳过</strong>"是同一个机制的一体两面：<strong>查询靠它跳过无关段，删除靠它只投相关段</strong>。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/storage/stats.go</span><span class="ln">PrimaryKeyStats：段级主键摘要，含布隆过滤器（节选）</span></div>
  <pre><span class="kw">type</span> PrimaryKeyStats <span class="kw">struct</span> {
    PkType   int64                            <span class="cm">// 主键类型</span>
    MaxPk, MinPk PrimaryKey                   <span class="cm">// 主键上下界</span>
    BF       bloomfilter.BloomFilterInterface <span class="cm">// 布隆：删除据此路由到候选段</span>
}</pre>
</div>

<h2>upsert = 删除 + 插入</h2>
<p>明白了删除是"加一条带 ts 的墓碑"、插入是"加一条带 ts 的新行"，<strong>upsert</strong> 就豁然开朗了：它<strong>不是</strong>"原地把旧值改成新值"，而是被拆成两步——<strong>对同一个主键先删、再插</strong>。
旧版本被一条墓碑作废、新版本作为一行<strong>更晚时间戳</strong>的数据写入；同一个主键于是在物理上<strong>同时存在新旧两个版本</strong>，靠时间戳区分先后。这也解释了上一课那句"<strong>upsert = delete + insert（同主键、新版本）</strong>"的真正含义。</p>

<div class="cellgroup">
  <div class="cg-cap">upsert 主键 102：旧版本被墓碑作废，新版本以更晚 ts 写入（新旧并存，按 ts 取胜）</div>
  <div class="cells">
    <div class="cell dim"><span class="lab">旧版本</span><span class="q">pk=102 · v0 · 插入@t3</span></div>
    <div class="cell hl"><span class="lab">墓碑</span><span class="q">pk=102 · 作废@t8</span></div>
    <div class="cell"><span class="lab">新版本</span><span class="q">pk=102 · v1 · 插入@t8</span></div>
  </div>
</div>

<p>把 upsert 看成"删 + 插"有个非常实际的好处：<strong>整条写入链路不必为 upsert 单设一套特殊机制</strong>。删除有的（墓碑、布隆路由、L0、compaction 应用），upsert 直接复用；插入有的（列式 binlog、按 ts 排序），upsert 也直接复用。
一个看似独立的"更新"语义，被优雅地<strong>归约</strong>成两个已有原语的组合——这是系统设计里"<strong>用少量正交原语拼出丰富语义</strong>"的典范。代价是同主键会短暂存在多个版本，但这恰恰被下面要讲的 MVCC <strong>正好接住</strong>：多版本本就是 MVCC 的家常便饭。</p>

<p>这种"删 + 插"的归约还顺手解释了 upsert 的一个<strong>语义细节</strong>：它<strong>不保证字段级的部分更新</strong>。因为新版本是作为<strong>一整行</strong>重新写入的，你 upsert 时若只给了部分字段，那么<strong>没给的字段会按默认或重写规则整体覆盖</strong>，而不是像 SQL 的 <span class="inline">UPDATE ... SET col=...</span> 那样只动一列、其余保留。
理解了"upsert 本质是<strong>整行替换</strong>（旧行作废 + 新行写入）"，你就不会误以为它能做"原地改一个字段"——这是向量库与传统行式数据库在更新语义上的一个常见认知落差。背后的根因还是那条铁律：<strong>底层 binlog 不可变</strong>，任何"改"都只能表达成"作废旧的、追加新的"，没有真正的原地修改可言。</p>

<p>还有一个常被追问的细节：既然 upsert 是"先删后插"，那<strong>同一主键反复 upsert 多次</strong>会怎样？答案是——每一次都<strong>追加</strong>一对"墓碑 + 新版本"，于是同主键会沉淀出一串按时间戳排开的版本，但<strong>任意时刻读取，都只会命中最新那个未被作废的版本</strong>（由下一节的 MVCC 规则裁定）。
那些更早的旧版本既不会被读到，也不会永远占着空间——它们正是上一课与第 19 课讲的 <strong>compaction</strong> 要清理的对象：物理应用墓碑、合并段时，作废的旧版本会被真正抹去。于是"反复 upsert 留下的历史包袱"也由后台 compaction 兜底回收，写入侧依旧只管<strong>快速追加</strong>，不必操心清理——又一次印证了那条贯穿整个写入链路的主线：<strong>快速记账在前台，慢慢清算在后台</strong>。</p>

<h2>把一切统一起来：按时间戳的 MVCC</h2>
<p>到这里，插入、删除、upsert 都被归结成了"<strong>一堆带时间戳的不可变事件</strong>"：插入是"某行在 ts 诞生"，删除是"某主键在 ts 作废"。那么"<strong>某一行此刻到底可不可见</strong>"该怎么判定？答案就是 <strong>MVCC（多版本并发控制）</strong>的核心规则——<strong>一切以时间戳裁决</strong>。MVCC 不去"删掉"或"覆盖"任何东西，它把所有版本都留在时间轴上，把"哪个版本算数"这个问题，交给读取时携带的那个时间戳来回答。</p>

<p>读取时会带一个<strong>保证时间戳 T</strong>（guarantee-ts，由一致性级别决定，第 30 课展开）。一行数据，<strong>当且仅当</strong>同时满足两个条件时，对这次读取<strong>可见</strong>：</p>

<div class="cellgroup">
  <div class="cg-cap">MVCC 可见性规则：以保证时间戳 T 读，一行可见 ⇔ 已插入 且 未被更早的墓碑作废</div>
  <div class="cells">
    <div class="cell hl"><span class="lab">条件一</span><span class="q">该行的插入 ts ≤ T（在 T 之前已诞生）</span></div>
    <div class="cell sep"><span class="lab">且</span><span class="q">AND</span></div>
    <div class="cell hl"><span class="lab">条件二</span><span class="q">不存在 ts ≤ T 的墓碑作废它（截至 T 未被删）</span></div>
  </div>
</div>

<p>把这条规则套到前面的例子上就一目了然了。对主键 102：若以 <strong>T=t5</strong> 读，看到的是 <strong>v0</strong>（插入@t3 ≤ t5，而作废@t8 还在未来、尚未生效）；若以 <strong>T=t9</strong> 读，v0 已被 t8 的墓碑作废、不可见，看到的是 <strong>v1</strong>（插入@t8 ≤ t9）。
<strong>同一份底层数据，换一个读取时间戳 T，就切出一张不同时刻的快照</strong>——这就是"多版本"的威力：写入方只管<strong>不断追加</strong>新版本与墓碑，读取方靠一个 T <strong>干净地切出</strong>"截至此刻"的一致视图，读写互不阻塞。</p>

<p>这套"读取快照、写入追加"的并发模型，带来一个在分布式向量库里极其宝贵的性质：<strong>读和写不会互相等待、互相加锁</strong>。传统数据库里"一边在改、一边要读"常常意味着锁竞争、读被写阻塞；而在 MVCC 下，正在持续写入的新版本与墓碑<strong>根本不会打扰</strong>一个以较早 T 进行的查询——那次查询看到的，永远是它出发时刻 T 所对应的<strong>一致快照</strong>，哪怕此刻底层数据已被改得面目全非。
这对一个要<strong>高吞吐写入、又要稳定低延迟检索</strong>的向量库来说至关重要：海量插入、删除、upsert 源源不断地往时间轴后端追加，而每一次 search 都能拿一个 T 干净地"<strong>定格</strong>"出一个不动的世界来检索，两者各行其道、互不拖累。这正是"<strong>多版本</strong>"三个字真正买到的东西——不是为了保存历史，而是为了<strong>让读写在时间轴上解耦</strong>。</p>

<div class="timeline">
  <div class="lane"><span class="lane-label">主键 102 的事件</span><span class="tslot">插入 v0 @t3</span><span class="tslot">墓碑作废 @t8</span><span class="tslot span">插入 v1 @t8</span></div>
  <div class="lane"><span class="lane-label">读 T=t5</span><span class="tslot now">看见 v0（t8 在未来）</span></div>
  <div class="lane"><span class="lane-label">读 T=t9</span><span class="tslot now">看见 v1（v0 已被作废）</span></div>
</div>

<p>这把"<strong>时间戳裁决可见性</strong>"的钥匙，正是 Milvus 在分布式环境下兼顾<strong>一致性</strong>与<strong>高并发</strong>的根基。它不需要给数据加读写锁，而是让"读"和"写"各自沿着时间轴前进：写只追加、读取一个快照。
但它也留下一个尚未回答的问题：<strong>那个保证时间戳 T 到底怎么定？</strong>读"最新"要等多久才能保证看全？这就是<strong>一致性级别</strong>（Strong / Bounded / Eventual 等）的舞台——它在"看得多新"和"要等多久"之间做权衡。这部分的完整机制——TSO 怎么发号、delegator 怎么等水位、快照怎么对齐——留到<strong>第 30 课</strong>专门展开。本课你只需牢牢记住这条统一规则：<strong>插入给行盖生日、删除给行盖忌日，一次读取拿着 T，只认"生日 ≤ T 且 忌日 > T 或没有忌日"的行。</strong>把这条规则记牢，你就握住了贯穿插入、删除、upsert 三种写操作的同一把尺子。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：在只追加的存储上，<strong>删除不是抹除而是盖一枚带时间戳的墓碑</strong>——它作为<strong>删除消息</strong>进 WAL、沉淀为 <strong>L0 deltalog</strong>，靠<strong>布隆过滤器</strong>（<span class="inline">PrimaryKeyStats</span> 的 <span class="inline">BF</span>，<span class="mono">internal/storage/stats.go</span>）路由到可能含此主键的段，最终由 <strong>Level0DeleteCompaction</strong> 物理应用（第 19 课）。<strong>upsert = 删除 + 插入</strong>（同主键、更晚 ts 的新版本）。统一这一切的是<strong>按时间戳的 MVCC</strong>：以保证时间戳 T 读，一行可见 ⇔ 插入 ts ≤ T 且无 ts ≤ T 的墓碑作废它；T 怎么定由一致性级别决定（第 30 课）。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>删除即墓碑</strong>：delete 变成 WAL 里的删除消息（主键+ts），沉淀为 L0 删除数据 / deltalog，不原地抹除。</li>
    <li><strong>布隆路由</strong>：拿待删主键逐段问布隆（<span class="inline">PrimaryKeyStats.BF</span>，<span class="mono">internal/storage/stats.go</span>），"肯定没有"的段跳过，只把墓碑落到"可能含"的段；绝不漏报保证不错删。</li>
    <li><strong>物理应用</strong>：L0 墓碑由 Level0DeleteCompaction 真正下沉应用进段（第 19 课），写入侧只快速记账。</li>
    <li><strong>upsert = delete + insert</strong>：同主键先删后插，新旧版本按 ts 区分；复用删除与插入的全部机制，无需特殊路径。</li>
    <li><strong>按时间戳的 MVCC</strong>：以保证时间戳 T 读，一行可见 ⇔ 插入 ts ≤ T 且无 ts ≤ T 的墓碑；同一数据换 T 即换快照，读写互不阻塞。</li>
    <li><strong>T 怎么定</strong>：由一致性级别（Strong/Bounded/Eventual）权衡"看多新 vs 等多久"，完整机制见第 30 课。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
"Delete a row" sounds like the most trivial operation in a database, yet on an <strong>append-only, immutable</strong> storage substrate it hides a twist: once a binlog is written it can't be changed — so what does "delete" actually delete? This lesson fully cracks open <strong>delete</strong> and <strong>upsert</strong> —
how a delete becomes a <strong>delete message</strong> in the WAL, then settles into <strong>Level-0 (L0) delete data / deltalogs</strong>; how <strong>bloom filters</strong> <strong>route</strong> a delete to the segments that might hold the PK; <strong>why upsert is just "delete + insert"</strong>; and the key that unifies it all — <strong>timestamp-based MVCC (multi-version concurrency control)</strong>: whether a row is "visible at all" is decided jointly by the read's guarantee timestamp and each version's timestamp.
</p>

<div class="card analogy">
  <div class="tag">📚 Analogy</div>
  Picture a collection as a hotel's <strong>guest registry</strong> — and one that can <strong>only be appended to, never altered</strong>. When a guest checks out, the front desk does <strong>not</strong> flip back and strike out that line (the ledger can't be changed); instead it stamps on a new page: "<strong>guest X checked out at time t</strong>" — that is a <strong>delete tombstone</strong>.
  To know "which page a guest is on," the desk needn't read the whole ledger but checks a <strong>quick index card</strong> (bloom filter): it tells you only "<strong>this ledger <em>definitely lacks</em> this guest</strong>" or "<strong>maybe has them, go look</strong>" — to quickly rule out impossible ledgers.
  A guest wants to <strong>change rooms</strong> (update info)? The way is "<strong>stamp checkout on the old room + write a check-in for the new</strong>" — that is exactly <strong>upsert = delete + insert</strong>. And the question "<strong>who is actually staying now</strong>" depends on <strong>which moment you read the ledger as-of</strong>: read the "as-of-now" snapshot to cleanly count current guests — that is <strong>timestamp-based MVCC</strong>.
</div>

<h2>A delete's journey: message → WAL → L0 deltalog</h2>
<p>Recall <strong>Lessons 15 and 16</strong>: a write doesn't go straight to storage but first becomes a message <strong>Appended into the WAL</strong>, and the WAL is the single source of truth. A delete takes <strong>the same road</strong> — it doesn't go to object storage to "find that row and erase it," but generates a <strong>delete message</strong> carrying the <strong>PK to void</strong> and a <strong>delete timestamp</strong>, Appended into the WAL, queued into the <strong>same global time order</strong> as inserts.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>client issues delete</h4><p>specify "whom to delete" by PK or expression.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Proxy stamps a timestamp</h4><p>asks TSO for a delete ts, fixing this delete's place in the global order.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Append to WAL</h4><p>the delete message (PK + ts) is written to the WAL, in the same stream as inserts.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>settle as L0 deltalog</h4><p>the consumer buffers the delete as Level-0 delete data (deltalog), not yet landed on a specific sealed segment.</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>Level0DeleteCompaction applies it</h4><p>the background sinks and applies the L0 tombstone into the matching segments (Lesson 19).</p></div></div>
</div>

<p>The key insight here is: a delete is modeled as a <strong>timestamped, immutable event</strong>, not an "in-place modification." It first exists as <strong>Level-0 delete data</strong> — a batch of deltalogs holding only "<strong>void PK + delete timestamp</strong>," <strong>hovering above all sealed segments, not yet applied to any specific one</strong>.
Why hover first? Because "which segments this delete should act on" needs per-segment judgment (next section), and the rewrite cost of truly erasing rows from data is large — so, like inserts, deletes follow "<strong>book fast, settle in the background</strong>": record the tombstone quickly into L0, leaving the slow "physical apply" to Lesson 19's <strong>Level0DeleteCompaction</strong>. This is the full landing, on the <strong>write side</strong>, of last lesson's "deletes don't truly delete."</p>

<p>There's also an easily-overlooked yet crucial design here: <strong>deletes and inserts share the same WAL, queued in the same global time order</strong>. Why does this matter so much? Because only when "insert this row" and "delete this row" are placed on the <strong>same monotonically-increasing time axis</strong> can the system unambiguously decide their <strong>ordering</strong> — is it "insert first, delete later" (then the row should vanish), or "delete first, then a new row of the same PK inserted later" (then the new row should stay)?
Imagine if deletes took a separate channel: the two streams' orderings would need extra coordination to align, and the slightest slip would produce bizarre results like "deleted yet alive, or alive yet wrongly deleted." Folding deletes <strong>into the same WAL as inserts</strong> lets the TSO, that "global number-issuer" (Lesson 16), <strong>adjudicate the ordering of all write events together</strong>, dissolving delete/insert ordering conflicts at the source. This is the natural extension, to delete semantics, of Milvus's creed "<strong>log as data, WAL as the single source of truth</strong>."</p>

<h2>Routing a delete with bloom filters</h2>
<p>A delete message says "<strong>void PK X</strong>," but row X may sit in <strong>one</strong> of hundreds or thousands of segments — you can't blindly stuff this tombstone into every segment. This is where the <strong>bloom filter</strong> comes in (recall Lesson 18: it's serialized into the stats binlog alongside PK stats).
The system takes PK X and <strong>asks each segment's bloom</strong>: "could this segment <strong>possibly</strong> hold X?" — the bloom answers only "<strong>definitely not</strong>" or "<strong>maybe</strong>." Every segment answering "definitely not" is <strong>safely skipped</strong>, and only the few answering "maybe" need the tombstone applied.</p>

<div class="cellgroup">
  <div class="cg-cap">Bloom routing: screen each segment with the to-delete PK X, land the tombstone only on segments that "might hold X"</div>
  <div class="cells">
    <div class="cell dim"><span class="lab">seg1</span><span class="q">bloom: definitely not → skip</span></div>
    <div class="cell hl"><span class="lab">seg2</span><span class="q">bloom: maybe → apply tombstone</span></div>
    <div class="cell dim"><span class="lab">seg3</span><span class="q">bloom: definitely not → skip</span></div>
    <div class="cell"><span class="lab">seg4</span><span class="q">bloom: maybe → apply tombstone</span></div>
  </div>
</div>

<p>The bloom filter's "<strong>never a false negative</strong>" property is the <strong>lifeline of correctness</strong> here: if it says "definitely not," it <strong>truly isn't</strong>, so a skipped segment never wrongly misses a row that should be deleted; while its occasional "false positive" (says maybe, a closer look finds nothing) at most causes <strong>a little wasted work</strong>, never a wrong delete.
This asymmetric guarantee of "<strong>rather over-check than ever miss</strong>" is exactly the foundation on which delete routing can confidently prune. In Milvus this bloom filter is held by <span class="inline">PrimaryKeyStats</span> (<span class="mono">internal/storage/stats.go</span>) — it carries the PK bounds (<span class="inline">MaxPk</span>/<span class="inline">MinPk</span>) and that <span class="inline">BF</span> (<span class="inline">bloomfilter.BloomFilterInterface</span>), exposed via <span class="inline">BloomFilterSet</span>/<span class="inline">pkoracle</span>, the <strong>decision basis</strong> for "which segments a delete should land on."</p>

<p>It's worth appreciating bloom routing's significance at <strong>scale</strong>: a large collection may have thousands of segments, and if every delete stuffed its tombstone indiscriminately into each one, the cost of a delete would <strong>balloon linearly</strong> with the segment count, with the vast majority of tombstones landing on segments that "don't hold the PK at all" — pure waste.
The bloom filter compresses this from "<strong>broadcast to all segments</strong>" down to "<strong>precise delivery to a few candidate segments</strong>" — at the price of one tiny probabilistic bitmap per segment, it <strong>greatly shrinks</strong> the delete write volume and leaves far fewer tombstones for later Level0DeleteCompaction to process. This is the classic engineering tradeoff of "<strong>spend a little summary space to save a lot of blind I/O</strong>," two sides of the same mechanism as Lesson 18's bloom helping queries "<strong>skip whole segments</strong>": <strong>queries use it to skip irrelevant segments, deletes use it to deliver only to relevant ones</strong>.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/storage/stats.go</span><span class="ln">PrimaryKeyStats: a segment-level PK summary, with bloom filter (excerpt)</span></div>
  <pre><span class="kw">type</span> PrimaryKeyStats <span class="kw">struct</span> {
    PkType   int64                            <span class="cm">// the PK type</span>
    MaxPk, MinPk PrimaryKey                   <span class="cm">// PK upper/lower bounds</span>
    BF       bloomfilter.BloomFilterInterface <span class="cm">// bloom: routes deletes to candidate segments</span>
}</pre>
</div>

<h2>upsert = delete + insert</h2>
<p>Once you see that a delete is "append a timestamped tombstone" and an insert is "append a timestamped new row," <strong>upsert</strong> becomes obvious: it is <strong>not</strong> "change the old value to the new in place," but is split into two steps — <strong>for the same PK, delete first, then insert</strong>.
The old version is voided by a tombstone, and the new version is written as a row with a <strong>later timestamp</strong>; the same PK thus physically holds <strong>both old and new versions at once</strong>, distinguished by timestamp. This explains the true meaning of last lesson's line "<strong>upsert = delete + insert (same PK, new version)</strong>."</p>

<div class="cellgroup">
  <div class="cg-cap">upsert PK 102: the old version is voided by a tombstone, the new written with a later ts (both coexist, latest-ts wins)</div>
  <div class="cells">
    <div class="cell dim"><span class="lab">old version</span><span class="q">pk=102 · v0 · inserted@t3</span></div>
    <div class="cell hl"><span class="lab">tombstone</span><span class="q">pk=102 · voided@t8</span></div>
    <div class="cell"><span class="lab">new version</span><span class="q">pk=102 · v1 · inserted@t8</span></div>
  </div>
</div>

<p>Seeing upsert as "delete + insert" has a very practical benefit: <strong>the whole write path needs no special mechanism just for upsert</strong>. Whatever delete has (tombstones, bloom routing, L0, compaction apply), upsert reuses directly; whatever insert has (columnar binlogs, ordering by ts), upsert reuses too.
A seemingly standalone "update" semantic is elegantly <strong>reduced</strong> to a composition of two existing primitives — a model example of "<strong>building rich semantics from a few orthogonal primitives</strong>" in system design. The cost is that a PK briefly holds multiple versions, but that is exactly <strong>caught</strong> by the MVCC below: multiple versions are MVCC's bread and butter.</p>

<p>This "delete + insert" reduction also incidentally explains a <strong>semantic detail</strong> of upsert: it <strong>does not guarantee field-level partial updates</strong>. Because the new version is rewritten as <strong>a whole row</strong>, if you upsert with only some fields, the <strong>omitted fields are wholesale overwritten by defaults or rewrite rules</strong>, not preserved as SQL's <span class="inline">UPDATE ... SET col=...</span> would by touching one column and keeping the rest.
Understand that "upsert is essentially a <strong>whole-row replacement</strong> (void the old row + write a new row)," and you won't mistakenly assume it can "change one field in place" — a common cognitive gap between vector DBs and traditional row stores on update semantics. The root cause is again that iron law: <strong>the underlying binlog is immutable</strong>, so any "change" can only be expressed as "void the old, append the new" — there is no true in-place modification.</p>

<p>A frequently-asked detail: since upsert is "delete then insert," what happens when <strong>the same PK is upserted many times over</strong>? The answer — each time <strong>appends</strong> a "tombstone + new version" pair, so a PK accumulates a string of versions laid out by timestamp, but <strong>any read at any moment only hits the latest non-voided version</strong> (adjudicated by the next section's MVCC rule).
Those earlier old versions are neither read nor occupy space forever — they are exactly the targets of <strong>compaction</strong> from last lesson and Lesson 19: when tombstones are physically applied and segments merged, the voided old versions are truly erased. So even "the historical baggage left by repeated upserts" is backstopped and reclaimed by background compaction, and the write side still only <strong>appends fast</strong> without worrying about cleanup — once more proving the through-line spanning the whole write path: <strong>fast bookkeeping in the foreground, slow settling in the background</strong>.</p>

<h2>Unifying it all: timestamp-based MVCC</h2>
<p>By now, insert, delete, and upsert have all been reduced to "<strong>a pile of timestamped immutable events</strong>": an insert is "a row born at ts," a delete is "a PK voided at ts." So how is "<strong>whether a row is visible right now</strong>" decided? The answer is the core rule of <strong>MVCC (multi-version concurrency control)</strong> — <strong>everything is judged by timestamp</strong>. MVCC doesn't "remove" or "overwrite" anything; it keeps all versions on the time axis and hands the question of "which version counts" to the timestamp a read carries.</p>

<p>A read carries a <strong>guarantee timestamp T</strong> (guarantee-ts, determined by the consistency level, expanded in Lesson 30). A row is <strong>visible</strong> to this read <strong>if and only if</strong> two conditions both hold:</p>

<div class="cellgroup">
  <div class="cg-cap">MVCC visibility rule: read at guarantee-ts T, a row is visible ⇔ already inserted AND not voided by an earlier tombstone</div>
  <div class="cells">
    <div class="cell hl"><span class="lab">condition 1</span><span class="q">the row's insert ts ≤ T (born before T)</span></div>
    <div class="cell sep"><span class="lab">and</span><span class="q">AND</span></div>
    <div class="cell hl"><span class="lab">condition 2</span><span class="q">no tombstone with ts ≤ T voids it (not deleted as of T)</span></div>
  </div>
</div>

<p>Apply this rule to the earlier example and it's crystal clear. For PK 102: reading at <strong>T=t5</strong>, you see <strong>v0</strong> (inserted@t3 ≤ t5, while voided@t8 is still in the future, not yet in effect); reading at <strong>T=t9</strong>, v0 is voided by the t8 tombstone and invisible, so you see <strong>v1</strong> (inserted@t8 ≤ t9).
<strong>The same underlying data, with a different read timestamp T, carves out a different point-in-time snapshot</strong> — that is the power of "multi-version": writers just <strong>keep appending</strong> new versions and tombstones, while a reader, with one T, <strong>cleanly carves out</strong> a consistent "as-of-now" view, and reads and writes never block each other.</p>

<p>This concurrency model of "reads take a snapshot, writes append" yields a property extremely precious in a distributed vector DB: <strong>reads and writes never wait on or lock each other</strong>. In a traditional database, "modifying while reading" often means lock contention, reads blocked by writes; under MVCC, the new versions and tombstones being continuously written <strong>simply don't disturb</strong> a query running at an earlier T — that query always sees the <strong>consistent snapshot</strong> corresponding to its departure moment T, even if the underlying data has since been changed beyond recognition.
For a vector DB needing <strong>high-throughput writes yet stable low-latency retrieval</strong>, this is vital: massive inserts, deletes, and upserts keep appending to the tail of the time axis, while every search grabs a T to cleanly "<strong>freeze</strong>" a motionless world to retrieve over — the two run on separate tracks, never dragging each other down. This is what the words "<strong>multi-version</strong>" truly buy — not to preserve history, but to <strong>decouple reads and writes along the time axis</strong>.</p>

<div class="timeline">
  <div class="lane"><span class="lane-label">events of PK 102</span><span class="tslot">insert v0 @t3</span><span class="tslot">tombstone void @t8</span><span class="tslot span">insert v1 @t8</span></div>
  <div class="lane"><span class="lane-label">read T=t5</span><span class="tslot now">see v0 (t8 is future)</span></div>
  <div class="lane"><span class="lane-label">read T=t9</span><span class="tslot now">see v1 (v0 voided)</span></div>
</div>

<p>This key of "<strong>timestamp decides visibility</strong>" is the very foundation by which Milvus reconciles <strong>consistency</strong> and <strong>high concurrency</strong> in a distributed setting. It needs no read/write locks on the data; instead it lets "reads" and "writes" each advance along the time axis: writes only append, a read takes a snapshot.
But it leaves one question unanswered: <strong>how exactly is that guarantee timestamp T set?</strong> How long must reading "the latest" wait to guarantee seeing everything? That is the stage of <strong>consistency levels</strong> (Strong / Bounded / Eventual, etc.) — they trade off "how fresh you see" against "how long you wait." The full mechanism — how TSO issues numbers, how the delegator waits on watermarks, how snapshots align — is reserved for <strong>Lesson 30</strong>. For this lesson, firmly remember the unifying rule: <strong>an insert stamps a row's birthday, a delete stamps its deathday; a read holding T sees only rows whose "birthday ≤ T and deathday > T or none."</strong> Hold this rule firmly and you grasp the single yardstick spanning all three write operations — insert, delete, and upsert.</p>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: on append-only storage, <strong>a delete is not an erase but stamping a timestamped tombstone</strong> — it enters the WAL as a <strong>delete message</strong>, settles into an <strong>L0 deltalog</strong>, is routed by <strong>bloom filters</strong> (<span class="inline">PrimaryKeyStats</span>'s <span class="inline">BF</span>, <span class="mono">internal/storage/stats.go</span>) to segments that might hold the PK, and is finally physically applied by <strong>Level0DeleteCompaction</strong> (Lesson 19). <strong>upsert = delete + insert</strong> (same PK, a new version with later ts). Unifying it all is <strong>timestamp-based MVCC</strong>: read at guarantee-ts T, a row is visible ⇔ insert ts ≤ T and no tombstone with ts ≤ T voids it; how T is set is decided by the consistency level (Lesson 30).
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Delete is a tombstone</strong>: a delete becomes a WAL delete message (PK + ts), settling into L0 delete data / deltalogs, with no in-place erase.</li>
    <li><strong>Bloom routing</strong>: ask each segment's bloom with the to-delete PK (<span class="inline">PrimaryKeyStats.BF</span>, <span class="mono">internal/storage/stats.go</span>); "definitely not" segments are skipped, the tombstone lands only on "maybe" segments; no false negatives guarantees no wrong delete.</li>
    <li><strong>Physical apply</strong>: L0 tombstones are truly sunk and applied into segments by Level0DeleteCompaction (Lesson 19); the write side only books fast.</li>
    <li><strong>upsert = delete + insert</strong>: for the same PK, delete then insert, old and new versions distinguished by ts; reuses all delete and insert machinery, no special path.</li>
    <li><strong>Timestamp-based MVCC</strong>: read at guarantee-ts T, a row is visible ⇔ insert ts ≤ T and no tombstone with ts ≤ T; the same data with a different T is a different snapshot, reads and writes never block.</li>
    <li><strong>How T is set</strong>: the consistency level (Strong/Bounded/Eventual) trades "how fresh vs how long to wait"; full mechanism in Lesson 30.</li>
  </ul>
</div>
""",
}
