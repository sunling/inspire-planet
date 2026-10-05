---
name: inspireplanet
description: 启发星球线上会议纪要发布包总控。用于根据某期会议转写，路由生成会议纪要、金句卡片、小红书图文材料、公众号发布辅助材料、视频号材料和会议纪要公众号封面；不负责个人分享稿，也不负责由个人分享稿改写的文章。
---

# Inspire Planet Publisher

## Event workspace

每期线上会议材料位于同一个 event folder：

```text
events/{year}/{YYYYMMDD}-epXX/
```

常见文件：

```text
transcript.txt
recap.md
promo.md
xiaohongshu.md
shipinhao.md
quote-cards.json
covers/recap-cover.png
```

只创建真实需要的文件，不补空目录或占位产物。

## 子 Skill

- `inspireplanet-transcript`：从腾讯会议拉取会议逐字稿，保存为 `transcript.txt`；
- `inspireplanet-recap`：从会议转写生成只包含纪要正文的 `recap.md`；
- `inspireplanet-cards`：从会议转写生成 `quote-cards.json`；
- `inspireplanet-promo`：生成公众号摘要、标题和封面副标题候选，保存到 `promo.md`；
- `inspireplanet-xhs`：为一位分享者生成小红书图文材料（标题、封面副标题、图集脚本、正文、话题词），保存到 `xiaohongshu.md`；
- `inspireplanet-sph`：为一位分享者生成视频号图文材料（标题、正文、图片脚本、话题词），保存到 `shipinhao.md`；
- `inspireplanet-cover`：生成会议纪要封面，并把最终封面配置写回 `promo.md`。

## 路由

- “逐字稿 / 转写 / 下载本期逐字稿” → `inspireplanet-transcript`；
- “整理会议纪要” → `inspireplanet-recap`；
- “金句 / 卡片 / JSON” → `inspireplanet-cards`；
- “标题 / 摘要 / 公众号” → `inspireplanet-promo`；
- “小红书 / 图文 / 图集” → `inspireplanet-xhs`；
- “视频号 / 短视频” → `inspireplanet-sph`；
- “会议封面图” → `inspireplanet-cover`；
- “完整发布包” → transcript（缺失时）→ recap（分篇）→ promo → cards → xiaohongshu → shipinhao → cover。

执行完整发布包时，后一步读取前一步的真实产物，不把同一内容复制到多个文件。

## 整期一次性生成

用户说“生成这一期的内容 / 全套内容 / 一次把各渠道都生成好”时，按顺序一次做完：

1. **逐字稿**（缺 `transcript.txt` 时）→ `inspireplanet-transcript`；
2. **公众号纪要分篇** → `inspireplanet-recap`：`recap.md`（总览，300–600 字）+ `recap-{序}-{slug}.md`（每人一篇，450–1000 字）；
3. **公众号发布材料** → `inspireplanet-promo`：每篇一个标题与摘要；
4. **小红书图文材料** → `inspireplanet-xhs`；
5. **视频号图文材料** → `inspireplanet-sph`。

生成阶段**只产出文字文件**：图片渲染（`scripts/render-cards.py`）和发布都由人手动完成，不在这条链里烧时间。

金句卡片（`inspireplanet-cards`）不在默认链里，用户明确要时才做。

## 共享边界

- 会议事实以 `transcript.txt` 为准；
- `recap.md` 只保存会议纪要正文；
- `promo.md` 只保存公众号发布材料与封面配置；
- `xiaohongshu.md` 只保存小红书图文材料，一期可多篇、每篇一节；渲染成图和发布都是人工触发，不并入自动链；
- `shipinhao.md` 只保存视频号图文材料（标题 + 正文 + 图片脚本），一期可多条；出图和发布都是人工触发，图片可与小红书共用；
- 这个 Skill 只处理线上会议及其会议纪要发布包；
- `shares/` 中的个人分享稿只是安排在同一期分享，不是会议纪要的输入或产出；
- `articles/` 中由个人分享稿改写的文章不属于这个 Skill；
- 不读取、改写、移动或覆盖个人分享稿及其对应文章，除非用户另行明确指定其他 Skill 处理；
- 不从个人分享稿或 `journals/` 补充会议事实、个人经历或现场状态；
- 活动时间、会议 ID、下一期日期和加入方式从当前项目、event 或用户提供的信息读取，不写死在 Skill 中；
- 文件位置由这次 event 决定，不由发布渠道决定；
- 严禁捏造人物观点、数据、经历和现场状态。
