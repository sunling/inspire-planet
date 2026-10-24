"""Read-only occurrence diagnostics: no raw responses, IDs, URLs or bodies logged."""
import json, os, re
from pathlib import Path
import meeting_content as m
import latest_transcript as l

token = os.environ['TENCENT_MEETING_TOKEN']

def transport(packet):
    response = m.send_json(m.MCP_URL, packet, {'X-Tencent-Meeting-Token': token, 'X-Skill-Version': m.SKILL_VERSION})
    if packet['method'] == 'tools/call':
        result = response.get('result', {})
        data = result.get('structuredContent')
        if not isinstance(data, dict):
            try:
                data = json.loads(result['content'][0]['text'])
            except (KeyError, IndexError, ValueError):
                data = {}
        for _ in range(6):
            if not isinstance(data, dict): break
            if 'status_code' in data and data['status_code'] != 200:
                raw = data.get('body', '')
                encoded = raw if isinstance(raw, str) else json.dumps(raw)
                flags = [x for x in ('NoneType', 'KeyError', 'TypeError', 'ValueError', 'JSONDecodeError', 'permission', 'Permission', 'not found', 'invalid', 'Unauthorized', 'Traceback', 'timeout', 'Internal Server Error', 'record_file_id', 'meeting_id', 'pid', 'limit') if x in encoded]
                try:
                    body = json.loads(raw) if isinstance(raw, str) else raw
                except (ValueError, TypeError): body = None
                shape = sorted(k for k in body if re.fullmatch('[a-zA-Z_]{1,40}', k)) if isinstance(body, dict) else []
                print('upstream-diagnostic:', json.dumps({'status': data['status_code'], 'body_bytes': len(encoded.encode()), 'json_keys': shape, 'recognized_flags': flags}), flush=True)
                break
            if isinstance(data.get('body'), str):
                try: data = json.loads(data['body'])
                except ValueError: break
            elif 'data' in data: data = data['data']
            else: break
    return response

client = m.MCP(transport)
listing = client.rpc('tools/list', {})
for tool in listing.get('tools', []):
    if tool.get('name') in ('get_transcripts_details', 'get_transcripts_paragraphs', 'get_record_addresses'):
        schema = tool['inputSchema']
        print('tool-schema:', json.dumps({'name': tool['name'], 'required': schema.get('required', []), 'properties': {key: {k:v for k,v in val.items() if k in ('type','minimum','maximum','default')} for key,val in schema.get('properties', {}).items()}}), flush=True)
config = json.loads(Path('scripts/meeting-project.json').read_text())
meeting = l.historical_local(client, config, os.environ['CONTENT_DATE'])
records = meeting.get('records', [])
groups = m.token_pages(client, 'get_records_list', {'meeting_id': meeting['meeting_id']}, 'record_meetings')
candidates = []
for record in records:
    if '转写' in str(record.get('type', '')):
        candidates.append(('metadata', record['record_file_id']))
for group in groups:
    if (group.get('meeting_id'),group.get('sub_meeting_id')) == (meeting['meeting_id'],meeting['sub_meeting_id']):
        for file in group.get('record_files', []):
            candidates.append(('native',file['record_file_id']))
unique = list(dict.fromkeys(file_id for _,file_id in candidates))
m.need(len(unique) <= 12, '诊断候选过多')
print('candidate-counts:', json.dumps({'metadata': len(records), 'unique':len(unique)}), flush=True)
texts = []
for index,file_id in enumerate(unique, 1):
    for mode in ('default', 'omit-meeting-id'):
        if mode == 'omit-meeting-id' and 'meeting_id' in client.schemas['get_transcripts_details'].get('required', []): break
        class Wrapper:
            def call(self, name, args):
                if mode == 'omit-meeting-id': args = {k:v for k,v in args.items() if k != 'meeting_id'}
                return client.call(name,args)
        try:
            text = m.read_file_transcript(Wrapper(), meeting['meeting_id'],file_id)
            print(f'candidate={index}; mode={mode}; paragraphs={len(m.parse_transcript(text)) if text else 0}', flush=True)
            if text: texts.append(text)
            break
        except m.SafeError as exc:
            print(f'candidate={index}; mode={mode}; failure={exc}', flush=True)
print(f'complete-transcripts={len(texts)}', flush=True)
if texts:
    def canonical(text):
        return [(b['speaker'],b['time'],''.join(b['text'].split())) for b in m.parse_transcript(text)]
    paths = list(Path('events').glob(os.environ['CONTENT_DATE'][:4]+'/'+os.environ['CONTENT_DATE'].replace('-','')+'-ep*/transcript.txt'))
    if len(paths)==1:
        local=canonical(paths[0].read_text())
        print('archive-match='+str(any(canonical(text)==local for text in texts)), flush=True)
else:
    raise SystemExit(1)
