import pytest
from mtgmeta.mtgo.copy_links import link_card_names, prepare_copy, validate_card_tokens

CATALOG = {'Dread Return': {'zh_name': '颤栗再现'}, 'Consider': {'zh_name': '思虑'}, 'Return': {'zh_name': '返回'}}


def test_exact_names_preserve_prose_and_existing_tokens():
    text = '探子颤栗再现\nDread Return; [[card:Consider|思虑]]'
    linked, questions = link_card_names(text, CATALOG)
    assert linked == '探子[[card:Dread Return|颤栗再现]]\n[[card:Dread Return|Dread Return]]; [[card:Consider|思虑]]'
    assert not questions
    assert link_card_names(linked, CATALOG)[0] == linked


def test_manually_authored_card_tokens_must_match_canonical_localization():
    validate_card_tokens('[[card:Dread Return|颤栗再现]] and [[card:Consider|Consider]]', CATALOG)
    with pytest.raises(ValueError, match='name mismatch'):
        validate_card_tokens('[[card:Consider|颤栗再现]]', CATALOG)
    with pytest.raises(ValueError, match='absent from the canonical localization'):
        validate_card_tokens('[[card:Missing Card|不存在]]', CATALOG)


def test_ambiguous_and_embedded_english_not_guessed():
    linked, questions = link_card_names('Consider; Dread Returns; 重名', {**CATALOG, 'A': {'zh_name':'重名'}, 'B': {'zh_name':'重名'}})
    assert linked == 'Consider; Dread Returns; 重名'
    assert questions == ['Consider', '重名']


def test_english_card_names_adjacent_to_chinese_are_linked():
    catalog = {'Dread Return': {'zh_name': '颤栗再现'}}
    linked, questions = link_card_names('使用Dread Return和其他牌；Dread Returns不匹配', catalog)
    assert linked == '使用[[card:Dread Return|Dread Return]]和其他牌；Dread Returns不匹配'
    assert not questions


def test_feature_references_are_scope_local_and_unknown_rejected():
    items = [{'order': 1, 'text': {'zh':'第一行\n【F1】'}}]
    token = 'deck:' + 'a'*20
    output, _ = prepare_copy(items, {}, {'F1': token})
    assert output[0]['text']['zh'] == '第一行\n' + token
    assert items[0]['text']['zh'].endswith('【F1】')
    with pytest.raises(ValueError, match='Unknown feature'):
        prepare_copy(items, {}, {})


def test_body_repairs_wrapper_without_editing_prose_or_relinking_tokens():
    token = 'deck:' + 'a' * 20
    items = [{'order': 1, 'text': {'zh': f'颤栗再现：[令人意外] [{token}]',
                                  'en': f'Dread Return: [{token}]'}}]
    output, questions = prepare_copy(items, CATALOG, {})
    assert output[0]['text']['zh'] == f'[[card:Dread Return|颤栗再现]]：[令人意外] {token}'
    assert output[0]['text']['en'] == f'[[card:Dread Return|Dread Return]]: {token}'
    assert not questions
    assert prepare_copy(output, CATALOG, {}) == (output, [])


def test_same_card_front_face_is_not_ambiguous_and_context_stays_plain():
    catalog = {'Pompous Battlemage': {'zh_name': '浮夸战巫师'},
               'Pompous Battlemage // Improvised Act': {'zh_name': '浮夸战巫师'},
               'Exhume': {'zh_name': '掘坟'}, 'Poison Dart Frog': {'zh_name': '毒镖蛙'}}
    text = '苏勒台掘坟，毒镖蛙哥MacIsaac，浮夸战巫师，掘坟'
    linked, questions = link_card_names(text, catalog, non_card_phrases=['苏勒台掘坟', '毒镖蛙哥MacIsaac'])
    assert linked == ('苏勒台掘坟，毒镖蛙哥MacIsaac，[[card:Pompous Battlemage|浮夸战巫师]]，'
                      '[[card:Exhume|掘坟]]')
    assert not questions
