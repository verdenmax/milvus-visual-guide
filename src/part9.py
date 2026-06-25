"""Content for Part 9 (API, tools & operations). Lessons 38-41.

Bilingual {"zh","en"} dicts mirroring part1-8. Facts verified against
internal/distributed/proxy (gRPC + REST), internal/proxy/impl.go, the
milvus-proto MilvusService contract, pkg observability (mlog/metrics/trace),
paramtable + configs/milvus.yaml, and deployment scripts/helm.
"""

LESSON_38 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前八部分我们一路从宏观架构钻到 C++ 内核。从这一部分（第九部分）起，我们回到<strong>用户能直接摸到的那一层</strong>——API、工具与运维。第一课先看最贴近你的东西：<strong>你写的客户端代码，到底是怎么和 Milvus 对话的？</strong>答案的核心是一份<strong>契约</strong>（milvus-proto）和一个<strong>门面</strong>（Proxy）：所有语言的 SDK 都照着同一份 proto 说话，经 gRPC（或 REST）抵达 Proxy，再由它转身指挥整个集群。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  把 Milvus 的 API 想成一家<strong>跨国餐厅</strong>。墙上挂着一份<strong>标准菜单</strong>（<span class="mono">milvus-proto</span>）：每道菜叫什么、要哪些配料、上桌是什么样，写得清清楚楚、<strong>全球统一</strong>。服务员有<strong>说各种语言的</strong>（Python、Go、Java、Node 的 SDK），但他们点的都是<strong>同一份菜单</strong>，所以你用哪国话点"宫保鸡丁"，端上来的都是同一道菜。
  顾客进店有<strong>两道门</strong>：正门走 <strong>gRPC</strong>（高效、二进制），侧门走 <strong>REST/HTTP</strong>（人人会用的 JSON）；但两道门通向的是<strong>同一个后厨</strong>——<span class="mono">Proxy</span>。后厨才是真正派活、协调上菜的地方。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong>所有 Milvus API 由一份 <span class="mono">milvus-proto</span> 的 <span class="mono">MilvusService</span> 定义（生成为 <span class="mono">milvuspb</span>），各语言 SDK 都照它说话；请求经 gRPC 或 REST 抵达 Proxy 的"传输层"(<span class="inline">internal/distributed/proxy</span>)，再转交"逻辑层"(<span class="inline">internal/proxy/impl.go</span>) 真正处理</strong>。一份契约统一所有客户端，一个 Proxy 门面统一所有入口。
</div>

<h2>一份契约定义所有 API：milvus-proto</h2>
<p>Milvus 的所有对外能力——建集合、插入、搜索、查询、建索引、加载……——都不是各 SDK 各写各的，而是<strong>集中定义在一份协议里</strong>：<span class="mono">milvus-proto</span>（仓库 <span class="mono">github.com/milvus-io/milvus-proto</span>）。它用 <strong>Protocol Buffers</strong> 描述了一个叫 <span class="mono">MilvusService</span> 的 gRPC 服务，以及每个接口的<strong>请求/响应消息</strong>：<span class="mono">SearchRequest</span> / <span class="mono">SearchResults</span>、<span class="mono">InsertRequest</span>、<span class="mono">CreateCollectionRequest</span>……这些定义一经编译，就生成各语言的代码——Go 侧生成的包叫 <span class="mono">milvuspb</span>（在 <span class="mono">go-api/v3</span> 里）。</p>

<p>先打个比方理解"契约"为什么重要。设想没有这份统一协议会怎样：Python SDK 的作者按自己的理解约定"搜索请求里 topK 这个字段叫 limit、放第 3 个位置"，Go SDK 的作者却约定"叫 top_k、放第 5 个位置"，服务端再各自去猜……只要有一处理解不一致，就会冒出"<strong>这边发的、那边读不对</strong>"的诡异 bug，而且极难排查。proto 契约把这种"口头约定"变成了"<strong>白纸黑字、机器可校验</strong>"的规范：字段叫什么、什么类型、第几号、是否必填，全部钉死在一份文件里。服务端和所有 SDK 都以它为准、由它生成代码，于是"理解不一致"这种问题<strong>从根上就不可能发生</strong>。这就是为什么在任何需要"多方协作、跨语言对接"的系统里，<strong>先定契约</strong>都是头等大事——契约是各方信任的锚点。Milvus 把这份锚点放在一个<strong>独立仓库</strong>里单独维护、单独发版，正是因为它的稳定与权威，比任何一端的实现都更重要。</p>
<p>"<strong>以 proto 为唯一事实来源</strong>"是这套设计的灵魂。因为服务端和所有客户端 SDK 都<strong>从同一份 proto 生成或绑定</strong>，所以它们对"一次搜索请求长什么样、返回什么字段"有<strong>完全一致的理解</strong>，不会出现"Python 以为是这样、Go 以为是那样"的鸡同鸭讲。想加一个新接口或给请求加一个字段？先改 proto，再各端重新生成——<strong>契约先行，实现跟上</strong>。这也是为什么第 8 部分反复提醒你"<strong>proto 类型住在 milvus-proto/go-api，而不是 milvus 仓库自己的 pkg/proto</strong>"：对外 API 的契约是一个<strong>独立、共享</strong>的仓库，Milvus 主仓只是它的一个使用者。把契约独立出来，多语言生态才能围着同一个中心转。</p>

<p>再多说一句 Protocol Buffers 为什么适合做这件事。它是一种<strong>与语言无关的接口描述语言（IDL）</strong>：你只写一份 <span class="mono">.proto</span> 文件描述"消息长什么样、服务有哪些方法"，再用代码生成器一键产出 Python、Go、Java 等各语言的<strong>强类型代码</strong>。相比让每种语言手写一套"怎么把请求拼成字节流"，这种方式有三个实打实的好处：一是<strong>不会写错、不会写歪</strong>——序列化/反序列化由生成代码保证，各端字节级一致；二是<strong>高效紧凑</strong>——proto 编码出来的是二进制，比 JSON 这种文本格式更小更快，正适合"一次搜索要传一大批高维向量"的场景；三是<strong>演进友好</strong>——proto 的字段都带编号，新增字段用新编号、老字段不动，于是<strong>新老客户端能兼容共存</strong>（老客户端忽略不认识的新字段即可）。这套"<strong>一份 IDL、多端生成、向后兼容</strong>"的机制，正是 gRPC 生态的基石，也是 Milvus 敢于维护这么多语言 SDK 而不乱套的底气。</p>

<h2>传输与逻辑分离：Server（distributed）vs Proxy（impl）</h2>
<p>请求抵达服务端后，有一个很值得学的<strong>分层</strong>：Milvus 把"<strong>怎么收网络请求</strong>"和"<strong>请求该怎么处理</strong>"<strong>拆成了两层</strong>。第一层是<strong>传输层</strong>，在 <span class="inline">internal/distributed/proxy/service.go</span>：这里有一个 gRPC <span class="mono">Server</span>，它 <span class="mono">RegisterMilvusServiceServer</span> 把自己注册成 <span class="mono">MilvusService</span> 的实现，于是每个 gRPC 方法都落在它身上。但你去看它的 <span class="mono">Search</span> 方法，会发现它<strong>几乎什么都没做</strong>——只有一行：<span class="mono">return s.proxy.Search(ctx, request)</span>。</p>
<p>真正的活在<strong>第二层</strong>：<span class="inline">internal/proxy/impl.go</span> 里的 <span class="mono">Proxy</span> 类型，它的 <span class="mono">Search</span> 才是那段长长的业务逻辑（鉴权、参数校验、入队 dqQueue、扇出到 QueryNode、归并结果——正是第 25 课讲过的）。为什么要这么分？因为"<strong>传输</strong>"和"<strong>逻辑</strong>"是两件会各自变化的事。传输层要操心 gRPC 怎么收、TLS、鉴权拦截、限流、还要兼管 REST/HTTP 入口；逻辑层只关心"一次搜索语义上该怎么完成"。把它们解耦，就能<strong>各自演进、各自测试</strong>：换个网络框架不影响业务逻辑，改业务逻辑也不必碰网络栈。这正是第 36 课"机制与策略分离"那种审美，在 API 层的又一次体现。下面这张分层图把"从你的代码到 Proxy 逻辑"这条路画清楚。</p>

<p>这种分层还有一个很实在的运维含义：<strong>同一套逻辑层 Proxy，可以被多种传输层"复用"</strong>。你已经看到 gRPC 和 REST 两道门都落到同一个 <span class="mono">Proxy</span>；正因为业务逻辑不掺杂任何"我是从 gRPC 来还是从 HTTP 来"的判断，将来想再加一种接入方式（比如某种新协议网关），也只需在传输层再搭一座桥、同样转交给 <span class="mono">Proxy</span> 即可，<strong>逻辑层一行都不用改</strong>。反过来，鉴权、TLS、限流、连接管理这些"<strong>每个请求都要过一遍</strong>"的横切关注点，被集中在传输层统一处理，逻辑层就能保持干净、专注。这种"<strong>把变化的东西关在一层里、把稳定的核心护在另一层</strong>"的切分，是大型服务端工程反复验证过的好习惯——它让系统在面对"新协议、新安全要求、新限流策略"这类外部变化时，<strong>改动面始终收敛在传输层</strong>，而最核心、最不该被频繁触碰的业务逻辑岿然不动。</p>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">客户端</span><span class="name">你的代码 + SDK（pymilvus / go / java …）</span></div><div class="ld">照 milvus-proto 构造 SearchRequest，经 gRPC/REST 发出</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">传输层</span><span class="name">gRPC/REST Server（internal/distributed/proxy）</span></div><div class="ld">收网络请求、鉴权、限流；Server.Search 仅一行转交 s.proxy.Search</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">逻辑层</span><span class="name">Proxy（internal/proxy/impl.go）</span></div><div class="ld">真正的业务：校验、入队(dqQueue)、扇出 QueryNode、归并结果</div></div>
</div>

<h2>一份 proto，多语言 SDK</h2>
<p>有了"以 proto 为契约"这块地基，Milvus 的<strong>多语言 SDK 生态</strong>就水到渠成。官方维护了 <strong>Python（pymilvus）、Go、Java、Node.js</strong> 等多种 SDK，它们底层都做同一件事：<strong>把你调用的方法（如 <span class="mono">client.search(...)</span>）翻译成一个 <span class="mono">SearchRequest</span> proto 消息、经 gRPC 发给 Proxy、再把返回的 <span class="mono">SearchResults</span> 解析成你这门语言里顺手的对象</strong>。因为大家照的是同一份菜单，所以<strong>跨语言行为一致</strong>：同样的参数，在 Python 和 Java 里语义相同、结果相同。</p>
<p>这对你意味着什么？<strong>选 SDK 主要看团队顺手、而非功能差异</strong>——核心能力由 proto 统一保证，不会"Python 能搜、Go 搜不了"。SDK 之上往往还有一层更好用的封装（比如 pymilvus 的 <span class="mono">MilvusClient</span> 把建集合、插入、搜索包成几个简洁方法，再加上连接池、重试、类型转换等便利），但<strong>剥到最里层，都是在收发那几个 proto 消息</strong>。理解了这一点，SDK 对你就不再是黑盒：任何一个 SDK 方法，你都能在脑子里把它还原成"<strong>它在构造哪个 Request、解析哪个 Response</strong>"——这也是排查问题、读 SDK 源码时最有用的一把钥匙。下面把几种入口摆在一起看。</p>

<p>顺带破除一个常见误解：很多人以为"SDK 里那些方便的功能（连接池、自动重试、负载均衡、把结果转成 DataFrame）是 Milvus 服务端给的"，其实不然——这些大多是<strong>SDK 客户端侧自己加的便利层</strong>，服务端只认那几个 proto 消息。这条边界很重要：它意味着<strong>同一个 Milvus 集群，配不同成熟度的 SDK，体验可能不一样</strong>。比如某语言的 SDK 实现了客户端重试、另一种没有，那么面对偶发的网络抖动，前者会自动重发、后者会直接报错给你。也意味着当你怀疑"是 Milvus 的问题还是 SDK 的问题"时，有一个屡试不爽的排查法：<strong>绕过 SDK，直接用 curl 打 REST 接口</strong>复现一次——如果 REST 也错，问题多半在服务端；如果只有某个 SDK 错，那就去看那个 SDK 的封装逻辑。把"服务端只管 proto 语义、SDK 各自加料"这条线划清楚，你定位问题就有了稳稳的支点，而不是在"到底谁的锅"里瞎猜。</p>

<div class="cols">
  <div class="col"><h4>各语言 SDK（gRPC）</h4><p>pymilvus / Go / Java / Node 等，把方法调用译成 proto 消息经 gRPC 收发。<strong>高效、二进制、长连接</strong>，是生产首选。行为由同一份 proto 统一。</p></div>
  <div class="col"><h4>RESTful API（HTTP/JSON）</h4><p>Proxy 内置 gin HTTP 服务（<span class="inline">httpserver/handler_v2.go</span>，路径 <span class="mono">/v2/vectordb</span>）。<strong>无需 SDK、curl 即可</strong>，适合快速试验、跨语言/无 gRPC 环境。落到的还是同一个 Proxy。</p></div>
</div>

<h2>两道门：gRPC 与 REST，通向同一个 Proxy</h2>
<p>最后点清那"两道门"。<strong>gRPC</strong> 是主入口：基于 HTTP/2 的二进制协议，配合 proto 序列化，<strong>高效、强类型、支持流式与长连接</strong>，几乎所有官方 SDK 走的都是它。但并非人人都想引一个 gRPC SDK，于是 Proxy 还在 <span class="inline">internal/distributed/proxy/service.go</span> 里<strong>同时起了一个 HTTP 服务</strong>（<span class="mono">registerHTTPServer</span>，用 gin 框架），把同样的能力包成 <strong>RESTful 风格的 JSON 接口</strong>（处理器在 <span class="inline">httpserver/handler_v2.go</span>，路径前缀 <span class="mono">/v2/vectordb</span>）。这样，一个只会发 HTTP 请求的环境（浏览器脚本、curl、某些没有 Milvus SDK 的语言）也能用上 Milvus。</p>

<p>那么实战里到底该选哪道门？给你一条朴素的判断线。<strong>生产环境、追求吞吐与延迟</strong>，走 gRPC：长连接复用、二进制编码、传大批向量时省下的带宽与解析开销很可观，官方 SDK 也都为它做了连接管理与负载均衡。<strong>快速试验、临时脚本、跨语言集成、或所在环境装 gRPC SDK 不方便</strong>，走 REST：一条 curl 就能建集合、插数据、发搜索，调试时在浏览器或 Postman 里看 JSON 一目了然。很多团队的实际用法是<strong>两者并用</strong>：开发联调期用 REST 快速验证想法，上线后核心链路切回 gRPC 求性能。无论怎么选，记住那句话——<strong>两道门通向同一个后厨</strong>，语义不会因为换了门而改变。你甚至可以用 REST 把一个搜索调通、确认参数无误后，再放心地用 gRPC SDK 把它写进生产代码，因为你清楚两者落到的是同一套 <span class="mono">Proxy</span> 逻辑。这种"<strong>能在两种包装间自由切换、心里却始终清楚底层是同一回事</strong>"的笃定，正是真正理解了 API 层之后的从容。</p>
<p>关键在于：<strong>两道门，同一个后厨</strong>。无论你走 gRPC 还是 REST，请求最终都汇聚到<strong>同一个 Proxy 逻辑层</strong>去处理——REST 处理器本质上也是把 JSON 转成对应的 proto 请求、调用同一套 <span class="mono">Proxy</span> 方法。所以两条路的<strong>语义完全一致</strong>，只是"包装"不同：gRPC 省带宽、低延迟、适合生产；REST 零门槛、易调试、适合上手与集成。理解了"<strong>一份契约 + 一个门面 + 两种包装</strong>"，你就抓住了 Milvus API 层的全貌。下一课，我们转向另一件运维必修课——<strong>可观测性</strong>：当请求在这套系统里跑起来，我们靠日志、指标、链路追踪怎么"看见"它。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>客户端构造请求</h4><p>SDK 把 <span class="mono">client.search(...)</span> 译成 <span class="mono">SearchRequest</span> proto（或 REST 的 JSON）。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>选一道门</h4><p>走 gRPC（二进制/HTTP2）或 REST（gin，<span class="mono">/v2/vectordb</span>）发出。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>传输层接住</h4><p><span class="inline">distributed/proxy</span> 的 Server 鉴权/限流后，一行转交 <span class="mono">s.proxy.Search</span>。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>逻辑层处理</h4><p><span class="inline">proxy/impl.go</span> 的 Proxy 校验、入队、扇出集群，归并结果原路返回。</p></div></div>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>一份契约</strong>：所有 API 由 <span class="mono">milvus-proto</span> 的 <span class="mono">MilvusService</span> 定义（生成 <span class="mono">milvuspb</span>：SearchRequest/SearchResults…）；服务端与各 SDK 都从同一份 proto 生成，行为天然一致。</li>
    <li><strong>传输/逻辑分离</strong>：<span class="inline">internal/distributed/proxy</span> 的 gRPC <span class="mono">Server</span> 只收网络请求并一行转交；真正逻辑在 <span class="inline">internal/proxy/impl.go</span> 的 <span class="mono">Proxy</span>。</li>
    <li><strong>多语言 SDK</strong>：pymilvus/Go/Java/Node 等只是"方法↔proto 消息"的翻译层；选 SDK 看团队顺手，核心能力由 proto 统一。</li>
    <li><strong>两道门</strong>：gRPC（高效二进制，生产首选）与 REST（gin，<span class="mono">/v2/vectordb</span>，零门槛）通向同一个 Proxy，语义一致、仅包装不同。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
The first eight parts drilled from macro architecture down to the C++ core. From here (Part 9) we return to <strong>the layer you can touch directly</strong> — APIs, tools, and operations. First, the thing closest to you: <strong>how does your client code actually talk to Milvus?</strong> The answer centers on a <strong>contract</strong> (milvus-proto) and a <strong>facade</strong> (the Proxy): SDKs in every language speak the same proto, arriving via gRPC (or REST) at the Proxy, which then turns around and directs the whole cluster.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Picture Milvus's API as a <strong>multinational restaurant</strong>. On the wall hangs a <strong>standard menu</strong> (<span class="mono">milvus-proto</span>): what each dish is called, what ingredients it needs, how it's plated — written clearly and <strong>identical worldwide</strong>. Waiters speak <strong>many languages</strong> (the Python, Go, Java, Node SDKs), but they all order from the <strong>same menu</strong>, so whichever language you use to order "kung pao chicken", the same dish arrives.
  Guests enter through <strong>two doors</strong>: the front door is <strong>gRPC</strong> (efficient, binary), the side door is <strong>REST/HTTP</strong> (everyone's JSON); but both lead to the <strong>same kitchen</strong> — the <span class="mono">Proxy</span>. The kitchen is where work is dispatched and dishes coordinated.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>all Milvus APIs are defined by <span class="mono">MilvusService</span> in <span class="mono">milvus-proto</span> (generated into <span class="mono">milvuspb</span>), which every-language SDK speaks; a request arrives via gRPC or REST at the Proxy's "transport layer" (<span class="inline">internal/distributed/proxy</span>) and is handed to the "logic layer" (<span class="inline">internal/proxy/impl.go</span>) for real processing</strong>. One contract unifies all clients; one Proxy facade unifies all entrances.
</div>

<h2>One contract defines all APIs: milvus-proto</h2>
<p>All of Milvus's outward capabilities — create collection, insert, search, query, build index, load… — are not written separately by each SDK, but <strong>defined centrally in one protocol</strong>: <span class="mono">milvus-proto</span> (repo <span class="mono">github.com/milvus-io/milvus-proto</span>). Using <strong>Protocol Buffers</strong>, it describes a gRPC service called <span class="mono">MilvusService</span> and each endpoint's <strong>request/response messages</strong>: <span class="mono">SearchRequest</span> / <span class="mono">SearchResults</span>, <span class="mono">InsertRequest</span>, <span class="mono">CreateCollectionRequest</span>… Compiled, these generate code in each language — the Go package is <span class="mono">milvuspb</span> (under <span class="mono">go-api/v3</span>).</p>
<p>"<strong>The proto as the single source of truth</strong>" is the soul of this design. Because the server and all client SDKs are <strong>generated from or bound to the same proto</strong>, they share a <strong>completely consistent understanding</strong> of "what a search request looks like, what fields come back" — no "Python thinks one thing, Go thinks another". Want a new endpoint or a new request field? Change the proto, regenerate everywhere — <strong>contract first, implementation follows</strong>. This is why Part 8 kept reminding you that "<strong>proto types live in milvus-proto/go-api, not the milvus repo's own pkg/proto</strong>": the API contract is a <strong>separate, shared</strong> repo, of which the main Milvus repo is just one consumer. Pulling the contract out is what lets a multi-language ecosystem orbit one center.</p>

<h2>Transport vs logic: Server (distributed) vs Proxy (impl)</h2>
<p>Once a request reaches the server, there's a <strong>layering</strong> well worth learning: Milvus <strong>splits</strong> "<strong>how to receive a network request</strong>" from "<strong>how the request should be handled</strong>". The first is the <strong>transport layer</strong>, in <span class="inline">internal/distributed/proxy/service.go</span>: a gRPC <span class="mono">Server</span> that <span class="mono">RegisterMilvusServiceServer</span> registers itself as the implementation of <span class="mono">MilvusService</span>, so every gRPC method lands on it. But look at its <span class="mono">Search</span> method and you'll find it does <strong>almost nothing</strong> — one line: <span class="mono">return s.proxy.Search(ctx, request)</span>.</p>
<p>The real work is in the <strong>second layer</strong>: the <span class="mono">Proxy</span> type in <span class="inline">internal/proxy/impl.go</span>, whose <span class="mono">Search</span> holds the long business logic (auth, validation, enqueue to dqQueue, fan out to QueryNodes, merge results — exactly Lesson 25). Why split this way? Because "<strong>transport</strong>" and "<strong>logic</strong>" change for different reasons. The transport layer worries about how gRPC receives, TLS, auth interceptors, rate limiting, and also hosts the REST/HTTP entrance; the logic layer cares only about "how a search should be completed semantically". Decouple them and each can <strong>evolve and be tested separately</strong>: swap the network framework without touching business logic, change business logic without touching the network stack. It's Lesson 36's "mechanism vs policy" aesthetic, again at the API layer. The layered diagram traces "from your code to Proxy logic".</p>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">client</span><span class="name">your code + SDK (pymilvus / go / java …)</span></div><div class="ld">build a SearchRequest per milvus-proto, send via gRPC/REST</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">transport</span><span class="name">gRPC/REST Server (internal/distributed/proxy)</span></div><div class="ld">receive, auth, rate-limit; Server.Search is one line forwarding to s.proxy.Search</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">logic</span><span class="name">Proxy (internal/proxy/impl.go)</span></div><div class="ld">the real business: validate, enqueue (dqQueue), fan out to QueryNodes, merge</div></div>
</div>

<h2>One proto, many SDKs</h2>
<p>With "the proto as contract" as foundation, Milvus's <strong>multi-language SDK ecosystem</strong> follows naturally. The project maintains SDKs for <strong>Python (pymilvus), Go, Java, Node.js</strong> and more, all doing the same thing underneath: <strong>translate your method call (e.g. <span class="mono">client.search(...)</span>) into a <span class="mono">SearchRequest</span> proto message, send it via gRPC to the Proxy, then parse the returned <span class="mono">SearchResults</span> into objects natural to your language</strong>. Because everyone follows the same menu, <strong>behavior is consistent across languages</strong>: the same params mean the same thing and return the same results in Python and Java.</p>
<p>What does that mean for you? <strong>Pick an SDK by what your team prefers, not by feature differences</strong> — core capabilities are guaranteed uniform by the proto; there's no "Python can search but Go can't". SDKs often add a more ergonomic wrapper on top (pymilvus's <span class="mono">MilvusClient</span> packs create/insert/search into a few clean methods, plus connection pooling, retries, type conversion), but <strong>peel to the core and it's all sending/receiving those proto messages</strong>. Grasp this and the SDK stops being a black box: any SDK method, you can mentally reduce to "<strong>which Request it builds, which Response it parses</strong>" — the most useful key when debugging or reading SDK source. The entrances side by side:</p>

<div class="cols">
  <div class="col"><h4>Language SDKs (gRPC)</h4><p>pymilvus / Go / Java / Node, translating method calls into proto messages over gRPC. <strong>Efficient, binary, long-lived connections</strong> — the production choice. Behavior unified by one proto.</p></div>
  <div class="col"><h4>RESTful API (HTTP/JSON)</h4><p>The Proxy embeds a gin HTTP server (<span class="inline">httpserver/handler_v2.go</span>, path <span class="mono">/v2/vectordb</span>). <strong>No SDK needed — curl works</strong>, great for quick trials and gRPC-less environments. It still lands on the same Proxy.</p></div>
</div>

<h2>Two doors: gRPC and REST, into the same Proxy</h2>
<p>Finally, the "two doors". <strong>gRPC</strong> is the main entrance: an HTTP/2 binary protocol with proto serialization — <strong>efficient, strongly typed, supporting streaming and long connections</strong> — used by nearly all official SDKs. But not everyone wants to pull in a gRPC SDK, so the Proxy <strong>also starts an HTTP server</strong> in <span class="inline">internal/distributed/proxy/service.go</span> (<span class="mono">registerHTTPServer</span>, using gin), wrapping the same capabilities as a <strong>RESTful JSON API</strong> (handlers in <span class="inline">httpserver/handler_v2.go</span>, path prefix <span class="mono">/v2/vectordb</span>). So an HTTP-only environment (browser scripts, curl, languages without a Milvus SDK) can use Milvus too.</p>
<p>The key: <strong>two doors, one kitchen</strong>. Whether you take gRPC or REST, the request ultimately converges on the <strong>same Proxy logic layer</strong> — the REST handler essentially turns JSON into the corresponding proto request and calls the same <span class="mono">Proxy</span> methods. So the two paths are <strong>semantically identical</strong>, differing only in "wrapping": gRPC saves bandwidth, low latency, for production; REST is zero-friction, easy to debug, for getting started and integration. Grasp "<strong>one contract + one facade + two wrappings</strong>" and you've got the whole picture of Milvus's API layer. Next lesson turns to another ops essential — <strong>observability</strong>: once requests run through this system, how do we "see" them via logs, metrics, and tracing.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Client builds the request</h4><p>the SDK translates <span class="mono">client.search(...)</span> into a <span class="mono">SearchRequest</span> proto (or REST JSON).</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Pick a door</h4><p>send via gRPC (binary/HTTP2) or REST (gin, <span class="mono">/v2/vectordb</span>).</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Transport catches it</h4><p>the <span class="inline">distributed/proxy</span> Server auths/rate-limits, then forwards in one line to <span class="mono">s.proxy.Search</span>.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Logic handles it</h4><p>the <span class="inline">proxy/impl.go</span> Proxy validates, enqueues, fans out to the cluster, and merges results back.</p></div></div>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>One contract</strong>: all APIs are defined by <span class="mono">MilvusService</span> in <span class="mono">milvus-proto</span> (generates <span class="mono">milvuspb</span>: SearchRequest/SearchResults…); server and SDKs all generate from the same proto, so behavior is inherently consistent.</li>
    <li><strong>Transport/logic split</strong>: the gRPC <span class="mono">Server</span> in <span class="inline">internal/distributed/proxy</span> only receives and forwards in one line; the real logic is the <span class="mono">Proxy</span> in <span class="inline">internal/proxy/impl.go</span>.</li>
    <li><strong>Many SDKs</strong>: pymilvus/Go/Java/Node are just "method↔proto message" translators; choose by team preference — core capability is unified by the proto.</li>
    <li><strong>Two doors</strong>: gRPC (efficient binary, production choice) and REST (gin, <span class="mono">/v2/vectordb</span>, zero-friction) lead to the same Proxy — identical semantics, only different wrapping.</li>
  </ul>
</div>
""",
}

LESSON_39 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
上一课，一个请求经 API 进了门。可它在 Milvus 这套<strong>分布式系统</strong>里跑起来后——穿过 Proxy、扇到几个 QueryNode、又牵动 DataCoord——我们怎么<strong>"看见"它</strong>？一旦出问题，去哪儿找线索？这就是<strong>可观测性</strong>要解决的事。它有三根支柱：<strong>日志</strong>（发生了什么）、<strong>指标</strong>（整体好不好）、<strong>链路追踪</strong>（一个请求走过了哪些节点）。这一课看 Milvus 怎么把三者落地，尤其是它们如何<strong>携手追踪一个跨越多节点的请求</strong>。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  把运维一套分布式系统，想成<strong>医院监护一位病人</strong>。<strong>日志</strong>像<strong>详细的病程记录</strong>：几点几分发生了什么、用了什么药、医生写了哪句话——<strong>逐条、带时间、可回溯</strong>。<strong>指标</strong>像<strong>床头的生命体征监视器</strong>：心率、血压、血氧，是<strong>随时间变化的一串数字</strong>，一眼看出"整体状况好不好、有没有异常波动"。
  <strong>链路追踪</strong>则像<strong>跟着这一位病人走完全程</strong>：挂号→门诊→化验→取药，每一站花了多久、在哪卡住了。在"<strong>多个科室协作</strong>"（多节点）的医院里，光看某科的记录不够——你得把<strong>同一个病人</strong>在各科的足迹<strong>串成一条线</strong>，才知道慢在哪、错在哪。三者缺一不可。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong>Milvus 的可观测性由三根支柱组成——日志用 <span class="mono">pkg/mlog</span>（强制带 ctx、结构化字段、可经 gRPC 跨节点传播）；指标用 Prometheus 风格的 <span class="mono">pkg/metrics</span>（各组件分别埋点）；链路追踪用 OpenTelemetry（<span class="mono">pkg/tracer</span> + otelgrpc 拦截器，span 随 RPC 跨节点流动）</strong>。三者共同回答"<strong>一个请求在分布式系统里到底经历了什么</strong>"。
</div>

<h2>可观测性的三大支柱</h2>
<p>"可观测性"听起来抽象，拆开就是三件具体的事，各答一个不同的问题。<strong>日志（Logs）</strong>答"<strong>到底发生了什么</strong>"：一条条带时间戳的事件记录，是出问题后<strong>翻案底</strong>的第一手资料。<strong>指标（Metrics）</strong>答"<strong>整体状况如何</strong>"：把大量事件<strong>聚合成数字</strong>——每秒请求数、平均延迟、内存占用、队列长度——随时间画成曲线，最适合<strong>看趋势、设告警</strong>。<strong>链路追踪（Traces）</strong>答"<strong>一个请求走过了哪些环节、各花多久</strong>"：把<strong>同一个请求</strong>在各节点、各阶段的足迹串成一条带层级的时间线。</p>
<p>为什么三者缺一不可？因为它们各有盲区。光有指标，你能看到"延迟突然涨了"，却不知道是<strong>哪个请求、卡在哪一步</strong>；光有日志，海量分散在各节点的日志里，你很难把"<strong>属于同一个请求</strong>"的那些条目<strong>挑出来连成线</strong>；光有链路追踪，你知道"卡在 QueryNode 那一段"，却可能需要那一刻的<strong>详细日志</strong>才能看清根因。所以成熟系统都是<strong>三管齐下</strong>：指标用来<strong>发现</strong>异常（告警），链路追踪用来<strong>定位</strong>是哪个请求、哪个环节，日志用来<strong>还原</strong>那个环节的细节。下面这张表把三者并排，帮你记住"<strong>各答什么问、用什么实现</strong>"。</p>

<p>这里特别值得点破"<strong>聚合</strong>"这件事，它是日志与指标最本质的分野。日志是<strong>不聚合</strong>的：每发生一件事，就老老实实记一条，于是它<strong>细节满满</strong>，但量也<strong>大得吓人</strong>——一个繁忙集群一天能产出几亿条日志，你不可能靠"一条条读"来掌握全局。指标恰恰相反，它从一开始就<strong>把同类事件合并成数字</strong>：不是记录"第 10001 次请求耗时 8 毫秒"，而是维护"<strong>过去一分钟平均耗时</strong>""<strong>请求总数</strong>"这样的<strong>累计量或分布</strong>。这一聚合，让指标<strong>极其轻量</strong>（存的是数字曲线，不是海量文本），适合<strong>长期保留、快速画图、实时告警</strong>；代价是<strong>丢掉了个体细节</strong>——它能告诉你"延迟涨了"，却没法告诉你"是哪一条请求"。所以日志与指标天生互补：<strong>一个细而重、一个粗而轻</strong>，一个用来事后查案、一个用来实时盯盘。理解了这层"聚合与否"的取舍，你就明白为什么不能只留其一——只靠日志会被海量淹没、且没法实时告警；只靠指标又会在出事时"<strong>看得见烟、找不到火</strong>"。</p>

<table class="t">
  <tr><th>支柱</th><th>回答的问题</th><th>形态</th><th>Milvus 实现</th></tr>
  <tr><td><strong>日志 Logs</strong></td><td>到底发生了什么（逐条事件）</td><td>带时间戳的文本/结构化记录</td><td class="mono">pkg/mlog（zap）</td></tr>
  <tr><td><strong>指标 Metrics</strong></td><td>整体状况如何（趋势/告警）</td><td>随时间变化的数字曲线</td><td class="mono">pkg/metrics（Prometheus）</td></tr>
  <tr><td><strong>链路追踪 Traces</strong></td><td>一个请求走过哪些环节、各花多久</td><td>带层级的跨节点时间线</td><td class="mono">pkg/tracer（OpenTelemetry）</td></tr>
</table>

<h2>日志：mlog——强制带 ctx、结构化、可跨节点传播</h2>
<p>先看三根支柱里你最常打交道的——日志。Milvus 有一条<strong>铁律</strong>：日志只能用 <span class="mono">pkg/mlog</span>，不准用标准库 <span class="mono">log</span>、不准直接 <span class="mono">fmt.Println</span>、也不准裸用 zap。为什么管得这么严？因为 <span class="mono">mlog</span> 替你扛起了分布式日志最难的几件事，而它的设计处处是讲究。</p>
<p>第一个讲究：<strong>每条日志都必须带 ctx</strong>。你写的是 <span class="mono">mlog.Info(ctx, "消息", mlog.String("字段", 值))</span>——第一个参数永远是上下文。为什么强制？因为 ctx 里可以<strong>挂上一路累积的"身份信息"</strong>。第二个讲究：<strong>结构化字段</strong>。不是把变量拼进一句话（<span class="mono">"user " + id + " failed"</span>），而是用 <span class="mono">mlog.String</span>、<span class="mono">mlog.Int64</span> 这样的<strong>带类型的键值对</strong>。结构化日志的好处是<strong>机器可查</strong>：日志收集系统能按"字段 = 值"精确过滤，而不是在文本里瞎搜。第三个、也是最妙的讲究：<strong>字段能跨节点传播</strong>。用 <span class="mono">mlog.WithFields(ctx, ...)</span> 把字段挂到 ctx 上，子上下文会自动继承；更进一步，给字段加上 <span class="mono">mlog.OptPropagated()</span>（比如集合名、集合 ID），再配合 gRPC 拦截器（<span class="mono">mlog.UnaryServerInterceptor</span> / <span class="mono">UnaryClientInterceptor</span>），这些字段就能<strong>随着 RPC 调用一起"飞"到下游节点</strong>。于是 Proxy 上给一个请求打的标记，会原样出现在它触发的 QueryNode、DataNode 日志里——你<strong>用一个 ID 就能把散落在全集群的相关日志一网打尽</strong>。这正是分布式排错时最珍贵的能力。下面对比一下"拼字符串"与"结构化 + 可传播"的差别。</p>

<p>多说一句这条"<strong>每条日志必带 ctx</strong>"的铁律为什么值得严格执行。在单机程序里，日志带不带上下文，差别也许不大——反正都在一个进程里，前后翻翻就能对上。但 Milvus 是<strong>分布式</strong>的：一个请求的"故事"被<strong>拆散在好几个进程、好几台机器</strong>上书写。如果每个节点都只顾埋头记自己那一段、彼此没有共同的"线索 ID"，那这些日志就像<strong>一地散落、没有页码的稿纸</strong>——信息都在，却永远拼不回一个完整故事。ctx 的作用，就是给每一页稿纸<strong>盖上同一个编号</strong>。正因为这个编号能随 ctx 一路传递、还能经拦截器跨节点传播，事后你才能拿着它，把十几台机器上属于同一个请求的日志<strong>一键归拢</strong>。所以这条铁律绝不是"代码规范洁癖"，而是<strong>分布式系统能否被排查</strong>的生死线——少传一个 ctx，可能就意味着某段关键日志从此"<strong>失联</strong>"、再也归不进它该属于的那个故事。把这一点刻进肌肉记忆，是每个 Milvus 贡献者的必修课。</p>

<div class="cols">
  <div class="col"><h4>❌ 拼字符串的日志</h4><p><span class="mono">log.Printf("user %d search failed", id)</span>。信息埋在文本里，跨节点各打各的、对不上号；想按 user 过滤只能正则瞎搜；换节点就断了线索。</p></div>
  <div class="col"><h4>✅ mlog：结构化 + 可传播</h4><p><span class="mono">mlog.Info(ctx, "search failed", mlog.Int64("user", id))</span>。字段带类型、可精确过滤；经 ctx + <span class="mono">OptPropagated</span> + 拦截器，标记<strong>跟着请求跨节点流动</strong>，全集群一个 ID 串起来。</p></div>
</div>

<h2>指标与链路追踪：Prometheus + OpenTelemetry</h2>
<p>再看另外两根支柱，它们都建立在业界<strong>开放标准</strong>之上，所以能直接接入成熟的生态工具。<strong>指标</strong>用的是 <strong>Prometheus 风格</strong>：在 <span class="inline">pkg/metrics</span> 下，每个组件都有自己的埋点文件（<span class="mono">datacoord_metrics.go</span>、<span class="mono">datanode_metrics.go</span>、querynode、proxy，甚至还有 <span class="mono">cgo_metrics.go</span> 盯着 Go↔C++ 那道桥）。这些指标暴露成一个 HTTP 端点，由 Prometheus 定期<strong>抓取</strong>、存成时间序列，再用 <strong>Grafana</strong> 画成仪表盘——延迟、QPS、各队列水位、内存占用一目了然，还能设阈值<strong>自动告警</strong>。</p>
<p><strong>链路追踪</strong>用的是 <strong>OpenTelemetry</strong>（当前最通行的追踪标准）：核心在 <span class="inline">pkg/tracer</span>，依赖 <span class="mono">go.opentelemetry.io/otel</span>。它的关键同样是"<strong>跨节点把线索串起来</strong>"——靠的是 <strong>otelgrpc 拦截器</strong>（<span class="mono">GetInterceptorOpts</span>）：当一次请求从 Proxy 经 gRPC 调到 QueryNode 时，拦截器会把"<strong>追踪上下文</strong>"（trace context，含本次追踪的唯一 ID 与当前 span）<strong>塞进 RPC 元数据带过去</strong>；下游节点收到后，把自己这段处理作为一个<strong>子 span</strong> 挂到同一条 trace 上。所有节点的 span 汇集到 Jaeger 这类后端，就拼成一棵<strong>完整的调用树</strong>：哪一段最耗时、在哪一跳出的错，画成一条时间线，<strong>一眼看穿</strong>。你会发现日志（OptPropagated 字段）和追踪（otel trace context）<strong>用的是同一招</strong>——<strong>把"身份"塞进 ctx、再随 RPC 传播</strong>。这不是巧合，而是分布式可观测性的<strong>核心心法</strong>。</p>

<p>顺带说说为什么 Milvus 要<strong>站在 Prometheus、OpenTelemetry 这些开放标准上</strong>，而不是自造一套。可观测性的价值，很大程度上取决于<strong>能不能接进顺手的工具去看</strong>——光把指标、span 采集出来还不够，还得有人画图、有人告警、有人按 trace ID 检索。Prometheus（指标存储与告警）、Grafana（仪表盘）、Jaeger（追踪可视化）这些工具，早已是云原生世界的<strong>事实标准</strong>，运维同学大多<strong>本来就会用</strong>。Milvus 只要让自己的指标、追踪<strong>说这些工具听得懂的"普通话"</strong>，用户就能把它<strong>无缝接进既有的监控体系</strong>，而不必为了一个数据库专门学一套私有面板。这是一种很务实的<strong>生态思维</strong>：在"<strong>采集</strong>"这件 Milvus 该做的事上认真做（埋点、传播、暴露端点），在"<strong>展示与告警</strong>"这件成熟生态已做得很好的事上<strong>不重复造轮子</strong>，而是开放对接。这和第 37 课"GPU 算法交给 Knowhere/RAFT、自己专注集成"、第 8 课"依赖 etcd/对象存储等成熟组件"是同一种克制——<strong>把专业的事交给专业的工具，自己只做好那道连接的胶水</strong>。</p>

<h2>三者合一：在分布式系统里追一个请求</h2>
<p>把三根支柱接起来，看一次"搜索变慢了"的排查实战。<strong>第一步，指标发现异常</strong>：Grafana 上 P99 延迟曲线突然抬头、告警触发——你知道"<strong>出事了</strong>"，但还不知道是谁、卡在哪。<strong>第二步，链路追踪定位环节</strong>：翻看慢请求的 trace，那棵调用树清清楚楚——Proxy 很快、扇出的三个 QueryNode 里有<strong>一个</strong>的子 span 特别长，问题缩小到了"<strong>那一跳</strong>"。<strong>第三步，日志还原细节</strong>：拿着这个请求的传播 ID，去那个 QueryNode 的日志里一过滤，相关条目<strong>整整齐齐</strong>地浮出来——原来是某个段在做 mmap 缺页、冷数据首次加载慢（第 35 课）。三步走完，根因水落石出。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>指标发现</h4><p>Grafana 上 P99 延迟曲线抬头、告警触发——知道"出事了"，但不知是谁、卡在哪。（Prometheus 指标）</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>追踪定位</h4><p>看慢请求的 trace 调用树：某个 QueryNode 的子 span 特别长，问题缩小到"那一跳"。（OpenTelemetry）</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>日志还原</h4><p>用该请求的传播 ID 过滤那个节点的日志，细节浮现：原来是 mmap 缺页、冷段首次加载慢。（mlog）</p></div></div>
</div>
<p>这套配合的<strong>灵魂</strong>，就是那条反复出现的主线：<strong>给请求一个能跨节点传播的"身份"</strong>。无论是 mlog 的可传播字段，还是 otel 的 trace context，本质都是<strong>把一个标识塞进 ctx、再让 gRPC 拦截器带着它走遍全程</strong>。正因如此，散落在十几个节点、成千上万条日志/指标/span 里的碎片，才能围绕"<strong>同一个请求</strong>"重新聚拢成一个完整故事。回想第 38 课"每条日志必须带 ctx"那条铁律，你现在该明白它的深意了——<strong>ctx 不只是个参数，它是串起整个分布式可观测性的那根线</strong>。下一课我们转向另一件运维基本功：这套系统成百上千的<strong>配置项</strong>是怎么管理的（paramtable 与 milvus.yaml）。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>三大支柱</strong>：日志(发生了什么)、指标(整体趋势/告警)、链路追踪(一个请求走过哪些环节)，各有盲区、三管齐下：指标<strong>发现</strong>、追踪<strong>定位</strong>、日志<strong>还原</strong>。</li>
    <li><strong>日志=mlog</strong>：强制带 ctx、结构化字段(mlog.String/Int64)、可经 <span class="mono">WithFields</span>+<span class="mono">OptPropagated</span>+gRPC 拦截器<strong>跨节点传播</strong>，一个 ID 串起全集群日志。</li>
    <li><strong>指标=Prometheus</strong>(<span class="inline">pkg/metrics</span> 各组件埋点→抓取→Grafana)；<strong>追踪=OpenTelemetry</strong>(<span class="inline">pkg/tracer</span> + otelgrpc，trace context 随 RPC 传播、子 span 拼成调用树)。</li>
    <li><strong>核心心法</strong>：把请求的"身份"塞进 ctx、再随 gRPC 传播——日志与追踪用的是同一招，这正是"每条日志必带 ctx"铁律的深意。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Last lesson, a request came in through the API. But once it runs through Milvus's <strong>distributed system</strong> — across the Proxy, fanned to several QueryNodes, stirring DataCoord — how do we <strong>"see" it</strong>? When something breaks, where do we look? That's what <strong>observability</strong> solves. It has three pillars: <strong>logs</strong> (what happened), <strong>metrics</strong> (how's the whole doing), and <strong>traces</strong> (which nodes one request crossed). This lesson shows how Milvus implements all three — especially how they <strong>jointly trace a request spanning many nodes</strong>.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of operating a distributed system as a <strong>hospital monitoring a patient</strong>. <strong>Logs</strong> are the <strong>detailed chart notes</strong>: at what time what happened, which medicine, what the doctor wrote — <strong>line by line, timestamped, traceable</strong>. <strong>Metrics</strong> are the <strong>bedside vital-signs monitor</strong>: heart rate, blood pressure, oxygen — <strong>numbers over time</strong>, telling at a glance "is the overall condition fine, any abnormal swings".
  <strong>Traces</strong> are <strong>following this one patient end to end</strong>: registration → exam → lab → pharmacy, how long each took, where it stalled. In a hospital of "<strong>many cooperating departments</strong>" (many nodes), one department's notes aren't enough — you must <strong>stitch the same patient's footprints across departments into one line</strong> to see where it's slow or wrong. All three are indispensable.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>Milvus's observability has three pillars — logs via <span class="mono">pkg/mlog</span> (ctx mandatory, structured fields, propagatable across nodes over gRPC); metrics via Prometheus-style <span class="mono">pkg/metrics</span> (each component instrumented); traces via OpenTelemetry (<span class="mono">pkg/tracer</span> + otelgrpc interceptors, spans flowing across RPCs)</strong>. Together they answer "<strong>what a request actually experienced across the distributed system</strong>".
</div>

<h2>The three pillars of observability</h2>
<p>"Observability" sounds abstract; unpacked it's three concrete things, each answering a different question. <strong>Logs</strong> answer "<strong>what exactly happened</strong>": timestamped event records, the first-hand evidence for <strong>going through the case file</strong> after a problem. <strong>Metrics</strong> answer "<strong>how's the whole doing</strong>": masses of events <strong>aggregated into numbers</strong> — requests per second, average latency, memory, queue length — plotted over time, ideal for <strong>watching trends and setting alerts</strong>. <strong>Traces</strong> answer "<strong>which stages one request crossed, and how long each took</strong>": the footprints of <strong>one request</strong> across nodes and phases, stitched into a hierarchical timeline.</p>
<p>Why is each indispensable? Each has blind spots. With only metrics, you see "latency spiked" but not <strong>which request, stuck where</strong>; with only logs, amid masses scattered across nodes, it's hard to <strong>pick out and connect</strong> the entries "<strong>belonging to the same request</strong>"; with only traces, you know "it stalled in the QueryNode segment" but may need that moment's <strong>detailed logs</strong> for the root cause. So mature systems go <strong>three-pronged</strong>: metrics to <strong>detect</strong> anomalies (alert), traces to <strong>locate</strong> which request and stage, logs to <strong>reconstruct</strong> that stage's detail. The table puts the three side by side, to remember "<strong>what each answers, implemented by what</strong>".</p>

<table class="t">
  <tr><th>Pillar</th><th>Question answered</th><th>Form</th><th>Milvus impl</th></tr>
  <tr><td><strong>Logs</strong></td><td>what exactly happened (event by event)</td><td>timestamped text/structured records</td><td class="mono">pkg/mlog (zap)</td></tr>
  <tr><td><strong>Metrics</strong></td><td>how's the whole doing (trends/alerts)</td><td>numeric curves over time</td><td class="mono">pkg/metrics (Prometheus)</td></tr>
  <tr><td><strong>Traces</strong></td><td>which stages a request crossed, how long each</td><td>hierarchical cross-node timeline</td><td class="mono">pkg/tracer (OpenTelemetry)</td></tr>
</table>

<h2>Logs: mlog — ctx mandatory, structured, propagatable across nodes</h2>
<p>First the pillar you deal with most — logs. Milvus has an <strong>iron rule</strong>: logging may only use <span class="mono">pkg/mlog</span> — not the standard <span class="mono">log</span>, not bare <span class="mono">fmt.Println</span>, not raw zap. Why so strict? Because <span class="mono">mlog</span> shoulders the hardest parts of distributed logging for you, and its design is thoughtful throughout.</p>
<p>First touch: <strong>every log must carry ctx</strong>. You write <span class="mono">mlog.Info(ctx, "message", mlog.String("field", value))</span> — the first argument is always the context. Why mandatory? Because ctx can <strong>carry "identity" accumulated along the way</strong>. Second touch: <strong>structured fields</strong>. Not splicing variables into a sentence (<span class="mono">"user " + id + " failed"</span>) but typed key-value pairs like <span class="mono">mlog.String</span>, <span class="mono">mlog.Int64</span>. Structured logs are <strong>machine-queryable</strong>: a log system can filter precisely by "field = value" instead of grepping text. Third and most elegant: <strong>fields can propagate across nodes</strong>. Attach fields to ctx with <span class="mono">mlog.WithFields(ctx, ...)</span> and child contexts inherit them; further, mark a field with <span class="mono">mlog.OptPropagated()</span> (e.g. collection name, collection ID) and, via gRPC interceptors (<span class="mono">mlog.UnaryServerInterceptor</span> / <span class="mono">UnaryClientInterceptor</span>), those fields <strong>"fly" with the RPC to downstream nodes</strong>. So a marker stamped on a request at the Proxy reappears verbatim in the QueryNode and DataNode logs it triggers — <strong>one ID nets every related log across the whole cluster</strong>. That's the most precious ability when debugging distributed systems. The two styles compared:</p>

<div class="cols">
  <div class="col"><h4>❌ String-spliced logs</h4><p><span class="mono">log.Printf("user %d search failed", id)</span>. Info buried in text; each node logs its own, unmatchable; filtering by user means regex guessing; cross a node and the trail breaks.</p></div>
  <div class="col"><h4>✅ mlog: structured + propagatable</h4><p><span class="mono">mlog.Info(ctx, "search failed", mlog.Int64("user", id))</span>. Typed fields, precisely filterable; via ctx + <span class="mono">OptPropagated</span> + interceptors, the marker <strong>flows with the request across nodes</strong>, one ID stitching the whole cluster.</p></div>
</div>

<h2>Metrics & traces: Prometheus + OpenTelemetry</h2>
<p>The other two pillars both build on industry <strong>open standards</strong>, so they plug straight into mature ecosystem tools. <strong>Metrics</strong> are <strong>Prometheus-style</strong>: under <span class="inline">pkg/metrics</span>, each component has its own instrumentation file (<span class="mono">datacoord_metrics.go</span>, <span class="mono">datanode_metrics.go</span>, querynode, proxy, even <span class="mono">cgo_metrics.go</span> watching the Go↔C++ bridge). These are exposed at an HTTP endpoint, periodically <strong>scraped</strong> by Prometheus into time series, then drawn into dashboards by <strong>Grafana</strong> — latency, QPS, queue levels, memory at a glance, with thresholds for <strong>automatic alerts</strong>.</p>
<p><strong>Traces</strong> use <strong>OpenTelemetry</strong> (today's prevailing tracing standard): the core is in <span class="inline">pkg/tracer</span>, depending on <span class="mono">go.opentelemetry.io/otel</span>. Its key is again "<strong>stitching the trail across nodes</strong>" — via <strong>otelgrpc interceptors</strong> (<span class="mono">GetInterceptorOpts</span>): when a request goes from Proxy over gRPC to a QueryNode, the interceptor <strong>tucks the "trace context"</strong> (containing this trace's unique ID and current span) <strong>into the RPC metadata</strong>; the downstream node, on receipt, attaches its own processing as a <strong>child span</strong> on the same trace. All nodes' spans, gathered into a backend like Jaeger, assemble a <strong>complete call tree</strong>: which segment is slowest, which hop errored, drawn as a timeline you <strong>see through at a glance</strong>. Notice logs (OptPropagated fields) and traces (otel trace context) <strong>use the same move</strong> — <strong>tuck "identity" into ctx, then propagate with the RPC</strong>. No coincidence — it's the <strong>core method</strong> of distributed observability.</p>

<h2>Three as one: tracing a request across the distributed system</h2>
<p>Wire the three pillars together for a real "search got slow" investigation. <strong>Step 1, metrics detect the anomaly</strong>: on Grafana the P99 latency curve suddenly rises, an alert fires — you know "<strong>something's wrong</strong>", but not who or where. <strong>Step 2, traces locate the stage</strong>: open a slow request's trace and the call tree is clear — the Proxy was fast, but among the three fanned-out QueryNodes, <strong>one</strong> child span is unusually long; the problem narrows to "<strong>that hop</strong>". <strong>Step 3, logs reconstruct the detail</strong>: take this request's propagated ID, filter the logs of that QueryNode, and the related entries surface <strong>neatly</strong> — turns out a segment was faulting in via mmap, cold data slow on first load (Lesson 35). Three steps, root cause in hand.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Metrics detect</h4><p>Grafana's P99 latency rises, an alert fires — you know "something's wrong" but not who or where. (Prometheus metrics)</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Traces locate</h4><p>open the slow request's trace tree: one QueryNode's child span is unusually long; the problem narrows to "that hop". (OpenTelemetry)</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Logs reconstruct</h4><p>filter that node's logs by the request's propagated ID; the detail surfaces: an mmap fault, a cold segment slow on first load. (mlog)</p></div></div>
</div>
<p>The <strong>soul</strong> of this teamwork is that recurring throughline: <strong>give the request an "identity" that propagates across nodes</strong>. Whether mlog's propagatable fields or otel's trace context, the essence is <strong>tucking an identifier into ctx and letting gRPC interceptors carry it the whole way</strong>. That's why fragments scattered across a dozen nodes and thousands of logs/metrics/spans can re-gather, around "<strong>the same request</strong>", into one complete story. Recall Lesson 38's iron rule "every log must carry ctx" — now you see its depth: <strong>ctx isn't just a parameter, it's the thread stitching the whole distributed observability together</strong>. Next lesson turns to another ops fundamental: how this system's hundreds of <strong>configuration items</strong> are managed (paramtable and milvus.yaml).</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Three pillars</strong>: logs (what happened), metrics (overall trend/alert), traces (which stages a request crossed) — each has blind spots, so three-pronged: metrics <strong>detect</strong>, traces <strong>locate</strong>, logs <strong>reconstruct</strong>.</li>
    <li><strong>Logs = mlog</strong>: ctx mandatory, structured fields (mlog.String/Int64), propagatable across nodes via <span class="mono">WithFields</span>+<span class="mono">OptPropagated</span>+gRPC interceptors — one ID stitches cluster-wide logs.</li>
    <li><strong>Metrics = Prometheus</strong> (<span class="inline">pkg/metrics</span> per-component → scrape → Grafana); <strong>traces = OpenTelemetry</strong> (<span class="inline">pkg/tracer</span> + otelgrpc, trace context propagated over RPC, child spans forming a call tree).</li>
    <li><strong>Core method</strong>: tuck the request's "identity" into ctx and propagate with gRPC — logs and traces use the same move, which is the deeper point of the "every log carries ctx" rule.</li>
  </ul>
</div>
""",
}
