"""Validated, fail-closed loading for the manually approved Melee whitelist."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

import yaml

from ..config import DuplicateKeyLoader


MELEE_EVENT_SCHEMA_VERSION = "3.0.0"
EVENT_ID_PATTERN = re.compile(r"^[1-9][0-9]*$")
PHASE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
MELEE_EVENT_URL_PATTERN = re.compile(r"^https://melee\.gg/Tournament/View/([1-9][0-9]*)$")
CONSTRUCTED_FORMATS = frozenset({"standard", "pauper", "modern", "pioneer", "legacy", "vintage"})
GAME_FORMATS = CONSTRUCTED_FORMATS | {"limited", "unknown"}
SERIES = frozenset(
    {
        "world_championship",
        "pro_tour",
        "regional_championship",
        "spotlight_series",
        "paupergeddon",
        "eternal_weekend",
    }
)
STRUCTURES = frozenset({"constructed_day2", "constructed_single_stage", "mixed"})
STAGES = frozenset({"day1", "day2", "playoff", "other"})
ROUND_PHASES = frozenset({"draft", "constructed", "playoff", "unknown"})
REVIEW_STATUSES = frozenset({"pending", "verified", "rejected"})
RESULT_TYPES = frozenset(
    {
        "played_win", "played_loss", "played_draw", "intentional_draw", "bye",
        "no_show", "unplayed_drop", "awarded_win_top8_lock", "administrative",
    }
)
PLAYED_RESULT_TYPES = frozenset({"played_win", "played_loss", "played_draw"})


class MeleeConfigError(ValueError):
    """Raised when the manually maintained Melee whitelist is invalid."""


class UnknownMeleeEventError(MeleeConfigError):
    """Raised when a caller requests an event absent from the whitelist."""


class DisabledMeleeEventError(MeleeConfigError):
    """Raised when a known event is not authorized for fetching."""


@dataclass(frozen=True)
class MeleePhaseDefinition:
    id: str
    stage: str
    round_phase: str
    game_format: str
    swiss: bool
    rounds: tuple[int, ...]
    source_labels: tuple[str, ...]


@dataclass(frozen=True)
class MeleeRawRequestDefinition:
    """One manually approved raw response request for a whitelisted event."""

    id: str
    resource_type: str
    url: str
    content_type: str
    page_parameter: str | None
    start_page: int | None
    max_pages: int | None


@dataclass(frozen=True)
class MeleeAdvancement:
    day2_after_round: int | None
    day2_minimum_match_points: int | None
    top8_lock_supported: bool | None


@dataclass(frozen=True)
class MeleeOverrideCompetitor:
    source_participant_id: str
    result_type: str
    match_points: int


@dataclass(frozen=True)
class MeleeMatchOverride:
    id: str
    source_match_id: str
    review_status: str
    played: bool
    competitors: tuple[MeleeOverrideCompetitor, ...]
    reason: str
    source_evidence: tuple[str, ...]


@dataclass(frozen=True)
class MeleeEventDefinition:
    id: str
    url: str
    name: str
    start_date: date
    end_date: date
    format: str
    series: str
    structure: str
    enabled: bool
    review_status: str
    mixed_format: bool
    raw_requests: tuple[MeleeRawRequestDefinition, ...]
    include_playoffs: bool
    phases: tuple[MeleePhaseDefinition, ...]
    advancement: MeleeAdvancement | None
    reviewed_overrides: tuple[MeleeMatchOverride, ...]
    constructed_game_format: str
    source_evidence: tuple[str, ...]
    special_handling: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class MeleeEventRegistry:
    schema_version: str
    events: tuple[MeleeEventDefinition, ...]

    def get(self, event_id: str) -> MeleeEventDefinition:
        if not isinstance(event_id, str) or not EVENT_ID_PATTERN.fullmatch(event_id):
            raise UnknownMeleeEventError("event id must be a non-empty decimal string")
        for event in self.events:
            if event.id == event_id:
                return event
        raise UnknownMeleeEventError(f"Melee event {event_id!r} is not present in the whitelist")

    def require_fetchable(self, event_id: str) -> MeleeEventDefinition:
        """Return an event only when its whitelist entry explicitly authorizes fetching."""

        event = self.get(event_id)
        if not event.enabled:
            raise DisabledMeleeEventError(f"Melee event {event_id!r} is registered but disabled for fetching")
        if event.review_status != "verified":
            raise DisabledMeleeEventError(f"Melee event {event_id!r} is not verified for fetching")
        return event


def _error(path: str, message: str) -> MeleeConfigError:
    return MeleeConfigError(f"{path}: {message}")


def _load_yaml_mapping(text: str, label: str) -> dict[str, Any]:
    try:
        data = yaml.load(text, Loader=DuplicateKeyLoader)
    except yaml.YAMLError as exc:
        raise MeleeConfigError(f"{label}: {str(exc).splitlines()[0]}") from exc
    if not isinstance(data, dict):
        raise _error(label, "expected a mapping")
    return data


def _require_mapping(value: Any, path: str, required: set[str], optional: set[str] = frozenset()) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(path, "must be a mapping")
    missing = required - set(value)
    unsupported = set(value) - required - optional
    if missing or unsupported:
        raise _error(path, "has unsupported, missing, or malformed fields")
    return value


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise _error(path, "must be a non-empty string")
    return value


def _require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise _error(path, "must be a boolean")
    return value


def _require_non_negative_int(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise _error(path, "must be a non-negative integer")
    return value


def _require_https_url(value: Any, path: str) -> str:
    url = _require_string(value, path)
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise _error(path, "must be an HTTPS URL")
    return url


def _parse_date_range(value: Any, path: str) -> tuple[date, date]:
    data = _require_mapping(value, path, {"start", "end"})
    try:
        start = date.fromisoformat(_require_string(data["start"], f"{path}.start"))
        end = date.fromisoformat(_require_string(data["end"], f"{path}.end"))
    except ValueError as exc:
        raise _error(path, "must contain ISO-8601 dates") from exc
    if start > end:
        raise _error(path, "start must not be after end")
    return start, end


def _parse_string_list(value: Any, path: str, *, required: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or (required and not value):
        raise _error(path, "must be a non-empty list")
    items = tuple(_require_string(item, f"{path}[{index}]") for index, item in enumerate(value))
    if len(items) != len(set(items)):
        raise _error(path, "must not contain duplicates")
    return items


def _parse_phase(value: Any, path: str, constructed_format: str, enabled: bool) -> MeleePhaseDefinition:
    data = _require_mapping(
        value,
        path,
        {"id", "stage", "round_phase", "game_format", "swiss"},
        {"rounds", "source_labels"},
    )
    if "rounds" not in data and "source_labels" not in data:
        raise _error(path, "must declare rounds or source_labels")
    phase_id = _require_string(data["id"], f"{path}.id")
    if not PHASE_ID_PATTERN.fullmatch(phase_id):
        raise _error(f"{path}.id", "must be a lowercase underscore-separated identifier")
    stage = _require_string(data["stage"], f"{path}.stage")
    if stage not in STAGES:
        raise _error(f"{path}.stage", "is not a supported stage")
    round_phase = _require_string(data["round_phase"], f"{path}.round_phase")
    if round_phase not in ROUND_PHASES:
        raise _error(f"{path}.round_phase", "is not a supported round phase")
    game_format = _require_string(data["game_format"], f"{path}.game_format")
    if game_format not in GAME_FORMATS:
        raise _error(f"{path}.game_format", "is not a supported game format")
    swiss = _require_bool(data["swiss"], f"{path}.swiss")

    rounds_data = data.get("rounds", [])
    if not isinstance(rounds_data, list):
        raise _error(f"{path}.rounds", "must be a list")
    rounds = tuple(_require_non_negative_int(number, f"{path}.rounds[{index}]") for index, number in enumerate(rounds_data))
    if any(number == 0 for number in rounds):
        raise _error(f"{path}.rounds", "must contain only positive round numbers")
    if len(rounds) != len(set(rounds)):
        raise _error(f"{path}.rounds", "must not contain duplicates")

    source_labels = _parse_string_list(data.get("source_labels", []), f"{path}.source_labels", required=False)
    if not rounds and not source_labels:
        raise _error(path, "must declare at least one round or source label")

    if round_phase == "draft" and game_format != "limited":
        raise _error(path, "draft phases must use limited game_format")
    if round_phase == "constructed" and game_format != constructed_format:
        raise _error(path, "constructed phases must use the event constructed format")
    if enabled and (round_phase == "unknown" or game_format == "unknown"):
        raise _error(path, "enabled events must not contain unknown phase assignments")
    return MeleePhaseDefinition(phase_id, stage, round_phase, game_format, swiss, rounds, source_labels)


def _parse_raw_requests(value: Any, path: str, event_id: str) -> tuple[MeleeRawRequestDefinition, ...]:
    if not isinstance(value, list) or not value or len(value) > 32:
        raise _error(path, "must be a non-empty list with at most 32 requests")
    requests: list[MeleeRawRequestDefinition] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        data = _require_mapping(item, item_path, {"id", "resource_type", "url", "content_type"}, {"pagination"})
        request_id = _require_string(data["id"], f"{item_path}.id")
        if not PHASE_ID_PATTERN.fullmatch(request_id):
            raise _error(f"{item_path}.id", "must be a lowercase underscore-separated identifier")
        resource_type = _require_string(data["resource_type"], f"{item_path}.resource_type")
        if resource_type not in {"tournament", "decklist"}:
            raise _error(f"{item_path}.resource_type", "must be tournament or decklist")
        url = _require_string(data["url"], f"{item_path}.url")
        parsed_url = urlparse(url)
        unsafe_url = (
            parsed_url.scheme != "https"
            or parsed_url.hostname != "melee.gg"
            or parsed_url.port is not None
            or parsed_url.username is not None
            or parsed_url.password is not None
            or bool(parsed_url.fragment)
        )
        tournament_path = parsed_url.path == f"/Tournament/View/{event_id}"
        decklist_path = bool(re.fullmatch(r"/Decklist/View/[1-9][0-9]*", parsed_url.path))
        if unsafe_url or (resource_type == "tournament" and not tournament_path) or (resource_type == "decklist" and not decklist_path):
            raise _error(f"{item_path}.url", "must be an HTTPS Melee tournament URL for this event")
        content_type = _require_string(data["content_type"], f"{item_path}.content_type")
        if content_type not in {"html", "json"}:
            raise _error(f"{item_path}.content_type", "must be html or json")
        page_parameter: str | None = None
        start_page: int | None = None
        max_pages: int | None = None
        if "pagination" in data:
            if resource_type != "tournament":
                raise _error(f"{item_path}.pagination", "is supported only for tournament resources")
            pagination = _require_mapping(data["pagination"], f"{item_path}.pagination", {"parameter", "start_page", "max_pages"})
            page_parameter = _require_string(pagination["parameter"], f"{item_path}.pagination.parameter")
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", page_parameter):
                raise _error(f"{item_path}.pagination.parameter", "must be a safe query parameter name")
            start_page = _require_non_negative_int(pagination["start_page"], f"{item_path}.pagination.start_page")
            max_pages = _require_non_negative_int(pagination["max_pages"], f"{item_path}.pagination.max_pages")
            if start_page == 0 or max_pages == 0 or max_pages > 100:
                raise _error(f"{item_path}.pagination", "must use positive pages and at most 100 pages")
        requests.append(MeleeRawRequestDefinition(request_id, resource_type, url, content_type, page_parameter, start_page, max_pages))
    ids = [request.id for request in requests]
    if len(ids) != len(set(ids)):
        raise _error(path, "must not contain duplicate request IDs")
    return tuple(requests)


def _parse_advancement(value: Any, path: str) -> MeleeAdvancement:
    data = _require_mapping(value, path, set(), {"day2_after_round", "day2_minimum_match_points", "top8_lock_supported"})
    after_round = data.get("day2_after_round")
    if after_round is not None:
        after_round = _require_non_negative_int(after_round, f"{path}.day2_after_round")
        if after_round == 0:
            raise _error(f"{path}.day2_after_round", "must be positive")
    match_points = data.get("day2_minimum_match_points")
    if match_points is not None:
        match_points = _require_non_negative_int(match_points, f"{path}.day2_minimum_match_points")
    top8_lock_supported = data.get("top8_lock_supported")
    if top8_lock_supported is not None:
        top8_lock_supported = _require_bool(top8_lock_supported, f"{path}.top8_lock_supported")
    return MeleeAdvancement(after_round, match_points, top8_lock_supported)


def _parse_reviewed_overrides(value: Any, path: str) -> tuple[MeleeMatchOverride, ...]:
    if not isinstance(value, list):
        raise _error(path, "must be a list")
    overrides: list[MeleeMatchOverride] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        data = _require_mapping(
            item,
            item_path,
            {"id", "source_match_id", "review_status", "played", "competitors", "reason", "source_evidence"},
        )
        override_id = _require_string(data["id"], f"{item_path}.id")
        if not PHASE_ID_PATTERN.fullmatch(override_id):
            raise _error(f"{item_path}.id", "must be a lowercase underscore-separated identifier")
        source_match_id = _require_string(data["source_match_id"], f"{item_path}.source_match_id")
        review_status = _require_string(data["review_status"], f"{item_path}.review_status")
        if review_status != "verified":
            raise _error(f"{item_path}.review_status", "must be verified")
        played = _require_bool(data["played"], f"{item_path}.played")
        competitors_data = data["competitors"]
        if not isinstance(competitors_data, list) or not 1 <= len(competitors_data) <= 2:
            raise _error(f"{item_path}.competitors", "must contain one or two competitors")
        competitors: list[MeleeOverrideCompetitor] = []
        for position, competitor_value in enumerate(competitors_data):
            competitor_path = f"{item_path}.competitors[{position}]"
            competitor = _require_mapping(
                competitor_value,
                competitor_path,
                {"source_participant_id", "result_type", "match_points"},
            )
            result_type = _require_string(competitor["result_type"], f"{competitor_path}.result_type")
            if result_type not in RESULT_TYPES:
                raise _error(f"{competitor_path}.result_type", "is not a supported reviewed result")
            competitors.append(
                MeleeOverrideCompetitor(
                    _require_string(competitor["source_participant_id"], f"{competitor_path}.source_participant_id"),
                    result_type,
                    _require_non_negative_int(competitor["match_points"], f"{competitor_path}.match_points"),
                )
            )
        participant_ids = [item.source_participant_id for item in competitors]
        if len(participant_ids) != len(set(participant_ids)):
            raise _error(f"{item_path}.competitors", "must not contain duplicate participants")
        result_types = tuple(item.result_type for item in competitors)
        if played != all(result_type in PLAYED_RESULT_TYPES for result_type in result_types):
            raise _error(item_path, "played must agree with all competitor result types")
        if played and (
            len(competitors) != 2
            or sorted(result_types) not in [["played_loss", "played_win"], ["played_draw", "played_draw"]]
        ):
            raise _error(item_path, "played overrides must be win/loss or draw/draw pairs")
        expected_points = {"played_win": 3, "played_loss": 0, "played_draw": 1}
        if played and any(
            item.match_points != expected_points[item.result_type] for item in competitors
        ):
            raise _error(item_path, "played override points must match win/loss/draw semantics")
        evidence = _parse_string_list(data["source_evidence"], f"{item_path}.source_evidence")
        for position, url in enumerate(evidence):
            _require_https_url(url, f"{item_path}.source_evidence[{position}]")
        overrides.append(
            MeleeMatchOverride(
                override_id,
                source_match_id,
                review_status,
                played,
                tuple(competitors),
                _require_string(data["reason"], f"{item_path}.reason"),
                evidence,
            )
        )
    ids = [item.id for item in overrides]
    source_match_ids = [item.source_match_id for item in overrides]
    if len(ids) != len(set(ids)):
        raise _error(path, "must not contain duplicate override IDs")
    if len(source_match_ids) != len(set(source_match_ids)):
        raise _error(path, "must not contain multiple overrides for one match")
    return tuple(overrides)


def _parse_event(value: Any, path: str) -> MeleeEventDefinition:
    required = {
        "id", "url", "name", "date", "format", "series", "structure", "enabled", "review_status",
        "tabletop", "team_event", "mixed_format", "raw_requests", "include", "phases", "statistics", "source_evidence",
        "special_handling", "notes",
    }
    data = _require_mapping(value, path, required, {"advancement", "reviewed_overrides"})
    event_id = _require_string(data["id"], f"{path}.id")
    if not EVENT_ID_PATTERN.fullmatch(event_id):
        raise _error(f"{path}.id", "must be a non-empty decimal string")
    url = _require_string(data["url"], f"{path}.url")
    url_match = MELEE_EVENT_URL_PATTERN.fullmatch(url)
    if not url_match:
        raise _error(f"{path}.url", "must be an HTTPS Melee tournament URL")
    if url_match.group(1) != event_id:
        raise _error(f"{path}.url", "event ID must match the whitelist id")
    name = _require_string(data["name"], f"{path}.name")
    start_date, end_date = _parse_date_range(data["date"], f"{path}.date")
    constructed_format = _require_string(data["format"], f"{path}.format")
    if constructed_format not in CONSTRUCTED_FORMATS:
        raise _error(f"{path}.format", "is not a supported Constructed format")
    series = _require_string(data["series"], f"{path}.series")
    if series not in SERIES:
        raise _error(f"{path}.series", "is not an approved event series")
    structure = _require_string(data["structure"], f"{path}.structure")
    if structure not in STRUCTURES:
        raise _error(f"{path}.structure", "is not a supported event structure")
    enabled = _require_bool(data["enabled"], f"{path}.enabled")
    review_status = _require_string(data["review_status"], f"{path}.review_status")
    if review_status not in REVIEW_STATUSES:
        raise _error(f"{path}.review_status", "is not a supported review status")
    if enabled and review_status != "verified":
        raise _error(f"{path}.review_status", "must be verified when the event is enabled")
    if data["tabletop"] is not True:
        raise _error(f"{path}.tabletop", "must be true")
    if data["team_event"] is not False:
        raise _error(f"{path}.team_event", "must be false")
    mixed_format = _require_bool(data["mixed_format"], f"{path}.mixed_format")
    if mixed_format != (structure == "mixed"):
        raise _error(f"{path}.mixed_format", "must match the event structure")
    raw_requests = _parse_raw_requests(data["raw_requests"], f"{path}.raw_requests", event_id)

    include = _require_mapping(data["include"], f"{path}.include", {"swiss", "playoffs"})
    if include["swiss"] is not True:
        raise _error(f"{path}.include.swiss", "must be true")
    include_playoffs = _require_bool(include["playoffs"], f"{path}.include.playoffs")

    phases_data = data["phases"]
    if not isinstance(phases_data, list) or not phases_data:
        raise _error(f"{path}.phases", "must be a non-empty list")
    phases = tuple(
        _parse_phase(item, f"{path}.phases[{index}]", constructed_format, enabled)
        for index, item in enumerate(phases_data)
    )
    phase_ids = [phase.id for phase in phases]
    if len(phase_ids) != len(set(phase_ids)):
        raise _error(f"{path}.phases", "must not contain duplicate phase IDs")
    round_numbers = [number for phase in phases for number in phase.rounds]
    if len(round_numbers) != len(set(round_numbers)):
        raise _error(f"{path}.phases", "must not assign one round to multiple phases")
    source_labels = [label for phase in phases for label in phase.source_labels]
    if len(source_labels) != len(set(source_labels)):
        raise _error(f"{path}.phases", "must not assign one source label to multiple phases")
    if enabled and not any(phase.round_phase == "constructed" for phase in phases):
        raise _error(f"{path}.phases", "enabled events must identify at least one Constructed phase")

    statistics = _require_mapping(
        data["statistics"],
        f"{path}.statistics",
        {"default_match_scope", "constructed_game_format", "include_playoffs"},
    )
    if statistics["default_match_scope"] != "all_constructed_swiss":
        raise _error(f"{path}.statistics.default_match_scope", "must be all_constructed_swiss")
    statistics_format = _require_string(statistics["constructed_game_format"], f"{path}.statistics.constructed_game_format")
    if statistics_format != constructed_format:
        raise _error(f"{path}.statistics.constructed_game_format", "must match the event format")
    if statistics["include_playoffs"] is not False:
        raise _error(f"{path}.statistics.include_playoffs", "must be false")

    evidence = _parse_string_list(data["source_evidence"], f"{path}.source_evidence")
    for index, source_url in enumerate(evidence):
        _require_https_url(source_url, f"{path}.source_evidence[{index}]")
    special_handling = _parse_string_list(data["special_handling"], f"{path}.special_handling", required=False)
    notes = _require_string(data["notes"], f"{path}.notes")
    advancement = _parse_advancement(data["advancement"], f"{path}.advancement") if "advancement" in data else None
    reviewed_overrides = _parse_reviewed_overrides(
        data.get("reviewed_overrides", []), f"{path}.reviewed_overrides"
    )
    if any(
        competitor.result_type == "awarded_win_top8_lock"
        for override in reviewed_overrides
        for competitor in override.competitors
    ) and (advancement is None or advancement.top8_lock_supported is not True):
        raise _error(f"{path}.reviewed_overrides", "Top 8 lock awards require explicit advancement support")
    return MeleeEventDefinition(
        event_id, url, name, start_date, end_date, constructed_format, series, structure, enabled,
        review_status, mixed_format, raw_requests, include_playoffs, phases, advancement, reviewed_overrides, statistics_format,
        evidence, special_handling, notes,
    )


def parse_melee_event_text(text: str) -> MeleeEventRegistry:
    """Parse a whitelist without making network requests or enabling any event."""

    data = _load_yaml_mapping(text, "melee_events")
    if set(data) != {"schema_version", "events"}:
        raise _error("melee_events", "must contain only schema_version and events")
    if data["schema_version"] != MELEE_EVENT_SCHEMA_VERSION:
        raise _error("schema_version", f"must equal {MELEE_EVENT_SCHEMA_VERSION!r}")
    entries = data["events"]
    if not isinstance(entries, list) or not entries:
        raise _error("events", "must be a non-empty list")
    events = tuple(_parse_event(entry, f"events[{index}]") for index, entry in enumerate(entries))
    event_ids = [event.id for event in events]
    if len(event_ids) != len(set(event_ids)):
        raise _error("events", "must not contain duplicate event IDs")
    return MeleeEventRegistry(MELEE_EVENT_SCHEMA_VERSION, events)


def load_melee_event_registry(path: str | Path) -> MeleeEventRegistry:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise MeleeConfigError(f"{source}: cannot read whitelist: {exc}") from exc
    return parse_melee_event_text(text)
