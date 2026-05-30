from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    # 主对话 LLM(OpenAI 兼容协议 — DeepSeek V4-Flash via 官方 endpoint)
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://api.deepseek.com/v1"
    OPENAI_MODEL: str = "deepseek-v4-flash"

    # 视觉 LLM(OpenAI 兼容协议 — Qwen3-VL-Flash via 阿里百炼)
    # 独立 endpoint/key:主对话与视觉解耦,允许按场景挑成本最优的模型
    VISION_API_KEY: str
    VISION_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    VISION_MODEL: str = "qwen3-vl-flash"

    # MySQL
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    # 7 天 — dev/portfolio 体验优先(30 分钟会频繁踢出登录)。
    # 若上线给真实用户,改回 30~60 分钟 + 配 refresh token。
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # LangGraph checkpoint (AsyncSqliteSaver,异步生命周期由 main.py lifespan 管)
    CHECKPOINT_DB_PATH: str = "nutrition_checkpoints.db"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
