# 出图与协作指南

旧图文 skills 已退役，本页仅保留历史工具操作说明；新内容使用 [原声短视频流程](content-workflow.md)。

本指南用于小红书／视频号文字图卡。仓库长期保存文章、脚本、JSON 与必要的授权原始素材；不提交生成图片、预览 HTML 或 ZIP。

## 图卡：GitHub 网页一键渲染

具备仓库 Actions 权限的成员可以：

1. 打开 [Render content (temporary download)](https://github.com/sunling/inspire-planet/actions/workflows/render-content.yml)，点击 **Run workflow**。
2. 在 **Use workflow from** 选择已审阅、包含最新脚本的分支。
3. 输入 **episode**，例如 `20261017-ep41`（当前工作流读取 `events/2026/`），选择 **channel**：
   - `xhs`：本期所有小红书图卡；
   - `sph`：本期所有视频号图卡；
   - `all`：以上两平台中实际存在的脚本；没有可用脚本时提示 `No renderable content`。
4. 运行成功后，在 **Artifacts** 下载 `render-...`；下载文件本身是 ZIP。
5. 解压并打开 `preview.html` 检查，从 `ready/` 取图发布。

```text
ready/
  xhs/{slug}/         # 小红书 01.jpg、02.jpg…
  sph/{slug}/         # 视频号 01.jpg、02.jpg…
preview.html
```

Artifact 保留 1 天，到期可重新渲染。工作流使用只读权限，不回写图片，不自动发布。

## 本地图卡渲染

从仓库根目录运行：

```bash
python3 -m pip install -r scripts/text-cards/requirements.txt
python3 -m playwright install chromium
python3 scripts/render-publish.py events/2026/20261017-ep41 \
  --channel xhs --channel sph --root /tmp/inspire-planet-publish
# 单篇示例
python3 scripts/render-publish.py events/2026/20261017-ep41 \
  --channel xhs --slug wendy --root /tmp/inspire-planet-publish
```

本地 CLI 只接受 `xhs`、`sph`，需要多平台时重复 `--channel`；只传本期存在脚本的渠道。所需中文字体由图卡工具首次自动下载，离线时用 `--font` 指向本机文件；也可用 `--browser` 指定浏览器。

临时输出在仓库外，包括 `ready/`、预览和平台 ZIP；本地同一目录重跑可能保留 `history/`。它们不入 Git，取图后可清理。历史公众号输出不会混入新的图卡发布包。

### 调试单篇设计

```bash
python3 scripts/text-cards/render.py \
  events/2026/20261017-ep41/xhs-wendy.md \
  /tmp/ep41-xhs-wendy --jpeg
python3 scripts/check-content.py
python3 scripts/test-render-publish.py
```

图卡输出目录须为空。修改文案、字体或 CSS 后检查留白、溢出、遮挡、连续页码、署名、尺寸与预览。脚本与主题细节见 [图卡说明](../scripts/text-cards/README.md)，维护入口见 [设计修改清单](design-editing.md)。

## 发布与保存

源稿可长期维护，生成图片不提交仓库。图卡由临时 Artifact 或本地临时目录交付，不自动发布。

原始照片、二维码与生成图片不同，是否入库要核对许可与隐私。文章、署名、涉及他人的信息及公开范围仍须当事人确认；本期授权与发布链接记录在单期 README。
