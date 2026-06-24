"""Content for Part 3 (distributed architecture). M3 ships lessons 09-14.

Each lesson is a bilingual dict {"zh": html, "en": html}, mirroring the
authoring model of part1.py / part2.py: lead -> analogy card -> macro card ->
>=3 visual diagrams per language -> cited code (file+symbol) -> key-points card.
Milvus facts are verified against the repo at /home/verden/course/milvus:
- component interfaces in internal/types/types.go (Component, RootCoord,
  DataCoord, QueryCoord, Proxy, QueryNode, DataNode, MixCoord which embeds the
  three coordinator gRPC servers);
- MixCoord packaging in internal/coordinator/mix_coord.go, gRPC wrapper in
  internal/distributed/mixcoord;
- proxy task scheduler queues ddQueue/dmQueue/dqQueue in
  internal/proxy/task_scheduler.go;
- TSO via tso2.NewGlobalTSOAllocator + id alloc via allocator.NewGlobalIDAllocator
  in internal/rootcoord/root_coord.go; IMetaTable in internal/rootcoord/meta_table.go;
- SegmentState_* lives in milvus-proto commonpb (go-api/v3), used in
  internal/datacoord/segment_manager.go;
- querycoordv2 Balance interface in internal/querycoordv2/balance/balance.go,
  dist/target/replica managers under internal/querycoordv2/meta;
- catalog interfaces in internal/metastore/catalog.go; kv interfaces in
  pkg/kv/kv.go (BaseKV/TxnKV/MetaKv/WatchKV); sessions in
  internal/util/sessionutil/session_util.go.
"""

LESSON_09 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前两部分讲清了"向量是什么"和"数据怎么存"。从这一课起，我们把镜头拉到<strong>整个集群</strong>：Milvus 由一群进程协作完成工作，
而它们之间最根本的分工，就是<strong>控制面（control plane）</strong>与<strong>数据面（data plane）</strong>——前者<strong>决定谁该做什么</strong>，
后者<strong>真正把活干掉</strong>。理解了这条主线，后面 RootCoord、DataCoord、QueryCoord、Proxy 各司其职的故事才会条理分明。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把 Milvus 想成一座<strong>机场</strong>：<strong>塔台</strong>不搬一件行李、不开一架飞机，但它掌握全局——哪架飞机走哪条跑道、停哪个登机口、几点起飞，
  这是<strong>控制面</strong>。而<strong>飞机和地勤</strong>才是真正运送旅客与货物的人，他们<strong>听从塔台调度</strong>，但塔台从不替他们扛箱子，这是<strong>数据面</strong>。
  塔台关心的是"<strong>调度与元数据</strong>"，飞机关心的是"<strong>执行与吞吐</strong>"。两者一旦混在一起，机场就会瘫痪。
</div>

<h2>两个面：决策与执行</h2>
<p>Milvus 把所有进程按职责切成两层。<strong>控制面（协调者 / coordinators）</strong>管<strong>元数据、调度、分配</strong>：集合的 schema 长什么样、
段（segment）该分到哪台机器、哪个 QueryNode 负责哪个分片、什么时候触发 flush 与 compaction……它们<strong>做决定</strong>，但几乎不碰用户的真实数据流。
<strong>数据面（节点 / nodes）</strong>则是<strong>干活的人</strong>：Proxy 接收请求、QueryNode 在内存里做向量检索、DataNode 把写入落盘成段、StreamingNode 承载写入日志。
它们<strong>听协调者的安排</strong>，但真正的吞吐压力都压在它们身上。换句话说，控制面回答的是"<strong>该怎么办</strong>"，数据面回答的是"<strong>现在就办</strong>"；
前者是一张随时更新的"作战地图"，后者是地图上正在冲锋的部队。本课接下来要做的，就是把这张地图的图例（接口）、指挥部的编制（MixCoord）、以及部队与指挥部如何通信（服务发现）一一讲清。</p>

<p>这种"控制面窄、数据面宽"还有一个微妙之处值得点破：<strong>Proxy 虽属数据面，却不存任何用户数据</strong>。它是"无状态网关"——只做校验、鉴权、限流、分派，
把请求拆给协调者要时间戳、向节点要结果，自己不持有段也不持有索引。正因如此，Proxy 可以像 Web 服务器一样<strong>随意加减实例</strong>，前面挂个负载均衡即可。
这提醒我们：控制面/数据面是按"是否承载用户吞吐"划分的，而不是按"是否存数据"。Proxy 在数据面，是因为它<strong>站在吞吐链路上</strong>；
而它能轻松扩缩，又恰恰因为它<strong>无状态</strong>。把"承载吞吐"和"持有状态"这两件事分开看，你才能准确理解每个组件的扩缩容策略。</p>

<p>这种分层不是为了好看，而是为了<strong>可扩展与高可用</strong>：决策逻辑（元数据、调度）天然是"少而关键"的，适合集中、强一致地管理；
执行逻辑（检索、写盘）天然是"多而繁重"的，适合横向铺开、按负载扩容。把两者拆开，你就能<strong>单独扩展数据面</strong>（加 QueryNode 提升查询吞吐）
而不必动控制面，反之亦然。这正是"存算分离"在进程层面的延伸——上一部分讲的 etcd、对象存储、消息队列，是<strong>外部依赖</strong>；
这一部分讲的控制面/数据面，是<strong>Milvus 自身进程</strong>的分工。</p>

<p>分层还带来一个常被忽视的好处：<strong>故障隔离</strong>。数据面节点是"无状态"的——它内存里的索引和段，都是从对象存储里加载、可随时重建的副本，
真正的"权威元数据"只在控制面与 etcd 里。于是一台 QueryNode 突然崩溃，丢的只是"一份内存副本"，控制面立刻把它负责的分片重新分给别人，
对外几乎无感。反过来，控制面虽然关键，但它处理的请求量小、逻辑稳定，可以用更保守的方式（如多副本、强一致存储）保护。
<strong>把"易变易崩的重活"和"稳定关键的决策"分开，正是分布式系统抗故障的基本功</strong>。</p>

<p>再给一组直觉上的数量级对比：一个集群里，协调者通常只有<strong>个位数</strong>个实例（甚至就一个 MixCoord），而 QueryNode / DataNode 可以有<strong>几十上百</strong>个。
请求量上，控制面每秒处理的多是"建表、加载、上报心跳"这类<strong>低频</strong>操作，而数据面每秒要扛<strong>成千上万</strong>条 search/insert。
这种"<strong>控制面窄、数据面宽</strong>"的形状，决定了二者必须用完全不同的设计取向——前者求稳求准，后者求快求多。</p>

<div class="layers">
  <div class="layer l-core"><div class="lh"><span class="badge">控制面</span><span class="name">Coordinators</span></div>
    <div class="ld">RootCoord（DDL 与身份）、DataCoord（写入侧与存储）、QueryCoord（读取侧）。掌管元数据、时间戳、段与分片的<strong>分配与调度</strong>；做决定，不扛吞吐。今天打包进一个 <strong>MixCoord</strong> 进程。</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">数据面 · 网关</span><span class="name">Proxy</span></div>
    <div class="ld">所有客户端请求的唯一入口：校验、鉴权、限流，再把任务分派给协调者与节点。无状态，可横向扩展。</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">数据面 · 执行</span><span class="name">QueryNode / DataNode / StreamingNode</span></div>
    <div class="ld">QueryNode 在内存里做检索；DataNode 把写入落盘成段、跑 compaction 与建索引的实际工作；StreamingNode 承载写入日志（WAL）。真正的 CPU/内存/IO 压力都在这一层。</div></div>
  <div class="layer l-app"><div class="lh"><span class="badge">外部依赖</span><span class="name">etcd · 对象存储 · 消息队列</span></div>
    <div class="ld">第 8 课讲过：元数据/服务发现给 etcd，数据与索引给对象存储，写入日志给消息队列。控制面与数据面都站在它们之上。</div></div>
</div>

<h2>组件接口：types.go 里的契约</h2>
<p>这套分工不是口头约定，而是写死在 Go 接口里的。<span class="inline">internal/types/types.go</span> 用一组接口定义了"每个组件长什么样"。
最底层是一个共同基座 <span class="inline">Component</span>：任何组件，无论协调者还是节点，都必须实现 <span class="mono">Init / Start / Stop / Register</span> 四个方法——
<strong>初始化、启动、停止、向 etcd 注册自己</strong>。这四个动词就是一个分布式组件的"生命周期最小集"。</p>

<p>在 <span class="inline">Component</span> 之上，每类组件再叠加自己的业务方法：<span class="inline">RootCoord</span> 管 DDL，<span class="inline">DataCoord</span> 管段，
<span class="inline">QueryCoord</span> 管加载，<span class="inline">Proxy</span> 是网关，<span class="inline">QueryNode</span> / <span class="inline">DataNode</span> 是执行节点。
其中最特别的是 <span class="inline">MixCoord</span>：它<strong>同时嵌入了三个协调者的 gRPC 服务接口</strong>，等于"一个接口、三种角色"。</p>

<p>用接口而不是具体类型当"契约"，在工程上有两个实打实的好处。其一是<strong>可替换</strong>：同一个接口，本地调用时是直连实现，跨进程时是 gRPC 客户端代理，
上层代码完全不必关心对方在本机还是在另一台机器——这正是 <span class="inline">internal/distributed/</span> 那层 gRPC 包装能"无缝插入"的前提。
其二是<strong>可测试</strong>：接口能被 mock 出来，于是测 Proxy 的逻辑时不必真的拉起一个 MixCoord，给它一个假的实现即可。
你会看到源码里大量 <span class="mono">//go:generate mockery</span> 注释，就是在为这些接口自动生成 mock。<strong>接口是分布式系统的"可插拔接缝"</strong>，这条思路贯穿整个 Milvus。</p>

<table class="t">
  <tr><th>接口</th><th>角色（管什么）</th><th>所在面</th><th>实现包</th></tr>
  <tr><td class="mono">Component</td><td>所有组件的基座：Init/Start/Stop/Register</td><td>—</td><td class="mono">internal/types</td></tr>
  <tr><td class="mono">RootCoord</td><td>DDL、元数据表、TSO、全局 ID</td><td>控制面</td><td class="mono">internal/rootcoord</td></tr>
  <tr><td class="mono">DataCoord</td><td>段分配、flush、compaction、GC、索引调度</td><td>控制面</td><td class="mono">internal/datacoord</td></tr>
  <tr><td class="mono">QueryCoord</td><td>加载/释放、段与分片分配、均衡、副本</td><td>控制面</td><td class="mono">internal/querycoordv2</td></tr>
  <tr><td class="mono">Proxy</td><td>请求入口：校验、鉴权、限流、分派</td><td>数据面</td><td class="mono">internal/proxy</td></tr>
  <tr><td class="mono">QueryNode</td><td>内存中执行向量检索</td><td>数据面</td><td class="mono">internal/querynodev2</td></tr>
  <tr><td class="mono">DataNode</td><td>落盘成段、跑 compaction、建索引</td><td>数据面</td><td class="mono">internal/datanode</td></tr>
  <tr><td class="mono">MixCoord</td><td>把三个协调者打包进一个进程</td><td>控制面</td><td class="mono">internal/coordinator</td></tr>
</table>

<p>下面这段就是契约的核心：<span class="inline">Component</span> 的四个方法，以及 <span class="inline">MixCoord</span> 如何把三个协调者的服务接口
<strong>一口气嵌进来</strong>。注意 <span class="mono">RootCoordServer / QueryCoordServer / DataCoordServer</span> 是 proto 生成的 gRPC 服务接口，
它们来自 <span class="mono">milvus-proto</span> 的 <span class="mono">rootcoordpb / querypb / datapb</span> 包，而不是 Milvus 仓库里手写的类型。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/types/types.go</span><span class="ln">Component / MixCoord 接口</span></div>
  <pre><span class="cm">// 所有组件的共同基座：生命周期最小集</span>
<span class="kw">type</span> Component <span class="kw">interface</span> {
    Init() <span class="kw">error</span>
    Start() <span class="kw">error</span>
    Stop() <span class="kw">error</span>
    Register() <span class="kw">error</span>   <span class="cm">// 向 etcd 注册自己（服务发现）</span>
}

<span class="cm">// MixCoord：一个接口，嵌入三个协调者的 gRPC 服务</span>
<span class="kw">type</span> MixCoord <span class="kw">interface</span> {
    Component
    rootcoordpb.RootCoordServer   <span class="cm">// RootCoord 角色</span>
    querypb.QueryCoordServer      <span class="cm">// QueryCoord 角色</span>
    datapb.DataCoordServer        <span class="cm">// DataCoord 角色</span>
    <span class="cm">// ... 外加少量跨协调者的聚合方法</span>
}</pre>
</div>

<h2>MixCoord：一个进程，三个角色</h2>
<p>很多人第一次看 Milvus 架构图会数出"三个协调者进程"，但<strong>今天的真实部署里，它们被打包进同一个进程——MixCoord</strong>。
也就是说，RootCoord、DataCoord、QueryCoord 在<strong>逻辑上是三个角色</strong>，但在<strong>物理上是一个可执行体</strong>。
这个打包逻辑在 <span class="inline">internal/coordinator/mix_coord.go</span> 里：一个 <span class="mono">mixCoordImpl</span> 同时持有三套协调者的实现，对外用 <span class="mono">NewMixCoordServer</span> 启动。</p>

<p>为什么这么做？因为三个协调者之间<strong>交互极其频繁</strong>（DataCoord 要问 RootCoord 要时间戳、QueryCoord 要问 DataCoord 段在哪里），
把它们放进一个进程能<strong>省掉大量跨进程 RPC</strong>，部署也更简单。但接口仍然<strong>各自独立</strong>，意味着将来若有需要，依旧能拆回三个进程而不动业务逻辑。
对外，<span class="inline">internal/distributed/mixcoord</span> 把它包成一个 gRPC 服务器——注意 <span class="inline">internal/distributed/</span> 下<strong>没有</strong>单独的 rootcoord/datacoord/querycoord 目录，
正印证了"三合一"的现状。</p>

<p>这其实是 Milvus 架构演进的一个缩影。早期版本里，三个协调者是<strong>三个独立进程</strong>，各自启动、各自注册、彼此用 gRPC 通信；
这在概念上很干净，但运维上要管三套进程，且协调者之间频繁的内部调用都得走网络，徒增延迟。后来社区把它们<strong>合并成 MixCoord</strong>：
对内三套实现共享同一进程、直接函数调用；对外仍暴露三套服务接口，向后兼容。<strong>"逻辑上分、物理上合"</strong>是一种典型的工程折中——
它保留了清晰的职责边界（接口不变），又收割了同进程协作的性能与运维红利。所以当你看老一点的设计文档说"DataCoord 进程"时，别困惑：
那是<strong>角色名</strong>，今天它住在 MixCoord 这套房子里。本教程统一遵循"代码为准"：以仓库里真实的 <span class="mono">mixCoordImpl</span> 为现状描述。</p>

<div class="cols">
  <div class="col"><h4>控制面在想什么</h4><p>"这个新集合的元数据存哪？""这批新写入该开一个新段还是续用旧段？""这个 QueryNode 挂了，它负责的分片谁来接？"
  ——全是<strong>决策与分配</strong>问题。控制面要的是<strong>正确、一致、全局视角</strong>，不追求高吞吐。</p></div>
  <div class="col"><h4>数据面在想什么</h4><p>"这条 search 请求，我在自己内存里的索引上算 topK""这批 insert，我追加到当前段的列存里""这个段太碎了，我把它和邻居合并"
  ——全是<strong>执行</strong>问题。数据面要的是<strong>快、并行、可水平扩容</strong>，单点挂掉不影响全局元数据。</p></div>
</div>

<h2>服务发现与会话：etcd 怎么把它们粘起来</h2>
<p>进程拆成两面之后，新问题来了：Proxy 怎么知道 MixCoord 在哪个地址？QueryCoord 怎么知道现在有几台活着的 QueryNode？
答案是 <strong>etcd 上的会话（session）机制</strong>。每个组件启动时执行 <span class="mono">Register()</span>，在 etcd 里写下一条带<strong>租约（lease）</strong>的 session 记录——
"我是 querynode-3，地址在这里，我还活着"。租约要靠<strong>定期续约</strong>维持，一旦进程崩溃、心跳停止，租约到期、记录自动消失。</p>

<p>另一端，协调者<strong>watch</strong>这些 session 的目录：有节点上线，watch 立刻收到"新增"事件；有节点掉线，收到"删除"事件。
于是控制面始终掌握着<strong>当前活着的节点清单</strong>，可以据此分配段、做均衡、在故障时把工作转移给别人。这套"注册—续约—监听"就是 Milvus 的<strong>服务发现</strong>，
也是控制面/数据面能动态协作的底座。它的实现我们留到第 14 课细看，这里先记住它的角色。</p>

<p>这里有个容易混淆的点：<strong>session 里存的是"地址"，不是"数据"</strong>。etcd 在这条链路上扮演的是"通讯录 + 心跳板"，它告诉你"谁在、在哪"，
但真正的 search/insert 流量绝不经过 etcd——那会瞬间把它打爆。组件拿到对方地址后，是<strong>点对点直连 gRPC</strong> 发请求的。
把 etcd 想成机场的<strong>航班信息屏</strong>：它显示哪架飞机在哪个登机口，但旅客是走廊桥直接登机，而不是挤到信息屏前面去。
这条"控制信息走 etcd、数据流量走直连"的分界，和本课的控制面/数据面是同一种哲学在不同层面的复现。</p>

<div class="flow">
  <div class="node"><div class="nt">节点启动</div><div class="nd">QueryNode/DataNode…</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">Register()</div><div class="nd">写带租约的 session 到 etcd</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">协调者 watch</div><div class="nd">收到"节点上线"事件</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">分配工作</div><div class="nd">把段/分片派给它</div></div>
</div>

<p>把这一课收束成一句话：Milvus 是一支<strong>分工明确的团队</strong>——协调者动脑、节点动手，etcd 当通讯录。
读懂了"谁决策、谁执行、靠什么互相找到"，接下来四课分别深入每个协调者时，你就能始终把它放回这张大图里，不至于迷失在细节里。</p>

<h2>三条边界纪律：别让两个面互相越界</h2>
<p>有了大图，最后给三条"边界纪律"，它们能帮你在读后面源码时迅速判断"这段逻辑该属于哪个面"。<strong>第一条：权威元数据只属于控制面</strong>。
集合 schema、段的归属、分片的分配，这些"真相"只能由协调者写、由 etcd 与元数据存储持久化；数据面节点哪怕在内存里缓存了一份，也只是<strong>只读副本</strong>，
随时可丢、随时可重建。任何"节点擅自改元数据"都是设计上的越界。</p>

<p><strong>第二条：用户数据吞吐只属于数据面</strong>。一条 search 的几千次距离计算、一批 insert 的列存追加，绝不能跑到协调者身上——否则控制面会被海量请求压垮，
全局调度随之停摆。协调者只在"决策时刻"被触达：建表、加载、上报、故障转移，都是低频事件。<strong>把高频吞吐挡在控制面之外，是保证集群稳定的红线</strong>。</p>

<p><strong>第三条：跨面通信只走接口与 etcd</strong>。两个面不靠"共享内存"或"偷看对方文件"协作，而是要么通过 <span class="inline">types.go</span> 定义的接口发 RPC，
要么通过 etcd 的 session 与 watch 间接感知。这条纪律换来的是<strong>松耦合</strong>：你可以独立升级、重启、扩缩任意一个组件，只要它仍遵守接口契约、仍按时续约 session，
整个系统就能继续运转。后面每深入一个协调者，不妨都用这三条纪律回看一眼——它能帮你把纷繁的细节，重新归位到"决策 vs 执行"这条主线上。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话串起来：<strong>控制面（协调者）决定谁做什么 → 数据面（节点）真正执行 → types.go 用接口写死契约 → MixCoord 把三个协调者打包成一个进程 → etcd 的 session 让两面互相发现</strong>。
  这张"决策 vs 执行"的大图，是后面 RootCoord / DataCoord / QueryCoord / Proxy 每一课的共同坐标系。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>两个面</strong>：控制面=协调者（管元数据、调度、分配，做决定）；数据面=节点（Proxy/QueryNode/DataNode，真正干活）。</li>
    <li><strong>接口契约</strong>：<span class="mono">internal/types/types.go</span> 里，<span class="mono">Component</span>（Init/Start/Stop/Register）是基座，各组件在其上叠加业务方法。</li>
    <li><strong>MixCoord</strong>：三个协调者今天打包进一个进程（<span class="mono">internal/coordinator/mix_coord.go</span>），它<strong>嵌入三套 gRPC 服务接口</strong>——逻辑三角色、物理一进程。</li>
    <li><strong>分层为了扩展</strong>：少而关键的决策集中管理，多而繁重的执行横向扩容，两面可独立伸缩。</li>
    <li><strong>服务发现</strong>：组件用 <span class="mono">Register()</span> 在 etcd 写带租约的 session，协调者 watch 它们，实现动态上线/下线感知（详见第 14 课）。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Parts 1 and 2 covered "what a vector is" and "how data is stored." From here we zoom out to the <strong>whole cluster</strong>:
Milvus is a group of cooperating processes, and their most fundamental division of labor is the <strong>control plane</strong> vs the
<strong>data plane</strong> — the former <strong>decides who does what</strong>, the latter <strong>actually does the work</strong>.
Grasp this through-line and the next four lessons on RootCoord, DataCoord, QueryCoord, and Proxy fall neatly into place.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Picture Milvus as an <strong>airport</strong>. The <strong>control tower</strong> carries no luggage and flies no plane, yet it holds the
  global picture — which runway each plane takes, which gate it parks at, when it departs. That is the <strong>control plane</strong>.
  The <strong>planes and ground crew</strong> are who actually move passengers and cargo; they <strong>obey the tower</strong>, but the tower never
  hauls a box for them. That is the <strong>data plane</strong>. The tower cares about <strong>scheduling and metadata</strong>; the planes care about
  <strong>execution and throughput</strong>. Mix the two and the airport grinds to a halt.
</div>

<h2>Two planes: deciding vs executing</h2>
<p>Milvus splits every process by responsibility. The <strong>control plane (coordinators)</strong> owns <strong>metadata, scheduling, assignment</strong>:
what a collection's schema looks like, which machine a segment goes to, which QueryNode serves which shard, when to trigger flush and compaction.
They <strong>make decisions</strong> but barely touch the user's real data stream. The <strong>data plane (nodes)</strong> are the <strong>workers</strong>: Proxy receives requests,
QueryNode runs vector search in memory, DataNode persists writes into segments, StreamingNode carries the write log. They <strong>follow the coordinators</strong>,
yet all the throughput pressure lands on them. Put differently, the control plane answers "<strong>what should be done</strong>" and the data plane answers "<strong>do it now</strong>";
the former is a constantly-updated battle map, the latter the troops charging across it. The rest of this lesson explains that map's legend (the interfaces), the headquarters' org chart (MixCoord), and how troops and HQ communicate (service discovery).</p>

<p>This "narrow control, wide data" shape has a subtle point worth naming: <strong>Proxy is in the data plane yet stores no user data</strong>. It's a "stateless gateway" — it only validates, authenticates, rate-limits, and dispatches,
asking coordinators for timestamps and nodes for results, holding no segments and no indexes itself. Precisely because of that, Proxy can <strong>add and remove instances freely</strong> like a web server, with a load balancer in front.
The lesson: the control/data split is by "does it carry user throughput," not by "does it store data." Proxy is in the data plane because it <strong>sits on the throughput path</strong>;
and it scales easily exactly because it is <strong>stateless</strong>. Separate "carries throughput" from "holds state" and you can read each component's scaling strategy correctly.</p>

<p>This layering isn't cosmetic — it exists for <strong>scalability and availability</strong>. Decision logic (metadata, scheduling) is "few but critical"
and suits centralized, strongly-consistent management; execution logic (search, persistence) is "many and heavy" and suits spreading out and scaling by load.
Split them and you can <strong>scale the data plane alone</strong> (add QueryNodes for query throughput) without touching the control plane, and vice versa.
This is "storage-compute separation" extended to the process level — the etcd / object storage / message queue from Part 2 are <strong>external dependencies</strong>;
the control/data plane here is the division of labor among <strong>Milvus's own processes</strong>.</p>

<p>Layering brings an often-overlooked benefit: <strong>fault isolation</strong>. Data-plane nodes are "stateless" — the indexes and segments in their memory are
replicas loaded from object storage and rebuildable at any time; the real "authoritative metadata" lives only in the control plane and etcd. So when a QueryNode
suddenly crashes, all that's lost is "one in-memory copy"; the control plane immediately reassigns its shards to others, almost invisibly to clients. Conversely,
the control plane is critical but handles little traffic with stable logic, so it can be protected more conservatively (multi-replica, strongly-consistent storage).
<strong>Separating "the volatile, crash-prone heavy lifting" from "the stable, critical decisions" is a basic fault-tolerance discipline in distributed systems.</strong></p>

<p>Here's an order-of-magnitude intuition: in a cluster, coordinators usually number in the <strong>single digits</strong> (often just one MixCoord), while QueryNodes / DataNodes
can be in the <strong>dozens or hundreds</strong>. By traffic, the control plane mostly handles <strong>low-frequency</strong> operations per second — create-table, load, heartbeat reports —
while the data plane carries <strong>thousands</strong> of search/insert per second. This "<strong>narrow control plane, wide data plane</strong>" shape forces the two to adopt
entirely different design stances: the former optimizes for stability and correctness, the latter for speed and volume.</p>

<div class="layers">
  <div class="layer l-core"><div class="lh"><span class="badge">control plane</span><span class="name">Coordinators</span></div>
    <div class="ld">RootCoord (DDL &amp; identity), DataCoord (write side &amp; storage), QueryCoord (read side). Own metadata, timestamps, and the <strong>assignment/scheduling</strong> of segments and shards; they decide, they don't shoulder throughput. Today packed into one <strong>MixCoord</strong> process.</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">data plane · gateway</span><span class="name">Proxy</span></div>
    <div class="ld">The single entry for all client requests: validate, authenticate, rate-limit, then dispatch tasks to coordinators and nodes. Stateless, horizontally scalable.</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">data plane · execute</span><span class="name">QueryNode / DataNode / StreamingNode</span></div>
    <div class="ld">QueryNode searches in memory; DataNode persists writes into segments and runs the real compaction/index-build work; StreamingNode carries the write log (WAL). All the CPU/memory/IO pressure lives here.</div></div>
  <div class="layer l-app"><div class="lh"><span class="badge">external deps</span><span class="name">etcd · object storage · message queue</span></div>
    <div class="ld">From Lesson 8: metadata/service-discovery to etcd, data/indexes to object storage, the write log to the message queue. Both planes stand on top of these.</div></div>
</div>

<h2>Component interfaces: the contract in types.go</h2>
<p>This division isn't a verbal agreement — it's frozen into Go interfaces. <span class="inline">internal/types/types.go</span> defines "what each component looks like."
At the very bottom is a shared base, <span class="inline">Component</span>: any component, coordinator or node, must implement four methods <span class="mono">Init / Start / Stop / Register</span> —
<strong>initialize, start, stop, and register itself with etcd</strong>. Those four verbs are the minimal lifecycle of a distributed component.</p>

<p>Above <span class="inline">Component</span>, each component adds its own business methods: <span class="inline">RootCoord</span> owns DDL, <span class="inline">DataCoord</span> owns segments,
<span class="inline">QueryCoord</span> owns loading, <span class="inline">Proxy</span> is the gateway, <span class="inline">QueryNode</span> / <span class="inline">DataNode</span> are execution nodes.
The special one is <span class="inline">MixCoord</span>: it <strong>embeds all three coordinators' gRPC service interfaces at once</strong> — "one interface, three roles."</p>

<p>Using interfaces rather than concrete types as the "contract" buys two real engineering wins. First, <strong>substitutability</strong>: the same interface is a direct implementation for a local call
and a gRPC client proxy across processes, so upper-layer code never cares whether the peer is on this machine or another — exactly what lets the gRPC wrappers in <span class="inline">internal/distributed/</span> slot in seamlessly.
Second, <strong>testability</strong>: an interface can be mocked, so testing Proxy logic needs no real MixCoord — just hand it a fake implementation. You'll see many <span class="mono">//go:generate mockery</span>
comments in the source generating mocks for these very interfaces. <strong>Interfaces are the "pluggable seams" of a distributed system</strong>, a theme running through all of Milvus.</p>

<table class="t">
  <tr><th>Interface</th><th>Role (owns what)</th><th>Plane</th><th>Impl package</th></tr>
  <tr><td class="mono">Component</td><td>Base of all: Init/Start/Stop/Register</td><td>—</td><td class="mono">internal/types</td></tr>
  <tr><td class="mono">RootCoord</td><td>DDL, meta table, TSO, global IDs</td><td>control</td><td class="mono">internal/rootcoord</td></tr>
  <tr><td class="mono">DataCoord</td><td>segment alloc, flush, compaction, GC, index sched</td><td>control</td><td class="mono">internal/datacoord</td></tr>
  <tr><td class="mono">QueryCoord</td><td>load/release, segment &amp; shard assign, balance, replicas</td><td>control</td><td class="mono">internal/querycoordv2</td></tr>
  <tr><td class="mono">Proxy</td><td>request entry: validate, auth, rate-limit, dispatch</td><td>data</td><td class="mono">internal/proxy</td></tr>
  <tr><td class="mono">QueryNode</td><td>execute vector search in memory</td><td>data</td><td class="mono">internal/querynodev2</td></tr>
  <tr><td class="mono">DataNode</td><td>persist segments, run compaction, build indexes</td><td>data</td><td class="mono">internal/datanode</td></tr>
  <tr><td class="mono">MixCoord</td><td>packs the three coordinators into one process</td><td>control</td><td class="mono">internal/coordinator</td></tr>
</table>

<p>Here is the heart of the contract: <span class="inline">Component</span>'s four methods, and how <span class="inline">MixCoord</span> <strong>embeds all three coordinator service interfaces in one breath</strong>.
Note that <span class="mono">RootCoordServer / QueryCoordServer / DataCoordServer</span> are proto-generated gRPC service interfaces from
<span class="mono">milvus-proto</span>'s <span class="mono">rootcoordpb / querypb / datapb</span> packages, not hand-written types in the Milvus repo.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/types/types.go</span><span class="ln">Component / MixCoord interfaces</span></div>
  <pre><span class="cm">// Shared base of every component: the minimal lifecycle</span>
<span class="kw">type</span> Component <span class="kw">interface</span> {
    Init() <span class="kw">error</span>
    Start() <span class="kw">error</span>
    Stop() <span class="kw">error</span>
    Register() <span class="kw">error</span>   <span class="cm">// register self with etcd (service discovery)</span>
}

<span class="cm">// MixCoord: one interface embedding three coordinators' gRPC services</span>
<span class="kw">type</span> MixCoord <span class="kw">interface</span> {
    Component
    rootcoordpb.RootCoordServer   <span class="cm">// the RootCoord role</span>
    querypb.QueryCoordServer      <span class="cm">// the QueryCoord role</span>
    datapb.DataCoordServer        <span class="cm">// the DataCoord role</span>
    <span class="cm">// ... plus a few cross-coordinator aggregate methods</span>
}</pre>
</div>

<h2>MixCoord: one process, three roles</h2>
<p>On first look at a Milvus diagram, many people count "three coordinator processes," but <strong>in today's real deployment they are packed into one process — MixCoord</strong>.
That is, RootCoord, DataCoord, and QueryCoord are <strong>three roles logically</strong> but <strong>one executable physically</strong>.
The packaging lives in <span class="inline">internal/coordinator/mix_coord.go</span>: a single <span class="mono">mixCoordImpl</span> holds all three coordinator implementations and is started via <span class="mono">NewMixCoordServer</span>.</p>

<p>Why? Because the three coordinators <strong>interact extremely often</strong> (DataCoord asks RootCoord for timestamps; QueryCoord asks DataCoord where segments live).
Putting them in one process <strong>saves a mountain of cross-process RPCs</strong> and simplifies deployment. Yet the interfaces stay <strong>independent</strong>, so they could be split back into three processes later without touching business logic.
Externally, <span class="inline">internal/distributed/mixcoord</span> wraps it as one gRPC server — note there is <strong>no</strong> separate rootcoord/datacoord/querycoord directory under <span class="inline">internal/distributed/</span>,
which confirms the "three-in-one" reality.</p>

<p>This is really a microcosm of Milvus's architectural evolution. In early versions the three coordinators were <strong>three separate processes</strong>, each starting, registering, and talking over gRPC;
conceptually clean, but operationally you managed three sets of processes, and the frequent internal calls between coordinators all crossed the network, adding latency. The community later <strong>merged them into MixCoord</strong>:
internally the three implementations share one process with direct function calls; externally it still exposes all three service interfaces, staying backward-compatible. <strong>"Split logically, merged physically"</strong> is a classic engineering trade-off —
it keeps clear responsibility boundaries (interfaces unchanged) while reaping the performance and ops dividends of same-process collaboration. So when an older design doc says "the DataCoord process," don't be puzzled:
that's a <strong>role name</strong>; today it lives inside the MixCoord house. This guide follows "code is truth," describing the present state via the real <span class="mono">mixCoordImpl</span> in the repo.</p>

<div class="cols">
  <div class="col"><h4>What the control plane thinks</h4><p>"Where do I store this new collection's metadata?" "Should this batch of writes open a new segment or continue an old one?" "This QueryNode died — who takes its shard?"
  — all <strong>decision and assignment</strong> questions. The control plane wants <strong>correctness, consistency, a global view</strong>, not raw throughput.</p></div>
  <div class="col"><h4>What the data plane thinks</h4><p>"This search request — I compute topK on my in-memory index." "This insert — I append to the current segment's columnar store." "This segment is too fragmented — I merge it with neighbors."
  — all <strong>execution</strong> questions. The data plane wants <strong>speed, parallelism, horizontal scaling</strong>; one dying node doesn't lose global metadata.</p></div>
</div>

<h2>Service discovery and sessions: how etcd glues them together</h2>
<p>Once processes split into two planes, a new problem appears: how does Proxy know MixCoord's address? How does QueryCoord know how many QueryNodes are alive right now?
The answer is the <strong>session mechanism on etcd</strong>. On startup each component runs <span class="mono">Register()</span>, writing a session record with a <strong>lease</strong> into etcd —
"I am querynode-3, here's my address, I'm alive." The lease must be kept by <strong>periodic renewal</strong>; once the process crashes and heartbeats stop, the lease expires and the record vanishes automatically.</p>

<p>On the other end, coordinators <strong>watch</strong> these session directories: a node comes up and the watch immediately gets an "added" event; a node drops and it gets a "deleted" event.
Thus the control plane always holds the <strong>current list of live nodes</strong> and can assign segments, rebalance, and on failure shift work to others.
This "register — renew — watch" loop is Milvus's <strong>service discovery</strong>, the foundation that lets the two planes cooperate dynamically. We dive into its implementation in Lesson 14; for now just remember its role.</p>

<p>One easy point of confusion: <strong>a session stores an "address," not "data."</strong> On this path etcd plays "address book + heartbeat board," telling you "who's up and where,"
but the real search/insert traffic never goes through etcd — that would instantly overwhelm it. Once a component has the peer's address, it sends requests over a <strong>direct point-to-point gRPC</strong> connection.
Think of etcd as the airport's <strong>flight information board</strong>: it shows which plane is at which gate, but passengers board via the jet bridge directly rather than crowding around the board.
This split — "control info through etcd, data traffic direct" — is the same philosophy as this lesson's control/data plane, replayed at a different layer.</p>

<div class="flow">
  <div class="node"><div class="nt">node starts</div><div class="nd">QueryNode/DataNode…</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">Register()</div><div class="nd">write leased session to etcd</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">coordinator watches</div><div class="nd">gets "node up" event</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">assign work</div><div class="nd">hand it segments/shards</div></div>
</div>

<p>To wrap this lesson in one line: Milvus is a <strong>team with a clear division of labor</strong> — coordinators think, nodes act, etcd is the address book.
Once you grasp "who decides, who executes, and how they find each other," the next four lessons that drill into each coordinator stay anchored to this big picture, never lost in the details.</p>

<h2>Three boundary disciplines: keep the planes from trespassing</h2>
<p>With the big picture in hand, here are three "boundary disciplines" that help you quickly judge "which plane does this logic belong to" while reading later source.
<strong>One: authoritative metadata belongs only to the control plane.</strong> Collection schema, segment ownership, shard assignment — these "truths" may only be written by coordinators
and persisted by etcd and the metadata store; even if a data-plane node caches a copy in memory, it is just a <strong>read-only replica</strong>, droppable and rebuildable anytime.
Any "node editing metadata on its own" is a design trespass.</p>

<p><strong>Two: user-data throughput belongs only to the data plane.</strong> A search's thousands of distance computations, an insert batch's columnar appends — these must never land on a coordinator,
or the control plane gets crushed by traffic and global scheduling stalls with it. Coordinators are touched only at "decision moments": create-table, load, reporting, failover — all low-frequency events.
<strong>Keeping high-frequency throughput out of the control plane is the red line for cluster stability.</strong></p>

<p><strong>Three: cross-plane communication goes only through interfaces and etcd.</strong> The two planes don't cooperate via "shared memory" or "peeking at each other's files" — they either send RPCs through
the interfaces defined in <span class="inline">types.go</span>, or sense each other indirectly through etcd's sessions and watches. This discipline buys <strong>loose coupling</strong>: you can upgrade, restart, or scale any one
component independently, and as long as it still honors the interface contract and renews its session on time, the whole system keeps running. As you drill into each coordinator later, re-read it through these three disciplines —
they snap the swirl of details back onto the "decide vs execute" through-line.</p>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  In one line: <strong>the control plane (coordinators) decides who does what → the data plane (nodes) actually executes → types.go freezes the contract in interfaces → MixCoord packs the three coordinators into one process → etcd sessions let the two planes discover each other</strong>.
  This "decide vs execute" picture is the shared coordinate system for every later lesson on RootCoord / DataCoord / QueryCoord / Proxy.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Two planes</strong>: control = coordinators (own metadata, scheduling, assignment; decide); data = nodes (Proxy/QueryNode/DataNode; actually work).</li>
    <li><strong>Interface contract</strong>: in <span class="mono">internal/types/types.go</span>, <span class="mono">Component</span> (Init/Start/Stop/Register) is the base; each component adds business methods on top.</li>
    <li><strong>MixCoord</strong>: the three coordinators are packed into one process today (<span class="mono">internal/coordinator/mix_coord.go</span>); it <strong>embeds all three gRPC service interfaces</strong> — three roles logically, one process physically.</li>
    <li><strong>Layering for scale</strong>: few-but-critical decisions centralized; many-and-heavy execution scaled out; the two planes scale independently.</li>
    <li><strong>Service discovery</strong>: components <span class="mono">Register()</span> a leased session in etcd, coordinators watch them — dynamic up/down awareness (detailed in Lesson 14).</li>
  </ul>
</div>
""",
}


LESSON_10 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课我们站在高空俯瞰整个集群：协调者决策、节点执行。这一课聚焦数据面最前线的<strong>Proxy（代理 / 网关）</strong>——
所有客户端请求的<strong>唯一入口</strong>。它既是门卫（校验、鉴权、限流），又是调度员（把请求排进不同队列、分派给协调者与节点），
还是汇总者（把多个分片的结果合并成一份答案）。读懂 Proxy，你就握住了"一次请求从进门到出门"的全貌。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把 Proxy 想成一家大医院的<strong>分诊台</strong>：病人（请求）一进门，分诊台先核对身份与挂号（鉴权）、看你今天号还够不够（限流），
  再按病情把你分到不同<strong>队列</strong>——挂号改信息走"行政窗口"（DDL），打针输液走"治疗区"（DML），做检查看报告走"检验科"（DQL）。
  分诊台自己<strong>不看病、不拍片</strong>，但全院的秩序都靠它维持；它也<strong>不保存病历</strong>，所以可以随时多开几个窗口分担人流——这正是 Proxy"无状态、可横向扩展"的精髓。
</div>

<h2>唯一入口：milvuspb 这套 API 表面</h2>
<p>无论你用 Python SDK、Go SDK 还是 REST，请求最终都会打到 Proxy 暴露的 <strong>gRPC 服务</strong>上。这套服务的契约由 proto 定义，
对应包是 <span class="inline">milvuspb</span>（来自 <span class="mono">milvus-proto/go-api/v3/milvuspb</span>，而非仓库里手写的类型）。一个 <span class="mono">CreateCollection</span>、
一个 <span class="mono">Insert</span>、一个 <span class="mono">Search</span>，在 Proxy 这边都对应一个方法 <span class="mono">func (node *Proxy) Xxx(...)</span>。
换句话说，<strong>Proxy 就是 MilvusService 这套对外 API 的实现体</strong>，而协调者与节点的接口都是"对内"的。</p>

<p>这层"对外/对内"的分界很重要：客户端永远只和 Proxy 说话，看不见也不需要知道后面有几台 QueryNode、段存在哪、TSO 从哪来。
Proxy 把这些复杂度<strong>全部封装</strong>在身后。于是后端怎么扩、怎么改、怎么做故障转移，对客户端都是透明的——API 稳定，拓扑随意。
这也是为什么我们能在第 8 课说"Lite / Standalone / Cluster 同一套 API"：变的是后端规模，不变的是 Proxy 暴露的这张表面。</p>

<p>再往深一层看，Proxy 还承担了一个容易被忽略的角色：<strong>协议与拓扑的翻译官</strong>。客户端发来的是"我要在集合 A 里搜这个向量、要 topK=10"这种<strong>业务语义</strong>，
但后端真正要做的，是"集合 A 现在加载在哪几台 QueryNode 上、它有几个分片、每个分片的 delegator 是谁、要把请求拆成几路发出去"。
这中间的鸿沟，全靠 Proxy 用它缓存的元数据来填平。它要随时跟着集合的加载状态、分片分布而更新这张"路由表"，否则就会把请求发给一台早已不负责该分片的节点。
正因为这份"翻译"工作只读元数据、不改元数据，多个 Proxy 才能各自持有一份缓存、彼此独立地服务，而不需要互相同步——这是它能无状态扩展的<strong>前提条件</strong>。</p>

<div class="flow">
  <div class="node"><div class="nt">客户端 SDK</div><div class="nd">Python / Go / REST</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">Proxy</div><div class="nd">milvuspb 服务实现</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">协调者</div><div class="nd">要时间戳 / 元数据</div></div>
  <div class="arrow">＋</div>
  <div class="node"><div class="nt">节点</div><div class="nd">QueryNode / DataNode 干活</div></div>
</div>

<h2>三道关卡：校验、鉴权、限流</h2>
<p>请求进了 Proxy，并不会立刻被执行，而要先过三道<strong>拦截器（interceptor）</strong>。这是 gRPC 的标准玩法：在真正的业务方法之前，
串接一组中间件，逐个把关。Milvus 把它们拆成独立文件，职责清晰：</p>

<ul>
  <li><strong>鉴权（authentication）</strong>：你是谁？<span class="inline">authentication_interceptor.go</span> 校验用户名/密码或 token，认不出来直接拒。</li>
  <li><strong>权限（privilege）</strong>：你能不能做这件事？<span class="inline">privilege_interceptor.go</span> 检查 RBAC 角色对这个集合/操作有没有授权。</li>
  <li><strong>数据库路由（database）</strong>：你说的是哪个 database？<span class="inline">database_interceptor.go</span> 把请求归到正确的 db 上下文。</li>
  <li><strong>限流（rate limit）</strong>：你今天是不是太猛了？<span class="inline">rate_limit_interceptor.go</span> 按配额给写入/查询降速甚至挡回，保护后端不被打垮。</li>
</ul>

<p>这四关合起来，就是 Proxy 作为"门卫"的全部职责。它们<strong>挡在业务逻辑之前</strong>，意味着一个非法、越权或超额的请求，
根本到不了排队和执行阶段就被拦下——既省后端算力，也守住了安全与稳定的底线。注意这些都是<strong>无状态的判断</strong>（查的是元数据与配额），
所以多开几个 Proxy 实例，每个都能独立完成把关，不需要彼此同步。</p>

<p>其中<strong>限流</strong>这一关，值得多说一句，因为它体现了 Proxy"保护后端"的自觉。向量数据库的写入与查询都很"重"：一次大批量 insert 可能瞬间灌入几十万行，
一次高 topK、大 nprobe 的 search 可能让 QueryNode 满负荷。如果 Proxy 来者不拒，突发流量会直接把后端打到内存溢出或长尾飙升。
于是限流器按配置的配额（可以按集合、按操作类型、按租户细分）给请求<strong>背压（backpressure）</strong>：能扛就放行，扛不住就降速、排队甚至直接拒绝并提示稍后重试。
这是一种"宁可让少数请求慢一点、也不让整个集群崩掉"的取舍——把它放在最前端，正是因为<strong>越早拦住过载，代价越小</strong>。</p>

<table class="t">
  <tr><th>关卡</th><th>问的问题</th><th>实现文件</th><th>不过会怎样</th></tr>
  <tr><td><strong>鉴权</strong></td><td>你是谁</td><td class="mono">authentication_interceptor.go</td><td>拒绝连接</td></tr>
  <tr><td><strong>权限</strong></td><td>你能不能做</td><td class="mono">privilege_interceptor.go</td><td>无权限错误</td></tr>
  <tr><td><strong>数据库路由</strong></td><td>哪个 database</td><td class="mono">database_interceptor.go</td><td>找不到库</td></tr>
  <tr><td><strong>限流</strong></td><td>是否超额</td><td class="mono">rate_limit_interceptor.go</td><td>限速 / 拒绝</td></tr>
</table>

<h2>任务调度器：三个队列各管一摊</h2>
<p>过了关卡，请求并不会一窝蜂直接执行，而是被包装成<strong>任务（task）</strong>放进<strong>任务调度器（task scheduler）</strong>。
这是 Proxy 的"调度大脑"，它内部维护着三个<strong>独立队列</strong>，按请求类型分流：</p>

<p>这种"按类型分队列"的设计，背后是一个朴素却深刻的观察：<strong>不同请求对系统的诉求根本不同，混在一起只会互相拖累</strong>。
建一张表（DDL）一年也许只发生几次，但必须万无一失、严格有序；插入数据（DML）每秒成千上万，要的是高吞吐和持久化保证；
查询（DQL）延迟敏感、彼此独立，要的是极致并发。把它们塞进同一个队列，等于让一辆救护车、一队货车和一群轿车挤同一条单车道——谁都快不了。
分车道，才能各行其速。</p>

<ul>
  <li><strong>ddQueue（DDL 队列）</strong>：数据定义类——建/删集合、分区、索引、别名。这类操作改的是<strong>元数据结构</strong>，要严格串行、按序执行。</li>
  <li><strong>dmQueue（DML 队列）</strong>：数据操作类——insert、delete、upsert。这类是<strong>写入</strong>，要拿时间戳、要写进 WAL/消息队列。</li>
  <li><strong>dqQueue（DQL 队列）</strong>：数据查询类——search、query。这类是<strong>读取</strong>，要扇出到多个分片再合并结果。</li>
</ul>

<p>为什么要分三个队列而不是一个大队列？因为这三类请求的<strong>排序约束、并发度、资源画像完全不同</strong>。DDL 改结构，必须谨慎串行，
否则两个并发的"改 schema"会打架；DML 是写，关心顺序与持久化；DQL 是读，关心并发与延迟，彼此之间几乎无依赖、可以大量并行。
把它们<strong>物理隔离</strong>，调度器就能对每条流水线施加最合适的策略——读的高并发不会被某个慢 DDL 堵住，反之亦然。
（源码里其实还有第四个 <span class="inline">dcQueue</span>"数据控制队列"，用于 flush 这类控制写入状态的操作，这里先聚焦主三条。）</p>

<p>队列内部还藏着一个关键设计：<strong>任务的两段式生命周期</strong>。一个任务进队后，先经历 <span class="mono">PreExecute</span>（执行前校验：把集合名翻译成 ID、检查字段是否匹配、补全默认参数），
再到 <span class="mono">Execute</span>（真正干活：发 RPC、等结果），最后 <span class="mono">PostExecute</span>（收尾：归并、组装返回）。
调度器之所以要把"未发出（unissued）"和"执行中（active）"两个阶段分开管理，是为了控制并发——比如 DML 写入要保证拿到的时间戳<strong>按序生效</strong>，
就不能让后拿到时间戳的任务抢先执行。这套机制把"什么时候允许下一个任务往前走"牢牢攥在调度器手里，是 Proxy 能在高并发下仍维持正确时序的根基。
你不必记住每个方法名，但要记住这个直觉：<strong>排队不只是排个先后，更是在为"时间戳顺序"和"资源并发"两件事同时把关</strong>。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/proxy/task_scheduler.go</span><span class="ln">taskScheduler 与三个队列</span></div>
  <pre><span class="kw">type</span> taskScheduler <span class="kw">struct</span> {
    ddQueue *ddTaskQueue   <span class="cm">// DDL：建/删 集合、分区、索引、别名</span>
    dmQueue *dmTaskQueue   <span class="cm">// DML：insert / delete / upsert</span>
    dqQueue *dqTaskQueue   <span class="cm">// DQL：search / query</span>

    <span class="cm">// 数据控制队列，用于 flush 等控制数据状态的操作</span>
    dcQueue *ddTaskQueue
    <span class="cm">// ... ctx / cancel / waitgroup</span>
}

<span class="kw">func</span> newTaskScheduler(ctx context.Context, tso tsoAllocator, ...) (*taskScheduler, <span class="kw">error</span>) {
    s := &amp;taskScheduler{ ... }
    s.ddQueue = newDdTaskQueue(tso)
    s.dmQueue = newDmTaskQueue(tso)
    s.dqQueue = newDqTaskQueue(tso)
    <span class="kw">return</span> s, <span class="kw">nil</span>
}</pre>
</div>

<h2>一次请求的内部旅程</h2>
<p>把上面拼起来，看一条请求在 Proxy 里走完的完整流水线。注意第 ④ 步"拿时间戳"：每个写入/查询任务在入队时都会向协调者的 <strong>TSO</strong> 要一个全局时间戳
（下一课讲 RootCoord 时细说），它决定了这条操作在全局时间线上的位置——这正是第 3 课"时间戳的角色"在 Proxy 这一层的落地。
这条流水线最值得玩味的，是它把一次看似简单的调用拆成了"<strong>把关 → 排队 → 定序 → 扇出 → 归并</strong>"五个阶段，每个阶段都对应后端某个子系统：把关靠 RBAC 与配额元数据，
定序靠 RootCoord 的 TSO，扇出与归并靠 QueryCoord 维护的分片分布。一个请求的"一生"，其实就是 Proxy 不断向控制面借力、再把结果收拢的过程。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>接收请求</h4><p>gRPC/REST 打到 Proxy 的 milvuspb 方法，如 <span class="mono">Search</span>。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>三道关卡</h4><p>鉴权 → 权限 → 数据库路由 → 限流，拦截器逐个把关。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>包装成任务、选队列</h4><p>按类型进 ddQueue / dmQueue / dqQueue。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>分配时间戳</h4><p class="mono">tsoAllocator</p><p>向协调者要全局时间戳/ID，定下这条操作的时序。</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>执行：扇出</h4><p>DML 写进 WAL/MQ；DQL 把查询发给负责各分片的 QueryNode。</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>归并 reduce</h4><p>把多个分片返回的 topK 合并、重排成一份最终结果。</p></div></div>
  <div class="step"><div class="num">7</div><div class="sc"><h4>返回客户端</h4><p>一份干净的答案，后端的复杂度对调用方完全透明。</p></div></div>
</div>

<h2>读与写：两条不同的路</h2>
<p>把 DML（写）和 DQL（读）的执行路径并排看，能更清楚 Proxy 的"分派"到底在分什么。它们的终点不同、关心的东西也不同：</p>

<div class="cols">
  <div class="col"><h4>DML 写入路径</h4><p>insert/delete 拿到时间戳后，被<strong>写进消息队列 / WAL</strong>（按 vchannel 分发），由 StreamingNode/DataNode 异步消费、落盘成段。
  Proxy 关心的是<strong>顺序与持久化</strong>——写成功即返回，真正落盘在后台进行。这正是第 7 课"日志即数据"的写侧入口。</p></div>
  <div class="col"><h4>DQL 查询路径</h4><p>search/query 被<strong>扇出（fan-out）</strong>到负责各个分片的 QueryNode，每个节点在自己内存里的索引上算出局部 topK，
  再把结果<strong>汇总回 Proxy 归并（reduce）</strong>成全局 topK。Proxy 关心的是<strong>并发与延迟</strong>——慢的那个分片决定整体快慢。</p></div>
</div>

<p>这条"扇出—归并"是分布式检索的核心难点：单个分片只看见局部数据，必须把它们的局部最优<strong>正确地合并</strong>成全局最优，
还要处理重复、删除标记、分数归一等细节。它足够复杂，值得单开一课——我们留到第 29 课深挖。这里你只需记住：<strong>Proxy 是这次归并的汇合点</strong>，
是它把"分散在多台机器上的部分答案"重新拼成"一份完整答案"。</p>

<p>顺带厘清一个常见误解：search 的"<strong>一致性级别</strong>"也是在 Proxy 这一层落地的。客户端可以要求"强一致"（读到此刻为止的所有写入）或"有界过期"（容忍一点点延迟换更低延时）。
Proxy 的做法是：在发出查询前，决定带上一个<strong>保证时间戳（guarantee timestamp）</strong>，告诉 QueryNode"请把数据至少消费到这个时间点再回答我"。
强一致就用当前最新的时间戳，最终一致就用一个稍旧的。你看，又是<strong>时间戳</strong>在背后统一调度读与写的可见性——这正是第 3 课埋下的伏笔在分布式层面的兑现。
把这一点和前面的扇出/归并合起来，你就理解了 Proxy 在一次查询里同时扮演的三个角色：<strong>路由器、时序协调者、结果归并器</strong>。</p>

<h2>无状态：Proxy 为什么能随便扩</h2>
<p>最后回到那句反复出现的话：<strong>Proxy 是无状态的</strong>。它不持有任何段、任何索引、任何用户数据——它需要的元数据来自协调者与 etcd（且可缓存），
时间戳来自 TSO，真正的数据在节点和对象存储里。既然每个 Proxy 实例都能<strong>独立、对等地</strong>完成"把关—调度—归并"，那么应对流量高峰就很简单：
<strong>多开几个 Proxy，前面挂一个负载均衡器</strong>，请求随便落到哪个实例都一样。某个 Proxy 崩了也不丢数据，因为它本来就没存数据。</p>

<p>这就是把"承载吞吐"和"持有状态"分开设计的回报（第 9 课讲过这条原则）：Proxy 站在吞吐链路最前端，压力最大，但因为无状态，
它反而是整个系统里<strong>最容易扩展</strong>的一环。把它和"有状态、需要协调分配"的 QueryNode/DataNode 对照，你会更深刻地体会 Milvus 的分层哲学——
让每个组件只承担一种复杂度，再用接口与队列把它们干净地缝起来。</p>

<p>不过"无状态"并不等于"无脑转发"。Proxy 仍要维护一份会随后端变化而更新的<strong>本地缓存</strong>（集合 schema、分片分布、各 QueryNode 的负载提示等），
否则每个请求都去问一次协调者，协调者就成了新瓶颈。这份缓存是"软状态"——可以丢、丢了能从协调者与 etcd 重新拉回来，所以不破坏无状态扩展的本质。
它的更新同样借助第 9 课讲的 watch 机制：当 QueryCoord 改变了某个集合的分片分布，相关变更会传导到 Proxy，让它的路由表保持新鲜。
理解了这一点，你就能回答一个常见面试题：<strong>"Proxy 既然无状态，为什么还要缓存？"——因为缓存是为性能服务的软状态，而非为正确性兜底的硬状态</strong>，两者在分布式系统里有本质区别。</p>

<p>最后把视角拉回这一部分的主线。Proxy 是数据面的网关，但它一刻也离不开控制面：要时间戳找 RootCoord（下一课），要知道集合加载在哪找 QueryCoord（第 13 课），
要落盘成段背后是 DataCoord（第 12 课）。换句话说，<strong>Proxy 是把"控制面的决策"翻译成"对客户端可用的服务"的那层皮</strong>。
接下来三课我们逐个走进这三个协调者，你会发现每一个都在为 Proxy 这条流水线的某一环提供支撑——读完它们，再回看这张图，一切都会严丝合缝。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话串起来：<strong>Proxy 是唯一入口（milvuspb 服务）→ 先过鉴权/权限/数据库/限流四关 → 包装成任务进 ddQueue/dmQueue/dqQueue 三个队列 → 向协调者要时间戳 → 写入扇进 WAL、查询扇出到节点 → 归并成一份结果返回</strong>。
  它无状态，所以可以横向扩展、前挂负载均衡。把这条流水线记牢，后面每个协调者都是它身后的一环。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>唯一入口</strong>：Proxy 实现对外的 <span class="mono">milvuspb</span> MilvusService（gRPC/REST），把后端拓扑全部封装在身后。</li>
    <li><strong>四道关卡</strong>：鉴权 / 权限 / 数据库路由 / 限流，由独立 interceptor 实现，挡在业务逻辑之前。</li>
    <li><strong>三个队列</strong>：<span class="mono">ddQueue</span>(DDL)、<span class="mono">dmQueue</span>(DML)、<span class="mono">dqQueue</span>(DQL)，按排序约束与并发画像物理隔离（另有 <span class="mono">dcQueue</span> 管 flush）。见 <span class="mono">task_scheduler.go</span>。</li>
    <li><strong>时间戳</strong>：每个写/读任务入队时向协调者 TSO 要全局时间戳，定下时序（详见第 11 课）。</li>
    <li><strong>读写两路</strong>：DML 扇进 WAL/MQ 关心持久化；DQL 扇出到 QueryNode 再<strong>归并 reduce</strong>，关心并发与延迟（reduce 深入见第 29 课）。</li>
    <li><strong>无状态</strong>：不存数据，可横向扩展、负载均衡，是最易扩的一环。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson we hovered over the whole cluster: coordinators decide, nodes execute. This lesson zooms into the data plane's front line, the
<strong>Proxy (the gateway)</strong> — the <strong>single entry point</strong> for every client request. It is the doorkeeper (validate, authenticate, rate-limit),
the dispatcher (queue requests and hand them to coordinators and nodes), and the aggregator (merge results from many shards into one answer).
Understand the Proxy and you hold the full arc of "a request from entering the door to leaving it."
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Picture the Proxy as a big hospital's <strong>triage desk</strong>: a patient (request) walks in, the desk first checks identity and registration (auth) and whether you still
  have a slot today (rate limit), then routes you by case into different <strong>queues</strong> — paperwork changes go to the "admin window" (DDL), shots and IVs go to "treatment" (DML),
  scans and reports go to "labs" (DQL). The desk itself <strong>treats no one and scans nothing</strong>, yet the whole hospital's order depends on it; it also <strong>stores no medical records</strong>,
  so you can open more desks anytime to share the crowd — exactly the essence of the Proxy being "stateless and horizontally scalable."
</div>

<h2>Single entry: the milvuspb API surface</h2>
<p>Whether you use the Python SDK, Go SDK, or REST, a request ultimately lands on the <strong>gRPC service</strong> the Proxy exposes. That service's contract is defined by proto,
in the <span class="inline">milvuspb</span> package (from <span class="mono">milvus-proto/go-api/v3/milvuspb</span>, not hand-written types in the repo). A <span class="mono">CreateCollection</span>,
an <span class="mono">Insert</span>, a <span class="mono">Search</span> each map to a method <span class="mono">func (node *Proxy) Xxx(...)</span> on the Proxy side.
In other words, <strong>the Proxy is the implementation of the public MilvusService API</strong>, while the coordinator and node interfaces are all "internal."</p>

<p>This "external vs internal" boundary matters: the client only ever talks to the Proxy and never needs to know how many QueryNodes sit behind it, where segments live, or where the TSO comes from.
The Proxy <strong>encapsulates all that complexity</strong> behind itself. So however the backend scales, changes, or fails over, it's transparent to the client — the API is stable, the topology is free.
That's why Lesson 8 could say "Lite / Standalone / Cluster, one API": what changes is backend scale; what stays is the surface the Proxy exposes.</p>

<p>One layer deeper, the Proxy also plays an easily-missed role: <strong>translator between protocol and topology</strong>. The client sends <strong>business semantics</strong> like "search this vector in collection A, topK=10,"
but what the backend must actually do is "which QueryNodes is collection A loaded on right now, how many shards does it have, who is each shard's delegator, into how many parallel calls should the request be split."
The Proxy bridges that gap using its cached metadata. It must keep this "routing table" updated as the collection's load state and shard distribution change, or it would send a request to a node that no longer serves that shard.
Precisely because this "translation" only reads metadata and never writes it, multiple Proxies can each hold their own cache and serve independently without syncing — the <strong>prerequisite</strong> for stateless scaling.</p>

<div class="flow">
  <div class="node"><div class="nt">client SDK</div><div class="nd">Python / Go / REST</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">Proxy</div><div class="nd">milvuspb service impl</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">coordinators</div><div class="nd">for timestamps / metadata</div></div>
  <div class="arrow">＋</div>
  <div class="node"><div class="nt">nodes</div><div class="nd">QueryNode / DataNode do work</div></div>
</div>

<h2>Three gates: validate, authenticate, rate-limit</h2>
<p>Once a request enters the Proxy it isn't executed right away — it must first pass a chain of <strong>interceptors</strong>. This is standard gRPC practice: before the real business method,
a set of middlewares vet the request one by one. Milvus splits them into clear, single-purpose files:</p>

<ul>
  <li><strong>Authentication</strong>: who are you? <span class="inline">authentication_interceptor.go</span> checks username/password or token; unknown callers are rejected.</li>
  <li><strong>Privilege</strong>: are you allowed to do this? <span class="inline">privilege_interceptor.go</span> checks the RBAC role against this collection/operation.</li>
  <li><strong>Database routing</strong>: which database do you mean? <span class="inline">database_interceptor.go</span> pins the request to the right db context.</li>
  <li><strong>Rate limit</strong>: are you hammering us today? <span class="inline">rate_limit_interceptor.go</span> throttles or blocks writes/queries by quota to protect the backend.</li>
</ul>

<p>Together these four gates are the Proxy's full "doorkeeper" duty. Because they sit <strong>before business logic</strong>, an illegal, unauthorized, or over-quota request is stopped
before it ever reaches queueing and execution — saving backend compute and holding the line on security and stability. Note these are all <strong>stateless judgments</strong> (querying metadata and quotas),
so spinning up more Proxy instances lets each one vet independently, with no need to sync with the others.</p>

<p>The <strong>rate-limit</strong> gate deserves an extra word, because it embodies the Proxy's instinct to "protect the backend." Vector-DB writes and queries are both "heavy": one bulk insert can pour in hundreds of thousands of rows at once,
one high-topK, large-nprobe search can saturate a QueryNode. If the Proxy accepted everything, a traffic spike would drive the backend straight into out-of-memory or tail-latency blowups.
So the limiter applies <strong>backpressure</strong> per configured quota (which can be split by collection, by operation kind, by tenant): pass it if we can bear it, otherwise throttle, queue, or reject outright with a "retry later" hint.
This is a "rather slow a few requests than crash the whole cluster" trade-off — placed at the very front exactly because <strong>the earlier you stop overload, the cheaper it is</strong>.</p>

<table class="t">
  <tr><th>Gate</th><th>Question</th><th>Impl file</th><th>If it fails</th></tr>
  <tr><td><strong>Auth</strong></td><td>who are you</td><td class="mono">authentication_interceptor.go</td><td>reject connection</td></tr>
  <tr><td><strong>Privilege</strong></td><td>may you do this</td><td class="mono">privilege_interceptor.go</td><td>permission error</td></tr>
  <tr><td><strong>DB routing</strong></td><td>which database</td><td class="mono">database_interceptor.go</td><td>db not found</td></tr>
  <tr><td><strong>Rate limit</strong></td><td>over quota</td><td class="mono">rate_limit_interceptor.go</td><td>throttle / reject</td></tr>
</table>

<h2>The task scheduler: three queues, three lanes</h2>
<p>Past the gates, requests don't all execute in a stampede — each is wrapped into a <strong>task</strong> and placed into the <strong>task scheduler</strong>.
This is the Proxy's "scheduling brain," holding three <strong>independent queues</strong> that split traffic by request kind:</p>

<p>This "a queue per kind" design rests on a plain yet deep observation: <strong>different requests demand fundamentally different things from the system, and mixing them only drags everyone down</strong>.
Creating a table (DDL) might happen a few times a year but must be flawless and strictly ordered; inserting data (DML) happens thousands of times a second and wants high throughput and durability;
querying (DQL) is latency-sensitive and mutually independent and wants maximum concurrency. Cramming them into one queue is like making an ambulance, a convoy of trucks, and a stream of cars share one single-lane road — nobody goes fast.
Separate lanes let each move at its own speed.</p>

<ul>
  <li><strong>ddQueue (DDL)</strong>: data-definition — create/drop collection, partition, index, alias. These change <strong>metadata structure</strong> and must run strictly serially and in order.</li>
  <li><strong>dmQueue (DML)</strong>: data-manipulation — insert, delete, upsert. These are <strong>writes</strong> that need timestamps and go into the WAL/message queue.</li>
  <li><strong>dqQueue (DQL)</strong>: data-query — search, query. These are <strong>reads</strong> that fan out to multiple shards and then merge.</li>
</ul>

<p>Why three queues instead of one big queue? Because the three kinds have <strong>completely different ordering constraints, concurrency, and resource profiles</strong>. DDL changes structure and must be carefully serial,
or two concurrent "alter schema" calls collide; DML is a write that cares about order and durability; DQL is a read that cares about concurrency and latency, with little inter-dependence and high parallelism.
<strong>Physically isolating</strong> them lets the scheduler apply the most fitting policy to each lane — high-concurrency reads aren't blocked behind a slow DDL, and vice versa.
(The source actually has a fourth <span class="inline">dcQueue</span>, a "data control queue" for operations like flush that control data state; here we focus on the main three.)</p>

<p>Inside each queue hides a key design: a task's <strong>two-stage lifecycle</strong>. After a task enters the queue it goes through <span class="mono">PreExecute</span> (pre-checks: translate the collection name to an ID, verify fields match, fill in defaults),
then <span class="mono">Execute</span> (the real work: send RPCs, await results), and finally <span class="mono">PostExecute</span> (wrap-up: reduce, assemble the response).
The scheduler separately manages an "unissued" and an "active" stage in order to control concurrency — for example, DML writes must have their assigned timestamps <strong>take effect in order</strong>,
so a task that got a later timestamp must not run ahead. This mechanism keeps "when the next task may move forward" firmly in the scheduler's hands, the basis for the Proxy maintaining correct ordering under high concurrency.
You needn't memorize each method name, but keep the intuition: <strong>queueing isn't just ordering — it simultaneously guards both "timestamp order" and "resource concurrency."</strong></p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/proxy/task_scheduler.go</span><span class="ln">taskScheduler and its three queues</span></div>
  <pre><span class="kw">type</span> taskScheduler <span class="kw">struct</span> {
    ddQueue *ddTaskQueue   <span class="cm">// DDL: create/drop collection, partition, index, alias</span>
    dmQueue *dmTaskQueue   <span class="cm">// DML: insert / delete / upsert</span>
    dqQueue *dqTaskQueue   <span class="cm">// DQL: search / query</span>

    <span class="cm">// data control queue, for flush etc. that control data state</span>
    dcQueue *ddTaskQueue
    <span class="cm">// ... ctx / cancel / waitgroup</span>
}

<span class="kw">func</span> newTaskScheduler(ctx context.Context, tso tsoAllocator, ...) (*taskScheduler, <span class="kw">error</span>) {
    s := &amp;taskScheduler{ ... }
    s.ddQueue = newDdTaskQueue(tso)
    s.dmQueue = newDmTaskQueue(tso)
    s.dqQueue = newDqTaskQueue(tso)
    <span class="kw">return</span> s, <span class="kw">nil</span>
}</pre>
</div>

<h2>One request's journey inside</h2>
<p>Putting it together, here is a request's full pipeline inside the Proxy. Note step ④ "get a timestamp": as each write/query task is enqueued, it asks the coordinator's <strong>TSO</strong> for a global timestamp
(detailed next lesson on RootCoord) that fixes this operation's place on the global timeline — exactly Lesson 3's "role of timestamps," realized at the Proxy layer.
What's most worth savoring is how this pipeline breaks a seemingly simple call into five stages — "<strong>gate → queue → order → fan out → reduce</strong>" — each mapping to some backend subsystem: gating relies on RBAC and quota metadata,
ordering on RootCoord's TSO, fan-out and reduce on the shard distribution QueryCoord maintains. A request's "life" is really the Proxy repeatedly borrowing strength from the control plane and then gathering the results back.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>receive</h4><p>gRPC/REST hits a Proxy milvuspb method, e.g. <span class="mono">Search</span>.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>three gates</h4><p>auth → privilege → db routing → rate limit, interceptors vet in turn.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>wrap as task, pick queue</h4><p>route into ddQueue / dmQueue / dqQueue by kind.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>assign timestamp</h4><p class="mono">tsoAllocator</p><p>ask the coordinator for a global timestamp/ID, fixing this op's order.</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>execute: fan out</h4><p>DML writes into WAL/MQ; DQL sends the query to the QueryNodes serving each shard.</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>reduce</h4><p>merge and re-rank the topK returned by multiple shards into one final result.</p></div></div>
  <div class="step"><div class="num">7</div><div class="sc"><h4>return</h4><p>one clean answer; backend complexity is fully transparent to the caller.</p></div></div>
</div>

<h2>Reads and writes: two different paths</h2>
<p>Placing the DML (write) and DQL (read) execution paths side by side makes clear what the Proxy's "dispatch" actually splits. They end in different places and care about different things:</p>

<div class="cols">
  <div class="col"><h4>DML write path</h4><p>After getting a timestamp, insert/delete is <strong>written into the message queue / WAL</strong> (dispatched by vchannel), to be consumed asynchronously by StreamingNode/DataNode and persisted into segments.
  The Proxy cares about <strong>order and durability</strong> — once the write succeeds it returns; actual persistence happens in the background. This is the write-side entrance to Lesson 7's "log-as-data."</p></div>
  <div class="col"><h4>DQL query path</h4><p>search/query is <strong>fanned out</strong> to the QueryNodes serving each shard; each node computes a local topK on its in-memory index,
  then results are <strong>gathered back to the Proxy and reduced</strong> into a global topK. The Proxy cares about <strong>concurrency and latency</strong> — the slowest shard sets the overall speed.</p></div>
</div>

<p>This "fan-out / reduce" is the core difficulty of distributed search: each shard sees only local data, and their local optima must be <strong>correctly merged</strong> into the global optimum,
while handling duplicates, delete markers, score normalization, and more. It's complex enough to deserve its own lesson — we dive into it in Lesson 29. Here, just remember: <strong>the Proxy is the merge point</strong>,
the one that reassembles "partial answers scattered across machines" into "one complete answer."</p>

<p>While we're here, let's clear up a common misconception: a search's <strong>consistency level</strong> is also realized at the Proxy layer. The client may demand "strong" (read every write up to now) or "bounded staleness" (tolerate a little lag for lower latency).
The Proxy's trick: before issuing the query it decides on a <strong>guarantee timestamp</strong> to attach, telling QueryNodes "please consume data at least up to this point before answering me."
Strong consistency uses the current latest timestamp; eventual uses a slightly older one. See — once again it's the <strong>timestamp</strong> orchestrating the visibility of reads vs writes behind the scenes, the distributed-level payoff of the seed planted in Lesson 3.
Combine this with the earlier fan-out/reduce and you grasp the three roles the Proxy plays in a single query: <strong>router, ordering coordinator, and result merger</strong>.</p>

<h2>Stateless: why the Proxy scales freely</h2>
<p>Finally, back to that recurring line: <strong>the Proxy is stateless</strong>. It holds no segments, no indexes, no user data — the metadata it needs comes from coordinators and etcd (and can be cached),
timestamps come from the TSO, and the real data lives in nodes and object storage. Since every Proxy instance can <strong>independently and identically</strong> do "gate — schedule — reduce," handling a traffic spike is simple:
<strong>spin up more Proxies behind a load balancer</strong>; a request can land on any instance and behave the same. If a Proxy crashes, no data is lost, because it never stored any.</p>

<p>This is the payoff of separating "carries throughput" from "holds state" (the principle from Lesson 9): the Proxy sits at the very front of the throughput path under the most pressure, yet because it is stateless
it is the <strong>easiest part of the whole system to scale</strong>. Contrast it with the stateful, assignment-coordinated QueryNode/DataNode and you feel Milvus's layering philosophy more deeply —
let each component carry just one kind of complexity, then stitch them together cleanly with interfaces and queues.</p>

<p>But "stateless" doesn't mean "mindless forwarding." The Proxy still maintains a <strong>local cache</strong> that updates as the backend changes (collection schema, shard distribution, per-QueryNode load hints, etc.),
or else every request would query a coordinator and the coordinator becomes the new bottleneck. This cache is "soft state" — droppable, and re-fetchable from coordinators and etcd when lost, so it doesn't break the essence of stateless scaling.
Its updates also rely on Lesson 9's watch mechanism: when QueryCoord changes a collection's shard distribution, the relevant change propagates to the Proxy to keep its routing table fresh.
Grasp this and you can answer a common interview question: <strong>"If the Proxy is stateless, why cache at all?" — because the cache is soft state serving performance, not hard state backing correctness</strong>; the two are fundamentally different in distributed systems.</p>

<p>Finally, pull back to this part's through-line. The Proxy is the data plane's gateway, but it can't live a moment without the control plane: it asks RootCoord for timestamps (next lesson), asks QueryCoord where a collection is loaded (Lesson 13),
and behind persisting segments is DataCoord (Lesson 12). In other words, <strong>the Proxy is the skin that translates "control-plane decisions" into "a service usable by clients."</strong>
The next three lessons walk into these three coordinators one by one, and you'll find each supports some link of the Proxy's pipeline — read them, look back at this diagram, and everything snaps into place.</p>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  In one line: <strong>the Proxy is the single entry (milvuspb service) → it passes four gates auth/privilege/db/rate-limit → wraps tasks into ddQueue/dmQueue/dqQueue → asks the coordinator for a timestamp → writes fan into the WAL, queries fan out to nodes → results are reduced into one answer and returned</strong>.
  It is stateless, so it scales horizontally behind a load balancer. Hold this pipeline in mind and every coordinator ahead is one link behind it.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Single entry</strong>: the Proxy implements the public <span class="mono">milvuspb</span> MilvusService (gRPC/REST), encapsulating all backend topology behind it.</li>
    <li><strong>Four gates</strong>: auth / privilege / db routing / rate limit, each an independent interceptor sitting before business logic.</li>
    <li><strong>Three queues</strong>: <span class="mono">ddQueue</span>(DDL), <span class="mono">dmQueue</span>(DML), <span class="mono">dqQueue</span>(DQL), physically isolated by ordering and concurrency profile (plus a <span class="mono">dcQueue</span> for flush). See <span class="mono">task_scheduler.go</span>.</li>
    <li><strong>Timestamps</strong>: each write/read task asks the coordinator's TSO for a global timestamp to fix its order (detailed in Lesson 11).</li>
    <li><strong>Two paths</strong>: DML fans into the WAL/MQ (durability); DQL fans out to QueryNodes then <strong>reduces</strong> (concurrency/latency; reduce deep-dived in Lesson 29).</li>
    <li><strong>Stateless</strong>: stores no data, scales horizontally behind a load balancer — the easiest link to scale.</li>
  </ul>
</div>
""",
}


LESSON_11 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课 Proxy 在排队时反复向"协调者"要一个东西——<strong>全局时间戳</strong>。发这个时间戳的，正是这一课的主角 <strong>RootCoord（根协调者）</strong>。
它管两件大事：一是所有 <strong>DDL</strong>（建/删集合、分区、别名、数据库）与其背后的<strong>元数据表</strong>；二是给全集群发<strong>时间</strong>与<strong>身份</strong>——
单调递增的 TSO 时间戳，和全局唯一的 ID。它是整个 Milvus 的"<strong>定序大脑</strong>"。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把 RootCoord 想成一个国家的<strong>户籍 + 国家授时中心</strong>。一方面它是<strong>户籍处</strong>：谁出生（建集合）、谁注销（删集合）、改名换户（改 schema / 别名），
  都要在它那本<strong>总账（元数据表）</strong>上登记，登记完才算数。另一方面它是<strong>授时台</strong>：全国所有钟表都对它报时——它发出的时间<strong>只增不减、绝不重复</strong>，
  于是天南海北发生的事都能排出一个公认的先后。它还兼着<strong>发证件号</strong>：每个新生事物都领一个全国唯一的编号。<strong>登记、授时、发号</strong>——一个机构，三件大事。
</div>

<h2>第一件大事：DDL 与元数据表</h2>
<p>当你 <span class="mono">create_collection</span>、加一个分区、建一个别名，或者新建一个 database，这些都属于 <strong>DDL（数据定义语言）</strong>。
它们改变的不是数据本身，而是<strong>数据的结构与身份</strong>——集合有哪些字段、主键是谁、向量多少维、分了几个分区。这类信息必须有一份<strong>权威、持久、唯一</strong>的记录，
否则整个集群就会对"集合长什么样"各执一词。RootCoord 持有的这份记录，就叫<strong>元数据表（meta table）</strong>，接口名是 <span class="inline">IMetaTable</span>。</p>

<p>为什么 DDL 一定要集中到 RootCoord 一处串行处理？因为结构变更<strong>天然怕并发</strong>。设想两个客户端同时给同一个集合改 schema、或一个在建分区另一个在删集合——
若各改各的，元数据就会自相矛盾，后端节点读到的"集合定义"也会随之分裂。把所有 DDL 收口到一个大脑、按序落账，是保证<strong>结构一致性</strong>最朴素也最可靠的办法。
这也呼应了上一课 Proxy 把 DDL 单独排进 <span class="mono">ddQueue</span> 并严格串行的设计——两端配合，才守住了"结构永远只有一个版本"的底线。</p>

<p>你可能会担心：所有 DDL 都串行，会不会太慢？在实践中并不会成为问题，因为 DDL 是<strong>低频但高价值</strong>的操作——一个集合的 schema 一旦定下，往往几个月都不会改一次，
真正高频的是 insert 与 search 这类数据面操作，而它们走的是完全不同的并发路径（上一课的 dmQueue / dqQueue）。把"罕见但必须正确"的事情做成严格串行，把"频繁且可并行"的事情放开并发，
这种<strong>按频率与一致性要求分而治之</strong>的设计哲学，贯穿了整个 Milvus。RootCoord 甘当 DDL 的"独木桥"，正是因为这座桥本来就没多少人走，却必须保证每个过桥的人都不会摔下去。</p>

<p>元数据表本身并不把数据存在内存里就算完，它<strong>背靠持久化</strong>：每一次登记最终都要写进 etcd（下节会展开"存在哪"）。RootCoord 启动时会从持久层把全量元数据<strong>回放</strong>到内存，
之后内存里的这份既是<strong>读缓存</strong>（Proxy 频繁来问"集合 A 的 ID 和 schema 是什么"），又随每次 DDL <strong>同步落盘</strong>。于是即便 RootCoord 进程重启，集合定义也不会丢——
这正是"元数据"与"数据"在可靠性上享受同等待遇的体现。</p>

<p>我们用一次最常见的 <span class="mono">create_collection</span> 把这条登记链路走一遍，你会看到 RootCoord 的三件大事其实在一个动作里就<strong>同时上场</strong>了：要发号、要定序、要落账。
这也解释了为什么"建一张表"看起来只是一行 SDK 调用，背后却牵动着整个定序大脑。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Proxy 收到 DDL</h4><p>客户端 <span class="mono">create_collection</span> 经 Proxy 校验后，进 <span class="mono">ddQueue</span> 严格串行。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>发号</h4><p class="mono">idAllocator.Alloc</p><p>RootCoord 给新集合分配一个全局唯一的 collectionID。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>定序</h4><p class="mono">tsoAllocator</p><p>取一个 TSO 时间戳，标定这次结构变更在全局时间线上的位置。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>登记落账</h4><p>把集合定义写进 <span class="mono">IMetaTable</span>，并经 catalog/kv 持久化到 etcd。</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>广播</h4><p>把这条 DDL 经流式通道有序播给相关节点，让它们更新各自视图。</p></div></div>
</div>

<p>这条链路里最值得记住的，是"<strong>发号 → 定序 → 落账 → 广播</strong>"这四步的顺序与配合：先有唯一身份，再有时间位置，然后才把它写成权威记录，最后才让全集群知道。
任何一步出问题，集群对"这个集合是谁、什么时候建的、长什么样"的认知就会出现裂缝。RootCoord 把这四步牢牢串在一处、按序完成，正是它"权威"二字的分量所在。</p>

<table class="t">
  <tr><th>职责</th><th>对应机制</th><th>接口 / 文件</th></tr>
  <tr><td>建/删集合、分区、别名、库</td><td>DDL 串行登记</td><td class="mono">IMetaTable</td></tr>
  <tr><td>权威元数据的内存视图</td><td>启动回放 + 读缓存</td><td class="mono">MetaTable struct</td></tr>
  <tr><td>元数据持久化</td><td>写入 etcd（经 catalog/kv）</td><td class="mono">meta_table.go</td></tr>
  <tr><td>发时间戳</td><td>全局 TSO 分配器</td><td class="mono">tsoAllocator</td></tr>
  <tr><td>发唯一 ID</td><td>全局 ID 分配器</td><td class="mono">idAllocator</td></tr>
</table>

<h2>第二件大事：TSO，全集群的统一时钟</h2>
<p><strong>TSO（Timestamp Oracle，时间戳预言机）</strong>是 RootCoord 最具分量的职责。它对外只承诺一件事，却价值千金：发出的每个时间戳都<strong>全局唯一、单调递增</strong>。
有了它，分布在不同机器上的写入与查询，就能被放到<strong>同一条时间线</strong>上排出先后——这正是第 3 课讲"时间戳的角色"、第 10 课 Proxy"拿时间戳"的源头。
没有一个统一时钟，分布式系统就无法回答"这两件事谁先谁后"这个最基本的问题。</p>

<p>这个时间戳在概念上是个<strong>混合值</strong>：高位是物理时间（墙上时钟的毫秒），低位是一个逻辑计数器，两段拼进一个 64 位整数。物理位保证它大致跟着真实时间走，
逻辑位保证同一毫秒内连发多个也各不相同。你不必记住精确的位宽，只要抓住直觉：<strong>它既像时间、又保证唯一且有序</strong>。正因如此，比较两个时间戳的大小，
就等于在比较两件事在全局时间线上的先后——这是 Milvus 实现一致性读、读写隔离、以及"读到某个时间点为止的数据"的基石。</p>

<p>TSO 还有一个精妙的工程设计：<strong>批量分配 + 高水位持久化</strong>。RootCoord 并不会每发一个时间戳就写一次 etcd（那样太慢），而是周期性地把一个<strong>高水位（high-water mark）</strong>预先推进并持久化到 etcd，
之后在这段已被持久化的区间内，发时间戳就是纯内存操作，极快。一个后台 ticker 定时调用 <span class="mono">UpdateTSO</span> 推进并落盘水位。这样既快又<strong>崩溃安全</strong>：
万一 RootCoord 挂掉重启，它从 etcd 读回的水位一定<strong>大于等于</strong>之前发出去的任何时间戳，于是绝不会发生"重启后发出的时间戳比之前更小"这种致命倒退。</p>

<p>为什么"绝不倒退"这件事如此重要？因为整个 Milvus 的一致性都建立在"时间戳能比大小"这一假设上。查询会带一个<strong>读保证时间戳</strong>，约定"我要读到这个时间点为止的所有写入"；
写入则各自带着自己的时间戳落进日志。只要时间戳全局单调，节点就能干净利落地判断"哪些写入该被这次查询看见、哪些还太新应被忽略"。一旦时间戳出现倒退或重复，这套判断就会崩塌：
本该可见的数据被漏掉，或本不该出现的数据提前冒头——一致性就此破功。所以 RootCoord 宁可在持久化上多花一点力气，也要把"单调"这条铁律焊死。这也是为什么授时这件事<strong>只能有一个源头</strong>：
两个时钟各发各的，永远无法保证全局单调。</p>

<p>这里还藏着一个常见的疑问：既然每次发时间戳都要这么讲究，会不会成为整个集群的瓶颈？答案是不会——恰恰因为有了批量分配，<strong>绝大多数取时间戳的请求都在内存里瞬间完成</strong>，
只有周期性推进水位才触碰 etcd。换句话说，慢的那一步被摊薄到很低的频率，快的那一步承担了几乎全部流量。这是分布式系统里一种典型的"<strong>把昂贵操作批量化、把廉价操作高频化</strong>"的取舍，
后面讲段分配、ID 分配时你会反复见到同样的套路。理解了 TSO，就等于拿到了读懂 Milvus 一致性模型的钥匙。</p>

<div class="timeline">
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t1</span><span class="tl-c">Proxy 写入 A 入队，向 RootCoord 取时间戳 ts=100</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t2</span><span class="tl-c">另一台 Proxy 写入 B，取得 ts=101（绝不会再发 100）</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t3</span><span class="tl-c">查询 C 取读保证时间戳 ts=102，可读到 ts&lt;=102 的所有写入</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t4</span><span class="tl-c">后台 ticker 推进高水位并持久化到 etcd（崩溃也不回退）</span></div>
</div>

<h2>第三件大事：全局唯一 ID</h2>
<p>除了发时间，RootCoord 还<strong>发号</strong>。集合、分区、段（segment）这些对象都需要一个<strong>全集群唯一</strong>的 64 位 ID 来标识自己。这件事和 TSO 高度同构：
同样要求唯一、同样为了性能而<strong>批量分配</strong>——一次性从持久层取一段 ID 区间到内存，之后在区间内发号都是内存操作，用完再取下一段。
于是无论哪台机器、哪个时刻申请，拿到的 ID 都不会撞车。Proxy 要建集合时，就会向 RootCoord 的 <span class="mono">idAllocator.Alloc(count)</span> 一次性领走一批 ID。</p>

<p>你或许会问：为什么不用 UUID 这种本地就能生成的随机 ID？因为 Milvus 需要的不只是"唯一"，还要"<strong>紧凑且可比较</strong>"——64 位整数比 128 位字符串省内存、好索引，递增的序号还天然带一点"谁先创建"的语义。
集中发号虽然多了一次和 RootCoord 的往返，但凭借批量分配，这次往返被摊薄到几乎可忽略，换来的却是全集群整洁、统一、可排序的身份体系。这又是一处"用一点协调成本换取全局秩序"的典型权衡。</p>

<p>把"发时间"和"发号"放在同一处，并非偶然：它们都需要一个<strong>全局唯一的发号源</strong>，都靠"批量取一段、内存内快速分发、高水位持久化防回退"这套相同的机制。
RootCoord 正是这两件事天然的归属——它本就是集群里那个"唯一、权威、串行"的点。理解了这一层，你就明白为什么我们叫它"<strong>定序大脑</strong>"：
集群中关于<strong>时间</strong>与<strong>身份</strong>的最终裁决，都出自这里。</p>

<p>值得点一句的是 TSO 与 ID 在实现上的<strong>同源</strong>：在源码里它们底层共用同一套"全局分配器"的思路，连持久化用的 KV 句柄都是同一个（你会在下面的代码里看到 <span class="mono">tsoKV</span> 同时喂给两个分配器）。
区别只在于：一个分配的是"会跟着墙上时钟走"的时间戳，一个分配的是"只管递增、不关心物理时间"的纯序号。把它们做成同构的两兄弟，既减少了实现负担，也让"唯一性"这件事有了统一的保证来源。
对使用者而言，你只需记住：<strong>凡是需要全局唯一标识或全局统一时序的地方，背后都站着 RootCoord 这个发号台</strong>。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/rootcoord/root_coord.go</span><span class="ln">TSO 与 ID 分配器的装配</span></div>
  <pre><span class="kw">type</span> Core <span class="kw">struct</span> {
    <span class="cm">// ...</span>
    idAllocator  allocator.Interface   <span class="cm">// 全局唯一 ID 分配器</span>
    tsoAllocator tso2.Allocator        <span class="cm">// 全局 TSO 时间戳分配器</span>
}

<span class="cm">// 启动时装配：ID 分配器</span>
idAllocator := allocator.NewGlobalIDAllocator(globalIDAllocatorKey, tsoKV)
c.idAllocator = idAllocator

<span class="cm">// 装配 TSO 分配器（底层走 tso 包的 GlobalTSOAllocator）</span>
tsoAllocator := tso2.NewGlobalTSOAllocator(globalTSOAllocatorKey, tsoKV)
c.tsoAllocator = tsoAllocator

<span class="cm">// 调度器同时拿到这两个分配器，DDL 任务靠它们取号与定序</span>
c.scheduler = newScheduler(c.ctx, c.idAllocator, c.tsoAllocator)</pre>
</div>

<h2>DDL 如何传播，以及 RootCoord 住在哪</h2>
<p>登记完一条 DDL，仅仅写进元数据表还不够——后端的节点也得知道"集合变了"。RootCoord 会把 DDL 通过一条<strong>流式（streaming）通道</strong>广播出去，
让相关节点按序消费这条结构变更。这条"DDL 走流式日志"的链路本身很有讲究，但它属于后面讲<strong>写路径 / 流式系统</strong>的范畴，这里只需记住一个直觉：
<strong>DDL 不是改完就完事，而是像一条带时间戳的消息一样，被有序地播给需要它的人</strong>。这样 schema 变更才能在分布式环境下做到"人人最终看到同一个版本、且顺序一致"。</p>

<p>为什么 DDL 也要带时间戳、也要走有序日志？因为结构变更和数据写入在分布式里其实是<strong>同一类问题</strong>：都需要让"先后"成为全局共识。设想一次"给集合加字段"的 DDL 和一批 insert 几乎同时发生，
节点必须能判断这批数据到底该按旧 schema 还是新 schema 来解释——靠的正是两者各自携带的 TSO 时间戳。于是 DDL 与 DML 在同一条时间线上被统一定序，节点只需老老实实"按时间戳顺序回放"，
就能得到一个前后一致、人人相同的世界视图。这再次印证了 RootCoord 作为"定序大脑"的核心价值：<strong>它把结构与数据都纳入同一套时序，整个集群才有了统一的因果。</strong></p>

<p>最后别忘了上一课的结论：今天的 RootCoord 并不是一个独立进程，而是和 DataCoord、QueryCoord 一起<strong>跑在 MixCoord 这一个进程里</strong>，扮演其中的"根协调"这一逻辑角色（见第 9 课）。
所以当我们说"向 RootCoord 要时间戳"，物理上是在和 MixCoord 进程里的那段逻辑通信。把它单独成课，是因为它的<strong>职责边界</strong>清晰且关键：
谁来定序、谁来发号、谁来守元数据——这三件事，认准 RootCoord 就对了。下一课我们转向写入侧的另一个大脑 <strong>DataCoord</strong>（第 12 课），看段是怎么被分配、封存、落盘的。</p>
所以当我们说"向 RootCoord 要时间戳"，物理上是在和 MixCoord 进程里的那段逻辑通信。把它单独成课，是因为它的<strong>职责边界</strong>清晰且关键：
谁来定序、谁来发号、谁来守元数据——这三件事，认准 RootCoord 就对了。下一课我们转向写入侧的另一个大脑 <strong>DataCoord</strong>（第 12 课），看段是怎么被分配、封存、落盘的。</p>

<div class="flow">
  <div class="node"><div class="nt">Proxy</div><div class="nd">DDL / 取时间戳·ID</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">RootCoord</div><div class="nd">登记·授时·发号</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">元数据表</div><div class="nd">IMetaTable → etcd</div></div>
  <div class="arrow">＋</div>
  <div class="node"><div class="nt">流式通道</div><div class="nd">把 DDL 播给节点</div></div>
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  RootCoord 是集群里那个"唯一、权威、串行"的点。它干三件事，且都必须由<strong>一处</strong>来干：登记 DDL（保证集合结构只有一个版本）、发 TSO 时间戳（给全集群一条统一时间线）、发全局唯一 ID（给万物一个不撞车的身份）。
  时间戳与 ID 都用"批量取一段 + 高水位持久化"换来既快又防回退；元数据则背靠 etcd 持久化、启动回放。它和另两个协调者合住在 MixCoord 进程里——逻辑上独立，物理上同居。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>DDL + 元数据</strong>：建/删集合、分区、别名、库都收口到 RootCoord 串行登记，落在 <span class="mono">IMetaTable</span>，背靠 etcd 持久化。</li>
    <li><strong>TSO 时间戳</strong>：全局唯一、单调递增；概念上是"物理时间 + 逻辑计数"的 64 位混合值，给分布式事件一条统一时间线。</li>
    <li><strong>批量 + 高水位</strong>：TSO/ID 都批量分配、内存内快速发放，高水位持久化到 etcd，崩溃重启绝不回退。</li>
    <li><strong>全局 ID</strong>：集合/分区/段的唯一 64 位身份，由 <span class="mono">idAllocator.Alloc</span> 批量发放。</li>
    <li><strong>住在 MixCoord</strong>：今天 RootCoord 是 MixCoord 进程里的一个逻辑角色（第 9 课），DDL 经流式通道有序广播给节点。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson the Proxy kept asking a "coordinator" for one thing while queuing — a <strong>global timestamp</strong>. The issuer is this lesson's star, <strong>RootCoord (the root coordinator)</strong>.
It owns two big jobs: first, all <strong>DDL</strong> (create/drop collection, partition, alias, database) and the <strong>meta table</strong> behind it; second, handing out <strong>time</strong> and <strong>identity</strong> cluster-wide —
monotonically increasing TSO timestamps and globally unique IDs. It is Milvus's "<strong>ordering brain</strong>."
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of RootCoord as a nation's <strong>civil registry + national time service</strong>. On one hand it is the <strong>registry office</strong>: who is born (create collection), who is deregistered (drop collection), who renames or re-files (alter schema / alias) —
  all must be entered in its <strong>master ledger (the meta table)</strong>, and only then does it count. On the other hand it is the <strong>time-broadcast tower</strong>: every clock in the country syncs to it — the time it emits <strong>only increases, never repeats</strong>,
  so events happening anywhere can be ordered into one agreed sequence. It also <strong>issues ID numbers</strong>: every newborn thing gets a nationally unique number. <strong>Register, broadcast time, issue numbers</strong> — one office, three big jobs.
</div>

<h2>Big job one: DDL and the meta table</h2>
<p>When you <span class="mono">create_collection</span>, add a partition, make an alias, or create a new database, these are all <strong>DDL (data definition language)</strong>.
They change not the data itself but the <strong>structure and identity of data</strong> — which fields a collection has, who is the primary key, how many dimensions the vector is, how many partitions. Such information needs one <strong>authoritative, durable, unique</strong> record,
or the whole cluster will disagree on "what the collection looks like." The record RootCoord holds is the <strong>meta table</strong>, whose interface is <span class="inline">IMetaTable</span>.</p>

<p>Why must DDL be funneled to one place and serialized? Because structural changes are <strong>inherently allergic to concurrency</strong>. Imagine two clients altering the same collection's schema at once, or one adding a partition while another drops the collection —
if each does its own thing, metadata contradicts itself and the "collection definition" backend nodes read splits too. Funneling all DDL into one brain and booking it in order is the simplest, most reliable way to guarantee <strong>structural consistency</strong>.
This echoes last lesson's design where the Proxy queues DDL into <span class="mono">ddQueue</span> and runs it strictly serially — both ends cooperate to keep "there is only ever one version of the structure."</p>

<p>You might worry: if all DDL is serial, isn't it too slow? In practice it's not a problem, because DDL is a <strong>low-frequency but high-value</strong> operation — once a collection's schema is set, it often won't change for months;
the truly high-frequency operations are data-plane ones like insert and search, which travel a completely different concurrent path (last lesson's dmQueue / dqQueue). Making "rare but must-be-correct" things strictly serial, and letting "frequent and parallelizable" things run concurrently,
this design philosophy of <strong>divide-and-conquer by frequency and consistency requirement</strong> runs through all of Milvus. RootCoord willingly serves as DDL's "single-file bridge" precisely because few cross that bridge, yet every crosser must be guaranteed not to fall off.</p>

<p>The meta table isn't done by just keeping things in memory; it is <strong>backed by persistence</strong>: every registration eventually writes to etcd (the next lesson covers "where things live"). On startup RootCoord <strong>replays</strong> the full metadata from the persistent layer into memory,
and that in-memory copy then serves both as a <strong>read cache</strong> (the Proxy frequently asks "what is collection A's ID and schema") and as something kept <strong>in sync to disk</strong> on each DDL. So even if RootCoord restarts, collection definitions aren't lost —
this is exactly how "metadata" enjoys the same reliability treatment as "data."</p>

<p>Let's walk one most-common <span class="mono">create_collection</span> through this registration path; you'll see RootCoord's three big jobs all <strong>take the stage at once</strong> within a single action: issue a number, fix an order, book the record.
This also explains why "creating a table" looks like one SDK call yet stirs the entire ordering brain behind the scenes.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Proxy receives DDL</h4><p>client <span class="mono">create_collection</span>, after Proxy checks, enters <span class="mono">ddQueue</span> strictly serially.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Issue number</h4><p class="mono">idAllocator.Alloc</p><p>RootCoord allocates a globally unique collectionID for the new collection.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Fix order</h4><p class="mono">tsoAllocator</p><p>get a TSO timestamp to mark this structural change's place on the global timeline.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Book the record</h4><p>write the collection definition into <span class="mono">IMetaTable</span>, persisted to etcd via catalog/kv.</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>Broadcast</h4><p>deliver this DDL in order over the streaming channel so nodes update their views.</p></div></div>
</div>

<p>What's most worth remembering here is the order and cooperation of "<strong>issue number → fix order → book record → broadcast</strong>": first a unique identity, then a position in time, then writing it as an authoritative record, and only then letting the whole cluster know.
If any step goes wrong, the cluster's understanding of "who this collection is, when it was created, what it looks like" cracks. RootCoord chaining these four steps in one place, in order, is precisely the weight behind the word "authoritative."</p>

<table class="t">
  <tr><th>Responsibility</th><th>Mechanism</th><th>Interface / file</th></tr>
  <tr><td>Create/drop collection, partition, alias, db</td><td>Serialized DDL registration</td><td class="mono">IMetaTable</td></tr>
  <tr><td>Authoritative in-memory metadata view</td><td>Startup replay + read cache</td><td class="mono">MetaTable struct</td></tr>
  <tr><td>Metadata persistence</td><td>Write to etcd (via catalog/kv)</td><td class="mono">meta_table.go</td></tr>
  <tr><td>Issue timestamps</td><td>Global TSO allocator</td><td class="mono">tsoAllocator</td></tr>
  <tr><td>Issue unique IDs</td><td>Global ID allocator</td><td class="mono">idAllocator</td></tr>
</table>

<h2>Big job two: TSO, the cluster's unified clock</h2>
<p><strong>TSO (Timestamp Oracle)</strong> is RootCoord's weightiest job. It promises one thing, but a priceless one: every timestamp it emits is <strong>globally unique and monotonically increasing</strong>.
With it, writes and queries scattered across machines can be placed on <strong>one timeline</strong> and ordered — exactly the source of Lesson 3's "role of timestamps" and Lesson 10's Proxy "getting a timestamp."
Without a unified clock, a distributed system cannot answer the most basic question: "which of these two events came first?"</p>

<p>This timestamp is conceptually a <strong>hybrid value</strong>: the high bits are physical time (wall-clock milliseconds), the low bits a logical counter, packed into one 64-bit integer. The physical part keeps it roughly tracking real time,
the logical part keeps many emitted in the same millisecond distinct. You needn't memorize exact bit widths; just grasp the intuition: <strong>it acts like time yet guarantees uniqueness and order</strong>. Hence comparing two timestamps
equals comparing the order of two events on the global timeline — the cornerstone for Milvus's consistent reads, read/write isolation, and "data up to a given point in time."</p>

<p>TSO also has an elegant engineering design: <strong>batch allocation + high-water-mark persistence</strong>. RootCoord does not write etcd for each timestamp (too slow); instead it periodically advances and persists a <strong>high-water mark</strong> to etcd,
after which, within that already-persisted range, issuing timestamps is pure in-memory work — very fast. A background ticker periodically calls <span class="mono">UpdateTSO</span> to advance and flush the mark. This is both fast and <strong>crash-safe</strong>:
if RootCoord dies and restarts, the mark it reads back from etcd is always <strong>greater than or equal to</strong> any timestamp previously issued, so the fatal regression "timestamps after restart are smaller than before" can never happen.</p>

<p>Why is "never regress" so important? Because all of Milvus's consistency rests on the assumption that "timestamps can be compared." A query carries a <strong>read-guarantee timestamp</strong>, agreeing "I want to read all writes up to this point";
writes each fall into the log carrying their own timestamps. As long as timestamps are globally monotonic, a node can cleanly decide "which writes this query should see, and which are too new and should be ignored." Once timestamps regress or repeat, that decision collapses:
data that should be visible gets missed, or data that shouldn't appear surfaces early — and consistency breaks. So RootCoord would rather spend a bit more on persistence than let the iron law of "monotonic" slip. This is also why time-issuing <strong>can have only one source</strong>:
two clocks each issuing their own can never guarantee global monotonicity.</p>

<p>A common question lurks here: if issuing each timestamp is so careful, won't it become the cluster's bottleneck? The answer is no — precisely because of batch allocation, <strong>the vast majority of timestamp requests complete instantly in memory</strong>,
and only the periodic mark advance touches etcd. In other words, the slow step is amortized down to a very low frequency, while the fast step carries nearly all the traffic. This is a classic distributed-systems trade-off — "<strong>batch the expensive operation, make the cheap operation high-frequency</strong>" —
and you'll see the same pattern again when we cover segment allocation and ID allocation. Grasp TSO and you hold the key to reading Milvus's consistency model.</p>

<div class="timeline">
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t1</span><span class="tl-c">Proxy enqueues write A, gets timestamp ts=100 from RootCoord</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t2</span><span class="tl-c">Another Proxy writes B, gets ts=101 (100 is never reissued)</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t3</span><span class="tl-c">Query C gets read-guarantee ts=102, reads all writes with ts&lt;=102</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">t4</span><span class="tl-c">Background ticker advances the high-water mark and persists to etcd (no regression on crash)</span></div>
</div>

<h2>Big job three: globally unique IDs</h2>
<p>Besides handing out time, RootCoord <strong>hands out numbers</strong>. Collections, partitions, segments — each needs a <strong>cluster-wide unique</strong> 64-bit ID to identify itself. This is highly isomorphic to TSO:
also required to be unique, also <strong>batch-allocated</strong> for performance — fetch a range of IDs from the persistent layer into memory at once, then issue within that range as pure in-memory work, fetching the next range when exhausted.
So whatever machine, whatever moment requests, the IDs never collide. When the Proxy wants to create a collection it grabs a batch from RootCoord's <span class="mono">idAllocator.Alloc(count)</span> in one shot.</p>

<p>You might ask: why not use locally generated random IDs like UUIDs? Because Milvus needs more than "unique" — it needs "<strong>compact and comparable</strong>": a 64-bit integer saves memory and indexes better than a 128-bit string, and an increasing sequence number even carries a hint of "who was created first."
Central issuing adds one round-trip to RootCoord, but thanks to batch allocation that round-trip is amortized to nearly nothing, buying in return a clean, unified, sortable identity system for the whole cluster. Once more, a classic trade-off of "spend a little coordination cost to gain global order."</p>

<p>Putting "issue time" and "issue numbers" in one place is no accident: both need a <strong>globally unique issuing source</strong>, both rely on the same "fetch a range, dispense fast in memory, persist a high-water mark against regression" mechanism.
RootCoord is their natural home — it is already the cluster's "single, authoritative, serialized" point. Grasp this and you see why we call it the "<strong>ordering brain</strong>":
the final verdict on <strong>time</strong> and <strong>identity</strong> in the cluster comes from here.</p>

<p>Worth noting is the <strong>shared origin</strong> of TSO and ID in the implementation: in the source they share the same "global allocator" idea underneath, even reusing the same KV handle for persistence (you'll see <span class="mono">tsoKV</span> fed to both allocators in the code below).
The only difference: one allocates timestamps that "track the wall clock," the other allocates pure sequence numbers that "just increase, indifferent to physical time." Making them isomorphic siblings cuts implementation burden and gives "uniqueness" one unified source of guarantee.
For users, just remember: <strong>wherever a globally unique identifier or a globally unified ordering is needed, RootCoord the issuing desk stands behind it</strong>.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/rootcoord/root_coord.go</span><span class="ln">Wiring the TSO and ID allocators</span></div>
  <pre><span class="kw">type</span> Core <span class="kw">struct</span> {
    <span class="cm">// ...</span>
    idAllocator  allocator.Interface   <span class="cm">// global unique ID allocator</span>
    tsoAllocator tso2.Allocator        <span class="cm">// global TSO timestamp allocator</span>
}

<span class="cm">// At startup: wire the ID allocator</span>
idAllocator := allocator.NewGlobalIDAllocator(globalIDAllocatorKey, tsoKV)
c.idAllocator = idAllocator

<span class="cm">// Wire the TSO allocator (backed by the tso package's GlobalTSOAllocator)</span>
tsoAllocator := tso2.NewGlobalTSOAllocator(globalTSOAllocatorKey, tsoKV)
c.tsoAllocator = tsoAllocator

<span class="cm">// The scheduler receives both; DDL tasks use them to get numbers and order</span>
c.scheduler = newScheduler(c.ctx, c.idAllocator, c.tsoAllocator)</pre>
</div>

<h2>How DDL propagates, and where RootCoord lives</h2>
<p>Once a DDL is booked, merely writing the meta table isn't enough — backend nodes must also learn "the collection changed." RootCoord broadcasts DDL over a <strong>streaming channel</strong>,
letting relevant nodes consume the structural change in order. This "DDL over a streaming log" path is itself subtle, but it belongs to a later treatment of the <strong>write path / streaming system</strong>; here just keep one intuition:
<strong>DDL isn't done once written — like a timestamped message, it is delivered in order to those who need it</strong>. Only then can schema changes achieve, in a distributed setting, "everyone eventually sees the same version, in a consistent order."</p>

<p>Why must DDL also carry a timestamp and travel an ordered log? Because structural change and data write are really <strong>the same kind of problem</strong> in a distributed setting: both need "order" to become global consensus. Imagine an "add a field" DDL and a batch of inserts happening almost simultaneously;
nodes must decide whether that batch should be interpreted under the old or the new schema — and it's exactly the TSO timestamps each carries that decide. So DDL and DML are uniformly ordered on the same timeline, and a node need only faithfully "replay in timestamp order"
to reach a self-consistent, identical-for-everyone view of the world. This again confirms RootCoord's core value as the "ordering brain": <strong>by folding both structure and data into one ordering, the whole cluster gains a unified causality.</strong></p>

<p>Finally, recall last lesson's conclusion: today's RootCoord is not a standalone process but <strong>runs inside the single MixCoord process</strong> together with DataCoord and QueryCoord, playing the "root coordination" logical role (see Lesson 9).
So when we say "ask RootCoord for a timestamp," physically we are talking to that slice of logic inside the MixCoord process. We give it its own lesson because its <strong>responsibility boundary</strong> is clear and critical:
who orders, who issues numbers, who guards metadata — for these three, look to RootCoord. Next lesson turns to the other write-side brain, <strong>DataCoord</strong> (Lesson 12), to see how segments get allocated, sealed, and flushed.</p>

<div class="flow">
  <div class="node"><div class="nt">Proxy</div><div class="nd">DDL / get time·ID</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">RootCoord</div><div class="nd">register·time·numbers</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">meta table</div><div class="nd">IMetaTable → etcd</div></div>
  <div class="arrow">＋</div>
  <div class="node"><div class="nt">streaming</div><div class="nd">broadcast DDL to nodes</div></div>
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  RootCoord is the cluster's "single, authoritative, serialized" point. It does three things, all of which must be done in <strong>one place</strong>: register DDL (so a collection's structure has only one version), issue TSO timestamps (one unified timeline for the whole cluster), and issue globally unique IDs (a non-colliding identity for everything).
  Both timestamps and IDs trade "batch a range + persist a high-water mark" for being fast yet regression-proof; metadata is backed by etcd persistence and replayed on startup. It co-lives with the other two coordinators inside the MixCoord process — logically independent, physically cohabiting.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>DDL + metadata</strong>: create/drop collection, partition, alias, db all funnel to RootCoord for serial registration in <span class="mono">IMetaTable</span>, backed by etcd persistence.</li>
    <li><strong>TSO timestamps</strong>: globally unique, monotonically increasing; conceptually a 64-bit "physical time + logical counter" hybrid giving distributed events one timeline.</li>
    <li><strong>Batch + high-water mark</strong>: TSO/ID are batch-allocated and dispensed fast in memory; a high-water mark persisted to etcd prevents any regression on restart.</li>
    <li><strong>Global IDs</strong>: unique 64-bit identities for collections/partitions/segments, dispensed in batches by <span class="mono">idAllocator.Alloc</span>.</li>
    <li><strong>Lives in MixCoord</strong>: today RootCoord is a logical role inside the MixCoord process (Lesson 9); DDL is broadcast in order to nodes over a streaming channel.</li>
  </ul>
</div>
""",
}


LESSON_12 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
RootCoord 管"结构与时间"，这一课的 <strong>DataCoord（数据协调者）</strong>则管"<strong>数据落到哪、怎么落、何时清</strong>"。它是写入侧的总调度：把涌进来的行分配到一个个<strong>段（segment）</strong>里，
在合适的时机封存、落盘、合并、回收，还顺手安排索引怎么建。读懂 DataCoord，你就理解了第 7 课"日志即数据、段即载体"在分布式层面的真正运转。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把 DataCoord 想成一座<strong>大型仓库的调度主管</strong>。货物（数据行）源源不断到货，他先指挥工人把货<strong>码进当前正在装的那个货箱（growing 段）</strong>；
  箱子装满了，就<strong>封箱（sealed）</strong>、贴上清单、搬进<strong>永久库房（落盘成 binlog）</strong>。库房里零碎的小箱子多了，他安排<strong>并箱（compaction）</strong>腾地方；
  过期作废的箱子，他派人<strong>清运（GC）</strong>。他还得决定每条入库流水线（vchannel）由哪个工人（datanode）负责，以及哪些货要<strong>额外编目录（建索引）</strong>方便日后快速查找。他从不亲手搬货，但整个仓库的秩序全在他脑子里。
</div>

<h2>段的分配：从一行数据说起</h2>
<p>当一批 insert 经 Proxy 写进来，这些行最终要被组织进<strong>段（segment）</strong>——Milvus 存储与检索的基本单位（第 7 课）。但"该把这批行放进哪个段"并不是节点自己拍脑袋决定的，而是由 DataCoord 统一<strong>分配</strong>。
它维护着每个集合、每个分片当前<strong>正在增长（growing）</strong>的那个段，把新来的行分派进去；当这个段<strong>写满了</strong>（行数或容量达到阈值），或者<strong>攒够久了</strong>（超时），就把它<strong>封存（seal）</strong>，再开一个新的 growing 段接着收。</p>

<p>为什么要由一个中心来分配段，而不是每个 datanode 各自为政？因为段是要被<strong>全集群一致地引用</strong>的：QueryCoord 要知道有哪些段、分别加载到哪台 QueryNode；compaction 要知道哪些小段可以合并；GC 要知道哪些段已经没用。
如果段的产生是去中心、随意的，这些下游协调就会失去统一的"账本"。DataCoord 把"段从哪来、现在是什么状态"这件事<strong>收口管理</strong>，整个写入侧才有了一致、可追溯的视图。它分配段时会给段打上 <span class="mono">commonpb.SegmentState_Growing</span> 的初始状态，
后续每一次状态流转也都由它记账。</p>

<p>这里有一个容易混淆的点值得说清：DataCoord <strong>分配</strong>段、<strong>记录</strong>段的状态，但真正把数据<strong>写进</strong>段、把段<strong>刷成文件</strong>的，是 datanode / streamingnode 这些干活的节点。这又是第 9 课"协调者决策、节点执行"的一次具体落地——
DataCoord 是那个发号施令、在账本上勾画的大脑，节点才是搬砖落盘的双手。把"决策"与"执行"分开，写入侧才能既有统一秩序、又能水平扩展出多个 worker 并行干活。</p>

<p>段的大小也是一门学问，而这恰恰是 DataCoord 要权衡的：段太小，则数量爆炸，查询要打开成百上千个文件、元数据也臃肿；段太大，则单段加载慢、compaction 一次要搬动的数据量也大。
于是 DataCoord 用"<strong>写满阈值 + 超时</strong>"两个条件来折中——高写入量的集合靠"写满"快速封段，低写入量的集合靠"超时"避免一个段半天攒不满、迟迟不能落盘被查询到。这个看似不起眼的"何时封段"决策，
直接影响着集合后续的查询性能与存储开销，是 DataCoord 作为写入侧大脑最日常、也最关键的判断之一。</p>

<h2>段的一生：四个状态的旅程</h2>
<p>一个段从诞生到消亡，会经历一条清晰的<strong>状态机</strong>。这些状态名不是随便起的，它们是 proto 里定义好的枚举 <span class="mono">commonpb.SegmentState_*</span>（注意：它属于 go-api 的 commonpb 包，不在 datacoord 自己的类型里）。
理解这条状态流转，就理解了数据"从内存里的活跃写入，一步步固化成磁盘上不可变文件"的全过程：</p>

<div class="timeline">
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">Growing</span><span class="tl-c">正在增长：DataCoord 把新行不断分配进来，段还在内存里活跃接收写入</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">Sealed</span><span class="tl-c">已封存：写满或超时，不再接收新行，等待落盘</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">Flushing</span><span class="tl-c">落盘中：正在把段写成 binlog 文件持久化到对象存储</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">Flushed</span><span class="tl-c">已落盘：成为<strong>不可变</strong>的持久段，可被加载、索引、合并</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">Dropped</span><span class="tl-c">已废弃：被 compaction 合并掉或被删除，等待 GC 清理其文件</span></div>
</div>

<p>这条链路的关键转折是 <strong>Flushed</strong>：一旦落盘，段就<strong>不可变（immutable）</strong>了。这是 Milvus 整个存储模型的基石——不可变意味着可以安全地被多个 QueryNode 同时加载、可以放心地建索引、可以被缓存而不必担心被改写。
所有的"修改"（删除、更新）都不去改已落盘的段，而是以<strong>新的写入 + delta 日志</strong>的形式追加，查询时再把基础数据与 delta 合并出最新视图。这正是第 7 课"日志即数据"的精髓：<strong>只追加、不就地改</strong>。
DataCoord 的状态机，就是在严格守护这个"一旦固化便不可变"的契约。</p>

<p>除了主干的四态，还有几个旁支状态：<span class="mono">Importing</span>（批量导入专用的中间态）、<span class="mono">NotExist</span>（占位/不存在），以及上面提到的 <span class="mono">Dropped</span>。
你不必背全，但要抓住主线直觉：<strong>段的一生，是一条"从可变到不可变、从内存到磁盘、从活跃到回收"的单向旅程</strong>，而 DataCoord 就是这条旅程上每一步的签发人。每一次状态切换它都会落账到元数据里，
这样即便节点重启、协调者切换，集群也能从账本里恢复出"每个段现在走到了哪一步"。</p>

<p>把段状态做成一台显式的状态机，还有一个深层好处：<strong>它让"数据现在安不安全"变成一个可被精确判断的问题</strong>。一个还在 Growing 的段，数据只在内存里，节点一挂就可能丢；一个已经 Flushed 的段，数据已在对象存储里，怎么挂都能恢复。
于是当用户调用 flush 接口、想确保"我刚写的数据已经持久化"，系统只需检查相关段是否都已到达 Flushed 状态即可给出确定的回答。状态机不只是内部记账，它把"持久性保证"这件抽象的事，落成了一个个看得见、查得到的具体状态。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/datacoord/segment_manager.go</span><span class="ln">分配新段时打上 Growing，封存时切到 Sealed</span></div>
  <pre><span class="kw">import</span> <span class="st">"github.com/milvus-io/milvus-proto/go-api/v3/commonpb"</span>

<span class="cm">// 新分配的段，初始状态为 Growing</span>
segmentInfo := &amp;SegmentInfo{
    State: commonpb.SegmentState_Growing,
    <span class="cm">// ... collectionID / partitionID / channel ...</span>
}

<span class="cm">// 写满或超时后，把段切到 Sealed，不再接收新行</span>
<span class="kw">if</span> err := s.meta.SetState(ctx, id, commonpb.SegmentState_Sealed); err != nil {
    <span class="kw">return</span> err
}</pre>
</div>

<h2>落盘、合并、回收：三件后台大事</h2>
<p>段被封存只是开始，DataCoord 还要操心三件持续运转的后台工作。第一件是 <strong>Flush（落盘）</strong>：把 sealed 段真正写成 binlog 文件、持久化到对象存储。落盘之后，数据才算"安全着陆"——
即便所有内存数据丢失，也能从对象存储里重建。Flush 由 DataCoord 调度、datanode 执行，是连接"内存中的活跃写入"与"磁盘上的持久档案"的桥梁。</p>

<p>值得一提的是，一次 flush 并非写出单个文件，而是一组 <strong>binlog</strong>——列数据、统计信息、删除日志各自分开写。按列拆分让后续查询只读需要的字段，把删除单独存放则维持了"只追加"的纪律。于是一个段在对象存储里其实是一小簇文件，DataCoord 会把它们的路径全部记进元数据，供日后加载、compaction 与 GC 精确引用。</p>

<table class="t">
  <tr><th>后台工作</th><th>触发时机</th><th>由谁执行</th><th>效果</th></tr>
  <tr><td><strong>Flush 落盘</strong></td><td>段被 seal 后</td><td class="mono">datanode</td><td>段固化为不可变 binlog，数据安全着陆</td></tr>
  <tr><td><strong>Compaction 合并</strong></td><td>小段堆积 / delta 过多</td><td class="mono">datanode</td><td>小段并大段、应用 delete，查询更轻快</td></tr>
  <tr><td><strong>GC 回收</strong></td><td>文件无引用且过保留期</td><td class="mono">datacoord</td><td>从对象存储删除垃圾，回收空间省成本</td></tr>
  <tr><td><strong>索引调度</strong></td><td>段 flushed 后</td><td class="mono">datanode worker</td><td>为段构建 ANN 索引，加速检索</td></tr>
</table>

<p>第二件是 <strong>Compaction（合并）</strong>。随着不断 flush，集合里会积累大量<strong>小段</strong>，还会因为删除而产生大量 delta 日志。小段多了，查询要打开的文件就多、开销就大；delta 多了，每次查询都要做更多"基础数据 + 删除"的合并。
于是 DataCoord 周期性地调度 compaction，把多个小段<strong>合并成大段</strong>、把 delete 日志<strong>应用进数据</strong>（即所谓 L0 compaction），还有为提升检索局部性的 clustering compaction。合并的具体算法（深入是第 19 课）这里不展开，
但要记住它的价值：<strong>compaction 是用后台的整理，换前台查询的轻快</strong>。它是 LSM 式"只追加"存储模型必然要付出的代价，也是它能长期保持高性能的秘诀。</p>

<p>compaction 的调度也并非一刀切，而是有多种<strong>策略</strong>各司其职：有的盯着"小段太多"触发合并，有的专门处理 L0 层里堆积的 delete 日志，有的为提升向量数据的局部性做 clustering 重排，还有的在用户主动要求时做强制合并。
DataCoord 会综合段的数量、大小、delete 比例等信号，挑选合适的时机与策略下发任务——既不能太频繁（白白消耗算力、和写入抢资源），也不能太懒（让小段和 delete 越积越拖慢查询）。这种"什么时候、用哪种方式整理"的拿捏，
正是写入侧性能调优的关键一环。</p>

<p>第三件是 <strong>GC（垃圾回收）</strong>。compaction 合并掉的旧段、被删除的集合、导入失败的残留——这些文件如果不清理，对象存储会越积越多、白白烧钱。DataCoord 的 <span class="inline">garbage_collector</span> 周期性地巡检，
找出那些"已经没有任何元数据引用、且过了安全保留期"的文件，安全地从对象存储删除。这里的分寸很关键：删早了可能误删还在被某个慢查询引用的数据，删晚了又浪费空间，所以 GC 总是<strong>保守而谨慎</strong>，宁可多留一会儿也不冒错删的风险。</p>

<p>把这三件事放在一起看，你会发现它们共同回答了一个问题：<strong>如何让一个"只追加、不就地改"的存储系统长期保持健康？</strong>只追加意味着写得快、并发友好、天然可靠，但代价是文件会不断增多、删除只是逻辑标记而非物理移除。
Flush 负责把数据安全固化，compaction 负责把碎片整理、把逻辑删除真正兑现，GC 负责把整理后留下的垃圾清走。三者像一支后勤队伍，在前台查询毫无察觉的情况下，默默维持着存储的整洁与高效。
这也是为什么我们说 DataCoord 是"<strong>写入侧的总管</strong>"——它操心的不只是"怎么写进去"，更是"写进去之后这堆数据如何长治久安"。</p>

<div class="cols">
  <div class="col"><h4>Compaction 合并</h4><p>把许多<strong>小段并成大段</strong>、把 delete 日志应用进数据，减少查询要打开的文件数与合并开销。是"<strong>整理</strong>"，目标是让查询更快。深入见第 19 课。</p></div>
  <div class="col"><h4>GC 回收</h4><p>把<strong>没人再引用</strong>且过了保留期的文件从对象存储删除，回收空间、节省成本。是"<strong>清运</strong>"，目标是不让垃圾无限堆积。原则是宁可保守也不误删。</p></div>
</div>

<h2>通道分配与索引调度，以及"没有 indexnode"</h2>
<p>除了管段，DataCoord 还负责<strong>通道（channel）分配</strong>：决定每个集合的每条 <span class="mono">vchannel</span>（虚拟数据通道）由哪个 datanode / streamingnode 来负责消费与落盘。
通道是写入流的载体，把它们均匀地分给各个节点，写入吞吐才能水平扩展；某个节点挂了，DataCoord 还要把它负责的通道<strong>重新分配</strong>给别人，保证写入不中断。这套"谁负责哪条通道"的账，同样由 DataCoord 统一记。</p>

<p>通道分配看似只是"派活"，其实暗含着写入侧的<strong>负载均衡</strong>与<strong>故障容错</strong>两层考量。负载均衡上，DataCoord 要避免把太多繁忙的通道压在同一个节点，否则它会成为写入瓶颈；
容错上，一旦它通过 etcd 的会话机制（第 9 课、第 14 课会细讲）发现某个 datanode 失联，就必须立刻把那个节点身上的通道转交给健在的节点，让中断的写入尽快恢复。你会发现，这和下一课 QueryCoord 给查询侧做的"段/通道分配 + 再平衡"
在思路上高度对称——一个管写入侧的均衡，一个管查询侧的均衡，但都遵循"中心记账、动态调度、故障转移"这同一套协调者哲学。</p>

<p>最后是<strong>索引构建调度</strong>。向量要能被高效检索，得先建好 ANN 索引（第 5、6 课）。DataCoord 负责<strong>调度</strong>这些索引构建任务：哪个段该建索引、用什么参数、派给谁建。
这里有一个常被误解的事实，必须讲清楚：<strong>Milvus 今天没有独立的 indexnode 进程</strong>。索引构建任务虽然由 DataCoord 调度，但真正<strong>执行构建的是 datanode 里的 worker</strong>。
在代码里你能看到证据：<span class="mono">DataNodeClient</span> 接口直接<strong>内嵌</strong>了 <span class="mono">workerpb.IndexNodeClient</span>——也就是说，"索引节点"的能力被合并进了 datanode，而不是另起一个进程。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/types/types.go</span><span class="ln">DataNodeClient 内嵌 IndexNode 能力：没有独立 indexnode</span></div>
  <pre><span class="kw">type</span> DataNodeClient <span class="kw">interface</span> {
    component
    datapb.DataNodeClient
    workerpb.IndexNodeClient   <span class="cm">// 索引构建 worker 直接并入 datanode</span>
}</pre>
</div>

<p>这条"没有 indexnode"的事实，和第 9 课"MixCoord 把三个协调者合进一个进程"是同一种演进方向：<strong>把曾经独立的角色合并，降低部署与运维的复杂度</strong>。早期 Milvus 确有独立的 indexnode，
但随着架构演进，索引构建被收进了 datanode worker。如果你读到的旧文档还在讲"indexnode 是一个独立组件"，请以代码为准——<strong>代码里 DataNodeClient 内嵌 IndexNodeClient，就是当下的事实</strong>。
DataCoord 因此成了写入侧名副其实的总管：段、通道、落盘、合并、回收、索引调度，写数据这件事的方方面面，都在它的账本上。</p>

<p>为什么索引构建特别适合并入 datanode，而不是单独成节点？因为索引构建本质上是一个<strong>批处理型的重计算任务</strong>：读取一个已 flushed 的段、在上面跑 ANN 建图算法、把结果写回对象存储。
它和 datanode 已经在做的"读写段文件"高度同源，共享同一批数据访问能力与节点资源。把它并进来，既省去了一类进程的部署与监控，又让索引构建能就近复用 datanode 的 IO 与缓存。这正体现了 Milvus 近年架构演进的一条主线：
<strong>能合则合，用更少的进程类型承担更多职责</strong>，从而让中小规模部署更轻、运维更省心——这与第 8 课 Standalone / Cluster 的形态选择遥相呼应。</p>

<div class="flow">
  <div class="node"><div class="nt">Proxy 写入</div><div class="nd">insert 经 vchannel</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">DataCoord</div><div class="nd">分段·调度·记账</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">DataNode worker</div><div class="nd">落盘·合并·建索引</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">对象存储</div><div class="nd">binlog / 索引文件</div></div>
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  DataCoord 是写入侧的总调度，核心是一台<strong>段的状态机</strong>：Growing → Sealed → Flushing → Flushed（再到 Dropped）。它分配段、记录每一次状态流转，但落盘、合并、建索引都交给 datanode worker 执行——决策与执行分离。
  落盘把数据安全固化成不可变 binlog；compaction 用后台整理换前台查询轻快；GC 保守地清运无人引用的文件；通道分配让写入水平扩展。关键事实：<strong>没有独立 indexnode</strong>，索引构建 worker 已并入 datanode（DataNodeClient 内嵌 IndexNodeClient）。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>段的分配</strong>：DataCoord 维护每个分片当前的 growing 段，写满或超时就 seal、再开新段；段状态由它统一记账。</li>
    <li><strong>状态机</strong>：<span class="mono">commonpb.SegmentState_*</span> 走 Growing → Sealed → Flushing → Flushed → Dropped；注意它在 go-api 的 commonpb 包，不在 datapb。</li>
    <li><strong>Flushed 即不可变</strong>：落盘后的段只读，删除/更新以新写入 + delta 形式追加——只追加、不就地改（第 7 课）。</li>
    <li><strong>三件后台事</strong>：Flush 落盘、Compaction 合并小段与应用 delete（深入第 19 课）、GC 保守回收无引用文件。</li>
    <li><strong>通道与索引</strong>：分配 vchannel 给节点；调度索引构建。<strong>没有独立 indexnode</strong>——构建 worker 并入 datanode（DataNodeClient 内嵌 IndexNodeClient）。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
RootCoord governs "structure and time"; this lesson's <strong>DataCoord (the data coordinator)</strong> governs "<strong>where data lands, how it lands, when it's cleaned</strong>." It is the write-side master scheduler: it assigns incoming rows into <strong>segments</strong>,
seals, flushes, compacts, and reclaims them at the right moments, and arranges how indexes get built along the way. Understand DataCoord and you grasp how Lesson 7's "log-as-data, segment-as-vessel" actually runs at the distributed layer.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of DataCoord as the <strong>dispatch supervisor of a giant warehouse</strong>. Goods (data rows) keep arriving; he first directs workers to <strong>stack them into the crate currently being filled (the growing segment)</strong>;
  when a crate is full, it gets <strong>sealed</strong>, labeled with a manifest, and moved into the <strong>permanent vault (flushed to binlogs)</strong>. When too many small crates clutter the vault, he schedules <strong>merging (compaction)</strong> to free space;
  expired, voided crates he sends crews to <strong>haul away (GC)</strong>. He also decides which worker (datanode) handles each intake line (vchannel), and which goods need an <strong>extra catalog (index build)</strong> for fast future lookup. He never lifts a crate himself, yet the whole warehouse's order lives in his head.
</div>

<h2>Segment allocation: starting from a single row</h2>
<p>When a batch of inserts comes in via the Proxy, those rows must ultimately be organized into <strong>segments</strong> — Milvus's basic unit of storage and retrieval (Lesson 7). But "which segment this batch goes into" is not decided by a node on a whim; it is uniformly <strong>allocated</strong> by DataCoord.
It maintains, for each collection and each shard, the segment currently <strong>growing</strong>, and dispatches new rows into it; when that segment is <strong>full</strong> (row count or capacity hits a threshold) or has <strong>aged enough</strong> (timeout), it <strong>seals</strong> it and opens a fresh growing segment to keep receiving.</p>

<p>Why must one center allocate segments rather than each datanode going its own way? Because segments are <strong>referenced consistently cluster-wide</strong>: QueryCoord needs to know which segments exist and which QueryNode each is loaded onto; compaction needs to know which small segments can merge; GC needs to know which segments are useless.
If segment creation were decentralized and arbitrary, these downstream coordinations would lose a unified "ledger." By <strong>funneling management</strong> of "where segments come from and what state they're in," the whole write side gains a consistent, traceable view. When allocating a segment it stamps the initial state <span class="mono">commonpb.SegmentState_Growing</span>,
and books every later state transition too.</p>

<p>One easily-confused point worth clarifying: DataCoord <strong>allocates</strong> segments and <strong>records</strong> their states, but what actually <strong>writes</strong> data into segments and <strong>flushes</strong> them into files are the working nodes — datanode / streamingnode. This is again Lesson 9's "coordinators decide, nodes execute" made concrete —
DataCoord is the brain that gives orders and marks the ledger, while nodes are the hands that haul bricks and flush to disk. Separating "decision" from "execution" lets the write side have both unified order and the ability to scale out multiple workers in parallel.</p>

<p>Segment size is also an art, and it is exactly what DataCoord must weigh: too small, and the count explodes — queries open hundreds or thousands of files and metadata bloats; too big, and a single segment loads slowly and each compaction moves a huge amount of data.
So DataCoord compromises with two conditions — "<strong>fill threshold + timeout</strong>": high-write collections seal segments quickly by "fill," low-write collections rely on "timeout" so a segment doesn't sit half-full for ages, unable to flush and become queryable. This seemingly humble "when to seal" decision
directly shapes a collection's later query performance and storage overhead, and is among the most everyday yet most critical judgments DataCoord makes as the write side's brain.</p>

<h2>A segment's life: a journey of four states</h2>
<p>From birth to death, a segment follows a clear <strong>state machine</strong>. These state names aren't arbitrary; they are proto-defined enums <span class="mono">commonpb.SegmentState_*</span> (note: they belong to go-api's commonpb package, not datacoord's own types).
Understand this transition and you understand the whole process of data "going from active in-memory writes, step by step, to immutable files on disk":</p>

<div class="timeline">
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">Growing</span><span class="tl-c">growing: DataCoord keeps allocating new rows in; the segment is active in memory receiving writes</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">Sealed</span><span class="tl-c">sealed: full or timed out, no longer accepts new rows, awaiting flush</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">Flushing</span><span class="tl-c">flushing: being written into binlog files persisted to object storage</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">Flushed</span><span class="tl-c">flushed: becomes an <strong>immutable</strong> persistent segment, loadable, indexable, mergeable</span></div>
  <div class="tl-row"><span class="tl-dot"></span><span class="tl-t">Dropped</span><span class="tl-c">dropped: merged away by compaction or deleted, awaiting GC to clean its files</span></div>
</div>

<p>This path's key turning point is <strong>Flushed</strong>: once flushed, a segment becomes <strong>immutable</strong>. This is the cornerstone of Milvus's entire storage model — immutability means it can be safely loaded by many QueryNodes at once, indexed without worry, and cached without fear of being overwritten.
All "modifications" (deletes, updates) don't touch the flushed segment; they are appended as <strong>new writes + delta logs</strong>, and queries merge base data with deltas into the latest view. This is exactly Lesson 7's essence of "log-as-data": <strong>append only, never modify in place</strong>.
DataCoord's state machine is precisely guarding this contract of "once solidified, immutable."</p>

<p>Besides the four main states, there are a few side states: <span class="mono">Importing</span> (an intermediate state for bulk import), <span class="mono">NotExist</span> (placeholder/absent), and the <span class="mono">Dropped</span> above.
You needn't memorize them all, but grasp the main thread: <strong>a segment's life is a one-way journey "from mutable to immutable, from memory to disk, from active to reclaimed,"</strong> and DataCoord is the issuer of every step on it. Each transition it books into metadata,
so that even if a node restarts or a coordinator fails over, the cluster can recover from the ledger "which step each segment has reached."</p>

<p>Making segment state an explicit state machine has a deeper benefit: <strong>it turns "is the data safe right now" into a precisely answerable question</strong>. A still-Growing segment has data only in memory — a node crash may lose it; an already-Flushed segment has data in object storage — recoverable through any crash.
So when a user calls the flush API wanting to ensure "the data I just wrote is persisted," the system need only check whether the relevant segments have all reached Flushed to give a definite answer. The state machine isn't just internal bookkeeping; it lands the abstract matter of "durability guarantee" into concrete, visible, queryable states.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/datacoord/segment_manager.go</span><span class="ln">stamp Growing on a new segment, switch to Sealed when sealing</span></div>
  <pre><span class="kw">import</span> <span class="st">"github.com/milvus-io/milvus-proto/go-api/v3/commonpb"</span>

<span class="cm">// A newly allocated segment starts in Growing</span>
segmentInfo := &amp;SegmentInfo{
    State: commonpb.SegmentState_Growing,
    <span class="cm">// ... collectionID / partitionID / channel ...</span>
}

<span class="cm">// After full or timeout, switch the segment to Sealed; no more new rows</span>
<span class="kw">if</span> err := s.meta.SetState(ctx, id, commonpb.SegmentState_Sealed); err != nil {
    <span class="kw">return</span> err
}</pre>
</div>

<h2>Flush, compact, reclaim: three background jobs</h2>
<p>Sealing a segment is just the start; DataCoord must also tend three continuously running background jobs. First is <strong>Flush</strong>: turning a sealed segment into binlog files, persisted to object storage. Only after flush has data "safely landed" —
even if all in-memory data is lost, it can be rebuilt from object storage. Flush is scheduled by DataCoord and executed by datanode; it is the bridge from "active in-memory writes" to "durable archives on disk."</p>

<p>Worth noting: a flush isn't a single file but a set of <strong>binlogs</strong> — column data, statistics, and delete logs all written separately. Splitting by column lets later queries read only the fields they need, and keeping deletes apart preserves the "append-only" discipline. So one segment becomes a small bundle of files in object storage, and DataCoord records the paths to all of them in metadata for later loading, compaction, and GC to reference precisely.</p>

<table class="t">
  <tr><th>Background job</th><th>Trigger</th><th>Executed by</th><th>Effect</th></tr>
  <tr><td><strong>Flush</strong></td><td>after a segment is sealed</td><td class="mono">datanode</td><td>solidify into immutable binlog; data safely landed</td></tr>
  <tr><td><strong>Compaction</strong></td><td>small segments / too many deltas</td><td class="mono">datanode</td><td>merge small into big, apply deletes; lighter queries</td></tr>
  <tr><td><strong>GC</strong></td><td>files unreferenced and past retention</td><td class="mono">datacoord</td><td>delete garbage from object storage; reclaim space</td></tr>
  <tr><td><strong>Index scheduling</strong></td><td>after a segment is flushed</td><td class="mono">datanode worker</td><td>build ANN index for the segment; faster retrieval</td></tr>
</table>

<p>Second is <strong>Compaction</strong>. As flushes accumulate, a collection piles up many <strong>small segments</strong>, and deletions produce many delta logs. Many small segments mean more files to open per query and higher overhead; many deltas mean each query does more "base data + deletes" merging.
So DataCoord periodically schedules compaction to <strong>merge small segments into big ones</strong>, <strong>apply delete logs into data</strong> (so-called L0 compaction), plus clustering compaction to improve retrieval locality. The specific algorithms (deep dive in Lesson 19) we won't expand here,
but remember its value: <strong>compaction trades background tidying for foreground query lightness</strong>. It is the inevitable price of an LSM-style "append-only" storage model, and the secret to keeping it performant over the long run.</p>

<p>Compaction scheduling isn't one-size-fits-all either; several <strong>policies</strong> each play their part: some watch for "too many small segments" to trigger merges, some specifically handle delete logs piling up in the L0 layer, some do clustering re-layout to improve vector locality, and some force-merge on the user's explicit request.
DataCoord weighs signals like segment count, size, and delete ratio to pick the right moment and policy to dispatch tasks — neither too often (wasting compute and contending with writes) nor too lazy (letting small segments and deletes pile up and slow queries). This judgment of "when, and in which way, to tidy"
is a key part of write-side performance tuning.</p>

<p>Third is <strong>GC (garbage collection)</strong>. Old segments merged away by compaction, deleted collections, leftovers from failed imports — if these files aren't cleaned, object storage piles up and burns money for nothing. DataCoord's <span class="inline">garbage_collector</span> periodically patrols,
finds files that are "no longer referenced by any metadata and past a safe retention period," and safely deletes them from object storage. The discretion here is crucial: delete too early and you might wrongly remove data still referenced by a slow query; delete too late and you waste space. So GC is always <strong>conservative and cautious</strong>, preferring to keep things a while longer over risking a wrong deletion.</p>

<p>Look at these three together and you see they jointly answer one question: <strong>how do you keep an "append-only, never-modify-in-place" storage system healthy over the long run?</strong> Append-only means fast writes, concurrency-friendly, inherently reliable — but the price is files keep multiplying, and a delete is only a logical mark, not a physical removal.
Flush solidifies data safely, compaction tidies fragments and truly redeems logical deletes, GC hauls away the garbage left after tidying. The three act like a logistics crew, quietly keeping storage clean and efficient while foreground queries notice nothing.
This is why we call DataCoord the "<strong>write side's steward</strong>" — it worries not only about "how to write in" but about "how this pile of data stays sound for the long term once written."</p>

<div class="cols">
  <div class="col"><h4>Compaction (merge)</h4><p>Merge <strong>many small segments into big ones</strong> and apply delete logs into data, cutting the file count and merge overhead per query. It's "<strong>tidying</strong>," aimed at faster queries. Deep dive in Lesson 19.</p></div>
  <div class="col"><h4>GC (reclaim)</h4><p>Delete files that are <strong>no longer referenced</strong> and past retention from object storage, reclaiming space and cutting cost. It's "<strong>hauling away</strong>," aimed at not letting garbage pile up endlessly. The principle: rather conservative than wrongly deleting.</p></div>
</div>

<h2>Channel assignment and index scheduling, and "no indexnode"</h2>
<p>Beyond segments, DataCoord also handles <strong>channel assignment</strong>: deciding which datanode / streamingnode consumes and flushes each collection's each <span class="mono">vchannel</span> (virtual data channel).
Channels are the carriers of write streams; spreading them evenly across nodes lets write throughput scale out; if a node dies, DataCoord <strong>reassigns</strong> the channels it owned to others, keeping writes uninterrupted. This "who owns which channel" ledger is likewise kept by DataCoord.</p>

<p>Channel assignment may look like mere "task handing-out," but it quietly carries two layers of write-side concern: <strong>load balancing</strong> and <strong>fault tolerance</strong>. For balancing, DataCoord must avoid piling too many busy channels on one node, or it becomes a write bottleneck;
for tolerance, once it discovers via etcd's session mechanism (detailed in Lessons 9 and 14) that a datanode has gone missing, it must immediately hand that node's channels to healthy ones so interrupted writes recover fast. You'll find this highly symmetric, in spirit, with the next lesson's QueryCoord doing "segment/channel assignment + rebalancing" on the query side —
one balances the write side, the other the query side, but both follow the same coordinator philosophy of "central bookkeeping, dynamic scheduling, failover."</p>

<p>Finally, <strong>index-build scheduling</strong>. For vectors to be efficiently searchable, ANN indexes must be built first (Lessons 5 & 6). DataCoord <strong>schedules</strong> these index-build tasks: which segment to index, with what params, assigned to whom.
A commonly misunderstood fact must be made clear: <strong>Milvus today has no standalone indexnode process</strong>. Although index-build tasks are scheduled by DataCoord, what actually <strong>runs the build is a worker inside datanode</strong>.
You can see the evidence in code: the <span class="mono">DataNodeClient</span> interface directly <strong>embeds</strong> <span class="mono">workerpb.IndexNodeClient</span> — meaning the "index node" capability has been merged into datanode, rather than spun up as a separate process.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/types/types.go</span><span class="ln">DataNodeClient embeds IndexNode capability: no standalone indexnode</span></div>
  <pre><span class="kw">type</span> DataNodeClient <span class="kw">interface</span> {
    component
    datapb.DataNodeClient
    workerpb.IndexNodeClient   <span class="cm">// index-build worker folded into datanode</span>
}</pre>
</div>

<p>This "no indexnode" fact is the same evolutionary direction as Lesson 9's "MixCoord folds three coordinators into one process": <strong>merge once-separate roles to lower deployment and ops complexity</strong>. Early Milvus did have a standalone indexnode,
but as the architecture evolved, index building was folded into the datanode worker. If a doc you read still describes "indexnode as a standalone component," defer to the code — <strong>in the code DataNodeClient embeds IndexNodeClient, and that is today's reality</strong>.
DataCoord thus becomes the write side's genuine steward: segments, channels, flush, compaction, GC, index scheduling — every facet of writing data sits on its ledger.</p>

<p>Why is index building especially fit to fold into datanode rather than be its own node? Because index building is essentially a <strong>batch-style heavy compute task</strong>: read an already-flushed segment, run the ANN graph-building algorithm over it, write the result back to object storage.
It is highly homologous to what datanode already does — "read and write segment files" — sharing the same data-access capabilities and node resources. Folding it in saves deploying and monitoring a whole class of process, and lets index building reuse datanode's IO and cache nearby. This embodies a main thread of Milvus's recent architectural evolution:
<strong>merge where possible, carry more responsibility with fewer process types</strong>, making small-to-medium deployments lighter and ops easier — echoing Lesson 8's choice between Standalone and Cluster forms.</p>

<div class="flow">
  <div class="node"><div class="nt">Proxy write</div><div class="nd">insert via vchannel</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">DataCoord</div><div class="nd">segment·schedule·book</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">DataNode worker</div><div class="nd">flush·compact·index</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">object storage</div><div class="nd">binlog / index files</div></div>
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  DataCoord is the write side's master scheduler, at its core a <strong>segment state machine</strong>: Growing → Sealed → Flushing → Flushed (then Dropped). It allocates segments and records every transition, but flush, compaction, and index building are all executed by datanode workers — decision separated from execution.
  Flush safely solidifies data into immutable binlogs; compaction trades background tidying for foreground query lightness; GC conservatively hauls away unreferenced files; channel assignment lets writes scale out. Key fact: <strong>no standalone indexnode</strong> — the index-build worker is folded into datanode (DataNodeClient embeds IndexNodeClient).
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Segment allocation</strong>: DataCoord maintains each shard's current growing segment; seals it on full/timeout and opens a new one; it books all segment states.</li>
    <li><strong>State machine</strong>: <span class="mono">commonpb.SegmentState_*</span> runs Growing → Sealed → Flushing → Flushed → Dropped; note it lives in go-api's commonpb package, not datapb.</li>
    <li><strong>Flushed is immutable</strong>: flushed segments are read-only; deletes/updates append as new writes + delta — append only, never modify in place (Lesson 7).</li>
    <li><strong>Three background jobs</strong>: Flush to disk, Compaction merges small segments and applies deletes (deep dive Lesson 19), GC conservatively reclaims unreferenced files.</li>
    <li><strong>Channels and indexes</strong>: assign vchannels to nodes; schedule index builds. <strong>No standalone indexnode</strong> — the build worker is folded into datanode (DataNodeClient embeds IndexNodeClient).</li>
  </ul>
</div>
""",
}


LESSON_13 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
DataCoord 管"数据怎么写进去、怎么存好"，这一课的 <strong>QueryCoordV2（查询协调者）</strong>则管"数据怎么被搜出来"。它是读取侧的总调度：把要查的集合<strong>加载</strong>进 QueryNode 的内存，
把段和分片<strong>分配</strong>给各个节点，用<strong>均衡器</strong>让负载均匀，用<strong>副本</strong>换来高可用与高吞吐，还时刻盯着"<strong>当前分布</strong>"与"<strong>目标分布</strong>"的差距去校正。读懂它，你就握住了向量检索在分布式层面的全貌。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把 QueryCoordV2 想成一座<strong>大图书馆的阅览室调度主任</strong>。库房里（对象存储）躺着海量的书（段），但读者不能直接进库房翻——主任得先把要用的书<strong>搬上阅览室的书架（加载进 QueryNode 内存）</strong>，读者才能快速取阅。
  他要决定<strong>哪本书放哪个书架</strong>（段分配），让每个书架的书量均匀、别挤在一处（均衡）；热门的书还会<strong>多备几本副本</strong>分放不同书架，这样一个书架坏了别处还能借到（高可用），多人同时借也不必排队（高吞吐）。
  他手里始终攥着两张表：<strong>现在每个书架上实际有哪些书</strong>，和<strong>理想情况下应该有哪些书</strong>——他的工作，就是不断让前者向后者靠拢。
</div>

<h2>加载与释放：搜索的前提</h2>
<p>第一个要打破的直觉是：<strong>在 Milvus 里，数据"存着"不等于"能搜"</strong>。一个集合的段安安静静躺在对象存储里，本身是搜不了的；必须先经过 <strong>load（加载）</strong>——QueryCoord 把这个集合的段与索引调度进若干 QueryNode 的内存，
建立起可供检索的在线副本，集合才进入"可搜索"状态。反过来，<strong>release（释放）</strong>则把这些内存占用还回去，集合重新变为"只存不搜"。这就是为什么你在用 Milvus 时，建完集合、灌完数据，还要显式 <span class="mono">load_collection</span> 之后才能 search。</p>

<p>为什么要有这道"加载"的门槛，而不是让所有数据随时可搜？因为向量检索是<strong>内存密集</strong>的：ANN 索引要常驻内存才能快（第 5、6 课），而内存是昂贵且有限的资源。如果把所有集合无脑全部加载，内存很快就会被撑爆。
于是 Milvus 把"<strong>是否占用宝贵的查询内存</strong>"这个决定权，通过 load/release 交到用户手里——你想搜哪个集合，就把哪个加载进来；暂时不用了，就释放掉腾出空间。QueryCoord 正是这道闸门的看守者，它统一掌管"此刻哪些集合在线、各自加载在哪些节点上"。</p>

<p>这道闸门的存在，也让 Milvus 能优雅地支持"<strong>数据量远大于内存</strong>"的场景。你可以往一个集合里灌入远超单机内存的数据，安心地存在对象存储里；真正要查时，再按需把需要的集合（甚至按分区、按需局部）加载进来。
换句话说，<strong>存储容量由对象存储兜底、查询能力由内存决定</strong>，两者解耦。这正是第 7 课"存算分离"在读取侧的直接体现——你不必为了能查一点数据，就被迫把全部数据都常驻昂贵的内存里。</p>

<p>加载远不只是"把文件读进内存"这么简单，它是一连串协调动作的总和：要确定这个集合有哪些段、哪些分片；要为每个段、每条分片通道挑选承载的 QueryNode；要把它们的索引也一并就位；
还要在加载完成后，让 Proxy 能查到"这个集合现在加载在哪、分了几个副本、每个分片的 delegator 是谁"，这样查询才能被正确地扇出。这一整套，正是 QueryCoord 作为读取侧大脑要操心的事。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>用户请求加载</h4><p><span class="mono">load_collection</span> 经 Proxy 到达 QueryCoord。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>确定目标分布</h4><p>算出这个集合该有哪些段、哪些分片，要加载几个副本——形成"目标（target）"。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>分配段与分片</h4><p>把段、分片通道（delegator）分派给各个 QueryNode。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>节点加载</h4><p>QueryNode 从对象存储拉取段与索引，载入内存，建立在线副本。</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>校正到位</h4><p>观测"当前分布"逼近"目标分布"，全部就位后集合变为可搜索。</p></div></div>
</div>

<h2>段与分片的分配：谁来搜哪一块</h2>
<p>一个大集合往往有成百上千个段、若干个分片，而 QueryNode 有很多台——所以核心问题是：<strong>哪个段、哪条分片该交给哪台 QueryNode？</strong>QueryCoord 要做两类分配。一类是<strong>段分配</strong>：把历史的、已落盘的段（第 12 课的 Flushed 段）摊到各个节点的内存里，每个节点负责自己那一摊段的局部检索。
另一类是<strong>分片（通道）分配</strong>：每个分片对应一条 vchannel，由某台 QueryNode 上的 <strong>delegator（分片代理 / shard leader）</strong>负责。delegator 是这条分片的"门面"，它既要协调该分片下所有段的查询，又要承接该分片最新的、还没落盘的增量数据（growing 段）。</p>

<p>为什么要区分"段"与"分片/delegator"两层？因为一次查询要看到的，既有<strong>历史数据</strong>（已落盘的 sealed/flushed 段），也有<strong>最新数据</strong>（还在内存里流动的 growing 段）。delegator 正是把这两者缝合起来的关键角色：
它代表一条分片，把对历史段的查询<strong>扇出</strong>给持有这些段的 QueryNode，再把这条分片上最新的增量也一并查上，最后<strong>归并</strong>成这条分片的完整结果。于是 Proxy 只需把查询发给各分片的 delegator，就能拿到"历史 + 最新"都不漏的答案。这套机制的细节（跨分片归并）会在第 29 课深入，这里先抓住角色分工。</p>

<p>delegator 这个角色还解释了一个常见疑问：为什么 Milvus 能做到"刚写进去的数据立刻就能被搜到"（在合适的一致性级别下）？因为最新的 growing 增量本就由 delegator 直接持有并参与查询，不必等它落盘、不必等它被加载——
查询打到 delegator 时，它把"已落盘的历史段结果"和"手里最新的内存增量结果"现场合并，于是新旧数据一个都不漏。这正是写入侧（DataCoord 的段流转）与读取侧（QueryCoord 的 delegator）在同一条分片上<strong>无缝接力</strong>的体现：数据在写侧从 growing 一路走向 flushed，在读侧则由 delegator 始终盯着这条流，保证查询看到的永远是完整的当下。</p>

<div class="cols">
  <div class="col"><h4>段分配 segment</h4><p>把已落盘的<strong>历史段</strong>摊给各个 QueryNode，每台负责一部分段的局部 topK 检索。关注的是<strong>把存量数据均匀铺开</strong>，让检索算力水平扩展。</p></div>
  <div class="col"><h4>分片分配 delegator</h4><p>每条分片由一个 <strong>delegator</strong> 承载，缝合该分片的历史段查询与最新 growing 增量，并对外作为这条分片的查询门面。关注的是<strong>让每条数据流都有人负责到最新</strong>。</p></div>
</div>

<h2>均衡器：让负载不偏不倚</h2>
<p>分配不是一次性的。节点会上线下线、集合会增删、各节点的负载会逐渐倾斜——于是需要一个 <strong>均衡器（balancer）</strong>持续地把段和分片<strong>重新摊匀</strong>。它的目标朴素而重要：别让某台 QueryNode 又热又挤、另一台却闲着，
因为查询的整体延迟往往被<strong>最忙的那台</strong>拖累。当有新节点加入，均衡器要把一部分段迁过去让它分担；当某节点离开，它负责的段要被接管到别处；当负载长期不均，也要主动搬运校正。</p>

<p>Milvus 的均衡器有不止一种策略。最简单的是<strong>轮询（round-robin）</strong>：纯按数量把段均匀分，不管每个段实际多大、多热——实现简单，适合分布相对均匀的场景。更精细的是<strong>打分（score-based）</strong>策略：综合考虑节点的段数、行数、内存占用等"真实负载"来打分，
把段往负载更轻的节点放。两种策略对应不同取舍：轮询图省事、求均匀的数量，打分图精准、求均匀的真实压力。它们都实现了同一个 <span class="mono">Balance</span> 接口，由 QueryCoord 按需选用。</p>

<p>均衡这件事还有一个微妙的代价必须权衡：<strong>搬迁本身是有成本的</strong>。把一个段从 A 节点挪到 B 节点，意味着 B 要重新从对象存储拉取这个段、重新载入内存、重建必要的状态，期间还要小心别影响正在进行的查询。
所以均衡器不能见到一点点不均就疯狂搬运——那会让集群陷入"反复折腾、净收益为负"的抖动。好的均衡策略懂得<strong>设阈值、留余量、慢慢收敛</strong>：只有当不均衡程度超过某个门槛、且收益明显大于搬迁成本时才动手。这种"克制的勤奋"，正是分布式均衡设计里最考验功力的地方。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/querycoordv2/balance/balance.go</span><span class="ln">Balance 接口：产出段与通道的搬迁计划</span></div>
  <pre><span class="kw">type</span> Balance <span class="kw">interface</span> {
    <span class="cm">// 为一个副本均衡段与通道，返回"该怎么搬"的计划</span>
    BalanceReplica(ctx context.Context, replica *meta.Replica) (
        []assign.SegmentAssignPlan, []assign.ChannelAssignPlan)

    <span class="cm">// 取出底层的分配策略（轮询 / 打分）</span>
    GetAssignPolicy() assign.AssignPolicy
}

<span class="cm">// 轮询均衡器：纯按数量把段/通道均匀分到各节点</span>
<span class="kw">type</span> RoundRobinBalancer <span class="kw">struct</span> { <span class="cm">/* ... */</span> }</pre>
</div>

<h2>副本：用冗余换高可用与高吞吐</h2>
<p>加载一个集合时，你可以让它有<strong>多个副本（replica）</strong>——也就是把同一个集合的段，在<strong>不同的 QueryNode 上各加载一份</strong>。副本一举换来两样好东西。其一是<strong>高可用（HA）</strong>：某个副本所在的节点挂了，
另一个副本还在别处好端端地服务，查询不中断、数据不丢可用性。其二是<strong>高吞吐</strong>：多个副本可以<strong>并行分担</strong>查询流量，同样一个集合，两个副本理论上能扛近两倍的并发查询。冗余在这里不是浪费，而是<strong>稳与快</strong>的来源。</p>

<p>当然副本不是免费的：N 个副本就要 N 倍的查询内存。所以副本数是用户根据"这个集合多重要、查询量多大"来权衡的旋钮——核心业务、超高并发的集合多开几个副本，冷僻的集合一个就够。QueryCoord 的 <span class="mono">ReplicaManager</span> 统一管理这些副本：每个副本里有哪些节点、各自承载哪些段，都记在它这本账上。
这呼应了第 9 课"协调者持有真相、节点执行"的分工——副本怎么排布是 QueryCoord 决定并记账的，QueryNode 只管把分到自己头上的段加载好、查好。</p>

<p>这里还藏着一个常被忽略的细节：副本之间并不是简单的"完全镜像"，而是各自独立地承载该集合的全部数据、独立地做均衡。这样设计的好处是，<strong>一个副本内部的搬迁、扩缩，不会牵连另一个副本</strong>，故障与负载彼此隔离。
当一次查询打进来，Proxy 会从可用的副本里挑一个去执行（通常按负载或就近原则），于是流量天然地被分摊到各副本上。可以说，副本既是"<strong>纵向的安全垫</strong>"（挂了有备份），也是"<strong>横向的扩音器</strong>"（并发被放大）——这正是为什么我们把它列为读取侧最重要的可用性与扩展手段。</p>

<h2>分布 vs 目标：永不停歇的校正</h2>
<p>在深入这套校正机制前，先把这一课出现的几个核心概念列成一张表，理清各自的角色——它们正是 QueryCoordV2 这本"账"里最重要的几栏：</p>

<table class="t">
  <tr><th>概念</th><th>是什么</th><th>角色</th></tr>
  <tr><td><strong>distribution 分布</strong></td><td>当前实际加载现状</td><td>记录"哪个段此刻真的在哪台节点"</td></tr>
  <tr><td><strong>target 目标</strong></td><td>期望的理想布局</td><td>声明"应该加载成什么样"，供校正参照</td></tr>
  <tr><td><strong>replica 副本</strong></td><td>集合的一份在线拷贝</td><td>换取高可用与高吞吐，N 份即 N 倍内存</td></tr>
  <tr><td><strong>delegator 分片代理</strong></td><td>一条分片的查询门面</td><td>缝合历史段与最新 growing 增量</td></tr>
  <tr><td><strong>balancer 均衡器</strong></td><td>负载再平衡器</td><td>持续把段/分片摊匀，避免热点</td></tr>
</table>

<p>QueryCoordV2 这个"V2"架构里最精髓的设计，是它把状态拆成了<strong>两张视图</strong>来管理。一张叫<strong>分布（distribution）</strong>：现在<strong>实际</strong>是什么样——哪个段此刻真的加载在哪台节点、哪条分片的 delegator 现在在哪。
另一张叫<strong>目标（target）</strong>：理想中<strong>应该</strong>是什么样——根据集合的加载请求、副本数、均衡策略算出来的期望布局。两者之间几乎总有差距：节点刚挂、段刚迁、加载刚发起……现实永远在追赶理想。</p>

<p>QueryCoord 的核心循环，就是一群<strong>观测者（observer）</strong>不断比对这两张表，发现差距就生成动作去抹平它：目标里该有但分布里还没有的段，就调度加载；分布里多出来、目标里已不需要的，就释放；该搬的搬、该补的补。
这种"<strong>声明目标 → 持续校正现状向目标收敛</strong>"的设计，正是现代分布式系统（如 Kubernetes 的 reconcile）公认的健壮范式：你不去写一长串"先做这步再做那步"的脆弱流程，而是只声明"我想要的终态"，让系统自己一轮一轮地逼近。
目标本身还分<strong>当前目标（current target）</strong>与<strong>下一目标（next target）</strong>，用来平滑地从旧布局过渡到新布局而不打断正在进行的查询。理解了这套"分布逼近目标"的循环，你就抓住了 QueryCoordV2 区别于老架构的灵魂。</p>

<p>为什么要分"当前"与"下一"两个目标？想象一次大规模的重新加载或均衡：如果直接把目标一步换成全新布局，正在用旧布局执行的查询就可能突然找不到段。两段式目标让系统能<strong>先准备好下一目标、待新布局就绪后再平滑切换</strong>，
让旧查询走完、新查询走新布局，整个过程对用户无感。这种"<strong>双缓冲式</strong>"的切换，把"既要变、又不能停"这对矛盾化解得干净利落。至此，从 load 到分配、到均衡、到副本、再到这套分布逼近目标的循环，QueryCoordV2 作为读取侧大脑的全貌就清晰了——
它和上一课的 DataCoord 一写一读，共同撑起了 Milvus 在分布式层面"既能稳稳存好、又能快快搜出"的两端。</p>

<div class="flow">
  <div class="node"><div class="nt">用户 load</div><div class="nd">声明要搜的集合</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">QueryCoord</div><div class="nd">算目标·分配·均衡</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">QueryNode</div><div class="nd">加载段·当 delegator</div></div>
  <div class="arrow">↺</div>
  <div class="node"><div class="nt">observer</div><div class="nd">分布逼近目标</div></div>
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  QueryCoordV2 是读取侧的总调度。它的世界从 <strong>load</strong> 开始：存着不等于能搜，必须把集合的段与索引加载进 QueryNode 内存才可检索。它做两类分配——把历史段摊给各节点、把每条分片交给一个 delegator（缝合历史段与最新 growing 增量）；
  用均衡器（轮询 / 打分两种策略，同一 <span class="mono">Balance</span> 接口）持续把负载摊匀；用副本换取高可用与高吞吐。最精髓的是"<strong>分布 vs 目标</strong>"：观测者不断让"实际加载现状"向"期望布局"收敛——声明终态、持续校正，正是它健壮的根源。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>load / release</strong>：存着 ≠ 能搜；必须把集合段与索引加载进 QueryNode 内存才可检索，释放则还回内存。</li>
    <li><strong>两类分配</strong>：段分配（把历史段摊给各节点）+ 分片分配（每条分片一个 <strong>delegator</strong>，缝合历史段与最新 growing 增量）。</li>
    <li><strong>均衡器</strong>：持续把段/分片摊匀，避免热点；有轮询与打分两种策略，同实现 <span class="mono">Balance</span> 接口。</li>
    <li><strong>副本</strong>：同集合在不同节点各加载一份，换来高可用（节点挂了还有副本）与高吞吐（并行分担查询），代价是 N 倍内存。</li>
    <li><strong>分布 vs 目标</strong>：distribution=实际现状、target=期望布局；observer 持续校正使现状逼近目标（含 current/next target 平滑过渡）。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
DataCoord governs "how data is written in and stored well"; this lesson's <strong>QueryCoordV2 (the query coordinator)</strong> governs "how data is searched out." It is the read side's master scheduler: it <strong>loads</strong> the collections to be queried into QueryNode memory,
<strong>assigns</strong> segments and shards to nodes, uses a <strong>balancer</strong> to even out load, uses <strong>replicas</strong> to buy high availability and throughput, and constantly watches the gap between the "<strong>current distribution</strong>" and the "<strong>target distribution</strong>" to correct it. Understand it and you grasp vector retrieval's whole picture at the distributed layer.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of QueryCoordV2 as the <strong>reading-room dispatch director of a great library</strong>. In the stacks (object storage) lie vast numbers of books (segments), but readers can't rummage there directly — the director must first move the needed books <strong>onto the reading-room shelves (load into QueryNode memory)</strong> before readers can fetch them fast.
  He decides <strong>which book goes on which shelf</strong> (segment assignment), keeping each shelf's book count even and not crammed in one spot (balancing); popular books get <strong>several copies</strong> on different shelves, so if one shelf breaks you can still borrow elsewhere (high availability), and many readers borrowing at once needn't queue (high throughput).
  He always holds two lists: <strong>which books each shelf actually has now</strong>, and <strong>which books it ideally should have</strong> — his job is to keep nudging the former toward the latter.
</div>

<h2>Load and release: the prerequisite for search</h2>
<p>The first intuition to break: <strong>in Milvus, data being "stored" doesn't mean it's "searchable."</strong> A collection's segments lying quietly in object storage can't be searched as-is; they must first go through <strong>load</strong> — QueryCoord schedules that collection's segments and indexes into several QueryNodes' memory,
building online copies available for retrieval, and only then does the collection enter the "searchable" state. Conversely, <strong>release</strong> returns that memory, turning the collection back to "stored but not searched." That's why, using Milvus, after creating a collection and ingesting data, you must still explicitly <span class="mono">load_collection</span> before you can search.</p>

<p>Why this "load" threshold rather than making all data searchable anytime? Because vector retrieval is <strong>memory-intensive</strong>: ANN indexes must reside in memory to be fast (Lessons 5 & 6), and memory is an expensive, limited resource. Loading every collection blindly would soon blow memory.
So Milvus hands the decision of "<strong>whether to occupy precious query memory</strong>" to the user via load/release — load the collection you want to search; release it to free space when idle. QueryCoord is the keeper of this gate, uniformly governing "which collections are online right now, and on which nodes each is loaded."</p>

<p>This gate also lets Milvus gracefully support the "<strong>data far larger than memory</strong>" scenario. You can ingest into a collection far more data than a single machine's memory, resting safely in object storage; only when you actually query do you load the needed collection (even partially, by partition, on demand) into memory.
In other words, <strong>storage capacity is backstopped by object storage while query capability is determined by memory</strong> — the two decoupled. This is Lesson 7's "storage-compute separation" made concrete on the read side — you needn't keep all data resident in expensive memory just to query a little of it.</p>

<p>Loading is far more than "reading files into memory"; it is the sum of a chain of coordination acts: determine which segments and shards this collection has; pick a hosting QueryNode for each segment and each shard channel; bring their indexes into place too;
and after loading completes, let the Proxy discover "where this collection is now loaded, how many replicas, who is each shard's delegator," so queries can be fanned out correctly. This whole set is what QueryCoord, as the read side's brain, must tend.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>User requests load</h4><p><span class="mono">load_collection</span> reaches QueryCoord via the Proxy.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Determine the target</h4><p>compute which segments and shards this collection should have, and how many replicas — forming the "target."</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Assign segments and shards</h4><p>dispatch segments and shard channels (delegators) to QueryNodes.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Nodes load</h4><p>QueryNodes pull segments and indexes from object storage into memory, building online copies.</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>Correct into place</h4><p>observe the "current distribution" approaching the "target"; once all in place the collection becomes searchable.</p></div></div>
</div>

<h2>Segment and shard assignment: who searches which piece</h2>
<p>A big collection often has hundreds or thousands of segments and several shards, while there are many QueryNodes — so the core question is: <strong>which segment, which shard goes to which QueryNode?</strong> QueryCoord does two kinds of assignment. One is <strong>segment assignment</strong>: spreading historical, flushed segments (Lesson 12's Flushed segments) across nodes' memory, each node handling local retrieval over its share.
The other is <strong>shard (channel) assignment</strong>: each shard maps to a vchannel, hosted by a <strong>delegator (shard proxy / shard leader)</strong> on some QueryNode. The delegator is that shard's "face": it both coordinates queries over all segments under the shard and takes on the shard's latest, not-yet-flushed incremental data (growing segments).</p>

<p>Why distinguish the "segment" and "shard/delegator" layers? Because one query must see both <strong>historical data</strong> (flushed/sealed segments) and the <strong>latest data</strong> (growing segments still flowing in memory). The delegator is the key role stitching the two together:
representing one shard, it <strong>fans out</strong> queries over historical segments to the QueryNodes holding them, also queries the shard's latest increments, and finally <strong>reduces</strong> them into that shard's complete result. So the Proxy need only send queries to each shard's delegator to get an answer that misses neither "history nor latest." The details of this mechanism (cross-shard reduce) go deep in Lesson 29; here just grasp the role division.</p>

<p>The delegator role also explains a common question: why can Milvus make "data just written immediately searchable" (under a suitable consistency level)? Because the latest growing increments are held directly by the delegator and participate in queries — no need to wait for flush, no need to wait to be loaded —
when a query reaches the delegator, it merges on the spot the "results from flushed historical segments" with the "latest in-memory increment results it holds," so neither old nor new data is missed. This is exactly the <strong>seamless relay</strong> between the write side (DataCoord's segment transitions) and the read side (QueryCoord's delegator) on the same shard: on the write side data travels from growing to flushed, while on the read side the delegator always watches this stream, ensuring queries always see a complete present.</p>

<div class="cols">
  <div class="col"><h4>Segment assignment</h4><p>Spread flushed <strong>historical segments</strong> across QueryNodes, each doing local topK over part of the segments. The focus: <strong>spread the existing data evenly</strong> so retrieval compute scales out.</p></div>
  <div class="col"><h4>Delegator assignment</h4><p>Each shard is hosted by a <strong>delegator</strong> that stitches the shard's historical-segment queries with its latest growing increments, serving as the shard's query face. The focus: <strong>ensure every data stream is covered up to the latest</strong>.</p></div>
</div>

<h2>The balancer: keeping load impartial</h2>
<p>Assignment isn't one-off. Nodes come and go, collections are added and dropped, each node's load gradually skews — so a <strong>balancer</strong> is needed to continually <strong>re-spread</strong> segments and shards. Its goal is plain yet important: don't let one QueryNode be hot and crammed while another sits idle,
because overall query latency is often dragged down by <strong>the busiest one</strong>. When a new node joins, the balancer must migrate some segments over to share load; when a node leaves, its segments must be taken over elsewhere; when load stays uneven, it must proactively move things to correct it.</p>

<p>Milvus's balancer has more than one strategy. The simplest is <strong>round-robin</strong>: spread segments evenly purely by count, regardless of each segment's actual size or heat — simple to implement, fit for relatively uniform distributions. The finer one is the <strong>score-based</strong> strategy: scoring by a node's "real load" — segment count, row count, memory usage — and placing segments on lighter-loaded nodes.
The two embody different trade-offs: round-robin for simplicity and even counts, score-based for precision and even real pressure. Both implement the same <span class="mono">Balance</span> interface, chosen by QueryCoord as needed.</p>

<p>Balancing also carries a subtle cost to weigh: <strong>migration itself isn't free</strong>. Moving a segment from node A to node B means B must re-pull the segment from object storage, reload it into memory, and rebuild necessary state, all while being careful not to disturb in-flight queries.
So the balancer can't frantically shuffle at the slightest imbalance — that would throw the cluster into "constant churn with negative net gain" thrash. A good balancing strategy knows to <strong>set thresholds, leave margins, and converge slowly</strong>: it acts only when the imbalance exceeds some bar and the gain clearly outweighs the migration cost. This "restrained diligence" is exactly where distributed balancing design most tests one's skill.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/querycoordv2/balance/balance.go</span><span class="ln">The Balance interface: produce segment and channel move plans</span></div>
  <pre><span class="kw">type</span> Balance <span class="kw">interface</span> {
    <span class="cm">// balance segments and channels for a replica; return "how to move" plans</span>
    BalanceReplica(ctx context.Context, replica *meta.Replica) (
        []assign.SegmentAssignPlan, []assign.ChannelAssignPlan)

    <span class="cm">// fetch the underlying assign policy (round-robin / score-based)</span>
    GetAssignPolicy() assign.AssignPolicy
}

<span class="cm">// Round-robin balancer: spread segments/channels evenly by count</span>
<span class="kw">type</span> RoundRobinBalancer <span class="kw">struct</span> { <span class="cm">/* ... */</span> }</pre>
</div>

<h2>Replicas: trading redundancy for HA and throughput</h2>
<p>When loading a collection, you can give it <strong>multiple replicas</strong> — that is, load the same collection's segments <strong>once each on different QueryNodes</strong>. Replicas buy two good things at once. First, <strong>high availability (HA)</strong>: if a node holding one replica dies,
another replica is still serving fine elsewhere, queries uninterrupted, availability preserved. Second, <strong>high throughput</strong>: multiple replicas can <strong>share query traffic in parallel</strong>; for the same collection, two replicas can in theory handle nearly twice the concurrent queries. Redundancy here is no waste but the source of <strong>steadiness and speed</strong>.</p>

<p>Of course replicas aren't free: N replicas cost N times the query memory. So replica count is a knob the user weighs by "how important this collection is, how heavy its query load" — core, ultra-concurrent collections get more replicas, obscure ones need just one. QueryCoord's <span class="mono">ReplicaManager</span> uniformly manages these replicas: which nodes are in each replica and which segments each carries are all kept on its ledger.
This echoes Lesson 9's "coordinators hold the truth, nodes execute" division — how replicas are laid out is decided and booked by QueryCoord, while QueryNodes just load and search the segments assigned to them.</p>

<p>A commonly overlooked detail hides here: replicas are not simple "exact mirrors"; each independently carries the collection's full data and independently balances. The benefit: <strong>migration and scaling within one replica don't entangle another replica</strong> — faults and load are isolated from each other.
When a query arrives, the Proxy picks one available replica to execute on (usually by load or proximity), so traffic is naturally spread across replicas. You could say a replica is both a "<strong>vertical safety cushion</strong>" (a backup if one dies) and a "<strong>horizontal amplifier</strong>" (concurrency magnified) — which is why we rank it the read side's most important availability and scaling lever.</p>

<h2>Distribution vs target: the ever-running correction</h2>
<p>Before diving into this correction mechanism, let's tabulate the core concepts of this lesson to clarify each one's role — they are the most important columns in QueryCoordV2's "ledger":</p>

<table class="t">
  <tr><th>Concept</th><th>What it is</th><th>Role</th></tr>
  <tr><td><strong>distribution</strong></td><td>the current actual loaded state</td><td>records "which segment is really on which node right now"</td></tr>
  <tr><td><strong>target</strong></td><td>the desired ideal layout</td><td>declares "what it should be loaded as," the reference for correction</td></tr>
  <tr><td><strong>replica</strong></td><td>an online copy of a collection</td><td>buys HA and throughput; N copies = N× memory</td></tr>
  <tr><td><strong>delegator</strong></td><td>a shard's query face</td><td>stitches historical segments with the latest growing increments</td></tr>
  <tr><td><strong>balancer</strong></td><td>the load re-balancer</td><td>continually spreads segments/shards evenly, avoiding hotspots</td></tr>
</table>

<p>The most essential design in this "V2" architecture is that it splits state into <strong>two views</strong>. One is the <strong>distribution</strong>: what it <strong>actually</strong> looks like now — which segment is really loaded on which node at this moment, where each shard's delegator currently is.
The other is the <strong>target</strong>: what it <strong>ought</strong> to look like — the desired layout computed from the collection's load request, replica count, and balancing strategy. There is almost always a gap between them: a node just died, a segment just migrated, a load just started... reality forever chasing the ideal.</p>

<p>QueryCoord's core loop is a swarm of <strong>observers</strong> constantly comparing these two and, on finding a gap, generating actions to close it: a segment the target wants but the distribution lacks gets scheduled to load; one the distribution has but the target no longer needs gets released; move what should move, fill what should fill.
This "<strong>declare the target → continually correct the actual toward it</strong>" design is exactly the robust paradigm modern distributed systems (like Kubernetes' reconcile) acknowledge: instead of writing a long, brittle "do this step then that step" procedure, you only declare "the end state I want" and let the system converge round by round.
The target itself further splits into <strong>current target</strong> and <strong>next target</strong>, to transition smoothly from old layout to new without interrupting in-flight queries. Grasp this "distribution approaching target" loop and you hold the soul that distinguishes QueryCoordV2 from the old architecture.</p>

<p>Why split "current" and "next" targets? Imagine a large-scale reload or rebalance: swapping the target to a brand-new layout in one step could leave queries running on the old layout suddenly unable to find segments. The two-stage target lets the system <strong>prepare the next target first, then switch smoothly once the new layout is ready</strong>,
letting old queries finish and new queries use the new layout, the whole process invisible to users. This "<strong>double-buffered</strong>" switch resolves the tension of "must change, yet must not stop" cleanly. With that, from load to assignment, to balancing, to replicas, and on to this distribution-approaching-target loop, QueryCoordV2's whole picture as the read side's brain is clear —
it and last lesson's DataCoord, one writing and one reading, together hold up Milvus's two ends at the distributed layer: "store soundly, search swiftly."</p>

<div class="flow">
  <div class="node"><div class="nt">user load</div><div class="nd">declare the collection to search</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">QueryCoord</div><div class="nd">target·assign·balance</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">QueryNode</div><div class="nd">load segments·be delegator</div></div>
  <div class="arrow">↺</div>
  <div class="node"><div class="nt">observer</div><div class="nd">distribution → target</div></div>
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  QueryCoordV2 is the read side's master scheduler. Its world starts at <strong>load</strong>: stored doesn't mean searchable — a collection's segments and indexes must be loaded into QueryNode memory to be retrievable. It does two kinds of assignment — spread historical segments across nodes, and give each shard a delegator (stitching historical segments with the latest growing increments);
  it uses a balancer (round-robin / score-based, one <span class="mono">Balance</span> interface) to keep load even; it uses replicas to buy HA and throughput. Most essential is "<strong>distribution vs target</strong>": observers keep converging "actual loaded state" toward "desired layout" — declare the end state, continually correct — the root of its robustness.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>load / release</strong>: stored ≠ searchable; a collection's segments and indexes must be loaded into QueryNode memory to be retrievable; release returns the memory.</li>
    <li><strong>Two assignments</strong>: segment assignment (spread historical segments across nodes) + shard assignment (each shard gets a <strong>delegator</strong> stitching historical segments with the latest growing increments).</li>
    <li><strong>Balancer</strong>: continually re-spreads segments/shards to avoid hotspots; has round-robin and score-based strategies, both implementing the <span class="mono">Balance</span> interface.</li>
    <li><strong>Replicas</strong>: the same collection loaded once each on different nodes, buying HA (a replica survives a node death) and throughput (parallel query sharing), at the cost of N× memory.</li>
    <li><strong>Distribution vs target</strong>: distribution = actual current state, target = desired layout; observers continually correct the actual toward the target (with current/next target for smooth transition).</li>
  </ul>
</div>
""",
}


LESSON_14 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前面五课分别认识了控制面/数据面，以及 Proxy、RootCoord、DataCoord、QueryCoordV2 四个角色。但它们各自心里那张"全局地图"——集合的 schema、段分到哪、谁加载了什么、哪台节点还活着——<strong>到底存在哪、又怎么互相同步</strong>？
这一课讲的就是把整套架构<strong>粘起来的胶水</strong>：<strong>etcd</strong> 作元数据存储、<strong>session</strong> 做服务发现、<strong>metastore/Catalog</strong> 抽象元数据读写、<strong>kv</strong> 层提供存取原语、<strong>watch</strong> 让协调者派活、节点接活。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把元数据系统想成一栋大楼的<strong>物业前台 + 档案室</strong>。<strong>etcd 是前台</strong>：每位住户（组件）一搬进来就在登记簿上写下"我是谁、住哪间、还在不在"，并领一张<strong>会定期续期的门禁卡（租约）</strong>——卡一旦忘了续，前台就知道这人搬走了。
  <strong>档案室（对象存储）</strong>放的是真正笨重的大件——家具、设备（数据与索引文件）；前台只在登记簿里记一句"3 号库房第 7 排放着谁家的钢琴"，绝不会把钢琴搬到前台。
  而<strong>Catalog 就是档案管理员</strong>：楼里所有人要存取档案，都得走他这道标准窗口，而不是自己翻库房。
</div>

<h2>一张总图：元数据从协调者落到 etcd</h2>
<p>先把这一课要讲的东西摆成一摞，你就不会迷路。最上面是<strong>协调者</strong>——RootCoord/DataCoord/QueryCoord，它们是元数据的<strong>生产者与消费者</strong>：建表要写 schema、分段要记 segment、加载要存 replica。
它们不直接拼 etcd 的 key，而是调用下一层 <strong>metastore 的 Catalog 接口</strong>，用 <span class="mono">CreateCollection</span>、<span class="mono">AddSegment</span>、<span class="mono">SaveReplica</span> 这样的"业务动词"读写元数据。
Catalog 再往下，落到 <strong>kv 层</strong>——把"一个 Collection 对象"序列化成"一串 key/value"，调用 <span class="mono">Save</span>/<span class="mono">MultiSave</span>/<span class="mono">LoadWithPrefix</span> 这样的原语。最底层，kv 才真正把字节写进 <strong>etcd</strong>（小而关键的元数据）或把大块数据交给<strong>对象存储</strong>。</p>

<div class="layers">
  <div class="layer l-core"><div class="lh"><span class="badge">生产/消费</span><span class="name">Coordinators</span></div>
    <div class="ld">RootCoord/DataCoord/QueryCoord 在做决策时读写元数据：schema、段、索引、副本、加载状态。它们只认"业务动词"，不碰存储细节。</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">抽象接口</span><span class="name">metastore · Catalog</span></div>
    <div class="ld"><span class="mono">RootCoordCatalog / DataCoordCatalog / QueryCoordCatalog</span>：把"持久化集合/段/副本元数据"抽象成接口，屏蔽底层是 etcd 还是别的后端。</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">存取原语</span><span class="name">kv 层</span></div>
    <div class="ld"><span class="mono">BaseKV / TxnKV / MetaKv / WatchKV</span>（<span class="mono">pkg/kv/kv.go</span>）：Save/Load/Remove、事务、带租约、可 Watch。实现见 <span class="mono">internal/kv/etcd</span>。</div></div>
  <div class="layer l-app"><div class="lh"><span class="badge">真正落地</span><span class="name">etcd · 对象存储</span></div>
    <div class="ld">小而关键的元数据进 etcd（强一致、可 watch）；笨重的向量/索引文件进对象存储，元数据里只留一个引用路径。</div></div>
</div>

<p>这张图的精髓是一句话：<strong>协调者说"业务语言"，Catalog 翻译成"键值语言"，kv 把它写进 etcd</strong>。每往下一层，抽象就更通用、更不关心业务含义。
正因为有 Catalog 这道翻译，上层 RootCoord 完全不必知道"一个 collection 在 etcd 里被拆成了多少个 key"；而下层换存储后端（比如 etcd 换成 TiKV）时，上层也一行都不用改。这就是<strong>分层解耦</strong>在元数据系统里的体现。</p>

<p>不妨拿"建一个集合"走一遍全程，感受这条流水线。客户端发来 CreateCollection，Proxy 把它转给 RootCoord；RootCoord 先向自己要一个全局时间戳与若干 ID（第 11 课讲过），把 schema 组装成一个 <span class="mono">model.Collection</span> 领域对象，然后调用 <span class="mono">RootCoordCatalog.CreateCollection(ctx, coll, ts)</span>。
到了 Catalog，这个对象被<strong>拆解</strong>：集合本身一条 key、每个字段一条 key、每个分区一条 key……再调用 <span class="mono">kv.MultiSave</span> 把这一批 key/value <strong>一次性事务写入</strong> etcd。整条链上，RootCoord 只说了一句"建表"，真正"拆成多少个 key、怎么保证原子性"全被下面两层悄悄消化掉了。这正是好抽象的标志：<strong>上层的意图简单，下层的复杂被封装</strong>。</p>

<h2>etcd 与会话：组件如何互相发现</h2>
<p>元数据要"存得住"，组件还要"找得到"彼此。第 9 课提过：每个组件启动时调用 <span class="mono">Register()</span>，在 etcd 里写下一条<strong>带租约（lease）</strong>的 session——"我是 querynode-3，gRPC 地址在这里，我还活着"。
这套实现在 <span class="inline">internal/util/sessionutil/session_util.go</span> 里：<span class="mono">Session</span> 结构体持有一个 <span class="mono">LeaseID</span>，后台 goroutine 不停地 <strong>keepalive 续约</strong>；一旦进程崩溃、心跳停止，租约到期，etcd 自动删掉这条 session 记录。</p>

<p>另一端，协调者调用 <span class="mono">WatchServices</span> 去<strong>监听</strong>这些 session 的前缀目录：有节点上线，立刻收到"新增"事件；有节点掉线（租约过期），收到"删除"事件。
于是控制面始终握着一份<strong>当前活着的节点清单</strong>，据此分配段、做均衡、在故障时把工作转交别人。这套"<strong>注册 → 续约 → 监听</strong>"就是 Milvus 的服务发现——它和元数据共用同一个 etcd，但承载的是"谁在、在哪"的<strong>瞬时状态</strong>，而非"集合长什么样"的<strong>持久元数据</strong>。</p>

<p>这里要再强调第 9 课那条红线：<strong>session 里存的是"地址"，不是"数据"</strong>。etcd 在这条链路上是"通讯录 + 心跳板"，它告诉你"谁在、在哪"，但真正的 search/insert 流量绝不经过 etcd——那会瞬间把它打爆。组件拿到对方地址后，是<strong>点对点直连 gRPC</strong> 发请求的。控制信息走 etcd、数据流量走直连，这条分界贯穿整个 Milvus。</p>

<p>为什么非要用"租约 + 续约"，而不是简单地写一个 <span class="mono">alive=true</span> 的标记？因为分布式系统里最难处理的不是"优雅退出"，而是"<strong>突然失联</strong>"——进程被 kill -9、机器断电、网线被拔。这些情况下没人有机会去把标记改成 false。
租约的精妙正在于它<strong>把"活着"变成一件需要持续付出才能维持的事</strong>：只要心跳一停，etcd 自己就会在租约到期时清掉记录，无需任何人善后。这是一种"<strong>故障即默认</strong>"的设计——系统假设节点随时可能消失，活着才是需要不断证明的例外。理解了这一点，你就理解了几乎所有分布式心跳机制背后的同一套哲学。</p>

<p>还有个实用细节值得一提：所有这些 key（元数据也好、session 也好）都挂在一个统一的 <strong>metaRoot 前缀</strong>下（由配置决定，如 <span class="mono">by-dev/meta</span>）。这样同一套 etcd 集群就能<strong>隔离多个 Milvus 实例</strong>——各用各的前缀，互不串扰。这也是为什么源码里到处是 <span class="mono">LoadWithPrefix</span>、<span class="mono">WatchWithPrefix</span>：在 etcd 这种扁平 key/value 空间里，<strong>前缀就是命名空间</strong>，是 Milvus 组织整张元数据图的基本手法。</p>

<h2>metastore 与 Catalog：元数据的"档案接口"</h2>
<p>现在看核心抽象。<span class="inline">internal/metastore/catalog.go</span> 里定义了几个<strong>按协调者切分</strong>的接口：<span class="mono">RootCoordCatalog</span> 管库/表/分区/别名/凭证/角色；
<span class="mono">DataCoordCatalog</span> 管段（<span class="mono">ListSegments</span>/<span class="mono">AddSegment</span>/<span class="mono">DropSegment</span>）、channel、索引；<span class="mono">QueryCoordCatalog</span> 管加载信息（<span class="mono">SaveCollection</span>/<span class="mono">SaveReplica</span>/<span class="mono">SaveCollectionTargets</span>）。
每个方法都是一个<strong>业务动词</strong>，参数是 <span class="mono">model.Collection</span>、<span class="mono">datapb.SegmentInfo</span>、<span class="mono">querypb.Replica</span> 这样的领域对象，而不是裸的字节。</p>

<p>留意这份对称：三个 Catalog 接口恰好对应第 11–13 课的三个协调者。RootCoord 管"有什么"（schema/DDL），DataCoord 管"数据在哪"（段/channel），QueryCoord 管"加载了什么"（副本/target）。
每个协调者只通过自己那个 Catalog 持久化属于自己的那片世界，三片几乎不重叠。正是这种<strong>干净的分区</strong>，让三个角色能被各自独立推理、也能被打包进同一个 MixCoord 进程而元数据互不踩踏。<strong>Catalog 的三分，正是你早已学过的职责三分在存储层的镜像</strong>。</p>

<p>注意 RootCoordCatalog 的很多方法都带一个 <span class="mono">ts typeutil.Timestamp</span> 参数——这是因为 RootCoord 的元数据是<strong>多版本</strong>的：DDL 操作都挂在一个时间戳上，于是"在某个时间点看到的 schema"可以被精确复现。
历史上这靠一层"快照 KV（snapshot kv）"实现——把同一个 key 的不同版本按时间戳存成多条记录，读时取"不晚于某时刻"的最新版。它让一致性级别、时间旅行式读取成为可能。今天 Catalog 的具体实现（<span class="mono">internal/metastore/kv/rootcoord</span>）持有一个 <span class="mono">kv.TxnKV</span>，把领域对象拆成 key/value 落进去。</p>

<p>把元数据读写收口到 Catalog 接口，还有一个工程上的大好处：<strong>可测试</strong>。测 RootCoord 的建表逻辑时，你不必真的拉起一个 etcd——给它一个 mock 的 Catalog，或一个内存版 kv（<span class="mono">internal/kv/mem</span>）就行，测试又快又稳。
这和第 9 课"用接口当可插拔接缝"是同一招：<strong>凡是会触达外部世界（存储、网络）的地方，都用接口隔一道</strong>，于是既能在生产里接真实 etcd，又能在测试里接假实现。你在 Milvus 源码里看到大量 <span class="mono">mock_*.go</span>，很多就是为这些 Catalog/kv 接口自动生成的。<strong>抽象不只是为了优雅，更是为了能被独立验证</strong>。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/metastore/catalog.go</span><span class="ln">Catalog 接口（节选）</span></div>
  <pre><span class="cm">// RootCoord 的元数据：库/表/分区，方法带 ts（多版本）</span>
<span class="kw">type</span> RootCoordCatalog <span class="kw">interface</span> {
    CreateCollection(ctx, coll *model.Collection, ts Timestamp) <span class="kw">error</span>
    GetCollectionByID(ctx, dbID, ts Timestamp, id UniqueID) (*model.Collection, <span class="kw">error</span>)
    DropCollection(ctx, coll *model.Collection, ts Timestamp) <span class="kw">error</span>
    <span class="cm">// ... 分区、别名、凭证、角色 ...</span>
}

<span class="cm">// DataCoord 的元数据：段与 channel</span>
<span class="kw">type</span> DataCoordCatalog <span class="kw">interface</span> {
    ListSegments(ctx, collectionID <span class="kw">int64</span>) ([]*datapb.SegmentInfo, <span class="kw">error</span>)
    AddSegment(ctx, segment *datapb.SegmentInfo) <span class="kw">error</span>
    DropSegment(ctx, segment *datapb.SegmentInfo) <span class="kw">error</span>
}</pre>
</div>

<h2>kv 层：Catalog 脚下的存取原语</h2>
<p>Catalog 再往下踩的是 <span class="inline">pkg/kv/kv.go</span> 里一组<strong>逐层叠加</strong>的接口。最底是 <span class="mono">BaseKV</span>：<span class="mono">Save/Load/Remove/MultiSave/LoadWithPrefix</span> 这些最朴素的增删查。
往上 <span class="mono">TxnKV</span> 加了<strong>事务</strong>（<span class="mono">MultiSaveAndRemove</span>——多个写和删要么全成、要么全败，这对"改 schema 同时删旧 key"至关重要）。
再上 <span class="mono">MetaKv</span> 加了<strong>带租约</strong>与 <span class="mono">CompareVersionAndSwap</span>（乐观锁）。最上 <span class="mono">WatchKV</span> 加了 <span class="mono">Watch</span>——这正是服务发现与"派活"机制的底座。</p>

<p>这种"接口套接口"的叠加，和第 9 课的 <span class="mono">Component</span> 是同一种工程审美：<strong>需要多少能力，就依赖到哪一层</strong>。一个只读配置的模块依赖 <span class="mono">BaseKV</span> 就够；
要做事务的 Catalog 依赖 <span class="mono">TxnKV</span>；要监听变化的服务发现依赖 <span class="mono">WatchKV</span>。实现都在 <span class="mono">internal/kv/etcd</span>（etcd 版）与 <span class="mono">internal/kv/mem</span>（内存版，测试用）。
下面这段就是从 <span class="mono">BaseKV</span> 一路叠到 <span class="mono">WatchKV</span> 的契约：</p>

<p>这里 <span class="mono">MetaKv</span> 上那个 <span class="mono">CompareVersionAndSwap</span>（比较版本再交换，即 CAS）值得单独点一下：它是<strong>乐观锁</strong>的基础。设想两个协调者副本同时想改同一份元数据，如果各写各的，后写的会悄悄覆盖先写的，造成丢更新。
CAS 的做法是"<strong>带着我看到的版本号去写</strong>"——只有当 etcd 里的版本仍和我读到的一致时，写才成功；若期间已被别人改过（版本变了），写就失败，调用方需重读重试。这把"先读后写"的竞态挡在了存储层，让上层不必自己加分布式锁。<strong>事务保证一组写的原子性，CAS 保证一次写的不被覆盖</strong>——两者一起，撑起了元数据在并发下的正确性。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">pkg/kv/kv.go</span><span class="ln">BaseKV → TxnKV → MetaKv → WatchKV</span></div>
  <pre><span class="cm">// 最朴素的增删查</span>
<span class="kw">type</span> BaseKV <span class="kw">interface</span> {
    Load(ctx, key) (<span class="kw">string</span>, <span class="kw">error</span>)
    Save(ctx, key, value) <span class="kw">error</span>
    Remove(ctx, key) <span class="kw">error</span>
    LoadWithPrefix(ctx, key) ([]<span class="kw">string</span>, []<span class="kw">string</span>, <span class="kw">error</span>)
    <span class="cm">// ... MultiSave / MultiRemove / Has ...</span>
}

<span class="kw">type</span> TxnKV  <span class="kw">interface</span> { BaseKV; MultiSaveAndRemove(...) }   <span class="cm">// +事务</span>
<span class="kw">type</span> MetaKv <span class="kw">interface</span> { TxnKV; CompareVersionAndSwap(...) }  <span class="cm">// +租约/CAS</span>
<span class="kw">type</span> WatchKV <span class="kw">interface</span> { MetaKv; Watch(ctx, key) WatchChan } <span class="cm">// +监听</span></pre>
</div>

<h2>什么存哪：etcd 与对象存储的分工</h2>
<p>一个常被问到的问题：既然有 etcd 又有对象存储，到底什么进哪个？答案就一条<strong>体量与角色</strong>的分界——<strong>小而关键、要强一致、要被 watch 的"元数据"进 etcd；大而笨重、只需可靠存放的"数据与索引"进对象存储</strong>。
元数据里只留一个指向对象存储的<strong>路径引用</strong>。这样 etcd 永远很"瘦"，watch 与一致性才扛得住；对象存储则随数据量线性膨胀，但它不参与一致性协调，便宜、可无限堆。</p>

<p>这条分界不是洁癖，而是被 etcd 的硬约束逼出来的。etcd 是一个基于 Raft 的<strong>强一致</strong>存储，每一次写都要在多数派副本间达成共识——这让它<strong>可靠，但也"贵"</strong>：它对单个 value 的大小、对总数据量都有保守上限，吞吐也远不如对象存储。
如果有人图省事，把一段几百 MB 的向量 binlog 直接塞进 etcd，轻则拖垮 watch 与选主，重则整个集群的元数据层瘫痪。所以"<strong>大块数据一律下沉到对象存储、etcd 里只留路径</strong>"不是可选项，而是红线。记住这条，你看任何分布式系统的"元数据 vs 数据"分层时，都会立刻抓住要害：<strong>把强一致用在最该用的地方，别让它为海量数据买单</strong>。</p>

<table class="t">
  <tr><th>内容</th><th>存在哪</th><th>为什么</th></tr>
  <tr><td>集合 schema、分区、别名</td><td class="mono">etcd</td><td>小、关键、需强一致与多版本</td></tr>
  <tr><td>段元数据（SegmentInfo、binlog 路径）</td><td class="mono">etcd</td><td>记的是"段在哪"，本身很小</td></tr>
  <tr><td>加载信息、副本、target</td><td class="mono">etcd</td><td>QueryCoord 的调度依据，需 watch</td></tr>
  <tr><td>服务发现 session（地址+租约）</td><td class="mono">etcd</td><td>瞬时状态，靠租约自动过期</td></tr>
  <tr><td>向量数据 binlog、索引文件</td><td class="mono">对象存储</td><td>体量大，只需可靠存放，元数据里留引用</td></tr>
  <tr><td>写入日志（WAL）</td><td class="mono">消息队列</td><td>第 7 课"日志即数据"的承载</td></tr>
</table>

<p>顺带把三个外部依赖在元数据视角下的分工再钉死一次：<strong>etcd 管"状态与协调"、对象存储管"大块数据"、消息队列管"写入流水"</strong>。第 8 课从部署角度认识过它们，这一课你看到的是它们在<strong>元数据链路</strong>里的角色。三者各守一摊、互不越界，正是 Milvus 能把"存"和"算"、"控制"和"数据"干净拆开的底层支撑。</p>

<h2>watch：协调者派活、节点接活</h2>
<p>最后一块拼图，是控制面如何把决策<strong>下发</strong>给数据面。机制还是 etcd 的 watch，但方向反过来：不是节点向 etcd 注册、协调者监听，而是<strong>协调者把"分配方案"写进 etcd，节点 watch 自己那一份</strong>。
比如 DataCoord 决定"vchannel-A 由 datanode-2 负责"，就把这条 channel 分配写进 etcd；datanode-2 watch 到属于自己的 key，就开始消费这条 channel。QueryCoord 派段也类似——这正是上一课"distribution 向 target 收敛"在存储层的落地：target 写进 etcd，节点 watch 后照着干。</p>

<div class="flow">
  <div class="node"><div class="nt">节点 Register()</div><div class="nd">写带租约 session 到 etcd</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">协调者 WatchServices</div><div class="nd">感知"谁活着、在哪"</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">协调者写分配</div><div class="nd">把 channel/段方案写进 etcd</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">节点 watch 接活</div><div class="nd">看到属于自己的 key，开始执行</div></div>
</div>

<p>把整条链收束成一句：<strong>etcd 既是"档案柜"（存元数据），又是"公告板"（发分配、做发现）</strong>。组件之间几乎不直接喊话定状态，而是"写 etcd / watch etcd"间接协作——这正是第 9 课"跨面通信只走接口与 etcd"那条纪律的物理实现。
读懂了元数据存哪、组件怎么发现彼此、协调者怎么派活，你就拿到了贯穿整个分布式部分的最后一把钥匙。</p>

<p>最后补一个"watch 并不那么简单"的现实。网络会抖动、连接会断，watch 一旦断开重连，中间那几个事件可能就漏掉了。Milvus 的应对是：watch 时记住一个 <strong>revision（版本水位）</strong>，断线重连后从这个水位<strong>续看</strong>，而不是从头再来；
更稳的做法是"<strong>先全量拉一次、再增量 watch</strong>"——先用 <span class="mono">GetSessions</span>/<span class="mono">LoadWithPrefix</span> 取一份当前快照对齐状态，再带着快照的 revision 开 watch，这样既不丢事件、也不会重复处理。你会发现 <span class="mono">WatchServices</span> 正是返回了一个 revision 给调用方，就是为此。
这提醒我们：<strong>watch 是"通知"，不是"真相"</strong>——真相永远是 etcd 里那份当前状态，通知只是帮你少做轮询。带着这个心态去读任何"监听变更"的代码，你就不会被"事件一定不丢"的幻觉误导。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话串起来：<strong>协调者说业务语言 → Catalog 翻译成键值语言 → kv 把它写进 etcd（小而关键的元数据）或对象存储（笨重的数据/索引）</strong>。
  与此并行，组件用 <strong>Register() 写带租约的 session</strong>、协调者 <strong>WatchServices</strong> 做服务发现；派活则反向——<strong>协调者把分配写进 etcd、节点 watch 接活</strong>。
  于是 etcd 同时扮演"档案柜 + 公告板"：存得住状态、又能让两个面间接协作。这就是把前五课所有角色粘起来的胶水。
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>三层落地</strong>：协调者（业务动词）→ metastore 的 <span class="mono">Catalog</span> 接口 → <span class="mono">kv</span> 原语 → etcd / 对象存储。每下一层更通用、更不懂业务。</li>
    <li><strong>Catalog 抽象</strong>：<span class="mono">internal/metastore/catalog.go</span> 按协调者切成 <span class="mono">RootCoordCatalog / DataCoordCatalog / QueryCoordCatalog</span>，屏蔽底层存储；RootCoord 的方法带 <span class="mono">ts</span>（多版本/快照）。</li>
    <li><strong>kv 层</strong>：<span class="mono">pkg/kv/kv.go</span> 逐层叠加 <span class="mono">BaseKV → TxnKV → MetaKv → WatchKV</span>（增删查 → 事务 → 租约/CAS → 监听），实现在 <span class="mono">internal/kv/etcd</span>。</li>
    <li><strong>什么存哪</strong>：小而关键、需强一致与 watch 的元数据进 etcd；笨重的向量/索引进对象存储，元数据里只留引用路径。</li>
    <li><strong>服务发现 + 派活</strong>：组件 <span class="mono">Register()</span> 带租约 session、协调者 <span class="mono">WatchServices</span> 监听上下线；派活反向——协调者把分配写进 etcd、节点 watch 接活。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The last five lessons introduced the control/data planes and the four roles: Proxy, RootCoord, DataCoord, QueryCoordV2. But the "global map" each one holds — a collection's schema, where segments live, who loaded what, which node is still alive — <strong>where is it stored, and how do they stay in sync</strong>?
This lesson is the <strong>glue that binds the whole architecture</strong>: <strong>etcd</strong> as the metadata store, <strong>sessions</strong> for service discovery, the <strong>metastore/Catalog</strong> abstraction over metadata I/O, the <strong>kv</strong> layer for primitives, and <strong>watch</strong> so coordinators assign work and nodes pick it up.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of the metadata system as a building's <strong>front desk + archive room</strong>. <strong>etcd is the front desk</strong>: every resident (component) signs the register on move-in — "who I am, which unit, am I still here" — and gets a <strong>keycard that must be periodically renewed (a lease)</strong>; forget to renew and the desk knows you've moved out.
  The <strong>archive room (object storage)</strong> holds the genuinely bulky things — furniture, equipment (data and index files); the desk only notes "the piano belongs to unit 7, shelf 3 in storeroom" — it never drags the piano to the front desk.
  And <strong>the Catalog is the archivist</strong>: everyone who reads or writes archives goes through that one standard window, never rummaging the storeroom themselves.
</div>

<h2>The whole picture: metadata from coordinators down to etcd</h2>
<p>Stack what this lesson covers and you won't get lost. At the top are the <strong>coordinators</strong> — RootCoord/DataCoord/QueryCoord — the <strong>producers and consumers</strong> of metadata: creating a collection writes a schema, segmenting records a segment, loading saves a replica.
They never hand-assemble etcd keys; they call the next layer's <strong>metastore Catalog interface</strong>, reading/writing metadata with "business verbs" like <span class="mono">CreateCollection</span>, <span class="mono">AddSegment</span>, <span class="mono">SaveReplica</span>.
Below Catalog sits the <strong>kv layer</strong> — serializing "a Collection object" into "a series of key/values" and calling primitives like <span class="mono">Save</span>/<span class="mono">MultiSave</span>/<span class="mono">LoadWithPrefix</span>. At the very bottom, kv actually writes bytes into <strong>etcd</strong> (small, critical metadata) or hands bulk data to <strong>object storage</strong>.</p>

<div class="layers">
  <div class="layer l-core"><div class="lh"><span class="badge">produce/consume</span><span class="name">Coordinators</span></div>
    <div class="ld">RootCoord/DataCoord/QueryCoord read/write metadata while deciding: schema, segments, indexes, replicas, load state. They speak only "business verbs," never touch storage details.</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">abstract interface</span><span class="name">metastore · Catalog</span></div>
    <div class="ld"><span class="mono">RootCoordCatalog / DataCoordCatalog / QueryCoordCatalog</span>: abstract "persist collection/segment/replica metadata" into interfaces, hiding whether the backend is etcd or something else.</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">primitives</span><span class="name">kv layer</span></div>
    <div class="ld"><span class="mono">BaseKV / TxnKV / MetaKv / WatchKV</span> (<span class="mono">pkg/kv/kv.go</span>): Save/Load/Remove, transactions, leases, watchable. Implementations in <span class="mono">internal/kv/etcd</span>.</div></div>
  <div class="layer l-app"><div class="lh"><span class="badge">where it lands</span><span class="name">etcd · object storage</span></div>
    <div class="ld">Small, critical metadata goes to etcd (strongly consistent, watchable); bulky vector/index files go to object storage, with metadata keeping only a reference path.</div></div>
</div>

<p>The essence of this picture is one line: <strong>coordinators speak "business language," Catalog translates to "key-value language," and kv writes it into etcd</strong>. Each layer down is more generic and cares less about business meaning.
Because Catalog is that translator, RootCoord never needs to know "how many keys a collection is split into in etcd"; and when the storage backend is swapped (say etcd for TiKV), the upper layers change not a single line. That is <strong>layered decoupling</strong> applied to the metadata system.</p>

<p>Walk "create a collection" end to end to feel the pipeline. The client sends CreateCollection, Proxy forwards it to RootCoord; RootCoord first allocates a global timestamp and some IDs from itself (Lesson 11), assembles the schema into a <span class="mono">model.Collection</span> domain object, then calls <span class="mono">RootCoordCatalog.CreateCollection(ctx, coll, ts)</span>.
At Catalog the object is <strong>decomposed</strong>: one key for the collection, one per field, one per partition... then <span class="mono">kv.MultiSave</span> writes that batch of key/values into etcd <strong>atomically in one transaction</strong>. Across the whole chain RootCoord only said "create a collection"; "into how many keys, and how to keep it atomic" was quietly absorbed by the two layers below. That is the hallmark of good abstraction: <strong>the upper intent is simple, the lower complexity is encapsulated</strong>.</p>

<h2>etcd and sessions: how components discover each other</h2>
<p>Metadata must "persist," but components must also "find" each other. Lesson 9 mentioned: at startup each component calls <span class="mono">Register()</span>, writing a <strong>leased</strong> session into etcd — "I am querynode-3, my gRPC address is here, I'm alive."
This lives in <span class="inline">internal/util/sessionutil/session_util.go</span>: a <span class="mono">Session</span> struct holds a <span class="mono">LeaseID</span>, and a background goroutine keeps <strong>renewing the lease (keepalive)</strong>; once the process crashes and the heartbeat stops, the lease expires and etcd auto-deletes the session record.</p>

<p>On the other end, coordinators call <span class="mono">WatchServices</span> to <strong>watch</strong> the prefix directory of these sessions: a node comes up and an "added" event fires instantly; a node drops (lease expires) and a "deleted" event fires.
So the control plane always holds a <strong>live roster of nodes</strong>, using it to assign segments, balance load, and reassign work on failure. This "<strong>register → renew → watch</strong>" is Milvus's service discovery — it shares the same etcd as metadata, but carries the <strong>transient state</strong> of "who's here, where," not the <strong>persistent metadata</strong> of "what a collection looks like."</p>

<p>Reiterate that red line from Lesson 9: <strong>a session stores an "address," not "data."</strong> On this path etcd is an "address book + heartbeat board"; it tells you "who's here, where," but real search/insert traffic never passes through etcd — that would instantly overwhelm it. Once a component has the peer's address, it sends requests over <strong>direct point-to-point gRPC</strong>. Control info via etcd, data traffic direct — a divide that runs through all of Milvus.</p>

<p>Why insist on "lease + renewal" instead of simply writing an <span class="mono">alive=true</span> flag? Because the hardest thing in a distributed system is not "graceful exit" but "<strong>sudden disappearance</strong>" — a process gets kill -9'd, a machine loses power, a cable is yanked. In those cases nobody gets a chance to flip the flag to false.
The beauty of a lease is that it <strong>makes "being alive" something you must keep paying to maintain</strong>: the moment the heartbeat stops, etcd itself purges the record when the lease expires, with no cleanup by anyone. This is a "<strong>failure is the default</strong>" design — the system assumes a node may vanish at any time, and being alive is the exception that must be continually proven. Grasp this and you grasp the same philosophy behind nearly every distributed heartbeat mechanism.</p>

<p>One practical detail worth noting: all these keys (metadata and sessions alike) hang under a unified <strong>metaRoot prefix</strong> (config-driven, e.g. <span class="mono">by-dev/meta</span>). This lets one etcd cluster <strong>isolate multiple Milvus instances</strong> — each uses its own prefix, never crossing wires. It's also why <span class="mono">LoadWithPrefix</span> and <span class="mono">WatchWithPrefix</span> appear everywhere in the source: in etcd's flat key/value space, <strong>a prefix is a namespace</strong>, the basic device by which Milvus organizes its whole metadata graph.</p>

<h2>metastore and Catalog: the "archive interface" for metadata</h2>
<p>Now the core abstraction. <span class="inline">internal/metastore/catalog.go</span> defines several interfaces <strong>split by coordinator</strong>: <span class="mono">RootCoordCatalog</span> owns databases/collections/partitions/aliases/credentials/roles;
<span class="mono">DataCoordCatalog</span> owns segments (<span class="mono">ListSegments</span>/<span class="mono">AddSegment</span>/<span class="mono">DropSegment</span>), channels, indexes; <span class="mono">QueryCoordCatalog</span> owns load info (<span class="mono">SaveCollection</span>/<span class="mono">SaveReplica</span>/<span class="mono">SaveCollectionTargets</span>).
Every method is a <strong>business verb</strong>, and its arguments are domain objects like <span class="mono">model.Collection</span>, <span class="mono">datapb.SegmentInfo</span>, <span class="mono">querypb.Replica</span> — not raw bytes.</p>

<p>Notice the symmetry: the three catalog interfaces map exactly onto the three coordinators from Lessons 11–13. RootCoord owns "what exists" (schema/DDL), DataCoord owns "where data sits" (segments/channels), QueryCoord owns "what's loaded" (replicas/targets). Each coordinator persists only its own slice of the world through its own catalog, and the slices barely overlap. That clean partition is why the three roles can be reasoned about — and packaged into one MixCoord process — without their metadata stepping on each other. The Catalog split is the storage-layer mirror of the responsibility split you already learned.</p>

<p>Note that many RootCoordCatalog methods carry a <span class="mono">ts typeutil.Timestamp</span> argument — because RootCoord's metadata is <strong>multi-versioned</strong>: DDL operations hang on a timestamp, so "the schema as seen at a given instant" can be reproduced exactly.
Historically this was done by a "snapshot kv" layer — storing different versions of the same key as multiple records keyed by timestamp, reading the latest "no later than instant T." It makes consistency levels and time-travel reads possible. Today Catalog's concrete impl (<span class="mono">internal/metastore/kv/rootcoord</span>) holds a <span class="mono">kv.TxnKV</span> and splits domain objects into key/value pairs.</p>

<p>Funneling metadata I/O through the Catalog interface has another big engineering payoff: <strong>testability</strong>. To test RootCoord's create-collection logic you needn't spin up a real etcd — hand it a mock Catalog, or an in-memory kv (<span class="mono">internal/kv/mem</span>), and tests run fast and stable.
This is the same move as Lesson 9's "interfaces as pluggable seams": <strong>wherever code touches the outside world (storage, network), insulate it behind an interface</strong>, so production wires in real etcd while tests wire in a fake. The many <span class="mono">mock_*.go</span> files in the Milvus source are largely auto-generated for exactly these Catalog/kv interfaces. <strong>Abstraction is not only for elegance, but to be independently verifiable</strong>.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/metastore/catalog.go</span><span class="ln">Catalog interfaces (excerpt)</span></div>
  <pre><span class="cm">// RootCoord metadata: db/collection/partition; methods carry ts (multi-version)</span>
<span class="kw">type</span> RootCoordCatalog <span class="kw">interface</span> {
    CreateCollection(ctx, coll *model.Collection, ts Timestamp) <span class="kw">error</span>
    GetCollectionByID(ctx, dbID, ts Timestamp, id UniqueID) (*model.Collection, <span class="kw">error</span>)
    DropCollection(ctx, coll *model.Collection, ts Timestamp) <span class="kw">error</span>
    <span class="cm">// ... partitions, aliases, credentials, roles ...</span>
}

<span class="cm">// DataCoord metadata: segments and channels</span>
<span class="kw">type</span> DataCoordCatalog <span class="kw">interface</span> {
    ListSegments(ctx, collectionID <span class="kw">int64</span>) ([]*datapb.SegmentInfo, <span class="kw">error</span>)
    AddSegment(ctx, segment *datapb.SegmentInfo) <span class="kw">error</span>
    DropSegment(ctx, segment *datapb.SegmentInfo) <span class="kw">error</span>
}</pre>
</div>

<h2>The kv layer: the primitives beneath Catalog</h2>
<p>Below Catalog is a set of <strong>incrementally stacked</strong> interfaces in <span class="inline">pkg/kv/kv.go</span>. At the bottom is <span class="mono">BaseKV</span>: the plainest create/read/delete — <span class="mono">Save/Load/Remove/MultiSave/LoadWithPrefix</span>.
Above it, <span class="mono">TxnKV</span> adds <strong>transactions</strong> (<span class="mono">MultiSaveAndRemove</span> — multiple writes and deletes all succeed or all fail, crucial for "alter schema while deleting old keys").
Above that, <span class="mono">MetaKv</span> adds <strong>leases</strong> and <span class="mono">CompareVersionAndSwap</span> (optimistic locking). At the top, <span class="mono">WatchKV</span> adds <span class="mono">Watch</span> — the very foundation of service discovery and the "assign work" mechanism.</p>

<p>This "interface-on-interface" stacking is the same engineering aesthetic as <span class="mono">Component</span> in Lesson 9: <strong>depend on exactly the layer whose capabilities you need</strong>. A module that only reads config depends on <span class="mono">BaseKV</span>;
a Catalog that needs transactions depends on <span class="mono">TxnKV</span>; service discovery that watches for changes depends on <span class="mono">WatchKV</span>. Implementations live in <span class="mono">internal/kv/etcd</span> (the etcd version) and <span class="mono">internal/kv/mem</span> (an in-memory version for tests).
Here is the contract stacking from <span class="mono">BaseKV</span> all the way up to <span class="mono">WatchKV</span>:</p>

<p>That <span class="mono">CompareVersionAndSwap</span> (compare-then-swap, i.e. CAS) on <span class="mono">MetaKv</span> deserves a callout: it is the basis of <strong>optimistic locking</strong>. Imagine two coordinator replicas both wanting to edit the same metadata; if each writes blindly, the later write silently overwrites the earlier — a lost update.
CAS instead "<strong>writes carrying the version I saw</strong>" — the write succeeds only if etcd's version still matches what I read; if someone changed it meanwhile (version moved), the write fails and the caller must re-read and retry. This blocks the read-then-write race at the storage layer, sparing upper layers from rolling their own distributed lock. <strong>Transactions guarantee atomicity of a group of writes; CAS guarantees one write isn't overwritten</strong> — together they uphold metadata correctness under concurrency.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">pkg/kv/kv.go</span><span class="ln">BaseKV → TxnKV → MetaKv → WatchKV</span></div>
  <pre><span class="cm">// the plainest create/read/delete</span>
<span class="kw">type</span> BaseKV <span class="kw">interface</span> {
    Load(ctx, key) (<span class="kw">string</span>, <span class="kw">error</span>)
    Save(ctx, key, value) <span class="kw">error</span>
    Remove(ctx, key) <span class="kw">error</span>
    LoadWithPrefix(ctx, key) ([]<span class="kw">string</span>, []<span class="kw">string</span>, <span class="kw">error</span>)
    <span class="cm">// ... MultiSave / MultiRemove / Has ...</span>
}

<span class="kw">type</span> TxnKV  <span class="kw">interface</span> { BaseKV; MultiSaveAndRemove(...) }   <span class="cm">// +transactions</span>
<span class="kw">type</span> MetaKv <span class="kw">interface</span> { TxnKV; CompareVersionAndSwap(...) }  <span class="cm">// +lease/CAS</span>
<span class="kw">type</span> WatchKV <span class="kw">interface</span> { MetaKv; Watch(ctx, key) WatchChan } <span class="cm">// +watch</span></pre>
</div>

<h2>What goes where: etcd vs object storage</h2>
<p>A common question: with both etcd and object storage, what goes in which? The answer is a single line drawn on <strong>size and role</strong> — <strong>small, critical "metadata" that needs strong consistency and watching goes to etcd; bulky "data and indexes" that only need reliable storage go to object storage</strong>.
Metadata keeps only a <strong>reference path</strong> into object storage. This keeps etcd forever "thin," so watch and consistency hold up; object storage grows linearly with data but never participates in consistency coordination — it's cheap and stackable without limit.</p>

<p>This divide is not fastidiousness but is forced by etcd's hard constraints. etcd is a Raft-based <strong>strongly consistent</strong> store; every write must reach consensus across a majority of replicas — which makes it <strong>reliable but also "expensive"</strong>: it imposes conservative caps on single-value size and total data volume, with throughput far below object storage.
If someone took a shortcut and stuffed a few-hundred-MB vector binlog straight into etcd, at best it drags down watch and leader election, at worst it paralyzes the cluster's whole metadata layer. So "<strong>bulk data always sinks to object storage; etcd keeps only the path</strong>" is not optional but a red line. Remember it and you'll instantly grasp the crux of any "metadata vs data" layering: <strong>spend strong consistency where it matters most, and don't make it pay for massive data</strong>.</p>

<table class="t">
  <tr><th>Content</th><th>Where</th><th>Why</th></tr>
  <tr><td>collection schema, partitions, aliases</td><td class="mono">etcd</td><td>small, critical, needs strong consistency + versions</td></tr>
  <tr><td>segment metadata (SegmentInfo, binlog paths)</td><td class="mono">etcd</td><td>records "where a segment is"; tiny itself</td></tr>
  <tr><td>load info, replicas, targets</td><td class="mono">etcd</td><td>QueryCoord's scheduling basis; needs watch</td></tr>
  <tr><td>discovery session (address + lease)</td><td class="mono">etcd</td><td>transient state, auto-expires via lease</td></tr>
  <tr><td>vector binlogs, index files</td><td class="mono">object storage</td><td>bulky; only needs reliable storage; metadata keeps a reference</td></tr>
  <tr><td>write-ahead log (WAL)</td><td class="mono">message queue</td><td>the carrier for Lesson 7's "log-as-data"</td></tr>
</table>

<p>While here, nail down the three external dependencies once more from the metadata angle: <strong>etcd owns "state and coordination," object storage owns "bulk data," the message queue owns "the write pipeline."</strong> Lesson 8 met them from a deployment angle; here you see their roles in the <strong>metadata path</strong>. Each guards its own turf without trespassing — the underlying support that lets Milvus cleanly split "store" from "compute," and "control" from "data."</p>

<h2>watch: coordinators assign, nodes pick up</h2>
<p>The final piece is how the control plane <strong>pushes</strong> decisions down to the data plane. The mechanism is still etcd watch, but reversed: instead of nodes registering and coordinators watching, <strong>coordinators write the "assignment plan" into etcd and nodes watch their own slice</strong>.
For instance, DataCoord decides "vchannel-A is handled by datanode-2" and writes that channel assignment into etcd; datanode-2 watches the key belonging to it and starts consuming that channel. QueryCoord assigns segments similarly — which is exactly the previous lesson's "distribution converging to target" realized at the storage layer: the target is written into etcd, and nodes watch and act on it.</p>

<div class="flow">
  <div class="node"><div class="nt">node Register()</div><div class="nd">writes leased session to etcd</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">coord WatchServices</div><div class="nd">learns "who's alive, where"</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">coord writes assignment</div><div class="nd">channel/segment plan into etcd</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">node watches, picks up</div><div class="nd">sees its own key, starts executing</div></div>
</div>

<p>Collapse the whole chain to one line: <strong>etcd is both the "filing cabinet" (stores metadata) and the "bulletin board" (publishes assignments, drives discovery)</strong>. Components rarely shout directly to fix state; instead they cooperate indirectly via "write etcd / watch etcd" — the physical realization of Lesson 9's discipline "cross-plane communication only via interfaces and etcd."
Once you understand where metadata lives, how components discover each other, and how coordinators assign work, you hold the last key that runs through the entire distributed part.</p>

<p>One last reality: "watch is not as simple as it looks." Networks jitter, connections drop, and once a watch disconnects and reconnects, the few events in between may be missed. Milvus's answer: remember a <strong>revision (a version watermark)</strong> when watching, and after a reconnect <strong>resume from that watermark</strong> rather than starting over;
the sturdier pattern is "<strong>full pull once, then incremental watch</strong>" — first take a current snapshot with <span class="mono">GetSessions</span>/<span class="mono">LoadWithPrefix</span> to align state, then open the watch carrying that snapshot's revision, so you neither miss events nor double-process them. You'll notice <span class="mono">WatchServices</span> returns a revision to the caller for exactly this.
The reminder is: <strong>watch is a "notification," not the "truth"</strong> — the truth is always the current state in etcd; the notification just saves you from polling. Read any "watch for changes" code with this mindset and you won't be fooled by the illusion that "events are never lost."</p>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  In one line: <strong>coordinators speak business language → Catalog translates to key-value language → kv writes it into etcd (small, critical metadata) or object storage (bulky data/index)</strong>.
  In parallel, components <strong>Register() a leased session</strong> and coordinators <strong>WatchServices</strong> for discovery; assignment goes the other way — <strong>coordinators write the plan into etcd and nodes watch to pick it up</strong>.
  So etcd plays both "filing cabinet + bulletin board": it persists state and lets the two planes cooperate indirectly. That is the glue binding all five earlier roles together.
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Three layers down</strong>: coordinators (business verbs) → metastore's <span class="mono">Catalog</span> interfaces → <span class="mono">kv</span> primitives → etcd / object storage. Each layer down is more generic, less business-aware.</li>
    <li><strong>Catalog abstraction</strong>: <span class="mono">internal/metastore/catalog.go</span> splits by coordinator into <span class="mono">RootCoordCatalog / DataCoordCatalog / QueryCoordCatalog</span>, hiding the backend; RootCoord's methods carry <span class="mono">ts</span> (multi-version/snapshot).</li>
    <li><strong>kv layer</strong>: <span class="mono">pkg/kv/kv.go</span> stacks <span class="mono">BaseKV → TxnKV → MetaKv → WatchKV</span> (CRUD → transactions → lease/CAS → watch), implemented in <span class="mono">internal/kv/etcd</span>.</li>
    <li><strong>What goes where</strong>: small, critical metadata needing strong consistency + watch goes to etcd; bulky vectors/indexes go to object storage, with metadata keeping only a reference path.</li>
    <li><strong>Discovery + assignment</strong>: components <span class="mono">Register()</span> a leased session and coordinators <span class="mono">WatchServices</span> for up/down; assignment is reversed — coordinators write plans into etcd and nodes watch to pick up.</li>
  </ul>
</div>
""",
}
