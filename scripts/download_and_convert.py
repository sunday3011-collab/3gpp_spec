#!/usr/bin/env python3
"""
下载缺失的3GPP协议(doc/docx)并用纯标准库转换为Markdown。

合并自:
  - skill fetch_spec.py 的「目录列举 + 版本选择 + 下载解压」逻辑
  - 本地 convert.py 的「纯标准库 docx -> markdown」转换 (无需 pandoc/libreoffice)

支持:
  - 38/37/24 等任意系列 (按编号前两位推断 <xx>_series 目录)
  - 带子编号的协议 (如 38101-5 -> 目录 38.101-5)
  - 一个zip内多个docx自动合并

用法:
  python3 download_and_convert.py 38413:NGAP 24501:NAS_5GS ...
  (每项格式 <编号>[:<名称>]，编号去掉点，如 38.101-5 写作 38101-5)
"""

import os
import re
import shutil
import sys
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

# 路径从脚本自身位置推导，仓库迁移后仍可用 (scripts/ 在仓库根下一层)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 下载得到的 md 落入 raw_sources 的暂存区 _incoming，供后续整理/ingest；可用环境变量 OUT_MD_DIR 覆盖
OUT_MD_DIR = os.environ.get(
    "OUT_MD_DIR", os.path.join(REPO, "3gpp-wiki", "raw_sources", "specs", "_incoming"))
WORK_ROOT = os.path.join(REPO, "downloads")  # 临时工作区，运行结束自动清理
BASE_URL_TEMPLATE = "https://www.3gpp.org/ftp/specs/archive/{series}_series"
RELEASE_LETTERS = {19: "j", 18: "i", 17: "h", 16: "g", 15: "f"}

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


# ---------- 下载 / 选版 (源自 fetch_spec.py) ----------

def spec_to_dirname(spec):
    """38413 -> 38.413 ; 38101-5 -> 38.101-5 ; 24301 -> 24.301"""
    return spec[:2] + "." + spec[2:]


def fetch_dir_listing(spec):
    series = spec[:2]
    dir_name = spec_to_dirname(spec)
    url = f"{BASE_URL_TEMPLATE.format(series=series)}/{dir_name}/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def find_best_zip(html, spec, preferred_letters):
    pattern = re.escape(spec) + r"-([0-9a-z]{3})\.zip"
    matches = [m.lower() for m in re.findall(pattern, html, flags=re.IGNORECASE)]
    for letter in preferred_letters:
        candidates = sorted(m for m in matches if m.startswith(letter))
        if candidates:
            return f"{spec}-{candidates[-1]}.zip", candidates[-1]
    return None, None


def download_and_extract(zip_url, workdir):
    """下载zip并解压所有 doc/docx，返回路径列表"""
    zip_path = os.path.join(workdir, "spec.zip")
    req = urllib.request.Request(zip_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(zip_path, "wb") as f:
        shutil.copyfileobj(resp, f)
    out = []
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith((".doc", ".docx"))]
        if not names:
            raise RuntimeError("zip中未找到doc/docx文件")
        for n in sorted(names):
            zf.extract(n, workdir)
            out.append(os.path.join(workdir, n))
    os.remove(zip_path)
    return out


# ---------- 转换 (源自 convert.py, 纯标准库) ----------

def get_text(elem):
    return "".join(t.text for t in elem.findall(".//w:t", NS) if t.text)


def get_heading_level(para):
    pPr = para.find("w:pPr", NS)
    if pPr is None:
        return 0
    pStyle = pPr.find("w:pStyle", NS)
    if pStyle is None:
        return 0
    val = pStyle.get("{%s}val" % NS["w"]) or ""
    m = re.match(r"Heading(\d+)", val, re.I)
    if m:
        return int(m.group(1))
    if "heading" in val.lower():
        for i in range(1, 7):
            if str(i) in val:
                return i
    return 0


def table_to_md(table_elem):
    rows = []
    for tr in table_elem.findall("w:tr", NS):
        cells = []
        for tc in tr.findall("w:tc", NS):
            txt = re.sub(r"\s+", " ", get_text(tc).strip())
            cells.append(txt.replace("|", "\\|"))
        rows.append(cells)
    if not rows:
        return ""
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    md = "| " + " | ".join(rows[0]) + " |\n"
    md += "| " + " | ".join(["---"] * ncol) + " |\n"
    for row in rows[1:]:
        md += "| " + " | ".join(row) + " |\n"
    return md


def convert_docx_to_md(docx_path):
    with zipfile.ZipFile(docx_path, "r") as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find("w:body", NS)
    if body is None:
        return ""
    lines = []
    for child in body:
        if child.tag.endswith("}p"):
            level = get_heading_level(child)
            text = get_text(child).strip()
            if not text:
                lines.append("")
            elif level > 0:
                lines.append("#" * min(level, 6) + " " + text)
            else:
                lines.append(text)
        elif child.tag.endswith("}tbl"):
            lines.append(table_to_md(child))
            lines.append("")
    # 折叠多余空行
    result, prev_blank = [], False
    for ln in lines:
        blank = (ln.strip() == "")
        if blank and prev_blank:
            continue
        result.append(ln)
        prev_blank = blank
    return "\n".join(result)


# ---------- 主流程 ----------

def process(spec, name, release=19):
    preferred = [RELEASE_LETTERS[release], RELEASE_LETTERS.get(release - 1)]
    preferred = [p for p in preferred if p]
    print(f"\n[处理] {spec} ({name})")
    try:
        html = fetch_dir_listing(spec)
    except Exception as e:
        print(f"  [失败] 无法访问目录: {e}")
        return None
    fname, ver = find_best_zip(html, spec, preferred)
    if not fname:
        print(f"  [失败] 未找到 {preferred} 前缀版本")
        return None
    print(f"  选定版本: {fname}")

    workdir = os.path.join(WORK_ROOT, spec)
    shutil.rmtree(workdir, ignore_errors=True)
    os.makedirs(workdir, exist_ok=True)
    try:
        series = spec[:2]
        zip_url = f"{BASE_URL_TEMPLATE.format(series=series)}/{spec_to_dirname(spec)}/{fname}"
        print(f"  下载: {zip_url}")
        docs = download_and_extract(zip_url, workdir)
        if any(d.lower().endswith(".doc") for d in docs):
            print("  [警告] 含旧式 .doc 二进制格式，无 libreoffice 无法转换，跳过这些文件")
        docx_list = [d for d in docs if d.lower().endswith(".docx")]
        if not docx_list:
            print("  [失败] 无 .docx 文件可转换 (可能为旧式 .doc)")
            return None
        parts = []
        for d in docx_list:
            print(f"  转换: {os.path.basename(d)}")
            parts.append(convert_docx_to_md(d))
        md = "\n\n---\n\n".join(parts)
        out_name = f"{spec_to_dirname(spec)}_{name}_{ver}.md"
        out_path = os.path.join(OUT_MD_DIR, out_name)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        kb = os.path.getsize(out_path) / 1024
        print(f"  [完成] -> {out_name} ({kb:.1f} KB)")
        return out_path
    except Exception as e:
        print(f"  [失败] {e}")
        return None
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main():
    os.makedirs(OUT_MD_DIR, exist_ok=True)
    os.makedirs(WORK_ROOT, exist_ok=True)
    results = {}
    for arg in sys.argv[1:]:
        spec, _, name = arg.partition(":")
        results[spec] = process(spec, name or spec)
    print("\n==== 汇总 ====")
    for spec, path in results.items():
        print(f"  {spec}: {'成功' if path else '失败'}")
    shutil.rmtree(WORK_ROOT, ignore_errors=True)


if __name__ == "__main__":
    main()
