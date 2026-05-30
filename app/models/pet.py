"""Pet 档案模型 — 跨 thread 复用,绑定 user。

设计思路:
- 同一 user 下 (user_id, name) 唯一 — 主人可以养多只,但名字不能重复
- 关键营养字段(species/weight/age_months/neutered/conditions/allergens)
  与 AgentState.PetProfile 字段对齐,方便互转
- conditions / allergens 用 JSON 列表存,避免另起 N 张关系表
"""
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from app.core.database import Base


class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)            # 旺财 / 喵喵
    species = Column(String(20), nullable=False)         # "dog" | "cat"
    breed = Column(String(50), nullable=True)            # 品种(可选)
    weight_kg = Column(Float, nullable=False)
    age_months = Column(Integer, nullable=True)
    neutered = Column(Boolean, nullable=True)
    conditions = Column(JSON, nullable=False, default=list)  # ["kidney", "obesity", ...]
    allergens = Column(JSON, nullable=False, default=list)   # ["chicken", "beef", ...]
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_pet_name"),
    )

    def to_dict(self) -> dict:
        """供 Agent / API 使用的序列化形式,字段与 PetProfile TypedDict 对齐。"""
        return {
            "id": self.id,
            "name": self.name,
            "species": self.species,
            "breed": self.breed,
            "weight_kg": self.weight_kg,
            "age_months": self.age_months,
            "neutered": self.neutered,
            "conditions": self.conditions or [],
            "allergens": self.allergens or [],
        }
