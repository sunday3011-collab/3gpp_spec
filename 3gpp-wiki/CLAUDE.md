# 3GPP Knowledge Wiki — 操作规约 (CLAUDE.md)

> 本文件是本知识库的治理文档。每次会话开始、每次 ingest/query/lint 前，先读本文件。

---

## 系统定位

这是一个 **top-down 知识管理系统**，适用于 3GPP 协议栈这类**结构在外部已经存在且有操作意义**的领域（协议分层、WG 归属、规范编号体系都是先验存在的骨架）。

- **LLM 负责 bookkeeping**：交叉引用维护、摘要更新、矛盾标注、一致性维护、frontmatter 规范、index/log 同步。
- **人负责供给与沉淀**：投喂 `raw_sources/`，沉淀 `personal_insights/`。

LLM 不创造一手知识，只编译、组织、维护人投喂的原始材料，并把热点知识缓存进 `wiki/`。

---

## 目录权限规则

| 目录 | LLM 权限 | 说明 |
|------|---------|------|
| `raw_sources/` | **只读** | 人投喂原始文档，LLM 不得修改 / 删除 / 新建 |
| `wiki/compiled/` | **全权维护** | LLM 可创建、修改、重写 |
| `wiki/authored/` | **仅追加** | LLM 只能 append，不得重写已有内容 |
| `personal_insights/` | **辅助结构化** | 人写，LLM 协助结构化，不主动修改已有内容 |
| `wiki/index.md` | **每次 ingest 后必须更新** | 全库导航入口 |
| `wiki/log.md` | **append-only** | 只追加，绝不修改历史记录 |

---

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

---

## 术语规范

ingest 和写作时**强制执行**：

- handover，不写 handoff
- UE，不写 终端 / 手机
- gNB，不写 5G 基站
- Release 标注格式：**Rel-18**，不写 R18
- 引用规范必须**同时写编号和标题**（如 `TS38.321 MAC protocol specification`）
- 产品私有行为必须标注 **⚠️ 产品私有，不代表 3GPP 标准**

---

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

规则：
- `compiled/` 目录下所有页面：`llm_can_overwrite: true`
- `authored/` 目录下所有页面：`llm_can_overwrite: false`

---

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

---

## Query 规程

收到技术问题时：

1. 先读 `wiki/index.md`，定位相关页面
2. 读取相关 wiki 页面综合答案
3. 答案引用必须**精确到 TS 编号和章节**
4. 判断答案是否有归档价值：
   - 有价值 → 写入 `wiki/compiled/` 或 `wiki/authored/`
   - 在 `log.md` 追加：`## [日期] query | [问题摘要] | 归档：[是/否]`

---

## Lint 规程

收到 `lint` 指令时，检查：

- 孤立页面（无任何 wikilink 指向）
- 过时 Release 声明（已有更新版 spec 但页面仍标注旧 Release）
- 缺失的交叉引用（A 页面提到 B 概念但未链接 B 页面）
- `product_notes` 与 `compiled/protocols/` 的矛盾
- `personal_insights/inbox/` 中滞留超过 2 周的笔记（提示需要提炼）

**输出 lint 报告，不自动修改，等待我确认后再执行。**

---

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

---

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

---

## 链接规范

所有页面间引用使用 Obsidian 标准 wikilink 格式：`[[页面名]]`。
