# SDAP 层

**职责**：负责 QoS flow 到 DRB 的映射、上下行 QoS flow 标识（QFI）标记，是用户面最高的 AS 子层。

- **对应 TS 规范**：TS37.324 Service Data Adaptation Protocol (SDAP) specification
  > 注：原始初始化需求将 SDAP 标注为 TS38.401，实际为 **TS37.324**（TS38.401 是 NG-RAN 架构规范），此处按 3GPP 实际修正。
- **WG 归属**：RAN WG2

## 接口关系
- **上层（5GC 用户面）**：处理来自 5GC 的 **QoS flow**。
- **下层（PDCP）**：通过**无线承载**（DRB）使用 [[PDCP/README]] 的服务。

## 当前已有页面
（初始为空，等待 ingest）
