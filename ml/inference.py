"""Load the saved pipeline and combine its score with offline security signals."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import joblib
if TYPE_CHECKING:
    from sklearn.pipeline import Pipeline

from .contracts import Analysis
from .rules import analyze_rules
from .urls import inspect_urls

SPAM_THRESHOLD = 0.8
REVIEW_THRESHOLD = 0.3
HIGH_RISK_RULE_WEIGHT = 3
MIN_CONFIDENT_WORDS = 4
SCORE_DECIMAL_PLACES = 4
MODEL_PATH = Path(__file__).with_name("model.joblib")


@lru_cache(maxsize=1)
def get_model() -> Pipeline:
    """Load the trusted artifact at most once per process, on first use."""
    return joblib.load(MODEL_PATH)


def _select_verdict(
    score: float, weight: int, uncertain: bool, standalone: bool
) -> tuple[str, str, str]:
    """Apply the original thresholds; standalone URLs ignore the SMS score."""
    verdict_score = 0.0 if standalone else score
    if verdict_score >= SPAM_THRESHOLD or weight >= HIGH_RISK_RULE_WEIGHT:
        return (
            "Potential Scam",
            "danger",
            "This message contains strong warning signs. Pause before replying, "
            "paying or sharing information.",
        )
    if verdict_score >= REVIEW_THRESHOLD or weight > 0 or uncertain or standalone:
        return (
            "Needs a Closer Look",
            "caution",
            "There is not enough clear evidence to trust this message. Check the "
            "sender through an independent channel.",
        )
    return (
        "No Strong Scam Indicators",
        "clear",
        "The checks found no strong warning signs in this text. This does not "
        "establish that the sender or links are safe.",
    )


def _model_assessment(score: float, uncertain: bool) -> str:
    """Describe a spam score without presenting it as a fraud probability."""
    if score >= SPAM_THRESHOLD:
        return "Spam-like"
    if score >= REVIEW_THRESHOLD or uncertain:
        return "Mixed or uncertain"
    return "Mostly non-spam-like"


def analyze(text: str) -> Analysis:
    """Return the existing message/URL analysis schema without retraining."""
    url_result = inspect_urls(text)
    model = get_model()
    score = float(
        model.predict_proba([text])[0][list(model.classes_).index("spam")]
    )
    # Preserve both pipeline calls in this parity-only pass.
    vector = model.named_steps["tfidf"].transform([text])
    signals, hosts = analyze_rules(text, url_result=url_result)
    weight = sum(signal["weight"] for signal in signals)
    uncertain = vector.nnz == 0 or len(text.split()) < MIN_CONFIDENT_WORDS
    verdict, state, explanation = _select_verdict(
        score, weight, uncertain, url_result["standalone"]
    )
    assessment = _model_assessment(score, uncertain)
    if url_result["standalone"]:
        assessment = "Not used for URL-only verdict"
        if state != "danger":
            explanation = (
                "A URL alone cannot establish safety. The hostname was inspected "
                "without opening the link; verify the service independently."
            )
    return dict(
        analysis_type="url" if url_result["standalone"] else "message",
        url_analysis=url_result["links"],
        verdict=verdict,
        state=state,
        explanation=explanation,
        model_assessment=assessment,
        spam_score=round(score, SCORE_DECIMAL_PLACES),
        score_note=(
            "Uncalibrated spam classification score; not a probability of fraud."
        ),
        signals=signals,
        domains=hosts,
        recommendations=[
            "Verify the sender using an official app or a contact you already know.",
            "Never share an OTP, UPI PIN or password.",
            "Do not pay or open a link just because a message pressures you.",
        ],
    )
