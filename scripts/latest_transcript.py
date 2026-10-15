#!/usr/bin/env python3
"""Zero-input project discovery; deterministic transcript-only public drafts."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import meeting_content as m


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
    m.need(isinstance(config.get('title'), str) and bool(config['title'].strip()), '项目标题未配置')
    rows = m.token_pages(client, 'get_user_ended_meetings',
                        {'start_time': day + 'T00:00:00Z', 'end_time': day + 'T23:59:59Z'}, 'meeting_info_list')
    return m.select_meeting(rows, day, config['title'], '')


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
    parser.add_argument('command', choices=['readonly', 'prepare', 'fetch-check', 'fetch', 'write', 'publish'])
    parser.add_argument('--date', help='Historical UTC occurrence date; no episode or filter input')
    args = parser.parse_args(argv)
    command = args.command
    if args.date is not None:
        m.need(command in ('prepare', 'fetch-check'), '日期仅用于历史 prepare/fetch-check')
        m.need(bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', args.date)), '日期须为 YYYY-MM-DD')
        m.utc_day(args.date + 'T00:00:00Z')
    m.need(command != 'fetch-check' or args.date is not None, '历史检查需要日期')
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
        meeting = historical(client, config, args.date)
        text = m.fetch_occurrence(client, meeting)
        blocks = m.parse_transcript(text)
        check_cache = root / '.git/meeting-content-fetch-check.txt'
        m.need(not check_cache.is_symlink(), '缓存路径不安全')
        check_cache.write_text(text, encoding='utf-8')
        print(f'历史远程完整转写已验证：{len(blocks)} 段；仅 runner 缓存，未写入公开文件。')
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
        rows = ([historical(client_factory(), config, args.date)] if args.date else
                discover(client_factory(), config, now or datetime.now(timezone.utc)))
        plan = plan_latest(rows, archive, config)
        if not plan['skip']:
            metadata = plan['metadata']
            if args.date:
                mapped = archive['mapping'].get(metadata['date'], set())
                episode = next(iter(mapped)) if len(mapped) == 1 else None
            else:
                episode = episode_for(plan['meeting'], rows, config)
            event = m.event_identity(metadata['date'], episode)[0] if episode else 'incoming/meetings/' + metadata['instance_key']
            plan.update(latest=True, event=event, episode=episode, date=metadata['date'],
                        branch='content/meeting-' + metadata['instance_key'], base='main',
                        head=run(['git', 'rev-parse', 'HEAD']).strip())
            branches = [plan['branch']]
            if episode:
                branches.append(m.event_identity(metadata['date'], episode)[1])
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
