---
name: inspireplanet-transcript
description: 从腾讯会议拉取某一期会议的逐字稿（文字转写），按仓库格式保存为本期目录下的 transcript.txt。
---

# Inspire Planet Transcript

## 目标

把每周线上会议的逐字稿存为对应 event 的 `transcript.txt`，作为本期所有内容的事实来源。可调用脚本从腾讯会议拉取，也可接收用户手动下载的原稿；手动稿原样保存并确认对应日期与期数，无需 CLI 授权。

## 路径

```text
events/{year}/{YYYYMMDD}-epXX/transcript.txt
```

目录日期取腾讯会议返回的**会议时间戳日期（UTC）**，例如 `2026-09-26T00:00:00Z` → `20260926`。

## 前置条件

下载步骤目前暂由孙玲完成，手动下载与 CLI 拉取均如此。已有本期转写时直接进入内容生成；没有时明确标记等待孙玲提供，不要求其他协作者登录孙玲账号或取得她的凭据。孙玲可以在自己的已授权环境中调用本 Skill 完成下载。

以下条件仅适用于脚本拉取：

- 腾讯会议官方 CLI `tmeet` 已安装并在 PATH 中（可用环境变量 `TMEET_BIN` 覆盖路径）；
- 已授权：`tmeet auth login`。过期需重新登录（access token 约 6 小时，refresh token 约 30 天）；
- 凭据在 `~/.tmeet`，**不写入仓库、不复制到对话、不提交**。

## 工作流程

1. 确认本期日期与期数；
2. 运行（按会议时间自动建目录）：

   ```bash
   python3 scripts/pull-transcript.py --date {YYYY-MM-DD} --episode {NN}
   ```

   也可用 `--event {event 目录}` 指定目录，或 `--meeting-id {id} --out {路径}` 直接指定输出。
   `--episode` 必须配合 `--date`：周期会议的 meeting-id 相同，无法区分期数。
   已有 `transcript.txt` 时脚本不覆盖，确需覆盖才加 `--force`；
3. 校验：应有若干 `发言人(HH:MM:SS):` 发言块，正文非空。

转写可能有识别错误，原样保存，不润色。

## 完成后的回复

1. 写入的 `transcript.txt` 路径；
2. 会议名称、发言块数量与大致字数；
3. 是否有授权、隐私或识别错误需要人工确认。
