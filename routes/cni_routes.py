# routes/cni_routes.py
# Endpoints FastAPI pour la vérification CNI

from fastapi              import APIRouter, UploadFile, File, HTTPException, Depends, Path
from fastapi.responses    import JSONResponse
from sqlalchemy.orm       import Session
from database             import get_db
from models.cni_verifier  import verificateur_cni
from routes.ia_routes     import verifier_api_key
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cni", tags=["CNI"])

MIMES_ACCEPTES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


# ─────────────────────────────────────────────────────
# POST /api/cni/analyser
# Upload + analyse immédiate (sans sauvegarder en base)
# ─────────────────────────────────────────────────────

@router.post("/analyser")
async def analyser_cni(
    fichier : UploadFile = File(..., description="Image CNI (jpg/png/webp, max 5 Mo)"),
    _       : None       = Depends(verifier_api_key),
):
    """
    Analyse une CNI uploadée et retourne le résultat IA.
    Ne sauvegarde rien en base — utiliser /valider pour persister.
    """
    if fichier.content_type not in MIMES_ACCEPTES:
        raise HTTPException(
            status_code = 422,
            detail      = f"Format non supporté : {fichier.content_type}. "
                          f"Acceptés : jpeg, png, webp"
        )

    contenu = await fichier.read()
    if len(contenu) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image trop lourde (max 5 Mo)")

    logger.info(f"[CNI] Analyse démarrée — {fichier.filename} ({len(contenu)//1024} Ko)")

    resultat = verificateur_cni.analyser(contenu, media_type=fichier.content_type)

    if not resultat["succes"]:
        raise HTTPException(status_code=500, detail=resultat["erreur"])

    logger.info(f"[CNI] Résultat : {resultat['analyse']['recommandation']}"
                f" (confiance {resultat['analyse']['score_confiance']})")

    return JSONResponse(content=resultat)


# ─────────────────────────────────────────────────────
# POST /api/cni/valider/{id_agent}
# Analyse + mise à jour statut agent en base
# ─────────────────────────────────────────────────────

@router.post("/valider/{id_agent}")
async def valider_cni_agent(
    id_agent : int        = Path(..., description="ID de l'agent"),
    fichier  : UploadFile = File(...),
    db       : Session    = Depends(get_db),
    _        : None       = Depends(verifier_api_key),
):
    """
    Analyse la CNI et met à jour le statut de l'agent en base :
    - APPROUVER  → statut = 'actif',   cni_valide = True
    - REJETER    → statut = 'rejeté',  cni_valide = False
    - VERIFIER_MANUELLEMENT → statut = 'en_attente', flag manuel
    """
    # Vérifier que l'agent existe
    # agent = db.query(Agent).filter(Agent.id == id_agent).first()
    # if not agent:
    #     raise HTTPException(status_code=404, detail="Agent introuvable")

    contenu = await fichier.read()
    resultat = verificateur_cni.analyser(contenu, media_type=fichier.content_type)

    if not resultat["succes"]:
        raise HTTPException(status_code=500, detail=resultat["erreur"])

    analyse = resultat["analyse"]
    reco    = analyse.get("recommandation")

    # ── Mettre à jour l'agent selon la recommandation ──
    # Décommenter quand le modèle Agent est prêt :
    #
    # if reco == "APPROUVER":
    #     agent.statut     = "actif"
    #     agent.cni_valide = True
    #     agent.cni_donnees = json.dumps(analyse["donnees_extraites"])
    # elif reco == "REJETER":
    #     agent.statut     = "rejete"
    #     agent.cni_valide = False
    #     agent.cni_motif_rejet = analyse.get("motif_recommandation")
    # else:  # VERIFIER_MANUELLEMENT
    #     agent.cni_verif_manuelle = True
    #
    # agent.cni_score_confiance = analyse["score_confiance"]
    # agent.cni_analyse_at      = analyse["analyse_at"]
    # db.commit()

    logger.info(f"[CNI] Agent {id_agent} → {reco}")

    return {
        "id_agent"      : id_agent,
        "recommandation": reco,
        "statut_agent"  : {
            "APPROUVER"             : "actif",
            "REJETER"               : "rejete",
            "VERIFIER_MANUELLEMENT" : "en_attente",
        }.get(reco, "en_attente"),
        "analyse"       : analyse,
    }


# ─────────────────────────────────────────────────────
# POST /api/cni/decision/{id_agent}
# Décision manuelle admin (override IA)
# ─────────────────────────────────────────────────────

@router.post("/decision/{id_agent}")
def decision_manuelle(
    id_agent : int,
    decision : dict,   # {"action": "approuver" | "rejeter", "motif": "..."}
    db       : Session = Depends(get_db),
    _        : None    = Depends(verifier_api_key),
):
    """
    L'admin prend une décision finale, override le résultat IA.
    Body : { "action": "approuver", "motif": "Document vérifié physiquement" }
    """
    action = decision.get("action", "").lower()
    motif  = decision.get("motif", "Décision manuelle admin")

    if action not in ("approuver", "rejeter"):
        raise HTTPException(status_code=422, detail="action doit être 'approuver' ou 'rejeter'")

    # agent = db.query(Agent).filter(Agent.id == id_agent).first()
    # if not agent:
    #     raise HTTPException(404, "Agent introuvable")
    #
    # agent.statut             = "actif"    if action == "approuver" else "rejete"
    # agent.cni_valide         = action == "approuver"
    # agent.cni_decision_admin = action
    # agent.cni_motif_admin    = motif
    # db.commit()

    logger.info(f"[CNI] Décision manuelle agent {id_agent} : {action} — {motif}")

    return {
        "id_agent"  : id_agent,
        "action"    : action,
        "motif"     : motif,
        "nouveau_statut": "actif" if action == "approuver" else "rejete",
    }
