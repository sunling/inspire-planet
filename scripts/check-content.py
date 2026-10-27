#!/usr/bin/env python3
"""Check the shared archive's local links, card JSON, skill paths and episode transcripts."""
from pathlib import Path
import json
import re
from datetime import datetime
from urllib.parse import unquote
from validate_publication import validate_publication

ROOT = Path(__file__).resolve().parents[1]
errors = []


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def string_list(value, nonempty=False):
    return (isinstance(value, list) and (bool(value) or not nonempty)
            and all(nonempty_string(item) for item in value))


def check_episode(value, path):
    match = re.fullmatch(r'EP(\d+)', value) if isinstance(value, str) else None
    expected = int(path.parent.name.rsplit('-ep', 1)[1])
    require(match is not None and int(match[1]) == expected,
            'episode must match directory episode')


for p in ROOT.rglob('*.md'):
    if '.git' in p.parts:
        continue
    text = p.read_text()
    visible = re.sub(r'```.*?```', '', text, flags=re.S)
    visible = re.sub(r'`[^`\n]+`', '', visible)
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', visible):
        target = unquote(target.strip('<>').split('#')[0])
        if not target or re.match(r'[a-z]+:', target):
            continue
        resolved = (p.parent / target).resolve()
        if not resolved.is_relative_to(ROOT) or not resolved.exists():
            errors.append(f'{p.relative_to(ROOT)}: broken local link {target}')
    if '/Users/' in text:
        errors.append(f'{p.relative_to(ROOT)}: machine-local path')
    if '.agents/skills' in p.as_posix() and 'practices/inspire-planet/' in text:
        errors.append(f'{p.relative_to(ROOT)}: old workspace path')
for p in (ROOT / 'events').rglob('quote-cards.json'):
    try:
        data = json.loads(p.read_text())
        require(isinstance(data, list), 'expected card array')
        for index, row in enumerate(data):
            require(isinstance(row, dict) and set(row) == {'name', 'title', 'quote', 'detail', 'episode'},
                    f'card {index + 1}: incorrect fields')
            require(all(nonempty_string(value) for value in row.values()),
                    f'card {index + 1}: fields must be nonempty strings')
            check_episode(row['episode'], p)
            require(not re.search(r'出处\s*[：:]|\b\d{1,2}:\d{2}:\d{2}\b', row['detail']),
                    f'card {index + 1}: detail contains source note or transcript timestamp')
    except ValueError as exc:
        errors.append(f'{p.relative_to(ROOT)}: invalid card data {exc}')
skills = ROOT / '.agents/skills'
for p in skills.glob('*/SKILL.md'):
    text = p.read_text()
    if not text.startswith('---\n') or f'name: {p.parent.name}\n' not in text or '\ndescription: ' not in text:
        errors.append(f'{p.relative_to(ROOT)}: invalid skill metadata')
for p in (ROOT / 'events').rglob('summary.json'):
    try:
        data = json.loads(p.read_text())
        require(isinstance(data, dict), 'expected summary object')
        require({'episode', 'date', 'title', 'overview', 'topics'} <= set(data), 'missing summary fields')
        require(all(nonempty_string(data[key]) for key in ('episode', 'date', 'title', 'overview')),
                'summary text fields must be nonempty strings')
        check_episode(data['episode'], p)
        expected_date = datetime.strptime(p.parent.name.split('-')[0], '%Y%m%d').strftime('%Y-%m-%d')
        require(data['date'] == expected_date, 'date must match directory date (YYYY-MM-DD)')
        require(isinstance(data['topics'], list) and bool(data['topics']), 'topics must be a nonempty array')
        for index, topic in enumerate(data['topics']):
            require(isinstance(topic, dict) and all(nonempty_string(topic.get(key)) for key in ('speaker', 'title')),
                    f'topic {index + 1}: missing speaker or title')
            if 'keyPoints' in topic:
                require(string_list(topic['keyPoints'], nonempty=True), f'topic {index + 1}: invalid keyPoints')
                require(all(nonempty_string(topic.get(key)) for key in ('context', 'quote')),
                        f'topic {index + 1}: missing context or quote')
                require(isinstance(topic.get('discussion'), str), f'topic {index + 1}: discussion must be a string')
            else:
                require(nonempty_string(topic.get('summary')), f'topic {index + 1}: missing historical summary')
        if 'highlights' in data:
            require(string_list(data['highlights']), 'highlights must be an array of nonempty strings')
    except ValueError as exc:
        errors.append(f'{p.relative_to(ROOT)}: invalid summary data {exc}')
for p in (ROOT / 'events').rglob('episode-publication.json'):
    try:
        cards_path = p.parent / 'quote-cards.json'
        cards = json.loads(cards_path.read_text()) if cards_path.is_file() else []
        validate_publication(json.loads(p.read_text()), len(cards))
    except (ValueError, TypeError) as exc:
        errors.append(f'{p.relative_to(ROOT)}: invalid publication data {exc}')
episodes = [p for p in (ROOT / 'events').glob('*/*-ep*') if p.is_dir()]
for d in episodes:
    date_prefix = d.name.split('-')[0]
    if date_prefix >= '20260207':
        if not (d / 'transcript.txt').is_file():
            errors.append(f'{d.relative_to(ROOT)}: missing transcript.txt')
    else:
        if not (d / 'transcript.txt').is_file() and not (d / 'quote-cards.json').is_file():
            errors.append(f'{d.relative_to(ROOT)}: missing transcript.txt or quote-cards.json')
if errors:
    raise SystemExit('\n'.join(errors))
print(f"Content check passed: {len(episodes)} episodes, {len(list(skills.glob('*/SKILL.md')))} skills.")
