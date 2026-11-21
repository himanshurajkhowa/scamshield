"""Explainable text heuristics. URL parsing is offline: no DNS or HTTP requests."""

import re

from .contracts import Signal, URLAnalysis
from .urls import inspect_urls

CREDENTIAL_REQUEST_PATTERN = re.compile(
    r"\b(share|send|tell|provide|enter|batao|bhejo|do)\b.{0,45}"
    r"\b(otp|upi\s*pin|password)\b|\b(otp|upi\s*pin|password)\b"
    r".{0,25}\b(bhejo|batao)\b"
)
SAFETY_ADVICE_PATTERN = re.compile(r"\b(never|not|don.t|do not|mat|nahi)\b")
KYC_PATTERN = re.compile(r"\b(kyc|pan|aadhaar|aadhar)\b")
ACCOUNT_THREAT_PATTERN = re.compile(r"block|suspend|expire|deactivat|band ho")
URGENCY_PATTERN = re.compile(
    r"\b(urgent|immediately|last warning|within \d+ (?:hours|minutes)|"
    r"arrest|legal action|abhi|jaldi)\b"
)
REWARD_PATTERN = re.compile(r"\b(won|lottery|reward|cashback|refund|prize)\b")
REWARD_ACTION_PATTERN = re.compile(r"claim|pay|fee|click|send|deposit")
DELIVERY_PATTERN = re.compile(r"deliver|parcel|courier|shipment")
DELIVERY_PAYMENT_PATTERN = re.compile(r"pay|fee|charge|payment")


def _requests_credentials(text: str) -> bool:
    """Ignore explicit safety advice using the original clause/negation rules."""
    clauses = re.split(r"[.!?;\n]+", text)
    return any(
        CREDENTIAL_REQUEST_PATTERN.search(clause)
        and not SAFETY_ADVICE_PATTERN.search(clause)
        for clause in clauses
    )


def analyze_rules(
    text: str, url_result: URLAnalysis | None = None
) -> tuple[list[Signal], list[str]]:
    """Evaluate the existing text rules and merge offline URL findings."""
    normalized_text = text.casefold()
    signals: list[Signal] = []

    def add(code: str, title: str, detail: str, weight: int) -> None:
        signals.append(dict(code=code, title=title, detail=detail, weight=weight))

    if _requests_credentials(normalized_text):
        add(
            "credentials", "Request for a secret",
            "The text asks for an OTP, UPI PIN or password. "
            "Never share these with another person.",
            3,
        )
    if (
        KYC_PATTERN.search(normalized_text)
        and ACCOUNT_THREAT_PATTERN.search(normalized_text)
    ):
        add(
            "kyc", "KYC or account-blocking pressure",
            "Identity verification is paired with a threat of losing access.", 2,
        )
    if URGENCY_PATTERN.search(normalized_text):
        add(
            "pressure", "Pressure to act quickly",
            "Urgency can discourage you from checking the sender.", 1,
        )
    if (
        REWARD_PATTERN.search(normalized_text)
        and REWARD_ACTION_PATTERN.search(normalized_text)
    ):
        add(
            "reward", "Reward or refund with a catch",
            "A reward or refund is paired with an action or payment request.", 2,
        )
    if (
        DELIVERY_PATTERN.search(normalized_text)
        and DELIVERY_PAYMENT_PATTERN.search(normalized_text)
    ):
        add(
            "delivery", "Delivery payment request",
            "Check any delivery charge through the courier’s official app "
            "or website.", 1,
        )
    if url_result is None:
        url_result = inspect_urls(text)
    signals.extend(url_result["signals"])
    # Preserve last-value deduplication and the original insertion order.
    signals = list({signal["code"]: signal for signal in signals}.values())
    return signals, url_result["hosts"]
