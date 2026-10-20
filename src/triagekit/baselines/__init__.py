"""Alternative (non-deterministic) triage backends, kept for comparison.

The deterministic engine is the product. These baselines exist so the project
can eventually answer "how would an LLM do the same job, and at what
cost/latency/consistency?" Formal head-to-head benchmarking is future work,
pending finalized clinical gold labels — so nothing here computes accuracy.
"""

from .llm import DECISION_STATES, LLMConfig, triage_with_llm

__all__ = ["DECISION_STATES", "LLMConfig", "triage_with_llm"]
