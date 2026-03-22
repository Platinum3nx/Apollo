import sqlite3
from typing import Optional
from config import DATABASE_PATH

DB_PATH = DATABASE_PATH


def get_medicare_rate(cpt_code: str, facility_type: str = "non_facility") -> Optional[dict]:
    """Look up the Medicare rate for a CPT code."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT cpt_code, description, non_facility_price, facility_price FROM medicare_rates WHERE cpt_code = ?",
        (cpt_code,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    price = row["facility_price"] if facility_type == "facility" else row["non_facility_price"]

    return {
        "cpt_code": row["cpt_code"],
        "description": row["description"],
        "medicare_rate": price,
    }


def benchmark_line_item(line_item: dict, facility_type: str = "non_facility") -> dict:
    """Benchmark a single line item against Medicare rates."""
    cpt = line_item["cpt_code"]
    charged = line_item["total_charge"]

    rate_info = get_medicare_rate(cpt, facility_type)

    if rate_info is None or rate_info["medicare_rate"] is None or rate_info["medicare_rate"] == 0:
        return {
            "line_item_id": line_item["id"],
            "cpt_code": cpt,
            "description": line_item["description"],
            "charged": charged,
            "medicare_rate": None,
            "fair_price_low": None,
            "fair_price_mid": None,
            "fair_price_high": None,
            "overcharge_ratio": None,
            "potential_savings": 0.0,
            "severity": "unknown",
            "note": f"CPT code {cpt} not found in Medicare fee schedule. This may be a non-covered service or an incorrect code."
        }

    medicare_rate = rate_info["medicare_rate"]
    fair_low = round(medicare_rate * 1.5, 2)
    fair_mid = round(medicare_rate * 2.0, 2)
    fair_high = round(medicare_rate * 2.5, 2)

    overcharge_ratio = round(charged / fair_mid, 2) if fair_mid > 0 else 0
    potential_savings = round(max(0, charged - fair_mid), 2)

    if overcharge_ratio <= 1.5:
        severity = "fair"
    elif overcharge_ratio <= 2.5:
        severity = "moderate"
    elif overcharge_ratio <= 4.0:
        severity = "high"
    else:
        severity = "critical"

    return {
        "line_item_id": line_item["id"],
        "cpt_code": cpt,
        "description": line_item["description"],
        "charged": charged,
        "medicare_rate": medicare_rate,
        "fair_price_low": fair_low,
        "fair_price_mid": fair_mid,
        "fair_price_high": fair_high,
        "overcharge_ratio": overcharge_ratio,
        "potential_savings": potential_savings,
        "severity": severity,
    }


def benchmark_all(line_items: list, facility_type: str = "non_facility") -> list:
    """Benchmark all line items from a parsed bill."""
    return [benchmark_line_item(item, facility_type) for item in line_items]
