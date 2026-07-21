"""Deterministic parsing of stored Melee raw-response snapshots.

P5-04 converts already archived HTML or JSON responses into immutable
source-level records.  It deliberately does not join participants across
resources or assign normalized stages, formats, result types, statistical
eligibility, or archetypes.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


SUPPORTED_RESOURCE_TYPES = frozenset({"tournament", "standings", "matches", "decklist"})
SUPPORTED_CONTENT_TYPES = frozenset({"html", "json"})
MAX_SOURCE_BYTES = 32 * 1024 * 1024


class MeleeSourceParseError(ValueError):
    """Raised when a stored source response cannot be parsed safely."""


@dataclass(frozen=True)
class SourceArtifact:
    request_id: str
    resource_type: str
    page: int
    url: str
    path: str
    expected_content_type: str
    sha256: str
    bytes: int
    method: str | None = None
    request_body_sha256: str | None = None
    source_round_id: str | None = None
    source_participant_id: str | None = None
    source_decklist_id: str | None = None


@dataclass(frozen=True)
class SourceTournament:
    source_event_id: str
    name: str
    start_text: str | None
    end_text: str | None


@dataclass(frozen=True)
class SourceStanding:
    source_standing_id: str
    source_participant_id: str
    display_name: str
    rank: int | None
    match_points: int | None
    record_text: str | None
    status_text: str | None


@dataclass(frozen=True)
class SourceDecklistReference:
    source_decklist_id: str
    source_participant_id: str
    url: str


@dataclass(frozen=True)
class SourceRound:
    source_round_id: str
    label: str
    number: int | None


@dataclass(frozen=True)
class SourceCompetitor:
    source_participant_id: str
    outcome_text: str | None
    match_points: int | None


@dataclass(frozen=True)
class SourceMatch:
    source_match_id: str
    source_round_id: str
    competitor_source_ids: tuple[str, ...]
    competitor_results: tuple[SourceCompetitor, ...]
    result_text: str | None
    status_text: str | None
    table_number: int | None


@dataclass(frozen=True)
class SourceCard:
    name: str
    quantity: int
    section_text: str


@dataclass(frozen=True)
class SourceDecklist:
    source_decklist_id: str
    source_participant_id: str
    format_text: str | None
    cards: tuple[SourceCard, ...]


@dataclass(frozen=True)
class ParsedSourcePage:
    artifact: SourceArtifact
    tournament: SourceTournament | None = None
    standings: tuple[SourceStanding, ...] = ()
    decklist_references: tuple[SourceDecklistReference, ...] = ()
    rounds: tuple[SourceRound, ...] = ()
    matches: tuple[SourceMatch, ...] = ()
    decklists: tuple[SourceDecklist, ...] = ()


@dataclass(frozen=True)
class ParsedMeleeSnapshot:
    event_id: str
    event_url: str
    fetched_at: str
    pages: tuple[ParsedSourcePage, ...]


class _JsonScriptCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._capturing = False
        self._buffer: list[str] = []
        self.candidates: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script" or self._capturing:
            return
        attributes = {key.lower(): value for key, value in attrs}
        if (attributes.get("type") or "").lower() == "application/json":
            self._capturing = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._capturing:
            self.candidates.append("".join(self._buffer))
            self._capturing = False
            self._buffer = []


class _RealTournamentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_title = False
        self._title: list[str] = []
        self.start_text: str | None = None
        self.rounds: dict[str, tuple[str, bool]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value for key, value in attrs}
        if tag.casefold() == "title":
            self._in_title = True
        if self.start_text is None and values.get("data-toggle") == "datetime" and values.get("data-value"):
            self.start_text = values["data-value"].strip()
        if tag.casefold() != "button" or "round-selector" not in set((values.get("class") or "").split()):
            return
        round_id = values.get("data-id") or ""
        label = (values.get("data-name") or "").strip()
        if not round_id.isdigit() or not label:
            return
        completed = (values.get("data-is-completed") or "").casefold() == "true"
        previous = self.rounds.get(round_id)
        self.rounds[round_id] = (label, completed or bool(previous and previous[1]))

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self._in_title = False

    @property
    def name(self) -> str:
        title = "".join(self._title).strip()
        return title.removesuffix(" | Melee").strip()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MeleeSourceParseError(f"source JSON contains duplicate key {key!r}")
        result[key] = value
    return result


def _decode_json(text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except MeleeSourceParseError:
        raise
    except json.JSONDecodeError as exc:
        raise MeleeSourceParseError(f"{label}: invalid JSON at line {exc.lineno} column {exc.colno}") from exc
    if not isinstance(value, dict):
        raise MeleeSourceParseError(f"{label}: source payload must be a mapping")
    return value


def _decode_payload(body: bytes, content_type: str, label: str) -> dict[str, Any]:
    if len(body) > MAX_SOURCE_BYTES:
        raise MeleeSourceParseError(f"{label}: source response exceeds the parser size limit")
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise MeleeSourceParseError(f"{label}: source response is not valid UTF-8") from exc
    if content_type == "json":
        return _decode_json(text, label)
    if content_type != "html":
        raise MeleeSourceParseError(f"{label}: unsupported content type {content_type!r}")
    collector = _JsonScriptCollector()
    try:
        collector.feed(text)
        collector.close()
    except Exception as exc:
        raise MeleeSourceParseError(f"{label}: malformed HTML") from exc
    payloads: list[dict[str, Any]] = []
    for index, candidate in enumerate(collector.candidates):
        try:
            decoded = _decode_json(candidate, f"{label} script[{index}]")
        except MeleeSourceParseError:
            continue
        if decoded.get("resource_type") in SUPPORTED_RESOURCE_TYPES:
            payloads.append(decoded)
    if len(payloads) != 1:
        raise MeleeSourceParseError(
            f"{label}: expected exactly one supported application/json source payload"
        )
    return payloads[0]


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise MeleeSourceParseError(f"{path}: expected a mapping")
    return value


def _fields(
    value: Any,
    path: str,
    required: set[str],
    optional: set[str] = frozenset(),
) -> Mapping[str, Any]:
    data = _mapping(value, path)
    missing = required - set(data)
    unsupported = set(data) - required - optional
    if missing:
        raise MeleeSourceParseError(f"{path}: missing required fields {sorted(missing)}")
    if unsupported:
        raise MeleeSourceParseError(f"{path}: unsupported fields {sorted(unsupported)}")
    return data


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise MeleeSourceParseError(f"{path}: expected a list")
    return value


def _string(value: Any, path: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise MeleeSourceParseError(f"{path}: expected a non-empty string")
    return value.strip()


def _integer(value: Any, path: str, *, optional: bool = False, minimum: int = 0) -> int | None:
    if value is None and optional:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise MeleeSourceParseError(f"{path}: expected an integer >= {minimum}")
    return value


def _unique(records: Iterable[Any], attribute: str, path: str) -> tuple[Any, ...]:
    values = tuple(records)
    identities = [getattr(record, attribute) for record in values]
    if len(identities) != len(set(identities)):
        raise MeleeSourceParseError(f"{path}: duplicate source IDs are not allowed")
    return values


def _parse_tournament(value: Any, path: str) -> SourceTournament:
    data = _fields(value, path, {"source_event_id", "name"}, {"start_text", "end_text"})
    return SourceTournament(
        source_event_id=_string(data.get("source_event_id"), f"{path}.source_event_id"),
        name=_string(data.get("name"), f"{path}.name"),
        start_text=_string(data.get("start_text"), f"{path}.start_text", optional=True),
        end_text=_string(data.get("end_text"), f"{path}.end_text", optional=True),
    )


def _parse_standings(value: Any, path: str) -> tuple[SourceStanding, ...]:
    records = []
    for index, item in enumerate(_list(value, path)):
        item_path = f"{path}[{index}]"
        data = _fields(
            item,
            item_path,
            {"source_standing_id", "source_participant_id", "display_name"},
            {"rank", "match_points", "record_text", "status_text"},
        )
        records.append(
            SourceStanding(
                source_standing_id=_string(data.get("source_standing_id"), f"{item_path}.source_standing_id"),
                source_participant_id=_string(data.get("source_participant_id"), f"{item_path}.source_participant_id"),
                display_name=_string(data.get("display_name"), f"{item_path}.display_name"),
                rank=_integer(data.get("rank"), f"{item_path}.rank", optional=True, minimum=1),
                match_points=_integer(data.get("match_points"), f"{item_path}.match_points", optional=True),
                record_text=_string(data.get("record_text"), f"{item_path}.record_text", optional=True),
                status_text=_string(data.get("status_text"), f"{item_path}.status_text", optional=True),
            )
        )
    return _unique(records, "source_standing_id", path)


def _parse_decklist_references(value: Any, path: str) -> tuple[SourceDecklistReference, ...]:
    records = []
    for index, item in enumerate(_list(value, path)):
        item_path = f"{path}[{index}]"
        data = _fields(
            item,
            item_path,
            {"source_decklist_id", "source_participant_id", "url"},
        )
        records.append(
            SourceDecklistReference(
                source_decklist_id=_string(data.get("source_decklist_id"), f"{item_path}.source_decklist_id"),
                source_participant_id=_string(data.get("source_participant_id"), f"{item_path}.source_participant_id"),
                url=_string(data.get("url"), f"{item_path}.url"),
            )
        )
    return _unique(records, "source_decklist_id", path)


def _parse_rounds(value: Any, path: str) -> tuple[SourceRound, ...]:
    records = []
    for index, item in enumerate(_list(value, path)):
        item_path = f"{path}[{index}]"
        data = _fields(item, item_path, {"source_round_id", "label"}, {"number"})
        records.append(
            SourceRound(
                source_round_id=_string(data.get("source_round_id"), f"{item_path}.source_round_id"),
                label=_string(data.get("label"), f"{item_path}.label"),
                number=_integer(data.get("number"), f"{item_path}.number", optional=True, minimum=1),
            )
        )
    return _unique(records, "source_round_id", path)


def _parse_matches(value: Any, path: str) -> tuple[SourceMatch, ...]:
    records = []
    for index, item in enumerate(_list(value, path)):
        item_path = f"{path}[{index}]"
        data = _fields(
            item,
            item_path,
            {"source_match_id", "source_round_id"},
            {"competitors", "competitor_source_ids", "result_text", "status_text", "table_number"},
        )
        if ("competitors" in data) == ("competitor_source_ids" in data):
            raise MeleeSourceParseError(
                f"{item_path}: expected exactly one of competitors or competitor_source_ids"
            )
        competitors: tuple[SourceCompetitor, ...]
        if "competitors" in data:
            parsed_competitors = []
            for position, value in enumerate(_list(data["competitors"], f"{item_path}.competitors")):
                competitor_path = f"{item_path}.competitors[{position}]"
                competitor = _fields(
                    value,
                    competitor_path,
                    {"source_participant_id"},
                    {"outcome_text", "match_points"},
                )
                parsed_competitors.append(
                    SourceCompetitor(
                        source_participant_id=_string(
                            competitor.get("source_participant_id"),
                            f"{competitor_path}.source_participant_id",
                        ),
                        outcome_text=_string(
                            competitor.get("outcome_text"),
                            f"{competitor_path}.outcome_text",
                            optional=True,
                        ),
                        match_points=_integer(
                            competitor.get("match_points"),
                            f"{competitor_path}.match_points",
                            optional=True,
                        ),
                    )
                )
            competitors = tuple(parsed_competitors)
        else:
            competitors = tuple(
                SourceCompetitor(
                    source_participant_id=_string(
                        source_id,
                        f"{item_path}.competitor_source_ids[{position}]",
                    ),
                    outcome_text=None,
                    match_points=None,
                )
                for position, source_id in enumerate(
                    _list(data["competitor_source_ids"], f"{item_path}.competitor_source_ids")
                )
            )
        competitor_ids = tuple(item.source_participant_id for item in competitors)
        if not 1 <= len(competitors) <= 2 or len(competitor_ids) != len(set(competitor_ids)):
            raise MeleeSourceParseError(
                f"{item_path}.competitors: expected one or two distinct source IDs"
            )
        records.append(
            SourceMatch(
                source_match_id=_string(data.get("source_match_id"), f"{item_path}.source_match_id"),
                source_round_id=_string(data.get("source_round_id"), f"{item_path}.source_round_id"),
                competitor_source_ids=competitor_ids,
                competitor_results=competitors,
                result_text=_string(data.get("result_text"), f"{item_path}.result_text", optional=True),
                status_text=_string(data.get("status_text"), f"{item_path}.status_text", optional=True),
                table_number=_integer(data.get("table_number"), f"{item_path}.table_number", optional=True, minimum=1),
            )
        )
    return _unique(records, "source_match_id", path)


def _parse_cards(value: Any, path: str) -> tuple[SourceCard, ...]:
    cards = []
    for index, item in enumerate(_list(value, path)):
        item_path = f"{path}[{index}]"
        data = _fields(item, item_path, {"name", "quantity", "section_text"})
        cards.append(
            SourceCard(
                name=_string(data.get("name"), f"{item_path}.name"),
                quantity=_integer(data.get("quantity"), f"{item_path}.quantity", minimum=1),
                section_text=_string(data.get("section_text"), f"{item_path}.section_text"),
            )
        )
    return tuple(cards)


def _parse_decklist(value: Any, path: str) -> SourceDecklist:
    data = _fields(
        value,
        path,
        {"source_decklist_id", "source_participant_id", "cards"},
        {"format_text"},
    )
    return SourceDecklist(
        source_decklist_id=_string(data.get("source_decklist_id"), f"{path}.source_decklist_id"),
        source_participant_id=_string(data.get("source_participant_id"), f"{path}.source_participant_id"),
        format_text=_string(data.get("format_text"), f"{path}.format_text", optional=True),
        cards=_parse_cards(data.get("cards"), f"{path}.cards"),
    )


def _real_tournament(body: bytes, artifact: SourceArtifact) -> ParsedSourcePage:
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise MeleeSourceParseError(f"{artifact.path}: source response is not valid UTF-8") from exc
    parser = _RealTournamentParser()
    parser.feed(text)
    parser.close()
    event_id = artifact.url.rstrip("/").rsplit("/", 1)[-1]
    if not event_id.isdigit() or not parser.name:
        raise MeleeSourceParseError(f"{artifact.path}: real tournament metadata is incomplete")
    rounds = []
    for round_id, (label, completed) in parser.rounds.items():
        if not completed:
            continue
        parts = label.casefold().split()
        number = int(parts[1]) if len(parts) == 2 and parts[0] == "round" and parts[1].isdigit() else None
        rounds.append(SourceRound(round_id, label, number))
    if not rounds:
        raise MeleeSourceParseError(f"{artifact.path}: no completed rounds were found")
    return ParsedSourcePage(
        artifact=artifact,
        tournament=SourceTournament(event_id, parser.name, parser.start_text, None),
        rounds=tuple(rounds),
    )


def _real_player(team: Any, path: str) -> tuple[str, str, str | None]:
    team_data = _mapping(team, path)
    players = _list(team_data.get("Players"), f"{path}.Players")
    if len(players) != 1:
        raise MeleeSourceParseError(f"{path}.Players: expected one individual competitor")
    player = _mapping(players[0], f"{path}.Players[0]")
    participant_id = str(player.get("ID") or "")
    display_name = str(player.get("DisplayName") or "").strip()
    if not participant_id.isdigit() or not display_name:
        raise MeleeSourceParseError(f"{path}.Players[0]: participant identity is incomplete")
    status_value = team_data.get("StatusDescription")
    status = str(status_value).strip() if status_value is not None and str(status_value).strip() else None
    return participant_id, display_name, status


def _real_standings(payload: Mapping[str, Any], artifact: SourceArtifact) -> ParsedSourcePage:
    rows = _list(payload.get("data"), f"{artifact.path}.data")
    standings: list[SourceStanding] = []
    references: list[SourceDecklistReference] = []
    for index, value in enumerate(rows):
        path = f"{artifact.path}.data[{index}]"
        row = _mapping(value, path)
        participant_id, display_name, status = _real_player(row.get("Team"), f"{path}.Team")
        standing_id = str(row.get("ID") or "")
        if not standing_id:
            raise MeleeSourceParseError(f"{path}.ID: standing identity is missing")
        rank = row.get("Rank")
        points = row.get("Points")
        standings.append(SourceStanding(
            source_standing_id=standing_id,
            source_participant_id=participant_id,
            display_name=display_name,
            rank=rank if isinstance(rank, int) and rank >= 1 else None,
            match_points=points if isinstance(points, int) and points >= 0 else None,
            record_text=str(row.get("MatchRecord")).strip() if row.get("MatchRecord") else None,
            status_text=status,
        ))
        decklist_values = row.get("Decklists") or []
        for position, item in enumerate(_list(decklist_values, f"{path}.Decklists")):
            reference = _mapping(item, f"{path}.Decklists[{position}]")
            decklist_id = str(reference.get("DecklistId") or "")
            owner_id = str(reference.get("PlayerId") or "")
            if not decklist_id or owner_id != participant_id:
                raise MeleeSourceParseError(f"{path}.Decklists[{position}]: decklist identity is inconsistent")
            references.append(SourceDecklistReference(
                decklist_id, participant_id,
                f"https://melee.gg/Decklist/GetDecklistDetails?id={decklist_id}",
            ))
    return ParsedSourcePage(
        artifact=artifact,
        standings=_unique(standings, "source_standing_id", artifact.path),
        decklist_references=_unique(references, "source_decklist_id", artifact.path),
    )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _real_matches(payload: Mapping[str, Any], artifact: SourceArtifact) -> ParsedSourcePage:
    if artifact.source_round_id is None:
        raise MeleeSourceParseError(f"{artifact.path}: match response lacks source_round_id context")
    matches: list[SourceMatch] = []
    for index, value in enumerate(_list(payload.get("data"), f"{artifact.path}.data")):
        path = f"{artifact.path}.data[{index}]"
        row = _mapping(value, path)
        match_id = str(row.get("Guid") or "")
        row_round_id = str(row.get("RoundId") or "")
        if not match_id or row_round_id != artifact.source_round_id:
            raise MeleeSourceParseError(f"{path}: match or round identity is inconsistent")
        competitors_raw = _list(row.get("Competitors") or [], f"{path}.Competitors")
        competitors: list[tuple[str, int, int]] = []
        for position, raw in enumerate(competitors_raw):
            competitor = _mapping(raw, f"{path}.Competitors[{position}]")
            participant_id, _display_name, _status = _real_player(
                competitor.get("Team"), f"{path}.Competitors[{position}].Team"
            )
            wins = competitor.get("GameWins")
            byes = competitor.get("GameByes")
            competitors.append((
                participant_id,
                wins if isinstance(wins, int) and wins >= 0 else 0,
                byes if isinstance(byes, int) and byes >= 0 else 0,
            ))
        if not 1 <= len(competitors) <= 2 or len({item[0] for item in competitors}) != len(competitors):
            raise MeleeSourceParseError(f"{path}.Competitors: expected one or two distinct participants")
        has_result = row.get("HasResult") is True
        bye_reason = _optional_text(row.get("ByeReasonDescription"))
        loss_reason = _optional_text(row.get("LossReasonDescription"))
        status = bye_reason or loss_reason
        results: list[SourceCompetitor] = []
        if len(competitors) == 1 and (has_result or bye_reason or competitors[0][2] > 0):
            qualified = (bye_reason or "").casefold() == "qualified"
            outcome = "Qualified" if qualified else "Bye"
            results.append(SourceCompetitor(competitors[0][0], outcome, 3))
            status = outcome
        elif len(competitors) == 2 and has_result:
            first_wins, second_wins = competitors[0][1], competitors[1][1]
            game_draws = row.get("GameDraws")
            intentional_draw = first_wins == second_wins == 0 and game_draws == 3
            if first_wins == second_wins:
                outcomes = ("Draw", "Draw")
                points = (1, 1)
            elif first_wins > second_wins:
                outcomes = ("Win", "Loss")
                points = (3, 0)
            else:
                outcomes = ("Loss", "Win")
                points = (0, 3)
            results.extend(
                SourceCompetitor(competitor[0], outcome, point)
                for competitor, outcome, point in zip(competitors, outcomes, points, strict=True)
            )
            if intentional_draw:
                status = "Intentional Draw"
        else:
            results.extend(SourceCompetitor(item[0], None, None) for item in competitors)
        table = row.get("TableNumber")
        matches.append(SourceMatch(
            source_match_id=match_id,
            source_round_id=row_round_id,
            competitor_source_ids=tuple(item.source_participant_id for item in results),
            competitor_results=tuple(results),
            result_text=_optional_text(row.get("ResultString")),
            status_text=status,
            table_number=table if isinstance(table, int) and table >= 1 else None,
        ))
    return ParsedSourcePage(artifact=artifact, matches=_unique(matches, "source_match_id", artifact.path))


def _real_decklist(payload: Mapping[str, Any], artifact: SourceArtifact) -> ParsedSourcePage:
    if artifact.source_participant_id is None or artifact.source_decklist_id is None:
        raise MeleeSourceParseError(f"{artifact.path}: decklist response lacks manifest owner context")
    payload_id = str(payload.get("Guid") or "")
    if payload_id.casefold() != artifact.source_decklist_id.casefold():
        raise MeleeSourceParseError(f"{artifact.path}: decklist identity does not match manifest")
    cards = []
    section_names = {0: "Main Deck", 2: "Commander", 3: "Commander", 99: "Sideboard"}
    for index, value in enumerate(_list(payload.get("Records"), f"{artifact.path}.Records")):
        path = f"{artifact.path}.Records[{index}]"
        record = _mapping(value, path)
        section = record.get("c")
        if section not in section_names:
            continue
        name = record.get("n")
        quantity = record.get("q")
        cards.append(SourceCard(
            name=_string(name, f"{path}.n"),
            quantity=_integer(quantity, f"{path}.q", minimum=1),
            section_text=section_names[section],
        ))
    if not cards:
        raise MeleeSourceParseError(f"{artifact.path}: decklist contains no recognized cards")
    return ParsedSourcePage(artifact=artifact, decklists=(SourceDecklist(
        source_decklist_id=artifact.source_decklist_id,
        source_participant_id=artifact.source_participant_id,
        format_text=_optional_text(payload.get("FormatName")),
        cards=tuple(cards),
    ),))


def parse_source_response(body: bytes, artifact: SourceArtifact) -> ParsedSourcePage:
    """Parse one verified source response without applying normalized semantics."""

    if artifact.resource_type not in SUPPORTED_RESOURCE_TYPES:
        raise MeleeSourceParseError(f"{artifact.path}: unsupported resource type {artifact.resource_type!r}")
    if artifact.expected_content_type not in SUPPORTED_CONTENT_TYPES:
        raise MeleeSourceParseError(
            f"{artifact.path}: unsupported content type {artifact.expected_content_type!r}"
        )
    if artifact.resource_type == "tournament" and artifact.expected_content_type == "html":
        try:
            payload = _decode_payload(body, artifact.expected_content_type, artifact.path)
        except MeleeSourceParseError as exc:
            if "expected exactly one supported" not in str(exc):
                raise
            collector = _JsonScriptCollector()
            collector.feed(body.decode("utf-8-sig"))
            collector.close()
            supported = 0
            for candidate in collector.candidates:
                try:
                    decoded = _decode_json(candidate, artifact.path)
                except MeleeSourceParseError:
                    continue
                supported += decoded.get("resource_type") in SUPPORTED_RESOURCE_TYPES
            if supported:
                raise
            return _real_tournament(body, artifact)
    else:
        payload = _decode_payload(body, artifact.expected_content_type, artifact.path)
    if "resource_type" not in payload:
        if artifact.resource_type == "standings":
            return _real_standings(payload, artifact)
        if artifact.resource_type == "matches":
            return _real_matches(payload, artifact)
        if artifact.resource_type == "decklist":
            return _real_decklist(payload, artifact)
        raise MeleeSourceParseError(f"{artifact.path}: real source payload is not supported")
    if payload.get("resource_type") != artifact.resource_type:
        raise MeleeSourceParseError(f"{artifact.path}: payload resource type does not match manifest")
    if artifact.resource_type == "tournament":
        payload = _fields(
            payload,
            artifact.path,
            {"resource_type", "tournament"},
            {"standings", "decklist_references", "rounds", "matches"},
        )
        tournament = _parse_tournament(payload.get("tournament"), "tournament")
        return ParsedSourcePage(
            artifact=artifact,
            tournament=tournament,
            standings=_parse_standings(payload.get("standings", []), "standings"),
            decklist_references=_parse_decklist_references(
                payload.get("decklist_references", []), "decklist_references"
            ),
            rounds=_parse_rounds(payload.get("rounds", []), "rounds"),
            matches=_parse_matches(payload.get("matches", []), "matches"),
        )
    if artifact.resource_type != "decklist":
        raise MeleeSourceParseError(f"{artifact.path}: fixture payload is unsupported for this resource")
    payload = _fields(payload, artifact.path, {"resource_type", "decklist"})
    return ParsedSourcePage(
        artifact=artifact,
        decklists=(_parse_decklist(payload.get("decklist"), "decklist"),),
    )


def _artifact(value: Any, index: int) -> SourceArtifact:
    path = f"manifest.responses[{index}]"
    data = _fields(
        value,
        path,
        {
            "request_id",
            "resource_type",
            "page",
            "url",
            "path",
            "expected_content_type",
            "response_content_type",
            "etag",
            "last_modified",
            "status_code",
            "attempts",
            "sha256",
            "bytes",
        },
        {
            "method", "request_body_sha256", "source_round_id",
            "source_participant_id", "source_decklist_id",
        },
    )
    return SourceArtifact(
        request_id=_string(data.get("request_id"), f"{path}.request_id"),
        resource_type=_string(data.get("resource_type"), f"{path}.resource_type"),
        page=_integer(data.get("page"), f"{path}.page", minimum=1),
        url=_string(data.get("url"), f"{path}.url"),
        path=_string(data.get("path"), f"{path}.path"),
        expected_content_type=_string(
            data.get("expected_content_type"), f"{path}.expected_content_type"
        ),
        sha256=_string(data.get("sha256"), f"{path}.sha256"),
        bytes=_integer(data.get("bytes"), f"{path}.bytes"),
        method=_string(data.get("method"), f"{path}.method", optional=True),
        request_body_sha256=_string(
            data.get("request_body_sha256"), f"{path}.request_body_sha256", optional=True
        ),
        source_round_id=_string(data.get("source_round_id"), f"{path}.source_round_id", optional=True),
        source_participant_id=_string(
            data.get("source_participant_id"), f"{path}.source_participant_id", optional=True
        ),
        source_decklist_id=_string(
            data.get("source_decklist_id"), f"{path}.source_decklist_id", optional=True
        ),
    )


def _safe_artifact_path(snapshot: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or len(pure.parts) != 1 or pure.name in {"", ".", ".."}:
        raise MeleeSourceParseError(f"manifest response path is unsafe: {relative!r}")
    destination = snapshot / pure.name
    if destination.is_symlink() or not destination.is_file():
        raise MeleeSourceParseError(f"manifest response is not a regular file: {relative!r}")
    return destination


def parse_raw_snapshot(snapshot_path: str | Path) -> ParsedMeleeSnapshot:
    """Verify and parse one complete P5-03 raw archive snapshot."""

    snapshot = Path(snapshot_path)
    manifest_path = snapshot / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise MeleeSourceParseError("raw snapshot manifest.json is missing or unsafe")
    try:
        manifest = _decode_json(manifest_path.read_text(encoding="utf-8"), "manifest.json")
    except (OSError, UnicodeError) as exc:
        raise MeleeSourceParseError(f"manifest.json: cannot read manifest: {exc}") from exc
    if manifest.get("schema_version") not in {"1.0.0", "2.0.0"} or manifest.get("source") != "melee":
        raise MeleeSourceParseError("manifest.json: unsupported raw archive contract")
    manifest = _fields(
        manifest,
        "manifest",
        {"schema_version", "source", "event_id", "event_url", "fetched_at", "responses"},
    )
    event_id = _string(manifest.get("event_id"), "manifest.event_id")
    event_url = _string(manifest.get("event_url"), "manifest.event_url")
    fetched_at = _string(manifest.get("fetched_at"), "manifest.fetched_at")
    response_values = _list(manifest.get("responses"), "manifest.responses")
    if not response_values:
        raise MeleeSourceParseError("manifest.responses: at least one response is required")
    pages = []
    seen_paths: set[str] = set()
    for index, response_value in enumerate(response_values):
        if manifest["schema_version"] == "2.0.0":
            response_mapping = _mapping(response_value, f"manifest.responses[{index}]")
            v2_fields = {
                "method", "request_body_sha256", "source_round_id",
                "source_participant_id", "source_decklist_id",
            }
            missing_v2 = v2_fields - set(response_mapping)
            if missing_v2:
                raise MeleeSourceParseError(
                    f"manifest.responses[{index}]: missing v2 fields {sorted(missing_v2)}"
                )
        artifact = _artifact(response_value, index)
        if manifest["schema_version"] == "2.0.0":
            post_resource = artifact.resource_type in {"standings", "matches"}
            if artifact.method != ("POST" if post_resource else "GET"):
                raise MeleeSourceParseError(
                    f"{artifact.path}: HTTP method does not match its resource type"
                )
            if post_resource != (artifact.request_body_sha256 is not None):
                raise MeleeSourceParseError(
                    f"{artifact.path}: request-body digest does not match its HTTP method"
                )
            if artifact.resource_type in {"standings", "matches"} and artifact.source_round_id is None:
                raise MeleeSourceParseError(f"{artifact.path}: round response lacks source context")
            if artifact.resource_type == "decklist" and (
                artifact.source_participant_id is None or artifact.source_decklist_id is None
            ):
                raise MeleeSourceParseError(f"{artifact.path}: decklist response lacks source context")
        if artifact.path in seen_paths:
            raise MeleeSourceParseError("manifest.responses: duplicate response paths are not allowed")
        seen_paths.add(artifact.path)
        source_path = _safe_artifact_path(snapshot, artifact.path)
        try:
            body = source_path.read_bytes()
        except OSError as exc:
            raise MeleeSourceParseError(f"{artifact.path}: cannot read source response: {exc}") from exc
        if len(body) != artifact.bytes:
            raise MeleeSourceParseError(f"{artifact.path}: byte count does not match manifest")
        if sha256(body).hexdigest() != artifact.sha256:
            raise MeleeSourceParseError(f"{artifact.path}: SHA-256 does not match manifest")
        page = parse_source_response(body, artifact)
        if page.tournament is not None and page.tournament.source_event_id != event_id:
            raise MeleeSourceParseError(
                f"{artifact.path}: tournament event ID does not match manifest"
            )
        pages.append(page)
    return ParsedMeleeSnapshot(event_id, event_url, fetched_at, tuple(pages))


__all__ = [
    "MAX_SOURCE_BYTES",
    "MeleeSourceParseError",
    "ParsedMeleeSnapshot",
    "ParsedSourcePage",
    "SourceArtifact",
    "SourceCard",
    "SourceDecklist",
    "SourceDecklistReference",
    "SourceMatch",
    "SourceRound",
    "SourceStanding",
    "SourceTournament",
    "parse_raw_snapshot",
    "parse_source_response",
]
