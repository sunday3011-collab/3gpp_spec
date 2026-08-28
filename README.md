# 3GPP Protocols

3GPP 协议库 + 基于 Karpathy「LLM Wiki」方法论的知识管理系统。

## 仓库结构

```
.
├── 3gpp-specs/    # 知识库 (Obsidian vault)，见 3gpp-specs/README.md
└── scripts/       # 下载/转换/登记脚本，见 scripts/README.md
```

- **3gpp-specs/**：**35 个** 3GPP 协议（R19 为主）已入库并**全部蒸馏**（带 clause 引用的
  结构化知识页）。原始 Markdown 存于 `raw_sources/specs/`（单文件超 2MB 已按标题边界
  拆分为多 part），ETSI 官方最新版 PDF 存于 `raw_sources/pdfs/`，LLM 编译的蒸馏页存于
  `wiki/compiled/`，个人洞察存于 `personal_insights/`。全库章节索引 `wiki/sections.tsv`
  支持按 clause 精确取原文切片；检索阶梯与治理规约见 `3gpp-specs/CLAUDE.md`。
- **scripts/**：纯 Python 标准库实现，无外部依赖。`download_and_convert.py` 负责从
  3GPP 官网下载协议转 Markdown、或从 ETSI 下载官方最新 PDF；`ingest_md_to_wiki.py`
  是初始一次性迁移脚本。

## 快速开始

```bash
# 下载并转换新协议 (编号去掉点，38.101-5 写作 38101-5)
python3 scripts/download_and_convert.py 38413:NGAP 24501:NAS_5GS

# 从 ETSI 下载官方最新版 PDF
python3 scripts/download_and_convert.py --pdf 38331:RRC 23501:5GS_Architecture

# 对已有 md 按 2MB 上限拆分 (不重新下载)
python3 scripts/download_and_convert.py --split 3gpp-specs/raw_sources/specs

# 刷新章节索引 (sections.tsv 行号区间)
WIKI_DIR=3gpp-specs python3 scripts/gen_section_index.py
```

下载产物落入 `3gpp-specs/raw_sources/specs/_incoming/`，再整理到对应
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
