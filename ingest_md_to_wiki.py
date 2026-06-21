#!/usr/bin/env python3
"""
将 md/ 下的全部3GPP协议结构化登记进 3gpp-wiki：
  1. 把每个 md 移入 raw_sources/specs/<TS子目录>/ (人投喂动作)
  2. 为每个 spec 生成 wiki/compiled/ 概览页 (frontmatter + 职责 + 章节目录 + 原文链接)
  3. 重建 wiki/index.md
  4. 追加 wiki/log.md (append-only)

仅结构化登记，不杜撰逐条技术细节。章节目录从原文 Heading1 抽取。
"""

import os
import re
import shutil

REPO = "/Users/huangyang/Code/3GPP_Protocols"
MD_DIR = os.path.join(REPO, "md")
WIKI = os.path.join(REPO, "3gpp-wiki")
RAW = os.path.join(WIKI, "raw_sources", "specs")
COMPILED = os.path.join(WIKI, "wiki", "compiled")
TODAY = "2026-06-21"

# md文件名 -> 登记元数据
# (spec, title, layer, comp_subdir, page_name, raw_subdir, keywords, duty)
SPECS = {
    # ---- PHY (RAN1) ----
    "38.201_PHY_General_j00.md": ("TS38.201", "Physical layer; General description", "PHY", "protocols/PHY", "TS38.201_PHY_General.md", "TS38.201_PHY_General", "PHY,总览", "NR 物理层总体描述与各 PHY 规范的导览。"),
    "38.202_PHY_Services_j00.md": ("TS38.202", "Services provided by the physical layer", "PHY", "protocols/PHY", "TS38.202_PHY_Services.md", "TS38.202_PHY_Services", "PHY,services", "物理层向高层提供的服务模型。"),
    "38.211_PHY-Channels_j30.md": ("TS38.211", "Physical channels and modulation", "PHY", "protocols/PHY", "TS38.211_PHY-Channels.md", "TS38.211_PHY", "PHY,物理信道,调制", "物理信道定义、调制、参考信号与帧结构。"),
    "38.212_PHY-Coding_j30.md": ("TS38.212", "Multiplexing and channel coding", "PHY", "protocols/PHY", "TS38.212_PHY-Coding.md", "TS38.212_Coding", "PHY,信道编码,复用", "传输信道复用与信道编码 (LDPC/Polar)。"),
    "38.213_PHY-Control_j30.md": ("TS38.213", "Physical layer procedures for control", "PHY", "protocols/PHY", "TS38.213_PHY-Control.md", "TS38.213_PHY_Procedures", "PHY,控制过程,PDCCH", "控制相关物理层过程 (功控、随机接入、PDCCH 监测等)。"),
    "38.214_PHY-Data_j30.md": ("TS38.214", "Physical layer procedures for data", "PHY", "protocols/PHY", "TS38.214_PHY-Data.md", "TS38.214_PHY_Data", "PHY,数据过程,PDSCH,PUSCH", "数据相关物理层过程 (PDSCH/PUSCH、CSI、调度)。"),
    "38.215_PHY_Measurements_j20.md": ("TS38.215", "Physical layer measurements", "PHY", "protocols/PHY", "TS38.215_PHY_Measurements.md", "TS38.215_PHY_Measurements", "PHY,测量,RSRP", "物理层测量量定义 (RSRP/RSRQ/SINR 等)。"),
    # ---- MAC ----
    "38.321_MAC_j20.md": ("TS38.321", "Medium Access Control (MAC) protocol specification", "MAC", "protocols/MAC", "TS38.321_MAC.md", "TS38.321_MAC", "MAC,HARQ,调度,随机接入", "逻辑信道复用、HARQ、调度、随机接入。"),
    # ---- RLC ----
    "38.322_RLC_j20.md": ("TS38.322", "Radio Link Control (RLC) protocol specification", "RLC", "protocols/RLC", "TS38.322_RLC.md", "TS38.322_RLC", "RLC,ARQ,分段重组", "分段与重组、ARQ、TM/UM/AM 模式。"),
    # ---- PDCP ----
    "38.323_PDCP_j10.md": ("TS38.323", "Packet Data Convergence Protocol (PDCP) specification", "PDCP", "protocols/PDCP", "TS38.323_PDCP.md", "TS38.323_PDCP", "PDCP,头压缩,加密,重排序", "头压缩、加解密与完整性、序列号与重排序。"),
    # ---- SDAP ----
    "37.324_SDAP_j00.md": ("TS37.324", "Service Data Adaptation Protocol (SDAP) specification", "SDAP", "protocols/SDAP", "TS37.324_SDAP.md", "TS37.324_SDAP", "SDAP,QoS flow,DRB", "QoS flow 到 DRB 映射、QFI 标记。"),
    # ---- RRC ----
    "38.331_RRC_j20.md": ("TS38.331", "Radio Resource Control (RRC) protocol specification", "RRC", "protocols/RRC", "TS38.331_RRC.md", "TS38.331_RRC", "RRC,连接管理,移动性", "连接建立/重配/释放、移动性、测量、广播。"),
    "38.304_UE_Idle_j20.md": ("TS38.304", "UE procedures in Idle mode and RRC Inactive state", "RRC", "protocols/RRC", "TS38.304_UE_Idle.md", "TS38.304_UE_Idle", "RRC,Idle,小区选择", "空闲态/非激活态 UE 过程 (小区选择/重选、寻呼)。"),
    "38.306_UE_Capabilities_j20.md": ("TS38.306", "UE radio access capabilities", "RRC", "protocols/RRC", "TS38.306_UE_Capabilities.md", "TS38.306_UE_Capabilities", "RRC,UE能力", "UE 无线接入能力参数定义。"),
    # ---- NAS (CT1) ----
    "24.501_NAS_5GS_j62.md": ("TS24.501", "Non-Access-Stratum (NAS) protocol for 5G System (5GS)", "NAS", "protocols/NAS", "TS24.501_NAS_5GS.md", "TS24.501_NAS", "NAS,5GS,注册,会话管理", "5GS 非接入层信令 (注册/连接/会话/移动性/安全)。"),
    "24.301_NAS_EPS_j60.md": ("TS24.301", "Non-Access-Stratum (NAS) protocol for Evolved Packet System (EPS)", "NAS", "protocols/NAS", "TS24.301_NAS_EPS.md", "TS24.301_NAS_EPS", "NAS,EPS,EMM,ESM", "EPS 非接入层信令 (EMM/ESM)。"),
    # ---- concept / 其他 (非7层无线协议栈) ----
    "38.300_NG-RAN_Overall_j20.md": ("TS38.300", "NR and NG-RAN Overall description; Stage 2", "concept", "concepts", "TS38.300_NG-RAN_Overall.md", "TS38.300_NG-RAN_Overall", "PHY/MAC/RLC/PDCP/SDAP/RRC", "NG-RAN 总体架构与协议栈 Stage 2 描述。"),
    "38.305_UE_Positioning_j10.md": ("TS38.305", "NG-RAN; Stage 2 functional specification of UE positioning", "concept", "concepts", "TS38.305_UE_Positioning.md", "TS38.305_UE_Positioning", "定位,positioning,LMF", "UE 定位 Stage 2 功能 (定位方法、LMF 交互)。"),
    "38.314_L2_Measurements_j00.md": ("TS38.314", "NR; Layer 2 measurements", "concept", "concepts", "TS38.314_L2_Measurements.md", "TS38.314_L2_Measurements", "MAC/RLC/PDCP,L2测量", "L2 测量量定义 (吞吐、时延、缓存等)。"),
    "38.340_BAP_j00.md": ("TS38.340", "Backhaul Adaptation Protocol (BAP) specification", "concept", "concepts", "TS38.340_BAP.md", "TS38.340_BAP", "BAP,IAB,回传", "IAB 回传适配协议 (BAP) —— 多跳路由与承载映射。【独立协议层，未列入5G UE接入栈7层】"),
    "37.213_Shared_Spectrum_j00.md": ("TS37.213", "Physical layer procedures for shared spectrum channel access", "concept", "concepts", "TS37.213_Shared_Spectrum.md", "TS37.213_SharedSpectrum", "PHY,免许可,LBT", "共享频谱信道接入物理层过程 (LBT 等)。"),
    "38.413_NGAP_j20.md": ("TS38.413", "NG-RAN; NG Application Protocol (NGAP)", "concept", "concepts", "TS38.413_NGAP.md", "TS38.413_NGAP", "NG接口,NGAP,RAN3", "NG 接口 (gNB↔AMF) 应用层信令协议。"),
    "38.423_XnAP_j20.md": ("TS38.423", "NG-RAN; Xn Application Protocol (XnAP)", "concept", "concepts", "TS38.423_XnAP.md", "TS38.423_XnAP", "Xn接口,XnAP,RAN3", "Xn 接口 (gNB↔gNB) 应用层信令协议。"),
    "38.473_F1AP_j20.md": ("TS38.473", "NG-RAN; F1 Application Protocol (F1AP)", "concept", "concepts", "TS38.473_F1AP.md", "TS38.473_F1AP", "F1接口,F1AP,CU-DU", "F1 接口 (gNB-CU↔gNB-DU) 应用层信令协议。"),
    "38.101-1_RF_Requirements_FR1_j50.md": ("TS38.101-1", "UE radio transmission and reception; Part 1: Range 1 Standalone", "concept", "concepts", "TS38.101-1_RF_FR1.md", "TS38.101-1_RF_FR1", "RF,FR1,RAN4", "UE 射频收发要求 (FR1 独立组网)。【RAN4 RF 要求】"),
    "38.101-2_RF_Requirements_FR2_j40.md": ("TS38.101-2", "UE radio transmission and reception; Part 2: Range 2 Standalone", "concept", "concepts", "TS38.101-2_RF_FR2.md", "TS38.101-2_RF_FR2", "RF,FR2,RAN4", "UE 射频收发要求 (FR2 独立组网)。【RAN4 RF 要求】"),
    "38.101-3_RF_Requirements_Interworking_j50.md": ("TS38.101-3", "UE radio transmission and reception; Part 3: Range 1 and Range 2 Interworking", "concept", "concepts", "TS38.101-3_RF_Interworking.md", "TS38.101-3_RF_Interworking", "RF,FR1+FR2,互操作,RAN4", "UE 射频要求 (FR1/FR2 互操作)。【RAN4 RF 要求】"),
    "38.101-4_RF_Performance_j22.md": ("TS38.101-4", "UE radio transmission and reception; Part 4: Performance requirements", "concept", "concepts", "TS38.101-4_RF_Performance.md", "TS38.101-4_RF_Performance", "RF,性能要求,RAN4", "UE 射频性能要求 (解调/CSI 报告等)。【RAN4 RF 要求】"),
    "38.101-5_RF_Part5_j40.md": ("TS38.101-5", "UE radio transmission and reception; Part 5: Satellite access RF and performance", "concept", "concepts", "TS38.101-5_RF_Part5.md", "TS38.101-5_RF_Part5", "RF,NTN,卫星接入,RAN4", "UE 射频与性能要求 (卫星/NTN 接入)。【RAN4 RF 要求】"),
    "38.133_RRM_j40.md": ("TS38.133", "Requirements for support of radio resource management", "concept", "concepts", "TS38.133_RRM.md", "TS38.133_RRM", "RRM,测量要求,RAN4", "无线资源管理 (RRM) 支持要求 (测量精度/时延)。【RAN4 RRM 要求】"),
}

# index.md 中归入「协议层页面」表的 layer
PROTOCOL_LAYERS = {"PHY", "MAC", "RLC", "PDCP", "SDAP", "RRC", "NAS"}


def extract_toc(md_path, cap=40):
    """抽取 Heading1 (# xxx)，修正 '1Scope'->'1 Scope'，去重，截断。"""
    toc, seen = [], set()
    with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("# ") and not line.startswith("## "):
                h = line[2:].strip()
                h = re.sub(r"^(\d+(?:\.\d+)*)([A-Za-z])", r"\1 \2", h)
                if h and h not in seen and len(h) < 120:
                    seen.add(h)
                    toc.append(h)
            if len(toc) >= cap:
                break
    return toc


def release_from_filename(fname):
    m = re.search(r"_([a-z])\d{2}\.md$", fname)
    letter = m.group(1) if m else "j"
    return {"j": "Rel-19", "i": "Rel-18", "h": "Rel-17"}.get(letter, "Rel-19")


def main():
    rows_proto, rows_concept = [], []

    # 同层兄弟，用于「相关页面」
    siblings = {}
    for fname, meta in SPECS.items():
        siblings.setdefault(meta[2], []).append(meta[4][:-3])  # page name without .md

    for fname, meta in SPECS.items():
        spec, title, layer, comp_subdir, page_name, raw_subdir, keywords, duty = meta
        release = release_from_filename(fname)
        src = os.path.join(MD_DIR, fname)
        if not os.path.exists(src):
            print(f"[跳过] 源缺失: {fname}")
            continue

        # 1. 移动到 raw_sources
        raw_dir = os.path.join(RAW, raw_subdir)
        os.makedirs(raw_dir, exist_ok=True)
        dst = os.path.join(raw_dir, fname)
        shutil.move(src, dst)
        raw_link = fname[:-3]  # Obsidian wikilink basename

        # 2. 章节目录
        toc = extract_toc(dst)
        toc_md = "\n".join(f"- {t}" for t in toc) if toc else "（未抽取到章节）"

        # 相关页面 (同层其他)
        rel = [p for p in siblings[layer] if p != page_name[:-3]]
        rel_md = "\n".join(f"- [[{p}]]" for p in rel) if rel else "（无）"

        # 3. 生成概览页
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

## 相关页面（同层）
{rel_md}

---
> 本页为结构化登记概览，未展开逐条技术细节。需要细节时对原文执行 `ingest`。
"""
        out_dir = os.path.join(COMPILED, comp_subdir)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, page_name), "w", encoding="utf-8") as f:
            f.write(page)

        # index 行
        pn = page_name[:-3]
        if layer in PROTOCOL_LAYERS:
            rows_proto.append((spec, f"[[{pn}]]", layer, spec, release, TODAY))
        else:
            rows_concept.append((spec, f"[[{pn}]]", keywords))
        print(f"[登记] {spec:12} -> compiled/{comp_subdir}/{page_name}")

    # 4. 重建 index.md
    rows_proto.sort()
    rows_concept.sort()
    idx = ["# 3GPP Wiki Index", f"最后更新：{TODAY}", "",
           "## 协议层页面",
           "| 页面 | 层 | 主要规范 | Release | 最后更新 |",
           "|------|-----|---------|---------|---------|"]
    for _, pg, layer, spec, rel, upd in rows_proto:
        idx.append(f"| {pg} | {layer} | {spec} | {rel} | {upd} |")
    idx += ["", "## 概念页面",
            "| 页面 | 涉及层 | 关键词 |",
            "|------|--------|-------|"]
    for _, pg, kw in rows_concept:
        idx.append(f"| {pg} | concept | {kw} |")
    idx += ["", "## 对比页面",
            "| 页面 | 对比维度 |",
            "|------|---------|", "",
            "## 产品笔记",
            "| 产品 | 页面 | 涉及层 |",
            "|------|------|-------|", ""]
    with open(os.path.join(WIKI, "wiki", "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(idx))

    # 5. 追加 log.md
    n = len(rows_proto) + len(rows_concept)
    log_entry = (f"\n## [{TODAY}] ingest | md/ 全量结构化登记 | "
                 f"影响页面：{n} 个 spec 概览页 + index.md 重建\n"
                 f"- 协议层页面 {len(rows_proto)} 个，概念页面 {len(rows_concept)} 个\n"
                 f"- 原始 md 已移入 raw_sources/specs/ 对应子目录\n")
    with open(os.path.join(WIKI, "wiki", "log.md"), "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"\n完成：协议层 {len(rows_proto)} + 概念 {len(rows_concept)} = {n} 页")


if __name__ == "__main__":
    main()
