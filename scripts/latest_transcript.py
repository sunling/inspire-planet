#!/usr/bin/env python3
"""Zero-input project discovery; deterministic transcript-only public drafts.

Historical backfill accepts either a repository episode number (EP, which only
exists as an events/ directory concept and is resolved to a UTC date through the
committed mapping) or the user's own local calendar date (auto-matched across
UTC / Asia-Shanghai / America-Los_Angeles). A blank historical invocation runs a
bounded read-only scan of unarchived project occurrences.
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


def historical(client, config, day):
    """Exact project occurrence whose UTC day is `day`; unique match required."""
    m.need(isinstance(config.get('title'), str) and bool(config['title'].strip()), '项目标题未配置')
    rows = m.token_pages(client, 'get_user_ended_meetings',
                        {'start_time': day + 'T00:00:00Z', 'end_time': day + 'T23:59:59Z'}, 'meeting_info_list')
    return m.select_meeting(rows, day, config['title'], '')


def local_window(day):
    """UTC window covering local calendar day `day` in every LOCAL_ZONES zone."""
    try:
        d = datetime.strptime(day, '%Y-%m-%d').date()
    except ValueError:
        raise m.SafeError('日期无效') from None
    nxt = d + timedelta(days=1)
    starts, ends = [], []
    for zone in LOCAL_ZONES:
        tz = ZoneInfo(zone)
        starts.append(datetime(d.year, d.month, d.day, tzinfo=tz).astimezone(timezone.utc))
        ends.append(datetime(nxt.year, nxt.month, nxt.day, tzinfo=tz).astimezone(timezone.utc))
    return min(starts), max(ends)


def historical_local(client, config, day):
    """Exact project occurrence starting within local calendar day `day`.

    The user provides their own local date and never needs to know UTC; the
    occurrence is matched in any of LOCAL_ZONES so long as it is unique.
    """
    m.need(isinstance(config.get('title'), str) and bool(config['title'].strip()), '项目标题未配置')
    d = datetime.strptime(day, '%Y-%m-%d').date()
    start, end = local_window(day)
    rows = m.token_pages(client, 'get_user_ended_meetings',
                        {'start_time': iso(start), 'end_time': iso(end)}, 'meeting_info_list')
    zones = [ZoneInfo(z) for z in LOCAL_ZONES]
    matches = [r for r in rows if r.get('subject') == config['title']
               and any(timestamp(r.get('start_time')).astimezone(z).date() == d for z in zones)]
    m.need(len(matches) == 1, '本地日期必须唯一命中一场项目会议；同日多场或没有则停止')
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


def parse_episode(value):
    """Parse '48', 'EP48', '2025-48' or '2025-EP48' into (optional year, EP)."""
    text = value.strip() if isinstance(value, str) else ''
    match = re.fullmatch(r'(?:(\d{4})-)?(?:[Ee][Pp])?(\d{1,3})', text)
    m.need(bool(match), '期数格式须为 48、EP48 或 2025-48（年份可选；期数每年重置）')
    ep = str(int(match.group(2)))
    m.need(bool(re.fullmatch(r'[1-9]\d{0,2}', ep)), '期数须为 1–999')
    return (int(match.group(1)) if match.group(1) else None), ep


def resolve_episode_date(root, episode, year=None):
    """Resolve a repository EP to its unique UTC date, else fail closed.

    Tencent exposes no episode concept: EP is purely a repository convention
    (events/{year}/{YYYYMMDD}-epXX). Numbers reset every year, so a bare EP that
    exists in more than one year is ambiguous and must be qualified (2025-48 or
    a separate year). A year is never chosen silently and another year's mapping
    is never used.
    """
    if year is not None:
        year = year if isinstance(year, str) else str(year)
        m.need(bool(re.fullmatch(r'\d{4}', year)), '年份须为 4 位数字')
        year = int(year)
    embedded, ep = parse_episode(episode)
    m.need(not (embedded is not None and year is not None and embedded != year), '期数与年份输入不一致')
    wanted = year if year is not None else embedded
    mapping = episode_mapping(root)
    years = sorted({y for (y, e) in mapping if e == ep})
    available = '、'.join(str(y) for y in years) if years else '无'
    matches = sorted((y, e) for (y, e) in mapping if e == ep and (wanted is None or y == wanted))
    if not matches:
        if wanted is None:
            raise m.SafeError(f'期数 EP{ep} 在仓库 events 目录中没有匹配的年份；该期数可用年份：{available}')
        raise m.SafeError(f'仓库 events 目录中 {wanted} 年没有 EP{ep}；该期数可用年份：{available}')
    if len(matches) > 1:
        raise m.SafeError(f'期数 EP{ep} 匹配多个年份（{available}）；请用 2025-{ep} 形式指定年份，不会自动选年')
    y, e = matches[0]
    day = mapping[(y, e)]
    same_day = {(yy, ee) for (yy, ee), value_day in mapping.items() if value_day == day}
    m.need(same_day == {(y, e)}, f'日期 {day} 对应多个期次目录，无法唯一定位；请改用本地日期')
    return day, e, y


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


def scan(client, config, archive, now):
    """Bounded read-only scan of unarchived project occurrences.

    Chunks list-ended into <=90-day windows over a capped lookback, excludes
    future/out-of-window occurrences and the same occurrence twice, and prints
    only counts, occurrence dates and static read-availability reasons. No
    bodies, tokens, names or other project meetings are ever emitted.
    """
    m.need(isinstance(config.get('title'), str) and bool(config['title'].strip()), '项目标题未配置')
    title = config['title']
    start, bounds = scan_window(now)
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
    items = sorted(found.values(), key=lambda item: (item[0]['date'], item[0]['instance_key']))
    probed = min(len(items), SCAN_MAX_PROBES)
    print(f'scan: lookback_days={SCAN_LOOKBACK_DAYS}; windows={len(bounds)}; unarchived={len(items)}; '
          f'probed={probed}; truncated={str(len(items) > SCAN_MAX_PROBES).lower()}')
    readable = 0
    for index, (meta, row) in enumerate(items):
        if index >= SCAN_MAX_PROBES:
            print(f'{meta["date"]} probed=false')
            continue
        ok, reason = probe_readable(client, row)
        if ok:
            readable += 1
        print(f'{meta["date"]} readable={str(ok).lower()} reason={reason}')
    print(f'scan: readable={readable}; unarchived={len(items)}; probed={probed}')
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
    parser.add_argument('--date', help='你的本地日历日期 YYYY-MM-DD；自动匹配 UTC/北京/美西当天的项目会议')
    parser.add_argument('--episode', help='仓库期数：48、EP48 或年份限定的 2025-48（期数每年重置）')
    parser.add_argument('--year', help='4 位年份，配合 --episode 消除跨年期数歧义（也可直接写 2025-48）')
    args = parser.parse_args(argv)
    command = args.command
    date = args.date if args.date else None
    episode = args.episode if args.episode else None
    year = args.year if args.year else None
    historical_input = args.date is not None or args.episode is not None or args.year is not None
    if historical_input:
        m.need(command in ('prepare', 'fetch-check'), '日期或期数仅用于历史 prepare/fetch-check')
    if date is not None:
        m.need(bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', date)), '日期须为 YYYY-MM-DD')
        m.utc_day(date + 'T00:00:00Z')
    if year is not None:
        m.need(bool(re.fullmatch(r'\d{4}', year)), '年份须为 4 位数字')
        m.need(episode is not None, '年份需要同时提供期数')
    m.need(not (date and episode), '期数与日期只能二选一')
    m.need(not (command == 'scan' and historical_input), '扫描不接受日期或期数')
    m.need(command != 'fetch-check' or date or episode, '历史检查需要本地日期或期数')
    m.need(bool(date or episode) or not historical_input, '历史补录需要本地日期或仓库期数；留空请使用只读扫描')
    root = root or Path(__file__).resolve().parents[1]
    # Resolve a repository EP to its unique UTC date from local events/ directories
    # before any Git/GitHub or remote work, so an unmapped or ambiguous episode
    # (numbers reset every year) fails closed early.
    resolved_episode = resolve_episode_date(root, episode, year) if episode else None
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
        if resolved_episode:
            meeting = historical(client, config, resolved_episode[0])
        else:
            meeting = historical_local(client, config, date)
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
        scan(client_factory(), config, archive, now or datetime.now(timezone.utc))
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
        if resolved_episode:
            rows = [historical(client_factory(), config, resolved_episode[0])]
        elif date:
            rows = [historical_local(client_factory(), config, date)]
        else:
            rows = discover(client_factory(), config, now or datetime.now(timezone.utc))
        plan = plan_latest(rows, archive, config)
        if not plan['skip']:
            metadata = plan['metadata']
            if resolved_episode:
                m.need(metadata['date'] == resolved_episode[0], '期数映射日期与会议 UTC 日期不一致')
                mapped_episode = resolved_episode[1]
            elif date:
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
