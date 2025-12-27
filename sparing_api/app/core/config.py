from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field
from typing import List
import json

class Settings(BaseSettings):
    app_env: str = "dev"
    tz: str = "Asia/Jakarta"
    db_url: str = "mysql+aiomysql://sparing:sparing@mysql:3306/sparing"
    jwt_secret: str = "change_me"
    jwt_alg: str = "HS256"
    access_token_expire_min: int = 60
    refresh_token_expire_min: int = 60*24*7
    
    # Store as string to avoid pydantic-settings JSON parsing issues
    cors_origins_str: str = Field(
        default="http://localhost:5173,http://localhost:3000,http://localhost:3001",
        alias="CORS_ORIGINS"
    )
    
    rate_limit_per_min: int = 120
    log_level: str = "info"

    # 👇 add these two so pydantic accepts the values from .env
    gunicorn_workers: int = 2
    uvicorn_workers: int = 1

    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        """Parse cors_origins_str into a list of origins."""
        v = self.cors_origins_str.strip()
        if not v:
            return []
        # Try to parse as JSON array first
        if v.startswith("["):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed]
            except json.JSONDecodeError:
                pass
        # Fall back to comma-separated values
        return [s.strip() for s in v.split(",") if s.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,  # Allow both alias and field name
    )

settings = Settings()
