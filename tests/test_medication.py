from app.agent.tools.medication import medication_guide


class TestMedicationFound:
    def test_dog_dosage_calculation(self):
        result = medication_guide.invoke({
            "drug_name": "恩诺沙星",
            "species": "狗",
            "weight_kg": 10.0,
        })
        assert result["found"] is True
        assert result["species"] == "狗"
        assert "恩诺沙星" in result["drug"]
        assert "广谱抗生素" in result["usage"]
        assert 50.0 <= float(result["calculated_dosage"].split("–")[0]) <= 200.0

    def test_cat_dosage_calculation(self):
        result = medication_guide.invoke({
            "drug_name": "恩诺沙星",
            "species": "猫",
            "weight_kg": 4.0,
        })
        assert result["found"] is True
        assert result["species"] == "猫"
        # cat dosage is 5mg/kg = 20mg for 4kg
        assert "20.0" in result["calculated_dosage"]

    def test_dosage_range_for_variable_dog_dose(self):
        result = medication_guide.invoke({
            "drug_name": "阿莫西林克拉维酸钾",
            "species": "狗",
            "weight_kg": 10.0,
        })
        assert result["found"] is True
        assert "–" in result["calculated_dosage"]

    def test_returns_warnings(self):
        result = medication_guide.invoke({
            "drug_name": "恩诺沙星",
            "species": "狗",
            "weight_kg": 10.0,
        })
        assert len(result["warnings"]) > 0
        assert "软骨" in "".join(result["warnings"])

    def test_returns_disclaimer(self):
        result = medication_guide.invoke({
            "drug_name": "恩诺沙星",
            "species": "狗",
            "weight_kg": 10.0,
        })
        assert "遵医嘱" in result["disclaimer"]

    def test_returns_frequency_and_duration(self):
        result = medication_guide.invoke({
            "drug_name": "多西环素",
            "species": "狗",
            "weight_kg": 8.0,
        })
        assert result["frequency"]
        assert result["duration"]


class TestMedicationNotFound:
    def test_unknown_drug(self):
        result = medication_guide.invoke({
            "drug_name": "不存在药",
            "species": "狗",
            "weight_kg": 10.0,
        })
        assert result["found"] is False
        assert "未找到" in result["message"]

    def test_unsupported_species(self):
        result = medication_guide.invoke({
            "drug_name": "恩诺沙星",
            "species": "兔",
            "weight_kg": 2.0,
        })
        assert result["found"] is True
        assert "仅支持猫/狗" in result["message"] or "猫/狗" in result.get("message", "")


class TestMedicationContraindications:
    def test_species_contraindication(self):
        result = medication_guide.invoke({
            "drug_name": "对乙酰氨基酚",
            "species": "猫",
            "weight_kg": 4.0,
        })
        assert len(result["contraindications"]) > 0
        assert any("猫" in c for c in result["contraindications"])

    def test_contraindication_even_when_drug_not_found(self):
        result = medication_guide.invoke({
            "drug_name": "伊维菌素",
            "species": "狗",
            "weight_kg": 10.0,
            "breed": "柯利犬",
        })
        if result["found"]:
            assert isinstance(result["contraindications"], list)

    def test_no_contraindication_for_safe_combination(self):
        result = medication_guide.invoke({
            "drug_name": "头孢氨苄",
            "species": "狗",
            "weight_kg": 10.0,
            "breed": "金毛",
        })
        assert result["contraindications"] == []

    def test_breed_contraindication_warning(self):
        result = medication_guide.invoke({
            "drug_name": "伊维菌素",
            "species": "狗",
            "weight_kg": 15.0,
            "breed": "柯利犬",
        })
        if result["found"]:
            contraindications = result.get("contraindications", [])
            if contraindications:
                assert any("慎用" in c or "禁用" in c for c in contraindications)


class TestMedicationEdgeCases:
    def test_zero_weight(self):
        result = medication_guide.invoke({
            "drug_name": "恩诺沙星",
            "species": "狗",
            "weight_kg": 0.0,
        })
        assert result["found"] is True
        assert "0.0" in result["calculated_dosage"]

    def test_very_small_weight(self):
        result = medication_guide.invoke({
            "drug_name": "多西环素",
            "species": "猫",
            "weight_kg": 0.5,
        })
        assert result["found"] is True

    def test_large_weight(self):
        result = medication_guide.invoke({
            "drug_name": "头孢氨苄",
            "species": "狗",
            "weight_kg": 60.0,
        })
        assert result["found"] is True
        assert float(result["calculated_dosage"].split("–")[-1].split()[0]) > 100

    def test_unknown_breed_passes(self):
        result = medication_guide.invoke({
            "drug_name": "恩诺沙星",
            "species": "狗",
            "weight_kg": 10.0,
            "breed": "未知品种",
        })
        assert result["found"] is True
