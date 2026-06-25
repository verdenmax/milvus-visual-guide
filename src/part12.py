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

<p>这里要澄清一个常见误解：<strong>一致性级别是"读"侧的选择，不是"写"侧的</strong>。无论你选哪一档，<strong>写入永远是完整、确定地进入系统的</strong>——
盖戳、入 WAL、最终被所有节点消费到，这一点不因级别而变。级别只影响"<strong>一次读愿意等到多新、看到哪一刻的快照</strong>"。
所以"用了 Eventually 会不会丢写入？"这个担心是多余的：数据一条都不会少，你只是<strong>选择了暂时不等它到齐就先答</strong>而已。
把"写得全不全"和"读得新不新"这两件事分开，你就不会被一致性级别绕晕。</p>

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

<p>A common misconception to clear up here: <strong>the consistency level is a "read"-side choice, not a "write"-side one</strong>. Whichever tier
you pick, <strong>a write always enters the system fully and deterministically</strong> — stamped, into the WAL, eventually consumed by every node;
that doesn't change with the level. The level only affects "<strong>how fresh a single read is willing to wait for, which instant's snapshot it
sees</strong>". So the worry "does using Eventually lose writes?" is misplaced: not one row goes missing; you've merely <strong>chosen to answer
before waiting for it all to arrive</strong>. Separate "how complete the write" from "how fresh the read" and the consistency levels stop being
confusing.</p>

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


LESSON_53 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前两课讲的是"日志"和"时间戳"这两条软件层面的主线。这一课换个角度，看一条<strong>物理层面</strong>的设计：Milvus 为什么要把"计算"和"存储"彻底拆开，
让干活的节点几乎"不带状态"？这背后，藏着它能弹性扩缩、能秒级故障转移的秘密。</p>

<div class="card analogy"><div class="tag">🍳 打个比方</div>
<p>想象一家中央厨房：厨师（计算）<strong>自己不囤任何食材</strong>，所有原料都放在一个<strong>共享的大仓库</strong>（对象存储）里。要加一个厨师？直接来上工就行，
因为没有任何重要的东西"长在"某个厨师身上；某个厨师病倒了？换一个顶上，从仓库取料继续做，菜品分毫不差。Milvus 的计算节点，就是这样一群"不囤货的厨师"——
<strong>重要的字节都在仓库里，节点只负责加工</strong>。</p></div>

<h2>目标：为什么要把"算"和"存"拆开</h2>
<p>传统数据库常把数据<strong>绑在本地磁盘</strong>上：计算和存储挤在同一台机器里。这在单机时代很自然，但到了云原生、要随业务弹性伸缩时，它有两个致命问题。
其一，<strong>扩容不灵活</strong>：你的业务可能"读多写少"（典型的检索服务）或"写多读少"（离线灌一大批数据），可计算和存储绑死在一起，
想单独给某一头加资源都做不到，只能整机复制，既浪费又笨重。其二，<strong>故障代价高</strong>：如果最新数据就躺在某台机器的本地盘上，这台机器一挂，
数据要么直接丢失、要么得漫长地从别处恢复，期间服务大打折扣。Milvus 的答案是把两者<strong>彻底解耦</strong>：持久的字节交给专门的对象存储，
计算节点退化成"无状态"的加工者——<strong>算力和存储各自独立伸缩，节点挂了换一个就行</strong>。这不是为了炫技，而是云时代对一个数据库最实在的要求。</p>

<p>举个具体例子你就懂了：你的检索服务白天流量高峰、读多写少，于是你只想<strong>多加几个 QueryNode</strong> 扛搜索，而写入侧、存储侧原封不动；
到了夜里要离线灌一大批数据，你又只想<strong>临时加几个 DataNode</strong> 加速建段建索引，读侧不受影响。存算分离让这种"按需、局部、独立"的伸缩成为可能——
哪一环吃紧就给哪一环加资源，钱花在刀刃上。而在"计算存储绑死"的世界里，你想多扛点搜索，却被迫连存储一起复制，既贵又慢。</p>

<p>其实"无状态"这条原则贯穿得比你想的更彻底：不只是 QueryNode，连写入侧的 StreamingNode 也一样——它掌管的 WAL 真身存在可换的后端
（RocksMQ / Pulsar / Woodpecker）里，节点本身只是日志的"管家"而非"保险箱"（第 31 课）。<strong>从写到读、从存到算，整条链路上的工作节点都尽量不沉淀独有状态</strong>，
状态要么在 etcd、要么在对象存储、要么在 WAL 后端。这种一以贯之，正是 Milvus 能整体做到弹性与韧性的根本。</p>

<div class="card macro"><div class="tag">🗺️ 大图景</div>
<p>把系统分成三层来看：<strong>控制面</strong>（协调者把元数据存进 etcd）、<strong>计算层</strong>（无状态的 DataNode、QueryNode 只管处理）、
<strong>存储层</strong>（对象存储装着真正的数据与索引）。三层各自独立扩缩、各自可替换。这条"存算分离"的主线，正是上一课"日志即数据"的物理延伸——
既然段和索引都是可重建的派生品，那把它们放进共享存储、让计算节点不依赖本地状态，就顺理成章了。</p></div>

<div class="layers">
  <div class="layer l-part"><div class="lh"><span class="badge">控制面</span><span class="name">协调者 + etcd</span></div><div class="ld">元数据、段分配、节点健康——状态住这里（第 14 课）</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">计算层</span><span class="name">DataNode / QueryNode（无状态）</span></div><div class="ld">只管加工：建段、建索引、检索；挂了即可替换</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">存储层</span><span class="name">对象存储（binlog + 索引文件）</span></div><div class="ld">真正的字节，独立扩容、可靠且廉价</div></div>
</div>

<h2>持久的字节，住在别处</h2>
<p>数据真正的"家"是对象存储（S3 / MinIO 之类）：DataNode 把段刷成 binlog 文件、worker 把索引建成索引文件，统统写进对象存储（第 8、18 课）。
这一步带来一个极漂亮的解耦——对象存储成了<strong>建索引一方（DataNode worker）和加载一方（QueryNode）之间的"中转仓库"</strong>：
建的人只管把索引文件写进去，加载的人只管从里面读出来，<strong>两边根本不用直接通信、甚至不用知道对方是谁、在不在线</strong>（第 21、23 课）。
这正是上一课"共享一条日志、互不直接调用"那套哲学，在存储维度上的又一次体现：<strong>把耦合收敛到一个共享的中间物上</strong>，参与方就都松绑了。</p>

<p>为什么偏偏选对象存储，而不是某种分布式文件系统或数据库？因为对象存储恰好提供了 Milvus 最想要的几样东西：<strong>近乎无限的容量、按量付费的低成本、
极高的可靠性（多副本 / 纠删码由它内部搞定）、以及简单的"读写一个个不可变对象"的接口</strong>。而 binlog 和索引文件恰恰都是"写一次、读多次、几乎不改"的不可变文件——
和对象存储的特性<strong>天作之合</strong>。Milvus 只要把数据切成一个个段文件扔进去，剩下的持久性、扩容、容灾全由对象存储兜底，自己一行存储引擎代码都不用写。</p>

<h2>加载要便宜：mmap 的妙用</h2>
<p>字节在对象存储里，QueryNode 怎么把它们变成能检索的内存结构？最朴素的办法是全读进内存，但那样"能装多少数据"就被物理内存死死卡住了。
Milvus 的关键一招是 <strong>mmap</strong>（内存映射，第 35 课）：把索引/数据文件映射进进程地址空间，<strong>由操作系统按页惰性加载</strong>——
热点页常驻内存、冷页自动换出，于是<strong>"大于内存"的段也能服务</strong>，单机能承载的数据量大幅增加。代价是冷页首次访问要触发缺页、读一次磁盘，
尾延迟可能升高；所以是否启用、对哪些字段启用，是一个典型的"容量 vs 延迟"权衡。但无论全内存还是 mmap，关键都一样：
<strong>计算节点只是临时把共享存储里的字节"借"进来用，用完即可释放，自己不沉淀任何不可替代的状态</strong>。</p>

<p>正因为节点的内存只是共享存储的一层"缓存"，它还带来一个运维上的好处：<strong>节点是可以"预热"的</strong>。新加一个 QueryNode 上线，
它会按 QueryCoord 的分配从对象存储把该负责的段加载进来——加载完就能服务，整个过程不需要任何其他节点配合、也不会动到数据的真身。
同理，缩容时直接下线一个节点也很安全：它内存里那点"缓存"丢了无所谓，反正真相一直在对象存储里。这种"<strong>内存即缓存、存储即真相</strong>"的关系，
正是无状态弹性的微观写照。</p>

<div class="flow">
  <div class="node"><div class="nt">建索引侧</div><div class="nd">DataNode worker 写</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">对象存储</div><div class="nd">索引文件 / binlog · 中转仓库</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">加载侧</div><div class="nd">QueryNode 读（mmap）</div></div>
</div>

<h2>状态，住在控制面</h2>
<p>如果计算节点都"无状态"了，那"谁持有哪个段、集群现在长什么样"这些<strong>状态</strong>存哪？答案是<strong>控制面</strong>：元数据通过 Catalog / kv 层写进 etcd（第 14 课）、
由协调者统一掌管；QueryCoord 负责把段分配给各 QueryNode，并在节点上下线时重新均衡（第 13 课）。于是<strong>故障转移变得极快</strong>：
一个 QueryNode 挂了，它本来也没存什么独有数据——QueryCoord 只要把它负责的段<strong>重新分配给别的节点，新节点从对象存储把那些段重新加载一遍即可</strong>，
服务很快恢复，一个字节都不会丢。这就是"无状态"最大的红利：<strong>节点变成了可随意增删替换的"算力插槽"，而不是必须小心呵护的"数据保险箱"</strong>。
你会在下一课"故障是常态"里看到，这种"状态与计算分离"正是系统能自愈的物理基础。</p>

<p>为什么状态要单独放进 etcd，而不是也丢给对象存储？因为这两类数据的脾气完全不同。元数据（有哪些集合、段在谁手里、节点是否存活）
<strong>小、关键、要强一致、还要能被监听</strong>——一改动，相关组件得马上知道；这正是 etcd（基于 Raft 的强一致 KV）擅长的（第 14 课）。
而 binlog、索引这类<strong>大块、海量、只需可靠存放</strong>的数据，则交给对象存储。<strong>小而关键的状态进 etcd，大而笨重的字节进对象存储</strong>——
按数据的脾气分门别类，是这套架构干净利落的又一处体现。</p>

<p>这套"状态进 etcd"还顺手解决了"<strong>变化怎么传开</strong>"的问题：etcd 支持 watch，组件可以订阅自己关心的那部分元数据，<strong>一有变动立刻被通知</strong>——
比如 QueryCoord 把某个段重新分配给了新节点，相关方瞬间就能感知并行动。于是"谁该加载哪个段"这种调度决策，能在秒级内传达、生效。
把"大块数据放对象存储、关键状态放可监听的 etcd"两件事合起来，Milvus 才既能装下海量数据、又能对集群变化快速响应。</p>

<div class="cols">
  <div class="col"><h4>❌ 计算存储绑在本地盘</h4><p>数据躺在节点本地，扩容只能<strong>整机复制</strong>；节点一挂，数据要么丢、要么漫长恢复。状态"长在"机器上，节点成了不敢碰的保险箱。</p></div>
  <div class="col"><h4>✅ 无状态节点 + 共享存储</h4><p>字节在对象存储、状态在 etcd，节点只加工。算力与存储<strong>各自独立扩缩</strong>，坏了换一个、从存储重载即可，秒级恢复。</p></div>
</div>

<h2>代价与取舍</h2>
<p>存算分离不是没有代价。最直接的，是<strong>多了一跳网络</strong>：数据不在本地盘、而在远端对象存储，读它天然比读本地慢。Milvus 用一整套手段来摊薄这个代价——
growing 段把最新数据留在内存里兜底（第 7 课）、mmap 让热点页常驻、各级缓存减少回源、批量读减少往返。另一个代价是<strong>系统更复杂</strong>：
你需要一个可靠的对象存储、一个强一致的 etcd，还要协调者来编排分配与均衡——这也是为什么 Milvus 选择"<strong>站在成熟组件的肩膀上</strong>"（第 8 课），
而不是自己从头造一套存储。但换来的回报，是云时代最看重的三样东西：<strong>弹性</strong>（按需、局部、独立地扩缩）、<strong>韧性</strong>（节点无状态、秒级替换）、
<strong>成本</strong>（对象存储廉价、计算按需付费）。一句话：<strong>用"多一跳 + 多依赖"的代价，买来了"算力与存储各自自由伸缩、节点坏了也无所谓"的云原生体质</strong>。</p>

<p>值得一提的是，这"一跳网络"的代价，在向量检索场景里其实被摊得很薄：一次检索的瓶颈往往在"算距离"这种 CPU/GPU 密集的计算上，
而不在"把索引读进来"这一步——更何况热点段的页早被 mmap 常驻、或被各级缓存命中了。所以现实中，存算分离带来的弹性与韧性，
远远盖过那一点点额外的读延迟。这也是为什么几乎所有现代云数据库（不止 Milvus）都不约而同走向了存算分离。</p>

<div class="card key"><div class="tag">📌 本课要点</div>
<ul>
  <li><strong>三层解耦</strong>：控制面（etcd 存状态）/ 计算层（无状态节点）/ 存储层（对象存储装字节），各自独立扩缩、各自可替换。</li>
  <li><strong>对象存储 = 中转仓库</strong>：建索引侧写、加载侧读，两边不直接通信——上一课"共享中间物"哲学的存储版。</li>
  <li><strong>mmap</strong>：让"大于内存"的段也能加载，热点页常驻、冷页换出，是容量 ↔ 延迟的取舍。</li>
  <li><strong>状态在控制面</strong>：元数据在 etcd、段分配由 QueryCoord 管；节点挂了重分配 + 从存储重载，秒级恢复、零丢失。</li>
  <li><strong>取舍</strong>：代价是多一跳网络 + 多依赖；回报是<strong>弹性、韧性、成本</strong>——云原生体质。</li>
</ul></div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The last two lessons were software throughlines — "the log" and "the timestamp". This one shifts angle to a <strong>physical</strong> design:
why does Milvus fully separate "compute" from "storage", leaving the working nodes almost "stateless"? Hidden in this is the secret of how it
scales elastically and fails over in seconds.</p>

<div class="card analogy"><div class="tag">🍳 An analogy</div>
<p>Picture a central kitchen: the cooks (compute) <strong>stock no ingredients themselves</strong>; all raw material lives in one
<strong>shared warehouse</strong> (object storage). Add a cook? They just show up and work, because nothing important "lives in" any one cook.
A cook falls ill? Swap in another, fetch from the warehouse, and the dishes are identical. Milvus's compute nodes are exactly this crew of
"non-stocking cooks" — <strong>the important bytes are in the warehouse; the nodes only process</strong>.</p></div>

<h2>The goal: why separate "compute" from "storage"</h2>
<p>Traditional databases often <strong>bind data to local disk</strong>: compute and storage crammed onto one machine. Natural in the
single-box era, but for cloud-native elastic scaling it has two fatal problems. First, <strong>inflexible scaling</strong>: your workload might
be "read-heavy, write-light" (a typical search service) or "write-heavy, read-light" (bulk offline loading), yet with compute and storage
welded together you can't add resources to just one side — you can only clone whole machines, wasteful and clumsy. Second, <strong>costly
failure</strong>: if the freshest data sits on one machine's local disk, that machine dying means data is lost or must be slowly recovered from
elsewhere, with degraded service throughout. Milvus's answer is to <strong>fully decouple</strong>: durable bytes go to dedicated object
storage, and compute nodes degrade into "stateless" processors — <strong>compute and storage scale independently, and a dead node is just
swapped out</strong>. Not showing off, but the most concrete demand the cloud era makes of a database.</p>

<p>A concrete example makes it click: your search service peaks by day, read-heavy and write-light, so you want to <strong>add a few
QueryNodes</strong> to carry searches while the write and storage sides stay untouched; at night you bulk-load a big batch offline, so you
want to <strong>temporarily add a few DataNodes</strong> to speed up building segments and indexes, leaving the read side unaffected.
Separation makes this "on-demand, local, independent" scaling possible — pour resources into whichever link is strained, spending where it
counts. In the "compute and storage welded" world, wanting to carry more searches forces you to clone storage along with it, both costly and
slow.</p>

<p>In fact "stateless" runs deeper than you might think: not just QueryNode, but the write side's StreamingNode too — the WAL it owns
actually lives in a swappable backend (RocksMQ / Pulsar / Woodpecker), and the node itself is the log's "steward", not its "safe" (Lesson 31).
<strong>From write to read, from storage to compute, every working node along the chain sediments as little unique state as possible</strong>;
state lives either in etcd, or in object storage, or in the WAL backend. This consistency is the root of how Milvus achieves elasticity and
resilience as a whole.</p>

<div class="card macro"><div class="tag">🗺️ The big picture</div>
<p>See the system as three tiers: the <strong>control plane</strong> (coordinators store metadata in etcd), the <strong>compute tier</strong>
(stateless DataNode/QueryNode just process), and the <strong>storage tier</strong> (object storage holds the real data and indexes). Each tier
scales and is replaced independently. This "storage-compute separation" throughline is the physical extension of last lesson's "log as data":
since segments and indexes are rebuildable derivatives, putting them in shared storage and freeing compute nodes from local state follows
naturally.</p></div>

<div class="layers">
  <div class="layer l-part"><div class="lh"><span class="badge">control plane</span><span class="name">coordinators + etcd</span></div><div class="ld">metadata, segment assignment, node health — state lives here (L14)</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">compute tier</span><span class="name">DataNode / QueryNode (stateless)</span></div><div class="ld">only process: build segments/indexes, search; swappable on death</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">storage tier</span><span class="name">object storage (binlog + index files)</span></div><div class="ld">the real bytes, independently scalable, reliable and cheap</div></div>
</div>

<h2>The durable bytes live elsewhere</h2>
<p>Data's real "home" is object storage (S3 / MinIO and the like): DataNode flushes segments into binlog files and a worker builds indexes
into index files, all written to object storage (Lessons 8, 18). This brings a beautiful decoupling — object storage becomes the
<strong>"transfer warehouse" between the build side (DataNode worker) and the load side (QueryNode)</strong>: the builder just writes index
files in, the loader just reads them out, and <strong>the two need never communicate directly, nor even know who the other is or whether it's
online</strong> (Lessons 21, 23). This is exactly last lesson's "share one log, never call each other directly" philosophy, shown again on the
storage axis: <strong>converge coupling onto one shared intermediary</strong> and every party is unbound.</p>

<p>Why object storage specifically, rather than some distributed file system or database? Because object storage happens to offer exactly
what Milvus wants most: <strong>near-infinite capacity, pay-as-you-go low cost, very high reliability (replication / erasure coding handled
internally), and a simple "read/write immutable objects one by one" interface</strong>. And binlogs and index files are precisely
"write-once, read-many, barely-modified" immutable files — a <strong>perfect match</strong> for object storage's nature. Milvus just slices
data into segment files and tosses them in; durability, scaling, and disaster recovery are all backstopped by object storage, without writing
a single line of storage-engine code itself.</p>

<h2>Loading must be cheap: the magic of mmap</h2>
<p>With bytes in object storage, how does a QueryNode turn them into searchable in-memory structures? The naïve way is to read it all into
RAM, but then "how much data you can hold" is hard-capped by physical memory. Milvus's key move is <strong>mmap</strong> (memory mapping,
Lesson 35): map index/data files into the process's address space and <strong>let the OS page them in lazily</strong> — hot pages resident,
cold pages evicted — so <strong>segments "larger than memory" can still be served</strong> and a node's capacity grows sharply. The cost is
that a cold page's first access triggers a fault and a disk read, so tail latency may rise; whether to enable it, and for which fields, is a
classic "capacity vs latency" tradeoff. But whether fully in-memory or mmap, the crux is the same: <strong>a compute node merely "borrows"
bytes from shared storage temporarily, releasing them when done, sedimenting no irreplaceable state of its own</strong>.</p>

<p>Because a node's memory is just a "cache" layer over shared storage, it brings an operational nicety: <strong>nodes can be "warmed
up"</strong>. Bring a new QueryNode online and, per QueryCoord's assignment, it loads its segments from object storage — once loaded it can
serve, with no coordination from other nodes and no touching the data's true body. Likewise, scaling down by simply taking a node offline is
safe: losing that bit of "cache" in its memory doesn't matter, since the truth has been in object storage all along. This "<strong>memory is
cache, storage is truth</strong>" relationship is the micro-portrait of stateless elasticity.</p>

<div class="flow">
  <div class="node"><div class="nt">build side</div><div class="nd">DataNode worker writes</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">object storage</div><div class="nd">index files / binlog · transfer warehouse</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">load side</div><div class="nd">QueryNode reads (mmap)</div></div>
</div>

<h2>State lives in the control plane</h2>
<p>If compute nodes are all "stateless", where do the <strong>state</strong>s — "who holds which segment, what the cluster looks like now" —
live? In the <strong>control plane</strong>: metadata is written into etcd via the Catalog/kv layers (Lesson 14), governed by the
coordinators; QueryCoord assigns segments to QueryNodes and rebalances on join/leave (Lesson 13). So <strong>failover becomes very fast</strong>:
a QueryNode dies, but it held no unique data anyway — QueryCoord simply <strong>reassigns its segments to other nodes, and the new node reloads
those segments from object storage</strong>, service recovers quickly, and not a byte is lost. That is "statelessness"'s biggest dividend:
<strong>nodes become "compute slots" you can freely add, drop, and replace, not "data safes" you must nurse carefully</strong>. You'll see in
the next lesson, "failure as the default", that this "state-compute separation" is the very physical basis for self-healing.</p>

<p>Why does state go into etcd specifically, rather than also into object storage? Because the two kinds of data have utterly different
temperaments. Metadata (which collections exist, who holds which segment, whether a node is alive) is <strong>small, critical, needs strong
consistency, and must be watchable</strong> — change it and the relevant components must know at once; that is exactly etcd's forte (a
Raft-based strongly-consistent KV, Lesson 14). Bulky, massive data that only needs reliable storage — binlogs, indexes — goes to object
storage instead. <strong>Small critical state into etcd, big heavy bytes into object storage</strong> — sorting data by its temperament is
another place this architecture stays crisp.</p>

<p>Putting "state into etcd" also neatly solves "<strong>how a change propagates</strong>": etcd supports watch, so a component can subscribe
to the slice of metadata it cares about and <strong>be notified the instant it changes</strong> — e.g. QueryCoord reassigns a segment to a new
node and the relevant parties perceive and act on it instantly. So a scheduling decision like "who should load which segment" propagates and
takes effect within seconds. Combine "big data in object storage, critical state in watchable etcd" and Milvus can both hold massive data and
react quickly to cluster change.</p>

<div class="cols">
  <div class="col"><h4>❌ Compute + storage on local disk</h4><p>Data sits on the node's local disk; scaling means <strong>cloning whole machines</strong>; a node dies and data is lost or slowly recovered. State "lives on" the machine, making the node an untouchable safe.</p></div>
  <div class="col"><h4>✅ Stateless nodes + shared storage</h4><p>Bytes in object storage, state in etcd, nodes only process. Compute and storage <strong>scale independently</strong>; a failure just swaps a node and reloads from storage — recovery in seconds.</p></div>
</div>

<h2>The payoff and the tradeoff</h2>
<p>Separation isn't free. The most direct cost is <strong>an extra network hop</strong>: data isn't on local disk but in remote object storage,
inherently slower to read than local. Milvus thins this cost with a whole toolkit — growing segments keep the freshest data in memory as a
backstop (Lesson 7), mmap keeps hot pages resident, layered caches reduce round-trips to the origin, batched reads cut trips. Another cost is
<strong>more complexity</strong>: you need a reliable object store, a strongly-consistent etcd, and coordinators to orchestrate assignment and
balancing — which is exactly why Milvus chooses to "<strong>stand on the shoulders of mature components</strong>" (Lesson 8) rather than build
a storage layer from scratch. But the reward is the three things the cloud era prizes most: <strong>elasticity</strong> (scale on demand,
locally, independently), <strong>resilience</strong> (stateless nodes, second-scale replacement), and <strong>cost</strong> (cheap object
storage, pay-as-you-go compute). In one line: <strong>at the cost of "one more hop + more dependencies", you buy the cloud-native constitution
of "compute and storage each scaling freely, and a dead node being no big deal"</strong>.</p>

<p>Worth noting, this "one network hop" cost is actually spread thin in vector search: a search's bottleneck is usually the CPU/GPU-heavy
"distance computation", not the "read the index in" step — all the more so when hot segments' pages are already resident via mmap or hit in
caches. So in practice, the elasticity and resilience that separation brings far outweigh that sliver of extra read latency. This is why
nearly all modern cloud databases (not just Milvus) have converged on storage-compute separation.</p>

<div class="card key"><div class="tag">📌 Key points</div>
<ul>
  <li><strong>Three-tier decoupling</strong>: control plane (etcd holds state) / compute tier (stateless nodes) / storage tier (object storage holds bytes), each scaling and replaceable independently.</li>
  <li><strong>Object storage = transfer warehouse</strong>: build side writes, load side reads, never communicating directly — the storage version of last lesson's "shared intermediary" philosophy.</li>
  <li><strong>mmap</strong>: lets segments "larger than memory" still load, hot pages resident, cold evicted — a capacity ↔ latency tradeoff.</li>
  <li><strong>State in the control plane</strong>: metadata in etcd, segment assignment by QueryCoord; a dead node is reassigned + reloaded from storage, recovering in seconds with zero loss.</li>
  <li><strong>Tradeoff</strong>: the cost is one more hop + more dependencies; the reward is <strong>elasticity, resilience, cost</strong> — a cloud-native constitution.</li>
</ul></div>
""",
}


LESSON_54 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
"亿级向量、毫秒检索"——这句宣传语背后，藏着一个看似不可能的任务：一台机器既装不下十亿条向量，更不可能在毫秒内把它们逐一比对一遍。
Milvus 是怎么做到的？答案不是某种魔法算法，而是一套<strong>把大问题拆成小问题、再把小答案拼回大答案</strong>的工程艺术——这一课就讲它。</p>

<div class="card analogy"><div class="tag">🚓 打个比方</div>
<p>想象一场全国通缉：总部不可能把十四亿人挨个核对一遍。真正的做法是<strong>分而治之</strong>——把任务下发到各省、各市、各派出所，<strong>每个派出所只在自己辖区里排查</strong>，
然后<strong>只把各自最像的几个嫌疑人往上报</strong>。省里汇总市里的、总部汇总省里的，每一层都只处理"下一层报上来的少数候选"。
十四亿人里锁定目标，靠的从来不是谁真的看了十四亿张脸，而是<strong>层层缩小、层层只上报精华</strong>。Milvus 的一次检索，就是这样一场通缉。</p></div>

<h2>目标：为什么"十亿级"必须分而治之</h2>
<p>先看清楚难在哪。十亿条 768 维的 float 向量，光原始数据就有约 3 TB——任何单机内存都装不下；就算装得下，一次检索若要和每条向量都算一次距离（<strong>暴力扫描</strong>），
那是十亿次浮点运算起步，毫秒级响应根本无从谈起。所以"大规模"天然要求两件事同时成立：<strong>数据要能摊到很多台机器上</strong>（单机装不下就横向铺开），
<strong>每台机器上的检索还要足够快</strong>（不能在自己那份数据上也暴力扫）。这两件事，恰好对应 Milvus 的两大法宝——<strong>分段 + 扇出归并</strong>，和<strong>每段建索引 + 过滤下推</strong>。</p>

<p>换个角度感受一下这个量级：暴力扫描的耗时和数据量成正比——一百万条向量也许还能勉强毫秒级扫完，但一亿条就是一百倍、十亿条就是一千倍，线性地慢下去，
很快退化到秒级、十秒级，彻底不可用。而分而治之的耗时，理想情况下几乎不随<strong>总量</strong>增长，只随<strong>每个节点分到的那份</strong>增长——
你加机器、把每份摊薄，墙上时间还能压回去。这就是"线性扫描"和"分布式分治"两条曲线的本质差别：一个随规模爆炸，一个随机器数被压平。</p>

<p>更妙的是，分而治之不只是"为了装得下"的无奈之举，它还顺带换来了<strong>并行</strong>：既然数据本就摊在很多节点上，那一次检索就能让这些节点<strong>同时</strong>各搜各的，
墙上时间几乎不随数据量线性增长。换句话说，<strong>同一套设计，既解决了"容量"，又解决了"延迟"</strong>——这正是它优雅的地方。</p>

<p>这种"一套设计同时解决容量和延迟"的优雅，并非免费得来，它依赖一个前提：<strong>问题本身可以被分解</strong>。所幸"找最近邻"恰好是一个高度可分解的问题——
全局最近的 K 个，一定也是"某个局部最近的 K 个"之一。正因为有这个数学性质，把数据切开、各搜各的、再合并，才不会丢掉正确答案。
很多看似强大的系统之所以难以扩展，根子就在于它们的核心问题<strong>不可分解</strong>；而向量检索的可分解性，是 Milvus 能轻松横向扩展的幸运起点。</p>

<div class="card macro"><div class="tag">🗺️ 大图景</div>
<p>把一次检索想成三个动作：<strong>分</strong>（数据被切成一个个段、摊在多个分片/节点上）、<strong>搜</strong>（查询扇出到所有相关段，各自在本地算出局部 topK）、
<strong>并</strong>（局部结果逐层归并成全局 topK）。关键的数学保证是：<strong>各局部 topK 的并集，必定包含真正的全局 topK</strong>——所以每一层只往上传 K 个候选就够了，
网络上永远只流动 K 量级的数据。十亿向量在底下并行计算，网络上却轻盈得很。</p></div>

<div class="flow">
  <div class="node hl"><div class="nt">分</div><div class="nd">切成段 · 摊到分片/节点</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">搜</div><div class="nd">各段并行算局部 topK</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">并</div><div class="nd">逐层归并出全局 topK</div></div>
</div>

<h2>分：把数据切成可并行的小块</h2>
<p>一切的前提是<strong>切分</strong>。一个集合的数据并不是堆成一坨，而是被切成许多<strong>段（segment）</strong>（封口 sealed 后即不可变），再分散到若干<strong>分片（shard，即 vchannel）</strong>上（第 7、12 课）。
段是<strong>检索的最小并行单位</strong>：每个段可以独立地被检索、被建索引、被加载，互不依赖。分片则是<strong>路由与并行的单位</strong>：写入按主键哈希进不同分片，
查询则扇出到所有分片。正因为数据从一开始就被切好、摊开，"让很多节点同时干活"才有了物理基础——你没法并行一个不可分割的整体，但可以轻松并行一堆独立的段。</p>

<p>那一个集合该切成多少分片、每段装多少行？这本身就是个工程权衡：分片太少，并行度不够、扛不住高并发写入；分片太多，每次查询要扇出的目标也变多、归并的开销上升。
段的大小同理——太小则段的数量爆炸、管理和归并都变重，太大则单段检索变慢、加载也不灵活。Milvus 把这些交给 DataCoord 按配置和负载自动决策（第 12 课），
但理解了背后的取舍，你在调优时就知道该往哪个方向拧。</p>

<h2>搜与并：扇出去，再层层收回来</h2>
<p>查询来了，走的是经典的<strong>扇出—归约（scatter-gather）</strong>形状（第 3、25 课）。Proxy 把请求<strong>扇出</strong>到所有相关分片；每个分片的 delegator 再把它分发给持有不同段的 QueryNode；
每个段在 C++ segcore 里算出<strong>自己的 topK</strong>。然后结果<strong>反向归约</strong>，而且是<strong>三层归并</strong>（第 29 课）：段内 topK → 每个分片的 delegator 把本分片各 QueryNode 的段结果并成<strong>分片 topK</strong> →
Proxy 再把各分片的结果并成<strong>全局 topK</strong>。每一层都只把"前 K 个候选"往上交，所以哪怕底下有上亿向量，<strong>网络上流动的数据也只有 K 量级</strong>——这正是分布式检索又快又省的命门。</p>

<p>为什么"每层只上交 K 个"这么关键？算一笔账就懂了：假设有 1000 个段、每段算出 top-10，如果把所有候选都往上搬，那是一万条；
可如果每个节点先把自己负责的段归并成 top-10、再往上交，Proxy 最终只需在<strong>分片数 × 10</strong> 这个量级的候选里挑出全局 top-10。
无论底下是一亿还是十亿向量，<strong>跨网络流动的永远只是 K 乘以层数那么点数据</strong>。这就是为什么 Milvus 的检索延迟主要取决于"段内算得多快"，
而不是"数据总量多大"——总量的压力，早被分治和并行消化掉了。</p>

<div class="trace">
  <div class="tcap"><b>一次 topK 检索的扇出—归并</b>：每层只上交局部 topK，逐层收敛</div>
  <div class="stations">
    <div class="stn"><h5>段</h5><div class="cellrow"><span class="vc">段 topK</span></div><div class="cellrow"><span class="vc">段 topK</span></div><div class="tlab">segcore 各算各的</div></div>
    <div class="stn"><h5>分片</h5><div class="cellrow"><span class="vc hot">分片 topK</span></div><div class="tlab">delegator 归并本分片</div></div>
    <div class="stn"><h5>Proxy</h5><div class="cellrow"><span class="vc hot">全局 topK</span></div><div class="tlab">跨分片归并</div></div>
  </div>
</div>

<h2>让每个小块也很快：索引与过滤下推</h2>
<p>光把数据切开还不够——如果每个段内部还是暴力扫，那只是把"慢"分摊到很多机器上，总量没变。所以还要让<strong>每个段自己也很快</strong>。两手：其一，<strong>每个 sealed 段建 ANN 索引</strong>
（HNSW/IVF 等，第 21、23 课），把"段内找最近邻"从暴力扫降成近似的图/簇查找；其二，<strong>标量过滤下推</strong>——带条件的查询，先用标量索引算出一个 bitset 掩码，
把"哪些行合格"下推给向量检索，让 ANN 只在合格子集上搜（第 28 课）。两手合起来，意味着检索在每一层都尽早、尽小地剪枝：<strong>过滤缩小候选、索引加速段内、归并只搬精华</strong>，
环环相扣，才托得起"亿级毫秒"。</p>

<p>还有个容易忽略的细节：索引是<strong>按段</strong>建的，不是给整张表建一个大索引。为什么？因为段不可变、又是并行单位，按段建索引意味着每个段的索引可以
<strong>独立构建、独立加载、独立检索</strong>，新段建好就能用、坏了只补那一个段，天然契合"分而治之"。而最新写入的 growing 段还没来得及建索引，就先用暴力扫描兜底——
等它封口、建好索引，再由 QueryCoord 协调"切换"到索引检索（第 7、23 课）。于是"边写边查"和"亿级快检"在同一套段的生命周期里被优雅地统一了起来。</p>

<div class="cols">
  <div class="col"><h4>✅ 分而治之（Milvus）</h4><p>数据切成段并行搜，每层只上交 K 个候选。<strong>网络只流动 K 量级</strong>，计算可并行铺开，于是能横向扩展到十亿级。</p></div>
  <div class="col"><h4>❌ 把全部向量拉回来暴力算</h4><p>Proxy 自己拉回上亿向量逐一算 topK——网络被打爆、单点算不动。规模一大就彻底跑不动，这正是分布式检索要避开的反面。</p></div>
</div>

<h2>代价与取舍</h2>
<p>分而治之的代价，主要是两类。其一，<strong>召回是近似的</strong>：因为段内用的是 ANN 而非暴力，最终的召回率由<strong>段内检索的精度</strong>（nprobe/ef 等参数）决定，
而<strong>不是</strong>由归并决定——归并只是忠实地合并各段交上来的结果。所以想要更准，该调的是段内检索的参数，而非别处；这也是个老朋友：召回 ↔ 延迟 ↔ 内存的三角取舍（第 5、22 课）。
其二，<strong>有些操作天生更贵</strong>：深翻页（offset 很大）和过大的 K，会让每一层都得搬更多候选、归并更重，是分布式检索里少数"规模敏感"的操作，要在业务上尽量避免。
但抛开这些，"分—搜—并"这条主线托起的，是 Milvus 最核心的承诺：<strong>数据再多，也只让网络流动一点点、让计算并行铺开</strong>——这就是它敢说"十亿级"的底气。</p>

<p>举个具体例子体会"召回由段内决定"：假设你发现检索结果不够准、漏掉了一些本该召回的近邻，该怎么办？很多人第一反应是"加大 topK"或"改归并逻辑"——
但那都没用，因为归并只是忠实合并，它不会凭空变出段内没找到的近邻。正确的旋钮是<strong>调高段内 ANN 的搜索强度</strong>（比如 IVF 的 nprobe、HNSW 的 ef），
让每个段在自己那份数据里找得更全、把更靠谱的候选交上来。把"准不准"这件事定位到"段内检索"，是用好 Milvus 的一个关键认知，也再次印证了那条主线：
<strong>真正的工作发生在段内，归并只负责诚实地拼装</strong>。</p>

<p>顺带说清"深翻页为什么特别贵"：要返回第 10000~10010 名，系统没法直接"跳"到第 10000 名——它必须让每一层都先算出<strong>前 10010 名</strong>、再丢掉前面的，
才能取到你要的那一段。于是 offset 越大，每层要搬运和归并的候选就越多，开销随之膨胀。这也是为什么向量检索里"翻很多页"是个反模式，实践中更推荐用
<strong>迭代器</strong>按游标顺序取大结果集（第 50 课），而不是用巨大的 offset 硬翻。理解了这一点，你在设计"取大量结果"的功能时，就会自觉绕开深翻页这个坑，转而用更契合分布式检索的游标式翻页。</p>

<div class="card key"><div class="tag">📌 本课要点</div>
<ul>
  <li><strong>分</strong>：数据切成不可变的段、摊到多个分片，段是检索的最小并行单位——这是横向扩展与并行的物理前提。</li>
  <li><strong>搜+并</strong>：扇出到段各算局部 topK，再三层归并（段→节点→Proxy）；每层只上交 K 个，<strong>网络只流动 K 量级</strong>。</li>
  <li><strong>数学保证</strong>：各局部 topK 的并集必含全局 topK，所以"只上报精华"不丢正确性。</li>
  <li><strong>让小块也快</strong>：每段建 ANN 索引 + 标量过滤下推，尽早尽小地剪枝，避免"把慢分摊到多机"。</li>
  <li><strong>取舍</strong>：召回近似（由段内精度决定，不由归并决定）；深翻页/过大 K 是少数规模敏感操作，要避开。</li>
</ul></div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
"Billions of vectors, millisecond search" — behind that tagline hides a seemingly impossible task: one machine can neither hold a billion
vectors nor compare them one by one within milliseconds. How does Milvus do it? Not with some magic algorithm, but with an engineering art
of <strong>splitting a big problem into small ones, then stitching the small answers back into a big one</strong> — this lesson is about it.</p>

<div class="card analogy"><div class="tag">🚓 An analogy</div>
<p>Picture a nationwide manhunt: headquarters can't check 1.4 billion people one by one. The real method is <strong>divide and
conquer</strong> — push the task down to provinces, cities, precincts, where <strong>each precinct searches only its own district</strong>, then
<strong>reports up only its few best suspects</strong>. The province aggregates the cities', HQ aggregates the provinces', each layer handling
only "the few candidates the layer below reported". Pinning a target among 1.4 billion never relies on anyone actually viewing 1.4 billion
faces, but on <strong>narrowing layer by layer, reporting up only the cream</strong>. One Milvus search is exactly such a manhunt.</p></div>

<h2>The goal: why "billions" must divide and conquer</h2>
<p>First see the difficulty clearly. A billion 768-dim float vectors are about 3 TB of raw data alone — no single machine's memory holds it;
and even if it did, a search that computes a distance against every vector (<strong>brute force</strong>) is a billion floating-point ops at
minimum, with millisecond response out of the question. So "scale" inherently demands two things at once: <strong>data must spread across many
machines</strong> (if one box can't hold it, lay it out horizontally), and <strong>the search on each machine must still be fast</strong> (no
brute force even on its own slice). These two map precisely onto Milvus's two big weapons — <strong>segmentation + scatter-gather</strong>, and
<strong>a per-segment index + filter pushdown</strong>.</p>

<p>Feel the magnitude from another angle: brute force's time is proportional to data size — a million vectors might just scan within
milliseconds, but a hundred million is 100×, a billion 1000×, growing linearly until it degrades to seconds, tens of seconds, utterly unusable.
Divide-and-conquer's time, ideally, barely grows with the <strong>total</strong>, only with <strong>the slice each node gets</strong> — add
machines, thin each slice, and wall-clock time comes back down. That's the essential difference between the "linear scan" and "distributed
divide" curves: one explodes with scale, the other is flattened by machine count.</p>

<p>Better still, divide-and-conquer isn't only a "so it fits" concession; it also yields <strong>parallelism</strong>: since the data already
spreads over many nodes, one search lets those nodes search <strong>simultaneously</strong>, and wall-clock time barely grows linearly with
data size. In other words, <strong>one design solves both "capacity" and "latency"</strong> — that is its elegance.</p>

<p>This elegance of "one design solving both capacity and latency" isn't free; it rests on a premise: <strong>the problem itself must be
decomposable</strong>. Happily, "find nearest neighbors" is highly decomposable — the global nearest K must each also be "some locally nearest
K". It's this mathematical property that lets you cut the data, search each piece, and merge without losing the right answer. Many seemingly
powerful systems are hard to scale precisely because their core problem is <strong>not decomposable</strong>; vector search's decomposability is
the lucky starting point of Milvus's easy horizontal scaling.</p>

<div class="card macro"><div class="tag">🗺️ The big picture</div>
<p>See a search as three acts: <strong>split</strong> (data is cut into segments, spread over shards/nodes), <strong>search</strong> (the query
fans out to all relevant segments, each computing a local topK), <strong>combine</strong> (local results merge layer by layer into a global
topK). The key mathematical guarantee: <strong>the union of the local topKs necessarily contains the true global topK</strong> — so each layer
needs to pass up only K candidates, and only K-scale data ever crosses the network. A billion vectors compute in parallel below, yet the
network stays feather-light.</p></div>

<div class="flow">
  <div class="node hl"><div class="nt">split</div><div class="nd">cut into segments · spread over shards/nodes</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">search</div><div class="nd">segments compute local topK in parallel</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">combine</div><div class="nd">merge layer by layer into a global topK</div></div>
</div>

<h2>Split: cut data into parallelizable small blocks</h2>
<p>The premise of everything is <strong>splitting</strong>. A collection's data isn't one heap but is cut into many <strong>segments</strong>
(immutable once sealed), then spread over several <strong>shards (vchannels)</strong> (Lessons 7, 12). A segment is the <strong>smallest unit of
parallel search</strong>: each can be searched, indexed, and loaded independently, with no dependency on the others. A shard is the <strong>unit
of routing and parallelism</strong>: writes hash by primary key into different shards, queries fan out to all shards. Because data is cut and
spread from the start, "letting many nodes work at once" has a physical basis — you can't parallelize an indivisible whole, but you can easily
parallelize a pile of independent segments.</p>

<p>So how many shards should a collection be cut into, and how many rows per segment? That's itself an engineering tradeoff: too few shards and
parallelism is insufficient, unable to bear high-concurrency writes; too many and each query fans out to more targets, raising merge overhead.
Segment size likewise — too small and the segment count explodes, making management and merging heavier; too large and single-segment search
slows and loading gets inflexible. Milvus leaves these to DataCoord to decide automatically by config and load (Lesson 12), but grasping the
tradeoff tells you which way to turn the dial when tuning.</p>

<h2>Search & combine: fan out, then gather back layer by layer</h2>
<p>A query takes the classic <strong>scatter-gather</strong> shape (Lessons 3, 25). The Proxy <strong>scatters</strong> the request to all
relevant shards; each shard's delegator hands it to the QueryNodes holding different segments; each segment computes <strong>its own topK</strong>
in C++ segcore. Results then <strong>gather back</strong> — in <strong>three merge levels</strong> (Lesson 29): segment topK → each shard's delegator
merges its shard's QueryNodes' results into a <strong>shard topK</strong> → the Proxy merges the shards' results into a <strong>global topK</strong>. Each
layer passes up only "the top K candidates", so even with hundreds of millions of vectors below, <strong>only K-scale data flows on the
network</strong> — the very crux of fast, cheap distributed search.</p>

<p>Why is "each layer passes up only K" so crucial? Do the arithmetic: say 1000 segments each compute top-10; hauling all candidates up is ten
thousand; but if each node first merges its segments into a top-10 then passes that up, the Proxy finally picks the global top-10 from only
<strong>shard-count × 10</strong> candidates. Whether a hundred million or a billion vectors lie below, <strong>only K-times-layers worth of data
ever crosses the network</strong>. That is why Milvus's search latency depends mainly on "how fast a segment computes", not "how big the total
is" — the total's pressure was long since absorbed by divide-and-conquer and parallelism.</p>

<div class="trace">
  <div class="tcap"><b>scatter-gather of one topK search</b>: each layer passes up a local topK, converging upward</div>
  <div class="stations">
    <div class="stn"><h5>segment</h5><div class="cellrow"><span class="vc">segment topK</span></div><div class="cellrow"><span class="vc">segment topK</span></div><div class="tlab">segcore each on its own</div></div>
    <div class="stn"><h5>shard</h5><div class="cellrow"><span class="vc hot">shard topK</span></div><div class="tlab">delegator merges this shard</div></div>
    <div class="stn"><h5>Proxy</h5><div class="cellrow"><span class="vc hot">global topK</span></div><div class="tlab">cross-shard merge</div></div>
  </div>
</div>

<h2>Make each small block fast too: index & filter pushdown</h2>
<p>Cutting the data isn't enough — if each segment still brute-forces internally, you've merely spread the "slow" across many machines, the
total unchanged. So each segment must be <strong>fast on its own</strong>, two ways. One: <strong>build an ANN index on each sealed
segment</strong> (HNSW/IVF, etc., Lessons 21, 23), turning "find nearest neighbors in a segment" from brute force into an approximate graph/cluster
lookup. Two: <strong>scalar filter pushdown</strong> — for a conditional query, first compute a bitset mask with a scalar index and push "which
rows qualify" down into the vector search, so ANN searches only the qualifying subset (Lesson 28). Together they prune as early and as small as
possible at every layer: <strong>filtering shrinks candidates, the index speeds the segment, the merge moves only the cream</strong> — interlocking
to hold up "billions in milliseconds".</p>

<p>An easily-missed detail: the index is built <strong>per segment</strong>, not one big index for the whole table. Why? Because segments are
immutable and the unit of parallelism, so a per-segment index can be <strong>built, loaded, and searched independently</strong> — a new segment
is usable as soon as it's built, a broken one needs only that one segment repaired, naturally fitting "divide and conquer". And the freshest
growing segment, not yet indexed, is covered by brute force first — once it seals and its index is built, QueryCoord coordinates the "switch"
to indexed search (Lessons 7, 23). So "query-while-write" and "billion-scale fast search" are elegantly unified within one segment
lifecycle.</p>

<div class="cols">
  <div class="col"><h4>✅ Divide and conquer (Milvus)</h4><p>Data cut into segments searched in parallel, each layer passing up only K candidates. <strong>Only K-scale crosses the network</strong>, compute spreads in parallel, so it scales horizontally to billions.</p></div>
  <div class="col"><h4>❌ Pull all vectors back and brute-force</h4><p>The Proxy pulls hundreds of millions of vectors back to compute topK itself — the network melts, a single point can't crunch it. It collapses utterly at scale, exactly the anti-pattern distributed search avoids.</p></div>
</div>

<h2>The payoff and the tradeoff</h2>
<p>Divide-and-conquer costs you mainly two things. First, <strong>recall is approximate</strong>: because segments use ANN, not brute force, the
final recall is set by the <strong>in-segment search precision</strong> (params like nprobe/ef), <strong>not</strong> by the merge — the merge only
faithfully combines what the segments hand up. So to get more accurate results, tune the in-segment search params, not elsewhere; an old friend
again: the recall ↔ latency ↔ memory triangle (Lessons 5, 22). Second, <strong>some operations are inherently pricier</strong>: deep paging (a large
offset) and an oversized K make every layer move more candidates and merge harder — among the few "scale-sensitive" operations in distributed
search, best avoided at the business level. But setting those aside, the "split–search–combine" throughline upholds Milvus's most core promise:
<strong>however much data there is, let only a little cross the network while compute spreads in parallel</strong> — that is what lets it dare to
say "billions".</p>

<p>A concrete example to feel "recall is set in-segment": suppose your results aren't accurate enough, missing some neighbors that should have
been recalled — what do you do? Many reach first for "raise topK" or "change the merge logic" — but neither helps, because the merge only
faithfully combines; it can't conjure neighbors the segments never found. The right dial is to <strong>raise the in-segment ANN's search
effort</strong> (e.g. IVF's nprobe, HNSW's ef), so each segment searches its own slice more thoroughly and hands up better candidates. Locating
"accuracy" at "in-segment search" is a key insight for using Milvus well, and reaffirms the throughline: <strong>the real work happens in the
segment; the merge only honestly assembles</strong>.</p>

<p>To spell out "why deep paging is so pricey": to return ranks 10000–10010, the system can't directly "jump" to rank 10000 — it must have every
layer first compute the <strong>top 10010</strong>, then discard the front, to take the slice you want. So the larger the offset, the more
candidates each layer moves and merges, and the cost balloons. This is why "turning many pages" is an anti-pattern in vector search; in practice
prefer an <strong>iterator</strong> taking a large result set by cursor order (Lesson 50) over forcing a huge offset. Grasp this and you'll
instinctively dodge the deep-paging trap when designing "fetch many results" features.</p>

<div class="card key"><div class="tag">📌 Key points</div>
<ul>
  <li><strong>Split</strong>: data cut into immutable segments spread over shards; a segment is the smallest unit of parallel search — the physical premise of horizontal scale and parallelism.</li>
  <li><strong>Search + combine</strong>: fan out to segments for local topKs, then merge in three levels (segment → node → Proxy); each passes up only K, so <strong>only K-scale crosses the network</strong>.</li>
  <li><strong>Mathematical guarantee</strong>: the union of local topKs necessarily contains the global topK, so "report only the cream" loses no correctness.</li>
  <li><strong>Make small blocks fast</strong>: per-segment ANN index + scalar filter pushdown, pruning as early and small as possible, avoiding "spread the slow across machines".</li>
  <li><strong>Tradeoff</strong>: recall is approximate (set by in-segment precision, not the merge); deep paging / oversized K are the few scale-sensitive operations to avoid.</li>
</ul></div>
""",
}


LESSON_55 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
为什么打开 Milvus 的源码，会看到 Go 和 C++ 两套代码并存，中间还夹着一层叫 cgo 的桥？这不是历史包袱，而是一个深思熟虑的设计：
<strong>把最吃性能的计算交给 C++，把分布式编排交给 Go，让两种语言各自做最擅长的事</strong>。这一课讲的，就是这条"两种语言、一套系统"的主线。</p>

<div class="card analogy"><div class="tag">🏎️ 打个比方</div>
<p>想象一支赛车队：车子的<strong>引擎</strong>是手工打造、压榨到极限的精密机器（C++ 内核），而包裹引擎的<strong>底盘、座舱、电子系统</strong>则要舒适、好维护、方便改装（Go 编排）。
你不会用打造引擎的方式去做座椅，也不会用做座椅的方式去造引擎——<strong>每一部分都用最适合它的工艺</strong>。Milvus 就是这样一台车：
C++ 的引擎负责"算得飞快"，Go 的底盘负责"调度得灵活"，cgo 则是把两者拧在一起的传动轴。</p></div>

<h2>目标：为什么要用两种语言</h2>
<p>一个分布式向量数据库，身上其实压着两类<strong>性质完全不同</strong>的活儿。一类是<strong>极致的数值计算</strong>：在上亿条向量里算距离、走索引、做归并——
这要榨干 CPU 的 SIMD 指令、用上 GPU、精细管理内存布局，对性能锱铢必较。另一类是<strong>复杂的分布式编排</strong>：节点之间收发 RPC、协调者调度任务、管理元数据与一致性——
这要的是高并发下的开发效率、成熟的网络生态、不容易写错的并发模型。<strong>没有哪一种语言能把这两件事都做到最好</strong>：纯 Go 跑不出手工调优的数值内核的速度，
纯 C++ 写起分布式编排又笨重、易错、迭代慢。Milvus 的选择很务实——<strong>哪类活儿，就用哪种语言</strong>。</p>

<p>如果硬要"一种语言走到底"，会怎样？假设全用 C++：你确实能把数值算到飞快，但写起协调者之间的 RPC、goroutine 那样的高并发调度、动态的元数据管理，
会被手动内存管理、繁琐的并发原语、漫长的编译反复拖累，迭代速度慢到难以演进一个活跃的分布式系统。反过来全用 Go：分布式逻辑写得飞快，
但一到"在亿级向量上算距离"，垃圾回收的停顿、缺乏对 SIMD/GPU 的贴身控制，会让性能差出一个数量级。<strong>两难之下，Milvus 干脆不二选一，
而是让两种语言在各自的主场作战。</strong></p>

<div class="card macro"><div class="tag">🗺️ 大图景</div>
<p>把系统按"语言"分层：上层是 <strong>Go</strong> 的世界——协调者、各类节点、RPC、调度、元数据；下层是 <strong>C++</strong> 的世界——segcore 内核与 Knowhere 索引库，
承包所有最重的计算；中间一层薄薄的 <strong>cgo</strong> 桥把两者连起来；还点缀着一点 <strong>Rust</strong>（tantivy 全文索引）。前面学过的每一个"快"，几乎都落在 C++ 那层；
每一个"调度、协调、容错"，几乎都落在 Go 那层。</p></div>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">Go</span><span class="name">编排层：协调者 / 节点 / RPC / 调度</span></div><div class="ld">分布式逻辑、并发、元数据——开发效率优先（第 9-13 课）</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">cgo</span><span class="name">语言桥（薄而关键）</span></div><div class="ld">粗粒度、零拷贝地把调用送进内核，并带上下文（第 34 课）</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">C++</span><span class="name">内核层：segcore + Knowhere</span></div><div class="ld">过滤 / 检索 / 归并 / 列式 / SIMD / GPU——性能优先（第 22/27/34 课）</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">Rust</span><span class="name">tantivy 全文索引</span></div><div class="ld">BM25 全文，被 C++ 调用（第 24 课）</div></div>
</div>

<h2>热路径在 C++：把最重的算到极致</h2>
<p>哪些活儿被划进 C++ 内核？答案是<strong>一切最吃性能的计算</strong>。QueryNode 加载段之后，每次检索都经 cgo 调进 <strong>segcore</strong>：由 expr/exec 做标量过滤、
由 index 模块走 ANN 检索、由 reduce 收敛出段内 topK（第 27、28、29 课全在这一层）。而真正的向量索引算法（HNSW、IVF、PQ……）则来自专门的 <strong>Knowhere</strong> 库
（它统一封装了 Faiss、HNSWlib、DiskANN、cuVS 等，第 22 课）。为什么非 C++ 不可？因为这一层要做的事——<strong>精细的内存布局、列式分块、SIMD 向量化、GPU 加速</strong>——
都需要贴着硬件编程，而 C++ 正是这种"榨干机器"的语言。把段的数据布局、距离计算、索引类型这些<strong>最关键的数据结构与算法只实现一次</strong>，
查询时用它、建索引时也用它，这正是 Milvus "快"的底层来源。</p>

<p>这里还有一个常被忽略的妙处：C++ 内核<strong>同时服务"查询"和"建索引"两条路径</strong>（第 34 课）。查询时，QueryNode 调进来做过滤、检索、归并；
建索引时，建索引的 worker 也调进来，把一个段的原始向量交给 Knowhere 做成索引。换句话说，无论"读"还是"建索引"，最重的那部分计算都落在
<strong>同一套 C++ 内核</strong>里——关键的数据结构与算法只实现一次、两边复用，既省事、又不会出现"两套代码算得不一致"的隐患。
把易变、专门的算法收进 Knowhere，把稳定的系统骨架留在 Go，是另一层"让专业的归专业"。</p>

<p>那"贴着硬件编程"到底意味着什么？举几个具体的：把向量按<strong>列式</strong>摆放，让一次距离计算能连续读取内存、对缓存友好；
用 <strong>SIMD</strong> 指令一条指令同时算多个维度的乘加；把热数据按 <strong>mmap</strong> 摊在内存里、冷数据留在磁盘；需要时再把整批向量丢上 <strong>GPU</strong> 并行。
这些手段，每一个都要求对内存布局和指令集有精细的掌控——这恰恰是 C++（以及它背后成熟的数值计算生态）的看家本领，也是 Go 这类带垃圾回收、抽象层更高的语言难以企及的。</p>

<h2>编排在 Go：把分布式做得灵活</h2>
<p>那 Go 负责什么？<strong>把这台机器组织成一个集群</strong>。协调者（rootcoord / datacoord / querycoord）做调度、定序、管元数据；各类节点
（proxy / querynode / datanode / streamingnode）收发请求、消费日志、加载段（第 9-13 课）。这些活儿的共同点是：<strong>并发多、网络重、要快速迭代、还要容错</strong>。
Go 在这里如鱼得水——goroutine 让高并发代码写起来简单，gRPC 生态成熟，垃圾回收省去手动内存管理的心智负担，编译快、还能部署成一个二进制（第 42 课）。
如果硬要用 C++ 写这一层，开发效率会断崖式下降、并发 bug 会层出不穷。<strong>把分布式逻辑交给 Go，等于把"人写代码的效率"也当成一种要优化的资源。</strong></p>

<p>具体到代码体验，这种分工的好处立竿见影。Go 的 goroutine 让"同时处理成千上万个连接、并发消费多个日志分片"这类代码写起来几乎是顺手的事，
而在 C++ 里实现等价的并发，往往要小心翼翼地玩线程池、锁和回调，bug 还防不胜防。垃圾回收虽然带来一点停顿，但它把"谁该释放这块内存"这个分布式系统里最容易出错的问题直接消解掉了。
再加上一条命令编译、产物是单个静态二进制——部署、灰度、回滚都简单。<strong>这些"不起眼的开发效率"，累加起来就是一个能持续快速演进的系统。</strong></p>

<div class="cols">
  <div class="col"><h4>🔧 Go 最擅长</h4><p>高并发（goroutine）、成熟网络生态（gRPC）、垃圾回收省心、编译快、单二进制——适合<strong>分布式编排、调度、容错、快速迭代</strong>。</p></div>
  <div class="col"><h4>⚡ C++ 最擅长</h4><p>贴硬件的内存布局、SIMD / GPU、零开销抽象——适合<strong>极致数值计算：算距离、走索引、做归并</strong>。</p></div>
</div>

<div class="flow">
  <div class="node"><div class="nt">QueryNode（Go）</div><div class="nd">收到检索、整批参数</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">cgo 桥</div><div class="nd">一次粗粒度调用 · 零拷贝</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">segcore（C++）</div><div class="nd">批量算几千条向量</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">返回（Go）</div><div class="nd">拿回段内 topK</div></div>
</div>

<h2>桥要薄：cgo 的纪律</h2>
<p>两种语言之间的那座桥（cgo）不是免费的。每一次跨语言调用都有<strong>固定开销</strong>（栈切换、参数编排），而且 Go 的内存和 C++ 的内存<strong>互不认识</strong>，
长期持有对方的指针并不安全。所以 Milvus 给 cgo 立了铁律：<strong>粗粒度调用、零拷贝传数据</strong>——别一行一次地调，而是把<strong>一整段的检索打包成一次调用</strong>，
让 C++ 一口气算完几千条向量再返回；数据靠共享内存或直接传指针、避免来回拷贝（比如 mmap 的数据就直接被 C++ 读那块映射区）。把"跨桥次数"压到最少、
把"每次过桥的负载"做到最大，正是用好 cgo 的关键，也是为什么第 29 课强调"批量检索（大 nq）划算"——批越大，那点固定开销就摊得越薄。这座桥还不只传数据，
也传<strong>上下文</strong>：trace、超时、错误码都要跟着过去，跨语言的检索才不会在可观测性上"掉线"。</p>

<p>反过来看，如果违反了这条纪律会怎样？设想有人图省事，把检索写成"每比对一条向量就过一次 cgo 桥"——那么算一亿条向量，就要过一亿次桥，
每次那点固定开销累加起来，足以把性能拖垮到不可用。这正是"边界设计"成为性能隐形战场的原因：真正决定快慢的，往往不是某个算法，
而是<strong>你有没有把跨语言、跨网络、跨进程的边界设计成"少次数、大批量"</strong>。Milvus 在 cgo 这道边界上反复强调粗粒度与零拷贝，本质就是在守护这条性能生命线。</p>

<p>内存模型的割裂也值得多说一句。Go 有垃圾回收、会移动对象，C++ 手动管理、对象地址稳定——两边的指针不能随便交给对方长期持有，否则 GC 一动，
C++ 手里的指针就悬空了。所以 cgo 边界上传数据，要么拷贝一份过去（小数据可以，大数据太贵），要么用 C++ 这边分配、双方都能稳定访问的内存
（比如 mmap 区、或专门的缓冲区）。理解了这层约束，你就明白为什么 Milvus 的内核接口里，除了"查询参数"和"结果"，还总夹着一些不起眼的句柄、缓冲区和状态码——
它们正是让两套运行时安全协作的黏合剂。</p>

<h2>代价与取舍</h2>
<p>两种语言一套系统，代价主要有两块。其一，<strong>那座桥的开销与约束</strong>：cgo 调用有固定成本、内存模型割裂，逼着你把接口设计成"粗粒度、零拷贝、批量"——
这是一种持续的设计纪律，稍不注意就会让性能在边界处悄悄漏掉。其二，<strong>构建更复杂</strong>：要先用 conan/cmake 编出 C++ 库，再用 cgo 链接、编出 Go 二进制，
两段式构建（第 42 课）比纯 Go 项目门槛高得多。但换来的回报，是任何单一语言都给不了的：<strong>C++ 那层榨出了硬件的极限性能，Go 那层换来了分布式的开发效率与迭代速度</strong>，
还能在合适处引入 Rust（tantivy）这样更现代的工具。一句话：<strong>语言只是工具、不是信仰；让每一层都用最趁手的工具，正是 Milvus 既快又好演进的底层智慧。</strong></p>

<p>顺便回应一个常见的问题：既然追求极致性能，为什么内核不用 Rust？答案还是"历史与生态"。Milvus 起步时，向量检索成熟的内核库——尤其是 Knowhere/Faiss 这一脉——
和各种 GPU 计算工具链，几乎都是 C++ 的世界；用 C++ 写内核，能<strong>直接复用这些高性能积木</strong>，而不必重造轮子。后来 Milvus 也确实引入了一点 Rust
（第 24 课的 tantivy 全文索引就是 Rust 写、再包给 C++ 调用），说明它并不排斥更现代的语言——<strong>用什么、用在哪，只取决于哪个生态最成熟、哪种迁移最划算</strong>。
这正是"工具不是信仰"的最好注脚。</p>

<p>把这一课放回整个第十二部分来看，它和前几课其实是同一种智慧的不同侧面：日志即数据，是让"协作"收敛到一份共享日志；存算分离，是让"状态"收敛到共享存储；
而两种语言一套系统，是让"实现"各归其位、各用所长。它们共同指向一个朴素却深刻的工程原则——<strong>把复杂系统拆成边界清晰、各司其职的部分，再用尽量薄的接口把它们连起来</strong>。
读懂了这一点，你看 Milvus 就不再是一堆零件，而是一套贯通的设计哲学。</p>

<div class="card key"><div class="tag">📌 本课要点</div>
<ul>
  <li><strong>两类活儿</strong>：极致数值计算（算距离 / 索引 / 归并）vs 复杂分布式编排（RPC / 调度 / 元数据），没有单一语言能都做到最好。</li>
  <li><strong>热路径在 C++</strong>：segcore + Knowhere 承包过滤 / 检索 / 归并 + 列式 / SIMD / GPU，关键算法只实现一次。</li>
  <li><strong>编排在 Go</strong>：协调者与节点做调度、网络、容错——把"人写代码的效率"也当成一种资源来优化。</li>
  <li><strong>cgo 要薄</strong>：粗粒度、零拷贝、批量过桥，还要带上 trace / 超时 / 错误码等上下文；批越大固定开销摊越薄。</li>
  <li><strong>取舍</strong>：代价是桥的开销 + 两段式构建；回报是"硬件极限性能 + 分布式开发效率"的双赢，语言是工具不是信仰。</li>
</ul></div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Why does opening Milvus's source show Go and C++ side by side, with a layer called cgo wedged between? Not legacy baggage, but a deliberate
design: <strong>give the most performance-critical computation to C++, give distributed orchestration to Go, and let each language do what it's
best at</strong>. This lesson is about that "two languages, one system" throughline.</p>

<div class="card analogy"><div class="tag">🏎️ An analogy</div>
<p>Picture a racing team: the car's <strong>engine</strong> is a hand-built, squeezed-to-the-limit precision machine (the C++ kernel), while the
<strong>chassis, cockpit, and electronics</strong> wrapping it must be comfortable, maintainable, easy to modify (the Go orchestration). You
wouldn't build the seats the way you build the engine, nor build the engine the way you build the seats — <strong>each part uses the craft that
suits it</strong>. Milvus is exactly such a car: the C++ engine handles "compute blazingly fast", the Go chassis handles "schedule flexibly", and
cgo is the driveshaft bolting the two together.</p></div>

<h2>The goal: why two languages</h2>
<p>A distributed vector database actually carries two kinds of work of <strong>utterly different nature</strong>. One is <strong>extreme numeric
computation</strong>: computing distances, walking indexes, merging over hundreds of millions of vectors — squeezing the CPU's SIMD, using the
GPU, finely managing memory layout, every cycle counting. The other is <strong>complex distributed orchestration</strong>: nodes exchanging RPCs,
coordinators scheduling tasks, managing metadata and consistency — wanting development velocity under high concurrency, a mature networking
ecosystem, a concurrency model that's hard to get wrong. <strong>No single language does both best</strong>: pure Go can't match a hand-tuned
numeric kernel's speed, and pure C++ makes distributed orchestration clumsy, error-prone, slow to iterate. Milvus's choice is pragmatic —
<strong>whichever kind of work, use whichever language</strong>.</p>

<p>What if you forced "one language all the way"? Say all C++: you'd indeed compute numerics blazingly fast, but writing inter-coordinator RPC,
goroutine-style high-concurrency scheduling, and dynamic metadata management would be dragged down again and again by manual memory management,
fiddly concurrency primitives, and long compiles, iterating too slowly to evolve a living distributed system. Conversely, all Go: distributed
logic flies, but the moment you "compute distances over hundreds of millions of vectors", GC pauses and the lack of close control over SIMD/GPU
put performance an order of magnitude behind. <strong>Caught between the two, Milvus simply refuses to choose, letting each language fight on its
home turf.</strong></p>

<div class="card macro"><div class="tag">🗺️ The big picture</div>
<p>Layer the system by "language": the upper world is <strong>Go</strong> — coordinators, the various nodes, RPC, scheduling, metadata; the lower
world is <strong>C++</strong> — the segcore kernel and the Knowhere index library, taking on all the heaviest computation; a thin <strong>cgo</strong>
bridge in the middle joins them; with a dash of <strong>Rust</strong> (the tantivy full-text index). Almost every "fast" you've learned lands in
the C++ tier; almost every "schedule, coordinate, tolerate faults" lands in the Go tier.</p></div>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">Go</span><span class="name">orchestration: coordinators / nodes / RPC / scheduling</span></div><div class="ld">distributed logic, concurrency, metadata — dev velocity first (L9-13)</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">cgo</span><span class="name">the language bridge (thin but critical)</span></div><div class="ld">push calls into the kernel coarse-grained, zero-copy, carrying context (L34)</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">C++</span><span class="name">kernel: segcore + Knowhere</span></div><div class="ld">filter / search / reduce / columnar / SIMD / GPU — performance first (L22/27/34)</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">Rust</span><span class="name">tantivy full-text index</span></div><div class="ld">BM25 full-text, called by C++ (L24)</div></div>
</div>

<h2>The hot path in C++: compute the heaviest to the limit</h2>
<p>Which work is drawn into the C++ kernel? All the most performance-critical computation. After a QueryNode loads a segment, every search crosses
cgo into <strong>segcore</strong>: expr/exec does scalar filtering, the index module does ANN search, reduce converges the in-segment topK (Lessons
27, 28, 29 all happen in this tier). And the actual vector index algorithms (HNSW, IVF, PQ…) come from the dedicated <strong>Knowhere</strong>
library (which uniformly wraps Faiss, HNSWlib, DiskANN, cuVS, etc., Lesson 22). Why must it be C++? Because what this tier does — <strong>fine memory
layout, columnar chunking, SIMD vectorization, GPU acceleration</strong> — needs programming close to the hardware, and C++ is exactly that
"squeeze the machine" language. Implementing the segment's data layout, distance computation, and index types — the most critical data structures
and algorithms — <strong>only once</strong>, used at both query and index-build time, is the underlying source of Milvus's speed.</p>

<p>A frequently-overlooked beauty here: the C++ kernel <strong>serves both the "query" and "index-build" paths at once</strong> (Lesson 34). At
query time, the QueryNode calls in to filter, search, and merge; at index-build time, the build worker also calls in, handing a segment's raw
vectors to Knowhere to make an index. In other words, whether "read" or "build index", the heaviest computation lands in <strong>the same C++
kernel</strong> — the critical data structures and algorithms are implemented once and reused on both sides, saving effort and removing the
hazard of "two codebases computing inconsistently". Tucking the volatile, specialized algorithms into Knowhere and leaving the stable system
skeleton in Go is another layer of "let the specialists specialize".</p>

<p>So what does "programming close to the hardware" actually mean? A few concretes: laying vectors out <strong>columnar</strong> so one distance
computation reads memory contiguously, cache-friendly; using <strong>SIMD</strong> to multiply-add several dimensions per instruction; spreading
hot data in memory via <strong>mmap</strong> while cold stays on disk; and tossing whole batches of vectors onto the <strong>GPU</strong> when
needed. Each of these demands fine control over memory layout and instruction set — exactly C++'s forte (and that of the mature numeric-computing
ecosystem behind it), and exactly what a GC'd, higher-abstraction language like Go struggles to match.</p>

<h2>Orchestration in Go: make the distributed part flexible</h2>
<p>So what does Go handle? <strong>Organizing this machine into a cluster</strong>. Coordinators (rootcoord / datacoord / querycoord) schedule,
order, and manage metadata; the various nodes (proxy / querynode / datanode / streamingnode) exchange requests, consume the log, load segments
(Lessons 9-13). What these share: <strong>heavy concurrency, heavy networking, fast iteration, fault tolerance</strong>. Go thrives here —
goroutines make high-concurrency code simple, the gRPC ecosystem is mature, garbage collection removes the mental load of manual memory
management, compilation is fast, and it deploys as a single binary (Lesson 42). Force this tier into C++ and development velocity falls off a
cliff while concurrency bugs proliferate. <strong>Handing distributed logic to Go treats "the efficiency of humans writing code" as a resource to
optimize too.</strong></p>

<p>In day-to-day code, the dividend of this split is immediate. Go's goroutines make code like "handle thousands of connections at once,
concurrently consume several log shards" almost effortless, whereas implementing equivalent concurrency in C++ usually means gingerly juggling
thread pools, locks, and callbacks, with bugs hard to ward off. Garbage collection brings a little pause, but it dissolves outright "who should
free this memory", the most error-prone problem in a distributed system. Add one-command compilation into a single static binary — deploy,
canary, and rollback all simple. <strong>These "unglamorous bits of dev velocity", added up, are a system that can keep evolving fast.</strong></p>

<div class="cols">
  <div class="col"><h4>🔧 Go's forte</h4><p>high concurrency (goroutines), a mature networking ecosystem (gRPC), carefree GC, fast compiles, a single binary — suited to <strong>distributed orchestration, scheduling, fault tolerance, fast iteration</strong>.</p></div>
  <div class="col"><h4>⚡ C++'s forte</h4><p>hardware-hugging memory layout, SIMD / GPU, zero-overhead abstraction — suited to <strong>extreme numeric computation: distances, index walks, merging</strong>.</p></div>
</div>

<div class="flow">
  <div class="node"><div class="nt">QueryNode (Go)</div><div class="nd">receives the search, a whole batch of params</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">cgo bridge</div><div class="nd">one coarse-grained call · zero-copy</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">segcore (C++)</div><div class="nd">crunch thousands of vectors in a batch</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">return (Go)</div><div class="nd">get the in-segment topK back</div></div>
</div>

<h2>The bridge must be thin: cgo's discipline</h2>
<p>The bridge between the two languages (cgo) isn't free. Every cross-language call has a <strong>fixed overhead</strong> (stack switching,
argument marshaling), and Go's memory and C++'s memory <strong>don't recognize each other</strong> — holding the other's pointer long-term is
unsafe. So Milvus sets cgo an iron rule: <strong>coarse-grained calls, zero-copy data</strong> — don't call once per row, but <strong>pack a whole
segment's search into one call</strong>, letting C++ crunch thousands of vectors in one go before returning; data is passed by shared memory or
direct pointers, avoiding copying back and forth (mmap'd data, for instance, is read straight from the mapped region by C++). Keeping "the number
of crossings" minimal and "the payload per crossing" maximal is the key to using cgo well — and why Lesson 29 stresses that "batched search (large
nq) pays off": the bigger the batch, the thinner that fixed overhead is amortized. The bridge carries not just data but <strong>context</strong>:
trace, timeout, error codes must travel across too, so a cross-language search doesn't "go dark" on observability.</p>

<p>Conversely, what if you broke this discipline? Imagine someone, for convenience, writing a search as "cross the cgo bridge once per vector
compared" — then computing a hundred million vectors crosses the bridge a hundred million times, and that small fixed overhead, summed, is enough
to drag performance into the unusable. This is why "boundary design" is performance's hidden battlefield: what really decides speed is often not
some algorithm but <strong>whether you designed the cross-language, cross-network, cross-process boundaries as "few crossings, big
batches"</strong>. Milvus's repeated insistence on coarse-grained and zero-copy at the cgo boundary is, at heart, guarding this performance
lifeline.</p>

<p>The split memory model is worth one more word. Go has garbage collection and moves objects; C++ manages manually with stable object addresses
— neither side's pointer can be casually held by the other long-term, or once the GC moves things, the pointer C++ holds dangles. So passing data
across the cgo boundary either copies it over (fine for small data, too expensive for big) or uses memory allocated on the C++ side that both can
access stably (an mmap region, or a dedicated buffer). Grasp this constraint and you see why Milvus's kernel interfaces, besides "query params"
and "results", are always dotted with unassuming handles, buffers, and status codes — they are the glue that lets the two runtimes cooperate
safely.</p>

<h2>The payoff and the tradeoff</h2>
<p>Two languages, one system, costs you mainly two things. First, <strong>the bridge's overhead and constraints</strong>: cgo calls have a fixed
cost and a split memory model, forcing you to design interfaces as "coarse-grained, zero-copy, batched" — a continuous design discipline, and a
moment's inattention lets performance quietly leak at the boundary. Second, <strong>a more complex build</strong>: you must first compile the C++
libs with conan/cmake, then link via cgo and compile the Go binary, a two-stage build (Lesson 42) far higher-friction than a pure-Go project. But
the reward is what no single language can give: <strong>the C++ tier squeezes the hardware's limit performance, the Go tier buys distributed
development velocity and iteration speed</strong>, and you can bring in a more modern tool like Rust (tantivy) where it fits. In one line:
<strong>a language is a tool, not a faith; letting every tier use the handiest tool is the underlying wisdom behind Milvus being both fast and
easy to evolve.</strong></p>

<p>To answer a common question in passing: if it's peak performance you want, why not Rust for the kernel? Again, "history and ecosystem". When
Milvus started, the mature vector-search kernel libraries — especially the Knowhere/Faiss lineage — and the various GPU compute toolchains were
almost entirely a C++ world; writing the kernel in C++ <strong>reuses those high-performance building blocks directly</strong> instead of
reinventing them. Milvus did later bring in a little Rust (Lesson 24's tantivy full-text index is written in Rust and wrapped for C++ to call),
showing it isn't hostile to more modern languages — <strong>what to use, and where, depends only on which ecosystem is most mature and which
migration is cheapest</strong>. That is the best footnote to "a tool, not a faith".</p>

<p>Put this lesson back into Part 12 as a whole, and it's a different facet of the same wisdom as the lessons before: log as data converges
"collaboration" onto one shared log; storage-compute separation converges "state" onto shared storage; and two-languages-one-system lets
"implementation" each go to its place and play to its strength. Together they point at one plain yet profound engineering principle —
<strong>split a complex system into parts with clear boundaries and distinct duties, then connect them with the thinnest possible
interfaces</strong>. Grasp this and Milvus stops being a pile of parts and becomes one coherent design philosophy.</p>

<div class="card key"><div class="tag">📌 Key points</div>
<ul>
  <li><strong>Two kinds of work</strong>: extreme numeric computation (distances / index / merge) vs complex distributed orchestration (RPC / scheduling / metadata) — no single language does both best.</li>
  <li><strong>Hot path in C++</strong>: segcore + Knowhere take on filter / search / merge + columnar / SIMD / GPU, the critical algorithms implemented only once.</li>
  <li><strong>Orchestration in Go</strong>: coordinators and nodes do scheduling, networking, fault tolerance — treating "the efficiency of humans writing code" as a resource to optimize.</li>
  <li><strong>cgo must be thin</strong>: coarse-grained, zero-copy, batched crossings, carrying context (trace / timeout / error codes); the bigger the batch, the thinner the fixed overhead.</li>
  <li><strong>Tradeoff</strong>: the cost is the bridge's overhead + a two-stage build; the reward is a win-win of "hardware-limit performance + distributed dev velocity" — a language is a tool, not a faith.</li>
</ul></div>
""",
}


LESSON_56 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
走到最后一课。前面五条设计主线——日志、时间戳、存算分离、分而治之、两种语言——讲的都是"<strong>正常时怎么又快又对</strong>"。
可分布式系统真正的考验，从来不在正常时，而在<strong>出故障时</strong>。这一课，也是全书的收尾，讲 Milvus 最后一条、也最能体现其韧性的主线：<strong>故障是常态，系统要能自愈</strong>。</p>

<div class="card analogy"><div class="tag">⚡ 打个比方</div>
<p>想象一座城市的电网：它从设计之初就<strong>假定"总会有某个变电站坏掉"</strong>，所以一旦某处断电，电流会<strong>自动绕开故障点重新路由</strong>，居民几乎无感。
它不是"祈祷永不出故障"，而是"<strong>把出故障当成正常运行的一部分</strong>"，提前把自愈能力建进骨子里。
Milvus 对待节点宕机、网络抖动、进程崩溃，正是这种电网式的态度——<strong>故障不是异常，而是默认</strong>。</p></div>

<h2>目标：为什么要"假定故障"</h2>
<p>在一台机器上跑的程序，崩溃是小概率事件；可一旦你有几十、上百个节点，"<strong>此刻总有某个东西正在坏</strong>"几乎是必然——磁盘会坏、网络会抖、进程会被 OOM 杀掉、机器会被重启。
如果一个系统是按"一切正常"的乐观假设写的，那么任何一次故障都可能让它丢数据、或者卡死。Milvus 反其道而行：<strong>从设计之初就假定故障会发生</strong>，
并为此把三件事提前准备好——<strong>崩了不丢已提交的数据、坏了能自动回到该有的样子、挂了能被及时发现并接管</strong>。把"故障"当成必须处理的正常输入、而不是意外，
正是大规模系统能长期稳定运行的前提。</p>

<p>举个反例你就懂"乐观假设"有多脆：设想某系统在内存里维护着"哪个节点持有哪个段"的关键信息，却没把它持久化。平时一切正常，
可一旦协调者进程重启，这份信息就凭空蒸发——它再也不知道数据在哪、谁该干什么，整个集群直接瘫痪。这类"<strong>只在 happy path 上能跑</strong>"的设计，
规模小的时候也许侥幸无事，规模一大、故障一来就原形毕露。Milvus 把关键状态持久化进 etcd、把数据持久化进对象存储与 WAL，
正是为了让"重启""宕机"这些必然发生的事，变成无足轻重的小事。</p>

<div class="card macro"><div class="tag">🗺️ 大图景</div>
<p>把"自愈"拆成三层能力：① <strong>不丢</strong>——靠 WAL + 检查点 + 重放，已提交的写入永远能被找回；
② <strong>对账</strong>——靠协调者持续比对"<strong>该有的样子</strong>"与"<strong>实际的样子</strong>"，发现偏差就纠正（重建索引、重分配段）；
③ <strong>感知与接管</strong>——靠 etcd 的 session / lease 发现谁活着、谁挂了，再把活儿交给别人。这三层，恰好串起了前面所有课讲过的容错机制。</p></div>

<div class="flow">
  <div class="node"><div class="nt">节点宕机</div><div class="nd">进程崩 / 机器挂</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">租约过期</div><div class="nd">etcd session 失效、被发现</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">重新分配</div><div class="nd">协调者把它的段/任务派给别人</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">重载 + 重放</div><div class="nd">新节点从对象存储 / 日志恢复</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">恢复服务</div><div class="nd">一个字节不丢</div></div>
</div>

<h2>第一道防线：已提交的，永不丢失</h2>
<p>自愈的底线是<strong>不丢数据</strong>。这一层完全建立在第 51 课"日志即数据"之上：写入只要进了 WAL 就算成功，而 WAL 是可靠存储、可重放的。
于是任何节点崩溃，恢复都退化成同一个动作——<strong>从检查点（checkpoint）继续重放日志</strong>（第 16、31 课）：节点记着自己消费到哪了，挂了之后接手者从那个位置接着读，
缺的部分自然补齐，崩溃前后的世界完全一致。更进一步，<strong>跨集群复制</strong>还在异地保留了一份同样可重放的副本（第 33 课），连"整个机房没了"这种灾难，也能靠备集群顶上。
<strong>因为真相是一条可靠的日志，"恢复"就永远只是"再读一遍"，而不是"想办法把丢的数据找回来"</strong>。</p>

<p>对比一下两种"恢复"的心智，差别就很刺眼。在没有可靠日志的系统里，"丢了数据怎么办"是个开放式难题——你得想各种补偿、对照、人工介入，还未必补得齐。
而在 Milvus 里，"恢复"是一个<strong>确定性、可重复</strong>的动作：从检查点重放同一段日志，结果一定和崩溃前一致，既不需要灵光一现，也不需要运维半夜起来救火。
<strong>把"恢复"从一门玄学变成一条流水线</strong>，正是"日志即数据"在容错维度上最大的馈赠。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>正常消费</h4><p>节点跟着日志前进，定期记下检查点（已消费到的位置）。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>崩溃</h4><p>进程挂了，内存里没落盘的状态全没了——但日志还在。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>从检查点重放</h4><p>接手者从上次检查点继续读日志，把崩溃时丢的部分重新算出来。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>追平</h4><p>重放到日志尾，状态与崩溃前完全一致，对外恢复服务。</p></div></div>
</div>

<h2>第二道防线：自动回到"该有的样子"</h2>
<p>光不丢还不够——故障常常让集群"<strong>偏离</strong>"该有的状态：某个段的索引没建完、某个节点该加载的段没加载。Milvus 的应对是<strong>对账（reconcile）</strong>：
协调者持续地比对"<strong>声明的目标状态</strong>"和"<strong>观测到的实际状态</strong>"，一发现偏差就自动纠正。比如 DataCoord 的 index inspector 会周期性巡检，
发现哪个 sealed 段还缺索引，就<strong>重新派发构建任务</strong>——所以一个 worker 建索引中途崩了也没关系，下一轮巡检会把它重新调度（第 21 课）。
再比如 QueryCoord 的 balancer，发现某节点挂了、它负责的段没人加载，就<strong>把这些段重新分配</strong>给活着的节点，新节点从对象存储重载即可（第 13、53 课）。
这种"<strong>声明目标 + 持续对账 + 可重入任务</strong>"的模式，正是云原生系统自愈的通用范式：你不需要为每种故障写一套专门的恢复逻辑，只要让系统<strong>不断地把现实拉回理想</strong>。</p>

<p>这种"对账"的思路，值得单独玩味。传统做法是"<strong>事件驱动</strong>"：发生了什么故障，就触发对应的处理逻辑——可故障的组合千变万化，
你永远写不全所有情况，漏掉一种就是一个潜在的死角。而"对账"是"<strong>状态驱动</strong>"：它不关心"发生了什么"，只关心"现在和该有的样子差多少"，然后把差距抹平。
无论中间经历了什么离奇的故障序列，只要系统持续地对账，最终都会收敛到正确状态。<strong>这种"不问过程、只看目标"的自愈，比为每种故障写专门补救要健壮得多，
也是 Kubernetes 等云原生系统共同的灵魂。</strong></p>

<p>要让"对账"成立，还有一个隐含要求：每个恢复动作都得是<strong>可重入（幂等）</strong>的。重新派发的建索引任务、重新分配的段加载，哪怕因为再次故障而重复执行，
也不能把状态搞乱——做两遍和做一遍结果一样。正因为每一步都幂等，系统才敢于"不确定上一次到底做没做完，那就再做一次"，对账循环也才能放心地一遍遍跑下去。
<strong>幂等 + 对账，是自愈能稳稳收敛而不越修越乱的关键。</strong></p>

<h2>第三道防线：及时发现，安全接管</h2>
<p>对账的前提，是<strong>知道谁活着、谁挂了</strong>。这靠 etcd 的 <strong>session 与 lease（租约）</strong>：每个节点上线时注册一个带租约的 session，并定期续约；
一旦它崩了、续不上约，租约到期，etcd 就让所有关注者知道"<strong>这个节点没了</strong>"（第 14 课），对账和重分配随即启动。而在"接管"这一步，还藏着一个微妙但关键的保证：
<strong>结构变更必须原子</strong>。如果一次建表只在一半分片上生效，集群就会对"这个集合到底存不存在"产生分裂的认知，比丢几条数据可怕得多。
所以 Milvus 用 <strong>Broadcaster</strong> 把 DDL 做成"全有或全无"的原子广播（第 32 课），杜绝"半生效"的脏状态。最后，连<strong>升级</strong>也被纳入"故障可控"的范畴：
索引引擎按"以最弱节点为准"协商版本，保证滚动升级期间新建的索引所有节点都能加载、服务不中断（第 23 课）。</p>

<p>把这三道防线连起来看一次完整的故障转移就很清楚了：某个 QueryNode 突然宕机 → 它的 etcd 租约续不上、到期失效，于是"它没了"这件事被所有关注者感知（<strong>感知</strong>）→
QueryCoord 发现它负责的段现在没人加载、偏离了目标状态，于是把这些段重新分配给活着的节点（<strong>对账</strong>）→ 新节点从对象存储把段重新加载、必要时从日志重放最新数据（<strong>不丢</strong>）→
几秒之内，服务恢复，用户几乎无感，一个字节也没丢。<strong>三道防线环环相扣，把一次本可能是灾难的宕机，化解成了一次悄无声息的自我修复。</strong></p>

<div class="cols">
  <div class="col"><h4>❌ 祈祷永不出故障</h4><p>按"一切正常"写代码、把故障当意外。结果：任何一次宕机 / 抖动都可能丢数据或卡死，规模越大越脆。</p></div>
  <div class="col"><h4>✅ 假定故障是常态</h4><p>把崩溃当正常输入：WAL 兜底不丢、对账自动纠偏、租约感知接管。故障只是"再读一遍 + 重分配一下"。</p></div>
</div>

<h2>全书收尾：六条主线，一种智慧</h2>
<p>到这里，整本书就讲完了。回头看 Milvus，它早已不是一堆零件，而是六条设计主线编织成的一张网：<strong>日志即数据</strong>让写入飞快、让恢复退化为重放；
<strong>时间戳</strong>让边写边查既新鲜又正确；<strong>存算分离</strong>让节点无状态、能弹性伸缩；<strong>分而治之</strong>让亿级向量也能毫秒检索；
<strong>两种语言</strong>让性能与开发效率兼得；<strong>故障自愈</strong>让这一切在真实世界的风雨里依然站得住。而这六条主线，背后其实是同一种工程智慧：
<strong>把复杂系统拆成边界清晰、各司其职的部分，用尽量薄而可靠的接口（一条日志、一个时间戳、一层存储、一道桥）把它们连起来，再假定每个部分都可能出错、让整体能够自愈。</strong>
读懂了这张网，你读懂的就不只是 Milvus，而是一整套构建大规模分布式系统的思维方式。愿它在你之后的工程路上，常被想起。</p>

<p>如果这份指南达到了它的目的，那么当你下一次面对任何一个大规模系统时，你看到的将不再是陌生术语的堆砌，而是一组可以追问的设计选择：
它的真相存在哪里？它怎么定序、怎么容错？它把什么和什么解耦了？又是用多薄的接口连起来的？<strong>带着这些问题去读任何系统，你就拥有了把复杂化为清晰的钥匙。</strong>
感谢你读到这里——旅程到此结束，但你的工程之路，才刚刚展开。</p>

<div class="card key"><div class="tag">📌 本课要点</div>
<ul>
  <li><strong>故障是默认</strong>：大规模下"总有东西在坏"，按乐观假设写的系统必然脆——要从设计之初假定故障。</li>
  <li><strong>不丢</strong>：WAL + 检查点 + 重放，已提交永不丢；恢复 = 从检查点再读一遍；跨集群复制再加异地保险。</li>
  <li><strong>对账</strong>：协调者持续比对目标 vs 实际、自动纠偏（索引重派、段重分配），靠可重入任务兜底。</li>
  <li><strong>感知与原子</strong>：session / lease 发现存活，Broadcaster 让 DDL 原子（杜绝半生效），索引版本协商保证滚动升级不中断。</li>
  <li><strong>取舍与收尾</strong>：代价是对账 / 检查点的额外开销与"最终而非瞬时"恢复；回报是持久、自愈、不停服——以及全书六条主线共同的工程智慧。</li>
</ul></div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The final lesson. The previous five throughlines — log, timestamp, storage-compute separation, divide-and-conquer, two languages — were all about
"<strong>how to be fast and correct when things are normal</strong>". But a distributed system's real test is never in the normal case; it's
<strong>when something fails</strong>. This lesson, which also closes the guide, is Milvus's last throughline, the one that best shows its
resilience: <strong>failure is the default, and the system must heal itself</strong>.</p>

<div class="card analogy"><div class="tag">⚡ An analogy</div>
<p>Picture a city's power grid: from the start it <strong>assumes "some substation will always fail"</strong>, so the moment power drops somewhere,
current <strong>automatically reroutes around the fault</strong>, residents barely noticing. It doesn't "pray to never fail" but "<strong>treats
failure as part of normal operation</strong>", building self-healing into its bones in advance. Toward node crashes, network jitter, and process
deaths, Milvus takes exactly this grid-like attitude — <strong>failure is not an exception but the default</strong>.</p></div>

<h2>The goal: why "assume failure"</h2>
<p>For a program on one machine, a crash is a rare event; but once you have dozens or hundreds of nodes, "<strong>at any moment something is
breaking</strong>" is all but certain — disks fail, networks jitter, processes get OOM-killed, machines get restarted. A system written on the
optimistic assumption that "all is well" can lose data or hang on any single failure. Milvus does the opposite: <strong>it assumes failure will
happen from the start</strong>, and prepares three things for it — <strong>a crash loses no committed data, a fault auto-returns to the intended
shape, a death is detected and taken over in time</strong>. Treating "failure" as a normal input that must be handled, not an accident, is the
premise of a large system running stably for the long haul.</p>

<p>A counter-example shows how fragile "optimistic assumptions" are: imagine a system keeping the critical info "which node holds which segment"
in memory but not persisting it. All's well in normal times, but the moment a coordinator process restarts, that info vanishes into thin air — it
no longer knows where data is or who should do what, and the whole cluster seizes up. Such "<strong>only runs on the happy path</strong>" designs
may get away with it at small scale, but show their true colors the moment scale grows and a failure hits. Milvus persists critical state into etcd
and data into object storage and the WAL precisely to turn inevitable events like "restart" and "crash" into trivialities.</p>

<div class="card macro"><div class="tag">🗺️ The big picture</div>
<p>Split "self-healing" into three capabilities: ① <strong>don't lose</strong> — via WAL + checkpoint + replay, committed writes can always be
recovered; ② <strong>reconcile</strong> — via coordinators continuously comparing "<strong>the intended shape</strong>" with "<strong>the actual
shape</strong>", correcting any divergence (rebuild indexes, reassign segments); ③ <strong>detect and take over</strong> — via etcd's session/lease
to find who's alive and who's dead, then hand the work to someone else. These three tie together every fault-tolerance mechanism the earlier
lessons taught.</p></div>

<div class="flow">
  <div class="node"><div class="nt">node dies</div><div class="nd">process crash / machine down</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">lease expires</div><div class="nd">etcd session lapses, detected</div></div>
  <div class="arrow">→</div>
  <div class="node hl"><div class="nt">reassign</div><div class="nd">coordinator hands its segments/tasks to others</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">reload + replay</div><div class="nd">a new node recovers from object storage / log</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">service restored</div><div class="nd">not a byte lost</div></div>
</div>

<h2>First line of defense: the committed is never lost</h2>
<p>Self-healing's floor is <strong>losing no data</strong>. This layer rests entirely on Lesson 51's "log as data": a write counts as success once
in the WAL, and the WAL is reliably stored and replayable. So any node crash, recovery degenerates into the same action — <strong>resume replaying
the log from the checkpoint</strong> (Lessons 16, 31): a node records how far it consumed, its successor resumes reading from there, the missing
part fills back in, and the world before and after the crash is identical. Further, <strong>cross-cluster replication</strong> keeps an equally
replayable copy off-site (Lesson 33), so even a disaster like "the whole datacenter is gone" can be carried by the backup cluster. <strong>Because
the truth is a reliable log, "recovery" is forever just "read it again", never "figure out how to retrieve lost data"</strong>.</p>

<p>Contrast the two mindsets of "recovery" and the difference is stark. In a system without a reliable log, "what do we do about lost data" is an
open-ended hard problem — you must devise all kinds of compensation, reconciliation, manual intervention, and may still not patch it whole. In
Milvus, "recovery" is a <strong>deterministic, repeatable</strong> action: replay the same stretch of log from the checkpoint and the result is
necessarily identical to before the crash, needing no flash of insight nor ops staff up at midnight firefighting. <strong>Turning "recovery" from a
dark art into an assembly line</strong> is the greatest gift of "log as data" on the fault-tolerance axis.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>normal consumption</h4><p>the node advances along the log, periodically recording a checkpoint (how far it consumed).</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>crash</h4><p>the process dies; un-flushed in-memory state is gone — but the log remains.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>replay from the checkpoint</h4><p>the successor resumes reading the log from the last checkpoint, recomputing what was lost at the crash.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>catch up</h4><p>replaying to the log's tail, state is identical to before the crash; service resumes.</p></div></div>
</div>

<h2>Second line of defense: auto-return to the intended shape</h2>
<p>Not losing isn't enough — failure often makes a cluster <strong>diverge</strong> from its intended state: some segment's index isn't built, some
node hasn't loaded the segments it should. Milvus's answer is <strong>reconcile</strong>: coordinators continuously compare "<strong>the declared
target state</strong>" with "<strong>the observed actual state</strong>" and auto-correct any divergence. For instance, DataCoord's index inspector
periodically sweeps and, finding a sealed segment still lacking an index, <strong>re-dispatches the build task</strong> — so a worker crashing
mid-build is fine; the next sweep reschedules it (Lesson 21). Or QueryCoord's balancer, finding a node dead and its segments unloaded,
<strong>reassigns those segments</strong> to living nodes, which reload them from object storage (Lessons 13, 53). This "<strong>declare a target +
continuous reconcile + idempotent tasks</strong>" pattern is the universal paradigm of cloud-native self-healing: you needn't write a dedicated
recovery routine for each failure, only let the system <strong>keep pulling reality back toward the ideal</strong>.</p>

<p>This "reconcile" mindset deserves its own savor. The traditional approach is "<strong>event-driven</strong>": whatever failure happens triggers
the corresponding handling logic — but failure combinations are endlessly varied, you can never write them all, and missing one is a potential
blind spot. "Reconcile" is "<strong>state-driven</strong>": it doesn't care "what happened", only "how far now diverges from the intended shape",
then erases the gap. Whatever bizarre failure sequence occurred in between, as long as the system keeps reconciling, it eventually converges to the
correct state. <strong>This "don't ask the process, only the goal" self-healing is far more robust than writing dedicated remedies for each failure,
and is the shared soul of cloud-native systems like Kubernetes.</strong></p>

<p>For "reconcile" to hold, there's an implicit requirement: each recovery action must be <strong>idempotent</strong>. A re-dispatched index-build
task, a reassigned segment load — even if a further failure makes them execute again, must not scramble state: doing it twice equals doing it once.
Because every step is idempotent, the system dares to "not be sure whether last time finished, so just do it again", and the reconcile loop can
safely run round after round. <strong>Idempotency + reconcile is the key to self-healing converging steadily rather than fixing itself into ever
more chaos.</strong></p>

<h2>Third line of defense: detect in time, take over safely</h2>
<p>Reconcile's premise is <strong>knowing who's alive and who's dead</strong>. That rides on etcd's <strong>session and lease</strong>: each node, on
coming online, registers a leased session and renews it periodically; once it crashes and can't renew, the lease expires and etcd lets all watchers
know "<strong>this node is gone</strong>" (Lesson 14), whereupon reconcile and reassignment kick in. And in the "take over" step hides a subtle but
crucial guarantee: <strong>structural changes must be atomic</strong>. If a create-collection takes effect on only half the shards, the cluster splits
on "does this collection even exist", far scarier than losing a few rows. So Milvus uses the <strong>Broadcaster</strong> to make DDL an
"all-or-nothing" atomic broadcast (Lesson 32), abolishing the "half-applied" dirty state. Finally, even <strong>upgrades</strong> fall under
"failure kept controllable": the index engine negotiates a version "deferring to the weakest node", guaranteeing that during a rolling upgrade every
node can load newly-built indexes and service isn't interrupted (Lesson 23).</p>

<p>String the three lines of defense together for one complete failover and it's clear: a QueryNode suddenly dies → its etcd lease can't renew and
expires, so "it's gone" is perceived by all watchers (<strong>detect</strong>) → QueryCoord finds its segments now unloaded, diverged from the
target state, and reassigns them to living nodes (<strong>reconcile</strong>) → the new node reloads the segments from object storage, replaying the
latest data from the log if needed (<strong>don't lose</strong>) → within seconds service recovers, users barely noticing, not a byte lost.
<strong>The three interlocking lines of defense dissolve what could have been a disastrous outage into a silent act of self-repair.</strong></p>

<div class="cols">
  <div class="col"><h4>❌ Pray never to fail</h4><p>Code on the "all is well" assumption, treating failure as an accident. Result: any single crash / jitter may lose data or hang, more fragile the larger you scale.</p></div>
  <div class="col"><h4>✅ Assume failure is the default</h4><p>Treat a crash as normal input: WAL backstops loss, reconcile auto-corrects, leases detect and take over. A failure is just "read again + reassign".</p></div>
</div>

<h2>Closing the guide: six throughlines, one wisdom</h2>
<p>And with that, the whole guide is done. Looking back, Milvus was long since not a pile of parts but a web woven from six design throughlines:
<strong>log as data</strong> makes writes fast and degenerates recovery into replay; <strong>the timestamp</strong> makes query-while-write both fresh
and correct; <strong>storage-compute separation</strong> makes nodes stateless and elastic; <strong>divide-and-conquer</strong> lets billions of
vectors still be searched in milliseconds; <strong>two languages</strong> win both performance and dev velocity; <strong>failure self-healing</strong>
lets all of it stand firm in the real world's storms. And behind these six is one and the same engineering wisdom: <strong>split a complex system
into parts with clear boundaries and distinct duties, connect them with the thinnest, most reliable interfaces possible (one log, one timestamp,
one storage tier, one bridge), then assume every part may fail and let the whole heal itself.</strong> Grasp this web and what you've understood is
not just Milvus, but a whole way of thinking about building large-scale distributed systems. May it be remembered often on the engineering road
ahead.</p>

<p>If this guide has done its job, then the next time you face any large-scale system, what you see will no longer be a heap of unfamiliar jargon
but a set of design choices you can interrogate: where does its truth live? How does it order, how does it tolerate faults? What did it decouple
from what? And with how thin an interface did it connect them? <strong>Read any system with these questions and you hold the key to turning
complexity into clarity.</strong> Thank you for reading this far — the journey ends here, but your own engineering road is only just unfolding.</p>

<div class="card key"><div class="tag">📌 Key points</div>
<ul>
  <li><strong>Failure is the default</strong>: at scale "something is always breaking", so a system written on optimistic assumptions is inevitably fragile — assume failure from the start.</li>
  <li><strong>Don't lose</strong>: WAL + checkpoint + replay, the committed is never lost; recovery = read again from the checkpoint; cross-cluster replication adds off-site insurance.</li>
  <li><strong>Reconcile</strong>: coordinators continuously compare target vs actual and auto-correct (re-dispatch indexes, reassign segments), backstopped by idempotent tasks.</li>
  <li><strong>Detect & atomicity</strong>: session/lease detect liveness, the Broadcaster makes DDL atomic (no half-applied state), index version negotiation keeps rolling upgrades uninterrupted.</li>
  <li><strong>Tradeoff & closing</strong>: the cost is reconcile/checkpoint overhead and "eventual, not instant" recovery; the reward is durability, self-healing, no downtime — and the shared engineering wisdom of all six throughlines.</li>
</ul></div>
""",
}
