from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Finding:
    code: str
    nutrient: str
    severity: Severity
    message: str
    actual: float | None = None
    target_min: float | None = None
    target_max: float | None = None
    unit: str = ""


@dataclass
class NutrientResult:
    nutrient: str
    actual: float
    target_min: float | None
    target_max: float | None
    unit: str
    status: str


@dataclass
class EnergyResult:
    rer: float
    mer: float
    intake_kcal: float
    balance_pct: float


@dataclass
class DietTotals:
    kcal: float
    nutrients: dict
    ingredient_names: list = field(default_factory=list)


@dataclass
class NutritionAssessment:
    energy: EnergyResult
    nutrients: list
    findings: list
