#!/usr/bin/env python3
"""从腾讯会议拉取某一期的逐字稿（文字转写），保存为仓库里的 transcript.txt。

用法：

    # 用会议时间自动推出目录 events/{year}/{YYYYMMDD}-ep{NN}/transcript.txt
    python3 scripts/pull-transcript.py --date 2026-09-26 --episode 39

    # 指定 event 目录
    python3 scripts/pull-transcript.py --date 2026-09-26 \
        --event events/2026/20260926-ep39

    # 直接指定会议 ID
    python3 scripts/pull-transcript.py --meeting-id 13319006708380765410 --out /tmp/t.txt

目录日期取腾讯会议返回的会议时间戳日期（UTC），例如 2026-09-26T00:00:00Z → 20260926。

依赖：腾讯会议官方 CLI `tmeet`（@tencentcloud/tmeet）。
首次使用需先授权：`tmeet auth login`（凭据保存在 ~/.tmeet，不进仓库）。
CLI 位置可用环境变量 TMEET_BIN 覆盖，否则从 PATH 查找。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

TIME_FMT_HINT = "ISO 8601，例如 2026-09-26T00:00:00Z"


def tmeet_bin():
    return os.environ.get("TMEET_BIN") or shutil.which("tmeet") or "/data/.npm-global/bin/tmeet"


def run(*args, fatal=True):
    """调用 tmeet，返回解析后的 JSON；fatal=False 时失败返回 None。"""
    cmd = [tmeet_bin(), *args, "--format", "json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        if fatal:
            sys.exit(f"tmeet 调用失败: {' '.join(args)}\n{proc.stderr.strip()[:500]}")
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        if fatal:
            sys.exit(f"tmeet 输出无法解析: {proc.stdout[:300]}")
        return None


def find_meeting_by_date(date):
    """按日期查找已结束会议。date 是腾讯会议返回时间戳所在的日期（UTC）。"""
    d = run("meeting", "list-ended", "--start", f"{date}T00:00:00Z",
            "--end", f"{date}T23:59:59Z")
    items = (d or {}).get("data", {}).get("meeting_info_list", [])
    if not items:
        sys.exit(f"{date} 没有找到已结束的会议（{TIME_FMT_HINT}）")
    if len(items) > 1:
        print(f"注意：{date} 有 {len(items)} 场会议，使用第一场；如需指定请用 --meeting-id")
    return items[0]


def meeting_datestamp(meeting):
    """取腾讯会议返回的会议时间戳日期（UTC），返回 (year, YYYYMMDD)。"""
    start = meeting.get("start_time")
    if not start:
        d = run("meeting", "get", "--meeting-id", meeting["meeting_id"], fatal=False) or {}
        infos = (d.get("data", {}) or {}).get("meeting_info_list") or []
        start = infos[0].get("start_time") if infos else None
    if not start:
        sys.exit("无法获取会议时间，请改用 --event 或 --out 指定输出路径")
    day = start[:10]
    return day[:4], day.replace("-", "")


def dur_seconds(text):
    try:
        parts = [int(x) for x in str(text).split(":")]
    except ValueError:
        return 0
    while len(parts) < 3:
        parts.insert(0, 0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def transcript_file_ids(meeting):
    """列出该会议所有文字转写文件，按时长从长到短排序。

    一场会议可能有多个转写文件（例如一段几分钟的片段），必须先取最长的，
    否则会命中只含片段的空壳，接口返回 30002「纪要无内容」。
    """
    recs = meeting.get("records") or []
    if not recs:
        d = run("record", "list", "--meeting-id", meeting["meeting_id"], fatal=False) or {}
        data = d.get("data", {})
        recs = data.get("records") or data.get("record_list") or []
    cand = [(r.get("duration", ""), r["record_file_id"])
            for r in recs if "转写" in r.get("type", "")]
    cand.sort(key=lambda x: dur_seconds(x[0]), reverse=True)
    return [fid for _, fid in cand]


def norm_time(text):
    """把 tmeet 的混合时间轴（MM:SS 或 HH:MM:SS）统一成 HH:MM:SS。"""
    try:
        parts = [int(x) for x in str(text).split(":")]
    except ValueError:
        return "00:00:00"
    while len(parts) < 3:
        parts.insert(0, 0)
    return "%02d:%02d:%02d" % tuple(parts[-3:])


def pull_paragraphs(meeting_id, file_id, batch=100):
    """分页拉取全部段落，取不到内容时返回 None。"""
    paragraphs, pid = [], 0
    while True:
        d = run("record", "transcript-get", "--meeting-id", meeting_id,
                "--record-file-id", file_id, "--pid", str(pid), "--limit", str(batch),
                fatal=False)
        if not d or d.get("data", {}).get("code", 0) != 0:
            return None
        data = d.get("data", {})
        chunk = data.get("minutes", {}).get("paragraphs", [])
        if not chunk:
            break
        paragraphs.extend(chunk)
        pid = int(chunk[-1]["pid"]) + 1
        if not data.get("more"):
            break
        if len(paragraphs) > 20000:
            sys.exit("段落数异常（>20000），已停止")
    return paragraphs or None


def to_transcript(paragraphs):
    blocks = []
    for p in paragraphs:
        name = (p.get("speaker") or {}).get("user_name") or "未知"
        text = "".join(w.get("text", "")
                       for s in p.get("sentences", []) for w in s.get("words", [])).strip()
        if text:
            blocks.append(f"{name}({norm_time(p.get('start_time'))}):\n{text}")
    return "\n\n".join(blocks) + "\n"


def ensure_dirs(path):
    """确保目标目录存在；返回本次新建的目录（含年份目录），由浅到深。

    events/{year} 不存在时，会在写入前先创建年份目录。
    """
    p = os.path.abspath(path)
    missing, cur = [], p
    while cur and not os.path.isdir(cur):
        missing.append(cur)
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    os.makedirs(p, exist_ok=True)
    return list(reversed(missing))


def main():
    ap = argparse.ArgumentParser(description="拉取腾讯会议逐字稿到 transcript.txt")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--date", help="会议日期 YYYY-MM-DD（腾讯会议时间戳所在日期，UTC）")
    src.add_argument("--meeting-id", help="腾讯会议 meeting_id")
    ap.add_argument("--event", help="event 目录，写入 <event>/transcript.txt")
    ap.add_argument("--episode", help="期号（如 39 或 ep39），用会议时间自动生成 event 目录")
    ap.add_argument("--repo-root", help="仓库根目录，默认取脚本上级目录")
    ap.add_argument("--out", help="输出文件路径")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的 transcript.txt")
    a = ap.parse_args()

    if a.meeting_id:
        if a.episode:
            sys.exit("--episode 需要配合 --date 使用：周期会议的 meeting-id 相同，"
                     "meeting-id 无法区分是哪一期；请用 --date 或直接给 --event")
        meeting = {"meeting_id": a.meeting_id, "subject": "(按 meeting-id)"}
    else:
        meeting = find_meeting_by_date(a.date)

    print(f"会议: {meeting.get('subject', '?')} id={meeting['meeting_id']}")

    if a.out:
        out = a.out
    elif a.event:
        out = os.path.join(a.event, "transcript.txt")
    elif a.episode:
        year, ymd = meeting_datestamp(meeting)
        ep = a.episode.lower().removeprefix("ep")
        root = a.repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = os.path.join(root, "events", year, f"{ymd}-ep{ep}", "transcript.txt")
        print(f"按会议时间戳生成目录: {os.path.dirname(out)}")
    else:
        sys.exit("需要 --out、--event 或 --episode 之一")

    if os.path.exists(out) and not a.force:
        sys.exit(f"已存在 {out}，未覆盖（如需覆盖加 --force）")
    files = transcript_file_ids(meeting)
    if not files:
        sys.exit("未找到文字转写文件（该会议可能没有开启转写）")

    paragraphs = None
    for fid in files:
        paragraphs = pull_paragraphs(meeting["meeting_id"], fid)
        if paragraphs:
            print(f"使用转写文件 id={fid}，共 {len(paragraphs)} 段")
            break
        print(f"转写文件 id={fid} 无内容，尝试下一个")
    if not paragraphs:
        sys.exit("所有转写文件都取不到内容")

    text = to_transcript(paragraphs)
    outdir = os.path.dirname(os.path.abspath(out))
    for d in ensure_dirs(outdir):
        print(f"已创建目录 {d}")
    with open(out, "w") as f:
        f.write(text)
    n = text.count("\n\n") + 1
    print(f"已写入 {out}（{len(text)} 字符，约 {n} 个发言块）")


if __name__ == "__main__":
    main()
