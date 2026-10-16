---
name: inspireplanet-summary
description: 从启发星球某期会议转写与当期稿件中提炼结构化的单期分享纪要 JSON（summary.json），用于网站每期页面展示“这一期，我们分享了什么”。
---

# Inspire Planet Episode Summary

## 第一阶段：纪要与金句的能力与交付门禁

- 默认使用本人或协作者自己的 AI 工具与订阅，不需要项目模型 API，不共享登录。只有能实际读取完整仓库文件的工具才能按这些规则生成；ChatGPT 对话／浏览器能打开 GitHub 不等于能写仓库。
- 开工先读取当前 main 的 AGENTS、README、current、总控及 summary/cards SKILL、cards EXAMPLES/LEARNINGS 和 events/data-contract；fetch 后确认目标分支、精确 head 与脏状态，保护不相关文件，独立分支，或核对后安全续用同一期转写分支。
- 完整阅读目标期 transcript.txt 与已有 README 授权／匿名边界，不只看片段；只生成用户指定交付物。“第一阶段／纪要＋金句”只做 summary.json 和 quote-cards.json，不扩展文章、封面配置或图片。已有人工文件默认不覆盖，只补缺失项；重做或编辑已有内容须有明确授权。
- 年份＋EP 唯一定位；incoming 先确认期次并归档到 events，不能猜期数或直接生成网站 JSON。事实和署名回查转写，摘录保留单人连续原文依据；隐私、授权与语义需人工审阅，不能用结构校验替代。
- 运行 python3 scripts/check-content.py，检查本期白名单 diff，提交公开 Draft PR，不合并。main 会被网站读取，不是草稿区。
- 没有写文件／执行／GitHub 提交工具时，明确缺少哪项能力，交付可下载的目标路径 JSON 文件与核对说明；未运行的检查标为未运行，不能假称已保存、commit、push 或建 PR。下载文件不等于入库。

手动 Actions 是可选 Plan B，使用同一规则与数据契约，不自动跟随转写执行；未配置项目 API 时不可用。完整设置与边界见 [两条内容生产通道](../../../scripts/content-plan.md)。

## 路径

```text
events/{year}/{YYYYMMDD}-epXX/
  transcript.txt   输入（必读）
  README.md        输入（如有，只参考导航、发布备注与授权边界）
  gzh-*.md         输入（参考已整理的分享脉络，如有）
  quote-cards.json 输入（参考代表金句，如有）
  summary.json     输出
```

## 边界

- 所有人物、经历、问题与现场回应必须来自本期真实转写，不补造事实、不替分享者下结论。
- 以结构化纪要呈现每位分享者的【分享缘起】、【关键脉络要点】、【代表金句】与【现场追问与碰撞】，让未参会的人也能快速看清这场分享聊了什么。
- 遵守本期 `README.md` 发布备注中的隐私与匿名边界。

字段与同步规则见 [内容数据约定](../../../events/data-contract.md)。保持现有字段兼容；年份由目录确定，`episode` 与目录期数一致，`date` 与目录日期一致。代表金句可以与卡片重复，但两份 JSON 不要求一一对应。

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

1. 阅读目标期 `transcript.txt`，以及已有的 `README.md`、`gzh-*.md`、`quote-cards.json`。
2. 从转写梳理本期 2–5 个核心分享话题，已有稿件仅辅助理解，不要求 README 保存会议内容或固定栏目。
3. 为每个话题提炼 `speaker`、`title`、`context`（分享缘起）、3–4 条结构化的 `keyPoints`（关键脉络）、`quote`（代表金句）以及 `discussion`（现场问答碰撞）。
4. 将未单独成篇但有温度的现场互动归入 `highlights`，没有时用空数组；没有现场追问与回应时 `discussion` 用空字符串，不补造问答。
5. 写入 `events/{year}/{YYYYMMDD}-epXX/summary.json`，并运行 `python3 scripts/check-content.py` 验证格式。
