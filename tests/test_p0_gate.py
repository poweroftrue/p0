import contextlib
import importlib.util
import io
import json
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / "plugins" / "p0" / "hooks" / "p0_gate.py"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "bousla_google_search_7_rounds.md"


def load_hook():
    spec = importlib.util.spec_from_file_location("p0_gate_under_test", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def extract_footers():
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^P0_GATE:\n"
        r"status: .+\n"
        r"p0_count: .+\n"
        r"rounds_completed: .+\n"
        r"code_paths_read: .+$",
        re.MULTILINE,
    )
    return [match.group(0) for match in pattern.finditer(text)]


class P0GateHookTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.hook = load_hook()
        self.hook.STATE_DIR = Path(self.tmpdir.name)
        self.base_payload = {
            "session_id": "test-session",
            "turn_id": "test-turn",
            "cwd": str(ROOT),
        }

    def tearDown(self):
        self.tmpdir.cleanup()

    def activate(self):
        payload = dict(self.base_payload, hook_event_name="UserPromptSubmit", prompt="$p0 test")
        return self.call(self.hook.handle_user_prompt_submit, payload)

    def stop(self, message):
        payload = dict(self.base_payload, hook_event_name="Stop", last_assistant_message=message)
        return self.call(self.hook.handle_stop, payload)

    def call(self, func, payload):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            result = func(payload)
        self.assertEqual(result, 0)
        output = buffer.getvalue().strip()
        if not output:
            return []
        return [json.loads(line) for line in output.splitlines()]

    def assert_blocking_round(self, output, expected_round):
        self.assertEqual(output[0]["decision"], "block")
        reason = output[0]["reason"]
        self.assertIn(f"review/revision round {expected_round}", reason)
        self.assertIn(f"rounds_completed: {expected_round}", reason)

    def test_revised_footer_advances_to_next_round(self):
        self.activate()

        output = self.stop(
            "P0 remains.\n\n"
            "P0_GATE:\n"
            "status: revised\n"
            "p0_count: 1\n"
            "rounds_completed: 1\n"
            "code_paths_read: synthetic"
        )

        self.assert_blocking_round(output, 2)

        output = self.stop(
            "P0 remains.\n\n"
            "P0_GATE:\n"
            "status: revised\n"
            "p0_count: 1\n"
            "rounds_completed: 2\n"
            "code_paths_read: synthetic"
        )

        self.assert_blocking_round(output, 3)

    def test_invalid_clear_with_nonzero_p0_count_keeps_gate_running(self):
        self.activate()

        output = self.stop(
            "Contradictory clear.\n\n"
            "P0_GATE:\n"
            "status: clear\n"
            "p0_count: 2\n"
            "rounds_completed: 2\n"
            "code_paths_read: bousla google search"
        )

        self.assert_blocking_round(output, 3)
        self.assertIn("not a valid clear footer", output[0]["reason"])

    def test_clear_must_advance_after_revised_round(self):
        self.activate()
        self.stop(
            "P0 remains.\n\n"
            "P0_GATE:\n"
            "status: revised\n"
            "p0_count: 1\n"
            "rounds_completed: 1\n"
            "code_paths_read: synthetic"
        )

        output = self.stop(
            "No P0 remains.\n\n"
            "P0_GATE:\n"
            "status: clear\n"
            "p0_count: 0\n"
            "rounds_completed: 1\n"
            "code_paths_read: synthetic"
        )

        self.assert_blocking_round(output, 2)
        self.assertIn("did not advance", output[0]["reason"])

    def test_bousla_google_search_fixture_runs_seven_rounds(self):
        footers = extract_footers()
        self.assertEqual(len(footers), 7)
        self.activate()

        for round_number, footer in enumerate(footers[:6], start=1):
            output = self.stop(f"Round {round_number} revised.\n\n{footer}")
            self.assert_blocking_round(output, round_number + 1)

        output = self.stop(f"Round 7 clear.\n\n{footers[6]}")
        self.assertEqual(output, [])
        self.assertEqual(list(self.hook.STATE_DIR.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
