"""Measure completed Codex replay turns from existing local logs, without prompts."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path


def seconds(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def measure(path):
    turns, active, calls = [], None, {}
    for line in Path(path).open(encoding="utf-8"):
        row = json.loads(line)
        payload, timestamp = row.get("payload", {}), row["timestamp"]
        kind = payload.get("type")
        if row["type"] == "event_msg" and kind == "task_started":
            active = {"started_at": timestamp, "turn_id": payload.get("turn_id"), "tools": []}
            calls = {}
        elif active and row["type"] == "turn_context":
            active["model"] = payload.get("model", "unknown")
            active["reasoning_effort"] = payload.get("effort", "unknown")
        elif active and row["type"] == "response_item":
            if kind in {"custom_tool_call", "function_call"}:
                calls[payload["call_id"]] = {"name": payload.get("name"), "start": timestamp}
            elif kind in {"custom_tool_call_output", "function_call_output"} and payload.get("call_id") in calls:
                call = calls.pop(payload["call_id"])
                call["end"] = timestamp
                call["seconds"] = round(seconds(timestamp) - seconds(call["start"]), 4)
                active["tools"].append(call)
        elif active and row["type"] == "event_msg" and kind == "task_complete":
            active["completed_at"] = timestamp
            intervals = sorted((seconds(c["start"]), seconds(c["end"])) for c in active["tools"])
            merged = []
            for start, end in intervals:
                if merged and start <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], end)
                else:
                    merged.append([start, end])
            tool_time = sum(end-start for start, end in merged)
            elapsed = seconds(timestamp) - seconds(active["started_at"])
            active.update(elapsed_seconds=round(elapsed, 4), outer_tool_seconds=round(tool_time, 4),
                          remaining_seconds=round(elapsed-tool_time, 4), unmatched_calls=list(calls),
                          user_wait_inside_turn_seconds=0,
                          external_wait="Included in outer tools when observed; no reliable independent attribution")
            turns.append(active)
            active = None
    return {"log": str(path), "measurement": "task_started through task_complete; overlapping tool intervals merged",
            "remaining_meaning": "Unattributed time between tools and result submission, not pure reasoning", "turns": turns}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Retain earlier measurements; choose a new file")
    result = [measure(path) for path in args.log]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps([{ "log": item["log"], "turns": [{k:v for k,v in turn.items() if k != "tools"} for turn in item["turns"]]} for item in result], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
