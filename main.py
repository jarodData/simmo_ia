from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from routes.ia_routes import router as ia_router, moteur, recharger_moteur, demarrer_scheduler
from routes.cni_routes import router as cni_router
from routes.prix_routes import router as prix_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Démarrage SIMMo IA...")

    await recharger_moteur()
    print(f"Moteur prêt — {len(moteur.prix.annonces)} annonces chargées.")

    demarrer_scheduler()

    yield

    from routes.ia_routes import scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)
    print("Arrêt SIMMo IA.")


app = FastAPI(
    title       = "SIMMo IA API",
    description = "API Intelligence Artificielle pour SIMMo",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(cni_router)
app.include_router(ia_router)

app.include_router(prix_router)

@app.get("/")
def root():
    return {"message": "SIMMo IA opérationnelle", "version": "1.0.0"}