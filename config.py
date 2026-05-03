import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Team Metadata
    TEAM_NAME: str = "Vera-Rebuild"
    TEAM_MEMBERS: List[str] = ["Vera Team"]
    BOT_VERSION: str = "1.0.0"
    
    # Model Configuration
    # Models
    PRIMARY_MODEL: str = "llama-3.1-8b-instant"
    SECONDARY_MODEL: str = "llama-3.1-8b-instant"
    TEMPERATURE: float = 0.2
    FALLBACK_MODEL: str = "gemini-1.5-flash" # Gemini
    
    # API Keys (Loaded from .env)
    GROQ_API_KEYS: str = "" # Comma-separated in .env
    GEMINI_API_KEY: str = ""
    
    @property
    def groq_keys_list(self) -> List[str]:
        if not self.GROQ_API_KEYS:
            return []
        return [k.strip() for k in self.GROQ_API_KEYS.split(",") if k.strip()]
    
    # Operational Constraints
    LLM_TIMEOUT: int = 20  # seconds (leaves 10s buffer for 30s budget)
    TEMPERATURE: float = 0.0 # Deterministic
    MAX_ACTIONS_PER_TICK: int = 20
    
    # Server Config
    PORT: int = int(os.environ.get("PORT", 8081))
    HOST: str = "0.0.0.0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
