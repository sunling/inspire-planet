# 迁移说明

2026-10-04，从 `sunling/sunling-os` 的启发星球实践目录拆出共同会议内容。本仓库只导入所列文件，不导入私人仓库提交历史。

迁移范围：33 份转写、15 篇会议纪要、17 份金句 JSON、16 份金句笔记、10 份发布文案、7 张会议封面，以及 5 个 skills 的完整目录（14 个文件）。当前运营配置迁至根目录 `current.md`。

逐文件来源和原始 Git blob SHA 见 [migration-manifest.json](migration-manifest.json)。转写原文与金句保持原样；skills 的目录引用及纪要中的旧本机封面路径随迁移修正。

路径修正：EP33 的 `trascript.txt` 更正为 `transcript.txt`；EP36 与 EP38 根目录转写归入 `meeting/`；EP37 的纯文本转写从 `transcript.md` 统一为 `transcript.txt`。保留历史 EP32 目录的既有日期，本次不猜测实际日期。

2024–2025 历史个人分享、个人文章、个人演示和配图，以及一对一实验资料与 EP29 实验封面留在原仓库。EP39 目前只有个人分享，没有可迁移会议资料。

2026-10-05，原仓库清理 [PR #96](https://github.com/sunling/sunling-os/pull/96) 已合并，系统结构与内容完整性 CI 均通过。已迁移的共同文件从原仓库主分支移除，个人材料保留原位。今后请以本仓库为共同会议内容的维护位置。

2026-10-06，调整 events 目录结构：去掉每期下的 `meeting/` 子目录，会议文件直接放在期目录下，`covers/` 保留；同时把历史 33 期的目录日期由会议当天的西雅图日期改为会议时间戳日期（北京时间，即原目录 +1 天），例如 `20260925-ep38` 改为 `20260926-ep38`。`migration-manifest.json` 的 `source_path` 保留原仓库来源，未改动。

2026-10-06，封面产出规范化，两处变更：

1. 每期图片目录由 `covers/` 更名为 `assets/`（6 期已迁移目录一并改名）。`migration-manifest.json` 只更新 `target_path`，`source_path` 仍保留原仓库来源；`recap.md`、`promo.md`、`README.md`、`events/README.md` 与相关 skills 中的路径引用同步更新。
2. 封面成品由 PNG 改为 JPEG（`quality=88`、`optimize`、`progressive`，横版宽度 ≥1920px、竖版 1080×1440），单张体积约为原来的 1/10。历史 PNG 文件保留原位、不追溯转换；新格式的保存规范写在 `.agents/skills/inspireplanet-cover/SKILL.md`。

2026-10-06，skills 按「交付物」重组，取消 `inspireplanet-recap`、`inspireplanet-promo`、`inspireplanet-cover` 三个技能：

1. 新增 `inspireplanet-gzh`，承接原 `inspireplanet-recap` 的文章能力、原 `inspireplanet-promo` 的标题与摘要能力，以及原 `inspireplanet-cover` 的公众号横版封面能力；产出 `gzh-{slug}.md`（正文 + 文件末尾的标题、备选标题、摘要）与 `assets/recap-cover.jpg`。
2. 期级材料（本期索引、发布排期、公众号封面配置、发布备注）合并进 `index.md`，由总控 `inspireplanet` 产出，不再新增 `promo.md`。小红书竖版封面并入 `inspireplanet-xhs`，成品 `assets/xiaohongshu-cover.jpg`。
3. 封面设计原则与 JPEG 保存规范抽到 `.agents/skills/inspireplanet/references/cover-design.md`，公众号与小红书共用一份，避免两份漂移。
4. 二维码插入位由 `index.md` 移到 `gzh-{slug}.md`：`index.md` 是仓库内材料、不对外发布，原先由它承担二维码落点没有实际用途。
5. `migration-manifest.json` 中原 `inspireplanet-recap`、`inspireplanet-promo`、`inspireplanet-cover` 的条目只更新 `target_path` 到内容现在的所在位置，`source_path` 仍保留原仓库来源。历史期的 `recap.md` / `promo.md` 与已有 PNG 封面保留原位，不追溯改名或转换。

