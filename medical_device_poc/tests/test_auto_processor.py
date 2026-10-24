from __future__ import annotations

import sys

from apps.submissions.auto_processor import _should_start_auto_processor


def test_auto_processor_only_starts_in_runserver_child(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["manage.py", "runserver"])
    monkeypatch.setenv("RUN_MAIN", "true")
    monkeypatch.delenv("DISABLE_SUBMISSION_AUTO_PROCESSOR", raising=False)

    assert _should_start_auto_processor() is True


def test_auto_processor_does_not_start_for_management_commands(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["manage.py", "pytest"])
    monkeypatch.setenv("RUN_MAIN", "true")

    assert _should_start_auto_processor() is False


def test_auto_processor_starts_for_runserver_without_reloader(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["manage.py", "runserver", "--noreload"])
    monkeypatch.delenv("RUN_MAIN", raising=False)

    assert _should_start_auto_processor() is True


def test_auto_processor_can_be_disabled(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["manage.py", "runserver"])
    monkeypatch.setenv("RUN_MAIN", "true")
    monkeypatch.setenv("DISABLE_SUBMISSION_AUTO_PROCESSOR", "1")

    assert _should_start_auto_processor() is False
