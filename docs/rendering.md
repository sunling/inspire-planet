# 渲染与协作指南

本项目采用 **源内容入库、图片按需渲染**：长期保留转写、公众号文章、图文脚本、结构化 JSON、封面配置以及必要的授权原始素材；**不提交生成的 JPG、HTML 预览或 ZIP**。

## GitHub 网页一键渲染（协作者）

无需 VS Code 或本地 Python 环境。具备仓库 Actions 运行权限的成员可以：

1. 打开 [Render content (temporary download)](https://github.com/sunling/inspire-planet/actions/workflows/render-content.yml)，选择 **Run workflow**。
2. 在 **Use workflow from** 中选择已经审阅、包含内容与配置的分支。
3. 输入 **episode**，例如 `20260919-ep37`（目前工作流只读取 `events/2026/`）；选择 **channel**：
   - `gzh`：公众号所有封面（读取 `assets/cover-configs.md`）
   - `xhs`：该期所有 `xhs-*.md` 图卡
   - `sph`：该期所有 `sph-*.md` 图卡
   - `all`：只渲染该期**存在的**渠道材料；全部缺失时会提示 `No renderable content`
4. 运行成功后打开该次运行，在 **Artifacts** 下载 `render-...`，下载文件本身就是 ZIP。
5. 解压后，在浏览器中打开 `preview.html` 检查版式；从 `ready/` 中取 JPG 发布。

下载结构（依据所选渠道，缺失渠道不会生成目录）：

```text
ready/
  gzh/                # 公众号封面 JPG
  xhs/{slug}/         # 小红书图卡（01.jpg、02.jpg…）
  sph/{slug}/         # 视频号图卡
preview.html          # 本地浏览器可打开的图片总览
```

Artifact 只保留 **1 天**，需要时重新运行即可。云端工作流采用只读权限，不会提交图片回仓库，也不会自动发布。

> 渲染成功不等于可公开发布：稿件、署名、涉及其他人的信息与公开范围仍需要当事人确认。

## Clone 后本地手动渲染（维护者）

适合修改 CSS、模板和图文内容时快速反复检查；与云端工作流共用同一套渲染器。下面命令均从仓库根目录执行。

### 1. 首次安装

```bash
python3 -m pip install -r scripts/text-cards/requirements.txt
python3 -m playwright install chromium
```

公众号封面还需要 **霞鹜文楷** `LXGWWenKai-Regular.ttf`，本地可放在 `~/Library/Fonts/` 或 `~/.cache/inspireplanet-fonts/`，也可以通过 `--font` 明确指定。字体未安装时，直接渲染公众号封面会报错；图卡工具本身支持首次自动下载所需字体。

### 2. 按渠道渲染

以下以 EP37 为例，指定系统临时目录作为 `--root`，避免将结果放进 Git 仓库。**本地运行结束后可手动清理**：

```bash
# 公众号封面（字体文件路径按你的电脑调整）
python3 scripts/render-publish.py events/2026/20260919-ep37 \
  --channel gzh --root /tmp/inspire-planet-publish \
  --font ~/Library/Fonts/LXGWWenKai-Regular.ttf

# 小红书
python3 scripts/render-publish.py events/2026/20260919-ep37 \
  --channel xhs --root /tmp/inspire-planet-publish

# 视频号
python3 scripts/render-publish.py events/2026/20260919-ep37 \
  --channel sph --root /tmp/inspire-planet-publish
```

该 CLI 支持多个 `--channel`，若各渠道材料**都已存在**，可以一次运行：

```bash
python3 scripts/render-publish.py events/2026/20261010-ep40 \
  --channel gzh --channel xhs --channel sph \
  --root /tmp/inspire-planet-publish \
  --font ~/Library/Fonts/LXGWWenKai-Regular.ttf
```

**注意：本地 CLI 不会像云端 `all` 一样自动跳过缺失渠道。** 只传本期实际存在的渠道。其现有打包实现仍会在本地输出 `ready/`、`preview.html`、按渠道 ZIP、`all.zip`，在同一 `--root` 重跑时还可能生成 `history/`；它们都是临时文件，不要提交。云端 Artifact 只上传 `ready/` 与 `preview.html`，不上传重复 ZIP。

本地输出示例：

```text
/tmp/inspire-planet-publish/20260919-ep37/
  ready/gzh/
  preview.html
  gzh.zip
  all.zip
```

### 3. 单独调试设计

调整单个封面模板或图卡时，可以绕开整体发布包，仅调用原始渲染器：

```bash
# 全部公众号封面：必须指定仓库外输出目录
python3 scripts/covers/render.py \
  events/2026/20260919-ep37/assets/cover-configs.md \
  --out-dir /tmp/ep37-covers \
  --font ~/Library/Fonts/LXGWWenKai-Regular.ttf

# 单篇小红书图卡：输出目录应为空
python3 scripts/text-cards/render.py \
  events/2026/20261010-ep40/xhs-liying.md \
  /tmp/ep40-xhs-liying --jpeg
```

修改稿件、字号、主题或设计后，重新渲染，检查文字溢出、遮挡、分页、署名、照片授权与实际浏览器效果。

### 测试与排错

```bash
python3 scripts/check-content.py
python3 scripts/test-render-publish.py
```

如果报缺字体，检查 `--font` 路径；如果报 `No renderable content`，确认期数目录和该渠道的脚本或封面配置是否存在。脚本细节见 [发布与存储规则](rendering.md#发布与存储规则)、[公众号封面渲染器](../scripts/covers/README.md)、[图卡渲染器](../scripts/text-cards/README.md)。

## 发布与存储规则

**源稿为长期资产，生成图为临时输出。** Git 仓库只保存转写、文章、脚本、JSON、封面配置和必要的授权原始素材；不提交生成的 JPG、预览 HTML、ZIP，也不维护永久 `ready/` 或 `history/` 存档。公众号配置的 `asset` 字段仅是输出文件名。

GitHub Actions 使用只读 `contents: read` 权限、不注入社交平台发布密钥。运行成功后 Artifact 中只有 `ready/` 与 `preview.html`，下载文件本身是 ZIP，**保留 1 天**。过期重新运行即可；旧图不会自动归档。所有平台均需人工检查版式和获取当事人明确的公开授权，不会因渲染成功而自动发布。

本地原有 `render-publish.py` 在重复使用同一个 `--root` 时可能保留旧版到 `history/` 并生成内部 ZIP；这是兼容逻辑，并非长期存储要求。建议将 `--root` 指向仓库外临时目录，完成检查或取图后自行删除。本地运行时不传 `--root` 会使用仓库外默认固定目录。

原始照片、二维码等作为渲染输入的素材与生成的图片不同；它们是否可入库应单独核对许可与隐私。公开渠道的发布日期、链接、署名和授权边界写在单期 README 的发布备注中。
