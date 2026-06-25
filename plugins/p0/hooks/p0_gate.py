#!/usr/bin/env python3
"""Codex P0 plan gate hook.

Activates on prompts such as `/plan p0 <task>` (Codex passes only `p0 <task>`
to UserPromptSubmit) or `$p0 <task>`. Stop hooks then keep the same turn
running until the assistant emits a clear or blocked P0_GATE footer.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


STATE_DIR = Path.home() / ".codex" / "p0-gate"


ACTIVATION_RE = re.compile(
    r"^\s*(?:\$?p0(?:\s+gate)?|p0[-_ ]gate|P0_GATE_ACTIVE)\b",
    re.IGNORECASE,
)
FOOTER_RE = re.compile(r"P0_GATE:\s*(?P<body>.*)\s*$", re.IGNORECASE | re.DOTALL)
FIELD_RE = re.compile(r"^\s*([a-zA-Z0-9_]+)\s*:\s*(.*?)\s*$", re.MULTILINE)
INTEGER_RE = re.compile(r"^\d+$")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    event = payload.get("hook_event_name")
    if event == "UserPromptSubmit":
        return handle_user_prompt_submit(payload)
    if event == "Stop":
        return handle_stop(payload)
    return 0


def handle_user_prompt_submit(payload: dict[str, Any]) -> int:
    prompt = payload.get("prompt") or ""
    if not ACTIVATION_RE.search(prompt):
        return 0

    state = {
        "session_id": payload.get("session_id"),
        "turn_id": payload.get("turn_id"),
        "cwd": payload.get("cwd"),
        "last_completed_round": 0,
        "round": 0,
    }
    write_state(payload, state)

    emit_context(
        "P0 gate is active. Treat a leading `p0` or `$p0` as an activation prefix, "
        "not as part of the implementation request. Stay in plan-only mode. Draft "
        "or revise the plan, inspect the concrete code paths and contracts the plan "
        "touches, then review for P0 blockers. If a P0 is found, revise the plan and "
        "continue reviewing for as many rounds as needed. If no P0 remains, stop with "
        "the required P0_GATE footer: status clear, p0_count 0, rounds_completed, and "
        "code_paths_read."
    )
    return 0


def handle_stop(payload: dict[str, Any]) -> int:
    state = read_state(payload)
    if not state:
        return 0

    last_message = payload.get("last_assistant_message") or ""
    footer = parse_footer(last_message)
    status = footer.get("status")
    footer_round = parse_round(footer.get("rounds_completed"))
    last_completed_round = parse_round(str(state.get("last_completed_round") or state.get("round") or 0)) or 0

    if status == "clear" and footer_is_clear(footer):
        if footer_round is not None and footer_round > last_completed_round:
            remove_state(payload)
            return 0
        reason = (
            "The last P0_GATE footer said clear, but it did not advance "
            "`rounds_completed` beyond the prior revised round."
        )
        return continue_gate(payload, state, footer_round, reason)

    if status == "blocked":
        remove_state(payload)
        return 0

    if not footer:
        reason = "The last assistant message did not include a parseable P0_GATE footer."
    elif status == "clear":
        reason = (
            "The last P0_GATE footer was not a valid clear footer. Clear requires "
            "`status: clear`, `p0_count: 0`, and a new valid `rounds_completed` value."
        )
    elif status == "revised":
        reason = "The last P0_GATE footer reported a revised plan with remaining P0 work."
    else:
        reason = "The last P0_GATE footer did not report clear or blocked status."

    return continue_gate(payload, state, footer_round, reason)


def continue_gate(
    payload: dict[str, Any],
    state: dict[str, Any],
    footer_round: int | None,
    reason: str,
) -> int:
    last_completed_round = parse_round(str(state.get("last_completed_round") or state.get("round") or 0)) or 0
    completed_round = max(last_completed_round, footer_round or 0)
    next_round = completed_round + 1
    state["last_completed_round"] = completed_round
    state["round"] = completed_round
    write_state(payload, state)

    block(
        f"P0 gate is active. {reason} You have completed {completed_round} "
        f"review round(s); continue with review/revision round {next_round}. "
        "Do not implement. Re-read the current plan and inspect the concrete code paths, "
        "contracts, data flows, call sites, tests, and external interactions that the plan "
        "makes relevant. Let the code decide what needs more reading; do not use a fixed "
        "lens checklist. Look only for P0 blockers: issues that invalidate the plan or risk "
        "severe data, security, money, availability, deployment, or irreversible side-effect "
        f"failure. After this pass, set `rounds_completed: {next_round}`. If you find a P0, "
        "revise the plan to address it and end with `P0_GATE` status `revised`. If no P0 "
        "remains after re-reading the revised plan, end with `P0_GATE` status `clear` and "
        "`p0_count: 0`."
    )
    return 0


def state_path(payload: dict[str, Any]) -> Path:
    session_id = sanitize(str(payload.get("session_id") or "unknown-session"))
    turn_id = sanitize(str(payload.get("turn_id") or "unknown-turn"))
    return STATE_DIR / f"{session_id}-{turn_id}.json"


def sanitize(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def write_state(payload: dict[str, Any], state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = state_path(payload)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def read_state(payload: dict[str, Any]) -> dict[str, Any] | None:
    path = state_path(payload)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def remove_state(payload: dict[str, Any]) -> None:
    try:
        state_path(payload).unlink()
    except FileNotFoundError:
        pass


def parse_footer(message: str) -> dict[str, str]:
    match = FOOTER_RE.search(message)
    if not match:
        return {}
    fields = {}
    for key, value in FIELD_RE.findall(match.group("body")):
        fields[key.lower()] = value.strip().lower()
    return fields


def parse_round(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip()
    if not INTEGER_RE.match(value):
        return None
    return int(value)


def footer_is_clear(footer: dict[str, str]) -> bool:
    if footer.get("status") != "clear":
        return False
    p0_count = footer.get("p0_count")
    return p0_count in {"0", "0.0"}


def emit_context(context: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            }
        )
    )


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    raise SystemExit(main())
