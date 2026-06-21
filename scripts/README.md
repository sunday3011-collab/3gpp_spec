# scripts/

3GPP 协议库的维护脚本。均为 **Python 3 标准库**实现，无需 pandoc/libreoffice 或 pip 依赖。
路径从脚本自身位置推导，可随仓库整体迁移。

## 活跃脚本

### `download_and_convert.py`
从 3GPP 官网下载指定协议的 docx 并转换为 Markdown。

- 自动选版：优先 R19（`j` 前缀），回退 R18（`i`），取同前缀最大小版本。
- 支持任意系列（按编号前两位推断 `<xx>_series`）与带子编号的协议（如 `38101-5`）。
- 一个 zip 内多个 docx 自动合并。

```bash
python3 scripts/download_and_convert.py 38413:NGAP 24501:NAS_5GS
# 每项格式 <编号>[:<名称>]，编号去掉点（38.101-5 写作 38101-5）
```

输出默认落入 `3gpp-wiki/raw_sources/specs/_incoming/`（可用环境变量 `OUT_MD_DIR` 覆盖），
下载后再整理到对应 `TS<...>` 子目录并执行 `ingest`。

### `ingest_md_to_wiki.py`
**一次性迁移脚本**：把 `md/` 下全部协议结构化登记进 `3gpp-wiki/`
（移入 raw_sources、生成 compiled 概览页、重建 index.md、追加 log.md）。
初始 30 个 spec 已于 2026-06-21 执行完毕，保留供复现/参考。

> 早期独立的 docx/doc→md 转换脚本（convert.py 等）其逻辑已被
> `download_and_convert.py` 内联吸收，已删除。
