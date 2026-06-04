from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from routes.ia_routes import router as ia_router
from routes.cni_routes import router as cni_router
from routes.prix_routes import router as prix_router

logging.basicConfig(level=logging.INFO)

# ---------- LIFESPAN SAFE ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 SIMMo IA démarre...")

    # ⚠️ NE PAS charger modèles lourds ici si possible
    # sinon encapsuler dans try/except

    try:
        print("✔ Startup OK")
    except Exception as e:
        print("❌ Startup error:", e)

    yield

    print("🛑 Arrêt SIMMo IA")

# ---------- APP ----------
app = FastAPI(
    title="SIMMo IA API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routers
app.include_router(ia_router)
app.include_router(prix_router)
app.include_router(cni_router)

@app.get("/")
def root():
    return {"message": "SIMMo IA OK"}