---
name: inspireplanet
description: 启发星球对外内容工作流总控：从某期会议转写路由生成公众号文章、金句卡片、小红书图文和视频号图文，并负责本期的索引与发布面板 `index.md`。定位是把分享者的分享整理出来、让更多人看见；不负责个人分享稿，也不负责由个人分享稿改写的文章。
---

# Inspire Planet Publisher

## 定位

启发星球的对外内容，目标是**把分享者的分享整理出来被更多人看见**，同时也吸引读者。

所以默认产出不是“记录一场会议”，而是**把一位分享者的一件事做出来**：一期多篇、一篇一个人一件事。会议纪要式的长篇汇总不是默认形态；`index.md` 在仓库里只作本期索引与发布面板。

## Event workspace

每期线上会议材料位于同一个 event folder：

```text
events/{year}/{YYYYMMDD}-epXX/
```

常见文件：

```text
transcript.txt                # 会议原始转写
index.md                      # 本期索引 + 发布面板（本 Skill 产出）
gzh-{slug}.md                 # 公众号分享文章（一位分享者一篇；末尾附标题/摘要）
xhs-{slug}.md                 # 小红书图文（一位分享者一篇）
sph-{slug}.md                 # 视频号图文（一位分享者一篇）
quote-cards.json              # 金句卡片数据
assets/recap-cover.jpg        # 公众号横版封面（多篇时加 -{slug} 后缀）
assets/xiaohongshu-cover.jpg  # 小红书竖版封面
```

文件名规则：**渠道缩写-分享者英文 slug**，例如 `gzh-liying.md`、`xhs-liying.md`、`sph-liying.md`。一期选了谁、哪个渠道有内容，看文件名就知道；同一渠道有多位分享者时就有多个文件。历史期沿用旧的 `recap.md` / `xiaohongshu.md` / `promo.md`，不追溯改名。

只创建真实需要的文件，不补空目录或占位产物。

## 子 Skill

- `inspireplanet-transcript`：从腾讯会议拉取会议逐字稿，保存为 `transcript.txt`；
- `inspireplanet-gzh`：把选中的分享写成公众号分享文章 `gzh-{slug}.md`（含该篇标题、备选标题、摘要）并生成公众号横版封面；
- `inspireplanet-cards`：从会议转写生成 `quote-cards.json`；
- `inspireplanet-xhs`：为一位分享者生成小红书图文材料（标题、封面副标题、图集脚本、正文、话题词）与竖版封面，保存到 `xhs-{slug}.md`；
- `inspireplanet-sph`：为一位分享者生成视频号图文材料（标题、正文、图片脚本、话题词），保存到 `sph-{slug}.md`。

`index.md` 由**本 Skill 直接产出**，不再单独设技能——它是期级材料，不属于任何单一渠道。

## 路由

- “逐字稿 / 转写 / 下载本期逐字稿” → `inspireplanet-transcript`；
- “整理会议纪要 / 写分享文章 / 公众号文章 / 标题 / 摘要” → `inspireplanet-gzh`；
- “金句 / 卡片 / JSON” → `inspireplanet-cards`；
- “小红书 / 图文 / 图集” → `inspireplanet-xhs`；
- “视频号 / 短视频” → `inspireplanet-sph`；
- “封面图 / 会议封面” → 按渠道走 `inspireplanet-gzh`（横版）或 `inspireplanet-xhs`（竖版）；
- “本期索引 / 发布排期 / 发布备注” → 本 Skill；
- “完整发布包” → 见下节。

执行完整发布包时，后一步读取前一步的真实产物，不把同一内容复制到多个文件。

## 整期一次性生成

标准流程：**逐字稿下载后，一次生成各渠道内容；之后的卡片渲染和发布全部由人手动完成。**

用户说“生成这一期的内容 / 全套内容 / 一次把各渠道都生成好”时，按顺序一次做完：

1. **逐字稿**（缺 `transcript.txt` 时）→ `inspireplanet-transcript`；
2. **公众号文章 + 标题/摘要 + 横版封面** → `inspireplanet-gzh`：`gzh-{slug}.md`（一期通常 1–2 篇，篇幅由内容决定）+ `assets/recap-cover.jpg`；
3. **本期索引与发布面板** → 本 Skill：`index.md`；
4. **小红书图文** → `inspireplanet-xhs`；
5. **视频号图文** → `inspireplanet-sph`；
6. **金句卡片** → `inspireplanet-cards`：`quote-cards.json`。

生成阶段产出文字文件与封面成品；卡片图渲染（`scripts/text-cards/render.py`）和发布都由人手动完成，不在这条链里烧时间。

## index.md（本 Skill 产出）

`index.md` 是**本期索引 + 发布面板**，仓库内材料，**不单独发公众号**。

```md
# EPXX｜本期索引

一句话概括本期

## 这一期有谁
- {名字}：[{这件事的题眼}](gzh-{slug}.md)

## 这一期还聊到
{没能单独成篇的内容，一两句}

## 发布排期

| 顺序 | 文件 | 建议发布 |
|---|---|---|
| 1 | `gzh-{slug}.md` | 第 1 天 |

## 公众号封面配置

### {slug}（`gzh-{slug}.md`）
- 最终副标题：
- 视觉命题：
- 生成提示词：
- 成品路径：assets/recap-cover.jpg

## 发布备注
- 待人工确认的事实、授权、时间
```

规则：

- **不写文章摘要、不放文章正文**——那些跟着各自的 `gzh-{slug}.md` 走；
- **不放二维码插入位**：`index.md` 不对外发布，二维码落在 `gzh-{slug}.md` 末尾；
- 「发布排期」只放**公众号**的跨篇顺序（公众号一期多篇，排期不属于任何单篇）；小红书、视频号各自的排期写在各自的 `xhs-*.md` / `sph-*.md` 里；
- 「公众号封面配置」由 `inspireplanet-gzh` 出图后回写；已有 `index.md` 时只更新对应篇，不覆盖索引正文与发布备注；
- 只写真实存在的篇目，不补空小节占位。

## 选题与排期

- **每期不必覆盖每一位分享者**：按渠道各自挑值得发的，1–2 位即可；
- **各渠道可以挑不同的人**：公众号、小红书、视频号独立选题，不要为了“一视同仁”把所有人都塞进去；
- 一期里同一渠道**每隔一天发一篇**；
- 生成本期材料时，把“这个渠道选了谁、建议的发布顺序”写进对应位置：公众号写进 `index.md` 的「发布排期」，小红书 / 视频号写进各自文件开头的 `## 发布排期`。

## 共享边界

- 会议事实以 `transcript.txt` 为准；
- `index.md` 是本期索引与发布面板（仓库内材料，不单独发公众号）；`gzh-{slug}.md` 才是发公众号的分享文章；
- `gzh-{slug}.md` 同时保存该篇的发布信息（标题、备选标题、摘要）与公众号横版封面配置；官网封面成品在 `assets/recap-cover.jpg`；
- `xhs-{slug}.md` 只保存小红书图文材料与竖版封面配置，一位分享者一个文件；渲染成图和发布都是人工触发，不并入自动链；
- `sph-{slug}.md` 只保存视频号图文材料（标题 + 正文 + 图片脚本），一位分享者一个文件；出图和发布都是人工触发，图片可与小红书共用；
- 封面设计原则与 JPEG 保存规范见 `.agents/skills/inspireplanet/references/cover-design.md`，公众号与小红书共用一份，避免两份漂移；
- 这个 Skill 只处理线上会议及其发布包；
- `shares/` 中的个人分享稿只是安排在同一期分享，不是会议内容的输入或产出；
- `articles/` 中由个人分享稿改写的文章不属于这个 Skill；
- 不读取、改写、移动或覆盖个人分享稿及其对应文章，除非用户另行明确指定其他 Skill 处理；
- 不从个人分享稿或 `journals/` 补充会议事实、个人经历或现场状态；
- 活动时间、会议 ID、下一期日期和加入方式从当前项目、event 或用户提供的信息读取，不写死在 Skill 中；
- 文件位置由这次 event 决定，不由发布渠道决定；
- 严禁捏造人物观点、数据、经历和现场状态。
