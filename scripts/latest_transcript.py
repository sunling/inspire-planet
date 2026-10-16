#!/usr/bin/env python3
"""Zero-input project discovery; deterministic transcript-only public drafts.

Historical selection is occurrence-based and never uses an episode number as an
input. The user gives their own local calendar date (auto-matched across UTC /
Asia-Shanghai / America-Los_Angeles), or leaves it blank for a bounded read-only
scan that numbers unarchived project occurrences so a later run can pick=N one.
EP numbers are at most a display hint derived from existing directories; they
reset every year and some directory dates are migration artifacts, so fetch
dates come from real Tencent occurrence data only.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from zoneinfo import ZoneInfo
import meeting_content as m

# A user's local calendar day is matched in any of these zones; Tencent has no
# notion of a "local day", so the same occurrence may fall on a different UTC
# date depending on where the user lives. Asia-Shanghai and America/Los_Angeles
# are the two communities this project is run for.
LOCAL_ZONES = ('UTC', 'Asia/Shanghai', 'America/Los_Angeles')

# Bounded read-only scan limits (no bodies, no public writes).
SCAN_LOOKBACK_DAYS = 365
SCAN_WINDOW_DAYS = 90
SCAN_MAX_PROBES = 20


def timestamp(value):
    try:
        if type(value) in (int, float) or (isinstance(value, str) and value.isdigit()):
            return datetime.fromtimestamp(float(value), timezone.utc)
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        m.need(dt.tzinfo is not None, '会议时间缺少时区')
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError, AttributeError):
        raise m.SafeError('会议时间格式不支持') from None


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def discover(client, config, now):
    days = config['lookback_days']
    m.need(type(days) is int and 1 <= days <= 90 and bool(config['title']), '发现配置无效')
    m.need(now.tzinfo is not None, '发现时间必须有时区')
    start = now - timedelta(days=days)
    rows = m.token_pages(client, 'get_user_ended_meetings',
                         {'start_time': iso(start), 'end_time': iso(now)}, 'meeting_info_list')
    selected = [r for r in rows if r.get('subject') == config['title']
                and start <= timestamp(r.get('start_time')) <= now]
    return sorted(selected, key=lambda r: timestamp(r['start_time']))


def local_window(day, zone='Asia/Shanghai'):
    """UTC bounds of one calendar date in the explicitly selected time zone."""
    m.need(zone in LOCAL_ZONES, '不支持的会议时区')
    try:
        d = datetime.strptime(day, '%Y-%m-%d').date()
    except ValueError:
        raise m.SafeError('日期无效') from None
    nxt = d + timedelta(days=1)
    tz = ZoneInfo(zone)
    return (datetime(d.year, d.month, d.day, tzinfo=tz).astimezone(timezone.utc),
            datetime(nxt.year, nxt.month, nxt.day, tzinfo=tz).astimezone(timezone.utc))


def historical_local(client, config, day, zone='Asia/Shanghai'):
    """Match only the requested zone's calendar date; fail on zero or multiple."""
    m.need(isinstance(config.get('title'), str) and bool(config['title'].strip()), '项目标题未配置')
    start, end = local_window(day, zone)
    d = datetime.strptime(day, '%Y-%m-%d').date()
    rows = m.token_pages(client, 'get_user_ended_meetings',
                        {'start_time': iso(start), 'end_time': iso(end)}, 'meeting_info_list')
    tz = ZoneInfo(zone)
    matches = [r for r in rows if r.get('subject') == config['title']
               and timestamp(r.get('start_time')).astimezone(tz).date() == d]
    m.need(len(matches) == 1, '所选时区的当天必须唯一命中一场项目会议；同日多场或没有则停止')
    return matches[0]


def episode_mapping(root):
    """Repo (year, EP) -> UTC date from committed events/ directories.

    Episode numbers RESET every year (2025 ep02..ep50, 2026 ep01..ep40), so an
    EP number alone is ambiguous across years and must be year-qualified.
    """
    mapping = {}
    base = root / 'events'
    if not base.is_dir():
        return mapping
    for year_dir in sorted(base.iterdir()):
        if not year_dir.is_dir() or not re.fullmatch(r'\d{4}', year_dir.name):
            continue
        for event in sorted(year_dir.iterdir()):
            match = re.fullmatch(r'(\d{8})-ep(\d{2,3})', event.name)
            if not match or not event.is_dir():
                continue
            stamp = match.group(1)
            if stamp[:4] != year_dir.name:
                continue
            day = stamp[:4] + '-' + stamp[4:6] + '-' + stamp[6:]
            mapping[(int(year_dir.name), str(int(match.group(2))))] = day
    return mapping


def episode_hints(root):
    """Display-only EP hint per UTC date, from unambiguous events/ directories.

    Episode numbers are a repository naming convention that resets every year,
    and several directory dates are legacy migration artifacts (many episodes
    share one date), so a hint is shown only when a date maps to exactly one
    episode directory. Hints never select or resolve a fetch date: dates come
    from Tencent occurrence data only.
    """
    by_date = {}
    for (year, ep), day in episode_mapping(root).items():
        by_date.setdefault(day, set()).add((year, ep))
    return {day: f'{year}-ep{int(ep):02d}'
            for day, keys in by_date.items() if len(keys) == 1
            for year, ep in keys}


WEEKDAYS = ('周一', '周二', '周三', '周四', '周五', '周六', '周日')


def weekday(day):
    return WEEKDAYS[datetime.strptime(day, '%Y-%m-%d').weekday()]


def instance(row):
    meeting, sub = row.get('meeting_id'), row.get('sub_meeting_id')
    m.need(isinstance(meeting, str) and bool(meeting) and isinstance(sub, str) and bool(sub), '会议实例身份缺失')
    start = iso(timestamp(row.get('start_time')))
    key = hashlib.sha256(json.dumps([meeting, sub, start], separators=(',', ':')).encode()).hexdigest()
    return {'instance_key': key, 'meeting_id': meeting, 'sub_meeting_id': sub,
            'start_time': start, 'date': m.utc_day(start)}


def archives(run):
    """Read main and every open PR head, without checking out untrusted code."""
    run(['git', 'fetch', '--no-tags', 'origin', '+refs/heads/main:refs/remotes/origin/main'])
    pages = json.loads(run(['gh', 'api', '--paginate', '--slurp',
                           'repos/{owner}/{repo}/pulls?state=open&per_page=100']))
    refs = ['origin/main']
    for page in pages:
        m.need(isinstance(page, list), '开放 PR 列表结构不支持')
        for pr in page:
            sha = pr.get('head', {}).get('sha', '')
            m.need(bool(re.fullmatch('[0-9a-f]{40}', sha)), 'PR SHA 无效')
            run(['git', 'fetch', '--no-tags', 'origin', sha])
            refs.append(sha)
    result = {'keys': set(), 'dates': set(), 'mapping': {}}
    for ref in refs:
        paths = run(['git', 'ls-tree', '-r', '--name-only', ref]).splitlines()
        for path in paths:
            match = re.fullmatch(r'events/(\d{4})/(\d{8})-ep(\d{2,3})/.+', path)
            if match:
                stamp = match[2]
                day = stamp[:4] + '-' + stamp[4:6] + '-' + stamp[6:]
                if path.endswith('/transcript.txt'):
                    result['dates'].add(day)
                result['mapping'].setdefault(day, set()).add(str(int(match[3])))
            if re.fullmatch(r'(?:incoming/meetings/[0-9a-f]{64}|events/\d{4}/\d{8}-ep\d{2,3})/metadata.json', path):
                data = json.loads(run(['git', 'show', ref + ':' + path]))
                m.need(instance(data) == {k: data.get(k) for k in instance(data)}, '归档实例身份无效')
                if path.startswith('incoming/'):
                    m.need(path.split('/')[2] == data['instance_key'], '暂存身份与路径不一致')
                result['keys'].add(data['instance_key'])
                result['dates'].add(data['date'])
    return result


def episode_for(latest, rows, config):
    anchor = config['anchor']
    day = m.utc_day(latest['start_time'])
    # Only this user-verified date mapping is trusted; legacy directory maxima
    # and elapsed weeks never establish an episode number.
    if day == anchor['date'] and latest['meeting_id'] == anchor['meeting_id']:
        return anchor['episode'] if sum(m.utc_day(r['start_time']) == day for r in rows) == 1 else None
    anchors = [r for r in rows if m.utc_day(r['start_time']) == anchor['date']
               and r['meeting_id'] == anchor['meeting_id']]
    if len(anchors) != 1:
        return None
    following = [r for r in rows if timestamp(r['start_time']) > timestamp(anchors[0]['start_time'])]
    if (len(following) == 1 and instance(following[0]) == instance(latest)
            and latest['meeting_id'] == anchor['meeting_id'] and day[:4] == anchor['date'][:4]
            and timestamp(latest['start_time']) - timestamp(anchors[0]['start_time']) == timedelta(days=7)):
        return str(int(anchor['episode']) + 1)
    return None


def plan_latest(rows, archive, config):
    if not rows:
        return {'skip': True, 'reason': 'no-new'}
    latest = max(rows, key=lambda row: (timestamp(row['start_time']), instance(row)['instance_key']))
    metadata = instance(latest)
    if metadata['instance_key'] in archive['keys'] or metadata['date'] in archive['dates']:
        return {'skip': True, 'reason': 'already-archived'}
    return {'skip': False, 'metadata': metadata, 'meeting': latest}


def scan_window(now):
    m.need(now.tzinfo is not None, '扫描时间必须有时区')
    start = now - timedelta(days=SCAN_LOOKBACK_DAYS)
    bounds, cursor = [], start
    while cursor < now:
        end = min(cursor + timedelta(days=SCAN_WINDOW_DAYS), now)
        bounds.append((cursor, end))
        cursor = end
    return start, bounds


def probe_readable(client, row):
    """Whether an occurrence's transcript can be read, without pulling bodies.

    A 转写 record in the occurrence's own list is the same criterion the fetch
    pipeline uses; records[] is known to be unreliable (may be empty even when a
    transcript exists), so a native record listing is consulted as a fallback.
    """
    listed = any('转写' in str(r.get('type', '')) and r.get('record_file_id')
                 for r in (row.get('records') or []))
    if listed:
        return True, 'listed-transcript'
    try:
        groups = m.token_pages(client, 'get_records_list', {'meeting_id': row['meeting_id']}, 'record_meetings')
    except m.SafeError:
        return False, 'record-list-unavailable'
    sub = row.get('sub_meeting_id')
    native = {f.get('record_file_id') for group in groups
              if group.get('meeting_id') == row['meeting_id'] and group.get('sub_meeting_id') == sub
              for f in (group.get('record_files') or [])}
    return False, ('native-recording-no-listed-transcript' if native else 'no-recording')


def enumerate_unarchived(client, config, archive, start, bounds, now):
    """Ordered (oldest first) unarchived project occurrences in the window.

    Occurrence-based selection: dates come from real Tencent data only. Future
    and out-of-window occurrences are excluded, and the same occurrence is never
    returned twice (deduped by instance identity across windows and pages).
    """
    m.need(isinstance(config.get('title'), str) and bool(config['title'].strip()), '项目标题未配置')
    title = config['title']
    found = {}
    for begin, end in bounds:
        rows = m.token_pages(client, 'get_user_ended_meetings',
                             {'start_time': iso(begin), 'end_time': iso(end)}, 'meeting_info_list')
        for row in rows:
            if row.get('subject') != title:
                continue
            if not (start <= timestamp(row.get('start_time')) <= now):
                continue
            meta = instance(row)
            if meta['instance_key'] in archive['keys'] or meta['date'] in archive['dates']:
                continue
            found.setdefault(meta['instance_key'], (meta, row))
    return sorted(found.values(), key=lambda item: (item[0]['date'], item[0]['instance_key']))


def scan(client, config, archive, now, root=None):
    """Bounded read-only scan of unarchived project occurrences.

    Chunks list-ended into <=90-day windows over a capped lookback, excludes
    future/out-of-window occurrences and the same occurrence twice, and prints
    numbered rows (real date, weekday, optional EP display hint) with static
    read-availability reasons. No bodies, tokens, names or other project
    meetings are ever emitted. The numbers let the user re-run with pick=N.
    """
    start, bounds = scan_window(now)
    items = enumerate_unarchived(client, config, archive, start, bounds, now)
    hints = episode_hints(root) if root is not None else {}
    probed = min(len(items), SCAN_MAX_PROBES)
    print(f'scan: lookback_days={SCAN_LOOKBACK_DAYS}; windows={len(bounds)}; unarchived={len(items)}; '
          f'probed={probed}; truncated={str(len(items) > SCAN_MAX_PROBES).lower()}')
    readable = 0
    for index, (meta, row) in enumerate(items):
        label = f'[{index + 1}] {meta["date"]} {weekday(meta["date"])}'
        if hints.get(meta['date']):
            label += f' ep_hint={hints[meta["date"]]}'
        if index >= SCAN_MAX_PROBES:
            print(f'{label} probed=false')
            continue
        ok, reason = probe_readable(client, row)
        if ok:
            readable += 1
        print(f'{label} readable={str(ok).lower()} reason={reason}')
    print(f'scan: readable={readable}; unarchived={len(items)}; probed={probed}')
    print('用 pick=N 选择上面编号的一场（例如 pick=3）；编号只与同一回看窗口和归档状态一致。')
    return {'windows': len(bounds), 'unarchived': len(items), 'probed': probed, 'readable': readable}


def allowed_paths(plan):
    metadata = plan['metadata']
    m.need(instance(metadata) == {k: metadata.get(k) for k in instance(metadata)}, '计划实例身份不一致')
    key = metadata['instance_key']
    m.need(plan['branch'] == 'content/meeting-' + key and plan['date'] == metadata['date'], '计划分支或日期身份不一致')
    event = plan['event']
    if plan['episode'] is None:
        m.need(event == 'incoming/meetings/' + key, '暂存路径身份无效')
        return [event + '/' + name for name in ('transcript.txt', 'metadata.json', 'README.md')]
    m.need(event == m.event_identity(metadata['date'], plan['episode'])[0], '期次路径身份无效')
    return [*m.allowed_paths(event), event + '/metadata.json']


def write(root, plan, text):
    paths = allowed_paths(plan)
    m.parse_transcript(text)
    for relative in paths:
        path = root / relative
        m.need(path.resolve().is_relative_to(root.resolve()) and
               not any(p.is_symlink() for p in [path, *path.parents] if p != root.parent), '写入路径不安全')
        if relative != 'events/README.md':
            m.need(not path.exists(), '已有材料；禁止覆盖')
    if plan['episode'] is not None:
        m.write_draft(root, plan['event'], text)
    else:
        target = root / plan['event']
        target.mkdir(parents=True, exist_ok=True)
        with (target / 'transcript.txt').open('x', encoding='utf-8') as f:
            f.write(text)
        with (target / 'README.md').open('x', encoding='utf-8') as f:
            f.write('# 待确认期次的公开原始转写\n\n- 本目录与 Draft PR 均公开，不是私人暂存。\n'
                    '- 日期和实例已定位；期数未确认，未按周数或最大 EP 猜测。\n'
                    '- 请核对漏期、改期、跨年或多场情况，再确认年份与期数并保留 metadata.json。\n'
                    '- 原稿未经审核；检查参与者授权与隐私。不生成网站 JSON，不自动合并或发布。\n')
    with (root / plan['event'] / 'metadata.json').open('x', encoding='utf-8') as f:
        files = sorted([r['meeting_record_id'], r['record_file_id']] for r in plan.get('meeting', {}).get('records', []))
        json.dump(dict(plan['metadata'], episode=plan['episode'], record_files=files), f, ensure_ascii=False, indent=2)
        f.write('\n')
    return paths


def main(argv=None, root=None, run=None, client_factory=None, now=None):
    import argparse
    import os
    import subprocess
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['readonly', 'scan', 'prepare', 'fetch-check', 'fetch', 'write', 'publish'])
    parser.add_argument('--date', help='会议日期 YYYY-MM-DD；配合 --timezone 精确匹配')
    parser.add_argument('--timezone', choices=LOCAL_ZONES, default='Asia/Shanghai', help='会议日期所属时区（默认北京时间）')
    parser.add_argument('--pick', help='从只读扫描编号中选择一场未归档项目会议（如 3）；仅用于 prepare')
    args = parser.parse_args(argv)
    command = args.command
    date = args.date if args.date else None
    pick = args.pick if args.pick else None
    historical_input = args.date is not None or args.pick is not None
    if historical_input:
        m.need(command in ('prepare', 'fetch-check'), '日期或序号仅用于历史 prepare/fetch-check')
    if date is not None:
        m.need(bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', date)), '日期须为 YYYY-MM-DD')
        m.utc_day(date + 'T00:00:00Z')
    if pick is not None:
        m.need(bool(re.fullmatch(r'[1-9]\d{0,3}', pick)), '序号须为正整数（如 3）')
        m.need(command == 'prepare', '序号仅用于历史 prepare')
    m.need(not (date and pick), '日期与序号只能二选一')
    m.need(not (command == 'scan' and historical_input), '扫描不接受日期或序号')
    m.need(command != 'fetch-check' or date, '历史检查需要本地日期')
    m.need(bool(date or pick) or not historical_input, '历史补录需要本地日期或扫描序号；留空请使用只读扫描')
    root = root or Path(__file__).resolve().parents[1]
    if run is None:
        def run(args):
            try:
                result = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=180)
            except (OSError, subprocess.TimeoutExpired):
                raise m.SafeError('外部命令无法执行（原始输出已隐藏）') from None
            m.need(result.returncode == 0, 'Git/GitHub 命令失败；检查权限（原始输出已隐藏）')
            return result.stdout
    if client_factory is None:
        def client_factory():
            token = os.environ.get('TENCENT_MEETING_TOKEN', '')
            m.need(bool(token), '缺少腾讯会议 Secret')
            return m.MCP(lambda packet: m.send_json(m.MCP_URL, packet,
                {'X-Tencent-Meeting-Token': token, 'X-Skill-Version': m.SKILL_VERSION}))
    state = root / '.git/latest-plan.json'
    cache = root / '.git/latest-transcript.txt'
    m.need((root / '.git').is_dir() and not (root / '.git').is_symlink(), '要求安全 .git 目录')
    m.need(not state.is_symlink() and not cache.is_symlink(), '缓存路径不安全')
    if command == 'fetch-check':
        config = json.loads((root / 'scripts/meeting-project.json').read_text(encoding='utf-8'))
        client = client_factory()
        meeting = historical_local(client, config, date, args.timezone)
        text = m.fetch_occurrence(client, meeting)
        blocks = m.parse_transcript(text)
        check_cache = root / '.git/meeting-content-fetch-check.txt'
        m.need(not check_cache.is_symlink(), '缓存路径不安全')
        check_cache.write_text(text, encoding='utf-8')
        print(f'历史远程完整转写已验证：{len(blocks)} 段；仅 runner 缓存，未写入公开文件。')
        return
    if command == 'scan':
        config = json.loads((root / 'scripts/meeting-project.json').read_text(encoding='utf-8'))
        archive = archives(run)
        scan(client_factory(), config, archive, now or datetime.now(timezone.utc), root=root)
        return
    if command in ('readonly', 'prepare'):
        if command == 'prepare':
            m.need(run(['git', 'branch', '--show-current']).strip() == 'main', '生产必须检出 main')
            m.need(not run(['git', 'status', '--porcelain']).strip(), '生产工作区不干净')
            state.unlink(missing_ok=True)
            cache.unlink(missing_ok=True)
        config = json.loads((root / 'scripts/meeting-project.json').read_text(encoding='utf-8'))
        archive = archives(run)
        if command == 'prepare':
            m.need(run(['git', 'rev-parse', 'HEAD']).strip() == run(['git', 'rev-parse', 'origin/main']).strip(), 'main 已变化；请重新运行')
        moment = now or datetime.now(timezone.utc)
        if date:
            rows = [historical_local(client_factory(), config, date, args.timezone)]
        elif pick:
            start, bounds = scan_window(moment)
            items = enumerate_unarchived(client_factory(), config, archive, start, bounds, moment)
            index = int(pick) - 1
            m.need(0 <= index < len(items), '序号超出当前未归档场次范围；请先运行只读扫描查看编号')
            rows = [items[index][1]]
        else:
            rows = discover(client_factory(), config, moment)
        plan = plan_latest(rows, archive, config)
        if not plan['skip']:
            metadata = plan['metadata']
            if date or pick:
                mapped = archive['mapping'].get(metadata['date'], set())
                mapped_episode = next(iter(mapped)) if len(mapped) == 1 else None
            else:
                mapped_episode = episode_for(plan['meeting'], rows, config)
            event = m.event_identity(metadata['date'], mapped_episode)[0] if mapped_episode else 'incoming/meetings/' + metadata['instance_key']
            plan.update(latest=True, event=event, episode=mapped_episode, date=metadata['date'],
                        branch='content/meeting-' + metadata['instance_key'], base='main',
                        head=run(['git', 'rev-parse', 'HEAD']).strip())
            branches = [plan['branch']]
            if mapped_episode:
                branches.append(m.event_identity(metadata['date'], mapped_episode)[1])
            for branch in branches:
                if run(['git', 'ls-remote', '--heads', 'origin', 'refs/heads/' + branch]).strip():
                    plan.update(skip=True, reason='existing-branch')
        if command == 'prepare':
            state.write_text(json.dumps(plan), encoding='utf-8')
            if os.environ.get('GITHUB_OUTPUT'):
                with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
                    f.write('skip=' + str(plan['skip']).lower() + '\n')
        print('latest discovery: project_matches=' + str(len(rows)) + '; skip=' + str(plan['skip']).lower()
              + '; ' + (plan.get('reason', 'new-occurrence')) + '; 未拉取正文、未写入公开文件。')
        return
    m.need(state.is_file(), '请先执行 prepare')
    plan = json.loads(state.read_text(encoding='utf-8'))
    m.need(not plan['skip'], '已跳过；不得拉取或提交')
    allowed_paths(plan)
    m.need(plan['base'] == 'main' and run(['git', 'branch', '--show-current']).strip() == 'main'
           and run(['git', 'rev-parse', 'HEAD']).strip() == plan['head'], '生产基线改变')
    if command == 'fetch':
        # Recheck main/open drafts immediately before the first transcript read.
        archive = archives(run)
        m.need(not plan_latest([plan['meeting']], archive, {})['skip'], '已归档；停止且不重复拉取')
        m.need(instance(plan['meeting']) == plan['metadata'], '读取实例与计划不一致')
        m.need(not run(['git', 'ls-remote', '--heads', 'origin', 'refs/heads/' + plan['branch']]).strip(), '远端草稿分支已存在；不重复拉取')
        m.need(not (root / plan['event'] / 'transcript.txt').exists(), '已有逐字稿；不重复拉取')
        m.need(not cache.exists(), '已有抓取缓存；禁止重复拉取')
        text = m.fetch_occurrence(client_factory(), plan['meeting'])
        blocks = m.parse_transcript(text)
        with cache.open('x', encoding='utf-8') as f:
            f.write(text)
        print(f'完整转写已验证：{len(blocks)} 段；正文不进入日志。')
    elif command == 'write':
        m.need(cache.is_file(), '请先执行 fetch')
        write(root, plan, cache.read_text(encoding='utf-8'))
        print('公开原始转写与持久实例信息已写入；期次不明时待确认，不生成网站数据。')
    elif command == 'publish':
        m.need(os.environ.get('CONTENT_PUBLISH_ALLOWED') == 'true' and os.environ.get('GITHUB_ACTIONS') == 'true', '仅允许显式授权 Actions 发布')
        run(['python3', 'scripts/check-content.py'])
        run(['gh', 'auth', 'setup-git', '--hostname', 'github.com'])
        m.publish(root, plan, run)
        print('公开 Draft PR 已创建且回读验证；未合并、未发布。')


if __name__ == '__main__':
    try:
        main()
    except m.SafeError as exc:
        print(f'停止：{exc}', file=__import__('sys').stderr)
        raise SystemExit(1) from None
    except Exception:
        print('停止：数据或运行环境不兼容；原始响应已隐藏。', file=__import__('sys').stderr)
        raise SystemExit(1) from None
