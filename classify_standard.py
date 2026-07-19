import os
import json
import glob
import sys
from pathlib import Path

SHARED_SRC = Path(__file__).resolve().parent / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from mtgmeta.deck import count_card as shared_count_card
from mtgmeta.deck import deck_to_counts as shared_deck_to_counts
from mtgmeta.classifier import ClassificationResult, classify_counts
from mtgmeta.config import load_rule_set
from mtgmeta.legacy_rules import LegacyArchetypeRules, to_legacy_archetypes
from mtgmeta.rules import RuleSet

# === 配置 ===
RULES_FILE = "my_archetypes/standard.yaml"   # 版本化 Standard 规则库
DATA_DIR = "data/standard"                     # 你抓取的 standard 赛事数据
UNKNOWN_OUTPUT = "unknown_decks.txt"           # 归不了类的牌表导出到这里

# MTGO 版权改名卡 -> j6e 规则使用的标准卡名
# 仅覆盖 2025年末蜘蛛侠系列 ~ 2026年6月漫威系列 窗口期内高频改名卡
# 漫威系列发售后线上获得版权，新数据已用正名，此表把两个时期的数据归一
CARD_ALIASES = {
    "Kavaero, Mind-Bitten": "Superior Spider-Man",
    "Leyline Weaver": "Spider Manifestation",
}


def normalize_name(name):
    """Preserve the legacy public-output alias behavior during migration."""
    name = name.strip()
    return CARD_ALIASES.get(name, name)

# ---------- 1. 加载版本化 YAML，并适配现有调用方 ----------
def load_rules():
    rule_set = load_rule_set(RULES_FILE)
    archetypes = to_legacy_archetypes(rule_set)
    print(f"  已加载 {len(archetypes)} 条规则（来自 {RULES_FILE}）")
    return archetypes


# ---------- 2. 把一副牌整理成「卡名 -> 张数」的字典 ----------
def deck_to_counts(player):
    return shared_deck_to_counts(player)


# ---------- 3. 数某张卡在指定区域有几张 ----------
def count_card(card_name, zone, main_counts, side_counts):
    """根据 zone 决定在哪里数这张卡的张数"""
    return shared_count_card(card_name, zone, main_counts, side_counts)


# ---------- 4. 判断一张签名卡的条件是否满足 ----------
def signature_card_met(sig, main_counts, side_counts):
    name = sig["name"]
    zone = sig.get("zone", "any")
    actual = count_card(name, zone, main_counts, side_counts)
    if "exactCopies" in sig:
        return actual == sig["exactCopies"]
    if "minCopies" in sig:
        return actual >= sig["minCopies"]
    if "maxCopies" in sig:
        return actual <= sig["maxCopies"]
    return actual >= 1


class StandardClassificationConflict(RuntimeError):
    def __init__(self, result: ClassificationResult):
        self.result = result
        rule_ids = ", ".join(match.rule_id for match in result.conflict_matches)
        super().__init__(f"Standard classification conflict ({result.conflict_kind}): {rule_ids}")


class StandardInvalidDeck(ValueError):
    def __init__(self, result: ClassificationResult):
        self.result = result
        super().__init__("Standard deck classification input is invalid: " + "; ".join(result.errors))


def classify_standard_result(main_counts, side_counts, archetypes):
    """Return the shared result behind the temporary Standard compatibility API."""

    if isinstance(archetypes, LegacyArchetypeRules):
        rule_set = archetypes.rule_set
    elif isinstance(archetypes, RuleSet):
        rule_set = archetypes
    else:
        raise TypeError("shared Standard classification requires a RuleSet-backed rule collection")
    return classify_counts(rule_set, main_counts, side_counts)


def all_matching_archetype_names(main_counts, side_counts, archetypes):
    """Return every matched parent name while preserving legacy duplicate names."""

    if isinstance(archetypes, (LegacyArchetypeRules, RuleSet)):
        return [
            match.archetype_name
            for match in classify_standard_result(main_counts, side_counts, archetypes).matched_rules
        ]
    return [
        arch.get("name", "Unnamed")
        for arch in archetypes
        if arch.get("signatureCards")
        and all(signature_card_met(sig, main_counts, side_counts) for sig in arch["signatureCards"])
    ]



# ---------- 5. 尝试匹配一个套牌 ----------
def match_archetype(main_counts, side_counts, archetypes):
    if isinstance(archetypes, (LegacyArchetypeRules, RuleSet)):
        result = classify_standard_result(main_counts, side_counts, archetypes)
        if result.status == "classified":
            return result.archetype_name
        if result.status == "unknown":
            return None
        if result.status == "conflict":
            raise StandardClassificationConflict(result)
        if result.status == "invalid_deck":
            raise StandardInvalidDeck(result)
        raise RuntimeError(f"Unsupported Standard classification status: {result.status}")
    for arch in archetypes:
        sigs = arch.get("signatureCards", [])
        if sigs and all(signature_card_met(s, main_counts, side_counts) for s in sigs):
            return arch.get("name", "Unnamed")
    return None


# ---------- 6. 主流程 ----------
def main():
    archetypes = load_rules()

    counts = {}            # 每个分类结果的牌表数量
    total = 0
    unknown_decks = []     # 收集归不了类的牌表

    event_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    print(f"  找到 {len(event_files)} 个 standard 赛事文件\n")

    for event_path in event_files:
        with open(event_path, "r", encoding="utf-8") as f:
            event = json.load(f)
        for player in event.get("players", []):
            total += 1
            main_counts, side_counts = deck_to_counts(player)

            result = match_archetype(main_counts, side_counts, archetypes)
            if result is None:
                result = "Unknown"
                # 记录 Unknown 牌表（带张数，方便后续审查）
                main_list = sorted(f"{qty} {name}" for name, qty in main_counts.items())
                unknown_decks.append((event.get("description", "?"),
                                      player.get("player", "?"),
                                      main_list))

            counts[result] = counts.get(result, 0) + 1

    # ---------- 输出报告 ----------
    print("=" * 50)
    print(f"总牌表数: {total}")
    print("=" * 50)
    for name, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        pct = cnt / total * 100 if total else 0
        print(f"  {cnt:>4} ({pct:4.1f}%)  {name}")

    unknown_count = counts.get("Unknown", 0)
    matched = total - unknown_count
    print("=" * 50)
    if total:
        print(f"成功分类: {matched} / {total}  ({matched/total*100:.1f}%)")
    print(f"完全归不了类 (Unknown): {unknown_count}")

    # 导出 Unknown 牌表
    with open(UNKNOWN_OUTPUT, "w", encoding="utf-8") as f:
        for desc, pname, cards in unknown_decks:
            f.write(f"=== {desc} | {pname} ===\n")
            for card in cards:
                f.write(f"  {card}\n")
            f.write("\n")
    print(f"\nUnknown 牌表已导出到 {UNKNOWN_OUTPUT}")


if __name__ == "__main__":
    main()
