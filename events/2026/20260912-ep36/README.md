# EP36｜2026-09-12

从下班后的紧绷，到书中不易被看见的劳动生活：从各自具体的经验出发，慢慢理解自己与他人。

通用步骤与 prompt 见 [内容制作说明](../../../docs/content-workflow.md)。

## 稿件导航

| 分享者／选题 | 公众号 | 小红书 | 视频号 |
|---|---|---|---|
| 李影：下班后如何真正休息 | [文章](gzh-liying.md) | [图文脚本](xhs-liying.md) | [图文脚本](sph-liying.md) |
| 抹茶：《我比世界晚熟》与阅读 | [文章](gzh-matcha.md) | [图文脚本](xhs-matcha.md) | [图文脚本](sph-matcha.md) |

来源：[转写](transcript.txt)。纪要：[JSON](summary.json)。金句：[JSON](quote-cards.json)。公众号封面：[配置](assets/cover-configs.md)。

## 本期命令

确认对应稿件、封面和图文脚本后，在仓库根目录按渠道分别执行：

```bash
python3 scripts/render-publish.py events/2026/20260912-ep36 --channel gzh
python3 scripts/render-publish.py events/2026/20260912-ep36 --channel xhs --slug liying
python3 scripts/render-publish.py events/2026/20260912-ep36 --channel xhs --slug matcha
python3 scripts/render-publish.py events/2026/20260912-ep36 --channel sph --slug liying
python3 scripts/render-publish.py events/2026/20260912-ep36 --channel sph --slug matcha
```

云端入口与下载说明：[渲染与交付说明](../../../docs/rendering.md)。生成 JPG、预览及 ZIP 不入库；临时 Artifact 保留 1 天。

## 发布备注

- 两位分享者的第一人称文章、署名及社交平台图卡，均须对应本人审阅确认后才能公开。没有授权时应先匿名化，不可默认转载或合并到公开网站数据。
- 抹茶文章涉及胡安焉《我比世界晚熟》的内容为会议中的读书转述，正式发布前请与原书核对事实，避免把书中摘录误当作本人经历；涉及 tao 等参与者的真实经历也需核对匿名与公开边界。
- 会议中提及工作场景、家庭、收入与健康相关的具体细节，发布时应再次检查可识别信息；引用参与者现场言论前需获得授权。
- 公众号封面短句、视觉命题以及小红书和视频号各自的每页文字、主题需分别确认；两个平台不可复用同一套成品图。
- 本期日期沿用既有目录 `20260912-ep36`，不凭转写中的时区口述更改期次日期。
