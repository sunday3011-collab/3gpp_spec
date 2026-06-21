# PDCP 层

**职责**：负责头压缩（ROHC）、加密与完整性保护、序列号维护、重排序与重复检测，承载无线承载（radio bearer）。

- **对应 TS 规范**：TS38.323 Packet Data Convergence Protocol (PDCP) specification
- **WG 归属**：RAN WG2

## 接口关系
- **上层（SDAP / RRC）**：通过**无线承载**（DRB 经 [[SDAP/README]]，SRB 承载 [[RRC/README]] 信令）提供服务。
- **下层（RLC）**：通过 **RLC channel** 使用 [[RLC/README]] 的服务。

## 当前已有页面
（初始为空，等待 ingest）
