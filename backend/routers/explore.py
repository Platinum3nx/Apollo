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

        where_clause = " AND ".join(conditions) if conditions else "1 = 1"
        cursor = conn.execute(
            f"""
            SELECT cpt_code, description, non_facility_price, facility_price
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
            ORDER BY
                CASE
                    WHEN normalized_description = ? THEN 0
                    WHEN normalized_description LIKE ? THEN 1
                    WHEN padded_description LIKE ? THEN 2
                    WHEN normalized_description LIKE ? THEN 3
                    ELSE 4
                END,
                LENGTH(description) ASC,
                cpt_code ASC
            LIMIT ?
            """,
            params
            + [
                normalized_query,
                f"{normalized_query}%",
                f"% {normalized_query} %",
                f"%{normalized_query}%",
                limit,
            ]
        )

    rows = cursor.fetchall()
    conn.close()

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
