from fastapi import APIRouter, HTTPException, Query
import sqlite3
from config import DATABASE_PATH

router = APIRouter()
DB_PATH = DATABASE_PATH


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
            "SELECT cpt_code, description, non_facility_price, facility_price FROM medicare_rates WHERE cpt_code LIKE ? LIMIT ?",
            (f"{stripped}%", limit)
        )
    else:
        # Search by description keywords (AND logic: all words must match)
        words = stripped.split()
        conditions = " AND ".join(["description LIKE ?" for _ in words])
        params = [f"%{word}%" for word in words]
        cursor = conn.execute(
            f"SELECT cpt_code, description, non_facility_price, facility_price FROM medicare_rates WHERE {conditions} ORDER BY non_facility_price DESC LIMIT ?",
            params + [limit]
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
