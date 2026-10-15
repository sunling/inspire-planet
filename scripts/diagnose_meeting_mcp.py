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
            content = response.get('result', {}).get('content', [])
            if len(content) == 1:
                envelope = json.loads(content[0]['text'])
                wrapper = envelope.get('data', envelope)
                if isinstance(wrapper.get('body'), str):
                    print('body-structure')
                    shape(json.loads(wrapper['body']))
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
    original_call = client.call
    def probe_call(name, args):
        # The live schema advertises is_compact; false preserves paging metadata.
        if client.schemas[name]['properties'].get('is_compact', {}).get('type') != 'boolean':
            raise RuntimeError('schema')
        client.rpc('tools/call', {'name': name, 'arguments': dict(args, is_compact=False)})
    for name, schema in client.schemas.items():
        for field, prop in schema.get('properties', {}).items():
            if field in TOOL_FIELDS[name]:
                desc = prop.get('description', '')
                print('schema-numeric-hints', name, field, re.findall(r'\b\d{1,5}\b', desc))
                print('schema-time-unit-hints', field, '毫秒' in desc or 'millisecond' in desc.lower(), '秒' in desc or 'second' in desc.lower())
    for name, args in [
        ('get_user_ended_meetings', {'start_time': '2026-10-10T00:00:00Z', 'end_time': '2026-10-10T23:59:59Z', 'page_size': 100, 'page_token': ''}),
        ('get_records_list', {'meeting_id': '13319006708380765410', 'page_size': 100, 'page_token': ''}),
    ]:
        result = client.call(name, args)
        if name == 'get_user_ended_meetings':
            body = json.loads(result['body'])
            meetings = body['meeting_info_list']
            selected = [r for r in meetings if r['meeting_id'] == '13319006708380765410']
            if len(selected) != 1:
                raise RuntimeError('nonunique')
            records = [r for r in selected[0]['records'] if '转写' in r.get('type', '')]
            from meeting_content import norm_time
            def duration(r):
                h, minute, second = map(int, norm_time(r['duration']).split(':'))
                return h * 3600 + minute * 60 + second
            records.sort(key=duration, reverse=True)
            if records:
                probe_call('get_transcripts_details', {'meeting_id': '13319006708380765410', 'record_file_id': records[0]['record_file_id'], 'pid': '0', 'limit': 100})


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('STOP: probe failed; details hidden')
        raise SystemExit(1) from None
