from google import genai
from google.genai import types
import datetime
import json
import re
from config import GEMINI_API_KEY, GEMINI_LETTER_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)


def _response_text(response) -> str:
    text = getattr(response, "text", None)
    if text:
        return text.strip()

    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                return part_text.strip()

    return ""


DATE_LINE_RE = re.compile(r"^\s*(\[\s*Date\s*\]|[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})\s*$")

LETTER_PROMPT = """You are a medical billing advocate writing a formal dispute letter on behalf of a patient. Generate a professional dispute letter based on the following analysis.

LETTER METADATA:
- Exact letter date to use: {today_date}
- Sender and signatory: {sender_name}

PATIENT INFORMATION:
- Name: {patient_name}
- Account Number: {account_number}
- Date of Service: {date_of_service}

PROVIDER:
- Name: {provider_name}
- Address: {provider_address}

PRICING ISSUES FOUND:
{benchmarks_text}

BILLING ERRORS FOUND:
{errors_text}

TOTAL BILLED: ${total_billed}
ESTIMATED FAIR PRICE: ${fair_total}
POTENTIAL SAVINGS: ${potential_savings}

PATIENT'S STATE: {state}

APPLICABLE STATE LAWS:
{state_laws_text}

APPLICABLE FEDERAL LAWS:
{federal_laws_text}

ADDITIONAL CONTEXT FROM PATIENT: {additional_context}

LETTER REQUIREMENTS:
- Format as a proper business letter using this exact date at the top: {today_date}
- Write in the patient's voice. The sender and person signing the letter is exactly: {sender_name}
- Close the letter with the patient's name as the signature: {sender_name}
- Do not invent an advocate, lawyer, organization, mailing address, phone number, or email for the sender. If sender contact details are unavailable, omit them.
- Return plain text only. Do not use markdown formatting such as **bold**, bullet asterisks, or code fences.
- Address to "Billing Department" at the provider
- Open with a clear statement of purpose: disputing specific charges
- For EACH pricing issue with severity "moderate", "high", or "critical": state the CPT code, what was charged, what the Medicare rate is, and what a fair commercial rate would be. Cite "CMS Medicare Physician Fee Schedule" as your source.
- For EACH billing error: explain what the error is, cite the relevant regulation, and state the expected correction amount
- Include a dedicated section titled "Your Rights Under State and Federal Law" that cites each applicable state law by name and statute citation (e.g., "Under the Virginia Balance Billing Protection Act, Va. Code § 38.2-3445.01, ..."). Also cite applicable federal protections like the No Surprises Act.
- Request a complete itemized re-review of all charges
- Request a written response within 30 business days
- State that if the dispute is not resolved satisfactorily, you will escalate to the {state} State Insurance Commissioner and/or file a complaint with CMS, citing the specific laws that may have been violated
- Close professionally
- The tone should be firm, factual, and professional. Not threatening, not apologetic.
- Do NOT include placeholder brackets or instructions — this should be ready to print and mail

Return ONLY the letter text, no additional commentary.
"""


def _apply_letter_metadata(letter: str, today_date: str, sender_name: str) -> str:
    """Normalize the returned letter so the date and signature stay anchored to the patient."""
    lines = letter.strip().splitlines()
    if not lines:
        return letter.strip()

    date_applied = False
    for idx, line in enumerate(lines[:15]):
        if DATE_LINE_RE.match(line):
            lines[idx] = today_date
            date_applied = True
            break

    if not date_applied:
        lines = [today_date, ""] + lines

    tail = [line.strip() for line in lines[-8:]]
    if sender_name and sender_name not in tail:
        lines.extend(["", "Sincerely,", "", sender_name])

    return "\n".join(lines).strip()


def _plain_text_letter(letter: str) -> str:
    """Strip common markdown styling so the saved letter is ready to send."""
    cleaned = letter.replace("\r\n", "\n")
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"^\s*#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*[\*\-]\s+", "- ", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _format_benchmarks(benchmarks: list) -> str:
    if not benchmarks:
        return "- None"

    def money(value):
        return f"${float(value):.2f}" if value is not None else "N/A"

    lines = []
    for benchmark in benchmarks:
        medicare_rate = benchmark.get("medicare_rate")
        fair_low = benchmark.get("fair_price_low")
        fair_mid = benchmark.get("fair_price_mid")
        fair_high = benchmark.get("fair_price_high")
        lines.append(
            f"- CPT {benchmark.get('cpt_code')}: {benchmark.get('description')} | charged {money(benchmark.get('charged') or 0)} | "
            f"Medicare {money(medicare_rate)} | "
            f"fair range {money(fair_low)} to {money(fair_high)} | "
            f"fair target {money(fair_mid)} | "
            f"potential savings {money(benchmark.get('potential_savings') or 0)} | severity {benchmark.get('severity')}"
        )
    return "\n".join(lines)


def _format_errors(errors: list) -> str:
    if not errors:
        return "- None"

    lines = []
    for error in errors:
        affected = ", ".join(
            f"{item.get('cpt_code') or 'N/A'} ({item.get('description') or 'Unknown'})"
            for item in error.get("affected_items", [])
        ) or "Not specified"
        lines.append(
            f"- {error.get('title')} | type {error.get('type')} | affected items: {affected} | "
            f"estimated overcharge ${float(error.get('estimated_overcharge') or 0):.2f} | "
            f"regulation: {error.get('regulation')}"
        )
    return "\n".join(lines)


def _format_laws(laws: list) -> str:
    if not laws:
        return "- None"

    return "\n".join(
        f"- {law.get('law_name')} ({law.get('law_citation')}): {law.get('summary')}"
        for law in laws
    )


async def generate_letter(parsed_bill: dict, benchmarks: list, errors: list, state_laws: list, federal_laws: list, state: str = "VA", additional_context: str = "") -> str:
    """Generate a dispute letter from analysis results, including state-specific legal citations."""

    # Filter benchmarks to only include moderate+ severity
    flagged_benchmarks = [b for b in benchmarks if b.get("severity") in ("moderate", "high", "critical")]

    patient = parsed_bill.get("patient", {})
    provider = parsed_bill.get("provider", {})
    today_date = datetime.date.today().isoformat()
    sender_name = patient.get("name") or "The Patient"

    fair_total = sum(
        b["fair_price_mid"] if b.get("fair_price_mid") is not None else (b.get("charged") or 0)
        for b in benchmarks
    )
    total_billed = parsed_bill.get("total_billed", 0)
    potential_savings = round(total_billed - fair_total, 2)

    prompt = LETTER_PROMPT.format(
        today_date=today_date,
        sender_name=sender_name,
        patient_name=patient.get("name", "[Patient Name]"),
        account_number=patient.get("account_number", "[Account Number]"),
        date_of_service=patient.get("date_of_service", "[Date]"),
        provider_name=provider.get("name", "[Provider Name]"),
        provider_address=provider.get("address", "[Provider Address]"),
        benchmarks_text=_format_benchmarks(flagged_benchmarks),
        errors_text=_format_errors(errors),
        total_billed=total_billed,
        fair_total=round(fair_total, 2),
        potential_savings=max(0, potential_savings),
        state=state,
        state_laws_text=_format_laws(state_laws),
        federal_laws_text=_format_laws(federal_laws),
        additional_context=additional_context or "None provided.",
    )

    response = client.models.generate_content(
        model=GEMINI_LETTER_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=3000,
        ),
    )

    return _plain_text_letter(_apply_letter_metadata(_response_text(response), today_date, sender_name))
