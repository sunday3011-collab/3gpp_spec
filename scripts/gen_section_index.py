#!/usr/bin/env python3
"""
扫描 raw_sources/specs/ 下全部协议原文，生成章节地址索引 wiki/sections.tsv。

每个标题一行，记录其 clause 编号与在原文中的行号区间，使任意 clause 可被随机访问
（只读对应几十行切片，而非整篇巨型原文）。grep 即可用，不依赖模型能力。

列：spec  clause  level  title  file  start_line  end_line
- level：标题层级（# 的个数）
- 区间含本 clause 及其全部子 clause（start..end，1-based 闭区间）
- file：相对仓库根的路径
"""

import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPECS_ROOT = os.path.join(REPO, "3gpp-wiki", "raw_sources", "specs")
OUT = os.path.join(REPO, "3gpp-wiki", "wiki", "sections.tsv")

HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
# clause: 数字式(可带尾字母,如 5.1.1a) 或 附录式(A.4.1)
CLAUSE = re.compile(r"^(\d+(?:\.\d+)*[a-z]?|[A-Z]\.\d+(?:\.\d+)*)(.*)$")


def spec_from_filename(fname):
    m = re.match(r"(\d{2}\.\d+(?:-\d+)?)", fname)
    return "TS" + m.group(1) if m else fname


def scan_file(path):
    """返回 [(level, clause, title, start, end), ...]"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    heads = []  # (lineno, level, clause, title)
    for i, line in enumerate(lines, 1):
        m = HEADING.match(line)
        if not m:
            continue
        level = len(m.group(1))
        text = m.group(2).strip()
        cm = CLAUSE.match(text)
        if cm:
            clause, title = cm.group(1), cm.group(2).strip()
        else:
            clause, title = "", text
        heads.append((i, level, clause, title))
    # 计算每个标题的 end：下一个 level<=本级 的标题前一行，否则文件末尾
    total = len(lines)
    out = []
    for idx, (ln, lvl, clause, title) in enumerate(heads):
        end = total
        for ln2, lvl2, _, _ in heads[idx + 1:]:
            if lvl2 <= lvl:
                end = ln2 - 1
                break
        out.append((lvl, clause, title, ln, end))
    return out


def main():
    rows = []
    for root, _, files in os.walk(SPECS_ROOT):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            path = os.path.join(root, fn)
            spec = spec_from_filename(fn)
            rel = os.path.relpath(path, REPO)
            for lvl, clause, title, start, end in scan_file(path):
                title = title.replace("\t", " ")
                rows.append((spec, clause, str(lvl), title, rel, str(start), str(end)))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("spec\tclause\tlevel\ttitle\tfile\tstart_line\tend_line\n")
        for r in rows:
            f.write("\t".join(r) + "\n")

    specs = sorted({r[0] for r in rows})
    print(f"已生成 {OUT}")
    print(f"  {len(rows)} 个章节，覆盖 {len(specs)} 个 spec")


if __name__ == "__main__":
    main()
