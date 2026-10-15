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
    shape(client.call('get_user_ended_meetings', {'start_time': '2026-10-10T00:00:00Z', 'end_time': '2026-10-10T23:59:59Z', 'page_size': 100, 'page_token': ''}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('STOP: response incompatible; details hidden')
        raise SystemExit(1) from None
