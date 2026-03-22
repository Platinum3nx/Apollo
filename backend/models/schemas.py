from pydantic import BaseModel
from typing import Optional


class Provider(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    npi: Optional[str] = None
    phone: Optional[str] = None


class Patient(BaseModel):
    name: Optional[str] = None
    account_number: Optional[str] = None
    date_of_service: Optional[str] = None
    insurance: Optional[str] = None


class LineItem(BaseModel):
    id: int = 0
    description: str
    cpt_code: str
    cpt_inferred: bool = False
    quantity: int = 1
    unit_charge: float = 0.0
    total_charge: float
    date: Optional[str] = None


class ParsedBill(BaseModel):
    provider: Provider = Provider()
    patient: Patient = Patient()
    line_items: list[LineItem] = []
    total_billed: float = 0.0
    insurance_paid: Optional[float] = None
    adjustments: Optional[float] = None
    patient_responsibility: Optional[float] = None
    parsing_confidence: float = 0.0


class FairPriceRange(BaseModel):
    low: Optional[float] = None
    mid: Optional[float] = None
    high: Optional[float] = None


class Benchmark(BaseModel):
    line_item_id: int
    cpt_code: str
    description: str
    charged: float
    medicare_rate: Optional[float] = None
    fair_price_low: Optional[float] = None
    fair_price_mid: Optional[float] = None
    fair_price_high: Optional[float] = None
    overcharge_ratio: Optional[float] = None
    potential_savings: float = 0.0
    severity: str = "unknown"
    note: Optional[str] = None


class AffectedItem(BaseModel):
    cpt_code: Optional[str] = None
    description: Optional[str] = None
    charge: Optional[float] = None


class BillingError(BaseModel):
    id: int = 0
    type: str
    severity: str
    confidence: float
    title: str
    description: str
    affected_items: list = []
    estimated_overcharge: Optional[float] = None
    regulation: str = ""
    recommendation: str = ""


class AnalysisSummary(BaseModel):
    total_billed: float = 0.0
    estimated_fair_total: float = 0.0
    total_potential_savings: float = 0.0
    savings_from_overcharges: float = 0.0
    savings_from_errors: float = 0.0
    overall_confidence: float = 0.0
    items_flagged: int = 0
    items_fair: int = 0
    errors_found: int = 0


class StateLaw(BaseModel):
    law_name: str
    law_citation: str
    category: str
    summary: str
    applies_to: Optional[str] = None
    effective_date: Optional[str] = None
    url: Optional[str] = None


class AnalysisResponse(BaseModel):
    parsed_bill: dict
    benchmarks: list[dict]
    errors: list[dict]
    dispute_letter: str = ""
    state_laws: list[dict] = []
    federal_laws: list[dict] = []
    summary: dict


class GenerateLetterRequest(BaseModel):
    parsed_bill: dict
    selected_benchmarks: list[dict] = []
    selected_errors: list[dict] = []
    patient_state: str = "VA"
    additional_context: str = ""


class CptSearchResult(BaseModel):
    cpt_code: str
    description: Optional[str] = None
    medicare_non_facility: Optional[float] = None
    medicare_facility: Optional[float] = None
    fair_price_range: FairPriceRange = FairPriceRange()


class CptSearchResponse(BaseModel):
    query: str
    results: list[CptSearchResult] = []
    total_results: int = 0
