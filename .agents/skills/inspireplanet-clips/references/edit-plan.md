# 剪辑单与本地工具

本文仅在检查素材、对齐或渲染时读取。所有命令在仓库根目录执行，`{skill}` 表示 `.agents/skills/inspireplanet-clips`。不要求把大文件移入 Git 跟踪目录。

## 运行环境

使用已有可用 Python 环境；需要时在被忽略的 `replays/.venv/` 下建立环境，安装 `scripts/requirements.txt`。对齐工具的 `transcribe` 子命令另需 `faster-whisper>=1.2,<2`。下载工具、模型遵循运行环境权限，不上传会议音视频。

渲染默认尝试系统中文字体，也可在剪辑单中提供可用字体路径。FFmpeg 必须支持 `ass`、`overlay`、`loudnorm`；随 imageio-ffmpeg 提供的本地二进制可以用于 EP41 同类素材。字体缺失时提供实际可用的中文字体，不静默用缺字方块出片。

## 素材检查与对齐

```bash
python {skill}/scripts/align.py inspect replays/20261017-ep41.mp4
python {skill}/scripts/align.py inspect replays/20261017-ep41.mp4 --frame 1400 --output replays/20261017-ep41-clips/inspect
python {skill}/scripts/align.py transcribe replays/20261017-ep41.mp4 --start 1380 --duration 90 --output replays/20261017-ep41-clips/align-sunling --model small
```

时间参数全部是实际媒体秒数。模型下载目录默认 `replays/.models/`；可指定 `--model-dir`。工具只向模型仓库请求模型，不发送素材。模型未缓存且不允许联网时使用 `--offline`，缺模型则报告缺失，不切换到远程转写。已存在识别结果时先检查并复用，不重复下载或识别。

已有本地模型时，也可将 `--model` 设为该模型目录的实际路径，配合 `--offline` 复用，不需要重新下载。

识别使用局部窗口，不加人名提示，不把前一段识别文本作为后一段的条件，避免静音与停顿处复述提示词。原始 ASR 保留为 `words.json`，包含每句及每个词在源媒体中的实际时间；还需对照转写和原声。工具不会自动把它们标记为已人工听审的字幕。

## edit-plan.json

剪辑单放在本地制作目录，渲染输出到同目录。`source` 和自定义字体路径相对于剪辑单解析。下面是结构示例，须替换为检查得到的真实媒体时间、裁切区域与文案；它不是任何真实会议的已确认切点。

```json
{
  "version": 1,
  "source": "../20261017-ep41.mp4",
  "event": {"year": 2026, "episode": 41, "date": "2026-10-17"},
  "brand": {"website": "inspireplanet.cc"},
  "clips": [
    {
      "slug": "speaker-story",
      "speaker": "分享者",
      "confirmed": false,
      "title": ["具体的情境", "真实的转折"],
      "label": "故事的一句话提示",
      "cover_text": "与原声一致的一句表达",
      "cover_time": 120.5,
      "spans": [[120.5, 130.0], [132.0, 140.0]],
      "crop": [0, 0, 1280, 720],
      "video_box": [60, 610, 960, 540],
      "captions": [[120.7, 123.0, "一句实际原声\n可分两行"]]
    }
  ]
}
```

- `event`、`brand` 来自真实期次与已确认运营信息；可在 `brand` 中记录实际 `join_url` 与 `episode_url`，供撰写文案使用，渲染器只显示 `website`。
- 每条 `slug` 用英文小写、数字和连字符，且不重复。标题最多两行，太长会拒绝渲染，改写后再做。
- `spans` 是按原始顺序保留的源媒体范围，不是转写时间。必须非空、递增、不重叠；删减依据写到该条私人稿件。
- `captions` 使用源媒体秒数。渲染器将其映射到剪辑后的时间，生成对应 SRT 和 ASS；跨越删减点的字幕应在源稿中拆开，不让同一条字幕隐含删去的发言。
- 有视频时 `crop` 为 `[x, y, width, height]`，单位是原始画面像素；不填或设 `null` 表示使用全画面。`video_box` 为竖版中的位置和尺寸，不要侵占标题、署名与字幕。不同剪辑段画面布局不同，需要拆成不同条目或调整渲染实现，不能假装固定裁切能追踪人像。
- 只有音频时将 `crop` 设为 `null`，渲染器在画面区显示文字标题与“原声分享”，不生成假人像。也可提供 `still` 本地授权图片（相对剪辑单路径）。原始人像视频不默认被静态封面替代。
- `cover_time` 是保留区间内的源媒体秒数，和 `cover_text` 一样仅用于按需导出的独立封面。默认使用视频首帧，不要求填写这两个字段。
- 可选 `style.font` 和 `style.regular_font` 为中文字体路径；默认优先 macOS 黑体，Linux 尝试 Noto CJK、文泉驿。保持原风格时沿用现有字体，不因环境路径不同擅自更换设计。

## 渲染与复用

```bash
python {skill}/scripts/render.py replays/20261017-ep41-clips/edit-plan.json --check
python {skill}/scripts/render.py replays/20261017-ep41-clips/edit-plan.json --slug speaker-story
```

`--check` 只检查计划和源媒体，不出片。执行渲染时要求所选条目 `confirmed: true`；这个字段仅记录用户已选片段，不能代替会话中的真实确认。默认选择全部条目，也可指定单条。修改主题、官网等画面设置后用同一剪辑单重渲染，不重复选段。

每条默认生成 `{slug}-draft.mp4`、`{slug}.srt`、`{slug}.ass`、`{slug}-preview.jpg`。仅明确需要独立封面时加 `--cover`，额外生成 `{slug}-cover.jpg`，临时模板、日志和导出检查结果在 `work/`。输出强制留在被 Git 忽略的 `replays/` 内，防止误提交；不会覆盖源回放、剪辑单、字体或授权图片。已有的同名生成文件会重写；未加 `--cover` 时不会生成、重写或自动删除已有封面。检查预览供内部 QA 使用，不当作独立封面交付。

渲染后全片解码并输出尺寸、实际时长与轨道检查记录。程序成功不等于完成视觉检查、听审或得到公开授权。需要用户审阅的事项放到 `clip-{slug}.md`，与两平台文案一起维护。

## 维护验证

修改工具后，用合成媒体验证时间映射、素材保护、未确认选段拦截、视频与纯音频导出：

```bash
python -m unittest discover -s .agents/skills/inspireplanet-clips/scripts -p 'test_render.py' -v
python3 scripts/check-content.py
```

测试使用本地 `replays/.tests/` 的临时目录，不会写入真实会议源文件或上传素材。
