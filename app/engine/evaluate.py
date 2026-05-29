from app.engine.allergens import check_allergens
from app.engine.constraints import apply_constraints
from app.engine.energy import compute_mer, compute_rer, resolve_life_stage
from app.engine.models import (
    EnergyResult,
    Finding,
    NutrientResult,
    NutritionAssessment,
    Severity,
)
from app.engine.requirements import get_requirements, resolve_stage

_NUTRIENT_NAMES = {
    "protein_g": "protein", "fat_g": "fat", "carb_g": "carb", "fiber_g": "fiber",
    "calcium_mg": "calcium", "phosphorus_mg": "phosphorus",
    "taurine_mg": "taurine", "sodium_mg": "sodium",
}
_NUTRIENT_UNITS = {
    "protein_g": "g/1000kcal", "fat_g": "g/1000kcal", "carb_g": "g/1000kcal",
    "fiber_g": "g/1000kcal", "calcium_mg": "mg/1000kcal", "phosphorus_mg": "mg/1000kcal",
    "taurine_mg": "mg/1000kcal", "sodium_mg": "mg/1000kcal",
}


def _density(total: float, kcal: float) -> float:
    return total / kcal * 1000 if kcal > 0 else 0.0


def _compare_nutrients(diet, reqs):
    results = []
    findings = []
    for key, bounds in reqs.items():
        if key == "ca_p_ratio" or key not in diet.nutrients:
            continue
        short = _NUTRIENT_NAMES.get(key, key)
        unit = _NUTRIENT_UNITS.get(key, "")
        density = _density(diet.nutrients[key], diet.kcal)
        tmin = bounds.get("min")
        tmax = bounds.get("max")
        status = "ok"
        if tmin is not None and density < tmin:
            status = "low"
            sev = Severity.CRITICAL if density < 0.5 * tmin else Severity.WARNING
            findings.append(Finding(
                code=f"{short}_deficient", nutrient=short, severity=sev,
                message=f"{short} 偏低:{density:.0f} {unit} < 目标 {tmin}",
                actual=round(density, 1), target_min=tmin, target_max=tmax, unit=unit,
            ))
        elif tmax is not None and density > tmax:
            status = "high"
            sev = Severity.CRITICAL if density > 1.5 * tmax else Severity.WARNING
            findings.append(Finding(
                code=f"{short}_excess", nutrient=short, severity=sev,
                message=f"{short} 偏高:{density:.0f} {unit} > 目标 {tmax}",
                actual=round(density, 1), target_min=tmin, target_max=tmax, unit=unit,
            ))
        results.append(NutrientResult(
            nutrient=short, actual=round(density, 1),
            target_min=tmin, target_max=tmax, unit=unit, status=status,
        ))
    return results, findings


def _ca_p_findings(diet, reqs):
    ca = diet.nutrients.get("calcium_mg")
    p = diet.nutrients.get("phosphorus_mg")
    bounds = reqs.get("ca_p_ratio")
    if ca is None or p is None or p <= 0 or bounds is None:
        return []
    ratio = ca / p
    rmin = bounds.get("min", 1.0)
    rmax = bounds.get("max")
    if ratio < 1.0:
        return [Finding(code="ca_p_ratio_inverted", nutrient="calcium", severity=Severity.CRITICAL,
                        message=f"钙磷比倒置:Ca:P = {ratio:.2f}(应 ≥ {rmin})",
                        actual=round(ratio, 2), target_min=rmin, target_max=rmax, unit="ratio")]
    if ratio < rmin:
        return [Finding(code="ca_p_ratio_low", nutrient="calcium", severity=Severity.WARNING,
                        message=f"钙磷比偏低:Ca:P = {ratio:.2f}(应 ≥ {rmin})",
                        actual=round(ratio, 2), target_min=rmin, target_max=rmax, unit="ratio")]
    if rmax is not None and ratio > rmax:
        return [Finding(code="ca_p_ratio_high", nutrient="calcium", severity=Severity.WARNING,
                        message=f"钙磷比偏高:Ca:P = {ratio:.2f}(应 ≤ {rmax})",
                        actual=round(ratio, 2), target_min=rmin, target_max=rmax, unit="ratio")]
    return []


def _energy_findings(balance_pct):
    if balance_pct > 20:
        sev = Severity.CRITICAL if balance_pct > 50 else Severity.WARNING
        return [Finding(code="overfeeding", nutrient="", severity=sev,
                        message=f"热量摄入超出维持需求 {balance_pct:.0f}%",
                        actual=round(balance_pct, 1), unit="%")]
    if balance_pct < -20:
        sev = Severity.CRITICAL if balance_pct < -50 else Severity.WARNING
        return [Finding(code="underfeeding", nutrient="", severity=sev,
                        message=f"热量摄入低于维持需求 {abs(balance_pct):.0f}%",
                        actual=round(balance_pct, 1), unit="%")]
    return []


def _allergen_findings(conflicts):
    return [Finding(code="allergen_conflict", nutrient="", severity=Severity.CRITICAL,
                    message=f"饮食含已知过敏原:{c}") for c in conflicts]


def assess(profile, diet, conditions=None, *, mer_factors=None, requirements_db=None,
           constraints_db=None, allergens_db=None) -> NutritionAssessment:
    """引擎主入口:编排能量、需求、约束、营养素比较、过敏原 → 结构化评估。"""
    conditions = conditions if conditions is not None else profile.get("conditions", [])
    pet_allergens = profile.get("allergens", [])
    species = profile["species"]

    rer = compute_rer(profile["weight_kg"])
    life_stage = resolve_life_stage(profile, conditions)
    mer = compute_mer(profile["weight_kg"], species, life_stage, mer_factors)
    balance_pct = (diet.kcal - mer) / mer * 100 if mer > 0 else 0.0
    energy = EnergyResult(rer=round(rer, 1), mer=round(mer, 1),
                          intake_kcal=round(diet.kcal, 1), balance_pct=round(balance_pct, 1))

    stage = resolve_stage(profile)
    reqs = get_requirements(species, stage, requirements_db)
    reqs, _triggered = apply_constraints(reqs, conditions, constraints_db)

    nutrient_results, findings = _compare_nutrients(diet, reqs)
    findings += _ca_p_findings(diet, reqs)
    findings += _energy_findings(balance_pct)
    conflicts = check_allergens(diet.ingredient_names, pet_allergens, allergens_db)
    findings += _allergen_findings(conflicts)

    return NutritionAssessment(energy=energy, nutrients=nutrient_results, findings=findings)
