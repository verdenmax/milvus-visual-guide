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


LESSON_52 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课我们看到，写入只是飞快地追加进日志、立刻返回。可这立刻带来一个尖锐的问题：我刚写完一条数据，转身就去搜它，能搜到吗？
在一个写入异步流过日志、查询又分散在一堆节点上的分布式系统里，"<strong>边写边查还得保证对</strong>"绝不是理所当然的。这一课讲的就是 Milvus 怎么把它做到。</p>

<div class="card analogy"><div class="tag">📚 打个比方</div>
<p>想象一座图书馆，每本书入库都贴一张<strong>带时间戳的入库单</strong>。你来查书时，不是问"现在书架上有什么"，而是问"<strong>给我看截至下午 3:00 的书架</strong>"。
服务台会一直等到<strong>每一排书架都把 3:00 之前的入库单都归档完</strong>，才把结果给你——于是你看到的是一个干净、自洽、属于"3:00 那一刻"的快照：
既不会漏掉 3:00 前入库的书，也不会被 3:01 才到的书搅乱。Milvus 的一致性，就是这套"<strong>按时间戳看快照</strong>"的机制。</p></div>

<h2>目标：边写边查，还得是对的</h2>
<p>用户的期待很朴素：上传一张图，马上就能搜到它（read-your-writes）；或者反过来，做大规模离线分析时，差几条最新数据无所谓、但要快。
难点在于，Milvus 的写入是<strong>异步流过 WAL</strong> 的——你写成功的那一刻，数据可能还没被某个 QueryNode 消费到。如果天真地"有什么查什么"，
就会冒出两类错误：要么<strong>读到的不是一个时间点的一致快照</strong>（这条数据的插入看到了、但同一批的删除还没到，结果自相矛盾）；
要么<strong>读不到自己刚写的</strong>（明明写成功了却搜不到，体验崩塌）。要同时避免这两类错误、又不能让查询无脑地死等，就需要一套精巧的时间戳机制。
说白了，这一课要回答的是：在"日志即数据、写入异步物化"的前提下，<strong>怎么让一次读看到一个既新鲜又自洽的世界</strong>。</p>

<p>举个最常见的崩塌场景：用户上传了一张商品图，前端立刻拿这张图的向量去检索"相似商品"，期待至少能看到自己刚传的这张。
如果这次检索恰好落在一个<strong>还没消费到这条写入</strong>的 QueryNode 上、又用了"有什么查什么"的策略，结果里就是没有它——用户一脸困惑："我明明刚传成功了？"。
同样的道理也会反过来坑你：一条数据先被插入、又被同一批操作删除，如果你读到了插入却没读到删除，就会看到一条"本该消失"的脏数据。
这两种错误的共同根源，都是"<strong>没有一个统一的『此刻』</strong>"——而时间戳，正是用来定义这个"此刻"的。</p>

<div class="card macro"><div class="tag">🗺️ 大图景</div>
<p>把一致性拆成三步看：① <strong>盖戳</strong>——RootCoord 的 TSO 给每一次写和每一次读发一个全局单调时间戳；
② <strong>定级</strong>——Proxy 按你选的一致性级别，算出这次查询"要看截至哪一刻"的保证时间戳 Tg；
③ <strong>等齐再过滤</strong>——QueryNode 等到自己消费的进度 tsafe 追上 Tg，再用 MVCC 按 Tg 过滤出可见行。
三步合起来，才有了那个"<strong>自洽、且新鲜度可选</strong>"的快照。</p></div>

<div class="timeline">
  <div class="lane"><div class="lane-label">写入流</div><div class="tslot">w@98</div><div class="tslot">w@100</div><div class="tslot now">w@103</div></div>
  <div class="lane"><div class="lane-label">读 Tg=100</div><div class="tslot span">tsafe=98 &lt; 100：挂起等待</div><div class="tslot now">tsafe≥100：按 MVCC 作答</div></div>
</div>

<h2>第一步：给万物盖一个统一的时间戳</h2>
<p>一切的起点是<strong>时间</strong>。RootCoord 维护着一个全局、<strong>单调递增、绝不回退</strong>的时间戳源，叫 <strong>TSO</strong>（Timestamp Oracle，第 11、30 课）。
无论是一次写入要被定序，还是一次读要确定"看哪一刻"，都向它要一个戳。为什么不让各节点用自己的本地时钟？因为机器时钟会漂移、会不同步，靠它定序迟早乱套；
而 TSO 从<strong>单一源头</strong>发号，就保证了全集群对"先后"有<strong>唯一、一致</strong>的理解。写入的戳被打进 WAL（成为 TimeTick，第 16 课），
读的戳则用来圈定可见范围——<strong>同一把钟，同时管住了写的顺序和读的视野</strong>。这也是上一课"日志即数据"能成立的隐形前提：没有统一时钟，多方重放就对不齐。</p>

<p>这把全局时钟在实现上是一个<strong>混合逻辑时钟</strong>：一个 64 位整数，高位是物理时间（毫秒），低位是逻辑计数器。物理位让时间戳大致对应真实时间、
便于人理解和做 TTL 之类的判断，逻辑位则保证<strong>同一毫秒内涌进来的大量请求也能被严格区分先后</strong>、绝不撞车。RootCoord 还会把已分配的时间戳
<strong>批量预留并持久化</strong>，这样即便它重启，新发的戳也一定比重启前的大——<strong>单调性在故障面前也不破</strong>。正因为有这把"既贴近真实时间、又绝对单调"的钟，
后面的定序、可见性、等待才有了一把共同的标尺。</p>

<h2>第二步：让"看多新"成为一个可选的旋钮</h2>
<p>拿到时间这把尺之后，Proxy 在查询的 PreExecute 阶段，会按你指定的<strong>一致性级别</strong>推导出一个<strong>保证时间戳 Tg</strong>
（<span class="inline">parseGuaranteeTsFromConsistency</span>，第 25、30 课）。它本质是一个旋钮：<strong>Strong</strong> 把 Tg 设成最新的 tMax，看得最全，但可能要等；
<strong>Bounded</strong> 把 Tg 往回挪一点（tMax 减一个 gracefulTime），用"容忍几秒陈旧"换"几乎不用等"，所以是很多场景的默认；
<strong>Session</strong> 保证至少能读到本会话刚写的；<strong>Eventually</strong> 把 Tg 设到极小，从不等待、秒回，代价是可能看不到最新几条；
<strong>Customized</strong> 则让你指定任意时刻，做"时间旅行"查询。关键在于：<strong>这个选择权交在你手里</strong>——Milvus 不替你在"新鲜"和"快"之间做决定。</p>

<p>把这几档对到真实场景就很清楚了：刚写完要立刻查到自己写的（上传后即搜），用 Session 或 Strong；对一致性极敏感、宁可慢也要最新（金融、审计），用 Strong；
绝大多数高并发检索、推荐、RAG，差几条无伤大雅但要低延迟高吞吐，用 Bounded（默认）；只要"大概新"、极致求快（离线分析、海量召回），用 Eventually；
要看某个历史时刻的快照（时间旅行、回溯排查），用 Customized 指定 ts。还要记住：<strong>同一个集合、不同查询完全可以用不同级别</strong>——
级别是查询粒度的选择，不是集合的全局属性，这给了你按业务逐查调优的空间。</p>

<div class="cellgroup">
  <div class="cg-cap"><b>MVCC：用 Tg=100 决定谁可见</b>（可见 ⇔ 插入 ts ≤ 100 且其后无墓碑 ≤ 100）</div>
  <div class="cells"><span class="lab">行A</span><span class="cell q">插入@80</span><span class="sep">→</span><span class="cell q">可见 ✓</span></div>
  <div class="cells"><span class="lab">行B</span><span class="cell">插入@80</span><span class="cell dim">删除@95</span><span class="sep">→</span><span class="cell dim">不可见（墓碑 ≤ 100）</span></div>
  <div class="cells"><span class="lab">行C</span><span class="cell">插入@120</span><span class="sep">→</span><span class="cell dim">不可见（120 &gt; 100）</span></div>
</div>

<h2>第三步：等数据到齐，再按时间戳过滤</h2>
<p>Tg 定好了，怎么保证"截至 Tg 的写入真的都到了 QueryNode 手里"？靠 <strong>tsafe</strong>（服务时间水位）：每个 QueryNode 记着"我已经把 WAL 消费并应用到了哪个 TimeTick"，
节点每消费一段日志，tsafe 就往前推（第 26、30 课）。读请求带着 Tg 进来，节点先比：<strong>tsafe ≥ Tg 就立刻搜，tsafe &lt; Tg 就挂起等待</strong>，
直到追上（或超时）——"保证时间戳"里"保证"二字的由来正在于此。等到数据齐了，最后一步是 segcore 按 <strong>MVCC</strong> 过滤：一行可见，当且仅当它的
<strong>插入 ts ≤ Tg 且其后没有 ts ≤ Tg 的删除墓碑</strong>（第 20、30 课）。删除在这里不是真删，而是记一个带时间戳的墓碑；这样不同 Tg 的读，
各自看到属于自己那一刻的版本，读和写、读和读之间互不阻塞，结果还自洽。新写入之所以能"边写边查"，是因为它先进了 growing 段、又被 tsafe 机制纳入可见——
可不可见、要不要等，全看你选的级别（第 7 课）。</p>

<p>这里藏着一个很优雅的设计：因为可见性完全由"时间戳和 Tg 的比较"决定，读<strong>根本不需要对数据加锁</strong>。传统数据库里"读要不要阻塞写、写要不要阻塞读"
是个老大难，要靠各种锁和隔离级别来回权衡；而 Milvus 把它化简成一道算术题——每一行带着自己的插入/删除时间戳，每一次读带着自己的 Tg，谁可见谁不可见一比便知。
新写入不断进来、老版本依然按各自的 Tg 被看见，<strong>读写互不打扰、并发天然安全</strong>。这正是"快照隔离（snapshot isolation）"的精髓，
也是 Milvus 能在高并发下既快又对的底气。</p>

<p>顺带说清一个常被误解的点：在这套机制里，<strong>"删除"从来不是把数据从段里抠出来</strong>，而是追加一条带时间戳的墓碑（第 20 课）；
"更新（upsert）"则是"删旧 + 插新"两步、各带各的时间戳。为什么要这么绕？因为段是不可变的、又要支持"按任意 Tg 看历史快照"，
所以唯一干净的做法就是<strong>只追加、用时间戳分版本</strong>，把"哪个版本该被这次读看见"完全交给 MVCC 去算。这也解释了为什么大量删除/更新之后需要
compaction（第 19 课）把墓碑和被覆盖的旧版本真正清理掉——平时它们只是"逻辑上不可见"，物理上还躺在段里。</p>

<div class="flow">
  <div class="node"><div class="nt">TSO @ RootCoord</div><div class="nd">发全局单调戳</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">Proxy</div><div class="nd">按级别算 Tg</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">QueryNode</div><div class="nd">等 tsafe ≥ Tg</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">segcore</div><div class="nd">按 MVCC 过滤(Tg)</div></div>
</div>

<h2>代价与取舍：新鲜 vs 延迟</h2>
<p>这套机制的代价，全压在一个旋钮上：<strong>越新鲜，可能越要等</strong>。Strong 把 Tg 顶到最新，所以在写入洪峰、或某个节点消费滞后时，
读会被迫等 tsafe 追上去——延迟可能抖升；而且 tsafe 是<strong>按 vchannel（分片）维度</strong>推进的，一次强一致读要等它涉及的<strong>所有</strong>分片都追上，
任一分片卡住都会拖慢整次查询。反过来，Bounded 把 Tg 往回挪一点，就极大概率"一来就满足"、几乎不用等。所以实践里的智慧是：
<strong>先想清楚"这次查询能容忍多旧"，再倒推该选哪一档</strong>——绝大多数检索/推荐/RAG 用 Bounded 就好，真要"写完即查"才上 Session 或 Strong。
把一致性级别理解成"<strong>花多少延迟买多少新鲜</strong>"的旋钮，你就拿到了在正确性与性能之间精细权衡的方向盘。这也呼应第一课说的"边写边查"：
能做到，是因为时间戳把"写得飞快"和"读得正确"缝在了同一条时间线上。</p>

<p>这套取舍还给了你一个排查线上问题的抓手：当你看到"某些强一致查询偶发变慢"，十有八九对应着"<strong>写入积压</strong>"或"<strong>某个分片所在节点消费滞后</strong>"——
因为 Strong 读必须等所有相关分片的 tsafe 都追上 Tg，任何一个分片卡住都会现形为查询延迟。把"查询慢"和"消费滞后"对应起来，往往是同一件事的两面。
理解了这一层，你在选级别、定 SLA、排查抖动时，就不再是凭感觉，而是清楚每一步在为"新鲜度"付什么"延迟"。这也是把一致性从"玄学"变成"可度量、可调优"的关键一步。</p>

<p>说到底，这一课和上一课讲的是同一枚硬币的两面：上一课用日志把"写"做到了飞快，这一课用时间戳把"读"做到了既新鲜又正确，
而它们共享同一个真相——<strong>那个从 TSO 发出、贯穿写入与读取的单调时间戳</strong>。下次你在 SDK 里写下 consistency_level 这个参数时，
希望你眼前能浮现这整条链路：TSO 发戳、Proxy 定 Tg、QueryNode 等 tsafe、segcore 按 MVCC 过滤——一个看似简单的参数背后，
是一整套让"分布式、边写边查、还要正确"同时成立的精巧设计。</p>

<div class="card key"><div class="tag">📌 本课要点</div>
<ul>
  <li><strong>三步走</strong>：TSO 盖戳 → Proxy 按级别算 Tg → QueryNode 等 tsafe ≥ Tg、segcore 按 MVCC 过滤。</li>
  <li><strong>TSO</strong>：RootCoord 的全局单调时钟，<strong>同时</strong>管住写的顺序和读的视野，避免本地时钟漂移导致定序错乱。</li>
  <li><strong>Tg 是旋钮</strong>：Strong / Bounded / Session / Eventually / Customized = 新鲜度 ↔ 延迟，选择权交在你手里。</li>
  <li><strong>MVCC + 墓碑</strong>：可见 ⇔ 插入 ts ≤ Tg 且无墓碑 ≤ Tg；读写、读读互不阻塞，结果自洽。</li>
  <li><strong>取舍</strong>：越新鲜越可能等（且要按分片维度等齐）；按"能容忍多旧"反推级别，别无脑求 Strong。</li>
</ul></div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson we saw a write just append to the log and return instantly. But that raises a sharp question at once: I just wrote a row, then
turn around to search for it — will I find it? In a distributed system where writes flow asynchronously through a log and queries are spread
across many nodes, "<strong>query-while-you-write, and still be correct</strong>" is anything but automatic. This lesson is how Milvus pulls it off.</p>

<div class="card analogy"><div class="tag">📚 An analogy</div>
<p>Picture a library where every book gets a <strong>timestamped check-in slip</strong> on arrival. When you query, you don't ask "what's on the
shelves now" but "<strong>show me the shelves as of 3:00pm</strong>". The desk waits until <strong>every aisle has filed all its pre-3:00
slips</strong>, then hands you the result — so you see a clean, self-consistent snapshot belonging to "the 3:00 instant": it misses no book
checked in before 3:00 and isn't muddled by one that arrived at 3:01. Milvus's consistency is exactly this "<strong>view a snapshot by
timestamp</strong>" mechanism.</p></div>

<h2>The goal: query-while-write, and still correct</h2>
<p>Users' expectation is plain: upload an image and immediately search it (read-your-writes); or conversely, for large offline analytics,
missing a few latest rows is fine but it must be fast. The difficulty is that Milvus's writes flow <strong>asynchronously through the
WAL</strong> — at the instant your write succeeds, the data may not yet be consumed by some QueryNode. Naïvely "search whatever's there" yields
two kinds of error: either <strong>what you read isn't a consistent snapshot of one instant</strong> (you see a row's insert but not the
same batch's delete, so the result self-contradicts), or you <strong>can't read your own write</strong> (it succeeded yet isn't searchable —
the experience collapses). Avoiding both, while not letting queries blindly hang forever, needs a delicate timestamp machinery. In short,
this lesson answers: under "log as data, writes materialized asynchronously", <strong>how does one read see a world that is both fresh and
self-consistent</strong>.</p>

<p>Take the commonest collapse: a user uploads a product photo, and the front end immediately searches "similar products" with that photo's
vector, expecting to at least see the one just uploaded. If that search happens to land on a QueryNode that <strong>hasn't yet consumed this
write</strong> and uses a "search whatever's there" policy, the result simply won't include it — and the user is baffled: "but I just uploaded
it successfully?". The same logic bites the other way: a row is inserted then deleted by the same batch; if you read the insert but not the
delete, you see a "should-be-gone" dirty row. Both errors share one root cause — <strong>there is no single agreed "now"</strong> — and the
timestamp is precisely what defines that "now".</p>

<div class="card macro"><div class="tag">🗺️ The big picture</div>
<p>See consistency as three steps: ① <strong>stamp</strong> — RootCoord's TSO hands every write and every read a global monotonic timestamp;
② <strong>set the level</strong> — the Proxy, from the consistency level you chose, derives a guarantee timestamp Tg, "as of which instant this
query should see"; ③ <strong>wait then filter</strong> — the QueryNode waits until its own consumption progress tsafe catches up to Tg, then
uses MVCC to filter visible rows by Tg. The three together produce that "<strong>self-consistent, freshness-of-your-choice</strong>"
snapshot.</p></div>

<div class="timeline">
  <div class="lane"><div class="lane-label">write stream</div><div class="tslot">w@98</div><div class="tslot">w@100</div><div class="tslot now">w@103</div></div>
  <div class="lane"><div class="lane-label">read Tg=100</div><div class="tslot span">tsafe=98 &lt; 100: suspend &amp; wait</div><div class="tslot now">tsafe≥100: answer by MVCC</div></div>
</div>

<h2>Step 1: stamp everything with one shared timestamp</h2>
<p>It all starts with <strong>time</strong>. RootCoord maintains a global, <strong>monotonically increasing, never-rewinding</strong> timestamp
source called the <strong>TSO</strong> (Timestamp Oracle, Lessons 11, 30). Whether a write needs ordering or a read needs to fix "which instant",
both ask it for a stamp. Why not let each node use its own local clock? Because machine clocks drift and desync; ordering by them scrambles
sooner or later. The TSO issuing from a <strong>single source</strong> guarantees the whole cluster a <strong>single, consistent</strong>
understanding of "before and after". A write's stamp is driven into the WAL (becoming TimeTick, Lesson 16); a read's stamp delimits its visible
range — <strong>one clock governing both write order and read horizon</strong>. This is also the hidden premise that made last lesson's "log as
data" hold: without a shared clock, many replayers can't line up.</p>

<p>This global clock is implemented as a <strong>hybrid logical clock</strong>: a 64-bit integer whose high bits are physical time
(milliseconds) and low bits a logical counter. The physical bits make the timestamp roughly correspond to real time — handy for humans and
for judgments like TTL — while the logical bits ensure that <strong>even a flood of requests arriving within the same millisecond are
strictly ordered</strong>, never colliding. RootCoord also <strong>pre-reserves and persists</strong> allocated timestamps in batches, so
even after a restart the stamps it issues are guaranteed larger than before — <strong>monotonicity survives failure</strong>. It is this
"close to real time yet absolutely monotonic" clock that gives ordering, visibility, and waiting a shared ruler.</p>

<h2>Step 2: make "how fresh" a dial you can turn</h2>
<p>Holding this ruler of time, the Proxy in a query's PreExecute derives a <strong>guarantee timestamp Tg</strong> from the
<strong>consistency level</strong> you specify (<span class="inline">parseGuaranteeTsFromConsistency</span>, Lessons 25, 30). It is essentially a
dial: <strong>Strong</strong> sets Tg to the latest tMax — sees the most, but may wait; <strong>Bounded</strong> nudges Tg back a little (tMax
minus a gracefulTime), trading "tolerate a few seconds of staleness" for "almost never wait", which is why it's a common default;
<strong>Session</strong> guarantees you at least read this session's own writes; <strong>Eventually</strong> sets Tg tiny, never waits, returns
instantly, at the cost of maybe missing the last few; <strong>Customized</strong> lets you name any instant for a "time-travel" query. The crux:
<strong>this choice is in your hands</strong> — Milvus won't decide "fresh vs fast" for you.</p>

<p>Map the tiers onto real scenarios and it's clear: need to read your own write immediately (search right after upload) — Session or
Strong; extremely consistency-sensitive, slower-but-latest (finance, audit) — Strong; the vast majority of high-concurrency search,
recommendation, RAG, where missing a few rows is harmless but low latency and high throughput matter — Bounded (the default); only "roughly
fresh", chasing raw speed (offline analytics, massive recall) — Eventually; viewing a snapshot at some historical instant (time travel,
retrospective debugging) — Customized with an explicit ts. And remember: <strong>the same collection can use different levels for different
queries</strong> — the level is a per-query choice, not a global property of the collection, giving you room to tune query by query.</p>

<div class="cellgroup">
  <div class="cg-cap"><b>MVCC: Tg=100 decides who is visible</b> (visible &hArr; insert ts ≤ 100 and no tombstone ≤ 100 after it)</div>
  <div class="cells"><span class="lab">row A</span><span class="cell q">insert@80</span><span class="sep">→</span><span class="cell q">visible ✓</span></div>
  <div class="cells"><span class="lab">row B</span><span class="cell">insert@80</span><span class="cell dim">delete@95</span><span class="sep">→</span><span class="cell dim">invisible (tombstone ≤ 100)</span></div>
  <div class="cells"><span class="lab">row C</span><span class="cell">insert@120</span><span class="sep">→</span><span class="cell dim">invisible (120 &gt; 100)</span></div>
</div>

<h2>Step 3: wait for the data, then filter by timestamp</h2>
<p>Tg is set — how do we guarantee "the writes up to Tg have actually reached the QueryNode"? Via <strong>tsafe</strong> (the served watermark):
each QueryNode tracks "to which TimeTick I have consumed and applied the WAL", and each chunk of log it consumes pushes tsafe forward (Lessons 26,
30). A read arrives with Tg, and the node compares: <strong>if tsafe ≥ Tg, search now; if tsafe &lt; Tg, suspend and wait</strong> until it catches
up (or times out) — that is the source of the word "guarantee". Once the data is present, the last step is segcore filtering by
<strong>MVCC</strong>: a row is visible iff its <strong>insert ts ≤ Tg and no delete tombstone with ts ≤ Tg comes after</strong> (Lessons 20, 30).
A delete here isn't a real removal but a timestamped tombstone; this way reads at different Tg each see the version belonging to their instant,
reads/writes and reads/reads don't block each other, and results stay self-consistent. A fresh write is "query-while-write"-able because it first
enters a growing segment and is then folded into visibility by tsafe — whether you see it, and whether you wait, is set by the level you choose
(Lesson 7).</p>

<p>A very elegant design hides here: because visibility is decided entirely by "comparing timestamps against Tg", a read <strong>needs no
lock on the data at all</strong>. In traditional databases "should reads block writes, should writes block reads" is a perennial headache
balanced via locks and isolation levels; Milvus reduces it to an arithmetic check — each row carries its own insert/delete timestamps, each
read carries its own Tg, and who is visible is settled by comparison. Fresh writes keep flowing in while old versions stay visible at their
own Tg, so <strong>reads and writes never disturb each other and concurrency is safe by construction</strong>. This is the essence of
"snapshot isolation", and the reason Milvus can be both fast and correct under heavy concurrency.</p>

<p>One often-misunderstood point, for clarity: in this mechanism a <strong>"delete" never gouges data out of a segment</strong> but appends a
timestamped tombstone (Lesson 20); an "upsert" is "delete-old + insert-new", each with its own timestamp. Why so roundabout? Because segments
are immutable and must support "view a historical snapshot at any Tg", so the only clean approach is to <strong>append only and version by
timestamp</strong>, leaving "which version this read should see" entirely to MVCC. This also explains why heavy deletes/updates need compaction
(Lesson 19) to truly purge tombstones and overwritten old versions — ordinarily they're merely "logically invisible" while still physically
sitting in the segment.</p>

<div class="flow">
  <div class="node"><div class="nt">TSO @ RootCoord</div><div class="nd">issue global monotonic stamps</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">Proxy</div><div class="nd">derive Tg by level</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">QueryNode</div><div class="nd">wait tsafe ≥ Tg</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">segcore</div><div class="nd">filter by MVCC(Tg)</div></div>
</div>

<h2>The payoff and the tradeoff: freshness vs latency</h2>
<p>The cost of all this rests on one dial: <strong>the fresher you want it, the more you may wait</strong>. Strong pins Tg to the latest, so under
a write surge or a node lagging in consumption, a read is forced to wait for tsafe to catch up — latency can spike; and tsafe advances <strong>per
vchannel (shard)</strong>, so one strong-consistency read waits for <strong>every</strong> shard it touches to catch up, and any stuck shard
slows the whole query. Conversely, Bounded nudges Tg back a little and very often "satisfies on arrival", barely waiting. So the practical wisdom
is: <strong>first decide "how stale this query can tolerate", then work backward to the level</strong> — the vast majority of search /
recommendation / RAG do fine on Bounded; reach for Session or Strong only when you truly need "write then immediately read". Read the consistency
level as a "<strong>how much latency you spend to buy how much freshness</strong>" dial and you hold the steering wheel for trading correctness
against performance. This echoes Lesson 1's "query while you write": it works because the timestamp stitches "write blazingly fast" and "read
correctly" onto the same timeline.</p>

<p>This tradeoff also hands you a handle for diagnosing production: when you see "some strong-consistency queries occasionally slow down",
nine times out of ten it maps to a <strong>write backlog</strong> or <strong>a node holding some shard lagging in consumption</strong> —
because a Strong read must wait for every involved shard's tsafe to reach Tg, and any stuck shard surfaces as query latency. Mapping "slow
query" onto "lagging consumption" is usually two sides of one thing. Grasp this layer and choosing levels, setting SLAs, and chasing jitter
stop being gut feel and become a clear accounting of what "latency" each step pays for "freshness". It's the key step that turns consistency
from "dark art" into "measurable and tunable".</p>

<p>Ultimately, this lesson and the last are two faces of one coin: last lesson used the log to make "writes" blazingly fast, this one used
timestamps to make "reads" both fresh and correct, and they share one truth — <strong>that monotonic timestamp issued by the TSO, running
through both write and read</strong>. Next time you write the consistency_level parameter in the SDK, may you picture this whole chain: TSO
stamping, Proxy fixing Tg, QueryNode waiting on tsafe, segcore filtering by MVCC — behind a seemingly simple parameter is a whole apparatus
that makes "distributed, query-while-write, and still correct" hold at once.</p>

<div class="card key"><div class="tag">📌 Key points</div>
<ul>
  <li><strong>Three steps</strong>: TSO stamps → Proxy derives Tg by level → QueryNode waits tsafe ≥ Tg, segcore filters by MVCC.</li>
  <li><strong>TSO</strong>: RootCoord's global monotonic clock governs <strong>both</strong> write order and read horizon, avoiding scrambled ordering from local-clock drift.</li>
  <li><strong>Tg is a dial</strong>: Strong / Bounded / Session / Eventually / Customized = freshness ↔ latency, the choice in your hands.</li>
  <li><strong>MVCC + tombstones</strong>: visible iff insert ts ≤ Tg and no tombstone ≤ Tg; reads/writes and reads/reads don't block, results stay self-consistent.</li>
  <li><strong>Tradeoff</strong>: fresher may mean waiting (and waiting per shard); work backward from "how stale you tolerate" to the level — don't reflexively reach for Strong.</li>
</ul></div>
""",
}
