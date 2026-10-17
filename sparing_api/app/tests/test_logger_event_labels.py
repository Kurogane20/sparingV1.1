"""Logger events on the dashboard read as Indonesian sentences, not raw codes."""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.models import LoggerEvent
from app.utils.timeseries_service import _logger_events

TS = datetime(2026, 8, 1, tzinfo=timezone.utc)


def _event(event_type, detail=None, severity="warning"):
    return LoggerEvent(site_id=1, event_uid=f"{event_type}-{detail}", type=event_type, ts=TS,
                       received_at=TS + timedelta(minutes=3), severity=severity, detail=detail)


@pytest.mark.parametrize("detail, label, severity", [
    ("gagal kirim: KLHK", "Gagal Kirim ke KLHK", "info"),
    ("gagal kirim: MM", "Gagal Kirim ke Server", "warning"),
    ("gagal kirim: MM+KLHK", "Gagal Kirim ke Server & KLHK", "warning"),
])
def test_send_fail_label_names_the_destination(detail, label, severity):
    [event] = _logger_events("S", [_event("send_fail", detail)])

    assert (event.label, event.severity) == (label, severity)


@pytest.mark.parametrize("event_type, label", [
    ("net_down", "Internet Terputus"),
    ("net_up", "Internet Tersambung"),
    ("started", "Logger Menyala"),
    ("stopped", "Logger Dimatikan"),
    ("stopping", "Logger Dimatikan"),
])
def test_logger_lifecycle_labels_are_indonesian(event_type, label):
    [event] = _logger_events("S", [_event(event_type, severity="info")])

    assert event.label == label


def test_logger_event_has_no_delivery_latency_as_interval():
    [event] = _logger_events("S", [_event("net_up", severity="info")])

    assert event.context.interval_seconds is None
