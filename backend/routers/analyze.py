import logging

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services.bill_parser import parse_bill
from services.benchmarker import benchmark_all
from services.error_detector import detect_ai_errors, detect_rule_based_errors, finalize_errors
from services.state_laws import get_state_laws
from services.letter_generator import generate_letter, render_dispute_letter_locally
from services.recovery import get_recovery_case_for_upload, is_transient_ai_failure
from models.schemas import GenerateLetterRequest

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/jpg", "application/pdf"}


def _upload_name(upload: UploadFile) -> str:
    return upload.filename or "unnamed file"


def _normalize_uploads(files: list[UploadFile] | None, file: UploadFile | None) -> list[UploadFile]:
    uploads: list[UploadFile] = []

    if files:
        uploads.extend(files)
    if file is not None:
        uploads.append(file)

    return uploads


def _build_error_savings_index(errors: list) -> dict[int, float]:
    """Map deterministic billing-error savings to the line item they would remove or reduce."""
    error_savings_by_item = {}

    for error in errors:
        amount = error.get("estimated_overcharge") or 0
        if not isinstance(amount, (int, float)) or amount <= 0:
            continue

        line_item_id = error.get("primary_line_item_id")
        if not isinstance(line_item_id, int):
            affected_items = error.get("affected_items") or []
            if len(affected_items) == 1:
                candidate_id = affected_items[0].get("id")
                if isinstance(candidate_id, int):
                    line_item_id = candidate_id

        if isinstance(line_item_id, int):
            error_savings_by_item[line_item_id] = max(error_savings_by_item.get(line_item_id, 0.0), float(amount))

    return error_savings_by_item


def _calculate_summary_savings(parsed_bill: dict, benchmarks: list, errors: list) -> dict:
    """
    Calculate savings without double-counting.

    If a line item is both overpriced and involved in a billing error, count only the larger
    of the benchmark savings or the error savings for that line item.
    """
    benchmark_savings_by_item = {
        benchmark["line_item_id"]: max(float(benchmark.get("potential_savings") or 0), 0.0)
        for benchmark in benchmarks
        if isinstance(benchmark.get("line_item_id"), int)
    }
    error_savings_by_item = _build_error_savings_index(errors)

    savings_from_overcharges = 0.0
    savings_from_errors = 0.0

    for item in parsed_bill.get("line_items", []):
        line_item_id = item.get("id")
        charged = max(float(item.get("total_charge") or 0), 0.0)

        benchmark_savings = min(benchmark_savings_by_item.get(line_item_id, 0.0), charged)
        error_savings = min(error_savings_by_item.get(line_item_id, 0.0), charged)

        if error_savings > benchmark_savings:
            savings_from_errors += error_savings
        else:
            savings_from_overcharges += benchmark_savings

    total_billed = max(float(parsed_bill.get("total_billed") or 0), 0.0)
    total_potential_savings = min(savings_from_overcharges + savings_from_errors, total_billed)

    return {
        "total_billed": total_billed,
        "estimated_fair_total": round(max(total_billed - total_potential_savings, 0.0), 2),
        "total_potential_savings": round(total_potential_savings, 2),
        "savings_from_overcharges": round(savings_from_overcharges, 2),
        "savings_from_errors": round(savings_from_errors, 2),
    }


def _build_letter_fallback(
    parsed_bill: dict,
    benchmarks: list,
    errors: list,
    state_laws: list,
    federal_laws: list,
    state: str,
    additional_context: str = "",
    recovery_case=None,
    facility_type: str = "non_facility",
) -> str:
    if (
        recovery_case
        and not additional_context
        and state.upper() == recovery_case.default_state
        and facility_type == recovery_case.default_facility_type
    ):
        return recovery_case.initial_letter

    return render_dispute_letter_locally(
        parsed_bill,
        benchmarks,
        errors,
        state_laws,
        federal_laws,
        state=state,
        additional_context=additional_context,
    )


@router.post("/analyze")
async def analyze_bill(
    files: list[UploadFile] | None = File(None),
    file: UploadFile | None = File(None),
    state: str = Form("VA"),
    facility_type: str = Form("non_facility"),
):
    uploads = _normalize_uploads(files, file)
    if not uploads:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    parser_uploads = []
    for upload in uploads:
        if upload.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type for {_upload_name(upload)}: {upload.content_type}. Upload PNG, JPG, or PDF.",
            )

        file_bytes = await upload.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail=f"Empty file uploaded: {_upload_name(upload)}.")

        parser_uploads.append(
            {
                "filename": _upload_name(upload),
                "content_type": upload.content_type,
                "bytes": file_bytes,
            }
        )

    recovery_case = None
    if len(parser_uploads) == 1:
        recovery_case = get_recovery_case_for_upload(parser_uploads[0]["bytes"])

    # 2. Parse the bill (Gemini Vision)
    try:
        parsed_bill = await parse_bill(parser_uploads)
    except Exception as exc:
        if recovery_case and is_transient_ai_failure(exc):
            logger.warning("Using seeded recovery parse for known demo PDF after parser failure: %s", exc.__class__.__name__)
            parsed_bill = recovery_case.clone_parsed_bill()
        elif isinstance(exc, ValueError):
            raise HTTPException(status_code=422, detail=str(exc))
        elif is_transient_ai_failure(exc):
            raise HTTPException(status_code=502, detail="Apollo could not parse the bill because the AI service was unavailable. Please try again.")
        else:
            raise

    # 3. Benchmark each line item against CMS data
    benchmarks = benchmark_all(parsed_bill["line_items"], facility_type)

    # 4. Detect billing errors (rule-based + AI)
    rule_based_errors = detect_rule_based_errors(parsed_bill["line_items"])
    try:
        ai_errors = await detect_ai_errors(parsed_bill["line_items"], rule_based_errors)
    except Exception as exc:
        if recovery_case and is_transient_ai_failure(exc):
            logger.warning("Using seeded AI recovery findings for known demo PDF after AI audit failure: %s", exc.__class__.__name__)
            ai_errors = recovery_case.clone_seeded_ai_errors(parsed_bill["line_items"])
        elif is_transient_ai_failure(exc):
            logger.warning("Gemini AI error detection failed; continuing with rule-based findings only: %s", exc.__class__.__name__)
            ai_errors = []
        else:
            raise
    errors = finalize_errors(rule_based_errors + ai_errors)

    # 5. Look up state laws
    state_laws_data = get_state_laws(state)
    state_laws = state_laws_data["laws"] if state_laws_data else []
    federal_laws = state_laws_data["federal_laws"] if state_laws_data else []

    # 6. Generate dispute letter (only if there are issues to dispute)
    has_issues = any(b["severity"] in ("moderate", "high", "critical") for b in benchmarks) or len(errors) > 0
    if has_issues:
        try:
            dispute_letter = await generate_letter(
                parsed_bill, benchmarks, errors, state_laws, federal_laws, state
            )
        except Exception as exc:
            if is_transient_ai_failure(exc):
                logger.warning("Falling back to deterministic letter generation after AI failure: %s", exc.__class__.__name__)
                dispute_letter = _build_letter_fallback(
                    parsed_bill,
                    benchmarks,
                    errors,
                    state_laws,
                    federal_laws,
                    state,
                    recovery_case=recovery_case,
                    facility_type=facility_type,
                )
            else:
                raise
    else:
        dispute_letter = ""

    # 7. Compute summary
    savings = _calculate_summary_savings(parsed_bill, benchmarks, errors)
    items_flagged = sum(1 for b in benchmarks if b["severity"] in ("moderate", "high", "critical"))
    items_fair = sum(1 for b in benchmarks if b["severity"] == "fair")

    avg_confidence = 0
    confidence_sources = [
        c for c in (
            [1.0 if b.get("medicare_rate") is not None else 0.3 for b in benchmarks]
            + [e.get("confidence", 0) for e in errors]
        )
        if isinstance(c, (int, float))
    ]
    if confidence_sources:
        avg_confidence = round(sum(confidence_sources) / len(confidence_sources), 2)

    summary = {
        "total_billed": savings["total_billed"],
        "estimated_fair_total": savings["estimated_fair_total"],
        "total_potential_savings": savings["total_potential_savings"],
        "savings_from_overcharges": savings["savings_from_overcharges"],
        "savings_from_errors": savings["savings_from_errors"],
        "overall_confidence": avg_confidence,
        "items_flagged": items_flagged,
        "items_fair": items_fair,
        "errors_found": len(errors),
    }

    return {
        "parsed_bill": parsed_bill,
        "benchmarks": benchmarks,
        "errors": errors,
        "dispute_letter": dispute_letter,
        "patient_state": state,
        "state_laws": state_laws,
        "federal_laws": federal_laws,
        "summary": summary,
    }


@router.post("/generate-letter")
async def regenerate_letter(request: GenerateLetterRequest):
    """Regenerate the dispute letter with user-selected issues."""
    from services.state_laws import get_state_laws as _get_state_laws

    state_laws_data = _get_state_laws(request.patient_state)
    state_laws = state_laws_data["laws"] if state_laws_data else []
    federal_laws = state_laws_data["federal_laws"] if state_laws_data else []

    try:
        letter = await generate_letter(
            request.parsed_bill,
            request.selected_benchmarks,
            request.selected_errors,
            state_laws,
            federal_laws,
            request.patient_state,
            request.additional_context,
        )
    except Exception as exc:
        if is_transient_ai_failure(exc):
            logger.warning("Falling back to deterministic letter regeneration after AI failure: %s", exc.__class__.__name__)
            letter = render_dispute_letter_locally(
                request.parsed_bill,
                request.selected_benchmarks,
                request.selected_errors,
                state_laws,
                federal_laws,
                state=request.patient_state,
                additional_context=request.additional_context,
            )
        else:
            raise

    return {"dispute_letter": letter}


@router.get("/lookup/{cpt_code}")
async def lookup_cpt(cpt_code: str):
    """Look up fair pricing for a specific CPT code."""
    from services.benchmarker import get_medicare_rate

    nf = get_medicare_rate(cpt_code, "non_facility")
    f = get_medicare_rate(cpt_code, "facility")

    if nf is None and f is None:
        raise HTTPException(status_code=404, detail=f"CPT code {cpt_code} not found in database.")

    rate_info = nf or f
    nf_price = nf["medicare_rate"] if nf else None
    f_price = f["medicare_rate"] if f else None
    base_price = nf_price or f_price or 0

    return {
        "cpt_code": rate_info["cpt_code"],
        "description": rate_info["description"],
        "medicare_non_facility": nf_price,
        "medicare_facility": f_price,
        "fair_price_range": {
            "low": round(base_price * 1.5, 2) if base_price else None,
            "mid": round(base_price * 2.0, 2) if base_price else None,
            "high": round(base_price * 2.5, 2) if base_price else None,
        }
    }
