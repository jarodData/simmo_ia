import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Base de données MySQL (même que Laravel)
    DB_HOST     : str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT     : str = os.getenv("DB_PORT", "3306")
    DB_NAME     : str = os.getenv("DB_NAME", "simmo_db")
    DB_USER     : str = os.getenv("DB_USER", "root")
    DB_PASSWORD : str = os.getenv("DB_PASSWORD", "")

    # API
    API_KEY     : str = os.getenv("IA_API_KEY", "simmo-secret-key-2026")
    VERSION     : str = "1.0.0"

settings = Settings()