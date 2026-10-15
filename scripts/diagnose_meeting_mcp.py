"""Temporary explicit EP40 dispatch structure probe; no values/artifacts."""
import os
import re
from meeting_content import MCP, MCP_URL, SKILL_VERSION, send_json


def shape(value, path='$', depth=0):
    if depth > 9:
        return
    if isinstance(value, dict):
        print(path, 'object', len(value))
        for key, child in value.items():
            key = key if re.fullmatch('[A-Za-z_][A-Za-z_]{0,63}', key) else '<key>'
            shape(child, path + '.' + key, depth + 1)
    elif isinstance(value, list):
        print(path, 'array', len(value))
        if value:
            shape(value[0], path + '[]', depth + 1)
    else:
        safe_numeric = (path.endswith('_count') or path.endswith('.has_more') or path.endswith('.more') or path.endswith('.code'))
        print(path, type(value).__name__, value if safe_numeric and type(value) in (int, bool) else '')


def main():
    if os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        raise RuntimeError()
    token = os.environ['TENCENT_MEETING_TOKEN']
    client = MCP(lambda payload: send_json(MCP_URL, payload, {'X-Tencent-Meeting-Token': token, 'X-Skill-Version': SKILL_VERSION}))
    from meeting_content import token_pages, utc_day
    ended = client.call('get_user_ended_meetings', {'start_time': '2026-10-10T00:00:00Z', 'end_time': '2026-10-10T23:59:59Z', 'page_size': 100, 'page_token': ''})
    shape(ended)
    meeting = ended['meeting_info_list'][0]
    rows = token_pages(client, 'get_records_list', {'meeting_id': '13319006708380765410'}, 'record_meetings')
    shape(rows)
    sub = meeting.get('sub_meeting_id')
    same_sub = [r for r in rows if sub and r.get('sub_meeting_id') == sub]
    same_day = [r for r in rows if utc_day(r['media_start_time']) == '2026-10-10']
    print('record-groups-count', len(rows), 'matching-sub-count', len(same_sub), 'matching-day-count', len(same_day))
    print('selected-sub-present', bool(sub))
    known = {r['meeting_record_id'] for r in meeting['records']}
    print('matching-record-id-count', sum(r['meeting_record_id'] in known for r in rows))
    shape(same_day)
    # Compare only identities in memory; output contains counts, never IDs.
    files = {f['record_file_id'] for r in same_day for f in r['record_files']}
    print('ended-file-count', len(meeting['records']), 'day-file-count', len(files), 'overlap-count', sum(r['record_file_id'] in files for r in meeting['records']))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('STOP: response incompatible; details hidden')
        raise SystemExit(1) from None
