"""Contratos de dados entre motor estatístico e pipeline de raciocínio."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SampleInfo(BaseModel):
    matches_home_season: int = Field(ge=0)
    matches_away_season: int = Field(ge=0)
    thin_data: bool


class LambdaPair(BaseModel):
    home: float = Field(ge=0)
    away: float = Field(ge=0)


class PriorProbabilities(BaseModel):
    home: float = Field(ge=0, le=1)
    draw: float = Field(ge=0, le=1)
    away: float = Field(ge=0, le=1)


class DerivedProbabilities(BaseModel):
    over_25: float | None = Field(default=None, ge=0, le=1)
    btts: float | None = Field(default=None, ge=0, le=1)


class StandardErrors(BaseModel):
    home: float = Field(ge=0)
    draw: float = Field(ge=0)
    away: float = Field(ge=0)


class StatisticalPrior(BaseModel):
    """Saída do estágio 0 — consumida pelo pipeline inteiro."""

    match_id: str
    model_version: str = "poisson-dc-v0.1"
    sample: SampleInfo
    lambda_: LambdaPair = Field(alias="lambda")
    p_prior: PriorProbabilities
    derived: DerivedProbabilities = Field(default_factory=DerivedProbabilities)
    se_prior: StandardErrors
    already_in_model: list[str] = Field(
        default_factory=lambda: ["home_advantage", "recent_form_via_elo"]
    )
    calibration_bucket: str

    model_config = {"populate_by_name": True}


MarketType = Literal["h2h", "totals", "btts", "double_chance", "corners"]
ValueDecision = Literal["VALUE", "NOISE", "ABSTAIN"]
RiskLabel = Literal["conservative", "moderate", "risky"]


class ValueGateInput(BaseModel):
    """Input para o estágio 5 — motor de value (código, não LLM)."""

    p_adj: float = Field(ge=0, le=1)
    se_adj: float = Field(ge=0)
    p_fair: float = Field(ge=0, le=1)
    information_completeness: float = Field(ge=0, le=1)
    thin_data: bool
    k_multiplier: float = Field(default=1.75, ge=1.0)
    completeness_threshold: float = Field(default=0.7, ge=0, le=1)


class ValueGateResult(BaseModel):
    edge: float
    decision: ValueDecision
    reason: str
