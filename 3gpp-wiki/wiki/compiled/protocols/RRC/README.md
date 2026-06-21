# RRC 层

**职责**：负责 AS 层无线资源控制——连接建立/重配/释放、移动性管理（handover）、系统消息广播、测量配置、承载控制，是控制面核心。

- **对应 TS 规范**：TS38.331 Radio Resource Control (RRC) protocol specification
- **WG 归属**：RAN WG2

## 接口关系
- **上层（NAS）**：透传 [[NAS/README]] 信令（NAS PDU 经 RRC 承载）。
- **下层（PDCP）**：RRC 信令经 **SRB** 由 [[PDCP/README]] 承载。
- **横向**：配置并控制 [[PHY/README]] / [[MAC/README]] / [[RLC/README]] / [[PDCP/README]] / [[SDAP/README]] 各层参数。

## 当前已有页面
（初始为空，等待 ingest）
