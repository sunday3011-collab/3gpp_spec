# Wiki 操作日志
<!-- append-only，不修改历史记录 -->

## [2026-08-27] ingest | 全量重转换入库 (3gpp-wiki-v2) | 影响页面：35 个 spec 概览页 + index.md 重建
- 35 个协议基于官网最新 docx 重新转换 (OMML→LaTeX 公式 + 图片附件)
- 原始 docx 存于 raw_sources/word/，转换 md 存于 raw_sources/specs/
- 协议层页面 16 个，概念页面 19 个

## [2026-08-28] split | 大 md 文件按 2MB 上限拆分 (3gpp-wiki-v2) | 影响页面：8 个 spec 概览页 + sections.tsv 重建
- 8 个 >2MB 协议原文按标题边界拆分为 36 个 part (每份 <2MB)：38.133(15) 38.331(6) 24.501(4) 38.101-1(2) 23.502(3) 23.501(2) 38.101-3(2) 24.301(2)
- 图片引用不变，各 part 共用同一 images/<stem>/ 目录
- 重跑 `WIKI_DIR=3gpp-wiki-v2 python3 scripts/gen_section_index.py` 刷新 sections.tsv 行号区间 (28017 章节，35 spec)
- 8 个概览页 原始文档 行更新为指向 part 文件，章节定位统一指向 wiki/sections.tsv
