import sqlite3
from google import genai
from google.genai import types
import json
import re
from config import GEMINI_API_KEY, DATABASE_PATH, GEMINI_ANALYSIS_MODEL
from services.recovery import AIResponseError, UpstreamAIError

client = genai.Client(api_key=GEMINI_API_KEY)
DB_PATH = DATABASE_PATH


def extract_response_text(response) -> str:
    text = getattr(response, "text", None)
    if text:
        return text

    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                return part_text

    return ""

# ──────────────────────────────
# PASS 1: Rule-Based Detection
# ──────────────────────────────


def detect_duplicates(line_items: list) -> list:
    """Find duplicate charges (same CPT code, same date)."""
    errors = []
    seen = {}
    for item in line_items:
        key = (item["cpt_code"], item.get("date"))
        if key in seen:
                errors.append({
                    "type": "duplicate",
                    "severity": "high",
                    "confidence": 0.92,
                    "title": f"Duplicate Charge: {item['description']}",
                "description": f"CPT code {item['cpt_code']} ({item['description']}) appears to be billed twice on {item.get('date', 'the same date')}. Unless two identical procedures were genuinely performed, this is likely an error.",
                    "affected_items": [seen[key], item],
                    "primary_line_item_id": item.get("id"),
                    "estimated_overcharge": item["total_charge"],
                    "regulation": "CMS Claims Processing Manual, Chapter 23 — duplicate claims",
                    "recommendation": "Request removal of the duplicate charge and a refund of the duplicated amount."
                })
        else:
            seen[key] = item
    return errors


def detect_unbundling(line_items: list) -> list:
    """Find codes that should be bundled per CCI edits."""
    errors = []
    conn = sqlite3.connect(DB_PATH)

    codes = [item["cpt_code"] for item in line_items]
    code_to_item = {item["cpt_code"]: item for item in line_items}
    seen_pairs = set()

    for i, code_a in enumerate(codes):
        for code_b in codes[i + 1:]:
            # Check both directions: (a,b) and (b,a)
            cursor = conn.execute(
                """SELECT column1_code, column2_code, modifier_indicator
                   FROM cci_edits
                   WHERE (column1_code = ? AND column2_code = ?)
                      OR (column1_code = ? AND column2_code = ?)""",
                (code_a, code_b, code_b, code_a)
            )
            row = cursor.fetchone()
            if row:
                comprehensive_code = row[0]
                component_code = row[1]
                modifier_indicator = row[2]
                if modifier_indicator == "1":
                    # CMS allows these together with an appropriate modifier, so do not
                    # present them as deterministic unbundling errors.
                    continue

                comp_item = code_to_item.get(component_code, code_to_item.get(code_b))
                pair_key = (comprehensive_code, component_code, comp_item.get("id") if comp_item else None)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                errors.append({
                    "type": "unbundling",
                    "severity": "high",
                    "confidence": 0.85,
                    "title": f"Unbundling: {comprehensive_code} + {component_code}",
                    "description": f"CPT {component_code} ({code_to_item.get(component_code, {}).get('description', 'N/A')}) is a component of {comprehensive_code} ({code_to_item.get(comprehensive_code, {}).get('description', 'N/A')}). Per CMS Correct Coding Initiative rules, these should not be billed separately.",
                    "affected_items": [code_to_item.get(comprehensive_code, {}), code_to_item.get(component_code, {})],
                    "primary_line_item_id": comp_item.get("id") if comp_item else None,
                    "estimated_overcharge": comp_item.get("total_charge", 0) if comp_item else 0,
                    "regulation": "CMS National Correct Coding Initiative (NCCI/CCI) Edits — Procedure-to-Procedure (PTP) edits",
                    "recommendation": f"Request removal of the component code ({component_code}) charge. The comprehensive code ({comprehensive_code}) already covers this service."
                })

    conn.close()
    return errors


# ──────────────────────────────
# PASS 2: AI-Powered Detection
# ──────────────────────────────

ERROR_DETECTION_PROMPT = """You are a medical billing auditor. Analyze the following medical bill line items for potential billing errors.

LINE ITEMS:
{line_items_text}

ALREADY DETECTED (do not repeat these):
{already_found_text}

Check for:
1. UPCODING: Is any E/M visit level (99211-99215) higher than what the combination of other services suggests? A routine visit with basic labs is typically 99213, not 99214 or 99215.
2. UNLIKELY COMBINATIONS: Are any services clinically implausible to have occurred together in the same visit?
3. QUESTIONABLE CHARGES: Are there facility fees, "miscellaneous" charges, or supply charges that seem unusual?

For each issue found, return JSON (no markdown fences):
[
  {{
    "type": "upcoding" | "unlikely_combination" | "questionable_charge",
    "severity": "low" | "medium" | "high",
    "confidence": 0.0-1.0,
    "title": "Short title",
    "description": "Detailed explanation in plain English",
    "affected_cpt_codes": ["99214", ...],
    "estimated_overcharge": number or null,
    "recommendation": "What the patient should do"
  }}
]

If no additional issues are found, return an empty array: []

Be conservative. Only flag issues where you have reasonable confidence. Do not repeat errors already detected.
"""


async def detect_ai_errors(line_items: list, already_found: list) -> list:
    """Use Gemini to detect upcoding and unlikely combinations."""
    line_items_text = "\n".join(
        f"- Line item {item.get('id')}: CPT {item.get('cpt_code')}, description: {item.get('description')}, "
        f"date: {item.get('date') or 'unknown'}, charge: ${float(item.get('total_charge') or 0):.2f}"
        for item in line_items
    )
    already_found_text = "\n".join(
        f"- {error['type']}: {error['title']}"
        for error in already_found
    ) or "- None"

    prompt = ERROR_DETECTION_PROMPT.format(
        line_items_text=line_items_text,
        already_found_text=already_found_text,
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_ANALYSIS_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=1024,
            ),
        )
    except Exception as exc:
        raise UpstreamAIError("Gemini billing error detector request failed.") from exc

    raw_text = extract_response_text(response)
    if not raw_text.strip():
        raise AIResponseError("Gemini billing error detector returned an empty response.")
    cleaned = re.sub(r"```json\s*|\s*```", "", raw_text).strip()

    try:
        ai_errors = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIResponseError("Gemini billing error detector did not return valid JSON.") from exc

    if not isinstance(ai_errors, list):
        raise AIResponseError("Gemini billing error detector returned an invalid JSON shape.")

    # Enrich AI errors with regulation citations and map affected items
    code_to_item = {item["cpt_code"]: item for item in line_items}
    enriched = []
    for error in ai_errors:
        affected_items = [code_to_item[c] for c in error.get("affected_cpt_codes", []) if c in code_to_item]
        enriched.append({
            "type": error.get("type", "questionable_charge"),
            "severity": error.get("severity", "medium"),
            "confidence": error.get("confidence", 0.5),
            "title": error.get("title", "Potential Issue"),
            "description": error.get("description", ""),
            "affected_items": affected_items,
            "primary_line_item_id": affected_items[0].get("id") if len(affected_items) == 1 else None,
            "estimated_overcharge": error.get("estimated_overcharge"),
            "regulation": get_regulation_citation(error.get("type", "")),
            "recommendation": error.get("recommendation", "Review this charge with your provider.")
        })

    return enriched


def get_regulation_citation(error_type: str) -> str:
    """Return the relevant regulation for an error type."""
    citations = {
        "upcoding": "CMS Evaluation and Management (E/M) Documentation Guidelines; OIG Compliance Program Guidance",
        "unlikely_combination": "CMS Medically Unlikely Edits (MUE); Clinical plausibility review",
        "questionable_charge": "Hospital Price Transparency Final Rule (CMS-1717-F2); No Surprises Act, Section 112",
        "duplicate": "CMS Claims Processing Manual, Chapter 23",
        "unbundling": "CMS National Correct Coding Initiative (NCCI) Edits",
    }
    return citations.get(error_type, "CMS billing guidelines")


def _dedupe_errors(errors: list) -> list:
    """Remove duplicate findings caused by repeated CPT pairs or repeated AI output."""
    deduped = []
    seen = set()

    for error in errors:
        affected_ids = tuple(sorted(
            item.get("id")
            for item in error.get("affected_items", [])
            if isinstance(item.get("id"), int)
        ))
        signature = (
            error.get("type"),
            error.get("title"),
            affected_ids,
            round(float(error.get("estimated_overcharge") or 0), 2),
        )
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(error)

    return deduped


# ──────────────────────────────
# Combined Detection Pipeline
# ──────────────────────────────

def detect_rule_based_errors(line_items: list) -> list:
    """Run the deterministic billing checks only."""
    errors = []
    errors.extend(detect_duplicates(line_items))
    errors.extend(detect_unbundling(line_items))
    return errors


def finalize_errors(errors: list) -> list:
    """Deduplicate, sort, and assign stable IDs."""
    errors = _dedupe_errors(errors)
    errors.sort(key=lambda e: e.get("confidence", 0), reverse=True)

    for i, error in enumerate(errors, start=1):
        error["id"] = i

    return errors


async def detect_all_errors(line_items: list) -> list:
    """Run all error detection (rule-based + AI) and return combined results."""
    errors = detect_rule_based_errors(line_items)
    errors.extend(await detect_ai_errors(line_items, errors))
    return finalize_errors(errors)
