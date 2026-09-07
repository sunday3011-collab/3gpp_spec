---
name: 3gpp-spec-downloader
description: 3GPP 协议库维护总入口（项目级 skill）。本 skill 即工具实体，捆绑 scripts/ 目录承载全部维护脚本（下载/转换/拆分/图片/索引/入库）。当用户要求"下载3GPP协议"、"获取38系列协议"、"下载RRC/MAC/PDCP/RLC/PHY/SDAP"、"转换docx为markdown"、"拆分md"、"WMF/EMF转PNG"、"刷新章节索引"、"整理raw_sources"、"增量入库"时使用。仓库根已无 scripts/ 目录，禁止引用 scripts/xxx.py 旧路径。版本优先 R19(j)/回退 R18(i)，公式 OMML→LaTeX。同仓库被 Claude Code(.claude/) 与 WorkBuddy(.workbuddy/skills/ symlink) 双入口加载，单份内容。
---

# 3GPP 协议库维护（3gpp-spec-downloader）

## 定位（Big Picture）

本 skill 是 `3GPP_Protocols` 仓库内协议工具的**唯一实体**：SKILL.md + 捆绑 `scripts/`。
2026-09-07 起仓库根的 `scripts/` 目录已整体迁入本 skill 的 `scripts/`，删除不保留。

| 入口 | 路径 | 加载方 |
|------|------|--------|
| 实体（源头） | `.claude/skills/3gpp-spec-downloader/` | Claude Code |
| symlink | `.workbuddy/skills/3gpp-spec-downloader` → 实体 | WorkBuddy |

## 脚本位置

所有命令以**仓库根为 cwd**：

```bash
cd /Users/huangyang/Code/3GPP_Protocols
SK=.claude/skills/3gpp-spec-downloader/scripts   # 下文用 $SK 代指，直接替换为完整路径
```

- 脚本通过**向上探测 `.git`** 定位仓库根（`_repo_root()`），故位于 skill 深层目录仍正确
- 仓库外单独运行（如用户级 skill 的镜像副本）探测失败时回退"上溯2层"，此时必须用环境变量覆盖输出目录
- `download_and_convert.py` 与 `omml2latex.py`、`add_specs.py` 的同目录 import 关系随整体迁移保持

## 工作流速查

| 任务 | 命令 |
|------|------|
| docx下载转md | `python3 $SK/download_and_convert.py 38331:RRC 38321:MAC` |
| ETSI官方PDF | `python3 $SK/download_and_convert.py --pdf 38331:RRC` |
| md超2MB拆分 | `python3 $SK/download_and_convert.py --split 3gpp-specs/raw_sources/specs` |
| WMF/EMF→PNG | `python3 $SK/convert_images.py [md或目录，缺省全部]` |
| 刷新章节索引 | `WIKI_DIR=3gpp-specs python3 $SK/gen_section_index.py` |
| 增量入库(低频) | 先编辑 `add_specs.py` 的 `ENTRIES` 再 `python3 $SK/add_specs.py` |
| 初始迁移(仅参考) | `ingest_md_to_wiki.py`（2026-06-21 已执行，保留复现用） |

## 脚本清单

| 文件 | 角色 |
|------|------|
| `download_and_convert.py` | 核心：FTP docx→md / ETSI PDF / md 拆分，import omml2latex |
| `omml2latex.py` | OMML→LaTeX 转换器（纯标准库），被 download_and_convert 调用 |
| `convert_images.py` | WMF/EMF→PNG 批量转换 + md 引用改写（依赖 LibreOffice soffice） |
| `gen_section_index.py` | 重建 `wiki/sections.tsv` 章节行号索引 |
| `add_specs.py` | 增量入库：下载+登记+生成概览页+追加 index/log |
| `ingest_md_to_wiki.py` | 一次性历史迁移脚本（保留复现/参考） |
| `README.md` | 脚本规范文档（细节以此为准） |

## 版本选择逻辑

3GPP FTP：默认 `--release 19` 优先 `j` 前缀(R19)，404 回退 `i`(R18)，同前缀取数字最大小版本。
ETSI PDF：解析版本目录按 (major, minor, patch) 排序取最高。

## 协议号格式

- 去点：`38.331`→`38331`，`38.101-5`→`38101-5`；可选 `:名称` 用于输出命名
- 系列按前两位自动推断，任意系列可用（38xxx→38_series）

## 输出结构

```
3gpp-specs/raw_sources/
├── pdfs/          # ETSI官方PDF，命名 <38.xxx>_<名称>_V<版本>.pdf
└── specs/         # 转换后的md
    ├── _incoming/ # 新下载md暂存区
    └── images/    # 图片，按md文件名分目录 (eq-NNNN公式 / fig-NNNN插图)
```

md 超 2MB 按标题边界拆 `_partN.md`，各 part 共用 images/。**整理协议时须把 images/ 随 md 一起移动**。

## 转换特性

- OMML 公式(`m:oMath`) → `$...$` / `$$...$$` LaTeX（分数/上下标/求和/根号/矩阵/分段函数）
- OLE 公式(Equation.3/MathType)/Visio 图 → 提取 `eq-NNNN.*` / `fig-NNNN.*` 到 images/
- 表格 → GFM 管道表，`|` 自动转义

## 维护与同步（防漂移）

本 skill（`.claude/skills/3gpp-spec-downloader/`）是**仓库内唯一源头**。与之相关的镜像：

| 镜像 | 方向 | 触发 |
|------|------|------|
| `~/.workbuddy/skills/3gpp-spec-downloader/`（用户级） | 源头→镜像 单向拷贝 | 本项目脚本更新后 |
| `.workbuddy/skills/3gpp-spec-downloader`（项目级 symlink） | 指向实体 | 无需维护 |

```bash
# 本 skill 脚本更新后同步到用户级镜像（下载器+公式转换器两个文件即可）
cp .claude/skills/3gpp-spec-downloader/scripts/{download_and_convert.py,omml2latex.py} \
   ~/.workbuddy/skills/3gpp-spec-downloader/scripts/
```

用户级镜像仅服务于**仓库外**（无 .git 环境）使用；仓库内一律走本 skill。

## 已知限制

- FTP 模式只处理 `.docx`；旧式二进制 `.doc` 跳过并警告（需 libreoffice）
- 部分协议在某 Release 不存在（新协议 R19 首次出现），目录 404 报失败
- 批量任务单个失败不中断，结束输出汇总；PDF 下载失败自动重试3次(指数退避)，仍失败清理残档
