---
name: inspireplanet-summary
description: 从启发星球某期会议转写与当期稿件中提炼结构化的单期分享纪要 JSON（summary.json），用于网站每期页面展示“这一期，我们分享了什么”。
---

# Inspire Planet Episode Summary

## 路径

```text
events/{year}/{YYYYMMDD}-epXX/
  transcript.txt   输入（必读）
  README.md        输入（参考本期选题与核对记录）
  gzh-*.md         输入（参考已整理的分享脉络，如有）
  quote-cards.json 输入（参考代表金句，如有）
  summary.json     输出
```

## 边界

- 所有人物、经历、问题与现场回应必须来自本期真实转写，不补造事实、不替分享者下结论。
- 既保留主要分享者的完整脉络（具体处境、尝试与变化），也保留星友之间的现场追问、碰撞与未单独成篇的讨论片段。
- 遵守本期 `README.md` 发布备注中的隐私与匿名边界。

## JSON 格式

输出纯 JSON 对象（UTF-8，2 空格缩进），字段顺序如下：

```json
{
  "episode": "EPXX",
  "date": "YYYY-MM-DD",
  "title": "本期一句话主标题（12–28 字，串联本期核心场景或问题）",
  "overview": "本期整体导语（80–160 字，交代这期谁带来了什么经历、现场围绕哪些真实问题展开）",
  "topics": [
    {
      "speaker": "分享者署名",
      "title": "这位分享者的主题标题（8–22 字）",
      "summary": "分享脉络（120–220 字：从什么具体经历或困境出发，做了什么尝试，观察到了什么变化）",
      "discussion": "现场回响与延伸讨论（60–150 字：其他伙伴如何回应、追问或补充了不同视角；若无独立延伸可省略或写简短回应）",
      "quote": "最能代表这段分享的一句原话或轻整理表达"
    }
  ],
  "highlights": [
    "未单独成篇但值得留下的现场片段、首次参与伙伴的回应或问题圆桌讨论（每条 40–100 字）"
  ]
}
```

## 工作流程

1. 阅读目标期 `transcript.txt`、`README.md` 以及已有的 `gzh-*.md`、`quote-cards.json`。
2. 梳理本期 2–5 个核心分享段落，分别提炼 `speaker`、`title`、`summary`、`discussion` 和 `quote`。
3. 检查是否有未单独写成公众号文章但有温度的现场互动（如新朋友发言、圆桌提问、即兴回应），归入 `highlights`。
4. 写入 `events/{year}/{YYYYMMDD}-epXX/summary.json`，并在本期 `README.md` 稿件导航中补充 `纪要：[JSON](summary.json)`（如适用）。
5. 运行 `python3 scripts/check-content.py` 验证格式与链接。
