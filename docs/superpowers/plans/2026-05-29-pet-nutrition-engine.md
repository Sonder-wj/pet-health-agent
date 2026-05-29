# 宠物营养引擎 实现计划(Plan 1 / 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个纯 Python、零 LLM 依赖、可独立穷举单测的宠物营养评估引擎(`app/engine/`)及其数据文件(`data/`),用黄金测试证明计算正确。

**Architecture:** 引擎是一组对"注入式数据"操作的纯函数 —— 能量计算、营养素分析、需求标准、疾病约束、过敏原检查、综合评估六层。数据(MER 系数 / USDA 食材 / AAFCO-FEDIAF 需求 / 疾病约束 / 过敏原)以带 provenance 的 JSON 存放,由 `data_loader` 加载;引擎函数默认用加载结果,但允许测试注入 fixture,从而保证确定性与可证明性。

**Tech Stack:** Python 3.12 标准库(`json` / `dataclasses` / `enum` / `math` / `pathlib`)+ pytest(已配置 `asyncio_mode=auto`,本计划测试均为同步)。引擎不引入任何新的第三方依赖。

---

## 本计划范围(Plan 1)

**In scope:** `app/engine/` 六模块 + `models.py` + `data_loader.py`;`data/` 五个数据文件(均带 provenance);`tests/` 下对应黄金测试。产出可独立运行 `pytest` 全绿的营养引擎。

**Out of scope(留给后续计划):**
- Plan 2 — Agent 集成:工具层(extract_label_nutrition / lookup_ingredient / compute_energy_requirement / assess_nutrition)、AgentState 改造、图改动、system prompt、config 清理、删除旧医疗代码。
- Plan 3 — 前端适配:Vue UI。

**前置说明:** 本计划只新增 `app/engine/`、`data/`、`tests/test_engine_*.py`,不触碰现有医疗代码,因此可与现有项目共存、独立测试,互不影响。

---

## Prerequisites(开工前一次性确认)

- [ ] 确认虚拟环境已激活:`.\.venv\Scripts\Activate.ps1`
- [ ] 确认 pytest 可用:`pytest --version`(预期打印版本号;若缺失则 `pip install pytest`)
- [ ] 确认在仓库根目录 `E:\develop\pet-health-agent`,且现有项目代码已提交为基线(由 subagent-driven-development 的 worktree 流程负责;若手动执行,先 `git add` 现有 `app/ frontend/ ...` 并提交一个基线 commit,以便 diff 清晰)

---

## File Structure(决策锁定:文件职责与共享接口)

新增文件及职责:

| 文件 | 职责 |
|------|------|
| `app/engine/__init__.py` | 包标记,导出主入口 `assess` |
| `app/engine/models.py` | 数据结构:`Severity` / `Finding` / `NutrientResult` / `EnergyResult` / `DietTotals` / `NutritionAssessment` |
| `app/engine/data_loader.py` | 读取 `data/*.json`、校验 provenance 元信息、返回 `data` 段;提供各数据集的默认加载函数 |
| `app/engine/energy.py` | `compute_rer` / `compute_mer` / `resolve_life_stage`(能量系数阶段) |
| `app/engine/nutrient_analysis.py` | `to_dmb` / `atwater_kcal` / `analyze_homemade` / `analyze_label` |
| `app/engine/requirements.py` | `resolve_stage`(adult/growth)/ `get_requirements` |
| `app/engine/constraints.py` | `apply_constraints`(按疾病覆盖需求目标,返回触发标记) |
| `app/engine/allergens.py` | `check_allergens`(食材名 vs 已知过敏原 → 冲突项) |
| `app/engine/evaluate.py` | `assess`(编排上述模块 → `NutritionAssessment`)及其私有 helper |
| `data/mer_factors.json` | MER 系数表(FEDIAF/WSAVA) |
| `data/ingredients.json` | USDA 食材子集(每 100g 营养谱 + FDC ID) |
| `data/nutrient_requirements.json` | AAFCO/FEDIAF 营养需求(per 1000 kcal ME) |
| `data/disease_constraints.json` | 疾病约束覆盖(IRIS/WSAVA) |
| `data/allergens.json` | 常见食物过敏原别名表 |
| `tests/test_engine_loader.py` | data_loader 测试 |
| `tests/test_engine_energy.py` | 能量计算黄金测试 |
| `tests/test_engine_nutrient.py` | 营养素分析黄金测试 |
| `tests/test_engine_requirements.py` | 需求/阶段测试 |
| `tests/test_engine_constraints.py` | 疾病约束测试 |
| `tests/test_engine_allergens.py` | 过敏原测试 |
| `tests/test_engine_evaluate.py` | 综合评估集成黄金测试 |

### 共享数据结构(最终签名,各 Task 必须一致)

```python
# app/engine/models.py
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Finding:
    code: str                      # 机器码,如 "calcium_deficient" / "ca_p_ratio_inverted"
    nutrient: str                  # 营养素名;非营养素发现用 ""
    severity: Severity
    message: str                   # 人类可读说明
    actual: float | None = None
    target_min: float | None = None
    target_max: float | None = None
    unit: str = ""


@dataclass
class NutrientResult:
    nutrient: str
    actual: float                  # per 1000 kcal 密度
    target_min: float | None
    target_max: float | None
    unit: str
    status: str                    # "ok" | "low" | "high"


@dataclass
class EnergyResult:
    rer: float
    mer: float
    intake_kcal: float
    balance_pct: float             # (intake - mer) / mer * 100


@dataclass
class DietTotals:
    kcal: float
    nutrients: dict                # 键∈{protein_g,fat_g,carb_g,calcium_mg,phosphorus_mg,taurine_mg,sodium_mg,fiber_g}
    ingredient_names: list = field(default_factory=list)


@dataclass
class NutritionAssessment:
    energy: EnergyResult
    nutrients: list                # list[NutrientResult]
    findings: list                 # list[Finding]
```

### 关键函数签名(供后续 Plan 2 工具层调用)

```python
# energy.py
def compute_rer(weight_kg: float) -> float: ...
def compute_mer(weight_kg: float, species: str, life_stage: str, factors: dict | None = None) -> float: ...
def resolve_life_stage(profile: dict, conditions: list[str] | None = None) -> str: ...

# nutrient_analysis.py
def to_dmb(value_pct: float, moisture_pct: float) -> float: ...
def atwater_kcal(protein_g: float, fat_g: float, carb_g: float) -> float: ...
def analyze_homemade(items: list[dict], ingredient_db: dict | None = None) -> DietTotals: ...
def analyze_label(label: dict, amount_g: float, ash_pct: float = 8.0) -> DietTotals: ...

# requirements.py
def resolve_stage(profile: dict) -> str: ...                       # "adult" | "growth"
def get_requirements(species: str, stage: str, db: dict | None = None) -> dict: ...

# constraints.py
def apply_constraints(reqs: dict, conditions: list[str], db: dict | None = None) -> tuple[dict, list[str]]: ...

# allergens.py
def check_allergens(ingredient_names: list[str], pet_allergens: list[str], db: dict | None = None) -> list[str]: ...

# evaluate.py
def assess(profile: dict, diet: DietTotals, conditions: list[str] | None = None, *,
           mer_factors: dict | None = None, requirements_db: dict | None = None,
           constraints_db: dict | None = None, allergens_db: dict | None = None) -> NutritionAssessment: ...
```

**约定的营养素键与单位:** 能量 `kcal`;蛋白/脂肪/碳水/纤维用 `*_g`(克);钙/磷/牛磺酸/钠用 `*_mg`(毫克)。需求(requirements)以 **per 1000 kcal ME** 表达,单位与上述一致(如钙 `calcium_mg` 表示 mg/1000kcal)。Ca:P 以无量纲 `ca_p_ratio:{min,max}` 单列。

---

## Task 1: 包骨架 + 数据结构 + 数据加载器

**Files:**
- Create: `app/engine/__init__.py`
- Create: `app/engine/models.py`
- Create: `app/engine/data_loader.py`
- Create: `data/mer_factors.json`
- Test: `tests/test_engine_loader.py`

- [ ] **Step 1: Write the failing test**

写 `tests/test_engine_loader.py`:

```python
import pytest

from app.engine.data_loader import load_dataset, load_mer_factors
from app.engine.models import Finding, Severity


def test_load_dataset_returns_data_section():
    data = load_dataset("mer_factors")
    assert "dog" in data
    assert "cat" in data
    assert data["cat"]["neutered_adult"] == 1.2


def test_load_dataset_requires_provenance(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text('{"data": {"x": 1}}', encoding="utf-8")
    monkeypatch.setattr("app.engine.data_loader.DATA_DIR", tmp_path)
    with pytest.raises(ValueError, match="provenance"):
        load_dataset("bad")


def test_load_mer_factors_helper():
    factors = load_mer_factors()
    assert factors["dog"]["weight_loss"] == 1.0


def test_finding_dataclass_defaults():
    f = Finding(code="x", nutrient="calcium", severity=Severity.CRITICAL, message="m")
    assert f.actual is None
    assert f.severity == "critical"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.engine'`

- [ ] **Step 3: Write minimal implementation**

`app/engine/__init__.py`:

```python
"""宠物营养引擎:纯 Python、零 LLM、可独立单测。"""
```

`app/engine/models.py`(完整内容见上方"共享数据结构",原样写入):

```python
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
```

`app/engine/data_loader.py`:

```python
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

_REQUIRED_PROVENANCE = ("source", "version", "review_date")
_cache: dict[str, dict] = {}


def load_dataset(name: str) -> dict:
    """读取 data/<name>.json,校验 provenance,返回其 data 段。"""
    if name in _cache:
        return _cache[name]
    path = DATA_DIR / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    missing = [k for k in _REQUIRED_PROVENANCE if k not in raw]
    if missing:
        raise ValueError(f"{name}.json 缺少 provenance 元信息: {missing}")
    data = raw.get("data")
    if data is None:
        raise ValueError(f"{name}.json 缺少 data 段")
    _cache[name] = data
    return data


def _clear_cache() -> None:
    _cache.clear()


def load_mer_factors() -> dict:
    return load_dataset("mer_factors")


def load_ingredients() -> dict:
    return load_dataset("ingredients")


def load_requirements() -> dict:
    return load_dataset("nutrient_requirements")


def load_disease_constraints() -> dict:
    return load_dataset("disease_constraints")


def load_allergens() -> dict:
    return load_dataset("allergens")
```

`data/mer_factors.json`:

```json
{
  "source": "FEDIAF Nutritional Guidelines (2021); WSAVA Global Nutrition Guidelines (2013)",
  "version": "2021",
  "review_date": "2026-05-29",
  "notes": "维持能量需求(MER)= RER × 系数。精选常用生理状态,Demo 子集。",
  "data": {
    "dog": {
      "neutered_adult": 1.6,
      "intact_adult": 1.8,
      "weight_loss": 1.0,
      "juvenile": 2.0,
      "senior": 1.4
    },
    "cat": {
      "neutered_adult": 1.2,
      "intact_adult": 1.4,
      "weight_loss": 0.8,
      "juvenile": 2.5,
      "senior": 1.1
    }
  }
}
```

> 注:`load_dataset` 使用模块级缓存且 `DATA_DIR` 用 `monkeypatch` 可替换。`test_load_dataset_requires_provenance` 用的临时文件名 `bad` 不会进入缓存(读取在缓存判断之后、抛错在缓存写入之前)。

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine_loader.py -v`
Expected: PASS(4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/engine/__init__.py app/engine/models.py app/engine/data_loader.py data/mer_factors.json tests/test_engine_loader.py
git commit -m "feat(engine): add models, data_loader with provenance check, MER factor data"
```

---

## Task 2: 能量计算(RER / MER / 生理阶段)

**Files:**
- Create: `app/engine/energy.py`
- Test: `tests/test_engine_energy.py`

- [ ] **Step 1: Write the failing test**

写 `tests/test_engine_energy.py`:

```python
import pytest

from app.engine.energy import compute_mer, compute_rer, resolve_life_stage


def test_rer_neutered_cat_5kg():
    # RER = 70 × 5^0.75 ≈ 234
    assert compute_rer(5.0) == pytest.approx(234, abs=1)


def test_mer_neutered_cat_5kg():
    # MER = RER × 1.2 ≈ 281
    assert compute_mer(5.0, "cat", "neutered_adult") == pytest.approx(281, abs=2)


def test_rer_dog_10kg():
    # RER = 70 × 10^0.75 ≈ 394
    assert compute_rer(10.0) == pytest.approx(394, abs=1)


def test_mer_dog_10kg_neutered():
    assert compute_mer(10.0, "dog", "neutered_adult") == pytest.approx(630, abs=2)


def test_compute_mer_accepts_injected_factors():
    factors = {"dog": {"neutered_adult": 2.0}}
    assert compute_mer(10.0, "dog", "neutered_adult", factors) == pytest.approx(
        compute_rer(10.0) * 2.0, abs=0.01
    )


def test_resolve_life_stage_obesity_forces_weight_loss():
    profile = {"species": "dog", "age_months": 36, "neutered": True}
    assert resolve_life_stage(profile, ["obesity"]) == "weight_loss"


def test_resolve_life_stage_juvenile():
    profile = {"species": "cat", "age_months": 6, "neutered": False}
    assert resolve_life_stage(profile) == "juvenile"


def test_resolve_life_stage_senior():
    profile = {"species": "dog", "age_months": 96, "neutered": True}
    assert resolve_life_stage(profile) == "senior"


def test_resolve_life_stage_intact_vs_neutered_adult():
    assert resolve_life_stage({"species": "dog", "age_months": 36, "neutered": False}) == "intact_adult"
    assert resolve_life_stage({"species": "dog", "age_months": 36, "neutered": True}) == "neutered_adult"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine_energy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.engine.energy'`

- [ ] **Step 3: Write minimal implementation**

`app/engine/energy.py`:

```python
from app.engine.data_loader import load_mer_factors

JUVENILE_MAX_MONTHS = 12
SENIOR_MIN_MONTHS = 84  # ~7 岁起按老年处理(Demo 简化,WSAVA 生命阶段)


def compute_rer(weight_kg: float) -> float:
    """静息能量需求 RER = 70 × (体重kg)^0.75。"""
    if weight_kg <= 0:
        raise ValueError("weight_kg 必须为正数")
    return 70 * (weight_kg ** 0.75)


def compute_mer(weight_kg: float, species: str, life_stage: str, factors: dict | None = None) -> float:
    """维持能量需求 MER = RER × 系数。factors 可注入,默认从数据加载。"""
    factors = factors if factors is not None else load_mer_factors()
    try:
        factor = factors[species][life_stage]
    except KeyError as e:
        raise ValueError(f"无 {species}/{life_stage} 的 MER 系数") from e
    return compute_rer(weight_kg) * factor


def resolve_life_stage(profile: dict, conditions: list[str] | None = None) -> str:
    """决定能量系数所用生理阶段(优先级:肥胖→幼年→老年→是否绝育)。"""
    conditions = conditions or []
    if "obesity" in conditions:
        return "weight_loss"
    age = profile.get("age_months")
    if age is not None:
        if age < JUVENILE_MAX_MONTHS:
            return "juvenile"
        if age >= SENIOR_MIN_MONTHS:
            return "senior"
    return "neutered_adult" if profile.get("neutered") else "intact_adult"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine_energy.py -v`
Expected: PASS(9 passed)

- [ ] **Step 5: Commit**

```bash
git add app/engine/energy.py tests/test_engine_energy.py
git commit -m "feat(engine): add RER/MER energy calculation and life-stage resolution"
```

---

## Task 3: 营养素分析(DMB / Atwater / 自制 / 商品粮)

**Files:**
- Create: `app/engine/nutrient_analysis.py`
- Create: `data/ingredients.json`
- Test: `tests/test_engine_nutrient.py`

- [ ] **Step 1: Write the failing test**

写 `tests/test_engine_nutrient.py`:

```python
import pytest

from app.engine.models import DietTotals
from app.engine.nutrient_analysis import analyze_homemade, analyze_label, atwater_kcal, to_dmb


def test_dmb_conversion():
    # 粗蛋白 10% as-fed,水分 78% → 干物质蛋白 45.5%
    assert to_dmb(10.0, moisture_pct=78.0) == pytest.approx(45.5, abs=0.1)


def test_dmb_dry_food_unchanged_when_zero_moisture():
    assert to_dmb(30.0, moisture_pct=0.0) == pytest.approx(30.0, abs=0.001)


def test_dmb_rejects_full_moisture():
    with pytest.raises(ValueError):
        to_dmb(10.0, moisture_pct=100.0)


def test_atwater_modified_factors():
    # 修正 Atwater:蛋白 3.5、脂肪 8.5、碳水 3.5 kcal/g
    assert atwater_kcal(protein_g=30, fat_g=10, carb_g=5) == pytest.approx(207.5, abs=0.01)


def test_analyze_homemade_scales_and_sums():
    db = {
        "chicken_breast_cooked": {
            "kcal": 165, "protein_g": 31.0, "fat_g": 3.6, "carb_g": 0.0,
            "calcium_mg": 15, "phosphorus_mg": 228, "taurine_mg": 18,
            "sodium_mg": 74, "fiber_g": 0.0,
        }
    }
    diet = analyze_homemade([{"name": "chicken_breast_cooked", "amount_g": 300}], db)
    assert isinstance(diet, DietTotals)
    assert diet.kcal == pytest.approx(495, abs=0.5)
    assert diet.nutrients["calcium_mg"] == pytest.approx(45, abs=0.5)
    assert diet.nutrients["phosphorus_mg"] == pytest.approx(684, abs=0.5)
    assert diet.ingredient_names == ["chicken_breast_cooked"]


def test_analyze_homemade_unknown_ingredient_raises():
    with pytest.raises(KeyError):
        analyze_homemade([{"name": "unicorn_meat", "amount_g": 100}], {})


def test_analyze_homemade_uses_real_data_default():
    # 不传 db → 走 data/ingredients.json,鸡胸肉必须存在
    diet = analyze_homemade([{"name": "chicken_breast_cooked", "amount_g": 100}])
    assert diet.kcal > 0
    assert diet.nutrients["phosphorus_mg"] > 0


def test_analyze_label_with_kcal():
    label = {"crude_protein_pct": 30, "crude_fat_pct": 12, "crude_fiber_pct": 4,
             "moisture_pct": 10, "kcal_per_kg": 3800}
    diet = analyze_label(label, amount_g=100)
    assert diet.kcal == pytest.approx(380, abs=0.5)
    assert diet.nutrients["protein_g"] == pytest.approx(30, abs=0.5)
    # NFE 碳水 = 100 - 30 - 12 - 4 - 10 - 8(默认灰分) = 36 → 36g/100g
    assert diet.nutrients["carb_g"] == pytest.approx(36, abs=0.5)


def test_analyze_label_without_kcal_uses_atwater():
    label = {"crude_protein_pct": 30, "crude_fat_pct": 12, "crude_fiber_pct": 4, "moisture_pct": 10}
    diet = analyze_label(label, amount_g=100)
    # Atwater: 3.5*30 + 8.5*12 + 3.5*36 = 333
    assert diet.kcal == pytest.approx(333, abs=0.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine_nutrient.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.engine.nutrient_analysis'`

- [ ] **Step 3: Write minimal implementation**

`data/ingredients.json`(USDA FoodData Central 子集,每 100g;数值为 Demo 精选近似值,逐条带 `fdc_id`):

```json
{
  "source": "USDA FoodData Central (SR Legacy / Foundation Foods)",
  "version": "FDC 2019-04 release subset",
  "review_date": "2026-05-29",
  "notes": "每 100g 可食部;taurine 为文献近似值(USDA 不单列牛磺酸)。Demo 精选子集。",
  "data": {
    "chicken_breast_cooked": {"fdc_id": "171077", "name_zh": "鸡胸肉(熟)", "kcal": 165, "protein_g": 31.0, "fat_g": 3.6, "carb_g": 0.0, "calcium_mg": 15, "phosphorus_mg": 228, "taurine_mg": 18, "sodium_mg": 74, "fiber_g": 0.0},
    "chicken_thigh_cooked": {"fdc_id": "187884", "name_zh": "鸡腿肉(熟)", "kcal": 209, "protein_g": 26.0, "fat_g": 10.9, "carb_g": 0.0, "calcium_mg": 12, "phosphorus_mg": 200, "taurine_mg": 30, "sodium_mg": 88, "fiber_g": 0.0},
    "beef_lean_cooked": {"fdc_id": "174032", "name_zh": "瘦牛肉(熟)", "kcal": 217, "protein_g": 26.1, "fat_g": 11.8, "carb_g": 0.0, "calcium_mg": 18, "phosphorus_mg": 201, "taurine_mg": 38, "sodium_mg": 66, "fiber_g": 0.0},
    "salmon_cooked": {"fdc_id": "175168", "name_zh": "三文鱼(熟)", "kcal": 206, "protein_g": 22.1, "fat_g": 12.4, "carb_g": 0.0, "calcium_mg": 15, "phosphorus_mg": 252, "taurine_mg": 130, "sodium_mg": 61, "fiber_g": 0.0},
    "chicken_liver_cooked": {"fdc_id": "171061", "name_zh": "鸡肝(熟)", "kcal": 172, "protein_g": 25.9, "fat_g": 6.5, "carb_g": 0.9, "calcium_mg": 11, "phosphorus_mg": 405, "taurine_mg": 110, "sodium_mg": 80, "fiber_g": 0.0},
    "beef_liver_cooked": {"fdc_id": "169451", "name_zh": "牛肝(熟)", "kcal": 175, "protein_g": 26.5, "fat_g": 4.8, "carb_g": 5.1, "calcium_mg": 6, "phosphorus_mg": 497, "taurine_mg": 68, "sodium_mg": 83, "fiber_g": 0.0},
    "egg_whole_cooked": {"fdc_id": "173424", "name_zh": "全蛋(熟)", "kcal": 155, "protein_g": 12.6, "fat_g": 10.6, "carb_g": 1.1, "calcium_mg": 56, "phosphorus_mg": 198, "taurine_mg": 0, "sodium_mg": 124, "fiber_g": 0.0},
    "rice_white_cooked": {"fdc_id": "169756", "name_zh": "白米饭(熟)", "kcal": 130, "protein_g": 2.7, "fat_g": 0.3, "carb_g": 28.2, "calcium_mg": 10, "phosphorus_mg": 43, "taurine_mg": 0, "sodium_mg": 1, "fiber_g": 0.4},
    "pumpkin_cooked": {"fdc_id": "170491", "name_zh": "南瓜(熟)", "kcal": 20, "protein_g": 0.7, "fat_g": 0.1, "carb_g": 4.9, "calcium_mg": 15, "phosphorus_mg": 30, "taurine_mg": 0, "sodium_mg": 1, "fiber_g": 1.1},
    "carrot_raw": {"fdc_id": "170393", "name_zh": "胡萝卜(生)", "kcal": 41, "protein_g": 0.9, "fat_g": 0.2, "carb_g": 9.6, "calcium_mg": 33, "phosphorus_mg": 35, "taurine_mg": 0, "sodium_mg": 69, "fiber_g": 2.8}
  }
}
```

`app/engine/nutrient_analysis.py`:

```python
from app.engine.data_loader import load_ingredients
from app.engine.models import DietTotals

_NUTRIENT_KEYS = (
    "protein_g", "fat_g", "carb_g",
    "calcium_mg", "phosphorus_mg", "taurine_mg", "sodium_mg", "fiber_g",
)


def to_dmb(value_pct: float, moisture_pct: float) -> float:
    """湿重百分比 → 干物质百分比(DMB)。"""
    if moisture_pct >= 100 or moisture_pct < 0:
        raise ValueError("moisture_pct 必须在 [0, 100)")
    return value_pct / (100 - moisture_pct) * 100


def atwater_kcal(protein_g: float, fat_g: float, carb_g: float) -> float:
    """修正 Atwater(宠物食品):蛋白 3.5、脂肪 8.5、碳水(NFE) 3.5 kcal/g。"""
    return 3.5 * protein_g + 8.5 * fat_g + 3.5 * carb_g


def analyze_homemade(items: list[dict], ingredient_db: dict | None = None) -> DietTotals:
    """自制饮食:逐食材查表 → 按份量缩放 → 跨食材加总。"""
    db = ingredient_db if ingredient_db is not None else load_ingredients()
    totals = {k: 0.0 for k in _NUTRIENT_KEYS}
    kcal = 0.0
    names: list[str] = []
    for item in items:
        name = item["name"]
        if name not in db:
            raise KeyError(f"食材库无此项: {name}")
        entry = db[name]
        scale = item["amount_g"] / 100.0
        kcal += entry.get("kcal", 0.0) * scale
        for k in _NUTRIENT_KEYS:
            totals[k] += entry.get(k, 0.0) * scale
        names.append(name)
    return DietTotals(kcal=kcal, nutrients=totals, ingredient_names=names)


def analyze_label(label: dict, amount_g: float, ash_pct: float = 8.0) -> DietTotals:
    """商品粮:从保证成分分析换算每份摄入;无 kcal 时用 Atwater 反推。"""
    scale = amount_g / 100.0
    protein_pct = label.get("crude_protein_pct", 0.0)
    fat_pct = label.get("crude_fat_pct", 0.0)
    fiber_pct = label.get("crude_fiber_pct", 0.0)
    moisture_pct = label.get("moisture_pct", 0.0)
    carb_pct = max(0.0, 100 - protein_pct - fat_pct - fiber_pct - moisture_pct - ash_pct)

    protein_g = protein_pct * scale
    fat_g = fat_pct * scale
    fiber_g = fiber_pct * scale
    carb_g = carb_pct * scale

    kcal_per_kg = label.get("kcal_per_kg")
    if kcal_per_kg is not None:
        kcal = kcal_per_kg / 1000.0 * amount_g
    else:
        kcal = atwater_kcal(protein_g, fat_g, carb_g)

    nutrients = {"protein_g": protein_g, "fat_g": fat_g, "carb_g": carb_g, "fiber_g": fiber_g}
    return DietTotals(kcal=kcal, nutrients=nutrients, ingredient_names=[])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine_nutrient.py -v`
Expected: PASS(9 passed)

- [ ] **Step 5: Commit**

```bash
git add app/engine/nutrient_analysis.py data/ingredients.json tests/test_engine_nutrient.py
git commit -m "feat(engine): add nutrient analysis (DMB, Atwater, homemade, label) + USDA subset"
```

---

## Task 4: 营养需求标准(阶段判定 + 需求查表)

**Files:**
- Create: `app/engine/requirements.py`
- Create: `data/nutrient_requirements.json`
- Test: `tests/test_engine_requirements.py`

- [ ] **Step 1: Write the failing test**

写 `tests/test_engine_requirements.py`:

```python
import pytest

from app.engine.requirements import get_requirements, resolve_stage


def test_resolve_stage_growth_when_young():
    assert resolve_stage({"species": "dog", "age_months": 6}) == "growth"


def test_resolve_stage_adult_when_mature():
    assert resolve_stage({"species": "cat", "age_months": 36}) == "adult"


def test_resolve_stage_defaults_adult_when_age_unknown():
    assert resolve_stage({"species": "dog"}) == "adult"


def test_get_requirements_adult_dog_has_calcium_min():
    reqs = get_requirements("dog", "adult")
    assert reqs["calcium_mg"]["min"] == 1250
    assert reqs["phosphorus_mg"]["min"] == 1000
    assert reqs["ca_p_ratio"]["min"] == 1.0
    assert reqs["ca_p_ratio"]["max"] == 2.0


def test_get_requirements_adult_cat_has_taurine():
    reqs = get_requirements("cat", "adult")
    assert reqs["taurine_mg"]["min"] == 250
    assert reqs["protein_g"]["min"] == 65


def test_get_requirements_returns_copy_not_shared_reference():
    a = get_requirements("dog", "adult")
    a["calcium_mg"]["min"] = 999
    b = get_requirements("dog", "adult")
    assert b["calcium_mg"]["min"] == 1250


def test_get_requirements_unknown_raises():
    with pytest.raises(ValueError):
        get_requirements("hamster", "adult")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine_requirements.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.engine.requirements'`

- [ ] **Step 3: Write minimal implementation**

`data/nutrient_requirements.json`(per 1000 kcal ME;矿物质单位 mg/1000kcal,常量营养素 g/1000kcal):

```json
{
  "source": "AAFCO Dog/Cat Food Nutrient Profiles (2014); FEDIAF Nutritional Guidelines (2021)",
  "version": "AAFCO-2014 / FEDIAF-2021 subset",
  "review_date": "2026-05-29",
  "notes": "per 1000 kcal ME 基准。Demo 精选关键营养素;成年维持(adult)与生长/繁殖(growth)两套。",
  "data": {
    "dog": {
      "adult": {
        "protein_g": {"min": 45},
        "fat_g": {"min": 13.8},
        "calcium_mg": {"min": 1250, "max": 6250},
        "phosphorus_mg": {"min": 1000},
        "sodium_mg": {"min": 200},
        "ca_p_ratio": {"min": 1.0, "max": 2.0}
      },
      "growth": {
        "protein_g": {"min": 56.3},
        "fat_g": {"min": 21.3},
        "calcium_mg": {"min": 3000, "max": 6250},
        "phosphorus_mg": {"min": 2500},
        "sodium_mg": {"min": 800},
        "ca_p_ratio": {"min": 1.0, "max": 1.8}
      }
    },
    "cat": {
      "adult": {
        "protein_g": {"min": 65},
        "fat_g": {"min": 22.5},
        "calcium_mg": {"min": 1440},
        "phosphorus_mg": {"min": 1250},
        "sodium_mg": {"min": 200},
        "taurine_mg": {"min": 250},
        "ca_p_ratio": {"min": 1.0, "max": 2.0}
      },
      "growth": {
        "protein_g": {"min": 75},
        "fat_g": {"min": 22.5},
        "calcium_mg": {"min": 2400},
        "phosphorus_mg": {"min": 2000},
        "sodium_mg": {"min": 400},
        "taurine_mg": {"min": 250},
        "ca_p_ratio": {"min": 1.0, "max": 1.5}
      }
    }
  }
}
```

`app/engine/requirements.py`:

```python
import copy

from app.engine.data_loader import load_requirements

GROWTH_MAX_MONTHS = 12


def resolve_stage(profile: dict) -> str:
    """需求阶段:幼年(<12 月)按 growth,否则 adult;年龄未知默认 adult。"""
    age = profile.get("age_months")
    if age is not None and age < GROWTH_MAX_MONTHS:
        return "growth"
    return "adult"


def get_requirements(species: str, stage: str, db: dict | None = None) -> dict:
    """返回该物种×阶段的营养需求(深拷贝,避免调用方污染数据)。"""
    data = db if db is not None else load_requirements()
    try:
        reqs = data[species][stage]
    except KeyError as e:
        raise ValueError(f"无 {species}/{stage} 的营养需求") from e
    return copy.deepcopy(reqs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine_requirements.py -v`
Expected: PASS(7 passed)

- [ ] **Step 5: Commit**

```bash
git add app/engine/requirements.py data/nutrient_requirements.json tests/test_engine_requirements.py
git commit -m "feat(engine): add nutrient requirements lookup (AAFCO/FEDIAF subset)"
```

---

## Task 5: 疾病约束(覆盖需求目标)

**Files:**
- Create: `app/engine/constraints.py`
- Create: `data/disease_constraints.json`
- Test: `tests/test_engine_constraints.py`

- [ ] **Step 1: Write the failing test**

写 `tests/test_engine_constraints.py`:

```python
from app.engine.constraints import apply_constraints


def _base_cat_reqs():
    return {
        "protein_g": {"min": 65},
        "phosphorus_mg": {"min": 1250},
        "sodium_mg": {"min": 200},
        "taurine_mg": {"min": 250},
        "ca_p_ratio": {"min": 1.0, "max": 2.0},
    }


def test_no_conditions_returns_unchanged():
    reqs = _base_cat_reqs()
    out, triggered = apply_constraints(reqs, [])
    assert out == reqs
    assert triggered == []


def test_kidney_adds_phosphorus_max_and_lowers_min():
    out, triggered = apply_constraints(_base_cat_reqs(), ["kidney"])
    assert out["phosphorus_mg"]["max"] == 1200
    assert out["phosphorus_mg"]["min"] == 500
    assert out["sodium_mg"]["max"] == 1000
    assert "kidney" in triggered


def test_apply_constraints_does_not_mutate_input():
    reqs = _base_cat_reqs()
    apply_constraints(reqs, ["kidney"])
    assert "max" not in reqs["phosphorus_mg"]


def test_obesity_sets_fat_max_and_fiber_min():
    out, triggered = apply_constraints({"fat_g": {"min": 22.5}}, ["obesity"])
    assert out["fat_g"]["max"] == 30
    assert out["fiber_g"]["min"] == 15
    assert "obesity" in triggered


def test_unknown_condition_ignored():
    out, triggered = apply_constraints(_base_cat_reqs(), ["lycanthropy"])
    assert triggered == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine_constraints.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.engine.constraints'`

- [ ] **Step 3: Write minimal implementation**

`data/disease_constraints.json`:

```json
{
  "source": "IRIS Staging of CKD (2023); WSAVA Global Nutrition Guidelines",
  "version": "IRIS-2023 / WSAVA subset",
  "review_date": "2026-05-29",
  "notes": "按疾病覆盖/收紧需求目标。Demo 精选;限磷为 CKD 管理核心。",
  "data": {
    "kidney": {
      "phosphorus_mg": {"min": 500, "max": 1200},
      "sodium_mg": {"max": 1000}
    },
    "obesity": {
      "fat_g": {"max": 30},
      "fiber_g": {"min": 15}
    },
    "diabetes_cat": {
      "carb_g": {"max": 30},
      "protein_g": {"min": 80}
    },
    "diabetes_dog": {
      "fiber_g": {"min": 20}
    }
  }
}
```

`app/engine/constraints.py`:

```python
import copy

from app.engine.data_loader import load_disease_constraints


def apply_constraints(reqs: dict, conditions: list[str], db: dict | None = None) -> tuple[dict, list[str]]:
    """按疾病覆盖需求目标(min/max 逐键合并)。返回(调整后需求, 触发的疾病码)。"""
    data = db if db is not None else load_disease_constraints()
    out = copy.deepcopy(reqs)
    triggered: list[str] = []
    for cond in conditions:
        overrides = data.get(cond)
        if not overrides:
            continue
        triggered.append(cond)
        for nutrient, bounds in overrides.items():
            target = out.setdefault(nutrient, {})
            for bound_key, value in bounds.items():
                target[bound_key] = value
    return out, triggered
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine_constraints.py -v`
Expected: PASS(5 passed)

- [ ] **Step 5: Commit**

```bash
git add app/engine/constraints.py data/disease_constraints.json tests/test_engine_constraints.py
git commit -m "feat(engine): add disease constraint overrides (IRIS/WSAVA subset)"
```

---

## Task 6: 过敏原检查

**Files:**
- Create: `app/engine/allergens.py`
- Create: `data/allergens.json`
- Test: `tests/test_engine_allergens.py`

- [ ] **Step 1: Write the failing test**

写 `tests/test_engine_allergens.py`:

```python
from app.engine.allergens import check_allergens


def test_detects_conflict_via_alias():
    # 宠物对鸡过敏,饮食含 chicken_breast_cooked → 命中
    conflicts = check_allergens(["chicken_breast_cooked", "rice_white_cooked"], ["chicken"])
    assert "chicken" in conflicts


def test_no_conflict_when_clean():
    conflicts = check_allergens(["rice_white_cooked", "pumpkin_cooked"], ["chicken", "beef"])
    assert conflicts == []


def test_case_insensitive_and_chinese_alias():
    conflicts = check_allergens(["鸡胸肉"], ["chicken"])
    assert "chicken" in conflicts


def test_multiple_allergens():
    conflicts = check_allergens(["beef_liver_cooked", "egg_whole_cooked"], ["beef", "egg", "chicken"])
    assert set(conflicts) == {"beef", "egg"}


def test_unknown_allergen_label_ignored():
    conflicts = check_allergens(["chicken_breast_cooked"], ["plutonium"])
    assert conflicts == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine_allergens.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.engine.allergens'`

- [ ] **Step 3: Write minimal implementation**

`data/allergens.json`:

```json
{
  "source": "Veterinary dermatology literature — common canine/feline food allergens (Mueller et al., 2016)",
  "version": "literature-subset",
  "review_date": "2026-05-29",
  "notes": "过敏原 → 别名/关键词(含中英文及食材库名片段),用子串匹配。",
  "data": {
    "chicken": ["chicken", "poultry", "鸡"],
    "beef": ["beef", "牛"],
    "dairy": ["milk", "cheese", "yogurt", "dairy", "乳", "奶"],
    "egg": ["egg", "蛋"],
    "wheat": ["wheat", "gluten", "小麦", "麸"],
    "soy": ["soy", "soya", "大豆", "豆"],
    "lamb": ["lamb", "mutton", "羊"],
    "fish": ["fish", "salmon", "tuna", "鱼", "三文鱼"],
    "corn": ["corn", "maize", "玉米"]
  }
}
```

`app/engine/allergens.py`:

```python
from app.engine.data_loader import load_allergens


def check_allergens(ingredient_names: list[str], pet_allergens: list[str], db: dict | None = None) -> list[str]:
    """比对饮食成分名 vs 宠物已知过敏原,返回命中的过敏原码(去重、保序)。"""
    data = db if db is not None else load_allergens()
    haystack = " ".join(ingredient_names).lower()
    conflicts: list[str] = []
    for allergen in pet_allergens:
        aliases = data.get(allergen)
        if not aliases:
            continue
        if any(alias.lower() in haystack for alias in aliases):
            if allergen not in conflicts:
                conflicts.append(allergen)
    return conflicts
```

> 注:食材库键名(如 `chicken_breast_cooked`)本身含英文关键词,故子串匹配可命中;中文别名匹配 `name_zh` 或用户自由文本。

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine_allergens.py -v`
Expected: PASS(5 passed)

- [ ] **Step 5: Commit**

```bash
git add app/engine/allergens.py data/allergens.json tests/test_engine_allergens.py
git commit -m "feat(engine): add allergen conflict detection with alias table"
```

---

## Task 7: 综合评估编排(引擎主入口)

**Files:**
- Create: `app/engine/evaluate.py`
- Modify: `app/engine/__init__.py`(导出 `assess`)
- Test: `tests/test_engine_evaluate.py`

- [ ] **Step 1: Write the failing test**

写 `tests/test_engine_evaluate.py`(集成黄金测试 —— 对照公开标准算例):

```python
import pytest

from app.engine.evaluate import assess
from app.engine.models import DietTotals, Severity
from app.engine.nutrient_analysis import analyze_homemade, analyze_label


def test_homemade_allmeat_low_calcium_flagged():
    profile = {"species": "dog", "weight_kg": 10, "age_months": 36, "neutered": True}
    diet = analyze_homemade([{"name": "chicken_breast_cooked", "amount_g": 300}])
    result = assess(profile, diet)
    assert any(f.nutrient == "calcium" and f.severity == Severity.CRITICAL for f in result.findings)
    assert any(f.code == "ca_p_ratio_inverted" for f in result.findings)


def test_kidney_cat_high_phosphorus_flagged():
    profile = {"species": "cat", "weight_kg": 4, "age_months": 60, "neutered": True, "conditions": ["kidney"]}
    diet = DietTotals(kcal=240, nutrients={"phosphorus_mg": 720, "calcium_mg": 900,
                                           "taurine_mg": 80, "protein_g": 40}, ingredient_names=[])
    result = assess(profile, diet)
    assert any(f.nutrient == "phosphorus" and f.severity == Severity.CRITICAL for f in result.findings)


def test_homemade_cat_taurine_deficiency_flagged():
    profile = {"species": "cat", "weight_kg": 4, "age_months": 36, "neutered": True}
    diet = DietTotals(kcal=240, nutrients={"taurine_mg": 0.0, "protein_g": 40, "fat_g": 15,
                                           "calcium_mg": 360, "phosphorus_mg": 300}, ingredient_names=[])
    result = assess(profile, diet)
    assert any(f.nutrient == "taurine" for f in result.findings)


def test_balanced_dog_diet_no_critical_findings():
    profile = {"species": "dog", "weight_kg": 10, "age_months": 36, "neutered": True}
    diet = DietTotals(kcal=630, nutrients={
        "protein_g": 50, "fat_g": 20, "carb_g": 30, "fiber_g": 5,
        "calcium_mg": 900, "phosphorus_mg": 700, "sodium_mg": 200,
    }, ingredient_names=["balanced_mix"])
    result = assess(profile, diet)
    assert all(f.severity != Severity.CRITICAL for f in result.findings)


def test_overfeeding_flagged_and_mer_correct():
    profile = {"species": "dog", "weight_kg": 10, "age_months": 36, "neutered": True}
    diet = DietTotals(kcal=1200, nutrients={"calcium_mg": 1800, "phosphorus_mg": 1400}, ingredient_names=[])
    result = assess(profile, diet)
    assert any(f.code == "overfeeding" for f in result.findings)
    assert result.energy.mer == pytest.approx(630, abs=2)
    assert result.energy.intake_kcal == 1200


def test_allergen_conflict_flagged():
    profile = {"species": "dog", "weight_kg": 10, "age_months": 36, "neutered": True, "allergens": ["chicken"]}
    diet = analyze_homemade([{"name": "chicken_breast_cooked", "amount_g": 200}])
    result = assess(profile, diet)
    assert any(f.code == "allergen_conflict" for f in result.findings)


def test_commercial_label_diet_skips_missing_minerals():
    profile = {"species": "cat", "weight_kg": 4, "age_months": 36, "neutered": True}
    label = {"crude_protein_pct": 32, "crude_fat_pct": 14, "crude_fiber_pct": 3,
             "moisture_pct": 10, "kcal_per_kg": 4000}
    diet = analyze_label(label, amount_g=60)
    result = assess(profile, diet)
    nutrient_names = {f.nutrient for f in result.findings}
    assert "calcium" not in nutrient_names
    assert "taurine" not in nutrient_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine_evaluate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.engine.evaluate'`

- [ ] **Step 3: Write minimal implementation**

`app/engine/evaluate.py`:

```python
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
```

Modify `app/engine/__init__.py` 追加导出:

```python
"""宠物营养引擎:纯 Python、零 LLM、可独立单测。"""
from app.engine.evaluate import assess

__all__ = ["assess"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine_evaluate.py -v`
Expected: PASS(7 passed)

- [ ] **Step 5: Commit**

```bash
git add app/engine/evaluate.py app/engine/__init__.py tests/test_engine_evaluate.py
git commit -m "feat(engine): add assessment orchestrator with golden integration tests"
```

---

## Task 8: 全量回归与静态检查

**Files:** 无新增,仅验证。

- [ ] **Step 1: Run all engine tests**

Run: `pytest tests/test_engine_loader.py tests/test_engine_energy.py tests/test_engine_nutrient.py tests/test_engine_requirements.py tests/test_engine_constraints.py tests/test_engine_allergens.py tests/test_engine_evaluate.py -v`
Expected: PASS(46 passed = 4+9+9+7+5+5+7)

- [ ] **Step 2: Run full suite (确认未破坏现有测试)**

Run: `pytest -q`
Expected: 新增 46 个引擎测试全过;现有医疗相关测试状态不变(引擎与之解耦)。

- [ ] **Step 3: Lint & type check**

Run: `ruff check app/engine/ tests/test_engine_*.py`
Expected: All checks passed.

Run: `mypy app/engine/`
Expected: no errors(如个别 dict 取值类型告警,按 ruff/mypy 现有配置宽容处理)。

- [ ] **Step 4: Commit any lint fixes**

```bash
git add -A app/engine/ tests/
git commit -m "chore(engine): lint and type-check fixes"
```

---

## Spec 覆盖映射(self-review)

| 设计文档(spec)条目 | 本计划任务 |
|------|------|
| §4.1 能量需求 RER/MER + 系数表 | Task 2 + `data/mer_factors.json` |
| §4.2 营养素分析(自制/商品粮/DMB/Atwater) | Task 3 + `data/ingredients.json` |
| §4.3 营养需求标准(物种×阶段) | Task 4 + `data/nutrient_requirements.json` |
| §4.4 疾病约束(肾病/肥胖/糖尿病) | Task 5 + `data/disease_constraints.json` |
| §4.5 过敏原检查 | Task 6 + `data/allergens.json` |
| §4.6 综合评估 + 严重度 + NutritionAssessment | Task 7 |
| §8 数据可证明性(每文件 source/version/review_date) | 全部 data 文件 + loader 强校验 |
| §11 五个黄金测试 | test_rer_neutered_cat_5kg(T2)、test_dmb_conversion(T3)、test_homemade_allmeat_low_calcium_flagged / test_kidney_cat_high_phosphorus_flagged / test_homemade_cat_taurine_deficiency_flagged(T7) |
| §5 工具层 / §6 图编排 / §7 多模态 / §10 旧代码删除 | **不在本计划**(Plan 2) |
| §9 报告渲染 / 前端 | **不在本计划**(Plan 2 报告由 final_answer 渲染;UI 见 Plan 3) |

**Self-review 结论:**
- **覆盖**:spec 第 4、8、11 节(引擎 + 数据 + 可证明性)全覆盖;工具/图/前端按计划拆分明确归属 Plan 2/3。
- **占位符**:已清除(含一次 import 笔误修正)。每个 step 均含可直接落地的真实代码、真实数值、确切命令与预期输出。
- **类型一致性**:`DietTotals`/`assess`/`compute_mer`/`get_requirements`/`apply_constraints`/`check_allergens` 在定义、测试、`evaluate` 调用三处签名一致;`Finding.nutrient` 统一用短名(calcium/phosphorus/taurine),与 spec 黄金测试断言一致。
- **数据真实性边界**:`data/*.json` 数值为公开标准的 Demo 精选近似值并标注来源;黄金测试中"判定逻辑类"用注入 fixture 保证确定性,"算法类"(RER/MER/DMB/Atwater)直接对教科书算例 —— 二者共同构成"计算正确"的证明。

---

## 执行衔接

本计划产出独立可测的营养引擎。完成后进入 **Plan 2(Agent 集成)**:把 `assess` / `compute_mer` / `analyze_*` 包成工具,改造 AgentState 与图,写 system prompt,清理旧医疗代码 —— 那时可直接引用本计划落地的**真实引擎 API**。
