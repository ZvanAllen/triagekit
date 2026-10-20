"""Tests for the generic engine mechanics and the non-clinical demo ruleset."""

from triagekit import CONTINUE, STOP, Decision, TriageConfig, TriageEngine
from triagekit.rulesets.demo import DEMO_RULES, TicketRecord


def test_stop_halts_evaluation():
    calls = []

    def rule_a(rec, res, cfg, ctx):
        calls.append("a")
        res.decision = Decision.ACCEPT
        return STOP

    def rule_b(rec, res, cfg, ctx):
        calls.append("b")
        return CONTINUE

    engine = TriageEngine(TriageConfig(), [rule_a, rule_b])
    result = engine.run({"anything": 1})
    assert result.decision == Decision.ACCEPT
    assert calls == ["a"]  # rule_b never ran


def test_context_is_shared_between_rules():
    def writer(rec, res, cfg, ctx):
        ctx["flag"] = True
        return CONTINUE

    def reader(rec, res, cfg, ctx):
        res.decision = Decision.ACCEPT if ctx.get("flag") else Decision.DECLINE
        return STOP

    engine = TriageEngine(TriageConfig(), [writer, reader])
    assert engine.run({}).decision == Decision.ACCEPT


def demo_engine():
    return TriageEngine(TriageConfig(), DEMO_RULES, record_factory=TicketRecord.from_raw)


def test_demo_urgent_accepts():
    r = demo_engine().run({"subject": "server down", "urgent": True, "has_contact": True})
    assert r.decision == Decision.ACCEPT
    assert "URGENT_QUEUE" in r.accepted_services


def test_demo_missing_contact_needs_followup():
    r = demo_engine().run({"subject": "question", "has_contact": False})
    assert r.decision == Decision.CONTACT_REQUIRED


def test_demo_missing_subject():
    assert demo_engine().run({"subject": ""}).decision == Decision.CONTACT_REQUIRED


def test_batch_echoes_identifiers():
    engine = demo_engine()
    out = engine.run_batch([{"subject": "x", "urgent": True, "has_contact": True}])
    assert out[0]["full_name"] == "x"
    assert out[0]["decision"] == Decision.ACCEPT
