# .claude/ — 项目级 agent 配置

本仓库的项目级 skill 与工具流配置，Claude Code 与 WorkBuddy 双环境共用。

## 结构

```
.claude/
├── README.md            # 本说明
└── skills/
    └── 3gpp-spec-downloader/   # 唯一实体（源头）
        ├── SKILL.md            # 操作手册 / 总入口
        └── scripts/            # 全部维护脚本（2026-09-07 自仓库根 scripts/ 迁入）
```

## 双入口约定（防漂移）

| 入口 | 类型 | 加载方 |
|------|------|--------|
| `.claude/skills/3gpp-spec-downloader/` | **实体（源头）** | Claude Code |
| `.workbuddy/skills/3gpp-spec-downloader` | symlink → 实体 | WorkBuddy |
| `~/.workbuddy/skills/3gpp-spec-downloader/` | 单向镜像（仓库外用） | WorkBuddy（全局） |

- **禁止**在 `.workbuddy/skills/` 或用户级 skill 里维护第二份脚本内容——实体只有一份
- 修改脚本/文档一律改 `.claude/skills/3gpp-spec-downloader/`，再同步用户级镜像
  （命令见 SKILL.md「维护与同步」）

## 变更史

- 2026-09-07：创建本目录；仓库根 `scripts/` 整体 `git mv` 迁入 skill 捆绑目录；
  5 个脚本仓库根定位改为向上探测 `.git`（`_repo_root()`），无 `.git` 时回退上溯 2 层
  （兼容仓库外运行）；建 `.workbuddy/skills` symlink；用户级 skill 源头指向更新。
