"""Pydantic models mirroring the database schema and the search RPC.

Per KB_SCAFFOLDING.md §4 and §6. Field names match the Postgres columns
and the RPC parameter names (with ``p_`` prefix) verbatim — these models
exist to validate the round-trip between the parser, the UI form, and
Supabase.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

VehicleType = Literal[
    "city_car",
    "berlina",
    "sw",
    "suv",
    "crossover",
    "monovolume",
    "commercial",
]
Motorization = Literal[
    "benzina",
    "diesel",
    "elettrico",
    "hybrid_benzina",
    "hybrid_diesel",
    "phev",
    "gpl",
    "metano",
]
CustomerType = Literal["b2c", "b2b"]
Gender = Literal["M", "F"]
Transmission = Literal["manuale", "automatico"]
ServiceTag = Literal[
    "manutenzione",
    "rca",
    "soccorso_stradale",
    "infortunio_conducente",
    "kasko",
    "pneumatici",
    "veicolo_sostitutivo",
]


class QuoteRecord(BaseModel):
    """One row of the ``quotations`` table.

    The Optional/required split mirrors the schema: only the fields needed
    to make the row useful for search are required (offer_number, customer
    name+type, vehicle brand+model+type, motorization, duration, km, fee).
    Everything else is nullable so partial parses still persist.
    """

    model_config = ConfigDict(extra="ignore")

    # Provenance (server-managed)
    id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    uploaded_by: Optional[str] = None
    pdf_url: Optional[str] = None
    vendor: str = "arval"

    # Offer / customer
    offer_number: str
    customer_code: Optional[str] = None
    customer_type: CustomerType
    customer_first_name: str
    customer_last_name: str
    customer_fiscal_code: Optional[str] = None
    customer_birth_date: Optional[date] = None
    customer_gender: Optional[Gender] = None
    customer_birth_place: Optional[str] = None
    customer_address_city: Optional[str] = None
    customer_address_province: Optional[str] = None
    customer_address_cap: Optional[str] = None

    # Vehicle
    vehicle_brand: str
    vehicle_model: str
    vehicle_version: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_type: VehicleType
    motorization: Motorization
    power_kw: Optional[int] = None
    co2_emissions: Optional[int] = None
    transmission: Optional[Transmission] = None

    # Commercials
    list_price: Optional[float] = None
    optional_price: Optional[float] = None
    duration_months: int = Field(gt=0)
    km_total: int = Field(ge=0)
    monthly_fee: float = Field(ge=0)
    monthly_fee_lease: Optional[float] = None
    monthly_fee_services: Optional[float] = None
    anticipo: Optional[float] = None
    deposito: Optional[float] = None

    # Services
    services_included: Optional[list[ServiceTag]] = None
    services_excluded: Optional[list[ServiceTag]] = None

    # Provenance JSON
    parsed_raw_json: Optional[dict[str, Any]] = None
    parser_version: Optional[str] = None


class SearchFilters(BaseModel):
    """Filters posted to ``search_quotations`` RPC.

    Key names mirror the SQL function parameters (``p_`` prefix kept) so a
    ``model_dump(exclude_none=True)`` is directly usable as the RPC body.
    """

    model_config = ConfigDict(extra="forbid")

    p_vendor: str = "arval"
    p_customer_type: Optional[CustomerType] = None
    p_target_monthly_fee: Optional[float] = Field(default=None, ge=0)
    p_target_duration_months: Optional[int] = Field(default=None, gt=0)
    p_target_km_total: Optional[int] = Field(default=None, ge=0)
    p_target_anticipo: Optional[float] = Field(default=None, ge=0)
    p_vehicle_type: Optional[VehicleType] = None
    p_vehicle_brand: Optional[str] = None
    p_motorization: Optional[Motorization] = None
    p_min_score: float = Field(default=0.5, ge=0.0, le=1.0)
    p_limit: int = Field(default=10, gt=0, le=100)
