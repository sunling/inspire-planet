#!/usr/bin/env python3
"""Bounded, read-only Tencent MCP → transcript-only drafts. Standard library only."""
import re
import json
from pathlib import Path
import urllib.request
import urllib.error
from urllib.parse import urlsplit

MCP_URL = 'https://mcp.meeting.tencent.com/mcp/wemeet-open/v1'
SKILL_VERSION = 'v1.0.15'  # config.json from official package, not registry metadata
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


def https_url(url):
    parsed = urlsplit(url)
    need(parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username and not parsed.password
         and not parsed.query and not parsed.fragment, '服务地址必须是无凭据、query、fragment 的 HTTPS URL')
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SafeError('拒绝 HTTP 重定向，防止凭据转发')


def send_json(url, payload, headers, opener=None):
    https_url(url)
    request = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                                     headers={'Content-Type': 'application/json', 'Accept': 'application/json', **headers}, method='POST')
    try:
        with (opener or urllib.request.build_opener(NoRedirect())).open(request, timeout=180) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
        need(len(body) <= MAX_RESPONSE_BYTES, '服务响应超过大小上限；拒绝截断')
        result = json.loads(body)
        need(isinstance(result, dict), '服务返回非 JSON 对象')
        return result
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        raise SafeError(f'服务 HTTP {code}；请核对地址、Token、权限和配额（正文已隐藏）') from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise SafeError('服务连接或 JSON 解析失败（原始错误已隐藏）') from None


def publish(root, plan, run):
    need(run(['git', 'branch', '--show-current']).strip() == plan['base'], '发布前检出分支改变；拒绝提交')
    need(run(['git', 'rev-parse', 'HEAD']).strip() == plan['head'], '发布前基线改变；拒绝提交')
    changed = set(run(['git', 'diff', '--name-only', 'HEAD']).splitlines())
    changed.update(run(['git', 'ls-files', '--others', '--exclude-standard']).splitlines())
    if plan.get('latest'):
        from latest_transcript import allowed_paths as latest_paths
        allowlist = set(latest_paths(plan))
    else:
        allowlist = set(allowed_paths(plan['event']))
    label = f"EP{int(plan['episode']):02d}" if plan['episode'] else '待确认期次'
    need(bool(changed) and changed <= allowlist, '改动包含非本期白名单文件；拒绝提交')
    for relative in allowlist:
        path = root / relative
        need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve()), '提交目标缺失或不是安全常规文件')
    # Recheck before commit: never overwrite an existing event branch.
    need(not run(['git', 'ls-remote', '--heads', 'origin', 'refs/heads/' + plan['branch']]).strip(), '远端内容分支已存在；停止且不覆盖')
    run(['git', 'switch', '-c', plan['branch']])
    need(run(['git', 'branch', '--show-current']).strip() == plan['branch'], '未检出本期内容分支')
    run(['git', 'add', '--', *sorted(allowlist)])
    staged = set(run(['git', 'diff', '--cached', '--name-only']).splitlines())
    need(staged == changed and staged <= allowlist, '暂存区超出本期范围')
    run(['git', '-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
         'commit', '-m', f"content: draft {plan['date']} {label}"])
    run(['git', 'push', '--set-upstream', 'origin', plan['branch']])
    local_head = run(['git', 'rev-parse', 'HEAD']).strip()
    remote = run(['git', 'ls-remote', '--heads', 'origin', 'refs/heads/' + plan['branch']]).split()
    need(bool(remote) and remote[0] == local_head, '无法确认内容分支推送结果')
    body = ('仅逐字稿的公开、未经人工审核 Draft PR；原始转写和姓名在公开分支可见。\n\n'
            '- [ ] 核对 UTC 日期、期数、会议来源和完整逐字稿\n'
            '- [ ] 确认所有参与者公开授权、隐私与可识别信息\n\n'
            '没有生成纪要、金句、文章或图片；后续可由 ChatGPT/Codex 在同一分支人工发起整理。\n'
            '不自动合并，不发布到网站或社交平台。')
    run(['gh', 'pr', 'create', '--draft', '--base', plan['base'], '--head', plan['branch'],
         '--title', f"内容草稿 {plan['date']} {label}", '--body', body])
    result = json.loads(run(['gh', 'pr', 'view', plan['branch'], '--json', 'state,isDraft,headRefName,baseRefName,files']))
    need(result.get('state') == 'OPEN' and result.get('isDraft') is True and result.get('headRefName') == plan['branch']
         and result.get('baseRefName') == plan['base'], '无法确认公开 Draft PR 状态')
    need({f['path'] for f in result.get('files', [])} == staged, 'Draft PR 文件范围不匹配')
    return result


def prepare(root, day, episode, base, run):
    event, branch = event_identity(day, episode)
    need(run(['git', 'branch', '--show-current']).strip() == base, '必须检出指定默认分支；拒绝在其他分支运行')
    need(not run(['git', 'status', '--porcelain']).strip(), '工作区不干净；拒绝混入其他改动')
    remote = run(['git', 'ls-remote', '--heads', 'origin', 'refs/heads/' + branch]).strip()
    prs = json.loads(run(['gh', 'pr', 'list', '--state', 'all', '--head', branch, '--base', base, '--limit', '100', '--json', 'number,state,isDraft']))
    existing = (root / event / 'transcript.txt').exists() or (root / event / 'transcript.txt').is_symlink()
    plan = {'date': day, 'episode': episode, 'event': event, 'branch': branch, 'base': base,
            'skip': bool(remote or prs or existing), 'head': run(['git', 'rev-parse', 'HEAD']).strip() if not (remote or prs or existing) else ''}
    return plan


def allowed_paths(event):
    need(bool(re.fullmatch(r'events/\d{4}/\d{8}-ep\d{2,3}', event)), 'event 路径无效')
    return [f'{event}/transcript.txt', 'events/README.md']


def update_transcript_index(index_text, event):
    """Update only the canonical six-column table, never append a second table.

    Preserve hand-edited links and everything following the first table (including
    older-year archives). Reject unexpected layouts before writing any transcript.
    """
    name = event.rsplit('/', 1)[-1]
    relative = event.removeprefix('events/')
    link = f'[转写]({relative}/transcript.txt)'
    lines = index_text.splitlines(keepends=True)
    header = '| 期次与日期 | 转写 | 纪要 | 金句 | 发布文案 | 封面 |'
    headers = [i for i, line in enumerate(lines) if line.strip() == header]
    need(len(headers) == 1, '会议索引主表表头缺失或重复；拒绝追加第二张表')
    header_at = headers[0]
    need(header_at + 1 < len(lines) and
         bool(re.fullmatch(r'\|(?:\s*:?-{3,}:?\s*\|){6}', lines[header_at + 1].strip())),
         '会议索引主表分隔行不支持')
    begin = header_at + 2
    end = begin
    while end < len(lines) and lines[end].lstrip().startswith('|'):
        end += 1

    entries = []
    for i in range(begin, end):
        parts = lines[i].rstrip('\r\n').split('|')
        need(len(parts) == 8 and bool(re.fullmatch(r'\d{8}-ep\d{2,3}', parts[1].strip())),
             '会议索引主表行格式不支持')
        entries.append((parts[1].strip(), i))
    keys = [key for key, _ in entries]
    need(keys == sorted(set(keys)), '会议索引主表有重复或日期顺序不正确')
    # A stale row elsewhere (e.g. after the 2025 <details> archive) must never
    # be silently duplicated.
    row_pattern = r'^\|\s*' + re.escape(name) + r'\s*\|'
    occurrences = [i for i, line in enumerate(lines) if re.match(row_pattern, line)]
    need(len(occurrences) <= 1 and all(begin <= i < end for i in occurrences),
         '会议索引行位于主表之外或重复；请先整理')

    if occurrences:
        i = occurrences[0]
        parts = lines[i].rstrip('\r\n').split('|')
        need(parts[2].strip() == '—', '已有索引转写；禁止覆盖')
        parts[2] = ' ' + link + ' '
        newline = '\r\n' if lines[i].endswith('\r\n') else '\n'
        lines[i] = '|'.join(parts) + newline
    else:
        position = next((i for key, i in entries if key > name), end)
        newline = '\r\n' if any(line.endswith('\r\n') for line in lines) else '\n'
        lines.insert(position, f'| {name} | {link} | — | — | — | — |' + newline)
    return ''.join(lines)


def write_draft(root, event, text):
    paths = allowed_paths(event)
    parse_transcript(text)
    target = root / event
    transcript = target / 'transcript.txt'
    index = root / 'events/README.md'
    for relative in paths:
        path = root / relative
        need(path.resolve().is_relative_to(root.resolve()) and
             not any(p.is_symlink() for p in [path, *path.parents] if p != root.parent),
             '写入路径不是安全常规路径')
    need(not transcript.exists() and not transcript.is_symlink(), '已有转写；禁止覆盖')
    # Compute and validate the index change before creating the transcript.
    index_text = update_transcript_index(index.read_text(encoding='utf-8'), event)
    target.mkdir(parents=True, exist_ok=True)
    with transcript.open('x', encoding='utf-8') as f:
        f.write(text)
    index.write_text(index_text, encoding='utf-8')
    return paths

MAX_TRANSCRIPT_CHARS = 300000


def parse_transcript(text):
    need(0 < len(text) <= MAX_TRANSCRIPT_CHARS, '转写为空或超过完整上下文上限；拒绝截断')
    pattern = r'^([^\n()]+)\((\d{1,3}:\d{2}:\d{2}|\d{1,3}:\d{2})\):[ \t]*\n'
    headers = list(re.finditer(pattern, text, re.M))
    need(bool(headers) and not text[:headers[0].start()].strip(), '本地转写格式不支持；须为发言人(时间): 换行正文')
    blocks = []
    for i, h in enumerate(headers):
        body = text[h.end():headers[i + 1].start() if i + 1 < len(headers) else len(text)].strip()
        need(bool(body) and h[1].strip().lower() not in ('未知', 'unknown'), '转写有空段落或未知发言人')
        blocks.append({'speaker': h[1].strip(), 'time': norm_time(h[2]), 'text': body})
    return blocks


# Names confirmed by Tencent help 2233 and official @tencent-adm package.
# These are the ONLY callable tools. Runtime tools/list must confirm all argument
# names/types before any call; no model may select tools or invent arguments.
TOOL_FIELDS = {
    'get_user_ended_meetings': {'start_time': 'string', 'end_time': 'string', 'page_size': 'integer', 'page_token': 'string'},
    'get_records_list': {'meeting_id': 'string', 'page_size': 'integer', 'page_token': 'string'},
    'get_transcripts_details': {'meeting_id': 'string', 'record_file_id': 'string', 'pid': 'string', 'limit': 'integer'},
}
for _fields in TOOL_FIELDS.values():
    _fields['is_compact'] = 'boolean'  # Full mode preserves business/paging flags.
MAX_PAGES = 200
MAX_PARAGRAPHS = 20000


class MCP:
    def __init__(self, transport):
        self.transport = transport
        self.schemas = {}
        cursor = None
        seen = set()
        for _ in range(MAX_PAGES):
            result = self.rpc('tools/list', {'cursor': cursor} if cursor else {})
            for tool in result.get('tools', []):
                if tool.get('name') in TOOL_FIELDS:
                    self.schemas[tool['name']] = tool['inputSchema']
            cursor = result.get('nextCursor')
            if not cursor:
                break
            need(cursor not in seen, 'MCP 工具列表分页未前进')
            seen.add(cursor)
        else:
            raise SafeError('MCP 工具列表超过分页上限')
        need(set(self.schemas) == set(TOOL_FIELDS), 'MCP 缺少所需只读工具；请核对官方 tools/list')
        for name, fields in TOOL_FIELDS.items():
            schema = self.schemas[name]
            need(schema.get('type') == 'object', 'MCP 工具 schema 不兼容')
            props = schema.get('properties', {})
            for key, expected in fields.items():
                actual = props.get(key, {}).get('type')
                need(actual == expected or (expected == 'integer' and actual == 'number'), 'MCP 参数 schema 已变化；请核对官方 tools/list')
            need(set(schema.get('required', [])) <= set(fields), 'MCP 新增必填参数；请更新适配器')

    def rpc(self, method, params):
        packet = self.transport({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
        need(isinstance(packet, dict) and packet.get('id') == 1 and 'error' not in packet, 'MCP RPC 失败；检查连接与授权（响应已隐藏）')
        result = packet.get('result')
        need(isinstance(result, dict), 'MCP RPC 返回结构不支持')
        return result

    def call(self, name, args):
        need(name in TOOL_FIELDS, '禁止非白名单 MCP 工具')
        need(args.get('is_compact', False) is False, 'MCP 必须使用完整模式；拒绝缺失分页标志')
        args = dict(args, is_compact=False)
        schema = self.schemas[name]
        need(set(args) <= set(TOOL_FIELDS[name]) and set(schema.get('required', [])) <= set(args), 'MCP 参数不符合已验证 schema')
        for key, value in args.items():
            typ = TOOL_FIELDS[name][key]
            need((typ == 'string' and isinstance(value, str)) or (typ == 'integer' and type(value) is int)
                 or (typ == 'boolean' and type(value) is bool), 'MCP 参数类型无效')
        result = self.rpc('tools/call', {'name': name, 'arguments': args})
        need(not result.get('isError'), 'MCP 工具失败；检查授权和录制状态（响应已隐藏）')
        if isinstance(result.get('structuredContent'), dict):
            data = result['structuredContent']
        else:
            content = result.get('content', [])
            need(len(content) == 1 and content[0].get('type') == 'text', 'MCP 工具返回结构不支持')
            try:
                data = json.loads(content[0]['text'])
            except (ValueError, KeyError):
                raise SafeError('MCP 工具未返回完整 JSON') from None
        need(isinstance(data, dict), 'MCP 工具返回结构不支持')
        # Observed MCP returns optional data -> HTTP envelope -> JSON body.
        # Check every layer (including the final body); never recursively hunt
        # for a plausible list or ignore an inner business/HTTP failure.
        for _ in range(6):
            if data.get('code') == 30002 and name == 'get_transcripts_details':
                return {'empty_transcript': True}
            need(data.get('code', 0) == 0, 'MCP 业务失败（响应已隐藏）')
            if 'status_code' in data or 'body' in data:
                status = data.get('status_code')
                if type(status) is not int or status != 200:
                    code = None
                    try:
                        body = json.loads(data.get('body', ''))
                        if isinstance(body, dict) and type(body.get('code')) is int:
                            code = body['code']
                    except (ValueError, TypeError):
                        pass
                    safe_status = status if type(status) is int else 'invalid'
                    raise SafeError(f'MCP 上游 HTTP 失败：tool={name}，status={safe_status}，code={code}（响应已隐藏）')
                need(isinstance(data.get('body'), str), 'MCP HTTP body 结构不支持')
                try:
                    data = json.loads(data['body'])
                except ValueError:
                    raise SafeError('MCP HTTP body 不是完整 JSON') from None
            elif 'data' in data:
                data = data['data']
            else:
                return data
            need(isinstance(data, dict), 'MCP data 结构不支持')
        raise SafeError('MCP 返回包装层数超过上限')


def token_pages(client, name, args, key):
    rows, token, seen = [], '', set()
    for _ in range(MAX_PAGES):
        data = client.call(name, dict(args, page_size=100, page_token=token))
        chunk = data.get(key)
        need(isinstance(chunk, list), 'MCP 列表结构不支持；请核对官方返回结构')
        rows.extend(chunk)
        need(isinstance(data.get('has_more'), bool), 'MCP 缺少分页完成标志；拒绝不完整数据')
        if not data['has_more']:
            return rows
        token = data.get('next_page_token')
        need(bool(chunk) and isinstance(token, str) and bool(token) and token not in seen, 'MCP 分页未前进')
        seen.add(token)
    raise SafeError('MCP 超过分页上限；拒绝截断数据')


def select_meeting(rows, day, subject, meeting_id):
    need(bool(subject.strip()) or bool(meeting_id.strip()), '必须配置精确会议主题或 meeting_id 过滤器')
    matches = [r for r in rows if (not subject or r.get('subject') == subject)
               and (not meeting_id or r.get('meeting_id') == meeting_id)
               and utc_day(r.get('start_time')) == day]
    need(len(matches) == 1, '指定 UTC 日期与过滤器必须唯一命中已结束会议；禁止任选最新场次')
    need(bool(matches[0].get('meeting_id')), '会议缺少 ID')
    return matches[0]


def fetch_transcript(client, day, subject, meeting_id):
    rows = token_pages(client, 'get_user_ended_meetings', {'start_time': day + 'T00:00:00Z', 'end_time': day + 'T23:59:59Z'}, 'meeting_info_list')
    meeting = select_meeting(rows, day, subject, meeting_id)
    return fetch_occurrence(client, meeting)


def read_file_transcript(client, meeting_id, record_file_id):
    """Read every page of one recording; return None only when its transcript is empty."""
    paragraphs, pid, seen = [], 0, set()
    for _ in range(MAX_PAGES):
        data = client.call('get_transcripts_details', {'meeting_id': meeting_id, 'record_file_id': record_file_id, 'pid': str(pid), 'limit': 100})
        if data.get('empty_transcript'):
            need(not paragraphs, '分页中途返回空转写错误；拒绝截断')
            break
        chunk = data.get('minutes', {}).get('paragraphs')
        need(isinstance(chunk, list) and isinstance(data.get('more'), bool), '转写返回结构不支持；拒绝截断')
        for p in chunk:
            try:
                current = int(p['pid'])
            except (ValueError, TypeError, KeyError):
                raise SafeError('转写段落 ID 无效') from None
            need(current >= pid and current not in seen, '转写分页重复或倒退')
            seen.add(current)
        paragraphs.extend(chunk)
        need(len(paragraphs) <= MAX_PARAGRAPHS, '转写超过段落上限；拒绝截断')
        if not data['more']:
            break
        need(bool(chunk), '转写空页仍有后续；拒绝截断')
        pid = int(chunk[-1]['pid']) + 1
    else:
        raise SafeError('转写超过分页上限；拒绝截断')
    blocks = []
    for p in paragraphs:
        text = ''.join(w['text'] for sentence in p.get('sentences', []) for w in sentence.get('words', [])).strip()
        if text:
            speaker = p.get('speaker', {}).get('user_name')
            need(isinstance(speaker, str) and bool(speaker.strip()) and speaker not in ('未知', 'unknown'), '转写包含未知发言人；请人工处理')
            need(not re.search(r'[\r\n()]', speaker), '转写发言人格式不支持')
            blocks.append(f"{speaker}({norm_time(p.get('start_time'))}):\n{text}")
    if blocks:
        return '\n\n'.join(blocks) + '\n'
    return None


def fetch_occurrence(client, meeting):
    # The ended-meetings records are a stale/incomplete summary. Use the fully
    # paginated recording endpoint as authority, scoped by BOTH occurrence IDs.
    records = meeting.get('records')
    sub = meeting.get('sub_meeting_id')
    need(isinstance(records, list) and isinstance(sub, str) and bool(sub), '本场录制列表或子会议身份缺失')
    groups = token_pages(client, 'get_records_list', {'meeting_id': meeting['meeting_id']}, 'record_meetings')
    native = []
    for group in groups:
        if group.get('meeting_id') != meeting['meeting_id'] or group.get('sub_meeting_id') != sub:
            continue
        files = group.get('record_files')
        need(isinstance(files, list) and bool(files) and bool(group.get('meeting_record_id')), '本场录制文件列表结构不支持')
        for file in files:
            need(isinstance(file.get('record_file_id'), str) and bool(file['record_file_id']), '录制文件缺少 ID')
            native.append((group['meeting_record_id'], file['record_file_id']))
    need(bool(native), '本场没有可验证的原生录制文件；停止且不跨期查找')
    # read_file_transcript addresses files by file ID, so IDs must be unique
    # even across recording groups within this occurrence.
    need(len({file_id for _, file_id in native}) == len(native),
         '本场录制文件 ID 重复；需人工核对')
    need(len(native) <= 8, '本场录制文件超过读取上限；拒绝遗漏并需人工核对')
    candidates = sorted(native)

    transcripts = []
    for index, (_, file_id) in enumerate(candidates, 1):
        print(f'正在验证本场转写候选 {index}/{len(candidates)}；未输出文件身份。')
        text = read_file_transcript(client, meeting['meeting_id'], file_id)
        if text:
            transcripts.append(text)
    need(bool(transcripts), '本场录制存在，但尚无非空完整文字转写；稍后重试')

    # Compare actual spoken text, not speaker names or timestamp headers.
    # Every candidate has passed full pagination validation. If two longest
    # transcripts differ, no unambiguous winner exists: fail closed.
    scored = [(sum(len(block['text']) for block in parse_transcript(text)), text)
              for text in transcripts]
    longest = max(length for length, _ in scored)
    winners = [text for length, text in scored if length == longest]
    need(all(text == winners[0] for text in winners[1:]),
         '同场最长文字转写出现并列且内容不同；请人工核对')
    print(f'同场录制文件={len(native)}；非空完整转写={len(transcripts)}；'
          f'选择最长正文，字数={longest}；未输出原始转写。')
    return winners[0]
from datetime import datetime, timezone


class SafeError(Exception):
    """Only static, credential-free messages may be raised with this type."""


def need(ok, message):
    if not ok:
        raise SafeError(message)


def event_identity(day, episode):
    try:
        need(bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', day)), '日期须为 YYYY-MM-DD')
        datetime.strptime(day, '%Y-%m-%d')
    except ValueError:
        raise SafeError('日期无效') from None
    need(bool(re.fullmatch(r'[1-9]\d{0,2}', episode)), '期数须为 1–999')
    stamp = day.replace('-', '')
    return f'events/{day[:4]}/{stamp}-ep{int(episode):02d}', f'content/{stamp}-ep{int(episode):02d}'


def utc_day(value):
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
            return datetime.fromtimestamp(float(value), timezone.utc).date().isoformat()
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        need(dt.tzinfo is not None, '会议时间缺少时区')
        return dt.astimezone(timezone.utc).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        raise SafeError('会议时间格式不支持') from None


def norm_time(value):
    # Native transcript timestamps are integer milliseconds (Tencent topic 797),
    # unlike CLI duration/header strings. Floor subsecond precision for headers.
    if type(value) is int:
        need(value >= 0, '转写时间戳无效')
        seconds = value // 1000
        return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'
    need(isinstance(value, str) and bool(re.fullmatch(r'\d+:\d{2}(?::\d{2})?', value)), '转写时间戳无效')
    parts = [int(x) for x in value.split(':')]
    if len(parts) == 2:
        parts.insert(0, 0)
    h, minute, second = parts
    need(minute < 60 and second < 60, '转写时间戳无效')
    return f'{h:02d}:{minute:02d}:{second:02d}'


def main(argv=None, root=None):
    import argparse
    import os
    import subprocess
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validate', 'connectivity', 'fetch-check', 'prepare', 'fetch', 'write', 'publish'])
    args = parser.parse_args(argv)
    root = root or Path(__file__).resolve().parents[1]
    def env(name):
        return os.environ.get(name, '')
    def run(command):
        try:
            result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=180, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise SafeError('外部命令无法执行或超时（原始错误已隐藏）') from None
        need(result.returncode == 0, 'Git/GitHub/内容检查命令失败；检查权限及仓库设置（输出已隐藏）')
        return result.stdout
    def client():
        token = env('TENCENT_MEETING_TOKEN')
        need(bool(token), '缺少 TENCENT_MEETING_TOKEN；请在 Actions secrets 设置')
        return MCP(lambda payload: send_json(MCP_URL, payload, {'X-Tencent-Meeting-Token': token, 'X-Skill-Version': SKILL_VERSION}))
    if args.command == 'connectivity':
        client()
        print('MCP 连接与只读工具参数 schema 校验通过；未读取会议、未调用模型、未写入公开内容。')
        return
    day, episode = env('CONTENT_DATE'), env('CONTENT_EPISODE')
    event, branch = event_identity(day, episode)
    if args.command == 'validate':
        path = root / event / 'transcript.txt'
        need(path.is_file(), '目标期没有本地转写')
        blocks = parse_transcript(path.read_text(encoding='utf-8'))
        print(f'本地转写验证通过：{len(blocks)} 段；未调用服务、未生成或提交内容。')
        return
    if args.command == 'fetch-check':
        need(bool(env('CONTENT_MEETING_SUBJECT').strip() or env('CONTENT_MEETING_ID').strip()), 'MCP 必须配置精确会议过滤器')
        need((root / '.git').is_dir() and not (root / '.git').is_symlink(), '缓存要求安全的 .git 目录')
        # Integration check must always exercise MCP, even for committed EP40.
        text = fetch_transcript(client(), day, env('CONTENT_MEETING_SUBJECT'), env('CONTENT_MEETING_ID'))
        blocks = parse_transcript(text)
        cache = root / '.git/meeting-content-fetch-check.txt'
        need(not cache.is_symlink(), '缓存不得为符号链接')
        cache.write_text(text, encoding='utf-8')
        print(f'远程转写拉取与完整性检查通过：{len(blocks)} 段；仅缓存 .git，未写入公开内容，正文不进入日志。')
        return
    need((root / '.git').is_dir() and not (root / '.git').is_symlink(), '缓存要求安全的 .git 目录')
    state = root / '.git/meeting-content-plan.json'
    cache = root / '.git/meeting-content-transcript.txt'
    need(not state.is_symlink() and not cache.is_symlink(), '计划与缓存不得为符号链接')
    if args.command == 'prepare':
        # Never let a prior attempt's transcript survive a new plan.
        cache.unlink(missing_ok=True)
        state.unlink(missing_ok=True)
        base = env('CONTENT_BASE_BRANCH')
        need(bool(base), '缺少默认分支配置')
        plan = prepare(root, day, episode, base, run)
        if not plan['skip']:
            need(bool(env('CONTENT_MEETING_SUBJECT').strip() or env('CONTENT_MEETING_ID').strip()), 'MCP 必须配置精确会议过滤器')
        state.write_text(json.dumps(plan), encoding='utf-8')
        if env('GITHUB_OUTPUT'):
            with open(env('GITHUB_OUTPUT'), 'a', encoding='utf-8') as f:
                f.write('skip=' + str(plan['skip']).lower() + '\n')
        print('跳过：已有逐字稿、PR 或远端草稿分支；未拉取或覆盖。' if plan['skip'] else '本期范围与远端幂等检查通过。')
        return
    need(state.is_file(), '请先执行 prepare')
    plan = json.loads(state.read_text())
    need(plan['event'] == event and plan['branch'] == branch and not plan['skip'], '计划身份不匹配或已经跳过')
    need(run(['git', 'branch', '--show-current']).strip() == plan['base'] and run(['git', 'rev-parse', 'HEAD']).strip() == plan['head'], '运行中基线分支改变；停止')
    if args.command == 'fetch':
        need(not (root / event / 'transcript.txt').exists(), '已有逐字稿；停止且不覆盖')
        text = fetch_transcript(client(), day, env('CONTENT_MEETING_SUBJECT'), env('CONTENT_MEETING_ID'))
        blocks = parse_transcript(text)
        cache.write_text(text, encoding='utf-8')
        print(f'完整转写已验证：{len(blocks)} 段；正文不进入日志。')
    elif args.command == 'write':
        need(cache.is_file(), '请先执行 fetch')
        write_draft(root, event, cache.read_text(encoding='utf-8'))
        print('仅逐字稿和总索引已写入；没有生成内容，仍需人工审核与公开授权确认。')
    elif args.command == 'publish':
        need(env('CONTENT_PUBLISH_ALLOWED') == 'true' and env('GITHUB_ACTIONS') == 'true', '发布仅允许显式授权的 Actions draft 模式')
        run(['python3', 'scripts/check-content.py'])
        run(['gh', 'auth', 'setup-git', '--hostname', 'github.com'])
        publish(root, plan, run)
        print('公开 Draft PR 已创建并回读验证；未合并、未发布站点。')


if __name__ == '__main__':
    try:
        main()
    except SafeError as exc:
        print(f'停止：{exc}', file=__import__('sys').stderr)
        raise SystemExit(1) from None
    except Exception:
        # Never print untrusted server messages, raw response bodies or tokens.
        print('停止：数据或运行环境不兼容；详细响应已隐藏，请按文档检查官方 schema 与权限。', file=__import__('sys').stderr)
        raise SystemExit(1) from None

