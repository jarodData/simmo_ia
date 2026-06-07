# main.py — VERSION OPTIMISÉE

from fastapi                 import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib              import asynccontextmanager
import logging

from routes.ia_routes  import router as ia_router, recharger_moteur, demarrer_scheduler, scheduler
from routes.cni_routes import router as cni_router
from routes.prix_routes import router as prix_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SIMMo IA démarre...")

    try:
        # 1. Charger les modèles
        await recharger_moteur()
        demarrer_scheduler()
        logger.info("Moteur IA prêt.")

        # 2. Pré-chauffer le cache Overpass sur Douala centre
        # pour que le premier utilisateur ne paie pas le délai
        try:
            from models.scoring_contextuel import ScoringContextuel
            sc = ScoringContextuel()
            # Douala centre — coordonnées approximatives
            sc.chercher_lieux_proches(4.0511, 9.7679, 'place_of_worship', 'muslim',  5)
            sc.chercher_lieux_proches(4.0511, 9.7679, 'place_of_worship', 'christian', 5)
            sc.chercher_lieux_proches(4.3612, 3.8527, 'place_of_worship', 'muslim',  5)  # Yaoundé
            logger.info("Cache Overpass pré-chargé — Douala + Yaoundé.")
        except Exception as e:
            logger.warning(f"Pré-chauffe Overpass ignorée : {e}")

    except Exception as e:
        logger.error(f"Erreur démarrage : {e}")

    yield

    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("SIMMo IA arrêtée.")


app = FastAPI(
    title    = "SIMMo IA API",
    version  = "1.0.0",
    lifespan = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(ia_router)
app.include_router(prix_router)
app.include_router(cni_router)


# CORRECTION : accepter HEAD pour UptimeRobot
@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "SIMMo IA opérationnelle", "version": "1.0.0"}
