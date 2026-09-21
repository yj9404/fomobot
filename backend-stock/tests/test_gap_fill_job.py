"""
jobs/gap_fill.py의 예외 처리 및 Sentry 캡처 격리 테스트.
"""

import sys
import logging
import pytest
from unittest import mock

from fomobot.jobs import gap_fill


class TestRunSentryCaptureException:
    def test_sentry_capture_exception_호출시_예외_무시하고_종료(self, monkeypatch, caplog):
        """
        run_gap_fill_for_market()에서 예외 발생 시,
        sentry_sdk.capture_exception()도 예외를 던지는 상황에서
        프로그램이 죽지 않고(가려지지 않고) sys.exit(1)로 정상 실패 처리되는지 확인.
        """
        class FakeSentry:
            def capture_exception(self):
                raise RuntimeError("Sentry capture failed")

        monkeypatch.setitem(sys.modules, "sentry_sdk", FakeSentry())

        with mock.patch("fomobot.batch.gap_fill.run_gap_fill_for_market", side_effect=Exception("mocked error")):
            with pytest.raises(SystemExit) as exc_info:
                gap_fill.run("kospi")

            assert exc_info.value.code == 1

    def test_sentry_capture_exception_성공시_종료(self, monkeypatch):
        """sentry_sdk.capture_exception()이 성공하더라도 sys.exit(1)로 종료되어야 함"""
        class FakeSentry:
            def capture_exception(self):
                pass

        monkeypatch.setitem(sys.modules, "sentry_sdk", FakeSentry())

        with mock.patch("fomobot.batch.gap_fill.run_gap_fill_for_market", side_effect=Exception("mocked error")):
            with pytest.raises(SystemExit) as exc_info:
                gap_fill.run("kospi")

            assert exc_info.value.code == 1
