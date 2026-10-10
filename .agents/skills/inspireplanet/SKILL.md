---
name: inspireplanet
description: 启发星球对外内容总控：从某期会议转写一次生成公众号文章、小红书和视频号图文、金句卡片，并写本期索引 `README.md`。目标是把分享者的分享整理出来，让更多人看见。
---

# Inspire Planet

## 定位

把分享者的分享整理出来，让更多人看见。默认产出是**一位分享者的一件事**：一期多篇，一篇一个人一件事，不写会议纪要式的长篇汇总。

## 本期目录

```text
events/{year}/{YYYYMMDD}-epXX/
  transcript.txt                会议原始转写
  gzh-{slug}.md                 公众号文章（文末附标题、摘要、封面成品路径）
  xhs-{slug}.md                 小红书图文
  sph-{slug}.md                 视频号图文
  quote-cards.json              金句卡片
  cover/cover-configs.md              本期所有封面的配置、设计信息与复用关系
  assets/recap-cover.jpg        公众号横版封面（多篇时加 -{slug}）
  assets/xiaohongshu-cover.jpg  小红书竖版封面（多篇时加 -{slug}）
  README.md                     本期索引与发布状态
```

`{slug}` 是分享者的英文小写名，一位分享者一个文件，如 `gzh-liying.md`。只创建真实需要的文件。

## 路由

- 逐字稿 / 转写 → `inspireplanet-transcript`
- 公众号文章 / 标题 / 摘要 / 横版封面 → `inspireplanet-gzh`
- 小红书 / 图集 / 竖版封面 → `inspireplanet-xhs`
- 视频号 → `inspireplanet-sph`
- 金句 / 卡片 JSON → `inspireplanet-cards`
- 本期索引 / 发布状态 → 本 Skill

## 工作流程

1. **取得转写**：可用 `inspireplanet-transcript` 调用拉取脚本，也可使用用户手动下载的转写稿，原样保存为本期 `transcript.txt`；已有稿件不重复拉取。
2. **生成内容**：用户要全套时，依次生成公众号、小红书、视频号、金句卡片 JSON；用户只要某个渠道或单个交付物时只生成对应内容。此阶段不渲染图片。
3. **生成封面脚本**：依据已生成的文章和图文首图，把对应的封面文字、视觉命题、完整配置和复用关系集中写入 `cover/cover-configs.md`。整期生成时先完成全部内容，再统一汇总配置；单独生成渠道内容时只更新相关配置，保留其他小节。只生成金句 JSON 时无需新建封面配置。运行 `scripts/covers/assign_themes.py {本期目录}/cover/cover-configs.md`，把未指定主题的配置随机均衡分配为具体主题，再更新本期 `README.md`，标记脚本待确认。确认后按已保存的主题渲染，不重新抽选。
4. **确认后渲染**：向用户交付具体稿件和封面脚本，等待用户明确确认相关脚本后再渲染文字卡及封面。已有确认在脚本未变时继续有效；用户在同一请求中明确确认已有脚本并要求渲染时可直接执行。改动图中文字或视觉命题后重新确认受影响部分。

封面出图方法见 `scripts/covers/README.md`；文字卡见 `scripts/text-cards/README.md`。封面成品存本期 `assets/`，文字卡图集存仓库外；图集首图按已确认的复用关系替换为对应竖版封面，再刷新总览与打包文件。渲染后核对裁切、溢出、重叠及文字，并更新本期状态。渲染确认与对外发布授权分别记录。

## README.md

本期目录下的 `README.md` 是仓库内的索引，不对外发布：

```md
# EPXX｜{YYYY-MM-DD}

{一句话概括本期}

## 本期文件

| 文件 | 是什么 | 对外发布 | 状态 |
|---|---|---|---|
| `transcript.txt` | 会议原始转写 | 否 | — |
| `gzh-{slug}.md` | 公众号文章：{名字} | 公众号 | 待本人过目 |
| `xhs-{slug}.md` | 小红书图文：{名字} | 小红书 | 待确认 |
| `sph-{slug}.md` | 视频号图文：{名字} | 视频号 | 待确认 |
| `quote-cards.json` | 金句卡片数据 | 渲染后发 | 待确认 |
| `cover/cover-configs.md` | 封面配置与设计信息 | 否 | 待确认 |

## 这一期有谁
- {名字}：[{这件事}](gzh-{slug}.md) · [小红书](xhs-{slug}.md) · [视频号](sph-{slug}.md)

## 这一期还聊到
{没能单独成篇的分享，一两句}

## 选题
{各渠道选了谁、为什么；没选的为什么没选}

## 发布备注
- {署名授权、需本人过目的篇目、未确认的事实或时间、隐私处理}
```

- 只列真实存在的文件和篇目，不补空小节；
- 不放文章正文和摘要；
- 制作状态记录 `待确认` / `待渲染` / `已渲染`；发布状态记录 `待本人过目` / `待发` / `已发 YYYY-MM-DD`，在表格或备注中分别注明。
