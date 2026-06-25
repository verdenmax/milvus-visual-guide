"""Content for Part 12 (Design themes, synthesis). Lessons 51-56.

Bilingual {"zh","en"} dicts mirroring part1-11. Unlike the earlier
module-by-module lessons, these are cross-cutting capstone chapters: each one
takes a single design goal ("why is it built this way") and shows what every
module contributes toward it, and why the goal matters. They synthesize and
cross-reference the existing 50 lessons rather than re-explaining them:

  L51 log-as-data            L52 query-while-write consistency
  L53 storage-compute split  L54 scale-to-billions
  L55 two-language split     L56 failure-as-default
"""


LESSON_51 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
到这里，Milvus 的每个零件你都见过了：Proxy、协调者、DataNode、QueryNode、segcore……但把它们拼成一台机器的，
不是某个零件，而是几条<strong>贯穿全局的设计主线</strong>。这一部分就来讲这些"为什么"。第一条，也是最根本的一条：<strong>日志即数据</strong>。</p>

<div class="card analogy"><div class="tag">🍜 打个比方</div>
<p>想象一家很忙的面馆：所有点单都<strong>先记在一卷不断变长的流水纸带上</strong>（这就是日志）。后厨的备餐板、客人的小票、当天账本——
全都是<strong>照着这卷纸带誊出来的副本</strong>。纸带才是唯一的真相：只要它还在，烧坏了备餐板、丢了小票，都能照着它重新誊一遍。
Milvus 对待数据，就是这家面馆对待那卷纸带——<strong>先把事情记进日志，其余一切都是日志的副本</strong>。</p></div>

<h2>目标：为什么"日志即数据"是地基</h2>
<p>传统数据库的直觉是"<strong>写入就是去改那张表</strong>"：插一行就直接落进段里、改进索引里。但 Milvus 反过来——<strong>写入的第一动作，
是往一条只能在末尾追加的日志（WAL，Write-Ahead Log）里记一笔</strong>，记上了就算成功返回。段、索引、副本这些"看得见的数据形态"，
全都是<strong>事后从日志里物化出来的派生品</strong>。为什么要这么拧巴？因为如果"写"和"查"共用同一份要随时改的结构，你就被迫在
"<strong>写得快</strong>"和"<strong>查得快</strong>"之间二选一：要查得快就得维护精巧的索引，可那让写变慢；要写得快就别动索引，
可那让查变慢。把日志单独拎出来当真相，这对矛盾就解开了——写只管飞快地追加，查用的段和索引在后台慢慢物化，<strong>互不拖累</strong>。
更关键的是<strong>崩溃恢复</strong>：进程随时可能挂，如果内存里改了一半的段直接没了，数据就丢了；而有了顺序日志，"恢复"不过是
<strong>从上次记号处把日志再重放一遍</strong>，丢不了任何一笔已经记上的写入。</p>

<p>不妨把两种世界观摆在一起看：传统数据库把"表"当主角、日志当保险，改表是<strong>同步</strong>的、索引必须当场更新，所以高并发写入要抢锁、要等索引；
Milvus 把"日志"当主角、段当真相的快照，写入只是<strong>无锁地往日志尾巴排队</strong>，段和索引在另一条时间线上慢慢生成。
正是这个视角的对调，让 Milvus 能把"每秒几十万条写入"和"亿级向量毫秒检索"这两件看似打架的事同时做到。
再举个具体场景：一个 DataNode 正把内存里的 growing 段往对象存储刷，刷到一半进程崩了。在"改表即写入"的世界里，这半个段可能就是一堆损坏的脏数据；
而在"日志即数据"的世界里，这无所谓——那段数据本来就还在 WAL 里躺着，接手的节点从检查点重放，缺的部分自然补齐，崩溃前后的世界完全一致。
<strong>崩溃不再是灾难，只是"从记号处再读一遍"</strong>。</p>

<div class="card macro"><div class="tag">🗺️ 大图景</div>
<p>把整套系统想成"<strong>一条主干 + 若干派生</strong>"：WAL 是主干（唯一事实），段/binlog、索引、备集群都是<strong>挂在主干上的派生视图</strong>。
前面学过的每个模块，其实都在围着这条主干做一件事——要么<strong>往日志里写</strong>（Proxy），要么<strong>从日志里读出来物化</strong>
（DataNode、QueryNode、复制器）。看懂了这条主干，你就看懂了 Milvus 的写入路径、流式系统、复制为什么都长成那样。</p></div>

<div class="flow">
  <div class="node hl"><div class="nt">Proxy</div><div class="nd">追加写入</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">WAL · 唯一事实</div><div class="nd">顺序追加 · 盖 TimeTick</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">DataNode</div><div class="nd">落段 / binlog</div></div>
  <div class="node"><div class="nt">QueryNode</div><div class="nd">消费尾巴 · 可查</div></div>
  <div class="node"><div class="nt">Replicator</div><div class="nd">重放到备集群</div></div>
</div>

<h2>写入侧：把"成功"定义为"已写进日志"</h2>
<p>一次插入到了 Proxy，它做完校验、补主键、按主键哈希到分片之后，<strong>核心动作只有一个</strong>：调用
<span class="inline">streaming.WAL().AppendMessages(...)</span> 把这批数据追加进 WAL（第 15、16 课）。WAL 由 StreamingNode 掌管，
写入时一个 <strong>TimeTick 拦截器</strong>会给它盖上一个<strong>单调递增的时间戳</strong>（第 16、31 课）——这个戳后面会成为全局定序、
MVCC 可见性、tsafe 等待的共同依据（第 30 课）。一旦日志记上，写入<strong>立刻算成功返回</strong>给客户端，根本不用等段落盘、不用等索引建好。
"为什么这就够了？"——因为日志才是真相，<strong>真相记下了，剩下的物化都可以慢慢来、且一定能补上</strong>。一个 PChannel 对应后端的一个 topic，
分片内 TimeTick 严格有序、分片间高度并行（第 31 课），于是"又快又有序"在这里同时成立。WAL 的后端还是可换的：单机默认 RocksMQ、
集群传统用 Pulsar、新实例官方推荐自研的 Woodpecker——但上层完全不用关心，它只依赖"<strong>追加、有序、可重放</strong>"这套抽象语义。</p>

<h2>物化侧：段与索引都是日志的"产物"</h2>
<p>日志记下了，"看得见的数据"是怎么冒出来的？靠<strong>消费日志的人</strong>。DataNode 跟在日志后面，把消息攒成内存里的 growing 段，
写满或超时就<strong>刷成不可变的 binlog 文件</strong>落进对象存储（第 17 课）；之后再由一个 DataNode 工作进程在段上<strong>构建 ANN 索引</strong>
（第 21、23 课）。注意这里的因果方向：<strong>不是"先有段再记日志"，而是"先有日志，段是日志重放出来的结果"</strong>。这也解释了一个常让新人困惑的点——
段和索引<strong>可以随时丢掉重建</strong>，因为它们不是真相，只是真相的一种物化形态；日志在，它们就能被重新誊出来。理解了这一点，
你也就明白为什么 Milvus 敢把 growing 段放在内存里、让多种数据形态异步地跟在日志后面：<strong>只要 WAL 还在，丢掉的都能从头重放回来</strong>。</p>

<p>把段和索引看成"派生"，还带来一个意外的灵活性：既然它们本就是从日志重新生成的，那么<strong>"换一种物化方式"几乎是免费的</strong>。
想给某字段换个索引类型？重建即可，原始向量一直好端端躺在 binlog 里。想升级索引引擎的格式？新段用新格式、老段保持兼容，
滚动升级期间服务不中断（第 23 课）。这种"<strong>真相不动、视图随便换</strong>"的自由度，是把数据和它的物化形态解耦之后才有的红利，
后面讲"存算分离"和"故障自愈"时你还会反复看到它。</p>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">真相</span><span class="name">WAL（append-only 日志）</span></div><div class="ld">唯一事实来源 · 顺序 · 可重放</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">派生</span><span class="name">段 / binlog</span></div><div class="ld">DataNode 重放日志物化而成（第 17 课）</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">派生</span><span class="name">索引</span></div><div class="ld">在段上构建，可随时重建（第 21/23 课）</div></div>
  <div class="layer l-app"><div class="lh"><span class="badge">派生</span><span class="name">备集群副本</span></div><div class="ld">重放同一份日志而来（第 33 课）</div></div>
</div>

<h2>消费侧：一份日志，多方按需重放</h2>
<p>日志最妙的地方在于：<strong>同一份日志，可以被很多人各自重放、各追各的进度</strong>，彼此不用直接打交道。QueryNode 的 delegator 就
<strong>盯着日志的尾巴</strong>消费，把最新写入的数据补进可查范围，于是"边写边查"成为可能（第 26 课）。连<strong>建表、改 schema 这类 DDL</strong>
也走同一条日志、共用同一条时间线，所以结构变更和数据变更天然有序（第 32 课）。<strong>跨集群复制</strong>更是直白——备集群只要
<strong>重放同一份日志</strong>就能得到一模一样的数据；复制拦截器还特意<strong>不重新盖戳</strong>、保留原始 TimeTick，两边顺序才严格一致（第 33 课）。
就连<strong>崩溃恢复</strong>也是这个套路：节点挂了，接手者<strong>从检查点（checkpoint）继续重放</strong>即可（第 31 课）。这就是
"<strong>一份日志、多方按需重放</strong>"——没有谁直接调用谁，大家只是各自盯着同一条不断变长的日志、按自己的节奏前进。
把"协作"简化成"共享一条只增不减的日志"，正是这套架构既复杂又有序的根源。</p>

<p>你可能会问：让 DataNode、QueryNode、复制器之间直接用 RPC 互相通知，不也能同步数据吗？能，但会非常脆。直接调用意味着
<strong>调用方要知道被调用方是谁、在哪、是否还活着</strong>，任何一方重启都可能丢消息、要补偿；而"共享一条日志"把这些耦合全部消解成一个简单约定——
<strong>你只管把自己消费到的位置（checkpoint）记好，挂了就从那儿接着读</strong>。想新增一类消费者（再来一个备集群、一条审计管道）？
不用改写入侧一行代码，它自己订阅日志、从头重放即可。这种"<strong>开放式扩展</strong>"正是日志架构最被低估的好处。</p>

<p>再往深一层：让"多方重放同一份日志"能得到<strong>一致结果</strong>的关键，是那个单调递增的 TimeTick。因为每条消息都带着严格递增的戳，
"重放"才是<strong>确定性</strong>的——同一段日志，无论谁来重放、重放多少次，结果都一模一样。这就是为什么前面反复强调"<strong>时间戳是缝合一切的那根线</strong>"：
它不仅给读一致性用，更是让整个"日志即数据"体系能自洽运转的底层保证；没有它，多个消费者各自重放就可能得到互相矛盾的世界。</p>

<div class="trace">
  <div class="tcap"><b>一条写入 @TimeTick=105</b>：进了日志就算成功，各消费者按自己的进度追</div>
  <div class="stations">
    <div class="stn"><h5>WAL</h5><div class="cellrow"><span class="vc hot">105 已落日志</span></div><div class="tlab">立即返回成功</div></div>
    <div class="stn"><h5>DataNode</h5><div class="cellrow"><span class="vc">已消费到 105</span></div><div class="tlab">落成段 / binlog</div></div>
    <div class="stn"><h5>QueryNode</h5><div class="cellrow"><span class="vc">已消费到 103</span></div><div class="tlab">tsafe=103，正在追</div></div>
    <div class="stn"><h5>备集群</h5><div class="cellrow"><span class="vc dim">已重放到 101</span></div><div class="tlab">复制有延迟</div></div>
  </div>
</div>

<h2>代价与取舍：主次反转</h2>
<p>天下没有免费的设计。把日志当真相，第一个代价是<strong>物化有延迟</strong>：写入虽然秒回，但它变成"可被索引高效检索的段"要等后台慢慢做——
所以才有 growing 段用暴力扫描兜住最新数据这一手（第 7 课）。第二个、也是更深的代价，是<strong>"主次反转"</strong>：在传统单机数据库里，
WAL 只是为了崩溃恢复而存在的<strong>副产品</strong>，表才是主角；而在 Milvus 里，<strong>WAL 反客为主成了唯一的真相，段和索引降格为派生数据</strong>。
这意味着<strong>日志本身成了整个系统最该被小心保护的东西</strong>——它要可靠存储、要能长期重放、要严格有序。</p>

<p>那么"守住一条日志"具体意味着什么？意味着 WAL 后端必须把"可靠存储"做到极致：消息一旦确认写入，断电、宕机都不能丢；
它还要支持<strong>长时间保留与从任意位置重放</strong>，否则一个落后很多的消费者（比如刚扩容上线的新节点）就追不上了；
它更要保证<strong>分片内严格有序</strong>，因为顺序一旦乱，重放出来的世界就和原来不一样了。这也是为什么 Milvus 在 WAL 后端上下了大功夫——
从复用成熟的 Pulsar/Kafka，到自研更贴合向量库需求的 Woodpecker——本质都是在把"那条必须守住的日志"守得更稳、更省、更好运维。</p>

<p>但换来的回报是巨大的：
写入与查询解耦（各自独立扩展、互不拖慢）、恢复退化为重放（简单且不丢数据）、众多消费者彼此独立（写入、落盘、查询、复制各跑各的）。
一句话：<strong>用"必须守住一条日志"的代价，换来了整个分布式系统的简单与自洽</strong>。这正是后面几课所有设计的共同底座。</p>

<div class="card key"><div class="tag">📌 本课要点</div>
<ul>
  <li><strong>日志即真相</strong>：WAL 是唯一事实来源，段 / 索引 / 副本都是从它物化出来的<strong>派生视图</strong>。</li>
  <li><strong>写 = 追加</strong>：Proxy 把数据追加进 WAL、盖上单调 TimeTick，<strong>记上即成功返回</strong>，不等落盘 / 建索引。</li>
  <li><strong>派生可重建</strong>：段和索引可随时丢弃重建，因为真相在日志里——这也是 Milvus 敢异步物化的底气。</li>
  <li><strong>一份日志多方重放</strong>：DataNode 落段、QueryNode 边写边查、复制器重放、崩溃恢复，各盯日志、各追各的进度。</li>
  <li><strong>取舍 = 主次反转</strong>：代价是物化延迟 + 必须守住日志；回报是<strong>写查解耦、恢复即重放、消费者互相独立</strong>。</li>
</ul></div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
By now you've met every part of Milvus: the Proxy, the coordinators, DataNode, QueryNode, segcore… But what fuses them into one
machine isn't any single part — it's a handful of <strong>design throughlines</strong>. This part is about those "whys". The first,
and most fundamental: <strong>log as data</strong>.</p>

<div class="card analogy"><div class="tag">🍜 An analogy</div>
<p>Picture a busy noodle shop: every order is <strong>first written onto one ever-growing ticket roll</strong> (that's the log). The
kitchen board, the customer receipts, the day's ledger — all are <strong>copies transcribed from that roll</strong>. The roll is the
one truth: as long as it survives, a scorched board or a lost receipt can simply be re-transcribed from it. Milvus treats data the way
this shop treats its ticket roll — <strong>record the event in the log first; everything else is a copy of the log</strong>.</p></div>

<h2>The goal: why "log as data" is the foundation</h2>
<p>A traditional database's instinct is "<strong>a write means editing the table</strong>": insert a row and land it straight into a
segment and an index. Milvus inverts this — <strong>a write's first act is to append one entry to an append-only log (WAL,
Write-Ahead Log)</strong>, and once it's logged the write returns as success. Segments, indexes, replicas — all the "visible forms of
data" — are <strong>derivatives materialized from the log afterward</strong>. Why so contorted? Because if "write" and "query" share
one structure that must be edited constantly, you're forced to choose between "<strong>writing fast</strong>" and "<strong>querying
fast</strong>": query-fast needs intricate indexes, which slow writes; write-fast leaves indexes alone, which slows queries. Pulling
the log out as the truth dissolves that tension — writes just append at top speed, while the segments and indexes used for queries
materialize lazily in the background, <strong>without dragging each other down</strong>. More crucial still is <strong>crash
recovery</strong>: a process can die at any moment, and a half-edited in-memory segment would vanish with the data; but with an ordered
log, "recovery" is merely <strong>replaying the log from the last mark</strong> — losing not a single already-logged write.</p>

<p>Set the two worldviews side by side: a traditional database casts the "table" as the star and the log as insurance — editing the
table is <strong>synchronous</strong> and the index must update on the spot, so high-concurrency writes contend for locks and wait on
indexing; Milvus casts the "log" as the star and segments as snapshots of the truth, so a write is just <strong>lock-free queuing at the
tail of the log</strong>, with segments and indexes generated lazily on another timeline. It is exactly this swap of perspective that lets
Milvus do "hundreds of thousands of writes per second" and "millisecond search over billions of vectors" at once. A concrete scene: a
DataNode is flushing an in-memory growing segment to object storage and the process dies halfway. In the "write = edit the table" world
that half-segment might be a pile of corrupt garbage; in the "log as data" world it doesn't matter — that data still sits in the WAL, the
successor replays from the checkpoint, the missing part fills back in, and the world before and after the crash is identical.
<strong>A crash is no longer a disaster, just "read again from the mark"</strong>.</p>

<div class="card macro"><div class="tag">🗺️ The big picture</div>
<p>Think of the whole system as "<strong>one trunk + several derivatives</strong>": the WAL is the trunk (the one truth), and
segments/binlogs, indexes, and the replica cluster are all <strong>derived views hanging off it</strong>. Every module you've studied
is doing one thing around this trunk — either <strong>writing into the log</strong> (the Proxy) or <strong>reading from it to
materialize something</strong> (DataNode, QueryNode, the replicator). Grasp this trunk and you grasp why Milvus's write path,
streaming system, and replication all look the way they do.</p></div>

<div class="flow">
  <div class="node hl"><div class="nt">Proxy</div><div class="nd">append write</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">WAL · the one truth</div><div class="nd">append in order · stamp TimeTick</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">DataNode</div><div class="nd">land segments / binlog</div></div>
  <div class="node"><div class="nt">QueryNode</div><div class="nd">consume the tail · queryable</div></div>
  <div class="node"><div class="nt">Replicator</div><div class="nd">replay into the backup</div></div>
</div>

<h2>Write side: define "success" as "written to the log"</h2>
<p>An insert reaches the Proxy; after it validates, fills the primary key, and hashes by PK into shards, its <strong>core action is
just one</strong>: call <span class="inline">streaming.WAL().AppendMessages(...)</span> to append the batch into the WAL (Lessons 15,
16). The WAL is owned by the StreamingNode, and on write a <strong>TimeTick interceptor</strong> stamps it with a <strong>monotonically
increasing timestamp</strong> (Lessons 16, 31) — a stamp that later becomes the shared basis for global ordering, MVCC visibility, and
tsafe waiting (Lesson 30). The instant it is logged, the write <strong>returns as success</strong> to the client, with no waiting for
segments to flush or indexes to build. "Why is that enough?" — because the log is the truth, and <strong>once the truth is recorded,
all the materialization can take its time and is guaranteed to catch up</strong>. One PChannel maps to one backend topic; within a
shard TimeTick is strictly ordered, across shards highly parallel (Lesson 31), so "fast and ordered" both hold at once. The WAL backend
is even swappable: RocksMQ by default for standalone, Pulsar traditionally for clusters, the in-house Woodpecker officially recommended
for new instances — yet the upper layers needn't care, depending only on the abstract semantics "<strong>append, ordered,
replayable</strong>".</p>

<h2>Materialize side: segments and indexes are "products" of the log</h2>
<p>The log is recorded — so how does "visible data" appear? Through <strong>those who consume the log</strong>. DataNode follows the log,
accumulating messages into in-memory growing segments and, when full or timed out, <strong>flushing them into immutable binlog
files</strong> in object storage (Lesson 17); later a DataNode worker <strong>builds the ANN index</strong> on a segment (Lessons 21,
23). Note the direction of causality here: <strong>it is not "segment first, then logged" but "log first, and the segment is the result
of replaying the log"</strong>. This also explains a point that often confuses newcomers — segments and indexes <strong>can be discarded
and rebuilt at any time</strong>, because they aren't the truth, only one materialized form of it; while the log survives, they can be
re-transcribed. Grasp this and you see why Milvus dares to keep growing segments in memory and let multiple data forms trail the log
asynchronously: <strong>as long as the WAL survives, anything dropped can be replayed back from scratch</strong>.</p>

<p>Seeing segments and indexes as "derived" also brings an unexpected flexibility: since they are regenerated from the log anyway,
<strong>"changing how you materialize" is almost free</strong>. Want a different index type on a field? Just rebuild — the raw vectors lie
safely in the binlogs the whole time. Want to upgrade the index-engine format? New segments use the new format while old ones stay
compatible, with no service interruption during the rolling upgrade (Lesson 23). This "<strong>truth stays put, views swap freely</strong>"
latitude is a dividend you get only after decoupling data from its materialized forms — you'll see it again when we cover storage-compute
separation and self-healing.</p>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">truth</span><span class="name">WAL (append-only log)</span></div><div class="ld">the one source of truth · ordered · replayable</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">derived</span><span class="name">segments / binlog</span></div><div class="ld">materialized by DataNode replaying the log (L17)</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">derived</span><span class="name">indexes</span></div><div class="ld">built on segments, rebuildable anytime (L21/L23)</div></div>
  <div class="layer l-app"><div class="lh"><span class="badge">derived</span><span class="name">replica cluster</span></div><div class="ld">arrived by replaying the same log (L33)</div></div>
</div>

<h2>Consume side: one log, many parties replaying on demand</h2>
<p>The loveliest thing about a log: <strong>the same log can be replayed by many parties, each at its own pace</strong>, without dealing
with one another directly. The QueryNode's delegator <strong>watches the tail of the log</strong>, folding the freshest writes into the
queryable range, which is what makes "query-while-you-write" possible (Lesson 26). Even <strong>DDL like create-collection or
schema-change</strong> rides the same log on the same timeline, so structural and data changes are naturally ordered (Lesson 32).
<strong>Cross-cluster replication</strong> is more direct still — the backup cluster only has to <strong>replay the same log</strong> to
hold identical data; the replicate interceptor even deliberately <strong>doesn't re-stamp</strong>, preserving the original TimeTick so
both sides' ordering stays strictly identical (Lesson 33). Even <strong>crash recovery</strong> is the same move: a node dies and its
successor simply <strong>resumes replaying from the checkpoint</strong> (Lesson 31). This is "<strong>one log, many parties replaying on
demand</strong>" — nobody calls anybody directly; each just watches the same ever-growing log and advances at its own rhythm. Reducing
"collaboration" to "sharing one append-only log" is the root reason this architecture can be both complex and orderly.</p>

<p>You might ask: couldn't DataNode, QueryNode, and the replicator just notify each other over RPC to stay in sync? They could, but it
would be brittle. A direct call means <strong>the caller must know who the callee is, where it is, and whether it's still alive</strong>; a
restart on either side can drop messages and demand compensation. "Sharing one log" dissolves all that coupling into one simple contract —
<strong>just record the position you've consumed to (your checkpoint), and on restart resume reading from there</strong>. Want to add a new
kind of consumer (another backup cluster, an audit pipeline)? Not one line of the write side changes; it subscribes to the log and replays
from the start on its own. This "<strong>open-ended extensibility</strong>" is the log architecture's most underrated benefit.</p>

<p>One level deeper: what lets "many parties replaying the same log" reach a <strong>consistent result</strong> is that monotonically
increasing TimeTick. Because every message carries a strictly increasing stamp, "replay" is <strong>deterministic</strong> — the same
stretch of log yields exactly the same result no matter who replays it or how many times. This is why we kept stressing that
"<strong>the timestamp is the thread that stitches everything together</strong>": it serves read consistency, yes, but it is also the
underlying guarantee that lets the whole "log as data" system stay self-consistent; without it, multiple consumers replaying independently
could reach mutually contradictory worlds.</p>

<div class="trace">
  <div class="tcap"><b>one write @TimeTick=105</b>: logged = success; each consumer catches up at its own pace</div>
  <div class="stations">
    <div class="stn"><h5>WAL</h5><div class="cellrow"><span class="vc hot">105 logged</span></div><div class="tlab">returns success now</div></div>
    <div class="stn"><h5>DataNode</h5><div class="cellrow"><span class="vc">consumed to 105</span></div><div class="tlab">lands segment / binlog</div></div>
    <div class="stn"><h5>QueryNode</h5><div class="cellrow"><span class="vc">consumed to 103</span></div><div class="tlab">tsafe=103, catching up</div></div>
    <div class="stn"><h5>backup</h5><div class="cellrow"><span class="vc dim">replayed to 101</span></div><div class="tlab">replication lag</div></div>
  </div>
</div>

<h2>The payoff and the tradeoff: inversion of primary and secondary</h2>
<p>No design is free. Treating the log as truth costs you, first, <strong>materialization latency</strong>: the write returns instantly,
but its turning into "a segment an index can search efficiently" waits on background work — which is exactly why growing segments use
brute force to cover the freshest data (Lesson 7). The second, deeper cost is the <strong>"inversion of primary and secondary"</strong>:
in a traditional single-node database the WAL is a <strong>by-product</strong> that exists only for crash recovery, with the table as the
star; in Milvus, <strong>the WAL takes over as the one truth, and segments and indexes are demoted to derived data</strong>. That means
<strong>the log itself becomes the thing the whole system must most carefully protect</strong> — it must be stored reliably, replayable
long-term, strictly ordered.</p>

<p>So what does "guarding one log" concretely mean? It means the WAL backend must take "reliable storage" to the limit: once a message is
acknowledged, a power cut or a crash must not lose it; it must support <strong>long retention and replay from any position</strong>, or a
far-behind consumer (say a freshly scaled-out node) could never catch up; and it must guarantee <strong>strict ordering within a
shard</strong>, because once order scrambles, the replayed world differs from the original. This is why Milvus invests so heavily in WAL
backends — from reusing mature Pulsar/Kafka to building the vector-DB-tailored Woodpecker — all of it about guarding "that one log you must
guard" more durably, cheaply, and operably.</p>

<p>But the reward is enormous: write and query are decoupled (each scales independently, neither drags the
other), recovery degenerates into replay (simple and lossless), and the many consumers are independent (writing, flushing, querying,
replicating each run on their own). In one line: <strong>at the cost of "you must guard one log", you buy the simplicity and
self-consistency of the entire distributed system</strong>. This is the shared bedrock of every design in the lessons that follow.</p>

<div class="card key"><div class="tag">📌 Key points</div>
<ul>
  <li><strong>Log is the truth</strong>: the WAL is the one source of truth; segments / indexes / replicas are <strong>derived views</strong> materialized from it.</li>
  <li><strong>Write = append</strong>: the Proxy appends data into the WAL, stamps a monotonic TimeTick, and <strong>returns success once logged</strong> — no waiting on flush / index.</li>
  <li><strong>Derivatives are rebuildable</strong>: segments and indexes can be discarded and rebuilt anytime because the truth is in the log — this is what lets Milvus materialize asynchronously.</li>
  <li><strong>One log, many replayers</strong>: DataNode lands segments, QueryNode queries-while-writing, the replicator replays, crash recovery resumes — each watches the log at its own pace.</li>
  <li><strong>Tradeoff = primary/secondary inversion</strong>: the cost is materialization latency + having to guard the log; the reward is <strong>write/query decoupling, recovery-as-replay, and independent consumers</strong>.</li>
</ul></div>
""",
}
