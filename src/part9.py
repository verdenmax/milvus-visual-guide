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
