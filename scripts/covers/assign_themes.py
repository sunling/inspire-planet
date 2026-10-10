#!/usr/bin/env python3
"""Choose varied cover themes before review and persist them in Markdown."""
import argparse
import json
import random
import re
from pathlib import Path

THEMES = ('collage', 'pop', 'garden', 'blueprint', 'night')
LAYOUTS = ('collage', 'editorial', 'signal')
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
    # Pick composition and palette independently, before review.
    for field, options in (('theme', THEMES), ('layout', LAYOUTS)):
        counts = {choice: 0 for choice in options}
        for cfg in configs:
            if not reshuffle and cfg.get(field) in counts:
                counts[cfg[field]] += 1
        previous = None
        for cfg in configs:
            if reshuffle or cfg.get(field) in (None, 'random'):
                candidates = [choice for choice in options if choice != previous]
                least = min(counts[choice] for choice in candidates)
                chosen = rng.choice([choice for choice in candidates if counts[choice] == least])
                cfg[field] = chosen
                counts[chosen] += 1
            previous = cfg.get(field)
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
        assign(args.source, args.seed, args.reshuffle)
        print(json.dumps([{'layout': cfg['layout'], 'theme': cfg['theme']} for cfg in [json.loads(m[2]) for m in BLOCK.finditer(args.source.read_text())]], ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')
