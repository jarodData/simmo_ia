# routes/ia_router.py  — version corrigée

from fastapi                          import APIRouter, Query, Depends, HTTPException, Header, BackgroundTasks
from sqlalchemy.orm                   import Session
from apscheduler.schedulers.asyncio   import AsyncIOScheduler
from database                         import get_db, fetch_annonces
from schemas.ia_schemas               import (
    RequeteRecommandation, ReponseRecommandation,
    RequetePrixPredit, ReponsePrixPredit, RequeteContextuelle
)
from utils.hybrid_engine              import MoteurHybride
from models.scoring_contextuel        import ScoringContextuel
from config                           import settings
import logging
import joblib
import re
from functools                        import lru_cache
from schemas.ia_schemas               import RequeteNLP
from pathlib import Path


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
moteur = MoteurHybride()
#model  = joblib.load('C:\www\projet-simmo\simmo_ia\simmo_ia\modeles\modele_prix.pkl')
#model = joblib.load(MODEL_DIR / "modele_prix.pkl")


# router = APIRouter()

@router.get("/test")
def test():
    return {"status": "ok"}


if not moteur.prix.charger_modele():
    print("modele prix non trouve. Lance POST /api/ia/entrainer une fois")

scoreur_contextuel = ScoringContextuel()
scheduler = AsyncIOScheduler()


# ─────────────────────────────────────────────────────
# Utilitaires internes
# ─────────────────────────────────────────────────────

def verifier_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide.")


async def recharger_moteur(db_session=None):
    try:
        from database import SessionLocal
        db       = db_session or SessionLocal()
        annonces = fetch_annonces(db)
        if not db_session:
            db.close()

        if not annonces:
            logger.warning("Aucune annonce active pour entraîner le moteur.")
            return 0

        moteur.annonces       = annonces
        moteur.prix.annonces  = annonces

        if not moteur.nlp.charger():
            moteur.nlp.entrainer_sur_corpus(annonces)
            moteur.nlp.sauvegarder()

        if not moteur.prix.charger_modele():
            moteur.prix.entrainer(annonces)
            moteur.prix.sauvegarder_modele()

        print(f"Moteur prêt - {len(annonces)} annonces chargées.")
        logger.info(f"Moteur ré-entraîné — {len(annonces)} annonces.")
        return len(annonces)

    except Exception as e:
        logger.error(f"Erreur rechargement moteur : {e}", exc_info=True)
        return 0


# ─────────────────────────────────────────────────────
# Scheduler
# ─────────────────────────────────────────────────────

def demarrer_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            recharger_moteur,
            trigger          = 'interval',
            hours            = 6,
            id               = 'recharger_moteur',
            max_instances    = 1,
            replace_existing = True,
        )
        scheduler.start()
        print("Scheduler démarré — rechargement toutes les 6h.")


@router.on_event("shutdown")
async def shutdown():
    scheduler.shutdown(wait=False)
    logger.info("Scheduler arrêté.")


# ─────────────────────────────────────────────────────
# /api/annonces
# ─────────────────────────────────────────────────────

@router.get("/annonces")
def get_annonces(
    limit : int     = Query(default=6),
    db    : Session = Depends(get_db),
):
    annonces = fetch_annonces(db)
    if not annonces:
        return {"annonces": [], "total": 0}

    annonces_triees = sorted(annonces, key=lambda x: x.get("id", 0), reverse=True)
    return {"annonces": annonces_triees[:limit], "total": len(annonces)}


# ─────────────────────────────────────────────────────
# /api/recherche
# ─────────────────────────────────────────────────────

@router.get("/recherche")
def recherche(
    tri:              str   = Query(default="pertinent"),
    page:             int   = Query(default=1),
    q:                str   = Query(default=None),
    ville:            str   = Query(default=None),
    budget_max:       float = Query(default=None),
    budget_min:       float = Query(default=None),
    type_bien:        str   = Query(default=None),
    type_transaction: str   = Query(default=None),
    nb_chambres:      int   = Query(default=None),
    surface_min:      float = Query(default=None),
    meuble:           bool  = Query(default=None),
    latitude:         float = Query(default=None),
    longitude:        float = Query(default=None),
    db:               Session = Depends(get_db),
):
    limite = 12
    page   = max(1, page)

    toutes = fetch_annonces(db)
    if not toutes:
        return {"annonces": [], "total": 0, "page": page, "pages": 0}

    requete = {
        k: v for k, v in {
            "q":               q,
            "ville":           ville,
            "budget_max":      budget_max,
            "budget_min":      budget_min,
            "type_bien":       type_bien,
            "type_transaction":type_transaction,
            "nb_chambres":     nb_chambres,
            "surface_min":     surface_min,
            "meuble":          meuble,
            "latitude":        latitude,
            "longitude":       longitude,
            "limite":          10000,
        }.items() if v is not None
    }

    resultats = moteur.recommander(toutes, requete)

    if   tri == "prix_asc":  resultats.sort(key=lambda x: x["prix"])
    elif tri == "prix_desc": resultats.sort(key=lambda x: x["prix"], reverse=True)
    elif tri == "populaire": resultats.sort(key=lambda x: x["score_popularite"], reverse=True)
    elif tri == "recent":    resultats.sort(key=lambda x: x["id_annonce"], reverse=True)

    total = len(resultats)
    debut = (page - 1) * limite
    pages = (total + limite - 1) // limite

    return {
        "annonces": resultats[debut : debut + limite],
        "total":    total,
        "page":     page,
        "pages":    pages,
    }


# ─────────────────────────────────────────────────────
# /api/ia/recommander
# ─────────────────────────────────────────────────────

@router.post("/ia/recommander")
def recommander(
    requete : RequeteRecommandation,
    db      : Session = Depends(get_db),
    _       : None    = Depends(verifier_api_key),
):
    annonces = fetch_annonces(db)
    if not annonces:
        return ReponseRecommandation(total=0, recommandations=[])

    if requete.budget_max:
        annonces = [a for a in annonces if a.get('prix', 999) <= requete.budget_max]
    if requete.budget_min:
        annonces = [a for a in annonces if a.get('prix', 0) >= requete.budget_min]
    if not annonces:
        return ReponseRecommandation(total=0, recommandations=[], message="Aucune annonce dans ce budget")

    photos    = {a["id"]: a.get("photo") for a in annonces}
    resultats = moteur.recommander(annonces, requete.dict())

    for r in resultats:
        id_annonce = r.get("id_annonce") or r.get("id")
        r["photo"] = photos.get(id_annonce)

    return ReponseRecommandation(total=len(resultats), recommandations=resultats)


# ─────────────────────────────────────────────────────
# /api/ia/predire-prix
# ─────────────────────────────────────────────────────

@router.post("/ia/predire-prix", response_model=ReponsePrixPredit)
def predire_prix(
    requete : RequetePrixPredit,
    _       : None = Depends(verifier_api_key),
):
    prediction = moteur.prix.predire_prix(
        ville            = requete.ville,
        categorie        = requete.categorie,
        surface_m2       = requete.surface_m2,
        nb_chambres      = requete.nb_chambres,
        meuble           = requete.meuble,
        type_transaction = requete.type_transaction,
        quartier         = requete.quartier or "Inconnu",
    )
    if prediction["prix_estime"] is None:
        raise HTTPException(status_code=503, detail="Modèle de prédiction pas encore disponible.")
    return ReponsePrixPredit(**prediction)


# ─────────────────────────────────────────────────────
# /api/ia/entrainer
# ─────────────────────────────────────────────────────

@router.post("/ia/entrainer")
def entrainer(
    db : Session = Depends(get_db),
    _  : None    = Depends(verifier_api_key),
):
    annonces = fetch_annonces(db)
    moteur.entrainer(annonces)
    return {"message": f"Modèles entraînés sur {len(annonces)} annonces."}


# ─────────────────────────────────────────────────────
# /api/ia/recharger
# ─────────────────────────────────────────────────────

@router.post("/ia/recharger")
async def recharger_manuel(
    background_tasks : BackgroundTasks,
    _                : None = Depends(verifier_api_key),
):
    background_tasks.add_task(recharger_moteur)
    return {"message": "Rechargement lancé en arrière-plan.", "status": "ok"}


# ─────────────────────────────────────────────────────
# /api/ia/status
# ─────────────────────────────────────────────────────

@router.get("/ia/status")
def statut_moteur(_: None = Depends(verifier_api_key)):
    prochain = scheduler.get_job("recharger_moteur")
    return {
        "moteur_entraine":       moteur.nlp.est_entraine,
        "prochain_rechargement": str(prochain.next_run_time if prochain else "inconnu"),
    }


# ─────────────────────────────────────────────────────
# /api/ia/health
# ─────────────────────────────────────────────────────

# @router.get("/ia/health")
# def health():
#     return {
#         "statut":          "ok",
#         "version":         settings.VERSION,
#         "modele_entraine": moteur.prix.est_entraine,
#     }

@router.api_route("/ia/health", methods=["GET", "HEAD"])
def health():
    return {
        "statut":          "ok",
        "version":         settings.VERSION,
        "modele_entraine": moteur.prix.est_entraine,
    }


# ─────────────────────────────────────────────────────
# /api/ia/recherche-contextuelle  — VERSION CORRIGÉE
# ─────────────────────────────────────────────────────

@router.post("/ia/recherche-contextuelle")
def recherche_contextuelle(
    requete : RequeteContextuelle,
    db      : Session = Depends(get_db),
    _       : None    = Depends(verifier_api_key),
):
    annonces = fetch_annonces(db)

    lieu_geocode        = None
    lieux_culte         = []
    commodites_trouvees = {}
    lieux_culte_ref     = []  # tous les lieux de culte depuis le point ref

    # ── Géocodage du lieu de référence ──────────────
    if requete.lieu_reference:
        lieu_geocode = scoreur_contextuel.geocoder_lieu(
            requete.lieu_reference,
            requete.ville_reference or ""
        )

    # OPTIMISATION 1 : UN SEUL appel Overpass pour la religion
    # depuis le point de référence avec grand rayon (5km)
    # Puis on filtre localement pour chaque annonce
    if requete.religion and lieu_geocode:
        info_ref = scoreur_contextuel.chercher_culte_depuis_reference(
            lat_ref   = lieu_geocode["latitude"],
            lon_ref   = lieu_geocode["longitude"],
            religion  = requete.religion,
            rayon_km  = 5,
        )
        lieux_culte     = info_ref.get('lieux', [])
        lieux_culte_ref = lieux_culte  # réutilisé pour chaque annonce

    # Commodités (avec cache)
    if requete.commodites and lieu_geocode:
        for commodite in requete.commodites:
            lieux = scoreur_contextuel.chercher_lieux_proches(
                lat       = lieu_geocode["latitude"],
                lon       = lieu_geocode["longitude"],
                type_lieu = commodite,
                rayon_km  = 5,
            )
            if lieux:
                commodites_trouvees[commodite] = lieux[:3]

    # ── Filtrage ─────────────────────────────────────
    filtres_standards = {k: v for k, v in {
        "ville":            requete.ville_reference,
        "type_bien":        requete.type_bien,
        "budget_max":       requete.budget_max,
        "budget_min":       requete.budget_min,
        "nb_chambres":      requete.nb_chambres,
        "type_transaction": requete.type_transaction,
        "surface_min":      requete.surface_min,
        "meuble":           requete.meuble,
    }.items() if v is not None}

    filtrees = moteur._appliquer_filtres(annonces, filtres_standards)

    if not filtrees:
        return {
            "total": 0, "lieu_geocode": lieu_geocode,
            "lieux_culte_trouves": lieux_culte, "annonces": [],
        }

    # ── Scores ───────────────────────────────────────
    scores_proximite = (
        scoreur_contextuel.scorer_annonces_par_contexte(
            filtrees, lieu_geocode["latitude"], lieu_geocode["longitude"],
        )
        if lieu_geocode else [0.5] * len(filtrees)
    )

    if lieu_geocode:
        for i, a in enumerate(filtrees):
            if not a.get("latitude") or not a.get("longitude"):
                scores_proximite[i] = 0.5

    texte       = f"{requete.type_bien or ''} {requete.religion or ''}"
    scores_nlp  = moteur.nlp.calculer_similarite(texte, filtrees)
    scores_prix = moteur._score_prix(filtrees, filtres_standards)

    # OPTIMISATION 2 : analyser_contexte_quartier avec cache
    # Grouper par coordonnées arrondies pour éviter doublons
    cache_quartier = {}
    for a in filtrees:
        if a.get("latitude") and a.get("longitude"):
            coord_key = (round(float(a["latitude"]), 3), round(float(a["longitude"]), 3))
            if coord_key not in cache_quartier:
                cache_quartier[coord_key] = scoreur_contextuel.analyser_contexte_quartier(
                    float(a["latitude"]), float(a["longitude"])
                )

    # OPTIMISATION 3 : prédictions prix en BATCH (1 seul appel ML)
    predictions = moteur.prix.predire_prix_batch(filtrees) if moteur.prix.est_entraine else [{'prix_estime': None}] * len(filtrees)

    resultats = []
    for i, annonce in enumerate(filtrees):
        score_final = round(
            float(scores_proximite[i]) * 0.40 +
            float(scores_prix[i])      * 0.30 +
            float(scores_nlp[i])       * 0.30,
            4
        )

        distance_ref     = None
        analyse_quartier = {}
        culte_annonce    = []

        if annonce.get("latitude") and annonce.get("longitude"):
            lat_a = float(annonce["latitude"])
            lon_a = float(annonce["longitude"])
            coord_key = (round(lat_a, 3), round(lon_a, 3))

            if lieu_geocode:
                distance_ref = round(scoreur_contextuel._haversine(
                    lieu_geocode["latitude"], lieu_geocode["longitude"],
                    lat_a, lon_a,
                ), 2)

            analyse_quartier = cache_quartier.get(coord_key, {})

            # OPTIMISATION 4 : filtrage LOCAL des lieux de culte
            # sans appel réseau supplémentaire
            if requete.religion and lieux_culte_ref:
                culte_annonce = scoreur_contextuel.lieux_culte_proches_annonce(
                    lat_a, lon_a, lieux_culte_ref, rayon_km=2
                )

        resultats.append({
            "id_annonce":          annonce["id"],
            "titre":               annonce["titre"],
            "prix":                float(annonce["prix"]),
            "categorie":           annonce["categorie"],
            "ville":               annonce["ville"],
            "quartier":            annonce.get("quartier"),
            "latitude":            annonce.get("latitude"),
            "longitude":           annonce.get("longitude"),
            "photo":               annonce.get("photo"),
            "score_final":         score_final,
            "score_proximite":     round(float(scores_proximite[i]), 4),
            "score_nlp":           round(float(scores_nlp[i]), 4),
            "score_prix":          round(float(scores_prix[i]), 4),
            "distance_lieu_ref":   distance_ref,
            "lieux_culte_proches": culte_annonce,
            "analyse_quartier":    analyse_quartier,
            "commodites_proches":  commodites_trouvees,
            "prix_estime":         predictions[i].get("prix_estime"),
            "raison":              _generer_raison_contextuelle(
                score_final, scores_proximite[i], distance_ref,
                requete, culte_annonce, analyse_quartier,
            ),
        })

    resultats.sort(key=lambda x: x["score_final"], reverse=True)
    limite = requete.limite or 10

    return {
        "total":               len(resultats),
        "lieu_geocode":        lieu_geocode,
        "lieux_culte_trouves": lieux_culte,
        "commodites_trouvees": commodites_trouvees,
        "annonces":            resultats[:limite],
    }

# ─────────────────────────────────────────────────────
# /api/ia/analyser-quartier
# ─────────────────────────────────────────────────────

@router.get("/ia/analyser-quartier")
def analyser_quartier(
    lat : float,
    lon : float,
    _   : None = Depends(verifier_api_key),
):
    return scoreur_contextuel.analyser_contexte_quartier(lat, lon)


# ─────────────────────────────────────────────────────
# /api/ia/recherche-nlp
# ─────────────────────────────────────────────────────

@router.post("/ia/recherche-nlp")
def recherche_nlp(
    requete : RequeteNLP,
    db      : Session = Depends(get_db),
    _       : None    = Depends(verifier_api_key),
):
    description = requete.description.strip()
    limite      = requete.limite or 12

    if len(description) < 5:
        raise HTTPException(status_code=400, detail="Description trop courte (min 5 caractères).")

    criteres = extraire_criteres_nlp(description)
    logger.info(f"[NLP] Critères extraits : {criteres}")

    annonces = fetch_annonces(db)
    if not annonces:
        return {"criteres_extraits": criteres, "mots_cles_nlp": [], "recommandations": [], "total": 0}

    filtrees = annonces
    if criteres.get("ville"):
        filtrees = [a for a in filtrees if criteres["ville"].lower() in (a.get("ville") or "").lower()]
    if criteres.get("type_bien"):
        filtrees = [a for a in filtrees if criteres["type_bien"].lower() in (a.get("categorie") or "").lower()]
    if criteres.get("type_transaction"):
        filtrees = [a for a in filtrees if a.get("type_transaction") == criteres["type_transaction"]]
    if criteres.get("budget_max"):
        filtrees = [a for a in filtrees if float(a.get("prix") or 0) <= criteres["budget_max"]]
    if criteres.get("nb_chambres"):
        filtrees = [a for a in filtrees if int(a.get("nb_chambres") or 0) >= criteres["nb_chambres"]]
    if criteres.get("surface_min"):
        filtrees = [a for a in filtrees if float(a.get("surface_m2") or 0) >= criteres["surface_min"]]
    if criteres.get("meuble"):
        filtrees = [a for a in filtrees if a.get("meuble")]

    if len(filtrees) < 3:
        logger.warning("[NLP] Pré-filtrage trop restrictif, élargissement.")
        filtrees = annonces[:100]

    scores_nlp  = moteur.nlp.calculer_similarite(description, filtrees)
    scores_prix = moteur._score_prix(filtrees, criteres)

    resultats = []
    for i, annonce in enumerate(filtrees):
        score_nlp   = float(scores_nlp[i])
        score_prix  = float(scores_prix[i])
        score_final = round(score_nlp * 0.70 + score_prix * 0.30, 4)

        prix_estime = None
        if moteur.prix.est_entraine:
            prediction = moteur.prix.predire_prix(
                ville            = annonce.get("ville", ""),
                categorie        = annonce.get("categorie", ""),
                surface_m2       = annonce.get("surface_m2") or 50,
                nb_chambres      = annonce.get("nb_chambres") or 1,
                meuble           = annonce.get("meuble") or False,
                type_transaction = annonce.get("type_transaction", "location"),
                quartier         = annonce.get("quartier") or "Inconnu",
            )
            prix_estime = prediction.get("prix_estime")

        raisons = []
        if score_nlp > 0.25:
            raisons.append("correspond à votre description")
        if criteres.get("ville") and criteres["ville"].lower() in (annonce.get("ville") or "").lower():
            raisons.append(f"situé à {criteres['ville']}")
        if criteres.get("budget_max") and float(annonce.get("prix") or 0) <= criteres["budget_max"]:
            raisons.append("dans votre budget")
        if annonce.get("meuble") and criteres.get("meuble"):
            raisons.append("meublé")
        if criteres.get("nb_chambres") and int(annonce.get("nb_chambres") or 0) >= criteres["nb_chambres"]:
            raisons.append(f"{annonce.get('nb_chambres')} chambre(s)")

        resultats.append({
            "id_annonce"  : annonce["id"],
            "titre"       : annonce["titre"],
            "prix"        : float(annonce["prix"]),
            "categorie"   : annonce.get("categorie"),
            "ville"       : annonce.get("ville"),
            "quartier"    : annonce.get("quartier"),
            "latitude"    : annonce.get("latitude"),
            "longitude"   : annonce.get("longitude"),
            "photo"       : annonce.get("photo"),
            "nb_chambres" : annonce.get("nb_chambres"),
            "surface_m2"  : annonce.get("surface_m2"),
            "meuble"      : annonce.get("meuble"),
            "score_final" : score_final,
            "score_nlp"   : round(score_nlp, 4),
            "score_prix"  : round(score_prix, 4),
            "prix_estime" : prix_estime,
            "raison"      : ("Ce bien " + ", ".join(raisons) + ".") if raisons else "Correspond à votre recherche.",
        })

    resultats.sort(key=lambda x: x["score_final"], reverse=True)
    mots_cles = moteur.nlp.extraire_mots_cles(description, n=6)

    return {
        "criteres_extraits" : criteres,
        "mots_cles_nlp"     : mots_cles,
        "recommandations"   : resultats[:limite],
        "total"             : len(resultats),
    }


# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────

def _generer_raison_contextuelle(score, score_prox, distance,
                                  requete, culte, quartier) -> str:
    raisons = []

    if distance is not None:
        if distance <= 1:
            raisons.append(f"à seulement {distance} km de {requete.lieu_reference or 'votre lieu de référence'}")
        elif distance <= 3:
            raisons.append(f"à {distance} km de {requete.lieu_reference or 'votre lieu de référence'}")

    if requete.religion and culte:
        raisons.append(f"{len(culte)} lieu(x) de culte {requete.religion} à moins de 2 km")

    if quartier.get("ecoles", 0) > 0:
        raisons.append(f"{quartier['ecoles']} école(s) à proximité")

    if quartier.get("hopitaux", 0) > 0:
        raisons.append("hôpital proche")

    if quartier.get("marches", 0) > 0:
        raisons.append("marché à proximité")

    if not raisons:
        raisons.append("correspond à vos critères")

    return "Ce bien " + ", ".join(raisons) + "."


def extraire_criteres_nlp(texte: str) -> dict:
    t        = texte.lower()
    criteres = {}

    types_bien = {
        'appartement' : ['appartement', 'appart'],
        'studio'      : ['studio', 'f1'],
        'villa'       : ['villa', 'maison', 'duplex', 'triplex'],
        'chambre'     : ['chambre seule', 'chambre individuelle'],
        'bureau'      : ['bureau', 'local commercial', 'boutique', 'magasin'],
        'terrain'     : ['terrain', 'parcelle'],
    }
    for type_bien, mots in types_bien.items():
        if any(m in t for m in mots):
            criteres['type_bien'] = type_bien
            break

    villes = {
        'Douala'    : ['douala', 'dla'],
        'Yaounde'   : ['yaounde', 'yaoundé', 'capitale'],
        'Bafoussam' : ['bafoussam', 'baf'],
        'Garoua'    : ['garoua'],
        'Bamenda'   : ['bamenda'],
    }
    for ville, mots in villes.items():
        if any(m in t for m in mots):
            criteres['ville'] = ville
            break

    quartiers = {
        'Bonamoussadi' : ['bonamoussadi', 'bonams'],
        'Akwa'         : ['akwa'],
        'Bonapriso'    : ['bonapriso'],
        'Makepe'       : ['makepe'],
        'Deido'        : ['deido'],
        'Bepanda'      : ['bepanda'],
        'Logpom'       : ['logpom'],
        'Bastos'       : ['bastos'],
        'Nlongkak'     : ['nlongkak'],
    }
    for quartier, mots in quartiers.items():
        if any(m in t for m in mots):
            criteres['quartier'] = quartier
            break

    if any(m in t for m in ['louer', 'location', 'à louer', 'mensuel', 'loyer']):
        criteres['type_transaction'] = 'location'
    elif any(m in t for m in ['acheter', 'achat', 'vente', 'à vendre', 'acquisition']):
        criteres['type_transaction'] = 'vente'

    patterns_budget = [
        (r'(\d[\d\s]*)[\s]*(?:f\s*cfa|fcfa|cfa|xaf|francs?)', False),
        (r'(\d+)\s*k\b',                                        True),
        (r'moins\s*de\s*(\d[\d\s]*)',                           False),
        (r'budget\s*(?:de|:)?\s*(\d[\d\s]*)',                   False),
        (r'(\d{2,})\s*000',                                     False),
    ]
    for pattern, is_k in patterns_budget:
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            val = int(m.group(1).replace(' ', ''))
            if is_k and val < 10000:
                val *= 1000
            if 1000 < val < 100_000_000:
                criteres['budget_max'] = val
                break

    if 'budget_max' not in criteres:
        if any(m in t for m in ['pas cher', 'abordable', 'économique', 'bon marché', 'modeste']):
            criteres['budget_max'] = 150_000

    for pattern in [r'(\d+)\s*(?:chambre|pièce|piece)', r'f(\d)\b', r'(\d)\s*ch\b']:
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            nb = int(m.group(1))
            if 1 <= nb <= 10:
                criteres['nb_chambres'] = nb
                break

    m = re.search(r'(\d+)\s*m[²2]', t, re.IGNORECASE)
    if m:
        s = int(m.group(1))
        if 10 < s < 2000:
            criteres['surface_min'] = s

    if any(m in t for m in ['meublé', 'meuble', 'équipé', 'avec meubles']):
        criteres['meuble'] = True

    return criteres