"""Rulesets: ordered lists of rules that define a triage policy.

``clinic`` is the reference clinical policy (specialty-clinic referral triage);
``demo`` is a tiny generic policy included to show the engine core is not
hardwired to one domain.
"""

from .clinic import CLINIC_RULES
from .demo import DEMO_RULES

__all__ = ["CLINIC_RULES", "DEMO_RULES"]
