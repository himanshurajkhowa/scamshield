"""Types describing existing analysis dictionaries; no runtime conversion."""

from typing import TypedDict


class Signal(TypedDict):
    code: str
    title: str
    detail: str
    weight: int


class URLLink(TypedDict):
    host: str | None
    scheme: str | None
    reference_match: bool
    challan_reference: bool


class URLAnalysis(TypedDict):
    signals: list[Signal]
    hosts: list[str]
    links: list[URLLink]
    standalone: bool


class Analysis(TypedDict):
    analysis_type: str
    url_analysis: list[URLLink]
    verdict: str
    state: str
    explanation: str
    model_assessment: str
    spam_score: float
    score_note: str
    signals: list[Signal]
    domains: list[str]
    recommendations: list[str]
