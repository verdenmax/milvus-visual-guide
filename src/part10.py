"""Content for Part 10 (Practice &amp; contributing). Lessons 42-46.

Bilingual {"zh","en"} dicts mirroring part1-9. Facts verified against the
Makefile (milvus/build-cpp/build-go/generated-proto/test-go/generate-mockery),
scripts/ (install_deps, start_standalone/cluster, standalone_embed), the test
tags (dynamic,test + gcflags), pkg/util/merr, and PR/DCO conventions.
Lesson 46 is a glossary (soft-exempt from the CJK/diagram floors).
"""

LESSON_42 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
前九部分，你已把 Milvus 从里到外看了个遍。最后一部分（第十部分），我们动手：<strong>怎么从源码把它编出来、跑起来，怎么测试、守哪些约定，又怎么提交你的第一个 PR</strong>。第一课先过最实际的一关——<strong>构建与运行</strong>。这里有个贯穿全书的关键：因为 Milvus 是 <strong>Go + C++ 经 cgo 黏合</strong>（第 2、34 课），它的构建天然是<strong>两段式</strong>的——这一点，决定了你编译它时几乎所有的"为什么"。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  编译一个 Go+C++ 项目，像<strong>组装一台既有金属底盘、又有电子板的设备</strong>。<strong>C++ 内核</strong>是那副<strong>金属底盘</strong>：要先进"<strong>机加工车间</strong>"（cmake + conan 这套 C++ 工具链）把它铸造、打磨出来。<strong>Go 部分</strong>是<strong>电子板</strong>：用它自己的工具链制作，再<strong>螺丝拧到底盘上</strong>（这道"拧合"就是 cgo）。
  顺序<strong>不能颠倒</strong>：没有底盘，电子板没处安装。所以你<strong>不能只 <span class="mono">go build</span></strong>——那等于"光做电子板、没造底盘"，一拧就空。必须先把 C++ 底盘铸好，Go 才能 cgo 链接上去。<span class="mono">make milvus</span> 就是那位<strong>统筹全场的总装师傅</strong>，按正确顺序把两段串起来。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong><span class="mono">make milvus</span> = 先 <span class="mono">build-cpp</span>（cmake/conan 编 C++ 内核，含 <span class="mono">generated-proto</span>）再 <span class="mono">build-go</span>（<span class="mono">CGO_ENABLED=1</span> 的 go build 链接 C++ 库，编出 <span class="mono">cmd/main.go</span>）；产物是<strong>一个 milvus 二进制</strong>，能扮演任意角色；依赖用 <span class="mono">scripts/install_deps.sh</span> 装，运行用 <span class="mono">scripts/start_standalone.sh</span> / <span class="mono">start_cluster.sh</span></strong>。两段式，源于 Go+C++ 的本质。
</div>

<p class="lead" style="font-size:1rem;color:var(--muted)">先别急着敲命令——理解了"为什么是两段"，你才知道每一步在做什么、卡住时该往哪查。下面就从这条最容易踩的坑讲起。</p>

<h2>为什么不能只 go build：两段式构建</h2>
<p>初次想编 Milvus 的人，常会下意识地敲一句 <span class="mono">go build</span>——然后撞一鼻子灰。原因正是第 2、34 课反复讲的：Milvus 的<strong>计算内核是 C++</strong>，Go 那部分要靠 <strong>cgo</strong> 链接到这些 C++ 库才能跑。所以 <span class="mono">go build</span> 单独执行时，找不到那些<strong>还没被编译出来的 C++ 库</strong>，必然失败。正确的姿势是 <span class="mono">make milvus</span>，它在 Makefile 里被定义成一条<strong>有序的流水线</strong>：<span class="mono">milvus: build-cpp print-build-info build-go</span>——<strong>先 C++、后 Go</strong>，次序写死。</p>

<p>为什么"<strong>用 make、而不是直接敲编译命令</strong>"在这种项目里几乎是必须的？因为这条流水线背后藏着一大堆<strong>你不该手动操心的细节</strong>：C++ 库编到哪个目录、Go 这边的 <span class="mono">CGO_LDFLAGS</span> 要指向哪里才能找到它们、要传哪些编译标记、链接哪些系统库、设什么 <span class="mono">RPATH</span> 让运行时找得到动态库……这些参数又长又容易写错。Makefile 把它们<strong>固化成一条可复现的命令</strong>，你只敲 <span class="mono">make milvus</span>，剩下的脏活它替你拼好。这就是<strong>构建系统</strong>存在的意义：把"<strong>怎么正确地把这堆东西编到一起</strong>"这件极易出错的事，沉淀成一份<strong>谁来执行都一样的脚本</strong>。所以当你看到 Milvus（以及几乎所有正经 C/C++/混合项目）都用 Makefile 而非让你裸敲 <span class="mono">go build</span>/<span class="mono">cmake</span>，要明白这不是繁琐，而是<strong>把复杂度收拢到一处、让构建变得可复现</strong>——这与第 40 课"把配置收口到 paramtable"是同一种"<strong>把易错的事统一管起来</strong>"的智慧。</p>
<p>拆开看这两段。<strong>第一段 <span class="mono">build-cpp</span></strong>：用 <strong>cmake + conan</strong>（C++ 的构建与包管理工具）编译 <span class="inline">internal/core</span> 那一整套 C++ 内核（段引擎、索引、执行、mmap……第 8 部分讲的全部），它还依赖 <span class="mono">generated-proto</span>（先把 proto 生成出来）。这一段产出一批 <strong>C++ 静态/动态库</strong>。<strong>第二段 <span class="mono">build-go</span></strong>：开着 <span class="mono">CGO_ENABLED=1</span> 跑 <span class="mono">go build</span>，通过 <span class="mono">CGO_LDFLAGS</span> / <span class="mono">CGO_CFLAGS</span> 把上一段那些 C++ 库<strong>链接进来</strong>，最终编出入口 <span class="inline">cmd/main.go</span>。两段一前一后、由 cgo 在接缝处咬合，缺一不可。这也解释了为什么编 Milvus 要装<strong>两套工具链</strong>：Go 一套、外加 C++ 的 cmake/conan 一套——而纯 Go 项目只需要前者。下面用对比把两段看清。</p>

<p>很多新人第一次构建 Milvus 时会卡在<strong>第一段</strong>——C++ 那部分，因为它要拉取并编译一大堆 C++ 依赖（FAISS/Knowhere、各种数学与存储库……），耗时长、对环境也挑剔。这正是 <span class="mono">conan</span> 这个工具的价值所在：它是 C++ 世界的"包管理器"，负责把这些第三方库<strong>按版本拉下来、编好、管好</strong>，免去你手动一个个 <span class="mono">make install</span> 的折磨。<span class="mono">cmake</span> 则是 C++ 的"构建编排器"，把成百上千个源文件按依赖关系组织、调用编译器产出库。理解这两件工具的分工，你遇到构建报错时就有了方向：是<strong>依赖没拉对</strong>（conan 的事），还是<strong>编译/链接配置不对</strong>（cmake 的事）。顺带提一句，第一段还内嵌了 <span class="mono">generated-proto</span>——也就是第 38 课说的"从 milvus-proto 生成代码"必须先于编译发生，因为 C++ 和 Go 的代码里都要 <span class="mono">#include</span> / import 这些生成出来的 proto 类型。这条<strong>"先生成、再编译"</strong>的依赖顺序，是所有用 protobuf 的项目共同的规矩。</p>

<div class="cols">
  <div class="col"><h4>第一段：build-cpp（C++ 底盘）</h4><p>cmake + conan 编 <span class="inline">internal/core</span>（段引擎/索引/执行/mmap），依赖 <span class="mono">generated-proto</span>。产出 C++ 库。<strong>这一步纯 Go 项目没有。</strong></p></div>
  <div class="col"><h4>第二段：build-go（Go 电子板）</h4><p><span class="mono">CGO_ENABLED=1</span> 的 go build，用 <span class="mono">CGO_LDFLAGS/CFLAGS</span> 链接上一段的 C++ 库，编出 <span class="mono">cmd/main.go</span>。<strong>cgo 在此咬合两段。</strong></p></div>
</div>

<h2>一条命令编出一个二进制：make milvus</h2>
<p>把依赖装齐、两段串好，最终你得到的是<strong>一个</strong>叫 <span class="mono">milvus</span> 的可执行文件——注意，是<strong>一个</strong>，不是十几个。这件事很有意思：Milvus 明明有 Proxy、各协调器、各类节点十几种角色，编出来却<strong>只有一个二进制</strong>。秘密在入口 <span class="inline">cmd/main.go</span>：同一个程序，<strong>靠启动参数决定"这次扮演哪个角色"</strong>。要起一个 Proxy，就用"proxy"角色启动它；要起 QueryNode，就用"querynode"角色启动它。</p>

<div class="flow">
  <div class="node"><div class="nt">milvus 二进制</div><div class="nd">一次编译的唯一产物</div></div>
  <div class="arrow">--role→</div>
  <div class="node hl"><div class="nt">扮演某一角色</div><div class="nd">proxy / 协调器 / querynode / datanode / streamingnode</div></div>
</div>

<p>这种"一个二进制扮演多角色"的玩法，技术上靠的是<strong>启动时的角色分发</strong>：<span class="inline">cmd/main.go</span> 解析命令行（要扮演哪个角色），再去初始化对应组件的服务。你可以把它想成一个<strong>"多面手演员"</strong>：剧本（代码）里写好了所有角色的台词，开演前导演（启动参数）告诉他"今晚演 Proxy"，他就只把 Proxy 那套演出来。这种设计在分布式系统里相当常见，因为它把"<strong>构建产物</strong>"和"<strong>运行角色</strong>"解耦了——<strong>编译期只管产出一个全能二进制，运行期才决定它当什么用</strong>。对比另一种思路（每个角色编一个独立二进制），单二进制的好处在运维上尤其明显：你的镜像仓库里只需要<strong>一个</strong>镜像、升级时只需替换<strong>一个</strong>制品，而不必同步十几个版本号。当然代价是这个二进制会大一些（它包含了所有角色的代码），但对一个反正要靠 cgo 链接整个 C++ 内核的程序来说，这点体积不值一提。理解了"单二进制 + 角色分发"，你再看第 41 课"同一个二进制在不同机器上以不同角色启动"，就会觉得顺理成章。</p>
<p>这种"<strong>一个二进制、多种角色</strong>"的设计，好处不少。<strong>构建简单</strong>：一次编译，到处部署，不必为每种角色单独打包。<strong>版本一致</strong>：所有角色天然同源同版本，杜绝"Proxy 是新版、QueryNode 是旧版"的错配。<strong>部署灵活</strong>：单机模式下，一个进程里就能把所有角色<strong>一起拉起</strong>（这正是第 41 课"内嵌单机"能那么轻的原因之一）；集群模式下，同一个二进制在不同机器上<strong>以不同角色</strong>分别启动。完整的构建流程，从装依赖到产出二进制，串成一条线就是下面这样。</p>

<p>第一次完整编译 Milvus 往往要<strong>等上不短的时间</strong>（C++ 那一大坨依赖与内核，初次编译动辄几十分钟），这很正常，别以为卡住了。好在<strong>增量编译</strong>会快很多：改了 Go 代码只重跑 <span class="mono">build-go</span>、改了 C++ 才需要重编对应的 C++ 部分。一个实用建议是：<strong>日常只改 Go 时，不必每次都从头 <span class="mono">make milvus</span></strong>——C++ 库没变的话，重链接一次 Go 即可，能省下大量等待。也正因为初次构建重，社区才提供了<strong>现成的 docker 镜像</strong>（第 41 课的 compose/Helm 拉的就是它们）：大多数只想"用" Milvus 的人，根本不需要自己编，直接拉镜像跑即可；只有当你要<strong>改它的源码、给它贡献代码</strong>时，才真正需要这条从源码构建的链路。这也顺势点出了第 10 部分的主题转变——从这一课起，我们的身份从"<strong>使用者</strong>"悄悄转向了"<strong>贡献者</strong>"：会从源码构建，是参与一个开源项目的<strong>第一道门槛</strong>，迈过它，你才谈得上改代码、跑测试、提 PR。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>装依赖</h4><p><span class="mono">scripts/install_deps.sh</span>：cmake、conan（C++）、Go 工具链等一次装齐。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>生成 proto</h4><p><span class="mono">make generated-proto</span>：由 milvus-proto 生成各语言/各模块代码。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>编 C++ 内核</h4><p><span class="mono">build-cpp</span>：cmake/conan 编 <span class="inline">internal/core</span>，产出 C++ 库。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>编 Go 并 cgo 链接</h4><p><span class="mono">build-go</span>：CGO 链接 C++ 库，编出唯一的 <span class="mono">milvus</span> 二进制（cmd/main.go）。</p></div></div>
</div>

<h2>把它跑起来：standalone 与 cluster 脚本</h2>
<p>编好了二进制，怎么跑？Milvus 在 <span class="inline">scripts/</span> 下备好了一组启动脚本，对应第 41 课讲的部署形态。最省事的是 <span class="mono">scripts/standalone_embed.sh</span>：<strong>内嵌单机</strong>，连 etcd 都用嵌入式、消息用本地 rocksmq，几乎零外部依赖，一条命令就能起一个完整 Milvus，最适合<strong>本地学习与开发</strong>。想要更接近真实形态，用 <span class="mono">scripts/start_standalone.sh</span>（单机，但依赖独立起）或 <span class="mono">scripts/start_cluster.sh</span>（集群，各组件分别启动）。停的时候用 <span class="mono">scripts/stop_graceful.sh</span>——注意是"<strong>优雅</strong>"停止，让正在进行的写入/刷盘有机会收尾，而不是粗暴杀进程。</p>

<p>这里值得停一下，体会这组脚本背后"<strong>由简到繁、平滑过渡</strong>"的用心。<span class="mono">standalone_embed.sh</span> 把一切都内嵌、藏起复杂度，让你"<strong>几分钟跑起一个能搜的 Milvus</strong>"，先建立信心、把玩起来；当你想看看"真实的它"长什么样，<span class="mono">start_standalone.sh</span> 让依赖（etcd、存储、MQ）变成独立进程，你能亲眼看到第 8 课说的"<strong>三大外部依赖</strong>"真的被一个个拉起；再进一步，<span class="mono">start_cluster.sh</span> 把各组件拆成独立角色分别启动，让你在本地就能<strong>摸到集群的形态</strong>。这条"脚本阶梯"和第 41 课的"部署阶梯"<strong>遥相呼应</strong>——它们都在传递同一个理念：<strong>让新手有最平缓的入口，让进阶者有逐级深入的路径</strong>。一个开源项目是否友好，很大程度就看它有没有把"<strong>第一次跑起来</strong>"这件事做得足够顺。Milvus 在这件事上的用心，本身就是一种值得学习的工程素养。</p>

<table class="t">
  <tr><th>命令</th><th>作用</th></tr>
  <tr><td class="mono">scripts/install_deps.sh</td><td>一次装齐构建依赖（cmake/conan/Go 等）</td></tr>
  <tr><td class="mono">make generated-proto</td><td>由 milvus-proto 重新生成代码</td></tr>
  <tr><td class="mono">make milvus</td><td>两段式编出 CPU 版 <span class="mono">milvus</span> 二进制</td></tr>
  <tr><td class="mono">make milvus-gpu</td><td>编出 GPU 版（第 37 课，链接 CUDA/RAFT）</td></tr>
  <tr><td class="mono">standalone_embed.sh</td><td>零依赖起一个内嵌单机（学习/开发）</td></tr>
  <tr><td class="mono">start_standalone.sh / start_cluster.sh</td><td>起单机（依赖独立）/ 起集群</td></tr>
  <tr><td class="mono">stop_graceful.sh</td><td>优雅停止，让写入/刷盘收尾</td></tr>
</table>

<p>顺带说说"<strong>优雅停止</strong>"为什么值得单独有个脚本，而不是直接 kill。Milvus 运行时，内存里往往攒着<strong>还没刷盘的数据</strong>（growing 段、未落盘的 WAL 消费进度等，第 17 课）。如果粗暴地一刀杀掉进程，这些在途状态可能<strong>来不及妥善收尾</strong>，重启后就得靠日志重放去恢复，既慢又徒增风险。优雅停止则会先<strong>通知各组件"准备打烊"</strong>：把该刷的刷掉、该记的检查点记好、把正在处理的请求做个了断，再退出。这和第 41 课 Operator 的"<strong>滚动升级</strong>"是同一种对生产的体贴——<strong>系统的"关"和"开"一样重要</strong>，草率地关机，常常是诡异数据问题的源头。养成"用 <span class="mono">stop_graceful.sh</span> 而非 kill"的习惯，是把玩具心态升级成生产心态的一小步。</p>
<p>把这一课收束一下：Milvus 的构建之所以"<strong>不只是 go build</strong>"，根子在它 <strong>Go + C++</strong> 的双语本质——你得先用 C++ 工具链铸好内核底盘、再用 Go 经 cgo 拧上来，<span class="mono">make milvus</span> 替你统筹这两段，产出一个能扮演所有角色的二进制，再由启动脚本按你要的形态把它跑起来。理解了这条链，你不仅会编 Milvus，更<strong>真正读懂了"Go+C++ 双语架构"在工程上的代价与回报</strong>——它换来了极致性能，也要求构建多走这一步。下一课，我们看怎么给这套双语系统写测试（尤其是那条"必须带 <span class="mono">-tags dynamic,test</span>"的特殊规矩）。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>两段式构建</strong>：因 Go+C++ 经 cgo 黏合，<span class="mono">make milvus = build-cpp（cmake/conan 编 C++ 内核 + generated-proto）→ build-go（CGO_ENABLED=1 链接 C++ 库）</span>；不能只 <span class="mono">go build</span>。</li>
    <li><strong>两套工具链</strong>：除 Go 外还需 C++ 的 cmake/conan，用 <span class="mono">scripts/install_deps.sh</span> 一次装齐。</li>
    <li><strong>一个二进制、多角色</strong>：产物是单个 <span class="mono">milvus</span>（<span class="inline">cmd/main.go</span>），靠启动参数决定扮演 Proxy/协调器/各节点；构建简单、版本一致、部署灵活。</li>
    <li><strong>运行</strong>：<span class="mono">standalone_embed.sh</span>(零依赖学习) / <span class="mono">start_standalone.sh</span> / <span class="mono">start_cluster.sh</span> 启动，<span class="mono">stop_graceful.sh</span> 优雅停止。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
Across the first nine parts you've seen Milvus inside out. The final part (Part 10) is hands-on: <strong>how to build and run it from source, how to test, what conventions to follow, and how to submit your first PR</strong>. First, the most practical gate — <strong>build and run</strong>. A guide-wide thread matters here: because Milvus is <strong>Go + C++ glued by cgo</strong> (Lessons 2, 34), its build is inherently <strong>two-stage</strong> — and that fact decides almost every "why" of compiling it.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Building a Go+C++ project is like <strong>assembling a device with both a metal chassis and an electronics board</strong>. The <strong>C++ core</strong> is the <strong>metal chassis</strong>: first into the "<strong>machine shop</strong>" (the cmake + conan C++ toolchain) to be cast and machined. The <strong>Go part</strong> is the <strong>electronics board</strong>: made with its own toolchain, then <strong>bolted onto the chassis</strong> (that bolting is cgo).
  The order <strong>can't be reversed</strong>: without a chassis, the board has nowhere to mount. So you <strong>can't just <span class="mono">go build</span></strong> — that's "making the board with no chassis", bolting into thin air. You must forge the C++ chassis first, then Go can cgo-link onto it. <span class="mono">make milvus</span> is the <strong>master assembler</strong> who runs the two stages in the right order.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong><span class="mono">make milvus</span> = first <span class="mono">build-cpp</span> (cmake/conan compiles the C++ core, including <span class="mono">generated-proto</span>) then <span class="mono">build-go</span> (a <span class="mono">CGO_ENABLED=1</span> go build links the C++ libs, compiling <span class="mono">cmd/main.go</span>); the product is <strong>one milvus binary</strong> that can play any role; deps install via <span class="mono">scripts/install_deps.sh</span>, run via <span class="mono">scripts/start_standalone.sh</span> / <span class="mono">start_cluster.sh</span></strong>. Two stages, born of the Go+C++ nature.
</div>

<h2>Why you can't just go build: the two-stage build</h2>
<p>Someone trying to build Milvus for the first time often reflexively types <span class="mono">go build</span> — and hits a wall. The reason is exactly what Lessons 2 and 34 kept stressing: Milvus's <strong>compute core is C++</strong>, and the Go part must <strong>cgo</strong>-link to those C++ libs to run. So a lone <span class="mono">go build</span> can't find the <strong>not-yet-compiled C++ libs</strong> and must fail. The right move is <span class="mono">make milvus</span>, defined in the Makefile as an <strong>ordered pipeline</strong>: <span class="mono">milvus: build-cpp print-build-info build-go</span> — <strong>C++ first, Go second</strong>, the order hard-wired.</p>
<p>Unpack the two stages. <strong>Stage one, <span class="mono">build-cpp</span></strong>: uses <strong>cmake + conan</strong> (C++ build and package tools) to compile the whole C++ core under <span class="inline">internal/core</span> (segment engine, index, exec, mmap… all of Part 8), also depending on <span class="mono">generated-proto</span> (generate the proto first). This stage yields a set of <strong>C++ static/dynamic libs</strong>. <strong>Stage two, <span class="mono">build-go</span></strong>: runs <span class="mono">go build</span> with <span class="mono">CGO_ENABLED=1</span>, <strong>linking in</strong> the previous stage's C++ libs via <span class="mono">CGO_LDFLAGS</span> / <span class="mono">CGO_CFLAGS</span>, finally compiling the entrypoint <span class="inline">cmd/main.go</span>. The two run back-to-back, meshed at the seam by cgo, neither dispensable. This is why building Milvus needs <strong>two toolchains</strong>: Go's, plus C++'s cmake/conan — whereas a pure-Go project needs only the former. The two stages compared:</p>

<div class="cols">
  <div class="col"><h4>Stage 1: build-cpp (C++ chassis)</h4><p>cmake + conan compile <span class="inline">internal/core</span> (segment engine/index/exec/mmap), depending on <span class="mono">generated-proto</span>. Yields C++ libs. <strong>A pure-Go project has no such step.</strong></p></div>
  <div class="col"><h4>Stage 2: build-go (Go board)</h4><p><span class="mono">CGO_ENABLED=1</span> go build, linking the stage-1 C++ libs via <span class="mono">CGO_LDFLAGS/CFLAGS</span>, compiling <span class="mono">cmd/main.go</span>. <strong>cgo meshes the two stages here.</strong></p></div>
</div>

<h2>One command, one binary: make milvus</h2>
<p>With deps installed and the two stages chained, what you finally get is <strong>one</strong> executable named <span class="mono">milvus</span> — note, <strong>one</strong>, not a dozen. This is intriguing: Milvus clearly has a dozen roles (Proxy, coordinators, various nodes), yet compiles to <strong>a single binary</strong>. The secret is the entrypoint <span class="inline">cmd/main.go</span>: the same program <strong>decides "which role to play this time" by launch arguments</strong>. To start a Proxy, launch it in the "proxy" role; for a QueryNode, the "querynode" role.</p>

<div class="flow">
  <div class="node"><div class="nt">milvus binary</div><div class="nd">the one product of a single build</div></div>
  <div class="arrow">--role→</div>
  <div class="node hl"><div class="nt">play one role</div><div class="nd">proxy / coordinator / querynode / datanode / streamingnode</div></div>
</div>
<p>This "<strong>one binary, many roles</strong>" design has real benefits. <strong>Simple builds</strong>: compile once, deploy everywhere, no per-role packaging. <strong>Version consistency</strong>: all roles are inherently same-source, same-version, ruling out "Proxy new, QueryNode old" mismatches. <strong>Flexible deployment</strong>: in standalone mode one process can bring up all roles <strong>together</strong> (a key reason Lesson 41's "embedded single-node" can be so light); in cluster mode the same binary is launched <strong>in different roles</strong> on different machines. The full build flow, from installing deps to producing the binary, as one line:</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Install deps</h4><p><span class="mono">scripts/install_deps.sh</span>: cmake, conan (C++), the Go toolchain, all at once.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Generate proto</h4><p><span class="mono">make generated-proto</span>: generate per-language/per-module code from milvus-proto.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Compile the C++ core</h4><p><span class="mono">build-cpp</span>: cmake/conan compile <span class="inline">internal/core</span>, yielding C++ libs.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Compile Go &amp; cgo-link</h4><p><span class="mono">build-go</span>: CGO links the C++ libs, compiling the single <span class="mono">milvus</span> binary (cmd/main.go).</p></div></div>
</div>

<h2>Run it: standalone and cluster scripts</h2>
<p>Binary built, how to run it? Milvus ships a set of launch scripts under <span class="inline">scripts/</span>, matching Lesson 41's deployment shapes. The easiest is <span class="mono">scripts/standalone_embed.sh</span>: <strong>embedded single-node</strong>, even etcd embedded, messaging via local rocksmq, near-zero external deps — one command starts a complete Milvus, ideal for <strong>local learning and development</strong>. For something closer to the real shape, use <span class="mono">scripts/start_standalone.sh</span> (standalone, but deps started separately) or <span class="mono">scripts/start_cluster.sh</span> (cluster, components launched separately). To stop, use <span class="mono">scripts/stop_graceful.sh</span> — note "<strong>graceful</strong>", letting in-flight writes/flushes finish rather than brutally killing the process.</p>

<table class="t">
  <tr><th>Command</th><th>What it does</th></tr>
  <tr><td class="mono">scripts/install_deps.sh</td><td>install build deps at once (cmake/conan/Go, etc.)</td></tr>
  <tr><td class="mono">make generated-proto</td><td>regenerate code from milvus-proto</td></tr>
  <tr><td class="mono">make milvus</td><td>two-stage build of the CPU <span class="mono">milvus</span> binary</td></tr>
  <tr><td class="mono">make milvus-gpu</td><td>build the GPU variant (Lesson 37, links CUDA/RAFT)</td></tr>
  <tr><td class="mono">standalone_embed.sh</td><td>start a zero-dep embedded single-node (learning/dev)</td></tr>
  <tr><td class="mono">start_standalone.sh / start_cluster.sh</td><td>start standalone (separate deps) / start a cluster</td></tr>
  <tr><td class="mono">stop_graceful.sh</td><td>graceful stop, letting writes/flushes finish</td></tr>
</table>

<p>A word on why "<strong>graceful stop</strong>" deserves its own script rather than a plain kill. While Milvus runs, memory often holds <strong>data not yet flushed</strong> (growing segments, unpersisted WAL consume progress, Lesson 17). Brutally killing the process may leave this in-flight state <strong>without a clean finish</strong>, so a restart must recover via log replay — slower and riskier. A graceful stop first <strong>tells components to "prepare to close"</strong>: flush what should be flushed, record checkpoints, settle in-flight requests, then exit. This is the same production care as Lesson 41's Operator <strong>rolling upgrade</strong> — <strong>how a system shuts down matters as much as how it starts</strong>; careless shutdowns are a frequent source of weird data problems. Building the habit of "<span class="mono">stop_graceful.sh</span>, not kill" is a small step from toy mindset to production mindset.</p>
<p>To wrap up: Milvus's build is "<strong>not just go build</strong>" at root because of its <strong>Go + C++</strong> bilingual nature — you must forge the C++ core chassis first, then bolt Go on via cgo; <span class="mono">make milvus</span> orchestrates both stages into one binary that plays all roles, which launch scripts then run in the shape you want. Grasp this chain and you not only can build Milvus but <strong>truly understand the cost and reward of the "Go+C++ bilingual architecture" in engineering terms</strong> — it buys peak performance and demands this extra build step. Next lesson: how to write tests for this bilingual system (especially the special rule of "must carry <span class="mono">-tags dynamic,test</span>").</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Two-stage build</strong>: because Go+C++ are glued by cgo, <span class="mono">make milvus = build-cpp (cmake/conan compile the C++ core + generated-proto) → build-go (CGO_ENABLED=1 links the C++ libs)</span>; you can't just <span class="mono">go build</span>.</li>
    <li><strong>Two toolchains</strong>: besides Go you need C++'s cmake/conan, installed at once via <span class="mono">scripts/install_deps.sh</span>.</li>
    <li><strong>One binary, many roles</strong>: the product is a single <span class="mono">milvus</span> (<span class="inline">cmd/main.go</span>) that plays Proxy/coordinator/nodes by launch args; simple builds, version consistency, flexible deployment.</li>
    <li><strong>Run</strong>: launch via <span class="mono">standalone_embed.sh</span> (zero-dep learning) / <span class="mono">start_standalone.sh</span> / <span class="mono">start_cluster.sh</span>; stop gracefully via <span class="mono">stop_graceful.sh</span>.</li>
  </ul>
</div>
""",
}

LESSON_43 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
能编出 Milvus 了，下一步是<strong>给它写测试、跑测试</strong>。但你很快会撞到一件怪事：直接 <span class="mono">go test ./...</span> <strong>跑不起来</strong>。原因还是那条主线——Milvus 是 <strong>Go + C++</strong> 的，还用了一种"<strong>运行时给函数打补丁</strong>"的 mock 工具，于是它的测试命令必须带上一串看似神秘的标志：<span class="mono">-tags dynamic,test</span> 和 <span class="mono">-gcflags="all=-N -l"</span>。这一课就把这串"咒语"逐字拆开，让你明白每个标志在防什么坑。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  在 Milvus 里跑测试，像进一间<strong>有特殊规程的实验室</strong>。你不能像逛公园一样直接走进去（<span class="mono">go test</span> 跑不通），得先穿戴<strong>专门的装备</strong>（那串标志）：一张"<strong>dynamic,test 通行证</strong>"（告诉编译器：要动态链接 C++、要带上测试专用代码），外加一条铁规——<strong>"把自动优化关掉"</strong>（<span class="mono">-N -l</span>），好让"质检员"（mockey 工具）能在实验中途<strong>把某个零件偷偷换成假的</strong>来测试。
  少穿一件装备，实验<strong>根本启动不了</strong>，还会报出一堆莫名其妙的错。许多新贡献者第一次跑测试卡住，都栽在<strong>忘了这串装备</strong>上。记住它，你就跨过了 Milvus 测试的第一道门槛。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong>Milvus 的 Go 测试必须带 <span class="mono">-tags dynamic,test</span>（动态链接 C++ + 测试代码）和 <span class="mono">-gcflags="all=-N -l"</span>（关优化/内联，好让 bytedance/mockey 运行时打补丁）；两种 mock——mockery(生成接口假实现，勿手改、用 <span class="mono">make generate-mockery-*</span> 重生成) 与 mockey(运行时给函数打补丁)；跑测试用 <span class="mono">make test-go</span> 或 <span class="mono">make test-proxy</span> 等模块快捷方式</strong>，它们都先编带单测的 C++。
</div>

<p class="lead" style="font-size:1rem;color:var(--muted)">为什么写测试这件"日常小事"，到了 Milvus 这里要单开一课？因为它的"特殊"恰恰浓缩了这个项目的两大基因——<strong>双语（cgo）</strong>与<strong>重度并发</strong>。把测试这关走通，你对这两点的体会会比读十遍架构图都深。</p>

<h2>为什么不能直接 go test：那串神秘标志</h2>
<p>先把"咒语"摆出来。Milvus 跑一个包的测试，真实命令长这样（取自 <span class="inline">scripts/run_go_unittest.sh</span>）：<span class="mono">go test -gcflags="all=-N -l" -race -cover -tags dynamic,test ".../proxy/..." -failfast -count=1 -ldflags="-r ${RPATH}"</span>。一长串，但每一段都<strong>有的放矢</strong>，不是随便堆的。我们逐个拆。</p>

<p>在拆之前，先建立一个意识：这串标志虽长，却<strong>分成三类用途</strong>，看懂分类就不再觉得它杂乱。<strong>第一类是"为了能编译/链接"</strong>——<span class="mono">-tags dynamic,test</span> 与 <span class="mono">-ldflags="-r ${RPATH}"</span>，它们解决"<strong>Go 怎么和 C++ 接上</strong>"这件 cgo 项目独有的事。<strong>第二类是"为了让 mock 能工作"</strong>——就是那条最关键的 <span class="mono">-gcflags="all=-N -l"</span>，专为 mockey 的运行时补丁服务。<strong>第三类是"为了测得严、测得准"</strong>——<span class="mono">-race</span>(查并发竞态)、<span class="mono">-cover</span>(覆盖率)、<span class="mono">-failfast</span>(首错即停)、<span class="mono">-count=1</span>(不走缓存)，这些和任何正经 Go 项目想要的"高质量测试"是一致的。把这串标志按"<strong>链接 / mock / 质量</strong>"三类一归，你不仅记得住，还能在遇到报错时<strong>快速定位是哪一类没配好</strong>：编译链接错往第一类查、mock 打不上往第二类查、用例本身挂往第三类查。下面我们就从最基础的那几个标志说起。</p>
<p><span class="mono">-tags dynamic,test</span> 是两个<strong>构建标签</strong>：<strong>dynamic</strong> 让 Go <strong>动态链接</strong>那套 C++ 内核库（cgo 的需要，和第 42 课构建一脉相承）；<strong>test</strong> 启用只在测试时编进来的代码路径（比如一些测试辅助、桩）。<span class="mono">-race</span> 打开<strong>竞态检测器</strong>——Milvus 满是并发，这能在测试时揪出数据竞争。<span class="mono">-cover</span> 收集<strong>覆盖率</strong>。<span class="mono">-failfast</span> 一旦有用例失败就<strong>立刻停</strong>、不再往下跑；<span class="mono">-count=1</span> 强制<strong>不走测试缓存</strong>，每次都真跑（Go 默认会缓存通过的测试结果）。<span class="mono">-ldflags="-r ${RPATH}"</span> 则把<strong>运行时库搜索路径</strong>写进去，好让测试程序跑起来时<strong>找得到</strong>那些 C++ 动态库。最关键、也最容易被忽略的，是 <span class="mono">-gcflags="all=-N -l"</span>——它单独值得一节。下面这张表把这串标志一次看清。</p>

<p>这里特意点一下 <span class="mono">-race</span>，因为它对 Milvus 这种<strong>重度并发</strong>的系统格外重要。数据竞争（多个 goroutine 同时读写同一块内存、又没加锁）是并发 bug 里<strong>最阴险的一类</strong>：它平时可能<strong>毫无症状</strong>，只在特定时序下偶尔出错，于是在本地怎么都复现不出、一上线就随机崩。<span class="mono">-race</span> 竞态检测器的厉害之处，是它能在测试运行时<strong>实时监测内存访问</strong>，一旦发现"没有同步保护的并发读写"就<strong>当场报警、指出是哪两处代码在打架</strong>——把一个本要靠运气才撞见的偶发 bug，变成测试里<strong>稳定可见</strong>的失败。对一个像 Milvus 这样到处是 goroutine、channel、协调器的系统，把 <span class="mono">-race</span> 设成测试默认项，等于给整个并发肌体装了一台<strong>持续体检仪</strong>。这也提醒你写 Milvus 代码时的一条直觉：<strong>凡是多个 goroutine 会碰到的共享状态，都要想清楚它的同步</strong>——而 <span class="mono">-race</span> 就是那个会无情戳穿你侥幸心理的考官。</p>

<table class="t">
  <tr><th>标志</th><th>作用</th></tr>
  <tr><td class="mono">-tags dynamic,test</td><td>dynamic=动态链接 C++ 内核(cgo)；test=启用测试专用代码</td></tr>
  <tr><td class="mono">-gcflags="all=-N -l"</td><td>关闭优化(-N)与内联(-l)，好让 mockey 能在运行时给函数打补丁</td></tr>
  <tr><td class="mono">-race</td><td>竞态检测器：揪出并发数据竞争</td></tr>
  <tr><td class="mono">-cover</td><td>收集测试覆盖率</td></tr>
  <tr><td class="mono">-failfast -count=1</td><td>首个失败即停；不走测试缓存、每次真跑</td></tr>
  <tr><td class="mono">-ldflags="-r ${RPATH}"</td><td>运行时库搜索路径，让测试找得到 C++ 动态库</td></tr>
</table>

<h2>-gcflags 的玄机：为了让 mockey 能打补丁</h2>
<p>这串标志里，<span class="mono">-gcflags="all=-N -l"</span> 最让新人费解：<strong>关掉编译器优化和内联</strong>，图什么？答案藏在 Milvus 测试用的一个特殊工具——<strong>mockey</strong>（字节跳动开源的 <span class="mono">bytedance/mockey</span>）。它能做一件"黑魔法"：在<strong>运行时，把某个函数的实现"偷梁换柱"</strong>成你指定的假版本（业界叫 monkey-patching，猴子补丁）。这在测试里极有用——比如想测"当某个下游 RPC 失败时本函数怎么处理"，你不必真的搭一个会失败的下游，只要用 mockey 把那个 RPC 函数<strong>临时替换</strong>成"直接返回错误"即可。</p>
<p>但这种"换实现"是<strong>在机器码层面动手术</strong>的：mockey 要找到那个函数的入口、把它跳转到假版本。问题来了——如果编译器做了<strong>内联</strong>（把小函数的代码直接铺进调用处，函数入口就"消失"了）或激进<strong>优化</strong>，mockey 就<strong>找不到那个入口、补丁打不上去</strong>，测试要么编译失败、要么运行时 panic。<span class="mono">-N</span>（关优化）和 <span class="mono">-l</span>（关内联）正是为此而生：它们让每个函数都<strong>老老实实保留一个可被替换的入口</strong>，mockey 才好下手。所以这条标志不是可有可无的调优，而是<strong>mockey 能正常工作的前提</strong>——这也是 Milvus 测试约定里<strong>反复强调"必须带 <span class="mono">-gcflags="all=-N -l"</span>"</strong>的根本原因。忘了它，你的 mockey 测试会以各种诡异方式失败，且报错往往<strong>指不到真正的原因</strong>。</p>

<p>这里值得多想一层：为什么 Milvus 要用 mockey 这种"<strong>动机器码</strong>"的重武器，而不是只靠优雅的接口注入？这恰恰反映了<strong>真实大型项目的无奈与务实</strong>。理想世界里，所有依赖都通过接口注入，测试时换个假实现即可——干净、安全。但现实中，有大量代码<strong>不是这么写的</strong>：包级的工具函数、第三方库里的方法、历史遗留的直接调用……它们没有接口可换，你又不可能为了测试把整个调用链推倒重构。mockey 的运行时补丁，正是为这种"<strong>没法优雅注入</strong>"的场景兜底——它让你能测那些<strong>本来很难测</strong>的代码，代价就是要忍受 <span class="mono">-N -l</span> 这点不便。所以你可以把"两种 mock 并存"读成一种<strong>分层策略</strong>：<strong>能用接口注入(mockery)就优先用，实在注入不了的再上运行时补丁(mockey)</strong>。理解了这层取舍，你写测试时就有了判断：先想"<strong>这个依赖能不能通过接口换掉</strong>"，不能，再请出 mockey。这种"<strong>优雅优先、务实兜底</strong>"的态度，是成熟工程师面对真实代码库时该有的分寸。</p>

<h2>两种 mock：mockery 与 mockey</h2>
<p>上面提到的 mockey，只是 Milvus 测试里<strong>两种 mock 手段之一</strong>。它们名字像、却是<strong>完全不同的两件事</strong>，初学时极易混淆，这里一次讲清。<strong>mockery</strong>（<span class="mono">vektra/mockery</span>）是<strong>编译期</strong>的：它读一个 Go <strong>接口</strong>，自动<strong>生成</strong>一个实现了该接口的"<strong>假对象</strong>"（你可以设定"调用某方法时返回什么"）。这些生成的文件就住在 <span class="inline">internal/mocks</span> 或各处的 <span class="mono">mock_*.go</span> 里。<strong>关键纪律：这些是生成物，不要手改</strong>——要改就改接口、再用 <span class="mono">make generate-mockery-{模块}</span> 重新生成（第 8 部分提过"生成文件别手编"）。</p>
<p><strong>mockey</strong>（<span class="mono">bytedance/mockey</span>）则是<strong>运行时</strong>的：它不依赖接口，而是直接在运行时<strong>替换一个具体函数的实现</strong>（就是上一节那个需要 <span class="mono">-N -l</span> 的猴子补丁）。两者各擅胜场：当被测代码<strong>面向接口编程</strong>（比如依赖一个 <span class="mono">Coordinator</span> 接口），用 mockery 造个假实现注进去最自然；当你要替换的是一个<strong>具体函数/方法</strong>（尤其是包级函数、或不好注入的依赖），mockey 的运行时补丁更灵活。理解了"<strong>接口用 mockery、函数用 mockey</strong>"这条分界，你读 Milvus 测试就不会再被这俩名字绕晕。下面把它们并排。</p>

<p>关于 mockery 那条"<strong>生成物别手改</strong>"的纪律，值得专门强调，因为它是新人最常踩的坑之一。你打开 <span class="inline">internal/mocks</span> 里某个 <span class="mono">mock_*.go</span>，会看到一大片"普通的 Go 代码"，很容易手痒直接改两笔让测试通过。但那是<strong>陷阱</strong>：这些文件由 mockery 根据接口<strong>自动生成</strong>，你的手改一旦下次有人重新生成就会<strong>被无情覆盖</strong>，白费功夫还埋下"代码与接口不一致"的雷。正确姿势是：<strong>改源头</strong>——改接口定义，再 <span class="mono">make generate-mockery-{模块}</span> 让工具重新产出对应的 mock。这和第 8 部分提过的"proto 生成的 .pb.go 别手编"是<strong>同一条铁律</strong>：<strong>凡是"生成物"，就改它的"生成源"，绝不直接改产物</strong>。怎么认出一个文件是生成的？看它顶部通常有一行 <span class="mono">// Code generated ... DO NOT EDIT</span> 的醒目注释。养成"<strong>动手前先看是不是生成文件</strong>"的习惯，能帮你躲掉大量"改了又被覆盖"的无用功——这是参与任何成熟项目都通用的基本素养。</p>

<div class="cols">
  <div class="col"><h4>mockery（编译期 / 接口）</h4><p><span class="mono">vektra/mockery</span> 读接口、<strong>生成</strong>假实现(<span class="inline">internal/mocks</span>、<span class="mono">mock_*.go</span>)。<strong>勿手改</strong>，改接口后 <span class="mono">make generate-mockery-*</span> 重生成。适合面向接口的依赖注入。</p></div>
  <div class="col"><h4>mockey（运行时 / 函数）</h4><p><span class="mono">bytedance/mockey</span> 在运行时<strong>给具体函数打补丁</strong>(monkey-patch)，替换其实现。需 <span class="mono">-gcflags="all=-N -l"</span>。适合替换包级函数、难注入的依赖。</p></div>
</div>

<h2>怎么跑：test-go 与各模块快捷方式</h2>
<p>知道了标志与 mock，实际跑测试反而简单——<strong>别手敲那长串</strong>，用 Makefile 包好的目标即可。跑全部 Go 单测：<span class="mono">make test-go</span>（它会先 <span class="mono">build-cpp-with-unittest</span> 把带单测的 C++ 编出来，再调 <span class="inline">scripts/run_go_unittest.sh</span> 用正确的标志跑）。只想跑某个模块？有一堆快捷方式：<span class="mono">make test-proxy</span>、<span class="mono">make test-querycoord</span>、<span class="mono">make test-datacoord</span>、<span class="mono">make test-rootcoord</span>、<span class="mono">make test-querynode</span>、<span class="mono">make test-datanode</span>……C++ 那边的单测则用 <span class="mono">make test-cpp</span>。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>先编带单测的 C++</h4><p><span class="mono">make test-go</span> 先跑 <span class="mono">build-cpp-with-unittest</span>——Go 测试要 cgo 链接 C++。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>带全套标志跑 go test</h4><p><span class="inline">run_go_unittest.sh</span> 用 <span class="mono">-tags dynamic,test -gcflags="all=-N -l" -race ...</span> 逐包跑。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>mock 就位</h4><p>接口靠 mockery 生成的假实现注入；具体函数靠 mockey 运行时打补丁(故需 -N -l)。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>收集结果</h4><p>-race 报竞态、-cover 出覆盖率、-failfast 首错即停；CI 据此判 PR 能否合入。</p></div></div>
</div>
<p>开发时如果你只想跑<strong>某一个测试函数</strong>，也可以直接用 go test，但<strong>那串标志一个都不能少</strong>：<span class="mono">go test -tags dynamic,test -gcflags="all=-N -l" ./internal/proxy/... -run TestXxx</span>。把这条命令记进肌肉，是给 Milvus 写代码的日常。串起这一课：测试 Milvus 的"特殊"，全都源于它 <strong>Go+C++ + 运行时 mock</strong> 的本质——<span class="mono">dynamic,test</span> 是为 cgo 与测试代码、<span class="mono">-N -l</span> 是为 mockey 打补丁；两种 mock 各管接口与函数；Makefile 把这些复杂度包成 <span class="mono">make test-*</span> 一键搞定。下一课，我们看写代码时要守的那些<strong>约定</strong>——错误处理(merr)、生成文件、import 顺序等，它们是你的代码能被合入的隐形门槛。</p>

<div class="cols">
  <div class="col"><h4>❌ go test ./...</h4><p>缺了那串标志：<strong>找不到还没编的 C++ 库</strong>（dynamic）、<strong>mockey 打不上补丁</strong>（缺 -N -l）→ 编译失败或诡异 panic。</p></div>
  <div class="col"><h4>✅ go test -tags dynamic,test -gcflags="all=-N -l"</h4><p>动态链接 C++ + 启用测试代码 + 保留可替换入口 → mockery/mockey 就位、<strong>测试正常跑</strong>。用 <span class="mono">make test-*</span> 一键带全。</p></div>
</div>

<p>退一步看，Milvus 的测试设定其实给了你一个<strong>极佳的学习抓手</strong>：它把这个项目最硬核的两点——<strong>cgo 双语</strong>与<strong>重度并发</strong>——逼到了你每天都要面对的命令行里。你每敲一次 <span class="mono">-tags dynamic,test</span>，就在复习"它是 Go+C++"；每敲一次 <span class="mono">-race</span>，就在提醒自己"它满是并发、共享状态要小心"；每靠 mockey 打一次补丁，就在体会"真实代码并非都能优雅注入"。所以别把这串标志当成需要死记的麻烦，把它读成 Milvus<strong>性格的速写</strong>——一个为性能而拥抱双语、为正确而严防并发的系统，连它的测试命令都在替它<strong>说出这两条立身之本</strong>。带着这种理解去跑测试，你敲下的就不只是命令，而是对这个系统一次次的<strong>温故</strong>。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>测试咒语</strong>：Go 测试必须带 <span class="mono">-tags dynamic,test</span>（动态链 C++ + 测试代码）和 <span class="mono">-gcflags="all=-N -l"</span>（关优化/内联）；直接 <span class="mono">go test</span> 跑不通。</li>
    <li><strong>-gcflags 为何必需</strong>：<span class="mono">-N -l</span> 让函数保留可替换入口，<strong>mockey 运行时打补丁</strong>才生效；忘了它，mockey 测试会诡异失败。</li>
    <li><strong>两种 mock</strong>：<span class="mono">mockery</span>(编译期生成接口假实现，<strong>勿手改</strong>、<span class="mono">make generate-mockery-*</span> 重生成) vs <span class="mono">mockey</span>(运行时给具体函数打补丁)。</li>
    <li><strong>怎么跑</strong>：<span class="mono">make test-go</span>(全量，先编带单测 C++) 或 <span class="mono">make test-proxy/test-querycoord/…</span> 模块快捷方式；C++ 用 <span class="mono">make test-cpp</span>。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
You can build Milvus; next is to <strong>write and run its tests</strong>. But you'll soon hit something odd: a plain <span class="mono">go test ./...</span> <strong>won't run</strong>. The reason is that same thread — Milvus is <strong>Go + C++</strong>, and it uses a "<strong>patch a function at runtime</strong>" mock tool, so its test command must carry a string of seemingly cryptic flags: <span class="mono">-tags dynamic,test</span> and <span class="mono">-gcflags="all=-N -l"</span>. This lesson unpacks that "incantation" word by word, so you see which pitfall each flag guards against.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Running tests in Milvus is like entering a <strong>lab with special protocols</strong>. You can't just stroll in like a park (<span class="mono">go test</span> won't run); you must don <strong>specific gear</strong> (those flags): a "<strong>dynamic,test pass</strong>" (telling the compiler: link C++ dynamically, include test-only code), plus an iron rule — <strong>"turn off auto-optimization"</strong> (<span class="mono">-N -l</span>) so the "inspectors" (the mockey tool) can <strong>swap a part for a fake mid-experiment</strong>.
  Miss one piece of gear and the experiment <strong>won't even start</strong>, throwing baffling errors. Many new contributors stall on their first test run precisely because they <strong>forgot this gear</strong>. Remember it and you've cleared the first hurdle of Milvus testing.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>Milvus's Go tests must carry <span class="mono">-tags dynamic,test</span> (dynamic-link C++ + test code) and <span class="mono">-gcflags="all=-N -l"</span> (disable optimization/inlining so bytedance/mockey can patch at runtime); two kinds of mocks — mockery (generated interface fakes; don't hand-edit, regenerate via <span class="mono">make generate-mockery-*</span>) and mockey (runtime function patching); run tests via <span class="mono">make test-go</span> or module shortcuts like <span class="mono">make test-proxy</span></strong>, which first build the C++ with unit tests.
</div>

<h2>Why you can't just go test: that string of cryptic flags</h2>
<p>First, the "incantation". To test one package, Milvus's real command looks like this (from <span class="inline">scripts/run_go_unittest.sh</span>): <span class="mono">go test -gcflags="all=-N -l" -race -cover -tags dynamic,test ".../proxy/..." -failfast -count=1 -ldflags="-r ${RPATH}"</span>. A mouthful, but every piece is <strong>purposeful</strong>, not piled on at random. Let's unpack each.</p>
<p><span class="mono">-tags dynamic,test</span> is two <strong>build tags</strong>: <strong>dynamic</strong> makes Go <strong>dynamically link</strong> the C++ core libs (cgo's need, continuous with Lesson 42's build); <strong>test</strong> enables code paths compiled in only for tests (helpers, stubs). <span class="mono">-race</span> turns on the <strong>race detector</strong> — Milvus is full of concurrency, and this catches data races during tests. <span class="mono">-cover</span> collects <strong>coverage</strong>. <span class="mono">-failfast</span> <strong>stops at once</strong> on the first failing case; <span class="mono">-count=1</span> forces <strong>no test caching</strong>, really running each time (Go caches passing results by default). <span class="mono">-ldflags="-r ${RPATH}"</span> bakes in the <strong>runtime library search path</strong> so the test program can <strong>find</strong> those C++ dynamic libs at runtime. The most crucial and most overlooked is <span class="mono">-gcflags="all=-N -l"</span> — it deserves its own section. The table shows the whole string at once.</p>

<table class="t">
  <tr><th>Flag</th><th>What it does</th></tr>
  <tr><td class="mono">-tags dynamic,test</td><td>dynamic=dynamically link the C++ core (cgo); test=enable test-only code</td></tr>
  <tr><td class="mono">-gcflags="all=-N -l"</td><td>disable optimization (-N) and inlining (-l) so mockey can patch functions at runtime</td></tr>
  <tr><td class="mono">-race</td><td>race detector: catch concurrent data races</td></tr>
  <tr><td class="mono">-cover</td><td>collect test coverage</td></tr>
  <tr><td class="mono">-failfast -count=1</td><td>stop at first failure; no test caching, run for real each time</td></tr>
  <tr><td class="mono">-ldflags="-r ${RPATH}"</td><td>runtime library search path so tests find the C++ dynamic libs</td></tr>
</table>

<h2>The -gcflags trick: so mockey can patch</h2>
<p>In this string, <span class="mono">-gcflags="all=-N -l"</span> most puzzles newcomers: <strong>disable the compiler's optimization and inlining</strong> — what for? The answer lies in a special tool Milvus tests use — <strong>mockey</strong> (ByteDance's open-source <span class="mono">bytedance/mockey</span>). It does a "black magic": at <strong>runtime, swap a function's implementation</strong> for a fake you specify (the industry calls it monkey-patching). This is hugely useful in tests — to test "how this function handles a downstream RPC failing", you needn't actually set up a failing downstream; just use mockey to <strong>temporarily replace</strong> that RPC function with "return an error".</p>
<p>But this "swap implementation" is <strong>surgery at the machine-code level</strong>: mockey must find the function's entry and redirect it to the fake. The catch — if the compiler <strong>inlined</strong> it (splicing a small function's code into the call site so its entry "vanishes") or aggressively <strong>optimized</strong>, mockey <strong>can't find the entry and the patch won't land</strong>, so tests either fail to compile or panic at runtime. <span class="mono">-N</span> (no optimization) and <span class="mono">-l</span> (no inlining) exist exactly for this: they keep every function <strong>honestly holding a replaceable entry</strong> for mockey to grab. So this flag isn't optional tuning but a <strong>prerequisite for mockey to work</strong> — the root reason Milvus's testing conventions <strong>keep stressing "must carry <span class="mono">-gcflags="all=-N -l"</span>"</strong>. Forget it and your mockey tests fail in baffling ways, often with errors that <strong>don't point at the real cause</strong>.</p>

<h2>Two kinds of mocks: mockery vs mockey</h2>
<p>The mockey above is just <strong>one of two mocking approaches</strong> in Milvus tests. Their names look alike but they're <strong>completely different things</strong>, easily confused early on, so let's settle it. <strong>mockery</strong> (<span class="mono">vektra/mockery</span>) is <strong>compile-time</strong>: it reads a Go <strong>interface</strong> and auto-<strong>generates</strong> a "<strong>fake object</strong>" implementing it (you set "return this when this method is called"). These generated files live in <span class="inline">internal/mocks</span> or various <span class="mono">mock_*.go</span>. <strong>Key discipline: these are generated — don't hand-edit</strong> — change the interface and regenerate via <span class="mono">make generate-mockery-{module}</span> (Part 8's "don't hand-edit generated files").</p>
<p><strong>mockey</strong> (<span class="mono">bytedance/mockey</span>) is <strong>runtime</strong>: not interface-based, it directly <strong>replaces a concrete function's implementation</strong> at runtime (the monkey-patch needing <span class="mono">-N -l</span> from the last section). Each shines in its place: when the code under test is <strong>interface-oriented</strong> (depends on, say, a <span class="mono">Coordinator</span> interface), injecting a mockery fake is most natural; when you must replace a <strong>concrete function/method</strong> (especially package-level functions or hard-to-inject deps), mockey's runtime patch is more flexible. Grasp "<strong>interfaces use mockery, functions use mockey</strong>" and these two names won't tangle you in Milvus tests. Side by side:</p>

<div class="cols">
  <div class="col"><h4>mockery (compile-time / interface)</h4><p><span class="mono">vektra/mockery</span> reads interfaces and <strong>generates</strong> fakes (<span class="inline">internal/mocks</span>, <span class="mono">mock_*.go</span>). <strong>Don't hand-edit</strong>; after changing the interface, regenerate via <span class="mono">make generate-mockery-*</span>. For interface-oriented dependency injection.</p></div>
  <div class="col"><h4>mockey (runtime / function)</h4><p><span class="mono">bytedance/mockey</span> <strong>patches concrete functions</strong> at runtime (monkey-patch), swapping implementations. Needs <span class="mono">-gcflags="all=-N -l"</span>. For replacing package-level functions and hard-to-inject deps.</p></div>
</div>

<h2>How to run: test-go and module shortcuts</h2>
<p>Knowing the flags and mocks, actually running tests is simple — <strong>don't type that long string</strong>; use the Makefile-wrapped targets. Run all Go unit tests: <span class="mono">make test-go</span> (it first runs <span class="mono">build-cpp-with-unittest</span> to build the C++ with unit tests, then calls <span class="inline">scripts/run_go_unittest.sh</span> with the right flags). Just one module? There's a pile of shortcuts: <span class="mono">make test-proxy</span>, <span class="mono">make test-querycoord</span>, <span class="mono">make test-datacoord</span>, <span class="mono">make test-rootcoord</span>, <span class="mono">make test-querynode</span>, <span class="mono">make test-datanode</span>… The C++ unit tests run via <span class="mono">make test-cpp</span>.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Build C++ with unit tests first</h4><p><span class="mono">make test-go</span> first runs <span class="mono">build-cpp-with-unittest</span> — Go tests must cgo-link C++.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Run go test with the full flags</h4><p><span class="inline">run_go_unittest.sh</span> runs per package with <span class="mono">-tags dynamic,test -gcflags="all=-N -l" -race ...</span>.</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Mocks in place</h4><p>interfaces injected via mockery-generated fakes; concrete functions patched at runtime by mockey (hence -N -l).</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Collect results</h4><p>-race reports races, -cover gives coverage, -failfast stops at first error; CI uses this to gate the PR.</p></div></div>
</div>
<p>During development, to run just <strong>one test function</strong>, you can use go test directly, but <strong>not one of those flags may be missing</strong>: <span class="mono">go test -tags dynamic,test -gcflags="all=-N -l" ./internal/proxy/... -run TestXxx</span>. Committing this to muscle memory is daily life writing Milvus code. To wrap up: the "specialness" of testing Milvus all stems from its <strong>Go+C++ + runtime-mock</strong> nature — <span class="mono">dynamic,test</span> for cgo and test code, <span class="mono">-N -l</span> for mockey's patching; two mock kinds cover interfaces and functions; the Makefile wraps this complexity into one-command <span class="mono">make test-*</span>. Next lesson: the <strong>conventions</strong> to follow when writing code — error handling (merr), generated files, import order — the invisible bar your code must clear to be merged.</p>

<div class="cols">
  <div class="col"><h4>❌ go test ./...</h4><p>missing the flag string: <strong>can't find the not-yet-built C++ libs</strong> (dynamic), <strong>mockey can't patch</strong> (no -N -l) → compile failure or baffling panic.</p></div>
  <div class="col"><h4>✅ go test -tags dynamic,test -gcflags="all=-N -l"</h4><p>dynamic-link C++ + enable test code + keep replaceable entries → mockery/mockey in place, <strong>tests run normally</strong>. <span class="mono">make test-*</span> carries them all.</p></div>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Test incantation</strong>: Go tests must carry <span class="mono">-tags dynamic,test</span> (dynamic-link C++ + test code) and <span class="mono">-gcflags="all=-N -l"</span> (disable optimization/inlining); a plain <span class="mono">go test</span> won't run.</li>
    <li><strong>Why -gcflags is required</strong>: <span class="mono">-N -l</span> keep functions with a replaceable entry so <strong>mockey's runtime patching</strong> works; forget it and mockey tests fail bafflingly.</li>
    <li><strong>Two mocks</strong>: <span class="mono">mockery</span> (compile-time generated interface fakes, <strong>don't hand-edit</strong>, regenerate via <span class="mono">make generate-mockery-*</span>) vs <span class="mono">mockey</span> (runtime patching of concrete functions).</li>
    <li><strong>How to run</strong>: <span class="mono">make test-go</span> (all, first builds C++ with unit tests) or <span class="mono">make test-proxy/test-querycoord/…</span> module shortcuts; C++ via <span class="mono">make test-cpp</span>.</li>
  </ul>
</div>
""",
}

LESSON_44 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
会编、会测了，离"<strong>代码能被合入</strong>"还差一关——<strong>约定</strong>。每个成熟项目都有一套写代码的规矩，Milvus 尤其在意几条：<strong>用 merr 处理错误</strong>（还要分清"谁的错"）、<strong>只用 mlog 打日志</strong>、<strong>import 按固定顺序</strong>、<strong>生成文件别手改</strong>。它们大多由 <strong>linter 自动把关</strong>——违反了，CI 直接拦下你的 PR。这一课带你认全这些"隐形门槛"，其中最有 Milvus 特色的，是 merr 那套<strong>"Input vs System"</strong>的错误哲学。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  团队的代码约定，像一间大工坊的<strong>共用规程</strong>。最要紧的一条，是出问题时<strong>分清"谁的错"</strong>：是<strong>顾客拿来的料本身不对</strong>（<strong>Input 错误</strong>——比如要搜一个不存在的集合），还是<strong>我们的机器自己出故障了</strong>（<strong>System 错误</strong>——比如某节点还没就绪）。这俩的处理<strong>南辕北辙</strong>：前者要<strong>如实告诉顾客"你这儿不对"</strong>、别瞎重试；后者该<strong>自动重试、报警</strong>，因为多半是暂时的。
  除了"分清谁的错"，工坊还有些<strong>整洁规矩</strong>：工具放哪一格（import 顺序）、用哪台官方仪器记录（只用 mlog）、<strong>机器自动盖章的零件别手动重涂</strong>（生成文件别手改）。门口还有位<strong>领班</strong>（linter）逐条查验——不合规，零件根本进不了车间。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong>错误用 <span class="mono">merr</span>（<span class="inline">pkg/util/merr</span>）不用 <span class="mono">fmt.Errorf</span>，且要分 Input(请求内容本身的错、不可重试) vs System(Milvus 自身/暂时性故障、保持可重试)；日志只用 <span class="mono">mlog</span>（<span class="mono">pkg/v3/log</span>、标准 log、裸 zap 都被 linter 禁用）；import 按"标准库 → 第三方 → github.com/milvus-io"由 gci 强制；mocks/proto 等生成文件别手改</strong>。大多数约定由 golangci-lint/gci 机器把关。
</div>

<h2>签名约定：用 merr 处理错误（Input vs System）</h2>
<p>Milvus 最有特色、也最该先掌握的约定，是<strong>错误处理</strong>。规矩第一条：<strong>别用 <span class="mono">fmt.Errorf</span> 造错误，用 <span class="mono">merr</span></strong>（<span class="inline">pkg/util/merr</span>）。merr 里每个错误都带一个<strong>错误码</strong>和<strong>是否可重试</strong>的属性，定义在 <span class="inline">errors.go</span>，形如 <span class="mono">newMilvusError("service not ready", 1, true)</span>——注意最后那个 <span class="mono">true</span>，意思是"这个错<strong>可以重试</strong>"。造错误时用工厂函数，如 <span class="mono">WrapErrServiceNotReady(...)</span>、<span class="mono">WrapErrCollectionNotFound(...)</span>，而不是自己拼字符串。</p>
<p>但 merr 真正的灵魂，是它逼你回答一个问题：<strong>这个错，到底是"谁的错"？</strong>Milvus 把错误分成两大类。<strong>Input 错误</strong>：是<strong>请求内容本身</strong>导致的——用户要搜一个不存在的集合、传了非法参数。这种错<strong>怪用户</strong>，正确做法是<strong>如实返回、别重试</strong>（重试一万次，那个集合还是不存在）。<strong>System 错误</strong>：是 <strong>Milvus 自己</strong>的问题或<strong>暂时性</strong>故障——某个节点还没就绪、一次内部的瞬时竞态。这种错<strong>不怪用户</strong>，而且往往<strong>过一会儿就好了</strong>，所以该<strong>保持可重试</strong>。判断的关键不是"看起来像不像参数校验"，而是那条<strong>归因测试</strong>：<strong>是"请求内容本身"逼出了这个分支，还是一个内部/暂时的失败？</strong>下面把两类摆清。</p>

<p>为什么这条"<strong>谁的错</strong>"的区分，值得被放在所有约定的最前面？因为它触及了一个更深的道理：<strong>一个错误不只是"出了问题"，它还携带着"<strong>该拿它怎么办</strong>"的信息</strong>。在单机小程序里，错误往往就是"打印出来、退出"那么简单；但在 Milvus 这种<strong>分布式</strong>系统里，一个错误会被层层上报、可能触发重试、可能被熔断、最终可能变成给用户的一条提示——它<strong>走过的每一站，都要根据它的"性质"做不同决定</strong>。如果错误本身不带"我是 Input 还是 System"这个标签，那么每一站都得<strong>靠猜</strong>，猜错了就是误重试、误熔断、把内部细节泄露给用户等一连串麻烦。merr 的设计，本质是让错误<strong>自带身份</strong>：错误码标明"是什么错"、可重试标志标明"能不能再试"、Input/System 标明"怪谁"。把这些信息<strong>钉在错误对象上、随它一起传播</strong>，下游各站才能<strong>不靠猜、按标签行事</strong>。理解了这一层，你就明白为什么 Milvus 宁可让你多花心思去给错误"<strong>分类</strong>"，也不允许随手一个 <span class="mono">fmt.Errorf</span> 糊弄过去——<strong>一个没有身份的错误，到了分布式系统里就是一颗定时炸弹</strong>。</p>

<div class="cols">
  <div class="col"><h4>Input 错误（怪请求）</h4><p>请求内容本身导致：搜不存在的集合、非法参数。<strong>如实返回用户、不可重试</strong>(重试也没用)。在 proxy 边界常用 <span class="mono">WrapErrAsInputError(When)</span> 标记。</p></div>
  <div class="col"><h4>System 错误（怪系统/暂时）</h4><p>Milvus 自身 bug 或暂时性故障：节点未就绪、内部瞬时竞态。<strong>保持可重试</strong>(过会儿可能就好)、该报警。是 merr 里很多错误的<strong>默认归类</strong>。</p></div>
</div>

<h2>为什么这条区分如此要紧：它决定了"要不要重试"</h2>
<p>你可能会问：分这么细，图什么？答案是——<strong>错误的归类，直接决定了系统的重试行为，错一点就出大问题</strong>。Milvus 内部很多地方会对失败的操作做<strong>自动重试</strong>（典型如 <span class="mono">retry.Do</span> 包着的调用）。如果一个<strong>本该重试</strong>的暂时性错误（System，比如"节点还没就绪"）被错标成 Input、变得不可重试，那么一次<strong>本来等一下就能成功</strong>的操作，会被<strong>当场判死</strong>、直接失败——明明是虚惊一场，却被你亲手做实了。</p>
<p>反过来更糟：如果一个<strong>注定失败</strong>的 Input 错误（比如"集合不存在"）被错标成可重试的 System 错误，那么系统会<strong>傻乎乎地一遍遍重试</strong>一个永远不会成功的操作，白白消耗资源、还可能拖垮调用方。所以 merr 里你能看到很讲究的设计：像 <span class="mono">ErrCollectionNotFound</span> 默认是 <strong>System 错误</strong>（因为 datacoord 等内部路径在恢复/重试时，需要把"暂时找不到"当作可重试），<strong>只在 proxy 那道面向用户的边界上</strong>，才用 <span class="mono">WrapErrAsInputErrorWhen</span> 把它"翻面"成给用户看的 Input 错误。这种"<strong>同一个错，在内部可重试、到边界才定性为用户错</strong>"的精细，正是 merr 的精髓。还有两条配套铁律要记牢：给已有错误加上下文，<strong>只用 <span class="mono">merr.Wrap/Wrapf</span></strong>（别用 <span class="mono">WrapErrXxxErr(err,…)</span>，那会盖掉里层的错误码）；把某个错误改成 Input 之前，先 grep 一下有没有 <span class="mono">retry.Do</span> 在依赖它的可重试性——<strong>改错一个归类，可能悄悄破坏一条重试链</strong>。</p>

<div class="flow">
  <div class="node"><div class="nt">错误发生</div><div class="nd">某分支返回 err</div></div>
  <div class="arrow">归因测试</div>
  <div class="node"><div class="nt">谁的错？</div><div class="nd">请求本身逼出=Input；内部/暂时=System</div></div>
  <div class="arrow">决定</div>
  <div class="node hl"><div class="nt">retry.Do</div><div class="nd">System→重试(可能成功)；Input→直接返回用户</div></div>
</div>

<p>这里顺带教你一个读 merr 代码时极有用的<strong>观察习惯</strong>：盯住 <span class="inline">errors.go</span> 里每个错误定义末尾那个<strong>布尔值</strong>（可重试与否）和那个<strong>数字码</strong>。可重试标志告诉你这个错"<strong>天生属于哪一类</strong>"——<span class="mono">true</span> 的多半是 System(暂时性、可再试)、<span class="mono">false</span> 的多半是确定性失败。而数字码是<strong>分段</strong>的：相近职责的错误，码也排在相近的<strong>区间</strong>里(你能在文件里看到一段段注释标明哪段归哪类)。这个分段不是装饰——新增错误时，你<strong>必须从对应区间里挑码</strong>，而不能随手拍一个数字，否则会破坏"<strong>码→类别</strong>"的隐含契约，甚至和别处(比如 C++ segcore 那套码)撞车。所以给 Milvus 加一个新错误，正确流程是：先 grep <span class="inline">errors.go</span> 看清现有的分段、找到你这个错该属于的家族区间、再在区间里取一个没用过的码、按 Input/System 设好可重试标志。这套"<strong>先看地图、再落子</strong>"的严谨，正是 merr 想培养你的工程直觉——<strong>错误码不是随便编的，它是一份需要被尊重的契约</strong>。</p>

<h2>其余硬约定：日志、import 顺序、生成文件</h2>
<p>除了 merr，还有几条约定虽不起眼，却同样会卡住你的 PR——好在它们大多被 <strong>linter 自动检查</strong>，你不必死记，违反了会被当场指出。<strong>日志只用 mlog</strong>：第 39 课讲过，Milvus 的 <span class="inline">.golangci.yml</span> 里用 depguard <strong>明令禁止</strong> <span class="mono">pkg/v3/log</span>、标准库 <span class="mono">log</span>、裸 <span class="mono">zap</span>——一律改用 <span class="mono">pkg/v3/mlog</span>，且每条日志带 ctx。<strong>import 顺序</strong>：用 <span class="mono">gci</span> 工具强制成三段——<strong>标准库 → 第三方 → <span class="mono">github.com/milvus-io</span></strong>，本项目的包永远排最后一组；<span class="mono">make</span> 里有 gci fix 帮你自动排好。<strong>生成文件别手改</strong>：mockery 生成的 mock（第 43 课）、proto 生成的 <span class="mono">.pb.go</span>，都要改"源头"再重新生成，别动产物。下面把这些约定连同"谁来把关"列成一张速查表。</p>

<p>你可能会觉得这些约定（import 排序、日志库选择）"<strong>太琐碎了，跟代码对不对有什么关系</strong>"？这是个很自然的疑问，值得正面回答。这些约定单看每一条，确实都是小事；但它们合起来，守护的是一个大东西——<strong>一致性</strong>。想象一个有几百位贡献者的代码库，如果每个人 import 各排各的、日志各用各的库、错误各造各的，那么这份代码读起来就像<strong>几百种口音混在一起的方言</strong>，每读一个新文件都要重新适应作者的个人习惯，认知负担极重。统一约定的价值，正在于<strong>抹平这种个体差异</strong>：当所有人的 import 都按同一顺序、日志都用同一个 mlog、错误都走同一套 merr，整个代码库读起来就像<strong>一个人写的</strong>——你在 A 文件学到的模式，到 B 文件原样适用。这种"<strong>可预期性</strong>"是大型协作的命脉。所以别把约定看成束缚个性的繁文缛节，它恰恰是<strong>让几百人能高效协作</strong>的润滑剂。而把这些约定交给 linter 自动执行，更是高明：它<strong>把"保持一致"这件需要持续自律的苦差，变成了零成本的自动检查</strong>，谁都不用记、谁都赖不掉。这正是成熟开源项目能"<strong>众人拾柴而不乱</strong>"的秘密之一。</p>

<table class="t">
  <tr><th>约定</th><th>规则</th><th>谁把关</th></tr>
  <tr><td>错误处理</td><td>用 <span class="mono">merr</span> 工厂/<span class="mono">Wrap</span>，分 Input/System，别用 <span class="mono">fmt.Errorf</span></td><td>评审 + merr 守护测试</td></tr>
  <tr><td>日志</td><td>只用 <span class="mono">mlog</span>(带 ctx)，禁 log/zap/fmt.Println</td><td>golangci-lint(depguard)</td></tr>
  <tr><td>import 顺序</td><td>标准库 → 第三方 → github.com/milvus-io</td><td>gci</td></tr>
  <tr><td>生成文件</td><td>mocks/.pb.go 改源头重生成，勿手改</td><td>评审 + 重生成无 diff</td></tr>
  <tr><td>配置</td><td>用 paramtable，不裸读文件/环境变量(第 40 课)</td><td>评审</td></tr>
</table>

<h2>大多由机器把关：让 CI 替你查</h2>
<p>把这些约定连起来，你会发现一个让人安心的事实：<strong>它们绝大多数不靠你死记，而靠工具自动执行</strong>。<span class="mono">gci</span> 帮你排好 import、<span class="mono">golangci-lint</span> 帮你抓住"用了禁用的日志库""明显的坏味道"、merr 的守护测试帮你守住错误码契约、CI 还会跑全套 <span class="mono">make test-*</span>。所以提 PR 前的明智做法是：<strong>本地先把这套自查跑一遍</strong>——格式化 import、过一遍 linter、跑相关模块的测试——把问题消灭在推送之前，而不是等 CI 红一片再来回折腾。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>排好 import</h4><p>gci fix 自动把 import 整成"标准库→三方→milvus-io"三段。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>过 linter</h4><p><span class="mono">golangci-lint</span>：抓禁用日志库、坏味道；depguard 守住"只用 mlog"。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>跑相关测试</h4><p><span class="mono">make test-proxy</span> 等：含 merr 守护测试、竞态检测，确认没破坏契约。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>再推送提 PR</h4><p>本地全绿再推，CI 大概率一次过——把来回折腾消灭在推送前。</p></div></div>
</div>
<p>这种"<strong>把约定固化成工具、让机器替人把关</strong>"的做法，本身就是一种值得学习的工程智慧：人会累、会忘、会有分歧，但 linter 不会——它<strong>铁面无私地、对每个人一视同仁地</strong>执行同一套标准。于是整个代码库才能在成百上千贡献者手里，<strong>长期保持一致的风格与质量底线</strong>。回望这一课，merr 的 Input/System 之分教你<strong>严谨地对待错误</strong>、mlog/gci/生成文件之类的硬约定教你<strong>尊重项目的统一规矩</strong>——两者合起来，就是"<strong>让你的代码看起来像 Milvus 原生的一部分</strong>"。做到这点，你的 PR 才算真正<strong>够格被合入</strong>。下一课，我们就走完最后一步：把你的改动<strong>提成一个合规的 PR</strong>（标题格式、DCO 签名、关联 issue 等）。</p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>merr 错误处理</strong>：用 <span class="mono">merr</span> 不用 <span class="mono">fmt.Errorf</span>；分 <strong>Input</strong>(请求本身的错、不可重试) vs <strong>System</strong>(自身/暂时故障、保持可重试)；归因测试看"是不是请求内容逼出该分支"。</li>
    <li><strong>归类决定重试</strong>：错标会让"本可重试"的操作枉死、或让"注定失败"的操作空转；加上下文只用 <span class="mono">merr.Wrap/Wrapf</span>；改 Input 前先 grep <span class="mono">retry.Do</span>。</li>
    <li><strong>硬约定</strong>：日志只用 <span class="mono">mlog</span>(带 ctx，禁 log/zap)；import 顺序 标准→三方→milvus-io(gci)；生成文件(mock/.pb.go)改源头重生成、勿手改。</li>
    <li><strong>机器把关</strong>：golangci-lint/gci/守护测试自动执行这些约定；提 PR 前本地先自查(格式化/lint/测试)，让代码"像 Milvus 原生的一部分"。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
You can build and test; one gate remains before "<strong>your code can be merged</strong>" — <strong>conventions</strong>. Every mature project has coding rules; Milvus especially cares about a few: <strong>handle errors with merr</strong> (and tell "whose fault" it is), <strong>log only via mlog</strong>, <strong>order imports a fixed way</strong>, <strong>don't hand-edit generated files</strong>. Most are <strong>enforced by linters</strong> — violate them and CI rejects your PR. This lesson walks you through these "invisible bars", the most Milvus-flavored being merr's "<strong>Input vs System</strong>" error philosophy.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  A team's code conventions are like a big workshop's <strong>shared protocol</strong>. The most important rule is, when something breaks, <strong>tell "whose fault" it is</strong>: did the <strong>customer bring the wrong materials</strong> (an <strong>Input error</strong> — e.g. searching a nonexistent collection), or did <strong>our own machine malfunction</strong> (a <strong>System error</strong> — e.g. a node not yet ready)? The two are handled <strong>oppositely</strong>: the former you <strong>honestly tell the customer "this is on you"</strong> and don't blindly retry; the latter you <strong>retry automatically and alarm</strong>, since it's usually temporary.
  Beyond "whose fault", the workshop has <strong>tidiness rules</strong>: which slot tools go in (import order), which official instrument to log with (mlog only), and <strong>don't manually repaint machine-stamped parts</strong> (don't hand-edit generated files). At the door a <strong>foreman</strong> (the linter) checks each item — non-compliant parts never enter the shop.
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>errors use <span class="mono">merr</span> (<span class="inline">pkg/util/merr</span>) not <span class="mono">fmt.Errorf</span>, split into Input (the request itself is wrong, not retriable) vs System (Milvus's own/transient failure, stays retriable); logging only via <span class="mono">mlog</span> (<span class="mono">pkg/v3/log</span>, standard log, raw zap are linter-forbidden); imports ordered "stdlib → third-party → github.com/milvus-io" enforced by gci; generated files (mocks/proto) must not be hand-edited</strong>. Most conventions are machine-checked by golangci-lint/gci.
</div>

<h2>The signature convention: handle errors with merr (Input vs System)</h2>
<p>Milvus's most distinctive and first-to-master convention is <strong>error handling</strong>. Rule one: <strong>don't build errors with <span class="mono">fmt.Errorf</span>; use <span class="mono">merr</span></strong> (<span class="inline">pkg/util/merr</span>). In merr, every error carries an <strong>error code</strong> and a <strong>retriable</strong> attribute, defined in <span class="inline">errors.go</span> like <span class="mono">newMilvusError("service not ready", 1, true)</span> — note that trailing <span class="mono">true</span>, meaning "this error <strong>may be retried</strong>". Create errors with factory functions like <span class="mono">WrapErrServiceNotReady(...)</span>, <span class="mono">WrapErrCollectionNotFound(...)</span>, not hand-spliced strings.</p>
<p>But merr's real soul is forcing you to answer: <strong>whose fault is this error?</strong> Milvus splits errors into two classes. <strong>Input errors</strong>: caused by the <strong>request content itself</strong> — searching a nonexistent collection, passing invalid params. These are <strong>the user's fault</strong>, and the right move is to <strong>return faithfully, don't retry</strong> (retry ten thousand times, the collection still doesn't exist). <strong>System errors</strong>: Milvus's <strong>own</strong> problem or a <strong>transient</strong> failure — a node not yet ready, an internal momentary race. These are <strong>not the user's fault</strong> and often <strong>clear up shortly</strong>, so they should <strong>stay retriable</strong>. The key test isn't "does it look like validation" but the <strong>blame test</strong>: <strong>did the request content itself force this branch, or an internal/transient failure?</strong> The two, clarified:</p>

<div class="cols">
  <div class="col"><h4>Input error (blame the request)</h4><p>caused by the request itself: searching a missing collection, invalid params. <strong>Return to the user, not retriable</strong> (retry won't help). At the proxy boundary, often marked via <span class="mono">WrapErrAsInputError(When)</span>.</p></div>
  <div class="col"><h4>System error (blame system/transient)</h4><p>a Milvus bug or transient failure: node not ready, internal momentary race. <strong>Stays retriable</strong> (may clear up soon), should alarm. The <strong>default classification</strong> for many merr errors.</p></div>
</div>

<h2>Why this distinction matters: it decides "to retry or not"</h2>
<p>You might ask: why split so finely? Because — <strong>an error's classification directly decides the system's retry behavior, and getting it slightly wrong causes big problems</strong>. Many places inside Milvus <strong>auto-retry</strong> failed operations (typically calls wrapped in <span class="mono">retry.Do</span>). If a transient error that <strong>should be retried</strong> (System, e.g. "node not ready") is mislabeled Input and becomes non-retriable, then an operation that <strong>would have succeeded after a brief wait</strong> gets <strong>condemned on the spot</strong> and fails outright — a false alarm you turned real with your own hands.</p>
<p>The reverse is worse: if a <strong>doomed</strong> Input error (e.g. "collection doesn't exist") is mislabeled a retriable System error, the system will <strong>foolishly retry over and over</strong> an operation that can never succeed, burning resources and possibly dragging down the caller. So merr has careful designs: <span class="mono">ErrCollectionNotFound</span> defaults to a <strong>System error</strong> (because internal paths in datacoord etc. need to treat "temporarily not found" as retriable during recovery/retry), and <strong>only at the user-facing proxy boundary</strong> is it "flipped" via <span class="mono">WrapErrAsInputErrorWhen</span> into an Input error for the user. This subtlety — "<strong>the same error is retriable internally, classified as user error only at the boundary</strong>" — is the essence of merr. Two companion iron rules to remember: to add context to an existing error, <strong>use only <span class="mono">merr.Wrap/Wrapf</span></strong> (not <span class="mono">WrapErrXxxErr(err,…)</span>, which masks the inner code); before turning an error Input, grep whether any <span class="mono">retry.Do</span> depends on its retriability — <strong>mislabeling one classification can quietly break a retry chain</strong>.</p>

<div class="flow">
  <div class="node"><div class="nt">an error occurs</div><div class="nd">a branch returns err</div></div>
  <div class="arrow">blame test</div>
  <div class="node"><div class="nt">whose fault?</div><div class="nd">request forces it=Input; internal/transient=System</div></div>
  <div class="arrow">decides</div>
  <div class="node hl"><div class="nt">retry.Do</div><div class="nd">System→retry (may succeed); Input→return to user</div></div>
</div>

<h2>Other hard conventions: logging, import order, generated files</h2>
<p>Beyond merr, a few unglamorous conventions can also block your PR — luckily most are <strong>linter-checked</strong>, so you needn't memorize them; violations are flagged on the spot. <strong>Log only via mlog</strong>: as Lesson 39 covered, Milvus's <span class="inline">.golangci.yml</span> uses depguard to <strong>explicitly forbid</strong> <span class="mono">pkg/v3/log</span>, the standard <span class="mono">log</span>, raw <span class="mono">zap</span> — all must become <span class="mono">pkg/v3/mlog</span>, every log carrying ctx. <strong>Import order</strong>: <span class="mono">gci</span> enforces three sections — <strong>stdlib → third-party → <span class="mono">github.com/milvus-io</span></strong>, this project's packages always last; <span class="mono">make</span> has a gci fix to sort them automatically. <strong>Don't hand-edit generated files</strong>: mockery-generated mocks (Lesson 43) and proto-generated <span class="mono">.pb.go</span> must be changed at the "source" and regenerated, not at the artifact. The conventions, with "who enforces", as a cheatsheet:</p>

<table class="t">
  <tr><th>Convention</th><th>Rule</th><th>Enforced by</th></tr>
  <tr><td>error handling</td><td>use <span class="mono">merr</span> factories/<span class="mono">Wrap</span>, split Input/System, no <span class="mono">fmt.Errorf</span></td><td>review + merr guard tests</td></tr>
  <tr><td>logging</td><td>only <span class="mono">mlog</span> (with ctx), no log/zap/fmt.Println</td><td>golangci-lint (depguard)</td></tr>
  <tr><td>import order</td><td>stdlib → third-party → github.com/milvus-io</td><td>gci</td></tr>
  <tr><td>generated files</td><td>mocks/.pb.go: change source and regenerate, don't hand-edit</td><td>review + no-diff regen</td></tr>
  <tr><td>config</td><td>use paramtable, no raw file/env reads (Lesson 40)</td><td>review</td></tr>
</table>

<h2>Mostly machine-enforced: let CI check for you</h2>
<p>Tie these conventions together and you'll find a reassuring fact: <strong>most don't rely on your memory but on tools to enforce</strong>. <span class="mono">gci</span> sorts your imports, <span class="mono">golangci-lint</span> catches "used a forbidden logging library" and "obvious bad smells", merr's guard tests defend the error-code contract, and CI runs the full <span class="mono">make test-*</span>. So the smart move before opening a PR is to <strong>run this self-check locally first</strong> — format imports, pass the linter, run the relevant module's tests — killing problems before pushing, rather than ping-ponging after CI turns red.</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Sort imports</h4><p>gci fix auto-arranges imports into "stdlib→third-party→milvus-io".</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Pass the linter</h4><p><span class="mono">golangci-lint</span>: catch forbidden log libs, bad smells; depguard enforces "mlog only".</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Run relevant tests</h4><p><span class="mono">make test-proxy</span> etc.: incl. merr guard tests, race detection — confirm no contract broken.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Then push the PR</h4><p>push only when locally green; CI likely passes first try — no post-push ping-pong.</p></div></div>
</div>
<p>This practice of "<strong>solidifying conventions into tools, letting machines enforce for humans</strong>" is itself worth learning: people tire, forget, and disagree, but a linter doesn't — it enforces one standard <strong>impartially, identically for everyone</strong>. That's how a codebase, in the hands of hundreds of contributors, can <strong>keep a consistent style and quality floor over the long run</strong>. Looking back over this lesson, merr's Input/System split teaches you to <strong>treat errors rigorously</strong>, while hard conventions like mlog/gci/generated-files teach you to <strong>respect the project's shared rules</strong> — together, they make "<strong>your code look like a native part of Milvus</strong>". Achieve that and your PR is truly <strong>fit to be merged</strong>. Next lesson, the final step: <strong>turn your change into a compliant PR</strong> (title format, DCO sign-off, linked issue, etc.).</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>merr error handling</strong>: use <span class="mono">merr</span> not <span class="mono">fmt.Errorf</span>; split <strong>Input</strong> (request's own fault, not retriable) vs <strong>System</strong> (own/transient failure, stays retriable); the blame test asks "did the request content force this branch".</li>
    <li><strong>Classification decides retry</strong>: mislabeling kills a "retriable" op or spins a "doomed" one; add context only via <span class="mono">merr.Wrap/Wrapf</span>; grep <span class="mono">retry.Do</span> before turning something Input.</li>
    <li><strong>Hard conventions</strong>: log only via <span class="mono">mlog</span> (with ctx, no log/zap); import order stdlib→third-party→milvus-io (gci); generated files (mock/.pb.go) change source and regenerate, don't hand-edit.</li>
    <li><strong>Machine-enforced</strong>: golangci-lint/gci/guard tests auto-enforce; self-check locally before a PR (format/lint/test) to make code "look like a native part of Milvus".</li>
  </ul>
</div>
""",
}

LESSON_45 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
会编、会测、守约定了，只剩最后一步——<strong>把你的改动提成一个 Milvus 会接受的 PR</strong>。这一步有它自己的规矩：<strong>fork-and-pull</strong> 的协作流程、每个 commit 都要的 <strong>DCO 签名</strong>（<span class="mono">-s</span>）、有讲究的 <strong>PR 标题格式</strong>，以及按改动类型而定的 <strong>issue / 设计文档关联</strong>。规矩不少，但一旦走通，你就<strong>从这份指南的"读者"，变成了 Milvus 的"贡献者"</strong>。这一课带你把这最后一公里走完。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比</div>
  提一个 PR，像<strong>向期刊投一篇论文</strong>。你不会直接把草稿塞进主刊（<strong>不能直接 push 到 master</strong>），而是先<strong>誊一份自己的副本</strong>（fork），在副本上改好，再<strong>走正式投稿通道</strong>（提 PR）。投稿得<strong>守格式</strong>（标题按 <span class="mono">type: 描述</span> 写）、<strong>注明出处</strong>（关联对应的 issue / 设计文档）、还得<strong>签字画押</strong>（DCO 签名，声明这代码确实可由你提交）。
  少了任何一样，"<strong>初审机器人</strong>"（Mergify、DCO check、CI）会在<strong>人类评审还没看到之前</strong>就把你退回。这不是刁难——就像期刊的格式审查，是为了让真正宝贵的<strong>人类评审精力</strong>，能专注在"<strong>代码本身好不好</strong>"，而非"<strong>格式对不对</strong>"。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观视角</div>
  一句话：<strong>走 fork-and-pull（fork→加 upstream→开分支→改→<span class="mono">git commit -s</span> 签 DCO→push→提 PR→CI+评审→合入 master）；PR 标题按 <span class="mono">{type}: {描述}</span>（feat/fix/enhance/test/doc/…）；按类型关联 issue 与设计文档（fix 要 issue、feat 要 issue+设计文档）；body 非空</strong>。格式由机器人(DCO/Mergify/CI)先把关，过了才轮到人评审。
</div>

<h2>fork-and-pull：贡献的标准流程</h2>
<p>Milvus（和绝大多数开源项目一样）用 <strong>fork-and-pull</strong> 协作。核心思想是：<strong>你没有官方仓库的写权限，所以你在自己的副本上干活，再请求把成果"拉"回去</strong>。流程是固定的几步。第一步，<strong>fork</strong>：在 GitHub 上把 <span class="mono">milvus-io/milvus</span> 复制一份到你自己的账号下。第二步，<strong>clone 并配 upstream</strong>：把你的 fork 克隆到本地，再把官方仓库加为 <span class="mono">upstream</span> 远程（<span class="mono">git remote add upstream git@github.com:milvus-io/milvus.git</span>），这样你能随时<strong>同步官方最新代码</strong>。</p>

<div class="flow">
  <div class="node"><div class="nt">本地仓库</div><div class="nd">写代码 + commit -s</div></div>
  <div class="arrow">push</div>
  <div class="node"><div class="nt">origin（你的 fork）</div><div class="nd">你有写权限</div></div>
  <div class="arrow">PR</div>
  <div class="node hl"><div class="nt">upstream（官方 master）</div><div class="nd">只能 fetch 同步，不能直接 push</div></div>
</div>

<p>这里把 fork、upstream、origin 这三个容易混的概念<strong>一次理清</strong>，因为很多新人就栽在搞不清"该往哪儿推、从哪儿拉"。<strong>upstream</strong> 指官方仓库 <span class="mono">milvus-io/milvus</span>——它是"<strong>真理之源</strong>"，你<strong>只能从它拉（fetch）、不能往它推</strong>。<strong>origin</strong> 指你自己账号下的那个 fork——它是你的<strong>专属工作区</strong>，你<strong>往它推（push）</strong>自己的分支。<strong>本地仓库</strong>则是你电脑上的克隆，是你真正写代码的地方。一次典型的贡献，数据就这样流动：<strong>从 upstream 拉最新 → 在本地改 → 推到 origin → 从 origin 向 upstream 发 PR</strong>。看清这个三角，你就不会再问"为什么 push 不上去官方仓库"（你本就没权限、也不该直接推），也不会忘了"<strong>开发前先从 upstream 同步</strong>"。把这三者的关系刻进脑子，整个 fork-and-pull 流程就从一串需要死记的命令，变成了一幅<strong>你能自己推导出来的图</strong>——这正是理解胜过记忆的地方。</p>
<p>第三步，<strong>开分支干活</strong>：从最新的 <span class="mono">upstream/master</span> 切出一个<strong>专题分支</strong>（<span class="mono">git checkout upstream/master -b my-topic-branch</span>），在上面改代码、提交。第四步，<strong>同步并推送</strong>：提交前先 <span class="mono">git fetch upstream</span>、必要时 rebase 解决冲突，再 push 到你自己的 fork（origin）。第五步，<strong>提 PR</strong>：在 GitHub 上从你的分支向 <span class="mono">milvus-io/milvus</span> 的 master 发起 Pull Request。之后就是 <strong>CI 自动跑 + 维护者评审</strong>；获得批准后，你的代码就被<strong>合入 master</strong>——恭喜，你成了贡献者。这套"<strong>各自在副本上改、通过 PR 汇聚</strong>"的模式，让成千上万素不相识的人，能在<strong>不互相踩脚</strong>的前提下协作改一个项目。下面把这条主路画出来。</p>

<p>为什么开源世界几乎都采用这种看着有点绕的 fork-and-pull，而不是让大家直接往主仓库推？根子在<strong>权限与信任的现实</strong>。一个像 Milvus 这样的大项目，贡献者成千上万、素昧平生，<strong>不可能给每个人开主仓库的写权限</strong>——那等于把家门钥匙发给所有路人。fork 机制巧妙地化解了这个矛盾：<strong>你对自己的副本有完全的写权限</strong>，可以随便折腾；而要把成果并入官方，则必须经过 PR 这道<strong>受控的关口</strong>，由 CI 和维护者把关。这样既<strong>不挡住任何人参与的自由</strong>，又<strong>守住了主仓库的质量与安全</strong>。配 upstream 远程这一步也别小看：它让你能<strong>持续追上官方的最新进展</strong>，开发前先 <span class="mono">fetch upstream</span>、基于最新 master 开分支，能大大减少日后合并时的冲突。养成"<strong>开工前先同步上游</strong>"的习惯，是顺畅协作的一个小诀窍——你越是基于最新代码开发，你的 PR 就越容易干净地合进去。</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Fork &amp; clone</h4><p>把 <span class="mono">milvus-io/milvus</span> fork 到你的账号，clone 到本地，加 <span class="mono">upstream</span> 远程。</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>开专题分支</h4><p>从 <span class="mono">upstream/master</span> 切出分支，改代码、<span class="mono">git commit -s</span>(带 DCO 签名)。</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>同步 &amp; 推送</h4><p><span class="mono">git fetch upstream</span>、rebase 解冲突，push 到自己的 fork。</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>提 PR → 评审 → 合入</h4><p>向 master 发 PR；DCO/CI 通过 + 维护者批准后合入。</p></div></div>
</div>

<h2>DCO：每个 commit 都要签名（-s）</h2>
<p>有一道几乎所有人第一次提 PR 都会撞上的关卡——<strong>DCO（Developer Certificate of Origin，开发者原创声明）</strong>。规则很简单：你的<strong>每一个 commit</strong> 的提交信息里，都必须有一行 <span class="mono">Signed-off-by: 你的名字 &lt;你的邮箱&gt;</span>。少了它，DCO 检查会<strong>直接把 PR 标红</strong>，不让合入。</p>
<p>你不用手敲那行字——<strong><span class="mono">git commit -s</span></strong> 会<strong>自动</strong>把它附到提交信息末尾（<span class="mono">-s</span> 即 sign-off）。那这行签名到底声明了什么？它是一份<strong>法律意义上的轻量声明</strong>：你确认"<strong>这段代码是我写的、或我有权按本项目的开源许可证提交它</strong>"。开源项目靠它<strong>厘清代码来源、规避版权风险</strong>——毕竟谁都不希望有人把别处的私有代码偷偷塞进来。所以 DCO 不是官僚主义，而是<strong>开源协作的信任基石</strong>。有个常见的坑要提醒：如果你用了 AI 辅助（如本指南用的 Copilot），<strong>真正的 sign-off 必须是"你这位开发者"在最后一行</strong>（<span class="mono">-s</span> 会自动用你的 git 身份），AI 的署名可以另加，但不能顶替你的 DCO。下面对比一下签与没签的差别。</p>

<p>关于补签，再给一个实用提示，因为这是新人最常手忙脚乱的一幕。假如你已经提交了好几个 commit 才发现<strong>忘了 <span class="mono">-s</span></strong>，别慌——DCO 检查报红时通常会附上<strong>修复指引</strong>。常见的补救是用 <span class="mono">git rebase</span> 把历史提交<strong>逐个补上 sign-off</strong>，再 <span class="mono">git push --force</span> 更新你的 PR 分支（因为改写了历史，必须强推）。为了一开始就不踩这个坑，最省心的办法是<strong>把签名变成肌肉记忆</strong>：每次都习惯性地敲 <span class="mono">git commit -s</span>，甚至配置 git 模板让它自动带上。这件小事提醒了一个更大的道理：<strong>开源协作里很多"麻烦"其实是一次性的——你只要把正确姿势养成习惯，之后就再也不会被它绊住</strong>。第一次提 PR 可能要为 DCO、标题格式、关联 issue 来回折腾几遍，但这些都是<strong>"学一次、用一辈子"</strong>的肌肉记忆；走通一遍，第二个 PR 就会顺畅得多。别因为第一次的些许繁琐就退缩——<strong>每个资深贡献者，都是从一个磕磕绊绊的第一次 PR 走过来的</strong>。</p>

<div class="cols">
  <div class="col"><h4>✅ git commit -s（签了）</h4><p>提交信息末尾自动有 <span class="mono">Signed-off-by: 你 &lt;邮箱&gt;</span>。DCO 检查通过，PR 可继续走评审。声明：这代码我有权提交。</p></div>
  <div class="col"><h4>❌ 忘了 -s（没签）</h4><p>提交无 sign-off。DCO 检查<strong>标红、拦下 PR</strong>，必须补签(可 <span class="mono">git rebase</span> 给历史提交补 <span class="mono">-s</span>)才能继续。每个 commit 都要。</p></div>
</div>

<h2>PR 标题与关联：按 type 定规矩</h2>
<p>过了 DCO，还有 PR 本身的<strong>格式规矩</strong>。Milvus 要求 PR 标题写成 <span class="mono">{type}: {描述}</span> 的形式，<strong>type 是固定的几种</strong>：<span class="mono">feat:</span>（新功能）、<span class="mono">fix:</span>（修 bug）、<span class="mono">enhance:</span>（增强/优化）、<span class="mono">test:</span>（测试）、<span class="mono">doc:</span>（文档）、还有 <span class="mono">auto:</span>、<span class="mono">build(deps):</span> 等。这个前缀不只是好看——它让维护者一眼看出<strong>这个改动的性质</strong>，也驱动了后续的<strong>自动化规则</strong>。</p>
<p>最关键的自动化，是按 type 决定<strong>必须关联什么</strong>。<span class="mono">fix:</span> 必须<strong>关联一个 issue</strong>（在 PR body 写 <span class="mono">issue: #123</span>）——因为修 bug 总得说清修的是哪个 bug。<span class="mono">feat:</span> 要求更高：除了 issue，还必须<strong>关联一份设计文档</strong>（放在 <span class="inline">docs/design-docs</span> 下）——新功能得先有设计、再有实现，没有设计文档，Mergify 机器人会贴上 <span class="mono">do-not-merge/missing-design-doc</span> 标签拦着不让合。<span class="mono">enhance:</span> 视改动大小而定（L/XL/XXL 这类大改才强制关联 issue）。<span class="mono">doc:</span> 和 <span class="mono">test:</span> 这类<strong>不涉及功能</strong>的，则不强制关 issue。另外，PR 的 <strong>body 不能为空</strong>；改 2.x 分支的 PR 还要关联对应的 master PR（<span class="mono">pr: #123</span>）。把这些规则记成一张表，提 PR 时照着填就不会被退。</p>

<p>这套"<strong>按 type 定规矩</strong>"的设计，藏着一个很值得体会的协作智慧：<strong>它把人的判断，部分地编码成了机器能执行的规则</strong>。想想看——"新功能必须先有设计文档"本是一条<strong>靠人自觉</strong>的好习惯，但靠自觉就难免有人忘、有人偷懒。Milvus 的做法是：用 PR 标题的 <span class="mono">feat:</span> 前缀做<strong>触发器</strong>，让 Mergify 机器人<strong>自动检查</strong>有没有关联设计文档，没有就<strong>贴标签拦住</strong>。于是"<strong>重要功能要先设计</strong>"这条本来软性的约定，变成了一条<strong>谁都绕不过的硬规则</strong>。这和第 44 课"用 linter 强制代码约定"是<strong>完全一样的思路</strong>——把<strong>重要但容易被忽视的要求，从"靠人记"升级成"靠机器查"</strong>。你在第 10 部分反复看到这种模式：测试用标志固化、约定用 linter 固化、贡献流程用 DCO/Mergify 固化。读懂这条主线，你就明白一个成熟开源项目真正的"<strong>护城河</strong>"不只是代码本身，更是这套<strong>让质量不依赖于个人自觉的自动化机制</strong>。它让项目即使在几千人手里、即使新人不断涌入，也能<strong>稳稳守住底线</strong>。</p>

<table class="t">
  <tr><th>PR 类型</th><th>含义</th><th>必须关联</th></tr>
  <tr><td class="mono">fix:</td><td>修 bug</td><td>issue（<span class="mono">issue: #123</span>）</td></tr>
  <tr><td class="mono">feat:</td><td>新功能</td><td>issue + 设计文档（docs/design-docs）</td></tr>
  <tr><td class="mono">enhance:</td><td>增强/优化</td><td>大改(L/XL/XXL)才需 issue</td></tr>
  <tr><td class="mono">doc: / test:</td><td>文档 / 测试</td><td>不强制关 issue</td></tr>
</table>

<h2>从读者到贡献者：你已经准备好了</h2>
<p>走到这里，请回望你已经拥有的东西。你懂 Milvus 的<strong>宏观架构</strong>（协调器与节点、控制面与数据面）、走过<strong>写入与查询</strong>的完整链路、钻进过 <strong>C++ 内核</strong>看它怎么把"快"做出来、也摸清了 <strong>API、可观测、配置、部署</strong>这层外圈；现在，你还会<strong>编它、测它、按它的约定改它、把改动提成合规的 PR</strong>。这一整套，正是一个<strong>合格贡献者</strong>该有的全貌——你已经准备好了。</p>
<p>提 PR 这件事，最难的从来不是流程，而是<strong>迈出第一步的勇气</strong>。别等"<strong>完全搞懂一切</strong>"才动手——没有人是那样开始的。一个好的起点，往往是从 <span class="mono">good first issue</span> 标签的小问题入手、或修一个文档里的笔误、补一处缺失的测试。流程会因为<strong>第一次走通而变得熟悉</strong>，自信会因为<strong>第一个 PR 被合入而建立</strong>。这份指南的全部内容——四十多课的图、类比、源码、测验——都是为了<strong>把你领到这一步</strong>：让你不再把 Milvus 当成一个高深莫测的黑盒，而是看清它的骨架、读懂它的取舍，并<strong>有底气去改它、去贡献它</strong>。读到这里的你，已经走完了从"<strong>好奇的旁观者</strong>"到"<strong>有准备的贡献者</strong>"的路。剩下的最后一课，是一份<strong>术语表</strong>，供你日后随时回查；术语表之后还有<strong>第 11 部分"进阶专题（选读）"</strong>，收录批量导入、混合检索、配额限流等生产里很重要的进阶话题，等你有需要时再来。而真正的下一步，在 GitHub 上等着你——<strong>去提你的第一个 PR 吧</strong>。</p>

<p>最后留一句话给此刻的你。技术细节会忘、命令会生疏、版本会演进，但这份指南真正想留给你的，不是某条具体的命令，而是一种<strong>面对庞大系统时的底气</strong>——相信任何复杂的东西，都能被<strong>拆成一层层可以理解的结构</strong>；相信再硬核的内核，背后也是一个个<strong>可被讲清的工程取舍</strong>。带着这份底气，你不仅能读懂 Milvus，也能去读懂下一个让你好奇的大系统。开源世界最迷人的地方，正在于它<strong>向每一个愿意动手的人敞开</strong>——你不需要是专家才能开始，你会<strong>因为开始而逐渐成为专家</strong>。这份指南到此即将作结，但你与 Milvus、与开源的故事，才刚刚翻开第一页。<strong>去贡献吧，世界在等你的第一个 PR。</strong></p>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>fork-and-pull</strong>：fork→clone+加 upstream→从 upstream/master 开专题分支→改+提交→fetch/rebase→push 到 fork→向 master 提 PR→CI+评审→合入。</li>
    <li><strong>DCO 签名</strong>：每个 commit 都要 <span class="mono">Signed-off-by</span>，用 <span class="mono">git commit -s</span> 自动加；声明你有权提交这段代码，少了 DCO 检查会拦下 PR。</li>
    <li><strong>PR 标题</strong>：<span class="mono">{type}: {描述}</span>（feat/fix/enhance/test/doc/…）；body 非空。</li>
    <li><strong>按类型关联</strong>：<span class="mono">fix:</span>→issue；<span class="mono">feat:</span>→issue+设计文档(docs/design-docs，否则 Mergify 拦)；<span class="mono">enhance:</span> 大改才需 issue；<span class="mono">doc:/test:</span> 不强制。从 good first issue 起步，迈出第一步。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
You can build, test, and follow conventions — one step remains: <strong>turn your change into a PR Milvus will accept</strong>. This step has its own rules: the <strong>fork-and-pull</strong> workflow, a <strong>DCO sign-off</strong> on every commit (<span class="mono">-s</span>), a careful <strong>PR title format</strong>, and <strong>issue / design-doc links</strong> that depend on the change type. Plenty of rules — but once you clear them, you go <strong>from this guide's "reader" to a Milvus "contributor"</strong>. This lesson walks the last mile.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Filing a PR is like <strong>submitting a paper to a journal</strong>. You don't shove your draft into the main issue (<strong>you can't push straight to master</strong>); you first <strong>make your own copy</strong> (fork), revise on it, then <strong>go through the formal submission channel</strong> (open a PR). The submission must <strong>follow the format</strong> (title as <span class="mono">type: description</span>), <strong>cite its origin</strong> (link the matching issue / design doc), and be <strong>signed</strong> (DCO sign-off, declaring this code is yours to submit).
  Miss any one and the "<strong>desk-review bots</strong>" (Mergify, the DCO check, CI) bounce you back <strong>before a human reviewer ever sees it</strong>. This isn't hazing — like a journal's format check, it's so that precious <strong>human review energy</strong> focuses on "<strong>is the code good</strong>", not "<strong>is the format right</strong>".
</div>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  In one line: <strong>follow fork-and-pull (fork→add upstream→branch→change→<span class="mono">git commit -s</span> to sign DCO→push→open PR→CI+review→merge to master); the PR title is <span class="mono">{type}: {description}</span> (feat/fix/enhance/test/doc/…); link issue and design doc by type (fix needs an issue; feat needs issue+design doc); the body is non-empty</strong>. Bots (DCO/Mergify/CI) gate the format first; only then do humans review.
</div>

<h2>fork-and-pull: the standard contribution flow</h2>
<p>Milvus (like most open-source projects) uses <strong>fork-and-pull</strong>. The core idea: <strong>you don't have write access to the official repo, so you work on your own copy and request to "pull" the result back</strong>. The flow is a fixed few steps. First, <strong>fork</strong>: on GitHub, copy <span class="mono">milvus-io/milvus</span> into your own account. Second, <strong>clone and set upstream</strong>: clone your fork locally, then add the official repo as the <span class="mono">upstream</span> remote (<span class="mono">git remote add upstream git@github.com:milvus-io/milvus.git</span>) so you can always <strong>sync the latest official code</strong>.</p>

<div class="flow">
  <div class="node"><div class="nt">local repo</div><div class="nd">write code + commit -s</div></div>
  <div class="arrow">push</div>
  <div class="node"><div class="nt">origin (your fork)</div><div class="nd">you have write access</div></div>
  <div class="arrow">PR</div>
  <div class="node hl"><div class="nt">upstream (official master)</div><div class="nd">fetch-only to sync, never push directly</div></div>
</div>
<p>Third, <strong>branch and work</strong>: cut a <strong>topic branch</strong> from the latest <span class="mono">upstream/master</span> (<span class="mono">git checkout upstream/master -b my-topic-branch</span>), change code and commit on it. Fourth, <strong>sync and push</strong>: before committing, <span class="mono">git fetch upstream</span>, rebase to resolve conflicts if needed, then push to your own fork (origin). Fifth, <strong>open a PR</strong>: on GitHub, file a Pull Request from your branch to <span class="mono">milvus-io/milvus</span>'s master. Then comes <strong>CI auto-running + maintainer review</strong>; once approved, your code is <strong>merged to master</strong> — congratulations, you're a contributor. This "<strong>everyone revises on a copy, converging via PRs</strong>" model lets thousands of strangers collaborate on one project <strong>without stepping on each other</strong>. The main path, drawn:</p>

<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Fork &amp; clone</h4><p>fork <span class="mono">milvus-io/milvus</span> to your account, clone locally, add the <span class="mono">upstream</span> remote.</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Topic branch</h4><p>cut a branch from <span class="mono">upstream/master</span>, change code, <span class="mono">git commit -s</span> (with DCO sign-off).</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Sync &amp; push</h4><p><span class="mono">git fetch upstream</span>, rebase to resolve conflicts, push to your fork.</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>PR → review → merge</h4><p>file a PR to master; merged after DCO/CI pass + maintainer approval.</p></div></div>
</div>

<h2>DCO: sign off every commit (-s)</h2>
<p>There's a gate nearly everyone hits on their first PR — the <strong>DCO (Developer Certificate of Origin)</strong>. The rule is simple: <strong>every commit</strong> message must contain a line <span class="mono">Signed-off-by: Your Name &lt;your@email&gt;</span>. Miss it and the DCO check <strong>turns the PR red</strong>, blocking the merge.</p>
<p>You needn't type that line — <strong><span class="mono">git commit -s</span></strong> <strong>automatically</strong> appends it to the commit message (<span class="mono">-s</span> = sign-off). What does this line declare? It's a <strong>lightweight legal statement</strong>: you confirm "<strong>this code is mine, or I have the right to submit it under this project's open-source license</strong>". Open-source projects use it to <strong>clarify code provenance and avoid copyright risk</strong> — nobody wants someone sneaking in private code from elsewhere. So DCO isn't bureaucracy but the <strong>trust bedrock of open collaboration</strong>. A common pitfall: if you used AI assistance (like this guide's Copilot), the <strong>actual sign-off must be "you, the developer", on the last line</strong> (<span class="mono">-s</span> uses your git identity automatically); the AI's attribution can be added too, but must not replace your DCO. Signed vs unsigned, compared:</p>

<div class="cols">
  <div class="col"><h4>✅ git commit -s (signed)</h4><p>the message ends with <span class="mono">Signed-off-by: You &lt;email&gt;</span>. The DCO check passes and the PR proceeds to review. Declares: I have the right to submit this code.</p></div>
  <div class="col"><h4>❌ forgot -s (unsigned)</h4><p>the commit has no sign-off. The DCO check <strong>turns red and blocks the PR</strong>; you must add the sign-off (a <span class="mono">git rebase</span> can add <span class="mono">-s</span> to past commits) to continue. Every commit needs it.</p></div>
</div>

<h2>PR title and links: rules by type</h2>
<p>Past DCO, there are the PR's own <strong>format rules</strong>. Milvus requires PR titles as <span class="mono">{type}: {description}</span>, with <strong>a fixed set of types</strong>: <span class="mono">feat:</span> (new feature), <span class="mono">fix:</span> (bug fix), <span class="mono">enhance:</span> (improvement), <span class="mono">test:</span> (tests), <span class="mono">doc:</span> (docs), plus <span class="mono">auto:</span>, <span class="mono">build(deps):</span> and so on. This prefix isn't just cosmetic — it lets maintainers see the <strong>nature of the change</strong> at a glance and drives downstream <strong>automation rules</strong>.</p>
<p>The key automation decides, by type, <strong>what must be linked</strong>. <span class="mono">fix:</span> must <strong>link an issue</strong> (write <span class="mono">issue: #123</span> in the PR body) — a bug fix should say which bug. <span class="mono">feat:</span> demands more: besides an issue, it must <strong>link a design doc</strong> (under <span class="inline">docs/design-docs</span>) — a feature needs a design before an implementation; without the design doc, the Mergify bot slaps a <span class="mono">do-not-merge/missing-design-doc</span> label to block the merge. <span class="mono">enhance:</span> depends on size (only large changes — L/XL/XXL — must link an issue). <span class="mono">doc:</span> and <span class="mono">test:</span>, which <strong>don't touch features</strong>, needn't link an issue. Also, the PR <strong>body must be non-empty</strong>; a PR to a 2.x branch must also link the matching master PR (<span class="mono">pr: #123</span>). Memorize these as a table and fill them in at PR time so you won't be bounced.</p>

<table class="t">
  <tr><th>PR type</th><th>Meaning</th><th>Must link</th></tr>
  <tr><td class="mono">fix:</td><td>bug fix</td><td>issue (<span class="mono">issue: #123</span>)</td></tr>
  <tr><td class="mono">feat:</td><td>new feature</td><td>issue + design doc (docs/design-docs)</td></tr>
  <tr><td class="mono">enhance:</td><td>improvement</td><td>issue only if large (L/XL/XXL)</td></tr>
  <tr><td class="mono">doc: / test:</td><td>docs / tests</td><td>no issue required</td></tr>
</table>

<h2>From reader to contributor: you're ready</h2>
<p>Having come this far, look back at what you now hold. You understand Milvus's <strong>macro architecture</strong> (coordinators and nodes, control vs data plane), have walked the full <strong>write and query</strong> paths, drilled into the <strong>C++ core</strong> to see how "fast" is made, and mapped the outer ring of <strong>API, observability, config, deployment</strong>; now you can also <strong>build it, test it, change it by its conventions, and turn changes into a compliant PR</strong>. That whole set is exactly what a <strong>qualified contributor</strong> has — you're ready.</p>
<p>The hardest part of filing a PR was never the process but the <strong>courage to take the first step</strong>. Don't wait to "<strong>understand everything</strong>" before acting — no one starts that way. A good start is often a small <span class="mono">good first issue</span>, fixing a typo in the docs, or adding a missing test. The process <strong>becomes familiar once you've done it once</strong>; confidence <strong>builds when your first PR is merged</strong>. Everything in this guide — forty-odd lessons of diagrams, analogies, source, and quizzes — was to <strong>bring you to this step</strong>: so you no longer see Milvus as an inscrutable black box, but read its skeleton, grasp its trade-offs, and <strong>have the nerve to change and contribute to it</strong>. Reaching here, you've walked the road from "<strong>a curious bystander</strong>" to "<strong>a prepared contributor</strong>". The last lesson is a <strong>glossary</strong> for future reference; after it comes <strong>Part 11, "Advanced topics (optional)"</strong> — bulk import, hybrid search, quotas and rate-limiting, and other production-important topics, there when you need them. But the real next step waits for you on GitHub — <strong>go file your first PR</strong>.</p>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>fork-and-pull</strong>: fork→clone+add upstream→branch from upstream/master→change+commit→fetch/rebase→push to fork→PR to master→CI+review→merge.</li>
    <li><strong>DCO sign-off</strong>: every commit needs <span class="mono">Signed-off-by</span>, auto-added by <span class="mono">git commit -s</span>; it declares you have the right to submit the code, and a missing one blocks the PR.</li>
    <li><strong>PR title</strong>: <span class="mono">{type}: {description}</span> (feat/fix/enhance/test/doc/…); non-empty body.</li>
    <li><strong>Link by type</strong>: <span class="mono">fix:</span>→issue; <span class="mono">feat:</span>→issue+design doc (docs/design-docs, else Mergify blocks); <span class="mono">enhance:</span>→issue only if large; <span class="mono">doc:/test:</span>→none. Start from a good first issue and take the first step.</li>
  </ul>
</div>
""",
}

LESSON_46 = {
    "zh": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
这是全书的<strong>术语速查表</strong>，把前 45 课出现的关键概念按主题归拢成几张表，每条配一句话定义与所属课次，方便你日后<strong>随时回查</strong>。读不懂某个词时，翻到这里、再顺着课次回到正文细看。
</p>

<h2>一、总览与架构</h2>
<table class="t">
  <tr><th>术语</th><th>一句话定义</th><th>课次</th></tr>
  <tr><td><strong>向量数据库</strong></td><td>以"相似检索(给向量找最近邻 topK)"为核心的数据库，区别于标量库的精确匹配</td><td>第 1 课</td></tr>
  <tr><td><strong>嵌入 / Embedding</strong></td><td>把文本/图片等映射成高维向量，使"语义相近"变成"距离相近"</td><td>第 4 课</td></tr>
  <tr><td><strong>ANN(近似最近邻)</strong></td><td>用少量精度换巨大速度的近邻检索，向量库的算法基石</td><td>第 5 课</td></tr>
  <tr><td><strong>Collection / Partition</strong></td><td>集合=逻辑上的"表"；分区=集合内的数据切分单位</td><td>第 6 课</td></tr>
  <tr><td><strong>段 / Segment</strong></td><td>数据的物理管理单元；growing(可写)→sealed(只读)→建索引</td><td>第 7 课</td></tr>
  <tr><td><strong>控制面 / 数据面</strong></td><td>控制面=协调/调度(Go)；数据面=真正搬运与计算数据</td><td>第 9 课</td></tr>
  <tr><td><strong>协调器 / Coordinator</strong></td><td>管元数据与调度；rootcoord/datacoord/querycoord，可合为 MixCoord</td><td>第 11-13 课</td></tr>
  <tr><td><strong>Proxy</strong></td><td>用户入口/门面：收请求、鉴权、入队、扇出、归并</td><td>第 10 课</td></tr>
  <tr><td><strong>QueryNode / DataNode / StreamingNode</strong></td><td>工作节点：分别负责检索、(压缩等)数据处理、消费 WAL 落盘</td><td>第 10、17 课</td></tr>
</table>

<h2>二、写入路径</h2>
<table class="t">
  <tr><th>术语</th><th>一句话定义</th><th>课次</th></tr>
  <tr><td><strong>WAL(预写日志)</strong></td><td>先把变更写成有序日志、再异步落盘；崩溃靠重放恢复</td><td>第 16、31 课</td></tr>
  <tr><td><strong>TimeTick / TSO</strong></td><td>全局有序的时间戳(由 TSO 单源发号)，定义"谁先谁后"</td><td>第 16、30 课</td></tr>
  <tr><td><strong>Flush / Binlog</strong></td><td>把内存中的段刷成磁盘上的列式 binlog 文件(落对象存储)</td><td>第 17、18 课</td></tr>
  <tr><td><strong>Compaction(压缩)</strong></td><td>把小段/碎片合并、清理已删数据；Mix/Merge/Clustering/L0 等</td><td>第 19 课</td></tr>
  <tr><td><strong>Delete / 布隆过滤器</strong></td><td>删除按主键标记;PrimaryKeyStats 的 bloom filter 加速"这段有没有它"</td><td>第 20 课</td></tr>
</table>

<h2>三、查询路径</h2>
<table class="t">
  <tr><th>术语</th><th>一句话定义</th><th>课次</th></tr>
  <tr><td><strong>topK</strong></td><td>一次搜索返回距离最近的 K 条结果</td><td>第 25 课</td></tr>
  <tr><td><strong>Delegator(委托者)</strong></td><td>QueryNode 上的协调者：扇出到各段、再归并段内 topK</td><td>第 26 课</td></tr>
  <tr><td><strong>三级 Reduce</strong></td><td>topK 结果的三层归并:段内→节点(delegator)→Proxy</td><td>第 29 课</td></tr>
  <tr><td><strong>一致性级别</strong></td><td>Strong/Bounded/Session/Eventually/Customized，新鲜度 vs 性能的取舍</td><td>第 30 课</td></tr>
  <tr><td><strong>保证时间戳</strong></td><td>由一致性级别推出的 GuaranteeTs，决定"至少要看到多新的数据"</td><td>第 30 课</td></tr>
  <tr><td><strong>先过滤再检索</strong></td><td>标量过滤产出 bitset，向量检索只在通过者上做</td><td>第 28 课</td></tr>
</table>

<h2>四、索引</h2>
<table class="t">
  <tr><th>术语</th><th>一句话定义</th><th>课次</th></tr>
  <tr><td><strong>HNSW</strong></td><td>分层可导航小世界图索引;在邻居图上贪心走近邻</td><td>第 5、22 课</td></tr>
  <tr><td><strong>IVF</strong></td><td>倒排+聚类:先定位候选簇、再簇内精算</td><td>第 5、22 课</td></tr>
  <tr><td><strong>DiskANN / PQ</strong></td><td>磁盘友好的图索引 / 乘积量化压缩(省内存、略损精度)</td><td>第 5、22 课</td></tr>
  <tr><td><strong>Knowhere</strong></td><td>Milvus 统一的向量索引引擎中台(封装 FAISS 等),CPU/GPU 索引都经它</td><td>第 22 课</td></tr>
  <tr><td><strong>标量 / 全文索引</strong></td><td>给标量字段(过滤)与文本(BM25,基于 Rust 的 tantivy)建索引</td><td>第 24 课</td></tr>
  <tr><td><strong>GPU 索引(CAGRA 等)</strong></td><td>类型在 Milvus、算法在 Knowhere/RAFT;编译期 milvus-gpu</td><td>第 37 课</td></tr>
</table>

<h2>五、C++ 内核</h2>
<table class="t">
  <tr><th>术语</th><th>一句话定义</th><th>课次</th></tr>
  <tr><td><strong>cgo</strong></td><td>Go 与 C++ 之间的 C-ABI 桥(*_c.h);粗粒度调用、数据零拷贝</td><td>第 34 课</td></tr>
  <tr><td><strong>列式分块 / ChunkedColumn</strong></td><td>段按字段成列、每列切定长块;利于 SIMD 与按块内存管理</td><td>第 35 课</td></tr>
  <tr><td><strong>mmap</strong></td><td>把 binlog 映射进虚拟内存、按需缺页;让数据大于物理内存</td><td>第 35 课</td></tr>
  <tr><td><strong>表达式两层 / ITypeExpr</strong></td><td>逻辑 ITypeExpr(算什么)降级为物理 Expr::Eval(向量化执行)</td><td>第 36 课</td></tr>
  <tr><td><strong>算子流水线 / Task·Driver·Operator</strong></td><td>向量化火山模型:Task(整次)、Driver(推数据)、Operator(各司其职)</td><td>第 36 课</td></tr>
  <tr><td><strong>SIMD</strong></td><td>单指令多数据:一条指令并行算一批浮点,向量化执行之本</td><td>第 36 课</td></tr>
</table>

<h2>六、流式系统</h2>
<table class="t">
  <tr><th>术语</th><th>一句话定义</th><th>课次</th></tr>
  <tr><td><strong>StreamingNode</strong></td><td>消费 WAL→flush 落盘的驱动者;DataNode 收窄为压缩等</td><td>第 17、31 课</td></tr>
  <tr><td><strong>Broadcaster</strong></td><td>DDL/DCL 的多日志广播器:加锁+ACK 保证多 WAL 一致生效</td><td>第 32 课</td></tr>
  <tr><td><strong>CDC / 复制</strong></td><td>跨集群同步:复制 WAL 并异地重放(传"发生了什么")、星型拓扑</td><td>第 33 课</td></tr>
  <tr><td><strong>消息队列(MQ)</strong></td><td>WAL 后端:rocksmq(单机)/Pulsar(集群)/Kafka/Woodpecker(推荐)</td><td>第 41 课</td></tr>
</table>

<h2>七、运维与贡献</h2>
<table class="t">
  <tr><th>术语</th><th>一句话定义</th><th>课次</th></tr>
  <tr><td><strong>milvuspb / MilvusService</strong></td><td>由 milvus-proto 定义的 gRPC 契约;所有 SDK 都照它说话</td><td>第 38 课</td></tr>
  <tr><td><strong>可观测三支柱</strong></td><td>日志(mlog)/指标(Prometheus)/追踪(OpenTelemetry);靠 ctx 串一个请求</td><td>第 39 课</td></tr>
  <tr><td><strong>paramtable</strong></td><td>类型安全的配置注册表(ParamItem+GetAsInt);多源按优先级合并、可热更新</td><td>第 40 课</td></tr>
  <tr><td><strong>merr(Input vs System)</strong></td><td>错误库:Input(怪请求、不可重试) vs System(怪系统/暂时、可重试)</td><td>第 44 课</td></tr>
  <tr><td><strong>mockery / mockey</strong></td><td>mockery=生成接口假实现;mockey=运行时给函数打补丁(需 -N -l)</td><td>第 43 课</td></tr>
  <tr><td><strong>测试标志</strong></td><td>Go 测试必带 -tags dynamic,test 与 -gcflags=all=-N -l</td><td>第 43 课</td></tr>
  <tr><td><strong>DCO / fork-and-pull</strong></td><td>每 commit 须 git commit -s 签名;fork→分支→PR→评审→合入</td><td>第 45 课</td></tr>
  <tr><td><strong>PR 类型</strong></td><td>feat(须 issue+设计文档)/fix(须 issue)/enhance/doc/test...</td><td>第 45 课</td></tr>
</table>

<p style="margin-top:1.4rem;color:var(--muted)">主线十个部分到此收束。后面的<strong>第 11 部分"进阶专题（选读）"</strong>是给学有余力的你准备的"加餐"——批量导入、混合检索与重排、配额限流、以及 RBAC/资源组/多租户等生产特性，需要时再翻。愿这些图、类比与源码，陪你把一个庞大的向量数据库，看成一幅可以理解、也可以参与的图景。<strong>去贡献吧——世界在等你的第一个 PR。</strong></p>
""",
    "en": r"""
<p class="lead" style="font-size:1.06rem;color:var(--muted);margin-top:-.6rem">
This is the guide's <strong>quick-reference glossary</strong>, gathering the key concepts from the first 45 lessons into a few tables by theme, each with a one-line definition and its lesson, for easy <strong>future lookup</strong>. When a term puzzles you, flip here, then follow the lesson back to the full text.
</p>

<h2>1. Overview &amp; architecture</h2>
<table class="t">
  <tr><th>Term</th><th>One-line definition</th><th>Lesson</th></tr>
  <tr><td><strong>Vector database</strong></td><td>a DB centered on "similarity search (find the nearest-neighbor topK for a vector)", vs scalar DBs' exact match</td><td>L1</td></tr>
  <tr><td><strong>Embedding</strong></td><td>map text/images into high-dimensional vectors so "semantically close" becomes "near in distance"</td><td>L4</td></tr>
  <tr><td><strong>ANN (approx. nearest neighbor)</strong></td><td>nearest-neighbor search trading a little accuracy for huge speed; the algorithmic bedrock</td><td>L5</td></tr>
  <tr><td><strong>Collection / Partition</strong></td><td>collection = a logical "table"; partition = a data-splitting unit within it</td><td>L6</td></tr>
  <tr><td><strong>Segment</strong></td><td>the physical data unit; growing (writable)→sealed (read-only)→indexed</td><td>L7</td></tr>
  <tr><td><strong>Control / data plane</strong></td><td>control plane = coordination/scheduling (Go); data plane = actually moving and computing data</td><td>L9</td></tr>
  <tr><td><strong>Coordinator</strong></td><td>manages metadata &amp; scheduling; rootcoord/datacoord/querycoord, mergeable into MixCoord</td><td>L11-13</td></tr>
  <tr><td><strong>Proxy</strong></td><td>the user entrance/facade: receive, auth, enqueue, fan out, merge</td><td>L10</td></tr>
  <tr><td><strong>QueryNode / DataNode / StreamingNode</strong></td><td>worker nodes: search; data processing (compaction etc.); consume WAL &amp; flush</td><td>L10, L17</td></tr>
</table>

<h2>2. Write path</h2>
<table class="t">
  <tr><th>Term</th><th>One-line definition</th><th>Lesson</th></tr>
  <tr><td><strong>WAL (write-ahead log)</strong></td><td>write changes as an ordered log first, flush asynchronously; recover by replay on crash</td><td>L16, L31</td></tr>
  <tr><td><strong>TimeTick / TSO</strong></td><td>a globally ordered timestamp (issued by a single-source TSO) defining "who comes first"</td><td>L16, L30</td></tr>
  <tr><td><strong>Flush / Binlog</strong></td><td>flush an in-memory segment to columnar binlog files on disk (object storage)</td><td>L17, L18</td></tr>
  <tr><td><strong>Compaction</strong></td><td>merge small/fragmented segments, purge deleted data; Mix/Merge/Clustering/L0 etc.</td><td>L19</td></tr>
  <tr><td><strong>Delete / bloom filter</strong></td><td>deletes mark by primary key; PrimaryKeyStats' bloom filter speeds "is it in this segment"</td><td>L20</td></tr>
</table>

<h2>3. Query path</h2>
<table class="t">
  <tr><th>Term</th><th>One-line definition</th><th>Lesson</th></tr>
  <tr><td><strong>topK</strong></td><td>a search returns the K nearest results by distance</td><td>L25</td></tr>
  <tr><td><strong>Delegator</strong></td><td>the coordinator on a QueryNode: fan out to segments, then merge their topK</td><td>L26</td></tr>
  <tr><td><strong>Three-level reduce</strong></td><td>three-tier topK merge: in-segment → node (delegator) → Proxy</td><td>L29</td></tr>
  <tr><td><strong>Consistency levels</strong></td><td>Strong/Bounded/Session/Eventually/Customized; a freshness vs performance trade-off</td><td>L30</td></tr>
  <tr><td><strong>Guarantee timestamp</strong></td><td>GuaranteeTs derived from the consistency level, deciding "how fresh data must be seen"</td><td>L30</td></tr>
  <tr><td><strong>Filter-then-search</strong></td><td>scalar filtering yields a bitset; vector search runs only over the survivors</td><td>L28</td></tr>
</table>

<h2>4. Indexing</h2>
<table class="t">
  <tr><th>Term</th><th>One-line definition</th><th>Lesson</th></tr>
  <tr><td><strong>HNSW</strong></td><td>hierarchical navigable small-world graph index; greedily walk toward neighbors on a graph</td><td>L5, L22</td></tr>
  <tr><td><strong>IVF</strong></td><td>inverted lists + clustering: locate candidate clusters, then compute within them</td><td>L5, L22</td></tr>
  <tr><td><strong>DiskANN / PQ</strong></td><td>disk-friendly graph index / product quantization compression (saves RAM, slight accuracy loss)</td><td>L5, L22</td></tr>
  <tr><td><strong>Knowhere</strong></td><td>Milvus's unified vector index engine (wrapping FAISS etc.); all CPU/GPU indexes go through it</td><td>L22</td></tr>
  <tr><td><strong>Scalar / full-text index</strong></td><td>index scalar fields (filtering) and text (BM25, via Rust's tantivy)</td><td>L24</td></tr>
  <tr><td><strong>GPU indexes (CAGRA etc.)</strong></td><td>types in Milvus, algorithms in Knowhere/RAFT; compile-time milvus-gpu</td><td>L37</td></tr>
</table>

<h2>5. C++ core</h2>
<table class="t">
  <tr><th>Term</th><th>One-line definition</th><th>Lesson</th></tr>
  <tr><td><strong>cgo</strong></td><td>the C-ABI bridge between Go and C++ (*_c.h); coarse-grained calls, zero-copy data</td><td>L34</td></tr>
  <tr><td><strong>Chunked columns / ChunkedColumn</strong></td><td>a segment is columnar, each column cut into fixed-size chunks; good for SIMD &amp; per-block memory</td><td>L35</td></tr>
  <tr><td><strong>mmap</strong></td><td>map binlog into virtual memory, fault in on demand; lets data exceed physical RAM</td><td>L35</td></tr>
  <tr><td><strong>Two-layer expressions / ITypeExpr</strong></td><td>logical ITypeExpr (what) lowered to physical Expr::Eval (vectorized execution)</td><td>L36</td></tr>
  <tr><td><strong>Operator pipeline / Task·Driver·Operator</strong></td><td>vectorized Volcano model: Task (one run), Driver (push data), Operator (single-purpose)</td><td>L36</td></tr>
  <tr><td><strong>SIMD</strong></td><td>single instruction, multiple data: compute a batch of floats in one instruction; basis of vectorization</td><td>L36</td></tr>
</table>

<h2>6. Streaming system</h2>
<table class="t">
  <tr><th>Term</th><th>One-line definition</th><th>Lesson</th></tr>
  <tr><td><strong>StreamingNode</strong></td><td>drives consume-WAL→flush; DataNode narrowed to compaction etc.</td><td>L17, L31</td></tr>
  <tr><td><strong>Broadcaster</strong></td><td>the multi-log broadcaster for DDL/DCL: lock + ACK so many WALs take effect consistently</td><td>L32</td></tr>
  <tr><td><strong>CDC / replication</strong></td><td>cross-cluster sync: replicate the WAL and replay remotely ("what happened"); star topology</td><td>L33</td></tr>
  <tr><td><strong>Message queue (MQ)</strong></td><td>the WAL backend: rocksmq (standalone)/Pulsar (cluster)/Kafka/Woodpecker (recommended)</td><td>L41</td></tr>
</table>

<h2>7. Operations &amp; contributing</h2>
<table class="t">
  <tr><th>Term</th><th>One-line definition</th><th>Lesson</th></tr>
  <tr><td><strong>milvuspb / MilvusService</strong></td><td>the gRPC contract defined by milvus-proto; every SDK speaks it</td><td>L38</td></tr>
  <tr><td><strong>Three observability pillars</strong></td><td>logs (mlog) / metrics (Prometheus) / traces (OpenTelemetry); stitch one request via ctx</td><td>L39</td></tr>
  <tr><td><strong>paramtable</strong></td><td>a type-safe config registry (ParamItem + GetAsInt); multi-source by priority, hot-reloadable</td><td>L40</td></tr>
  <tr><td><strong>merr (Input vs System)</strong></td><td>the error library: Input (blame request, not retriable) vs System (blame system/transient, retriable)</td><td>L44</td></tr>
  <tr><td><strong>mockery / mockey</strong></td><td>mockery = generate interface fakes; mockey = patch functions at runtime (needs -N -l)</td><td>L43</td></tr>
  <tr><td><strong>Test flags</strong></td><td>Go tests must carry -tags dynamic,test and -gcflags=all=-N -l</td><td>L43</td></tr>
  <tr><td><strong>DCO / fork-and-pull</strong></td><td>every commit needs git commit -s sign-off; fork→branch→PR→review→merge</td><td>L45</td></tr>
  <tr><td><strong>PR types</strong></td><td>feat (needs issue+design doc)/fix (needs issue)/enhance/doc/test...</td><td>L45</td></tr>
</table>

<p style="margin-top:1.4rem;color:var(--muted)">The main ten parts close here. The following <strong>Part 11, "Advanced topics (optional)"</strong> is a bonus course for when you have appetite to spare — bulk import, multi-vector hybrid search & reranking, quotas and rate-limiting, plus RBAC/resource groups/multi-tenancy and other production features; come back when you need them. May these diagrams, analogies, and snippets of source help you see a vast vector database as a landscape you can understand — and join. <strong>Go contribute — the world awaits your first PR.</strong></p>
""",
}
