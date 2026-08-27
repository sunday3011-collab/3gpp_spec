#!/usr/bin/env python3
"""gen_section_index.py — 扫描 raw_sources/specs/ 全部原文标题，生成 wiki/sections.tsv。

列格式（TSV）：spec clause level title file start_line end_line
- file 为相对 workspace 根的路径（raw_sources/specs/<name>.md）
- level = '#' 的数量
- clause 支持数字（1 / 4.5.4.1 / 5.1.1a）、Annex 编号（A.2.1）、以及无编号标题（Foreword）
- 跳过 *_partNN.md 分片（与完整文件内容重复）与 README
"""

import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
SPECS_DIR = WORKSPACE / "raw_sources" / "specs"
OUT_TSV = WORKSPACE / "wiki" / "sections.tsv"

# "# 1Scope" / "# 5MAC procedures" / "### 5.1.1aInitialization" / "# A.1Introduction"
CLAUSE_RE = re.compile(r"^(\d+(?:\.\d+)*[a-z]?|[A-Z](?:\.\d+)*[a-z]?)\s*(.*)$")
# "###### Annex A (informative):Change history"
ANNEX_RE = re.compile(r"^(Annex\s+[A-Z].*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s?(.*)$")
SPEC_RE = re.compile(r"^(\d+\.\d+(?:-\d+)?)_")


def spec_of(filename: str) -> str | None:
    m = SPEC_RE.match(filename)
    return f"TS{m.group(1)}" if m else None


def parse_file(path: Path, rel_path: str, spec: str) -> list[list[str]]:
    rows: list[list[str]] = []
    headings: list[tuple[str, str, int, int]] = []  # (clause, title, level, line_no)
    with open(path, encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, 1):
            m = HEADING_RE.match(line.rstrip("\n"))
            if not m:
                continue
            level = len(m.group(1))
            text = m.group(2).strip()
            if not text:
                continue
            cm = CLAUSE_RE.match(text)
            if cm:
                clause, title = cm.group(1), cm.group(2).strip()
            else:
                am = ANNEX_RE.match(text)
                clause, title = ("", am.group(1)) if am else ("", text)
            headings.append((clause, title, level, line_no))

    total_lines = line_no  # 最后一行行号 = 文件总行数
    for i, (clause, title, level, start) in enumerate(headings):
        end = headings[i + 1][3] - 1 if i + 1 < len(headings) else total_lines
        rows.append([spec, clause, str(level), title, rel_path, str(start), str(end)])
    return rows


def main() -> int:
    if not SPECS_DIR.is_dir():
        print(f"error: {SPECS_DIR} not found", file=sys.stderr)
        return 1

    files = sorted(
        f for f in SPECS_DIR.glob("*.md")
        if not re.search(r"_part\d+\.md$", f.name) and f.name != "README.md"
    )
    all_rows: list[list[str]] = []
    for f in files:
        spec = spec_of(f.name)
        if not spec:
            print(f"warn: 无法从文件名提取 spec 编号，跳过 {f.name}", file=sys.stderr)
            continue
        rel = f"raw_sources/specs/{f.name}"
        rows = parse_file(f, rel, spec)
        all_rows.extend(rows)

    with open(OUT_TSV, "w", encoding="utf-8") as f:
        f.write("spec\tclause\tlevel\ttitle\tfile\tstart_line\tend_line\n")
        for row in all_rows:
            f.write("\t".join(row) + "\n")

    print(f"OK: {len(files)} 个 spec 文件 → {len(all_rows)} 条 clause 记录 → {OUT_TSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
