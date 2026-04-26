"""
tests/test_audit.py
Tests for the AuditTrail module (local backend).
"""
import json
import os
import tempfile
import pytest

from audit.trail import AuditTrail, AuditEvent


@pytest.fixture()
def tmp_trail(tmp_path):
    """AuditTrail backed by a temp file."""
    log_file = str(tmp_path / "test_audit.jsonl")
    os.environ["AUDIT_BACKEND"] = "local"
    os.environ["AUDIT_LOCAL_PATH"] = log_file
    trail = AuditTrail()
    trail._local_path = log_file   # override in case env was stale
    yield trail
    # cleanup
    if os.path.exists(log_file):
        os.remove(log_file)


class TestAuditEvent:
    def test_fields_default(self):
        ev = AuditEvent()
        assert ev.event_id  # UUID auto-set
        assert ev.timestamp  # ISO datetime auto-set
        assert ev.outcome == ""

    def test_to_dict_roundtrip(self):
        ev = AuditEvent(incident_id="inc-1", workflow="pr_review", outcome="completed")
        d = ev.to_dict()
        assert d["incident_id"] == "inc-1"
        assert d["workflow"] == "pr_review"

    def test_to_json_valid(self):
        ev = AuditEvent(incident_id="inc-2", workflow="cicd_analysis")
        parsed = json.loads(ev.to_json())
        assert parsed["incident_id"] == "inc-2"

    def test_summary_truncated_at_500(self):
        ev = AuditEvent(summary="x" * 1000)
        # AuditTrail.log truncates; AuditEvent itself stores what's given
        assert len(ev.summary) == 1000  # raw; trail truncates on log()


class TestAuditTrailLocal:
    def test_log_creates_file(self, tmp_trail, tmp_path):
        tmp_trail.log(
            incident_id="inc-001",
            workflow="pr_review",
            repo="org/repo",
            outcome="completed",
            summary="All good",
        )
        assert os.path.exists(tmp_trail._local_path)

    def test_log_writes_valid_json(self, tmp_trail):
        tmp_trail.log(
            incident_id="inc-002",
            workflow="scaling_analysis",
            repo="org/api",
            outcome="completed",
            duration_seconds=12.5,
            metadata={"deployment": "api-server"},
        )
        with open(tmp_trail._local_path) as f:
            line = f.readline()
        data = json.loads(line)
        assert data["incident_id"] == "inc-002"
        assert data["workflow"] == "scaling_analysis"
        assert data["duration_seconds"] == 12.5
        assert data["metadata"]["deployment"] == "api-server"

    def test_get_events_returns_logged(self, tmp_trail):
        for i in range(3):
            tmp_trail.log(
                incident_id=f"inc-{i:03d}",
                workflow="cicd_analysis",
                repo="org/repo",
                outcome="completed",
            )
        events = tmp_trail.get_events(limit=10)
        assert len(events) == 3

    def test_get_events_filter_by_incident(self, tmp_trail):
        tmp_trail.log(incident_id="target", workflow="pr_review", repo="r", outcome="ok")
        tmp_trail.log(incident_id="other", workflow="pr_review", repo="r", outcome="ok")
        events = tmp_trail.get_events(incident_id="target")
        assert len(events) == 1
        assert events[0]["incident_id"] == "target"

    def test_get_events_most_recent_first(self, tmp_trail):
        tmp_trail.log(incident_id="old", workflow="pr_review", repo="r", outcome="ok")
        import time; time.sleep(0.01)
        tmp_trail.log(incident_id="new", workflow="pr_review", repo="r", outcome="ok")
        events = tmp_trail.get_events(limit=10)
        assert events[0]["incident_id"] == "new"

    def test_get_events_respects_limit(self, tmp_trail):
        for i in range(10):
            tmp_trail.log(incident_id=f"i{i}", workflow="pr_review", repo="r", outcome="ok")
        events = tmp_trail.get_events(limit=3)
        assert len(events) == 3

    def test_summary_truncated_to_500(self, tmp_trail):
        tmp_trail.log(
            incident_id="trunc-001",
            workflow="incident_response",
            repo="org/repo",
            outcome="completed",
            summary="A" * 2000,
        )
        events = tmp_trail.get_events(incident_id="trunc-001")
        assert len(events[0]["summary"]) == 500

    def test_empty_file_returns_empty(self, tmp_trail):
        events = tmp_trail.get_events()
        assert events == []
