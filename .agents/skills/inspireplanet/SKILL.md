---
name: inspireplanet
description: 启发星球线上会议纪要发布包总控。用于根据某期会议转写，路由生成会议纪要、金句卡片、独立发布辅助材料和会议纪要公众号封面；不负责个人分享稿，也不负责由个人分享稿改写的文章。
---

# Inspire Planet Publisher

## Event workspace

每期线上会议材料位于同一个 event folder：

```text
events/{year}/{YYYYMMDD}-epXX/
```

常见文件：

```text
meeting/transcript.txt
meeting/recap.md
meeting/promo.md
meeting/quote-cards.json
covers/recap-cover.png
```

只创建真实需要的文件，不补空目录或占位产物。

## 子 Skill

- `inspireplanet-recap`：从会议转写生成只包含纪要正文的 `meeting/recap.md`；
- `inspireplanet-cards`：从会议转写生成 `meeting/quote-cards.json`；
- `inspireplanet-promo`：生成摘要、标题、社交文案和封面副标题候选，保存到 `meeting/promo.md`；
- `inspireplanet-cover`：生成会议纪要封面，并把最终封面配置写回 `meeting/promo.md`。

## 路由

- “整理会议纪要” → `inspireplanet-recap`；
- “金句 / 卡片 / JSON” → `inspireplanet-cards`；
- “标题 / 摘要 / 小红书 / 视频号” → `inspireplanet-promo`；
- “会议封面图” → `inspireplanet-cover`；
- “完整发布包” → recap → cards → promo → cover。

执行完整发布包时，后一步读取前一步的真实产物，不把同一内容复制到多个文件。

## 共享边界

- 会议事实以 `meeting/transcript.txt` 为准；
- `meeting/recap.md` 只保存会议纪要正文；
- `meeting/promo.md` 只保存发布辅助材料与封面配置；
- 这个 Skill 只处理线上会议及其会议纪要发布包；
- `shares/` 中的个人分享稿只是安排在同一期分享，不是会议纪要的输入或产出；
- `articles/` 中由个人分享稿改写的文章不属于这个 Skill；
- 不读取、改写、移动或覆盖个人分享稿及其对应文章，除非用户另行明确指定其他 Skill 处理；
- 不从个人分享稿或 `journals/` 补充会议事实、个人经历或现场状态；
- 活动时间、会议 ID、下一期日期和加入方式从当前项目、event 或用户提供的信息读取，不写死在 Skill 中；
- 文件位置由这次 event 决定，不由发布渠道决定；
- 严禁捏造人物观点、数据、经历和现场状态。
