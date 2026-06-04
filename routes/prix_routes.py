from fastapi import APIRouter, Header
from pydantic import BaseModel
import pandas as pd
import joblib
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

MODEL_PATH = r"C:\www\projet-simmo\simmo_ia\simmo_ia\modeles\modele_prix.pkl"
model = joblib.load(MODEL_PATH)


class PayloadPrix(BaseModel):
    ville: str
    categorie: str
    surface_m2: float
    nb_chambres: int
    meuble: bool
    type_transaction: str
    quartier: str


@router.post("/api/ia/predire-prix")
async def predire_prix(payload: PayloadPrix, x_api_key: str = Header(None)):
    logger.debug("Payload reçu : %s", payload.dict())

    df = pd.DataFrame([payload.dict()])
    prix_estime = model.predict(df)[0]

    fourchette_min = max(prix_estime * 0.7, 50_000)
    fourchette_max = prix_estime * 1.3
    fiabilite = "haute" if payload.surface_m2 > 15 else "basse"

    return {
        "prix_estime"   : round(prix_estime),
        "fourchette_min": round(fourchette_min),
        "fourchette_max": round(fourchette_max),
        "fiabilite"     : fiabilite,
    }