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


SUPPORTED_RESOURCE_TYPES = frozenset({"tournament", "decklist"})
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


def parse_source_response(body: bytes, artifact: SourceArtifact) -> ParsedSourcePage:
    """Parse one verified source response without applying normalized semantics."""

    if artifact.resource_type not in SUPPORTED_RESOURCE_TYPES:
        raise MeleeSourceParseError(f"{artifact.path}: unsupported resource type {artifact.resource_type!r}")
    if artifact.expected_content_type not in SUPPORTED_CONTENT_TYPES:
        raise MeleeSourceParseError(
            f"{artifact.path}: unsupported content type {artifact.expected_content_type!r}"
        )
    payload = _decode_payload(body, artifact.expected_content_type, artifact.path)
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
    if manifest.get("schema_version") != "1.0.0" or manifest.get("source") != "melee":
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
        artifact = _artifact(response_value, index)
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
