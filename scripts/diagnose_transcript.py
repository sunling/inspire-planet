#!/usr/bin/env python3
"""Read-only bounded probes; never select, cache, print or publish a transcript."""
import argparse
import json
import os
from pathlib import Path
import sys

import latest_transcript as latest
import meeting_content as m

MAX_PROBES = 16


def diagnose(client, config, day):
    rows = latest.historical_candidates(client, config, day, 'Asia/Shanghai')
    m.need(len(rows) <= 8, '诊断日期超过 8 场；停止且不跨日查找')
    probes = 0
    seen = set()
    print('只读诊断：每文件最多请求第一页 1 段，不重试、不输出正文或身份；'
          '全程最多 16 次探测；成功不等于完整转写验证通过。', flush=True)
    for index, row in enumerate(sorted(rows, key=lambda r: latest.timestamp(r['start_time'])), 1):
        print(f'诊断场次 {index}/{len(rows)} '
              f'start_utc={latest.iso(latest.timestamp(row["start_time"]))}', flush=True)
        native, selected, typed = m.occurrence_files(client, row)
        native_ids = {file_id for _, file_id in native}
        selected_ids = {file_id for _, file_id in selected}
        print(f'原生文件数={len(native_ids)}；选用候选数={len(selected_ids)}；'
              f'候选来源={"明确标注转写" if typed else "原生录制列表"}；'
              f'两列表共享文件数={len(native_ids & selected_ids)}', flush=True)
        # Examine the original candidates first, then independently verified
        # same-occurrence native IDs. Never substitute a successful probe.
        files = list(dict.fromkeys([file_id for _, file_id in selected + native]))
        for ordinal, file_id in enumerate(files, 1):
            key = (row['meeting_id'], row['sub_meeting_id'], file_id)
            if key in seen:
                continue
            if probes >= MAX_PROBES:
                print('已达 16 次探测上限；诊断不完整，不选择或归档。', flush=True)
                return
            seen.add(key)
            probes += 1
            source = 'shared' if file_id in native_ids & selected_ids else (
                'selected-only' if file_id in selected_ids else 'native-only')
            args = {'meeting_id': row['meeting_id'], 'record_file_id': file_id,
                    'pid': '0', 'limit': 1}
            try:
                # The regular adapter still validates the whitelist/schema and
                # every response layer; one diagnostic attempt, no retry loop.
                data = client._call_once('get_transcripts_details', args)
                if data.get('empty_transcript'):
                    outcome = 'empty_transcript'
                else:
                    minutes = data.get('minutes')
                    m.need(isinstance(minutes, dict), '诊断响应结构不支持')
                    paragraphs = minutes.get('paragraphs')
                    m.need(isinstance(paragraphs, list) and isinstance(data.get('more'), bool),
                           '诊断响应结构不支持')
                    outcome = f'page_ok paragraphs={len(paragraphs)} more={data["more"]}'
            except m.UpstreamHTTPError as exc:
                status = exc.status if type(exc.status) is int else 'invalid'
                outcome = f'upstream_http={status}'
            except m.SafeError:
                outcome = 'rpc_business_or_format_error'
            print(f'文件候选 {ordinal}/{len(files)} source={source} '
                  f'pid=0 limit=1 result={outcome}', flush=True)
    print(f'诊断结束：探测={probes}；原完整读取仍失败，未缓存或归档任何正文。', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', required=True)
    args = parser.parse_args()
    token = os.environ.get('TENCENT_MEETING_TOKEN', '')
    m.need(bool(token), '缺少腾讯会议 Secret')
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / 'scripts/meeting-project.json').read_text())
    client = m.MCP(lambda packet: m.send_json(m.MCP_URL, packet,
        {'X-Tencent-Meeting-Token': token, 'X-Skill-Version': m.SKILL_VERSION}))
    diagnose(client, config, args.date)


if __name__ == '__main__':
    try:
        main()
    except m.SafeError as exc:
        print(f'诊断停止：{exc}', file=sys.stderr)
        sys.exit(1)
