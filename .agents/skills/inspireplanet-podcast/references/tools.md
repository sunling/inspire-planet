# 播客本地工具

在仓库根目录执行。`{skill}` 代表 `.agents/skills/inspireplanet-podcast`，`{work}` 代表本期被忽略的本地制作目录。使用已安装 `scripts/requirements.txt` 依赖的 Python 环境，不硬编码本机临时环境路径。按需在 `replays/.venv/` 安装；不上传音频、不用 GitHub Actions 处理私人回放。

剪辑单可直接引用带声音的回放视频，工具读取音轨，不要求先生成独立音频文件；已有音频也支持。以下以与视频切片共用的 MP4 为例。

```bash
python {skill}/scripts/podcast.py inspect 本地回放.mp4
python {skill}/scripts/podcast.py analyze 本地回放.mp4 --output {work}/analysis
python {skill}/scripts/podcast.py render {work}/edit-plan.json --output {work}/export --check
python {skill}/scripts/podcast.py render {work}/edit-plan.json --output {work}/export
```

`analyze` 以 -48 dB、4 秒找低音量候选并完整解码输入，不自动切音。参数是候选起点，不保证其他录音同样适用；背景噪声较重或发言非常轻时另用局部波形／识别核对，不为凑数量强行找删减。原声定位可复用已有本地识别工具；只有需要识别时才读 [clips 的识别运行说明](../../inspireplanet-clips/references/edit-plan.md)。

## 剪辑单

以下为格式示例，不对应真实期次：

```json
{
  "source": "../source.mp4",
  "cuts": [
    {
      "start": 0,
      "end": 12.5,
      "reason": "开场等待",
      "evidence": "实际媒体局部识别、波形与原声核对"
    },
    {
      "start": 46.2,
      "end": 49.8,
      "reason": "已确认长空白，前后保留自然停顿",
      "evidence": "低音量候选经局部原声核对"
    }
  ],
  "chapters": [
    {"source_seconds": 12.5, "title": "现场开场"},
    {"source_seconds": 60, "title": "第一个话题"}
  ]
}
```

- `source` 相对于剪辑单解析。`cuts` 按时间递增、不重叠，范围须在真实媒体内，每处都须有理由与真实依据；不能把未做的听审写进依据。
- 时间使用有限数字；不允许删完整集。`cuts: []` 可导出不删内容的响度处理版。
- `chapters` 使用实际源音频时间，严格递增且落在保留范围。脚本将其换算成成品时间，落在删减范围的章节会报错，不悄悄移到邻近内容。
- `--check` 校验素材、路径、剪辑及章节，不导出。输出目录必须被本仓库 Git 忽略，且不能包含源文件或剪辑单，避免误覆盖输入。

## 渲染与复查

逐段读取原始媒体，接缝约 8 毫秒淡入淡出以减少点击声；不默认交叉淡化、混合发言、降噪或更改语速。中间 PCM 仅暂存于私有输出目录，完成后清理。

单声道目标 -19 LUFS，双声道目标 -16 LUFS；多声道素材先降为双声道。编码前峰值目标 -2 dBTP，给 AAC 编码留余量。导出 AAC/M4A 后再完整解码与测量：响度偏离目标超过 1 LU 或真峰值高于 -1 dBTP 会拒绝替换已有导出，需根据日志调整。默认导出 128 kbps；文件大小随时长变化。

报告记录源时长、成品时长、删减量、响度和解码结果。`human_listening_reviewed` 与 `release_approved` 默认 `false`，工具不自动代替用户审片与公开授权。即使通过技术检查，仍需检查句首句尾、每处接缝、不同分享者的听感及隐私范围。

脚本会更新同一导出目录中的固定生成文件；源文件、剪辑单和符号链接不会被覆盖。导出前保留想比较的旧版本。

## 工具维护验证

```bash
python -m unittest discover -s .agents/skills/inspireplanet-podcast/scripts -p 'test_podcast.py' -v
python3 scripts/check-content.py
```

测试只在被忽略的 `replays/.tests/` 内生成合成素材，验证章节换算、越界／重叠／无效时间拦截、源文件保护及真实音频导出，不读取会议私密内容。
