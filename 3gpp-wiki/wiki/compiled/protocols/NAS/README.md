# NAS 层

**职责**：UE 与核心网（AMF）之间的非接入层信令——注册管理、连接管理、会话管理、移动性管理、安全（鉴权与 NAS 加密/完整性保护）。

- **对应 TS 规范**：TS24.501 Non-Access-Stratum (NAS) protocol for 5G System (5GS)
- **WG 归属**：CT WG1

## 接口关系
- **对端**：UE ↔ 5GC 的 **AMF**（端到端，对 NG-RAN 透明）。
- **下层（AS）**：NAS PDU 经 [[RRC/README]] 在空口承载（SRB）。
- **关联**：会话管理（SM）与 [[SDAP/README]] / 5GC 用户面的 QoS 体系相关。

## 当前已有页面
（初始为空，等待 ingest）
