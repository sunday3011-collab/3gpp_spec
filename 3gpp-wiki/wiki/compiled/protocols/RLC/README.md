# RLC 层

**职责**：负责 SDU 的分段与重组、ARQ 重传（AM 模式）、按模式（TM/UM/AM）提供可靠性，连接 PDCP 与 MAC。

- **对应 TS 规范**：TS38.322 Radio Link Control (RLC) protocol specification
- **WG 归属**：RAN WG2

## 接口关系
- **上层（PDCP）**：通过 **RLC channel** 为 [[PDCP/README]] 提供服务。
- **下层（MAC）**：通过**逻辑信道**（logical channel）使用 [[MAC/README]] 的服务。

## 当前已有页面
（初始为空，等待 ingest）
