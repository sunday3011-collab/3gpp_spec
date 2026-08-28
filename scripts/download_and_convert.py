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
  - 转换后单文件 > 2MB 自动按标题边界拆分为多份 < 2MB 的文件
    (<stem>_part1.md, <stem>_part2.md, ...), 原文件删除; 图片引用不变,
    各 part 共用同一 images/<stem>/ 目录。
  - 从 ETSI deliver 站点直接下载官方发布的 PDF 最新版
    (HTML 目录列表发现所有版本目录，按版本号元组排序取最高)。

用法:
  python3 download_and_convert.py 38413:NGAP 24501:NAS_5GS ...
  (每项格式 <编号>[:<名称>]，编号去掉点，如 38.101-5 写作 38101-5)

  # 对目录下已有 md 文件按 2MB 上限拆分 (不重新下载)
  python3 download_and_convert.py --split 3gpp-wiki-v2/raw_sources/specs

  # 从 ETSI 下载最新 PDF，落入 3gpp-wiki-v2/raw_sources/pdfs/
  python3 download_and_convert.py --pdf 38331:RRC 23501:5GS_Architecture 38101-1:RF_FR1
"""

import os
import re
import shutil
import sys
import time
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omml2latex import omml_to_latex

# 路径从脚本自身位置推导，仓库迁移后仍可用 (scripts/ 在仓库根下一层)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 下载得到的 md 落入 raw_sources 的暂存区 _incoming，供后续整理/ingest；可用环境变量 OUT_MD_DIR 覆盖
OUT_MD_DIR = os.environ.get(
    "OUT_MD_DIR", os.path.join(REPO, "3gpp-wiki-v2", "raw_sources", "specs", "_incoming"))
WORK_ROOT = os.path.join(REPO, "downloads")  # 临时工作区，运行结束自动清理
BASE_URL_TEMPLATE = "https://www.3gpp.org/ftp/specs/archive/{series}_series"
RELEASE_LETTERS = {19: "j", 18: "i", 17: "h", 16: "g", 15: "f"}

# 单个 md 文件大小上限 (字节): 超过则按标题边界拆分为多份 < 上限的文件
MAX_MD_BYTES = 2 * 1024 * 1024  # 2 MB
# 拆分目标略小于上限, 留出余量确保每个 part 严格 < 2 MB
SPLIT_TARGET_BYTES = MAX_MD_BYTES - 4 * 1024

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}


def local(tag):
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


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


# ---------- 转换 (纯标准库: OMML公式->LaTeX + OLE对象/图片提取) ----------

class ImageSink:
    """跨 docx 部件共享的图片提取器: OLE公式(eq-)/图(fig-)统一编号落盘"""

    def __init__(self, images_dir):
        self.images_dir = images_dir
        self.counter = 0
        os.makedirs(images_dir, exist_ok=True)
        # md 与 images/ 同级, 引用形如 images/<stem>/eq-0001.wmf
        self.rel_prefix = os.path.join(
            os.path.basename(os.path.dirname(images_dir))
            or "images", os.path.basename(images_dir))

    def save(self, zf, media_target, is_equation):
        """从 docx zip 提取 media 文件, 返回相对 md 的引用路径"""
        try:
            data = zf.read("word/" + media_target.lstrip("/"))
        except KeyError:
            return None
        self.counter += 1
        prefix = "eq" if is_equation else "fig"
        ext = os.path.splitext(media_target)[1].lower() or ".bin"
        fname = "%s-%04d%s" % (prefix, self.counter, ext)
        with open(os.path.join(self.images_dir, fname), "wb") as f:
            f.write(data)
        return "%s/%s" % (self.rel_prefix, fname)


class DocxContext:
    """单个 docx 的解析上下文: rels 映射 + zip 句柄"""

    def __init__(self, zf, sink):
        self.zf = zf
        self.sink = sink
        self.rels = {}
        try:
            rel_root = ET.fromstring(zf.read("word/_rels/document.xml.rels"))
        except KeyError:
            return
        for rel in rel_root:
            rid = rel.get("Id")
            target = rel.get("Target") or ""
            if rel.get("TargetMode") != "External" and "media" in target:
                self.rels[rid] = target

    def object_image_md(self, obj_elem):
        """w:object (OLE 公式/图) -> markdown 图片引用; ProgID 区分公式与图"""
        imgdata, progid = None, ""
        for e in obj_elem.iter():
            lt = local(e.tag)
            if lt == "imagedata" and imgdata is None:
                imgdata = e
            elif lt == "OLEObject" and not progid:
                progid = (e.get("ProgID")
                          or e.get("{%s}ProgID" % NS["o"]) or "")
        if imgdata is None:
            return ""
        rid = imgdata.get("{%s}id" % NS["r"])
        target = self.rels.get(rid)
        if not target:
            return ""
        is_eq = progid.startswith("Equation") or "DSMT" in progid
        ref = self.sink.save(self.zf, target, is_eq)
        return "![](%s)" % ref if ref else ""

    def drawing_image_md(self, drawing_elem):
        """w:drawing (内嵌图片) -> markdown 图片引用"""
        for e in drawing_elem.iter():
            if local(e.tag) == "blip":
                rid = e.get("{%s}embed" % NS["r"])
                target = self.rels.get(rid)
                if target:
                    ref = self.sink.save(self.zf, target, False)
                    if ref:
                        return "![](%s)" % ref
        return ""


SKIP_TAGS = {"pPr", "rPr", "bookmarkStart", "bookmarkEnd", "proofErr",
             "sectPr", "commentRangeStart", "commentRangeEnd"}


def _run_content(run_elem, out, ctx):
    """处理 w:r 的子元素: 文本 / OLE对象(w:object) / 图片(w:drawing)"""
    for c in run_elem:
        lt = local(c.tag)
        if lt == "t":
            out.append(c.text or "")
        elif lt in ("tab", "br"):
            out.append(" ")
        elif lt == "object":
            out.append(ctx.object_image_md(c))
        elif lt == "drawing":
            out.append(ctx.drawing_image_md(c))
        elif lt == "pict":  # VML 图片 (旧格式)
            for e in c.iter():
                if local(e.tag) == "imagedata":
                    rid = e.get("{%s}id" % NS["r"])
                    target = ctx.rels.get(rid)
                    if target:
                        ref = ctx.sink.save(ctx.zf, target, False)
                        if ref:
                            out.append("![](%s)" % ref)
                    break


def para_to_md(para, ctx):
    """顺序遍历段落: 文本/OMML公式/OLE对象图片, 保持文档内出现顺序"""
    out = []

    def walk(elem):
        for child in elem:
            lt = local(child.tag)
            if lt in SKIP_TAGS:
                continue
            if lt == "r":
                _run_content(child, out, ctx)
            elif lt == "oMath":
                latex = omml_to_latex(child)
                if latex:
                    out.append("$%s$" % latex)
            elif lt == "oMathPara":
                parts = [omml_to_latex(m) for m in child
                         if local(m.tag) == "oMath"]
                parts = [p for p in parts if p]
                if parts:
                    out.append("\n$$%s$$\n" % " \\quad ".join(parts))
            elif lt == "AlternateContent":
                # OMML 公式常包在 mc:AlternateContent 内 (Fallback 是 OLE 旧形态)
                choice = next((c for c in child if local(c.tag) == "Choice"),
                              None)
                if choice is not None:
                    walk(choice)
            elif lt == "object":
                out.append(ctx.object_image_md(child))
            elif lt == "drawing":
                out.append(ctx.drawing_image_md(child))
            else:
                walk(child)

    walk(para)
    return "".join(out)


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


def table_to_md(table_elem, ctx):
    rows = []
    for tr in table_elem.findall("w:tr", NS):
        cells = []
        for tc in tr.findall("w:tc", NS):
            cell_parts = [para_to_md(p, ctx).strip()
                          for p in tc.findall("w:p", NS)]
            txt = re.sub(r"\s+", " ", " ".join(x for x in cell_parts if x))
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


def convert_docx_to_md(docx_path, sink):
    """转换单个 docx: OMML 公式转 LaTeX, OLE公式/图提取到 images 目录"""
    with zipfile.ZipFile(docx_path, "r") as z:
        root = ET.fromstring(z.read("word/document.xml"))
        ctx = DocxContext(z, sink)
        body = root.find("w:body", NS)
        if body is None:
            return ""
        lines = []
        for child in body:
            if child.tag.endswith("}p"):
                level = get_heading_level(child)
                text = para_to_md(child, ctx).strip()
                if not text:
                    lines.append("")
                elif level > 0:
                    lines.append("#" * min(level, 6) + " " + text)
                else:
                    # 整段只有一条公式 -> 升级为块级 $$ 展示
                    if (text.startswith("$") and text.endswith("$")
                            and text.count("$") == 2
                            and "\n" not in text):
                        text = "$$%s$$" % text[1:-1]
                    lines.append(text)
            elif child.tag.endswith("}tbl"):
                lines.append(table_to_md(child, ctx))
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


# ---------- 大文件拆分 (按标题边界, 每份 < 2 MB) ----------

def _byte_len(s):
    return len(s.encode("utf-8"))


def _split_by_paragraphs(content, max_size):
    """最后手段: 按空行段落拆分; 单段仍超限则按字节硬切。"""
    paras = re.split(r"(\n\n+)", content)
    parts, cur, cur_len = [], "", 0
    for p in paras:
        plen = _byte_len(p)
        if plen > max_size:
            if cur:
                parts.append(cur)
                cur, cur_len = "", 0
            # 单段超限, 按字节硬切 (解码边界容忍)
            b = p.encode("utf-8")
            for i in range(0, len(b), max_size):
                parts.append(b[i:i + max_size].decode("utf-8", errors="ignore"))
        elif cur_len + plen > max_size:
            if cur:
                parts.append(cur)
            cur, cur_len = p, plen
        else:
            cur += p
            cur_len += plen
    if cur:
        parts.append(cur)
    return parts


def _split_md_segments(content, max_size, level=1):
    """递归按标题边界拆分, 每个 part 字节数 <= max_size。"""
    if _byte_len(content) <= max_size:
        return [content]
    # 仅匹配恰好 level 级标题 (# level=1, ## level=2, ...)
    pattern = re.compile(r"(?m)^#{%d} [^\n]*$" % level)
    matches = list(pattern.finditer(content))
    if not matches:
        if level < 6:
            return _split_md_segments(content, max_size, level + 1)
        return _split_by_paragraphs(content, max_size)

    segments = []
    if matches[0].start() > 0:
        preamble = content[:matches[0].start()]
        if preamble.strip():
            segments.append(preamble)
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        seg = content[start:end]
        if seg.strip():
            segments.append(seg)

    parts, cur, cur_len = [], "", 0
    for seg in segments:
        seg_len = _byte_len(seg)
        if seg_len > max_size:
            # 单个标题段仍超限: 先落盘当前 part, 再下钻一级拆分该段
            if cur:
                parts.append(cur)
                cur, cur_len = "", 0
            parts.extend(_split_md_segments(seg, max_size, level + 1))
        elif cur_len + seg_len > max_size:
            if cur:
                parts.append(cur)
            cur, cur_len = seg, seg_len
        else:
            cur += seg
            cur_len += seg_len
    if cur:
        parts.append(cur)
    return parts


_TITLE_RE = re.compile(r"3GPP TS \S+ V\S+ \([0-9-]+\)")


def _ensure_leading_heading(part_text, fallback_title):
    """若 part 首个非空行不是 markdown 标题, 在开头补一个 H1。
    标题优先从扉页正文提取 3GPP TS 标识 (如 3GPP TS 38.133 V19.5.0 (2026-06)),
    提取不到则用 fallback_title, 保证每个 part 都以标题起首。"""
    for line in part_text.splitlines():
        if line.strip():
            if line.lstrip().startswith("#"):
                return part_text
            break
    m = _TITLE_RE.search(part_text)
    title = m.group(0) if m else fallback_title
    return "# %s\n\n%s" % (title, part_text)


def split_md_file(path, max_size=MAX_MD_BYTES):
    """
    若 path 超过 max_size 字节, 按标题边界拆分为多份 < max_size 的文件
    <stem>_part1.md, <stem>_part2.md, ...; 原文件删除。
    图片引用 (images/<stem>/...) 在各 part 中保持不变, 共用同一图片目录。
    每个 part 起首若非标题则自动补 H1 (扉页/前言前导内容)。
    返回新文件路径列表 (未拆分则返回 [path])。
    """
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if _byte_len(content) <= max_size:
        return [path]
    parts = _split_md_segments(content, SPLIT_TARGET_BYTES, level=1)
    if len(parts) <= 1:
        # 极端情况: 按标题拆不出多份, 用段落级硬切兜底
        parts = _split_by_paragraphs(content, SPLIT_TARGET_BYTES)
    if len(parts) <= 1:
        return [path]
    stem, _ = os.path.splitext(path)
    fallback = os.path.basename(stem)
    new_paths = []
    for i, part in enumerate(parts, 1):
        new_path = "%s_part%d.md" % (stem, i)
        part = _ensure_leading_heading(part, fallback)
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(part)
        new_paths.append(new_path)
    os.remove(path)
    return new_paths


def split_dir(dir_path):
    """对目录下所有 .md 文件 (递归) 执行拆分, 仅处理超过上限的文件。"""
    count = 0
    for root, _, files in os.walk(dir_path):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            p = os.path.join(root, fn)
            if os.path.getsize(p) <= MAX_MD_BYTES:
                continue
            print("[拆分] %s (%.2f MB)" % (p, os.path.getsize(p) / 1024 / 1024))
            results = split_md_file(p)
            if len(results) > 1:
                count += 1
                for r in results:
                    print("  -> %s (%.1f KB)" % (os.path.basename(r),
                                                 os.path.getsize(r) / 1024))
    print("\n==== 拆分汇总: %d 个文件被拆分 ====" % count)
    return count


# ---------- ETSI PDF 下载 (官方发布 PDF, 版本目录最新优先) ----------

ETSI_DELIVER_BASE = "https://www.etsi.org/deliver/etsi_TS"
# PDF 输出目录: 与 specs/ 同级, 方便与 raw_sources/ 内其他原始材料一起管理
PDF_OUT_DIR = os.environ.get(
    "PDF_OUT_DIR", os.path.join(REPO, "3gpp-wiki-v2", "raw_sources", "pdfs"))

_VER_DIR_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)_\d+$")   # 例: 19.03.00_60


def _spec_to_etsi(spec_str):
    """Turn CLI spec (e.g. "38331", "38101-1") into (etsi_code, range_dir, dotted).

    38.331   -> code=138331,    range=138300_138399
    38.101-1 -> code=13810101,  range=138100_138199
    23.501   -> code=123501,    range=123500_123599
    """
    dotted = spec_to_dirname(spec_str)   # "38.101-1"
    m = re.match(r"^(\d{2})\.(\d+)(?:-(\d+))?$", dotted)
    if not m:
        raise ValueError(f"无法解析协议编号: {spec_str!r}")
    xx, yyy, part = m.group(1), m.group(2), m.group(3)
    etsi_code = "1" + xx + yyy
    if part:
        etsi_code += "%02d" % int(part)
    floor = (int(yyy) // 100) * 100
    range_dir = "1%s%03d_1%s%03d" % (xx, floor, xx, floor + 99)
    return etsi_code, range_dir, dotted


def _fetch_etsi_links(url, suffix=None):
    """抓取 ETSI 目录列表页面, 返回链接名列表(目录/文件)。

    ETSI deliver 页面示例:
      <A HREF="/deliver/etsi_TS/138300_138399/138331/19.03.00_60/">19.03.00_60</A>
      <A HREF="/deliver/.../ts_138331v190300p.pdf">ts_138331v190300p.pdf</A>
    从 href 中取路径 basename, 跳过父目录和不匹配 suffix 的条目。
    """
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    # HREF 大小写不敏感; href 可能是绝对路径
    hrefs = re.findall(r"""href\s*=\s*["']([^"']+)["']""", html, re.IGNORECASE)
    results = []
    for h in hrefs:
        name = os.path.basename(h.rstrip("/"))
        if not name or "[To Parent" in name:
            continue
        if suffix and not name.endswith(suffix):
            continue
        if name not in results:
            results.append(name)
    return results


def _pick_latest_version(dir_names):
    """按 (major, minor, patch) 元组排序, 返回版本最高的目录名。"""
    best = None  # ((major, minor, patch), dir_name)
    for d in dir_names:
        m = _VER_DIR_RE.match(d)
        if not m:
            continue
        ver = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if best is None or ver > best[0]:
            best = (ver, d)
    return best[1] if best else None


def _ver_dir_to_version(ver_dir):
    """'19.03.00_60' -> (19, 3, 0)"""
    m = _VER_DIR_RE.match(ver_dir)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def process_pdf(spec, name, out_dir=PDF_OUT_DIR):
    """下载单个 spec 的 ETSI 官方最新 PDF。

    返回落地文件路径或 None。已有同名文件时跳过(不变更)。
    """
    print(f"\n[PDF] {spec} ({name})")
    try:
        etsi_code, range_dir, dotted = _spec_to_etsi(spec)
    except ValueError as e:
        print(f"  [失败] {e}")
        return None
    spec_url = f"{ETSI_DELIVER_BASE}/{range_dir}/{etsi_code}/"
    try:
        ver_dirs = _fetch_etsi_links(spec_url)
    except Exception as e:
        print(f"  [失败] 无法访问 ETSI 目录 {spec_url}: {e}")
        return None
    latest = _pick_latest_version(ver_dirs)
    if not latest:
        print(f"  [失败] 在 {spec_url} 未找到版本目录")
        return None
    ver_tuple = _ver_dir_to_version(latest)
    ver_str = "V%d.%d.%d" % ver_tuple if ver_tuple else latest
    print(f"  最新版本目录: {latest}  ({ver_str})")

    ver_url = f"{ETSI_DELIVER_BASE}/{range_dir}/{etsi_code}/{latest}/"
    try:
        files = _fetch_etsi_links(ver_url, suffix=".pdf")
    except Exception as e:
        print(f"  [失败] 无法访问版本目录 {ver_url}: {e}")
        return None
    pdf_name = next((f for f in files if f.endswith(".pdf")), None)
    if not pdf_name:
        print(f"  [失败] 版本目录中未找到 .pdf 文件 (已发现: {files})")
        return None
    pdf_url = f"{ver_url}{pdf_name}"

    os.makedirs(out_dir, exist_ok=True)
    out_name = f"{dotted}_{name}_{ver_str}.pdf"
    out_path = os.path.join(out_dir, out_name)
    if os.path.exists(out_path):
        sz = os.path.getsize(out_path)
        print(f"  [跳过] 已存在 -> {out_name} ({sz/1024:.1f} KB)")
        return out_path
    # 下载: 分块 + 进度打印 + 失败重试 (最多 3 次, 指数退避)
    MAX_ATTEMPTS = 3
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            print(f"  下载 (尝试 {attempt}/{MAX_ATTEMPTS}): {pdf_url}")
            req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
            done = 0
            next_mark = 5 * 1024 * 1024  # 每 5MB 打印一次进度
            with urllib.request.urlopen(req, timeout=300) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                with open(out_path, "wb") as f:
                    while True:
                        chunk = resp.read(64 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if done >= next_mark:
                            if total:
                                print(f"  进度 {done/1024/1024:.1f}/{total/1024/1024:.1f} MB ({done*100/total:.0f}%)")
                            else:
                                print(f"  已下载 {done/1024/1024:.1f} MB")
                            next_mark += 5 * 1024 * 1024
            last_err = None
            break
        except Exception as e:
            last_err = e
            print(f"  [重试 {attempt}/{MAX_ATTEMPTS}] {e}")
            if os.path.exists(out_path):
                os.remove(out_path)
            if attempt < MAX_ATTEMPTS:
                wait = 2 ** attempt  # 2s, 4s
                print(f"  等待 {wait}s 后重试...")
                time.sleep(wait)
    if last_err is not None:
        print(f"  [失败] 下载出错 (已重试 {MAX_ATTEMPTS} 次): {last_err}")
        if os.path.exists(out_path):
            os.remove(out_path)
        return None
    kb = os.path.getsize(out_path) / 1024
    print(f"  [完成] -> {out_name} ({kb:.1f} KB)")
    return out_path


def process_pdf_all(specs):
    """批量执行 process_pdf; specs 为 [(spec, name), ...]; 打印汇总。"""
    os.makedirs(PDF_OUT_DIR, exist_ok=True)
    results = {}
    for spec, name in specs:
        results[spec] = process_pdf(spec, name)
    print("\n==== PDF 汇总 ====")
    for spec, path in results.items():
        if path:
            print(f"  {spec}: 成功 -> {os.path.basename(path)}")
        else:
            print(f"  {spec}: 失败")
    return results


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
        out_name = f"{spec_to_dirname(spec)}_{name}_{ver}.md"
        out_path = os.path.join(OUT_MD_DIR, out_name)
        # 公式图/插图目录与 md 同级: images/<md名>/eq-NNNN.* | fig-NNNN.*
        sink = ImageSink(os.path.join(OUT_MD_DIR, "images",
                                      os.path.splitext(out_name)[0]))
        parts = []
        for d in docx_list:
            print(f"  转换: {os.path.basename(d)}")
            parts.append(convert_docx_to_md(d, sink))
        md = "\n\n---\n\n".join(parts)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        kb = os.path.getsize(out_path) / 1024
        print(f"  [完成] -> {out_name} ({kb:.1f} KB)")
        # 超过 2MB 则按标题边界拆分为多份 < 2MB 的文件
        out_paths = split_md_file(out_path)
        if len(out_paths) > 1:
            print(f"  [拆分] -> {len(out_paths)} 份 (每份 < 2MB):")
            for p in out_paths:
                print(f"    - {os.path.basename(p)} "
                      f"({os.path.getsize(p) / 1024:.1f} KB)")
        return out_paths
    except Exception as e:
        print(f"  [失败] {e}")
        return None
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main():
    # --pdf <spec[:name]> ... 模式: 从 ETSI 下载最新 PDF
    if len(sys.argv) >= 2 and sys.argv[1] == "--pdf":
        specs = []
        for arg in sys.argv[2:]:
            spec, _, name = arg.partition(":")
            specs.append((spec, name or spec))
        process_pdf_all(specs)
        return
    # --split <dir> 模式: 对目录下已有 md 文件按 2MB 上限拆分, 不重新下载
    if len(sys.argv) >= 3 and sys.argv[1] == "--split":
        split_dir(sys.argv[2])
        return
    os.makedirs(OUT_MD_DIR, exist_ok=True)
    os.makedirs(WORK_ROOT, exist_ok=True)
    results = {}
    for arg in sys.argv[1:]:
        spec, _, name = arg.partition(":")
        results[spec] = process(spec, name or spec)
    print("\n==== 汇总 ====")
    for spec, paths in results.items():
        if paths:
            names = ", ".join(os.path.basename(p) for p in paths)
            print(f"  {spec}: 成功 -> {names}")
        else:
            print(f"  {spec}: 失败")
    shutil.rmtree(WORK_ROOT, ignore_errors=True)


if __name__ == "__main__":
    main()
