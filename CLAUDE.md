# 3GPP Protocols — 操作规约 (CLAUDE.md)

> 本文件是本仓库（Claude Code 工程）的**总治理文档**。每次会话开始、以及涉及协议下载/转换、
> 知识库 ingest/query/lint 的操作前，先读本文件（结构说明另见仓库根 `.claude/README.md`）。

---

## 仓库定位与结构

本仓库 = **Obsidian 知识库**（仓库根即 vault）：**索引外部知识源，wiki 页面在本库管理**。

- **外部知识源只被索引**：3GPP 协议（md/PDF/docx）、产品私有文档、**代码库**等原始资料通过
  `sources.json` 注册位置（可指向仓库内或仓库外任意路径），本库只引用、不负责其本体管理
- **索引产出由本库持有**：LLM 编译的 wiki 页面（蒸馏页、章节索引 `sections.tsv`、长文）、
  个人洞察全部是本库管理的内容，位置无关化后重组源目录不影响任何页面

```
.
├── CLAUDE.md                 # 本文件：总治理规约
├── README.md                 # 仓库总览与快速开始
├── sources.json              # 外部知识源位置注册表（唯一路径真理源）
├── wiki/                     # 索引产出的 wiki 页面（本库管理）：compiled/ · authored/ · index · log · sections.tsv
├── raw_sources/              # 外部知识源（被索引对象）：3gpp_sources/{specs(md) · pdfs · word} + product/
├── personal_insights/        # 人写的个人洞察
└── .claude/                  # 项目级 agent 配置（skill = 工具实体，唯一源头）
    └── skills/3gpp-spec-downloader/
        ├── SKILL.md          # 协议工具总入口（下载/转换/图片/索引）
        └── scripts/          # 全部维护脚本（2026-09-07 自原仓库根 scripts/ 迁入）
```

关键事实（避免过时认知）：
- **2026-09-12 起 `3gpp-specs/` 目录壳已去掉**，wiki/raw_sources/personal_insights 直接位于仓库根；
  仓库根即 Obsidian vault
- **仓库根不再有 `scripts/` 目录**；一切工具脚本在 `.claude/skills/3gpp-spec-downloader/scripts/`
- `.workbuddy/skills/3gpp-spec-downloader` 是指向 `.claude/skills/...` 的 symlink（WorkBuddy 入口），
  Claude Code 直接读 `.claude/`——单份内容，无漂移

---

## 工具入口（协议下载 / 转换 / 索引）

协议维护一律走项目级 skill，命令以仓库根为 cwd：

```bash
SK=.claude/skills/3gpp-spec-downloader/scripts   # 脚本目录代称

python3 $SK/config.py list / set <类型> <路径> / doctor  # Source 位置配置 (仓库根 sources.json)
python3 $SK/download_and_convert.py 38331:RRC 38321:MAC            # FTP docx → md
python3 $SK/download_and_convert.py --pdf 38331:RRC                # ETSI 官方 PDF
python3 $SK/download_and_convert.py --split <md目录>                # md 超2MB 拆分
python3 $SK/convert_images.py [md或目录]                            # WMF/EMF → PNG
python3 $SK/gen_section_index.py                                   # 刷新 sections.tsv
```

- **Source 位置可配置**（2026-09-11 重构）：specs/pdfs/word/product 及新增类型的位置统一由
  仓库根 `sources.json` 注册，相对路径基于仓库根，支持仓库外绝对路径。
  优先级：环境变量（`OUT_MD_DIR`/`PDF_OUT_DIR`/`WIKI_DIR`/`SPECS_ROOT`）> sources.json > 内置默认
- 版本选择：FTP 优先 R19(`j`前缀)、404 回退 R18(`i`)；ETSI 解析版本目录取最高
- 下载产物落入 Source `specs` 的 `_incoming/`，整理到 `TS<...>` 子目录后再 ingest
- 完整操作细节（协议号格式/输出结构/已知限制）见 `.claude/skills/3gpp-spec-downloader/SKILL.md`
  ／该目录 `scripts/README.md`

---

# 知识库操作规约

> **路径基线**：本章所有相对路径均以**仓库根**为基准（2026-09-12 起知识库即仓库根，
> 无 `3gpp-specs/` 中间层）。知识库同时是 Obsidian vault。

## 系统定位

这是一个 **top-down 知识管理系统**，适用于 3GPP 协议栈这类**结构在外部已经存在且有操作意义**的领域（协议分层、WG 归属、规范编号体系都是先验存在的骨架）。

- **LLM 负责 bookkeeping**：交叉引用维护、摘要更新、矛盾标注、一致性维护、frontmatter 规范、index/log 同步。
- **人负责供给与沉淀**：投喂 `raw_sources/`，沉淀 `personal_insights/`。

LLM 不创造一手知识，只编译、组织、维护人投喂的原始材料，并把热点知识缓存进 `wiki/`。

## 目录权限规则

| 目录 | LLM 权限 | 说明 |
|------|---------|------|
| `raw_sources/` | **只读** | 人投喂原始文档，LLM 不得修改 / 删除 / 新建 |
| 外部代码库（sources.json 注册路径） | **只读** | 见「代码源（code）规约」；禁止修改文件与任何 git 写操作 |
| `wiki/compiled/` | **全权维护** | LLM 可创建、修改、重写 |
| `wiki/authored/` | **仅追加** | LLM 只能 append，不得重写已有内容 |
| `personal_insights/` | **辅助结构化** | 人写，LLM 协助结构化，不主动修改已有内容 |
| `wiki/index.md` | **每次 ingest 后必须更新** | 全库导航入口 |
| `wiki/log.md` | **append-only** | 只追加，绝不修改历史记录 |

## 协议层分类（WG 归属）

```
PHY      ← RAN WG1: TS38.211 / 38.212 / 38.213 / 38.214
MAC      ← RAN WG2: TS38.321
RLC      ← RAN WG2: TS38.322
PDCP     ← RAN WG2: TS38.323
SDAP     ← RAN WG2: TS37.324   ← 修正：原始需求标注为 TS38.401，SDAP 实际规范为 TS37.324（TS38.401 为 NG-RAN 架构）
RRC      ← RAN WG2: TS38.331
NAS      ← CT WG1:  TS24.501
5GC      ← SA WG2:  TS23.501 / 23.502 / 23.503
```

## 术语规范

ingest 和写作时**强制执行**：

- handover，不写 handoff
- UE，不写 终端 / 手机
- gNB，不写 5G 基站
- Release 标注格式：**Rel-18**，不写 R18
- 引用规范必须**同时写编号和标题**（如 `TS38.321 MAC protocol specification`）
- 产品私有行为必须标注 **⚠️ 产品私有，不代表 3GPP 标准**

## Wiki 页面 Frontmatter 规范

每个 `wiki/compiled/` 页面必须包含：

```yaml
---
layer: PHY | MAC | RLC | PDCP | SDAP | RRC | NAS | concept | comparison
spec: TS38.321
release: Rel-18
authored_by: llm | human | mixed
llm_can_overwrite: true | false
last_updated: YYYY-MM-DD
---
```

可选字段：
- `hot: true` —— 标记高频热点协议（RRC/PHY/MAC/RLC/PDCP），检索优先命中、维护优先盯时效。
- **`code_notes/` 页面必填**：`repo: <仓库名>`、`commit: <短hash>`、`branch: <分支>` ——
  代码持续演进，页面是**某时点的快照**，必须标注快照版本；回答时若源码已前进需提醒可能过时。

规则：
- `compiled/` 目录下所有页面：`llm_can_overwrite: true`
- `authored/` 目录下所有页面：`llm_can_overwrite: false`

## Ingest 规程

收到 `ingest [文件路径或知识点]` 指令时，按以下顺序执行：

1. 读取 `raw_sources` 中的目标文件
2. 读取 `wiki/index.md`，确认相关页面已存在或需新建
3. 提取知识单元，判断归属层（protocol / concept / comparison）
4. 更新或新建 `wiki/compiled/` 对应页面
5. 检查是否涉及跨层交互 → 如有，在 `wiki/compiled/concepts/` 或 `personal_insights/inbox/` 创建提示
6. 检查与已有页面的矛盾（**不同 Release 间差异 ≠ 矛盾**）
7. 更新 `wiki/index.md`
8. 在 `wiki/log.md` 追加记录，格式：
   `## [日期] ingest | [来源文件] | 影响页面：[列表]`

## Query 规程

收到技术问题时，**按检索阶梯由廉价到昂贵逐级升级，永远不要直接整篇加载 `raw_sources/` 原文**
（单篇可达数万行，会撑爆上下文、且弱模型不可用）。token 纪律是第一原则。

### 检索阶梯
0. **判源**：问题涉及**代码实现**（某功能怎么实现/在哪定义/行为细节）而非协议规范时，
   走下方「代码源（code）规约」的检索纪律，不进入本阶梯。
1. **路由**：读 `wiki/index.md`（先看 `🔥 热点协议` 区），定位候选页面。
2. **命中缓存**：读相关 `wiki/compiled/` 蒸馏页 —— 多数问题到此即可作答。
3. **取 clause 切片**：若蒸馏页不足，查 `wiki/sections.tsv`
   （列：`spec clause level title file start_line end_line`，用 grep/awk），
   定位精确 clause，**只读其 `start_line..end_line` 行号区间**那几十行，而非整篇。
   例：`awk -F'\t' '$1=="TS38.321" && $2=="5.1.4"' wiki/sections.tsv`
   → 得到 file 与行号区间 → 按区间 Read（file 为相对 `raw_sources/3gpp_sources/specs/` 的路径）。
4. **兜底**：仅当上述都不够时，才读原文更大段落。

### 作答与归档
- 答案引用必须**精确到 TS 编号和章节**（如 `TS38.321 §5.1.4`）。
- 判断答案是否有归档价值：
  - 有价值 → 写入 `wiki/compiled/`（热点层优先）或 `wiki/authored/`，使下次查询命中阶梯第 2 级。
  - 在 `log.md` 追加：`## [日期] query | [问题摘要] | 归档：[是/否]`

> `wiki/sections.tsv` 由 `.claude/skills/3gpp-spec-downloader/scripts/gen_section_index.py`
> 生成（扫描全部原文标题）。
> 原文有增删/换版后重新运行以刷新行号区间。

## Lint 规程

收到 `lint` 指令时，检查：

- 孤立页面（无任何 wikilink 指向）
- 过时 Release 声明（已有更新版 spec 但页面仍标注旧 Release）
- 缺失的交叉引用（A 页面提到 B 概念但未链接 B 页面）
- `product_notes` 与 `compiled/protocols/` 的矛盾
- `personal_insights/inbox/` 中滞留超过 2 周的笔记（提示需要提炼）

**输出 lint 报告，不自动修改，等待我确认后再执行。**

## 目录重组规约（Source 位置变更）

移动/重命名 raw_sources 下的源目录时，**只允许碰两处**，其余位置全部位置无关：

```bash
git mv raw_sources/<旧> raw_sources/<新>      # 1. git mv 保留历史
python3 $SK/config.py set <类型> <新相对路径>                        # 2. 更新 sources.json 注册
python3 $SK/gen_section_index.py                                    # 3. 重建 sections.tsv
```

硬性约定（防止路径知识散落）：
- **compiled 页面原文引用一律用 `[[wikilink]]`**，不写死 `raw_sources/...` 路径文本
  （Obsidian 按 basename 全库解析，位置无关；具体位置由 sources.json + sections.tsv 提供）
- **脚本不硬编码 Source 路径**，一律 `import config` 读取；模板同此
- 文档中的路径仅为示例，标注"以 sources.json 为准"；重组后 structure 图可顺手更新但不强制

## 代码源（code）规约

外部代码库是继协议/产品文档之后的第三类知识源：**本库只索引与检索，不收纳代码本体**。
接入方式是 grep/find 等工具直接对注册路径检索（无外部 AI 依赖）。

### 注册与发现

```bash
python3 $SK/config.py set code /绝对路径/代码仓库     # 单仓库
python3 $SK/config.py set code-<仓库名> /绝对路径/xxx  # 多仓库时用 code-<名> 区分
python3 $SK/config.py list                            # 查看当前注册
```

- 代码库保持独立 git 仓库，位置在仓库外；本库对其**零写入**
- 代码库移动/换路径 = 一条 `config.py set`，无需改任何页面（同「目录重组规约」哲学）

### 检索纪律（token 纪律同检索阶梯）

1. **先蒸馏后源码**：先查 `wiki/compiled/code_notes/` 是否已有相关页面，命中即答
2. **先地图后钻探**：首次接触某仓库，先读其 README / 顶层目录结构 / 构建脚本建立地图，
   再用 `grep -rn` / `find` 定位目标符号，**只 Read 命中的文件与行号区间**，禁止整仓/整目录加载
3. **只读铁律**：对外部代码库**禁止**修改/新建/删除文件、禁止 `git commit/push/checkout` 等
   一切写操作；本库 agent 对代码库只有检索与阅读两种动作

### 引用与蒸馏

- **引用格式**：`<仓库名>/<仓库相对路径>:<行号>`（如 `myapp/src/mac/scheduler.c:123`）。
  code_notes 页面**不使用 wikilink**（外部文件不在 vault 内，basename 解析不可达），用路径文本
- **蒸馏页**：`wiki/compiled/code_notes/<仓库名>/`，典型页面：架构总览、模块职责、
  关键流程（函数级调用链）、与 3GPP 规范的对应关系（链接回 `compiled/protocols/` 页面）
- frontmatter 必填 `repo` / `commit` / `branch`（快照时点，见 Frontmatter 规范）
- 有价值的代码问答按「作答与归档」规则写入 code_notes，并在 `log.md` 追加记录

### 代码知识生成（CodeWiki，可选加速器）

初稿生成可用开源工具 **CodeWiki**（FSoft-AI4Code/CodeWiki，静态依赖分析 + LLM 层级分解，
产出 Markdown + Mermaid 架构图，支持 C/C++/Python/Java 等 10 语言；论文 arXiv:2510.24428）。
它在仓库级做的正是本规约"先地图后钻探"第一步的自动化——依赖图、模块聚类、架构图一次产出。

接入纪律（CodeWiki 产物是**原料**，不是知识库页面）：

- **产物不进 vault**：生成目录留在代码仓库旁（如 `<repo>/../docs_codewiki/`）或临时目录；
  只把经本 agent **策展重构**后的页面收进 `code_notes/`，避免双真理源
- **策展 = 换格式**：补齐 frontmatter（`repo`/`commit`/`branch`）、引用统一为
  `仓库名/路径:行号`、保留 Mermaid 图、与本库 protocols 页面建立交叉链接
- **快照对齐**：CodeWiki 的 metadata.json 记录生成时 commit hash（支持 `--update` 增量），
  入库页面沿用该 hash；代码前进后用 `--update` 重新生成、再策展
- **检索基线不变**：grep/find 是检索的第一性工具；CodeWiki 只加速"生成"，检索阶梯不依赖它

> 同名陷阱：另有 gaosichun888/codewiki（Electron 桌面应用，自带 wiki/图谱/RAG）——
> 不要用，其自带知识库会与本 vault 形成双真理源。

### 与协议层的联动（本源的独特价值）

代码源与协议源交叉提问时（如"我们的 MAC 调度器实现和 TS38.321 §5.1.4 差异"）：
协议侧走检索阶梯取 clause 切片，代码侧走本规约定位实现，两侧结论在
`compiled/product_notes/` 或 `code_notes/` 的差异页汇合，格式沿用产品差异分析三段式。

## 产品知识处理规范

- `raw_sources/product/[产品名]/`：存放原始产品文档
- `wiki/compiled/product_notes/[产品名]/`：存放编译后的产品分析
- 产品页面结构：

```
## 标准行为（TS xx.xxx）
[标准描述]

## 产品实现（[产品名] vX.X）
> ⚠️ 产品私有行为，不代表 3GPP 标准
[产品描述]

## 差异分析
[原因推测，标注【推测】]
```

## personal_insights 提升规则

Flomo 笔记满足以下**任一条件**时，提示我提升至 `personal_insights/propositions/`：

1. 能用一个命题句表达（"X 导致 Y" / "X 和 Y 本质上是同一件事"）
2. 与 wiki 中已有协议页面存在张力或补充关系
3. 在 Flomo 每日回顾中被重复触发

提升流程：
- 我起草命题标题
- 你辅助结构化为原子笔记
- 写入 `personal_insights/propositions/`
- 在对应 wiki 协议页面底部加反向链接

## 链接规范

所有页面间引用使用 Obsidian 标准 wikilink 格式：`[[页面名]]`。
