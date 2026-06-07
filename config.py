# import os
# from dotenv import load_dotenv
# from pathlib import Path


# load_dotenv()

# class Settings:
#     # Base de données MySQL (même que Laravel)
#     DB_HOST     : str = os.getenv("DB_HOST", "127.0.0.1")
#     DB_PORT     : str = os.getenv("DB_PORT", "3306")
#     DB_NAME     : str = os.getenv("DB_NAME", "simmo_db")
#     DB_USER     : str = os.getenv("DB_USER", "root")
#     DB_PASSWORD : str = os.getenv("DB_PASSWORD", "")

#     # API
#     API_KEY     : str = os.getenv("IA_API_KEY", "simmo-secret-key-2026")
#     VERSION     : str = "1.0.0"

# settings = Settings()

# BASE_DIR = Path(__file__).resolve().parent
# MODEL_DIR = BASE_DIR / "modeles" 



import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Settings:
    # ── Base de données MySQL ──────────────────────────
    DB_HOST     : str = os.getenv("DB_HOST",     "127.0.0.1")
    DB_PORT     : str = os.getenv("DB_PORT",     "3306")
    DB_NAME     : str = os.getenv("DB_NAME",     "immo_db")
    DB_USER     : str = os.getenv("DB_USER",     "root")
    DB_PASSWORD : str = os.getenv("DB_PASSWORD", "")

    # ── API ───────────────────────────────────────────
    API_KEY           : str = os.getenv("IA_API_KEY",         "simmo-secret-key-2026")
    ANTHROPIC_API_KEY : str = os.getenv("ANTHROPIC_API_KEY",  "")
    VERSION           : str = "1.0.0"

settings = Settings()

BASE_DIR  = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "modeles"
