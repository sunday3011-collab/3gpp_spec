#!/usr/bin/env python3
"""
Source 位置统一配置工具（config.py）。

本仓库所有维护脚本的路径不再硬编码，统一从仓库根 `sources.json` 读取。
相对路径基于仓库根解析，绝对路径（仓库外，如外置硬盘/其他资料库）原样使用；
Source 类型是开放的 map，可任意新增/删除（如以后投喂厂商文档）。

配置文件结构 (sources.json):
{
  "version": 1,
  "wiki_root": ".",
  "sources": {
    "specs":   { "path": "raw_sources/3gpp_sources/specs",   "desc": "..." },
    ...
  }
}

CLI 用法 (以仓库根为 cwd):
  python3 $SK/config.py list                 # 列出全部 Source 及存在性
  python3 $SK/config.py get specs            # 打印解析后的绝对路径 (供 shell 取用)
  python3 $SK/config.py get wiki             # 打印 wiki_root
  python3 $SK/config.py set specs /path/dir  # 修改 (或新增) Source 位置
  python3 $SK/config.py remove specs         # 删除 Source 条目
  python3 $SK/config.py doctor               # 校验配置与路径有效性

环境变量 `SOURCES_CONFIG` 可指定其他配置文件路径；
脚本内读取路径的优先级: 环境变量 (OUT_MD_DIR/PDF_OUT_DIR/WIKI_DIR) > sources.json > 内置默认。
其他脚本: `import config` 后调用 `config.source_path("specs")` / `config.wiki_root()`。
"""

import json
import os
import sys


def _repo_root():
    """从本文件位置向上探测仓库根(含.git)；找不到则回退上溯2层。"""
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        p = os.path.dirname(d)
        if p == d:
            break
        d = p
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


REPO = _repo_root()
CONFIG_PATH = os.environ.get(
    "SOURCES_CONFIG", os.path.join(REPO, "sources.json"))

# 内置默认 (与 sources.json 首次生成内容一致; 配置文件缺失时自动落盘)
DEFAULT_CONFIG = {
    "version": 1,
    "_comment": "Source 位置注册表。相对路径基于仓库根解析；绝对路径(仓库外)原样使用。"
                "修改请用 config.py 子命令，或直接编辑本文件。",
    "wiki_root": ".",
    "sources": {
        "specs": {
            "path": "raw_sources/3gpp_sources/specs",
            "desc": "协议 Markdown 原文 (含 _incoming 暂存区与 images/)",
        },
        "pdfs": {
            "path": "raw_sources/3gpp_sources/pdfs",
            "desc": "ETSI 官方最新版 PDF",
        },
        "word": {
            "path": "raw_sources/3gpp_sources/word",
            "desc": "原始 doc/docx 文档",
        },
        "product": {
            "path": "raw_sources/product",
            "desc": "产品私有文档 (按产品名分子目录)",
        },
    },
}


# ---------- 库接口 (供其他脚本 import) ----------

def load():
    """加载配置；文件缺失时写入内置默认后返回。返回 (cfg, created: bool)。"""
    if not os.path.exists(CONFIG_PATH):
        save(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG), True
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg, False


def save(cfg):
    """写回配置 (UTF-8, 缩进 2, 保留中文)。"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")


def resolve(path):
    """相对路径 -> 基于仓库根的绝对路径；绝对路径原样返回 (归一化)。"""
    if os.path.isabs(path):
        return os.path.normpath(path)
    return os.path.normpath(os.path.join(REPO, path))


def source_path(type_):
    """返回指定 Source 类型的绝对路径；未知类型报错并提示 config.py 用法。"""
    cfg, _ = load()
    srcs = cfg.get("sources", {})
    if type_ not in srcs:
        raise KeyError(
            f"未注册的 Source 类型: {type_!r} (已有: {', '.join(sorted(srcs))})。"
            f"可用 `python3 {__file__} set {type_} <路径>` 注册。")
    return resolve(srcs[type_]["path"])


def wiki_root():
    """返回 wiki 根目录绝对路径。"""
    cfg, _ = load()
    return resolve(cfg.get("wiki_root", DEFAULT_CONFIG["wiki_root"]))


# ---------- CLI ----------

def cmd_list(cfg):
    print(f"配置文件: {CONFIG_PATH}")
    print(f"wiki_root: {cfg.get('wiki_root')} -> {wiki_root()}")
    print()
    print(f"{'类型':<12} {'状态':<4} 路径")
    print("-" * 78)
    for name in sorted(cfg.get("sources", {})):
        entry = cfg["sources"][name]
        p = resolve(entry["path"])
        ok = "✓" if os.path.isdir(p) else "✗"
        suffix = "" if os.path.isdir(p) else "  (不存在, 将在使用时自动创建)"
        print(f"{name:<12} {ok:<4} {p}{suffix}")
        if entry.get("desc"):
            print(f"{'':<12} {'':<4} # {entry['desc']}")


def cmd_get(cfg, type_):
    if type_ == "wiki":
        print(wiki_root())
        return 0
    try:
        print(source_path(type_))
        return 0
    except KeyError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1


def cmd_set(cfg, type_, path):
    path = os.path.normpath(os.path.expanduser(path))
    abs_path = resolve(path)
    if not os.path.isdir(abs_path):
        os.makedirs(abs_path, exist_ok=True)
        print(f"[创建] 目录不存在，已创建: {abs_path}")
    if type_ == "wiki":
        cfg["wiki_root"] = path
        save(cfg)
        print(f"[已保存] wiki_root -> {abs_path}")
        return 0
    cfg.setdefault("sources", {})[type_] = {
        "path": path,
        "desc": cfg.get("sources", {}).get(type_, {}).get("desc", ""),
    }
    save(cfg)
    print(f"[已保存] {type_} -> {abs_path}")
    return 0


def cmd_remove(cfg, type_):
    if type_ == "wiki":
        print("[错误] wiki_root 请用 `set wiki <路径>` 修改，不可 remove", file=sys.stderr)
        return 1
    if type_ not in cfg.get("sources", {}):
        print(f"[错误] 未注册的 Source 类型: {type_}", file=sys.stderr)
        return 1
    del cfg["sources"][type_]
    save(cfg)
    print(f"[已删除] {type_} (仅移除注册，不动磁盘上的文件)")
    return 0


def cmd_doctor(cfg):
    problems = 0
    print(f"配置文件: {CONFIG_PATH}")
    if not os.path.exists(CONFIG_PATH):
        print("  ✗ 配置文件不存在 (load() 会自动生成默认)")
        problems += 1
    wiki = wiki_root()
    print(f"wiki_root: {cfg.get('wiki_root')} -> {wiki} "
          f"{'✓' if os.path.isdir(wiki) else '✗ 目录不存在'}")
    if not os.path.isdir(wiki):
        problems += 1
    for name in sorted(cfg.get("sources", {})):
        entry = cfg["sources"][name]
        p = resolve(entry["path"])
        if os.path.isdir(p):
            n = sum(len(fs) for _, _, fs in os.walk(p))
            print(f"  ✓ {name:<10} {p}  ({n} 个文件)")
        else:
            print(f"  ✗ {name:<10} {p}  目录不存在 (脚本使用时会自动创建，若非预期请检查拼写)")
            problems += 1
    tsv = os.path.join(wiki, "wiki", "sections.tsv")
    if os.path.isfile(tsv):
        print(f"  ✓ sections.tsv 存在: {tsv}")
    else:
        print(f"  ! sections.tsv 不存在 (运行 gen_section_index.py 生成): {tsv}")
    print()
    print("校验通过" if problems == 0 else f"发现 {problems} 个问题")
    return 0 if problems == 0 else 1


USAGE = """用法: python3 config.py <子命令> [参数]
  list                    列出全部 Source 及存在性
  get <类型|wiki>         打印解析后的绝对路径
  set <类型> <路径>        注册/修改 Source 位置 (目录不存在会自动创建)
  remove <类型>            删除 Source 条目 (不动磁盘文件)
  doctor                  校验配置与路径有效性
环境变量 SOURCES_CONFIG 可指定其他配置文件 (默认 <仓库根>/sources.json)"""


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    cmd, rest = args[0], args[1:]
    cfg, created = load()
    if created:
        print(f"[初始化] 配置文件不存在，已写入内置默认: {CONFIG_PATH}\n")
    if cmd == "list" and not rest:
        return cmd_list(cfg) or 0
    if cmd == "get" and len(rest) == 1:
        return cmd_get(cfg, rest[0])
    if cmd == "set" and len(rest) == 2:
        return cmd_set(cfg, rest[0], rest[1])
    if cmd == "remove" and len(rest) == 1:
        return cmd_remove(cfg, rest[0])
    if cmd == "doctor" and not rest:
        return cmd_doctor(cfg)
    print(USAGE)
    return 1


if __name__ == "__main__":
    sys.exit(main())
