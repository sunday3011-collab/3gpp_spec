# 3GPP Protocols

**一个 Obsidian 知识库**（仓库根即 vault）：索引外部知识源，并为索引产出的 wiki
页面提供统一的加工与管理场所——即基于 Karpathy「LLM Wiki」方法论的知识管理系统。

核心机制：

- **外部知识源**（3GPP 协议 md/PDF/docx、产品私有文档、**外部代码库**）只被**索引与引用**，
  位置由 `sources.json` 注册，可指向仓库内或仓库外任意路径；原始文件本身不是知识库的一部分
- **wiki 页面在本库管理**：LLM 对源内容编译出的蒸馏页（`wiki/compiled/`）、章节索引
  （`wiki/sections.tsv`）、长文（`wiki/authored/`）全部由本库持有与治理
- **个人洞察**（`personal_insights/`）同样是本库管理的内容层

## 仓库结构

```
.
├── CLAUDE.md             # 总治理规约（知识库操作/检索阶梯/目录重组规约）
├── README.md             # 本文件
├── sources.json          # 外部知识源位置注册表 (specs/pdfs/word/product/code，支持仓库外路径)
├── wiki/                 # 索引产出的 wiki 页面（本库管理）：compiled/ · authored/ · index.md · log.md · sections.tsv
├── raw_sources/          # 外部知识源（被索引对象，LLM 只读）
│   ├── 3gpp_sources/     #   规格类原文：specs/(md) · pdfs/ · word/
│   └── product/          #   产品私有文档
├── personal_insights/    # 人写的个人洞察
└── .claude/              # 项目级 agent 配置（skill = 工具实体）
    └── skills/3gpp-spec-downloader/
        ├── SKILL.md      # 操作手册 / 总入口
        └── scripts/      # 全部维护脚本（路径统一读 sources.json）
```

- `.workbuddy/skills/3gpp-spec-downloader` 是 **symlink**，指向 `.claude/skills/...`
  实体：Claude Code（`.claude/`）与 WorkBuddy（`.workbuddy/skills/`）双入口加载
  **同一份内容**，无漂移。

- **知识库**：**35 个** 3GPP 协议（R19 为主）已入库并**全部蒸馏**（带 clause 引用的
  结构化知识页）。原始 Markdown 存于 `raw_sources/3gpp_sources/specs/`（单文件超 2MB 已按标题边界
  拆分为多 part），ETSI 官方最新版 PDF 存于 `raw_sources/3gpp_sources/pdfs/`，LLM 编译的蒸馏页存于
  `wiki/compiled/`，个人洞察存于 `personal_insights/`。全库章节索引 `wiki/sections.tsv`
  支持按 clause 精确取原文切片；检索阶梯与知识库治理规约见 [`CLAUDE.md`](CLAUDE.md)。
- **`.claude/skills/3gpp-spec-downloader/scripts/`**：纯 Python 标准库实现，无外部依赖。
  `download_and_convert.py` 负责从 3GPP 官网下载协议转 Markdown、或从 ETSI 下载官方最新
  PDF；`config.py` 管理 Source 位置；`gen_section_index.py` 重建章节索引。完整清单见
  `.claude/skills/3gpp-spec-downloader/scripts/README.md`。

## 快速开始

```bash
# 脚本目录代称（唯一源头，位于项目级 skill 捆绑目录）
SK=.claude/skills/3gpp-spec-downloader/scripts

# 配置各 Source 位置 (specs/pdfs/word/product，支持仓库外绝对路径)
python3 $SK/config.py list
python3 $SK/config.py set specs /外置盘/协议原文目录

# 下载并转换新协议 (编号去掉点，38.101-5 写作 38101-5)
python3 $SK/download_and_convert.py 38413:NGAP 24501:NAS_5GS

# 从 ETSI 下载官方最新版 PDF
python3 $SK/download_and_convert.py --pdf 38331:RRC 23501:5GS_Architecture

# 对已有 md 按 2MB 上限拆分 (不重新下载)
python3 $SK/download_and_convert.py --split raw_sources/3gpp_sources/specs

# 刷新章节索引 (sections.tsv 行号区间)
python3 $SK/gen_section_index.py
```

下载产物落入 `raw_sources/3gpp_sources/specs/_incoming/`，再整理到对应
`TS<...>` 子目录并在知识库中执行 `ingest`。

## 协议覆盖

| 层 | 规范 |
|----|------|
| PHY | TS38.201/202/211/212/213/214/215 |
| MAC / RLC / PDCP / SDAP | TS38.321 / 38.322 / 38.323 / TS37.324 |
| RRC | TS38.331 / 38.304 / 38.306 |
| NAS | TS24.501 / 24.301 |
| SA (架构/流程) | TS23.501 / 23.502 |
| 其他 (接口/RF/RRM/架构) | NGAP 38.413、XnAP 38.423、F1AP 38.473、BAP 38.340、38.101-x、38.133、38.300/305/314、38.401、37.213/340 |
