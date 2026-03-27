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
from utils.utils import BitwardenCommandException  # noqa: E402


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

    @patch("bitwardenCrdOperator.unlock_bw")
    @patch("bitwardenCrdOperator.command_wrapper")
    def test_signin_success_resets_failure_counter(
        self, command_wrapper_mock, unlock_bw_mock
    ):
        operator.auth_failures = 2
        command_wrapper_mock.return_value = {"success": True}

        operator.bitwarden_signin(self.logger)

        self.assertEqual(operator.auth_failures, 0)
        unlock_bw_mock.assert_called_once_with(self.logger)

    @patch("bitwardenCrdOperator.recover_auth_state")
    @patch("bitwardenCrdOperator.unlock_bw")
    @patch("bitwardenCrdOperator.command_wrapper")
    def test_signin_failure_below_threshold_does_not_trigger_recovery(
        self, command_wrapper_mock, unlock_bw_mock, recover_auth_state_mock
    ):
        os.environ["BW_AUTH_FAILURE_THRESHOLD"] = "3"
        command_wrapper_mock.return_value = None

        operator.bitwarden_signin(self.logger)

        self.assertEqual(operator.auth_failures, 1)
        unlock_bw_mock.assert_not_called()
        recover_auth_state_mock.assert_not_called()

    @patch("bitwardenCrdOperator.recover_auth_state")
    @patch("bitwardenCrdOperator.unlock_bw")
    @patch("bitwardenCrdOperator.command_wrapper")
    def test_recovery_runs_after_threshold_and_resets_counter(
        self, command_wrapper_mock, unlock_bw_mock, recover_auth_state_mock
    ):
        os.environ["BW_AUTH_FAILURE_THRESHOLD"] = "2"
        operator.auth_failures = 1
        command_wrapper_mock.side_effect = [
            None,
            {"success": True},
        ]

        operator.bitwarden_signin(self.logger)

        recover_auth_state_mock.assert_called_once_with(self.logger)
        self.assertEqual(operator.auth_failures, 0)
        self.assertEqual(unlock_bw_mock.call_count, 1)

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

    @patch(
        "bitwardenCrdOperator.unlock_bw",
        side_effect=BitwardenCommandException("unlock failed"),
    )
    @patch("bitwardenCrdOperator.command_wrapper", return_value={"success": True})
    def test_unlock_error_counts_as_auth_failure(
        self, _command_wrapper_mock, _unlock_bw_mock
    ):
        operator.bitwarden_signin(self.logger)

        self.assertEqual(operator.auth_failures, 1)


if __name__ == "__main__":
    unittest.main()
