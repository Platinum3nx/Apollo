#!/usr/bin/env python3
import argparse
import datetime as dt
from pathlib import Path
import sys
import time

import requests


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_A = ROOT / "frontend" / "public" / "sample-bills" / "sample-a.png"


def require(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def request_json(response: requests.Response) -> dict:
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Apollo end-to-end smoke test.")
    parser.add_argument("--api", default="http://localhost:8000/api", help="Apollo API base URL")
    parser.add_argument("--state", default="VA", help="Patient state to test")
    args = parser.parse_args()

    session = requests.Session()
    today = dt.date.today().isoformat()

    start = time.time()

    lookup_99214 = request_json(session.get(f"{args.api}/lookup/99214", timeout=30))
    require((lookup_99214.get("medicare_non_facility") or 0) > 0, "99214 should return a Medicare rate")
    print(f"PASS lookup 99214: ${lookup_99214['medicare_non_facility']:.2f}")

    lookup_80053 = request_json(session.get(f"{args.api}/lookup/80053", timeout=30))
    lab_rate = lookup_80053.get("medicare_non_facility") or 0
    require(lab_rate > 0, "80053 should return a non-zero lab rate")
    print(f"PASS lookup 80053: ${lab_rate:.2f}")

    search_results = request_json(session.get(f"{args.api}/search-cpt", params={"q": "MRI"}, timeout=30))
    require(search_results.get("results"), "MRI search should return results")
    print(f"PASS search-cpt MRI: {len(search_results['results'])} results")

    state_laws = request_json(session.get(f"{args.api}/state-laws/{args.state}", timeout=30))
    require(state_laws.get("state_code") == args.state, f"Expected state_code {args.state}")
    require(len(state_laws.get("laws", [])) > 0, "Expected at least one state law")
    print(f"PASS state-laws {args.state}: {len(state_laws['laws'])} state laws, {len(state_laws['federal_laws'])} federal laws")

    require(SAMPLE_A.exists(), f"Missing sample bill: {SAMPLE_A}")
    analyze_started = time.time()
    with SAMPLE_A.open("rb") as handle:
        analysis = request_json(
            session.post(
                f"{args.api}/analyze",
                files={"file": (SAMPLE_A.name, handle, "image/png")},
                data={"state": args.state, "facility_type": "non_facility"},
                timeout=240,
            )
        )
    analyze_elapsed = time.time() - analyze_started

    summary = analysis.get("summary", {})
    total_billed = summary.get("total_billed") or 0
    total_savings = summary.get("total_potential_savings") or 0
    fair_total = summary.get("estimated_fair_total") or 0

    require(total_savings < total_billed, "Total potential savings should be less than total billed")
    require(fair_total >= 0, "Estimated fair total should never be negative")

    error_titles = [error.get("title") for error in analysis.get("errors", [])]
    require(len(error_titles) == len(set(error_titles)), "Duplicate billing-error findings should be deduped")

    letter = analysis.get("dispute_letter") or ""
    patient_name = analysis.get("parsed_bill", {}).get("patient", {}).get("name") or "The Patient"
    require(today in letter, "Dispute letter should contain today's date")
    require("**" not in letter, "Dispute letter should be plain text without markdown")
    require(letter.strip().endswith(patient_name), "Dispute letter should be signed by the patient")

    print(
        "PASS analyze sample-a: "
        f"{analyze_elapsed:.1f}s, billed ${total_billed:.2f}, "
        f"savings ${total_savings:.2f}, fair total ${fair_total:.2f}"
    )

    flagged_benchmarks = [
        benchmark
        for benchmark in analysis.get("benchmarks", [])
        if benchmark.get("severity") in ("moderate", "high", "critical")
    ]
    regenerate_payload = {
        "parsed_bill": analysis["parsed_bill"],
        "selected_benchmarks": flagged_benchmarks[:2],
        "selected_errors": analysis.get("errors", [])[:2],
        "patient_state": args.state,
        "additional_context": "Keep the letter concise and professional.",
    }
    regenerate = request_json(
        session.post(f"{args.api}/generate-letter", json=regenerate_payload, timeout=240)
    )
    regenerated_letter = regenerate.get("dispute_letter") or ""
    require(today in regenerated_letter, "Regenerated letter should contain today's date")
    require(regenerated_letter.strip().endswith(patient_name), "Regenerated letter should be signed by the patient")
    print("PASS generate-letter: regenerated letter kept date and patient signature")

    elapsed = time.time() - start
    print(f"All smoke tests passed in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
