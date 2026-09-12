import pytest
from mtgmeta.mtgo.copy_links import link_card_names, prepare_copy

CATALOG = {'Dread Return': {'zh_name': '颤栗再现'}, 'Consider': {'zh_name': '思虑'}, 'Return': {'zh_name': '返回'}}


def test_exact_names_preserve_prose_and_existing_tokens():
    text = '探子颤栗再现\nDread Return; [[card:Consider|思虑]]'
    linked, questions = link_card_names(text, CATALOG)
    assert linked == '探子[[card:Dread Return|颤栗再现]]\n[[card:Dread Return|Dread Return]]; [[card:Consider|思虑]]'
    assert not questions
    assert link_card_names(linked, CATALOG)[0] == linked


def test_ambiguous_and_embedded_english_not_guessed():
    linked, questions = link_card_names('Consider; Dread Returns; 重名', {**CATALOG, 'A': {'zh_name':'重名'}, 'B': {'zh_name':'重名'}})
    assert linked == 'Consider; Dread Returns; 重名'
    assert questions == ['Consider', '重名']


def test_feature_references_are_scope_local_and_unknown_rejected():
    items = [{'order': 1, 'text': {'zh':'第一行\n【F1】'}}]
    token = 'deck:' + 'a'*20
    output, _ = prepare_copy(items, {}, {'F1': token})
    assert output[0]['text']['zh'] == '第一行\n' + token
    assert items[0]['text']['zh'].endswith('【F1】')
    with pytest.raises(ValueError, match='Unknown feature'):
        prepare_copy(items, {}, {})
