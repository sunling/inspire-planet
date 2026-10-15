#!/usr/bin/env python3
"""Explicit-dispatch EP40 probe. Structure only; never payload values or artifacts."""
import json
import os
import re
from meeting_content import MCP, MCP_URL, SKILL_VERSION, TOOL_FIELDS, send_json


def shape(value, path='$', depth=0):
    if depth > 12:
        return
    if isinstance(value, dict):
        print(path, 'object', len(value))
        for key, child in value.items():
            # Server keys are structural, not arbitrary printable content.
            safe = key if re.fullmatch(r'[A-Za-z_][A-Za-z_]{0,63}', key) else '<key>'
            shape(child, path + '.' + safe, depth + 1)
    elif isinstance(value, list):
        print(path, 'array', len(value))
        if value:
            shape(value[0], path + '[]', depth + 1)
    else:
        print(path, type(value).__name__, value if path.rsplit('.', 1)[-1] in {'code', 'has_more', 'more', 'maximum', 'maxItems'} and type(value) in (int, bool) else '')
        if isinstance(value, str) and (path.endswith('.text') or path.endswith('.body')):
            try:
                decoded = json.loads(value)
            except ValueError:
                return
            shape(decoded, path + '.decoded', depth + 1)


def main():
    if os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        raise RuntimeError('explicit dispatch required')
    token = os.environ['TENCENT_MEETING_TOKEN']
    def transport(packet):
        response = send_json(MCP_URL, packet, {'X-Tencent-Meeting-Token': token, 'X-Skill-Version': SKILL_VERSION})
        if packet['method'] == 'tools/call':
            print('tool', packet['params']['name'])
            shape(response)
        else:
            for tool in response.get('result', {}).get('tools', []):
                if tool.get('name') in TOOL_FIELDS:
                    print('schema', tool['name'])
                    shape(tool.get('inputSchema', {}))
                    if 'outputSchema' in tool:
                        print('output-schema')
                        shape(tool['outputSchema'])
        return response
    client = MCP(transport)
    for name, args in [
        ('get_user_ended_meetings', {'start_time': '2026-10-10T00:00:00Z', 'end_time': '2026-10-10T23:59:59Z', 'page_size': 100, 'page_token': ''}),
        ('get_records_list', {'meeting_id': '13319006708380765410', 'page_size': 100, 'page_token': ''}),
    ]:
        client.call(name, args)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('STOP: probe failed; details hidden')
        raise SystemExit(1) from None
