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
  cover-configs.md              本期所有封面的配置、设计信息与复用关系
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

## 整期生成

用户要“生成这一期的内容 / 全套内容”时，按顺序做完：

1. 缺 `transcript.txt` 时 → `inspireplanet-transcript`；
2. `inspireplanet-gzh`；
3. `inspireplanet-xhs`；
4. `inspireplanet-sph`；
5. `inspireplanet-cards`；
6. 最后写 `README.md`。

卡片图渲染由人手动触发，不在这条链里做。

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
| `xhs-{slug}.md` | 小红书图文：{名字} | 小红书 | 待发 |
| `sph-{slug}.md` | 视频号图文：{名字} | 视频号 | 待发 |
| `quote-cards.json` | 金句卡片数据 | 渲染后发 | 待发 |
| `cover-configs.md` | 封面配置与设计信息 | 否 | 已配置 |

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
- 状态用 `待确认` / `待本人过目` / `待发` / `已发 YYYY-MM-DD`。
