# Wiki 操作日志
<!-- append-only，不修改历史记录 -->

## [2026-06-21] init | 项目初始化完成
- 目录结构创建完毕
- CLAUDE.md 生成完毕
- 等待首批 raw_sources 投喂

## [2026-06-21] ingest | md/ 全量结构化登记 | 影响页面：30 个 spec 概览页 + index.md 重建
- 协议层页面 16 个，概念页面 14 个
- 原始 md 已移入 raw_sources/specs/ 对应子目录

## [2026-06-21] ingest | 增量入库 TS38.104、TS38.401、TS37.340、TS23.501、TS23.502 | 影响页面：5 个概览页 + index.md

## [2026-06-21] ingest | TS38.331 RRC 蒸馏页 | 影响页面：compiled/protocols/RRC/TS38.331_RRC.md
- 概览桩升级为热点蒸馏页：状态(§4.2.1)/SRB(§4.2.2)/核心过程(§5.3)/定时器(§7.1.1)/常量(§7.3)，均带 clause 引用

## [2026-06-21] ingest | 热点协议蒸馏(MAC/RLC/PDCP/PHY) | 影响页面：7 个 compiled 概览页升级
- TS38.321 MAC：RA/HARQ/SR/BSR/PHR/DRX(§5)、RNTI(§7.1)、MAC CE(§6.1.3)
- TS38.322 RLC：TM/UM/AM(§5.2)、ARQ(§5.3)、定时器/参数(§7)
- TS38.323 PDCP：功能(§4.4)、安全(§5.8/5.9)、状态变量与定时器(§7)
- TS38.211/212/213/214 PHY：帧结构/信道、编码、控制过程、数据过程(带clause)
