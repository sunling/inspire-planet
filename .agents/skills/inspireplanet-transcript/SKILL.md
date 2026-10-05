---
name: inspireplanet-transcript
description: 从腾讯会议拉取某一期会议的逐字稿（文字转写），按仓库格式保存为 transcript.txt，并衔接会议纪要与金句生成。
---

# Inspire Planet Transcript

## 目标

把每周线上会议的逐字稿从腾讯会议取下来，落到对应 event 的 `transcript.txt`，作为 `inspireplanet-recap`、`inspireplanet-cards`、`inspireplanet-promo` 的输入。

## 路径

event 目录：

```text
events/{year}/{YYYYMMDD}-epXX/
```

输出：

```text
transcript.txt
```

目录名里的日期取腾讯会议返回的**会议时间戳日期（UTC）**，例如 `2026-09-26T00:00:00Z` → `20260926`。
2026-10-06 起，全部期目录（含历史 33 期）已统一按此口径命名。

## 前置条件

- 腾讯会议官方 CLI `tmeet` 已安装并可从 PATH 调用（可用环境变量 `TMEET_BIN` 覆盖路径）；
- 已授权：`tmeet auth login`。授权过期需重新登录（access token 约 6 小时，refresh token 约 30 天）；
- 凭据保存在 `~/.tmeet`，**不写入仓库、不复制到对话、不提交**。

## 工作流程

1. 读 `AGENTS.md`，确认本期日期与期数；
2. `events/{year}` 或 event 目录不存在时，先创建年份目录，再建立 event 目录 `events/{year}/{YYYYMMDD}-epXX/`；只创建真实需要的文件；
3. 运行（用会议时间自动生成目录）：

   ```bash
   python3 scripts/pull-transcript.py --date {YYYY-MM-DD} --episode {NN}
   ```

   也可用 `--event {event 目录}` 指定目录，或用 `--meeting-id {id} --out {路径}` 直接指定输出。
   `--episode` 必须配合 `--date`：周期会议的 meeting-id 相同，无法区分是哪一期。
   脚本默认不覆盖已有 `transcript.txt`，确需覆盖再加 `--force`；
4. 校验输出：应包含若干形如 `发言人(HH:MM:SS):` 的发言块，正文非空；
5. 按下方“衔接”进入后续技能。

## 衔接

逐字稿落地后，按需要继续：

- 会议纪要 → `inspireplanet-recap`：`transcript.txt` → `recap.md`；
- 金句卡片 → `inspireplanet-cards`：`transcript.txt` → `quote-cards.json`；
- 发布文案 → `inspireplanet-promo`；封面 → `inspireplanet-cover`。

用户说“整理完整发布包”时，若 `transcript.txt` 缺失则先取逐字稿，再依次 recap → cards → promo → cover。

## 边界

- 转写来自腾讯会议，可能含识别错误；原始转写不随编辑稿润色，纠错须有依据并注明更正；
- 不从个人日记或个人分享稿补造会议事实；
- 不自动覆盖已有 `transcript.txt`；
- 年份不存在时先创建 `events/{year}`，不把新一年的内容写进旧年份目录；
- 公开归档前检查参与者授权范围与可识别隐私；
- 不自动对外发布或发送消息。

## 完成后的回复

1. 写入的 `transcript.txt` 路径；
2. 会议名称、发言块数量与大致字数；
3. 建议的下一步（recap / cards）；
4. 是否有授权、隐私或识别错误需要人工确认。
