"""Accepted Legacy family, role and color decisions for normal classification."""

from dataclasses import replace

from .branches import classify_branches as prior_classify
from .hogaak_colors import applies as is_hogaak_tempo, audit_color as old_hogaak_color
from .colors import audit

COLORS = {
    "": ("无色", "Colorless", "colorless"),
    "W": ("纯白", "Mono-White", "mono-white"),
    "U": ("纯蓝", "Mono-Blue", "mono-blue"),
    "B": ("纯黑", "Mono-Black", "mono-black"),
    "R": ("纯红", "Mono-Red", "mono-red"),
    "G": ("纯绿", "Mono-Green", "mono-green"),
    "WU": ("蓝白", "Azorius", "azorius"),
    "WB": ("白黑", "Orzhov", "orzhov"),
    "WR": ("红白", "Boros", "boros"),
    "WG": ("白绿", "Selesnya", "selesnya"),
    "UB": ("蓝黑", "Dimir", "dimir"),
    "UR": ("红蓝", "Izzet", "izzet"),
    "UG": ("蓝绿", "Simic", "simic"),
    "BR": ("红黑", "Rakdos", "rakdos"),
    "BG": ("黑绿", "Golgari", "golgari"),
    "RG": ("红绿", "Gruul", "gruul"),
    "WUB": ("艾斯波", "Esper", "esper"),
    "WUR": ("洁斯凯", "Jeskai", "jeskai"),
    "WUG": ("班特", "Bant", "bant"),
    "WBR": ("玛尔都", "Mardu", "mardu"),
    "WBG": ("阿布赞", "Abzan", "abzan"),
    "WRG": ("纳雅", "Naya", "naya"),
    "UBR": ("格利极", "Grixis", "grixis"),
    "UBG": ("苏勒台", "Sultai", "sultai"),
    "URG": ("铁木尔", "Temur", "temur"),
    "BRG": ("勇德", "Jund", "jund"),
    "WUBRG": ("五色", "Five-Color", "five-color"),
}
WORDS = dict(
    zip(
        "WUBRG",
        [
            ("白", "White"),
            ("蓝", "Blue"),
            ("黑", "Black"),
            ("红", "Red"),
            ("绿", "Green"),
        ],
    )
)
SUFFIX = {
    "azorius-control": ("控", "Control", "control"),
    "azorius-tempo": ("节奏", "Tempo", "tempo"),
    "azorius-stoneblade": ("曾哥剑", "Stoneblade", "stoneblade"),
    "azorius-energy": ("能量", "Energy", "energy"),
    "azorius-vial": ("精瓶", "Vial", "vial"),
    "boros-energy": ("能量", "Energy", "energy"),
    "boros-initiative": ("先制", "Initiative", "initiative"),
    "death-and-taxes-yorion-black-white": (
        "死税",
        "Death and Taxes",
        "death-and-taxes",
    ),
    "death-and-taxes-yorion-mono-white": ("死税", "Death and Taxes", "death-and-taxes"),
    "dimir-fantasticar": ("飞车", "Fantasticar", "fantasticar"),
    "dimir-tempo": ("节奏", "Tempo", "tempo"),
    "gwx-depths": ("深渊", "Depths", "depths"),
    "hogaak": ("霍佳葛", "Hogaak", "hogaak"),
    "izzet-tempo": ("节奏", "Tempo", "tempo"),
    "mono-black-midrange": ("快攻", "Aggro", "aggro"),
    "mono-black-reanimator": ("掘坟", "Reanimator", "reanimator"),
    "rakdos-reanimator": ("掘坟", "Reanimator", "reanimator"),
    "dimir-reanimator": ("掘坟", "Reanimator", "reanimator"),
    "painter-combo": ("画家", "Painter", "painter"),
    "ninjas": ("忍者", "Ninjas", "ninjas"),
    "selesnya-devoted-druid": ("缓伤", "Devoted Druid", "devoted-druid"),
    "mono-red-prison": ("锁", "Prison", "prison"),
    "mono-blue-tron": ("塔脉炉", "Tron", "tron"),
    "colorless-tron": ("塔脉炉", "Tron", "tron"),
    "blue-post": ("哨站", "Post", "post"),
    "green-post": ("哨站", "Post", "post"),
}
BASE_COLORS = {
    "azorius-control": "WU",
    "azorius-tempo": "WU",
    "azorius-stoneblade": "WU",
    "azorius-energy": "WU",
    "azorius-vial": "WU",
    "boros-energy": "WR",
    "boros-initiative": "WR",
    "dimir-fantasticar": "UB",
    "dimir-tempo": "UB",
    "izzet-tempo": "UR",
    "ninjas": "UB",
    "hogaak": "BG",
    "mono-red-prison": "R",
    "mono-blue-tron": "U",
    "colorless-tron": "",
    "blue-post": "U",
    "green-post": "G",
    "gwx-depths": "WG",
    "mono-black-midrange": "B",
    "mono-black-reanimator": "B",
    "rakdos-reanimator": "BR",
    "selesnya-devoted-druid": "WG",
    "death-and-taxes-yorion-black-white": "WB",
    "death-and-taxes-yorion-mono-white": "W",
    "dimir-reanimator": "UB",
    "painter-combo": "R",
}


def full_name(colors, zh, en, yorion=False):
    if len(colors) == 4:
        missing = next(c for c in "WUBRG" if c not in colors)
        a, b = WORDS[missing]
        return ("约力昂" if yorion else "") + zh + f"（无{a}）", (
            "Yorion " if yorion else ""
        ) + en + f" (Non-{b})"
    a, b, _ = COLORS[colors]
    return ("约力昂" if yorion else "") + a + zh, (
        "Yorion " if yorion else ""
    ) + b + " " + en


def remap(result, pid, en, sid=None, sname=None):
    """Keep match evidence aligned when a resolved identity is renamed/split."""
    old = result.archetype_id

    def match(m):
        return (
            replace(
                m,
                archetype_id=pid,
                archetype_name=en,
                subtype_id=sid,
                subtype_name=sname,
            )
            if m.archetype_id == old
            else m
        )

    return replace(
        result,
        archetype_id=pid,
        archetype_name=en,
        subtype_id=sid,
        subtype_name=sname,
        matched_rules=tuple(match(m) for m in result.matched_rules),
        top_priority_matches=tuple(match(m) for m in result.top_priority_matches),
        overridden_matches=tuple(match(m) for m in result.overridden_matches),
    )


def classify_with_review(rules, main, side):
    base = prior_classify(rules, main, side)
    info = {"path": "unchanged", "issues": []}
    if base.status != "classified":
        return base, info
    pid = base.archetype_id
    if (
        pid == "colorless-tron"
        and base.subtype_id == "colorless"
        and any(main.get(card, 0) + side.get(card, 0) for card in (
            "Portable Hole", "Perilous Snare", "Lich's Relic", "Mishra's Research Desk",
        ))
    ):
        # The Nexus audit has already proved the reviewed artifact-tool roles.
        # A second generic payment audit would count those same tools again.
        info.update(path="reviewed-colorless-tron-toolbox")
        return base, info
    if is_hogaak_tempo(base):
        # Mite is neutral even when another retained color table contains it.
        m = {n: q for n, q in main.items() if n != "Haywire Mite"}
        s = {n: q for n, q in side.items() if n != "Haywire Mite"}
        a = old_hogaak_color(rules, m, s)
        colors = set(a["colors"])
        # Latest Owner decision explicitly counts Silence + Forest support for
        # this Hogaak subtype, superseding the old free-Silence classification.
        forest = any(
            main.get(n, 0)
            for n in [
                "Bayou",
                "Forest",
                "Tropical Island",
                "Overgrown Tomb",
                "Breeding Pool",
            ]
        )
        if side.get("Reverent Silence", 0) and forest:
            colors.add("green")
        extra = colors - {"blue", "black"}
        suffix = "".join(
            c for c, k in [("w", "white"), ("r", "red"), ("g", "green")] if k in extra
        )
        label = "蓝黑霍佳葛" + (
            "（混"
            + "".join(
                t
                for t, k in [("白", "white"), ("红", "red"), ("绿", "green")]
                if k in extra
            )
            + "）"
            if extra
            else ""
        )
        sid = "hogaak" + ("-" + suffix if suffix else "")
        info.update(
            path="dimir-hogaak-subtype",
            colors=sorted(colors),
            issues=a["issues"],
            nameZh=label,
            nameEn="Dimir Hogaak"
            + (
                " ("
                + " and ".join(
                    t
                    for t, k in [("White", "white"), ("Red", "red"), ("Green", "green")]
                    if k in extra
                )
                + " Splash)"
                if extra
                else ""
            ),
        )
        return remap(base, "dimir-tempo", "Dimir Tempo", sid, label), info
    if pid == "dimir-tempo" and base.subtype_id == "dimir":
        info.update(
            path="ordinary-dimir-tempo", nameZh="普通蓝黑节奏", nameEn="Dimir Tempo"
        )
        return remap(base, pid, "Dimir Tempo", "dimir", "普通蓝黑节奏"), info
    if pid in {
        "dimir-erayo",
        "mono-black-saga-storm",
        "colorless-painter",
        "izzet-artifacts",
    }:
        zh = {
            "dimir-erayo": "蓝黑伟代",
            "mono-black-saga-storm": "纯黑克撒传风暴",
            "colorless-painter": "无色画家",
            "izzet-artifacts": "红蓝神器",
        }[pid]
        info.update(path="accepted-parent", nameZh=zh, nameEn=base.archetype_name)
        return remap(base, pid, base.archetype_name), info
    if pid == "mono-black-reanimator":
        # P3: color of the maindeck functional plan, not sideboard conversion
        # plans, defines this particular family. Reanimation targets stay neutral.
        main_audit = audit({"main": main, "side": {}, "candidate": {"parent": pid}})
        info["mainColorAudit"] = main_audit
        if not main_audit["issues"] and main_audit["colors"] == "B":
            info.update(
                path="mono-black-reanimator-main-plan",
                nameZh="黑掘坟",
                nameEn="Mono-Black Reanimator",
            )
            return remap(base, pid, "Mono-Black Reanimator"), info
    bean = (
        pid
        in {"bant-beanstalk", "multicolor-control", "domain-control", "sultai-midrange"}
        and main.get("Up the Beanstalk", 0) >= 3
        and main.get("Force of Will", 0) >= 2
        # An existing Beanstalk recognition already establishes its engine.
        # Enchantment-heavy lists need not use Brainstorm; keep that extra
        # signature when considering the broader control/midrange families.
        and (pid == "bant-beanstalk" or main.get("Brainstorm", 0) >= 2)
    )
    sewers = pid == "blue-artifacts"
    # Full known UW families and actual colored subtype paths are the accepted
    # policy surface. Unrelated pure/unknown families are not auto-relabelled.
    needs = (
        bean
        or sewers
        or pid
        in {
            "dimir-tempo",
            "azorius-control",
            "azorius-tempo",
            "azorius-stoneblade",
            "dimir-reanimator",
            "painter-combo",
        }
        or (pid in SUFFIX and base.subtype_id is not None)
    )
    if not needs:
        return base, info
    a = audit({"main": main, "side": side, "candidate": {"parent": pid}})
    info["colorAudit"] = a
    if a["issues"]:
        info.update(path="held-color-evidence", issues=a["issues"])
        return base, info
    cs = a["colors"]
    if bean or sewers:
        zh, en = full_name(
            cs,
            "豆茎控" if bean else "下水道",
            "Beanstalk Control" if bean else "Sewers",
            a["yorion"] if bean else False,
        )
        target = "multicolor-beanstalk-control" if bean else "sewers"
        sid = cs.lower() + ("-yorion" if bean and a["yorion"] else "")
        info.update(
            path="beanstalk-color-yorion" if bean else "sewers-colors",
            nameZh=zh,
            nameEn=en,
        )
        return remap(
            base, target, "Multi-Color Beanstalk Control" if bean else "Sewers", sid, zh
        ), info
    if pid not in SUFFIX:
        return base, info
    if cs == BASE_COLORS.get(pid):
        if pid == "dimir-tempo" and base.subtype_id is None:
            return remap(base, pid, "Dimir Tempo", "dimir", "普通蓝黑节奏"), info
        return base, info
    zh_suffix, en_suffix, id_suffix = SUFFIX[pid]
    # Three explicitly accepted former UW-control builds have UBW tempo engines.
    if (
        pid == "azorius-control"
        and cs == "WUB"
        and (
            main.get("Kaito, Bane of Nightmares", 0) >= 1
            and main.get("Orcish Bowmasters", 0) >= 2
            or main.get("Phelia, Exuberant Shepherd", 0)
            + main.get("Bilbo, Thief in the Night", 0)
            >= 2
            and main.get("Orcish Bowmasters", 0) >= 1
            or main.get("Phelia, Exuberant Shepherd", 0) >= 3
            and main.get("Stifle", 0) >= 3
        )
    ):
        zh_suffix, en_suffix, id_suffix = "节奏", "Tempo", "tempo"
    if zh_suffix == "控":
        zh_suffix = "控制"
    zh, en = full_name(cs, zh_suffix, en_suffix)
    prefix = (
        COLORS[cs][2]
        if cs in COLORS
        else "non-" + next(WORDS[c][1].lower() for c in "WUBRG" if c not in cs)
    )
    target = prefix + "-" + id_suffix
    info.update(path="full-color-parent", nameZh=zh, nameEn=en)
    return remap(base, target, en), info


def classify_accepted(rules, main, side):
    return classify_with_review(rules, main, side)[0]
