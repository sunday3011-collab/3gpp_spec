# 3GPP Knowledge Wiki

基于 Karpathy「LLM Wiki」方法论的 3GPP 协议知识库（Obsidian vault）。
**完整操作规约见 [CLAUDE.md](CLAUDE.md)** —— 每次会话前先读它。

## 三层结构

| 层 | 目录 | 谁来写 |
|----|------|--------|
| 原始文档 | `raw_sources/` | 人投喂，LLM **只读** |
| 编译缓存 | `wiki/` | LLM 维护（`compiled/` 全权、`authored/` 仅追加） |
| 个人洞察 | `personal_insights/` | 人写，LLM 辅助结构化 |

```
raw_sources/specs/<TS子目录>/   原始协议 md (人投喂)
raw_sources/specs/_incoming/    下载脚本产物暂存区
wiki/index.md                   全库导航 (每次 ingest 后更新)
wiki/log.md                     操作日志 (append-only)
wiki/compiled/protocols/<层>/   各协议层概览页 + README
wiki/compiled/concepts|comparisons|product_notes/
wiki/authored/                  LLM 撰写、不可重写的长文
personal_insights/inbox|propositions|patterns/
```

当前已登记 **30 个 spec**（16 协议层页 + 14 概念页），均为结构化概览，未展开逐条细节。

## 三个指令

| 指令 | 作用 |
|------|------|
| `ingest <路径或知识点>` | 读原文 → 提取知识单元 → 更新/新建 compiled 页 → 更新 index → 追加 log |
| 直接提问（query） | 先查 `index.md` 定位页面 → 综合作答（引用精确到 TS 编号+章节） |
| `lint` | 检查孤立页/过时 Release/缺失交叉引用/矛盾/滞留笔记，**只报告不自动改** |

示例：`ingest raw_sources/specs/TS38.321_MAC/38.321_MAC_j20.md`

## 约定速记
- 术语：handover（非 handoff）、UE、gNB、Rel-18（非 R18）；引用同时写编号+标题。
- compiled 页必须带 frontmatter；`compiled/` 可被 LLM 重写，`authored/` 不可。
- 产品私有行为标注 **⚠️ 产品私有，不代表 3GPP 标准**。
