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

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="两条写入路径殊途同归：流式写入（实时 insert → WAL → growing → flush 成段）与批量导入（批量文件 → ImportV2 作业 → 直接建段）都产出同规格的 binlog 段落到对象存储，被 QueryNode 一视同仁地加载与检索">
    <text x="24" y="56" style="fill:var(--muted)">① 流式写入（在线 · 实时可见）</text>
    <rect x="24" y="64" width="104" height="40" rx="8" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/><text x="76" y="89" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">实时 insert</text>
    <line x1="128" y1="84" x2="146" y2="84" style="stroke:var(--line);stroke-width:2"/><path d="M146,84 l-9,-4 l0,8 z" style="fill:var(--line)"/>
    <rect x="148" y="64" width="130" height="40" rx="8" style="fill:var(--panel);stroke:var(--accent)"/><text x="213" y="89" text-anchor="middle" style="fill:var(--ink)">WAL → growing</text>
    <line x1="278" y1="84" x2="296" y2="84" style="stroke:var(--line);stroke-width:2"/><path d="M296,84 l-9,-4 l0,8 z" style="fill:var(--line)"/>
    <rect x="298" y="64" width="104" height="40" rx="8" style="fill:var(--panel);stroke:var(--accent)"/><text x="350" y="89" text-anchor="middle" style="fill:var(--ink)">flush 成段</text>
    <text x="24" y="158" style="fill:var(--muted)">② 批量导入（离线 · 一次写定）</text>
    <rect x="24" y="166" width="104" height="40" rx="8" style="fill:var(--blue-soft);stroke:var(--blue);stroke-width:1.5"/><text x="76" y="191" text-anchor="middle" style="fill:var(--blue);font-weight:700">批量文件</text>
    <line x1="128" y1="186" x2="146" y2="186" style="stroke:var(--line);stroke-width:2"/><path d="M146,186 l-9,-4 l0,8 z" style="fill:var(--line)"/>
    <rect x="148" y="166" width="130" height="40" rx="8" style="fill:var(--panel);stroke:var(--blue)"/><text x="213" y="191" text-anchor="middle" style="fill:var(--ink)">ImportV2 作业</text>
    <line x1="278" y1="186" x2="296" y2="186" style="stroke:var(--line);stroke-width:2"/><path d="M296,186 l-9,-4 l0,8 z" style="fill:var(--line)"/>
    <rect x="298" y="166" width="104" height="40" rx="8" style="fill:var(--panel);stroke:var(--blue)"/><text x="350" y="191" text-anchor="middle" style="fill:var(--ink)">直接建段</text>
    <line x1="404" y1="88" x2="470" y2="120" style="stroke:var(--teal);stroke-width:2.5"/><path d="M470,120 l-11,-2 l3,-9 z" style="fill:var(--teal)"/>
    <line x1="404" y1="182" x2="470" y2="150" style="stroke:var(--teal);stroke-width:2.5"/><path d="M470,150 l-8,-7 l8,-4 z" style="fill:var(--teal)"/>
    <text x="430" y="128" text-anchor="middle" style="fill:var(--teal);font-weight:700">殊途同归</text>
    <rect x="474" y="100" width="220" height="56" rx="11" style="fill:var(--teal-soft);stroke:var(--teal);stroke-width:2"/><text x="584" y="124" text-anchor="middle" style="fill:var(--teal);font-weight:700">同规格 binlog 段</text><text x="584" y="144" text-anchor="middle" style="fill:var(--muted)">对象存储 · 同一张图纸</text>
    <line x1="584" y1="156" x2="584" y2="174" style="stroke:var(--teal);stroke-width:2"/><path d="M584,174 l-4,-10 l8,0 z" style="fill:var(--teal)"/>
    <rect x="474" y="176" width="220" height="40" rx="9" style="fill:var(--panel);stroke:var(--line)"/><text x="584" y="201" text-anchor="middle" style="fill:var(--ink)">QueryNode 一视同仁加载</text>
    <text x="380" y="256" text-anchor="middle" style="fill:var(--muted)">两条生产路径、同一种产物：上游细水长流或整车卸货，交付下游的都是同规格的段</text>
  </svg>
  <div class="figcap"><b>两条写入路径，殊途同归</b>：<b>① 流式写入</b>（在线、实时可见）走 <span class="mono">实时 insert → WAL → growing → flush 成段</span>；<b>② 批量导入</b>（离线、一次写定）走 <span class="mono">批量文件 → ImportV2 作业 → 直接建段</span>。两条路<b>最终都产出同规格的 binlog 段</b>落到对象存储——就像"不管哪条产线，下线的零件都符合同一张图纸"，于是 <b>QueryNode 一视同仁</b>地加载、检索，不必认两种段。把"多样的生产"收敛到"统一的产物接口"，正是系统能容纳多路径却不失控的关键。</div>
</div>

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

<p>One common misconception to clear up: <strong>"bypassing the WAL" doesn't mean "unsafe" or "loses data"</strong>. The WAL's core value is "<strong>log first, replay on crash</strong>" insurance for online writes that are real-time and could crash at any moment (Lesson 16). Bulk import's situation is fundamentally different: the source data <strong>already sits safely in files</strong> (parquet and the like in object storage), so if an import fails midway, <strong>the source files are still there — just run it again</strong>. In other words, the import's <strong>source of truth is those source files themselves</strong>, not the WAL, and the final commit is <strong>atomic</strong> (all-or-nothing), so a crash leaves no half-loaded mess. Bulk import bypasses the WAL not by <strong>cutting a safety corner</strong> but because <strong>this scenario simply doesn't need that layer</strong> — a tidy lesson in matching a mechanism to its premise: when the premise changes (offline, re-readable source files), pick the path that fits.</p>

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

<p>Look one level deeper at why PreImport estimates row counts, because its tie to autoID is worth spelling out. Recall Lesson 6: a primary key can be <strong>auto-allocated</strong> (autoID). In streaming writes each row's auto-increment PK is handed out one at a time — naturally. But bulk import loads a whole batch at once, so the system must <strong>know how many rows are coming in advance</strong> to <strong>pre-allocate a contiguous range of PK IDs</strong> for them — otherwise multiple DataNodes writing in parallel could <strong>collide on PKs or leave gaps</strong>. PreImport's row estimate is precisely what underpins this PK pre-allocation. So a seemingly trivial "scan first" actually guards <strong>primary-key uniqueness</strong>, a database's lifeline — proof that "how to safely mass-produce segments" is its own design problem, not just streaming logic poured in bulk.</p>

<h2>How it divides labor with streaming writes</h2>
<p>Finally, the <strong>division and cooperation</strong> of the two write paths. They <strong>share the same "segment" abstraction</strong> (Lesson 7): whether data was streamed into a growing segment then flushed, or bulk-imported straight into a segment, <strong>the end product is the same binlog-format segment in object storage</strong>, loaded and searched by QueryNodes alike. So bulk import <strong>isn't a separate world</strong> — it's <strong>a more efficient path producing the same product</strong>, which is why it slots seamlessly into the whole system.</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="Two write paths converge: streaming (live insert → WAL → growing → flush to segment) and bulk import (bulk files → ImportV2 job → build segment) both produce the same binlog-format segment in object storage, loaded and searched by QueryNode alike">
    <text x="24" y="56" style="fill:var(--muted)">① streaming (online · real-time)</text>
    <rect x="24" y="64" width="104" height="40" rx="8" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/><text x="76" y="89" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">live insert</text>
    <line x1="128" y1="84" x2="146" y2="84" style="stroke:var(--line);stroke-width:2"/><path d="M146,84 l-9,-4 l0,8 z" style="fill:var(--line)"/>
    <rect x="148" y="64" width="130" height="40" rx="8" style="fill:var(--panel);stroke:var(--accent)"/><text x="213" y="89" text-anchor="middle" style="fill:var(--ink)">WAL → growing</text>
    <line x1="278" y1="84" x2="296" y2="84" style="stroke:var(--line);stroke-width:2"/><path d="M296,84 l-9,-4 l0,8 z" style="fill:var(--line)"/>
    <rect x="298" y="64" width="104" height="40" rx="8" style="fill:var(--panel);stroke:var(--accent)"/><text x="350" y="89" text-anchor="middle" style="fill:var(--ink)">flush → seg</text>
    <text x="24" y="158" style="fill:var(--muted)">② bulk import (offline · write-once)</text>
    <rect x="24" y="166" width="104" height="40" rx="8" style="fill:var(--blue-soft);stroke:var(--blue);stroke-width:1.5"/><text x="76" y="191" text-anchor="middle" style="fill:var(--blue);font-weight:700">bulk files</text>
    <line x1="128" y1="186" x2="146" y2="186" style="stroke:var(--line);stroke-width:2"/><path d="M146,186 l-9,-4 l0,8 z" style="fill:var(--line)"/>
    <rect x="148" y="166" width="130" height="40" rx="8" style="fill:var(--panel);stroke:var(--blue)"/><text x="213" y="191" text-anchor="middle" style="fill:var(--ink)">ImportV2 job</text>
    <line x1="278" y1="186" x2="296" y2="186" style="stroke:var(--line);stroke-width:2"/><path d="M296,186 l-9,-4 l0,8 z" style="fill:var(--line)"/>
    <rect x="298" y="166" width="104" height="40" rx="8" style="fill:var(--panel);stroke:var(--blue)"/><text x="350" y="191" text-anchor="middle" style="fill:var(--ink)">build seg</text>
    <line x1="404" y1="88" x2="470" y2="120" style="stroke:var(--teal);stroke-width:2.5"/><path d="M470,120 l-11,-2 l3,-9 z" style="fill:var(--teal)"/>
    <line x1="404" y1="182" x2="470" y2="150" style="stroke:var(--teal);stroke-width:2.5"/><path d="M470,150 l-8,-7 l8,-4 z" style="fill:var(--teal)"/>
    <text x="430" y="128" text-anchor="middle" style="fill:var(--teal);font-weight:700">converge</text>
    <rect x="474" y="100" width="220" height="56" rx="11" style="fill:var(--teal-soft);stroke:var(--teal);stroke-width:2"/><text x="584" y="124" text-anchor="middle" style="fill:var(--teal);font-weight:700">same binlog segment</text><text x="584" y="144" text-anchor="middle" style="fill:var(--muted)">object storage · one blueprint</text>
    <line x1="584" y1="156" x2="584" y2="174" style="stroke:var(--teal);stroke-width:2"/><path d="M584,174 l-4,-10 l8,0 z" style="fill:var(--teal)"/>
    <rect x="474" y="176" width="220" height="40" rx="9" style="fill:var(--panel);stroke:var(--line)"/><text x="584" y="201" text-anchor="middle" style="fill:var(--ink)">QueryNode loads both alike</text>
    <text x="380" y="256" text-anchor="middle" style="fill:var(--muted)">two paths, one product: a trickle or a truckload upstream → the same segment downstream</text>
  </svg>
  <div class="figcap"><b>Two write paths, converging</b>: <b>① streaming</b> (online, real-time-visible) goes <span class="mono">live insert → WAL → growing → flush to segment</span>; <b>② bulk import</b> (offline, write-once) goes <span class="mono">bulk files → ImportV2 job → build segment</span>. Both paths <b>end in the same binlog-format segment</b> in object storage — like "whatever the production line, the parts off it meet one blueprint" — so <b>QueryNode treats them alike</b>, never needing to know two segment kinds. Converging "diverse production" onto "one product interface" is what lets a system hold many paths without losing control.</div>
</div>

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

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="RRF 倒数排名融合：向量 ANN 榜与 BM25 榜各自排名，RRF 只看名次给每个文档 1/(k+r) 分、跨榜相加，k=60；d1 在两榜都排第二、不拔尖却都在，融合后总分最高、排第一">
    <text x="86" y="60" text-anchor="middle" style="fill:var(--muted)">向量 ANN 榜</text>
    <rect x="30" y="72" width="118" height="32" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="89" y="93" text-anchor="middle" class="mono" style="fill:var(--muted)">① d3</text>
    <rect x="30" y="108" width="118" height="32" rx="7" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/><text x="89" y="129" text-anchor="middle" class="mono" style="fill:var(--accent-ink);font-weight:700">② d1</text>
    <rect x="30" y="144" width="118" height="32" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="89" y="165" text-anchor="middle" class="mono" style="fill:var(--muted)">③ d9</text>
    <text x="218" y="60" text-anchor="middle" style="fill:var(--muted)">BM25 榜</text>
    <rect x="162" y="72" width="118" height="32" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="221" y="93" text-anchor="middle" class="mono" style="fill:var(--muted)">① d5</text>
    <rect x="162" y="108" width="118" height="32" rx="7" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/><text x="221" y="129" text-anchor="middle" class="mono" style="fill:var(--accent-ink);font-weight:700">② d1</text>
    <rect x="162" y="144" width="118" height="32" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="221" y="165" text-anchor="middle" class="mono" style="fill:var(--muted)">③ d8</text>
    <line x1="282" y1="124" x2="312" y2="124" style="stroke:var(--teal);stroke-width:2.5"/><path d="M312,124 l-11,-5 l0,10 z" style="fill:var(--teal)"/>
    <rect x="314" y="78" width="130" height="92" rx="10" style="fill:var(--teal-soft);stroke:var(--teal);stroke-width:1.5"/><text x="379" y="102" text-anchor="middle" style="fill:var(--teal);font-weight:700">RRF · 只看名次</text><text x="379" y="126" text-anchor="middle" class="mono" style="fill:var(--ink)">Σ 1/(k+r)</text><text x="379" y="150" text-anchor="middle" style="fill:var(--muted)">k=60，抹平量纲</text>
    <line x1="444" y1="124" x2="472" y2="124" style="stroke:var(--accent);stroke-width:2.5"/><path d="M472,124 l-11,-5 l0,10 z" style="fill:var(--accent)"/>
    <text x="606" y="60" text-anchor="middle" style="fill:var(--muted)">融合最终榜</text>
    <rect x="476" y="72" width="262" height="32" rx="7" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:2"/><text x="607" y="93" text-anchor="middle" class="mono" style="fill:var(--accent-ink);font-weight:700">① d1 · 0.032（两榜都第 2）</text>
    <rect x="476" y="108" width="262" height="32" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="607" y="129" text-anchor="middle" class="mono" style="fill:var(--muted)">② d3 · 0.016（只在一榜拔尖）</text>
    <rect x="476" y="144" width="262" height="32" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="607" y="165" text-anchor="middle" class="mono" style="fill:var(--muted)">③ d5 · 0.016（只在一榜拔尖）</text>
    <text x="380" y="210" text-anchor="middle" style="fill:var(--muted)">RRF 不看原始分、只看名次（稠密相似度 0.92 与 BM25 14.7 不可比）→ 名次永远可比</text>
    <text x="380" y="232" text-anchor="middle" style="fill:var(--ink);font-weight:700">d1 两榜都第 2、不拔尖却都在 → 融合第 1：稳健的"哪都不差"胜过偏科的"只在一榜拔尖"</text>
  </svg>
  <div class="figcap"><b>RRF：把多份排名合成一份</b>，难点是不同子搜索的"分数"<b>不可比</b>（稠密相似度 0.92 vs BM25 14.7 不是一个量纲）。<b>RRF（倒数排名融合）</b>干脆<b>只看名次不看分数</b>：文档在某榜排第 r 名就得 <span class="mono">1/(k+r)</span> 分（k=60），跨榜相加即最终分——名次永远可比，天然抹平量纲。看 <span class="mono">d1</span>：它在两榜都只排<b>第 2</b>（不拔尖），但<b>两榜都在</b>，<span class="mono">1/62 + 1/62 ≈ 0.032</span> 反而<b>压过</b>只在单榜第 1 的 d3/d5（<span class="mono">1/61 ≈ 0.016</span>）→ 融合后<b>排第 1</b>。这正是 RRF 的精髓：<b>稳健地"哪都不差"，胜过偏科地"只在一路拔尖"</b>。（另有 WeightedRanker 加权、model reranker 精排两类。）</div>
</div>

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

<p>One easy-to-miss detail that strongly affects quality: <strong>each sub-search usually needs to fetch more candidates than the final topK</strong>. Intuitively you might think "I only want the top-10, so top-10 per path is enough" — but fusion <strong>reshuffles the ranks</strong>: a document ranked 15th on the semantic list yet 2nd on the keyword list may well land in the final top-10; if each path fetched only its own top-10, that document <strong>was never retrieved on the semantic side</strong> and is <strong>lost for good</strong> at fusion time. So in practice each sub-search fetches a <strong>candidate pool larger than the final topK</strong> (say final 10, but fetch 50 per path), leaving fusion room to "come from behind". This is one of the most common hybrid-search tuning traps — <strong>fusion isn't stitching a few top-Ks together but re-ranking over a larger candidate set</strong> — and missing it is exactly how recall silently drops after fusion.</p>

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

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="RRF reciprocal-rank fusion: the vector ANN list and the BM25 list each rank documents; RRF looks only at rank, giving each document 1/(k+r) and summing across lists with k=60; d1 is #2 in both lists (never top but always present) and so scores highest after fusion, ranking #1">
    <text x="86" y="60" text-anchor="middle" style="fill:var(--muted)">vector ANN</text>
    <rect x="30" y="72" width="118" height="32" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="89" y="93" text-anchor="middle" class="mono" style="fill:var(--muted)">① d3</text>
    <rect x="30" y="108" width="118" height="32" rx="7" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/><text x="89" y="129" text-anchor="middle" class="mono" style="fill:var(--accent-ink);font-weight:700">② d1</text>
    <rect x="30" y="144" width="118" height="32" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="89" y="165" text-anchor="middle" class="mono" style="fill:var(--muted)">③ d9</text>
    <text x="218" y="60" text-anchor="middle" style="fill:var(--muted)">BM25</text>
    <rect x="162" y="72" width="118" height="32" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="221" y="93" text-anchor="middle" class="mono" style="fill:var(--muted)">① d5</text>
    <rect x="162" y="108" width="118" height="32" rx="7" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/><text x="221" y="129" text-anchor="middle" class="mono" style="fill:var(--accent-ink);font-weight:700">② d1</text>
    <rect x="162" y="144" width="118" height="32" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="221" y="165" text-anchor="middle" class="mono" style="fill:var(--muted)">③ d8</text>
    <line x1="282" y1="124" x2="312" y2="124" style="stroke:var(--teal);stroke-width:2.5"/><path d="M312,124 l-11,-5 l0,10 z" style="fill:var(--teal)"/>
    <rect x="314" y="78" width="130" height="92" rx="10" style="fill:var(--teal-soft);stroke:var(--teal);stroke-width:1.5"/><text x="379" y="102" text-anchor="middle" style="fill:var(--teal);font-weight:700">RRF · rank only</text><text x="379" y="126" text-anchor="middle" class="mono" style="fill:var(--ink)">Σ 1/(k+r)</text><text x="379" y="150" text-anchor="middle" style="fill:var(--muted)">k=60, unit-free</text>
    <line x1="444" y1="124" x2="472" y2="124" style="stroke:var(--accent);stroke-width:2.5"/><path d="M472,124 l-11,-5 l0,10 z" style="fill:var(--accent)"/>
    <text x="606" y="60" text-anchor="middle" style="fill:var(--muted)">fused final</text>
    <rect x="476" y="72" width="262" height="32" rx="7" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:2"/><text x="607" y="93" text-anchor="middle" class="mono" style="fill:var(--accent-ink);font-weight:700">① d1 · 0.032 (#2 both)</text>
    <rect x="476" y="108" width="262" height="32" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="607" y="129" text-anchor="middle" class="mono" style="fill:var(--muted)">② d3 · 0.016 (#1 one only)</text>
    <rect x="476" y="144" width="262" height="32" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="607" y="165" text-anchor="middle" class="mono" style="fill:var(--muted)">③ d5 · 0.016 (#1 one only)</text>
    <text x="380" y="210" text-anchor="middle" style="fill:var(--muted)">RRF ignores raw scores, ranks only (0.92 vs 14.7 incomparable) → ranks always comparable</text>
    <text x="380" y="232" text-anchor="middle" style="fill:var(--ink);font-weight:700">d1 is #2 in both (never top, always there) → fused #1: consistent beats spiky</text>
  </svg>
  <div class="figcap"><b>RRF: merge several rankings into one</b>. The hard part is that sub-searches' "scores" are <b>incomparable</b> (a dense similarity 0.92 vs a BM25 14.7 aren't the same unit). <b>RRF (reciprocal rank fusion)</b> simply <b>looks at rank, not score</b>: a doc ranked r in a list earns <span class="mono">1/(k+r)</span> (k=60), summed across lists — ranks are always comparable, erasing the unit gap. See <span class="mono">d1</span>: only <b>#2</b> in each list (never top), yet <b>present in both</b>, so <span class="mono">1/62 + 1/62 ≈ 0.032</span> <b>beats</b> d3/d5 that top a single list (<span class="mono">1/61 ≈ 0.016</span>) → it ranks <b>#1</b> after fusion. That's RRF's essence: <b>consistently good everywhere beats spiky in one place</b>. (Also: WeightedRanker, and model rerankers for precision.)</div>
</div>

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
<p>So how do you choose among the three? Another familiar <strong>trade-off</strong>. RRF is the <strong>most carefree and robust</strong> — no tuning, no unit worries, friendliest when "I can't really say which path matters more", which is why it's often the default. WeightedRanker <strong>gives you control</strong> — when business sense tells you "semantics matters more here", you can push a weight in, at the cost of tuning that ratio yourself. Model reranking has the <strong>highest quality ceiling</strong> — a cross-encoder examines each query–candidate pair closely, far more precise than score fusion, but it runs a model inference <strong>per candidate</strong>, so latency and cost climb sharply; you therefore usually fine-rank only a <strong>small set</strong> of already-fused candidates (say the top ~50). A common production combo is <strong>coarse then fine</strong>: use RRF to fuse the paths into a candidate batch quickly, then model-rerank just that batch — <strong>filter the bulk cheaply, polish the tip expensively</strong>. This "two-level ranking" is the same layered-convergence wisdom as Lesson 5's ANN (coarse buckets, then exact) and Lesson 28's filter-then-search.</p>
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

LESSON_49 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
任何系统的产能都<strong>有上限</strong>。如果写入快到 flush 来不及落盘，内存会被 growing 段撑爆；如果查询多到耗尽资源，节点会被拖垮；如果数据涨到磁盘写满，整个集群可能<strong>雪崩</strong>。一个成熟的数据库必须能<strong>自我保护</strong>——这就是<strong>配额、限流与背压（backpressure）</strong>。这一课看 Milvus 怎么用 <strong>QuotaCenter</strong>（中央调速器）盯住实时指标、算出限速、再由 <strong>Proxy</strong> 在入口处落地，必要时<strong>主动拒绝</strong>请求，把集群从过载中救回来。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  把系统想成一家<strong>餐厅</strong>。后厨（各节点）的产能有限：同时在做的菜太多就会手忙脚乱、出餐崩盘。<strong>领位员</strong>（Proxy 入口）于是按后厨的忙碌程度<strong>控制放客进店的速度</strong>——不让人潮一下子涌进来压垮厨房。而<strong>经理</strong>（QuotaCenter）站在全局视角，<strong>实时盯着后厨的各项指标</strong>（灶台占用、备料余量、上菜延迟），算出"现在每分钟最多放几桌"，再告诉门口的领位员照此执行。
  当后厨实在要爆了，经理会下一道<strong>更狠的命令</strong>："<strong>今日满座、暂停接待</strong>"——宁可把新客挡在门外（让他们待会儿再来），也不能让已经在吃的客人一起遭殃。<strong>限速是温和的刹车，拒绝是紧急的刹车</strong>——两档配合，才能让餐厅在高峰里不崩。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong>QuotaCenter(<span class="inline">rootcoord/quota_center.go</span>)周期性从各节点<span class="mono">collectMetrics</span>(内存水位、磁盘、TT 延迟…)→<span class="mono">calculateRates</span> 算出各类操作(DML/DQL/DDL…)的限速→下发给所有 Proxy；Proxy 的 <span class="mono">RateLimitInterceptor</span> 在每个请求前检查，超限就回 <span class="mono">ErrServiceRateLimit</span>(可重试)；过载到硬上限时 <span class="mono">forceDenyWriting/Reading</span> 把速率压到 0、整类拒绝</strong>。中央决策、边缘落地。
</div>

<h2>为什么要自我保护：背压的本质</h2>
<p>先想清楚一个朴素的道理：<strong>一个系统消化请求的速度是有限的，但发请求的客户端不会自觉</strong>。如果放任客户端无限快地写、无限多地查，迟早会撞上某个<strong>硬资源的天花板</strong>：内存被未落盘的 growing 段撑满、磁盘被 binlog 写爆、CPU 被查询占满。撞上之后会发生什么？<strong>不是优雅地变慢，而是崩溃</strong>——节点 OOM 被杀、请求大面积超时、甚至引发<strong>雪崩式的连锁失败</strong>（一个节点挂了，负载转移到别的节点，把它们也压垮）。</p>
<p>所以成熟系统都信奉一条铁律：<strong>与其被冲垮，不如主动减速</strong>。这就是<strong>背压（backpressure）</strong>——当下游处理不过来时，<strong>反过来给上游施加压力、让它慢下来</strong>。就像水管下游堵了，压力会沿着管子往回传，让上游的水龙头不得不关小。对数据库而言，背压意味着：<strong>当系统逼近极限时，主动拒绝或拖慢一部分新请求</strong>，把有限的资源留给"已经在处理的活"，<strong>用牺牲一点点可用性，换取整体的不崩溃</strong>。这是一种典型的工程取舍：<strong>宁可对少数请求说"不"，也不让所有请求一起死</strong>。理解了这个"<strong>主动减速以自保</strong>"的核心，你就抓住了配额限流这套机制的灵魂——它不是为了刁难用户，而是系统的<strong>安全阀</strong>。</p>

<p>顺便厘清三个常被混用的词，它们其实是一条链上的三环：<strong>配额（quota）</strong>是"<strong>额度</strong>"——规定某类操作每秒最多多少（可在 <span class="inline">configs/milvus.yaml</span> 的 <span class="mono">quotaAndLimits</span> 里配，第 40 课）；<strong>限流（rate limiting）</strong>是"<strong>按额度放行</strong>"的动作——在入口处数着额度决定放不放；<strong>背压（backpressure）</strong>是更宏观的"<strong>反向施压</strong>"理念——下游忙不过来时，让上游自觉慢下来。三者的关系是：<strong>背压是目的，限流是手段，配额是手段里的具体数值</strong>。Milvus 把"配额该是多少"交给 QuotaCenter 根据实时指标<strong>动态算</strong>（而不是写死一个静态值），正是为了让这道安全阀能<strong>随系统冷暖自动松紧</strong>——闲时放宽、忙时收紧。理清这三个词，你读任何系统的限流文档都不会再犯迷糊。</p>

<p>这里值得多想一层：<strong>为什么"主动拒绝"反而是负责任的表现？</strong>很多人直觉上觉得"数据库就该来者不拒、有多少吃多少"，可那恰恰是脆弱系统的死法。设想一个不设防的系统：写入洪峰一来，它照单全收，内存一路涨到爆，然后<strong>整个节点 OOM 被杀</strong>——此刻<strong>所有请求</strong>（包括那些本来好好的）全部失败，已经写进内存还没落盘的数据可能也丢了。对比一个有背压的系统：同样的洪峰来临，它在内存到警戒线时就开始<strong>限速</strong>、到硬上限时<strong>拒绝新写入</strong>，于是内存稳在安全区，<strong>已经在处理的请求全部成功</strong>，被拒的请求收到的是一个"<strong>待会再来</strong>"的可重试信号、退避后大多也能成功。两相对比，高下立判：<strong>"优雅地拒绝一部分"远胜于"失控地全盘崩溃"</strong>。这就是为什么所有严肃的分布式系统——数据库、消息队列、网关——都把限流背压当成<strong>必备的基础设施</strong>，而不是可有可无的装饰。一个会"<strong>说不</strong>"的系统，才是一个<strong>靠得住</strong>的系统。</p>

<h2>QuotaCenter：中央调速器</h2>
<p>谁来决定"现在该不该减速、减多少"？是 RootCoord 上的 <strong>QuotaCenter</strong>（<span class="inline">internal/rootcoord/quota_center.go</span>）。它跑着一个<strong>周期性的循环</strong>，每一轮做三件事：<strong>收集 → 计算 → 下发</strong>。第一步 <span class="mono">collectMetrics()</span>：从全集群各节点<strong>汇总实时指标</strong>——内存水位多高、磁盘用了多少、TimeTick 延迟（写入消费追不追得上）、各类队列多深。第二步 <span class="mono">calculateRates()</span>：根据这些指标，<strong>算出此刻各类操作的允许速率</strong>——写入（DML）、查询（DQL）、DDL、建索引、flush、compaction 等，每一类都有自己的配额。第三步：把算好的限速<strong>下发给所有 Proxy</strong>。</p>
<p>为什么把这件事放在 RootCoord、做成一个中央组件？因为<strong>限速决策需要全局视角</strong>。单个 Proxy 只看得到流经自己的请求，根本不知道"整个集群的内存还剩多少""别的 Proxy 一共放进来多少写入"。只有一个能<strong>俯瞰全集群指标</strong>的中央大脑，才能做出"现在全局该限到多少"的正确决策——这正是<strong>控制面</strong>（第 9 课）该干的事：QuotaCenter 是决策者，Proxy 是执行者。这也再次呼应了全书的主线：<strong>把"需要全局信息才能做的决策"收敛到中央，把"按决策行动"分散到边缘</strong>。下面这张图就是 QuotaCenter 的反馈闭环。</p>

<div class="flow">
  <div class="node"><div class="nt">各节点指标</div><div class="nd">内存水位 / 磁盘 / TT 延迟 / 队列深</div></div>
  <div class="arrow">collectMetrics</div>
  <div class="node hl"><div class="nt">QuotaCenter（RootCoord）</div><div class="nd">calculateRates：算各类操作限速</div></div>
  <div class="arrow">下发</div>
  <div class="node"><div class="nt">所有 Proxy</div><div class="nd">拿到最新限速</div></div>
  <div class="arrow">enforce</div>
  <div class="node"><div class="nt">放行 / 拒绝</div><div class="nd">超限回 ErrServiceRateLimit</div></div>
</div>

<h2>两档刹车：限速与强制拒绝</h2>
<p>QuotaCenter 的"减速"不是一刀切，而是<strong>两档力度</strong>，对应过载的不同严重程度。第一档是<strong>限速（throttle / cool-off）</strong>：当指标<strong>接近</strong>警戒线（比如内存到了 80%），就把对应操作的速率<strong>逐步调低</strong>，让请求"<strong>排着队慢慢来</strong>"，给系统喘息和消化的时间。这是温和的刹车——请求还能进，只是变慢。</p>
<p>第二档是<strong>强制拒绝（force-deny）</strong>：当指标<strong>撞穿</strong>硬上限（比如内存/磁盘水位过高、或 TT 延迟大到危险），QuotaCenter 会调用 <span class="mono">forceDenyWriting</span>（把 DML 速率直接压到 <strong>0</strong>、拒绝所有写入）或 <span class="mono">forceDenyReading</span>（把 DQL 压到 0、拒绝所有读）。这是紧急刹车——<strong>整类操作被暂时挡在门外</strong>，直到水位降回安全线。为什么要有这么"狠"的一档？因为到了硬上限，<strong>再放进来就是 OOM/写满磁盘的崩溃</strong>，与其全军覆没，不如<strong>果断拒绝新请求、保住已有的</strong>。值得注意的是，<strong>写和读是分开管的</strong>：内存/磁盘压力大时往往先 deny 写（写才是占资源的大头），读可能还能继续。下面把两档刹车摆清。</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="两档刹车：随着内存磁盘用量与 TT 延迟上升，先进入限速档（接近约 85% 警戒线，逐步调低速率、请求排队慢来），再撞穿硬上限触发强制拒绝档（forceDenyWriting/Reading，速率归零、整类拒绝）">
    <text x="60" y="44" style="fill:var(--muted)">内存 / 磁盘用量、TT 延迟　→　越涨越收紧</text>
    <rect x="60" y="56" width="400" height="30" rx="6" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="260" y="76" text-anchor="middle" style="fill:var(--teal);font-weight:700">正常 · 满速放行</text>
    <rect x="460" y="56" width="140" height="30" style="fill:var(--amber-soft);stroke:var(--amber)"/><text x="530" y="76" text-anchor="middle" style="fill:var(--amber);font-weight:700">限速</text>
    <rect x="600" y="56" width="100" height="30" rx="6" style="fill:var(--red-soft);stroke:var(--red);stroke-width:2"/><text x="650" y="76" text-anchor="middle" style="fill:var(--red);font-weight:700">拒绝</text>
    <line x1="460" y1="50" x2="460" y2="92" style="stroke:var(--amber);stroke-dasharray:3 3"/><text x="460" y="104" text-anchor="middle" style="fill:var(--muted)">≈85% 警戒线</text>
    <line x1="600" y1="50" x2="600" y2="92" style="stroke:var(--red);stroke-dasharray:3 3"/><text x="600" y="104" text-anchor="middle" style="fill:var(--red)">硬上限 ≈95%</text>
    <rect x="40" y="120" width="156" height="36" rx="8" style="fill:var(--amber-soft);stroke:var(--amber);stroke-width:1.5"/><text x="118" y="143" text-anchor="middle" style="fill:var(--amber);font-weight:700">① 限速 throttle</text>
    <text x="206" y="143" style="fill:var(--muted)">接近警戒线(~85%)：逐步调低速率、请求排队慢来——还能进，只是变慢</text>
    <rect x="40" y="164" width="156" height="36" rx="8" style="fill:var(--red-soft);stroke:var(--red);stroke-width:1.5"/><text x="118" y="187" text-anchor="middle" style="fill:var(--red);font-weight:700">② 强制拒绝 deny</text>
    <text x="206" y="187" style="fill:var(--muted)">撞穿硬上限：forceDeny 写/读、速率→0、整类拒绝——保住已有</text>
    <text x="380" y="232" text-anchor="middle" style="fill:var(--ink);font-weight:700">渐进施压 + 极端兜底：平时柔和限速控压，真要撞墙才急刹拒绝</text>
    <text x="380" y="254" text-anchor="middle" style="fill:var(--muted)">写和读分开管：压力大时先 deny 写（写占资源大头），读可能还能继续</text>
  </svg>
  <div class="figcap"><b>两档刹车 = 渐进限速 + 极端拒绝</b>：<span class="mono">QuotaCenter</span> 的减速不是一刀切。随着内存/磁盘用量、TT 延迟上升——<b>① 限速 throttle</b>：接近警戒线（如内存 ~85%）就<b>逐步调低速率</b>、让请求排队慢来（还能进，只是变慢，温和刹车）；<b>② 强制拒绝 force-deny</b>：撞穿硬上限就调 <span class="mono">forceDenyWriting/forceDenyReading</span> 把速率<b>压到 0、整类拒绝</b>（紧急刹车，保住已有，避免 OOM/写满盘）。只有"拒绝"一档会在临界点剧烈抖动，只有"限速"又压不住洪峰——<b>两档配合才既平滑又托底</b>。写读分开管，压力大先 deny 写。</div>
</div>

<p>这"两档刹车"的设计，藏着一个很重要的<strong>分级响应</strong>思想，值得点透。如果只有"<strong>拒绝</strong>"一档会怎样？那系统就成了"<strong>要么全放、要么全关</strong>"的开关——在临界点附近<strong>剧烈抖动</strong>：刚一拒绝、压力降了又全放，放完又爆、又全拒……用户体验是"<strong>时好时坏、忽快忽停</strong>"。反过来，如果只有"<strong>限速</strong>"一档、没有硬性拒绝，那遇到极端洪峰时，温和的限速可能<strong>压不住</strong>，系统还是会被缓慢地推向崩溃。<strong>两档配合，才能既平滑又托底</strong>：平时用限速<strong>柔和地</strong>把压力维持在安全区（像汽车轻点刹车控速），只有在真要撞墙的瞬间才动用强制拒绝这记<strong>急刹</strong>。这种"<strong>渐进施压 + 极端兜底</strong>"的分级策略，在工程上随处可见——从网络拥塞控制（慢启动→拥塞避免→快速重传）到操作系统的内存回收（轻度回收→OOM kill）。Milvus 的配额限流，正是这套成熟智慧在向量数据库上的落地。看懂了"<strong>为什么要两档、而不是一档</strong>"，你对系统稳定性设计的理解就深了一层：<strong>好的自我保护，不是一道生硬的墙，而是一条有弹性的、能随压力平滑收紧的缰绳</strong>。</p>

<div class="cols">
  <div class="col"><h4>限速 throttle（温和）</h4><p>指标<strong>接近</strong>警戒线时，逐步<strong>调低速率</strong>、让请求排队慢行。请求仍能进、只是变慢，给系统喘息空间。</p></div>
  <div class="col"><h4>强制拒绝 force-deny（紧急）</h4><p>指标<strong>撞穿</strong>硬上限时，<span class="mono">forceDenyWriting/Reading</span> 把该类速率压到 <strong>0</strong>、整类拒绝，直到水位回落。宁拒新、保已有。</p></div>
</div>

<h2>在 Proxy 落地：RateLimitInterceptor</h2>
<p>限速由 QuotaCenter 决策，但<strong>真正"拦人"发生在 Proxy 入口</strong>。Proxy 上有一个 <span class="mono">RateLimitInterceptor</span>（<span class="inline">internal/proxy/rate_limit_interceptor.go</span>）——它是一个 gRPC 拦截器（回忆第 38 课，Proxy 用拦截器做横切关注点），<strong>每个请求进来都先过它这一关</strong>：根据请求类型（写/读/DDL…）查一下当前的限速额度，<strong>额度够就放行、不够就当场拒绝</strong>，返回一个 <span class="mono">ErrServiceRateLimit</span> 错误。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>请求到达 Proxy</h4><p>一次写/读/DDL 请求进来，先撞上 <span class="mono">RateLimitInterceptor</span>。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>查当前额度</h4><p>按请求类型查 QuotaCenter 最近下发的限速：还有额度吗？</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>够 → 放行</h4><p>额度充足，请求正常进入后续处理（校验、入队、扇出…）。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>不够 → 拒绝</h4><p>超限，当场回 <span class="mono">ErrServiceRateLimit</span>(可重试)；客户端退避、稍后重试。</p></div></div>
</div>
<p>这里有个和第 44 课呼应的精妙之处：<span class="mono">ErrServiceRateLimit</span> 是一个 <strong>可重试（System 类）</strong>的错误——它不是在说"你这请求本身错了"（那是 Input 错误、重试也没用），而是在说"<strong>我现在忙、你待会儿再来</strong>"。所以拿到这个错误的客户端（SDK）<strong>应当退避一下、稍后重试</strong>，而不是直接报错给用户。这正是背压<strong>温柔的一面</strong>：它把"系统过载"这件事，转化成一个<strong>客户端能理解、能自动应对</strong>的信号，让整个调用链<strong>协同地慢下来</strong>，而不是硬碰硬地崩掉。把这一课收一收：<strong>QuotaCenter（中央，看全局、定限速、过载时 force-deny）+ RateLimitInterceptor（边缘，每请求落地、超限回可重试错误）</strong>，一中央一边缘，共同构成了 Milvus 的<strong>自我保护安全阀</strong>。它用到的每块拼图你都见过——控制面决策（第 9 课）、拦截器（第 38 课）、可重试错误（第 44 课）、配额配置（第 40 课）、指标监控（第 39 课）——这一课把它们拧成了"<strong>系统怎么在过载中活下来</strong>"的一台完整机器。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>为何自保(背压)</strong>：产能有限、客户端不自觉，撞上硬资源天花板会崩溃甚至雪崩；与其被冲垮，不如主动减速——牺牲一点可用性换整体不崩。</li>
    <li><strong>QuotaCenter(中央调速器)</strong>：RootCoord 上周期循环 <span class="mono">collectMetrics</span>(内存/磁盘/TT 延迟)→<span class="mono">calculateRates</span>(各类操作限速)→下发各 Proxy；限速决策需全局视角，是控制面的活。</li>
    <li><strong>两档刹车</strong>：<strong>限速</strong>(接近警戒线→逐步调低、排队慢行) 与 <strong>强制拒绝</strong>(撞硬上限→<span class="mono">forceDenyWriting/Reading</span> 压到 0、整类拒绝)；写读分开管。</li>
    <li><strong>Proxy 落地</strong>：<span class="mono">RateLimitInterceptor</span> 每请求查额度、超限回 <span class="mono">ErrServiceRateLimit</span>(<strong>可重试</strong>，意为"忙、待会再来")；中央决策 + 边缘执行。复用控制面/拦截器/merr/配额/指标。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Every system has a <strong>capacity ceiling</strong>. If writes outrun flushing, memory fills with growing segments and bursts; if queries exhaust resources, nodes are dragged down; if data fills the disk, the whole cluster can <strong>avalanche</strong>. A mature database must <strong>protect itself</strong> — that's <strong>quota, rate-limiting, and backpressure</strong>. This lesson shows how Milvus uses <strong>QuotaCenter</strong> (the central governor) to watch live metrics, compute rate limits, and have the <strong>Proxy</strong> enforce them at the entrance, <strong>actively rejecting</strong> requests when needed to rescue the cluster from overload.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of the system as a <strong>restaurant</strong>. The kitchen (the nodes) has finite capacity: too many dishes at once and it flails, plating collapses. So the <strong>host</strong> (the Proxy entrance) <strong>controls the rate of letting guests in</strong> based on how busy the kitchen is — not letting a crowd flood in and overwhelm it. The <strong>manager</strong> (QuotaCenter), with a global view, <strong>watches the kitchen's live metrics</strong> (burner occupancy, prep stock, plating delay), computes "how many tables per minute we can seat now", and tells the host to follow it.
  When the kitchen is truly about to blow, the manager issues a <strong>harsher order</strong>: "<strong>fully booked, stop seating</strong>" — better to hold new guests at the door (come back later) than let the diners already inside suffer too. <strong>Throttling is a gentle brake; rejection is the emergency brake</strong> — together they keep the restaurant from collapsing at the peak.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>QuotaCenter (<span class="inline">rootcoord/quota_center.go</span>) periodically <span class="mono">collectMetrics</span> from nodes (memory water level, disk, TT lag…) → <span class="mono">calculateRates</span> for each operation type (DML/DQL/DDL…) → pushes them to all Proxies; the Proxy's <span class="mono">RateLimitInterceptor</span> checks before each request and returns <span class="mono">ErrServiceRateLimit</span> (retriable) when over; under hard-limit overload, <span class="mono">forceDenyWriting/Reading</span> drives rates to 0, rejecting a whole class</strong>. Decide centrally, enforce at the edge.
</div>

<h2>Why self-protect: the essence of backpressure</h2>
<p>First a plain truth: <strong>a system's rate of digesting requests is finite, but clients won't restrain themselves</strong>. Let clients write infinitely fast and query infinitely much, and sooner or later you hit some <strong>hard resource ceiling</strong>: memory filled by unflushed growing segments, disk burst by binlogs, CPU saturated by queries. And then? <strong>Not a graceful slowdown but a crash</strong> — nodes OOM-killed, requests timing out en masse, even <strong>avalanche-style cascading failure</strong> (one node dies, its load shifts to others and crushes them too).</p>
<p>So mature systems hold an iron rule: <strong>better to slow down on purpose than be swept away</strong>. That's <strong>backpressure</strong> — when downstream can't keep up, <strong>push back on upstream to make it slow down</strong>. Like a clog downstream in a pipe: pressure travels back up the pipe, forcing the upstream tap to close partway. For a database, backpressure means: <strong>as the system nears its limit, actively reject or slow some new requests</strong>, reserving scarce resources for "work already in flight" — <strong>trading a little availability for not crashing overall</strong>. A classic engineering trade-off: <strong>better to say "no" to a few requests than let all of them die together</strong>. Grasp this core of "<strong>slow down on purpose to survive</strong>" and you've got the soul of quota/rate-limiting — it's not to vex users but the system's <strong>safety valve</strong>.</p>

<p>Worth untangling three terms people often conflate; they're really three links in one chain. <strong>Quota</strong> is the "<strong>allowance</strong>" — the per-second ceiling for a class of operation (configurable under <span class="mono">quotaAndLimits</span> in <span class="inline">configs/milvus.yaml</span>, Lesson 40). <strong>Rate limiting</strong> is the <strong>act of admitting against that allowance</strong> — counting at the entrance to decide whether to let a request through. <strong>Backpressure</strong> is the broader idea of <strong>pushing back</strong> — when downstream can't keep up, make upstream slow down. Put simply: <strong>backpressure is the goal, rate limiting is the means, and quota is the concrete number inside that means</strong>. Milvus deliberately lets QuotaCenter <strong>compute the quota dynamically</strong> from live metrics rather than hardcode a static value, so the safety valve <strong>tightens and loosens with the system's load</strong> — looser when idle, tighter when busy.</p>

<h2>QuotaCenter: the central governor</h2>
<p>Who decides "should we slow down now, and by how much"? It's <strong>QuotaCenter</strong> on RootCoord (<span class="inline">internal/rootcoord/quota_center.go</span>). It runs a <strong>periodic loop</strong>, each round doing three things: <strong>collect → compute → distribute</strong>. First, <span class="mono">collectMetrics()</span>: <strong>aggregate live metrics</strong> from all nodes — memory water level, disk usage, TimeTick lag (whether consumption keeps up with writes), queue depths. Second, <span class="mono">calculateRates()</span>: from these metrics, <strong>compute the allowed rate for each operation type right now</strong> — writes (DML), queries (DQL), DDL, index building, flush, compaction — each with its own quota. Third, <strong>push the computed limits to all Proxies</strong>.</p>
<p>Why put this on RootCoord, as a central component? Because <strong>rate-limit decisions need a global view</strong>. A single Proxy sees only the requests flowing through it; it has no idea "how much memory the whole cluster has left" or "how much write the other Proxies admitted in total". Only a central brain that can <strong>survey cluster-wide metrics</strong> can correctly decide "what the global limit should be now" — exactly the <strong>control plane</strong>'s job (Lesson 9): QuotaCenter decides, Proxies execute. This again echoes the guide's throughline: <strong>converge "decisions needing global info" to the center, spread "acting on decisions" to the edge</strong>. The diagram below is QuotaCenter's feedback loop.</p>

<div class="flow">
  <div class="node"><div class="nt">node metrics</div><div class="nd">memory level / disk / TT lag / queue depth</div></div>
  <div class="arrow">collectMetrics</div>
  <div class="node hl"><div class="nt">QuotaCenter (RootCoord)</div><div class="nd">calculateRates: per-op-type limits</div></div>
  <div class="arrow">push</div>
  <div class="node"><div class="nt">all Proxies</div><div class="nd">receive the latest limits</div></div>
  <div class="arrow">enforce</div>
  <div class="node"><div class="nt">allow / reject</div><div class="nd">over-limit → ErrServiceRateLimit</div></div>
</div>

<h2>Two brakes: throttle and force-deny</h2>
<p>QuotaCenter's "slowing down" isn't all-or-nothing but <strong>two levels of force</strong>, matching overload severity. First, <strong>throttle (cool-off)</strong>: when a metric <strong>approaches</strong> a warning line (say memory at 80%), gradually <strong>lower the rate</strong> for the matching operation, making requests "<strong>queue and go slowly</strong>", giving the system room to breathe and digest. A gentle brake — requests still get in, just slower.</p>
<p>Second, <strong>force-deny</strong>: when a metric <strong>breaches</strong> a hard limit (memory/disk water level too high, or TT lag dangerously large), QuotaCenter calls <span class="mono">forceDenyWriting</span> (drive DML rate straight to <strong>0</strong>, reject all writes) or <span class="mono">forceDenyReading</span> (DQL to 0, reject all reads). An emergency brake — <strong>a whole operation class is temporarily held at the door</strong> until the water level recedes to safety. Why such a "harsh" level? Because at the hard limit, <strong>admitting more means an OOM/disk-full crash</strong>; rather than total wipeout, <strong>decisively reject new requests to save the existing ones</strong>. Notably, <strong>writes and reads are managed separately</strong>: under memory/disk pressure, writes (the big resource hog) are often denied first, while reads may still go. The two brakes side by side:</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="Two brakes: as memory/disk usage and TT delay climb, first the throttle band kicks in (near the ~85% watermark, gradually lowering the rate so requests queue and slow), then hitting the hard limit triggers force-deny (forceDenyWriting/Reading, rate to zero, the whole class rejected)">
    <text x="60" y="44" style="fill:var(--muted)">memory / disk usage, TT delay　→　tighter as it climbs</text>
    <rect x="60" y="56" width="400" height="30" rx="6" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="260" y="76" text-anchor="middle" style="fill:var(--teal);font-weight:700">normal · full speed</text>
    <rect x="460" y="56" width="140" height="30" style="fill:var(--amber-soft);stroke:var(--amber)"/><text x="530" y="76" text-anchor="middle" style="fill:var(--amber);font-weight:700">throttle</text>
    <rect x="600" y="56" width="100" height="30" rx="6" style="fill:var(--red-soft);stroke:var(--red);stroke-width:2"/><text x="650" y="76" text-anchor="middle" style="fill:var(--red);font-weight:700">deny</text>
    <line x1="460" y1="50" x2="460" y2="92" style="stroke:var(--amber);stroke-dasharray:3 3"/><text x="460" y="104" text-anchor="middle" style="fill:var(--muted)">≈85% watermark</text>
    <line x1="600" y1="50" x2="600" y2="92" style="stroke:var(--red);stroke-dasharray:3 3"/><text x="600" y="104" text-anchor="middle" style="fill:var(--red)">hard limit ≈95%</text>
    <rect x="40" y="120" width="156" height="36" rx="8" style="fill:var(--amber-soft);stroke:var(--amber);stroke-width:1.5"/><text x="118" y="143" text-anchor="middle" style="fill:var(--amber);font-weight:700">① throttle</text>
    <text x="206" y="143" style="fill:var(--muted)">near ~85%: lower the rate, requests queue and slow (still in, just slower)</text>
    <rect x="40" y="164" width="156" height="36" rx="8" style="fill:var(--red-soft);stroke:var(--red);stroke-width:1.5"/><text x="118" y="187" text-anchor="middle" style="fill:var(--red);font-weight:700">② force-deny</text>
    <text x="206" y="187" style="fill:var(--muted)">hard limit hit: forceDeny writes/reads, rate→0, deny all (save the existing)</text>
    <text x="380" y="232" text-anchor="middle" style="fill:var(--ink);font-weight:700">gradual pressure + extreme backstop: throttle gently, hard-deny only at the wall</text>
    <text x="380" y="254" text-anchor="middle" style="fill:var(--muted)">writes and reads managed separately: under pressure deny writes first (the resource hog)</text>
  </svg>
  <div class="figcap"><b>Two brakes = gradual throttle + extreme deny</b>: <span class="mono">QuotaCenter</span> doesn't slow with one switch. As memory/disk usage and TT delay climb — <b>① throttle</b>: near the watermark (memory ~85%) it <b>gradually lowers the rate</b>, requests queue and slow (still get in, just slower — a gentle brake); <b>② force-deny</b>: hitting the hard limit calls <span class="mono">forceDenyWriting/forceDenyReading</span> to drop the rate <b>to 0 and reject the whole class</b> (an emergency brake — save the existing, avoid OOM / a full disk). Deny-only would thrash at the threshold; throttle-only can't hold a flood — <b>the two together are both smooth and safe</b>. Writes and reads are governed separately; under pressure, writes are denied first.</div>
</div>

<div class="cols">
  <div class="col"><h4>Throttle (gentle)</h4><p>as a metric <strong>approaches</strong> the warning line, gradually <strong>lower the rate</strong> so requests queue and go slowly. Requests still get in, just slower — room to breathe.</p></div>
  <div class="col"><h4>Force-deny (emergency)</h4><p>as a metric <strong>breaches</strong> a hard limit, <span class="mono">forceDenyWriting/Reading</span> drives that rate to <strong>0</strong>, rejecting the whole class until levels recede. Reject the new, save the existing.</p></div>
</div>

<h2>Enforced at the Proxy: RateLimitInterceptor</h2>
<p>Limits are decided by QuotaCenter, but the actual "stopping people" happens at the <strong>Proxy entrance</strong>. The Proxy has a <span class="mono">RateLimitInterceptor</span> (<span class="inline">internal/proxy/rate_limit_interceptor.go</span>) — a gRPC interceptor (recall Lesson 38, the Proxy uses interceptors for cross-cutting concerns) that <strong>every request passes first</strong>: it checks the current rate quota for the request type (write/read/DDL…), <strong>admitting if there's quota, rejecting on the spot if not</strong>, returning an <span class="mono">ErrServiceRateLimit</span> error.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Request reaches the Proxy</h4><p>a write/read/DDL request arrives and first hits the <span class="mono">RateLimitInterceptor</span>.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Check current quota</h4><p>by request type, check the latest limit QuotaCenter pushed: is there quota left?</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Enough → admit</h4><p>quota available, the request proceeds to normal handling (validate, enqueue, fan out…).</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Not enough → reject</h4><p>over limit, return <span class="mono">ErrServiceRateLimit</span> (retriable) on the spot; the client backs off and retries.</p></div></div>
</div>
<p>Here's a subtlety echoing Lesson 44: <span class="mono">ErrServiceRateLimit</span> is a <strong>retriable (System-class)</strong> error — it doesn't say "your request itself is wrong" (that's an Input error, where retry won't help) but "<strong>I'm busy now, come back shortly</strong>". So a client (SDK) receiving it <strong>should back off and retry later</strong>, not surface an error to the user. This is backpressure's <strong>gentle face</strong>: it turns "the system is overloaded" into a signal the <strong>client can understand and auto-handle</strong>, letting the whole call chain <strong>slow down in concert</strong> instead of colliding and crashing. To wrap up: <strong>QuotaCenter (central — global view, sets limits, force-deny on overload) + RateLimitInterceptor (edge — per-request enforcement, returns a retriable error when over)</strong>, one central and one edge, together form Milvus's <strong>self-protection safety valve</strong>. Every piece it uses you've seen — control-plane decisions (Lesson 9), interceptors (Lesson 38), retriable errors (Lesson 44), quota config (Lesson 40), metric monitoring (Lesson 39) — and this lesson twists them into one complete machine for "<strong>how a system survives overload</strong>".</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Why self-protect (backpressure)</strong>: finite capacity, unrestrained clients; hitting a hard resource ceiling causes crashes, even avalanches; better to slow down on purpose — trade a little availability for not crashing.</li>
    <li><strong>QuotaCenter (central governor)</strong>: a RootCoord loop of <span class="mono">collectMetrics</span> (memory/disk/TT lag) → <span class="mono">calculateRates</span> (per-op-type limits) → push to Proxies; rate decisions need a global view — control-plane work.</li>
    <li><strong>Two brakes</strong>: <strong>throttle</strong> (near the warning line → gradually lower, queue and go slow) and <strong>force-deny</strong> (breach a hard limit → <span class="mono">forceDenyWriting/Reading</span> to 0, reject the whole class); writes and reads managed separately.</li>
    <li><strong>Enforced at the Proxy</strong>: <span class="mono">RateLimitInterceptor</span> checks quota per request and returns <span class="mono">ErrServiceRateLimit</span> (<strong>retriable</strong>, meaning "busy, come back later"); central decision + edge enforcement. Reuses control plane/interceptor/merr/quota/metrics.</li>
  </ul>
</div>
""",
}

LESSON_50 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
作为进阶专题（第 11 部分）的收尾，这一课用一次<strong>巡礼</strong>，把几块"<strong>生产里常用、但前面没专门讲</strong>"的特性串起来过一遍：<strong>RBAC</strong>（权限）、<strong>资源组</strong>（节点隔离）、<strong>数据库</strong>（多租户）、<strong>迭代器</strong>（翻页取数）、<strong>TTL</strong>（数据过期）、<strong>Function</strong>（服务端处理）。每块只讲清"<strong>是什么、解决什么、住在哪</strong>"——它们大多不属核心引擎，但会在你把 Milvus 真正用进业务时<strong>一一登场</strong>。把它们认全，你的 Milvus 地图就<strong>从内核一直补到了生产边缘</strong>。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  把这些特性想成一栋<strong>写字楼的物业服务</strong>。<strong>门禁系统</strong>决定谁能进哪层、能开哪扇门（<strong>RBAC</strong>）；把楼层<strong>分区租给不同公司</strong>、互不打扰（<strong>资源组</strong>）；每家公司有<strong>独立的工商注册</strong>、账目分开（<strong>数据库 / 多租户</strong>）；档案室支持<strong>一页页翻阅</strong>而不必一次全搬出来（<strong>迭代器</strong>）；过期文件<strong>到点自动销毁</strong>（<strong>TTL</strong>）；前台能<strong>代收快递并就地加工</strong>（<strong>Function</strong>，如把文本就地转成向量）。
  这些都不是"盖楼"（核心引擎）的事，而是"<strong>让楼真正能营业、能租给很多家、还安全省心</strong>"的物业能力。一栋楼盖得再好，没有这些，也租不出去、管不起来。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong>RBAC(用户/角色/权限，<span class="inline">rootcoord</span>) 管"谁能做什么"；资源组(<span class="inline">querycoordv2/meta/resource_group.go</span>)把 QueryNode 分组隔离；数据库(<span class="mono">CreateDatabase</span>)在集合之上再加一层多租户；搜索/查询迭代器翻页取大结果集；Collection TTL(<span class="mono">CollectionTTLConfigKey</span>)让数据到点自动过期；Function 模块(<span class="inline">util/function</span>，BM25 / 文本嵌入)在服务端就地把数据加工成向量</strong>。这些是把引擎变成"可运营服务"的那层。
</div>

<h2>安全：RBAC（用户 / 角色 / 权限）</h2>
<p>一个真实的库不可能"谁连上都能为所欲为"。Milvus 提供完整的 <strong>RBAC（基于角色的访问控制）</strong>：先有<strong>用户</strong>（带凭证），把<strong>权限</strong>（建集合、插入、搜索、删除……）打包成<strong>角色</strong>，再把角色<strong>授予用户</strong>。这样管权限就不用"一个用户一个用户地配"，而是"<strong>定义几种角色、按角色发牌</strong>"——典型的<strong>读者</strong>角色只能搜不能写、<strong>管理员</strong>角色无所不能。相关能力在 <span class="inline">rootcoord</span>（<span class="mono">CreateRole</span> / <span class="mono">OperatePrivilege</span> / <span class="mono">CreateCredential</span>，见 <span class="inline">ddl_callbacks_rbac_credential.go</span>），还支持<strong>权限组（privilege group）</strong>把一批权限打包、以及内置的 <strong>public 角色</strong>。</p>

<div class="flow">
  <div class="node"><div class="nt">权限</div><div class="nd">建集合/插入/搜索/删除…</div></div>
  <div class="arrow">打包成</div>
  <div class="node hl"><div class="nt">角色</div><div class="nd">如 reader（只读）/ admin（全权）</div></div>
  <div class="arrow">授予</div>
  <div class="node"><div class="nt">用户</div><div class="nd">带凭证、按角色拿到权限</div></div>
</div>
<p>这里有个值得点出的细节：<strong>权限元数据也是元数据</strong>，所以它走的还是第 14 课那套"<strong>协调器 → Catalog → etcd</strong>"的存取，并通过 DDL 回调在集群里一致地生效——你不必为 RBAC 另学一套机制，它就嵌在你已经懂的那张元数据图里。一句话：<strong>RBAC 回答"谁能对什么做什么"</strong>，是任何多人、多业务共用一个集群时绕不开的第一道门。</p>

<p>这里值得多想一层：<strong>为什么是"基于角色"，而不是直接给用户配权限？</strong>设想一个有几百号人、几十种权限的系统，如果"<strong>每个用户单独配一串权限</strong>"，那光是维护"谁有哪些权限"就会变成一场噩梦——来个新人要手动勾一遍，权限要改一项得逐个用户改。角色这层<strong>中间抽象</strong>把这件事解了套：权限先归拢成<strong>有限的几种角色</strong>（读者、写入者、管理员…），用户只管<strong>领角色</strong>。于是"<strong>一类人该有什么权限</strong>"只需在角色上定义一次，新人入职<strong>发个角色</strong>即可，权限调整<strong>改角色、所有持该角色的人同步生效</strong>。这正是"<strong>多对多关系，用一个中间层解耦</strong>"的经典手法——和你在数据库设计、甚至代码架构里反复见到的"加一层中间抽象"是同一种智慧。RBAC 不是 Milvus 的发明，而是它<strong>遵循了业界成熟的权限模型</strong>，让你已有的运维经验能直接迁移过来。</p>

<h2>隔离与多租户：资源组 + 数据库</h2>
<p>当很多业务<strong>共用一个集群</strong>时，两个问题立刻冒出来：<strong>算力会不会互相抢？数据会不会互相看见？</strong>Milvus 用两件工具分别回答。<strong>资源组（Resource Group）</strong>解决"<strong>算力隔离</strong>"：它把 <strong>QueryNode 分成若干组</strong>（<span class="inline">querycoordv2/meta/resource_group.go</span>，每组有 <span class="mono">request/limit</span> 的容量配置），让不同业务的集合<strong>加载到不同的节点组</strong>上——这样 A 业务的大查询<strong>压不到</strong> B 业务的节点。需要时还能 <span class="mono">TransferNode</span> 在组间挪节点，弹性调配。</p>

<p>资源组这件事，背后是个很现实的<strong>"吵闹邻居"问题</strong>。设想没有资源组：A 业务和 B 业务的集合<strong>混在同一批 QueryNode</strong> 上，某天 A 跑了一个超大范围的批量检索，把这些节点的 CPU 和内存吃光——结果<strong>B 业务的在线查询也跟着变慢甚至超时</strong>，明明 B 什么都没做错。这就是"吵闹邻居"：<strong>共享资源时，一个租户的行为会殃及另一个</strong>。资源组的解法很直接：<strong>给关键业务划一块专属的节点</strong>，把它和别人的负载<strong>物理隔开</strong>。这和第 13 课 QueryCoord"把段分配到节点"是同一层的事，只不过资源组多加了一道"<strong>这些节点只服务这个组</strong>"的约束。理解了它，你就明白为什么严肃的多租户部署几乎都要用资源组——<strong>隔离不是奢侈，而是多租户共存的前提</strong>。</p>
<p><strong>数据库（Database）</strong>则解决"<strong>命名与数据隔离</strong>"：它在<strong>集合之上又加了一层</strong>。回忆第 6 课的层级是"集合 → 分区 → 段"；数据库把它再往上扩一层成"<strong>数据库 → 集合 → 分区 → 段</strong>"。不同租户用不同数据库，<strong>集合名互不冲突、权限可按库授予</strong>（<span class="mono">CreateDatabase</span>，默认库 <span class="mono">default</span>）。<strong>资源组管"算力分给谁"、数据库管"数据归谁"</strong>，两者配合，才让一个 Milvus 集群能<strong>体面地服务很多家租户</strong>。下面这张分层图把多租户的层级摆清。</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="多租户隔离的两条泳道：租户 A 用 Database A（命名/数据隔离）与资源组 A（QueryNode n1、n2，算力隔离），租户 B 用 Database B 与资源组 B（QueryNode n3、n4）；两条泳道互不重叠，A 的负载压不到 B 的节点、集合名也不冲突">
    <rect x="20" y="48" width="722" height="60" rx="10" style="fill:none;stroke:var(--teal);stroke-dasharray:5 4"/>
    <rect x="30" y="58" width="78" height="40" rx="8" style="fill:var(--teal-soft);stroke:var(--teal);stroke-width:1.5"/><text x="69" y="83" text-anchor="middle" style="fill:var(--teal);font-weight:700">租户 A</text>
    <line x1="108" y1="78" x2="124" y2="78" style="stroke:var(--teal);stroke-width:2"/><path d="M124,78 l-9,-4 l0,8 z" style="fill:var(--teal)"/>
    <rect x="126" y="58" width="138" height="40" rx="8" style="fill:var(--panel);stroke:var(--teal)"/><text x="195" y="76" text-anchor="middle" style="fill:var(--ink)">Database A</text><text x="195" y="92" text-anchor="middle" style="fill:var(--muted)">命名 / 数据隔离</text>
    <rect x="276" y="58" width="458" height="40" rx="8" style="fill:var(--panel);stroke:var(--teal)"/><text x="290" y="76" style="fill:var(--teal);font-weight:700">资源组 A</text><text x="290" y="92" style="fill:var(--muted)">算力隔离</text>
    <rect x="470" y="64" width="66" height="28" rx="6" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="503" y="83" text-anchor="middle" class="mono" style="fill:var(--teal)">n1</text>
    <rect x="544" y="64" width="66" height="28" rx="6" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="577" y="83" text-anchor="middle" class="mono" style="fill:var(--teal)">n2</text>
    <text x="676" y="83" text-anchor="middle" style="fill:var(--faint)">专属</text>
    <rect x="20" y="142" width="722" height="60" rx="10" style="fill:none;stroke:var(--purple);stroke-dasharray:5 4"/>
    <rect x="30" y="152" width="78" height="40" rx="8" style="fill:var(--purple-soft);stroke:var(--purple);stroke-width:1.5"/><text x="69" y="177" text-anchor="middle" style="fill:var(--purple);font-weight:700">租户 B</text>
    <line x1="108" y1="172" x2="124" y2="172" style="stroke:var(--purple);stroke-width:2"/><path d="M124,172 l-9,-4 l0,8 z" style="fill:var(--purple)"/>
    <rect x="126" y="152" width="138" height="40" rx="8" style="fill:var(--panel);stroke:var(--purple)"/><text x="195" y="170" text-anchor="middle" style="fill:var(--ink)">Database B</text><text x="195" y="186" text-anchor="middle" style="fill:var(--muted)">命名 / 数据隔离</text>
    <rect x="276" y="152" width="458" height="40" rx="8" style="fill:var(--panel);stroke:var(--purple)"/><text x="290" y="170" style="fill:var(--purple);font-weight:700">资源组 B</text><text x="290" y="186" style="fill:var(--muted)">算力隔离</text>
    <rect x="470" y="158" width="66" height="28" rx="6" style="fill:var(--purple-soft);stroke:var(--purple)"/><text x="503" y="177" text-anchor="middle" class="mono" style="fill:var(--purple)">n3</text>
    <rect x="544" y="158" width="66" height="28" rx="6" style="fill:var(--purple-soft);stroke:var(--purple)"/><text x="577" y="177" text-anchor="middle" class="mono" style="fill:var(--purple)">n4</text>
    <text x="676" y="177" text-anchor="middle" style="fill:var(--faint)">专属</text>
    <text x="380" y="234" text-anchor="middle" style="fill:var(--ink);font-weight:700">两条泳道互不重叠：资源组隔算力（节点池）、数据库隔数据（命名/权限）</text>
    <text x="380" y="256" text-anchor="middle" style="fill:var(--muted)">A 的大查询压不到 B 的节点、集合名也不冲突——"吵闹邻居"被物理隔开</text>
  </svg>
  <div class="figcap"><b>多租户隔离 = 资源组（算力）+ 数据库（数据）</b>：很多业务共用一个集群时，怕"<b>抢算力、串数据</b>"。<b>资源组</b>解决<b>算力隔离</b>：把 QueryNode 分成若干组（如 A 用 <span class="mono">n1,n2</span>、B 用 <span class="mono">n3,n4</span>），不同业务的集合加载到不同节点组，<b>A 的大查询压不到 B 的节点</b>（需要时还能 <span class="mono">TransferNode</span> 在组间挪）。<b>数据库</b>解决<b>命名/数据隔离</b>：在集合之上再加一层（数据库 → 集合 → 分区 → 段），不同租户用不同库，<b>集合名不冲突、权限按库授予</b>。两条泳道互不重叠，"吵闹邻居"被隔开——隔离不是奢侈，而是多租户共存的前提。</div>
</div>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">数据库</span><span class="name">Database（多租户的最外层）</span></div><div class="ld">不同租户用不同库；集合名互不冲突、权限/配额可按库管(默认库 default)</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">集合·分区</span><span class="name">Collection → Partition（第 6 课）</span></div><div class="ld">一个库下的表与切分；段(Segment)是其下的物理单位</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">资源组</span><span class="name">Resource Group（算力隔离，正交一层）</span></div><div class="ld">把 QueryNode 分组，让不同业务的加载/查询落在不同节点组，互不抢算力</div></div>
</div>

<h2>取数的便利：迭代器 与 TTL</h2>
<p>两个小而实用的特性，专治"大结果"和"老数据"。<strong>迭代器（Search / Query Iterator）</strong>解决"<strong>结果太多、一次取不完</strong>"：普通搜索返回 topK，但有时你要<strong>遍历海量匹配</strong>（比如导出所有满足条件的行）。迭代器让你像<strong>翻页</strong>一样分批取——取一批、记住位置、再取下一批，而不必把几百万条结果<strong>一次性塞进内存</strong>。它在 Proxy 的搜索/查询路径里实现，是把"检索"从"只取最像的几条"扩展到"<strong>可遍历的数据访问</strong>"的关键。</p>
<p><strong>TTL（Time To Live，存活时间）</strong>解决"<strong>老数据该自动清走</strong>"：给集合设一个 TTL（<span class="mono">CollectionTTLConfigKey</span> / <span class="mono">collection.ttl.seconds</span>），<strong>超过这个寿命的数据会被自动判定为过期</strong>、在后续的 compaction（第 19 课）里被清理掉，查询时也不再可见。这对"<strong>只关心最近一段时间</strong>"的场景（日志、会话、时效性内容）极其省心——你不用写定时任务手动删旧数据，<strong>设个 TTL，系统替你忘掉过期的</strong>。它复用的正是第 19、20 课你已经懂的 compaction 与"按条件剔除可见行"的机制：TTL 不过是给"该不该看见这行"的判断，多加了一条"<strong>它过期了吗</strong>"。</p>

<p>把迭代器和 TTL 放在一起看，会发现它们其实是<strong>同一种成熟度的体现</strong>：一个能用进生产的数据库，光"<strong>存得下、搜得到</strong>"还不够，还得照顾<strong>真实数据的全生命周期与全访问模式</strong>。数据会<strong>变老</strong>——所以要有 TTL 帮你自动清理，而不是任由旧数据无限堆积、拖慢查询、吃光磁盘。结果会<strong>很多</strong>——所以要有迭代器让你能<strong>从容地分批取走</strong>，而不是被"一次只给 topK"卡住、或被"一次全给"撑爆内存。这些特性单看都不起眼，却恰恰是<strong>区分"能跑的 demo"和"扛得住生产的系统"</strong>的地方。Milvus 把这些"<strong>不性感但必要</strong>"的能力一点点补齐，正说明它是个<strong>认真面向生产</strong>的项目——而你能读懂它们各自解决什么问题、复用了哪些你已经学过的机制（compaction、可见性、Proxy 查询路径），也说明你对 Milvus 的理解，已经从"<strong>它怎么工作</strong>"长到了"<strong>怎么把它用好</strong>"。</p>

<h2>服务端处理：Function 模块</h2>
<p>最后一站，是一个让 Milvus 越来越"<strong>开箱即用</strong>"的方向：<strong>Function（函数）模块</strong>（<span class="inline">internal/util/function</span>）。传统用法里，"<strong>把文本变成向量</strong>"这件事是在<strong>客户端</strong>做的——你先用一个模型把文本转成 embedding，再把向量插进 Milvus。Function 模块把这一步<strong>搬进了服务端</strong>：你直接插入<strong>原始文本</strong>，Milvus 用配置好的 function <strong>就地把它加工成向量</strong>再存。</p>

<div class="flow">
  <div class="node"><div class="nt">插入原始文本</div><div class="nd">客户端只发文本，不发向量</div></div>
  <div class="arrow">服务端 function</div>
  <div class="node hl"><div class="nt">BM25 / 嵌入模型</div><div class="nd">就地把文本→稀疏/稠密向量</div></div>
  <div class="arrow">入库</div>
  <div class="node"><div class="nt">向量字段</div><div class="nd">写检索用同一套向量化逻辑</div></div>
</div>
<p>典型的两类：<strong>BM25 function</strong>（<span class="mono">FunctionType_BM25</span>）把文本就地转成<strong>稀疏向量</strong>（正是第 24、48 课全文检索/混合检索要用的那种）；<strong>文本嵌入 function</strong>则在服务端调用嵌入模型，把文本转成<strong>稠密向量</strong>。这带来的好处是<strong>简化客户端</strong>：业务只管插原始数据，"<strong>怎么向量化</strong>"交给服务端统一处理，既少了客户端的模型依赖，又保证了<strong>写入和检索用的是同一套向量化逻辑</strong>（否则两边模型不一致，检索质量会悄悄崩坏）。这也呼应了第 48 课——Milvus 正越来越多地把"<strong>检索增强</strong>"该有的能力（混合检索、重排、服务端嵌入）<strong>内建进来</strong>，让它从一个"<strong>纯向量存取引擎</strong>"长成一个"<strong>开箱即用的检索平台</strong>"。</p>

<p>Function 模块还藏着一个不易察觉、却极重要的<strong>正确性保障</strong>：写入和检索<strong>用同一套向量化逻辑</strong>。想想看，如果向量化在客户端做，你很容易踩这个坑——<strong>写入时用模型 A 把文档转成向量入库，检索时却用模型 B（或同模型的不同版本）把查询转成向量</strong>，两套向量"不在同一个空间里"，算出来的距离<strong>毫无意义</strong>，检索质量会<strong>悄无声息地崩坏</strong>，还极难排查（代码不报错、只是结果变差）。把向量化收进服务端的 Function，就<strong>从源头上杜绝</strong>了这种不一致：写也好、查也好，都走<strong>同一个 function</strong>，保证落在同一个向量空间。这是个很好的例子，说明"<strong>把易错的事统一收口</strong>"的价值——和第 40 课"配置收口 paramtable"、第 44 课"错误收口 merr"是同一种工程审美：<strong>让正确成为默认，让易错无处发生</strong>。</p>

<table class="t">
  <tr><th>特性</th><th>解决什么</th><th>住在哪</th></tr>
  <tr><td><strong>RBAC</strong></td><td>谁能对什么做什么（安全）</td><td class="mono">rootcoord（角色/权限/凭证）</td></tr>
  <tr><td><strong>资源组</strong></td><td>算力隔离：业务间不抢节点</td><td class="mono">querycoordv2/meta/resource_group</td></tr>
  <tr><td><strong>数据库</strong></td><td>多租户：命名与数据隔离</td><td class="mono">rootcoord（集合之上一层）</td></tr>
  <tr><td><strong>迭代器</strong></td><td>翻页遍历海量结果</td><td>Proxy 搜索/查询路径</td></tr>
  <tr><td><strong>TTL</strong></td><td>老数据到点自动过期清理</td><td>compaction + 可见性(第 19/20 课)</td></tr>
  <tr><td><strong>Function</strong></td><td>服务端就地把文本变向量</td><td class="mono">util/function（BM25/嵌入）</td></tr>
</table>

<p style="margin-top:1rem">巡礼到此，整份《Milvus 图解教程》——从"什么是向量数据库"，到写入/查询/索引/流式/C++ 内核，到 API、可观测、配置、部署、贡献，再到这一部分的进阶特性——<strong>就真正画上句号了</strong>。你手里这张 Milvus 地图，已经<strong>从最核心的引擎，一直铺到了生产运营的边缘</strong>。愿它陪你把一个庞大的系统，看成一幅可以理解、可以动手、也可以参与的图景。<strong>去用它、去改它、去贡献它吧。</strong></p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>RBAC</strong>：用户→角色→权限(rootcoord)，按角色发牌管"谁能做什么"；权限元数据走第 14 课的元数据存取，含权限组与内置 public 角色。</li>
    <li><strong>隔离/多租户</strong>：资源组(<span class="inline">querycoordv2/meta/resource_group</span>)把 QueryNode 分组隔离算力；数据库(<span class="mono">CreateDatabase</span>)在集合之上加一层、隔离命名与数据。算力归谁 + 数据归谁。</li>
    <li><strong>迭代器 / TTL</strong>：迭代器像翻页一样分批遍历海量结果(不一次塞内存)；Collection TTL 让老数据到点自动过期、随 compaction 清理(复用第 19/20 课)。</li>
    <li><strong>Function</strong>：服务端就地把文本加工成向量——BM25→稀疏向量、嵌入模型→稠密向量；简化客户端、保证写检索向量化一致。Milvus 正长成开箱即用的检索平台。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
To close Part 11, this lesson is a <strong>quick tour</strong> of several features that are "<strong>common in production but not covered before</strong>": <strong>RBAC</strong> (permissions), <strong>resource groups</strong> (node isolation), <strong>databases</strong> (multi-tenancy), <strong>iterators</strong> (paging), <strong>TTL</strong> (data expiry), and <strong>Function</strong> (server-side processing). Each gets a "<strong>what it is, what it solves, where it lives</strong>" — most aren't core engine, but they show up one by one as you put Milvus to real use. Learn them all and your Milvus map <strong>extends from the kernel all the way to the production edge</strong>.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of these as an <strong>office building's facility services</strong>. An <strong>access-control system</strong> decides who enters which floor and opens which door (<strong>RBAC</strong>); floors are <strong>zoned and rented to different companies</strong> without interference (<strong>resource groups</strong>); each company has its own <strong>business registration</strong> with separate books (<strong>databases / multi-tenancy</strong>); the archive room lets you <strong>browse page by page</strong> rather than haul everything out at once (<strong>iterators</strong>); expired files are <strong>auto-shredded on schedule</strong> (<strong>TTL</strong>); and the front desk can <strong>receive and process deliveries on the spot</strong> (<strong>Function</strong>, e.g. turning text into vectors right there).
  None of this is "constructing the building" (the core engine); it's the facility power that <strong>makes the building actually rentable to many tenants, safely and effortlessly</strong>. However well built, without these a building can't be leased or managed.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>RBAC (users/roles/privileges, <span class="inline">rootcoord</span>) governs "who can do what"; resource groups (<span class="inline">querycoordv2/meta/resource_group.go</span>) partition QueryNodes for isolation; databases (<span class="mono">CreateDatabase</span>) add a multi-tenancy layer above collections; search/query iterators page through large result sets; Collection TTL (<span class="mono">CollectionTTLConfigKey</span>) auto-expires old data; the Function module (<span class="inline">util/function</span>, BM25 / text embedding) turns data into vectors server-side</strong>. This is the layer that turns an engine into an operable service.
</div>

<h2>Security: RBAC (users / roles / privileges)</h2>
<p>A real database can't let "anyone who connects do anything". Milvus offers full <strong>RBAC (role-based access control)</strong>: there are <strong>users</strong> (with credentials), <strong>privileges</strong> (create collection, insert, search, delete…) are bundled into <strong>roles</strong>, and roles are <strong>granted to users</strong>. So managing permissions isn't "configure user by user" but "<strong>define a few roles and deal them out</strong>" — a typical <strong>reader</strong> role can only search, an <strong>admin</strong> role can do everything. The capabilities live in <span class="inline">rootcoord</span> (<span class="mono">CreateRole</span> / <span class="mono">OperatePrivilege</span> / <span class="mono">CreateCredential</span>, see <span class="inline">ddl_callbacks_rbac_credential.go</span>), with <strong>privilege groups</strong> bundling a set of privileges and a built-in <strong>public role</strong>.</p>

<div class="flow">
  <div class="node"><div class="nt">privileges</div><div class="nd">create coll/insert/search/delete…</div></div>
  <div class="arrow">bundled into</div>
  <div class="node hl"><div class="nt">role</div><div class="nd">e.g. reader (read-only) / admin (full)</div></div>
  <div class="arrow">granted to</div>
  <div class="node"><div class="nt">user</div><div class="nd">with credentials, gets privileges by role</div></div>
</div>
<p>A worthwhile detail: <strong>permission metadata is metadata too</strong>, so it travels the same Lesson 14 path of "<strong>coordinator → Catalog → etcd</strong>" and takes effect consistently across the cluster via DDL callbacks — you needn't learn a separate mechanism for RBAC; it's embedded in the metadata picture you already know. In a line: <strong>RBAC answers "who can do what to what"</strong>, the first gate you can't skip whenever many people or workloads share one cluster.</p>

<h2>Isolation &amp; multi-tenancy: resource groups + databases</h2>
<p>When many workloads <strong>share one cluster</strong>, two questions arise immediately: <strong>will they fight over compute? will they see each other's data?</strong> Milvus answers each with a tool. <strong>Resource Groups</strong> solve <strong>compute isolation</strong>: they <strong>partition QueryNodes into groups</strong> (<span class="inline">querycoordv2/meta/resource_group.go</span>, each with a <span class="mono">request/limit</span> capacity config), so different workloads' collections <strong>load onto different node groups</strong> — workload A's big query <strong>can't crush</strong> workload B's nodes. When needed, <span class="mono">TransferNode</span> moves nodes between groups for elastic allocation.</p>

<p>Resource groups exist to tame a very real <strong>"noisy neighbor" problem</strong>. Picture no resource groups: workload A's and workload B's collections <strong>share the same QueryNodes</strong>, and one day A runs a huge-range batch search that devours those nodes' CPU and memory — so <strong>B's online queries slow down or time out, even though B did nothing wrong</strong>. That's the noisy neighbor: <strong>when resources are shared, one tenant's behavior spills over onto another</strong>. The fix is direct — <strong>carve out dedicated nodes for the important workload and physically isolate it</strong> from everyone else's load. It's the same layer as Lesson 13's QueryCoord assigning segments to nodes, just with the added constraint that "<strong>these nodes serve only this group</strong>". That's why serious multi-tenant deployments almost always reach for resource groups — <strong>isolation isn't a luxury but a precondition for tenants coexisting</strong>.</p>
<p><strong>Databases</strong> solve <strong>naming and data isolation</strong>: they add <strong>another layer above collections</strong>. Recall Lesson 6's hierarchy "collection → partition → segment"; databases extend it upward into "<strong>database → collection → partition → segment</strong>". Different tenants use different databases, so <strong>collection names don't clash and permissions can be granted per database</strong> (<span class="mono">CreateDatabase</span>, default DB <span class="mono">default</span>). <strong>Resource groups govern "who gets compute", databases govern "whose data is whose"</strong>; together they let one Milvus cluster <strong>serve many tenants gracefully</strong>. The layered diagram lays out the multi-tenancy hierarchy.</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="Two non-overlapping lanes of multi-tenant isolation: tenant A uses Database A (naming/data isolation) and Resource Group A (QueryNode n1, n2 — compute isolation); tenant B uses Database B and Resource Group B (QueryNode n3, n4); the lanes never overlap, so A's load can't touch B's nodes and collection names don't clash">
    <rect x="20" y="48" width="722" height="60" rx="10" style="fill:none;stroke:var(--teal);stroke-dasharray:5 4"/>
    <rect x="30" y="58" width="78" height="40" rx="8" style="fill:var(--teal-soft);stroke:var(--teal);stroke-width:1.5"/><text x="69" y="83" text-anchor="middle" style="fill:var(--teal);font-weight:700">tenant A</text>
    <line x1="108" y1="78" x2="124" y2="78" style="stroke:var(--teal);stroke-width:2"/><path d="M124,78 l-9,-4 l0,8 z" style="fill:var(--teal)"/>
    <rect x="126" y="58" width="138" height="40" rx="8" style="fill:var(--panel);stroke:var(--teal)"/><text x="195" y="76" text-anchor="middle" style="fill:var(--ink)">Database A</text><text x="195" y="92" text-anchor="middle" style="fill:var(--muted)">naming / data iso</text>
    <rect x="276" y="58" width="458" height="40" rx="8" style="fill:var(--panel);stroke:var(--teal)"/><text x="290" y="76" style="fill:var(--teal);font-weight:700">Resource Group A</text><text x="290" y="92" style="fill:var(--muted)">compute iso</text>
    <rect x="470" y="64" width="66" height="28" rx="6" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="503" y="83" text-anchor="middle" class="mono" style="fill:var(--teal)">n1</text>
    <rect x="544" y="64" width="66" height="28" rx="6" style="fill:var(--teal-soft);stroke:var(--teal)"/><text x="577" y="83" text-anchor="middle" class="mono" style="fill:var(--teal)">n2</text>
    <text x="676" y="83" text-anchor="middle" style="fill:var(--faint)">exclusive</text>
    <rect x="20" y="142" width="722" height="60" rx="10" style="fill:none;stroke:var(--purple);stroke-dasharray:5 4"/>
    <rect x="30" y="152" width="78" height="40" rx="8" style="fill:var(--purple-soft);stroke:var(--purple);stroke-width:1.5"/><text x="69" y="177" text-anchor="middle" style="fill:var(--purple);font-weight:700">tenant B</text>
    <line x1="108" y1="172" x2="124" y2="172" style="stroke:var(--purple);stroke-width:2"/><path d="M124,172 l-9,-4 l0,8 z" style="fill:var(--purple)"/>
    <rect x="126" y="152" width="138" height="40" rx="8" style="fill:var(--panel);stroke:var(--purple)"/><text x="195" y="170" text-anchor="middle" style="fill:var(--ink)">Database B</text><text x="195" y="186" text-anchor="middle" style="fill:var(--muted)">naming / data iso</text>
    <rect x="276" y="152" width="458" height="40" rx="8" style="fill:var(--panel);stroke:var(--purple)"/><text x="290" y="170" style="fill:var(--purple);font-weight:700">Resource Group B</text><text x="290" y="186" style="fill:var(--muted)">compute iso</text>
    <rect x="470" y="158" width="66" height="28" rx="6" style="fill:var(--purple-soft);stroke:var(--purple)"/><text x="503" y="177" text-anchor="middle" class="mono" style="fill:var(--purple)">n3</text>
    <rect x="544" y="158" width="66" height="28" rx="6" style="fill:var(--purple-soft);stroke:var(--purple)"/><text x="577" y="177" text-anchor="middle" class="mono" style="fill:var(--purple)">n4</text>
    <text x="676" y="177" text-anchor="middle" style="fill:var(--faint)">exclusive</text>
    <text x="380" y="234" text-anchor="middle" style="fill:var(--ink);font-weight:700">two lanes never overlap: resource groups isolate compute, databases isolate data</text>
    <text x="380" y="256" text-anchor="middle" style="fill:var(--muted)">A's big query can't touch B's nodes, names don't clash — noisy neighbor fenced off</text>
  </svg>
  <div class="figcap"><b>Multi-tenant isolation = resource groups (compute) + databases (data)</b>: when many workloads share a cluster, you fear "<b>compute contention, data leakage</b>". <b>Resource groups</b> give <b>compute isolation</b>: split QueryNodes into groups (A uses <span class="mono">n1,n2</span>, B uses <span class="mono">n3,n4</span>) and load different workloads onto different node groups, so <b>A's big query can't touch B's nodes</b> (and <span class="mono">TransferNode</span> can move nodes between groups). <b>Databases</b> give <b>naming/data isolation</b>: a layer above collections (database → collection → partition → segment); different tenants use different DBs, so <b>names don't clash and permissions are per-database</b>. Two non-overlapping lanes — the noisy neighbor is fenced off; isolation isn't a luxury but the premise of multi-tenancy.</div>
</div>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">database</span><span class="name">Database (the outermost multi-tenancy layer)</span></div><div class="ld">different tenants use different DBs; collection names don't clash, permissions/quota per DB (default DB: default)</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">coll·part</span><span class="name">Collection → Partition (Lesson 6)</span></div><div class="ld">tables and partitioning within a DB; Segment is the physical unit below</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">res group</span><span class="name">Resource Group (compute isolation, an orthogonal layer)</span></div><div class="ld">partition QueryNodes so different workloads' loads/queries land on different node groups, no compute contention</div></div>
</div>

<h2>Convenient retrieval: iterators &amp; TTL</h2>
<p>Two small, practical features for "big results" and "old data". <strong>Iterators (Search / Query Iterator)</strong> solve "<strong>too many results to fetch at once</strong>": a normal search returns topK, but sometimes you must <strong>traverse a huge match set</strong> (e.g. export all qualifying rows). Iterators let you fetch in batches like <strong>turning pages</strong> — take a batch, remember the position, take the next — without <strong>cramming millions of results into memory at once</strong>. Implemented in the Proxy search/query path, they're key to extending "search" from "fetch just the most similar few" to "<strong>traversable data access</strong>".</p>
<p><strong>TTL (Time To Live)</strong> solves "<strong>old data should auto-clear</strong>": set a TTL on a collection (<span class="mono">CollectionTTLConfigKey</span> / <span class="mono">collection.ttl.seconds</span>), and <strong>data past that lifespan is automatically judged expired</strong>, cleaned up in later compaction (Lesson 19), and no longer visible to queries. For "<strong>only the recent window matters</strong>" cases (logs, sessions, time-sensitive content) it's a huge relief — no cron job to delete old data manually; <strong>set a TTL and the system forgets the expired for you</strong>. It reuses exactly the compaction and "exclude rows by condition from visibility" mechanisms you learned in Lessons 19–20: TTL just adds one more clause to "should this row be visible" — "<strong>has it expired?</strong>".</p>

<h2>Server-side processing: the Function module</h2>
<p>The last stop is a direction making Milvus increasingly "<strong>batteries-included</strong>": the <strong>Function module</strong> (<span class="inline">internal/util/function</span>). Traditionally, "<strong>turn text into vectors</strong>" happens on the <strong>client</strong> — you first run a model to embed the text, then insert the vectors into Milvus. The Function module <strong>moves this step server-side</strong>: you insert <strong>raw text</strong> directly, and Milvus uses a configured function to <strong>turn it into vectors on the spot</strong> before storing.</p>

<div class="flow">
  <div class="node"><div class="nt">insert raw text</div><div class="nd">client sends text, not vectors</div></div>
  <div class="arrow">server-side function</div>
  <div class="node hl"><div class="nt">BM25 / embedding model</div><div class="nd">text → sparse/dense vector on the spot</div></div>
  <div class="arrow">store</div>
  <div class="node"><div class="nt">vector field</div><div class="nd">write &amp; search share one vectorization</div></div>
</div>
<p>Two typical kinds: a <strong>BM25 function</strong> (<span class="mono">FunctionType_BM25</span>) turns text into <strong>sparse vectors</strong> (exactly what Lessons 24 and 48's full-text/hybrid search need); a <strong>text-embedding function</strong> calls an embedding model server-side to turn text into <strong>dense vectors</strong>. The benefit is a <strong>simpler client</strong>: the workload just inserts raw data, and "<strong>how to vectorize</strong>" is handled uniformly server-side — fewer client model dependencies, and a guarantee that <strong>writes and searches use the same vectorization logic</strong> (else mismatched models on the two sides quietly wreck search quality). This echoes Lesson 48 — Milvus increasingly <strong>builds in</strong> the capabilities retrieval-augmentation needs (hybrid search, reranking, server-side embedding), growing from a "<strong>pure vector store</strong>" into a "<strong>batteries-included retrieval platform</strong>".</p>

<table class="t">
  <tr><th>Feature</th><th>What it solves</th><th>Where it lives</th></tr>
  <tr><td><strong>RBAC</strong></td><td>who can do what to what (security)</td><td class="mono">rootcoord (roles/privileges/creds)</td></tr>
  <tr><td><strong>Resource group</strong></td><td>compute isolation: workloads don't fight for nodes</td><td class="mono">querycoordv2/meta/resource_group</td></tr>
  <tr><td><strong>Database</strong></td><td>multi-tenancy: naming &amp; data isolation</td><td class="mono">rootcoord (a layer above collections)</td></tr>
  <tr><td><strong>Iterator</strong></td><td>page through huge result sets</td><td>Proxy search/query path</td></tr>
  <tr><td><strong>TTL</strong></td><td>old data auto-expires &amp; is cleaned</td><td>compaction + visibility (L19/20)</td></tr>
  <tr><td><strong>Function</strong></td><td>turn text into vectors server-side</td><td class="mono">util/function (BM25/embedding)</td></tr>
</table>

<p style="margin-top:1rem">With this tour, the whole <strong>Milvus Visual Guide</strong> — from "what is a vector database", through write/query/indexing/streaming/the C++ core, through API, observability, config, deployment, contributing, to this part's advanced features — <strong>truly comes to a close</strong>. The Milvus map in your hands now <strong>stretches from the innermost engine all the way to the production edge</strong>. May it help you see a vast system as a landscape you can understand, work with, and join. <strong>Go use it, change it, contribute to it.</strong></p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>RBAC</strong>: users→roles→privileges (rootcoord), dealing out by role to govern "who can do what"; permission metadata travels Lesson 14's metadata path, with privilege groups and a built-in public role.</li>
    <li><strong>Isolation/multi-tenancy</strong>: resource groups (<span class="inline">querycoordv2/meta/resource_group</span>) partition QueryNodes for compute isolation; databases (<span class="mono">CreateDatabase</span>) add a layer above collections for naming/data isolation. Who gets compute + whose data is whose.</li>
    <li><strong>Iterators / TTL</strong>: iterators page through huge result sets (no cramming memory); Collection TTL auto-expires old data, cleaned by compaction (reusing L19/20).</li>
    <li><strong>Function</strong>: vectorize text server-side — BM25→sparse, embedding model→dense; simpler clients, consistent write/search vectorization. Milvus is growing into a batteries-included retrieval platform.</li>
  </ul>
</div>
""",
}
