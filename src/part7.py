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


LESSON_32 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课的写入有个隐含前提：一次 insert/delete 只落进<strong>一条</strong> PChannel。可有一类写入天生不一样——<strong>DDL/DCL</strong>（建/删集合、建/删分区、建数据库、改别名、授权 RBAC……）。
它们改的不是某个分片的数据，而是<strong>整个集合（乃至整个集群）的元信息</strong>，因此必须<strong>同时、原子地</strong>作用到<strong>很多条 PChannel</strong> 上：不能东边的分片已经"知道集合建好了"、西边的还"不知道"。
普通写入进一条日志就够，DDL/DCL 却要"<strong>一句话广播到所有相关日志、且要么全成、要么全不成</strong>"。这件事由一个叫 <strong>Broadcaster（广播器）</strong>的机制专门负责。它也再次展示了"一切皆消息"的威力：连"改结构"这种特殊操作，最终也被收进同一条日志流里统一处理。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  普通写入像给某个<strong>部门</strong>发一条通知（只进那条线）。而 DDL 像<strong>全公司同时换一份新规章</strong>：不能让市场部已按新规、财务部还按旧规——那会乱套。
  正确做法是：先<strong>把相关部门都"锁住"</strong>（这期间不许有人偷偷改同一份规章），把新规<strong>同时下发到每个部门</strong>，等<strong>每个部门都回执"收到并生效"</strong>，这次变更才算数。
  <strong>Broadcaster</strong> 干的就是这件"<strong>锁住 → 同时下发 → 收齐回执</strong>"的事，保证全公司对"现在按哪份规章"有一致认知。少了任何一步——不锁，就可能两份新规打架；不收齐回执，就可能有人没收到却以为成了——一致性就破了。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：<strong>DML 走 Append（进一条 PChannel）；DDL/DCL 走 Broadcast——经 StreamingCoord 的 Broadcaster 原子地广播到所有相关 PChannel，带资源锁与 ACK 确认</strong>。
  每个 DDL/DCL 事件都是一条<strong>带语义的 Message</strong>（建集合/建分区/RBAC…各有自己的类型）。  这样，"改结构"和"改数据"就<strong>共用同一条日志、同一套时间戳</strong>，天然有序、可重放、可恢复。说到底，Milvus 没有为 DDL 另起炉灶，而是把它<strong>翻译成日志里的一种消息</strong>，让"广播原子性"成为流式系统里一项可复用的能力——这正是统一抽象的力量。
</div>

<h2>DML vs DDL：一条日志 vs 一群日志</h2>
<p>先把两类写入摆清楚。<strong>DML（数据操作）</strong>——insert、delete、upsert——影响的是<strong>具体某些行</strong>，这些行按主键哈希落到某条 VChannel/PChannel，所以一次 DML <strong>只需进一条日志</strong>（第 15、31 课）。
<strong>DDL（数据定义）</strong>——create/drop collection、create/drop partition、create database、alter alias——和 <strong>DCL（数据控制）</strong>——RBAC 授权/回收——改的是<strong>元信息（schema、分区、权限）</strong>，
它<strong>对整个集合的所有分片都成立</strong>。设想"建集合 C"只广播给了一半 PChannel：那么一半分片认为 C 存在、能接收写入，另一半还不认 C——数据就分裂了。所以 DDL/DCL 必须满足两个硬性要求：
<strong>① 原子性</strong>（对所有相关 PChannel 要么全生效、要么全不生效）；<strong>② 与 DML 的相对顺序明确</strong>（"先建集合、再往里写"这种因果不能乱）。一条普通的 Append 给不了这两条保证，于是有了 Broadcaster。</p>

<p>为什么"一半生效"如此致命？因为 Milvus 的很多组件都<strong>独立地消费各自的 PChannel</strong> 来感知世界（第 31 课的"一份日志、多方重放"）。如果建集合的消息只到了一半 PChannel，
那么负责另一半的 StreamingNode、DataNode、QueryNode 就会处在"<strong>对同一个集合是否存在持有不同认知</strong>"的分裂状态：有的开始为它分配段、建索引、接收查询，有的却把发来的写入当成"未知集合"拒掉。
这种<strong>元信息层面的不一致</strong>，比丢几条数据要可怕得多——它会让系统对"现在到底有哪些集合、什么 schema、谁有权限"失去统一答案，进而引发连锁错误。所以 DDL/DCL 的原子性不是"锦上添花"，而是<strong>正确性的底线</strong>：
要么让所有人同时进入新认知，要么所有人都停在旧认知，绝不允许中间态。理解了这个"底线"，你就明白 Broadcaster 那套看似繁琐的"锁 + 全员 ACK"为什么必不可少——它正是为了把"中间态"彻底消灭。换句话说，繁琐不是设计的缺点，而是"原子性"在分布式世界里必须付出的、最小的代价。</p>

<div class="cols">
  <div class="col"><h4>DML：单 PChannel Append</h4><p>insert/delete 按主键落到某条 PChannel，<strong>进一条日志</strong>即可。范围小、并行高、走最快的路径。</p></div>
  <div class="col"><h4>DDL/DCL：多 PChannel Broadcast</h4><p>建/删集合、RBAC 等改元信息，必须<strong>原子地广播到所有相关 PChannel</strong>，要么全成、要么全不成，宁慢勿乱。</p></div>
</div>

<h2>Broadcaster：锁住、广播、收齐回执</h2>
<p>举个最直观的因果例子：你先 <span class="inline">create_collection("docs")</span>，紧接着 <span class="inline">insert</span> 一批数据进 docs。如果"建集合"和"插数据"走两条互不相干的路，
插数据的消息完全可能<strong>先于</strong>"建集合"到达某个分片——那个分片一脸茫然："docs 是什么？我不认识。"于是写入失败或行为未定义。要杜绝这种错乱，唯一可靠的办法是让"建集合"和"插数据"<strong>排在同一条有序时间线上</strong>，
且"建集合"对所有相关分片<strong>原子地先生效</strong>。Broadcaster 正是为前半句（原子广播）服务，而"同一条时间线"则靠把 DDL 也编进 WAL、共用 TimeTick 来实现。下面就看 Broadcaster 具体怎么做到"原子"。</p>
<p><strong>Broadcaster</strong>（代码在 <span class="mono">internal/streamingcoord/server/broadcaster</span>）是 StreamingCoord 里专管"跨 PChannel 原子广播"的部件。一次 DDL/DCL 的旅程是这样的：
客户端的请求经 Proxy，调用 <span class="mono">StreamingClient.Broadcast</span>（而不是普通的 Append），消息被交给 StreamingCoord 的 Broadcaster；Broadcaster 先做<strong>资源加锁</strong>——
把这次变更涉及的资源（比如某个集合）"锁住"，防止两个并发 DDL 同时改同一个对象造成冲突；然后把这条 DDL 消息<strong>分发到所有相关的 PChannel</strong>（每条 PChannel 各自把它当成一条日志写下）；
最后<strong>追踪每条 PChannel 的 ACK</strong>——只有当所有相关 PChannel 都确认"我已经把这条 DDL 写进我的日志"了，这次广播才算成功、锁才释放。<strong>锁 + 全员 ACK</strong>，共同保证了"原子地、一致地"生效。</p>

<p>这里有几个细节值得品味。其一，<strong>资源锁的粒度</strong>：Broadcaster 锁的是"<strong>这次变更涉及的资源</strong>"（如某个具体集合），而不是把整个集群锁死——这样不相干的 DDL（改 A 集合 vs 改 B 集合）可以并行，只有真正冲突的才互斥，
既保正确又不牺牲并发。其二，<strong>失败怎么办</strong>：如果广播过程中某条 PChannel 迟迟不 ACK（比如负责它的节点挂了），这次广播就不会被当成成功；配合上一课的"节点失联→PChannel 重新分配→从检查点重放"，新接手的节点会把这条 DDL 一并恢复出来，
最终仍能收敛到一致。其三，<strong>ACK 的意义</strong>：它确认的不是"消息送达网络"，而是"<strong>这条 DDL 已经被写进了那条 PChannel 的 WAL</strong>"——也就是说，一旦广播成功，这次变更就已经<strong>持久地、可重放地</strong>记在了每条相关日志里，崩溃也丢不了。
把这三点串起来看，Broadcaster 本质是在多条独立日志之上，<strong>搭了一层"全有或全无"的原子提交协议</strong>——这正是分布式系统里经典的难题，而 Milvus 借"日志 + 锁 + ACK"把它解得相当干净。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Broadcast 发起</h4><p>Proxy 调 <span class="mono">StreamingClient.Broadcast</span>，DDL 消息交给 StreamingCoord 的 Broadcaster。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>资源加锁</h4><p>锁住本次变更涉及的资源，防止并发 DDL 冲突。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>广播到各 PChannel</h4><p>把消息分发给所有相关 PChannel，各自落进自己的 WAL。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>收齐 ACK 才算成</h4><p>追踪每条 PChannel 的确认；全部 ACK 后释放锁，广播成功。</p></div></div>
</div>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/streamingcoord/server/broadcaster</span><span class="ln">跨 PChannel 原子广播（节选示意）</span></div>
  <pre><span class="cm">// DDL/DCL 经 Broadcast 而非 Append：</span>
<span class="cm">//   StreamingClient.Broadcast(msg)</span>
<span class="cm">//     -> Broadcaster: 锁资源 -> 分发到所有相关 PChannel</span>
<span class="cm">//     -> 收齐每条 PChannel 的 ACK -> 释放锁，成功</span></pre>
</div>

<h2>消息语义：每个事件都是一条"有类型的话"</h2>
<p>无论 DML 还是 DDL/DCL，写进 WAL 的都是一条 <strong>Message</strong>，而且是<strong>带语义、带类型</strong>的——不是一坨字节，而是"<strong>一句系统能看懂的话</strong>"。流式系统为不同的事件定义了各自的消息语义
（在文档 <span class="mono">message/message-semantic-*</span> 里分门别类）：建集合是一种、建分区是一种、数据库、别名、RBAC 各是一种，事务的开始/提交也各有其消息。
正因为消息是有类型的，<strong>每个消费者都能精确地知道"这条日志要我做什么"</strong>：是要建一个新段、刷一批数据，还是更新一份 schema、调整一条权限。把"系统里发生的一切"统一建模成"<strong>一条条有语义的消息流</strong>"，
是这套流式架构能优雅承载 DML、DDL、DCL、事务、复制等各种异质操作的根本——它们形态各异，但在日志里都是"消息"，都遵循同一套有序、可重放的规则。</p>

<table class="t">
  <tr><th>消息类别</th><th>典型事件</th><th>作用范围</th></tr>
  <tr><td><strong>Collection</strong></td><td class="mono">建/删集合、改 schema</td><td>该集合的所有 PChannel</td></tr>
  <tr><td><strong>Partition</strong></td><td class="mono">建/删分区</td><td>该集合的所有 PChannel</td></tr>
  <tr><td><strong>Database</strong></td><td class="mono">建/删数据库</td><td>集群级</td></tr>
  <tr><td><strong>Alias</strong></td><td class="mono">建/改/删别名</td><td>集群级</td></tr>
  <tr><td><strong>RBAC（DCL）</strong></td><td class="mono">授权/回收角色权限</td><td>集群级</td></tr>
  <tr><td><strong>Txn</strong></td><td class="mono">事务 开始 / 提交</td><td>把一批写入框成原子单元</td></tr>
</table>

<p>从这张表能看出一个规律：<strong>作用范围越大、越需要"广播 + 原子"</strong>。集群级的 Database/Alias/RBAC、集合级的 Collection/Partition，都得让相关的所有 PChannel 步调一致，所以走 Broadcaster；
而事务（Txn）则是另一类——它不是"广播给很多分片"，而是在<strong>同一条日志内</strong>把"开始…提交"之间的一串写入框成一个原子单元，靠的是上一课说的 <strong>Txn 拦截器</strong>。把"原子"这件事拆成两个维度看会更清楚：
<strong>跨 PChannel 的原子靠 Broadcaster（锁 + 全员 ACK），单 PChannel 内多条写入的原子靠事务</strong>。Milvus 用这两套机制，覆盖了从"改一个集合的结构"到"把一批数据当成一笔"这些不同尺度的原子需求。</p>

<p>消息有类型，还带来一个工程上的大便利：<strong>可演进</strong>。系统要支持一种新的 DDL（比如未来某个新对象的建/删），只需在消息体系里<strong>新增一种消息类型</strong>、在 Broadcaster 与各消费者那里<strong>加一条处理分支</strong>，
而不必重新设计写入与排序机制——因为"广播 + 原子 + 有序 + 可重放"这些底层能力是<strong>所有消息共享</strong>的。这正是把"系统事件"统一建模成"消息流"的复利：基础设施一次建好，之后每种新事件都只是"在既有轨道上多跑一种车"。
当你日后在 <span class="mono">internal/streamingnode</span> 里看到一长串 message 类型和对应的 handler，不必被数量吓到——它们形态各异，但都站在同一套有序日志的地基上，遵循同一套规则。<strong>抓住"一切皆消息"这条主线，纷繁的类型就有了统一的归处。</strong></p>

<h2>为什么 DDL 也要"进日志"</h2>
<p>你也许会问：元信息直接写进 etcd（第 14 课）不就行了，何必也塞进 WAL？关键在于<strong>顺序与一致</strong>。如果 DDL 走 etcd、DML 走 WAL，两条路各有各的时间线，就很难保证"<strong>先建集合、再写入</strong>"这种因果——
某个分片可能在"还没收到建集合"时就收到了写入，无所适从。把 DDL/DCL 也<strong>编进同一条 WAL、用同一套 TimeTick 排序</strong>，"改结构"和"改数据"就落在了<strong>同一条时间线</strong>上，先后一目了然、对所有消费者一致。
而且 DDL 进了日志，就同样获得了 WAL 的全部好处：<strong>可重放</strong>（崩溃后照样能把"集合建过了"这件事恢复出来）、<strong>可被多方消费</strong>（各组件按需感知结构变化）。最终元数据仍会落到 etcd 等存储，但"<strong>变更何时发生、与数据如何排序</strong>"由 WAL 统一裁定。</p>

<p>这其实触及一个更深的问题：<strong>"结构"和"数据"到底该不该用同一套机制管？</strong>很多系统把它们分开——元数据走一致性存储（如 etcd/ZooKeeper），数据走另一条路，结果就得额外花大力气去协调两条时间线的先后。
Milvus 的选择是<strong>把它们统一进同一条日志</strong>：DDL 是日志里的消息，DML 也是日志里的消息，二者天然共享顺序。这带来的简化是惊人的——你不再需要一个"DDL 与 DML 的协调器"，因为<strong>顺序在写进日志的那一刻就已被 TimeTick 一锤定音</strong>。
代价是 DDL 也得忍受日志的约束（要广播、要 ACK、要走流式路径），但换来"<strong>全局只有一条时间线</strong>"的清爽，对一个要正确处理"边改结构边读写"的分布式数据库来说，太值了。</p>

<p>这再次印证了"日志即数据"的统一之美：<strong>把结构变更也当成数据流里的一条消息</strong>，整个系统就只需要理解"一条有序的日志"这一种东西。下一课，我们看这条日志还能怎么"复制出去"——跨集群的<strong>复制与 CDC</strong>。</p>

<p>把这一课放回"日志即数据"的大图景：到此为止，我们已经看到 WAL 承载了<strong>三类越来越"重"的写</strong>——普通 DML（一条日志）、跨分片的 DDL/DCL（Broadcaster 广播）、以及把多条写框成一笔的事务（Txn 拦截器）。
它们的范围、原子性要求各不相同，却被<strong>统一收纳进同一条有序日志</strong>，用同一套 TimeTick 排序、同一套重放机制恢复。这种"<strong>用一个统一抽象，吸收各种异质需求</strong>"的能力，正是一个好架构的标志：你不必为每种操作都发明一套新机制，
而是把它们都翻译成"日志里的一条（或一组）消息"，剩下的有序、持久、可恢复、可消费，全由日志这层统一兜底。当你以后读 Milvus 源码、看到形形色色的 message 类型在 streamingnode 里流转，记住它们背后是<strong>同一条主线</strong>：
一切系统事件，都是这条单一事实来源日志上的一条消息。理解了这条主线，纷繁的细节就有了归处。这，也是 Milvus 把一个庞杂系统收拢成"一条日志 + 若干消费者"这种<strong>可理解、可演进</strong>结构的根本秘诀。把这点记牢，再看后面的复制与 CDC，你会发现它依旧是同一个故事的延续：连"把数据同步到另一个集群"，本质也只是"<strong>把这条日志复制一份过去重放</strong>"而已。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>DML vs DDL/DCL</strong>：DML 影响某些行、进一条 PChannel(Append)；DDL/DCL 改元信息、须对所有相关 PChannel <strong>原子生效</strong>。</li>
    <li><strong>Broadcaster</strong>(<span class="mono">streamingcoord/server/broadcaster</span>)：<span class="mono">StreamingClient.Broadcast</span> → <strong>资源加锁 → 广播到各 PChannel → 收齐 ACK → 释放锁</strong>，保证原子一致。</li>
    <li><strong>消息语义</strong>：每个事件都是一条<strong>带类型的 Message</strong>(建集合/分区/数据库/别名/RBAC/事务各一种)，消费者据此精确知道"该做什么"，且新增事件只需加一种消息类型，易演进。</li>
    <li><strong>DDL 也进日志</strong>：与 DML 共用同一条 WAL、同一套 TimeTick，"改结构"和"改数据"落在同一条时间线上——天然有序、可重放、对所有人一致。</li>
    <li><strong>两种原子</strong>：跨 PChannel 的原子靠 Broadcaster(锁+全员 ACK)，单 PChannel 内多写的原子靠事务(Txn 拦截器)；ACK 确认的是"已写进对方 WAL"，故持久不丢。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson's writes had an implicit premise: one insert/delete lands in <strong>one</strong> PChannel. But one kind of write is inherently
different — <strong>DDL/DCL</strong> (create/drop collection, create/drop partition, create database, alter alias, RBAC grants…). They change not
one shard's data but the <strong>metadata of the whole collection (even the whole cluster)</strong>, so they must apply <strong>atomically and at
once</strong> to <strong>many PChannels</strong>: you can't have the east shard already "know the collection exists" while the west shard does not.
An ordinary write into one log suffices; DDL/DCL must "<strong>broadcast one statement to all relevant logs, all-or-nothing</strong>". A mechanism
called the <strong>Broadcaster</strong> handles exactly this.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  An ordinary write is like a memo to one <strong>department</strong> (into that one line). DDL is like <strong>changing the company-wide rulebook
  at once</strong>: you can't have Marketing on the new rules while Finance is still on the old — chaos. The right way: first <strong>lock the relevant
  departments</strong> (so nobody secretly edits the same rulebook meanwhile), <strong>deliver the new rules to every department simultaneously</strong>,
  and only once <strong>every department acknowledges "received and in effect"</strong> does the change count. The <strong>Broadcaster</strong> does
  exactly this "<strong>lock → deliver to all → collect acks</strong>", ensuring everyone agrees on "which rulebook is current".
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>DML uses Append (into one PChannel); DDL/DCL uses Broadcast — via StreamingCoord's Broadcaster, atomically broadcast to all
  relevant PChannels, with resource locking and ACK confirmation</strong>. Every DDL/DCL event is a <strong>typed Message</strong> (create-collection /
  create-partition / RBAC… each its own type). So "changing structure" and "changing data" <strong>share one log and one set of timestamps</strong> —
  naturally ordered, replayable and recoverable.
</div>

<h2>DML vs DDL: one log vs a flock of logs</h2>
<p>First, sort out the two kinds of writes. <strong>DML (data manipulation)</strong> — insert, delete, upsert — affects <strong>specific rows</strong>;
those rows hash by primary key into some VChannel/PChannel, so one DML <strong>only needs one log</strong> (Lessons 15, 31). <strong>DDL (data definition)</strong>
— create/drop collection, create/drop partition, create database, alter alias — and <strong>DCL (data control)</strong> — RBAC grant/revoke — change
<strong>metadata (schema, partitions, permissions)</strong>, which <strong>holds for all shards of the collection</strong>. Imagine "create collection C"
reaching only half the PChannels: half the shards think C exists and accept writes, the other half don't recognize C — data splits. So DDL/DCL must meet two
hard requirements: <strong>(1) atomicity</strong> (all relevant PChannels take effect, or none) and <strong>(2) a clear order relative to DML</strong>
("create the collection, then write into it" causality must not scramble). An ordinary Append can't give these two, hence the Broadcaster.</p>

<div class="cols">
  <div class="col"><h4>DML: single-PChannel Append</h4><p>insert/delete land in one PChannel by primary key, <strong>into one log</strong>. Small scope, high parallelism.</p></div>
  <div class="col"><h4>DDL/DCL: multi-PChannel Broadcast</h4><p>create/drop collection, RBAC, etc. change metadata and must <strong>atomically broadcast to all relevant PChannels</strong> — all or nothing.</p></div>
</div>

<h2>The Broadcaster: lock, broadcast, collect acks</h2>
<p>The <strong>Broadcaster</strong> (code in <span class="mono">internal/streamingcoord/server/broadcaster</span>) is the part of StreamingCoord dedicated to
"atomic cross-PChannel broadcast". A DDL/DCL's journey: the client's request goes through the Proxy and calls <span class="mono">StreamingClient.Broadcast</span>
(not the ordinary Append); the message is handed to StreamingCoord's Broadcaster; the Broadcaster first does <strong>resource locking</strong> — locking the
resource this change touches (say a collection) so two concurrent DDLs can't conflict on the same object; then it <strong>distributes the DDL message to all
relevant PChannels</strong> (each writes it as a log entry); finally it <strong>tracks the ACK from each PChannel</strong> — only when all relevant PChannels
confirm "I've written this DDL into my log" does the broadcast succeed and the lock release. <strong>Lock + all-acks</strong> together guarantee "atomic,
consistent" effect.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Broadcast initiated</h4><p>the Proxy calls <span class="mono">StreamingClient.Broadcast</span>; the DDL message goes to StreamingCoord's Broadcaster.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Resource lock</h4><p>lock the resource this change touches, preventing concurrent-DDL conflicts.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Broadcast to PChannels</h4><p>distribute the message to all relevant PChannels, each landing it in its own WAL.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>All-acks to succeed</h4><p>track each PChannel's confirmation; after all ACK, release the lock — broadcast succeeds.</p></div></div>
</div>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/streamingcoord/server/broadcaster</span><span class="ln">atomic cross-PChannel broadcast (illustrative)</span></div>
  <pre><span class="cm">// DDL/DCL go via Broadcast, not Append:</span>
<span class="cm">//   StreamingClient.Broadcast(msg)</span>
<span class="cm">//     -> Broadcaster: lock resource -> distribute to all relevant PChannels</span>
<span class="cm">//     -> collect each PChannel's ACK -> release lock, success</span></pre>
</div>

<h2>Message semantics: every event is a "typed sentence"</h2>
<p>Whether DML or DDL/DCL, what's written into the WAL is a <strong>Message</strong>, and a <strong>semantic, typed</strong> one — not a blob of bytes
but "<strong>a sentence the system understands</strong>". The streaming system defines distinct message semantics for different events (categorized in the
docs <span class="mono">message/message-semantic-*</span>): create-collection is one type, create-partition another, and database, alias, RBAC each their own,
with transaction begin/commit having their own messages too. Because messages are typed, <strong>each consumer knows precisely "what this log entry asks me to
do"</strong>: build a new segment, flush a batch, update a schema, or adjust a permission. Modeling "everything that happens in the system" uniformly as
"<strong>a stream of semantic messages</strong>" is what lets this streaming architecture gracefully carry DML, DDL, DCL, transactions, replication and more —
they differ in form, but in the log they are all "messages", all obeying the same ordered, replayable rules.</p>

<table class="t">
  <tr><th>Message class</th><th>Typical events</th><th>Scope</th></tr>
  <tr><td><strong>Collection</strong></td><td class="mono">create/drop collection, alter schema</td><td>all PChannels of the collection</td></tr>
  <tr><td><strong>Partition</strong></td><td class="mono">create/drop partition</td><td>all PChannels of the collection</td></tr>
  <tr><td><strong>Database</strong></td><td class="mono">create/drop database</td><td>cluster level</td></tr>
  <tr><td><strong>Alias</strong></td><td class="mono">create/alter/drop alias</td><td>cluster level</td></tr>
  <tr><td><strong>RBAC (DCL)</strong></td><td class="mono">grant/revoke role permissions</td><td>cluster level</td></tr>
  <tr><td><strong>Txn</strong></td><td class="mono">transaction begin / commit</td><td>frame a batch as one atomic unit</td></tr>
</table>

<p>A pattern emerges from this table: <strong>the larger the scope, the more it needs "broadcast + atomic"</strong>. Cluster-level Database/Alias/RBAC and
collection-level Collection/Partition all need every relevant PChannel in lockstep, so they go through the Broadcaster; transactions (Txn) are another kind —
not "broadcast to many shards" but framing a run of writes "begin…commit" into one atomic unit <strong>within one log</strong>, via the <strong>Txn interceptor</strong>
from the last lesson. Seeing "atomicity" in two dimensions clarifies it: <strong>cross-PChannel atomicity via the Broadcaster (lock + all-acks), within-one-PChannel
multi-write atomicity via transactions</strong>. With these two mechanisms, Milvus covers atomic needs of different scales, from "change a collection's structure" to
"treat a batch as one".</p>

<p>Typed messages also bring a big engineering convenience: <strong>evolvability</strong>. To support a new DDL, you just <strong>add a new message type</strong> and a
handling branch in the Broadcaster and the consumers — no need to redesign writing or ordering, because "broadcast + atomic + ordered + replayable" are <strong>shared by all
messages</strong>. That is the compounding return of modeling "system events" as a "message stream": build the infrastructure once, and each new event is just "another kind of car
on existing rails".</p>

<h2>Why DDL also "goes into the log"</h2>
<p>You might ask: just write metadata into etcd (Lesson 14) — why also stuff it into the WAL? The key is <strong>ordering and consistency</strong>. If DDL went
via etcd and DML via the WAL, the two paths would have separate timelines, making "<strong>create collection, then write</strong>" causality hard to guarantee —
a shard might receive a write while it "hasn't seen the create-collection yet", and be at a loss. By <strong>encoding DDL/DCL into the same WAL, ordered by the
same TimeTick</strong>, "changing structure" and "changing data" land on <strong>one timeline</strong>: order is unambiguous and consistent for all consumers. And
once DDL is in the log, it gains all the WAL's benefits: <strong>replayable</strong> (recover "the collection was created" after a crash), <strong>multi-consumer</strong>
(each component perceives structural changes as needed). Metadata still ends up in etcd and the like, but "<strong>when the change happened and how it orders against
data</strong>" is adjudicated uniformly by the WAL. This again shows the unifying beauty of "log as data": <strong>treat structural changes as just another message in
the data stream</strong>, and the whole system only needs to understand one thing — "one ordered log". Next lesson, we see how this log can also be "copied out" —
cross-cluster <strong>replication and CDC</strong>.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>DML vs DDL/DCL</strong>: DML affects some rows, into one PChannel (Append); DDL/DCL change metadata and must take effect <strong>atomically across all relevant PChannels</strong>.</li>
    <li><strong>Broadcaster</strong> (<span class="mono">streamingcoord/server/broadcaster</span>): <span class="mono">StreamingClient.Broadcast</span> → <strong>lock resource → broadcast to PChannels → collect ACKs → release lock</strong>, ensuring atomic consistency.</li>
    <li><strong>Message semantics</strong>: every event is a <strong>typed Message</strong> (create-collection/partition/database/alias/RBAC/txn each a type), so consumers know precisely "what to do".</li>
    <li><strong>DDL also in the log</strong>: sharing one WAL and one TimeTick with DML, "changing structure" and "changing data" land on one timeline — naturally ordered, replayable, consistent for all.</li>
  </ul>
</div>
""",
}


LESSON_33 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
这一部分讲到现在，"日志即数据"已经反复出现。这一课是它的<strong>终极兑现</strong>：要把一个集群的数据<strong>同步到另一个集群</strong>（异地容灾、跨地域只读、平滑迁移……），
最朴素也最强大的办法，不是去逐表逐段地拷贝状态，而是——<strong>把那条 WAL 复制过去，让对方重放一遍</strong>。因为 WAL 是单一事实来源、重放又是确定性的，
"复制数据"就被优雅地化简成了"<strong>复制一条有序日志 + 重放它</strong>"。这就是 Milvus 的<strong>复制与 CDC（Change Data Capture，变更数据捕获）</strong>。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  像总行和异地分行<strong>共享同一本流水账</strong>：总行（primary）每记一笔，就把这一笔<strong>原样抄送</strong>给异地分行（secondary），分行照着抄来的账<strong>重放一遍</strong>——
  既然两边念的是同一本、同一顺序的账，最终的余额自然分毫不差。分行不需要懂任何业务细节，<strong>只要忠实地把抄来的每一笔重放</strong>即可。
  万一总行所在的城市断网了，异地分行手里有完整的账本副本，<strong>随时能顶上来继续营业</strong>——这正是"容灾"的底气。整套机制里，分行做的事简单到近乎"机械"：收到一笔、按原顺序记一笔、重放一笔，绝不自作主张。正因为"机械"，它才<strong>可靠</strong>。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  一句话：<strong>Milvus 用 CDC 做跨集群的 WAL 复制（星型拓扑）。主集群的 WAL → CDC ChannelReplicator → 备集群的 Proxy → 备集群的 WAL（经 Replicate 拦截器）→ 备集群重放</strong>。
  因为复制的是<strong>日志本身</strong>、且每条带单调 TimeTick，备集群只要<strong>像普通集群一样消费/重放自己的 WAL</strong>，就能重建出与主集群一致的数据——复制几乎不需要"特殊逻辑"。这正是"日志即数据"埋下的复利：当初为"可靠写入"建的这条日志，如今顺带把"跨集群同步"这道难题也解了。
</div>

<h2>复制的本质：复制"日志"，而不是复制"状态"</h2>
<p>同步两个数据库，有两条根本不同的路。一条是<strong>复制状态</strong>：定期把表、段、索引这些"最终结果"整份拷过去——直观，但又重又难：数据在变，拷到一半就不一致了，还得处理增量、冲突、版本。
另一条是 Milvus 走的<strong>复制日志</strong>：只把"<strong>发生了哪些变更</strong>"这条有序流复制过去，让对方<strong>按同样的顺序重放</strong>，自然得到同样的状态。这正是数据库领域经典的 <strong>CDC（变更数据捕获）</strong>思想——
不传"现在是什么"，而传"<strong>发生了什么</strong>"。对 Milvus 来说，这条路几乎是<strong>免费</strong>的：它本来就有一条记录了所有变更、带全局顺序、可重放的 WAL；做复制，无非是把这条已有的日志<strong>多一个消费者（异地集群）</strong>而已。
"把同步问题转化为复制一条有序日志"，是"日志即数据"省下的又一大笔工程。</p>

<p>这个"复制日志"的思路，其实和我们前面反复见到的机制是<strong>同一个故事</strong>。第 31 课说"崩溃后从日志重放恢复状态"，第 26 课说"QueryNode 消费 WAL 尾巴让 growing 数据保持新鲜"——
它们本质都是"<strong>有人按顺序重放这条日志、从而获得对应的状态</strong>"。复制不过是把这个"重放者"<strong>挪到了另一个集群、另一个地域</strong>而已。换句话说，备集群在 Milvus 眼里并不特殊，
它就是一个"<strong>恰好把上游日志接到了远方主集群</strong>"的普通消费者。一旦你接受了"<strong>状态 = 日志的重放结果</strong>"这个世界观，"在异地造一份一样的数据"就不再是难题，而几乎是"顺手的事"：
让异地也念同一本账，余额自然相同。这种"<strong>把看似不同的需求，都还原成对同一条日志的操作</strong>"的统一感，正是这套架构最迷人的地方，也是你读懂它后会由衷赞叹的设计。</p>

<div class="cols">
  <div class="col"><h4>⚠️ 复制状态（笨办法）</h4><p>整份拷表/段/索引。数据在变就难保证一致，要处理增量、冲突、版本，又重又脆。</p></div>
  <div class="col"><h4>✅ 复制日志（Milvus / CDC）</h4><p>只复制"发生了哪些变更"的有序流，对方按同序重放即得同状态。复用已有 WAL，几乎零额外机制。</p></div>
</div>

<h2>数据流：从主集群到备集群</h2>
<p>把这条复制链路拆开看。主集群（primary）里，<strong>CDC 的 ChannelReplicator</strong>（代码在 <span class="mono">internal/cdc/replication</span>）盯着主集群的 WAL，把一条条变更消息<strong>读出来、转发</strong>给备集群（secondary）；
备集群的 <strong>Proxy</strong> 接收这些消息，但它不会把它们当成"新写入"重新分配时间戳——而是经过一个特殊的 <strong>Replicate 拦截器</strong>，<strong>原样保留消息里已有的 TimeTick 等元信息</strong>，再写进备集群自己的 WAL。
之后，备集群就和一个普通集群<strong>完全一样</strong>地消费这条 WAL：StreamingNode 落段、flush binlog，QueryNode 加载段、建索引……一切照旧。整条链路是：</p>

<p>这里最妙的一笔，是那个 <strong>Replicate 拦截器</strong>"<strong>不重新盖戳</strong>"的设计。回忆第 31 课：普通写入进 WAL 时，TimeTick 拦截器会给它盖一个本地的新时间戳。
但复制来的消息<strong>已经带着主集群盖好的 TimeTick</strong> 了——如果备集群再盖一个自己的，两边的顺序就对不上、数据也就不一致了。所以 Replicate 拦截器的职责恰恰相反：<strong>识别出"这是复制来的消息"，原样保留它的 TimeTick，不要动</strong>。
正是这"<strong>保留原序</strong>"的一小步，保证了主备两边重放出的<strong>顺序严格一致</strong>，从而状态严格一致。你看，整套复制机制里"特殊"的部分，少到只剩这一个拦截器、只做这一件"别乱盖戳"的事——其余全是复用既有的 WAL 写入、消费、落段、建索引流程。
<strong>复用得越多、特例越少，系统就越简单、越不容易出错</strong>，这正是好架构的标志。</p>

<div class="flow">
  <div class="node hl"><div class="nt">主集群 WAL</div><div class="nd">primary 的变更日志</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">ChannelReplicator</div><div class="nd">读出并转发(CDC)</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">备集群 Proxy</div><div class="nd">经 Replicate 拦截器</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">备集群 WAL</div><div class="nd">重放→重建数据</div></div>
</div>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/cdc/replication</span><span class="ln">跨集群 WAL 复制（节选示意）</span></div>
  <pre><span class="cm">// ChannelReplicator: 读主集群 WAL -> 转发到备集群</span>
<span class="cm">//   primary WAL --(读出变更消息)--&gt; Replicator</span>
<span class="cm">//     --&gt; secondary Proxy（Replicate 拦截器：保留原 TimeTick）</span>
<span class="cm">//       --&gt; secondary WAL --&gt; 备集群照常消费/重放</span></pre>
</div>

<h2>角色与拓扑：星型，一主多备</h2>
<p>Milvus 的跨集群复制采用<strong>星型拓扑</strong>：一个<strong>主（primary）</strong>集群居中，向若干<strong>备（secondary）</strong>集群单向复制。谁是主、谁是备、哪些 channel 往哪复制，由 <strong>CDC controller</strong>（<span class="mono">internal/cdc/controller</span>）
统一<strong>协调与管理角色</strong>。星型而非任意网状，是个有意的简化：它让"<strong>变更从唯一的源头流出</strong>"这件事保持清晰，避免多主互相复制带来的环路与冲突——又一次体现了"把复杂收敛到一个权威源头"的设计取向（回忆 TSO 也是这么做的）。
需要时，主备角色可以<strong>切换</strong>（比如主集群故障，把某个备提升为新主），这正是容灾切换（failover）的基础。</p>

<p>为什么是<strong>单向</strong>、而不是两边互相同步？因为"<strong>谁是唯一真相</strong>"必须明确。如果两个集群都能写、又互相复制，就会遇到经典的<strong>多主冲突</strong>：同一条数据被两边几乎同时改成不同的值，到底听谁的？
解决多主冲突要引入复杂的合并/仲裁逻辑，既难又容易出错。Milvus 的选择干脆利落：<strong>同一时刻只有一个主在写、变更单向流向备</strong>，备只读不写（对外只承接读）。这样"真相只有一个源头"，根本不给冲突留余地。
需要"双活"或主备切换时，则通过 controller <strong>显式地变更角色</strong>来完成，而不是放任两边自由互写。这种"<strong>宁可简单也不要含糊</strong>"的取舍，和前面 TSO 用单一来源发号、Broadcaster 用单一源头广播，是<strong>同一种工程审美</strong>：
把"谁说了算"这件事收敛到一个明确的权威上，复杂度就塌缩了一大半。</p>

<div class="layers">
  <div class="layer l-core"><div class="lh"><span class="badge">primary</span><span class="name">主集群</span></div><div class="ld">唯一的变更源头；其 WAL 被复制出去</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">controller</span><span class="name">CDC controller</span></div><div class="ld">协调角色与复制关系（谁复制给谁）</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">secondary</span><span class="name">备集群（可多个）</span></div><div class="ld">单向接收并重放主集群的 WAL；可被提升为新主</div></div>
</div>

<h2>用在哪：容灾、跨地域、迁移</h2>
<p>把"一份日志复制到异地重放"这件事用起来，能解决几类很实在的需求。<strong>① 异地容灾（DR）</strong>：在另一个地域维持一个热备集群，时刻跟随主集群；一旦主集群所在机房整体故障，把热备<strong>提升为主</strong>即可继续服务，
数据几乎不丢（取决于复制延迟）。<strong>② 跨地域只读</strong>：让离用户更近的备集群承接本地读请求，降低跨域延迟——写仍走主集群，读就近分担。<strong>③ 平滑迁移</strong>：要把数据搬到新集群/新版本时，先让新集群作为备追平主集群的全部历史与增量，
追平后一次切换，<strong>几乎无停机</strong>。这三类需求看似不同，底层却是同一件事：<strong>让另一个集群通过重放同一条日志，拥有同一份数据</strong>。这就是"日志即数据"在<strong>跨集群</strong>尺度上的威力。</p>

<p>这里有个绕不开的现实因素：<strong>复制延迟</strong>。主集群盖戳、转发、备集群再重放，整条链路需要时间，所以备集群的数据总是比主集群<strong>稍微滞后一点点</strong>（落后的量取决于网络与负载）。
这个延迟决定了容灾时的"<strong>能丢多少数据</strong>"：如果主集群在某一刻整体崩溃，那些"已写进主集群、但还没复制到备集群"的最新变更，就有丢失风险——这正是衡量容灾能力的 <strong>RPO（恢复点目标）</strong>。
好在因为复制的是<strong>有序日志</strong>，备集群很清楚自己"重放到了哪个 TimeTick"，断点续传、追平进度都有据可依，不会出现"复制到一半、状态错乱"的情况。要把 RPO 压到很小，就尽量降低复制延迟；要绝对不丢，则需更强的同步复制语义——
这又回到了第 30 课那个永恒的主题：<strong>一致性/新鲜度与性能/成本之间，永远是一场取舍</strong>，跨集群复制也不例外。理解了这层取舍，你在为业务设计容灾方案时，就知道每个旋钮拧的是什么。</p>

<h2>为什么这么干净</h2>
<p>退一步想：跨集群数据同步，在很多系统里是出了名的难——要处理增量捕获、顺序、冲突、断点续传、一致性……为什么 Milvus 这里显得如此"轻"？答案还是那三个字：<strong>WAL</strong>。
因为 WAL <strong>本就是单一事实来源</strong>，所有变更<strong>本就有全局顺序（TimeTick）</strong>，重放<strong>本就是确定性</strong>的——所以"复制"退化成了"把一条已经记好、排好序、能重放的日志，多送一份给异地"。
备集群不需要任何特殊的"同步逻辑"，它只是<strong>多接了一条上游日志的普通集群</strong>；那个 Replicate 拦截器要做的，也仅仅是"<strong>别给复制来的消息重新盖戳，保留它原本的 TimeTick</strong>"，好让两边的顺序严格一致。
<strong>一个好的基础抽象，会让原本最难的问题不药而愈</strong>——这是本课、也是整个第七部分最想留给你的体会。</p>

<p>这件事也反过来印证了一个判断：<strong>"日志即数据"不是一句口号，而是一个能持续生息的设计本金</strong>。回看这一路——崩溃恢复（重放日志）、边写边查（消费日志尾巴）、DDL 原子生效（广播进日志）、跨集群容灾（复制日志）——
没有哪一个是单独发明的"特性"，它们全都是"<strong>把状态建模成日志的重放结果</strong>"这一个决定，在不同场景下自然结出的果实。一个真正好的核心抽象就是这样：你为它<strong>一次性</strong>付出理解成本，之后它在一个又一个问题上<strong>反复回报</strong>你。
所以这一部分虽然概念密集，却最值得反复咀嚼——它不只是讲"流式系统怎么实现"，更是在示范"<strong>一个统一抽象如何驯服一个庞杂系统</strong>"。</p>

<p>到此，第七部分（流式系统）就讲完了：第 31 课看 WAL 怎么被管、被写、被恢复，第 32 课看 DDL/DCL 如何靠广播原子地进日志，这一课看日志如何被复制到另一个集群。它们共同回答了一个问题——
<strong>当你把"写入"彻底建模成"往一条可靠、有序、可重放的日志上追加"，可靠性、一致性、恢复、乃至跨集群复制，会如何统统变成"关于这条日志的操作"</strong>。这正是 Milvus 流式系统的设计哲学，也是它区别于很多向量库的根本之一。</p>

<p>再把整个第七部分放进全书来看：第四部分（写入链路）讲的是"<strong>一次写如何落进日志、变成段</strong>"，是从<strong>用户视角</strong>看写；而第七部分讲的是"<strong>承载这条日志的流式系统本身如何运转</strong>"，是从<strong>系统视角</strong>看写。
两者一表一里，合起来才是 Milvus"写"的完整图景。而贯穿始终的，是同一句话——<strong>WAL 是单一事实来源</strong>。把它真正理解透，你就握住了 Milvus 最核心的设计直觉：<strong>不要让状态成为真相，让日志成为真相；状态只是日志的一个个投影</strong>。
带着这把钥匙，接下来的几部分（C++ 内核、API 与运维、实战与贡献）你都能更轻松地看懂——因为无论钻到多深，那条贯穿系统的有序日志，始终是你脚下的地基。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>复制日志而非状态</strong>：跨集群同步 = 复制 WAL + 重放；传"发生了什么"(CDC)而非"现在是什么"，复用已有 WAL，几乎零额外机制。</li>
    <li><strong>数据流</strong>：主集群 WAL → CDC ChannelReplicator(<span class="mono">internal/cdc/replication</span>) → 备集群 Proxy(Replicate 拦截器，保留原 TimeTick) → 备集群 WAL → 照常重放。</li>
    <li><strong>星型拓扑 + 角色</strong>：一主多备、单向复制，CDC controller 协调角色；主备可切换，是容灾 failover 的基础。</li>
    <li><strong>用途</strong>：异地容灾(热备升主)、跨地域只读、平滑迁移——本质都是"让另一个集群重放同一条日志、拥有同一份数据"。</li>
    <li><strong>复制延迟与 RPO</strong>：备集群总比主集群稍滞后，决定容灾时"能丢多少"；因复制的是有序日志，备方清楚自己重放到哪个 TimeTick，可断点续传、追平进度。</li>
    <li><strong>为何干净</strong>：WAL 是单一事实来源 + 全局有序 + 确定性重放，故"复制"退化为"多送一份日志"；好的抽象让最难的问题不药而愈，这是本课最核心的体会。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
By now in this part, "log as data" has recurred again and again. This lesson is its <strong>ultimate payoff</strong>: to sync one cluster's data
<strong>to another cluster</strong> (cross-region disaster recovery, read replicas, smooth migration…), the simplest and most powerful way is not to copy
state table by table and segment by segment, but to — <strong>copy that WAL over and let the other side replay it</strong>. Because the WAL is the single
source of truth and replay is deterministic, "copying data" elegantly reduces to "<strong>copy an ordered log + replay it</strong>". That is Milvus's
<strong>replication and CDC (Change Data Capture)</strong>.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Like a head office and a remote branch <strong>sharing one ledger</strong>: every entry head office (primary) records, it <strong>copies verbatim</strong> to
  the remote branch (secondary), which <strong>replays</strong> the copied entries — since both read the same ledger in the same order, the final balances match
  to the cent. The branch needn't understand any business detail, it just <strong>faithfully replays each copied entry</strong>. Should head office's city lose
  connectivity, the remote branch holds a complete copy of the ledger and <strong>can take over and keep operating</strong> — that is the basis of disaster recovery.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>Milvus does cross-cluster WAL replication via CDC (star topology). The primary's WAL → CDC ChannelReplicator → the secondary's Proxy →
  the secondary's WAL (via a Replicate interceptor) → the secondary replays</strong>. Because what's replicated is <strong>the log itself</strong>, each entry
  carrying a monotonic TimeTick, the secondary just <strong>consumes/replays its own WAL like any normal cluster</strong> and rebuilds data consistent with the
  primary — replication needs almost no "special logic".
</div>

<h2>The essence: replicate the "log", not the "state"</h2>
<p>Syncing two databases has two fundamentally different paths. One is <strong>replicating state</strong>: periodically copy the "final results" — tables, segments,
indexes — wholesale. Intuitive, but heavy and hard: data keeps changing, so a half-done copy is inconsistent, and you must handle increments, conflicts, versions. The
other is Milvus's path, <strong>replicating the log</strong>: copy only the ordered stream of "<strong>what changed</strong>", and let the other side <strong>replay in the
same order</strong>, naturally arriving at the same state. This is the classic database idea of <strong>CDC (Change Data Capture)</strong> — ship not "what it is now" but
"<strong>what happened</strong>". For Milvus this path is almost <strong>free</strong>: it already has a WAL recording all changes, globally ordered and replayable; replication
is merely <strong>one more consumer (the remote cluster)</strong> of that existing log. "Turning sync into copying one ordered log" is another big engineering saving from "log
as data".</p>

<div class="cols">
  <div class="col"><h4>⚠️ Replicate state (the clumsy way)</h4><p>copy tables/segments/indexes wholesale. With data changing, consistency is hard; you must handle increments, conflicts, versions — heavy and brittle.</p></div>
  <div class="col"><h4>✅ Replicate the log (Milvus / CDC)</h4><p>copy only the ordered stream of "what changed"; the other side replays in order to the same state. Reuses the existing WAL, with almost no extra mechanism.</p></div>
</div>

<h2>Data flow: from primary to secondary</h2>
<p>Unpack the replication chain. In the primary, <strong>CDC's ChannelReplicator</strong> (code in <span class="mono">internal/cdc/replication</span>) watches the
primary's WAL and <strong>reads out and forwards</strong> each change message to the secondary; the secondary's <strong>Proxy</strong> receives them, but it does NOT
treat them as "new writes" to re-stamp — instead, via a special <strong>Replicate interceptor</strong>, it <strong>preserves the messages' existing TimeTick and other
metadata</strong> and writes them into the secondary's own WAL. After that, the secondary consumes that WAL <strong>exactly like a normal cluster</strong>: StreamingNode
lands segments and flushes binlogs, QueryNode loads segments and builds indexes… business as usual. The whole chain is:</p>

<div class="flow">
  <div class="node hl"><div class="nt">Primary WAL</div><div class="nd">primary's change log</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">ChannelReplicator</div><div class="nd">read &amp; forward (CDC)</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">Secondary Proxy</div><div class="nd">via Replicate interceptor</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">Secondary WAL</div><div class="nd">replay → rebuild data</div></div>
</div>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">internal/cdc/replication</span><span class="ln">cross-cluster WAL replication (illustrative)</span></div>
  <pre><span class="cm">// ChannelReplicator: read the primary WAL -> forward to the secondary</span>
<span class="cm">//   primary WAL --(read change messages)--&gt; Replicator</span>
<span class="cm">//     --&gt; secondary Proxy (Replicate interceptor: keep original TimeTick)</span>
<span class="cm">//       --&gt; secondary WAL --&gt; secondary consumes/replays as usual</span></pre>
</div>

<h2>Roles and topology: a star, one primary, many secondaries</h2>
<p>Milvus's cross-cluster replication uses a <strong>star topology</strong>: one <strong>primary</strong> cluster at the center replicates one-way to several
<strong>secondary</strong> clusters. Who is primary, who is secondary, and which channels replicate where, is <strong>coordinated and role-managed</strong> by the
<strong>CDC controller</strong> (<span class="mono">internal/cdc/controller</span>). A star, not an arbitrary mesh, is a deliberate simplification: it keeps "<strong>change
flows out from a single source</strong>" clear, avoiding the loops and conflicts of multi-primary mutual replication — once more the design bias of "converge complexity to
one authoritative source" (recall the TSO does the same). When needed, primary/secondary roles can <strong>switch</strong> (e.g. the primary fails, promote a secondary to be
the new primary), which is the basis of disaster failover.</p>

<div class="layers">
  <div class="layer l-core"><div class="lh"><span class="badge">primary</span><span class="name">primary cluster</span></div><div class="ld">the single source of change; its WAL is replicated out</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">controller</span><span class="name">CDC controller</span></div><div class="ld">coordinates roles and the replication relationships (who replicates to whom)</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">secondary</span><span class="name">secondary clusters (many)</span></div><div class="ld">one-way receive and replay the primary's WAL; can be promoted to primary</div></div>
</div>

<h2>Where it's used: DR, cross-region, migration</h2>
<p>Put "copy one log to a remote site and replay" to work and it solves several very real needs. <strong>(1) Disaster recovery (DR)</strong>: keep a hot-standby cluster in
another region tracking the primary; if the primary's data center fails entirely, <strong>promote the standby to primary</strong> and keep serving, with almost no data loss
(depending on replication lag). <strong>(2) Cross-region read replicas</strong>: let a secondary closer to users serve local reads, cutting cross-region latency — writes still
go to the primary, reads are offloaded nearby. <strong>(3) Smooth migration</strong>: to move data to a new cluster/version, first let the new cluster, as a secondary, catch up
on the primary's full history and increments; after catching up, switch once, <strong>with almost no downtime</strong>. These three look different but are the same underneath:
<strong>let another cluster have the same data by replaying the same log</strong>. That is the power of "log as data" at <strong>cross-cluster</strong> scale.</p>

<h2>Why it's so clean</h2>
<p>Step back: cross-cluster data sync is notoriously hard in many systems — change capture, ordering, conflicts, resumable transfer, consistency… Why does Milvus's look so
"light"? The answer is again three letters: <strong>WAL</strong>. Because the WAL <strong>is the single source of truth</strong>, all changes <strong>already have a global order
(TimeTick)</strong>, and replay <strong>is already deterministic</strong> — so "replication" degenerates into "ship one already-recorded, already-ordered, replayable log to a
remote site too". The secondary needs no special "sync logic"; it is simply <strong>a normal cluster that took on one more upstream log</strong>; and all the Replicate interceptor
does is "<strong>don't re-stamp replicated messages, keep their original TimeTick</strong>", so both sides' order stays strictly identical. <strong>A good foundational abstraction
makes the hardest problems heal on their own</strong> — that is what this lesson, and all of Part 7, most wants to leave you with.</p>

<p>With that, Part 7 (the streaming system) is complete: Lesson 31 saw how the WAL is managed, written and recovered, Lesson 32 saw how DDL/DCL enter the log atomically by
broadcast, and this lesson saw how the log is replicated to another cluster. Together they answer one question — <strong>when you fully model "writing" as "append to one reliable,
ordered, replayable log", how do reliability, consistency, recovery, and even cross-cluster replication all become "operations on that one log"</strong>. That is the design
philosophy of Milvus's streaming system, and one of the roots of what sets it apart from many vector stores.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Replicate the log, not state</strong>: cross-cluster sync = replicate the WAL + replay; ship "what happened" (CDC), not "what it is", reusing the existing WAL with almost no extra mechanism.</li>
    <li><strong>Data flow</strong>: primary WAL → CDC ChannelReplicator (<span class="mono">internal/cdc/replication</span>) → secondary Proxy (Replicate interceptor, keep original TimeTick) → secondary WAL → replay as usual.</li>
    <li><strong>Star topology + roles</strong>: one primary, many secondaries, one-way; the CDC controller coordinates roles; primary/secondary can switch — the basis of DR failover.</li>
    <li><strong>Uses</strong>: cross-region DR (promote standby), cross-region read replicas, smooth migration — all "let another cluster have the same data by replaying the same log".</li>
    <li><strong>Why clean</strong>: the WAL is the single source of truth + globally ordered + deterministic replay, so "replication" degenerates to "ship one more copy of the log"; a good abstraction heals the hardest problems.</li>
  </ul>
</div>
""",
}
