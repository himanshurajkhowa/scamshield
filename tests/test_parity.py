"""Frozen contracts captured from the unchanged, approved 9d6c339 baseline."""

import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from app import app
from ml.inference import analyze, get_model
from ml.urls import inspect_urls

FIXTURE = Path(__file__).with_name("fixtures") / "baseline_v1.json"
HEADERS = (
    "Content-Type", "Cache-Control", "Content-Security-Policy",
    "X-Content-Type-Options", "Referrer-Policy",
)


def response_contract(response):
    return dict(
        status=response.status_code,
        body=response.get_json(silent=True),
        headers={name: response.headers.get(name) for name in HEADERS},
    )


class BaselineParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads(FIXTURE.read_text())

    def setUp(self):
        self.client = app.test_client()

    def test_active_artifact_is_unchanged(self):
        path = Path(__file__).resolve().parents[1] / "ml/model.joblib"
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            self.baseline["model_sha256"],
        )

    def test_all_analysis_fields_match_baseline(self):
        for case in self.baseline["cases"]:
            with self.subTest(text=case["text"][:100]):
                self.assertEqual(analyze(case["text"]), case["analysis"])
                self.assertEqual(inspect_urls(case["text"]), case["urls"])

    def test_api_bodies_statuses_and_headers_match_baseline(self):
        for case in self.baseline["cases"]:
            with self.subTest(text=case["text"][:100]):
                response = self.client.post(
                    "/api/analyze", json={"message": case["text"]}
                )
                self.assertEqual(response_contract(response), case["api"])

    def test_invalid_requests_match_baseline(self):
        for case in self.baseline["invalid"]:
            with self.subTest(payload=str(case["payload"])[:100]):
                response = self.client.post("/api/analyze", json=case["payload"])
                self.assertEqual(response_contract(response), case["api"])

    def test_thresholds_and_rule_overrides_match_baseline(self):
        model = get_model()
        for case in self.baseline["boundaries"]:
            with self.subTest(text=case["text"], score=case["score"]):
                score = case["score"]
                with patch.object(
                    model, "predict_proba",
                    return_value=np.array([[1 - score, score]]),
                ):
                    self.assertEqual(analyze(case["text"]), case["analysis"])

    def test_readiness_failure_contract(self):
        for error in (FileNotFoundError, ValueError, RuntimeError):
            with self.subTest(error=error.__name__):
                with patch("ml.inference.get_model", side_effect=error):
                    response = self.client.get("/api/health")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(
                    response.json,
                    dict(status="model_unavailable", model_ready=False),
                )
                self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_unexpected_analysis_failure_remains_html_500(self):
        # Freeze, rather than silently fix, the known behavior-changing defect.
        with patch("ml.inference.get_model", side_effect=ValueError):
            with patch.object(app.logger, "error"):
                response = self.client.post(
                    "/api/analyze", json={"message": "Fictional test message"}
                )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.mimetype, "text/html")
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_health_success_contract(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, dict(
            status="ok", model_ready=True, security_checks=True,
            security_revision="url-first-2026-11-21",
        ))
