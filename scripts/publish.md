# 按需云端渲染（不归档成品图片）

**原则：只保存可编辑的源内容。** Git 仓库保存转写、文章、图文脚本、结构化 JSON、封面配置及必要的授权原始素材；渲染生成的 JPEG、HTML 预览与 ZIP 不提交 Git，也不维护永久的仓库外 ready/history。

## 浏览器一键出图

1. 在 GitHub 打开 **Actions → Render content (temporary download) → Run workflow**。
2. **Use workflow from** 选择包含已审稿件和配置的分支；填写 `episode`，例如 `20260919-ep37`（只填文件夹名）。
3. 选择 `channel`：`gzh` 公众号封面、`xhs` 小红书、`sph` 视频号，或 `all` 渲染当前存在的渠道稿。
4. 运行成功后，在该次 Workflow Run 的 **Artifacts** 下载 `render-...` ZIP。解压后只含 `ready/` JPEG 和 `preview.html`；Artifact 下载文件本身已是 ZIP，不再额外嵌套 `gzh.zip`、`xhs.zip`、`sph.zip` 或 `all.zip`。
5. 下载解压后在浏览器打开 `preview.html` 检查版式、溢出、署名、分镜与隐私；人工确认后从 `ready/` 取图发布。

Artifact **仅保留 1 天**，过期后重新运行即可。工作流的 `contents: read` 权限不允许回写仓库；无仓库写入步骤、无长期云端图片存储。没有确认授权的内容不得直接公开发布。

## 本地调试（可选）

CI 调用原有渲染器，指定 runner 的临时目录：

```bash
python3 scripts/render-publish.py events/2026/20260919-ep37 \
  --channel gzh --root /tmp/inspire-planet-publish
```

本地调试若不指定 `--root`，历史兼容行为仍会在仓库旁生成持久目录；需要使用临时路径并在取图后自行清理。CI 不使用该默认路径。

原渲染器继续检查 JPEG 尺寸、文件完整性、图卡页码连续性与页面溢出。公众号封面配置的 `asset` 仅用于定义输出文件名；不代表该 JPEG 要入库。原图或固定二维码若需作为生成输入，应单独核对授权，不与生成成品混淆。

## 维护与安全

- 手动触发的 `workflow_dispatch` 仅对具有适当仓库操作权限的协作者开放。普通贡献者提交 PR、由维护者审稿后触发。
- 工作流固定 `contents: read`，不注入发布平台密钥，也不直接发布。不要使用带敏感凭据的高权限工作流来运行未经信任的 PR 代码。
- 文字或视觉配置修改后，必须重新审核再运行。Artifact 是临时交付物，不是已发布内容的备份；平台发布后的历史由平台本身管理。
- CI 所需依赖为 Playwright、Chromium、Pillow 和公开发布的中文字体。若字体下载地址改变，工作流会失败，需修复依赖后再运行。

