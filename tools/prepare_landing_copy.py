"""Prepare Owner-authored copy for any format, without accepting or publishing it."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mtgmeta.mtgo.copy_links import prepare_copy
from mtgmeta.mtgo.publication import require_private_output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--card-catalog', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require_private_output(ROOT, args.output.resolve())
    source = json.loads(args.input.read_text(encoding='utf-8'))
    catalog = json.loads(args.card_catalog.read_text(encoding='utf-8'))
    items, questions = prepare_copy(source['items'], catalog, source.get('feature_aliases', {}), source.get('confirmed_card_names', []))
    result = {**source, 'items': items, 'ambiguous_card_mentions': questions}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'items': len(items), 'ambiguities': len(questions)}))


if __name__ == '__main__':
    main()
