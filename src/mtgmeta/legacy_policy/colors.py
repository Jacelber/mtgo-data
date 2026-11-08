"""Role-based color evidence for the accepted Legacy identity policy."""

import re, collections
from .card_data import shared_fact
ORDER = "WUBRG"
letterzh = dict(zip(ORDER, "白蓝黑红绿"))
guild = {
    "W": "纯白",
    "U": "纯蓝",
    "B": "纯黑",
    "R": "纯红",
    "G": "纯绿",
    "WU": "蓝白",
    "WB": "白黑",
    "WR": "红白",
    "WG": "白绿",
    "UB": "蓝黑",
    "UR": "红蓝",
    "UG": "蓝绿",
    "BR": "红黑",
    "BG": "黑绿",
    "RG": "红绿",
    "WUB": "艾斯波",
    "WUR": "洁斯凯",
    "WUG": "班特",
    "WBR": "玛尔都",
    "WBG": "阿布赞",
    "WRG": "纳雅",
    "UBR": "格利极",
    "UBG": "苏勒台",
    "URG": "铁木尔",
    "BRG": "勇德",
}


def ordered(cs):
    return "".join(c for c in ORDER if c in cs)


def colorname(cs):
    s = ordered(cs)
    if not s:
        return "无色"
    full = "".join(letterzh[c] for c in s)
    return (
        guild[s] + ("（" + full + "）" if len(s) == 3 else "")
        if s in guild
        else ("五色" if len(s) == 5 else "四色") + "（" + full + "）"
    )


def card_fact(n):
    return shared_fact(n)


def front(n):
    f = card_fact(n)
    return (
        {**f, **f.get("card_faces", [{}])[0]}
        if f.get("card_faces") and n != "Wear/Tear"
        else f
    )


def requirements(cost):
    fixed = set()
    hybrid = []
    for token in re.findall(r"\{([^}]+)\}", cost or ""):
        if token in ORDER:
            fixed.add(token)
        elif "/" in token:
            if "P" in token or "2" in token:
                continue
            cs = set(token.split("/")) & set(ORDER)
            if cs:
                hybrid.append(cs)
    return fixed, hybrid


def spellreq(n):
    f = front(n)
    if "Land" in f.get("type_line", "") and not f.get("mana_cost"):
        return set(), []
    if "mana_cost" in f:
        return requirements(f["mana_cost"])
    return set(), []


FREE = {
    "Haywire Mite": "Owner明确例外：Mite单独不计绿",
    "Faerie Macabre": "使用弃牌异能，不计黑",
    "Surgical Extraction": "已确认按免费工具使用，不计黑",
    "Nihil Spellbomb": "可选抽牌不单独计黑",
    "Mutagenic Growth": "已确认支付生命用途",
    "Gut Shot": "已确认支付生命用途",
    "Dismember": "已确认支付生命用途",
    "Phyrexian Metamorph": "已确认工具用途可支付生命",
    "Elvish Spirit Guide": "放逐产费，不因自身费用计绿",
    "Simian Spirit Guide": "放逐产费，不因自身费用计红",
}
TARGETS = {
    "Atraxa, Grand Unifier",
    "Archon of Cruelty",
    "Griselbrand",
    "Ashen Rider",
    "Serra's Emissary",
    "Raph & Mikey, Troublemakers",
    "Koma, World-Eater",
    "Borborygmos Enraged",
    "Sire of Insanity",
    "Ghalta, Stampede Tyrant",
    "Valgavoth, Terror Eater",
    "Abdel Adrian, Gorion's Ward",
    "Colossal Grave-Reaver",
}
TARGETS.add("Worldgorger Dragon")  # Reanimation-loop target, not a red casting plan.
ABILITIES = {
    "Ancestral Vision": ("U", "无普通法术力费用，使用蓝色延缓费用"),
    "Boseiju, Who Endures": ("G", "已确认魂力用途"),
    "Mishra's Research Desk": ("R", "已确认返场资源用途"),
    "Aether Spellbomb": ("U", "回手工具的启动费用"),
    "Pyrite Spellbomb": ("R", "伤害工具的启动费用"),
    "Otawara, Soaring City": ("U", "魂力回手用途"),
}


def audit(r):
    allcards = set(r["main"]) | set(r["side"])
    main = r["main"]
    side = r["side"]
    sources = {c: [] for c in ORDER}
    ignored = {}
    issues = []
    evidence = []
    # Printed production and MDFC sources come from the shared snapshot.
    for n in allcards:
        f = card_fact(n)
        produced = set(f.get("produced_mana", []) or [])
        if n in [
            "Lotus Petal",
            "Mox Opal",
            "Mox Diamond",
            "Giant's Boulder",
            "Spire of Industry",
            "Chromatic Star",
            "Chromatic Sphere",
        ]:
            produced = set(ORDER)
        if n == "Elvish Spirit Guide":
            produced = {"G"}
        if n == "Simian Spirit Guide":
            produced = {"R"}
        if n == "Chrome Mox":
            counter = collections.Counter()
            for other in allcards:
                of = front(other)
                if "Artifact" not in of.get("type_line", "") and "Land" not in of.get(
                    "type_line", ""
                ):
                    for c in set(of.get("colors", [])) & set(ORDER):
                        counter[c] += main.get(other, 0) + side.get(other, 0)
            produced = {c for c, q in counter.items() if q >= 2}
        for c in produced & set(ORDER):
            sources[c].append(n)
    req = []
    hybrid = []
    knowncore = set()
    for zone in ["main", "side"]:
        for n, q in r[zone].items():
            if n in FREE:
                ignored[n] = FREE[n]
                continue
            if n == "Chaos Defiler" and r["candidate"]["parent"] == "painter-combo":
                ignored[n] = (
                    "Owner P4：画家焊接用途不计色；不扩展到塔脉炉等已确认双用途家族"
                )
                continue
            reanimate = "reanimator" in r["candidate"]["parent"]
            if n == "Ashen Rider" and zone == "side" and not sources["W"]:
                ignored[n] = "无白色正常施放支持，保留备牌直接入场目标用途"
                continue
            if n in TARGETS and (
                reanimate
                or main.get("Show and Tell", 0) >= 3
                or main.get("Natural Order", 0) >= 3
                or main.get("Portent of Calamity", 0) >= 3
            ):
                ignored[n] = "沿用组合技直接入场目标用途，不按目标牌面计色"
                continue
            if (
                n
                in [
                    "Leyline of the Void",
                    "Mindbreak Trap",
                    "Ravenous Trap",
                    "Archive Trap",
                ]
                and zone == "side"
            ):
                ignored[n] = "沿用已确认免费备牌工具用途"
                continue
            f = front(n)
            if not f or "mana_cost" not in f:
                issues.append(n + "：牌面缺失")
                continue
            cs, hy = spellreq(n)
            if n in ABILITIES:
                ac, why = ABILITIES[n]
                cs |= set(ac)
            if n == "Force of Vigor":
                # Do not infer paid green from a free sideboard card alone.
                independent = any(
                    c != n and "G" in spellreq(c)[0] and c not in set(FREE) | TARGETS
                    for c in main
                )
                if not independent:
                    ignored[n] = "无独立主牌绿色施放计划，沿用免费反仇恨用途"
                    continue
            for c in cs:
                if sources[c]:
                    req.append(
                        {
                            "card": n,
                            "zone": zone,
                            "quantity": q,
                            "color": c,
                            "sources": sources[c],
                            "use": ABILITIES[n][1] if n in ABILITIES else "正常施放",
                        }
                    )
                    knowncore.add(c)
                else:
                    issues.append(n + "：" + c + "费用但未找到法术力支持")
            for options in hy:
                hybrid.append((n, zone, q, options))
    # A hybrid symbol does not add every printed color. Prefer colors independently required.
    for n, zone, q, options in hybrid:
        usable = options & knowncore
        if usable:
            c = next(c for c in ORDER if c in usable)
        else:
            supported = {c for c in options if sources[c]}
            if len(supported) == 1:
                c = next(iter(supported))
            elif supported:
                # Common color among all symbols can pay the whole card (e.g. Guildpact).
                allhy = spellreq(n)[1]
                common = set.intersection(*allhy) if allhy else set()
                choices = common & supported
                if len(choices) == 1:
                    c = next(iter(choices))
                else:
                    issues.append(n + "：混血支付色需核实")
                    continue
            else:
                issues.append(n + "：混血费用无支付支持")
                continue
        req.append(
            {
                "card": n,
                "zone": zone,
                "quantity": q,
                "color": c,
                "sources": sources[c],
                "use": "混血费用可用该色支付，不展开全部牌面颜色",
            }
        )
    seen = set()
    for e in req:
        key = (e["card"], e["zone"], e["color"])
        if key not in seen:
            evidence.append(e)
            seen.add(key)
    cs = {e["color"] for e in evidence}
    return {
        "colors": ordered(cs),
        "colorName": colorname(cs),
        "evidence": evidence,
        "sources": sources,
        "excluded": ignored,
        "issues": sorted(set(issues)),
        "yorion": bool(side.get("Yorion, Sky Nomad")),
    }
