import datetime as dt
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch


from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DEMO_UPLOAD_BYTES = b"demo-pdf-bytes"

os.environ.setdefault("GEMINI_API_KEY", "test-key")
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient

from main import app
from services.benchmarker import benchmark_all
from services.letter_generator import render_dispute_letter_locally
from services.recovery import (
    AIResponseError,
    DEMO_PDF_SHA256,
    DEMO_PARSED_BILL,
    RECOVERY_CASES,
    UpstreamAIError,
    get_recovery_case_for_upload,
    is_transient_ai_failure,
)


class RecoveryHelpersTest(unittest.TestCase):
    def test_demo_pdf_hash_matches_recovery_case(self):
        with patch("services.recovery.compute_file_sha256", return_value=DEMO_PDF_SHA256):
            case = get_recovery_case_for_upload(DEMO_UPLOAD_BYTES)
        self.assertIsNotNone(case)
        self.assertEqual(case.file_sha256, DEMO_PDF_SHA256)
        self.assertIs(case, RECOVERY_CASES[DEMO_PDF_SHA256])

        cloned = case.clone_parsed_bill()
        cloned["patient"]["name"] = "Changed"
        self.assertEqual(case.parsed_bill["patient"]["name"], "Sarah M Thompson")

    def test_transient_ai_classifier(self):
        self.assertTrue(is_transient_ai_failure(AIResponseError("Gemini returned an empty response.")))
        self.assertTrue(is_transient_ai_failure(UpstreamAIError("Gemini request timed out.")))
        self.assertFalse(is_transient_ai_failure(ValueError("No files uploaded.")))

    def test_local_letter_fallback_contains_expected_fields(self):
        benchmarks = benchmark_all(DEMO_PARSED_BILL["line_items"], "non_facility")
        errors = [
            {
                "title": "Duplicate Charge: IV INFUSION THER/PROPH/DIAG 1ST HR",
                "description": "The first-hour infusion appears twice on the same date.",
                "estimated_overcharge": 478.0,
                "regulation": "CMS Claims Processing Manual, Chapter 23",
            }
        ]
        state_laws = [{"law_name": "Virginia Example Law", "law_citation": "Va. Code § 38.2-3445.01", "summary": "Protects emergency-service patients."}]
        federal_laws = [{"law_name": "No Surprises Act", "law_citation": "Public Law 116-260, Division BB, Title I", "summary": "Protects patients from certain surprise bills."}]

        letter = render_dispute_letter_locally(
            DEMO_PARSED_BILL,
            benchmarks,
            errors,
            state_laws,
            federal_laws,
            state="VA",
        )

        self.assertIn(dt.date.today().isoformat(), letter)
        self.assertIn("Account 784321560", letter)
        self.assertIn("Blue Ridge Regional Medical Center", letter)
        self.assertIn("Your Rights Under State and Federal Law", letter)
        self.assertTrue(letter.strip().endswith("Sarah M Thompson"))


class RecoveryEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.demo_bytes = DEMO_UPLOAD_BYTES

    def test_known_demo_pdf_recovers_from_parse_failure(self):
        case = RECOVERY_CASES[DEMO_PDF_SHA256]
        with patch("routers.analyze.get_recovery_case_for_upload", return_value=case), \
             patch("routers.analyze.parse_bill", new=AsyncMock(side_effect=AIResponseError("Gemini bill parser did not return valid JSON."))), \
             patch("routers.analyze.detect_ai_errors", new=AsyncMock(return_value=[])), \
             patch("routers.analyze.generate_letter", new=AsyncMock(return_value="Recovered letter")):
            response = self.client.post(
                "/api/analyze",
                files={"file": ("demo_bill_realistic.pdf", self.demo_bytes, "application/pdf")},
                data={"state": "VA", "facility_type": "non_facility"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["parsed_bill"]["patient"]["account_number"], "784321560")
        self.assertEqual(payload["dispute_letter"], "Recovered letter")

    def test_known_demo_pdf_uses_seeded_ai_errors_when_ai_audit_fails(self):
        case = RECOVERY_CASES[DEMO_PDF_SHA256]
        with patch("routers.analyze.get_recovery_case_for_upload", return_value=case), \
             patch("routers.analyze.parse_bill", new=AsyncMock(return_value=case.clone_parsed_bill())), \
             patch("routers.analyze.detect_ai_errors", new=AsyncMock(side_effect=UpstreamAIError("request timed out"))), \
             patch("routers.analyze.generate_letter", new=AsyncMock(return_value="Recovered letter")):
            response = self.client.post(
                "/api/analyze",
                files={"file": ("demo_bill_realistic.pdf", self.demo_bytes, "application/pdf")},
                data={"state": "VA", "facility_type": "non_facility"},
            )

        self.assertEqual(response.status_code, 200)
        titles = [error["title"] for error in response.json()["errors"]]
        self.assertIn("Duplicate Charge: IV INFUSION THER/PROPH/DIAG 1ST HR", titles)
        self.assertIn("Unbundling: 80053 + 80048", titles)
        self.assertIn("Questionable Observation Nursing Charge", titles)

    def test_non_matching_file_does_not_replay_demo_recovery(self):
        with patch("routers.analyze.get_recovery_case_for_upload", return_value=None), \
             patch("routers.analyze.parse_bill", new=AsyncMock(side_effect=AIResponseError("Gemini bill parser did not return valid JSON."))):
            response = self.client.post(
                "/api/analyze",
                files={"file": ("other.pdf", b"not-the-demo-pdf", "application/pdf")},
                data={"state": "VA", "facility_type": "non_facility"},
            )

        self.assertEqual(response.status_code, 422)
        self.assertIn("did not return valid JSON", response.json()["detail"])

    def test_generate_letter_endpoint_falls_back_to_local_renderer(self):
        payload = {
            "parsed_bill": DEMO_PARSED_BILL,
            "selected_benchmarks": benchmark_all(DEMO_PARSED_BILL["line_items"], "non_facility")[:2],
            "selected_errors": [
                {
                    "title": "Duplicate Charge: IV INFUSION THER/PROPH/DIAG 1ST HR",
                    "description": "The first-hour infusion appears twice on the same date.",
                    "estimated_overcharge": 478.0,
                    "regulation": "CMS Claims Processing Manual, Chapter 23",
                }
            ],
            "patient_state": "VA",
            "additional_context": "Keep the tone firm and concise.",
        }

        with patch("routers.analyze.generate_letter", new=AsyncMock(side_effect=UpstreamAIError("service unavailable"))):
            response = self.client.post("/api/generate-letter", json=payload)

        self.assertEqual(response.status_code, 200)
        letter = response.json()["dispute_letter"]
        self.assertIn(dt.date.today().isoformat(), letter)
        self.assertIn("Blue Ridge Regional Medical Center", letter)
        self.assertIn("Account 784321560", letter)
        self.assertTrue(letter.strip().endswith("Sarah M Thompson"))

    def test_search_cpt_returns_results_for_office_visit_phrase(self):
        response = self.client.get("/api/search-cpt", params={"q": "office visit"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(len(payload["results"]), 0)
        top_codes = [result["cpt_code"] for result in payload["results"][:5]]
        self.assertTrue(any(code.startswith("992") for code in top_codes))


if __name__ == "__main__":
    unittest.main()
