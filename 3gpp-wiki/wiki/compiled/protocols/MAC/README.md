# MAC 层

**职责**：负责逻辑信道复用/解复用、HARQ、调度与优先级处理、随机接入，连接逻辑信道与传输信道。

- **对应 TS 规范**：TS38.321 Medium Access Control (MAC) protocol specification
- **WG 归属**：RAN WG2

## 接口关系
- **上层（RLC）**：通过**逻辑信道**（logical channel）为 [[RLC/README]] 提供服务。
- **下层（PHY）**：通过**传输信道**（transport channel）使用 [[PHY/README]] 的传输服务。

## 当前已有页面
（初始为空，等待 ingest）
