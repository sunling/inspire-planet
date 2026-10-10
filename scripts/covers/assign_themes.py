#!/usr/bin/env python3
"""Choose varied cover themes before review and persist them in Markdown."""
import argparse
import json
import random
import re
from pathlib import Path

THEMES = ('collage', 'pop', 'garden', 'blueprint', 'night')
BLOCK = re.compile(r'(<!-- cover-config -->\s*```json\s*\n)(.*?)(\n```)', re.S)


def assign(source, seed=None, reshuffle=False):
    text = source.read_text(encoding='utf-8')
    blocks = list(BLOCK.finditer(text))
    if not blocks:
        raise ValueError('no cover-config blocks found')
    configs = [json.loads(match[2]) for match in blocks]
    if not all(isinstance(cfg, dict) for cfg in configs):
        raise ValueError('each cover config must be an object')
    rng = random.Random(seed)
    # Balance use across the episode; preserve previously reviewed selections.
    counts = {theme: 0 for theme in THEMES}
    for cfg in configs:
        if not reshuffle and cfg.get('theme') in counts:
            counts[cfg['theme']] += 1
    previous = None
    for cfg in configs:
        if reshuffle or cfg.get('theme') in (None, 'random'):
            candidates = [theme for theme in THEMES if theme != previous]
            least = min(counts[theme] for theme in candidates)
            chosen = rng.choice([theme for theme in candidates if counts[theme] == least])
            cfg['theme'] = chosen
            counts[chosen] += 1
        previous = cfg.get('theme')
    replacements = iter(configs)
    updated = BLOCK.sub(lambda m: m[1] + json.dumps(next(replacements), ensure_ascii=False, indent=2) + m[3], text)
    if updated != text:
        source.write_text(updated, encoding='utf-8')
    return [cfg.get('theme') for cfg in configs]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--seed', type=int, help='reproduce a selection')
    parser.add_argument('--reshuffle', action='store_true', help='replace existing selections; review again before rendering')
    args = parser.parse_args()
    try:
        print(json.dumps(assign(args.source, args.seed, args.reshuffle), ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')
