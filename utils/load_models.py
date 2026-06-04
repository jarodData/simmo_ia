import joblib
from config import MODEL_DIR

def load_model(name: str):
    path = MODEL_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Modèle introuvable: {path}")
    return joblib.load(path)