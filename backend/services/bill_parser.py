from google import genai
from google.genai import types
import json
import re
from pdf2image import convert_from_bytes
import io
from config import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)


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

BILL_PARSING_PROMPT = """You are a medical billing expert. Analyze this medical bill image and extract ALL structured data.

Return ONLY valid JSON (no markdown fences, no explanation) with this exact schema:

{
  "provider": {
    "name": string,
    "address": string or null,
    "npi": string or null,
    "phone": string or null
  },
  "patient": {
    "name": string or null,
    "account_number": string or null,
    "date_of_service": "YYYY-MM-DD" or null,
    "insurance": string or null
  },
  "line_items": [
    {
      "description": string (exact text from bill),
      "cpt_code": string (extract from bill if printed, otherwise infer the most likely CPT/HCPCS code based on the description),
      "cpt_inferred": boolean (true if you inferred the code, false if it was printed on the bill),
      "quantity": number (default 1),
      "unit_charge": number,
      "total_charge": number,
      "date": "YYYY-MM-DD" or null
    }
  ],
  "total_billed": number,
  "insurance_paid": number or null,
  "adjustments": number or null,
  "patient_responsibility": number or null
}

IMPORTANT RULES:
- Extract EVERY line item, even small charges like supplies or facility fees
- If CPT codes are not printed on the bill, INFER them from the description. Use your knowledge of medical billing codes. Set cpt_inferred to true.
- If a line item description is ambiguous, pick the most common CPT code for that service
- All monetary values should be plain numbers (no $ signs, no commas)
- If date_of_service appears once at the top, apply it to all line items
- If the bill shows both "amount billed" and "amount owed", use "amount billed" as the charge for each line item
- Parse ALL pages if multiple images are provided
"""


async def parse_bill(file_bytes: bytes, content_type: str) -> dict:
    """Parse a medical bill image or PDF into structured data."""

    # Convert PDF to images if needed
    if content_type == "application/pdf":
        images = convert_from_bytes(file_bytes, dpi=200)
        image_parts = []
        for img in images:
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            image_parts.append(
                types.Part.from_bytes(data=buffer.getvalue(), mime_type="image/png")
            )
    else:
        image_parts = [
            types.Part.from_bytes(data=file_bytes, mime_type=content_type)
        ]

    # Build the content parts: all images + the prompt
    contents = image_parts + [BILL_PARSING_PROMPT]

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=4096,
        ),
    )

    # Parse the response — handle potential markdown fencing
    raw_text = extract_response_text(response)
    cleaned = re.sub(r"```json\s*|\s*```", "", raw_text).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: try to find JSON object in the response
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
        else:
            raise ValueError("Gemini did not return valid JSON. Raw response: " + raw_text[:500])

    # Validate required fields exist
    validate_parsed_bill(parsed)

    # Add sequential IDs to line items
    for i, item in enumerate(parsed.get("line_items", []), start=1):
        item["id"] = i

    # Calculate parsing confidence based on how many fields were successfully extracted
    parsed["parsing_confidence"] = calculate_confidence(parsed)

    return parsed


def validate_parsed_bill(data: dict):
    """Ensure the parsed bill has minimum required fields."""
    if "line_items" not in data or len(data["line_items"]) == 0:
        raise ValueError("No line items could be extracted from this bill.")
    for item in data["line_items"]:
        if "total_charge" not in item or item["total_charge"] is None:
            raise ValueError(f"Line item missing charge amount: {item.get('description', 'unknown')}")
        if "cpt_code" not in item or item["cpt_code"] is None:
            raise ValueError(f"Could not determine CPT code for: {item.get('description', 'unknown')}")


def calculate_confidence(data: dict) -> float:
    """Estimate confidence in the parsing quality (0-1)."""
    score = 0.0
    total = 0.0

    # Provider info
    total += 3
    if data.get("provider", {}).get("name"):
        score += 1
    if data.get("provider", {}).get("address"):
        score += 1
    if data.get("provider", {}).get("npi"):
        score += 1

    # Patient info
    total += 2
    if data.get("patient", {}).get("date_of_service"):
        score += 1
    if data.get("patient", {}).get("account_number"):
        score += 1

    # Line items
    for item in data.get("line_items", []):
        total += 3
        if item.get("cpt_code"):
            score += 1
        if not item.get("cpt_inferred", True):
            score += 1  # Bonus for printed codes
        if item.get("total_charge") is not None:
            score += 1

    # Totals
    total += 2
    if data.get("total_billed"):
        score += 1
    if data.get("patient_responsibility") is not None:
        score += 1

    return round(score / max(total, 1), 2)
