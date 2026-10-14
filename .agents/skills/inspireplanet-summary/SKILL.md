---
name: inspireplanet-summary
description: 从启发星球某期会议转写与当期稿件中提炼结构化的单期分享纪要 JSON（summary.json），用于网站每期页面展示“这一期，我们分享了什么”。
---

# Inspire Planet Episode Summary

## 路径

```text
events/{year}/{YYYYMMDD}-epXX/
  transcript.txt   输入（必读）
  README.md        输入（参考本期选题概览与从转写整理出的关键脉络）
  gzh-*.md         输入（参考已整理的分享脉络，如有）
  quote-cards.json 输入（参考代表金句，如有）
  summary.json     输出
```

## 边界

- 所有人物、经历、问题与现场回应必须来自本期真实转写，不补造事实、不替分享者下结论。
- 以结构化纪要呈现每位分享者的【分享缘起】、【关键脉络要点】、【代表金句】与【现场追问与碰撞】，让未参会的人也能快速看清这场分享聊了什么。
- 遵守本期 `README.md` 发布备注中的隐私与匿名边界。

## JSON 格式

输出纯 JSON 对象（UTF-8，2 空格缩进），字段顺序如下：

```json
{
  "episode": "EPXX",
  "date": "YYYY-MM-DD",
  "title": "本期一句话主标题（12–28 字，串联本期核心场景或问题）",
  "overview": "本期整体导语（80–150 字，交代这期谁带来了什么经历、现场围绕哪些真实问题展开）",
  "topics": [
    {
      "speaker": "分享者署名",
      "title": "这位分享者的主题标题（8–22 字）",
      "context": "分享缘起与处境（40–90 字：交代这段分享从什么具体生活/工作场景或问题出发）",
      "keyPoints": [
        "脉络要点 1（50–100 字：最初的触发点、困惑或观察）",
        "脉络要点 2（50–100 字：过程中的具体经历、发现或转折）",
        "脉络要点 3（50–100 字：回到现实行动中的尝试、判断或变化）"
      ],
      "quote": "最能代表这段分享的一句原话或轻整理表达",
      "discussion": "现场回响与延伸讨论（60–150 字：其他伙伴如何回应、追问或补充了不同视角）"
    }
  ],
  "highlights": [
    "未单独归入上述主题但值得留下的现场片段、新朋友回应或问题圆桌讨论（每条 40–100 字）"
  ]
}
```

## 工作流程

1. 阅读目标期 `transcript.txt`、`README.md` 以及已有的 `gzh-*.md`、`quote-cards.json`。
2. 对照 `README.md` 的「选题概览」与「从转写整理出的关键脉络」，梳理本期 2–5 个核心分享话题。
3. 为每个话题提炼 `speaker`、`title`、`context`（分享缘起）、3–4 条结构化的 `keyPoints`（关键脉络）、`quote`（代表金句）以及 `discussion`（现场问答碰撞）。
4. 将未单独成篇但有温度的现场互动归入 `highlights`。
5. 写入 `events/{year}/{YYYYMMDD}-epXX/summary.json`，并运行 `python3 scripts/check-content.py` 验证格式。
