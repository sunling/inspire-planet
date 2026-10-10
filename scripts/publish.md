# 固定发布目录

先确认对应稿件与封面配置，再从仓库根目录运行：

```bash
python3 scripts/render-publish.py events/{year}/{YYYYMMDD}-epXX --channel gzh
python3 scripts/render-publish.py events/{year}/{YYYYMMDD}-epXX --channel xhs --channel sph
```

需要更新单篇时：

```bash
python3 scripts/render-publish.py events/{year}/{YYYYMMDD}-epXX --channel xhs --slug liying
```

默认输出在仓库旁的 `inspire-planet-publish/{YYYYMMDD}-epXX/`，始终从这里取待发布版本：

```text
{YYYYMMDD}-epXX/
  ready/
    gzh/               公众号封面
    xhs/{slug}/        小红书整套图卡
    sph/{slug}/        视频号整套图卡
  preview.html         当前图片总览
  gzh.zip              当前公众号封面包（有此渠道时）
  xhs.zip              当前小红书图片包（有此渠道时）
  sph.zip              当前视频号图片包（有此渠道时）
  all.zip              全部当前图片
  history/             被替换的旧版本，发布时不从这里取图
```

在临时目录渲染，沿用原渲染器的溢出与重叠检查，再检查图片尺寸和页码连续性、重建预览及 ZIP，全部成功后替换 `ready/`。单篇更新保留其余篇目和平台；失败保留旧版本。更新时不要同时取图或发布，等命令完成后打开固定预览。旧图片与当时的预览、下载包一起存入 `history/`，可以按需手动清理。

`--root <路径>` 可修改仓库外的发布根目录；选定后每次用同一位置。默认目录按仓库位置确定，不使用 `/tmp` 保存长期发布素材。`--font`、`--browser` 传给原渲染器。依赖见 [文字卡说明](text-cards/README.md)，公众号封面需本机霞鹜文楷；其他参数微调应先保存在已审阅的配置或脚本中。

导入已经检查的 JPEG（源目录需包含 `gzh/`、`xhs/{slug}/` 或 `sph/{slug}/`）：

```bash
python3 scripts/render-publish.py events/{year}/{YYYYMMDD}-epXX \
  --channel xhs --channel sph --import-dir <已有成品目录>
```

导入会检查图片完整性、尺寸与图卡页码，文字和排版需事先审阅。来源目录保留不动，导入后发布只认固定入口。公众号入库需要的 JPEG 可从 `ready/gzh/` 复制到本期 `assets/`；图卡、预览、下载包与历史均不提交 GitHub。

每期 README 的制作流程写明固定目录和命令；不记录生成或渲染状态。出图不代表对外发布授权。

验证：`python3 scripts/test-render-publish.py`（需 Pillow）。
