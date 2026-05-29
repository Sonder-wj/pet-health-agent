import json
from pathlib import Path

from langchain_core.tools import tool

# 从 JSON 文件加载药物数据和禁忌表
_DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "medications.json"
with open(_DATA_PATH, "r", encoding="utf-8") as _f:
    _med_data = json.load(_f)

COMMON_MEDICATIONS = _med_data["medications"]
BREED_CONTRAINDICATIONS = {k: set(v) for k, v in _med_data["breed_contraindications"].items()}
SPECIES_CONTRAINDICATIONS = {k: set(v) for k, v in _med_data["species_contraindications"].items()}


@tool
def medication_guide(
    drug_name: str,
    species: str,
    weight_kg: float,
    breed: str = "",
) -> dict:
    """查询宠物用药剂量、禁忌和注意事项。

    Args:
        drug_name: 药品名称
        species: 宠物种类（狗/猫）
        weight_kg: 宠物体重（公斤）
        breed: 品种名称（可选，用于检查品种禁忌）
    """
    # 品种/物种禁忌检查（药物未找到也检查，安全第一）
    contraindications = []
    for b, forbidden in BREED_CONTRAINDICATIONS.items():
        if breed and b in breed and drug_name in forbidden:
            contraindications.append(f"{b}慎用{drug_name}：可能引起严重不良反应")
    if species in SPECIES_CONTRAINDICATIONS and drug_name in SPECIES_CONTRAINDICATIONS[species]:
        contraindications.append(f"{species}禁用{drug_name}")

    drug = COMMON_MEDICATIONS.get(drug_name)
    if not drug:
        msg = f"数据库中未找到'{drug_name}'的剂量信息。请确认药名是否正确，或咨询兽医获取用药建议。"
        if contraindications:
            msg = f"⚠️ {'; '.join(contraindications)}。" + msg
        return {
            "found": False,
            "drug": drug_name,
            "message": msg,
            "contraindications": contraindications,
        }

    # 剂量计算
    if species == "狗":
        d_min = drug.get("dog_dosage_min", 0)
        d_max = drug.get("dog_dosage_max", d_min)
        unit = drug.get("cat_unit", drug.get("unit", "mg/kg"))
    elif species == "猫":
        d_min = drug.get("cat_dosage_min", 0)
        d_max = drug.get("cat_dosage_max", d_min)
        unit = drug.get("cat_unit", drug.get("unit", "mg/kg"))
    else:
        return {
            "found": True,
            "drug": drug_name,
            "species": species,
            "message": "暂仅支持猫/狗剂量查询，请确认物种",
        }

    total_min = round(d_min * weight_kg, 1)
    total_max = round(d_max * weight_kg, 1)
    dosage_range = f"{total_min}–{total_max} {unit.replace('mg/kg', 'mg')}" if total_min != total_max else f"{total_min} mg"

    return {
        "found": True,
        "drug": drug_name,
        "species": species,
        "breed": breed or "未指定",
        "weight_kg": weight_kg,
        "usage": drug["usage"],
        "dosage_per_kg": f"{d_min}–{d_max} {unit}" if d_min != d_max else f"{d_min} {unit}",
        "calculated_dosage": dosage_range,
        "frequency": drug["frequency"],
        "duration": drug["duration"],
        "warnings": drug.get("warnings", []),
        "contraindications": contraindications,
        "disclaimer": "以上信息仅供紧急参考，具体用药请遵医嘱。",
    }
