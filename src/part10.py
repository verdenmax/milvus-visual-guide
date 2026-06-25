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
