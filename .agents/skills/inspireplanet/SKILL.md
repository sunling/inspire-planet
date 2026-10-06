---
name: inspireplanet
description: 启发星球对外内容工作流总控：从某期会议转写路由生成分享文章（公众号）、金句卡片、小红书图文材料、视频号材料和封面。定位是把分享者的分享整理出来、让更多人看见；不负责个人分享稿，也不负责由个人分享稿改写的文章。
---

# Inspire Planet Publisher

## 定位

启发星球的对外内容，目标是**把分享者的分享整理出来被更多人看见**，同时也吸引读者。

所以默认产出不是“记录一场会议”，而是**把一位分享者的一件事做出来**：一期多篇、一篇一个人一件事。会议纪要式的长篇汇总不是默认形态；`index.md` 在仓库里只作本期索引。

## Event workspace

每期线上会议材料位于同一个 event folder：

```text
events/{year}/{YYYYMMDD}-epXX/
```

常见文件：

```text
transcript.txt
index.md              # 本期索引
gzh-{slug}.md         # 公众号分享文章（一位分享者一篇）
xhs-{slug}.md         # 小红书图文（一位分享者一篇）
sph-{slug}.md         # 视频号图文（一位分享者一篇）
promo.md              # 发布材料与封面配置
quote-cards.json
covers/recap-cover.jpg
```

文件名规则：**渠道缩写-分享者英文 slug**，例如 `gzh-liying.md`、`xhs-liying.md`、`sph-liying.md`。一期选了谁、哪个渠道有内容，看文件名就知道；同一渠道有多位分享者时就有多个文件。历史期沿用旧的 `recap.md` / `xiaohongshu.md`，不追溯改名。

只创建真实需要的文件，不补空目录或占位产物。

## 子 Skill

- `inspireplanet-transcript`：从腾讯会议拉取会议逐字稿，保存为 `transcript.txt`；
- `inspireplanet-recap`：把选中的分享写成可独立阅读的公众号分享文章，另生成仓库内的本期索引；
- `inspireplanet-cards`：从会议转写生成 `quote-cards.json`；
- `inspireplanet-promo`：为各篇分享文章生成标题、摘要和封面副标题候选，保存到 `promo.md`；
- `inspireplanet-xhs`：为一位分享者生成小红书图文材料（标题、封面副标题、图集脚本、正文、话题词），保存到 `xhs-{slug}.md`；
- `inspireplanet-sph`：为一位分享者生成视频号图文材料（标题、正文、图片脚本、话题词），保存到 `sph-{slug}.md`；
- `inspireplanet-cover`：生成会议纪要封面，并把最终封面配置写回 `promo.md`。

## 路由

- “逐字稿 / 转写 / 下载本期逐字稿” → `inspireplanet-transcript`；
- “整理会议纪要 / 写分享文章” → `inspireplanet-recap`；
- “金句 / 卡片 / JSON” → `inspireplanet-cards`；
- “标题 / 摘要 / 公众号” → `inspireplanet-promo`；
- “小红书 / 图文 / 图集” → `inspireplanet-xhs`；
- “视频号 / 短视频” → `inspireplanet-sph`；
- “会议封面图” → `inspireplanet-cover`；
- “完整发布包” → transcript（缺失时）→ recap（分篇）→ promo → cards → xiaohongshu → shipinhao → cover。

执行完整发布包时，后一步读取前一步的真实产物，不把同一内容复制到多个文件。

## 整期一次性生成

标准流程：**逐字稿下载后，一次生成各渠道内容；之后的渲染和发布全部由人手动完成。**

用户说“生成这一期的内容 / 全套内容 / 一次把各渠道都生成好”时，按顺序一次做完：

1. **逐字稿**（缺 `transcript.txt` 时）→ `inspireplanet-transcript`；
2. **公众号分享文章** → `inspireplanet-recap`：`index.md`（本期索引，200–400 字，不发公众号）+ `gzh-{slug}.md`（分享文章，一期通常 1–2 篇，篇幅由内容决定）；
3. **公众号发布材料** → `inspireplanet-promo`：每篇一个标题与摘要；
4. **小红书图文材料** → `inspireplanet-xhs`；
5. **视频号图文材料** → `inspireplanet-sph`。

生成阶段**只产出文字文件**：图片渲染（`scripts/render-cards.py`）和发布都由人手动完成，不在这条链里烧时间。

金句卡片（`inspireplanet-cards`）不在默认链里，用户明确要时才做。

## 选题与排期

- **每期不必覆盖每一位分享者**：按渠道各自挑值得发的，1–2 位即可；
- **各渠道可以挑不同的人**：公众号、小红书、视频号独立选题，不要为了“一视同仁”把所有人都塞进去；
- 一期里同一渠道**每隔一天发一篇**；
- 生成本期材料时，把"这个渠道选了谁、建议的发布顺序"写进对应文件开头的 `## 发布排期`。

## 共享边界

- 会议事实以 `transcript.txt` 为准；
- `index.md` 是本期索引（仓库内材料，不单独发公众号）；`gzh-{slug}.md` 才是发公众号的分享文章；
- `promo.md` 只保存公众号发布材料与封面配置；
- `xhs-{slug}.md` 只保存小红书图文材料，一位分享者一个文件；渲染成图和发布都是人工触发，不并入自动链；
- `sph-{slug}.md` 只保存视频号图文材料（标题 + 正文 + 图片脚本），一位分享者一个文件；出图和发布都是人工触发，图片可与小红书共用；
- 这个 Skill 只处理线上会议及其会议纪要发布包；
- `shares/` 中的个人分享稿只是安排在同一期分享，不是会议纪要的输入或产出；
- `articles/` 中由个人分享稿改写的文章不属于这个 Skill；
- 不读取、改写、移动或覆盖个人分享稿及其对应文章，除非用户另行明确指定其他 Skill 处理；
- 不从个人分享稿或 `journals/` 补充会议事实、个人经历或现场状态；
- 活动时间、会议 ID、下一期日期和加入方式从当前项目、event 或用户提供的信息读取，不写死在 Skill 中；
- 文件位置由这次 event 决定，不由发布渠道决定；
- 严禁捏造人物观点、数据、经历和现场状态。
