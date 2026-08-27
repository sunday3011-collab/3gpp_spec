#!/usr/bin/env python3
"""
把 images/ 目录下 OLE 公式/插图的 WMF/EMF 批量转为 PNG, 并改写 md 中的引用。

背景: 3GPP docx 中旧式公式 (Equation.3 / MathType) 和 Visio 图以 OLE 对象
嵌入, 只有 WMF/EMF 预览图。Obsidian/Typora/GitHub 均不渲染 WMF/EMF,
需要转成 PNG。转换依赖 LibreOffice (brew install --cask libreoffice)。

用法:
  python3 scripts/convert_images.py [md文件或目录...]
  不带参数则处理 3gpp-wiki/raw_sources/specs/ 下全部 md 与 images/ 目录

规则:
  - 仅转换 .wmf/.emf -> .png (soffice headless)
  - 转换成功后改写 md 内 ![](images/xxx/yyy.wmf) -> .png
  - 已有同名 .png 的跳过 (幂等, 可重跑)
"""

import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ROOT = os.path.join(REPO, "3gpp-wiki", "raw_sources", "specs")
SOFFICE = shutil.which("soffice") or "/Applications/LibreOffice.app/Contents/MacOS/soffice"


def convert_one(path):
    """wmf/emf -> png, 返回 png 路径或 None"""
    outdir = os.path.dirname(path)
    cmd = [SOFFICE, "--headless", "--convert-to", "png", "--outdir", outdir, path]
    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
    except (subprocess.TimeoutExpired, OSError):
        return None
    png = os.path.splitext(path)[0] + ".png"
    return png if os.path.exists(png) else None


def rewrite_md(md_path, converted):
    """把 md 中对已转换图片的引用从 wmf/emf 改为 png"""
    try:
        text = open(md_path, encoding="utf-8").read()
    except OSError:
        return 0
    n = 0
    for old_ext, new_ext in converted.items():
        new_text = text.replace(old_ext, new_ext)
        n += text.count(old_ext)
        text = new_text
    if n:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(text)
    return n


def process_dir(root):
    """处理一个含 images/ 的目录: 转换 + 改写同级及子目录 md"""
    n_img, n_md = 0, 0
    images_dirs = []
    for dirpath, dirnames, filenames in os.walk(root):
        if os.path.basename(dirpath) == "images":
            images_dirs.append(dirpath)
    if not images_dirs:
        return 0, 0
    converted = {}
    for imgdir in images_dirs:
        for fn in sorted(os.listdir(imgdir)):
            if not fn.lower().endswith((".wmf", ".emf")):
                continue
            src = os.path.join(imgdir, fn)
            png = os.path.splitext(src)[0] + ".png"
            if os.path.exists(png):
                converted[src] = png
                continue
            result = convert_one(src)
            if result:
                converted[src] = result
                n_img += 1
    # 改写所有 md 中的引用 (绝对路径匹配)
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".md"):
                md = os.path.join(dirpath, fn)
                text = open(md, encoding="utf-8").read()
                n = 0
                for old, new in converted.items():
                    old_rel = os.path.relpath(old, os.path.dirname(md))
                    new_rel = os.path.relpath(new, os.path.dirname(md))
                    if old_rel in text:
                        n += text.count(old_rel)
                        text = text.replace(old_rel, new_rel)
                if n:
                    open(md, "w", encoding="utf-8").write(text)
                    n_md += 1
    return n_img, n_md


def main():
    if not os.path.exists(SOFFICE):
        print("未找到 LibreOffice。安装后重试:")
        print("  brew install --cask libreoffice")
        sys.exit(1)
    targets = sys.argv[1:] or [DEFAULT_ROOT]
    total_img = total_md = 0
    for t in targets:
        if os.path.isdir(t):
            n_img, n_md = process_dir(t)
            total_img += n_img
            total_md += n_md
            print(f"[完成] {t}: 转换 {n_img} 张图, 改写 {n_md} 个 md")
        elif os.path.isfile(t):
            n_img, n_md = process_dir(os.path.dirname(t))
            total_img += n_img
            total_md += n_md
        else:
            print(f"[跳过] 不存在: {t}")
    print(f"==== 共转换 {total_img} 张 WMF/EMF -> PNG, 改写 {total_md} 个 md ====")


if __name__ == "__main__":
    main()
