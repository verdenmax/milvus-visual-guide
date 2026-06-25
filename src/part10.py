"""Content for Part 10 (Practice & contributing). Lessons 42-46.

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
