# scripts/

3GPP 协议库的维护脚本。均为 **Python 3 标准库**实现，无需 pandoc/libreoffice 或 pip 依赖。
路径从脚本自身位置推导，可随仓库整体迁移。

> 本目录是项目级 skill `3gpp-spec-downloader` 的捆绑脚本（2026-09-07 自仓库根 `scripts/`
> 迁入，仓库根已无 `scripts/`）。命令以仓库根为 cwd，脚本目录代称：
> `SK=.claude/skills/3gpp-spec-downloader/scripts`

## 路径配置（Source Registry）

全部脚本的 Source 位置统一从**仓库根 `sources.json`** 读取（2026-09-11 起）。
相对路径基于仓库根解析，支持仓库外绝对路径；类型是开放 map，可任意新增。

```bash
python3 $SK/config.py list              # 列出全部 Source 及存在性
python3 $SK/config.py get specs         # 打印解析后绝对路径
python3 $SK/config.py set <类型> <路径>  # 注册/修改（新增类型同用）
python3 $SK/config.py remove <类型>      # 删除条目（不动磁盘文件）
python3 $SK/config.py doctor            # 校验
```

路径优先级：**环境变量（`OUT_MD_DIR`/`PDF_OUT_DIR`/`WIKI_DIR`/`SPECS_ROOT`）> sources.json > 内置默认**。
环境变量 `SOURCES_CONFIG` 可指定其他配置文件（仓库外运行时必用）。

## 活跃脚本

### `config.py`
Source 位置配置工具 + 库接口（`source_path()` / `wiki_root()`），其余脚本 `import config`。

### `download_and_convert.py`
从 3GPP 官网下载指定协议的 docx 并转换为 Markdown。

- 自动选版：优先 R19（`j` 前缀），回退 R18（`i`），取同前缀最大小版本。
- 支持任意系列（按编号前两位推断 `<xx>_series`）与带子编号的协议（如 `38101-5`）。
- 一个 zip 内多个 docx 自动合并。
- **公式不丢失**（2026-08-27 起）：
  - OMML 公式（`m:oMath`，现代公式，38.211 有约 2900 处）→ 内联 `$...$` /
    块级 `$$...$$` LaTeX，由 `omml2latex.py` 转换（分数/上下标/求和/根号/
    矩阵/分段函数等 38 系列实际使用的全部结构）。
  - OLE 公式（Equation.3 / MathType，旧格式）与 Visio 图 → 提取预览图到
    `images/<md名>/`，公式命名 `eq-NNNN.*`，图命名 `fig-NNNN.*`，md 内以
    `![](images/...)` 引用。**整理协议时须把 images/ 目录随 md 一起移动**。

```bash
python3 $SK/download_and_convert.py 38413:NGAP 24501:NAS_5GS
# 每项格式 <编号>[:<名称>]，编号去掉点（38.101-5 写作 38101-5）
```

输出默认落入 Source `specs` 的 `_incoming/`（即 sources.json 注册位置，可用环境变量
`OUT_MD_DIR` 覆盖），下载后再整理到对应 `TS<...>` 子目录并执行 `ingest`。

### `gen_section_index.py`
扫描 Source `specs` 下全部协议原文，重建 `wiki/sections.tsv` 章节行号索引
（列：spec/clause/level/title/file/start_line/end_line）。原文增删/换版/拆分后重跑。

### `convert_images.py`
WMF/EMF → PNG 批量转换 + md 引用改写（Obsidian/GitHub 不渲染 WMF/EMF）。
依赖 LibreOffice：`brew install --cask libreoffice`。幂等可重跑。

```bash
python3 $SK/convert_images.py            # 处理 raw_sources/3gpp_sources/specs/ 全部
python3 $SK/convert_images.py <md或目录>  # 指定目标
```

### `omml2latex.py`
OMML → LaTeX 转换器（纯标准库），被 `download_and_convert.py` 调用；
也可独立调试：`python3 $SK/omml2latex.py <docx或document.xml>`。

### `add_specs.py`
增量入库：编辑 `ENTRIES` 后运行，下载+登记+生成概览页+追加 index/log。

### `ingest_md_to_wiki.py`
**一次性迁移脚本**：把 `md/` 下全部协议结构化登记进知识库（wiki/）
（移入 raw_sources、生成 compiled 概览页、重建 index.md、追加 log.md）。
初始 30 个 spec 已于 2026-06-21 执行完毕，保留供复现/参考。

> 早期独立的 docx/doc→md 转换脚本（convert.py 等）其逻辑已被
> `download_and_convert.py` 内联吸收，已删除。
