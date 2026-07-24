"""Format-aware Videre fetching and MTGO matchup generation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import logging
from pathlib import Path
import re
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from mtgmeta.classifier import classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.rules import RuleSet
from public_contract import versioned

from . import load_mtgo_context
from .classification import load_mtgo_events_for_format
from .stats import latest_complete_week, parse_event_date


VIDERE_BASE_URL = "https://api.videreproject.com"
DEFAULT_RANGES = (1, 4, 12, 36)
MIN_MATCHUP_SAMPLE = 20
WILSON_Z = 1.96
SOURCE_ID = "mtgo"
VIDERE_REQUEST_ATTEMPTS = 3
VIDERE_REQUEST_TIMEOUT_SECONDS = 30
VIDERE_RETRY_DELAY_SECONDS = 2.0
VIDERE_RETRYABLE_HTTP_CODES = frozenset({408, 425, 429})


LOGGER = logging.getLogger(__name__)


class NoResults(Exception):
    """Raised when Videre has no rows for an event."""


class MTGOMatchupError(RuntimeError):
    """Raised when matchup input cannot be classified or generated safely."""


@dataclass(frozen=True)
class MatchupIdentity:
    """Stable parent and most-specific matchup identities for one deck."""

    parent_id: str
    parent_name: str
    subtype_id: str | None
    subtype_name: str | None

    @property
    def leaf_id(self) -> str:
        if self.subtype_id is None:
            return self.parent_id
        return f"{self.parent_id}/{self.subtype_id}"

    @property
    def leaf_name(self) -> str:
        return self.subtype_name or self.parent_name


def api_get(
    format_id: str,
    params: dict[str, Any],
    *,
    opener: Callable[..., Any] | None = None,
    attempts: int = VIDERE_REQUEST_ATTEMPTS,
    timeout: float = VIDERE_REQUEST_TIMEOUT_SECONDS,
    retry_delay: float = VIDERE_RETRY_DELAY_SECONDS,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Read one Videre response with bounded transient-failure retries."""

    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1:
        raise ValueError("attempts must be a positive integer")
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or timeout <= 0
    ):
        raise ValueError("timeout must be positive")
    if (
        not isinstance(retry_delay, (int, float))
        or isinstance(retry_delay, bool)
        or retry_delay < 0
    ):
        raise ValueError("retry_delay must be non-negative")

    url = f"{VIDERE_BASE_URL}/matches/{format_id}?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "videre-fetch/0.2"})
    open_request = opener or urllib.request.urlopen
    wait = sleep or time.sleep
    for attempt in range(1, attempts + 1):
        try:
            with open_request(request, timeout=timeout) as response:
                value = json.loads(response.read().decode("utf-8"))
            if not isinstance(value, dict):
                raise MTGOMatchupError("Videre response root must be an object")
            return value
        except urllib.error.HTTPError as exc:
            if exc.code == 400:
                try:
                    body = json.loads(exc.read().decode("utf-8"))
                except Exception:
                    body = {}
                if str(body.get("message", "")).lower().startswith("no results"):
                    raise NoResults() from exc
            if (
                exc.code not in VIDERE_RETRYABLE_HTTP_CODES
                and not 500 <= exc.code < 600
            ):
                raise
            error: Exception = exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            error = exc
        if attempt >= attempts:
            raise error
        LOGGER.warning(
            "Videre request attempt %d/%d failed with %s; retrying in %.1f seconds",
            attempt,
            attempts,
            error,
            retry_delay,
        )
        if retry_delay:
            wait(retry_delay)
    raise AssertionError("unreachable Videre retry state")


def fetch_all_matches(
    format_id: str,
    event_id: str | int,
    *,
    api_getter: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Fetch every Videre page for one event."""

    getter = api_getter or api_get
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        body = getter(
            format_id,
            {"event_id": event_id, "limit": 500, "offset": offset},
        )
        data = body.get("data", [])
        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            raise MTGOMatchupError("Videre response data must be a list of objects")
        rows.extend(data)
        meta = body.get("meta", {})
        if not isinstance(meta, dict):
            raise MTGOMatchupError("Videre response meta must be an object")
        if meta.get("has_more") and meta.get("next_offset") is not None:
            offset = int(meta["next_offset"])
        else:
            return rows


def event_ids_from_fetched(path: str | Path, format_id: str) -> list[str]:
    """Return stable unique event IDs for one format from ``fetched.txt``."""

    source = Path(path)
    if not source.exists():
        return []
    pattern = re.compile(rf"(?:^|/){re.escape(format_id)}-.*?\d{{4}}-\d{{2}}-\d{{2}}(\d+)\s*$")
    ids: list[str] = []
    seen: set[str] = set()
    for line in source.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line.strip())
        if match is not None and match.group(1) not in seen:
            event_id = match.group(1)
            seen.add(event_id)
            ids.append(event_id)
    return ids


def fetch_and_store_matches(
    repository_root: str | Path,
    format_id: str,
    *,
    event_ids: list[str] | tuple[str, ...] | None = None,
    force: bool = False,
    fetched_file: str | Path | None = None,
    registry_path: str | Path | None = None,
    api_fetcher: Callable[[str, str], list[dict[str, Any]]] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Fetch Videre rows only after format authorization and path resolution."""

    context = load_mtgo_context(
        repository_root,
        format_id,
        "matchup_statistics",
        registry_path=registry_path,
    )
    root = context.repository_root
    source = Path(fetched_file) if fetched_file is not None else root / "fetched.txt"
    selected = list(event_ids) if event_ids is not None else event_ids_from_fetched(source, format_id)
    if any(not str(event_id).isdigit() for event_id in selected):
        raise MTGOMatchupError("Videre event IDs must contain digits only")
    selected = [str(event_id) for event_id in selected]
    output_directory = context.paths["matches"]
    fetcher = api_fetcher or (lambda fmt, event_id: fetch_all_matches(fmt, event_id))
    wait = sleep or time.sleep
    summary: dict[str, Any] = {
        "format": format_id,
        "requested": len(selected),
        "fetched": 0,
        "skipped": 0,
        "not_found": 0,
        "failed": 0,
        "missing_event_ids": [],
        "written": [],
        "errors": [],
    }
    for event_id in selected:
        destination = output_directory / f"{event_id}.json"
        if destination.exists() and not force:
            summary["skipped"] += 1
            continue
        try:
            rows = fetcher(format_id, event_id)
            if not rows:
                summary["not_found"] += 1
                summary["missing_event_ids"].append(event_id)
                continue
            output_directory.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps({"event_id": int(event_id), "matches": rows}, ensure_ascii=False, indent=2),
                encoding="utf-8",
                newline="\n",
            )
            summary["fetched"] += 1
            summary["written"].append(destination)
            wait(0.3)
        except NoResults:
            summary["not_found"] += 1
            summary["missing_event_ids"].append(event_id)
        except Exception as exc:  # Keep independent events fetchable after one failure.
            summary["failed"] += 1
            summary["errors"].append((event_id, str(exc)))
    return summary


def wilson_half_width(wins: float, total: int, z: float = WILSON_Z) -> float | None:
    if total <= 0:
        return None
    p = wins / total
    denominator = 1 + z * z / total
    return (
        z
        * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5)
        / denominator
    )


def _blank_cell() -> dict[str, int]:
    return {"wins": 0, "losses": 0, "draws": 0}


def _win_rate(cell: dict[str, int]) -> float | None:
    total = cell["wins"] + cell["losses"] + cell["draws"]
    return (cell["wins"] + 0.5 * cell["draws"]) / total if total else None


def _classify_parent(player: dict[str, Any], rule_set: RuleSet) -> str | None:
    result = classify_deck(rule_set, player)
    if result.status == "classified":
        return result.archetype_name
    if result.status == "unknown":
        return None
    detail = result.conflict_kind or ", ".join(result.errors) or result.status
    raise MTGOMatchupError(f"cannot aggregate {result.status} deck: {detail}")


def _classify_identity(
    player: dict[str, Any],
    rule_set: RuleSet,
) -> MatchupIdentity | None:
    """Classify one deck and enforce the approved no-residual subtype policy."""

    result = classify_deck(rule_set, player)
    if result.status == "unknown":
        return None
    if result.status != "classified":
        detail = result.conflict_kind or ", ".join(result.errors) or result.status
        raise MTGOMatchupError(f"cannot aggregate {result.status} deck: {detail}")
    definitions = {
        archetype.id: archetype for archetype in rule_set.archetypes
    }
    definition = definitions.get(result.archetype_id or "")
    if definition is None:
        raise MTGOMatchupError(
            f"classified archetype {result.archetype_id!r} is absent from the rule set"
        )
    if definition.subtypes and result.subtype_id is None:
        raise MTGOMatchupError(
            f"classified archetype {definition.id!r} defines subtypes but selected none"
        )
    if not definition.subtypes and result.subtype_id is not None:
        raise MTGOMatchupError(
            f"classified archetype {definition.id!r} selected an undefined subtype"
        )
    return MatchupIdentity(
        parent_id=definition.id,
        parent_name=definition.name,
        subtype_id=result.subtype_id,
        subtype_name=result.subtype_name,
    )


def load_official_events_from_directory(
    events_directory: str | Path,
    rule_set: RuleSet,
    *,
    classifier: Callable[[dict[str, Any], RuleSet], str | None] | None = None,
) -> list[tuple[date, str, dict[str, str], set[str]]]:
    """Load event dates and player-to-parent-archetype mappings."""

    classify = classifier or _classify_parent
    events: list[tuple[date, str, dict[str, str], set[str]]] = []
    for path in sorted(Path(events_directory).glob("*.json")):
        event = json.loads(path.read_text(encoding="utf-8"))
        event_date = parse_event_date(event.get("starttime"))
        event_id = str(event.get("event_id", "")).strip()
        if event_date is None or not event_id:
            continue
        mapping: dict[str, str] = {}
        all_names: set[str] = set()
        for player in event.get("players", []):
            name = player.get("player")
            if not name:
                continue
            all_names.add(name)
            archetype = classify(player, rule_set)
            if archetype is not None:
                mapping[name] = archetype
        events.append((event_date, event_id, mapping, all_names))
    return events


def load_official_events(
    repository_root: str | Path,
    format_id: str,
    *,
    registry_path: str | Path | None = None,
) -> list[tuple[date, str, dict[str, str], set[str]]]:
    context = load_mtgo_context(
        repository_root,
        format_id,
        "matchup_statistics",
        registry_path=registry_path,
    )
    return load_official_events_from_directory(
        context.paths["events"],
        load_rule_set(context.paths["rules"]),
    )


def build_matchup_hierarchy(rule_set: RuleSet) -> dict[str, Any]:
    """Build the complete stable parent/leaf hierarchy from maintained rules."""

    parents: list[dict[str, Any]] = []
    leaves: list[dict[str, Any]] = []
    for archetype in sorted(rule_set.archetypes, key=lambda item: item.id):
        subtype_ids = [
            f"{archetype.id}/{subtype.id}"
            for subtype in sorted(archetype.subtypes, key=lambda item: item.id)
        ]
        parents.append(
            {
                "id": archetype.id,
                "name": archetype.name,
                "expandable": len(archetype.subtypes) >= 2,
                "subtype_ids": subtype_ids,
            }
        )
        if archetype.subtypes:
            for subtype in sorted(archetype.subtypes, key=lambda item: item.id):
                leaves.append(
                    {
                        "id": f"{archetype.id}/{subtype.id}",
                        "kind": "subtype",
                        "name": subtype.name,
                        "parent_id": archetype.id,
                        "subtype_id": subtype.id,
                    }
                )
        else:
            leaves.append(
                {
                    "id": archetype.id,
                    "kind": "archetype",
                    "name": archetype.name,
                    "parent_id": archetype.id,
                    "subtype_id": None,
                }
            )
    return {"parents": parents, "leaves": leaves}


def load_hierarchical_events_from_directory(
    events_directory: str | Path,
    rule_set: RuleSet,
    *,
    repository_root: str | Path,
    format_id: str,
) -> list[tuple[date, str, dict[str, MatchupIdentity], set[str]]]:
    """Load exact-format events and stable parent/subtype mappings."""

    paths = sorted(Path(events_directory).glob("*.json"))
    loaded, excluded = load_mtgo_events_for_format(
        paths,
        repository_root,
        format_id,
    )
    if excluded:
        details = ", ".join(
            f"{item.source_file} ({item.actual_format})" for item in excluded
        )
        raise MTGOMatchupError(
            f"cross-format event input rejected for {format_id}: {details}"
        )
    events: list[tuple[date, str, dict[str, MatchupIdentity], set[str]]] = []
    for source_file, event in loaded:
        event_date = parse_event_date(event.get("starttime"))
        event_id = str(event.get("event_id", "")).strip()
        if event_date is None or not event_id:
            raise MTGOMatchupError(
                f"{source_file}: event date and event ID are required"
            )
        mapping: dict[str, MatchupIdentity] = {}
        all_names: set[str] = set()
        players = event.get("players", [])
        if not isinstance(players, list):
            raise MTGOMatchupError(f"{source_file}: players must be an array")
        for player in players:
            if not isinstance(player, dict):
                raise MTGOMatchupError(
                    f"{source_file}: every player must be an object"
                )
            name = player.get("player")
            if not isinstance(name, str) or not name:
                continue
            all_names.add(name)
            identity = _classify_identity(player, rule_set)
            if identity is not None:
                mapping[name] = identity
        events.append((event_date, event_id, mapping, all_names))
    return events


def accumulate_event(
    matches_directory: str | Path,
    event_id: str,
    player_arch: dict[str, str],
    official_names: set[str],
    matrix: dict[str, dict[str, dict[str, int]]],
    mirror: dict[str, dict[str, int]],
    overall: dict[str, dict[str, int]],
    seen_keys: set[tuple[Any, ...]],
    stats: dict[str, int],
) -> None:
    matches_path = Path(matches_directory) / f"{event_id}.json"
    if not matches_path.exists():
        stats["no_match_file"] += 1
        return
    raw = json.loads(matches_path.read_text(encoding="utf-8"))
    rows = raw.get("matches", []) if isinstance(raw, dict) else raw
    if not rows:
        stats["no_match_file"] += 1
        return

    for row in rows:
        if not isinstance(row, dict) or row.get("isbye"):
            continue
        player = row.get("player")
        opponent = row.get("opponent")
        result = row.get("result")
        round_id = row.get("round")
        if not player or not opponent or result not in ("win", "loss", "draw"):
            continue
        key = (str(event_id), round_id, frozenset((player, opponent)))
        if key in seen_keys:
            stats["dedup_skipped"] += 1
            continue
        seen_keys.add(key)
        stats["physical_matches"] += 1

        first = player_arch.get(player)
        second = player_arch.get(opponent)
        if first is None or second is None:
            stats["dropped_unmapped"] += 1
            for name, archetype in ((player, first), (opponent, second)):
                if archetype is None:
                    reason = "drop_reason_unknown_deck" if name in official_names else "drop_reason_not_in_official"
                    stats[reason] += 1
            continue

        stats["counted"] += 1
        if first == second:
            cell = mirror.setdefault(first, _blank_cell())
            if result == "win":
                cell["wins"] += 1
                cell["losses"] += 1
            elif result == "loss":
                cell["losses"] += 1
                cell["wins"] += 1
            else:
                cell["draws"] += 2
            stats["mirror_matches"] += 1
            continue

        first_cell = matrix.setdefault(first, {}).setdefault(second, _blank_cell())
        second_cell = matrix.setdefault(second, {}).setdefault(first, _blank_cell())
        first_overall = overall.setdefault(first, _blank_cell())
        second_overall = overall.setdefault(second, _blank_cell())
        if result == "win":
            first_cell["wins"] += 1
            second_cell["losses"] += 1
            first_overall["wins"] += 1
            second_overall["losses"] += 1
        elif result == "loss":
            first_cell["losses"] += 1
            second_cell["wins"] += 1
            first_overall["losses"] += 1
            second_overall["wins"] += 1
        else:
            first_cell["draws"] += 1
            second_cell["draws"] += 1
            first_overall["draws"] += 1
            second_overall["draws"] += 1
        stats["cross_matches"] += 1


def _inverse_result(result: str) -> str:
    if result == "win":
        return "loss"
    if result == "loss":
        return "win"
    return "draw"


def _add_directed_result(
    matrix: dict[str, dict[str, dict[str, int]]],
    row_id: str,
    column_id: str,
    result: str,
) -> None:
    cell = matrix.setdefault(row_id, {}).setdefault(column_id, _blank_cell())
    if result == "win":
        cell["wins"] += 1
    elif result == "loss":
        cell["losses"] += 1
    else:
        cell["draws"] += 1


def accumulate_hierarchical_event(
    matches_directory: str | Path,
    event_id: str,
    player_identity: dict[str, MatchupIdentity],
    official_names: set[str],
    leaf_matrix: dict[str, dict[str, dict[str, int]]],
    seen_keys: set[tuple[Any, ...]],
    stats: dict[str, int],
) -> None:
    """Accumulate canonical directed leaf counts for one physical event."""

    matches_path = Path(matches_directory) / f"{event_id}.json"
    if not matches_path.exists():
        stats["no_match_file"] += 1
        return
    raw = json.loads(matches_path.read_text(encoding="utf-8"))
    rows = raw.get("matches", []) if isinstance(raw, dict) else raw
    if not isinstance(rows, list) or not rows:
        stats["no_match_file"] += 1
        return

    for row in rows:
        if not isinstance(row, dict) or row.get("isbye"):
            continue
        player = row.get("player")
        opponent = row.get("opponent")
        result = row.get("result")
        round_id = row.get("round")
        if (
            not isinstance(player, str)
            or not player
            or not isinstance(opponent, str)
            or not opponent
            or result not in ("win", "loss", "draw")
        ):
            continue
        key = (str(event_id), round_id, frozenset((player, opponent)))
        if key in seen_keys:
            stats["dedup_skipped"] += 1
            continue
        seen_keys.add(key)
        stats["physical_matches"] += 1

        first = player_identity.get(player)
        second = player_identity.get(opponent)
        if first is None or second is None:
            stats["dropped_unmapped"] += 1
            for name, identity in ((player, first), (opponent, second)):
                if identity is None:
                    reason = (
                        "drop_reason_unknown_deck"
                        if name in official_names
                        else "drop_reason_not_in_official"
                    )
                    stats[reason] += 1
            continue

        stats["counted"] += 1
        _add_directed_result(
            leaf_matrix,
            first.leaf_id,
            second.leaf_id,
            result,
        )
        _add_directed_result(
            leaf_matrix,
            second.leaf_id,
            first.leaf_id,
            _inverse_result(result),
        )
        if first.parent_id == second.parent_id:
            stats["mirror_matches"] += 1
        else:
            stats["cross_matches"] += 1


def aggregate_matchup_counts(
    leaf_matrix: dict[str, dict[str, dict[str, int]]],
    row_identity: dict[str, str],
    column_identity: dict[str, str],
) -> dict[str, dict[str, dict[str, int]]]:
    """Aggregate canonical counts independently on each matrix axis."""

    aggregated: dict[str, dict[str, dict[str, int]]] = {}
    for row_id, columns in leaf_matrix.items():
        target_row = row_identity.get(row_id)
        if target_row is None:
            raise MTGOMatchupError(f"unknown matchup leaf ID {row_id!r}")
        for column_id, cell in columns.items():
            target_column = column_identity.get(column_id)
            if target_column is None:
                raise MTGOMatchupError(f"unknown matchup leaf ID {column_id!r}")
            target = aggregated.setdefault(target_row, {}).setdefault(
                target_column,
                _blank_cell(),
            )
            for field in ("wins", "losses", "draws"):
                target[field] += cell[field]
    return aggregated


def rollup_matchup_counts(
    leaf_matrix: dict[str, dict[str, dict[str, int]]],
    leaf_to_parent: dict[str, str],
) -> dict[str, dict[str, dict[str, int]]]:
    """Roll canonical leaf counts up to stable parent IDs on both axes."""

    return aggregate_matchup_counts(
        leaf_matrix,
        leaf_to_parent,
        leaf_to_parent,
    )


def _overall_from_directed_matrix(
    matrix: dict[str, dict[str, dict[str, int]]],
) -> dict[str, dict[str, int]]:
    """Return non-mirror overall counts from one directed matrix."""

    overall: dict[str, dict[str, int]] = {}
    for row_id, columns in matrix.items():
        target = overall.setdefault(row_id, _blank_cell())
        for column_id, cell in columns.items():
            if row_id == column_id:
                continue
            for field in ("wins", "losses", "draws"):
                target[field] += cell[field]
    return overall


def _directed_order(
    matrix: dict[str, dict[str, dict[str, int]]],
    overall: dict[str, dict[str, int]],
) -> list[str]:
    identities = set(matrix) | {
        column_id for columns in matrix.values() for column_id in columns
    }
    return sorted(
        identities,
        key=lambda identity: (
            -sum(overall.get(identity, _blank_cell()).values()),
            identity,
        ),
    )


def _emit_directed_matrix(
    matrix: dict[str, dict[str, dict[str, int]]],
    order: list[str],
) -> dict[str, dict[str, Any]]:
    return {
        row_id: {
            column_id: _emit_cell(cell, row_id == column_id)
            for column_id, cell in sorted(matrix.get(row_id, {}).items())
        }
        for row_id in order
    }


def _emit_overall(
    overall: dict[str, dict[str, int]],
    order: list[str],
) -> dict[str, dict[str, Any]]:
    return {
        identity: _emit_cell(overall.get(identity, _blank_cell()), False)
        for identity in order
    }


def _emit_cell(cell: dict[str, int], is_mirror: bool) -> dict[str, Any]:
    total = cell["wins"] + cell["losses"] + cell["draws"]
    win_rate = _win_rate(cell)
    interval = wilson_half_width(cell["wins"] + 0.5 * cell["draws"], total)
    return {
        "wins": cell["wins"],
        "losses": cell["losses"],
        "draws": cell["draws"],
        "matches": total,
        "win_rate": round(win_rate, 4) if win_rate is not None else None,
        "ci_half": round(interval, 4) if interval is not None else None,
        "low_sample": total < MIN_MATCHUP_SAMPLE,
        "mirror": is_mirror,
    }


def build_window_output(
    matrix: dict[str, dict[str, dict[str, int]]],
    mirror: dict[str, dict[str, int]],
    overall: dict[str, dict[str, int]],
) -> tuple[list[str], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    archetypes = set(matrix) | set(mirror) | set(overall)
    order = sorted(
        archetypes,
        key=lambda archetype: (
            -sum(overall.get(archetype, _blank_cell()).values()),
            archetype,
        ),
    )
    matrix_output: dict[str, dict[str, Any]] = {}
    overall_output: dict[str, dict[str, Any]] = {}
    for archetype in order:
        overall_output[archetype] = _emit_cell(overall.get(archetype, _blank_cell()), False)
        row: dict[str, Any] = {}
        if archetype in mirror:
            row[archetype] = _emit_cell(mirror[archetype], True)
        for opponent in matrix.get(archetype, {}):
            row[opponent] = _emit_cell(matrix[archetype][opponent], False)
        matrix_output[archetype] = row
    return order, matrix_output, overall_output


def build_window(
    events: list[tuple[date, str, dict[str, str], set[str]]],
    end_monday: date,
    n_weeks: int,
    *,
    matches_directory: str | Path,
    format_id: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    start_monday = end_monday - timedelta(weeks=n_weeks - 1)
    end_sunday = end_monday + timedelta(days=6)
    matrix: dict[str, dict[str, dict[str, int]]] = {}
    mirror: dict[str, dict[str, int]] = {}
    overall: dict[str, dict[str, int]] = {}
    seen_keys: set[tuple[Any, ...]] = set()
    stats = {
        key: 0
        for key in (
            "events_in_window",
            "no_match_file",
            "physical_matches",
            "dedup_skipped",
            "counted",
            "dropped_unmapped",
            "cross_matches",
            "mirror_matches",
            "drop_reason_unknown_deck",
            "drop_reason_not_in_official",
        )
    }
    for event_date, event_id, mapping, all_names in events:
        if start_monday <= event_date <= end_sunday:
            stats["events_in_window"] += 1
            accumulate_event(
                matches_directory,
                event_id,
                mapping,
                all_names,
                matrix,
                mirror,
                overall,
                seen_keys,
                stats,
            )
    order, matrix_output, overall_output = build_window_output(matrix, mirror, overall)
    return versioned(
        {
            "format": format_id,
            "source": SOURCE_ID,
            "period": {
                "type": f"{n_weeks}w",
                "start": start_monday.isoformat(),
                "end": end_sunday.isoformat(),
                "weeks": n_weeks,
            },
            "min_sample_hint": MIN_MATCHUP_SAMPLE,
            "archetype_order": order,
            "overall": overall_output,
            "matrix": matrix_output,
        }
    ), stats


def _validate_directed_counts(
    matrix: dict[str, dict[str, dict[str, int]]],
    physical_matches: int,
) -> None:
    observations = 0
    for row_id, columns in matrix.items():
        for column_id, cell in columns.items():
            observations += sum(cell.values())
            inverse = matrix.get(column_id, {}).get(row_id)
            if inverse is None:
                raise MTGOMatchupError(
                    f"missing inverse matchup cell for {row_id!r} and {column_id!r}"
                )
            if (
                cell["wins"] != inverse["losses"]
                or cell["losses"] != inverse["wins"]
                or cell["draws"] != inverse["draws"]
            ):
                raise MTGOMatchupError(
                    f"non-conserving matchup cells for {row_id!r} and {column_id!r}"
                )
    if observations != physical_matches * 2:
        raise MTGOMatchupError(
            "directed matchup observations do not equal twice the counted matches"
        )


def build_hierarchical_window(
    events: list[
        tuple[date, str, dict[str, MatchupIdentity], set[str]]
    ],
    end_monday: date,
    n_weeks: int,
    *,
    matches_directory: str | Path,
    format_id: str,
    rule_set: RuleSet,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Build one stable-ID hierarchical matchup window."""

    start_monday = end_monday - timedelta(weeks=n_weeks - 1)
    end_sunday = end_monday + timedelta(days=6)
    leaf_matrix: dict[str, dict[str, dict[str, int]]] = {}
    seen_keys: set[tuple[Any, ...]] = set()
    stats = {
        key: 0
        for key in (
            "events_in_window",
            "no_match_file",
            "physical_matches",
            "dedup_skipped",
            "counted",
            "dropped_unmapped",
            "cross_matches",
            "mirror_matches",
            "drop_reason_unknown_deck",
            "drop_reason_not_in_official",
        )
    }
    for event_date, event_id, mapping, all_names in events:
        if start_monday <= event_date <= end_sunday:
            stats["events_in_window"] += 1
            accumulate_hierarchical_event(
                matches_directory,
                event_id,
                mapping,
                all_names,
                leaf_matrix,
                seen_keys,
                stats,
            )

    hierarchy = build_matchup_hierarchy(rule_set)
    leaf_to_parent = {
        leaf["id"]: leaf["parent_id"] for leaf in hierarchy["leaves"]
    }
    _validate_directed_counts(leaf_matrix, stats["counted"])
    parent_matrix = rollup_matchup_counts(leaf_matrix, leaf_to_parent)
    _validate_directed_counts(parent_matrix, stats["counted"])

    leaf_overall = _overall_from_directed_matrix(leaf_matrix)
    parent_overall = _overall_from_directed_matrix(parent_matrix)
    leaf_order = _directed_order(leaf_matrix, leaf_overall)
    parent_order = _directed_order(parent_matrix, parent_overall)
    return versioned(
        {
            "format": format_id,
            "source": SOURCE_ID,
            "period": {
                "type": f"{n_weeks}w",
                "start": start_monday.isoformat(),
                "end": end_sunday.isoformat(),
                "weeks": n_weeks,
            },
            "min_sample_hint": MIN_MATCHUP_SAMPLE,
            "hierarchical": True,
            "canonical_level": "leaf",
            "hierarchy": hierarchy,
            "parent_order": parent_order,
            "parent_overall": _emit_overall(parent_overall, parent_order),
            "parent_matrix": _emit_directed_matrix(parent_matrix, parent_order),
            "leaf_order": leaf_order,
            "leaf_overall": _emit_overall(leaf_overall, leaf_order),
            "leaf_matrix": _emit_directed_matrix(leaf_matrix, leaf_order),
        }
    ), stats


def _generated_value(value: datetime | str | None) -> str:
    if value is None:
        return datetime.now().isoformat(timespec="seconds")
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return str(value)


def build_all_matchups(
    repository_root: str | Path,
    format_id: str,
    *,
    today: date | None = None,
    generated_at: datetime | str | None = None,
    output_directory: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> tuple[dict[str, Path], dict[int, dict[str, int]]]:
    """Generate all matchup windows after explicit format authorization."""

    context = load_mtgo_context(
        repository_root,
        format_id,
        "matchup_statistics",
        registry_path=registry_path,
    )
    rule_set = load_rule_set(context.paths["rules"])
    hierarchical = format_id != "standard"
    if hierarchical:
        events = load_hierarchical_events_from_directory(
            context.paths["events"],
            rule_set,
            repository_root=context.repository_root,
            format_id=format_id,
        )
    else:
        events = load_official_events_from_directory(context.paths["events"], rule_set)
    end_monday = latest_complete_week([(event[0], None) for event in events], today=today)
    if end_monday is None:
        return {}, {}

    output = Path(output_directory) if output_directory is not None else context.paths["statistics"]
    documents: dict[str, dict[str, Any]] = {}
    statistics: dict[int, dict[str, int]] = {}
    index_entries = []
    for weeks in DEFAULT_RANGES:
        if hierarchical:
            document, window_stats = build_hierarchical_window(
                events,
                end_monday,
                weeks,
                matches_directory=context.paths["matches"],
                format_id=format_id,
                rule_set=rule_set,
            )
        else:
            document, window_stats = build_window(
                events,
                end_monday,
                weeks,
                matches_directory=context.paths["matches"],
                format_id=format_id,
            )
        filename = f"matchup_{weeks}w.json"
        documents[filename] = document
        statistics[weeks] = window_stats
        entry = {
            "file": filename,
            "type": document["period"]["type"],
            "start": document["period"]["start"],
            "end": document["period"]["end"],
            "weeks": weeks,
            "archetypes": len(
                document["parent_order"]
                if hierarchical
                else document["archetype_order"]
            ),
            "counted_matches": window_stats["counted"],
        }
        if hierarchical:
            entry["leaves"] = len(document["leaf_order"])
        index_entries.append(entry)
    index_document = {
        "format": format_id,
        "source": SOURCE_ID,
        "generated": _generated_value(generated_at),
        "latest_complete_week": end_monday.isoformat(),
        "min_sample_hint": MIN_MATCHUP_SAMPLE,
        "ranges": index_entries,
    }
    if hierarchical:
        index_document["hierarchical"] = True
    documents["matchup_index.json"] = versioned(index_document)
    output.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for filename, document in documents.items():
        destination = output / filename
        destination.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )
        written[filename] = destination
    return written, statistics


__all__ = [
    "DEFAULT_RANGES",
    "MIN_MATCHUP_SAMPLE",
    "MTGOMatchupError",
    "NoResults",
    "VIDERE_BASE_URL",
    "WILSON_Z",
    "MatchupIdentity",
    "accumulate_event",
    "accumulate_hierarchical_event",
    "aggregate_matchup_counts",
    "api_get",
    "build_all_matchups",
    "build_hierarchical_window",
    "build_matchup_hierarchy",
    "build_window",
    "build_window_output",
    "event_ids_from_fetched",
    "fetch_all_matches",
    "fetch_and_store_matches",
    "load_official_events",
    "load_official_events_from_directory",
    "load_hierarchical_events_from_directory",
    "rollup_matchup_counts",
    "wilson_half_width",
]
