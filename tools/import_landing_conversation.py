"""Import already Owner-accepted conversation content into the private week source."""
import argparse
import json
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mtgmeta.mtgo import landing_editorial as editorial


def import_content(root, source):
    format_id = source['format']
    subject = editorial.build_top8_subject(root, format_id, source['week']['id'])
    if source['week'] != subject['week']:
        raise ValueError('Conversation week does not match current review subject')
    review = source['review']
    if review['top_copy']['reviewed'] is not True or review['features']['reviewed'] is not True:
        raise ValueError('Content must already have Owner acceptance')
    catalog = yaml.safe_load((root / editorial.DEFAULT_NAME_CATALOG).read_text(encoding='utf-8'))
    bindings = {key: subject[key] for key in ('source_event_ids','classifier_digest','selection_policy_digest','machine_fact_digest','link_catalog_digest')}
    if any(source['bindings'].get(key) != value for key, value in bindings.items()):
        raise ValueError('Accepted conversation references a different machine subject')
    bindings['bilingual_catalog_digest'] = editorial.name_catalog_binding_digest(catalog, review_schema_version='1.2.0', format_id=format_id)
    bindings['content_sha256'] = editorial.document_digest({key: source[key] for key in ('format','week','review')})
    document = {'schema_version':'1.2.0','source':'mtgo','format':format_id,'week':subject['week'],
                'bindings':bindings,'candidate_evidence':subject['candidate_evidence'],
                'all_top8':subject['all_top8'],'review':review,'known_archetype_ids':subject['known_archetype_ids']}
    editorial.validate_review_document(document,root/editorial.DEFAULT_REVIEW_SCHEMA)
    destination = root/'stats'/format_id/'mtgo/landing/review'/f"{subject['week']['id']}.yaml"
    editorial._write_yaml(destination,document)
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    args=parser.parse_args()
    print(import_content(ROOT,json.loads(args.input.read_text(encoding='utf-8'))))


if __name__=='__main__':
    main()
