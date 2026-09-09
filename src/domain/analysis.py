"""Domain models for story input and structured analysis output."""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ShortText = Annotated[str, Field(min_length=1, max_length=2_000)]
ListItem = Annotated[str, Field(min_length=1, max_length=1_000)]


class TaskType(str, Enum):
    NEW_FEATURE = "Nueva funcionalidad"
    EVOLUTION = "Evolutivo"
    BUG_FIX = "Corrección de bug"
    TECHNICAL_IMPROVEMENT = "Mejora técnica"
    INTEGRATION = "Integración"
    REFACTOR = "Refactor"
    UNKNOWN = "No lo sé"


class EstimationReadiness(str, Enum):
    READY = "READY"
    READY_WITH_RESERVATIONS = "READY_WITH_RESERVATIONS"
    NOT_READY = "NOT_READY"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class StoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, max_length=250)
    description: str = Field(min_length=20, max_length=12_000)
    acceptance_criteria: str | None = Field(default=None, max_length=8_000)
    technical_context: str | None = Field(default=None, max_length=6_000)
    task_type: TaskType = TaskType.UNKNOWN

    @field_validator("title", "acceptance_criteria", "technical_context", mode="before")
    @classmethod
    def empty_optional_strings_are_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class EstimateRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    optimistic_hours: float = Field(gt=0, le=1_000)
    realistic_hours: float = Field(gt=0, le=1_000)
    pessimistic_hours: float = Field(gt=0, le=1_000)

    @model_validator(mode="after")
    def validate_order(self) -> "EstimateRange":
        if not (
            self.optimistic_hours
            <= self.realistic_hours
            <= self.pessimistic_hours
        ):
            raise ValueError(
                "La estimación debe cumplir optimista <= realista <= pesimista."
            )
        return self


class AnalysisDraft(BaseModel):
    """Provider-facing schema before deterministic estimation policy is applied."""

    model_config = ConfigDict(extra="forbid")

    summary: ShortText
    real_request: ShortText
    impacted_areas: list[ListItem] = Field(default_factory=list, max_length=12)

    provided_facts: list[ListItem] = Field(default_factory=list, max_length=20)
    inferred_points: list[ListItem] = Field(default_factory=list, max_length=20)
    assumptions: list[ListItem] = Field(default_factory=list, max_length=20)
    missing_information: list[ListItem] = Field(default_factory=list, max_length=20)
    blocking_gaps: list[ListItem] = Field(default_factory=list, max_length=15)

    functional_questions: list[ListItem] = Field(default_factory=list, max_length=15)
    technical_questions: list[ListItem] = Field(default_factory=list, max_length=15)
    data_questions: list[ListItem] = Field(default_factory=list, max_length=15)
    integration_questions: list[ListItem] = Field(default_factory=list, max_length=15)

    risks: list[ListItem] = Field(default_factory=list, max_length=15)
    technical_breakdown: list[ListItem] = Field(default_factory=list, max_length=20)

    estimation_readiness: EstimationReadiness
    estimate: EstimateRange | None = None
    confidence: Confidence
    recommendation: ShortText


class AnalysisResult(AnalysisDraft):
    """Final domain result after estimation safety policy has been applied."""

    @model_validator(mode="after")
    def validate_estimation_contract(self) -> "AnalysisResult":
        if self.estimation_readiness is EstimationReadiness.NOT_READY:
            if self.estimate is not None:
                raise ValueError("NOT_READY no puede incluir una estimación de horas.")
            if self.confidence is not Confidence.LOW:
                raise ValueError("NOT_READY debe tener confianza LOW.")
            return self

        if self.estimate is None:
            raise ValueError(
                "READY y READY_WITH_RESERVATIONS requieren un rango de estimación."
            )

        if self.estimation_readiness is EstimationReadiness.READY_WITH_RESERVATIONS:
            if self.confidence is not Confidence.MEDIUM:
                raise ValueError(
                    "READY_WITH_RESERVATIONS debe tener confianza MEDIUM."
                )
        elif self.confidence is Confidence.LOW:
            raise ValueError("READY no puede tener confianza LOW.")

        return self
