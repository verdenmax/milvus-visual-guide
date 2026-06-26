"""Content for Part 9 (API, tools &amp; operations). Lessons 38-41.

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
<p>"<strong>以 proto 为唯一事实来源</strong>"是这套设计的灵魂。因为服务端和所有客户端 SDK 都<strong>从同一份 proto 生成或绑定</strong>，所以它们对"一次搜索请求长什么样、返回什么字段"有<strong>完全一致的理解</strong>，不会出现"Python 以为是这样、Go 以为是那样"的鸡同鸭讲。想加一个新接口或给请求加一个字段？先改 proto，再各端重新生成——<strong>契约先行，实现跟上</strong>。这也是为什么第 2、3 部分反复提醒你"<strong>proto 类型住在 milvus-proto/go-api，而不是 milvus 仓库自己的 pkg/proto</strong>"：对外 API 的契约是一个<strong>独立、共享</strong>的仓库，Milvus 主仓只是它的一个使用者。把契约独立出来，多语言生态才能围着同一个中心转。</p>

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

<p>An analogy first, for why a "contract" matters so much. Imagine there were no shared protocol: the Python SDK's author decides "the topK field is called <span class="mono">limit</span> and goes in slot 3", the Go SDK's author decides "it's <span class="mono">top_k</span> in slot 5", and the server is left guessing each one… The moment any single understanding diverges, you get baffling "<strong>sent from here, read wrong over there</strong>" bugs that are miserable to track down. A proto contract turns that kind of verbal agreement into a <strong>black-and-white, machine-verifiable</strong> spec: what each field is called, its type, its number, whether it's required — all nailed down in one file. The server and every SDK treat it as the authority and generate their code from it, so "inconsistent understanding" becomes <strong>impossible at the root</strong>. That's why in any system built on <strong>multi-party, cross-language collaboration</strong>, defining the contract first is job number one — the contract is the anchor of trust. Milvus keeps that anchor in a <strong>separate repo</strong>, versioned on its own, precisely because its stability and authority matter more than any single implementation.</p>
<p>"<strong>The proto as the single source of truth</strong>" is the soul of this design. Because the server and all client SDKs are <strong>generated from or bound to the same proto</strong>, they share a <strong>completely consistent understanding</strong> of "what a search request looks like, what fields come back" — no "Python thinks one thing, Go thinks another". Want a new endpoint or a new request field? Change the proto, regenerate everywhere — <strong>contract first, implementation follows</strong>. This is why Parts 2–3 kept reminding you that "<strong>proto types live in milvus-proto/go-api, not the milvus repo's own pkg/proto</strong>": the API contract is a <strong>separate, shared</strong> repo, of which the main Milvus repo is just one consumer. Pulling the contract out is what lets a multi-language ecosystem orbit one center.</p>

<p>A word more on why <strong>Protocol Buffers</strong> fit this job so well. It's a <strong>language-agnostic interface description language (IDL)</strong>: you write a single <span class="mono">.proto</span> file describing "what the messages look like and what methods the service has", then a code generator produces <strong>strongly-typed code</strong> for Python, Go, Java and the rest in one step. Compared with having each language hand-roll "how to pack a request into bytes", this buys three concrete wins: one, <strong>no mistakes or drift</strong> — serialization and deserialization are guaranteed by generated code, byte-for-byte identical on every end; two, <strong>compact and fast</strong> — proto encodes to binary, smaller and quicker than a text format like JSON, exactly right for "one search shipping a big batch of high-dimensional vectors"; three, <strong>evolution-friendly</strong> — every proto field carries a number, so a new field takes a new number while old fields stay put, letting <strong>old and new clients coexist</strong> (an older client simply ignores fields it doesn't recognize). This "<strong>one IDL, generated everywhere, backward-compatible</strong>" mechanism is the bedrock of the gRPC ecosystem, and the reason Milvus can maintain this many language SDKs without descending into chaos.</p>

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

<p>It's worth dispelling a common misconception here: many people assume the convenient features inside an SDK — connection pooling, automatic retries, load balancing, turning results into a DataFrame — <strong>come from the Milvus server</strong>. They don't. Most of these are a <strong>client-side convenience layer the SDK adds itself</strong>; the server only ever sees those few proto messages. That boundary matters: the <strong>same Milvus cluster, paired with SDKs of differing maturity, can feel different</strong>. If one language's SDK implements client-side retry and another doesn't, then on a bit of transient network jitter the former quietly resends while the latter throws an error in your face. It also gives you a reliable trick when you suspect "is this Milvus's problem or the SDK's?": <strong>bypass the SDK and hit the REST endpoint directly with curl</strong> (or talk raw gRPC with grpcurl) to reproduce it — if REST fails too, the problem is most likely server-side; if only one SDK fails, go read that SDK's wrapper logic. Drawing the line clearly — <strong>the server owns proto semantics, each SDK adds its own seasoning</strong> — gives you a solid fulcrum for locating bugs instead of guessing whose fault it is.</p>

<div class="cols">
  <div class="col"><h4>Language SDKs (gRPC)</h4><p>pymilvus / Go / Java / Node, translating method calls into proto messages over gRPC. <strong>Efficient, binary, long-lived connections</strong> — the production choice. Behavior unified by one proto.</p></div>
  <div class="col"><h4>RESTful API (HTTP/JSON)</h4><p>The Proxy embeds a gin HTTP server (<span class="inline">httpserver/handler_v2.go</span>, path <span class="mono">/v2/vectordb</span>). <strong>No SDK needed — curl works</strong>, great for quick trials and gRPC-less environments. It still lands on the same Proxy.</p></div>
</div>

<h2>Two doors: gRPC and REST, into the same Proxy</h2>
<p>Finally, the "two doors". <strong>gRPC</strong> is the main entrance: an HTTP/2 binary protocol with proto serialization — <strong>efficient, strongly typed, supporting streaming and long connections</strong> — used by nearly all official SDKs. But not everyone wants to pull in a gRPC SDK, so the Proxy <strong>also starts an HTTP server</strong> in <span class="inline">internal/distributed/proxy/service.go</span> (<span class="mono">registerHTTPServer</span>, using gin), wrapping the same capabilities as a <strong>RESTful JSON API</strong> (handlers in <span class="inline">httpserver/handler_v2.go</span>, path prefix <span class="mono">/v2/vectordb</span>). So an HTTP-only environment (browser scripts, curl, languages without a Milvus SDK) can use Milvus too.</p>

<p>So which door should you actually use? Here's a plain rule of thumb. For <strong>production, where you're chasing throughput and latency</strong>, take gRPC: reused long-lived connections, binary encoding, and the considerable bandwidth and parsing savings when shipping large batches of vectors — plus the official SDKs handle connection management and load balancing for you. For <strong>quick experiments, throwaway scripts, cross-language integration, or environments where pulling in a gRPC SDK is awkward</strong>, take REST: a single curl can create a collection, insert data, and run a search, and inspecting JSON in a browser or Postman makes debugging obvious. Plenty of teams use <strong>both</strong>: REST to validate ideas fast during development, then the core path switched back to gRPC for performance once in production. Whichever you pick, remember the refrain — <strong>two doors, one kitchen</strong> — the semantics don't change just because you changed doors. You can even get a search working over REST, confirm the parameters are right, and then confidently commit it to production code through a gRPC SDK, knowing both land on the very same <span class="mono">Proxy</span> logic.</p>
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

<div class="flow">
  <div class="node hl"><div class="nt">Proxy</div><div class="nd">打标记 req_id=abc + OptPropagated 字段</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">QueryNode</div><div class="nd">拦截器自动继承 → 日志带 req_id=abc</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">DataNode</div><div class="nd">同样继承 → 日志带 req_id=abc</div></div>
</div>

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

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="一个请求的分布式追踪：同一个 traceID 随 ctx 跨节点传播；Proxy 的 span 扇出到三个 QueryNode 的子 span，其中 QueryNode B 特别长（慢在这一跳）；三大支柱配合——指标发现、追踪定位、日志还原">
    <text x="20" y="38" style="fill:var(--muted)">一个请求的 trace 调用树（同一 <tspan class="mono" style="fill:var(--accent-ink)">traceID</tspan> 随 ctx 跨节点传播）</text>
    <text x="22" y="74" style="fill:var(--ink);font-weight:700">Proxy</text>
    <rect x="120" y="60" width="600" height="20" rx="4" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/><text x="130" y="75" style="fill:var(--accent-ink)">span · 父</text>
    <line x1="150" y1="80" x2="150" y2="146" style="stroke:var(--line);stroke-dasharray:3 3"/>
    <text x="22" y="100" style="fill:var(--muted)">QueryNode A</text>
    <rect x="150" y="90" width="140" height="16" rx="4" style="fill:var(--teal-soft);stroke:var(--teal)"/>
    <text x="22" y="124" style="fill:var(--muted)">QueryNode B</text>
    <rect x="150" y="114" width="410" height="16" rx="4" style="fill:var(--amber-soft);stroke:var(--amber);stroke-width:1.5"/><text x="570" y="127" style="fill:var(--amber);font-weight:700">← 慢在这一跳</text>
    <text x="22" y="148" style="fill:var(--muted)">QueryNode C</text>
    <rect x="150" y="138" width="160" height="16" rx="4" style="fill:var(--teal-soft);stroke:var(--teal)"/>
    <line x1="120" y1="166" x2="720" y2="166" style="stroke:var(--line)"/><text x="720" y="180" text-anchor="end" style="fill:var(--faint)">时间 →</text>
    <rect x="24" y="200" width="220" height="46" rx="9" style="fill:var(--panel);stroke:var(--blue);stroke-width:1.5"/><text x="134" y="220" text-anchor="middle" style="fill:var(--blue);font-weight:700">① 指标 Metrics</text><text x="134" y="238" text-anchor="middle" style="fill:var(--muted)">发现：P99↑、告警</text>
    <line x1="246" y1="223" x2="268" y2="223" style="stroke:var(--line);stroke-width:2"/><path d="M268,223 l-9,-4 l0,8 z" style="fill:var(--line)"/>
    <rect x="270" y="200" width="220" height="46" rx="9" style="fill:var(--panel);stroke:var(--amber);stroke-width:1.5"/><text x="380" y="220" text-anchor="middle" style="fill:var(--amber);font-weight:700">② 追踪 Traces</text><text x="380" y="238" text-anchor="middle" style="fill:var(--muted)">定位：慢的那一跳 span</text>
    <line x1="492" y1="223" x2="514" y2="223" style="stroke:var(--line);stroke-width:2"/><path d="M514,223 l-9,-4 l0,8 z" style="fill:var(--line)"/>
    <rect x="516" y="200" width="220" height="46" rx="9" style="fill:var(--panel);stroke:var(--teal);stroke-width:1.5"/><text x="626" y="220" text-anchor="middle" style="fill:var(--teal);font-weight:700">③ 日志 Logs</text><text x="626" y="238" text-anchor="middle" style="fill:var(--muted)">还原：用 ID 过滤日志</text>
    <text x="380" y="278" text-anchor="middle" style="fill:var(--muted)">靠同一个 traceID 塞进 ctx、随 gRPC 拦截器走遍全程，把碎片聚成"一个请求"的故事</text>
  </svg>
  <div class="figcap"><b>三者合一 · 在分布式系统里追一个请求</b>：给请求一个能<b>跨节点传播的身份</b>（traceID 塞进 ctx，随 gRPC 拦截器走遍全程）。于是 Proxy 的 span 扇出到三个 QueryNode 的<b>子 span</b>，拼成一棵<b>调用树</b>——<b>QueryNode B</b> 那条特别长，慢在这一跳。三大支柱接力：<b>① 指标</b>发现"出事了"、<b>② 追踪</b>定位"哪一跳"、<b>③ 日志</b>用同一个 ID 过滤、还原细节（原来是 mmap 缺页，第 35 课）。指标发现、追踪定位、日志还原，缺一不可。</div>
</div>

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

<p>It's worth spelling out <strong>aggregation</strong>, because it's the most fundamental divide between logs and metrics. Logs are <strong>un-aggregated</strong>: every time something happens, one line is faithfully recorded, so they're <strong>rich in detail</strong> but <strong>frighteningly large in volume</strong> — a busy cluster can emit hundreds of millions of log lines a day, and there's no way to grasp the whole by reading them one by one. Metrics are the opposite: from the very start they <strong>fold same-kind events into numbers</strong> — not "request #10001 took 8 ms" but a running "<strong>average latency over the last minute</strong>" or "<strong>total request count</strong>", a cumulative quantity or distribution. That aggregation makes metrics <strong>extremely lightweight</strong> (numeric curves, not mountains of text), ideal for <strong>long retention, fast charting, and real-time alerting</strong> — at the cost of <strong>dropping individual detail</strong>: they can tell you "latency rose" but not "which request". So the two are natural complements — <strong>one fine and heavy, one coarse and light</strong>; one for investigating after the fact, one for watching the dashboard live. Grasp this "aggregate or not" tradeoff and you see why you can't keep only one: logs alone drown you and can't alert in real time, while metrics alone leave you <strong>seeing the smoke but unable to find the fire</strong> when something breaks.</p>

<table class="t">
  <tr><th>Pillar</th><th>Question answered</th><th>Form</th><th>Milvus impl</th></tr>
  <tr><td><strong>Logs</strong></td><td>what exactly happened (event by event)</td><td>timestamped text/structured records</td><td class="mono">pkg/mlog (zap)</td></tr>
  <tr><td><strong>Metrics</strong></td><td>how's the whole doing (trends/alerts)</td><td>numeric curves over time</td><td class="mono">pkg/metrics (Prometheus)</td></tr>
  <tr><td><strong>Traces</strong></td><td>which stages a request crossed, how long each</td><td>hierarchical cross-node timeline</td><td class="mono">pkg/tracer (OpenTelemetry)</td></tr>
</table>

<h2>Logs: mlog — ctx mandatory, structured, propagatable across nodes</h2>
<p>First the pillar you deal with most — logs. Milvus has an <strong>iron rule</strong>: logging may only use <span class="mono">pkg/mlog</span> — not the standard <span class="mono">log</span>, not bare <span class="mono">fmt.Println</span>, not raw zap. Why so strict? Because <span class="mono">mlog</span> shoulders the hardest parts of distributed logging for you, and its design is thoughtful throughout.</p>
<p>First touch: <strong>every log must carry ctx</strong>. You write <span class="mono">mlog.Info(ctx, "message", mlog.String("field", value))</span> — the first argument is always the context. Why mandatory? Because ctx can <strong>carry "identity" accumulated along the way</strong>. Second touch: <strong>structured fields</strong>. Not splicing variables into a sentence (<span class="mono">"user " + id + " failed"</span>) but typed key-value pairs like <span class="mono">mlog.String</span>, <span class="mono">mlog.Int64</span>. Structured logs are <strong>machine-queryable</strong>: a log system can filter precisely by "field = value" instead of grepping text. Third and most elegant: <strong>fields can propagate across nodes</strong>. Attach fields to ctx with <span class="mono">mlog.WithFields(ctx, ...)</span> and child contexts inherit them; further, mark a field with <span class="mono">mlog.OptPropagated()</span> (e.g. collection name, collection ID) and, via gRPC interceptors (<span class="mono">mlog.UnaryServerInterceptor</span> / <span class="mono">UnaryClientInterceptor</span>), those fields <strong>"fly" with the RPC to downstream nodes</strong>. So a marker stamped on a request at the Proxy reappears verbatim in the QueryNode and DataNode logs it triggers — <strong>one ID nets every related log across the whole cluster</strong>. That's the most precious ability when debugging distributed systems. The two styles compared:</p>

<div class="flow">
  <div class="node hl"><div class="nt">Proxy</div><div class="nd">stamp req_id=abc + OptPropagated fields</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">QueryNode</div><div class="nd">interceptor inherits → logs carry req_id=abc</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">DataNode</div><div class="nd">inherits too → logs carry req_id=abc</div></div>
</div>

<p>A word more on why this "<strong>every log must carry ctx</strong>" rule deserves strict enforcement. In a single-machine program, whether a log carries context barely matters — it's all one process, and a little scrolling lets you line things up. But Milvus is <strong>distributed</strong>: a single request's "story" is written <strong>scattered across several processes and several machines</strong>. If every node just heads-down records its own segment with no shared "clue ID", those logs are like <strong>loose manuscript pages with no page numbers</strong> — all the information is there, yet it can never be reassembled into one whole story. The job of ctx is to <strong>stamp the same number on every page</strong>. Because that number rides along with ctx and can propagate across nodes through the interceptors, you can later take it and <strong>gather, in one stroke</strong>, every log belonging to the same request from a dozen machines. So this rule is not code-style fastidiousness; it's the <strong>life-or-death line for whether a distributed system can be debugged at all</strong> — drop one ctx and some critical log may go "<strong>off the grid</strong>", never rejoining the story it belongs to.</p>

<div class="cols">
  <div class="col"><h4>❌ String-spliced logs</h4><p><span class="mono">log.Printf("user %d search failed", id)</span>. Info buried in text; each node logs its own, unmatchable; filtering by user means regex guessing; cross a node and the trail breaks.</p></div>
  <div class="col"><h4>✅ mlog: structured + propagatable</h4><p><span class="mono">mlog.Info(ctx, "search failed", mlog.Int64("user", id))</span>. Typed fields, precisely filterable; via ctx + <span class="mono">OptPropagated</span> + interceptors, the marker <strong>flows with the request across nodes</strong>, one ID stitching the whole cluster.</p></div>
</div>

<h2>Metrics &amp; traces: Prometheus + OpenTelemetry</h2>
<p>The other two pillars both build on industry <strong>open standards</strong>, so they plug straight into mature ecosystem tools. <strong>Metrics</strong> are <strong>Prometheus-style</strong>: under <span class="inline">pkg/metrics</span>, each component has its own instrumentation file (<span class="mono">datacoord_metrics.go</span>, <span class="mono">datanode_metrics.go</span>, querynode, proxy, even <span class="mono">cgo_metrics.go</span> watching the Go↔C++ bridge). These are exposed at an HTTP endpoint, periodically <strong>scraped</strong> by Prometheus into time series, then drawn into dashboards by <strong>Grafana</strong> — latency, QPS, queue levels, memory at a glance, with thresholds for <strong>automatic alerts</strong>.</p>
<p><strong>Traces</strong> use <strong>OpenTelemetry</strong> (today's prevailing tracing standard): the core is in <span class="inline">pkg/tracer</span>, depending on <span class="mono">go.opentelemetry.io/otel</span>. Its key is again "<strong>stitching the trail across nodes</strong>" — via <strong>otelgrpc interceptors</strong> (<span class="mono">GetInterceptorOpts</span>): when a request goes from Proxy over gRPC to a QueryNode, the interceptor <strong>tucks the "trace context"</strong> (containing this trace's unique ID and current span) <strong>into the RPC metadata</strong>; the downstream node, on receipt, attaches its own processing as a <strong>child span</strong> on the same trace. All nodes' spans, gathered into a backend like Jaeger, assemble a <strong>complete call tree</strong>: which segment is slowest, which hop errored, drawn as a timeline you <strong>see through at a glance</strong>. Notice logs (OptPropagated fields) and traces (otel trace context) <strong>use the same move</strong> — <strong>tuck "identity" into ctx, then propagate with the RPC</strong>. No coincidence — it's the <strong>core method</strong> of distributed observability.</p>

<p>A word on why Milvus chooses to <strong>stand on open standards like Prometheus and OpenTelemetry</strong> rather than rolling its own. Observability is only as valuable as your ability to <strong>plug it into handy tools and actually look</strong> — collecting metrics and spans isn't enough; someone has to chart them, alert on them, and search them by trace ID. Tools like <strong>Prometheus</strong> (metric storage and alerting), <strong>Grafana</strong> (dashboards), and <strong>Jaeger</strong> (trace visualization) are already the <strong>de facto standards</strong> of the cloud-native world, and most ops engineers already know them. Milvus only has to make its metrics and traces <strong>speak the common tongue these tools understand</strong>, and users can drop it <strong>straight into their existing monitoring stack</strong> instead of learning a proprietary dashboard for one more database. It's pragmatic <strong>ecosystem thinking</strong>: do the part Milvus genuinely owns — <strong>collection</strong> (instrument, propagate, expose endpoints) — properly, and on the part the mature ecosystem already does well — <strong>display and alerting</strong> — don't reinvent the wheel, just open up for integration. It's the same restraint as Lesson 37's "hand GPU algorithms to Knowhere/RAFT and focus on integration" and Lesson 8's "lean on mature components like etcd and object storage": <strong>leave the specialist work to specialist tools, and just do the connecting glue well</strong>.</p>

<h2>Three as one: tracing a request across the distributed system</h2>
<p>Wire the three pillars together for a real "search got slow" investigation. <strong>Step 1, metrics detect the anomaly</strong>: on Grafana the P99 latency curve suddenly rises, an alert fires — you know "<strong>something's wrong</strong>", but not who or where. <strong>Step 2, traces locate the stage</strong>: open a slow request's trace and the call tree is clear — the Proxy was fast, but among the three fanned-out QueryNodes, <strong>one</strong> child span is unusually long; the problem narrows to "<strong>that hop</strong>". <strong>Step 3, logs reconstruct the detail</strong>: take this request's propagated ID, filter the logs of that QueryNode, and the related entries surface <strong>neatly</strong> — turns out a segment was faulting in via mmap, cold data slow on first load (Lesson 35). Three steps, root cause in hand.</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="A request's distributed trace: the same traceID propagates across nodes via ctx; the Proxy's span fans out to three QueryNode child spans, and QueryNode B's is unusually long (slow on this hop); the three pillars cooperate — metrics detect, traces locate, logs reconstruct">
    <text x="20" y="38" style="fill:var(--muted)">one request's trace call tree (same <tspan class="mono" style="fill:var(--accent-ink)">traceID</tspan>, propagated via ctx)</text>
    <text x="22" y="74" style="fill:var(--ink);font-weight:700">Proxy</text>
    <rect x="120" y="60" width="600" height="20" rx="4" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/><text x="130" y="75" style="fill:var(--accent-ink)">span · parent</text>
    <line x1="150" y1="80" x2="150" y2="146" style="stroke:var(--line);stroke-dasharray:3 3"/>
    <text x="22" y="100" style="fill:var(--muted)">QueryNode A</text>
    <rect x="150" y="90" width="140" height="16" rx="4" style="fill:var(--teal-soft);stroke:var(--teal)"/>
    <text x="22" y="124" style="fill:var(--muted)">QueryNode B</text>
    <rect x="150" y="114" width="410" height="16" rx="4" style="fill:var(--amber-soft);stroke:var(--amber);stroke-width:1.5"/><text x="570" y="127" style="fill:var(--amber);font-weight:700">← slow on this hop</text>
    <text x="22" y="148" style="fill:var(--muted)">QueryNode C</text>
    <rect x="150" y="138" width="160" height="16" rx="4" style="fill:var(--teal-soft);stroke:var(--teal)"/>
    <line x1="120" y1="166" x2="720" y2="166" style="stroke:var(--line)"/><text x="720" y="180" text-anchor="end" style="fill:var(--faint)">time →</text>
    <rect x="24" y="200" width="220" height="46" rx="9" style="fill:var(--panel);stroke:var(--blue);stroke-width:1.5"/><text x="134" y="220" text-anchor="middle" style="fill:var(--blue);font-weight:700">① Metrics</text><text x="134" y="238" text-anchor="middle" style="fill:var(--muted)">detect: P99↑, alert</text>
    <line x1="246" y1="223" x2="268" y2="223" style="stroke:var(--line);stroke-width:2"/><path d="M268,223 l-9,-4 l0,8 z" style="fill:var(--line)"/>
    <rect x="270" y="200" width="220" height="46" rx="9" style="fill:var(--panel);stroke:var(--amber);stroke-width:1.5"/><text x="380" y="220" text-anchor="middle" style="fill:var(--amber);font-weight:700">② Traces</text><text x="380" y="238" text-anchor="middle" style="fill:var(--muted)">locate: the slow span</text>
    <line x1="492" y1="223" x2="514" y2="223" style="stroke:var(--line);stroke-width:2"/><path d="M514,223 l-9,-4 l0,8 z" style="fill:var(--line)"/>
    <rect x="516" y="200" width="220" height="46" rx="9" style="fill:var(--panel);stroke:var(--teal);stroke-width:1.5"/><text x="626" y="220" text-anchor="middle" style="fill:var(--teal);font-weight:700">③ Logs</text><text x="626" y="238" text-anchor="middle" style="fill:var(--muted)">reconstruct: filter by ID</text>
    <text x="380" y="278" text-anchor="middle" style="fill:var(--muted)">one traceID in ctx, carried across every gRPC hop → fragments form one request's story</text>
  </svg>
  <div class="figcap"><b>Three pillars as one · tracing a request across the cluster</b>: give the request an <b>identity that propagates across nodes</b> (a traceID tucked into ctx, carried by gRPC interceptors the whole way). So the Proxy's span fans out to three QueryNode <b>child spans</b>, forming a <b>call tree</b> — <b>QueryNode B</b>'s is unusually long, slow on this hop. The pillars relay: <b>① metrics</b> detect "something's wrong", <b>② traces</b> locate "which hop", <b>③ logs</b> filter by the same ID and reconstruct the detail (an mmap page-fault, Lesson 35). Detect, locate, reconstruct — none is dispensable.</div>
</div>

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

LESSON_40 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
一套像 Milvus 这样的分布式系统，藏着<strong>成百上千个旋钮</strong>：超时多久、连接池多大、配额上限、端口、存储路径、各种阈值……这些旋钮怎么设、怎么按环境覆盖、代码怎么<strong>类型安全</strong>地读、又有哪些能<strong>边跑边拧</strong>（不重启）？这一课看 Milvus 的配置系统：上层是 <span class="mono">paramtable</span>（类型安全的配置注册表），底层是分层的<strong>数据源</strong>（<span class="mono">milvus.yaml</span> 文件 / 环境变量 / etcd），按<strong>优先级</strong>合并，部分还支持<strong>热更新</strong>。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  把配置想成一栋大楼的<strong>控制面板</strong>。面板上每个开关都<strong>印着标签、标好类型</strong>（这是温度、范围 16–30 度、默认 22）——你不会把"温度"误设成一句话，这就是 <span class="mono">paramtable</span> 的"<strong>类型安全</strong>"。开关的值有<strong>好几个来源</strong>，还讲<strong>优先级</strong>：墙上印的是<strong>出厂默认</strong>（<span class="mono">milvus.yaml</span>），房间门口的临时贴纸能<strong>覆盖默认</strong>（环境变量），而物业中控室能<strong>远程、实时</strong>地改某些开关（etcd）——级别越高、越"贴身"的来源，<strong>说了算</strong>。
  更妙的是：<strong>有些开关能在大楼运转时直接拧</strong>（热更新，比如调日志级别、限流阈值），<strong>有些则被锁死、只能停机才改</strong>（比如端口）。一块设计良好的面板，让你既改得方便、又不会误伤。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong>每个配置项是一个 <span class="mono">ParamItem</span>（带 Key、默认值、文档、<span class="mono">GetAsInt/Bool</span> 等类型化读取），按组件归类（grpc/quota/http…）；取值来自分层数据源——<span class="mono">milvus.yaml</span> 文件、环境变量、etcd——由 <span class="mono">config.Manager</span> 按优先级合并（值越小优先级越高），可变项还能经回调<strong>热更新</strong></strong>。代码只读类型化的值，从不自己解析字符串。
</div>

<h2>一个分布式系统有成百上千个旋钮</h2>
<p>先体会一下问题的规模。Milvus 有十几种组件、每种都有自己的可调项：Proxy 的限流阈值、各 RPC 的超时与重试、连接池大小、各类队列长度、配额与租户限制、对象存储的地址与桶名、etcd 路径、日志级别、是否对某字段启用 mmap……粗算下来<strong>成百上千</strong>。管理这么多配置，有四个绕不开的难题：一是<strong>怎么设默认值</strong>，让开箱即用；二是<strong>怎么按环境覆盖</strong>，开发/测试/生产各不相同；三是<strong>代码怎么读</strong>，既要类型正确（端口是整数、开关是布尔）又不能到处手写字符串解析；四是<strong>哪些能在运行时改</strong>，不必为调一个阈值就重启整个集群。</p>
<p>如果没有统一方案，这些难题会演变成灾难：默认值散落各处、改个配置要翻十个文件、各组件对"超时"的理解还不一致、读配置时到处 <span class="mono">strconv.Atoi</span> 还可能 panic……Milvus 的答案是把配置做成<strong>两层</strong>：上层 <span class="mono">paramtable</span> 提供"<strong>类型安全、有文档、可分组</strong>"的<strong>读取面</strong>，下层 <span class="mono">config</span> 提供"<strong>多来源、按优先级合并、可热更新</strong>"的<strong>取值面</strong>。两层一拆，"<strong>怎么用配置</strong>"和"<strong>配置从哪来</strong>"就各自清爽——这又是一次熟悉的"<strong>关注点分离</strong>"。</p>

<p>这种分离带来的好处，在<strong>读源码</strong>和<strong>排查"配置为什么不生效"</strong>时尤其明显。当你想知道"某个超时到底是多少、为什么是这个值"，你的排查路径会非常清晰：先去 <span class="mono">paramtable</span> 找到对应的 <span class="mono">ParamItem</span>，看它的 <span class="mono">Key</span> 和默认值；再去 <span class="mono">config</span> 那一层，看这个 Key 在 <span class="mono">milvus.yaml</span>、环境变量、etcd 里<strong>有没有被覆盖</strong>、谁的优先级更高。"<strong>用</strong>"的问题在上层、"<strong>取</strong>"的问题在下层，泾渭分明，你不会在一团乱麻里打转。反过来想，如果没有这层分离——假设每段业务代码都直接去读文件、读环境变量、还各自决定"谁覆盖谁"——那同一个配置在不同组件里可能被读出不同的值、覆盖规则也各执一词，这种 bug 几乎无法排查。所以"<strong>把取值统一收口到 config、把读取统一收口到 paramtable</strong>"不只是代码整洁，更是<strong>让整个系统的配置行为可预测、可解释</strong>的关键。一个旋钮无论被多少处代码读取，它的<strong>当前值只有一个、来源只有一条最高优先级的链路</strong>，这种确定性，正是大型系统配置管理的根本诉求。</p>

<h2>paramtable：类型安全的配置注册表</h2>
<p>先看上层。每一个配置项，在代码里都是一个 <span class="mono">ParamItem</span>（定义在 <span class="inline">pkg/util/paramtable/param_item.go</span>）。它远不只是"一个值"，而是把这个旋钮的<strong>全部元信息</strong>都登记在册：<span class="mono">Key</span>（形如 <span class="mono">"A.B.C"</span> 的层级键）、<span class="mono">DefaultValue</span>（默认值）、<span class="mono">Doc</span>（这个旋钮干什么用的文档）、<span class="mono">FallbackKeys</span>（兼容旧键名）、还有 <span class="mono">PanicIfEmpty</span>、<span class="mono">Immutable</span>、<span class="mono">Formatter</span> 等行为标记。</p>
<p>最关键的是它提供<strong>类型化的读取方法</strong>：<span class="mono">GetValue()</span> 取字符串、<span class="mono">GetAsBool()</span> 取布尔、<span class="mono">GetAsInt()</span> / <span class="mono">GetAsInt64()</span> 取整数……于是消费方的代码长这样：<span class="mono">Params.ProxyCfg.SomeTimeout.GetAsInt()</span>——<strong>直接拿到一个类型正确的值，从不自己解析字符串</strong>。这一点看似小，意义却大：它把"字符串 → 类型"的转换<strong>收口到一处</strong>（ParamItem 内部），既避免了满地的 <span class="mono">strconv</span> 与重复 bug，也让"忘了转换、转错类型"这类错误<strong>无处发生</strong>。这些 <span class="mono">ParamItem</span> 还按<strong>组件/主题</strong>分门别类地组织在不同文件里：<span class="mono">grpc_param.go</span>、<span class="mono">quota_param.go</span>、<span class="mono">http_param.go</span>、<span class="mono">knowhere_param.go</span>……每个文件聚一类旋钮，整整齐齐。下面这张分层图，画出从"取值底座"到"分组旋钮"再到"单个 ParamItem"的结构。</p>

<p>除了类型安全，<span class="mono">ParamItem</span> 登记的那些<strong>元信息</strong>还各有妙用，值得一一点出。<span class="mono">DefaultValue</span> 让系统<strong>开箱即用</strong>——你什么都不配，它也能用一套合理默认跑起来。<span class="mono">Doc</span> 不只是注释：它能被工具<strong>提取出来自动生成配置文档</strong>，于是 <span class="mono">milvus.yaml</span> 里每个旋钮旁边那句解释，和代码里的定义<strong>同一个源头、永不脱节</strong>。<span class="mono">FallbackKeys</span> 解决<strong>历史包袱</strong>：当一个配置项改了名字，老的键名还能作为后备被识别，这样升级 Milvus 时<strong>旧配置文件不会一夜失效</strong>。<span class="mono">PanicIfEmpty</span> 则是一道<strong>启动期护栏</strong>：对那些"没有就根本没法工作"的关键配置，干脆在启动时就因缺失而明确报错，而不是带着一个空值<strong>跑到半路才神秘崩溃</strong>。你看，把一个"配置项"做成一个登记齐全的对象、而非一个裸字符串，背后是一整套<strong>对可维护性、可升级性、可诊断性的周到考量</strong>——这正是成熟工程与玩具项目的分水岭。</p>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">取值底座</span><span class="name">config.Manager（合并多来源、按优先级给出当前值）</span></div><div class="ld">背后是 file/env/etcd 等数据源；支持热更新分发</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">分组</span><span class="name">组件参数（grpc_param / quota_param / http_param …）</span></div><div class="ld">按组件/主题把成百上千个旋钮归类，便于查找与维护</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">单项</span><span class="name">ParamItem（Key/Default/Doc + GetAsInt/Bool…）</span></div><div class="ld">登记元信息、提供类型化读取；代码只读类型值，不解析字符串</div></div>
</div>

<h2>配置从哪来：分层数据源与优先级</h2>
<p>再看下层——值到底从哪儿取。<span class="mono">config</span> 包（<span class="inline">pkg/config</span>）定义了多种<strong>数据源（Source）</strong>，每种来源各有<strong>优先级</strong>。最基础的是 <strong>FileSource</strong>：读 <span class="inline">configs/milvus.yaml</span>，这是<strong>人类可读的默认配置文件</strong>，也是所有旋钮"<strong>对外展示的清单</strong>"——你想知道有哪些配置、默认是多少，看它就对了。其上是 <strong>EnvSource</strong>：环境变量，方便在容器/CI 里<strong>临时覆盖</strong>，无需改文件。最高的是 <strong>EtcdSource</strong>：把配置放进 etcd，可<strong>集群级、运行时</strong>统一下发与修改。</p>
<p>多来源就要定<strong>谁说了算</strong>。<span class="mono">config.Manager</span>（<span class="inline">pkg/config/manager.go</span>）负责把各来源<strong>合并</strong>，规则是按优先级：源码里 <span class="mono">HighPriority=1</span>、<span class="mono">NormalPriority=11</span>、<span class="mono">LowPriority=21</span>，并注明"<strong>值越小、优先级越高</strong>"。直观理解就是"<strong>越贴身、越动态的来源越优先</strong>"：etcd（运行时下发）压过环境变量、环境变量压过文件默认。这套"<strong>分层覆盖</strong>"模式你一定不陌生——它和绝大多数成熟配置系统一个套路：<strong>给一套合理默认，再允许逐层精确覆盖</strong>，既开箱即用，又能在每个环境精准调校。下面把三种来源摆在一起。</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="配置取值的分层与优先级：以 quota.timeout 为例，etcd 运行时下发 60s（pri=1 最高、且有值）压过环境变量、milvus.yaml 文件的 30s 与内置默认 10s，合并后的生效值是 60s；值越小优先级越高">
    <text x="20" y="32" style="fill:var(--ink);font-weight:700">一个旋钮的取值从哪来？例：<tspan class="mono">quota.timeout</tspan>（值越小优先级越高）</text>
    <rect x="40" y="52" width="384" height="36" rx="7" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/><text x="54" y="75" style="fill:var(--accent-ink);font-weight:700">etcd · 运行时下发（pri=1 最高）</text><text x="410" y="75" text-anchor="end" style="fill:var(--accent-ink);font-weight:700">60s ✓</text>
    <rect x="40" y="96" width="384" height="36" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="54" y="119" style="fill:var(--muted)">环境变量 env（pri=11）</text><text x="410" y="119" text-anchor="end" style="fill:var(--faint)">未设</text>
    <rect x="40" y="140" width="384" height="36" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="54" y="163" style="fill:var(--muted)">milvus.yaml 文件（pri=21）</text><text x="410" y="163" text-anchor="end" style="fill:var(--faint);text-decoration:line-through">30s</text>
    <rect x="40" y="184" width="384" height="36" rx="7" style="fill:var(--panel-2);stroke:var(--line)"/><text x="54" y="207" style="fill:var(--muted)">默认值 default（内置兜底）</text><text x="410" y="207" text-anchor="end" style="fill:var(--faint);text-decoration:line-through">10s</text>
    <text x="34" y="48" style="fill:var(--faint)">高</text><text x="34" y="236" style="fill:var(--faint)">低</text>
    <line x1="446" y1="136" x2="532" y2="136" style="stroke:var(--accent);stroke-width:2.5"/><path d="M532,136 l-12,-5 l0,10 z" style="fill:var(--accent)"/><text x="489" y="128" text-anchor="middle" style="fill:var(--muted)">合并</text>
    <rect x="536" y="106" width="206" height="62" rx="11" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:2"/><text x="639" y="132" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">生效值 = 60s</text><text x="639" y="153" text-anchor="middle" style="fill:var(--muted)">← 最高优先级且有值</text>
    <text x="380" y="252" text-anchor="middle" style="fill:var(--muted)">config.Manager 合并：越贴身/越动态越优先（etcd &gt; env &gt; yaml &gt; default），可变项还能热更新</text>
  </svg>
  <div class="figcap"><b>配置从哪来 = 分层数据源 + 优先级合并</b>：同一个旋钮（如 <span class="mono">quota.timeout</span>）可能在多个来源里被设值，<span class="mono">config.Manager</span> 按优先级合并——<b>值越小优先级越高</b>，越<b>贴身/动态</b>的来源越优先：<b>etcd（运行时）&gt; 环境变量 &gt; milvus.yaml 文件 &gt; 内置默认</b>。本例里 etcd 下发了 60s（最高优先级且有值），就<b>压过</b>了 yaml 的 30s、默认的 10s，最终生效值 = <b>60s</b>。代码只读类型化的值，不关心它来自哪一层；可变项还能<b>热更新、不重启</b>。</div>
</div>

<div class="flow">
  <div class="node"><div class="nt">milvus.yaml</div><div class="nd">文件默认(低)</div></div>
  <div class="arrow">＜</div>
  <div class="node"><div class="nt">环境变量</div><div class="nd">部署覆盖(中)</div></div>
  <div class="arrow">＜</div>
  <div class="node hl"><div class="nt">etcd</div><div class="nd">运行时下发(高)</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">config.Manager</div><div class="nd">按优先级合并 → ParamItem.GetAsInt()</div></div>
</div>

<p>为什么"<strong>越贴身、越动态的来源优先级越高</strong>"这条规则是合理的？因为它恰好匹配了人们调整配置的<strong>真实意图</strong>。文件默认是"<strong>大多数情况下的合理选择</strong>"，最普适、也最该被特殊情况覆盖；环境变量是"<strong>这一次部署的特定需要</strong>"，比通用默认更贴合当下；而 etcd 里的运行时配置是"<strong>此刻、由运维明确下发的决定</strong>"，往往是为了应对正在发生的状况（比如临时收紧限流以扛住流量峰值）——它<strong>最贴身、最该说了算</strong>。把优先级设计成"动态压过静态、具体压过通用"，本质是让系统<strong>尊重"更晚、更具体、更有针对性"的那个决定</strong>。这也提醒你一个排查配置问题的要诀：当某个配置"<strong>改了文件却不生效</strong>"，十有八九是被一个<strong>更高优先级的来源</strong>（环境变量或 etcd）悄悄覆盖了——顺着优先级链从高往低查，往往一抓一个准。</p>

<table class="t">
  <tr><th>数据源</th><th>来自哪里</th><th>典型用途</th><th>优先级</th></tr>
  <tr><td class="mono">FileSource</td><td>configs/milvus.yaml</td><td>默认值 + 旋钮清单（人类可读）</td><td>低（兜底）</td></tr>
  <tr><td class="mono">EnvSource</td><td>环境变量</td><td>容器/CI 里临时覆盖，不改文件</td><td>中</td></tr>
  <tr><td class="mono">EtcdSource</td><td>etcd 中的配置</td><td>集群级、运行时统一下发/修改</td><td>高（最贴身）</td></tr>
</table>

<h2>热更新：有些旋钮能边跑边拧</h2>
<p>最后是最体现"分布式运维友好"的一招：<strong>热更新</strong>。很多时候，你只想调一个限流阈值或日志级别，却<strong>不想为此重启整个集群</strong>（重启意味着抖动、甚至短暂不可用）。Milvus 的配置系统支持：把变更写进 <strong>etcd</strong>，<span class="mono">config.Manager</span> 通过它的<strong>分发器（Dispatcher）</strong>感知到变化，回调通知相关的 <span class="mono">ParamItem</span> 刷新自己的 <span class="mono">lastValue</span>——于是代码下次 <span class="mono">GetAsInt()</span> 拿到的就是<strong>新值，立即生效，无需重启</strong>。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>改 etcd 里的值</h4><p>把某可变配置（如限流阈值、日志级别）的新值写进 etcd。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Manager 感知</h4><p><span class="mono">config.Manager</span> 经 EtcdSource 监听到变更，由 <strong>Dispatcher</strong> 分发事件。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>回调刷新 ParamItem</h4><p>相关 <span class="mono">ParamItem</span> 的回调被触发，更新其 <span class="mono">lastValue</span>。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>代码读到新值</h4><p>下次 <span class="mono">GetAsInt()</span> 即返回新值，立即生效——不可变项(Immutable)则拒绝此流程。</p></div></div>
</div>
<p>但并非所有旋钮都能这么改。有些配置<strong>天生不该在运行时变</strong>（比如服务端口、某些一经初始化就定型的结构），于是 <span class="mono">ParamItem</span> 用 <span class="mono">Immutable</span> / <span class="mono">Forbidden</span> 标记把它们<strong>锁住</strong>，拒绝热更新——这是一种<strong>保护</strong>：宁可不让你改，也不让"运行时改了个本不该动的东西"引发诡异故障。把"可变 / 不可变"显式标在每个旋钮上，正是一块好控制面板的素养：<strong>能动的让你方便地动，不能动的干脆锁死</strong>。</p>

<p>这里再借热更新这件事，说一个更深的设计取舍：<strong>"能改"与"安全"之间永远要权衡</strong>。把所有配置都做成可热更新，听起来很灵活，实则危险——有些参数一旦在运行中被改，可能让进行中的请求行为不一致、或让某些已按旧值初始化的内部结构与新值"对不上"，引发难以复现的诡异故障。所以 Milvus 的态度是<strong>保守而克制</strong>：默认把"改了可能出事"的旋钮锁住，只对那些<strong>明确安全、且确实有运行时调整需求</strong>的参数（限流、日志级别、部分配额）开放热更新。这种"<strong>把危险操作默认关掉、只在确知安全处才打开</strong>"的姿态，和第 37 课"GPU 默认 OFF、要的人才编译开启"是同一种工程价值观——<strong>面对一个分布式系统，宁可少给一点便利，也要守住确定性与稳定性这条底线</strong>。理解了这一点，你看 <span class="mono">Immutable</span>/<span class="mono">Forbidden</span> 这些标记就不再觉得是"限制"，而会读出背后那份"<strong>对生产环境的敬畏</strong>"。</p>

<p>串起这一课：<span class="mono">paramtable</span> 给你一个类型安全、有文档、分组清晰的<strong>读取面</strong>，<span class="mono">config</span> 给你一个多来源、按优先级合并、可热更新的<strong>取值面</strong>，两层协作，把"<strong>成百上千个旋钮</strong>"管得井井有条。下一课是第 9 部分的收尾——<strong>部署</strong>：standalone 与 cluster、它依赖的 etcd/对象存储/消息组件，以及怎么把这套系统真正跑起来。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>两层设计</strong>：<span class="mono">paramtable</span>(读取面：类型安全/有文档/分组) + <span class="mono">config</span>(取值面：多来源/优先级/热更新)；"怎么用配置"与"配置从哪来"分离。</li>
    <li><strong>ParamItem</strong>：每个旋钮一项，登记 Key/DefaultValue/Doc，提供 <span class="mono">GetAsInt/GetAsBool</span> 等类型化读取；代码不自己解析字符串，转换收口一处。</li>
    <li><strong>分层数据源</strong>：FileSource(milvus.yaml 默认/清单) &lt; EnvSource(环境变量) &lt; EtcdSource(运行时下发)，由 <span class="mono">config.Manager</span> 按优先级合并（值越小越优先）。</li>
    <li><strong>热更新</strong>：可变项经 etcd + Dispatcher 回调刷新、立即生效不重启；<span class="mono">Immutable/Forbidden</span> 项锁死、拒绝运行时修改以保安全。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
A distributed system like Milvus hides <strong>hundreds of knobs</strong>: timeouts, pool sizes, quota ceilings, ports, storage paths, thresholds… How are they set, overridden per environment, read <strong>type-safely</strong> by code, and which can be <strong>turned while running</strong> (no restart)? This lesson covers Milvus's config system: on top is <span class="mono">paramtable</span> (a type-safe config registry); underneath are layered <strong>sources</strong> (the <span class="mono">milvus.yaml</span> file / environment variables / etcd), merged by <strong>priority</strong>, with some supporting <strong>hot reload</strong>.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of config as a building's <strong>control panel</strong>. Each switch is <strong>labeled and typed</strong> (this is temperature, range 16–30, default 22) — you can't mis-set "temperature" to a sentence; that's <span class="mono">paramtable</span>'s "<strong>type safety</strong>". A switch's value has <strong>several sources</strong> with a <strong>priority</strong>: printed on the wall is the <strong>factory default</strong> (<span class="mono">milvus.yaml</span>), a sticky note by the door can <strong>override the default</strong> (env vars), and a facilities control room can change some switches <strong>remotely, in real time</strong> (etcd) — the higher, more "personal" source <strong>wins</strong>.
  Better still: <strong>some switches can be turned while the building runs</strong> (hot reload — log level, rate limits), while <strong>others are locked, changeable only when shut down</strong> (ports). A well-designed panel makes you both able to change easily and unable to break things by accident.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>each config item is a <span class="mono">ParamItem</span> (with Key, default, doc, typed getters like <span class="mono">GetAsInt/Bool</span>), grouped by component (grpc/quota/http…); values come from layered sources — <span class="mono">milvus.yaml</span>, env vars, etcd — merged by <span class="mono">config.Manager</span> by priority (lesser value = higher priority), with mutable items <strong>hot-reloadable</strong> via callbacks</strong>. Code only reads typed values; it never parses strings itself.
</div>

<h2>A distributed system has hundreds of knobs</h2>
<p>First, the scale of the problem. Milvus has a dozen kinds of components, each with its own tunables: the Proxy's rate limits, each RPC's timeout and retry, pool sizes, queue lengths, quotas and tenant limits, object-storage address and bucket, etcd paths, log level, whether to mmap a field… <strong>hundreds</strong> in all. Managing this many configs raises four unavoidable problems: how to <strong>set defaults</strong> for out-of-the-box use; how to <strong>override per environment</strong> (dev/test/prod differ); how <strong>code reads them</strong> (type-correctly — ports are ints, switches are bools — without hand-written string parsing everywhere); and which can be <strong>changed at runtime</strong> without restarting the whole cluster to tweak one threshold.</p>
<p>Without a unified scheme, these become a disaster: defaults scattered everywhere, changing one config means touching ten files, components disagree on what "timeout" means, reading config means <span class="mono">strconv.Atoi</span> all over the place that might panic… Milvus's answer is <strong>two layers</strong>: the upper <span class="mono">paramtable</span> provides a "<strong>type-safe, documented, grouped</strong>" <strong>read surface</strong>; the lower <span class="mono">config</span> provides a "<strong>multi-source, priority-merged, hot-reloadable</strong>" <strong>value surface</strong>. Split the two and "<strong>how to use config</strong>" and "<strong>where config comes from</strong>" each stay clean — a familiar "<strong>separation of concerns</strong>" again.</p>

<p>The payoff of this separation is most obvious when you're <strong>reading the source</strong> or chasing down "<strong>why isn't this config taking effect?</strong>". When you want to know "what is some timeout actually set to, and why that value", your path is crisp: first go to <span class="mono">paramtable</span>, find the matching <span class="mono">ParamItem</span>, and read its <span class="mono">Key</span> and default; then drop to the <span class="mono">config</span> layer and check whether that Key has been <strong>overridden</strong> in <span class="mono">milvus.yaml</span>, an env var, or etcd, and which source outranks which. The "<strong>use</strong>" question lives upstairs and the "<strong>fetch</strong>" question downstairs, cleanly divided, so you never spin in a tangle. The opposite — every piece of business code reading files and env vars directly and each deciding "who overrides whom" — would let the same config resolve to <strong>different values in different components</strong>, with override rules that each disagree, a nearly un-diagnosable bug. So funneling all value-fetching into <span class="mono">config</span> and all reading into <span class="mono">paramtable</span> isn't mere tidiness; it's what makes the whole system's config behavior <strong>predictable and explainable</strong> — a knob, however many places read it, has exactly <strong>one current value reached by one highest-priority chain</strong>, and that determinism is the bedrock requirement of large-system config management.</p>

<h2>paramtable: a type-safe config registry</h2>
<p>The upper layer first. Each config item, in code, is a <span class="mono">ParamItem</span> (defined in <span class="inline">pkg/util/paramtable/param_item.go</span>). It's far more than "a value" — it registers the knob's <strong>full metadata</strong>: <span class="mono">Key</span> (a hierarchical key like <span class="mono">"A.B.C"</span>), <span class="mono">DefaultValue</span>, <span class="mono">Doc</span> (what the knob is for), <span class="mono">FallbackKeys</span> (compatibility with old key names), plus behavior flags like <span class="mono">PanicIfEmpty</span>, <span class="mono">Immutable</span>, <span class="mono">Formatter</span>.</p>
<p>The key part is its <strong>typed getters</strong>: <span class="mono">GetValue()</span> for string, <span class="mono">GetAsBool()</span> for bool, <span class="mono">GetAsInt()</span> / <span class="mono">GetAsInt64()</span> for ints… So consumer code looks like <span class="mono">Params.ProxyCfg.SomeTimeout.GetAsInt()</span> — <strong>getting a correctly-typed value directly, never parsing strings itself</strong>. This seems small but matters: it <strong>funnels "string → type" conversion into one place</strong> (inside ParamItem), avoiding scattered <span class="mono">strconv</span> and duplicated bugs, and making "forgot to convert, converted to the wrong type" errors <strong>impossible to occur</strong>. These <span class="mono">ParamItem</span>s are also organized by <strong>component/topic</strong> across files: <span class="mono">grpc_param.go</span>, <span class="mono">quota_param.go</span>, <span class="mono">http_param.go</span>, <span class="mono">knowhere_param.go</span>… each file gathering one class of knobs, neatly. The layered diagram shows the structure from "value base" to "grouped knobs" to "a single ParamItem".</p>

<p>Beyond type safety, the <strong>metadata</strong> a <span class="mono">ParamItem</span> registers each earns its keep, and it's worth naming them one by one. <span class="mono">DefaultValue</span> makes the system <strong>work out of the box</strong> — configure nothing and it still runs on a set of sensible defaults. <span class="mono">Doc</span> is more than a comment: tools can <strong>extract it to auto-generate the config documentation</strong>, so the one-line explanation beside each knob in <span class="mono">milvus.yaml</span> and the definition in code share <strong>a single source and never drift apart</strong>. <span class="mono">FallbackKeys</span> handles <strong>historical baggage</strong>: when a config item is renamed, its old key name is still recognized as a fallback, so upgrading Milvus doesn't make an existing config file <strong>go invalid overnight</strong>. And <span class="mono">PanicIfEmpty</span> is a <strong>startup-time guardrail</strong>: for the critical configs that "can't function at all if absent", it deliberately fails loudly at startup over the missing value, rather than carrying an empty value and <strong>crashing mysteriously halfway through</strong>. Making a config item a fully-registered object instead of a bare string reflects a whole set of <strong>deliberate care for maintainability, upgradeability, and diagnosability</strong> — exactly what separates mature engineering from a toy project.</p>

<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">value base</span><span class="name">config.Manager (merges sources, gives the current value by priority)</span></div><div class="ld">backed by file/env/etcd sources; supports hot-update dispatch</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">groups</span><span class="name">component params (grpc_param / quota_param / http_param …)</span></div><div class="ld">categorize hundreds of knobs by component/topic for findability &amp; upkeep</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">item</span><span class="name">ParamItem (Key/Default/Doc + GetAsInt/Bool…)</span></div><div class="ld">registers metadata, offers typed reads; code reads typed values, no string parsing</div></div>
</div>

<h2>Where config comes from: layered sources and priority</h2>
<p>Now the lower layer — where values actually come from. The <span class="mono">config</span> package (<span class="inline">pkg/config</span>) defines several <strong>sources</strong>, each with a <strong>priority</strong>. The most basic is <strong>FileSource</strong>: reading <span class="inline">configs/milvus.yaml</span>, the <strong>human-readable default config file</strong> and the "<strong>catalog of every knob</strong>" — to learn which configs exist and their defaults, look here. Above it is <strong>EnvSource</strong>: environment variables, handy for <strong>temporary overrides</strong> in containers/CI without editing files. Highest is <strong>EtcdSource</strong>: config in etcd, for <strong>cluster-wide, runtime</strong> distribution and modification.</p>
<p>Multiple sources require deciding <strong>who wins</strong>. <span class="mono">config.Manager</span> (<span class="inline">pkg/config/manager.go</span>) <strong>merges</strong> the sources by priority: the source defines <span class="mono">HighPriority=1</span>, <span class="mono">NormalPriority=11</span>, <span class="mono">LowPriority=21</span>, noting "<strong>lesser value = higher priority</strong>". Intuitively, "<strong>the more personal and dynamic source wins</strong>": etcd (runtime) beats env vars, env vars beat file defaults. This "<strong>layered override</strong>" pattern is surely familiar — the same play as most mature config systems: <strong>give sensible defaults, then allow precise layered overrides</strong>, both out-of-the-box and tunable per environment. The three sources side by side:</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="Layered config sources and priority: for quota.timeout, etcd's runtime 60s (pri=1, highest, has a value) overrides env vars, the milvus.yaml file's 30s and the built-in default 10s; the merged effective value is 60s; lesser value = higher priority">
    <text x="20" y="32" style="fill:var(--ink);font-weight:700">where does a knob's value come from? e.g. <tspan class="mono">quota.timeout</tspan> (lesser = higher priority)</text>
    <rect x="40" y="52" width="384" height="36" rx="7" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.5"/><text x="54" y="75" style="fill:var(--accent-ink);font-weight:700">etcd · runtime override (pri=1, top)</text><text x="410" y="75" text-anchor="end" style="fill:var(--accent-ink);font-weight:700">60s ✓</text>
    <rect x="40" y="96" width="384" height="36" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="54" y="119" style="fill:var(--muted)">env vars (pri=11)</text><text x="410" y="119" text-anchor="end" style="fill:var(--faint)">unset</text>
    <rect x="40" y="140" width="384" height="36" rx="7" style="fill:var(--panel);stroke:var(--line)"/><text x="54" y="163" style="fill:var(--muted)">milvus.yaml file (pri=21)</text><text x="410" y="163" text-anchor="end" style="fill:var(--faint);text-decoration:line-through">30s</text>
    <rect x="40" y="184" width="384" height="36" rx="7" style="fill:var(--panel-2);stroke:var(--line)"/><text x="54" y="207" style="fill:var(--muted)">default value (built-in)</text><text x="410" y="207" text-anchor="end" style="fill:var(--faint);text-decoration:line-through">10s</text>
    <text x="34" y="48" style="fill:var(--faint)">high</text><text x="34" y="236" style="fill:var(--faint)">low</text>
    <line x1="446" y1="136" x2="532" y2="136" style="stroke:var(--accent);stroke-width:2.5"/><path d="M532,136 l-12,-5 l0,10 z" style="fill:var(--accent)"/><text x="489" y="128" text-anchor="middle" style="fill:var(--muted)">merge</text>
    <rect x="536" y="106" width="206" height="62" rx="11" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:2"/><text x="639" y="132" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">effective = 60s</text><text x="639" y="153" text-anchor="middle" style="fill:var(--muted)">← highest with a value</text>
    <text x="380" y="252" text-anchor="middle" style="fill:var(--muted)">config.Manager merges by priority: etcd &gt; env &gt; yaml &gt; default; mutable keys hot-reload</text>
  </svg>
  <div class="figcap"><b>Where config comes from = layered sources + priority merge</b>: one knob (e.g. <span class="mono">quota.timeout</span>) may be set in several sources; <span class="mono">config.Manager</span> merges by priority — <b>lesser value = higher priority</b>, and the more <b>personal/dynamic</b> source wins: <b>etcd (runtime) &gt; env vars &gt; milvus.yaml file &gt; built-in default</b>. Here etcd pushes 60s (highest priority, and it has a value), so it <b>overrides</b> yaml's 30s and the default 10s — effective value = <b>60s</b>. Code reads only the typed value, never caring which layer it came from; mutable keys even <b>hot-reload, no restart</b>.</div>
</div>

<div class="flow">
  <div class="node"><div class="nt">milvus.yaml</div><div class="nd">file default (low)</div></div>
  <div class="arrow">＜</div>
  <div class="node"><div class="nt">env vars</div><div class="nd">deploy override (mid)</div></div>
  <div class="arrow">＜</div>
  <div class="node hl"><div class="nt">etcd</div><div class="nd">runtime push (high)</div></div>
  <div class="arrow">→</div>
  <div class="node"><div class="nt">config.Manager</div><div class="nd">merge by priority → ParamItem.GetAsInt()</div></div>
</div>

<p>Why is "<strong>the more personal and dynamic the source, the higher its priority</strong>" a sensible rule? Because it lines up with people's <strong>real intent</strong> when they adjust config. The file default is "<strong>the reasonable choice in most situations</strong>" — the most universal, and the one that most deserves to be overridden by special cases. An env var is "<strong>this particular deployment's need</strong>", more fitted to the moment than a generic default. And a runtime value in etcd is "<strong>a decision ops is pushing deliberately, right now</strong>", often to deal with a situation that's actively unfolding (temporarily tightening rate limits to ride out a traffic spike, say) — it's the most personal, and the one that most deserves to win. Designing priority as "<strong>dynamic beats static, specific beats general</strong>" is essentially making the system <strong>honor the later, more specific, more targeted decision</strong>. It also hands you a key for troubleshooting config: when something "<strong>was changed in the file but won't take effect</strong>", nine times out of ten it's being quietly overridden by a <strong>higher-priority source</strong> (an env var or etcd) — walk the priority chain from high to low and you'll usually catch the culprit.</p>

<table class="t">
  <tr><th>Source</th><th>Where from</th><th>Typical use</th><th>Priority</th></tr>
  <tr><td class="mono">FileSource</td><td>configs/milvus.yaml</td><td>defaults + knob catalog (human-readable)</td><td>low (fallback)</td></tr>
  <tr><td class="mono">EnvSource</td><td>environment variables</td><td>temporary override in containers/CI, no file edits</td><td>medium</td></tr>
  <tr><td class="mono">EtcdSource</td><td>config in etcd</td><td>cluster-wide, runtime distribution/changes</td><td>high (most personal)</td></tr>
</table>

<h2>Hot reload: some knobs turn while running</h2>
<p>Finally, the move that best embodies "distributed-ops friendliness": <strong>hot reload</strong>. Often you just want to tweak a rate limit or log level, but <strong>not restart the whole cluster for it</strong> (a restart means jitter, even brief unavailability). Milvus's config system supports this: write the change into <strong>etcd</strong>, <span class="mono">config.Manager</span> senses it via its <strong>Dispatcher</strong>, callbacks notify the relevant <span class="mono">ParamItem</span> to refresh its <span class="mono">lastValue</span> — so the code's next <span class="mono">GetAsInt()</span> gets the <strong>new value, effective immediately, no restart</strong>.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Change the value in etcd</h4><p>write a new value for a mutable config (rate limit, log level) into etcd.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Manager senses it</h4><p><span class="mono">config.Manager</span> observes the change via EtcdSource; the <strong>Dispatcher</strong> dispatches the event.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Callback refreshes ParamItem</h4><p>the relevant <span class="mono">ParamItem</span>'s callback fires, updating its <span class="mono">lastValue</span>.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Code reads the new value</h4><p>the next <span class="mono">GetAsInt()</span> returns it, effective at once — Immutable items refuse this flow.</p></div></div>
</div>
<p>But not every knob may change this way. Some configs <strong>shouldn't vary at runtime</strong> (service ports, structures fixed once initialized), so <span class="mono">ParamItem</span> uses <span class="mono">Immutable</span> / <span class="mono">Forbidden</span> flags to <strong>lock them</strong>, refusing hot reload — a <strong>protection</strong>: better to forbid the change than let "changing something at runtime that shouldn't move" cause weird failures. Marking "mutable / immutable" explicitly on each knob is the mark of a good control panel: <strong>let you easily move what can move, lock outright what can't</strong>. Tying the lesson together: <span class="mono">paramtable</span> gives you a type-safe, documented, well-grouped <strong>read surface</strong>; <span class="mono">config</span> gives you a multi-source, priority-merged, hot-reloadable <strong>value surface</strong>; the two cooperate to keep "<strong>hundreds of knobs</strong>" in good order. Next lesson closes Part 9 — <strong>deployment</strong>: standalone vs cluster, its etcd/object-storage/messaging dependencies, and how to actually run the whole thing.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Two layers</strong>: <span class="mono">paramtable</span> (read surface: type-safe/documented/grouped) + <span class="mono">config</span> (value surface: multi-source/priority/hot-reload); "how to use config" separated from "where it comes from".</li>
    <li><strong>ParamItem</strong>: one per knob, registering Key/DefaultValue/Doc and offering typed getters (<span class="mono">GetAsInt/GetAsBool</span>); code never parses strings — conversion funneled to one place.</li>
    <li><strong>Layered sources</strong>: FileSource (milvus.yaml default/catalog) &lt; EnvSource (env vars) &lt; EtcdSource (runtime distribution), merged by <span class="mono">config.Manager</span> by priority (lesser = higher).</li>
    <li><strong>Hot reload</strong>: mutable items refresh via etcd + Dispatcher callbacks, effective without restart; <span class="mono">Immutable/Forbidden</span> items are locked, refusing runtime changes for safety.</li>
  </ul>
</div>
""",
}

LESSON_41 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
第 8 课告诉你 Milvus <strong>依赖什么</strong>（etcd、对象存储、消息队列）、有哪几种<strong>部署形态</strong>。这一课作为第 9 部分的收尾，换一副<strong>运维实战</strong>的眼镜：你到底怎么<strong>把它真正跑起来</strong>——从一行命令的内嵌单机，到一整个生产级 Kubernetes 集群；以及第 3 部分那套"<strong>拆开的架构</strong>"，在部署时如何回报你"<strong>哪里热就单独扩哪里</strong>"的弹性。这是把前面所有知识<strong>落到地上</strong>的一课。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  部署一套系统，像<strong>选一个住处</strong>。<strong>内嵌单机</strong>（<span class="mono">standalone_embed.sh</span>）像一间<strong>精装单身公寓</strong>：水电网全部内建、拎包即住、几分钟上手——适合一个人（开发、试用）。<strong>docker-compose</strong> 像一套<strong>带独立水电的服务式公寓</strong>：etcd、存储、消息队列都是真正分开的"管线"，但仍同住一栋楼（一台机器）。
  <strong>Kubernetes（Helm / Operator）</strong> 则像一整座<strong>有物业的公寓社区</strong>：每个服务住自己的单元、可以<strong>按需加盖楼层</strong>（独立伸缩），还有一位"<strong>物业管家</strong>"（Operator）替你处理扩容、故障替换、滚动升级。住处的选择，取决于你是"<strong>一个人试住</strong>"还是"<strong>要扛起一座城的流量</strong>"。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong>部署是一道阶梯——内嵌单机(零依赖、本地)→ docker-compose(本地全量)→ k8s 的 Helm Chart / Milvus Operator(生产)；集群模式下各组件可独立伸缩(读扩 QueryNode、写扩 streaming/DataNode)；消息队列(rocksmq/Pulsar/Kafka/Woodpecker)是关键部署决策，它就是第 16/31 课那条 WAL 的后端</strong>。配置(第 40 课)、可观测(第 39 课)、版本协调(第 37 课)在这里合流。
</div>

<h2>从一行命令到一个集群：部署的阶梯</h2>
<p>"怎么把 Milvus 跑起来"没有唯一答案，而是<strong>一道由简到繁的阶梯</strong>，你站在哪一级，取决于你要做什么。最低一级是<strong>内嵌单机</strong>（<span class="inline">scripts/standalone_embed.sh</span>）：它把该有的依赖尽量<strong>内嵌</strong>——连 etcd 都能用嵌入式的（脚本里能看到 <span class="mono">ETCD_USE_EMBED=true</span>）、消息用本地的 rocksmq、数据落本地盘。好处是<strong>几乎零外部依赖、一条命令起一个完整 Milvus</strong>，最适合<strong>学习、本地开发、跑通一个 demo</strong>。</p>
<p>往上一级是 <strong>docker-compose</strong>：把 etcd、对象存储（MinIO）、消息队列（如 Pulsar）作为<strong>真正独立的容器</strong>拉起来，再加上 Milvus 本身。这一级让你在<strong>一台机器</strong>上体验到"<strong>各依赖各司其职</strong>"的真实形态，比内嵌更接近生产、又比 k8s 简单，适合<strong>本地集成测试、小规模试用</strong>。最高一级是 <strong>Kubernetes</strong>，这才是生产的主场：官方提供 <strong>Helm Chart</strong>（一键模板化部署）和 <strong>Milvus Operator</strong>（用一个"运维大脑"声明式地管理整个集群的生命周期——扩缩容、故障自愈、滚动升级）。这道阶梯的设计很贴心：<strong>上手时零负担，认真用时有生产级方案</strong>，你可以随着需求"<strong>逐级往上走</strong>"，而不必一开始就被复杂度劝退。下面把这道阶梯画出来。</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="部署的阶梯：内嵌单机 → docker-compose → k8s 集群，逐级由简到繁；只有到了集群这一级，才能按需独立伸缩——读多写少就多加 QueryNode、写多就加 DataNode/流式、对象存储独立扩容">
    <rect x="18" y="186" width="134" height="48" rx="9" style="fill:var(--panel);stroke:var(--teal);stroke-width:1.5"/><text x="85" y="208" text-anchor="middle" style="fill:var(--teal);font-weight:700">① 内嵌单机</text><text x="85" y="225" text-anchor="middle" style="fill:var(--muted)">零依赖 · 学习</text>
    <line x1="152" y1="200" x2="184" y2="156" style="stroke:var(--accent);stroke-width:2.5"/><path d="M184,156 l-3,11 l9,-3 z" style="fill:var(--accent)"/>
    <rect x="186" y="132" width="146" height="48" rx="9" style="fill:var(--panel);stroke:var(--blue);stroke-width:1.5"/><text x="259" y="154" text-anchor="middle" style="fill:var(--blue);font-weight:700">② docker-compose</text><text x="259" y="171" text-anchor="middle" style="fill:var(--muted)">独立容器 · 测试</text>
    <line x1="332" y1="146" x2="362" y2="102" style="stroke:var(--accent);stroke-width:2.5"/><path d="M362,102 l-3,11 l9,-3 z" style="fill:var(--accent)"/>
    <rect x="364" y="76" width="146" height="48" rx="9" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:2"/><text x="437" y="98" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">③ k8s 集群</text><text x="437" y="115" text-anchor="middle" style="fill:var(--muted)">Helm · Operator</text>
    <line x1="510" y1="100" x2="540" y2="100" style="stroke:var(--accent);stroke-width:2.5"/><path d="M540,100 l-11,-5 l0,10 z" style="fill:var(--accent)"/>
    <text x="626" y="64" text-anchor="middle" style="fill:var(--ink);font-weight:700">集群的回报：按需独立伸缩</text>
    <rect x="514" y="74" width="226" height="46" rx="9" style="fill:var(--teal-soft);stroke:var(--teal);stroke-width:1.5"/><text x="528" y="94" style="fill:var(--teal);font-weight:700">QueryNode ×5</text><text x="528" y="112" style="fill:var(--muted)">读多写少 → 多加这侧</text>
    <rect x="514" y="126" width="226" height="46" rx="9" style="fill:var(--blue-soft);stroke:var(--blue);stroke-width:1.5"/><text x="528" y="146" style="fill:var(--blue);font-weight:700">DataNode / 流式 ×3</text><text x="528" y="164" style="fill:var(--muted)">写多 → 加这一侧</text>
    <rect x="514" y="178" width="226" height="46" rx="9" style="fill:var(--panel);stroke:var(--amber);stroke-width:1.5"/><text x="528" y="198" style="fill:var(--amber);font-weight:700">对象存储 · 独立扩容</text><text x="528" y="216" style="fill:var(--muted)">与计算分离 → 单独加容量</text>
    <text x="255" y="262" text-anchor="middle" style="fill:var(--muted)">逐级往上：上手零负担、认真用有生产级</text>
    <text x="255" y="282" text-anchor="middle" style="fill:var(--muted)">上集群的真正回报 = 哪一环瓶颈就单独给哪一环加机器</text>
  </svg>
  <div class="figcap"><b>从一行命令到一个集群 = 一道部署阶梯</b>：<b>① 内嵌单机</b>（<span class="mono">standalone_embed.sh</span>，嵌入式 etcd + 本地 rocksmq，一命令零依赖，学习/开发）→ <b>② docker-compose</b>（etcd/MinIO/Pulsar 各作独立容器，集成测试）→ <b>③ k8s 集群</b>（Helm 一键、Operator 声明式运维，生产）。上手零负担、认真用有生产级。<b>上集群的真正回报</b>不是"装更多数据"，而是<b>按需独立伸缩</b>：读多写少就多加 <span class="mono">QueryNode</span>、写多就加 <span class="mono">DataNode</span>/流式、对象存储无状态可单独扩容——哪一环瓶颈就给哪一环加机器，把钱花在刀刃上。</div>
</div>

<p>这道阶梯里，最值得多说一句的是 <strong>Milvus Operator</strong>，因为它代表了一种现代的运维范式——<strong>声明式管理</strong>。传统运维是"<strong>命令式</strong>"的：你一条条敲命令告诉系统"先起这个、再扩那个、挂了去重启"。Operator 反过来，是<strong>声明式</strong>的：你只写一份描述"<strong>我想要的最终状态</strong>"的清单（比如"QueryNode 要 5 个、DataNode 要 3 个、用这个版本"），Operator 这个"<strong>运维大脑</strong>"就会<strong>持续地把现实拉向你声明的状态</strong>——少了就补、挂了就换、要升级就一个个滚动替换。这背后是 Kubernetes 的核心思想：<strong>声明期望、由控制器不断校正</strong>。你会发现，这和 Milvus 内部协调器（第 11–13 课）"<strong>盯着期望状态、不断驱动现实向它收敛</strong>"的做法<strong>如出一辙</strong>——只不过一个管的是集群里的段与索引，一个管的是 k8s 里的 Pod 与服务。理解了这层同构，你就明白为什么说 Operator 是"把 Milvus 自己那套协调哲学，搬到了部署层"——<strong>整个系统从里到外，贯穿着同一种"声明期望、自动收敛"的审美</strong>。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>内嵌单机</h4><p><span class="mono">standalone_embed.sh</span>：嵌入式 etcd + 本地 rocksmq + 本地盘，一条命令、零外部依赖。学习/开发首选。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>docker-compose</h4><p>etcd / MinIO / Pulsar 各作独立容器 + Milvus，一台机器上体验真实分工。集成测试/小试用。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Helm Chart</h4><p>k8s 上模板化一键部署，参数可调，各组件以 Pod 形式运行。中大规模。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Milvus Operator</h4><p>声明式“运维大脑”：扩缩容、故障自愈、滚动升级全自动。生产首选。</p></div></div>
</div>

<h2>集群模式的回报：按需独立伸缩</h2>
<p>为什么要费劲上集群模式？因为它兑现了第 3 部分那套"<strong>存算分离、组件解耦</strong>"架构的<strong>核心红利</strong>：<strong>哪一部分成了瓶颈，就单独给哪一部分加机器</strong>，而不必整体放大。这一点，正是 Milvus 把"协调器/工作节点""读路径/写路径"拆得那么开的<strong>终极目的</strong>。</p>
<p>举几个具体场景你就懂了。业务是<strong>读多写少</strong>（典型的检索服务）？那就<strong>多加 QueryNode</strong>，让更多节点并行扛搜索流量，而写入侧的资源原封不动。反过来，正在<strong>灌一大批数据</strong>（离线导入）？那就临时<strong>加强写入/流式与建索引</strong>的算力，读侧不受影响。存储不够了？因为数据在<strong>对象存储</strong>（无状态、可独立扩容），加容量也不牵动计算节点。这种"<strong>按需、局部、独立</strong>"的伸缩，是单机模式给不了的——单机所有角色挤在一个进程里，要扩只能<strong>整体复制</strong>，既浪费又不灵活。所以选择集群模式的<strong>真正理由</strong>，往往不是"能装更多数据"，而是"<strong>能把钱花在刀刃上</strong>"：精准地为真正紧张的那一环扩容。下面用对比看清两种模式各自的取舍。</p>

<p>顺着这个思路，再点破一个常被初学者误解的点：<strong>"上集群"并不总是"更好"，而是"更适合某些场景"</strong>。集群模式带来弹性与容错，但代价也实打实——你要额外运维 etcd、Pulsar、对象存储这一整套外部依赖，要管 k8s、管网络、管一堆 Pod 的健康，整体复杂度<strong>陡增</strong>。对一个数据量不大、流量平稳、团队人手有限的场景，硬上集群往往是<strong>给自己找麻烦</strong>：你为"<strong>可能用得上的弹性</strong>"付出了"<strong>实打实的运维负担</strong>"。所以成熟的判断不是"集群一定比单机强"，而是<strong>按真实需求选型</strong>：先用单机把业务跑顺、把数据规模和流量摸清，<strong>当单机真的扛不住、或对可用性有了硬要求时，再往集群迁</strong>。这种"<strong>不为不需要的复杂度买单</strong>"的克制，和第 40 课"危险配置默认锁死"、第 37 课"GPU 默认不编译"是同一种工程成熟度——<strong>复杂度是有成本的，只在它确实带来价值时才引入</strong>。把这条原则记在心里，你在为 Milvus（乃至任何系统）做部署决策时，就不会被"看起来更高级"的方案牵着走，而会回到那个最朴素的问题：<strong>我的场景，到底需要什么？</strong></p>

<div class="cols">
  <div class="col"><h4>单机 standalone</h4><p>所有角色一个进程，依赖可内嵌。<strong>部署最简、延迟稳定</strong>，但要扩只能整体复制。适合开发、小规模、低运维负担的场景。</p></div>
  <div class="col"><h4>集群 cluster</h4><p>组件分散为独立 Pod，依赖外置(Pulsar/etcd/S3)。<strong>可按需独立伸缩</strong>(读扩 QueryNode、写扩 streaming/DataNode)、容错更强。代价是运维更复杂。生产首选。</p></div>
</div>

<h2>选哪种消息队列：一个关键部署决策</h2>
<p>部署 Milvus 时，有一个决定值得单独拎出来讲：<strong>用哪种消息队列（MQ）</strong>。回忆第 16、31 课——Milvus 的写入是"<strong>先落日志（WAL）</strong>"，而这条<strong>日志的后端</strong>，正是这里说的 MQ。<span class="inline">configs/milvus.yaml</span> 里 <span class="mono">mq.type</span> 支持四种：<strong>rocksmq</strong>（基于 RocksDB、本地嵌入）、<strong>Pulsar</strong>、<strong>Kafka</strong>、<strong>Woodpecker</strong>。</p>
<p>怎么选？官方给了清晰的默认与建议。<strong>单机模式</strong>默认用 <strong>rocksmq</strong>——它本地、轻量、零外部部署，最省心；<strong>集群模式</strong>默认用 <strong>Pulsar</strong>（注意：<strong>rocksmq 在集群模式下不支持</strong>，因为它是本地的、无法被多节点共享）。Kafka 是另一个成熟的集群选项。而对<strong>新部署</strong>，官方明确推荐 <strong>Woodpecker</strong>——它是 Milvus 自研的新一代日志存储，主打"<strong>更好的性能、更简单的运维、更低的成本</strong>"。这个选择之所以"关键"，是因为它直接决定了你的<strong>写入路径架在什么之上</strong>：选本地的 rocksmq 就只能单机；要上集群、要高吞吐写入，就得是 Pulsar/Kafka/Woodpecker 这类<strong>分布式日志</strong>。把这张表记住，部署时就不会在 MQ 上踩坑。</p>

<p>这里还藏着一个值得品味的<strong>架构深意</strong>：为什么 Milvus 要把"写日志"这件如此核心的事，<strong>外包给一个可替换的 MQ</strong>，而不是自己写死一套？答案又回到那条贯穿全书的哲学——<strong>把最难、最该交给专业组件的事，交出去</strong>。"一条全局有序、持久、可重放的日志"听起来简单，真要在分布式环境里做到<strong>高吞吐、不丢、可扩展</strong>，是极难的工程；Pulsar、Kafka 这些系统已经为此打磨了多年。Milvus 把日志后端做成<strong>可插拔</strong>，就既能在单机时用最轻的 rocksmq、又能在生产时换上久经考验的分布式日志，还能在时机成熟时换上自研、更贴合自身需求的 Woodpecker——<strong>同一套写入逻辑，底层日志想换就换</strong>。这种"<strong>对接口编程、把实现做成可替换</strong>"的思路，你在第 22 课（索引交给 Knowhere）、第 39 课（监控接 Prometheus/OTel）都见过，这里是它在<strong>写入路径</strong>上的又一次体现。看懂这一点，你选 MQ 时就不只是"挑个组件"，而是在<strong>为整条写入路径选地基</strong>——地基的吞吐与可靠性，直接决定了你的集群能扛多大的写入洪峰。</p>

<table class="t">
  <tr><th>MQ 类型</th><th>是什么</th><th>适用</th><th>默认/建议</th></tr>
  <tr><td class="mono">rocksmq</td><td>基于 RocksDB 的本地嵌入式日志</td><td>仅单机</td><td>单机默认</td></tr>
  <tr><td class="mono">Pulsar</td><td>成熟的分布式消息系统</td><td>集群</td><td>集群默认</td></tr>
  <tr><td class="mono">Kafka</td><td>成熟的分布式消息系统</td><td>集群</td><td>集群可选</td></tr>
  <tr><td class="mono">Woodpecker</td><td>Milvus 自研新一代日志存储</td><td>单机/集群</td><td>新部署推荐</td></tr>
</table>

<h2>运维三件套合一：配置、可观测、平滑升级</h2>
<p>把第 9 部分串起来，你会发现这几课讲的其实是<strong>同一件事的不同侧面</strong>——怎么让 Milvus 在生产里<strong>跑得稳、看得见、调得动、换得平</strong>。<strong>调得动</strong>，靠第 40 课的配置系统：用 etcd 下发、热更新限流与日志级别，不重启就能应对流量变化。<strong>看得见</strong>，靠第 39 课的可观测性：日志、指标、链路追踪三管齐下，出问题能从全集群里追出那一个请求。<strong>换得平</strong>，靠第 37 课提过的<strong>索引引擎版本协调</strong>（取所有节点的最小版本）以及 Operator 的<strong>滚动升级</strong>：一个节点一个节点地换，新老共存而不中断服务。</p>
<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">计算层</span><span class="name">Milvus 角色（集群模式各自独立伸缩）</span></div><div class="ld">Proxy / 协调器 / QueryNode（读） / streaming·DataNode（写）</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">依赖层</span><span class="name">三根外部支柱</span></div><div class="ld">etcd（一致性/元数据） · 对象存储（数据持久化） · MQ（有序日志 = WAL 后端）</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">部署载体</span><span class="name">从一个进程到一个集群</span></div><div class="ld">内嵌单机 / docker-compose / k8s Pod（Helm · Operator）</div></div>
</div>

<p>这就是把一套分布式向量数据库<strong>真正运营起来</strong>的全貌：<strong>部署</strong>决定它长在什么形态上、<strong>依赖</strong>替它扛住最难的分布式问题（一致性交给 etcd、持久化交给对象存储、有序日志交给 MQ）、<strong>独立伸缩</strong>让你把算力精准投到瓶颈处、<strong>配置与可观测</strong>让你在不停机的前提下看清并调整它。回望整个第 9 部分——从 API 契约、到可观测、到配置、到部署——我们其实走完了"<strong>一个用户/运维者会真正接触到的整张外圈</strong>"。至此，你不仅懂 Milvus 内部怎么运转，也懂了怎么把它用起来、管起来。下一部分（第 10 部分），我们走向最后一程：<strong>实践与贡献</strong>——怎么编译运行、怎么测试、有哪些代码约定，以及如何给 Milvus 提交你的第一个 PR。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>部署阶梯</strong>：内嵌单机(<span class="mono">standalone_embed.sh</span>，零依赖)→ docker-compose(本地全量)→ Helm Chart → Milvus Operator(声明式生产运维)；按需逐级往上。</li>
    <li><strong>集群的回报</strong>：兑现存算分离红利——按需独立伸缩(读扩 QueryNode、写扩 streaming/DataNode、存储在对象存储独立扩)，把算力精准投到瓶颈处。</li>
    <li><strong>MQ 是关键部署决策</strong>：它是 WAL 后端——rocksmq(仅单机/默认)、Pulsar(集群默认)、Kafka(集群可选)、Woodpecker(新部署推荐)；由 <span class="mono">mq.type</span> 选。</li>
    <li><strong>运维合流</strong>：配置(40，热更新)、可观测(39，追一个请求)、版本协调+滚动升级(37/Operator)共同让 Milvus 跑得稳、看得见、调得动、换得平。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Lesson 8 told you what Milvus <strong>depends on</strong> (etcd, object storage, message queue) and what <strong>deployment shapes</strong> exist. As Part 9's finale, this lesson puts on the <strong>ops glasses</strong>: how you actually <strong>run it</strong> — from a one-command embedded single node to a full production Kubernetes cluster; and how Part 3's "<strong>disaggregated architecture</strong>" pays you back at deploy time with the elasticity of "<strong>scale exactly the part that's hot</strong>". This is the lesson that brings everything down to earth.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Deploying a system is like <strong>choosing a place to live</strong>. <strong>Embedded single-node</strong> (<span class="mono">standalone_embed.sh</span>) is a <strong>fully-furnished studio</strong>: utilities all built in, move in instantly, ready in minutes — for one person (dev, trial). <strong>docker-compose</strong> is a <strong>serviced apartment with real separate utilities</strong>: etcd, storage, message queue are genuinely separate "lines", yet still one building (one machine).
  <strong>Kubernetes (Helm / Operator)</strong> is a whole <strong>managed apartment complex</strong>: each service lives in its own unit, you can <strong>add floors on demand</strong> (independent scaling), and a "<strong>property manager</strong>" (the Operator) handles scaling, fault replacement, and rolling upgrades for you. Which home you pick depends on whether you're "<strong>one person trying it out</strong>" or "<strong>carrying a city's worth of traffic</strong>".
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>deployment is a ladder — embedded single-node (zero-dep, local) → docker-compose (local full) → k8s Helm Chart / Milvus Operator (production); in cluster mode components scale independently (scale reads via QueryNode, writes via streaming/DataNode); the message queue (rocksmq/Pulsar/Kafka/Woodpecker) is a key deployment decision — it's the WAL backend of Lessons 16/31</strong>. Config (Lesson 40), observability (Lesson 39), and version coordination (Lesson 37) all converge here.
</div>

<h2>From one command to a cluster: the deployment ladder</h2>
<p>"How to run Milvus" has no single answer — it's a <strong>ladder from simple to elaborate</strong>, and which rung you stand on depends on what you're doing. The lowest rung is <strong>embedded single-node</strong> (<span class="inline">scripts/standalone_embed.sh</span>): it <strong>embeds</strong> the needed dependencies as much as possible — even etcd can be embedded (the script shows <span class="mono">ETCD_USE_EMBED=true</span>), messaging uses local rocksmq, data lands on local disk. The upside is <strong>nearly zero external dependencies — one command starts a complete Milvus</strong> — ideal for <strong>learning, local development, running a demo</strong>.</p>
<p>One rung up is <strong>docker-compose</strong>: bring up etcd, object storage (MinIO), and a message queue (e.g. Pulsar) as <strong>genuinely separate containers</strong>, plus Milvus itself. This rung lets you experience, on <strong>one machine</strong>, the real shape of "<strong>each dependency doing its job</strong>" — closer to production than embedded, simpler than k8s — good for <strong>local integration testing and small trials</strong>. The top rung is <strong>Kubernetes</strong>, the home turf of production: the project offers a <strong>Helm Chart</strong> (one-click templated deploy) and the <strong>Milvus Operator</strong> (an "ops brain" declaratively managing the whole cluster's lifecycle — scaling, self-healing, rolling upgrades). This ladder is considerate by design: <strong>zero burden to start, production-grade when serious</strong>; you can "<strong>climb rung by rung</strong>" as needs grow, rather than being scared off by complexity up front. The ladder, drawn:</p>

<div class="fig">
  <svg viewBox="0 0 760 300" role="img" aria-label="The deployment ladder: embedded single-node → docker-compose → k8s cluster, simple to elaborate; only at the cluster rung can you scale on demand — add QueryNodes for read-heavy, DataNode/streaming for write-heavy, object storage scales on its own">
    <rect x="18" y="186" width="134" height="48" rx="9" style="fill:var(--panel);stroke:var(--teal);stroke-width:1.5"/><text x="85" y="208" text-anchor="middle" style="fill:var(--teal);font-weight:700">① Embedded</text><text x="85" y="225" text-anchor="middle" style="fill:var(--muted)">0 deps · learn</text>
    <line x1="152" y1="200" x2="184" y2="156" style="stroke:var(--accent);stroke-width:2.5"/><path d="M184,156 l-3,11 l9,-3 z" style="fill:var(--accent)"/>
    <rect x="186" y="132" width="146" height="48" rx="9" style="fill:var(--panel);stroke:var(--blue);stroke-width:1.5"/><text x="259" y="154" text-anchor="middle" style="fill:var(--blue);font-weight:700">② docker-compose</text><text x="259" y="171" text-anchor="middle" style="fill:var(--muted)">containers · test</text>
    <line x1="332" y1="146" x2="362" y2="102" style="stroke:var(--accent);stroke-width:2.5"/><path d="M362,102 l-3,11 l9,-3 z" style="fill:var(--accent)"/>
    <rect x="364" y="76" width="146" height="48" rx="9" style="fill:var(--accent-soft);stroke:var(--accent);stroke-width:2"/><text x="437" y="98" text-anchor="middle" style="fill:var(--accent-ink);font-weight:700">③ k8s cluster</text><text x="437" y="115" text-anchor="middle" style="fill:var(--muted)">Helm · Operator</text>
    <line x1="510" y1="100" x2="540" y2="100" style="stroke:var(--accent);stroke-width:2.5"/><path d="M540,100 l-11,-5 l0,10 z" style="fill:var(--accent)"/>
    <text x="626" y="64" text-anchor="middle" style="fill:var(--ink);font-weight:700">Cluster payoff: scale on demand</text>
    <rect x="514" y="74" width="226" height="46" rx="9" style="fill:var(--teal-soft);stroke:var(--teal);stroke-width:1.5"/><text x="528" y="94" style="fill:var(--teal);font-weight:700">QueryNode ×5</text><text x="528" y="112" style="fill:var(--muted)">read-heavy → add here</text>
    <rect x="514" y="126" width="226" height="46" rx="9" style="fill:var(--blue-soft);stroke:var(--blue);stroke-width:1.5"/><text x="528" y="146" style="fill:var(--blue);font-weight:700">DataNode / streaming ×3</text><text x="528" y="164" style="fill:var(--muted)">write-heavy → add here</text>
    <rect x="514" y="178" width="226" height="46" rx="9" style="fill:var(--panel);stroke:var(--amber);stroke-width:1.5"/><text x="528" y="198" style="fill:var(--amber);font-weight:700">object storage · scale</text><text x="528" y="216" style="fill:var(--muted)">compute-decoupled → +capacity</text>
    <text x="255" y="262" text-anchor="middle" style="fill:var(--muted)">climb rung by rung: easy to start, production-grade when serious</text>
    <text x="255" y="282" text-anchor="middle" style="fill:var(--muted)">real payoff = add machines only to the bottlenecked part</text>
  </svg>
  <div class="figcap"><b>From one command to a cluster = a deployment ladder</b>: <b>① embedded single-node</b> (<span class="mono">standalone_embed.sh</span>, embedded etcd + local rocksmq, one command, zero deps — learning/dev) → <b>② docker-compose</b> (etcd/MinIO/Pulsar as separate containers — integration tests) → <b>③ k8s cluster</b> (Helm one-click, Operator declarative ops — production). Zero burden to start, production-grade when serious. The <b>real cluster payoff</b> isn't "hold more data" but <b>scaling on demand</b>: add <span class="mono">QueryNode</span>s for read-heavy, <span class="mono">DataNode</span>/streaming for write-heavy, and object storage (stateless) scales on its own — add machines only where it's the bottleneck, spending where it counts.</div>
</div>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Embedded single-node</h4><p><span class="mono">standalone_embed.sh</span>: embedded etcd + local rocksmq + local disk, one command, zero external deps. Learning/dev first choice.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>docker-compose</h4><p>etcd / MinIO / Pulsar as separate containers + Milvus; experience real division of labor on one machine. Integration tests/small trials.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Helm Chart</h4><p>templated one-click deploy on k8s, tunable params, each component as Pods. Medium/large scale.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Milvus Operator</h4><p>declarative "ops brain": scaling, self-healing, rolling upgrades all automatic. Production first choice.</p></div></div>
</div>

<h2>The cluster payoff: scale independently, on demand</h2>
<p>Why bother with cluster mode? Because it cashes in the <strong>core dividend</strong> of Part 3's "<strong>compute/storage separation, decoupled components</strong>" architecture: <strong>whichever part becomes the bottleneck, add machines to just that part</strong>, without scaling the whole. This is the <strong>ultimate purpose</strong> of why Milvus pulls "coordinators/worker nodes" and "read path/write path" so far apart.</p>
<p>A few concrete scenarios make it click. Workload is <strong>read-heavy, write-light</strong> (a typical search service)? Then <strong>add more QueryNodes</strong> so more nodes carry search traffic in parallel, while the write side stays untouched. Conversely, <strong>bulk-loading a huge dataset</strong> (offline import)? Then temporarily <strong>beef up write/streaming and index-building</strong> compute, leaving reads unaffected. Out of storage? Because data lives in <strong>object storage</strong> (stateless, independently scalable), adding capacity doesn't disturb compute nodes. This "<strong>on-demand, local, independent</strong>" scaling is what single-node can't give — there all roles crowd one process, and to scale you can only <strong>replicate the whole</strong>, wasteful and inflexible. So the <strong>real reason</strong> to choose cluster mode is often not "hold more data" but "<strong>spend money where it counts</strong>": scale precisely the one strained link. The two modes' trade-offs:</p>

<div class="cols">
  <div class="col"><h4>standalone</h4><p>all roles in one process, deps embeddable. <strong>Simplest deploy, stable latency</strong>, but scaling means replicating the whole. For dev, small scale, low ops burden.</p></div>
  <div class="col"><h4>cluster</h4><p>components as separate Pods, deps external (Pulsar/etcd/S3). <strong>Scale independently on demand</strong> (reads via QueryNode, writes via streaming/DataNode), stronger fault tolerance. Costlier to operate. Production choice.</p></div>
</div>

<h2>Which message queue: a key deployment decision</h2>
<p>When deploying Milvus, one decision deserves its own spotlight: <strong>which message queue (MQ)</strong>. Recall Lessons 16 and 31 — Milvus writes by "<strong>logging first (WAL)</strong>", and this <strong>log's backend</strong> is exactly the MQ here. In <span class="inline">configs/milvus.yaml</span>, <span class="mono">mq.type</span> supports four: <strong>rocksmq</strong> (RocksDB-based, local embedded), <strong>Pulsar</strong>, <strong>Kafka</strong>, <strong>Woodpecker</strong>.</p>
<p>How to choose? The project gives clear defaults and advice. <strong>Standalone</strong> defaults to <strong>rocksmq</strong> — local, lightweight, zero external deployment, most carefree; <strong>cluster</strong> defaults to <strong>Pulsar</strong> (note: <strong>rocksmq isn't supported in cluster mode</strong>, being local and unshareable across nodes). Kafka is another mature cluster option. For <strong>new deployments</strong>, the project explicitly recommends <strong>Woodpecker</strong> — Milvus's own next-gen log storage, aiming at "<strong>better performance, simpler ops, lower cost</strong>". This choice is "key" because it directly determines <strong>what your write path stands on</strong>: pick local rocksmq and you're single-node only; for a cluster with high-throughput writes you need a <strong>distributed log</strong> like Pulsar/Kafka/Woodpecker. Memorize this table and you won't trip on the MQ at deploy time.</p>

<table class="t">
  <tr><th>MQ type</th><th>What it is</th><th>For</th><th>Default/advice</th></tr>
  <tr><td class="mono">rocksmq</td><td>RocksDB-based local embedded log</td><td>standalone only</td><td>standalone default</td></tr>
  <tr><td class="mono">Pulsar</td><td>mature distributed messaging system</td><td>cluster</td><td>cluster default</td></tr>
  <tr><td class="mono">Kafka</td><td>mature distributed messaging system</td><td>cluster</td><td>cluster option</td></tr>
  <tr><td class="mono">Woodpecker</td><td>Milvus's own next-gen log storage</td><td>standalone/cluster</td><td>recommended for new</td></tr>
</table>

<h2>Ops trio as one: config, observability, smooth upgrades</h2>
<p>Tie Part 9 together and you'll see these lessons are <strong>different facets of one thing</strong> — how to make Milvus, in production, <strong>run stable, be seen, be tunable, upgrade smoothly</strong>. <strong>Tunable</strong>, via Lesson 40's config system: push via etcd, hot-reload rate limits and log levels, adapting to traffic without restart. <strong>Seen</strong>, via Lesson 39's observability: logs, metrics, traces three-pronged, tracing that one request out of the whole cluster when something breaks. <strong>Smooth upgrades</strong>, via Lesson 37's <strong>index-engine version coordination</strong> (take the minimum version across nodes) plus the Operator's <strong>rolling upgrade</strong>: replace node by node, old and new coexisting without interrupting service.</p>
<div class="layers">
  <div class="layer l-main"><div class="lh"><span class="badge">compute</span><span class="name">Milvus roles (scale independently in cluster mode)</span></div><div class="ld">Proxy / coordinators / QueryNode (reads) / streaming·DataNode (writes)</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">dependencies</span><span class="name">three external pillars</span></div><div class="ld">etcd (consistency/metadata) · object storage (durability) · MQ (ordered log = WAL backend)</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">deploy host</span><span class="name">from one process to a cluster</span></div><div class="ld">embedded single-node / docker-compose / k8s Pods (Helm · Operator)</div></div>
</div>

<p>This is the full picture of truly <strong>operating</strong> a distributed vector database: <strong>deployment</strong> decides what shape it grows into, <strong>dependencies</strong> shoulder the hardest distributed problems for it (consistency to etcd, durability to object storage, ordered logging to the MQ), <strong>independent scaling</strong> lets you pour compute precisely at the bottleneck, and <strong>config + observability</strong> let you see and adjust it without downtime. Looking back over all of Part 9 — from the API contract, to observability, to config, to deployment — we've actually walked "<strong>the entire outer ring a user/operator really touches</strong>". By now you not only understand how Milvus works inside, but how to use and run it. Next (Part 10), the final leg: <strong>practice and contributing</strong> — how to build and run, how to test, what code conventions exist, and how to submit your first PR to Milvus.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Deployment ladder</strong>: embedded single-node (<span class="mono">standalone_embed.sh</span>, zero-dep) → docker-compose (local full) → Helm Chart → Milvus Operator (declarative production ops); climb on demand.</li>
    <li><strong>Cluster payoff</strong>: cashes the compute/storage-separation dividend — scale independently on demand (reads via QueryNode, writes via streaming/DataNode, storage independently in object store), pouring compute precisely at the bottleneck.</li>
    <li><strong>MQ is a key deployment decision</strong>: it's the WAL backend — rocksmq (standalone-only/default), Pulsar (cluster default), Kafka (cluster option), Woodpecker (recommended for new); chosen via <span class="mono">mq.type</span>.</li>
    <li><strong>Ops convergence</strong>: config (40, hot reload), observability (39, trace one request), version coordination + rolling upgrade (37/Operator) together make Milvus run stable, be seen, be tunable, upgrade smoothly.</li>
  </ul>
</div>
""",
}
