import sqlite3
from typing import Optional
from config import DATABASE_PATH

DB_PATH = DATABASE_PATH

FEDERAL_LAWS = [
    {
        "law_name": "No Surprises Act",
        "law_citation": "Public Law 116-260, Division BB, Title I",
        "category": "surprise_billing",
        "summary": "Federal law protecting patients from surprise out-of-network bills for emergency services and certain non-emergency services at in-network facilities. Bans balance billing in these scenarios.",
        "applies_to": "emergency, in_network_facility_oon_provider, uninsured",
        "effective_date": "2022-01-01",
        "url": "https://www.cms.gov/nosurprises"
    },
    {
        "law_name": "Hospital Price Transparency Rule",
        "law_citation": "CMS-1717-F2 (45 CFR Part 180)",
        "category": "price_transparency",
        "summary": "Requires all hospitals to publish machine-readable files of standard charges including gross charges and payer-negotiated rates.",
        "applies_to": "all",
        "effective_date": "2021-01-01",
        "url": "https://www.cms.gov/hospital-price-transparency"
    },
    {
        "law_name": "Patient Right to Good Faith Estimate",
        "law_citation": "No Surprises Act, Section 112",
        "category": "dispute_rights",
        "summary": "Uninsured or self-pay patients can request a Good Faith Estimate before care. If the final bill exceeds the estimate by $400+, they can dispute it through the federal Patient-Provider Dispute Resolution process.",
        "applies_to": "uninsured, self_pay",
        "effective_date": "2022-01-01",
        "url": "https://www.cms.gov/nosurprises/consumers/understanding-costs-in-advance"
    }
]

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia"
}


def get_state_laws(state_code: str) -> Optional[dict]:
    """Return all billing protection laws for a given state plus federal laws."""
    state_code = state_code.upper()
    if state_code not in US_STATES:
        return None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM state_laws WHERE state_code = ? ORDER BY category",
        (state_code,)
    )
    rows = cursor.fetchall()
    conn.close()

    state_laws = [dict(row) for row in rows]

    return {
        "state_code": state_code,
        "state_name": US_STATES[state_code],
        "laws": state_laws,
        "federal_laws": FEDERAL_LAWS
    }


def get_laws_for_letter(state_code: str) -> tuple[list, list]:
    """Return state laws and federal laws as separate lists for the letter generator."""
    result = get_state_laws(state_code)
    if result is None:
        return [], FEDERAL_LAWS
    return result["laws"], result["federal_laws"]
