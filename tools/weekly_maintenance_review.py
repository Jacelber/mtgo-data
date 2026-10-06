"""Present retained maintenance facts using the established weekly review shell."""
import json
from pathlib import Path


def render_review(material, *, kind, lookup=None, names=None):
    tools = Path(__file__).parent
    template = (tools / 'weekly_review_web.html').read_text(encoding='utf-8')
    # Reuse the pre-skill layout, table, search, reason cards and deck dialog.
    marker = '<script>\nconst D='
    if template.count(marker) != 1:
        raise ValueError('Weekly review shell changed; update its maintenance adapter')
    shell = template.split(marker, 1)[0]
    payload = json.dumps({'kind': kind, 'material': material,
                          'localization': lookup or {}, 'names': names or []}, ensure_ascii=False)
    shell = shell.replace('__REVIEW_DATA__', payload.replace('<', '\\u003c'))
    script = (tools / 'weekly_maintenance_review.js').read_text(encoding='utf-8')
    return shell + '<script>\n' + script + '\n</script></html>'
