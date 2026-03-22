import sqlite3
import re

from fastapi import APIRouter, HTTPException, Query
from config import DATABASE_PATH

router = APIRouter()
DB_PATH = DATABASE_PATH
NORMALIZED_DESCRIPTION_SQL = (
    "trim(lower("
    "replace(replace(replace(replace(replace(coalesce(description, ''), '/', ' '), '-', ' '), '&', ' '), ',', ' '), '.', ' ')"
    "))"
)


def _normalize_search_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def _word_match(normalized_description: str, word: str) -> bool:
    if len(word) <= 3:
        return f" {word} " in f" {normalized_description} "
    return word in normalized_description


def _description_search_rank(row: sqlite3.Row, normalized_query: str, words: list[str]) -> tuple:
    normalized_description = row["normalized_description"] or ""
    padded_description = f" {normalized_description} "
    matched_words = [word for word in words if _word_match(normalized_description, word)]
    match_count = len(matched_words)
    match_score = sum(max(len(word), 1) for word in matched_words)

    if normalized_description == normalized_query:
        exact_rank = 0
    elif normalized_description.startswith(normalized_query):
        exact_rank = 1
    elif f" {normalized_query} " in padded_description:
        exact_rank = 2
    elif normalized_query in normalized_description:
        exact_rank = 3
    else:
        exact_rank = 4

    description = row["description"] or ""
    return (exact_rank, -match_score, -match_count, len(description), row["cpt_code"])


@router.get("/search-cpt")
async def search_cpt(
    q: str = Query(..., min_length=2, description="Search query for procedure name or CPT code"),
    limit: int = Query(20, ge=1, le=50, description="Max results to return")
):
    """Search CPT codes by description keyword or code prefix."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Check if query looks like a CPT code (starts with digits)
    stripped = q.strip()
    if stripped.isdigit() or (len(stripped) >= 4 and stripped[0].isdigit()):
        # Search by code prefix
        cursor = conn.execute(
            """
            SELECT cpt_code, description, non_facility_price, facility_price
            FROM medicare_rates
            WHERE cpt_code LIKE ?
            ORDER BY
                CASE WHEN cpt_code = ? THEN 0 ELSE 1 END,
                LENGTH(cpt_code) ASC,
                cpt_code ASC
            LIMIT ?
            """,
            (f"{stripped}%", stripped, limit)
        )
    else:
        # Search by description keywords using relevance instead of price-only sorting.
        normalized_query = _normalize_search_text(stripped)
        if not normalized_query:
            conn.close()
            return {"query": q, "results": [], "total_results": 0}

        words = [word for word in normalized_query.split() if word]
        conditions = []
        params = []

        for word in words:
            if len(word) <= 3:
                conditions.append("padded_description LIKE ?")
                params.append(f"% {word} %")
            else:
                conditions.append("normalized_description LIKE ?")
                params.append(f"%{word}%")

        where_clause = " OR ".join(conditions) if conditions else "1 = 1"
        cursor = conn.execute(
            f"""
            SELECT cpt_code, description, non_facility_price, facility_price, normalized_description
            FROM (
                SELECT
                    cpt_code,
                    description,
                    non_facility_price,
                    facility_price,
                    {NORMALIZED_DESCRIPTION_SQL} AS normalized_description,
                    ' ' || {NORMALIZED_DESCRIPTION_SQL} || ' ' AS padded_description
                FROM medicare_rates
            ) matched
            WHERE {where_clause}
            LIMIT 250
            """,
            params
        )

    rows = cursor.fetchall()
    conn.close()

    if not (stripped.isdigit() or (len(stripped) >= 4 and stripped[0].isdigit())):
        rows = sorted(rows, key=lambda row: _description_search_rank(row, normalized_query, words))[:limit]

    results = []
    for row in rows:
        nf_price = row["non_facility_price"]
        f_price = row["facility_price"]
        base_price = nf_price or f_price or 0

        results.append({
            "cpt_code": row["cpt_code"],
            "description": row["description"],
            "medicare_non_facility": nf_price,
            "medicare_facility": f_price,
            "fair_price_range": {
                "low": round(base_price * 1.5, 2) if base_price else None,
                "mid": round(base_price * 2.0, 2) if base_price else None,
                "high": round(base_price * 2.5, 2) if base_price else None,
            }
        })

    return {
        "query": q,
        "results": results,
        "total_results": len(results)
    }


@router.get("/state-laws/{state_code}")
async def get_state_laws_endpoint(state_code: str):
    """Return all billing protection laws for a state plus federal laws."""
    from services.state_laws import get_state_laws
    result = get_state_laws(state_code)
    if result is None:
        raise HTTPException(status_code=404, detail=f"State code '{state_code}' not recognized")
    return result
