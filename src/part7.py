"""Content for Part 7 (streaming system, deep dive). Lessons 31-33.

Each lesson is a bilingual dict {"zh": html, "en": html}, mirroring part1-6:
lead -> analogy card -> macro card -> >=3 visual diagrams per language ->
cited code (file+symbol) -> key-points card. Milvus facts verified against the
streaming-system agent guides and code under internal/streamingcoord,
internal/streamingnode, internal/cdc.
"""

LESSON_31 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
第 16 课我们说过：Milvus 把所有写入都先记进一条 <strong>WAL（Write-Ahead Log，预写日志）</strong>，它是整个系统的<strong>单一事实来源</strong>。
那一课只点到为止；这一部分（第七部分）我们就钻进这条日志的"引擎室"，看它到底由谁来管、怎么写、怎么在崩溃后恢复。先看骨架：
<strong>StreamingCoord</strong> 负责"<strong>把哪条日志分给哪台机器</strong>"，<strong>StreamingNode</strong> 负责"<strong>真正地写这条日志</strong>"，底下垫着一个可换的
<strong>WAL Backend</strong>（Kafka / Pulsar / Woodpecker / RocksMQ）。读懂这套架构，你就读懂了 Milvus"写"的最底层，也读懂了它<strong>为什么能既可靠、又可扩展、还能崩溃自愈</strong>——答案都藏在"一条可靠日志"这件事里。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把 WAL 想成一家银行的<strong>流水账本</strong>：任何一笔操作，<strong>先记账、再办事</strong>——只要账记下了，哪怕柜员下班、系统重启，事后照着账本一条条重放，状态就能完整复原。
  <strong>StreamingCoord</strong> 像<strong>总行调度</strong>：决定每个网点（PChannel）由哪位记账员（StreamingNode）负责；<strong>StreamingNode</strong> 是<strong>记账员</strong>本人，
  一笔笔往账本上写，还要盖时间戳、管事务、必要时上锁。账本本身存在哪种纸上（Kafka/Pulsar/…）可以换，但"先记账后办事"这条铁律不变。账记下了，就<strong>什么都不怕</strong>：哪怕整个机房断电，只要账本还在，把它从头念一遍，每一笔钱该在哪儿就还在哪儿。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：<strong>StreamingCoord（单例，跑在 RootCoord 进程里）把 PChannel 分配给 StreamingNode；StreamingNode 通过一条"拦截器链"(TimeTick/Txn/Shard/Lock)把每次写入落进 WAL Backend，并由 RecoveryStorage 负责检查点与崩溃恢复</strong>。
  WAL Backend 是可插拔的（Kafka/Pulsar/Woodpecker/RocksMQ），<strong>一个 PChannel 一个 topic</strong>。整条写入链路的可靠与有序，都由这套架构兜底。本课就沿"调度→写入→存储→恢复"这条线，把它逐层拆开看。
</div>

<h2>谁在管 WAL：StreamingCoord 与 StreamingNode</h2>
<p>WAL 不是一条，而是<strong>很多条</strong>——回忆第 7 课：一个集合被切成若干 <strong>VChannel（逻辑分片）</strong>，它们映射到物理的 <strong>PChannel</strong>，每个 PChannel 就是一条独立的日志流。
这么多条日志，得有人决定"<strong>哪条由哪台机器来写</strong>"，这就是 <strong>StreamingCoord</strong> 的活。它是一个<strong>单例</strong>，并不单独起进程，而是<strong>跑在 RootCoord（也就是今天 MixCoord 里）那部分</strong>。
它做<strong>通道管理（channel management）</strong>：把 PChannel 分配给各个 StreamingNode、监控节点健康、在节点上下线时重新均衡（balancer），还负责 VChannel/CChannel 的分配。简言之，StreamingCoord 是"<strong>日志的调度大脑</strong>"，但它<strong>自己不写日志</strong>。</p>

<p>真正写日志的是 <strong>StreamingNode</strong>。每个 StreamingNode 负责一批分给它的 PChannel，为每条 PChannel 跑一套完整的 WAL 机制（代码在 <span class="mono">internal/streamingnode/server/wal/</span>）。
它要做的事不少：给每条写入<strong>盖 TimeTick</strong>（那把单调时钟）、维护<strong>事务</strong>、做<strong>段分配（Shard Management）</strong>、必要时<strong>上锁</strong>保证独占写入、提供<strong>scanner</strong> 让消费者读日志、
以及最关键的——通过 <strong>RecoveryStorage</strong> 打检查点、在崩溃后从日志里把状态重建回来。一句话：<strong>StreamingCoord 管"谁来写"，StreamingNode 管"怎么写好、写稳、写得能恢复"</strong>。
这正是 Milvus 反复出现的"<strong>协调者调度、节点执行</strong>"分工，在写入最底层的又一次体现。</p>

<p>为什么要把一个集合的写入拆成<strong>多条 PChannel</strong>，而不是图省事用一条大日志？因为<strong>一条日志的吞吐有上限</strong>：写入是顺序追加的，一条 PChannel 再快，也终究是单点。
把集合切成多条 VChannel/PChannel、分散到多个 StreamingNode 上并行写，<strong>整体写入吞吐就能随机器数线性扩展</strong>——这正是"存算分离 + 水平扩展"在写入侧的体现。
代价是要有人统筹这些分片：哪条 PChannel 在哪台机器、某台机器挂了它负责的 PChannel 怎么办、新加机器后要不要把一些 PChannel 迁过去再均衡……这些"<strong>调度</strong>"工作正是 StreamingCoord 的 balancer 在做。
它持续<strong>监控各 StreamingNode 的健康</strong>：一旦某个节点失联，就把它名下的 PChannel <strong>重新分配</strong>给健康节点，新节点接手后从 WAL 的检查点处<strong>重放恢复</strong>，继续写。
于是对外看，写入<strong>既能横向扩展、又能在节点故障时自愈</strong>——而这一切的前提，正是"日志可被任何一台机器接手重放"。把"谁来写"这件会随集群变动的事，交给一个统一的大脑集中决策，是把复杂度收敛的关键一招。</p>

<div class="layers">
  <div class="layer l-core"><div class="lh"><span class="badge">调度</span><span class="name">StreamingCoord</span></div><div class="ld">单例，跑在 RootCoord 进程；把 PChannel 分给 StreamingNode、健康监控、再均衡（不写日志）</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">执行</span><span class="name">StreamingNode</span></div><div class="ld">为每条 PChannel 跑 WAL：拦截器链(TimeTick/Txn/Shard/Lock) + scanner + RecoveryStorage</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">存储</span><span class="name">WAL Backend</span></div><div class="ld">可插拔：Kafka / Pulsar / Woodpecker / RocksMQ，一个 PChannel 一个 topic</div></div>
</div>

<h2>拦截器链：每次写入都要"过五关"</h2>
<p>StreamingNode 写日志不是"直接往后追加"那么简单。每一次 <span class="inline">Append</span>，都要先穿过一条<strong>拦截器链（interceptor chain）</strong>——一组按顺序挂上去的处理器，每个负责一件横切的事。
这套设计的妙处在于：把"盖时间戳""管事务""分配段""上锁"这些<strong>正交的关注点拆开</strong>，各做各的、可插拔、易测试，而不是揉成一坨。主要的几关是：</p>

<p>这条链的<strong>顺序很有讲究</strong>：TimeTick 必须先盖，后面的事务、段分配才有统一的时间基准；Lock 通常在更外层，保证整段处理的原子性。你可以把它想成一条<strong>装配线</strong>——
每个工位只拧一种螺丝，零件按固定顺序流过，最后下线的就是一条"<strong>盖好戳、归好属、入好账</strong>"的合规日志。这种"<strong>责任单一、按序串联</strong>"的设计，让 Milvus 能<strong>灵活增减横切能力</strong>：
要支持一种新的写语义，往链上挂一个新拦截器即可，不必去动核心的追加逻辑。这也是为什么 DDL/DCL、事务、复制这些后来才加的能力，能比较干净地融进来——它们大多就是链上多挂的一环。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>TimeTick 拦截器</h4><p>给这条消息盖上 PChannel 级<strong>单调递增</strong>的 TimeTick——这把"日志时钟"正是读路径 tsafe 等待的对象（第 30 课）。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Txn 拦截器</h4><p>管理<strong>事务</strong>的生命周期：把一批本应"要么都见、要么都不见"的写入，框在一个事务里原子地落日志。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Shard 拦截器</h4><p>做<strong>段分配</strong>：决定这批行落到哪个 growing 段（段 ID 在此刻才定，回忆第 15 课"段 ID 在 StreamingNode 才分配"）。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Lock 拦截器</h4><p>在 VChannel 或 PChannel 粒度上做<strong>独占/共享</strong>访问控制，保证并发写入的正确顺序。</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>落 Backend</h4><p>穿过所有拦截器后，消息被<strong>真正追加</strong>到 WAL Backend 的对应 topic，成为不可变的一条日志。</p></div></div>
</div>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/streamingnode/server/wal/</span><span class="ln">WAL 与拦截器链（节选示意）</span></div>
  <pre><span class="cm">// 每条 PChannel 对应一个 WAL；Append 前穿过拦截器链</span>
<span class="kw">type</span> WAL <span class="kw">interface</span> {
    Append(ctx, msg) (MessageID, error)   <span class="cm">// 经拦截器链 -> 落 backend</span>
    Read(opt) (Scanner, error)            <span class="cm">// 消费者顺序读日志</span>
}
<span class="cm">// interceptors: timetick / txn / shard / lock，按序挂载</span></pre>
</div>

<h2>WAL Backend：底层那张"日志纸"可以换</h2>
<p>拦截器链的尽头，是把消息真正写进 <strong>WAL Backend</strong>。Milvus 把"底层用什么存日志"抽象成了一个可插拔的接口（<span class="mono">walimpls</span>），于是你可以按部署形态选不同的实现，
而上层的写入逻辑<strong>一行都不用改</strong>。约定很简单：<strong>一个 PChannel 对应后端里的一个 topic</strong>，日志在 topic 里顺序追加、可被多个消费者重放。常见的几种后端各有取舍：</p>

<p>为什么坚持"<strong>一个 PChannel 一个 topic</strong>"？因为 PChannel 是 Milvus 保证<strong>有序</strong>的最小单位：同一条 PChannel 内的所有写入，TimeTick 严格递增、消费时也严格按这个顺序，
于是"先写的先被看到"在分片内永远成立。不同 PChannel 之间不要求全局有序（那样会牺牲并行度），跨分片的全局协调另有 CChannel（控制通道）兜底。把"<strong>分片内强有序、分片间高并行</strong>"这两件看似矛盾的事同时拿到，
正是靠"一分片一日志一 topic"的清爽对应关系。理解了这点，你也就明白为什么扩容是"加分片/加 PChannel"——每多一条独立日志，就多一份可并行的吞吐，而每条日志内部的有序性丝毫不受影响。</p>

<table class="t">
  <tr><th>后端</th><th>形态</th><th>适合</th></tr>
  <tr><td><strong>Woodpecker</strong></td><td class="mono">Milvus 内置的 WAL</td><td>新实例推荐：性能好、运维简单、成本低</td></tr>
  <tr><td><strong>Pulsar</strong></td><td class="mono">外部消息队列</td><td>集群模式的传统默认，生态成熟</td></tr>
  <tr><td><strong>Kafka</strong></td><td class="mono">外部消息队列</td><td>已有 Kafka 基础设施时</td></tr>
  <tr><td><strong>RocksMQ</strong></td><td class="mono">单机本地队列</td><td>Standalone 模式默认（不支持集群）</td></tr>
</table>

<p>把"日志的<strong>语义</strong>（追加、有序、可重放）"和"日志的<strong>实现</strong>（用 Kafka 还是 Woodpecker）"分开，是这套架构最聪明的地方之一：语义是 Milvus 自己牢牢握住的契约，实现则交给最合适的存储。
这也呼应了第 8 课讲的部署形态——同一套代码，Standalone 用 RocksMQ、集群用 Pulsar 或 Woodpecker，对上层完全透明。</p>

<p>值得专门提一句 <strong>Woodpecker</strong>：它是 Milvus<strong>自研、内置</strong>的 WAL 实现，目标是把"日志存储"这件事做得<strong>更贴合向量数据库的需求</strong>——既不必额外部署运维一套重型消息队列（像 Pulsar 那样），
又能在性能、成本、运维简单度上取得更好的平衡。所以官方建议<strong>新实例优先用 Woodpecker</strong>。这件事本身也印证了"把语义和实现分开"的价值：正因为上层只依赖抽象的 WAL 语义，Milvus 才能<strong>在不惊动上层的情况下，换上一套更合适的底层日志</strong>。
一个良好的抽象，让系统能随需求演进而"换底盘不换车身"——这是任何想长期演进的系统都该追求的。</p>

<h2>RecoveryStorage：崩了之后，照着日志重来</h2>
<p>WAL 之所以叫"<strong>预写</strong>日志，价值就在崩溃时兑现。设想一个 StreamingNode 突然宕机：它内存里的 growing 段、刚分配的段信息、消费到哪儿的进度，全没了。怎么办？
答案是 <strong>RecoveryStorage</strong>（<span class="mono">internal/streamingnode/server/wal/recovery</span>）：它在正常运行时<strong>周期性打检查点（checkpoint）</strong>，记下"我已经把日志安全处理到哪个位置、对应的元数据是什么"；
崩溃重启后，它<strong>从最近的检查点出发、重放检查点之后的那段 WAL</strong>，就能把段、进度等状态<strong>一字不差地重建</strong>回来。因为 WAL 是单一事实来源、且每条都带单调的 TimeTick，所以"重放"是确定性的——
重放同一段日志，必然得到同一个状态。<strong>检查点 + 重放</strong>，就是分布式系统里"<strong>故障即默认</strong>、靠日志兜底"哲学的又一次落地（回忆第 14 课的"故障即默认"）。
检查点的频率，还藏着一个工程取舍：打得越勤，崩溃后要重放的日志越短、恢复越快，但平时的开销越大；打得越疏则反之。这正是分布式系统里典型的"恢复时间 vs 常态开销"的权衡，Milvus 用合理的默认值替你兜住，必要时也可调。</p>

<p>如果你用过传统数据库，会觉得"WAL + 检查点 + 崩溃重放"很眼熟——单机数据库（如 MySQL 的 redo log、PostgreSQL 的 WAL）正是靠它保证崩溃后不丢已提交事务。
Milvus 借用了同一套朴素而强大的思想，但把它<strong>放大到了分布式、并做成了系统的主干而非辅助</strong>：在单机数据库里 WAL 是"为了崩溃恢复而存在的副产物"，主角是表和索引；
而在 Milvus 里，<strong>WAL 本身就是主角、是唯一的事实来源</strong>，表（段）、索引反而是"由日志派生、随时可由日志重建"的次生数据。这个主次的<strong>反转</strong>，是"日志即数据（log as data）"的精髓，
也解释了为什么 Milvus 敢让段在内存里、敢让多种数据形态异步追日志——因为只要 WAL 在，丢什么都能从头重放回来。</p>

<p>还有一面我们一直没细说：<strong>消费侧</strong>。日志写进去，总要有人读出来用。StreamingNode 提供 <strong>scanner</strong> 让消费者<strong>顺序读</strong>某条 PChannel 的日志——
回忆第 17 课：正是 StreamingNode 的 flusher 顺着 WAL 把消息变成 growing 段、再 flush 成 binlog；第 26 课里 QueryNode 的 delegator 也靠消费 WAL 尾巴让 growing 数据保持新鲜。
也就是说，<strong>同一条 WAL，被多个消费者按各自的进度重放</strong>，各自维护自己"读到哪儿"（checkpoint/seek 位置）。这种"<strong>一份日志、多方按需重放</strong>"的模式，让写入、落盘、查询、复制彼此解耦：
谁都不直接调谁，只是各自盯着同一条日志、按自己的节奏前进。把"协作"简化成"共享一条只增的日志"，是这套架构能既复杂又不乱的根本原因。</p>

<div class="flow">
  <div class="node hl"><div class="nt">检查点</div><div class="nd">记录已处理到的日志位置 + 元数据</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">崩溃</div><div class="nd">内存状态丢失</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">重放</div><div class="nd">从检查点之后重放 WAL</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">状态复原</div><div class="nd">段/进度一字不差重建</div></div>
</div>

<h2>这一切，为了"单一事实来源"</h2>
<p>退一步看，这套又是调度、又是拦截器、又是可插拔后端、又是检查点重放的复杂机制，最终都服务于一句话：<strong>让 WAL 成为可靠、有序、可重放的单一事实来源</strong>。
一旦做到这一点，上层一切都顺了——读路径靠 TimeTick/tsafe 等到该看的数据（第 30 课）、DataNode/StreamingNode 靠重放 WAL 重建段、副本与 CDC 靠复制 WAL 同步（下两课）。
<strong>"写"被收敛成"往一条可靠日志上追加"，"恢复/同步/一致性"则统统化简为"重放这条日志"</strong>。这就是"日志即数据"在工程上的全部威力。下一课，我们看一类特殊的写入——<strong>DDL/DCL</strong>，
为什么它不能像普通写入那样只进一条日志，而要靠一个叫 <strong>Broadcaster</strong> 的机制，<strong>原子地广播到很多条日志</strong>上。</p>

<p>临走前再把这一课的<strong>三层抽象</strong>钉一下，它们层层垫高、各管一段：最上是 <strong>StreamingCoord</strong> 的"<strong>调度</strong>"——决定布局（谁写哪条），它面对的是"集群会变"这件事；
中间是 <strong>StreamingNode</strong> 的"<strong>写好一条日志</strong>"——拦截器链 + scanner + RecoveryStorage，它面对的是"写要正确、要能被读、要能恢复"；最下是 <strong>WAL Backend</strong> 的"<strong>把字节落到持久存储</strong>"——它面对的是"用什么存"。
三层之间只通过<strong>清晰的接口</strong>耦合，于是每一层都能独立演进、独立扩展、独立替换。当你以后在日志里看到一条诡异的消息、或排查一次写入为什么慢，<strong>先想清楚问题落在哪一层</strong>（是分配不均？是某个拦截器？还是后端慢？），
就已经赢了一半。把一个复杂系统拆成"几层各自单一职责、以接口相连"的结构，既是读懂它的钥匙，也是设计它的范式。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>分工</strong>：StreamingCoord（单例，在 RootCoord 内）调度——把 PChannel 分给 StreamingNode；StreamingNode 执行——真正写每条 PChannel 的 WAL。</li>
    <li><strong>拦截器链</strong>：每次 Append 依次过 <strong>TimeTick / Txn / Shard / Lock</strong>，把盖时间戳、事务、段分配、上锁等横切关注点拆开处理。</li>
    <li><strong>WAL Backend 可插拔</strong>：Kafka / Pulsar / Woodpecker / RocksMQ，<strong>一个 PChannel 一个 topic</strong>；语义(追加/有序/可重放)固定，实现可换。</li>
    <li><strong>RecoveryStorage</strong>：周期检查点 + 崩溃后从检查点重放 WAL，确定性地重建状态——"故障即默认，靠日志兜底"。</li>
    <li><strong>归宿</strong>：一切复杂度都服务于"让 WAL 成为单一事实来源"；恢复/同步/一致性都化简为"重放日志"。</li>
    <li><strong>主次反转</strong>：传统库里 WAL 是为崩溃恢复的副产物、表才是主角；Milvus 里 WAL 是主角与唯一事实来源，段/索引是可由日志重建的派生数据。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Lesson 16 said it: Milvus records every write into a <strong>WAL (Write-Ahead Log)</strong> first, and that log is the system's
<strong>single source of truth</strong>. That lesson only sketched it; this part (Part 7) goes into the log's "engine room" — who runs it,
how it is written, and how it recovers after a crash. The skeleton: <strong>StreamingCoord</strong> decides "<strong>which log goes to which
machine</strong>", <strong>StreamingNode</strong> "<strong>actually writes that log</strong>", and underneath sits a pluggable <strong>WAL
Backend</strong> (Kafka / Pulsar / Woodpecker / RocksMQ). Understand this and you understand the very bottom of how Milvus "writes".
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of the WAL as a bank's <strong>ledger</strong>: for any operation, <strong>record first, then act</strong> — once it's in the ledger,
  even if the teller goes home or the system reboots, replaying the entries one by one fully restores the state. <strong>StreamingCoord</strong>
  is like <strong>head-office dispatch</strong>: deciding which branch (PChannel) each bookkeeper (StreamingNode) handles. <strong>StreamingNode</strong>
  is the <strong>bookkeeper</strong>: writing entry by entry, stamping timestamps, managing transactions, locking when needed. The kind of paper the
  ledger is on (Kafka/Pulsar/…) can change, but the iron rule "record before you act" does not.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>StreamingCoord (a singleton inside the RootCoord process) assigns PChannels to StreamingNodes; a StreamingNode lands each
  write into the WAL Backend through an "interceptor chain" (TimeTick/Txn/Shard/Lock), and RecoveryStorage handles checkpoints and crash
  recovery</strong>. The WAL Backend is pluggable (Kafka/Pulsar/Woodpecker/RocksMQ), with <strong>one topic per PChannel</strong>. The whole write
  path's reliability and ordering rest on this architecture.
</div>

<h2>Who runs the WAL: StreamingCoord and StreamingNode</h2>
<p>There isn't one WAL but <strong>many</strong> — recall Lesson 7: a collection is sharded into <strong>VChannels</strong> mapped to physical
<strong>PChannels</strong>, and each PChannel is an independent log stream. With so many logs, someone must decide "<strong>which log is written by
which machine</strong>", and that's <strong>StreamingCoord</strong>'s job. It is a <strong>singleton</strong>, doesn't run as a separate process,
but <strong>runs inside the RootCoord part (today, inside MixCoord)</strong>. It does <strong>channel management</strong>: assigning PChannels to
StreamingNodes, monitoring node health, rebalancing on join/leave (the balancer), and allocating VChannel/CChannel. In short, StreamingCoord is
the "<strong>scheduling brain of the log</strong>", but it <strong>writes no log itself</strong>.</p>

<p>The one that actually writes is <strong>StreamingNode</strong>. Each StreamingNode owns a batch of assigned PChannels and runs a full WAL
mechanism per PChannel (code in <span class="mono">internal/streamingnode/server/wal/</span>). It has plenty to do: <strong>stamp each write with a
TimeTick</strong> (the monotonic clock), manage <strong>transactions</strong>, do <strong>segment assignment (Shard Management)</strong>,
<strong>lock</strong> for exclusive writes when needed, provide a <strong>scanner</strong> for consumers to read the log, and — most importantly —
checkpoint via <strong>RecoveryStorage</strong> and rebuild state from the log after a crash. In a line: <strong>StreamingCoord owns "who writes",
StreamingNode owns "how to write it well, stably, and recoverably"</strong>. This is Milvus's recurring "<strong>coordinator schedules, node
executes</strong>" split, showing up once more at the very bottom of the write path.</p>

<div class="layers">
  <div class="layer l-core"><div class="lh"><span class="badge">schedule</span><span class="name">StreamingCoord</span></div><div class="ld">singleton inside RootCoord; assigns PChannels to StreamingNodes, health monitoring, rebalancing (writes no log)</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">execute</span><span class="name">StreamingNode</span></div><div class="ld">runs the WAL per PChannel: interceptor chain (TimeTick/Txn/Shard/Lock) + scanner + RecoveryStorage</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">storage</span><span class="name">WAL Backend</span></div><div class="ld">pluggable: Kafka / Pulsar / Woodpecker / RocksMQ, one topic per PChannel</div></div>
</div>

<h2>The interceptor chain: every write "runs the gauntlet"</h2>
<p>A StreamingNode doesn't just "append straight to the end". Every <span class="inline">Append</span> first passes through an <strong>interceptor
chain</strong> — an ordered set of handlers, each owning one cross-cutting concern. The beauty: <strong>separate orthogonal concerns</strong> — stamping
timestamps, managing transactions, assigning segments, locking — so each is independent, pluggable and testable, rather than tangled together. The main
gates are:</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>TimeTick interceptor</h4><p>stamps the message with a PChannel-level <strong>monotonically increasing</strong> TimeTick — the "log clock" that the read path's tsafe waits on (Lesson 30).</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Txn interceptor</h4><p>manages the <strong>transaction</strong> lifecycle: framing a batch that should be "all-or-nothing visible" into one atomic log transaction.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Shard interceptor</h4><p>does <strong>segment assignment</strong>: which growing segment these rows land in (the segment ID is decided here — recall Lesson 15, "segment ID is assigned at the StreamingNode").</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Lock interceptor</h4><p><strong>exclusive/shared</strong> access control at VChannel or PChannel scope, ensuring correct ordering of concurrent writes.</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>Land in the Backend</h4><p>after all interceptors, the message is <strong>actually appended</strong> to the WAL Backend's topic, becoming one immutable log entry.</p></div></div>
</div>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/streamingnode/server/wal/</span><span class="ln">the WAL and its interceptor chain (illustrative)</span></div>
  <pre><span class="cm">// each PChannel has a WAL; Append passes the interceptor chain first</span>
<span class="kw">type</span> WAL <span class="kw">interface</span> {
    Append(ctx, msg) (MessageID, error)   <span class="cm">// via interceptors -> land in backend</span>
    Read(opt) (Scanner, error)            <span class="cm">// consumers read the log in order</span>
}
<span class="cm">// interceptors: timetick / txn / shard / lock, mounted in order</span></pre>
</div>

<h2>WAL Backend: the underlying "log paper" is swappable</h2>
<p>At the end of the interceptor chain, the message is actually written to the <strong>WAL Backend</strong>. Milvus abstracts "what stores the log
underneath" into a pluggable interface (<span class="mono">walimpls</span>), so you can pick different implementations per deployment shape while the
upper write logic <strong>doesn't change a line</strong>. The contract is simple: <strong>one PChannel maps to one topic in the backend</strong>; the log is
appended in order within a topic and can be replayed by multiple consumers. The common backends each have trade-offs:</p>

<table class="t">
  <tr><th>Backend</th><th>Form</th><th>Good for</th></tr>
  <tr><td><strong>Woodpecker</strong></td><td class="mono">Milvus's built-in WAL</td><td>recommended for new instances: good perf, simple ops, low cost</td></tr>
  <tr><td><strong>Pulsar</strong></td><td class="mono">external message queue</td><td>the traditional cluster default, mature ecosystem</td></tr>
  <tr><td><strong>Kafka</strong></td><td class="mono">external message queue</td><td>when you already have Kafka infrastructure</td></tr>
  <tr><td><strong>RocksMQ</strong></td><td class="mono">single-node local queue</td><td>Standalone default (not supported in cluster)</td></tr>
</table>

<p>Separating the log's <strong>semantics</strong> (append, ordered, replayable) from its <strong>implementation</strong> (Kafka or Woodpecker) is one of
the smartest parts of this architecture: the semantics are a contract Milvus holds firmly, while the implementation is delegated to the most suitable
storage. This echoes Lesson 8's deployment shapes — the same code uses RocksMQ in Standalone and Pulsar/Woodpecker in a cluster, entirely transparent to
the upper layers.</p>

<h2>RecoveryStorage: after a crash, redo it from the log</h2>
<p>The WAL is called a "<strong>write-ahead</strong>" log precisely because its value pays off on a crash. Picture a StreamingNode suddenly dying: its
in-memory growing segments, freshly assigned segment info, and consume progress are all gone. What now? The answer is <strong>RecoveryStorage</strong>
(<span class="mono">internal/streamingnode/server/wal/recovery</span>): during normal operation it <strong>periodically checkpoints</strong>, recording "how far
I've safely processed the log and the corresponding metadata"; after a restart it <strong>starts from the latest checkpoint and replays the WAL after
it</strong>, rebuilding segments, progress and other state <strong>exactly</strong>. Because the WAL is the single source of truth and every entry carries a
monotonic TimeTick, "replay" is deterministic — replaying the same log necessarily yields the same state. <strong>Checkpoint + replay</strong> is another
landing of the distributed-systems philosophy "<strong>failure is the default, backed by the log</strong>" (recall Lesson 14's "failure as default").</p>

<div class="flow">
  <div class="node hl"><div class="nt">Checkpoint</div><div class="nd">record processed log position + metadata</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Crash</div><div class="nd">in-memory state lost</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Replay</div><div class="nd">replay WAL after the checkpoint</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">State restored</div><div class="nd">segments/progress rebuilt exactly</div></div>
</div>

<h2>All of it, for a "single source of truth"</h2>
<p>Step back: this whole machinery — scheduling, interceptors, a pluggable backend, checkpoint-replay — ultimately serves one sentence: <strong>make the
WAL a reliable, ordered, replayable single source of truth</strong>. Once that holds, everything above falls into place — the read path waits on
TimeTick/tsafe for the data it should see (Lesson 30), DataNode/StreamingNode rebuild segments by replaying the WAL, replicas and CDC sync by copying the
WAL (the next two lessons). <strong>"Writing" collapses into "append to one reliable log", and "recovery/sync/consistency" all reduce to "replay that
log"</strong>. That is the full power of "log as data". Next lesson, we look at a special kind of write — <strong>DDL/DCL</strong> — and why it can't just go
into one log like an ordinary write, but needs a mechanism called the <strong>Broadcaster</strong> to <strong>atomically broadcast across many logs</strong>.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Split</strong>: StreamingCoord (singleton, inside RootCoord) schedules — assigns PChannels to StreamingNodes; StreamingNode executes — actually writes each PChannel's WAL.</li>
    <li><strong>Interceptor chain</strong>: every Append passes <strong>TimeTick / Txn / Shard / Lock</strong> in order, separating timestamp-stamping, transactions, segment assignment and locking.</li>
    <li><strong>Pluggable WAL Backend</strong>: Kafka / Pulsar / Woodpecker / RocksMQ, <strong>one topic per PChannel</strong>; the semantics (append/ordered/replayable) are fixed, the implementation swappable.</li>
    <li><strong>RecoveryStorage</strong>: periodic checkpoints + replay the WAL from a checkpoint after a crash, deterministically rebuilding state — "failure is the default, backed by the log".</li>
    <li><strong>The destination</strong>: all the complexity serves "make the WAL the single source of truth"; recovery/sync/consistency all reduce to "replay the log".</li>
  </ul>
</div>
""",
}
