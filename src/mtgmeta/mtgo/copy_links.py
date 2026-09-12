"""Link exact card names in owner prose without changing the displayed text."""
from collections import defaultdict
import re

TOKEN = re.compile(r"\[\[card:[^\[\]\r\n]+\]\]|deck:[0-9a-f]{20}")


def link_card_names(text, catalog, confirmed_names=()):
    """Return internal tokens and ambiguous names; preserve existing tokens.

    Catalog is the shared bilingual card lookup, not a format whitelist.
    Single-word English names require explicit context to avoid words such as
    Consider or Island becoming links accidentally.
    """
    identities = defaultdict(set)
    for english, entry in catalog.items():
        identities[english].add(english)
        chinese = entry.get('zh_name')
        if chinese:
            identities[chinese].add(english)
    if not identities:
        return text, []
    names = sorted(identities, key=lambda n: (-len(n), n))
    pattern = re.compile('|'.join(re.escape(n) for n in names))
    ambiguous = set()

    def replace_segment(segment):
        def replace(match):
            name = match.group()
            is_chinese = bool(re.search(r'[\u3400-\u9fff]', name))
            if not is_chinese:
                before = segment[match.start()-1:match.start()] if match.start() else ''
                after = segment[match.end():match.end()+1]
                if (before and (before.isalnum() or before == '_')) or (after and (after.isalnum() or after == '_')):
                    return name
            if len(identities[name]) != 1 or (not is_chinese and ' ' not in name and name not in confirmed_names):
                ambiguous.add(name)
                return name
            english = next(iter(identities[name]))
            return f'[[card:{english}|{name}]]'
        return pattern.sub(replace, segment)

    output, offset = [], 0
    for match in TOKEN.finditer(text):
        output.extend([replace_segment(text[offset:match.start()]), match.group()])
        offset = match.end()
    output.append(replace_segment(text[offset:]))
    return ''.join(output), sorted(ambiguous)


def prepare_copy(items, catalog, feature_aliases, confirmed_names=()):
    """Prepare numbered bilingual items; aliases belong to one caller scope."""
    output, questions = [], []
    for item in items:
        texts = {}
        for language, text in item['text'].items():
            def feature(match):
                alias = match[1]
                token = feature_aliases.get(alias)
                if not token or not re.fullmatch(r'deck:[0-9a-f]{20}', token):
                    raise ValueError(f'Unknown feature reference: {alias}')
                return token
            text = re.sub(r'【(F[1-9][0-9]*)】', feature, text)
            texts[language], ambiguous = link_card_names(text, catalog, confirmed_names)
            questions.extend({'order': item['order'], 'language': language, 'name': name} for name in ambiguous)
        output.append({**item, 'text': texts})
    return output, questions
