#!/usr/bin/env python3
"""
增量入库：下载若干 3GPP 协议并登记进 3gpp-wiki。

复用 download_and_convert 的下载/转换逻辑；随后：
  - 原文移入 raw_sources/specs/<raw_subdir>/
  - 生成 wiki/compiled/<comp_subdir>/<page>.md 概览页 (frontmatter+职责+章节目录+原文链接)
  - 追加行到 wiki/index.md 对应表 (协议层 / 概念，不重建)
  - 追加 wiki/log.md (append-only)

在 ENTRIES 中配置要入库的协议即可。
"""

import os
import re
import shutil

import download_and_convert as dl  # 同目录复用

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(REPO, "3gpp-wiki")
RAW = os.path.join(WIKI, "raw_sources", "specs")
COMPILED = os.path.join(WIKI, "wiki", "compiled")
INDEX = os.path.join(WIKI, "wiki", "index.md")
LOG = os.path.join(WIKI, "wiki", "log.md")
TODAY = "2026-06-21"

PROTOCOL_LAYERS = {"PHY", "MAC", "RLC", "PDCP", "SDAP", "RRC", "NAS"}

# 本次要入库的协议
# code(去点) | name | spec | title | layer | comp_subdir | raw_subdir | keywords | duty
ENTRIES = [
    ("38104", "BS_RF", "TS38.104", "NR; Base Station (BS) radio transmission and reception",
     "concept", "concepts", "TS38.104_BS_RF", "RF,gNB,基站射频,RAN4",
     "gNB 基站射频收发要求（发射/接收指标），UE 侧 38.101 的对应。【RAN4】"),
    ("38401", "NG-RAN_Architecture", "TS38.401", "NG-RAN; Architecture description",
     "concept", "concepts", "TS38.401_NG-RAN_Architecture", "架构,CU/DU,CU-CP/CU-UP,接口划分",
     "NG-RAN 架构：CU/DU、CU-CP/CU-UP 切分与接口划分。"),
    ("37340", "Multi_Connectivity", "TS37.340", "E-UTRA and NR; Multi-connectivity; Overall description; Stage 2",
     "concept", "concepts", "TS37.340_Multi_Connectivity", "EN-DC,NR-DC,多连接,DC",
     "多连接（EN-DC / NR-DC）总体描述 Stage 2，UE 与 gNB 双侧。"),
    ("23501", "5GS_Architecture", "TS23.501", "System architecture for the 5G System (5GS); Stage 2",
     "concept", "concepts", "TS23.501_5GS_Architecture", "5GC,系统架构,QoS,PDU会话,切片",
     "5G 系统架构（网元、QoS、PDU 会话、切片）Stage 2。【SA2 核心网，接入网参考上下文】"),
    ("23502", "5GS_Procedures", "TS23.502", "Procedures for the 5G System (5GS); Stage 2",
     "concept", "concepts", "TS23.502_5GS_Procedures", "5GC,流程,注册,会话建立,移动性",
     "5G 系统流程（注册、会话建立/修改、移动性）Stage 2。【SA2 核心网】"),
]


def extract_toc(md_path, cap=40):
    toc, seen = [], set()
    with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("# ") and not line.startswith("## "):
                h = re.sub(r"^(\d+(?:\.\d+)*)([A-Za-z])", r"\1 \2", line[2:].strip())
                if h and h not in seen and len(h) < 120:
                    seen.add(h)
                    toc.append(h)
            if len(toc) >= cap:
                break
    return toc


def insert_index_row(lines, section_header, new_row, key):
    """在 index.md 指定 section 的表格里插入一行并按首列排序。"""
    i = lines.index(section_header)
    # 跳过表头(2行)，定位数据区
    start = i + 3
    end = start
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    rows = lines[start:end]
    if any(key in r for r in rows):
        return lines  # 已存在，幂等
    rows.append(new_row)
    rows.sort()
    return lines[:start] + rows + lines[end:]


def main():
    os.makedirs(dl.OUT_MD_DIR, exist_ok=True)
    with open(INDEX, "r", encoding="utf-8") as f:
        idx_lines = f.read().split("\n")

    done = []
    for code, name, spec, title, layer, comp_subdir, raw_subdir, kw, duty in ENTRIES:
        out = dl.process(code, name)  # 下载+转换到 _incoming
        if not out:
            print(f"[失败] {spec} 下载失败，跳过")
            continue
        fname = os.path.basename(out)
        release = {"j": "Rel-19", "i": "Rel-18"}.get(
            (re.search(r"_([a-z])\d{2}\.md$", fname) or [None, "j"])[1], "Rel-19")

        # 移入 raw_sources
        rdir = os.path.join(RAW, raw_subdir)
        os.makedirs(rdir, exist_ok=True)
        dst = os.path.join(rdir, fname)
        shutil.move(out, dst)
        raw_link = fname[:-3]

        # 生成概览页
        toc = extract_toc(dst)
        toc_md = "\n".join(f"- {t}" for t in toc) if toc else "（未抽取到章节）"
        page = f"""---
layer: {layer}
spec: {spec}
release: {release}
authored_by: llm
llm_can_overwrite: true
last_updated: {TODAY}
---

# {spec} — {title}

- **层**：{layer}
- **职责**：{duty}
- **Release**：{release}
- **原始文档**：[[{raw_link}]] （`raw_sources/specs/{raw_subdir}/{fname}`）

## 规范章节目录
{toc_md}

---
> 本页为结构化登记概览，未展开逐条技术细节。需要细节时对原文执行 `ingest`。
"""
        page_name = f"{spec.replace('TS', 'TS')}_{name}.md"
        out_dir = os.path.join(COMPILED, comp_subdir)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, page_name), "w", encoding="utf-8") as f:
            f.write(page)
        pn = page_name[:-3]

        # 追加 index 行
        if layer in PROTOCOL_LAYERS:
            row = f"| [[{pn}]] | {layer} | {spec} | {release} | {TODAY} |"
            idx_lines = insert_index_row(idx_lines, "## 协议层页面", row, f"[[{pn}]]")
        else:
            row = f"| [[{pn}]] | concept | {kw} |"
            idx_lines = insert_index_row(idx_lines, "## 概念页面", row, f"[[{pn}]]")
        done.append((spec, pn))
        print(f"[入库] {spec} -> compiled/{comp_subdir}/{page_name}  ({release})")

    # 写回 index（更新日期）
    for n, l in enumerate(idx_lines):
        if l.startswith("最后更新："):
            idx_lines[n] = f"最后更新：{TODAY}"
            break
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write("\n".join(idx_lines))

    # 追加 log
    if done:
        names = "、".join(s for s, _ in done)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"\n## [{TODAY}] ingest | 增量入库 {names} | "
                    f"影响页面：{len(done)} 个概览页 + index.md\n")
    shutil.rmtree(dl.WORK_ROOT, ignore_errors=True)
    print(f"\n完成：入库 {len(done)} 个 spec")


if __name__ == "__main__":
    main()
