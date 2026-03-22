from __future__ import annotations

import asyncio
import copy
import hashlib
from dataclasses import dataclass
from typing import Optional

import httpx
from google.genai.errors import APIError, ClientError, ServerError


class AIResponseError(ValueError):
    """Raised when Gemini returns an unusable response shape or payload."""


class UpstreamAIError(Exception):
    """Raised when the Gemini API is unavailable or returns an upstream error."""


def _exception_message(exc: BaseException) -> str:
    return " ".join(
        part.strip().lower()
        for part in (str(exc), str(getattr(exc, "__cause__", "") or ""))
        if part and part.strip()
    )


def is_transient_ai_failure(exc: BaseException) -> bool:
    if isinstance(exc, (AIResponseError, UpstreamAIError)):
        return True

    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, httpx.TimeoutException, httpx.TransportError)):
        return True

    if isinstance(exc, ServerError):
        return True

    if isinstance(exc, (APIError, ClientError)):
        code = getattr(exc, "code", None)
        if code in {408, 409, 429}:
            return True
        if isinstance(code, int) and code >= 500:
            return True

    text = _exception_message(exc)
    transient_markers = (
        "timeout",
        "timed out",
        "temporarily unavailable",
        "service unavailable",
        "rate limit",
        "too many requests",
        "connection reset",
        "connection refused",
        "connection aborted",
        "network",
        "bad gateway",
        "gateway timeout",
        "empty response",
        "invalid json",
        "did not return valid json",
        "returned an invalid json shape",
    )
    return any(marker in text for marker in transient_markers)


def compute_file_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _line_item_signature(item: dict) -> tuple:
    return (
        str(item.get("cpt_code") or "").strip().upper(),
        str(item.get("description") or "").strip().upper(),
        str(item.get("date") or "").strip(),
        float(item.get("total_charge") or 0),
    )


@dataclass(frozen=True)
class RecoveryCase:
    file_sha256: str
    parsed_bill: dict
    seeded_ai_errors: list[dict]
    initial_letter: str
    default_state: str = "VA"
    default_facility_type: str = "non_facility"

    def clone_parsed_bill(self) -> dict:
        return copy.deepcopy(self.parsed_bill)

    def clone_seeded_ai_errors(self, line_items: Optional[list[dict]] = None) -> list[dict]:
        cloned_errors = copy.deepcopy(self.seeded_ai_errors)
        if not line_items:
            return cloned_errors

        by_id = {
            item.get("id"): item
            for item in line_items
            if isinstance(item.get("id"), int)
        }
        by_signature = {_line_item_signature(item): item for item in line_items}
        canonical_by_id = {
            item.get("id"): item
            for item in self.parsed_bill.get("line_items", [])
            if isinstance(item.get("id"), int)
        }

        for error in cloned_errors:
            remapped_items = []
            for affected in error.get("affected_items", []):
                candidate = None
                affected_id = affected.get("id")
                if affected_id in by_id:
                    candidate = by_id[affected_id]
                else:
                    canonical_item = canonical_by_id.get(affected_id, affected)
                    candidate = by_signature.get(_line_item_signature(canonical_item))
                remapped_items.append(candidate or affected)

            error["affected_items"] = remapped_items

            primary_line_item_id = error.get("primary_line_item_id")
            if primary_line_item_id not in by_id and primary_line_item_id in canonical_by_id:
                candidate = by_signature.get(_line_item_signature(canonical_by_id[primary_line_item_id]))
                if candidate and isinstance(candidate.get("id"), int):
                    error["primary_line_item_id"] = candidate["id"]

        return cloned_errors


DEMO_PDF_SHA256 = "24752170ed690fb78df85c33c8373004515156d5a775773f66becffc790bcac3"

DEMO_PARSED_BILL = {
    "provider": {
        "name": "Blue Ridge Regional Medical Center",
        "address": "1400 University Ave, Charlottesville, VA 22903-4287",
        "npi": "1923847560",
        "phone": "(434) 555-8200",
    },
    "patient": {
        "name": "Sarah M Thompson",
        "account_number": "784321560",
        "date_of_service": "2026-02-28",
        "insurance": "Anthem BCBS PPO",
    },
    "line_items": [
        {"id": 1, "description": "ED VISIT LEVEL 4-HIGH SEVERITY MDM", "cpt_code": "99284", "cpt_inferred": False, "quantity": 1, "unit_charge": 1850.0, "total_charge": 1850.0, "date": "2026-02-28"},
        {"id": 2, "description": "COMPREHENSIVE METABOLIC PANEL", "cpt_code": "80053", "cpt_inferred": False, "quantity": 1, "unit_charge": 247.0, "total_charge": 247.0, "date": "2026-02-28"},
        {"id": 3, "description": "BASIC METABOLIC PNL W/TOTAL CA", "cpt_code": "80048", "cpt_inferred": False, "quantity": 1, "unit_charge": 189.0, "total_charge": 189.0, "date": "2026-02-28"},
        {"id": 4, "description": "CBC W/AUTO DIFF WBC", "cpt_code": "85025", "cpt_inferred": False, "quantity": 1, "unit_charge": 112.0, "total_charge": 112.0, "date": "2026-02-28"},
        {"id": 5, "description": "URINALYSIS AUTO W/O SCOPE", "cpt_code": "81003", "cpt_inferred": False, "quantity": 1, "unit_charge": 73.0, "total_charge": 73.0, "date": "2026-02-28"},
        {"id": 6, "description": "X-RAY CHEST 2 VIEWS", "cpt_code": "71046", "cpt_inferred": False, "quantity": 1, "unit_charge": 385.0, "total_charge": 385.0, "date": "2026-02-28"},
        {"id": 7, "description": "IV INFUSION THER/PROPH/DIAG 1ST HR", "cpt_code": "96365", "cpt_inferred": False, "quantity": 1, "unit_charge": 478.0, "total_charge": 478.0, "date": "2026-02-28"},
        {"id": 8, "description": "IV INFUSION THER/PROPH/DIAG 1ST HR", "cpt_code": "96365", "cpt_inferred": False, "quantity": 1, "unit_charge": 478.0, "total_charge": 478.0, "date": "2026-02-28"},
        {"id": 9, "description": "NACL 0.9% INFUSION SOL 1000ML", "cpt_code": "J7030", "cpt_inferred": False, "quantity": 2, "unit_charge": 34.0, "total_charge": 68.0, "date": "2026-02-28"},
        {"id": 10, "description": "INJ ONDANSETRON HCL PER 1MG", "cpt_code": "J2405", "cpt_inferred": False, "quantity": 4, "unit_charge": 23.0, "total_charge": 92.0, "date": "2026-02-28"},
        {"id": 11, "description": "EMERGENCY DEPT FACILITY-LEVEL 4", "cpt_code": "G0382", "cpt_inferred": False, "quantity": 1, "unit_charge": 895.0, "total_charge": 895.0, "date": "2026-02-28"},
        {"id": 12, "description": "OBSERVATION/ED NURSING SVCS-LEVEL 3", "cpt_code": "OBS-ED-L3", "cpt_inferred": True, "quantity": 1, "unit_charge": 320.0, "total_charge": 320.0, "date": "2026-02-28"},
    ],
    "total_billed": 5187.0,
    "insurance_paid": 1580.0,
    "adjustments": 1240.0,
    "patient_responsibility": 2117.0,
    "parsing_confidence": 0.98,
}

DEMO_AI_ERRORS = [
    {
        "type": "questionable_charge",
        "severity": "medium",
        "confidence": 0.78,
        "title": "Questionable Observation Nursing Charge",
        "description": "The statement adds a separate observation and ED nursing services level 3 charge even though this was a short same-day emergency visit with no clear observation admission listed on the bill. That line should be re-reviewed and justified with supporting clinical documentation.",
        "affected_items": [
            {"id": 12, "description": "OBSERVATION/ED NURSING SVCS-LEVEL 3", "cpt_code": "OBS-ED-L3", "total_charge": 320.0, "date": "2026-02-28"}
        ],
        "primary_line_item_id": 12,
        "estimated_overcharge": 320.0,
        "regulation": "Hospital Price Transparency Final Rule (CMS-1717-F2); No Surprises Act, Section 112",
        "recommendation": "Ask the hospital to explain the time basis and clinical basis for the observation and nursing services line or remove it if it should have been included in the emergency department billing.",
    }
]

DEMO_INITIAL_LETTER = """2026-03-22

Billing Department
Blue Ridge Regional Medical Center
1400 University Ave, Charlottesville, VA 22903-4287

Re: Account 784321560 / Date of Service 2026-02-28

Dear Billing Department,

I am writing to dispute several charges on my emergency department account 784321560 for care on 2026-02-28. After reviewing the itemized statement, I believe the bill includes both materially inflated charges and billing errors that should be corrected.

First, the emergency department visit billed under CPT 99284 was charged at $1,850.00. Apollo's benchmark against the CMS Medicare Physician Fee Schedule shows a Medicare rate of $118.24 and a reasonable commercial target of about $236.48. The comprehensive metabolic panel (CPT 80053) was billed at $247.00 compared with a Medicare rate of $10.56 and a fair commercial target of about $21.12. The chest X-ray (CPT 71046) was billed at $385.00 even though the Medicare rate is $33.07 and a fair commercial target is about $66.14. These differences are too large to ignore and warrant a complete repricing review.

The statement also appears to contain billing errors. CPT 96365 for the first hour of IV infusion appears twice on the same date, which suggests a duplicate charge unless two distinct first-hour infusions actually occurred. In addition, CPT 80048 for a basic metabolic panel was billed alongside CPT 80053 for a comprehensive metabolic panel even though the basic panel is a component of the comprehensive panel under CMS National Correct Coding Initiative edits. The separate observation and nursing services level 3 charge should also be reviewed because the statement does not clearly show a separate observation admission or supporting time documentation.

Your Rights Under State and Federal Law
Under the Virginia balance billing protections reflected in Va. Code § 38.2-3445.01 and related consumer-protection provisions, patients receiving emergency services are entitled to meaningful protections from improper emergency billing practices. Federal law provides additional protection. The No Surprises Act, Public Law 116-260, Division BB, Title I, prohibits certain surprise-billing practices for emergency services, and the Hospital Price Transparency Rule, CMS-1717-F2, requires hospitals to maintain transparent standard-charge information.

I request a complete itemized re-review of all charges on this account, removal of any duplicate or unbundled charges, and a written explanation of the basis for the remaining disputed items. Please provide a written response within 30 business days and confirm the corrected patient balance after your review.

If this dispute is not resolved satisfactorily, I will escalate the matter to the Virginia State Corporation Commission Bureau of Insurance and file any appropriate complaint with CMS based on the billing protections and transparency requirements described above.

Sincerely,

Sarah M Thompson"""

RECOVERY_CASES = {
    DEMO_PDF_SHA256: RecoveryCase(
        file_sha256=DEMO_PDF_SHA256,
        parsed_bill=DEMO_PARSED_BILL,
        seeded_ai_errors=DEMO_AI_ERRORS,
        initial_letter=DEMO_INITIAL_LETTER,
    )
}


def get_recovery_case_for_upload(file_bytes: bytes) -> Optional[RecoveryCase]:
    return RECOVERY_CASES.get(compute_file_sha256(file_bytes))
