"""UserMemory — 跨 thread 的用户级长事实。

设计:
- 一条 memory = 一段可读文本(Agent 用自然语言写),不做语义检索
- 可选关联 pet_id(很多事实是宠物相关的,如"旺财对鸡肉过敏严重")
- category 字段做粗分类,方便未来按类型筛选/展示
- 没有 unique 约束,允许多条相似内容(Agent 自己负责去重判断)
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.core.database import Base


class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default="general")
    # 常用 category: preference(喜好) / constraint(限制如预算) /
    # history(既往) / veterinary(兽医指示) / general(其他)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pet_id": self.pet_id,
            "content": self.content,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
