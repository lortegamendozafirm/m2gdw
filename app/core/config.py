from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Configuración de la aplicación usando Pydantic Settings.
    Las variables se cargan desde .env o variables de entorno.
    """
    APP_NAME: str = "Markdown to Google Docs Writer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Google Cloud Settings
    GOOGLE_SERVICE_ACCOUNT_FILE: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
