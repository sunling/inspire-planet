# 内容制作说明

每期从真实会议转写与回放整理内容，只制作实际需要的交付物，不要求每期生成全部渠道材料。公开与发布须有当事人授权。

## 1. 下载与归档转写

通过 GitHub Actions 的 **Transcript download** 获取最新会议；历史会议使用 **Historical transcript (advanced)**，见 [下载说明](meeting-content.md)。转写通过校验后直接提交公开 `main`，运行前确认公开授权；期次不确定时写入 `incoming/meetings/`。已有本期 `transcript.txt` 无需重复下载；原始转写不润色。

## 2. 按需生成文章、纪要与金句

先读 [AGENTS.md](../AGENTS.md)。公众号使用 `inspireplanet-gzh`，网站纪要使用 `inspireplanet-summary`，金句使用 `inspireplanet-cards`；组合整理可用 `inspireplanet`，只生成请求的内容。

> 使用 inspireplanet，基于本期 transcript.txt 整理公众号文章、summary.json 和 quote-cards.json，核对事实与署名并更新本期导航。

字段和网站读取方式遵循 [内容数据约定](../events/data-contract.md)。单期 README 只维护导航、实际可用的命令和发布备注，不记录制作进度。

## 3. 小红书与视频号：原声短视频

两平台统一使用 [inspireplanet-clips](../.agents/skills/inspireplanet-clips/SKILL.md)。用户手动下载回放，直接放入被 Git 忽略的 `replays/`；沿用实际文件位置，不要求每期再建源文件夹。

> 使用 inspireplanet-clips，检查本期本地回放和转写，推荐短视频选段；我确认后再生成初剪、字幕与小红书和视频号的纯文本发布文案。

先核对实际媒体时间，再按确认选段剪辑；审片检查字幕、跳切、画面和公开范围。默认使用视频首帧，不单独出封面；有明确用途时才另做。官网和社群入口读取 `current.md` 已确认部分，每个平台正文只保留一个主要入口。

回放、识别结果、剪辑单、字幕、文案和成片都留在本地 `replays/`，不上传会议素材。历史 `xhs-*.md`、`sph-*.md` 留作存档，不再生成新的图文脚本；图文 skills、图卡渲染器、配套测试和出图工作流已移除。

## 4. 审阅与发布

分享者本人确认具体稿件、署名、家庭或他人信息和公开范围；原声短视频另需确认肖像、原声、他人话语与具体剪辑。选段确认不代表成片确认或发布授权。

用户检查后发布；只有收到明确发布指令，才操作外部平台。公开稿件的授权边界、待核对事实、发布日期和平台链接可放在单期 README 的发布备注中；私人短视频资料的制作与审核记录留在本地。

活动安排只使用经过确认的 [current.md](../current.md)。修改公开文件后运行 `python3 scripts/check-content.py`；提交到供网站读取的 `main` 前再次核对授权。
