#!/usr/bin/env python3
"""Check the shared archive's local links, card JSON, skill paths and episode transcripts."""
from pathlib import Path
import json
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
errors = []
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
        assert isinstance(data, list)
        assert all(isinstance(row, dict) and set(row) == {'name', 'title', 'quote', 'detail', 'episode'} for row in data)
    except (ValueError, AssertionError) as exc:
        errors.append(f'{p.relative_to(ROOT)}: invalid card data {exc}')
skills = ROOT / '.agents/skills'
for p in skills.glob('*/SKILL.md'):
    text = p.read_text()
    if not text.startswith('---\n') or f'name: {p.parent.name}\n' not in text or '\ndescription: ' not in text:
        errors.append(f'{p.relative_to(ROOT)}: invalid skill metadata')
episodes = [p for p in (ROOT / 'events').glob('*/*-ep*') if p.is_dir()]
for d in episodes:
    if not (d / 'transcript.txt').is_file():
        errors.append(f'{d.relative_to(ROOT)}: missing transcript.txt')
if errors:
    raise SystemExit('\n'.join(errors))
print(f"Content check passed: {len(episodes)} episodes, {len(list(skills.glob('*/SKILL.md')))} skills.")
