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
