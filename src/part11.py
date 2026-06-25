"""Content for Part 11 (Advanced topics, optional reading). Lessons 47-50.

Bilingual {"zh","en"} dicts mirroring part1-10. These cover production
capabilities that sit beyond the core engine path: bulk import (a second write
path), multi-vector hybrid search & reranking, quota/rate-limiting/backpressure,
and a tour of RBAC / resource groups / databases / iterators / TTL / functions.
Facts verified against internal/proxy/task_import.go, internal/datacoord/import_*,
internal/datanode/importv2, internal/util/importutilv2, the HybridSearch +
RescoresNode path, quota_center.go + rate_limit_interceptor.go, and the
rootcoord RBAC / querycoord resource-group / function modules.
"""

LESSON_47 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前面第 4 部分讲的写入，是<strong>在线、流式</strong>的那条路：一行行经 Proxy → WAL → growing → flush。但当你要<strong>一次性灌进上亿行</strong>历史数据（迁移、离线建库）时，让每行都走 WAL 既慢又浪费。Milvus 为此准备了<strong>第二条写入路径</strong>——<strong>批量导入（bulk import）</strong>：直接读文件、<strong>绕过 WAL</strong>、由 DataCoord 编排一个多阶段<strong>导入作业</strong>，把整批数据<strong>直接生成段</strong>。这一课看这条"批量进货"通道怎么运作，以及它和流式写入的分工。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  把流式写入想成餐厅<strong>零点上菜</strong>：客人一道道点，厨房一道道做、一道道端——<strong>实时、灵活</strong>，但一次只走一份。批量导入则像给仓库<strong>整车进货</strong>：一卡车货拉到后门，<strong>不走前厅点单流程</strong>，直接清点、上架、登记入库。
  你不会用"零点上菜"的方式去补一整仓库的货（太慢），也不会为了一位客人点一道菜去叫一整卡车。<strong>两条路各有各的场景</strong>：日常实时写入走流式（第 15–17 课），一次性海量灌库走批量导入。理解了"<strong>同一个库、两条进货通道</strong>"，你就明白为什么 Milvus 要单独做这套 import。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong>批量导入是绕过 WAL 的第二条写入路径——客户端调 <span class="mono">ImportV2</span>(<span class="inline">proxy/task_import.go</span>)，DataCoord 编排一个多阶段作业(<span class="inline">datacoord/import_*</span>)：Pending → PreImport(扫描/校验/估算) → Import(DataNode 读文件直接写段) → Sorting → IndexBuilding → 提交可见；文件读取由 <span class="inline">importutilv2</span> 支持 json/csv/numpy/parquet</strong>。它把"一次性海量灌库"做成一条专用的批处理流水线。
</div>

<p class="lead" style="font-size:1rem;color:var(--muted)">这一课是第 11 部分（进阶专题）的第一篇。前十部分讲透了 Milvus 的"主干"，这一部分补上几块"<strong>生产里很重要、但不属核心引擎</strong>"的拼图——先从这条容易被忽略、却几乎人人会用到的第二写入路径说起。</p>

<h2>为什么需要第二条写入路径</h2>
<p>第 15–17 课的流式写入，是为<strong>在线、持续</strong>的写入量身打造的：每条写入经 Proxy 打包、Append 进 WAL、由 StreamingNode 攒进 growing 段、再 flush 落盘。这套机制保证了<strong>实时可见、崩溃可恢复、读写共用一条有序日志</strong>——对"用户一边写、一边查"的在线场景堪称完美。但它有一个隐含前提：<strong>写入是"细水长流"的</strong>。</p>
<p>可现实里有另一类需求：<strong>一次性把一大批历史数据灌进来</strong>——从别的系统迁移过来、把离线算好的几亿条向量建成库、或定期批量回填。这种场景下，如果还让每一行都走 WAL，问题就来了：<strong>慢</strong>（每行都要序列化、Append、定序、消费），<strong>挤占在线写入</strong>（海量回填把 WAL 和 StreamingNode 堵死，正常实时写入跟着遭殃），还<strong>浪费</strong>（这些数据本来就是"一次写定、不再改"的，根本不需要 WAL 的实时性与可重放保险）。就像你不会用"零点上菜"的方式补满一仓库——<strong>批量场景需要批量工具</strong>。于是 Milvus 给出第二条路：<strong>批量导入</strong>，直接读文件、绕过 WAL、专为"大批量、离线、一次写定"优化。下面把两条路摆在一起。</p>

<p>这里要澄清一个常见误解：<strong>"绕过 WAL"不等于"不安全""会丢数据"</strong>。WAL 的核心价值，是为"<strong>实时、随时可能崩</strong>"的在线写入提供"<strong>先记日志、崩了重放</strong>"的保险（第 16 课）。但批量导入的场景<strong>性质完全不同</strong>：源数据<strong>本来就好端端地躺在文件里</strong>（对象存储上的 parquet 等），就算导入中途失败，<strong>源文件还在、重来一次即可</strong>，根本不需要 WAL 那套重放保险。换句话说，导入的"<strong>事实来源</strong>"是<strong>那批源文件本身</strong>，而不是 WAL。正因为有这个前提，批量导入才敢理直气壮地绕过 WAL、走捷径——它不是<strong>偷懒省掉了安全</strong>，而是<strong>这个场景本就不需要那一层</strong>。这是个很好的工程思维示范：<strong>一个机制（WAL）是为某种前提（实时、易失、唯一可信源在内存）服务的；当前提变了（离线、源文件可重读），就该大胆地为新场景选更合适的路</strong>，而不是教条地"凡写入必过 WAL"。看懂这一点，你就不会再担心"导入绕过 WAL 会不会不可靠"了。</p>

<div class="cols">
  <div class="col"><h4>流式写入（第 15–17 课）</h4><p>逐行经 Proxy → <strong>WAL</strong> → growing → flush。<strong>实时可见、可重放、读写共用日志</strong>。适合在线持续写入；但海量回填会又慢又挤占在线。</p></div>
  <div class="col"><h4>批量导入（本课）</h4><p>读文件 → <strong>绕过 WAL</strong> → 直接生成段 → 排序/建索引 → 提交。<strong>吞吐高、不挤占在线</strong>。适合迁移/离线建库/批量回填；不追求逐行实时。</p></div>
</div>

<h2>ImportV2 与导入作业</h2>
<p>批量导入从一个专门的 API 入口开始：<span class="mono">ImportV2</span>。客户端把"<strong>要导入哪些文件</strong>"（存在对象存储上的 json/csv/numpy/parquet 文件）告诉 Proxy，Proxy 侧由 <span class="inline">internal/proxy/task_import.go</span> 的 <span class="mono">importTask</span> 接住，转交给 <strong>DataCoord</strong>——注意，导入的<strong>编排大脑是 DataCoord</strong>（它本就是管段、管落盘、管建索引的协调者，第 12 课），由它来调度这件"把文件变成段"的批活，再自然不过。</p>

<div class="flow">
  <div class="node"><div class="nt">数据文件</div><div class="nd">对象存储上的 json/csv/numpy/parquet</div></div>
  <div class="arrow">ImportV2</div>
  <div class="node"><div class="nt">Proxy</div><div class="nd">importTask 接住、转交</div></div>
  <div class="arrow">编排</div>
  <div class="node hl"><div class="nt">DataCoord</div><div class="nd">多阶段作业状态机</div></div>
  <div class="arrow">派任务</div>
  <div class="node"><div class="nt">DataNode</div><div class="nd">读文件 → 直接写段(binlog)</div></div>
</div>
<p>DataCoord 不是把导入当成"一个动作"，而是当成一个<strong>有状态、多阶段的作业（Job）</strong>来管（代码在 <span class="inline">internal/datacoord/import_job.go</span>、<span class="mono">import_checker.go</span> 等）。这个作业有一台<strong>状态机</strong>：<span class="mono">Pending → PreImporting → Importing → Sorting → IndexBuilding → Uncommitted → Committing → 完成</span>（失败则进 <span class="mono">Failed</span>）。为什么要做成多阶段的作业、而不是一把梭？因为导入海量数据是个<strong>长时间、易失败</strong>的过程，拆成阶段才能<strong>断点续作、进度可查、失败可重试</strong>——这和第 21 课"按段建索引"的拆分智慧一脉相承：<strong>把一件大事拆成可调度、可恢复的小步</strong>。下面这条流水线，就是一次导入作业的完整旅程。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>PreImport（预导入）</h4><p>DataNode 先<strong>扫一遍文件</strong>：校验 schema 是否匹配、估算行数与分布（autoID 时尤其要估）。<strong>不写数据</strong>，相当于"开工前的清点与规划"。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Import（导入）</h4><p>DataNode 真正<strong>读文件、直接写进段</strong>（生成 binlog），<strong>绕过 WAL</strong>。这是搬运主力，按文件分配给多个 DataNode 并行干。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Sorting / IndexBuilding</h4><p>对导入的段<strong>排序</strong>（按主键/聚类，利于后续检索），再<strong>建索引</strong>（复用第 21–23 课的建索引链路）。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>提交可见</h4><p>一切就绪后<strong>原子提交</strong>，这批新段才正式<strong>对查询可见</strong>——要么全可见、要么都不可见，不会查到"灌了一半"的数据。</p></div></div>
</div>

<h2>两阶段的妙处：PreImport 与 Import 分开</h2>
<p>整条流水线里，最值得品味的是把 <strong>PreImport</strong> 和 <strong>Import</strong> <strong>拆成两段</strong>。直觉上你可能觉得"读文件写段，一步到位不就行了？"但 Milvus 偏要先<strong>空跑一遍</strong>（PreImport）：只<strong>扫描、校验、估算</strong>，不落任何数据。这一步在干什么？它在<strong>把风险和规划前置</strong>。</p>
<p>具体说，PreImport 会先确认<strong>文件能不能读、schema 对不对得上</strong>——如果你的 parquet 列和集合 schema 不匹配，这一步就能<strong>提前报错</strong>，而不是写到一半才发现、留下一堆半成品段要清理。它还会<strong>估算行数与数据分布</strong>：在 autoID（自增主键）场景下，系统需要预先知道"这批数据大概多少行、该怎么切段、该预分配多少主键 ID"，PreImport 的估算正是为正式 Import 阶段<strong>把段切得均匀、把资源备足</strong>。这种"<strong>先勘探、再施工</strong>"的两段式，是处理大批量、不确定输入时的经典工程手法：<strong>用一次廉价的预扫描，换取正式执行时的确定性与高效</strong>。一旦 PreImport 通过，Import 阶段就能<strong>放心大胆地并行搬运</strong>，因为该踩的雷已经在勘探阶段排掉了。这也呼应了第 44 课的 merr 哲学——<strong>能在边界上提前发现的"输入错误"，就别拖到深处才爆</strong>。</p>

<p>再往深看一层，PreImport 估算行数分布这件事，和 autoID 的关系尤其值得点破。回忆第 6 课：主键可以让 Milvus <strong>自增分配</strong>（autoID）。流式写入时，每行的自增主键是<strong>写一行发一个</strong>，顺理成章；但批量导入是<strong>一次灌一大批</strong>，系统必须<strong>预先知道这批有多少行</strong>，才能<strong>一次性预留出一整段连续的主键 ID 区间</strong>分给它们——否则多个 DataNode 并行写时，主键就可能<strong>撞号或留空洞</strong>。PreImport 的行数估算，正是为这件"预分配主键"的事打底。你看，一个看似简单的"先扫一遍"，背后牵动的是<strong>主键唯一性</strong>这条数据库的命根子。这也再次说明：<strong>批量与流式虽然产物相同，但"怎么安全地批量生产"本身是一门需要单独设计的学问</strong>——不能简单地把流式逻辑搬过来一灌了事。Milvus 把这些隐藏的复杂度，都收进了 import 作业这条专用流水线里，让你只需"告诉它文件在哪"，剩下的勘探、切段、分配、搬运、排序、建索引、提交，它替你一气呵成。</p>

<h2>它和流式写入怎么分工</h2>
<p>最后把两条写入路径的<strong>分工与协同</strong>讲清。它们<strong>共享同一套"段"的抽象</strong>（第 7 课）：无论数据是流式攒进 growing 再 flush 成的段，还是批量导入直接生成的段，<strong>最终都是对象存储里同样格式的 binlog 段</strong>，被 QueryNode 一视同仁地加载、检索。也就是说，批量导入<strong>不是另起炉灶</strong>，而是<strong>换一条更高效的路、生产出同样的产物</strong>——这正是它能无缝融入整个系统的原因。</p>

<p>这种"<strong>不同生产路径、相同最终产物</strong>"的设计，其实是个值得反复体会的架构智慧。试想另一种糟糕的设计：如果批量导入产出的是一种<strong>和流式段格式不同的"导入专用段"</strong>，那 QueryNode 就得<strong>认两种段、写两套加载与检索逻辑</strong>，整个读路径瞬间复杂一倍、还容易出 bug。Milvus 偏不——它让两条写入路径在<strong>"段"这个抽象上汇合</strong>：上游你爱怎么生产怎么生产（细水长流也好、整车卸货也罢），但<strong>交付给下游的，必须是同一种规格的段</strong>。这就像工厂里"<strong>不管哪条产线，下线的零件都得符合同一张图纸</strong>"——于是组装环节（QueryNode）才能对所有零件一视同仁。把"<strong>多样的生产</strong>"收敛到"<strong>统一的产物接口</strong>"，正是让一个系统能<strong>容纳多条路径却不失控</strong>的关键。你在第 22 课（索引交给 Knowhere 的统一接口）、第 36 课（算子统一吃一批吐一批）都见过这种审美，这里是它在<strong>写入路径</strong>上的又一次体现——而这，也正是第 11 部分想带你看到的：<strong>主干之外，Milvus 在每一处"该统一的地方统一、该分路的地方分路"的成熟权衡</strong>。</p>
<p>那实践中怎么选？<strong>在线、持续、要求实时可见</strong>的写入（用户应用的日常 insert）走<strong>流式</strong>；<strong>一次性、海量、离线、一次写定</strong>的灌库（数据迁移、批量回填、离线建库）走<strong>批量导入</strong>。很多生产部署是<strong>两者并用</strong>：先用一次大 import 把历史数据灌进来打底，再用流式写入承接此后的增量。理解了"<strong>同一个段抽象、两条生产路径</strong>"，你对 Milvus 写入侧的认识就完整了——它既能像水龙头一样接住实时细流，也能像卸货码头一样吞下整车批货。这正是一个成熟数据库该有的<strong>弹性</strong>。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>第二条写入路径</strong>：批量导入<strong>绕过 WAL</strong>，专为"大批量、离线、一次写定"优化；流式写入(第 15–17 课)则为在线实时写入而生，二者分工。</li>
    <li><strong>DataCoord 编排的作业</strong>：<span class="mono">ImportV2</span> → 多阶段状态机 <span class="mono">Pending→PreImport→Import→Sorting→IndexBuilding→提交</span>；拆阶段以便断点续作、进度可查、失败可重试。</li>
    <li><strong>PreImport vs Import</strong>：先空跑勘探(校验 schema、估算行数/分布，尤其 autoID)，再正式并行搬运(DataNode 读 json/csv/numpy/parquet 直接写段)。先勘探、再施工。</li>
    <li><strong>共享段抽象</strong>：导入产出的段与流式 flush 的段<strong>同格式</strong>，被 QueryNode 一视同仁加载；提交是<strong>原子的</strong>(全可见或都不可见)。生产常两者并用：import 打底 + 流式接增量。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The writes in Part 4 were the <strong>online, streaming</strong> path: row by row through Proxy → WAL → growing → flush. But when you must <strong>load hundreds of millions of rows at once</strong> (migration, offline base-loading), sending every row through the WAL is slow and wasteful. For this Milvus has a <strong>second write path</strong> — <strong>bulk import</strong>: read files directly, <strong>bypass the WAL</strong>, and have DataCoord orchestrate a multi-phase <strong>import job</strong> that turns whole batches <strong>directly into segments</strong>. This lesson covers that "by-the-truckload" channel and how it divides labor with streaming writes.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of streaming writes as <strong>à-la-carte service</strong>: guests order dish by dish, the kitchen makes and plates them one at a time — <strong>real-time, flexible</strong>, but one serving at a time. Bulk import is like <strong>restocking a warehouse by the truckload</strong>: a truck pulls up to the back, <strong>skipping the front-of-house ordering flow</strong>, and the goods are counted, shelved, and logged in directly.
  You wouldn't restock a whole warehouse "à la carte" (too slow), nor call a truck for one guest's dish. <strong>Each path has its scene</strong>: everyday real-time writes go streaming (Lessons 15–17); one-shot massive loading goes bulk import. Grasp "<strong>one database, two restocking channels</strong>" and you see why Milvus builds a separate import.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>bulk import is a second write path that bypasses the WAL — the client calls <span class="mono">ImportV2</span> (<span class="inline">proxy/task_import.go</span>), DataCoord orchestrates a multi-phase job (<span class="inline">datacoord/import_*</span>): Pending → PreImport (scan/validate/estimate) → Import (DataNode reads files straight into segments) → Sorting → IndexBuilding → commit-visible; file reading via <span class="inline">importutilv2</span> supports json/csv/numpy/parquet</strong>. It makes "one-shot massive loading" a dedicated batch pipeline.
</div>

<h2>Why a second write path</h2>
<p>The streaming writes of Lessons 15–17 are tailored for <strong>online, continuous</strong> ingestion: each write is packed by Proxy, appended to the WAL, buffered into a growing segment by the StreamingNode, then flushed. This guarantees <strong>real-time visibility, crash recovery, and a single ordered log shared by reads and writes</strong> — perfect for "write and query at the same time". But it assumes one thing: <strong>writes trickle in steadily</strong>.</p>
<p>Reality has another need: <strong>load one huge batch of historical data at once</strong> — migrating from another system, base-loading hundreds of millions of pre-computed vectors, or periodic batch backfills. Here, routing every row through the WAL causes trouble: it's <strong>slow</strong> (each row serialized, appended, ordered, consumed), it <strong>crowds out online writes</strong> (a massive backfill jams the WAL and StreamingNode, hurting normal real-time ingestion), and it's <strong>wasteful</strong> (this data is "written once, never changed" — it needs none of the WAL's real-time, replayable insurance). Just as you wouldn't restock a warehouse à la carte — <strong>batch scenarios need batch tools</strong>. So Milvus offers a second path: <strong>bulk import</strong>, reading files directly, bypassing the WAL, optimized for "large, offline, write-once". The two paths side by side:</p>

<div class="cols">
  <div class="col"><h4>Streaming writes (L15–17)</h4><p>row by row via Proxy → <strong>WAL</strong> → growing → flush. <strong>Real-time visible, replayable, log shared by reads/writes</strong>. For online continuous writes; but massive backfills are slow and crowd out online.</p></div>
  <div class="col"><h4>Bulk import (this lesson)</h4><p>read files → <strong>bypass the WAL</strong> → generate segments directly → sort/index → commit. <strong>High throughput, no crowding out online</strong>. For migration/offline base-loading/backfill; not for per-row real-time.</p></div>
</div>

<h2>ImportV2 and the import job</h2>
<p>Bulk import starts at a dedicated API entry: <span class="mono">ImportV2</span>. The client tells the Proxy <strong>which files to import</strong> (json/csv/numpy/parquet files sitting in object storage); on the Proxy side the <span class="mono">importTask</span> in <span class="inline">internal/proxy/task_import.go</span> catches it and hands it to <strong>DataCoord</strong> — note the <strong>orchestration brain is DataCoord</strong> (it already coordinates segments, flushing, and index building, Lesson 12), so scheduling this "turn files into segments" batch job is natural for it.</p>

<div class="flow">
  <div class="node"><div class="nt">data files</div><div class="nd">json/csv/numpy/parquet in object storage</div></div>
  <div class="arrow">ImportV2</div>
  <div class="node"><div class="nt">Proxy</div><div class="nd">importTask catches &amp; forwards</div></div>
  <div class="arrow">orchestrate</div>
  <div class="node hl"><div class="nt">DataCoord</div><div class="nd">multi-phase job state machine</div></div>
  <div class="arrow">dispatch</div>
  <div class="node"><div class="nt">DataNode</div><div class="nd">read files → write segments (binlog)</div></div>
</div>
<p>DataCoord treats an import not as "an action" but as a <strong>stateful, multi-phase job</strong> (code in <span class="inline">internal/datacoord/import_job.go</span>, <span class="mono">import_checker.go</span>, etc.). The job has a <strong>state machine</strong>: <span class="mono">Pending → PreImporting → Importing → Sorting → IndexBuilding → Uncommitted → Committing → done</span> (failures go to <span class="mono">Failed</span>). Why a multi-phase job rather than one shot? Because importing massive data is a <strong>long-running, failure-prone</strong> process, and splitting it into phases enables <strong>resumability, queryable progress, and retry on failure</strong> — the same wisdom as Lesson 21's "index per segment": <strong>break one big task into schedulable, recoverable steps</strong>. The pipeline below is the full journey of an import job.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>PreImport</h4><p>a DataNode first <strong>scans the files</strong>: validate schema match, estimate row count and distribution (especially under autoID). <strong>Writes no data</strong> — a "count-and-plan before work".</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Import</h4><p>DataNodes actually <strong>read files and write straight into segments</strong> (producing binlogs), <strong>bypassing the WAL</strong>. The main haul, split across DataNodes in parallel by file.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Sorting / IndexBuilding</h4><p><strong>sort</strong> the imported segments (by PK/clustering, aiding later search), then <strong>build indexes</strong> (reusing the Lesson 21–23 index pipeline).</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Commit to visible</h4><p>once everything's ready, an <strong>atomic commit</strong> makes the new segments <strong>visible to queries</strong> — all or nothing, so you never query a "half-loaded" batch.</p></div></div>
</div>

<h2>The beauty of two phases: PreImport vs Import</h2>
<p>The most savorable part of the pipeline is splitting <strong>PreImport</strong> from <strong>Import</strong>. Intuitively you might think "read files, write segments — just do it in one step?" But Milvus deliberately <strong>does a dry run first</strong> (PreImport): only <strong>scan, validate, estimate</strong>, writing no data. What is this step doing? It's <strong>front-loading risk and planning</strong>.</p>
<p>Concretely, PreImport first confirms <strong>the files are readable and the schema matches</strong> — if your parquet columns don't match the collection schema, this step <strong>errors early</strong>, instead of failing halfway and leaving a pile of half-built segments to clean up. It also <strong>estimates row count and distribution</strong>: under autoID (auto-increment primary keys), the system needs to know in advance "roughly how many rows, how to slice segments, how many PK IDs to pre-allocate", and PreImport's estimate lets the real Import phase <strong>slice segments evenly and reserve enough resources</strong>. This "<strong>survey first, then build</strong>" two-step is a classic engineering move for large, uncertain inputs: <strong>spend one cheap pre-scan to buy certainty and efficiency at execution time</strong>. Once PreImport passes, the Import phase can <strong>haul in parallel with confidence</strong>, because the mines were cleared during the survey. This echoes Lesson 44's merr philosophy — <strong>an "input error" catchable early at the boundary shouldn't be left to blow up deep inside</strong>.</p>

<h2>How it divides labor with streaming writes</h2>
<p>Finally, the <strong>division and cooperation</strong> of the two write paths. They <strong>share the same "segment" abstraction</strong> (Lesson 7): whether data was streamed into a growing segment then flushed, or bulk-imported straight into a segment, <strong>the end product is the same binlog-format segment in object storage</strong>, loaded and searched by QueryNodes alike. So bulk import <strong>isn't a separate world</strong> — it's <strong>a more efficient path producing the same product</strong>, which is why it slots seamlessly into the whole system.</p>
<p>How to choose in practice? <strong>Online, continuous, real-time-visible</strong> writes (an app's everyday insert) go <strong>streaming</strong>; <strong>one-shot, massive, offline, write-once</strong> loading (migration, batch backfill, offline base-loading) goes <strong>bulk import</strong>. Many production deployments <strong>use both</strong>: one big import to base-load historical data, then streaming writes to carry the incremental flow thereafter. Grasp "<strong>one segment abstraction, two production paths</strong>" and your view of Milvus's write side is complete — it can catch a real-time trickle like a tap, and swallow a truckload like a loading dock. That's the <strong>elasticity</strong> a mature database should have.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Second write path</strong>: bulk import <strong>bypasses the WAL</strong>, optimized for "large, offline, write-once"; streaming writes (L15–17) are built for online real-time ingestion — the two divide labor.</li>
    <li><strong>A DataCoord-orchestrated job</strong>: <span class="mono">ImportV2</span> → multi-phase state machine <span class="mono">Pending→PreImport→Import→Sorting→IndexBuilding→commit</span>; phased for resumability, queryable progress, retry on failure.</li>
    <li><strong>PreImport vs Import</strong>: a dry-run survey first (validate schema, estimate rows/distribution, esp. autoID), then parallel hauling (DataNodes read json/csv/numpy/parquet straight into segments). Survey first, then build.</li>
    <li><strong>Shared segment abstraction</strong>: imported segments are <strong>same-format</strong> as streamed-and-flushed ones, loaded alike by QueryNodes; the commit is <strong>atomic</strong> (all-visible or none). Production often uses both: import to base-load + streaming for the increment.</li>
  </ul>
</div>
""",
}

LESSON_48 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前面讲的检索，大多是"<strong>一个查询向量、在一个向量字段里找近邻</strong>"。但真实业务里，一次好的检索往往要<strong>综合多个信号</strong>：既看<strong>语义相似</strong>（稠密向量），又看<strong>关键词命中</strong>（稀疏向量 / BM25，第 24 课）；或者同时比对<strong>图像</strong>与<strong>文本</strong>两种 embedding。这就是<strong>混合检索（HybridSearch）</strong>：一个集合可以有<strong>多个向量字段</strong>，一次请求并行跑<strong>多路子搜索</strong>，再把多份结果<strong>融合（rerank）</strong>成一份最终排名。这一课看它怎么扇出、又怎么融合。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  把混合检索想成<strong>招聘时综合多个维度选人</strong>。同一批候选人，HR 会从几个角度各排一份榜：按"<strong>技能匹配</strong>"排一榜、按"<strong>过往经验</strong>"排一榜、按"<strong>文化契合</strong>"排一榜。每份榜单都有道理，但你最终要的是<strong>一份总排名</strong>。
  怎么把几份榜单<strong>融合</strong>成一份？有三种办法：只看每人在各榜的<strong>名次</strong>、名次靠前就加分（<strong>RRF</strong>）；给各榜不同<strong>权重</strong>、按加权分合并（<strong>加权融合</strong>）；或者请一位<strong>资深专家</strong>把入围者重新仔细面一遍、给出权威排序（<strong>模型重排</strong>）。混合检索做的，正是"<strong>多路打分 → 融合成一榜</strong>"这件事。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong>HybridSearch 在一个请求里带多路子搜索(<span class="mono">SubReqs</span>，各搜一个向量字段)，Proxy 扇出、各自得到一份 ranked 结果，再用一个 <span class="mono">ranker</span> 融合成最终 topK；ranker 有三类——RRF(按名次)、WeightedRanker(按加权分)、模型重排(<span class="inline">internal/util/function/rerank</span>，调外部 cross-encoder)</strong>。解析在 <span class="inline">proxy/task_search.go</span> 的 <span class="mono">parseRankParams</span> / <span class="inline">rerank_meta.go</span>。
</div>

<h2>为什么需要混合检索</h2>
<p>单一向量检索有个天生的局限：<strong>一种 embedding 只擅长抓一类信号</strong>。<strong>稠密向量</strong>（dense，第 4 课）擅长<strong>语义</strong>——"沙发"和"长椅"能匹配上，哪怕字面不同；但它对<strong>精确关键词</strong>不敏感——你搜一个具体型号"XJ-200"，语义向量可能反而抓不准。<strong>稀疏向量</strong>（sparse / BM25，第 24 课）正相反：它擅长<strong>关键词精确命中</strong>，却不懂语义近义。<strong>两者各有盲区，恰好互补</strong>。</p>

<div class="cols">
  <div class="col"><h4>稠密向量（dense）</h4><p>擅长<strong>语义</strong>：沙发≈长椅、医生≈大夫，字面不同也能匹配。盲区：对<strong>精确关键词/型号</strong>(XJ-200)不敏感。</p></div>
  <div class="col"><h4>稀疏向量（sparse / BM25）</h4><p>擅长<strong>关键词精确命中</strong>：搜什么词、命中什么词。盲区：不懂<strong>近义/语义</strong>，换个说法就漏。</p></div>
</div>
<p>于是一个很自然的想法冒出来：<strong>能不能两种都用，取长补短？</strong>这正是混合检索的动机。为支持它，Milvus 允许一个集合<strong>定义多个向量字段</strong>（第 6 课）——比如一个 <span class="mono">dense_vec</span> 存语义 embedding、一个 <span class="mono">sparse_vec</span> 存关键词权重。检索时，同一个查询<strong>同时打到这两个字段</strong>：稠密那路找语义最近的、稀疏那路找关键词最配的，最后<strong>融合</strong>。除了"语义+关键词"，混合检索还覆盖<strong>多模态</strong>（图像向量 + 文本向量一起搜）、<strong>多视角</strong>（同一对象的不同 embedding 模型）等场景。一句话：<strong>当"像不像"不能用单一标准衡量时，就把多个标准并起来、再融合</strong>——这是把向量检索从"玩具 demo"推向"真实业务"的关键一步。</p>

<p>这里值得点破一个 RAG（检索增强生成）时代特别常见的痛点，它正是混合检索大放异彩的舞台。当你用 LLM 做问答、给它喂检索来的上下文时，用户的提问<strong>既有语义、又常含关键术语</strong>：比如"<strong>2023 年 XJ-200 型号的退货政策</strong>"——"退货政策"是语义、"XJ-200""2023"是必须精确命中的关键词。<strong>纯语义检索可能召回一堆"退货政策"相关但型号不对的文档；纯关键词检索又可能因为换了个说法而错过最相关的那篇。</strong>只有把两路并起来、再融合，才能既<strong>抓住语义、又锁定关键词</strong>，把真正相关的文档顶到前面。这也是为什么近两年几乎所有正经的 RAG / 企业搜索方案，都把"<strong>dense + sparse 混合检索 + rerank</strong>"当成标配。理解了混合检索，你就握住了把 Milvus 用在生产级检索增强里的那把钥匙——它不再是"给个向量找近邻"的玩具，而是能<strong>综合多种相关性信号</strong>的真实检索引擎。</p>

<h2>一次 HybridSearch：多路子搜索</h2>
<p>机制上，一次混合检索<strong>不是一个搜索，而是一束搜索</strong>。客户端发来的 <span class="mono">HybridSearchRequest</span> 里带着一组<strong>子请求（<span class="mono">SubReqs</span>）</strong>——每个子请求就是一次<strong>普通的向量搜索</strong>：指定<strong>搜哪个向量字段、用什么查询向量、topK 多少、带什么过滤</strong>。Proxy 侧（<span class="inline">internal/proxy/task_search.go</span>）一看 <span class="mono">len(SubReqs) &gt; 0</span>，就知道这是"<strong>进阶（advanced）</strong>"的混合检索，于是把每个子请求<strong>当成一次独立搜索扇出去</strong>（复用第 25–29 课那整套查询链路），并行地各自跑完、各自<strong>归并出一份自己的 topK</strong>。</p>
<p>这里有个关键认知：<strong>每一路子搜索，本身就是一次完整的、你已经学过的向量检索</strong>。它一样经 delegator 扇到各段、一样 filter-then-search、一样三层 reduce（第 29 课）。所以混合检索<strong>没有另造一套检索引擎</strong>，而是<strong>把 N 次普通检索并起来跑、再加一道融合</strong>。这又是那个熟悉的设计哲学：<strong>用已有的、可组合的能力拼出新功能</strong>，而不是重起炉灶。子搜索的数量有上限（<span class="mono">defaultMaxSearchRequest</span>），免得一个请求扇出太多路把系统压垮。等所有子搜索都返回，Proxy 手里就有了 <strong>N 份各自排好的候选列表</strong>——接下来的问题是：<strong>怎么把这 N 份合成一份？</strong></p>

<p>顺带说一个容易忽略、却很影响效果的细节：<strong>每一路子搜索通常要多取一些候选</strong>。直觉上你可能觉得"我最终只要 top-10，那每路取 top-10 不就够了？"其实不然——因为融合会<strong>打乱名次</strong>：一个在语义榜排第 15、但在关键词榜排第 2 的文档，融合后很可能挤进最终 top-10；可如果每路只取了 top-10，它在语义那路<strong>压根没被取到</strong>，融合时就<strong>永远丢了</strong>。所以实践中，每路子搜索往往要取一个<strong>比最终 topK 更大的候选池</strong>（比如最终要 10、每路先取 50），给融合留足"翻盘"的余地。这是混合检索调参里最常踩的坑之一，也再次说明：<strong>融合不是简单地把几个 top-K 拼起来，而是要在更大的候选集上重新排序</strong>。理解这一点，你在用 Milvus 做混合检索时就能避开"召回莫名偏低"的暗坑。</p>

<div class="flow">
  <div class="node"><div class="nt">HybridSearch</div><div class="nd">一个请求，N 个 SubReqs</div></div>
  <div class="arrow">扇出</div>
  <div class="node hl"><div class="nt">子搜索：dense_vec</div><div class="nd">语义最近 → ranked 列表 A</div></div>
  <div class="node hl"><div class="nt">子搜索：sparse_vec</div><div class="nd">关键词最配 → ranked 列表 B</div></div>
  <div class="arrow">融合</div>
  <div class="node"><div class="nt">ranker</div><div class="nd">A+B → 最终 topK</div></div>
</div>

<h2>融合：RRF / 加权 / 模型重排</h2>
<p>把 N 份排名<strong>合成一份</strong>，是混合检索的灵魂，这一步叫 <strong>rerank（重排 / 融合）</strong>。难点在于：<strong>不同子搜索的"分数"往往不可比</strong>——稠密向量的相似度（比如 0.92）和稀疏向量的 BM25 分（比如 14.7）<strong>根本不是一个量纲</strong>，直接相加毫无意义。Milvus 提供三类 ranker 来解决这件事（配置见 <span class="inline">proxy/rerank_meta.go</span>、<span class="mono">parseRankParams</span>）。</p>
<p>第一类 <strong>RRF（Reciprocal Rank Fusion，倒数排名融合）</strong>：它<strong>干脆不看原始分数，只看名次</strong>。一个文档在某份榜单里排第 r 名，就得 <span class="mono">1/(k+r)</span> 分（k 是个平滑常数，默认 60），把它在所有榜单里的这种"名次分"加起来，就是最终分。妙在它<strong>天然抹平了量纲差异</strong>——名次永远是可比的。当你不确定各路分数该怎么权衡时，RRF 是个稳健的默认。第二类 <strong>WeightedRanker（加权融合）</strong>：当你<strong>明确想让某一路更重要</strong>时（比如"语义占七成、关键词占三成"），就给各路一个权重，把<strong>归一化后的分数</strong>加权求和。第三类 <strong>模型重排（model reranker）</strong>：把各路的候选<strong>交给一个专门的重排模型</strong>（cross-encoder，如 Cohere、TEI 等，代码在 <span class="inline">internal/util/function/rerank</span>）重新打分排序——质量最高，但要<strong>调用外部模型、成本也最高</strong>。下面把三者摆清。</p>

<p>怎么在这三者间选？这又是一道熟悉的<strong>取舍题</strong>。RRF <strong>最省心、最稳健</strong>——不用调参、不怕量纲、对"我也说不清两路谁更重要"的场景最友好，所以常被设成默认。WeightedRanker <strong>给你控制权</strong>——当你凭业务经验知道"这个场景语义更重要"时，能手动压一个权重上去，代价是要自己调那个比例。模型重排<strong>质量天花板最高</strong>——cross-encoder 会把"查询和每个候选"成对地细看一遍，比单纯的分数融合精准得多，但它要<strong>为每个候选都跑一次模型推理</strong>，延迟和成本都显著上去，所以通常只对前融合出的<strong>少量候选</strong>(比如 top-50)做精排。一个常见的生产组合是"<strong>先粗后精</strong>"：先用 RRF 把多路快速融合出一批候选，再用模型重排对这批候选做最终精排——<strong>用便宜的方法过滤大头、用昂贵的方法雕琢尖端</strong>。这种"两级排序"的思路，和第 5 课 ANN"先粗筛桶、再精算"、第 28 课"先过滤、再检索"是同一种<strong>分层收敛、把贵的算力花在刀刃上</strong>的智慧。</p>

<table class="t">
  <tr><th>Ranker</th><th>怎么融合</th><th>适用</th></tr>
  <tr><td class="mono"><strong>RRF</strong></td><td>只按名次：每榜得 1/(k+r) 分相加(k 默认 60)，抹平量纲差异</td><td>各路分数不可比 / 稳健默认</td></tr>
  <tr><td class="mono"><strong>WeightedRanker</strong></td><td>归一化分数后加权求和</td><td>明确想给某一路更高权重</td></tr>
  <tr><td class="mono"><strong>模型重排</strong></td><td>把候选交 cross-encoder 模型重新打分</td><td>追求最高相关性、可接受外部调用成本</td></tr>
</table>

<div class="cellgroup">
  <div class="cg-cap"><b>RRF 融合示例</b>（k=60）：只看名次、不看原始分，于是不同量纲也能合并</div>
  <div class="cells"><span class="lab">语义榜 A</span><span class="cell hl">文档 D 第 1 名</span><span class="sep">→</span><span class="cell q">1/(60+1) = 0.0164</span></div>
  <div class="cells"><span class="lab">关键词榜 B</span><span class="cell hl">文档 D 第 3 名</span><span class="sep">→</span><span class="cell q">1/(60+3) = 0.0159</span></div>
  <div class="cells"><span class="lab">RRF 合计</span><span class="cell">0.0164 + 0.0159</span><span class="sep">=</span><span class="cell q">0.0323 ← D 的最终分</span></div>
</div>

<h2>它落在系统的哪一层</h2>
<p>把混合检索放回整张架构图，你会发现它<strong>主要是 Proxy 的活</strong>，外加内核的一点配合。<strong>Proxy 是总指挥</strong>：它解析 <span class="mono">SubReqs</span>、把每路子搜索扇出去（经各 QueryNode 的 delegator）、收齐 N 份结果、再<strong>在 Proxy 这一层执行融合</strong>（RRF/加权由 Proxy 算，模型重排则由 Proxy 去调外部模型）。这很合理——融合需要<strong>看到所有路的全局结果</strong>，而 Proxy 正是那个"<strong>所有结果最终汇聚的点</strong>"（回忆第 29 课：Proxy 本就是三层 reduce 的最顶层）。</p>
<p>内核侧也有一个相关角色：<span class="inline">internal/core/src/exec/operator</span> 里的 <span class="mono">RescoresNode</span>——它和第 36 课的 <span class="mono">FilterBitsNode</span> 是兄弟，区别在于：FilterBitsNode 产出"<strong>哪些行通过</strong>"的 bitset，而 RescoresNode 接收一批 offset、对它们<strong>重新打分</strong>、产出带新分数的有效结果。它服务于在段内就需要"调整分数"的场景（比如某些 rerank/groupby 逻辑下推到 segcore）。但对大多数混合检索而言，<strong>融合发生在 Proxy 这一层</strong>，因为只有这里才同时握着所有子搜索的结果。把这一课收一收：混合检索 = <strong>多个向量字段</strong>（第 6 课）+ <strong>多路并行子搜索</strong>（复用第 25–29 课）+ <strong>一道融合</strong>（RRF/加权/模型）。它让 Milvus 能回答"<strong>既要语义像、又要关键词配</strong>"这类真实而复杂的检索诉求——这正是现代 RAG、推荐、多模态检索里最常用的一招。</p>

<p>最后留一个练习给你的直觉：下次设计检索时，先问自己一句——"<strong>我判断'相关'，真的只靠一种信号吗？</strong>"如果答案是"还要看关键词""还要看图片""还要看时效"，那你大概率就需要混合检索。把"相关性"拆成几路可独立检索的信号、各自召回、再用合适的 ranker 融合，是一种<strong>既灵活又强大</strong>的范式。它的代价是多了"<strong>选哪些字段、每路取多少、用哪种 ranker、怎么调权重</strong>"这些要调的旋钮；但回报是，你的检索质量能<strong>逼近真实业务对'相关'的复杂定义</strong>，而不再被单一向量的盲区所限。这，就是从"会用向量检索"到"会用好向量检索"的那道分水岭。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>为何混合</strong>：单一 embedding 有盲区——稠密擅语义、稀疏(BM25)擅关键词，互补；一个集合可有多个向量字段，混合检索综合多信号(也用于多模态/多视角)。</li>
    <li><strong>多路子搜索</strong>：<span class="mono">HybridSearch</span> 带 N 个 <span class="mono">SubReqs</span>，每个就是一次完整的普通向量检索；Proxy 扇出、各得一份 ranked 列表(复用第 25–29 课，不另造引擎)。</li>
    <li><strong>融合(rerank)</strong>：不同路分数不可比，需 ranker——<strong>RRF</strong>(只按名次 1/(k+r)，抹平量纲)、<strong>WeightedRanker</strong>(归一化后加权)、<strong>模型重排</strong>(cross-encoder，质量最高、成本最高)。</li>
    <li><strong>落在哪</strong>：融合主要由 <strong>Proxy</strong> 执行(它是所有结果的汇聚点，第 29 课最顶层 reduce)；内核的 <span class="mono">RescoresNode</span> 服务于段内重打分。常用于 RAG/推荐/多模态。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The searches so far were mostly "<strong>one query vector, find neighbors in one vector field</strong>". But real workloads often need to <strong>combine multiple signals</strong>: both <strong>semantic similarity</strong> (dense vectors) and <strong>keyword hits</strong> (sparse vectors / BM25, Lesson 24); or matching both an <strong>image</strong> and a <strong>text</strong> embedding. That's <strong>hybrid search</strong>: a collection can have <strong>multiple vector fields</strong>, one request runs several <strong>sub-searches</strong> in parallel, then <strong>fuses (reranks)</strong> the result lists into one final ranking. This lesson covers how it fans out and how it fuses.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of hybrid search as <strong>hiring by combining multiple dimensions</strong>. For the same candidate pool, HR ranks them several ways: by "<strong>skill match</strong>", by "<strong>past experience</strong>", by "<strong>culture fit</strong>". Each ranking has merit, but you ultimately want <strong>one combined ranking</strong>.
  How to <strong>fuse</strong> several rankings into one? Three ways: look only at each person's <strong>rank</strong> in each list and reward high ranks (<strong>RRF</strong>); give each list a <strong>weight</strong> and combine weighted scores (<strong>weighted fusion</strong>); or have a <strong>senior expert</strong> re-interview the shortlist and give an authoritative order (<strong>model reranking</strong>). Hybrid search does exactly this "<strong>score several ways → fuse into one list</strong>".
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>HybridSearch carries several sub-searches in one request (<span class="mono">SubReqs</span>, each over a vector field); the Proxy fans them out, gets a ranked list each, then fuses into the final topK with a <span class="mono">ranker</span> — three kinds: RRF (by rank), WeightedRanker (by weighted score), and model reranking (<span class="inline">internal/util/function/rerank</span>, calling an external cross-encoder)</strong>. Parsing is in <span class="mono">parseRankParams</span> (<span class="inline">proxy/task_search.go</span>) / <span class="inline">rerank_meta.go</span>.
</div>

<h2>Why hybrid search</h2>
<p>Single-vector search has an innate limit: <strong>one embedding is only good at capturing one kind of signal</strong>. <strong>Dense vectors</strong> (Lesson 4) excel at <strong>semantics</strong> — "sofa" matches "couch" even with different spelling; but they're insensitive to <strong>exact keywords</strong> — search a specific model "XJ-200" and a semantic vector may miss. <strong>Sparse vectors</strong> (sparse / BM25, Lesson 24) are the opposite: great at <strong>exact keyword hits</strong>, oblivious to semantic synonyms. <strong>Each has a blind spot, and they complement each other.</strong></p>

<div class="cols">
  <div class="col"><h4>Dense vectors</h4><p>great at <strong>semantics</strong>: sofa≈couch, doctor≈physician — matches despite different wording. Blind spot: insensitive to <strong>exact keywords/model numbers</strong> (XJ-200).</p></div>
  <div class="col"><h4>Sparse vectors (sparse / BM25)</h4><p>great at <strong>exact keyword hits</strong>: search a word, hit that word. Blind spot: oblivious to <strong>synonyms/semantics</strong> — reword it and it misses.</p></div>
</div>
<p>So a natural idea arises: <strong>can we use both and cover each other's weaknesses?</strong> That's the motivation for hybrid search. To support it, Milvus lets a collection <strong>define multiple vector fields</strong> (Lesson 6) — say a <span class="mono">dense_vec</span> for semantic embeddings and a <span class="mono">sparse_vec</span> for keyword weights. At search time the same query <strong>hits both fields</strong>: the dense path finds the semantically nearest, the sparse path the keyword-best, and the results are <strong>fused</strong>. Beyond "semantic + keyword", hybrid search also covers <strong>multimodal</strong> (image + text vectors together), <strong>multi-view</strong> (different embedding models of the same object), and more. In a line: <strong>when "similar" can't be measured by a single yardstick, combine several and fuse</strong> — a key step from "toy demo" to "real workload".</p>

<h2>One HybridSearch: several sub-searches</h2>
<p>Mechanically, a hybrid search is <strong>not one search but a bundle</strong>. The client's <span class="mono">HybridSearchRequest</span> carries a set of <strong>sub-requests (<span class="mono">SubReqs</span>)</strong> — each a <strong>plain vector search</strong>: which vector field, which query vector, what topK, what filter. The Proxy side (<span class="inline">internal/proxy/task_search.go</span>), seeing <span class="mono">len(SubReqs) &gt; 0</span>, knows this is an "<strong>advanced</strong>" hybrid search, so it <strong>fans each sub-request out as an independent search</strong> (reusing the whole Lesson 25–29 query path), runs them in parallel, each <strong>merging its own topK</strong>.</p>
<p>A key realization: <strong>each sub-search is itself a complete vector search you've already learned</strong>. It fans through delegators to segments, does filter-then-search, does the three-level reduce (Lesson 29). So hybrid search <strong>builds no new search engine</strong> — it <strong>runs N plain searches together, then adds a fusion step</strong>. Again that familiar philosophy: <strong>compose existing capabilities into a new feature</strong> rather than reinvent. The number of sub-searches is capped (<span class="mono">defaultMaxSearchRequest</span>) so one request can't fan out enough to crush the system. Once all sub-searches return, the Proxy holds <strong>N separately-ranked candidate lists</strong> — and the question becomes: <strong>how to combine these N into one?</strong></p>

<div class="flow">
  <div class="node"><div class="nt">HybridSearch</div><div class="nd">one request, N SubReqs</div></div>
  <div class="arrow">fan out</div>
  <div class="node hl"><div class="nt">sub-search: dense_vec</div><div class="nd">semantic nearest → ranked list A</div></div>
  <div class="node hl"><div class="nt">sub-search: sparse_vec</div><div class="nd">keyword best → ranked list B</div></div>
  <div class="arrow">fuse</div>
  <div class="node"><div class="nt">ranker</div><div class="nd">A+B → final topK</div></div>
</div>

<h2>Fusion: RRF / weighted / model reranking</h2>
<p>Combining N rankings <strong>into one</strong> is the soul of hybrid search; this step is <strong>rerank (fusion)</strong>. The hard part: <strong>scores from different sub-searches are often incomparable</strong> — a dense similarity (say 0.92) and a sparse BM25 score (say 14.7) are <strong>simply not the same unit</strong>, so adding them is meaningless. Milvus offers three kinds of ranker (config in <span class="inline">proxy/rerank_meta.go</span>, <span class="mono">parseRankParams</span>).</p>
<p>First, <strong>RRF (Reciprocal Rank Fusion)</strong>: it <strong>ignores raw scores and looks only at rank</strong>. A document ranked r-th in some list earns <span class="mono">1/(k+r)</span> (k a smoothing constant, default 60); summing these "rank scores" across all lists gives the final score. The beauty: it <strong>naturally erases unit differences</strong> — ranks are always comparable. When unsure how to weigh the scores, RRF is a robust default. Second, <strong>WeightedRanker</strong>: when you <strong>clearly want one path to matter more</strong> (say "semantics 70%, keywords 30%"), give each path a weight and sum the <strong>normalized scores</strong>. Third, <strong>model reranking</strong>: hand the candidates to a dedicated rerank model (a cross-encoder, e.g. Cohere, TEI; code in <span class="inline">internal/util/function/rerank</span>) to re-score and reorder — highest quality, but it <strong>calls an external model and costs the most</strong>. The three side by side:</p>

<table class="t">
  <tr><th>Ranker</th><th>How it fuses</th><th>Best for</th></tr>
  <tr><td class="mono"><strong>RRF</strong></td><td>by rank only: each list adds 1/(k+r) (k default 60), erasing unit differences</td><td>incomparable scores / robust default</td></tr>
  <tr><td class="mono"><strong>WeightedRanker</strong></td><td>normalize scores, then weighted sum</td><td>when you want one path weighted higher</td></tr>
  <tr><td class="mono"><strong>Model reranking</strong></td><td>hand candidates to a cross-encoder model to re-score</td><td>maximum relevance, external-call cost acceptable</td></tr>
</table>

<div class="cellgroup">
  <div class="cg-cap"><b>RRF fusion example</b> (k=60): rank only, not raw scores — so different units still combine</div>
  <div class="cells"><span class="lab">semantic list A</span><span class="cell hl">doc D ranked #1</span><span class="sep">→</span><span class="cell q">1/(60+1) = 0.0164</span></div>
  <div class="cells"><span class="lab">keyword list B</span><span class="cell hl">doc D ranked #3</span><span class="sep">→</span><span class="cell q">1/(60+3) = 0.0159</span></div>
  <div class="cells"><span class="lab">RRF total</span><span class="cell">0.0164 + 0.0159</span><span class="sep">=</span><span class="cell q">0.0323 ← D's final score</span></div>
</div>

<h2>Where it lands in the system</h2>
<p>Place hybrid search back on the architecture map and you'll see it's <strong>mostly the Proxy's job</strong>, with a touch of core help. <strong>The Proxy is the conductor</strong>: it parses <span class="mono">SubReqs</span>, fans each sub-search out (through QueryNode delegators), gathers the N results, and <strong>performs fusion at the Proxy layer</strong> (RRF/weighted computed by Proxy; model reranking has the Proxy call the external model). That makes sense — fusion needs to <strong>see the global results of all paths</strong>, and the Proxy is exactly "<strong>the point where all results converge</strong>" (recall Lesson 29: the Proxy is the top tier of the three-level reduce).</p>
<p>The core side has a related role: <span class="mono">RescoresNode</span> in <span class="inline">internal/core/src/exec/operator</span> — sibling to Lesson 36's <span class="mono">FilterBitsNode</span>, differing in that FilterBitsNode produces a "which rows pass" bitset, while RescoresNode takes an array of offsets, <strong>re-scores</strong> them, and produces valid results with new scores. It serves cases needing in-segment score adjustment (some rerank/groupby logic pushed down to segcore). But for most hybrid searches, <strong>fusion happens at the Proxy layer</strong>, since only there are all sub-search results held at once. To wrap up: hybrid search = <strong>multiple vector fields</strong> (Lesson 6) + <strong>parallel sub-searches</strong> (reusing Lessons 25–29) + <strong>one fusion step</strong> (RRF/weighted/model). It lets Milvus answer "<strong>both semantically similar and keyword-matching</strong>" — the most-used move in modern RAG, recommendation, and multimodal retrieval.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Why hybrid</strong>: a single embedding has blind spots — dense excels at semantics, sparse (BM25) at keywords, complementary; a collection can hold multiple vector fields, and hybrid search combines signals (also for multimodal/multi-view).</li>
    <li><strong>Sub-searches</strong>: <span class="mono">HybridSearch</span> carries N <span class="mono">SubReqs</span>, each a complete plain vector search; the Proxy fans them out, getting a ranked list each (reusing Lessons 25–29, no new engine).</li>
    <li><strong>Fusion (rerank)</strong>: scores across paths are incomparable, so a ranker is needed — <strong>RRF</strong> (rank-only 1/(k+r), erases units), <strong>WeightedRanker</strong> (normalize then weight), <strong>model reranking</strong> (cross-encoder, highest quality, highest cost).</li>
    <li><strong>Where it lands</strong>: fusion is mostly done by the <strong>Proxy</strong> (the convergence point of all results, the top reduce tier of Lesson 29); the core's <span class="mono">RescoresNode</span> serves in-segment re-scoring. Common in RAG/recommendation/multimodal.</li>
  </ul>
</div>
""",
}
