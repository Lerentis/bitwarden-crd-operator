import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import bitwardenCrdOperator as operator  # noqa: E402


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(("info", str(message)))

    def warn(self, message):
        self.messages.append(("warn", str(message)))

    def error(self, message):
        self.messages.append(("error", str(message)))


class BitwardenSigninRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.logger = DummyLogger()
        self.original_auth_failures = operator.auth_failures
        operator.auth_failures = 0
        os.environ.pop("BW_HOST", None)
        os.environ.pop("BW_SESSION", None)
        os.environ.pop("BW_AUTH_FAILURE_THRESHOLD", None)

    def tearDown(self):
        operator.auth_failures = self.original_auth_failures
        os.environ.pop("BW_AUTH_FAILURE_THRESHOLD", None)
        os.environ.pop("BW_SESSION", None)

    @patch("bitwardenCrdOperator.command_wrapper")
    def test_signin_success_resets_failure_counter(self, command_wrapper_mock):
        operator.auth_failures = 2
        command_wrapper_mock.side_effect = [
            {"success": True},
            {"data": {"template": {"status": "unlocked"}}},
        ]

        operator.bitwarden_signin(self.logger)

        self.assertEqual(operator.auth_failures, 0)

    @patch("bitwardenCrdOperator.recover_auth_state")
    @patch("bitwardenCrdOperator.command_wrapper")
    def test_signin_failure_below_threshold_does_not_trigger_recovery(
        self, command_wrapper_mock, recover_auth_state_mock
    ):
        os.environ["BW_AUTH_FAILURE_THRESHOLD"] = "3"
        command_wrapper_mock.return_value = None

        operator.bitwarden_signin(self.logger)

        self.assertEqual(operator.auth_failures, 1)
        recover_auth_state_mock.assert_not_called()

    @patch("bitwardenCrdOperator.recover_auth_state")
    @patch("bitwardenCrdOperator.command_wrapper")
    def test_recovery_runs_after_threshold_and_resets_counter(
        self, command_wrapper_mock, recover_auth_state_mock
    ):
        os.environ["BW_AUTH_FAILURE_THRESHOLD"] = "2"
        operator.auth_failures = 1
        command_wrapper_mock.side_effect = [
            None,
            {"success": True},
            {"data": {"template": {"status": "locked"}}},
            {"data": {"raw": "new-session"}},
        ]

        operator.bitwarden_signin(self.logger)

        recover_auth_state_mock.assert_called_once_with(self.logger)
        self.assertEqual(operator.auth_failures, 0)
        self.assertEqual(os.environ.get("BW_SESSION"), "new-session")

    @patch("bitwardenCrdOperator.sys.exit")
    @patch("bitwardenCrdOperator.recover_auth_state")
    @patch("bitwardenCrdOperator.command_wrapper")
    def test_recovery_failure_exits_process(
        self, command_wrapper_mock, recover_auth_state_mock, sys_exit_mock
    ):
        os.environ["BW_AUTH_FAILURE_THRESHOLD"] = "1"
        command_wrapper_mock.side_effect = [None, None]

        operator.bitwarden_signin(self.logger)

        recover_auth_state_mock.assert_called_once_with(self.logger)
        sys_exit_mock.assert_called_once_with(1)

    def test_invalid_threshold_uses_default_without_exception_control_flow(self):
        os.environ["BW_AUTH_FAILURE_THRESHOLD"] = "invalid"

        threshold = operator._auth_failure_threshold(self.logger)

        self.assertEqual(threshold, operator.AUTH_FAILURE_THRESHOLD)

    @patch("bitwardenCrdOperator.command_wrapper")
    def test_recover_auth_state_clears_session_and_cache_file(
        self, command_wrapper_mock
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_file = Path(temp_dir) / ".config" / "Bitwarden CLI" / "data.json"
            data_file.parent.mkdir(parents=True, exist_ok=True)
            data_file.write_text("{ invalid", encoding="utf-8")
            os.environ["BW_SESSION"] = "stale-session"

            with patch(
                "bitwardenCrdOperator.os.path.expanduser", return_value=temp_dir
            ):
                operator.recover_auth_state(self.logger)

            self.assertNotIn("BW_SESSION", os.environ)
            self.assertFalse(data_file.exists())
            command_wrapper_mock.assert_called_once_with(
                self.logger, "logout", use_success=False
            )

    @patch("bitwardenCrdOperator.command_wrapper")
    def test_status_failure_counts_as_auth_failure(self, command_wrapper_mock):
        command_wrapper_mock.side_effect = [
            {"success": True},
            None,
        ]

        operator.bitwarden_signin(self.logger)

        self.assertEqual(operator.auth_failures, 1)


if __name__ == "__main__":
    unittest.main()
